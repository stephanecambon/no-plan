"""verify — INDEPENDENT exact-arithmetic certificate verifier (SPEC §5, session S4).

SACRED MODULE (CLAUDE.md rule 4). This file:
  * is the credibility keystone: a disconnection result is "certified" only if
    ``cnp verify`` returns OK in EXACT arithmetic (CLAUDE.md rule 5);
  * uses ``fractions.Fraction`` ONLY — no numpy, no floats in the proof path;
  * imports NOTHING from the generator (cnp.polylin / ratfk / witness / engine /
    certificate). The Bernstein transform and the half-angle forward-kinematics
    substitution are RE-IMPLEMENTED here from scratch, so the verifier shares no
    code with the thing it checks (SPEC §5: "duplication assumed, that is the goal").

What it checks, all in exact rationals (SPEC §2 theorem):
  (0) assumptions / well-formedness (delta>0, box lo<hi, obstacle dim);
  (i) phi(s_start) < -delta  and  phi(s_goal) > +delta;
  (ii) the leaf cells tile the box P exactly (disjoint cover by midpoint bisection);
  (iii) every "outside" leaf is disjoint from the slab (Bernstein(±phi - delta) >= 0);
  (iv) every "collision" leaf certifies one (body, obstacle) pair: sum_k lambda_k == 1
        (exact identity), Bernstein(lambda_k) >= 0, mu_j >= 0, and Bernstein(g_j -
        mu_j*(delta^2 - phi^2)) >= 0 for each face j, with g_j = b_j*D - a_j . X and
        X = sum_k lambda_k * N_k the witness numerator over the common denom D (recomputed HERE).

SIGN (CLAUDE.md rule 2 / SPEC §2): the verifier itself forms ``g - mu*T`` (subtract) from
the stored mu — it owns the sign, so a cert cannot smuggle in the unsound ``g + mu*T``.
"""
from __future__ import annotations

import json
from fractions import Fraction
from math import comb


class CertificateRejected(Exception):
    """Raised with a human-readable reason when a certificate fails any check."""


def _reject(msg: str):
    raise CertificateRejected(msg)


# --------------------------------------------------------------------------- #
# Exact sparse tensor algebra (dict {exponent-tuple: Fraction})
# --------------------------------------------------------------------------- #

def _t_add(a: dict, b: dict) -> dict:
    out = dict(a)
    for e, c in b.items():
        out[e] = out.get(e, Fraction(0)) + c
    return {e: c for e, c in out.items() if c != 0}


def _t_scale(a: dict, c) -> dict:
    c = Fraction(c)
    if c == 0:
        return {}
    return {e: c * v for e, v in a.items()}


def _t_mul(a: dict, b: dict) -> dict:
    """Polynomial product (full convolution)."""
    out: dict = {}
    for ea, ca in a.items():
        for eb, cb in b.items():
            e = tuple(x + y for x, y in zip(ea, eb))
            out[e] = out.get(e, Fraction(0)) + ca * cb
    return {e: c for e, c in out.items() if c != 0}


def _t_eval(a: dict, point) -> Fraction:
    acc = Fraction(0)
    for e, c in a.items():
        term = c
        for i, p in enumerate(e):
            if p:
                term *= point[i] ** p
        acc += term
    return acc


def _mono(n: int, expo, coeff=1) -> dict:
    e = tuple(int(x) for x in expo)
    c = Fraction(coeff)
    return {e: c} if c != 0 else {}


# --------------------------------------------------------------------------- #
# Exact Bernstein transform over a box (re-implemented; no cnp.polylin)
# --------------------------------------------------------------------------- #

def _shift_matrix(d: int, lo: Fraction, hi: Fraction) -> list:
    """1-D map of monomial coeffs under s = lo + (hi-lo) x  (x in [0,1])."""
    w = hi - lo
    S = [[Fraction(0)] * (d + 1) for _ in range(d + 1)]
    for p in range(d + 1):
        for q in range(p + 1):
            S[q][p] = comb(p, q) * (lo ** (p - q)) * (w ** q)
    return S


def _bern_matrix(d: int) -> list:
    """1-D monomial-on-[0,1] -> Bernstein-coefficient map: B[i][j]=C(i,j)/C(d,j)."""
    B = [[Fraction(0)] * (d + 1) for _ in range(d + 1)]
    for i in range(d + 1):
        for j in range(i + 1):
            B[i][j] = Fraction(comb(i, j), comb(d, j))
    return B


