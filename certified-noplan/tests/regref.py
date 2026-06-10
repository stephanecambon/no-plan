"""Regression reference: planar scenes + Bernstein-LP certifier, ported from the
sandbox campaign E1-E4 (sandbox_reference/exp12_ladder.py, exp34_multipair.py).

This is the S0 regression oracle. It deliberately lives under tests/ (NOT in
src/cnp): per SPEC §3 the production witness/engine are written in S2/S3. The only
shared kernel with the generator is cnp.polylin. The numerics here must stay bit-
faithful to the sandbox so the t* / leaf-count references reproduce (gate G0').

SIGN (CLAUDE.md rule 2 / SPEC §2): the slab-aware constraint is Bernstein(g - mu*T)
>= t with mu >= 0. ``certify_cell_pair`` exposes ``putinar_sign`` only so the sign
can be *frozen* by tests/test_putinar_sign.py; production code uses the default
(-1, i.e. subtract). g + mu*T is UNSOUND.
"""
import time
from itertools import product as iproduct

import numpy as np
import cvxpy as cp

from cnp.polylin import PolyLin, zeros, mono, tmul, teval, bernstein_coeffs


# ======================================================================
# E1 + E2 — witness ladder x two back-ends (synthetic multilinear scene)
# ======================================================================

W = 0.35  # half widths of moving square A and fixed box B


def scene_tensors(n, a_tot=0.44, gamma=0.04):
    """Return (verts, cx): 4 vertex polys [vx, vy] of A(s) and the centre poly cx."""
    cx = zeros(n, 1)
    for i in range(n):
        e = [0] * n; e[i] = 1
        cx[tuple(e)] += a_tot / n
    for i in range(n - 1):
        e = [0] * n; e[i] = 1; e[i + 1] = 1
        cx[tuple(e)] += gamma / (n - 1)
    cy = zeros(n, 1)
    corners = [(+W, +W), (+W, -W), (-W, +W), (-W, -W)]
    verts = []
    one = mono(n, 1, [0] * n)
    for (dx, dy) in corners:
        verts.append([cx + dx * one, cy + dy * one])
    return verts, cx


def lam_basis(n, kind):
    if kind == 'const':
        return [tuple([0] * n)]
    if kind == 'affine':
        es = [tuple([0] * n)]
        for i in range(n):
            e = [0] * n; e[i] = 1; es.append(tuple(e))
        return es
    if kind == 'multilinear':
        return [e for e in iproduct(*[(0, 1)] * n)]
    raise ValueError(kind)


def build_constraint_polys(n, kind, verts):
    """Return (g_list deg<=2, lam_list deg<=1, nz)."""
    es = lam_basis(n, kind)
    K = 4
    nz = K * len(es)
    lams = []
    vid = 0
    for k in range(K):
        L = PolyLin(n, 1)
        for e in es:
            L.add(vid, mono(n, 1, list(e)))
            vid += 1
        lams.append(L)
    xx = PolyLin(n, 2); xy = PolyLin(n, 2)
    for k in range(K):
        xx = xx + lams[k].mul_fixed(verts[k][0], 2)
        xy = xy + lams[k].mul_fixed(verts[k][1], 2)
    one2 = mono(n, 2, [0] * n)
    g = []
    for comp, sgn in ((xx, +1), (xx, -1), (xy, +1), (xy, -1)):
        gi = PolyLin(n, 2); gi.add('const', W * one2)
        g.append(gi + comp.scale(-sgn))
    return g, lams, nz


def solve_bernstein(n, kind, verts, box=None):
    box = box or [(-1.0, 1.0)] * n
    g, lams, nz = build_constraint_polys(n, kind, verts)
    z = cp.Variable(nz); t = cp.Variable()
    cons = []
    Atot = np.zeros(((1 + 1) ** n, nz)); btot = np.zeros((1 + 1) ** n)
    for L in lams:
        A, b = L.coeff_rows(nz); Atot += A; btot += b
    target = np.zeros((2,) * n); target[(0,) * n] = 1.0
    cons.append(Atot @ z + btot == target.reshape(-1))
    for L in lams:
        A, b = L.bernstein_rows(box, nz)
        cons.append(A @ z + b >= 0)
    for gi in g:
        A, b = gi.bernstein_rows(box, nz)
        cons.append(A @ z + b >= t)
    prob = cp.Problem(cp.Maximize(t), cons)
    t0 = time.time()
    prob.solve(solver=cp.CLARABEL)
    dt = time.time() - t0
    return (None if t.value is None else float(t.value)), dt, nz


