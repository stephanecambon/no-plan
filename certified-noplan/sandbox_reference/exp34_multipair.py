"""E3 + E4: multi-pair certified disconnection, real 2-link rational FK.

Robot: planar 2-link, L1=L2=1, joint limits theta_i in [-pi/2, pi/2]
=> s_i = tan(theta_i/2) in [-1, 1].
Obstacles (workspace boxes), each blocking a DIFFERENT part of the slab:
  UP  = [0.97,1.30] x [ 0.12, 1.05]   (blocks link2 when folded up)
  DOWN= [0.97,1.30] x [-1.05,-0.12]   (blocks link2 when folded down)
  MID = [1.80,2.10] x [-0.45, 0.45]   (blocks link2 when extended)
Barrier phi(s), slab {|phi| <= delta}. Engine: branch-and-bound over the
limits box; each cell is either (a) certified disjoint from the slab
(Bernstein on phi), or (b) certified in-collision vs ONE pair (Bernstein-LP
witness on link2), or (c) split. Coverage of the slab is by construction.
Theorem: phi(start) <= -delta, phi(goal) >= +delta, slab subset C_obs
=> no collision-free path (within joint limits, |theta_i| < pi).
"""
import numpy as np, cvxpy as cp, time
from itertools import product as iproduct
from polylin import PolyLin, zeros, mono, tmul, teval, bernstein_coeffs

L1 = L2 = 1.0
LIM = [(-1.0, 1.0), (-1.0, 1.0)]
UP   = (0.97, 1.30, 0.08, 1.05)
DOWN = (0.97, 1.30, -1.05, -0.08)
MID  = (1.80, 2.10, -0.45, 0.45)

# ---------- rational FK numerators (deg <= 2 per var), denominator D > 0 ----------
def fk_tensors():
    n = 2
    def T(expos):  # dict {(e1,e2): coeff}
        t = zeros(n, 2)
        for e, c in expos.items(): t[e] += c
        return t
    D   = T({(0,0):1,(2,0):1,(0,2):1,(2,2):1})            # (1+s1^2)(1+s2^2)
    P1x = T({(0,0):1,(0,2):1,(2,0):-1,(2,2):-1})           # (1-s1^2)(1+s2^2)
    P1y = T({(1,0):2,(1,2):2})                             # 2 s1 (1+s2^2)
    C12 = T({(0,0):1,(0,2):-1,(2,0):-1,(2,2):1,(1,1):-4})  # (1-s1^2)(1-s2^2)-4s1s2
    S12 = T({(1,0):2,(1,2):-2,(0,1):2,(2,1):-2})           # 2s1(1-s2^2)+2s2(1-s1^2)
    return D, P1x, P1y, C12, S12

D, P1X, P1Y, C12, S12 = fk_tensors()

def fk_point(th1, th2, t):
    p1 = np.array([np.cos(th1), np.sin(th1)]) * L1
    p2 = p1 + np.array([np.cos(th1+th2), np.sin(th1+th2)]) * L2
    return p1 + t * (p2 - p1)

def seg_box_hit(th1, th2, box, m=60):
    xlo, xhi, ylo, yhi = box
    ts = np.linspace(0, 1, m)
    for t in ts:
        p = fk_point(th1, th2, t)
        if xlo <= p[0] <= xhi and ylo <= p[1] <= yhi:
            return True
    return False

def in_collision(th1, th2, boxes):
    return any(seg_box_hit(th1, th2, b) for b in boxes)

