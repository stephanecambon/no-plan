"""E1 + E2: witness ladder x two certification back-ends.

Scene (synthetic, multilinear, controlled): moving square A(s) (half-width w)
with center c_x(s) = a_tot * mean(s) + gamma * mean(s_i s_{i+1}), c_y = 0,
fixed box B = [-w,w]^2, cell Q = [-1,1]^n.
Collision holds for all s in Q iff max|c_x| <= 2w  (checked at vertices).

Witness: x(s) = sum_k lambda_k(s) v_k(s), sum lambda_k = 1, lambda_k >= 0 on Q.
Ladder: lambda constant | affine | multilinear.
Certify x(s) in B for all s in Q, maximize margin t.
Back-ends: (a) SOS: g - t = sigma0 + sum_i c_i (1 - s_i^2), sigma0 = m'Qm
           (b) Bernstein-LP: all Bernstein coeffs of g - t >= 0.
"""
import numpy as np, cvxpy as cp, time, json, sys
from itertools import product as iproduct
from polylin import PolyLin, zeros, mono, tmul, teval, bernstein_coeffs

W = 0.35  # half widths of A and B

def scene_tensors(n, a_tot=0.44, gamma=0.04):
    """Return list of 4 vertex polys [vx, vy] (deg<=1/var tensors) of A(s)."""
    cx = zeros(n, 1)
    for i in range(n):
        e = [0]*n; e[i] = 1
        cx[tuple(e)] += a_tot / n
    for i in range(n - 1):
        e = [0]*n; e[i] = 1; e[i+1] = 1
        cx[tuple(e)] += gamma / (n - 1)
    cy = zeros(n, 1)
    corners = [(+W,+W),(+W,-W),(-W,+W),(-W,-W)]
    verts = []
    one = mono(n, 1, [0]*n)
    for (dx, dy) in corners:
        verts.append([cx + dx*one, cy + dy*one])
    return verts, cx

def lam_basis(n, kind):
    """Exponent list for lambda polynomials."""
    if kind == 'const':
        return [tuple([0]*n)]
    if kind == 'affine':
        es = [tuple([0]*n)]
        for i in range(n):
            e = [0]*n; e[i] = 1; es.append(tuple(e))
        return es
    if kind == 'multilinear':
        return [e for e in iproduct(*[(0,1)]*n)]
    raise ValueError

def build_constraint_polys(n, kind, verts):
    """Return (g_list as PolyLin deg<=2, lam_list as PolyLin deg<=1, nz)."""
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
    # x(s) = sum lam_k * v_k  (deg <= 2 per var)
    xx = PolyLin(n, 2); xy = PolyLin(n, 2)
    for k in range(K):
        xx = xx + lams[k].mul_fixed(verts[k][0], 2)
        xy = xy + lams[k].mul_fixed(verts[k][1], 2)
    one2 = mono(n, 2, [0]*n)
    g = []
    for comp, sgn in ((xx, +1), (xx, -1), (xy, +1), (xy, -1)):
        # W - sgn*comp >= 0
        gi = PolyLin(n, 2); gi.add('const', W * one2)
        g.append(gi + comp.scale(-sgn))
    return g, lams, nz

def solve_bernstein(n, kind, verts, box=None):
    box = box or [(-1.0, 1.0)] * n
    g, lams, nz = build_constraint_polys(n, kind, verts)
    z = cp.Variable(nz); t = cp.Variable()
    cons = []
    # sum lam = 1 (coefficient identity)
    A1 = np.zeros(((2)**0,0))  # placeholder
    Asum = None
    Atot = np.zeros(((1+1)**n, nz)); btot = np.zeros((1+1)**n)
    for L in lams:
        A, b = L.coeff_rows(nz); Atot += A; btot += b
    target = np.zeros((2,)*n); target[(0,)*n] = 1.0
    cons.append(Atot @ z + btot == target.reshape(-1))
    # lam_k >= 0 on box (Bernstein of deg-1 tensor = vertex values: exact)
    for L in lams:
        A, b = L.bernstein_rows(box, nz)
        cons.append(A @ z + b >= 0)
    # g_j >= t on box via Bernstein
    for gi in g:
        A, b = gi.bernstein_rows(box, nz)
        cons.append(A @ z + b >= t)
    prob = cp.Problem(cp.Maximize(t), cons)
    t0 = time.time()
    prob.solve(solver=cp.CLARABEL)
    dt = time.time() - t0
    return (None if t.value is None else float(t.value)), dt, nz

