"""engine — n-dimensional branch-and-bound over the joint-limit box (session S3).

The per-leaf, per-pair certifier is :mod:`cnp.witness` (S2); this module is the
branch-and-bound that drives it over a binary partition of the s-box ``P`` and
assembles the global disconnection certificate of SPEC §2.

Reference flow (CLAUDE.md S3, task 1). The control flow generalises, to ``n``
dimensions and to a *list of (link, obstacle) pairs*, the frozen 2-D flow of the
regression oracle (``tests/regref.certify_slab``) that the S2 scaffold
(``tests/test_witness._bb_witness``) already reproduces leaf-for-leaf:

* a cell is a leaf ``outside`` when the slab ``T = delta^2 - phi^2`` cannot be
  positive on it (Bernstein bound of ``phi``: ``min >= delta`` or ``max <= -delta``);
* otherwise every pair is certified by the witness LP; the cell is a ``collision``
  leaf if the best margin ``t* > tol``;
* otherwise the cell is split on one axis and recursed; depth exhaustion is a
  ``FAIL`` leaf, budget exhaustion an ``undecided`` leaf.  Either ⇒ verdict
  ``UNDECIDED`` (never "infeasible": SPEC §1, CLAUDE.md rule 6).

Axis heuristic (CLAUDE.md S3): **slab boundary first** — if splitting some axis
puts a whole child outside the slab, take it (this is what makes the relay cheap and
reproduces the oracle).  Fallback: ``axis="oracle"`` takes the widest axis (the
oracle's choice, ⇒ identical E3/E4 partition); ``axis="margin"`` takes the
**worst LP-margin axis** of the failing cell (the axis on which the most-binding
Bernstein control point of the best pair sits furthest from centre — splitting
there tightens that bound the most).  The heuristic only ever changes *cost*, never
soundness (CLAUDE.md rule 9: depth = a cost parameter, not a feasibility one).

Parallelism (multiprocessing over leaves), checkpoint/resume on disk and budgets
are layered on top of the same recursion without changing the partition: the top of
the tree is expanded serially down to a *frontier* of still-undecided cells, and
each frontier subtree is solved independently (in a worker, and/or restored from a
checkpoint).  Same heuristic above and below the frontier ⇒ the parallel/resumed
certificate is identical to the serial one.

Soundness (CLAUDE.md rule 1): nothing here can turn a refusal into a proof — the LP
sign is frozen in :mod:`cnp.witness`; the engine only *partitions*.  The shared
kernel with the rest of cnp is :mod:`cnp.polylin` (Bernstein) and :mod:`cnp.witness`.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from multiprocessing import get_context

import numpy as np

from .polylin import bernstein_coeffs
from .witness import (Polytope, LPBackend, HighsBackend, HighspyBackend,  # noqa: F401
                      build_witness_lp)

# The engine's default LP back-end is DIRECT HiGHS via highspy (session S8): Mosek-free
# (CLAUDE.md rule 3 — importing cvxpy transitively wakes the Drake-bundled mosek), and
# the fastest of the three (no per-solve cvxpy canonicalisation, no scipy repacking — a
# reused Highs instance). t* agrees with CLARABEL / scipy-HiGHS to < 1e-6 and no leaf
# flips at tol (frozen in tests/test_witness.py). Through S7 the default was scipy-HiGHS
# (HighsBackend); both remain available. Pass ``backend=`` to override (CvxpyBackend for
# a cross-check).
ENGINE_BACKEND = HighspyBackend()

Cell = tuple  # tuple of (lo, hi) pairs, one per s-variable


# --------------------------------------------------------------------------- #
# Problem / budget / result data
# --------------------------------------------------------------------------- #

@dataclass
class Pair:
    """A candidate colliding pair: a moving convex body (rational-FK vertex
    numerators ``verts_num`` over the common denominator ``D``) against a static
    obstacle ``Polytope`` (H-rep).  ``name`` labels the leaf in the certificate."""

    name: str
    verts_num: list
    D: np.ndarray
    obstacle: Polytope


@dataclass
class Problem:
    """A disconnection sub-problem over the s-box ``box``.

    ``phi``/``delta`` define the slab; ``pairs`` are the (link, obstacle) candidates
    relayed across it; ``lam_degree`` is the witness multiplier degree (SPEC §2)."""

    box: list
    phi: np.ndarray
    delta: float
    pairs: list
    lam_degree: str = "affine"
    tol: float = 1e-6
    max_depth: int = 16

    @property
    def n(self) -> int:
        return len(self.box)


@dataclass
class Budget:
    """Stop refining when any limit is hit ⇒ the run is ``UNDECIDED`` with the
    still-open cells exported for diagnosis.  ``None`` = unlimited."""

    max_leaves: int | None = None
    max_time_s: float | None = None


@dataclass
class Leaf:
    cell: list
    status: str               # 'outside' | 'collision' | 'FAIL' | 'undecided'
    pair: str | None = None
    margin: float | None = None


@dataclass
class EngineResult:
    verdict: str              # 'PROOF' | 'UNDECIDED'
    leaves: list
    failed: list              # cells left undecided (FAIL or budget) — diagnostics
    stats: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.verdict == "PROOF"

    def counts(self) -> dict:
        """Per-status and per-pair leaf counts (figure / journal friendly)."""
        by_status, by_pair = {}, {}
        for lf in self.leaves:
            by_status[lf.status] = by_status.get(lf.status, 0) + 1
            if lf.status == "collision":
                by_pair[lf.pair] = by_pair.get(lf.pair, 0) + 1
        return {"status": by_status, "pair": by_pair, "n_leaves": len(self.leaves)}


# --------------------------------------------------------------------------- #
# Geometry helpers
# --------------------------------------------------------------------------- #

def cell_outside_slab(cell, phi, delta) -> bool:
    """``True`` when the slab ``|phi| <= delta`` cannot meet ``cell`` (Bernstein
    bound of ``phi`` over the cell is entirely above ``+delta`` or below ``-delta``).
    Identical test to the frozen oracle, re-expressed via :mod:`cnp.polylin`."""
    bc = bernstein_coeffs(phi, [tuple(c) for c in cell])
    return bool(bc.min() >= delta or bc.max() <= -delta)


def _widths(cell):
    return [hi - lo for (lo, hi) in cell]


# --------------------------------------------------------------------------- #
# Passive dimensions (S8, task #1 / annotation A18)
# --------------------------------------------------------------------------- #
#
# A dimension ``i`` is PASSIVE when neither the barrier ``phi`` nor any pair's moving
# geometry (vertex numerators + common denominator) depends on ``s_i``: the polynomials
# the per-cell certifier evaluates (the slab ``T = delta^2 - phi^2`` and every face
# ``g_j = b_j D - a_j^T X``) are then CONSTANT along axis ``i``.  Two consequences:
#
#   * splitting a passive axis can never change a cell's verdict — the outside test and
#     the witness LP give the IDENTICAL result on a child as on the parent (same
#     Bernstein coefficients), so a passive split only wastes depth.  This is exactly
#     the S6 comb blow-up: ``axis="oracle"`` (widest axis) keeps bisecting the passive
#     distal joint (736 leaves / UNDECIDED) where ``axis="margin"`` already avoided it
#     (54 leaves).  The fix is to certify each leaf over the passive dim's FULL interval
#     and never branch on it — "passive dimensions by intervals" (A18).
#
# Soundness (CLAUDE.md rule 1): excluding an axis from branching only COARSENS the
# partition.  Each leaf is still certified independently over its full box (the LP and
# the outside test are unchanged — same dimension, same margin ``t``), so a coarser
# partition can never turn a refusal into a proof; at worst it leaves a cell UNDECIDED.
# Mis-detecting an ACTIVE axis as passive is therefore a cost bug, never a soundness
# one.  The exact verifier reconstructs the cover from whatever midpoint bisections
# actually happened (verify ``_verify_cover``), so a passive-aware partition needs no
# verifier change.  The branch is still always re-validated by the adversarial suite.
#
# RATIONAL passivity (S9, annotation A29). The plain tensor test below misses a joint
# that is GEOMETRICALLY passive but whose ``(1 + s_i^2)`` denominator factor the common
# per-link denominator still carries on BOTH the numerators and ``D`` (the S3 roll: a
# joint about the upper arm's own axis does not move it, yet ``D = prod (1 + s_j^2)``
# over the unlocked chain to the body keeps an ``(1 + s_i^2)`` factor, and each numerator
# ``N_k = x_world * D`` carries it too).  Since ``x = N_k / D`` is unchanged by dividing
# numerator AND denominator by the SAME positive factor ``(1 + s_i^2)``, we divide it out
# exactly when it is present in D and EVERY numerator component (:func:`_simplify_geometry`),
# exposing the joint as plainly passive.  This is an exact, geometry-preserving rewrite of
# the DECISION-path geometry only; the certificate is re-solved from the full unsimplified
# FK (certificate.py) and the exact verifier re-derives FK independently, so a mis-division
# could at worst cost a leaf, never forge a PROOF.
#
# PER-PAIR reduction (S9, annotation A30 — the G2' lever).  Passivity is a property of the
# PAIR, not of the whole problem: for a pair on link ``k`` every joint downstream of ``k``
# is passive FOR THAT pair's LP (it does not move link ``k``'s body).  So each pair's leaf
# LP is reduced to ITS OWN active axes (:class:`_PairView`), which is in general a STRICTER
# reduction than the global one — a proximal pair on a long chain sees ``(d+1)^2`` rows
# where the global active set would keep ``(d+1)^n``.  Branching still happens on the GLOBAL
# active set (the union of the pairs' active axes), so the partition is unchanged; only the
# per-pair LP shrinks.  Same soundness architecture as S8 (decision-path only).

def _tensor_depends(t: np.ndarray, axis: int) -> bool:
    """``True`` iff the coefficient tensor ``t`` has a nonzero coefficient with a
    positive exponent on ``axis`` (i.e. the polynomial actually varies along ``s_axis``)."""
    sl = [slice(None)] * t.ndim
    sl[axis] = slice(1, None)
    return bool(np.any(t[tuple(sl)] != 0))


# Float dust tolerance for the exact ``(1 + s_i^2)`` factor test. The two slices are
# produced by the same tensor multiply (``_factor(..., "one")`` = coefficients [1, 0, 1]),
# so they are bit-identical in practice; the tiny atol only guards FK conversion dust. A
# false negative just forgoes a cost win; a false positive is caught by the exact verifier.
_FACTOR_TOL = 1e-12


def _divide_out_one_plus_s2(t: np.ndarray, axis: int):
    """If ``(1 + s_axis^2)`` divides tensor ``t`` with an ``s_axis``-independent quotient,
    return that quotient (axis collapsed to degree 0); else ``None`` (A29).

    ``t = (1 + s_axis^2) * M`` with ``M`` free of ``s_axis`` iff, slicing along ``axis``,
    the exponent-1 slice is zero and the exponent-0 and exponent-2 slices are equal (then
    ``M`` = the exponent-0 slice).  Tensors here are degree <= 2 per variable, so a present
    factor leaves the quotient at degree 0 on that axis."""
    e0 = np.take(t, 0, axis=axis)
    e1 = np.take(t, 1, axis=axis)
    e2 = np.take(t, 2, axis=axis)
    if np.any(e1 != 0.0) or not np.allclose(e0, e2, rtol=0.0, atol=_FACTOR_TOL):
        return None
    out = np.zeros_like(t)
    sl = [slice(None)] * t.ndim
    sl[axis] = 0
    out[tuple(sl)] = e0
    return out


def _simplify_geometry(verts_num, D, n: int):
    """A29: divide out every ``(1 + s_i^2)`` factor common to ``D`` AND all vertex-numerator
    components.  Returns ``(verts', D', removed_axes)`` representing the SAME world point
    ``x = N/D`` (we divide numerator and denominator by the same positive factor), but whose
    tensors no longer carry the removable factor — so a rationally-passive joint becomes
    detectable by :func:`_tensor_depends`."""
    removed = []
    D2 = D
    verts2 = [[c for c in v] for v in verts_num]
    for i in range(n):
        if not _tensor_depends(D2, i):
            continue                       # already independent of s_i (plainly passive)
        qD = _divide_out_one_plus_s2(D2, i)
        if qD is None:
            continue                       # factor not present in D ⇒ genuinely active
        qverts, ok = [], True
        for v in verts2:
            row = []
            for c in v:
                qc = _divide_out_one_plus_s2(c, i)
                if qc is None:
                    ok = False
                    break
                row.append(qc)
            if not ok:
                break
            qverts.append(row)
        if ok:                             # factor common to D and every numerator: divide
            D2, verts2 = qD, qverts
            removed.append(i)
    return verts2, D2, tuple(removed)


@dataclass
class _PairView:
    """A pair's DECISION-path view: its (A29-simplified) geometry and its OWN active axes
    (the axes ``phi`` or this pair's body depends on).  The leaf LP for this pair is reduced
    to ``active`` (A30); the certificate is still re-solved at full dim from the scene FK."""

    pair: Pair
    verts_num: list
    D: np.ndarray
    active: tuple


def _geom_passive(phi: np.ndarray, verts_num, D, n: int) -> tuple:
    """Axes neither ``phi`` nor this (already-simplified) geometry depends on."""
    passive = []
    for i in range(n):
        if _tensor_depends(phi, i) or _tensor_depends(D, i):
            continue
        if any(_tensor_depends(c, i) for v in verts_num for c in v):
            continue
        passive.append(i)
    return tuple(passive)


def pair_views(problem: Problem) -> list:
    """Per-pair decision views (A29 simplification + A30 per-pair active axes)."""
    n = problem.n
    views = []
    for pr in problem.pairs:
        verts, D, _removed = _simplify_geometry(pr.verts_num, pr.D, n)
        passive = set(_geom_passive(problem.phi, verts, D, n))
        active = tuple(i for i in range(n) if i not in passive)
        views.append(_PairView(pr, verts, D, active))
    return views


def _global_active(views, problem: Problem) -> tuple:
    """The axes to BRANCH on = the union of the pairs' active axes (A30 keeps branching on
    the union so the partition is unchanged; only the per-pair LP shrinks)."""
    if not views:
        return tuple(i for i in range(problem.n) if _tensor_depends(problem.phi, i))
    active: set = set()
    for view in views:
        active.update(view.active)
    return tuple(sorted(active))


def passive_dims(problem: Problem) -> tuple:
    """The axes the problem does not depend on — neither ``phi`` nor ANY pair's geometry,
    A29-simplified (so the S3 roll, hidden behind its ``(1+s²)`` denominator factor, now
    counts as passive).  A dim is globally passive iff it is passive for EVERY pair."""
    n = problem.n
    views = pair_views(problem)
    if not views:                          # degenerate (no pairs): only phi separates
        return tuple(i for i in range(n) if not _tensor_depends(problem.phi, i))
    passive = set(range(n))
    for view in views:
        passive &= set(i for i in range(n) if i not in view.active)
    return tuple(sorted(passive))


@dataclass
class EmbeddingCheck:
    """[L6, S12] Whether one pair's REDUCED witness may be EMBEDDED in full dimension
    instead of being re-solved there (:mod:`cnp.certificate`).

    ``applicable`` is the run-time answer for THIS pair on THIS problem — never presumed,
    never cached across scenes.  ``reason`` says why in one line (it is journalled and
    surfaced by the CLI)."""

    pair: str
    active: tuple
    passive: tuple
    a29_removed: tuple      # axes A29 had to divide a (1+s^2) factor out of  ⇒ blocks (i)
    blocking: tuple         # passive axes STILL present in the ORIGINAL D / N_k / phi ⇒ (ii)
    applicable: bool
    reason: str


def embedding_applicable(problem: Problem) -> dict:
    """[L6, S12] Per-pair run-time test: is the DIRECT EMBEDDING of the reduced witness
    SOUND for this pair?  Returns ``{pair_name: EmbeddingCheck}``.

    The decision path solves each leaf LP on the pair's A29-simplified geometry, reduced to
    the pair's own active axes (A30).  Exporting that witness *as is* — its lambda tensors
    read as full-dimensional polynomials with ZERO exponents on the passive axes — is only
    legitimate when the reduced problem IS the full problem restricted, i.e. when the full
    polynomials are genuinely CONSTANT along the passive axes of the ORIGINAL geometry:

      (i)  **A29 divided nothing** for this pair (``a29_removed == ()``).  When A29 had to
           divide a ``(1 + s_i^2)`` factor out of ``D`` and every numerator to expose the
           passivity, the reduced geometry is the original one divided by ``P(s) > 0``
           (``D_full = P * D_reduced``) while the slab tensor ``T = delta^2 - phi^2`` is NOT
           divided — so ``g - mu*T`` at full dimension is a DIFFERENT polynomial and the
           embedded multipliers do not certify it.  Re-resolution stays mandatory.
      (ii) Every passive axis of the pair's view is **absent from the ORIGINAL tensors**:
           the raw ``D``, every raw vertex numerator ``N_k[i]``, and ``phi``.  This is the
           EXACT tensor test on the pre-simplification tensors, not the conservative
           detection used to pick active axes.

    Under (i) and (ii) the full-dimensional Bernstein coefficients of every product are the
    reduced ones replicated along the passive axes, so a reduced certificate is a full one.

    Soundness does not RELY on this test: :mod:`cnp.verify` re-checks the exported
    certificate at full dimension with no shared code, so a wrong embedding is REJECTED
    (verdict falls back to ENGINE-PROOF / UNDECIDED), never turned into a false PROOF — the
    S8 argument.  The test is what keeps that rejection from ever happening in practice, and
    :mod:`cnp.certificate` counts every rejection loudly (A32 extended)."""
    n = problem.n
    views = {v.pair.name: v for v in pair_views(problem)}
    out = {}
    for pr in problem.pairs:
        _v, _D, removed = _simplify_geometry(pr.verts_num, pr.D, n)
        view = views[pr.name]
        passive = tuple(i for i in range(n) if i not in view.active)
        blocking = tuple(
            i for i in passive
            if _tensor_depends(pr.D, i)
            or any(_tensor_depends(c, i) for v in pr.verts_num for c in v)
            or _tensor_depends(problem.phi, i))
        applicable = (not removed) and (not blocking)
        if removed:
            reason = (f"A29 divided (1+s^2) on axes {removed} ⇒ the reduced geometry is the "
                      f"original divided by a positive factor the slab T does not carry; "
                      f"full-dim re-resolution required")
        elif blocking:
            reason = (f"passive axes {blocking} still occur in the ORIGINAL D / numerators / "
                      f"phi ⇒ the full polynomial is not constant along them; full-dim "
                      f"re-resolution required")
        elif not passive:
            reason = "no passive axis: the reduced LP already IS the full-dim LP"
        else:
            reason = (f"passive axes {passive} absent from the ORIGINAL D, numerators and "
                      f"phi, and A29 divided nothing ⇒ direct embedding is exact")
        out[pr.name] = EmbeddingCheck(pr.name, view.active, passive, removed, blocking,
                                      applicable, reason)
    return out


def active_axes(problem: Problem) -> tuple:
    """The axes worth BRANCHING on = all dims minus :func:`passive_dims` (= the union of the
    pairs' active axes; always non-empty for a real disconnection: ``phi`` separates start
    from goal on >= 1 axis)."""
    passive = set(passive_dims(problem))
    return tuple(i for i in range(problem.n) if i not in passive)


def _split(cell, axis):
    """Bisect ``cell`` on ``axis`` at its midpoint → (lower, upper) children."""
    mid = 0.5 * (cell[axis][0] + cell[axis][1])
    c1 = [list(c) for c in cell]
    c2 = [list(c) for c in cell]
    c1[axis][1] = mid
    c2[axis][0] = mid
    return tuple(tuple(c) for c in c1), tuple(tuple(c) for c in c2)


# --------------------------------------------------------------------------- #
# Per-cell certification (outside test + best pair)
# --------------------------------------------------------------------------- #

@dataclass
class _CellVerdict:
    status: str                         # 'outside' | 'collision' | 'undecided'
    pair: str | None = None
    margin: float | None = None


def _best_pair_margin(cell, problem: Problem, backend: LPBackend, views):
    """Best (largest) witness margin over all pair views on ``cell``; ``+inf`` if the cell
    is outside the slab (trivially certified), ``-inf`` if no pair returns a value.  Each
    view reduces its LP to ITS OWN active axes (A30) over its A29-simplified geometry."""
    if cell_outside_slab(cell, problem.phi, problem.delta):
        return float("inf"), None
    best_t, best_name = None, None
    for view in views:
        t = certify_cell_view_margin(cell, view, problem, backend)
        if t is not None and (best_t is None or t > best_t):
            best_t, best_name = t, view.pair.name
    return (best_t if best_t is not None else float("-inf")), best_name


def certify_cell_view_margin(cell, view: _PairView, problem: Problem, backend: LPBackend):
    """Witness margin ``t*`` of one (cell, pair view); ``None`` if the LP failed.  The LP is
    built from the view's A29-simplified geometry and reduced to the view's OWN active axes
    (A30) — Bernstein blocks shrink to ``(d+1)^{len(view.active)}`` rows.  The margin stays a
    sound lower bound and the final certificate is re-solved + verified at FULL dim."""
    lp = build_witness_lp(cell, view.verts_num, view.D, view.pair.obstacle,
                          phi=problem.phi, delta=problem.delta,
                          lam_degree=problem.lam_degree, active_dims=view.active)
    return backend.solve(lp).t


def _certify_cell(cell, problem: Problem, backend: LPBackend, views) -> _CellVerdict:
    """Decide one cell: outside / collision (best pair view) / undecided."""
    best_t, best_name = _best_pair_margin(cell, problem, backend, views)
    if best_t == float("inf"):
        return _CellVerdict("outside")
    if best_t == float("-inf"):
        return _CellVerdict("undecided")
    status = "collision" if best_t > problem.tol else "undecided"
    return _CellVerdict(status, best_name, best_t)


# --------------------------------------------------------------------------- #
# Axis heuristics
# --------------------------------------------------------------------------- #

def _slab_boundary_axis(cell, problem: Problem, active):
    """If splitting some axis makes a whole child fall outside the slab, return that
    axis (lowest such), else ``None``.  Same probe order as the frozen oracle. Restricted
    to ``active`` axes — a passive axis cannot move a child outside the slab anyway
    (``phi`` does not depend on it), so this only skips dead probes."""
    for ax in active:
        for child in _split(cell, ax):
            if cell_outside_slab(child, problem.phi, problem.delta):
                return ax
    return None


def _margin_axis(cell, problem: Problem, backend: LPBackend, active, views) -> int:
    """Worst-LP-margin axis of a failing cell: one-step lookahead toward the *relay*
    structure. For each axis, bisect and score the cut by the *best* child's best-pair
    margin; take the axis that maximises it — i.e. the cut that carves off one
    immediately-certifiable child (one obstacle of the relay) and leaves the rest to
    recurse. Bounded by construction (a productive cut, never a runaway), and it
    certifies E3/E4 with no FAIL leaf (journalled leaf counts may differ from the
    widest-axis oracle: that is the allowed deviation). Ties → widest axis, then
    lowest index. Restricted to the GLOBAL ``active`` axes (a passive split never improves
    the margin: same Bernstein bound on both children — A18); the child margins use the
    per-pair views (A30)."""
    widths = _widths(cell)
    scores = {}
    for ax in active:
        c1, c2 = _split(cell, ax)
        m1, _ = _best_pair_margin(c1, problem, backend, views)
        m2, _ = _best_pair_margin(c2, problem, backend, views)
        scores[ax] = max(m1, m2)
    return max(active, key=lambda i: (scores[i], widths[i], -i))


def _choose_axis(cell, problem: Problem, axis_mode: str,
                 backend: LPBackend, active, views) -> int:
    """Slab-boundary first; else the mode's fallback (widest / worst-margin), both
    restricted to the GLOBAL ``active`` axes so passive dims are kept as full intervals
    (A18); margin scoring uses the per-pair views (A30)."""
    ax = _slab_boundary_axis(cell, problem, active)
    if ax is not None:
        return ax
    if axis_mode == "margin":
        return _margin_axis(cell, problem, backend, active, views)
    widths = _widths(cell)               # "oracle": widest ACTIVE axis (lowest on tie)
    return max(active, key=lambda i: (widths[i], -i))


# --------------------------------------------------------------------------- #
# Serial recursion
# --------------------------------------------------------------------------- #

class _Ctx:
    """Mutable run state shared across the recursion (counters, deadline)."""

    def __init__(self, problem, budget, axis_mode, backend, start_depth):
        self.problem = problem
        self.budget = budget or Budget()
        self.axis_mode = axis_mode
        self.backend = backend
        self.views = pair_views(problem)     # per-pair simplified geometry + active (A29/A30)
        self.active = _global_active(self.views, problem)  # branch on the union (A18)
        self.start_depth = start_depth
        self.leaves: list[Leaf] = []
        self.failed: list = []
        self.deadline = (None if self.budget.max_time_s is None
                         else time.monotonic() + self.budget.max_time_s)
        self.n_lp = 0
        # S9f instrumentation (L0a, diagnostics only — never on the decision path):
        # which ceiling actually stopped the refinement, so an UNDECIDED can be told
        # apart as "budget" (the real wall) vs "depth_exhausted" (max_depth too low,
        # NOT the budget — the S9e k=5 case) vs "certified".
        self.max_depth_reached = start_depth
        self.budget_reason: str | None = None

    def budget_hit(self) -> bool:
        if self.budget.max_leaves is not None and len(self.leaves) >= self.budget.max_leaves:
            self.budget_reason = "budget_leaves"
            return True
        if self.deadline is not None and time.monotonic() >= self.deadline:
            self.budget_reason = "budget_time"
            return True
        return False

    def termination(self) -> str:
        """Why the serial refinement stopped (S9f, diagnostics): ``certified`` (no open
        cell), ``budget_leaves`` / ``budget_time`` (the genuine wall — budget spent), or
        ``depth_exhausted`` (cells hit ``max_depth`` while still undecided — a depth
        ceiling, NOT the budget; raising ``max_depth`` would refine further)."""
        if self.budget_reason is not None:
            return self.budget_reason
        if any(lf.status == "FAIL" for lf in self.leaves):
            return "depth_exhausted"
        return "certified"


def _recurse(ctx: _Ctx, cell, depth):
    """Process ``cell`` at ``depth``; append leaves. Returns ``True`` iff the whole
    subtree is certified (outside/collision everywhere)."""
    if depth > ctx.max_depth_reached:
        ctx.max_depth_reached = depth
    if ctx.budget_hit():
        ctx.failed.append(cell)
        ctx.leaves.append(Leaf(cell, "undecided"))
        return False
    v = _certify_cell(cell, ctx.problem, ctx.backend, ctx.views)
    ctx.n_lp += 0 if v.status == "outside" else len(ctx.problem.pairs)
    if v.status == "outside":
        ctx.leaves.append(Leaf(cell, "outside"))
        return True
    if v.status == "collision":
        ctx.leaves.append(Leaf(cell, "collision", v.pair, v.margin))
        return True
    if depth >= ctx.problem.max_depth:
        ctx.failed.append(cell)
        ctx.leaves.append(Leaf(cell, "FAIL", None, v.margin))
        return False
    axis = _choose_axis(cell, ctx.problem, ctx.axis_mode, ctx.backend, ctx.active, ctx.views)
    c1, c2 = _split(cell, axis)
    ok1 = _recurse(ctx, c1, depth + 1)
    ok2 = _recurse(ctx, c2, depth + 1)
    return ok1 and ok2


def _verdict(failed) -> str:
    return "UNDECIDED" if failed else "PROOF"


# --------------------------------------------------------------------------- #
# Frontier expansion (shared by parallel + checkpoint)
# --------------------------------------------------------------------------- #

def _uniform_frontier(box, depth, n):
    """Bisect ``box`` to ``depth`` (round-robin over axes) into ``2**depth``
    independent subcells — the parallel/checkpoint *frontier*.

    Unlike a heuristic cutoff, the parent does NO LP work here: every subcell is a
    self-contained sub-problem a worker certifies from scratch (outside regions
    collapse to a coarse leaf; collision/straddling cells recurse with the real
    heuristic from ``depth``). The union is a sound partition of ``box``. The forced
    top splits aren't heuristic-optimal, so the parallel partition has >= as many
    leaves as the serial one (a cost, never a soundness, difference); the exact 46/78
    oracle reproduction is the job of the serial ``axis="oracle"`` path. The frontier
    is deterministic ⇒ a resumed run reproduces the parallel certificate. (Round-robin
    beat a slab-tangent split, which re-isolated the slab in every column — wasteful.)"""
    cells = [tuple(tuple(c) for c in box)]
    for d in range(depth):
        ax = d % n
        nxt = []
        for cell in cells:
            nxt.extend(_split(cell, ax))
        cells = nxt
    return cells


def _solve_one(problem, axis_mode, start_depth, cell, budget, deadline):
    """Certify one frontier cell's whole subtree from ``start_depth``."""
    ctx = _Ctx(problem, budget, axis_mode, ENGINE_BACKEND, start_depth)
    if deadline is not None:
        ctx.deadline = deadline
    _recurse(ctx, tuple(tuple(c) for c in cell), start_depth)
    return ([asdict(lf) for lf in ctx.leaves],
            [list(c) for c in ctx.failed], ctx.n_lp)


