"""certificate — exact-rational disconnection certificate (session S4, SPEC §4).

This is the GENERATOR side of the credibility split. It turns a :class:`Scene`
(robot + obstacles + barrier, all exact rationals) into:

  * a float :class:`cnp.engine.Problem` the branch-and-bound solves
    (:func:`scene_to_problem`); and
  * a JSON certificate of **exact rationals** that an INDEPENDENT verifier
    (:mod:`cnp.verify`) re-checks in exact arithmetic (:func:`make_certificate`).

What goes in the certificate (SPEC §4, finalised here per CLAUDE.md rule 12):
``q_star``, the locked-joint values, the *home-made* half-angle substitution and
the per-link common denominator are all DEFINED in the certificate / scene, so
everything verify recomputes is pinned down by the certificate, never by the
generator's code (CLAUDE.md rule 4).

Soundness of the rounding (SPEC §4, "inward rounding with re-solve"). The witness
LP is solved in floating point; its optimum has a strictly positive face margin
``t* > 0`` (every face ``g_j - mu_j T >= t*``). We export rationals so that the
exact verifier accepts:

  * ``mu_j`` is rounded to a nearby non-negative rational;
  * the lambda multipliers of the first ``K-1`` hull vertices are rounded, and the
    LAST one is DERIVED by subtraction so that ``sum_k lambda_k == 1`` holds as an
    *exact* coefficient identity (no rounding can break the equality);
  * the rounding denominator (``max_den = 1e6``) is coarse enough that numerical
    dust (a Bernstein control point that is ``+1e-13`` instead of ``0``) collapses
    to exactly ``0``, yet fine enough (``1e-6 << t*``) that the face margins stay
    positive after rounding.

The exact arbiter is :mod:`cnp.verify`; the round-trip test (generate -> verify)
is the guarantee. If a leaf ever fails exact verification, raise ``max_den``.

Shared kernel with the rest of cnp: :mod:`cnp.polylin` / :mod:`cnp.ratfk` /
:mod:`cnp.engine` / :mod:`cnp.witness` (this is the generator). The verifier shares
NONE of these — it re-implements Bernstein and the FK substitution from scratch.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from fractions import Fraction

import numpy as np

from . import engine, polylin, witness
from .ratfk import RevoluteJoint, SympyRatFK

SPEC_VERSION = "1.2"
SUBSTITUTION = "half_angle_homemade_v1"
DENOMINATOR = "per_link_prod_1_plus_s2"
ASSUMPTIONS = ["no_wraparound_rel_qstar", "static_obstacles", "polytope_geometry"]
DEFAULT_MAX_DEN = 10 ** 6


def Q(x) -> Fraction:
    """Coerce ``x`` (int/str/Fraction/float) to an exact Fraction. A float is taken
    at face value (use :meth:`Fraction.limit_denominator` upstream to get a tidy
    rational from a fitted coefficient)."""
    if isinstance(x, Fraction):
        return x
    if isinstance(x, float):
        return Fraction(x)
    return Fraction(str(x))


# --------------------------------------------------------------------------- #
# Exact scene model
# --------------------------------------------------------------------------- #

@dataclass
class Robot:
    """A serial revolute robot, exact rationals. ``kind="planar_revolute"`` is the
    S4 regression robot (planar n-R arm, joint axes +z, links along local x)."""

    kind: str
    link_lengths: list           # [Fraction]; one per joint (link carried after it)
    q_star: list                 # [Fraction] reference posture (rad), one per joint
    locked: dict = field(default_factory=dict)  # joint idx -> locked angle (rad); S4: {}

    def __post_init__(self):
        self.link_lengths = [Q(v) for v in self.link_lengths]
        self.q_star = [Q(v) for v in self.q_star]
        self.locked = {int(k): Q(v) for k, v in self.locked.items()}

    @property
    def n_joints(self) -> int:
        return len(self.link_lengths)

    @property
    def n(self) -> int:
        """Number of UNLOCKED joints = number of s-variables."""
        return self.n_joints - len(self.locked)


@dataclass
class Scene:
    """A disconnection problem in exact rationals (the certified object)."""

    robot: Robot
    body_link: int               # index of the link carrying the moving convex body
    hull_vertices: list          # [[x, y, z], ...] body-frame hull vertices (rational)
    obstacles: dict              # name -> (A: list[list], b: list) H-rep (rational)
    phi: dict                    # {expo-tuple: coeff} barrier (rational)
    phi_degree: int              # per-variable degree of phi
    delta: Fraction              # slab half-width (rational, > 0)
    box: list                    # [(lo, hi)] per s-variable (rational)
    start_s: list                # [Fraction] s-image of the start config
    goal_s: list                 # [Fraction] s-image of the goal config
    pairs: list                  # obstacle names the body is relayed against
    lam_degree: str = "affine"

    def __post_init__(self):
        self.hull_vertices = [[Q(c) for c in v] for v in self.hull_vertices]
        self.obstacles = {k: ([[Q(x) for x in row] for row in A], [Q(x) for x in b])
                          for k, (A, b) in self.obstacles.items()}
        self.phi = {tuple(e): Q(c) for e, c in self.phi.items()}
        self.delta = Q(self.delta)
        self.box = [(Q(lo), Q(hi)) for lo, hi in self.box]
        self.start_s = [Q(v) for v in self.start_s]
        self.goal_s = [Q(v) for v in self.goal_s]


# --------------------------------------------------------------------------- #
# Float (generator) FK + problem construction
# --------------------------------------------------------------------------- #

def _planar_joints(robot: Robot) -> list:
    """Build the generic revolute chain for a planar arm: joint axes +z, each joint
    offset from the previous link frame by the previous link's length along x."""
    joints = []
    prev = 0.0
    for i in range(robot.n_joints):
        Xpj = np.eye(4)
        Xpj[0, 3] = prev
        joints.append(RevoluteJoint(f"link{i}", Xpj, np.array([0.0, 0.0, 1.0])))
        prev = float(robot.link_lengths[i])
    return joints