def _matmul(A: list, B: list) -> list:
    k = len(B)
    return [[sum((A[i][t] * B[t][j] for t in range(k)), Fraction(0))
             for j in range(len(B[0]))] for i in range(len(A))]


def _apply_axis(coeffs: dict, axis: int, M: list) -> dict:
    out: dict = {}
    for idx, c in coeffs.items():
        p = idx[axis]
        for q in range(len(M)):
            m = M[q][p]
            if m:
                nidx = idx[:axis] + (q,) + idx[axis + 1:]
                out[nidx] = out.get(nidx, Fraction(0)) + m * c
    return {e: c for e, c in out.items() if c != 0}


def _bernstein_control_points(coeffs: dict, n: int, d: int, box: list) -> dict:
    """Bernstein coefficients of the polynomial over ``box`` at per-var degree ``d``.
    Any control point not present is exactly 0. min(control points) <= poly min, so
    'all control points >= 0' is a SOUND certificate that the poly is >= 0 on box."""
    if any(any(e > d for e in idx) for idx in coeffs):
        _reject("polynomial degree exceeds the declared Bernstein degree")
    cur = dict(coeffs)
    for ax in range(n):
        lo, hi = box[ax]
        cur = _apply_axis(cur, ax, _matmul(_bern_matrix(d), _shift_matrix(d, lo, hi)))
    return cur


def _bern_all_nonneg(coeffs: dict, n: int, d: int, box: list) -> bool:
    cp = _bernstein_control_points(coeffs, n, d, box)
    return all(v >= 0 for v in cp.values())  # absent control points are 0 >= 0


# --------------------------------------------------------------------------- #
# Independent half-angle forward kinematics (re-implemented; no cnp.ratfk)
# --------------------------------------------------------------------------- #
# s_i = tan((q_i-q*_i)/2); clearing each joint's (1+s_i^2), the rotation numerator
# about a unit axis is R_i = (1+s_i^2) I + 2 s_i K + 2 s_i^2 K^2 over (1+s_i^2) (K =
# skew(axis)). We accumulate homogeneous 4x4 NUMERATOR matrices over the common
# denominator D = prod_{unlocked i in chain}(1+s_i^2). Same maths as cnp.ratfk,
# re-coded from scratch in exact Fraction tensors.

def _const_t(n: int, v) -> dict:
    v = Fraction(v)
    return {tuple([0] * n): v} if v != 0 else {}


def _matmul_t(A: list, B: list) -> list:
    m, p, q = len(A), len(B), len(B[0])
    out = [[{} for _ in range(q)] for _ in range(m)]
    for i in range(m):
        for j in range(q):
            acc: dict = {}
            for k in range(p):
                if A[i][k] and B[k][j]:
                    acc = _t_add(acc, _t_mul(A[i][k], B[k][j]))
            out[i][j] = acc
    return out


def _skew(a):
    return [[Fraction(0), -a[2], a[1]],
            [a[2], Fraction(0), -a[0]],
            [-a[1], a[0], Fraction(0)]]


def _rot_homog(n: int, s_index, axis, locked_cos_sin=None) -> list:
    """4x4 homogeneous numerator of a revolute joint over its own denominator.

    Unlocked joint: numerator over (1+s^2), s the joint's s-variable (index s_index).
    Locked joint: numeric rotation by a fixed angle (cos, sin given as rationals),
    denominator 1."""
    K = _skew(axis)
    K2 = [[sum(K[i][t] * K[t][j] for t in range(3)) for j in range(3)] for i in range(3)]
    T = [[{} for _ in range(4)] for _ in range(4)]
    if locked_cos_sin is None:
        den = _t_add(_const_t(n, 1), _mono(n, _unit(n, s_index, 2), 1))  # 1 + s^2
        s1 = _mono(n, _unit(n, s_index, 1), 2)               # 2 s
        s2 = _mono(n, _unit(n, s_index, 2), 2)               # 2 s^2
        for i in range(3):
            for j in range(3):
                term = _t_scale(den, 1) if i == j else {}
                term = _t_add(term, _t_scale(s1, K[i][j]))
                term = _t_add(term, _t_scale(s2, K2[i][j]))
                T[i][j] = term
        T[3][3] = den
    else:
        c, s = locked_cos_sin
        for i in range(3):
            for j in range(3):
                val = (Fraction(1) if i == j else Fraction(0)) + s * K[i][j] \
                      + (1 - c) * K2[i][j]
                T[i][j] = _const_t(n, val)
        T[3][3] = _const_t(n, 1)
    return T