def solve_sos(n, kind, verts, box_half=1.0):
    """SOS-SDP back-end (E2 cross-check only). Lives here, never imported by cnp
    core — CLAUDE.md rule 3 keeps SDP out of the critical path."""
    g, lams, nz = build_constraint_polys(n, kind, verts)
    z = cp.Variable(nz); t = cp.Variable()
    cons = []
    Atot = np.zeros((2 ** n, nz)); btot = np.zeros(2 ** n)
    for L in lams:
        A, b = L.coeff_rows(nz); Atot += A; btot += b
    target = np.zeros((2,) * n); target[(0,) * n] = 1.0
    cons.append(Atot @ z + btot == target.reshape(-1))
    box = [(-box_half, box_half)] * n
    for L in lams:
        A, b = L.bernstein_rows(box, nz)
        cons.append(A @ z + b >= 0)
    mexp = [e for e in iproduct(*[(0, 1)] * n)]
    M = len(mexp)

    def flat(e):
        f = 0
        for x in e:
            f = 3 * f + x
        return f

    pair_lists = {}
    for i in range(M):
        for j in range(M):
            e = tuple(a + b for a, b in zip(mexp[i], mexp[j]))
            pair_lists.setdefault(flat(e), ([], []))
            pair_lists[flat(e)][0].append(i); pair_lists[flat(e)][1].append(j)
    t0 = time.time()
    for gi in g:
        A, b = gi.coeff_rows(nz)
        Q = cp.Variable((M, M), symmetric=True)
        c = cp.Variable(n, nonneg=True)
        cons.append(Q >> 0)
        for fidx in range(3 ** n):
            lhs = A[fidx] @ z + b[fidx]
            e = np.base_repr(fidx, base=3).zfill(n)
            e = tuple(int(ch) for ch in e)
            rhs = 0
            if fidx in pair_lists:
                rows, cols = pair_lists[fidx]
                rhs = rhs + cp.sum(Q[rows, cols])
            if e == (0,) * n:
                rhs = rhs + t + cp.sum(c)
            for i in range(n):
                if e[i] == 2 and all(e[jj] == 0 for jj in range(n) if jj != i):
                    rhs = rhs - c[i] * (box_half ** 2)
            cons.append(lhs == rhs)
    prob = cp.Problem(cp.Maximize(t), cons)
    prob.solve(solver=cp.CLARABEL)
    dt = time.time() - t0
    return (None if t.value is None else float(t.value)), dt, (M, nz)


def truth_check(n, a_tot, gamma):
    """max |c_x| over vertices of Q; collision everywhere iff <= 2W."""
    _, cx = scene_tensors(n, a_tot, gamma)
    mx = 0.0
    for v in iproduct(*[(-1.0, 1.0)] * n):
        mx = max(mx, abs(teval(cx, v)))
    return mx


# ======================================================================
# E3 + E4 — multi-pair certified disconnection, real 2-link rational FK
# ======================================================================

L1 = L2 = 1.0
LIM = [(-1.0, 1.0), (-1.0, 1.0)]
UP = (0.97, 1.30, 0.08, 1.05)
DOWN = (0.97, 1.30, -1.05, -0.08)
MID = (1.80, 2.10, -0.45, 0.45)


