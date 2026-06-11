"""ratfk — rational forward kinematics as numerator tensors over a common denominator.

Session S1 (CLAUDE.md). For a serial revolute robot (limits strictly inside
(-pi, pi)), this exposes, per body, the world pose as RATIONAL functions of
``s_i = tan((q_i - q*_i) / 2)``:

    X_world(point) = N(s) / D(s),    D(s) = prod_{i in chain, unlocked} (1 + s_i^2) > 0

with N a tensor polynomial of degree <= 2 per variable (the bound that makes the
Bernstein-LP witness possible, SPEC §2). The denominator D is COMMON to every
entry of a body's pose (the 9 rotation + 3 translation numerators share it), so a
point's world position is a plain linear combination of numerator tensors over D.

Two interchangeable back-ends, same ``BodyRatFK`` interface:
  * :class:`DrakeRatFK` — wraps Drake ``RationalForwardKinematics`` (primary).
  * :class:`SympyRatFK` — symbolic FK of a generic revolute chain (REPLI, used if
    the Drake wheel is unavailable on macOS arm64, SPEC §9.4).

Soundness note: we do NOT reuse Drake's per-entry rational denominator (Drake
returns several distinct, reduced denominators across the pose). Instead we clear
the half-angle denominator OURSELVES, joint by joint, onto the canonical common
denominator ``D = prod (1 + s_i^2)``. This is the same substitution verify.py will
recompute independently in S4 (cos = (1-s^2)/(1+s^2), sin = 2s/(1+s^2)), so the
generator's FK is auditable rather than trusted.

The only shared kernel with the rest of cnp is :mod:`cnp.polylin` (tensor algebra).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from . import polylin

# Degree per variable per joint. Each revolute joint enters every pose numerator
# with degree at most 2 in its own s_i (Bernstein-LP requirement, SPEC §2).
D_MAX = 2

_VAR_RE = re.compile(r"(cos|sin)_delta\[(\d+)\]")


# --------------------------------------------------------------------------- #
# Per-joint rational substitution, as degree-2 numerator tensors (reuse polylin)
# --------------------------------------------------------------------------- #

def _factor(n: int, joint: int, kind: str) -> np.ndarray:
    """Numerator tensor of one joint's contribution after clearing its (1+s^2).

    A multilinear monomial touches joint ``joint`` in exactly one of three ways;
    after multiplying through by (1 + s_joint^2) the contribution becomes:
        cos_delta -> (1 - s^2)      sin_delta -> 2 s      absent -> (1 + s^2)
    Each is a polynomial of degree <= 2 in s_joint alone.
    """
    e0 = [0] * n
    if kind == "cos":
        t = polylin.mono(n, D_MAX, e0, 1.0)
        e = e0.copy(); e[joint] = 2
        t = t + polylin.mono(n, D_MAX, e, -1.0)
    elif kind == "sin":
        e = e0.copy(); e[joint] = 1
        t = polylin.mono(n, D_MAX, e, 2.0)
    elif kind == "one":
        t = polylin.mono(n, D_MAX, e0, 1.0)
        e = e0.copy(); e[joint] = 2
        t = t + polylin.mono(n, D_MAX, e, 1.0)
    else:  # pragma: no cover - guarded by callers
        raise ValueError(f"unknown factor kind: {kind!r}")
    return t


def _denominator(n: int, s_chain) -> np.ndarray:
    """Common denominator tensor D(s) = prod_{i in s_chain} (1 + s_i^2)."""
    D = polylin.mono(n, D_MAX, [0] * n, 1.0)
    for j in s_chain:
        D = polylin.tmul(D, _factor(n, j, "one"), D_MAX)
    return D


# --------------------------------------------------------------------------- #
# Body-level rational FK (back-end agnostic container)
# --------------------------------------------------------------------------- #

@dataclass
class BodyRatFK:
    """Rational pose of one body, as numerator tensors over a common denominator.

    All tensors have shape ``(D_MAX + 1,) * n`` (n = number of s-variables of the
    robot, i.e. unlocked joints). ``D`` is the shared positive denominator.
    ``pos_num[i]`` and ``rot_num[i][j]`` are the numerators of the body-frame
    origin position and rotation matrix entries, all over ``D``.
    """

    name: str
    n: int
    s_chain: tuple          # s-indices this body's pose depends on (sorted)
    D: np.ndarray           # common denominator numerator-tensor, > 0 on the box
    pos_num: list           # [Nx, Ny, Nz] numerator tensors of the body origin
    rot_num: list           # 3x3 numerator tensors of the rotation matrix

    @property
    def d(self) -> int:
        return D_MAX

    def point_numerator(self, p_B) -> list:
        """Numerator tensors (Nx, Ny, Nz) of a body-frame point's world position.

        World position = (pos + R @ p_B) / D. Since p_B is constant this is a
        linear combination of the stored numerator tensors over the common D.
        """
        p = np.asarray(p_B, dtype=float)
        if p.shape != (3,):
            raise ValueError("p_B must be a 3-vector in the body frame")
        out = []
        for i in range(3):
            t = self.pos_num[i].copy()
            for j in range(3):
                if p[j] != 0.0:
                    t = t + self.rot_num[i][j] * p[j]
            out.append(t)
        return out

    def vertex_numerators(self, vertices) -> list:
        """Numerators for several body-frame points (e.g. convex-hull vertices)."""
        return [self.point_numerator(v) for v in np.asarray(vertices, dtype=float)]

    def eval_world_point(self, p_B, s) -> np.ndarray:
        """Evaluate a body-frame point's world position at an s-sample (for tests)."""
        num = self.point_numerator(p_B)
        Dv = polylin.teval(self.D, s)
        return np.array([polylin.teval(num[i], s) / Dv for i in range(3)])

    def max_degree_per_var(self) -> int:
        """Largest exponent of any single variable across all numerator tensors."""
        worst = 0
        tensors = list(self.pos_num) + [t for row in self.rot_num for t in row] + [self.D]
        for t in tensors:
            for e in np.argwhere(t != 0):
                worst = max(worst, int(e.max()) if e.size else 0)
        return worst