def _unit(n: int, idx: int, p: int) -> tuple:
    e = [0] * n
    e[idx] = p
    return tuple(e)


def _trans_homog(n: int, x, y, z) -> list:
    T = [[_const_t(n, 1 if i == j else 0) for j in range(4)] for i in range(4)]
    T[0][3] = _const_t(n, x)
    T[1][3] = _const_t(n, y)
    T[2][3] = _const_t(n, z)
    return T


def _chain_joints(robot: dict) -> list:
    """Normalized chain ``[(offset (x,y,z), axis (x,y,z)), ...]`` re-derived from the
    certificate in exact Fractions (no generator code shared). planar_revolute (S4):
    axis +z, joint i offset ``(len_{i-1},0,0)`` along x. spatial_revolute (S9, G3'b):
    each joint its own rational offset and a UNIT axis (squares sum to 1 exactly)."""
    kind = robot["kind"]
    if kind == "planar_revolute":
        out, prev = [], Fraction(0)
        for ln in (Fraction(v) for v in robot["link_lengths"]):
            out.append(((prev, Fraction(0), Fraction(0)),
                        (Fraction(0), Fraction(0), Fraction(1))))
            prev = ln
        return out
    if kind == "spatial_revolute":
        out = []
        for jt in robot["joints"]:
            axis = tuple(Fraction(v) for v in jt["axis"])
            if sum(a * a for a in axis) != 1:
                _reject("verify: spatial joint axis is not a unit vector (exact)")
            out.append((tuple(Fraction(v) for v in jt["offset"]), axis))
        return out
    _reject(f"verify: unsupported robot kind {kind!r}")


def _body_fk(robot: dict, body_link: int):
    """Recompute (vertex-free) the body link's world pose NUMERATOR matrix and the
    common denominator D, independently, in exact Fraction tensors. Returns (T, D, n).

    q* absorbed into s (SPEC §2); a nonzero q* needs an irrational Rot(angle), refused
    (rule 5). LOCKED joints (S9c) carry EXACT rational cos/sin (``cos^2+sin^2==1``
    checked here), a numeric rotation and denominator 1; they take NO s-variable, so
    the unlocked joints are re-indexed 0..n-1 and only they add a ``(1+s^2)`` to D."""
    if any(Fraction(v) != 0 for v in robot["q_star"]):
        _reject("verify: nonzero q_star unsupported by the exact FK")
    joints = _chain_joints(robot)
    locked = {int(k): v for k, v in (robot.get("locked_joints") or {}).items()}
    n = len(joints) - len(locked)
    if n != int(robot["n"]):
        _reject("verify: robot n disagrees with the unlocked joint count")
    s_of = {j: k for k, j in enumerate(j for j in range(len(joints)) if j not in locked)}

    T = [[_const_t(n, 1 if i == j else 0) for j in range(4)] for i in range(4)]
    D = _const_t(n, 1)                           # D = prod over UNLOCKED chain (1 + s^2)
    for j in range(body_link + 1):
        (ox, oy, oz), axis = joints[j]
        if j in locked:
            c, s = Fraction(locked[j]["cos"]), Fraction(locked[j]["sin"])
            if c * c + s * s != 1:
                _reject("verify: locked joint cos^2+sin^2 != 1 (not an exact rotation)")
            rot = _rot_homog(n, None, axis, locked_cos_sin=(c, s))
        else:
            rot = _rot_homog(n, s_of[j], axis)
            D = _t_mul(D, _t_add(_const_t(n, 1), _mono(n, _unit(n, s_of[j], 2), 1)))
        T = _matmul_t(_matmul_t(T, _trans_homog(n, ox, oy, oz)), rot)
    return T, D, n


def _vertex_numerators(T: list, D: list, hull_vertices, n: int) -> list:
    """World-position numerators of the body-frame hull vertices over D."""
    verts = []
    for v in hull_vertices:
        x, y, z = (Fraction(c) for c in v)
        coords = []
        for i in range(3):
            num = _t_add(_t_add(_t_scale(T[i][0], x), _t_scale(T[i][1], y)),
                         _t_scale(T[i][2], z))
            num = _t_add(num, T[i][3])
            coords.append(num)
        verts.append(coords)
    return verts