def fk_tensors():
    """Rational FK numerators (deg <= 2 per var) and common denominator D > 0."""
    n = 2

    def T(expos):
        t = zeros(n, 2)
        for e, c in expos.items():
            t[e] += c
        return t

    D = T({(0, 0): 1, (2, 0): 1, (0, 2): 1, (2, 2): 1})                # (1+s1^2)(1+s2^2)
    P1x = T({(0, 0): 1, (0, 2): 1, (2, 0): -1, (2, 2): -1})            # (1-s1^2)(1+s2^2)
    P1y = T({(1, 0): 2, (1, 2): 2})                                    # 2 s1 (1+s2^2)
    C12 = T({(0, 0): 1, (0, 2): -1, (2, 0): -1, (2, 2): 1, (1, 1): -4})
    S12 = T({(1, 0): 2, (1, 2): -2, (0, 1): 2, (2, 1): -2})
    return D, P1x, P1y, C12, S12


D, P1X, P1Y, C12, S12 = fk_tensors()


def fk_point(th1, th2, t):
    p1 = np.array([np.cos(th1), np.sin(th1)]) * L1
    p2 = p1 + np.array([np.cos(th1 + th2), np.sin(th1 + th2)]) * L2
    return p1 + t * (p2 - p1)


def seg_box_hit(th1, th2, box, m=60):
    xlo, xhi, ylo, yhi = box
    for t in np.linspace(0, 1, m):
        p = fk_point(th1, th2, t)
        if xlo <= p[0] <= xhi and ylo <= p[1] <= yhi:
            return True
    return False


def in_collision(th1, th2, boxes):
    return any(seg_box_hit(th1, th2, b) for b in boxes)


def certify_cell_pair(cell, box, phi=None, delta=None, putinar_sign=-1):
    """Witness x(s)=p1+lam(s)(p2-p1) inside ``box`` for all s in ``cell`` intersected
    with the slab {phi^2 <= delta^2}. Returns t* (>0 => certified) or None.

    putinar_sign=-1 (default, SOUND): Bernstein(g - mu*T) >= t  =>  g >= t on {T>=0}.
    putinar_sign=+1 is UNSOUND (g + mu*T) and exists ONLY so test_putinar_sign.py
    can freeze the sign; production never sets it. See CLAUDE.md rule 2.
    """
    assert putinar_sign in (-1, +1)
    n = 2
    xlo, xhi, ylo, yhi = box
    es = [(0, 0), (1, 0), (0, 1)]  # affine lambda
    nz = len(es)
    lam = PolyLin(n, 1)
    for j, e in enumerate(es):
        lam.add(j, mono(n, 1, list(e)))
    Xx = PolyLin(n, 3); Xx.add('const', np.pad(P1X, (0, 1)))
    Xy = PolyLin(n, 3); Xy.add('const', np.pad(P1Y, (0, 1)))
    Xx = Xx + lam.mul_fixed(C12, 3)
    Xy = Xy + lam.mul_fixed(S12, 3)
    D3 = np.pad(D, (0, 1))
    gs = []
    for comp, lo, hi in ((Xx, xlo, xhi), (Xy, ylo, yhi)):
        g1 = PolyLin(n, 3); g1.add('const', -lo * D3); g1 = g1 + comp            # X - lo*D >= 0
        g2 = PolyLin(n, 3); g2.add('const', hi * D3); g2 = g2 + comp.scale(-1)   # hi*D - X >= 0
        gs += [g1, g2]
    z = cp.Variable(nz); t = cp.Variable()
    cons = []
    A, b = lam.bernstein_rows(cell, nz)
    cons += [A @ z + b >= 0, A @ z + b <= 1]
    DPAD = 4
    bT = None
    if phi is not None:
        Tt = np.zeros((DPAD + 1,) * n)
        Tt[(0,) * n] = delta ** 2
        Tt -= np.pad(tmul(phi, phi, 4), (0, DPAD - 4))
        bT = bernstein_coeffs(Tt, cell).reshape(-1)
        mu = cp.Variable(len(gs), nonneg=True)
    for j, g in enumerate(gs):
        gp = PolyLin(n, DPAD)
        for k, tt in g.terms.items():
            gp.add(k, np.pad(tt, (0, DPAD - g.d)))
        A, b = gp.bernstein_rows(cell, nz)
        if bT is not None:
            # putinar_sign=-1: g - mu*T >= t (SOUND);  +1: g + mu*T >= t (UNSOUND)
            cons.append(A @ z + b + putinar_sign * mu[j] * bT >= t)
        else:
            cons.append(A @ z + b >= t)
    prob = cp.Problem(cp.Maximize(t), cons)
    try:
        prob.solve(solver=cp.CLARABEL)
    except Exception:
        return None
    return None if t.value is None else float(t.value)


