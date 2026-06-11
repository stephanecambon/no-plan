"""scenes — YAML scene parser -> exact-rational :class:`cnp.certificate.Scene` (S6).

A scene file is the human-authored entry point of the tool. It is parsed into the
SAME exact-rational :class:`~cnp.certificate.Scene` that the certificate generator
and the independent verifier already share (S4), so ``cnp certify scene.yaml`` is just
``parse -> scene_to_problem -> engine.solve -> make_certificate`` and the resulting
certificate is verified by the untrusted :mod:`cnp.verify` exactly as before.

Everything is a rational string ("num/den", "3", "-9/10"); floats are accepted but
read at face value (author tidy rationals). The schema (SPEC §6, amended in S6 —
rule 12: V-rep convex prisms deferred, boxes + H-rep half-planes shipped):

```yaml
robot:
  kind: planar_revolute        # the S4/S6 builtin (axes +z, links along local x)
  link_lengths: ["1", "1", "1"]
  q_star: ["0", "0", "0"]      # optional, default zeros (planar verify needs q*=0)
  locked: {}                   # optional, "idx": "angle_rad"
body:
  link: 2                      # which link carries the moving convex body
  hull_vertices: [["0","0","0"], ["1","0","0"]]   # optional: derived from the link
obstacles:                     # world H-rep; author as an axis-aligned box or raw hrep
  TOOTH0:
    box: [["xlo","xhi"], ["ylo","yhi"], ["zlo","zhi"]]
  WALL:
    hrep: {A: [["1","0","0"], ...], b: ["13/10", ...]}
phi: {degree_per_var: 2, coeffs: {"1,0,0": "1"}}   # barrier hint (rational tensor)
delta: "1/20"
box: [["-1","1"], ["-1","1"], ["-1","1"]]          # the s-box P (one entry per UNLOCKED joint)
start_s: ["-9/10", "0", "0"]
goal_s:  ["9/10", "0", "0"]
pairs: ["TOOTH0", "WALL"]      # optional, default = every obstacle
lam_degree: affine             # optional
budget: {max_depth: 16, max_leaves: null, max_time_s: null}   # optional
```

The convex hull of the moving body is *extracted from the link geometry* (SPEC §6
task 1): for the planar builtin, link ``L`` is the segment ``[0,0,0] -> [len_L,0,0]``
in its body frame, so ``hull_vertices`` defaults to that segment. An explicit
``hull_vertices`` overrides it (e.g. a fatter capsule box).

This module also exposes a generic **collision oracle** for the planar builtin
(:func:`planar_collision_oracle`) that the φ-pipeline (S5) and the ground-truth /
adversarial checks consume — it samples the body link in world space and tests it
against the scene obstacles, independent of the certificate machinery.
"""
from __future__ import annotations

from fractions import Fraction
from dataclasses import dataclass

import numpy as np
import yaml

from . import certificate as _cert
from . import engine as _engine
from .ratfk import RevoluteJoint, SympyRatFK


# --------------------------------------------------------------------------- #
# Obstacle parsing (box / H-rep -> exact-rational H-rep)
# --------------------------------------------------------------------------- #

def _box_to_hrep(box):
    """Axis-aligned world box ``[[lo,hi], ...]`` (one [lo,hi] per world axis) ->
    exact-rational H-rep ``(A, b)``: ``+e_i . y <= hi_i`` and ``-e_i . y <= -lo_i``."""
    dim = len(box)
    los = [_cert.Q(lo) for lo, _ in box]
    his = [_cert.Q(hi) for _, hi in box]
    A, b = [], []
    for i in range(dim):                       # upper faces  +e_i . y <= hi_i
        row = [Fraction(0)] * dim
        row[i] = Fraction(1)
        A.append(row)
        b.append(his[i])
    for i in range(dim):                       # lower faces  -e_i . y <= -lo_i
        row = [Fraction(0)] * dim
        row[i] = Fraction(-1)
        A.append(row)
        b.append(-los[i])
    return A, b