def _solve_subtree(args):
    """Single-process worker entry (serial frontier / checkpoint): full picklable
    ``args`` carry the Problem (plain numpy / dataclasses)."""
    cell, problem, axis_mode, start_depth, budget, deadline = args
    return _solve_one(problem, axis_mode, start_depth, cell, budget, deadline)


# Pool path: the (large) Problem is shipped ONCE per worker via the initializer,
# not once per task — so per-frontier-item pickling stays tiny (just the cell).
_POOL_STATE: dict = {}


def _pool_init(problem, axis_mode, start_depth):
    _POOL_STATE["problem"] = problem
    _POOL_STATE["axis"] = axis_mode
    _POOL_STATE["start_depth"] = start_depth


def _solve_subtree_pooled(args):
    cell, budget, deadline = args
    return _solve_one(_POOL_STATE["problem"], _POOL_STATE["axis"],
                      _POOL_STATE["start_depth"], cell, budget, deadline)


# --------------------------------------------------------------------------- #
# Dynamic work-queue parallelism (default for n_workers > 1)
# --------------------------------------------------------------------------- #
#
# Why a work-queue and not a static frontier: the disconnection partition is thin
# (the slab is a measure-zero-ish sheet), so a static pre-split has only a handful of
# *heavy* cells — one worker ends up owning a big subtree and the speedup stalls
# (~2x). A shared queue fixes this: a worker that splits a cell pushes BOTH children
# back to the queue, so even a heavy subtree is spread across all workers as it
# expands. The processed tree is the deterministic heuristic tree, so the leaf SET is
# byte-identical to serial (no work inflation) regardless of who processed what.
#
# Start method: "forkserver" (default, S8). The parent is multi-threaded (idle BLAS
# pools), and Python 3.12 deprecates fork() from a multi-threaded process — so "fork",
# though SAFE here (the parent never solves an LP, no solver thread is live), raises a
# DeprecationWarning per worker. forkserver forks workers from a clean single-threaded
# server ⇒ no warning and no deadlock risk. The historical reason fork was the default
# (spawn/forkserver re-import cvxpy, crushing them to ~1.5x) vanished once the engine
# backend became highspy (S8): re-import is light, so forkserver is ~9% off fork and
# still >= 3x on 8 cores. "fork"/"spawn" stay overridable for portability.