def _body_numerators(scene: Scene):
    """Vertex numerators + common denominator of the moving body (float, via the S1
    generator FK :class:`cnp.ratfk.SympyRatFK`)."""
    if scene.robot.kind != "planar_revolute":
        raise NotImplementedError(f"robot kind {scene.robot.kind!r} not in S4")
    fk = SympyRatFK(_planar_joints(scene.robot),
                    locked={k: float(v) for k, v in scene.robot.locked.items()},
                    q_star=[float(v) for v in scene.robot.q_star])
    body = fk.body(f"link{scene.body_link}")
    verts = body.vertex_numerators([[float(c) for c in v] for v in scene.hull_vertices])
    return verts, body.D


def _phi_tensor(scene: Scene) -> np.ndarray:
    t = polylin.zeros(scene.robot.n, scene.phi_degree)
    for e, c in scene.phi.items():
        t[tuple(e)] = float(c)
    return t


def _polytope(A, b) -> witness.Polytope:
    return witness.Polytope(np.array([[float(x) for x in row] for row in A]),
                            np.array([float(x) for x in b]))


def scene_to_problem(scene: Scene, **kw) -> engine.Problem:
    """Build the float :class:`cnp.engine.Problem` the branch-and-bound solves."""
    verts, D = _body_numerators(scene)
    pairs = [engine.Pair(nm, verts, D, _polytope(*scene.obstacles[nm]))
             for nm in scene.pairs]
    return engine.Problem(box=[(float(lo), float(hi)) for lo, hi in scene.box],
                          phi=_phi_tensor(scene), delta=float(scene.delta),
                          pairs=pairs, lam_degree=scene.lam_degree, **kw)


# --------------------------------------------------------------------------- #
# Exact-rational helpers (serialisation)
# --------------------------------------------------------------------------- #

def _phi_eval(scene: Scene, s) -> Fraction:
    """Exact phi(s) for a rational point s (the generator can do this exactly)."""
    acc = Fraction(0)
    for e, c in scene.phi.items():
        term = c
        for i, p in enumerate(e):
            term *= s[i] ** p
        acc += term
    return acc


def _expo_key(e) -> str:
    return ",".join(str(int(x)) for x in e)