# --------------------------------------------------------------------------- #
# Certificate parsing helpers
# --------------------------------------------------------------------------- #

def _parse_tensor(coeffs: dict, n: int) -> dict:
    out = {}
    for key, val in coeffs.items():
        e = tuple(int(x) for x in key.split(",")) if key else tuple([0] * n)
        if len(e) != n:
            _reject("verify: phi/lambda exponent arity mismatch")
        out[e] = Fraction(val)
    return out


def _parse_cell(cell) -> list:
    return [(Fraction(lo), Fraction(hi)) for lo, hi in cell]


LAM_DEG = {"const": 0, "affine": 1, "quadratic": 2}
D_N = 2  # per-variable degree of a revolute pose numerator (half-angle, fixed)


# --------------------------------------------------------------------------- #
# The five checks
# --------------------------------------------------------------------------- #

def _check_assumptions(cert: dict):
    if cert.get("theorem") != "disconnection":
        _reject("verify: not a disconnection certificate")
    if cert["kinematics"]["substitution"] != "half_angle_homemade_v1":
        _reject("verify: unknown kinematic substitution")
    delta = Fraction(cert["delta"])
    if delta <= 0:
        _reject("verify: delta must be > 0")
    for lo, hi in (_parse_cell(cert["box"])):
        if not (lo < hi):
            _reject("verify: degenerate box bound")
    for nm, obs in cert["obstacles"].items():
        if any(len(row) != 3 for row in obs["A"]) or len(obs["A"]) != len(obs["b"]):
            _reject(f"verify: malformed obstacle {nm!r}")


def _check_condition_i(cert: dict, n: int):
    phi = _parse_tensor(cert["phi"]["coeffs"], n)
    delta = Fraction(cert["delta"])
    s0 = [Fraction(v) for v in cert["start_s"]]
    s1 = [Fraction(v) for v in cert["goal_s"]]
    if not (_t_eval(phi, s0) < -delta):
        _reject("verify: phi(s_start) is not < -delta (condition i)")
    if not (_t_eval(phi, s1) > delta):
        _reject("verify: phi(s_goal) is not > +delta (condition i)")


def _check_partition(cert: dict):
    box = _parse_cell(cert["box"])
    cells = [_parse_cell(lf["cell"]) for lf in cert["leaves"]]
    if not cells:
        _reject("verify: empty partition")
    _verify_cover(box, cells)


def _verify_cover(box: list, cells: list):
    """Prove ``cells`` is a disjoint exact cover of ``box`` by recursively finding the
    midpoint bisection that cleanly separates them (the engine only ever bisects at a
    cell's midpoint, so this reconstructs the partition tree)."""
    if len(cells) == 1:
        if cells[0] == box:
            return
        _reject("verify: leaf cell does not match its region (gap/overlap)")
    n = len(box)
    for ax in range(n):
        lo, hi = box[ax]
        mid = (lo + hi) / 2
        lower, upper, clean = [], [], True
        for c in cells:
            clo, chi = c[ax]
            if chi <= mid:
                lower.append(c)
            elif clo >= mid:
                upper.append(c)
            else:
                clean = False
                break
        if clean and lower and upper:
            lbox = list(box); lbox[ax] = (lo, mid)
            ubox = list(box); ubox[ax] = (mid, hi)
            _verify_cover(lbox, lower)
            _verify_cover(ubox, upper)
            return
    _reject("verify: cells do not tile the box (not a midpoint-bisection partition)")


def _check_outside_leaf(lf: dict, phi: dict, delta: Fraction, n: int, dphi: int):
    cell = _parse_cell(lf["cell"])
    phi_minus = _t_add(phi, _const_t(n, -delta))       # phi - delta >= 0  (phi >= delta)
    neg_phi_minus = _t_add(_t_scale(phi, -1), _const_t(n, -delta))  # -phi - delta >= 0
    if _bern_all_nonneg(phi_minus, n, dphi, cell) or \
       _bern_all_nonneg(neg_phi_minus, n, dphi, cell):
        return
    _reject(f"verify: 'outside' leaf {lf['cell']} is NOT disjoint from the slab")