def _wq_worker(problem, axis_mode, pending, results, active, lock, deadline):
    """Pull cells off ``pending``; emit leaves to ``results``; push children back.
    ``active`` (guarded by ``lock``) counts cells anywhere in flight — when it hits 0
    the tree is fully partitioned and the worker exits with a ``None`` sentinel."""
    from queue import Empty
    backend = ENGINE_BACKEND
    views = pair_views(problem)            # per-pair simplified geometry + active (A29/A30)
    active_ax = _global_active(views, problem)   # branch only on the union (A18)
    while True:
        with lock:
            if active.value == 0:
                break
        try:
            cell, depth = pending.get(timeout=0.05)
        except Empty:
            continue
        over_budget = deadline is not None and time.monotonic() >= deadline
        v = (_certify_cell(cell, problem, backend, views) if not over_budget
             else _CellVerdict("undecided"))
        if v.status == "outside":
            results.put((cell, "outside", None, None))
            with lock:
                active.value -= 1
        elif v.status == "collision":
            results.put((cell, "collision", v.pair, v.margin))
            with lock:
                active.value -= 1
        elif over_budget:
            results.put((cell, "undecided", None, None))
            with lock:
                active.value -= 1
        elif depth >= problem.max_depth:
            results.put((cell, "FAIL", None, v.margin))
            with lock:
                active.value -= 1
        else:
            ax = _choose_axis(cell, problem, axis_mode, backend, active_ax, views)
            c1, c2 = _split(cell, ax)
            with lock:
                active.value += 1        # 2 children replace 1 ⇒ net +1
            pending.put((c1, depth + 1))
            pending.put((c2, depth + 1))
    results.put(None)