def _tensor_str(d: dict) -> dict:
    """Serialise a sparse {expo: Fraction} tensor, dropping exact zeros."""
    return {_expo_key(e): str(c) for e, c in d.items() if c != 0}


# --------------------------------------------------------------------------- #
# Per-leaf certification (re-solve, round inward, derive last lambda)
# --------------------------------------------------------------------------- #

def _round_lambda(z, basis, max_den: int) -> list:
    """Round lambda multipliers to rationals so that ``sum_k lambda_k == 1`` is EXACT:
    round the first K-1 vertices coefficient-by-coefficient, DERIVE the last by
    subtracting them from the constant-1 tensor (no rounding can break the identity)."""
    K, B = z.shape
    basis = list(basis)
    origin = tuple([0] * len(basis[0]))
    lam = []
    for k in range(K - 1):
        lam.append({basis[j]: Fraction(float(z[k, j])).limit_denominator(max_den)
                    for j in range(B)})
    last = {}
    for e in basis:
        s = sum((lam[k].get(e, Fraction(0)) for k in range(K - 1)), Fraction(0))
        last[e] = (Fraction(1) if e == origin else Fraction(0)) - s
    lam.append(last)
    return lam


def _lambda_float(lam: list, basis) -> np.ndarray:
    """Flatten rational lambda dicts back to a float decision vector (basis order)."""
    basis = list(basis)
    return np.array([float(lam[k].get(e, Fraction(0)))
                     for k in range(len(lam)) for e in basis])


def _export_multipliers(res, lp, max_den: int):
    """Turn the float LP optimum into EXACT rational (lambda, mu) that the exact
    verifier accepts. Two robustness steps (SPEC §4 "inward rounding with re-solve"):

      * blend lambda toward the body barycenter by a small alpha so structural-zero
        Bernstein control points (the witness sitting exactly on a hull vertex) lift to
        ``alpha/K > 0`` and survive rounding (the barycenter sums to 1, so the equality
        is preserved); alpha is kept well below the face margin so faces stay positive;
      * round to ``max_den``; re-check feasibility in float with a strict positive
        threshold, escalating (alpha, max_den) until it holds (the exact verifier is
        the final arbiter).
    """
    K, B = res.K, len(res.basis)
    basis = list(res.basis)
    origin_idx = basis.index(tuple([0] * len(basis[0])))
    z = res.z.reshape(K, B)
    bary = np.zeros((K, B))
    bary[:, origin_idx] = 1.0 / K
    face0 = lp.face_Az @ res.z + (lp.face_Amu @ res.mu if res.mu is not None else 0)
    face_margin = float((face0 + lp.face_b).min())
    mu_src = res.mu if res.mu is not None else np.zeros(0)

    for alpha in (min(1e-2, 0.2 * face_margin), 1e-3, 1e-4, 1e-5):
        if alpha <= 0:
            continue
        for md in (max_den, max_den * 100, max_den * 10000):
            zbl = (1 - alpha) * z + alpha * bary
            lam = _round_lambda(zbl, basis, md)
            mu = [max(Fraction(0), Fraction(float(m)).limit_denominator(md))
                  for m in mu_src]
            zf = _lambda_float(lam, basis)
            muf = np.array([float(m) for m in mu])
            lam_ok = (lp.lam_A @ zf + lp.lam_b).min() >= 1e-12
            face = lp.face_Az @ zf + (lp.face_Amu @ muf if len(muf) else 0) + lp.face_b
            if lam_ok and face.min() >= 1e-12:
                return lam, mu
    raise ValueError("could not round leaf to an exactly-feasible certificate "
                     f"(face margin {face_margin:.2e}); re-solve / subdivide needed")