def _parse_obstacle(name, spec):
    """One obstacle spec -> ``(A, b)`` exact-rational H-rep."""
    if not isinstance(spec, dict) or ("box" in spec) == ("hrep" in spec):
        raise ValueError(f"obstacle {name!r}: give exactly one of 'box' or 'hrep'")
    if "box" in spec:
        return _box_to_hrep(spec["box"])
    h = spec["hrep"]
    A = [[_cert.Q(x) for x in row] for row in h["A"]]
    b = [_cert.Q(x) for x in h["b"]]
    if any(len(row) != len(A[0]) for row in A) or len(A) != len(b):
        raise ValueError(f"obstacle {name!r}: malformed H-rep (A/b shape mismatch)")
    return A, b


# --------------------------------------------------------------------------- #
# Robot / body
# --------------------------------------------------------------------------- #

def _parse_robot(spec) -> _cert.Robot:
    kind = spec.get("kind", "planar_revolute")
    locked = spec.get("locked", {}) or {}
    if kind == "spatial_revolute":
        joints = spec["joints"]
        n_joints = len(joints)
        q_star = spec.get("q_star", ["0"] * n_joints)
        return _cert.Robot(kind=kind, link_lengths=[], q_star=q_star,
                           locked={int(k): v for k, v in locked.items()},
                           joints=joints)
    link_lengths = spec["link_lengths"]
    q_star = spec.get("q_star", ["0"] * len(link_lengths))
    return _cert.Robot(kind=kind, link_lengths=link_lengths, q_star=q_star,
                       locked={int(k): v for k, v in locked.items()})


def _link_hull(robot: _cert.Robot, body_link: int):
    """Convex hull of the moving body, extracted from the link geometry (SPEC §6):
    the planar builtin link ``L`` is the segment ``[0,0,0] -> [len_L, 0, 0]``."""
    if robot.kind != "planar_revolute":
        raise NotImplementedError(f"hull extraction for kind {robot.kind!r} is S9+")
    length = robot.link_lengths[body_link]
    return [[Fraction(0), Fraction(0), Fraction(0)],
            [length, Fraction(0), Fraction(0)]]


# --------------------------------------------------------------------------- #
# Budget
# --------------------------------------------------------------------------- #

@dataclass
class SceneBudget:
    """Solver budget carried by the scene (SPEC §6): depth cap + engine Budget + the
    branch axis heuristic. ``axis`` only changes COST, never soundness (CLAUDE.md
    rule 9): ``"oracle"`` (widest axis, reproduces the E3/E4 partition) or ``"margin"``
    (relay-lookahead — needed when a scene has a PASSIVE joint the widest-axis rule
    would waste depth splitting; the passive-dimension optimisation proper is S8)."""
    max_depth: int = 16
    max_leaves: int | None = None
    max_time_s: float | None = None
    axis: str = "oracle"

    def engine_budget(self) -> _engine.Budget:
        return _engine.Budget(max_leaves=self.max_leaves, max_time_s=self.max_time_s)


def _parse_budget(spec) -> SceneBudget:
    spec = spec or {}
    axis = spec.get("axis", "oracle")
    if axis not in ("oracle", "margin"):
        raise ValueError(f"budget.axis must be 'oracle' or 'margin', got {axis!r}")
    return SceneBudget(max_depth=int(spec.get("max_depth", 16)),
                       max_leaves=spec.get("max_leaves"),
                       max_time_s=spec.get("max_time_s"), axis=axis)


# --------------------------------------------------------------------------- #
# Scene parsing
# --------------------------------------------------------------------------- #