def _solve_workqueue(problem, budget, axis_mode, n_workers, start_method, t0):
    ctx = get_context(start_method)
    pending, results = ctx.Queue(), ctx.Queue()
    active, lock = ctx.Value("i", 1), ctx.Lock()
    deadline = (None if budget.max_time_s is None
                else time.monotonic() + budget.max_time_s)
    pending.put((tuple(tuple(c) for c in problem.box), 0))
    procs = [ctx.Process(target=_wq_worker,
                         args=(problem, axis_mode, pending, results, active, lock,
                               deadline))
             for _ in range(n_workers)]
    for p in procs:
        p.start()

    leaves, failed, sentinels = [], [], 0
    while sentinels < n_workers:
        item = results.get()
        if item is None:
            sentinels += 1
            continue
        cell, status, pair, margin = item
        leaves.append(Leaf([list(c) for c in cell], status, pair, margin))
        if status in ("FAIL", "undecided"):
            failed.append([list(c) for c in cell])
    for p in procs:
        p.join()

    n_lp = sum(1 for lf in leaves if lf.status != "outside") * len(problem.pairs)
    stats = _stats(leaves, n_lp, time.monotonic() - t0, problem, n_workers,
                   parallel="work-queue", start_method=start_method)
    return EngineResult(_verdict(failed), leaves, failed, stats)