def _check_collision_leaf(lf: dict, cert: dict, verts: list, D: dict, n: int,
                          phi: dict, delta: Fraction, dphi: int):
    cell = _parse_cell(lf["cell"])
    lam_degree = cert["lam_degree"]
    d_lam = LAM_DEG[lam_degree]
    K = len(verts)
    lam = [_parse_tensor(t, n) for t in lf["lambda"]]
    if len(lam) != K:
        _reject("verify: lambda count != number of hull vertices")

    # sum_k lambda_k == 1  (exact polynomial identity)
    total: dict = {}
    for lk in lam:
        total = _t_add(total, lk)
    if total != _const_t(n, 1):
        _reject(f"verify: sum_k lambda_k != 1 on leaf {lf['cell']}")

    # lambda_k >= 0 on the cell (Bernstein)
    for k, lk in enumerate(lam):
        if not _bern_all_nonneg(lk, n, d_lam, cell):
            _reject(f"verify: lambda_{k} is not >= 0 on leaf {lf['cell']}")

    # witness numerator X_i = sum_k lambda_k * N_k[i]
    X = []
    for i in range(3):
        Xi: dict = {}
        for k in range(K):
            Xi = _t_add(Xi, _t_mul(lam[k], verts[k][i]))
        X.append(Xi)

    obs = cert["obstacles"][lf["obstacle"]]
    A = [[Fraction(x) for x in row] for row in obs["A"]]
    b = [Fraction(x) for x in obs["b"]]
    mu = [Fraction(m) for m in lf["mu"]]
    if len(mu) != len(A):
        _reject("verify: mu count != obstacle face count")

    # slab tensor T = delta^2 - phi^2
    T = _t_add(_const_t(n, delta * delta), _t_scale(_t_mul(phi, phi), -1))
    d_X = d_lam + D_N
    dpad = max(d_X, 2 * dphi)

    for j in range(len(A)):
        if mu[j] < 0:
            _reject(f"verify: mu_{j} < 0 on leaf {lf['cell']}")
        # g_j = b_j * D - a_j . X
        g = _t_scale(D, b[j])
        for i in range(3):
            if A[j][i]:
                g = _t_add(g, _t_scale(X[i], -A[j][i]))
        # SIGN g - mu*T (subtract) — the verifier forms it; certs cannot flip it.
        H = _t_add(g, _t_scale(T, -mu[j]))
        if not _bern_all_nonneg(H, n, dpad, cell):
            _reject(f"verify: face {j} of {lf['obstacle']!r} not certified on leaf "
                    f"{lf['cell']} (Bernstein(g - mu*T) has a negative coefficient)")


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #

def verify(cert: dict) -> tuple:
    """Verify a certificate in exact arithmetic.

    Returns ``(ok, message)``. ``ok`` is True only if every check passes (the result
    is genuinely PROOF, CLAUDE.md rule 5). Never raises on a bad certificate — it
    returns ``(False, reason)`` so callers can report UNDECIDED honestly."""
    try:
        _check_assumptions(cert)
        n = int(cert["robot"]["n"])
        dphi = int(cert["phi"]["degree_per_var"])
        phi = _parse_tensor(cert["phi"]["coeffs"], n)
        delta = Fraction(cert["delta"])

        _check_condition_i(cert, n)
        _check_partition(cert)

        T, D, fk_n = _body_fk(cert["robot"], int(cert["body"]["link"]))
        if fk_n != n:
            _reject("verify: FK arity disagrees with the certificate")
        verts = _vertex_numerators(T, D, cert["body"]["hull_vertices"], n)

        n_out = n_col = 0
        for lf in cert["leaves"]:
            if lf["status"] == "outside":
                _check_outside_leaf(lf, phi, delta, n, dphi)
                n_out += 1
            elif lf["status"] == "collision":
                _check_collision_leaf(lf, cert, verts, D, n, phi, delta, dphi)
                n_col += 1
            else:
                _reject(f"verify: undecided leaf status {lf['status']!r} (not a proof)")
    except CertificateRejected as exc:
        return False, str(exc)
    except (KeyError, ValueError, ZeroDivisionError, TypeError) as exc:
        return False, f"verify: malformed certificate ({exc!r})"
    return True, (f"PROOF verified exactly: {len(cert['leaves'])} leaves "
                  f"({n_col} collision, {n_out} outside); start/goal separated by the "
                  f"slab |phi| <= {delta}.")


def verify_file(path: str) -> tuple:
    with open(path) as f:
        return verify(json.load(f))
