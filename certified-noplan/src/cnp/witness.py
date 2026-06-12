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
:class:`LPResult`. :class:`CvxpyBackend` is the S2 default; S8 added :class:`HighspyBackend`
(the direct highspy C++ API) as the engine default, consuming the very same
:class:`WitnessLP`. The passive-dimension LP reduction (``active_dims``, A18) is also S8.

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
    import, so it is faster and lets forked workers start instantly. S8 added the direct
    :class:`HighspyBackend` (now the engine default); this scipy wrapper stays available
    and identical (the S2 isolation design). t* agrees with CLARABEL to < 1e-6 (proved in
    tests/test_witness.py)."""

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


class HighspyBackend(LPBackend):
    """DIRECT HiGHS back-end via the ``highspy`` C++ API (session S8), consuming the
    SAME solver-agnostic :class:`WitnessLP` as every other back-end (the S2 isolation
    design). It skips ``scipy.optimize.linprog``'s per-call Python repacking: the LP is
    handed to a reused :class:`highspy.Highs` instance as a single CSC matrix, so the
    fixed cost per cell drops to the solve itself. Like :class:`HighsBackend` it is
    **Mosek-free** (CLAUDE.md rule 3). ``t*`` agrees with CLARABEL / scipy-HiGHS to the
    engine tolerance (frozen in tests/test_witness.py). This is the S8 perf default.
    Honest scope (CLAUDE.md rules 5/6): the backend swap alone is a ~2x constant factor
    over cvxpy on these LPs, NOT 10x — the order-of-magnitude S8 win is the active-dim LP
    reduction (``active_dims`` below / A18), which shrinks the row count itself."""

    name = "highspy"

    def __init__(self):
        import highspy
        self._highspy = highspy
        self._inf = highspy.kHighsInf
        self._h = None          # reused Highs instance, created lazily PER PROCESS
        self._pid = None        # so a forked worker makes its own (never shares the C++
        #                         solver object across a fork)

    def _solver(self):
        """One reused Highs instance per process: re-allocating a fresh Highs() per cell
        dominates the solve at these sizes (passModel replaces the model in place, so
        sibling cells reuse the same warm internals). Re-created after a fork so workers
        never share the parent's C++ solver object."""
        import os
        if self._h is None or self._pid != os.getpid():
            self._h = self._highspy.Highs()
            self._h.setOptionValue("output_flag", False)
            self._pid = os.getpid()
        return self._h

    def _model(self, lp: WitnessLP):
        import numpy as np
        from scipy.sparse import csc_matrix
        hp, inf = self._highspy, self._inf
        nz, nmu = lp.nz, lp.nmu
        nv = nz + nmu + 1                       # z (free), mu (>=0), t (free, objective)

        # rows: eq (sum lambda == 1), lam (lambda >= 0), face (g - mu T - t >= -face_b)
        eqA = np.hstack([lp.eq_A, np.zeros((lp.eq_A.shape[0], nmu + 1))])
        lamA = np.hstack([lp.lam_A, np.zeros((lp.lam_A.shape[0], nmu + 1))])
        faceA = np.hstack([lp.face_Az, lp.face_Amu,
                           -np.ones((lp.face_Az.shape[0], 1))])
        A = csc_matrix(np.vstack([eqA, lamA, faceA]))
        rlo = np.concatenate([lp.eq_b, -lp.lam_b, -lp.face_b])
        rhi = np.concatenate([lp.eq_b,
                              np.full(lp.lam_A.shape[0], inf),
                              np.full(lp.face_Az.shape[0], inf)])
        c = np.zeros(nv); c[-1] = -1.0         # minimize -t == maximize t
        col_lo = np.array([-inf] * nz + [0.0] * nmu + [-inf])
        col_hi = np.array([inf] * nv)

        m = hp.HighsLp()
        m.num_col_, m.num_row_ = nv, A.shape[0]
        m.col_cost_ = c
        m.col_lower_, m.col_upper_ = col_lo, col_hi
        m.row_lower_, m.row_upper_ = rlo, rhi
        m.a_matrix_.format_ = hp.MatrixFormat.kColwise
        m.a_matrix_.start_ = A.indptr.astype(np.int32)
        m.a_matrix_.index_ = A.indices.astype(np.int32)
        m.a_matrix_.value_ = A.data
        return m, nz, nmu

    def solve(self, lp: WitnessLP) -> LPResult:
        import numpy as np
        try:
            m, nz, nmu = self._model(lp)
            h = self._solver()
            h.passModel(m)
            h.run()
            status = h.getModelStatus()
            if h.modelStatusToString(status) != "Optimal":
                return LPResult(None, h.modelStatusToString(status),
                                basis=lp.basis, K=lp.K, dim=lp.dim)
            sol = h.getSolution()
            x = np.asarray(sol.col_value, dtype=float)
        except Exception:  # noqa: BLE001 - any solver failure is UNDECIDED, not a crash
            return LPResult(None, "error", basis=lp.basis, K=lp.K, dim=lp.dim)
        return LPResult(float(x[-1]), "optimal",
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


def _tensor_depends(t: np.ndarray, axis: int) -> bool:
    """``True`` iff ``t`` has a nonzero coefficient with a positive exponent on ``axis``."""
    sl = [slice(None)] * t.ndim
    sl[axis] = slice(1, None)
    return bool(np.any(t[tuple(sl)] != 0))


def _project_tensor(t: np.ndarray, active, n_full: int) -> np.ndarray:
    """Drop the PASSIVE axes of a coefficient tensor that is constant along them.

    Used by the active-dimension LP reduction (A18): ``phi`` / ``N_k`` / ``D`` do not
    depend on the passive joints, so they are constant along those axes (only their
    exponent-0 slice is nonzero). Slicing that slice yields the same polynomial over the
    active axes. Refuses to drop an axis the tensor actually varies on (would silently
    discard a real term — a soundness trap), so a mis-classified axis fails loudly here
    rather than producing a quietly-wrong LP."""
    for i in range(n_full):
        if i not in active and _tensor_depends(t, i):
            raise ValueError(f"witness: axis {i} declared passive but the polynomial "
                             "depends on it (refusing an unsound projection)")
    idx = tuple(slice(None) if i in active else 0 for i in range(n_full))
    return t[idx]


def build_witness_lp(cell, verts_num, D, obstacle: Polytope,
                     phi=None, delta=None, lam_degree: str = "affine",
                     _putinar_sign: int = -1, active_dims=None) -> WitnessLP:
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
    active_dims : optional tuple of the axes the geometry/barrier actually depend on
        (session S8, annotation A18). When the problem has PASSIVE joints (``phi`` and the
        moving body are constant along them), passing the active axes builds the LP in the
        reduced ``k = len(active_dims)`` dimensions: the Bernstein blocks shrink from
        ``(d+1)^n`` to ``(d+1)^k`` rows — the core of the passive-dimension optimisation.
        The reduced LP's feasible set is a subset of the full one (λ forced constant along
        passive axes), so its margin ``t`` is a SOUND lower bound of the full margin
        (``t_reduced <= t_full``): a reduced "collision" is a fortiori a full collision,
        never the reverse. The exact verifier (:mod:`cnp.verify`) re-checks the FINAL
        certificate at FULL dimension regardless, so this only ever speeds the search.
        ``None`` (default) ⇒ full dimension (unchanged S2 behaviour).
    _putinar_sign : TEST-ONLY. -1 (default, SOUND) builds ``g - mu*T``; +1 builds the
        UNSOUND ``g + mu*T``. Frozen by tests/test_witness.py (CLAUDE.md rule 2).
    """
    assert _putinar_sign in (-1, +1)
    n_full = len(cell)
    if active_dims is not None and len(active_dims) < n_full:
        active = tuple(active_dims)
        cell = [cell[i] for i in active]
        D = _project_tensor(D, active, n_full)
        verts_num = [[_project_tensor(c, active, n_full) for c in v] for v in verts_num]
        if phi is not None:
            phi = _project_tensor(phi, active, n_full)
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