def _auto_frontier_depth(n_workers, n) -> int:
    """Smallest uniform-split depth giving ~4 subcells per worker (so the pool stays
    busy and load-balances over cells of uneven cost), capped to keep 2**depth sane."""
    target = max(4 * n_workers, 8)
    d = 1
    while (2 ** d) < target and d < 10:
        d += 1
    return d


# --------------------------------------------------------------------------- #
# Checkpoint (atomic per-frontier-item)
# --------------------------------------------------------------------------- #

def _fingerprint(problem: Problem, axis_mode, frontier) -> str:
    """A cheap stable fingerprint of the run so a checkpoint cannot be resumed
    against a different problem/frontier (which would corrupt the certificate)."""
    import hashlib
    h = hashlib.sha256()
    h.update(repr((problem.delta, problem.lam_degree, problem.tol, problem.max_depth,
                   axis_mode, problem.phi.tolist(),
                   [p.name for p in problem.pairs],
                   [(p.obstacle.A.tolist(), p.obstacle.b.tolist()) for p in problem.pairs],
                   [[float(x) for c in cell for x in c] for cell in frontier])).encode())
    return h.hexdigest()[:16]


class _Checkpoint:
    """Directory-backed checkpoint: ``meta.json`` + ``done/<idx>.json`` per solved
    frontier item, each written atomically (temp + os.replace) so a SIGKILL mid-write
    never leaves a half file. Resume = load ``done/*`` and only solve the rest."""

    def __init__(self, path, fingerprint, n_items):
        self.path = path
        self.done_dir = os.path.join(path, "done")
        self.fingerprint = fingerprint
        self.n_items = n_items

    def init(self):
        os.makedirs(self.done_dir, exist_ok=True)
        meta = os.path.join(self.path, "meta.json")
        if os.path.exists(meta):
            with open(meta) as f:
                old = json.load(f)
            if old.get("fingerprint") != self.fingerprint:
                raise ValueError("checkpoint fingerprint mismatch: refusing to "
                                 "resume a different problem (soundness)")
        else:
            self._atomic(meta, {"fingerprint": self.fingerprint,
                                "n_items": self.n_items})

    def _atomic(self, path, obj):
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(obj, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)

    def has(self, idx) -> bool:
        return os.path.exists(os.path.join(self.done_dir, f"{idx}.json"))

    def load(self, idx):
        with open(os.path.join(self.done_dir, f"{idx}.json")) as f:
            return json.load(f)

    def save(self, idx, payload):
        self._atomic(os.path.join(self.done_dir, f"{idx}.json"), payload)