def cell_outside_slab(cell, phi, delta):
    bc = bernstein_coeffs(phi, cell)
    return bc.min() >= delta or bc.max() <= -delta


def certify_slab(phi, delta, boxes, names, max_depth=16, tol=1e-6, putinar_sign=-1):
    """Branch-and-bound over LIM. Returns (ok, leaves, failed).
    leaves entries: (cell, status, pairname, t*)."""
    leaves = []
    failed = []

    def rec(cell, depth):
        if cell_outside_slab(cell, phi, delta):
            leaves.append((cell, 'outside', None, None)); return True
        best, bestname = None, None
        for b, nm in zip(boxes, names):
            ts = certify_cell_pair(cell, b, phi, delta, putinar_sign=putinar_sign)
            if ts is not None and (best is None or ts > best):
                best, bestname = ts, nm
        if best is not None and best > tol:
            leaves.append((cell, 'collision', bestname, best)); return True
        if depth >= max_depth:
            failed.append(cell); leaves.append((cell, 'FAIL', None, best)); return False
        i = 0 if (cell[0][1] - cell[0][0]) >= (cell[1][1] - cell[1][0]) else 1
        for ax in (0, 1):
            mid_ = 0.5 * (cell[ax][0] + cell[ax][1])
            for half in ((cell[ax][0], mid_), (mid_, cell[ax][1])):
                cc = [list(c) for c in cell]; cc[ax] = list(half)
                if cell_outside_slab([tuple(x) for x in cc], phi, delta):
                    i = ax; break
            else:
                continue
            break
        mid = 0.5 * (cell[i][0] + cell[i][1])
        c1 = [list(c) for c in cell]; c2 = [list(c) for c in cell]
        c1[i][1] = mid; c2[i][0] = mid
        ok1 = rec([tuple(c) for c in c1], depth + 1)
        ok2 = rec([tuple(c) for c in c2], depth + 1)
        return ok1 and ok2

    ok = rec([tuple(c) for c in LIM], 0)
    return ok, leaves, failed


def shrink(b, f=0.70):
    """Negative control: shrink an obstacle box about its centre by factor f."""
    cx, cy = (b[0] + b[1]) / 2, (b[2] + b[3]) / 2
    wx, wy = (b[1] - b[0]) / 2 * f, (b[3] - b[2]) / 2 * f
    return (cx - wx, cx + wx, cy - wy, cy + wy)


def fit_phi_e4(boxes, seed=1, nsamp=1500):
    """E4 learned barrier: seeded least-squares fit of phi over deg<=2/var basis.
    Returns (phi_fit tensor, delta_fit, start, goal)."""
    start = (-np.pi / 3, 0.0); goal = (np.pi / 3, 0.0)
    rng = np.random.default_rng(seed)
    S = rng.uniform(-1, 1, size=(nsamp, 2))
    y = np.array([1.0 if in_collision(2 * np.arctan(a), 2 * np.arctan(b), boxes) else 0.0
                  for a, b in S])
    expos = [(i, j) for i in range(3) for j in range(3)]
    F = np.stack([(S[:, 0] ** i) * (S[:, 1] ** j) for (i, j) in expos], axis=1)
    tgt = np.sign(S[:, 0]) * (1.0 - y) + 0.0 * y
    w, *_ = np.linalg.lstsq(F, tgt, rcond=None)
    phi_fit = zeros(2, 2)
    for c, e in zip(w, expos):
        phi_fit[e] += c
    s_start = [np.tan(start[0] / 2), np.tan(start[1] / 2)]
    s_goal = [np.tan(goal[0] / 2), np.tan(goal[1] / 2)]
    df = min(-teval(phi_fit, s_start), teval(phi_fit, s_goal))
    delta_f = 0.5 * df
    return phi_fit, delta_f, start, goal