def _collision_leaf(scene: Scene, lf, verts, D, backend, max_den: int) -> dict:
    """Re-solve the witness LP for the leaf's winning pair and export exact λ, μ."""
    cell = [(float(lo), float(hi)) for lo, hi in lf.cell]
    obstacle = _polytope(*scene.obstacles[lf.pair])
    phi = _phi_tensor(scene)
    lp = witness.build_witness_lp(cell, verts, D, obstacle, phi=phi,
                                  delta=float(scene.delta), lam_degree=scene.lam_degree)
    res = backend.solve(lp)
    if res.z is None or res.t is None or res.t <= 0:
        raise ValueError(f"leaf {lf.cell} did not re-solve to a positive margin "
                         f"(status={res.status})")
    lam, mu = _export_multipliers(res, lp, max_den)
    return {"cell": [[str(lo), str(hi)] for lo, hi in lf.cell], "status": "collision",
            "obstacle": lf.pair, "lambda": [_tensor_str(t) for t in lam],
            "mu": [str(m) for m in mu],
            "margin": str(Fraction(float(res.t)).limit_denominator(max_den))}


# --------------------------------------------------------------------------- #
# Certificate assembly
# --------------------------------------------------------------------------- #

def make_certificate(scene: Scene, result: engine.EngineResult,
                     backend=None, max_den: int = DEFAULT_MAX_DEN) -> dict:
    """Assemble the exact-rational JSON certificate from a PROOF engine result.

    Raises if the result is not a PROOF (UNDECIDED is not certifiable, SPEC §1)."""
    if result.verdict != "PROOF":
        raise ValueError("cannot certify a non-PROOF result (verdict="
                         f"{result.verdict}); this is UNDECIDED, not a proof")
    backend = backend or engine.ENGINE_BACKEND
    verts, D = _body_numerators(scene)

    leaves = []
    for lf in result.leaves:
        if lf.status == "outside":
            leaves.append({"cell": [[str(lo), str(hi)] for lo, hi in lf.cell],
                           "status": "outside"})
        elif lf.status == "collision":
            leaves.append(_collision_leaf(scene, lf, verts, D, backend, max_den))
        else:  # pragma: no cover - guarded by the verdict check above
            raise ValueError(f"undecided leaf in a PROOF result: {lf.status}")

    r = scene.robot
    cert = {
        "spec_version": SPEC_VERSION,
        "theorem": "disconnection",
        "robot": {
            "kind": r.kind,
            "link_lengths": [str(v) for v in r.link_lengths],
            "q_star": [str(v) for v in r.q_star],
            "locked_joints": {str(k): str(v) for k, v in r.locked.items()},
            "n": r.n,
        },
        "kinematics": {"substitution": SUBSTITUTION, "denominator": DENOMINATOR},
        "assumptions": ASSUMPTIONS,
        "body": {"link": scene.body_link,
                 "hull_vertices": [[str(c) for c in v] for v in scene.hull_vertices]},
        "obstacles": {nm: {"A": [[str(x) for x in row] for row in A],
                           "b": [str(x) for x in b]}
                      for nm, (A, b) in scene.obstacles.items()},
        "phi": {"degree_per_var": scene.phi_degree, "n": r.n,
                "coeffs": _tensor_str(scene.phi)},
        "delta": str(scene.delta),
        "box": [[str(lo), str(hi)] for lo, hi in scene.box],
        "start_s": [str(v) for v in scene.start_s],
        "goal_s": [str(v) for v in scene.goal_s],
        "checks": {"phi_start": str(_phi_eval(scene, scene.start_s)),
                   "phi_goal": str(_phi_eval(scene, scene.goal_s))},
        "lam_degree": scene.lam_degree,
        "pairs": list(scene.pairs),
        "leaves": leaves,
        "stats": {"n_leaves": len(leaves),
                  "n_collision": sum(1 for l in leaves if l["status"] == "collision"),
                  "n_outside": sum(1 for l in leaves if l["status"] == "outside")},
    }
    return cert


def certify(scene: Scene, backend=None, max_den: int = DEFAULT_MAX_DEN,
            **solve_kw) -> tuple:
    """Solve the scene and build its certificate. Returns ``(result, cert_dict)``."""
    problem = scene_to_problem(scene)
    result = engine.solve(problem, **solve_kw)
    cert = make_certificate(scene, result, backend=backend, max_den=max_den)
    return result, cert


def save(cert: dict, path: str) -> None:
    with open(path, "w") as f:
        json.dump(cert, f, indent=2, sort_keys=True)


def load(path: str) -> dict:
    with open(path) as f:
        return json.load(f)