def parse_scene(data: dict) -> tuple[_cert.Scene, SceneBudget]:
    """Validate and build the exact-rational :class:`~cnp.certificate.Scene` (and its
    :class:`SceneBudget`) from a parsed YAML mapping. Raises ``ValueError`` /
    ``KeyError`` on a malformed scene (the CLI turns that into a clean message)."""
    robot = _parse_robot(data["robot"])

    body = data["body"]
    body_link = int(body["link"])
    if not 0 <= body_link < robot.n_joints:
        raise ValueError(f"body.link {body_link} out of range for "
                         f"{robot.n_joints}-joint robot")
    hull = body.get("hull_vertices") or _link_hull(robot, body_link)

    obstacles = {nm: _parse_obstacle(nm, spec)
                 for nm, spec in data["obstacles"].items()}
    pairs = data.get("pairs") or list(obstacles)
    unknown = [p for p in pairs if p not in obstacles]
    if unknown:
        raise ValueError(f"pairs reference unknown obstacles: {unknown}")

    phi_spec = data.get("phi")
    if phi_spec is None:
        raise ValueError("scene has no 'phi' barrier; fit one with the φ-pipeline "
                         "(phifit) and bake the rational tensor into the scene")
    phi = {tuple(int(x) for x in k.split(",")): v
           for k, v in phi_spec["coeffs"].items()}
    phi_degree = int(phi_spec["degree_per_var"])

    box = data["box"]
    if len(box) != robot.n:
        raise ValueError(f"box has {len(box)} dims but robot has {robot.n} "
                         f"unlocked joints")
    for s_name in ("start_s", "goal_s"):
        if len(data[s_name]) != robot.n:
            raise ValueError(f"{s_name} has {len(data[s_name])} entries, "
                             f"expected {robot.n}")

    scene = _cert.Scene(
        robot=robot, body_link=body_link, hull_vertices=hull, obstacles=obstacles,
        phi=phi, phi_degree=phi_degree, delta=data["delta"], box=box,
        start_s=data["start_s"], goal_s=data["goal_s"], pairs=pairs,
        lam_degree=data.get("lam_degree", "affine"))
    return scene, _parse_budget(data.get("budget"))


def load(path: str) -> tuple[_cert.Scene, SceneBudget]:
    """Parse a YAML scene file into ``(Scene, SceneBudget)``."""
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"scene file {path!r} is not a YAML mapping")
    return parse_scene(data)


# --------------------------------------------------------------------------- #
# Scene -> engine.Problem (planar via certificate; spatial built here)
# --------------------------------------------------------------------------- #

def _spatial_joints(robot: _cert.Robot) -> list:
    js = []
    for i, j in enumerate(robot.joints):
        X = np.eye(4)
        X[:3, 3] = [float(_cert.Q(x)) for x in j["offset"]]
        js.append(RevoluteJoint(f"j{i}", X,
                                np.array([float(_cert.Q(x)) for x in j["axis"]])))
    return js


def _spatial_problem(scene: _cert.Scene, **kw) -> _engine.Problem:
    from . import witness
    fk = SympyRatFK(_spatial_joints(scene.robot),
                    locked={k: float(v) for k, v in scene.robot.locked.items()},
                    q_star=[float(v) for v in scene.robot.q_star])
    body = fk.body(scene.body_link)
    verts = body.vertex_numerators([[float(c) for c in v] for v in scene.hull_vertices])
    pairs = [_engine.Pair(nm, verts, body.D,
                          witness.Polytope(
                              np.array([[float(x) for x in row] for row in A]),
                              np.array([float(x) for x in b])))
             for nm in scene.pairs
             for (A, b) in [scene.obstacles[nm]]]
    return _engine.Problem(box=[(float(lo), float(hi)) for lo, hi in scene.box],
                           phi=_cert._phi_tensor(scene), delta=float(scene.delta),
                           pairs=pairs, lam_degree=scene.lam_degree, **kw)


def build_problem(scene: _cert.Scene, **kw) -> _engine.Problem:
    """Build the float :class:`cnp.engine.Problem` for a scene of any supported kind."""
    if scene.robot.kind == "planar_revolute":
        return _cert.scene_to_problem(scene, **kw)
    if scene.robot.kind == "spatial_revolute":
        return _spatial_problem(scene, **kw)
    raise NotImplementedError(f"robot kind {scene.robot.kind!r} not supported")


# --------------------------------------------------------------------------- #
# Collision oracle (planar builtin) — for the φ-pipeline and ground-truth checks
# --------------------------------------------------------------------------- #

def _planar_body_fk(scene: _cert.Scene):
    """Float FK of the scene's moving body via the S1 generator (:class:`SympyRatFK`)."""
    if scene.robot.kind != "planar_revolute":
        raise NotImplementedError(f"collision oracle for {scene.robot.kind!r} is S9+")
    joints = _cert._planar_joints(scene.robot)
    fk = SympyRatFK(joints,
                    locked={k: float(v) for k, v in scene.robot.locked.items()},
                    q_star=[float(v) for v in scene.robot.q_star])
    return fk.body(f"link{scene.body_link}")