def solve_sos(n, kind, verts, box_half=1.0):
    g, lams, nz = build_constraint_polys(n, kind, verts)
    z = cp.Variable(nz); t = cp.Variable()
    cons = []
    Atot = np.zeros((2**n, nz)); btot = np.zeros(2**n)
    for L in lams:
        A, b = L.coeff_rows(nz); Atot += A; btot += b
    target = np.zeros((2,)*n); target[(0,)*n] = 1.0
    cons.append(Atot @ z + btot == target.reshape(-1))
    # lam >= 0 at vertices (exact for deg<=1/var)
    box = [(-box_half, box_half)] * n
    for L in lams:
        A, b = L.bernstein_rows(box, nz)
        cons.append(A @ z + b >= 0)
    # SOS: for each g_j: g_j - t = m'Qm + sum_i c_i (1 - s_i^2)
    mexp = [e for e in iproduct(*[(0,1)]*n)]   # multilinear basis, 2^n
    M = len(mexp)
    # map exponent tuple (base 3) -> flat index
    def flat(e):
        f = 0
        for x in e: f = 3*f + x
        return f
    pair_lists = {}
    for i in range(M):
        for j in range(M):
            e = tuple(a+b for a, b in zip(mexp[i], mexp[j]))
            pair_lists.setdefault(flat(e), ([], []))
            pair_lists[flat(e)][0].append(i); pair_lists[flat(e)][1].append(j)
    t0 = time.time()
    for gi in g:
        A, b = gi.coeff_rows(nz)   # 3^n rows
        Q = cp.Variable((M, M), symmetric=True)
        c = cp.Variable(n, nonneg=True)
        cons.append(Q >> 0)
        for fidx in range(3**n):
            lhs = A[fidx] @ z + b[fidx]
            e = np.base_repr(fidx, base=3).zfill(n)
            e = tuple(int(ch) for ch in e)
            rhs = 0
            if fidx in pair_lists:
                rows, cols = pair_lists[fidx]
                rhs = rhs + cp.sum(Q[rows, cols])
            if e == (0,)*n:
                rhs = rhs + t + cp.sum(c)
            # term -c_i s_i^2
            for i in range(n):
                if e[i] == 2 and all(e[jj] == 0 for jj in range(n) if jj != i):
                    rhs = rhs - c[i] * (box_half**2)
            cons.append(lhs == rhs)
    prob = cp.Problem(cp.Maximize(t), cons)
    prob.solve(solver=cp.CLARABEL)
    dt = time.time() - t0
    return (None if t.value is None else float(t.value)), dt, (M, nz)

def truth_check(n, a_tot, gamma):
    """max |c_x| over vertices of Q; collision everywhere iff <= 2W."""
    _, cx = scene_tensors(n, a_tot, gamma)
    mx = 0.0
    for v in iproduct(*[(-1.0, 1.0)]*n):
        mx = max(mx, abs(teval(cx, v)))
    return mx

if __name__ == "__main__":
    results = []
    print(f"{'n':>2} {'scene':>9} {'witness':>11} {'backend':>9} {'t*':>8} {'time(s)':>8} {'size':>12}")
    for n in [3, 4, 5, 6]:
        for a_tot, tag in [(0.44, 'collision'), (0.85, 'NEGATIVE')]:
            mx = truth_check(n, a_tot, 0.04)
            truly = mx <= 2*W
            verts, _ = scene_tensors(n, a_tot, 0.04)
            for kind in ['const', 'affine', 'multilinear']:
                if tag == 'NEGATIVE' and kind != 'affine':
                    continue
                tb, dtb, nz = solve_bernstein(n, kind, verts)
                row = dict(n=n, scene=tag, truly_collision=truly, kind=kind,
                           backend='bern-LP', t=tb, time=dtb, size=str(nz))
                results.append(row)
                print(f"{n:>2} {tag:>9} {kind:>11} {'bern-LP':>9} {tb:>8.3f} {dtb:>8.2f} {('z='+str(nz)):>12}")
                if n <= 5 or kind == 'affine':
                    ts, dts, sz = solve_sos(n, kind, verts)
                    results.append(dict(n=n, scene=tag, truly_collision=truly, kind=kind,
                                        backend='SOS-SDP', t=ts, time=dts, size=str(sz)))
                    print(f"{n:>2} {tag:>9} {kind:>11} {'SOS-SDP':>9} {ts:>8.3f} {dts:>8.2f} {('Q='+str(sz[0])+'x'+str(sz[0])):>12}")
    json.dump(results, open('exp12_results.json', 'w'), indent=1)
    print("\nsaved exp12_results.json")