# ---------- witness certification on a cell vs one obstacle box ----------
def certify_cell_pair(cell, box, phi=None, delta=None):
    """Witness x(s)=p1+lam(s)(p2-p1) in box for all s in cell INTERSECTED with the
    slab {phi^2 <= delta^2} (Putinar multiplier, Bernstein back-end). t* or None."""
    n = 2
    xlo, xhi, ylo, yhi = box
    es = [(0,0),(1,0),(0,1)]  # affine lambda
    nz = len(es)
    lam = PolyLin(n, 1)
    for j, e in enumerate(es): lam.add(j, mono(n, 1, list(e)))
    # X = P1 + lam*(C12,S12), deg <= 3
    Xx = PolyLin(n, 3); Xx.add('const', np.pad(P1X, (0,1)))
    Xy = PolyLin(n, 3); Xy.add('const', np.pad(P1Y, (0,1)))
    Xx = Xx + lam.mul_fixed(C12, 3)
    Xy = Xy + lam.mul_fixed(S12, 3)
    D3 = np.pad(D, (0,1))
    gs = []
    for comp, lo, hi in ((Xx, xlo, xhi), (Xy, ylo, yhi)):
        g1 = PolyLin(n,3); g1.add('const', -lo*D3); g1 = g1 + comp           # X - lo*D >= 0
        g2 = PolyLin(n,3); g2.add('const',  hi*D3); g2 = g2 + comp.scale(-1) # hi*D - X >= 0
        gs += [g1, g2]
    z = cp.Variable(nz); t = cp.Variable()
    cons = []
    # lam in [0,1] on cell (deg-1 Bernstein = exact)
    A, b = lam.bernstein_rows(cell, nz)
    cons += [A @ z + b >= 0, A @ z + b <= 1]
    DPAD = 4
    bT = None
    if phi is not None:
        T = np.zeros((DPAD+1,)*n)
        T[(0,)*n] = delta**2
        T -= np.pad(tmul(phi, phi, 4), (0, DPAD-4)) if phi.shape[0]-1 <= 2 else None
        bT = bernstein_coeffs(T, cell).reshape(-1)
        mu = cp.Variable(len(gs), nonneg=True)
    for j, g in enumerate(gs):
        gp = PolyLin(n, DPAD)
        for k, tt in g.terms.items():
            gp.add(k, np.pad(tt, (0, DPAD - g.d)))
        A, b = gp.bernstein_rows(cell, nz)
        if bT is not None:
            cons.append(A @ z + b - mu[j] * bT >= t)  # g - mu*T >= t  =>  g >= t on {T>=0}
        else:
            cons.append(A @ z + b >= t)
    prob = cp.Problem(cp.Maximize(t), cons)
    try:
        prob.solve(solver=cp.CLARABEL)
    except Exception:
        return None
    return None if t.value is None else float(t.value)

# ---------- slab disjointness test ----------
def cell_outside_slab(cell, phi, delta):
    """True if Bernstein proves phi>=delta or phi<=-delta on the whole cell."""
    bc = bernstein_coeffs(phi, cell)
    return bc.min() >= delta or bc.max() <= -delta

# ---------- branch and bound ----------
def certify_slab(phi, delta, boxes, names, max_depth=16, tol=1e-6):
    leaves = []   # (cell, status, pairname, t*)
    failed = []
    def rec(cell, depth):
        if cell_outside_slab(cell, phi, delta):
            leaves.append((cell, 'outside', None, None)); return True
        best, bestname = None, None
        for b, nm in zip(boxes, names):
            ts = certify_cell_pair(cell, b, phi, delta)
            if ts is not None and (best is None or ts > best):
                best, bestname = ts, nm
        if best is not None and best > tol:
            leaves.append((cell, 'collision', bestname, best)); return True
        if depth >= max_depth:
            failed.append(cell); leaves.append((cell, 'FAIL', None, best)); return False
        # split-axis heuristic: prefer an axis whose halving makes a child outside-decidable
        i = 0 if (cell[0][1]-cell[0][0]) >= (cell[1][1]-cell[1][0]) else 1
        for ax in (0, 1):
            mid_ = 0.5*(cell[ax][0]+cell[ax][1])
            for half in ((cell[ax][0], mid_), (mid_, cell[ax][1])):
                cc = [list(c) for c in cell]; cc[ax] = list(half)
                if cell_outside_slab([tuple(x) for x in cc], phi, delta):
                    i = ax; break
            else:
                continue
            break
        mid = 0.5*(cell[i][0]+cell[i][1])
        c1 = [list(c) for c in cell]; c2 = [list(c) for c in cell]
        c1[i][1] = mid; c2[i][0] = mid
        ok1 = rec([tuple(c) for c in c1], depth+1)
        ok2 = rec([tuple(c) for c in c2], depth+1)
        return ok1 and ok2
    ok = rec([tuple(c) for c in LIM], 0)
    return ok, leaves, failed

# ---------- BFS path existence (for negative control honesty) ----------
def path_exists(boxes, start, goal, N=121):
    th = np.linspace(-np.pi/2, np.pi/2, N)
    free = np.zeros((N, N), bool)
    for i, a in enumerate(th):
        for j, b in enumerate(th):
            free[i, j] = not in_collision(a, b, boxes)
    def idx(q): return (np.abs(th - q[0]).argmin(), np.abs(th - q[1]).argmin())
    si, gi = idx(start), idx(goal)
    if not (free[si] and free[gi]): return None
    from collections import deque
    Q = deque([si]); seen = {si}
    while Q:
        i, j = Q.popleft()
        if (i, j) == gi: return True
        for di, dj in ((1,0),(-1,0),(0,1),(0,-1)):
            a, b = i+di, j+dj
            if 0 <= a < N and 0 <= b < N and free[a, b] and (a, b) not in seen:
                seen.add((a, b)); Q.append((a, b))
    return False