def is_exactly_verifiable(scene: _cert.Scene) -> bool:
    """Whether the independent exact verifier (:mod:`cnp.verify`, planar until S9) can
    re-check this scene: the planar builtin at ``q* = 0`` (SPEC §2 — a q*≠0 needs the
    irrational Rot(q*); spatial robots arrive with kind ``spatial_revolute`` in S9)."""
    return (scene.robot.kind == "planar_revolute"
            and all(v == 0 for v in scene.robot.q_star))


def scene_matches_cert(scene: _cert.Scene, cert: dict) -> tuple[bool, str]:
    """Cross-check that a self-contained certificate states the SAME problem as an
    externally-authored scene file (SPEC §5 / §6: ``cnp verify cert scene.yaml``).

    This ties the cert's embedded geometry to the human-authored scene; the EXACT proof
    (λ, μ, partition) is still re-checked by the untrusted :mod:`cnp.verify`. Pure
    string comparison of exact rationals, so it never accepts a silently-mutated cert."""
    def fail(msg):
        return False, f"scene/cert mismatch: {msg}"

    r = scene.robot
    cr = cert.get("robot", {})
    if cr.get("kind") != r.kind:
        return fail(f"robot kind {cr.get('kind')!r} != scene {r.kind!r}")
    if cr.get("link_lengths") != [str(v) for v in r.link_lengths]:
        return fail("link_lengths differ")
    if cr.get("q_star") != [str(v) for v in r.q_star]:
        return fail("q_star differs")
    if cr.get("locked_joints", {}) != {str(k): str(v) for k, v in r.locked.items()}:
        return fail("locked joints differ")
    cb = cert.get("body", {})
    if int(cb.get("link", -1)) != scene.body_link:
        return fail("body link differs")
    if cb.get("hull_vertices") != [[str(c) for c in v] for v in scene.hull_vertices]:
        return fail("body hull vertices differ")
    co = cert.get("obstacles", {})
    so = {nm: {"A": [[str(x) for x in row] for row in A], "b": [str(x) for x in b]}
          for nm, (A, b) in scene.obstacles.items()}
    if co != so:
        return fail("obstacles differ")
    if cert.get("delta") != str(scene.delta):
        return fail("delta differs")
    if cert.get("box") != [[str(lo), str(hi)] for lo, hi in scene.box]:
        return fail("box differs")
    if cert.get("start_s") != [str(v) for v in scene.start_s]:
        return fail("start_s differs")
    if cert.get("goal_s") != [str(v) for v in scene.goal_s]:
        return fail("goal_s differs")
    if list(cert.get("pairs", [])) != list(scene.pairs):
        return fail("relayed pairs differ")
    cp = cert.get("phi", {})
    sp = {",".join(str(int(x)) for x in e): str(c)
          for e, c in scene.phi.items() if c != 0}
    if cp.get("coeffs") != sp or int(cp.get("degree_per_var", -1)) != scene.phi_degree:
        return fail("barrier phi differs")
    return True, "scene matches certificate"


def planar_collision_oracle(scene: _cert.Scene, n_samples: int = 40):
    """A generic collision oracle ``f(s) -> bool`` for the planar builtin: sample the
    moving body link in world space and test it against every scene obstacle (H-rep).

    This is the robot-agnostic oracle the φ-pipeline (S5) consumes and the ground-truth
    / adversarial checks use; it is INDEPENDENT of the certificate (it samples the link,
    it does not read λ/μ). ``True`` iff some sampled body point lies inside some
    obstacle (all faces ``A y <= b`` satisfied)."""
    body = _planar_body_fk(scene)
    hull = np.array([[float(c) for c in v] for v in scene.hull_vertices])
    obstacles = [(np.array([[float(x) for x in row] for row in A]),
                  np.array([float(x) for x in b]))
                 for (A, b) in scene.obstacles.values()]
    ts = np.linspace(0.0, 1.0, n_samples)[:, None]

    def f(s) -> bool:
        s = np.asarray(s, dtype=float)
        pts = [body.eval_world_point(v, s) for v in hull]
        # convex hull of the link sampled as the segment hull[0]..hull[-1] (planar
        # link = 2-vertex segment); for >2 vertices sample the edges from vertex 0.
        seg = pts[0] * (1 - ts) + pts[-1] * ts
        for A, b in obstacles:
            if np.any(np.all(seg @ A.T <= b + 1e-12, axis=1)):
                return True
        return False

    return f
