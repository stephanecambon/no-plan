"""witness — slab-aware witness-certificate LP builder (session S2, CLAUDE.md).

Generic n-dimensional witness LP for a moving convex body (given by the rational-FK
*vertex numerators* over a common denominator, cf. :mod:`cnp.ratfk`) against a
static polytope obstacle in H-representation. This is the per-leaf, per-pair LP of
SPEC §2; the branch-and-bound that drives it over cells is :mod:`cnp.engine` (S3).

Mathematics (SPEC §2). For a cell ``Q`` of s-space, a body whose convex-hull
vertices have world positions ``v_k(s) = N_k(s) / D(s)`` (``N_k`` numerator tensors
of degree <= 2 per var, ``D`` the common denominator, ``D > 0`` on Q), and a static
obstacle ``O = {y : a_j^T y <= b_j}``:

    witness    x(s) = sum_k lambda_k(s) * v_k(s),   sum_k lambda_k = 1,  lambda_k >= 0
    numerator  X_i(s) = sum_k lambda_k(s) * N_k[i](s)        (so x = X / D)
    face j     g_j(s) = b_j * D(s) - a_j^T X(s) >= 0    <=>   a_j^T x <= b_j

Slab-aware (the slab is ``T = delta^2 - phi^2 >= 0``):

    Bernstein( g_j - mu_j * T ) >= t  on Q,    mu_j >= 0,    maximize t.

t > 0  =>  every face holds on Q intersect slab  =>  x(s) is inside O for all such s,
and x(s) lies in the body (convex combination of its vertices) => the body collides
with O on the whole slab-cell. Everything is linear in (lambda coeffs, mu, t): an LP.
No SDP, no Mosek (CLAUDE.md rule 3).

SIGN (CLAUDE.md rule 2 / SPEC §2): the slab term is ``g - mu*T`` (subtract).
``g + mu*T`` is UNSOUND (bug documented E3). The builder hard-codes the sound sign;
the ``_putinar_sign`` argument exists ONLY so tests/test_witness.py can *freeze* it,
exactly as tests/test_putinar_sign.py freezes the regression oracle. Production code
never sets it.

Back-end isolation: :func:`build_witness_lp` returns a solver-agnostic
:class:`WitnessLP` (plain numpy). A back-end consumes it and returns an
:class:`LPResult`. :class:`CvxpyBackend` is the S2 default; S8 will add a direct
highspy back-end consuming the very same :class:`WitnessLP`.

The only shared kernel with the rest of cnp is :mod:`cnp.polylin` (tensor algebra).
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product as iproduct

import numpy as np

from . import polylin
from .polylin import PolyLin, bernstein_coeffs, mono, tmul, zeros

# Total-degree cap of the lambda multipliers (SPEC §2: default affine).
LAM_DEGREE = {"const": 0, "affine": 1, "quadratic": 2}


# --------------------------------------------------------------------------- #
# Geometry: static obstacle in H-representation
# --------------------------------------------------------------------------- #

@dataclass
class Polytope:
    """Static obstacle ``{y in R^dim : A y <= b}`` (H-representation)."""

    A: np.ndarray  # (m, dim)
    b: np.ndarray  # (m,)

    def __post_init__(self):
        self.A = np.asarray(self.A, dtype=float)
        self.b = np.asarray(self.b, dtype=float).ravel()

    @classmethod
    def box(cls, lo, hi):
        """Axis-aligned box ``[lo_i, hi_i]`` as 2*dim faces."""
        lo = np.asarray(lo, dtype=float)
        hi = np.asarray(hi, dtype=float)
        dim = len(lo)
        A = np.vstack([np.eye(dim), -np.eye(dim)])
        b = np.concatenate([hi, -lo])
        return cls(A, b)

    @property
    def dim(self) -> int:
        return self.A.shape[1]

    @property
    def n_faces(self) -> int:
        return self.A.shape[0]

    def contains(self, y, tol: float = 0.0) -> bool:
        return bool(np.all(self.A @ np.asarray(y, dtype=float) <= self.b + tol))


# --------------------------------------------------------------------------- #
# Solver-agnostic LP container + back-end interface
# --------------------------------------------------------------------------- #

@dataclass
class WitnessLP:
    """Assembled witness LP in canonical 'maximize t' form (solver-agnostic).

    Decision vector is ``z`` (lambda coefficients, free) plus ``mu`` (>= 0, only if a
    slab is present) plus the scalar ``t`` (the objective).  Constraints:

        eq_A   @ z            == eq_b                         (sum_k lambda_k == 1)
        lam_A  @ z + lam_b    >= 0                            (lambda_k >= 0, Bernstein)
        face_Az@ z + face_Amu @ mu + face_b   >= t            (g_j - mu_j T >= t)

    ``basis`` and ``K`` describe the lambda layout so a witness point can be
    reconstructed from a solution (see :func:`eval_witness_point`).
    """

    nz: int
    nmu: int
    eq_A: np.ndarray
    eq_b: np.ndarray
    lam_A: np.ndarray
    lam_b: np.ndarray
    face_Az: np.ndarray
    face_Amu: np.ndarray
    face_b: np.ndarray
    basis: tuple
    K: int
    dim: int
    n_faces: int = 0   # #obstacle faces backing ``face_*`` (rows stacked per face)
    grid_dim: int = 0  # Bernstein grid extent per axis = DPAD+1 (face-row layout)


@dataclass
class LPResult:
    """Outcome of solving a :class:`WitnessLP`. ``t`` is the certified margin
    (``> 0`` means the pair certifies this cell). ``z`` / ``mu`` are the optimal
    multipliers (``None`` if the solve failed)."""

    t: float | None
    status: str
    z: np.ndarray | None = None
    mu: np.ndarray | None = None
    basis: tuple = ()
    K: int = 0
    dim: int = 0


class LPBackend:
    """Back-end interface: turn a :class:`WitnessLP` into an :class:`LPResult`."""

    name = "abstract"

    def solve(self, lp: WitnessLP) -> LPResult:  # pragma: no cover - interface
        raise NotImplementedError


class CvxpyBackend(LPBackend):
    """Default S2 back-end: cvxpy + CLARABEL (same solver as the S0 oracle)."""

    name = "cvxpy"

    def __init__(self, solver: str = "CLARABEL"):
        self.solver = solver

    def solve(self, lp: WitnessLP) -> LPResult:
        import cvxpy as cp

        z = cp.Variable(lp.nz)
        t = cp.Variable()
        cons = [lp.eq_A @ z == lp.eq_b, lp.lam_A @ z + lp.lam_b >= 0]
        mu = None
        if lp.nmu:
            mu = cp.Variable(lp.nmu, nonneg=True)
            cons.append(lp.face_Az @ z + lp.face_Amu @ mu + lp.face_b >= t)
        else:
            cons.append(lp.face_Az @ z + lp.face_b >= t)
        prob = cp.Problem(cp.Maximize(t), cons)
        try:
            prob.solve(solver=getattr(cp, self.solver))
        except Exception:  # noqa: BLE001 - any solver failure is UNDECIDED, not a crash
            return LPResult(None, "error", basis=lp.basis, K=lp.K, dim=lp.dim)
        if t.value is None:
            return LPResult(None, prob.status, basis=lp.basis, K=lp.K, dim=lp.dim)
        return LPResult(
            float(t.value),
            prob.status,
            z=np.asarray(z.value, dtype=float).ravel(),
            mu=None if mu is None else np.asarray(mu.value, dtype=float).ravel(),
            basis=lp.basis,
            K=lp.K,
            dim=lp.dim,
        )


class HighsBackend(LPBackend):
    """Direct LP back-end via ``scipy.optimize.linprog(method="highs")`` over the
    SAME solver-agnostic :class:`WitnessLP`. Two reasons it is the engine default
    (S3): (1) it is **Mosek-free** — unlike importing cvxpy, which probes every
    installed solver and so transitively wakes the Drake-bundled mosek (CLAUDE.md
    rule 3; see tests/test_mosek_guard.py); (2) no per-solve compile / no cvxpy
    import, so it is faster and lets forked workers start instantly. S8 will swap
    scipy for highspy directly; the WitnessLP stays identical (the S2 isolation
    design). t* agrees with CLARABEL to < 1e-6 (proved in tests/test_witness.py)."""

    name = "highs"

    def solve(self, lp: WitnessLP) -> LPResult:
        from scipy.optimize import linprog

        nz, nmu = lp.nz, lp.nmu
        nv = nz + nmu + 1                 # z (free), mu (>=0), t (free, the objective)
        c = np.zeros(nv); c[-1] = -1.0    # maximize t  <=>  minimize -t
        A_eq = np.hstack([lp.eq_A, np.zeros((lp.eq_A.shape[0], nmu + 1))])
        b_eq = lp.eq_b
        ub_rows = [np.hstack([-lp.lam_A, np.zeros((lp.lam_A.shape[0], nmu + 1))])]
        ub_b = [lp.lam_b]                 # lambda >= 0  <=>  -lam_A z <= lam_b
        face = np.hstack([lp.face_Az, lp.face_Amu,
                          -np.ones((lp.face_Az.shape[0], 1))])
        ub_rows.append(-face)            # g(-muT) - t >= -face_b  <=>  -(...) <= face_b
        ub_b.append(lp.face_b)
        bounds = [(None, None)] * nz + [(0, None)] * nmu + [(None, None)]
        try:
            r = linprog(c, A_ub=np.vstack(ub_rows), b_ub=np.concatenate(ub_b),
                        A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
        except Exception:  # noqa: BLE001 - any solver failure is UNDECIDED, not a crash
            return LPResult(None, "error", basis=lp.basis, K=lp.K, dim=lp.dim)
        if not r.success or r.x is None:
            return LPResult(None, r.message, basis=lp.basis, K=lp.K, dim=lp.dim)
        x = np.asarray(r.x, dtype=float)
        return LPResult(float(-r.fun), "optimal",
                        z=x[:nz], mu=(x[nz:nz + nmu] if nmu else None),
                        basis=lp.basis, K=lp.K, dim=lp.dim)


DEFAULT_BACKEND = CvxpyBackend()


# --------------------------------------------------------------------------- #
# LP assembly
# --------------------------------------------------------------------------- #

def lambda_basis(n: int, lam_degree: str) -> tuple:
    """Monomial exponents of a lambda multiplier: total degree <= LAM_DEGREE[kind]."""
    maxdeg = LAM_DEGREE[lam_degree]
    return tuple(e for e in iproduct(range(maxdeg + 1), repeat=n) if sum(e) <= maxdeg)


def _pad(t: np.ndarray, d_dst: int) -> np.ndarray:
    """Pad a coefficient tensor up to per-variable degree ``d_dst``."""
    d_src = t.shape[0] - 1
    if d_src == d_dst:
        return t
    if d_src > d_dst:  # pragma: no cover - guarded by callers
        raise ValueError("cannot pad to a smaller degree")
    return np.pad(t, [(0, d_dst - d_src)] * t.ndim)


def build_witness_lp(cell, verts_num, D, obstacle: Polytope,
                     phi=None, delta=None, lam_degree: str = "affine",
                     _putinar_sign: int = -1) -> WitnessLP:
    """Assemble the slab-aware witness LP for one (cell, moving body, obstacle).

    Parameters
    ----------
    cell : list of (lo, hi) per s-variable (the leaf box Q).
    verts_num : list of K vertices, each a list ``[N_0, ..., N_{dim-1}]`` of
        numerator tensors over the common denominator ``D`` (cf.
        ``ratfk.BodyRatFK.vertex_numerators``).
    D : common denominator tensor (``> 0`` on the cell).
    obstacle : :class:`Polytope` (static, H-rep).
    phi, delta : the slab ``T = delta^2 - phi^2``; pass ``phi=None`` to drop the slab
        (certify the whole cell, no barrier).
    lam_degree : 'const' | 'affine' | 'quadratic'.
    _putinar_sign : TEST-ONLY. -1 (default, SOUND) builds ``g - mu*T``; +1 builds the
        UNSOUND ``g + mu*T``. Frozen by tests/test_witness.py (CLAUDE.md rule 2).
    """
    assert _putinar_sign in (-1, +1)
    n = len(cell)
    K = len(verts_num)
    dim = obstacle.dim
    if any(len(v) != dim for v in verts_num):
        raise ValueError("vertex numerators and obstacle have mismatched dimension")

    d_N = D.shape[0] - 1
    d_lam = LAM_DEGREE[lam_degree]
    basis = lambda_basis(n, lam_degree)
    B = len(basis)
    nz = K * B

    # --- lambda multipliers: one PolyLin per vertex, own decision-variable ids ---
    lams = []
    vid = 0
    for _k in range(K):
        L = PolyLin(n, d_lam)
        for e in basis:
            L.add(vid, mono(n, d_lam, list(e)))
            vid += 1
        lams.append(L)

    # --- witness numerator X_i = sum_k lambda_k * N_k[i] (degree d_lam + d_N) ---
    d_X = d_lam + d_N
    X = []
    for i in range(dim):
        Xi = PolyLin(n, d_X)
        for k in range(K):
            Xi = Xi + lams[k].mul_fixed(verts_num[k][i], d_X)
        X.append(Xi)

    # --- slab tensor T = delta^2 - phi^2 (Bernstein over the cell) ---
    has_slab = phi is not None
    DPAD = d_X
    bT = None
    if has_slab:
        d_phi = phi.shape[0] - 1
        DPAD = max(d_X, 2 * d_phi)
        Tt = zeros(n, DPAD)
        Tt[(0,) * n] = float(delta) ** 2
        Tt = Tt - _pad(tmul(phi, phi, 2 * d_phi), DPAD)
        bT = bernstein_coeffs(Tt, cell).reshape(-1)

    # --- face polynomials g_j = b_j * D - a_j^T X ---
    Dp = _pad(D, DPAD)
    g_list = []
    for j in range(obstacle.n_faces):
        gj = PolyLin(n, DPAD)
        gj.add("const", obstacle.b[j] * Dp)
        for i in range(dim):
            aij = obstacle.A[j, i]
            if aij != 0.0:
                gj = gj + X[i].scale(-aij)
        g_list.append(gj)

    # --- equality: sum_k lambda_k == 1 (raw coefficients; identity in s) ---
    m_eq = (d_lam + 1) ** n
    eq_A = np.zeros((m_eq, nz))
    eq_b_acc = np.zeros(m_eq)
    for L in lams:
        a, b = L.coeff_rows(nz)
        eq_A += a
        eq_b_acc += b
    target = np.zeros(m_eq)
    target[0] = 1.0  # constant monomial (origin) is flat index 0
    eq_b = target - eq_b_acc

    # --- lambda_k >= 0 on the cell (Bernstein) ---
    lam_A_rows, lam_b_rows = [], []
    for L in lams:
        a, b = L.bernstein_rows(cell, nz)
        lam_A_rows.append(a)
        lam_b_rows.append(b)
    lam_A = np.vstack(lam_A_rows)
    lam_b = np.concatenate(lam_b_rows)

    # --- face rows: g_j (- mu_j T) >= t ---
    nmu = obstacle.n_faces if has_slab else 0
    face_Az_rows, face_b_rows, face_Amu_rows = [], [], []
    for j, gj in enumerate(g_list):
        a, b = gj.bernstein_rows(cell, nz)
        face_Az_rows.append(a)
        face_b_rows.append(b)
        if has_slab:
            amu = np.zeros((a.shape[0], nmu))
            amu[:, j] = _putinar_sign * bT  # SOUND default: g - mu*T
            face_Amu_rows.append(amu)
    face_Az = np.vstack(face_Az_rows)
    face_b = np.concatenate(face_b_rows)
    face_Amu = (np.vstack(face_Amu_rows) if has_slab
                else np.zeros((face_Az.shape[0], 0)))

    return WitnessLP(nz=nz, nmu=nmu, eq_A=eq_A, eq_b=eq_b,
                     lam_A=lam_A, lam_b=lam_b, face_Az=face_Az,
                     face_Amu=face_Amu, face_b=face_b,
                     basis=basis, K=K, dim=dim,
                     n_faces=obstacle.n_faces, grid_dim=DPAD + 1)


def certify_cell_pair(cell, verts_num, D, obstacle: Polytope,
                      phi=None, delta=None, lam_degree: str = "affine",
                      backend: LPBackend | None = None,
                      _putinar_sign: int = -1) -> LPResult:
    """Build and solve the witness LP for one (cell, body, obstacle). ``result.t > 0``
    certifies that the body collides with the obstacle across the slab-cell."""
    lp = build_witness_lp(cell, verts_num, D, obstacle, phi=phi, delta=delta,
                          lam_degree=lam_degree, _putinar_sign=_putinar_sign)
    return (backend or DEFAULT_BACKEND).solve(lp)


# --------------------------------------------------------------------------- #
# Witness-point reconstruction (for sampled ground-truth checks)
# --------------------------------------------------------------------------- #

def _teval_batch(t: np.ndarray, S: np.ndarray) -> np.ndarray:
    """Evaluate a coefficient tensor at many points ``S`` (shape (M, n)). Sparse."""
    out = np.zeros(S.shape[0])
    for e in np.argwhere(t != 0):
        term = float(t[tuple(e)]) * np.ones(S.shape[0])
        for i, p in enumerate(e):
            if p:
                term = term * S[:, i] ** int(p)
        out += term
    return out


def eval_witness_point(result: LPResult, verts_num, D, S: np.ndarray) -> np.ndarray:
    """World positions of the witness point at the samples ``S`` (shape (M, n)).

    ``x(s) = sum_k lambda_k(s) * N_k(s) / D(s)`` with lambda coefficients from the
    solved ``result``. Returns an (M, dim) array. Used by the sampled ground-truth
    soundness check (S2 exit criterion): a sound certificate puts every such point
    inside the obstacle.
    """
    if result.z is None:
        raise ValueError("result has no solution to evaluate")
    S = np.asarray(S, dtype=float)
    M = S.shape[0]
    basis, K, dim = result.basis, result.K, result.dim
    B = len(basis)
    z = result.z.reshape(K, B)

    # lambda_k(s) for every sample
    lam = np.zeros((K, M))
    for k in range(K):
        for c, e in zip(z[k], basis):
            if c != 0.0:
                term = c * np.ones(M)
                for i, p in enumerate(e):
                    if p:
                        term = term * S[:, i] ** int(p)
                lam[k] += term

    Dv = _teval_batch(D, S)
    Xnum = np.zeros((M, dim))
    for i in range(dim):
        acc = np.zeros(M)
        for k in range(K):
            acc += lam[k] * _teval_batch(verts_num[k][i], S)
        Xnum[:, i] = acc
    return Xnum / Dv[:, None]