def run(tag, boxes, names, phi, delta, start, goal):
    print(f"\n=== {tag} ===")
    # theorem condition (i)
    s_start = [np.tan(start[0]/2), np.tan(start[1]/2)]
    s_goal  = [np.tan(goal[0]/2),  np.tan(goal[1]/2)]
    ps, pg = teval(phi, s_start), teval(phi, s_goal)
    print(f"phi(start)={ps:+.3f}  phi(goal)={pg:+.3f}  delta={delta}")
    assert ps <= -delta and pg >= delta, "condition (i) violated"
    assert not in_collision(*start, boxes) and not in_collision(*goal, boxes), "start/goal not free"
    t0 = time.time()
    ok, leaves, failed = certify_slab(phi, delta, boxes, names)
    dt = time.time() - t0
    ncol = sum(1 for l in leaves if l[1] == 'collision')
    nout = sum(1 for l in leaves if l[1] == 'outside')
    used = {}
    for l in leaves:
        if l[1] == 'collision': used[l[2]] = used.get(l[2], 0) + 1
    print(f"certified={ok}  time={dt:.1f}s  leaves={len(leaves)} (collision={ncol}, outside={nout}, fail={len(failed)})")
    print(f"pairs used: {used}")
    if ok:
        print(">>> THEOREME: aucune trajectoire sans collision start->goal (limites articulaires donnees).")
    else:
        pe = path_exists(boxes, start, goal)
        print(f">>> NON certifie. BFS sur grille trouve un chemin: {pe}")
    return ok, leaves, failed

if __name__ == "__main__":
    boxes3 = [UP, DOWN, MID]; names3 = ['UP', 'DOWN', 'MID']
    start = (-np.pi/3, 0.0); goal = (np.pi/3, 0.0)
    phi_hand = mono(2, 2, [1, 0])   # phi = s1
    delta = 0.05

    # sanity: empirical coverage of the slab
    bad = 0; tot = 0
    for s1 in np.linspace(-delta, delta, 9):
        for s2 in np.linspace(-1, 1, 41):
            th1, th2 = 2*np.arctan(s1), 2*np.arctan(s2)
            tot += 1
            if not in_collision(th1, th2, boxes3): bad += 1
    print(f"slab empirical coverage: {tot-bad}/{tot} samples in collision")

    ok3, leaves3, _ = run("E3: 3 obstacles, phi = s1 (multi-paires)", boxes3, names3, phi_hand, delta, start, goal)

    # negative control: shrink obstacles 30% -> slab premise becomes FALSE,
    # certifier must refuse (soundness check)
    def shrink(b, f=0.70):
        cx, cy = (b[0]+b[1])/2, (b[2]+b[3])/2
        wx, wy = (b[1]-b[0])/2*f, (b[3]-b[2])/2*f
        return (cx-wx, cx+wx, cy-wy, cy+wy)
    boxesS = [shrink(b) for b in boxes3]
    holes = sum(1 for s1 in np.linspace(-delta, delta, 9) for s2 in np.linspace(-1, 1, 41)
                if not in_collision(2*np.arctan(s1), 2*np.arctan(s2), boxesS))
    print(f"\n[controle negatif] echantillons LIBRES dans la dalle (premisse fausse): {holes}/369")
    okN, _, failedN = certify_slab(phi_hand, delta, boxesS, names3)
    print(f"certifie={okN} (attendu: False), feuilles en echec: {len(failedN)}")
    assert not okN, 'SOUNDNESS VIOLATION'

    # E4: fitted phi from samples (hybrid 'learned barrier' pipeline)
    print("\n=== E4: phi appris (moindres carres sur echantillons) ===")
    rng = np.random.default_rng(1)
    S = rng.uniform(-1, 1, size=(1500, 2))
    y = np.array([1.0 if in_collision(2*np.arctan(a), 2*np.arctan(b), boxes3) else 0.0 for a, b in S])
    # features: full deg<=2 per var basis
    expos = [(i, j) for i in range(3) for j in range(3)]
    F = np.stack([ (S[:,0]**i)*(S[:,1]**j) for (i,j) in expos ], axis=1)
    # target: signed function, + on goal side of obstacle band, - on start side.
    tgt = np.sign(S[:,0]) * (1.0 - y) + 0.0 * y   # free points get sign(s1), collision points 0
    w, *_ = np.linalg.lstsq(F, tgt, rcond=None)
    phi_fit = zeros(2, 2)
    for c, e in zip(w, expos): phi_fit[e] += c
    s_start = [np.tan(start[0]/2), np.tan(start[1]/2)]; s_goal = [np.tan(goal[0]/2), np.tan(goal[1]/2)]
    df = min(-teval(phi_fit, s_start), teval(phi_fit, s_goal))
    delta_f = 0.5 * df
    print(f"phi_fit coeffs (deg<=2/var): {np.round(w,3)}  delta_fit={delta_f:.3f}")
    run("E4: barriere apprise + certification", boxes3, names3, phi_fit, delta_f, start, goal)
