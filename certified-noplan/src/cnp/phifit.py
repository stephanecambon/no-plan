"""phifit — barrier ``phi`` pipeline (session S5, SPEC §5 of the plan).

Turns a *collision oracle* (a seeded predicate over configuration space) into a
polynomial barrier ``phi`` of degree <= 2 per variable and a slab half-width
``delta``, such that:

  * condition (i): ``phi(s_start) < -delta`` and ``phi(s_goal) > +delta`` (the two
    configurations sit on opposite sides of the slab);
  * the slab ``{|phi| <= delta}`` straddles the colliding region that separates
    them, so the branch-and-bound can certify the disconnection.

Pipeline (one ``fit_barrier`` call):
  1. SAMPLE the s-box uniformly (seeded) and label each point free / colliding via
     the oracle (``q = q* + 2 arctan(s)``);
  2. FIT ``phi``: either a linear SVM in the degree-<=2 monomial feature space that
     separates start-side-free from goal-side-free points (its decision function is
     a polynomial barrier through the obstacle), or a signed-target least-squares
     fit (the E4 recipe). Both yield a ``(degree+1)**n`` coefficient tensor;
  3. SELECT ``delta`` from a low quantile of ``|phi|`` over the free samples
     (keep free space out of the slab) capped by condition (i);
  4. RATIONALISE ``phi``, ``delta`` to exact fractions and re-assert (i) exactly;
  5. PROPOSE -> CERTIFY -> REFINE: build the engine problem, solve; on a PROOF we
     are done, on UNDECIDED we *penalise* free samples that fall inside the failed
     cells (push the barrier away from that free space) and refit, up to a budget.

The sampling NEVER proves anything (CLAUDE.md rule 9: the grid misses micro-canals);
it only proposes a candidate barrier. The branch-and-bound + exact verifier are the
sole arbiters of soundness. ``phifit`` shares only :mod:`cnp.polylin` / engine with
the rest of cnp and takes the collision oracle and the problem builder as callables,
so it stays robot-agnostic (planar full-verify path and spatial engine-PROOF path
use the same code).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from fractions import Fraction

import numpy as np

from . import engine, polylin


# --------------------------------------------------------------------------- #
# Result container
# --------------------------------------------------------------------------- #

@dataclass
class FitResult:
    """A fitted barrier and the outcome of the certify/refine loop."""

    phi: dict                       # {exponent-tuple: Fraction} rationalised barrier
    phi_degree: int                 # per-variable degree (2)
    delta: Fraction                 # slab half-width (exact, > 0)
    phi_float: np.ndarray           # dense float tensor (figures / diagnostics)
    delta_float: float
    samples: np.ndarray             # (m, n) s-space samples
    labels: np.ndarray              # (m,) 1 = colliding, 0 = free
    attempts: int                   # number of fit iterations run
    method: str
    verdict: str | None = None      # engine verdict, if a build_problem was given
    result: engine.EngineResult | None = field(default=None, repr=False)


# --------------------------------------------------------------------------- #
# Sampling
# --------------------------------------------------------------------------- #

def sample_box(collision, box, n_samples: int, seed: int):
    """Seeded uniform sampling of the s-box; returns ``(S, y)`` with ``y[i]=1`` when
    ``collision(S[i])`` is true. ``collision`` takes an s-vector (numpy array)."""
    rng = np.random.default_rng(seed)
    lo = np.array([float(l) for l, _ in box])
    hi = np.array([float(h) for _, h in box])
    S = rng.uniform(lo, hi, size=(n_samples, len(box)))
    y = np.array([1.0 if collision(s) else 0.0 for s in S])
    return S, y


# --------------------------------------------------------------------------- #
# Polynomial feature basis (degree <= `degree` per variable, dense tensor order)
# --------------------------------------------------------------------------- #

def _expos(n: int, degree: int) -> list:
    return [e for e in itertools.product(range(degree + 1), repeat=n)]


def _features(S: np.ndarray, expos: list) -> np.ndarray:
    """Design matrix: column j is the monomial ``prod_i s_i**expos[j][i]``."""
    cols = []
    for e in expos:
        col = np.ones(S.shape[0])
        for i, p in enumerate(e):
            if p:
                col = col * S[:, i] ** p
        cols.append(col)
    return np.stack(cols, axis=1)


def _tensor_from_weights(w: np.ndarray, expos: list, n: int, degree: int) -> np.ndarray:
    t = polylin.zeros(n, degree)
    for c, e in zip(w, expos):
        t[tuple(e)] += float(c)
    return t


def _direction(start_s, goal_s):
    """Unit start->goal direction and the start/goal midpoint (signed-side reference)."""
    a = np.array([float(x) for x in start_s])
    b = np.array([float(x) for x in goal_s])
    d = b - a
    nrm = np.linalg.norm(d)
    if nrm == 0:
        raise ValueError("start and goal map to the same s-point; cannot orient phi")
    return d / nrm, 0.5 * (a + b)


# --------------------------------------------------------------------------- #
# Fits (both return a dense float phi tensor)
# --------------------------------------------------------------------------- #

def fit_phi_lstsq(S, y, start_s, goal_s, degree, weights=None) -> np.ndarray:
    """Signed-target least squares (the E4 recipe, generalised to n-dim): free points
    target the side they sit on (+/-1 along the start->goal direction), colliding
    points target 0, so the fitted ``phi`` crosses zero inside the obstacle."""
    n = S.shape[1]
    expos = _expos(n, degree)
    d, mid = _direction(start_s, goal_s)
    side = np.sign((S - mid) @ d)
    tgt = side * (1.0 - y)
    F = _features(S, expos)
    if weights is not None:
        sw = np.sqrt(weights)[:, None]
        F, tgt = F * sw, tgt * sw[:, 0]
    w, *_ = np.linalg.lstsq(F, tgt, rcond=None)
    return _tensor_from_weights(w, expos, n, degree)


def fit_phi_svm(S, y, start_s, goal_s, degree, weights=None, C=10.0) -> np.ndarray:
    """Linear SVM in the degree-<=2 monomial feature space, trained on the FREE
    samples labelled by side (start-side vs goal-side). Its decision function is a
    polynomial barrier whose zero-set lies in the colliding gap between the two."""
    from sklearn.svm import LinearSVC

    n = S.shape[1]
    expos = _expos(n, degree)
    d, mid = _direction(start_s, goal_s)
    free = y == 0
    side = np.sign((S[free] - mid) @ d)
    keep = side != 0
    Xf = _features(S[free][keep], expos)
    lab = side[keep]
    # drop the constant column: LinearSVC carries its own intercept.
    const_col = expos.index(tuple([0] * n))
    cols = [j for j in range(len(expos)) if j != const_col]
    sw = weights[free][keep] if weights is not None else None
    clf = LinearSVC(C=C, max_iter=20000)
    clf.fit(Xf[:, cols], lab, sample_weight=sw)
    w = np.zeros(len(expos))
    w[cols] = clf.coef_[0]
    w[const_col] = float(clf.intercept_[0])
    return _tensor_from_weights(w, expos, n, degree)


# --------------------------------------------------------------------------- #
# delta selection + rationalisation
# --------------------------------------------------------------------------- #

def _phi_eval_float(phi_t: np.ndarray, s) -> float:
    return float(polylin.teval(phi_t, np.asarray(s, dtype=float)))


def select_delta(phi_t, S, y, start_s, goal_s, quantile=0.02, safety=0.5) -> float:
    """Choose the slab half-width. The free samples sit at ``|phi| >= margin`` where
    ``margin`` is a low quantile of ``|phi|`` over free points (the nearest free
    sample to the slab centre); the colliding region overlaps that band, so the slab
    must be a FRACTION (``safety``) of ``margin`` to leave room for free space the grid
    missed (CLAUDE.md rule 9 micro-canal). Capped by half the condition-(i) bound so
    start/goal stay strictly on opposite sides. Returns 0.0 if (i) is infeasible."""
    bound = min(-_phi_eval_float(phi_t, start_s), _phi_eval_float(phi_t, goal_s))
    if bound <= 0:
        return 0.0
    free_vals = np.abs(_features_eval(phi_t, S[y == 0]))
    margin = float(np.quantile(free_vals, quantile)) if free_vals.size else bound
    return max(0.0, min(safety * margin, 0.5 * bound))


def _features_eval(phi_t: np.ndarray, S: np.ndarray) -> np.ndarray:
    """Vectorised phi at every row of S."""
    if S.shape[0] == 0:
        return np.zeros(0)
    return np.array([_phi_eval_float(phi_t, s) for s in S])


def _phi_eval_exact(phi: dict, s) -> Fraction:
    acc = Fraction(0)
    for e, c in phi.items():
        term = c
        for i, p in enumerate(e):
            if p:
                term *= s[i] ** p
        acc += term
    return acc


def rationalise(phi_t: np.ndarray, delta_f: float, start_s, goal_s,
                den: int = 10 ** 6) -> tuple:
    """Round ``phi`` and ``delta`` to exact fractions, then re-assert condition (i)
    in EXACT arithmetic, shrinking delta to a strict fraction of the exact bound if
    rounding nudged it. Returns ``(phi_dict, delta_Fraction)`` or ``(phi_dict, 0)``
    if (i) cannot hold exactly (caller refits)."""
    phi = {}
    for e in np.argwhere(np.abs(phi_t) > 1e-12):
        e = tuple(int(x) for x in e)
        phi[e] = Fraction(float(phi_t[e])).limit_denominator(den)
    ss = [Fraction(x) for x in start_s]
    gs = [Fraction(x) for x in goal_s]
    bound = min(-_phi_eval_exact(phi, ss), _phi_eval_exact(phi, gs))
    if bound <= 0:
        return phi, Fraction(0)
    delta = Fraction(delta_f).limit_denominator(den)
    if delta <= 0 or delta >= bound:
        delta = bound / 2
    return phi, delta


# --------------------------------------------------------------------------- #
# The pipeline: sample -> fit -> select delta -> certify -> refine
# --------------------------------------------------------------------------- #

def fit_barrier(collision, box, start_s, goal_s, build_problem=None, *,
                method: str = "svm", degree: int = 2, n_samples: int = 4000,
                seed: int = 0, den: int = 10 ** 6, quantile: float = 0.02,
                max_retries: int = 4, penalty: float = 8.0,
                solve_kw: dict | None = None) -> FitResult:
    """Fit a certifiable barrier for ``collision`` over ``box``.

    ``build_problem(phi_dict, phi_degree, delta) -> engine.Problem`` is the only
    robot-specific hook: it embeds the rational barrier into the scene geometry. If
    ``None``, a single fit is returned without solving (for figures / inspection).
    On UNDECIDED, free samples inside the failed cells get their weight multiplied by
    ``penalty`` and the barrier is refit (push it off that free space)."""
    if method not in ("svm", "lstsq"):
        raise ValueError(f"unknown fit method {method!r}")
    fit = fit_phi_svm if method == "svm" else fit_phi_lstsq
    S, y = sample_box(collision, box, n_samples, seed)
    weights = np.ones(S.shape[0])
    solve_kw = dict(solve_kw or {})
    safety = 0.5  # slab as a fraction of the free margin; shrinks on UNDECIDED

    last = None
    for attempt in range(1, max_retries + 1):
        phi_t = fit(S, y, start_s, goal_s, degree, weights=weights)
        delta_f = select_delta(phi_t, S, y, start_s, goal_s, quantile, safety)
        phi, delta = rationalise(phi_t, delta_f, start_s, goal_s, den)
        last = FitResult(phi=phi, phi_degree=degree, delta=delta, phi_float=phi_t,
                         delta_float=delta_f, samples=S, labels=y, attempts=attempt,
                         method=method)
        if delta <= 0:
            _repenalise_side_errors(weights, phi_t, S, y, start_s, goal_s, penalty)
            continue
        if build_problem is None:
            return last
        problem = build_problem(phi, degree, delta)
        result = engine.solve(problem, **solve_kw)
        last.verdict, last.result = result.verdict, result
        if result.verdict == "PROOF":
            return last
        # UNDECIDED: the slab covered free space. Push the barrier off that free space
        # (re-weight) AND thin the slab (it is the easiest knob toward slab ⊆ collision).
        _repenalise_failed_cells(weights, S, y, result.failed, penalty)
        safety *= 0.5
    return last


def _repenalise_failed_cells(weights, S, y, failed, penalty):
    """Bump the weight of FREE samples sitting inside any failed (uncertified) cell —
    the next fit pushes the barrier off the free space the slab was wrongly covering."""
    if not failed:
        return
    for cell in failed:
        lo = np.array([float(c[0]) for c in cell])
        hi = np.array([float(c[1]) for c in cell])
        inside = np.all((S >= lo) & (S <= hi), axis=1) & (y == 0)
        weights[inside] *= penalty


def _repenalise_side_errors(weights, phi_t, S, y, start_s, goal_s, penalty):
    """Fallback when condition (i) failed: emphasise free samples whose fitted sign
    disagrees with their geometric side, so the next fit orients phi correctly."""
    d, mid = _direction(start_s, goal_s)
    side = np.sign((S - mid) @ d)
    vals = _features_eval(phi_t, S)
    wrong = (np.sign(vals) != side) & (y == 0)
    weights[wrong] *= penalty
