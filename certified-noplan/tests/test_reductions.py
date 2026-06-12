"""S9 — the two leaf-LP reductions: rational passivity (A29) and per-pair reduction (A30).

These complete the S8 "passive dimensions by intervals" line (A18). Both act ONLY on the
DECISION path; the certificate is re-solved at full dimension from the scene FK and the
independent exact verifier re-derives FK from scratch, so a buggy reduction can at worst
cost a leaf (or downgrade PROOF→ENGINE-PROOF), never forge a proof (CLAUDE.md rule 1).

A29 — RATIONAL passivity. A joint that is geometrically passive but whose ``(1+s_i^2)``
denominator factor the common per-link denominator still carries on both ``D`` and every
numerator (the S3 base roll about the upper arm's own axis) is exposed by dividing that
factor out exactly. After it, the roll counts as passive and the leaf LP drops a dimension.

A30 — PER-PAIR reduction. Passivity is a property of the PAIR: a pair on a proximal link
has every distal joint passive FOR ITS LP. Each pair's leaf LP is reduced to its OWN active
axes (a stricter reduction than the global one on a multi-body scene); branching still uses
the GLOBAL active set so the partition is unchanged.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(__file__))

from cnp import scenes, engine, witness, certificate as cert, verify  # noqa: E402
from cnp.ratfk import RevoluteJoint, SympyRatFK  # noqa: E402

SCENES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scenes")
BACKEND = engine.ENGINE_BACKEND


def _s3():
    return scenes.load(os.path.join(SCENES, "S3_shoulder_elbow.yaml"))


# --------------------------------------------------------------------------- #
# A29 — the (1+s^2) division primitive
# --------------------------------------------------------------------------- #

def test_a29_primitive_divides_exact_factor():
    """``_divide_out_one_plus_s2`` returns the quotient iff ``(1+s_i^2)`` is genuinely a
    factor (exponent-1 slice zero, exponent-0 == exponent-2), else ``None``."""
    from cnp.polylin import zeros, mono, tmul, teval
    n, axis = 2, 1
    # M(s0) = 1 + 3*s0 ; build (1 + s1^2) * M and divide it back out
    M = zeros(n, 2)
    M[0, 0] = 1.0
    M[1, 0] = 3.0
    one_plus = mono(n, 2, [0, 0], 1.0) + mono(n, 2, [0, 2], 1.0)   # 1 + s1^2
    prod = tmul(M, one_plus, 2)
    assert engine._tensor_depends(prod, axis)                      # carries the factor
    q = engine._divide_out_one_plus_s2(prod, axis)
    assert q is not None
    assert not engine._tensor_depends(q, axis)                     # factor gone
    # quotient == M (compare by evaluation at a few points)
    for s in ([0.2, 0.5], [-0.4, 1.3], [0.0, 0.0]):
        assert abs(teval(q, s) - teval(M, s)) < 1e-12
    # a polynomial WITHOUT the factor (just 1 + s1) does not divide
    not_fact = mono(n, 2, [0, 0], 1.0) + mono(n, 2, [0, 1], 1.0)
    assert engine._divide_out_one_plus_s2(not_fact, axis) is None


def test_a29_simplify_preserves_geometry_s3():
    """A29 rewrites (verts, D) of the S3 upper arm to drop the roll's ``(1+s2^2)`` factor,
    yet ``x = N/D`` is unchanged at every sample (we divide numerator AND denominator by the
    same positive factor)."""
    scene, _ = _s3()
    prob = scenes.build_problem(scene, max_depth=8)
    pr = prob.pairs[0]
    verts2, D2, removed = engine._simplify_geometry(pr.verts_num, pr.D, prob.n)
    assert 2 in removed                                            # the roll factor was divided out
    assert engine._tensor_depends(pr.D, 2)                         # raw D carried s2 ...
    assert not engine._tensor_depends(D2, 2)                       # ... simplified D does not
    rng = np.random.default_rng(0)
    from cnp.polylin import teval
    for _ in range(200):
        s = rng.uniform([-0.7, -0.4, -1.0, 0.0], [0.7, 0.4, 1.0, 1.4])
        for k in range(len(pr.verts_num)):
            for i in range(3):
                x_full = teval(pr.verts_num[k][i], s) / teval(pr.D, s)
                x_simp = teval(verts2[k][i], s) / teval(D2, s)
                assert abs(x_full - x_simp) < 1e-9


def test_a29_detects_s3_roll_passive():
    """The S3 base roll s2 is geometrically passive but the plain tensor test (used through
    S8) misses it; A29 detects it ⇒ ``passive_dims`` now returns both distal joints."""
    scene, budget = _s3()
    prob = scenes.build_problem(scene, max_depth=budget.max_depth)
    # plain (pre-A29) detection would keep s2 active (raw D depends on it):
    assert engine._tensor_depends(prob.pairs[0].D, 2)
    # A29-aware detection marks it passive:
    assert engine.passive_dims(prob) == (2, 3)
    assert engine.active_axes(prob) == (0, 1)
    assert [v.active for v in engine.pair_views(prob)] == [(0, 1)]


# --------------------------------------------------------------------------- #
# A30 — per-pair reduction is EXACT (t_reduced == t_full per pair, rule 1)
# --------------------------------------------------------------------------- #

def _full_margin(cell, view, prob):
    """Margin of the same pair view solved WITHOUT the per-pair projection (all dims kept;
    the simplified geometry is constant along the passive axes, so it must match)."""
    lp = witness.build_witness_lp(cell, view.verts_num, view.D, view.pair.obstacle,
                                  phi=prob.phi, delta=prob.delta,
                                  lam_degree=prob.lam_degree, active_dims=None)
    return BACKEND.solve(lp).t


def test_a30_reduced_margin_equals_full_on_s3_leaves():
    """For every collision leaf of S3, the per-pair REDUCED LP margin equals the FULL-dim
    margin on the same (A29-simplified) geometry — the projection drops only genuinely
    passive axes, so it cannot inflate ``t`` (rule 1: a reduction that did would be unsound)."""
    scene, budget = _s3()
    prob = scenes.build_problem(scene, max_depth=budget.max_depth)
    res = engine.solve(prob, axis=budget.axis, budget=engine.Budget(max_leaves=4000))
    views = engine.pair_views(prob)
    checked = 0
    for lf in res.leaves:
        if lf.status != "collision":
            continue
        cell = [(float(lo), float(hi)) for lo, hi in lf.cell]
        for view in views:
            t_red = engine.certify_cell_view_margin(cell, view, prob, BACKEND)
            t_full = _full_margin(cell, view, prob)
            assert t_red is not None and t_full is not None
            assert abs(t_red - t_full) <= 1e-7 * (1 + abs(t_full))
            checked += 1
    assert checked > 0


def _two_body_problem():
    """A 5-joint chain with TWO pairs on DIFFERENT links: a proximal body (link 1, passive
    {2,3,4}) and a distal body (link 3, passive {4}) — so the pairs have different active
    sets and per-pair reduction (A30) is strictly finer than the global one."""
    def tr(x, y, z):
        T = np.eye(4); T[:3, 3] = [x, y, z]; return T

    # yaw (z) then four pitches (y), each body segment along local x so a pitch genuinely
    # moves it (no coaxial passivity); j4 is unused by either body ⇒ globally passive.
    axes = [[0, 0, 1.0], [0, 1.0, 0], [0, 1.0, 0], [0, 1.0, 0], [0, 1.0, 0]]
    joints = [RevoluteJoint(f"j{k}", tr(0 if k < 2 else 0.3, 0, 0), np.array(axes[k]))
              for k in range(5)]
    fk = SympyRatFK(joints)
    A = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1],
                  [-1, 0, 0], [0, -1, 0], [0, 0, -1]], float)
    b = np.array([2.0, 2.0, 2.0, 2.0, 2.0, 2.0])           # a large box (LP always feasible)
    prox = engine.Pair("PROX", fk.body("j1").vertex_numerators([[0, 0, 0], [0.3, 0, 0]]),
                       fk.body("j1").D, witness.Polytope(A, b))
    dist = engine.Pair("DIST", fk.body("j3").vertex_numerators([[0, 0, 0], [0.3, 0, 0]]),
                       fk.body("j3").D, witness.Polytope(A, b))
    phi = np.zeros((3,) * 5)
    phi[(1,) + (0,) * 4] = 1.0                              # phi = s0
    box = [(-0.6, 0.6)] * 5
    return engine.Problem(box=box, phi=phi, delta=0.1, pairs=[prox, dist],
                          lam_degree="affine", max_depth=18)


def test_a30_per_pair_active_is_finer_than_global():
    """On a two-body scene the proximal pair sees more passive joints than the distal one,
    and branching uses the UNION (so the partition is unchanged)."""
    prob = _two_body_problem()
    views = {v.pair.name: v.active for v in engine.pair_views(prob)}
    assert views["PROX"] == (0, 1)               # distal joints 2,3,4 passive for the upper arm
    assert views["DIST"] == (0, 1, 2, 3)         # only joint 4 passive for the forearm
    assert engine.active_axes(prob) == (0, 1, 2, 3)   # branch on the union (A30)
    assert engine.passive_dims(prob) == (4,)


def test_a30_reduced_equals_full_two_body():
    """t_reduced == t_full for BOTH pairs of the two-body scene, including the proximal pair
    whose LP drops three passive dimensions (rule 1: the per-pair projection is exact)."""
    prob = _two_body_problem()
    views = engine.pair_views(prob)
    cell = [(-0.3, 0.3), (-0.2, 0.2), (-0.4, 0.4), (-0.5, 0.5), (-0.6, 0.6)]
    for view in views:
        t_red = engine.certify_cell_view_margin(cell, view, prob, BACKEND)
        t_full = _full_margin(cell, view, prob)
        assert t_red is not None and t_full is not None
        assert abs(t_red - t_full) <= 1e-7 * (1 + abs(t_full))


# --------------------------------------------------------------------------- #
# no verdict change + the (non-gate) end-to-end bonus
# --------------------------------------------------------------------------- #

def test_reductions_keep_s3_proof_and_verify():
    """A29/A30 do not change the S3 verdict: still PROOF on both heuristics and the
    certificate still re-verifies in exact arithmetic."""
    scene, _ = _s3()
    for axis in ("margin", "oracle"):
        prob = scenes.build_problem(scene, max_depth=20)
        res = engine.solve(prob, axis=axis, budget=engine.Budget(max_leaves=4000))
        assert res.verdict == "PROOF"
        c = cert.make_certificate(scene, res, verify_loop=True)
        assert verify.verify(c)[0]


def test_a29_bonus_s3_end_to_end_speedup():
    """[non-gate bonus, A29] Detecting the roll cuts the S3 end-to-end decision cost
    (collision leaves x Bernstein LP rows) by >= 10x vs leaving it (falsely) active —
    fewer leaves AND a smaller LP per leaf. Measured ~19x; assert a conservative >= 10x."""
    scene, budget = _s3()

    def lp_work(simplify_on):
        orig = engine._simplify_geometry
        if not simplify_on:
            engine._simplify_geometry = lambda v, D, n: (v, D, ())
        try:
            prob = scenes.build_problem(scene, max_depth=budget.max_depth)
            res = engine.solve(prob, axis="oracle", budget=engine.Budget(max_leaves=8000))
            views = engine.pair_views(prob)
            rows = 0
            for lf in res.leaves:
                if lf.status != "collision":
                    continue
                cell = [(float(lo), float(hi)) for lo, hi in lf.cell]
                for vw in views:
                    lp = witness.build_witness_lp(
                        cell, vw.verts_num, vw.D, vw.pair.obstacle, phi=prob.phi,
                        delta=prob.delta, lam_degree=prob.lam_degree, active_dims=vw.active)
                    rows += lp.face_Az.shape[0] + lp.lam_A.shape[0]
            assert res.verdict == "PROOF"
            return rows
        finally:
            engine._simplify_geometry = orig

    on, off = lp_work(True), lp_work(False)
    assert off >= 10 * on