# --------------------------------------------------------------------------- #
# Public driver
# --------------------------------------------------------------------------- #

def solve(problem: Problem, budget: Budget | None = None, axis: str = "oracle",
          n_workers: int = 1, checkpoint_dir: str | None = None,
          frontier_depth: int | None = None, start_method: str = "forkserver",
          backend: LPBackend | None = None) -> EngineResult:
    """Certify (or refuse) the disconnection over ``problem.box``.

    ``axis``: ``"oracle"`` (widest-axis fallback ⇒ reproduces the E3/E4 oracle
    partition) or ``"margin"`` (worst-LP-margin fallback).

    Execution mode (all sound; they only change *how* the same tree is explored):
      * default (``n_workers<=1``, no checkpoint): serial recursion;
      * ``n_workers>1`` (no checkpoint): the **dynamic work-queue** — workers share a
        queue and push split children back, so the partition is byte-identical to
        serial (no inflation) and load-balances dynamically (>= 3x on 8 cores);
      * ``checkpoint_dir`` set: the resumable **frontier** path (uniform pre-split,
        each subtree checkpointed atomically) — a kill-9 then resume yields the same
        certificate. ``checkpoint_dir`` takes precedence over the work-queue.
    """
    if axis not in ("oracle", "margin"):
        raise ValueError(f"unknown axis heuristic: {axis!r}")
    backend = backend or ENGINE_BACKEND
    t0 = time.monotonic()

    if checkpoint_dir is None and n_workers > 1:
        return _solve_workqueue(problem, budget or Budget(), axis, n_workers,
                                start_method, t0)

    if n_workers <= 1 and checkpoint_dir is None:
        ctx = _Ctx(problem, budget, axis, backend, 0)
        _recurse(ctx, tuple(tuple(c) for c in problem.box), 0)
        stats = _stats(ctx.leaves, ctx.n_lp, time.monotonic() - t0, problem, n_workers,
                       termination=ctx.termination(),
                       max_depth_reached=ctx.max_depth_reached,
                       max_depth_limit=problem.max_depth)
        return EngineResult(_verdict(ctx.failed), ctx.leaves, ctx.failed, stats)

    # --- frontier-based path (parallel and/or checkpointed) ---
    if frontier_depth is None:
        frontier_depth = _auto_frontier_depth(max(n_workers, 1), problem.n)
    frontier = _uniform_frontier(problem.box, frontier_depth, problem.n)

    budget = budget or Budget()
    deadline = None if budget.max_time_s is None else time.monotonic() + budget.max_time_s
    per_item_budget = Budget(max_leaves=budget.max_leaves, max_time_s=None)

    ckpt = None
    if checkpoint_dir is not None:
        ckpt = _Checkpoint(checkpoint_dir, _fingerprint(problem, axis, frontier),
                           len(frontier))
        ckpt.init()

    results = [None] * len(frontier)
    pending = []
    for idx in range(len(frontier)):
        if ckpt is not None and ckpt.has(idx):
            results[idx] = ckpt.load(idx)
        else:
            pending.append(idx)

    if pending:
        if n_workers > 1:
            ctxmp = get_context("spawn")
            pooled = [(list(frontier[i]), per_item_budget, deadline) for i in pending]
            with ctxmp.Pool(processes=n_workers, initializer=_pool_init,
                            initargs=(problem, axis, frontier_depth)) as pool:
                for idx, payload in zip(pending,
                                        pool.map(_solve_subtree_pooled, pooled)):
                    if ckpt is not None:
                        ckpt.save(idx, payload)
                    results[idx] = payload
        else:
            for idx in pending:
                payload = _solve_subtree((list(frontier[idx]), problem, axis,
                                          frontier_depth, per_item_budget, deadline))
                if ckpt is not None:
                    ckpt.save(idx, payload)
                results[idx] = payload

    leaves: list = []
    failed: list = []
    n_lp = 0
    for payload in results:
        leaf_dicts, fail_cells, sub_lp = payload
        for d in leaf_dicts:
            leaves.append(Leaf(d["cell"], d["status"], d.get("pair"), d.get("margin")))
        failed.extend(fail_cells)
        n_lp += sub_lp

    stats = _stats(leaves, n_lp, time.monotonic() - t0, problem, n_workers,
                   n_frontier=len(frontier), frontier_depth=frontier_depth)
    return EngineResult(_verdict(failed), leaves, failed, stats)


def _stats(leaves, n_lp, dt, problem, n_workers, **extra):
    by_status = {}
    for lf in leaves:
        by_status[lf.status] = by_status.get(lf.status, 0) + 1
    s = {"n_leaves": len(leaves), "n_lp_solves": n_lp, "time_s": dt,
         "n_workers": n_workers, "axis_n": problem.n, "by_status": by_status}
    s.update(extra)
    return s


# --------------------------------------------------------------------------- #
# Partition export (figure-friendly, CLAUDE.md S3 task 3)
# --------------------------------------------------------------------------- #

def partition_records(result: EngineResult) -> list:
    """Flatten leaves into plain dict records ``{cell, status, pair, margin}`` for
    the figure layer (``scripts/make_figures.py``) and the certificate (S4)."""
    return [{"cell": [list(c) for c in lf.cell], "status": lf.status,
             "pair": lf.pair, "margin": lf.margin} for lf in result.leaves]