# --------------------------------------------------------------------------- #
# Drake back-end
# --------------------------------------------------------------------------- #

class DrakeRatFK:
    """Rational FK from a finalized Drake ``MultibodyPlant`` (serial revolute).

    Parameters
    ----------
    plant : pydrake MultibodyPlant (finalized, all single-dof revolute joints,
        base welded so position index == joint/delta index).
    locked : optional mapping ``{position_index: locked_q_value_rad}``. Locked
        joints are folded into constant coefficients; they carry no s-variable and
        no (1+s^2) denominator factor.
    q_star : optional nominal posture (len num_positions); defaults to zeros, so
        ``s_i = tan(q_i / 2)``.
    """

    def __init__(self, plant, locked=None, q_star=None):
        from pydrake.multibody.rational import RationalForwardKinematics

        self.plant = plant
        self._ratfk = RationalForwardKinematics(plant)
        nq = plant.num_positions()
        self.nq = nq
        self.q_star = np.zeros(nq) if q_star is None else np.asarray(q_star, dtype=float)
        self.locked = {int(k): float(v) for k, v in (locked or {}).items()}
        self.unlocked = [i for i in range(nq) if i not in self.locked]
        self.n = len(self.unlocked)
        self._s_of_pos = {p: k for k, p in enumerate(self.unlocked)}
        self._world = plant.world_body().index()
        self._cache: dict[str, BodyRatFK] = {}

    def s_value(self, q) -> np.ndarray:
        """Map a full configuration q (rad) to the s-vector of unlocked joints."""
        q = np.asarray(q, dtype=float)
        return np.array([np.tan((q[p] - self.q_star[p]) / 2.0) for p in self.unlocked])

    def _numtensor(self, poly, chain_pos, const) -> np.ndarray:
        """Convert one multilinear pose entry to a numerator tensor over D."""
        out = polylin.zeros(self.n, D_MAX)
        for mono, coeff in poly.monomial_to_coefficient_map().items():
            c = coeff.Evaluate({})
            kinds: dict[int, str] = {}
            for var, power in mono.get_powers().items():
                m = _VAR_RE.match(var.get_name())
                kinds[int(m.group(2))] = m.group(1)
            term = polylin.mono(self.n, D_MAX, [0] * self.n, c)
            for p in chain_pos:
                kind = kinds.get(p, "one")
                if p in self.locked:
                    # Locked joint: substitute the numeric cos/sin; no s, no denom.
                    if kind == "cos":
                        term = term * const[p][0]
                    elif kind == "sin":
                        term = term * const[p][1]
                    # 'one' (absent) -> factor 1, nothing to do
                else:
                    sidx = self._s_of_pos[p]
                    term = polylin.tmul(term, _factor(self.n, sidx, kind), D_MAX)
            out = out + term
        return out

    def body(self, name_or_index) -> BodyRatFK:
        if isinstance(name_or_index, str):
            if name_or_index in self._cache:
                return self._cache[name_or_index]
            body = self.plant.GetBodyByName(name_or_index)
            key = name_or_index
        else:
            body = self.plant.get_body(name_or_index)
            key = body.name()
            if key in self._cache:
                return self._cache[key]

        pose = self._ratfk.CalcBodyPoseAsMultilinearPolynomial(
            self.q_star, body.index(), self._world)
        pos = pose.position()
        rot = pose.rotation()
        entries = list(pos) + [rot[i, j] for i in range(3) for j in range(3)]

        # Chain = union of joints appearing in ANY pose entry (full kinematic chain
        # to this body), so the common denominator covers rotation*point too.
        chain_pos = set()
        for poly in entries:
            for var in poly.indeterminates():
                m = _VAR_RE.match(var.get_name())
                chain_pos.add(int(m.group(2)))
        chain_pos = sorted(chain_pos)

        # Numeric cos/sin for locked chain joints, at their fixed delta = q - q*.
        const = {}
        for p in chain_pos:
            if p in self.locked:
                delta = self.locked[p] - self.q_star[p]
                const[p] = (np.cos(delta), np.sin(delta))

        s_chain = tuple(self._s_of_pos[p] for p in chain_pos if p not in self.locked)
        D = _denominator(self.n, s_chain)
        pos_num = [self._numtensor(pos[i], chain_pos, const) for i in range(3)]
        rot_num = [[self._numtensor(rot[i, j], chain_pos, const) for j in range(3)]
                   for i in range(3)]

        bfk = BodyRatFK(name=key, n=self.n, s_chain=s_chain, D=D,
                        pos_num=pos_num, rot_num=rot_num)
        self._cache[key] = bfk
        return bfk


# --------------------------------------------------------------------------- #
# Sympy back-end (REPLI) — generic revolute serial chain
# --------------------------------------------------------------------------- #

@dataclass
class RevoluteJoint:
    """One revolute joint of a generic chain (used by the sympy fallback).

    ``X_pj`` is the 4x4 fixed transform from the previous link frame to this
    joint's frame (applied BEFORE the rotation). ``axis`` is the rotation axis in
    that joint frame (unit vector). ``name`` is the child link's name.
    """

    name: str
    X_pj: np.ndarray   # 4x4
    axis: np.ndarray   # 3-vector


class SympyRatFK:
    """Symbolic rational FK of a serial revolute chain (Drake-free REPLI).

    Same public interface as :class:`DrakeRatFK`: ``.n``, ``.s_value(q)`` and
    ``.body(name)`` returning a :class:`BodyRatFK`. Builds each link pose as a
    Rodrigues rotation with the half-angle substitution and extracts numerator
    tensors over the canonical common denominator with sympy.
    """

    def __init__(self, joints, locked=None, q_star=None):
        import sympy as sp

        self._sp = sp
        self.joints = list(joints)
        nq = len(self.joints)
        self.nq = nq
        self.q_star = np.zeros(nq) if q_star is None else np.asarray(q_star, dtype=float)
        self.locked = {int(k): float(v) for k, v in (locked or {}).items()}
        self.unlocked = [i for i in range(nq) if i not in self.locked]
        # A12 (CLAUDE.md): this back-end folds delta_i = q_i - q*_i into
        # s_i = tan(delta_i/2) but does NOT apply the constant pre-rotation
        # Rot(axis, q*_i) for unlocked joints, so a nonzero q* there would be
        # SILENTLY ignored. Refuse it loudly rather than return a wrong FK; only
        # q*=0 is sound on the sympy path (use the Drake back-end for q*!=0).
        bad = {p: self.q_star[p] for p in self.unlocked if self.q_star[p] != 0.0}
        if bad:
            raise ValueError(
                "SympyRatFK ignores q_star on unlocked joints (no Rot(axis,q*) "
                f"pre-rotation): joints {bad} have a nonzero q*. Only q*=0 is "
                "supported on the sympy path (CLAUDE.md A12); use DrakeRatFK for "
                "q*!=0.")
        self.n = len(self.unlocked)
        self._s_of_pos = {p: k for k, p in enumerate(self.unlocked)}
        self._s = sp.symbols(f"s0:{self.n}") if self.n else ()
        self._cache: dict[str, BodyRatFK] = {}
        self._build()

    def s_value(self, q) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        return np.array([np.tan((q[p] - self.q_star[p]) / 2.0) for p in self.unlocked])

    @staticmethod
    def _skew(a):
        import sympy as sp
        return sp.Matrix([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])

    def _joint_transform(self, i):
        """4x4 homogeneous transform of joint i as (numerator matrix, scalar denom)."""
        sp = self._sp
        jt = self.joints[i]
        Xpj = sp.Matrix(jt.X_pj)
        a = np.asarray(jt.axis, dtype=float)
        a = a / np.linalg.norm(a)
        K = self._skew(a)
        if i in self.locked:
            delta = float(self.locked[i] - self.q_star[i])
            c, s = float(np.cos(delta)), float(np.sin(delta))
            R = sp.eye(3) + s * K + (1 - c) * (K * K)
            den = sp.Integer(1)
        else:
            si = self._s[self._s_of_pos[i]]
            # Rodrigues with cos=(1-s^2)/(1+s^2), sin=2s/(1+s^2), cleared of (1+s^2):
            R = (1 + si**2) * sp.eye(3) + (2 * si) * K + (2 * si**2) * (K * K)
            den = 1 + si**2
        # Homogeneous numerator over the common scalar denom `den`: EVERY entry,
        # including the (3,3) corner, must share that denominator, hence den*I with
        # the rotation block overwritten (otherwise the translation column gets
        # silently divided by den).
        Trot = den * sp.eye(4)
        Trot[:3, :3] = R
        # Offset first, then rotate: X_parent_child = X_pj @ Rot(axis, theta).
        Tden = Xpj * Trot  # Xpj has denom 1; numerator matrix, common scalar `den`
        return Tden, den

    def _build(self):
        sp = self._sp
        T = sp.eye(4)          # accumulated numerator transform
        for i, jt in enumerate(self.joints):
            Ti, _di = self._joint_transform(i)
            T = T * Ti
            # The accumulated numerator T is already over the common denominator
            # D = prod_{unlocked j <= i}(1 + s_j^2): each joint contributed its
            # numerator and one (1+s_j^2) factor, and s_j appears in no later
            # constant factor, so deg <= 2 per var holds and the ratio is exactly 1.
            s_chain = tuple(self._s_of_pos[p] for p in range(i + 1) if p not in self.locked)
            D = _denominator(self.n, s_chain)
            pos_num = [self._poly_to_tensor(sp.expand(T[r, 3])) for r in range(3)]
            rot_num = [[self._poly_to_tensor(sp.expand(T[r, col])) for col in range(3)]
                       for r in range(3)]
            self._cache[jt.name] = BodyRatFK(
                name=jt.name, n=self.n, s_chain=s_chain, D=D,
                pos_num=pos_num, rot_num=rot_num)

    def _poly_to_tensor(self, expr):
        """sympy expression in s-vars -> dense coefficient tensor (deg <= 2 / var)."""
        sp = self._sp
        out = polylin.zeros(self.n, D_MAX)
        if self.n == 0:
            out[()] = float(expr)
            return out
        poly = sp.Poly(expr, *self._s)
        for monom, coeff in poly.terms():
            if any(e > D_MAX for e in monom):
                raise ValueError(f"degree overflow in sympy FK: {monom}")
            out[tuple(monom)] += float(coeff)
        return out

    def body(self, name_or_index) -> BodyRatFK:
        if isinstance(name_or_index, str):
            return self._cache[name_or_index]
        return self._cache[self.joints[name_or_index].name]
