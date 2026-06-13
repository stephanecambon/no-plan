"""S9f — regression for the re-sonde of the scaling wall (DECISION-G2.md §3d-bis).

Locks in the four corrections of the S9e §3d:
  (L0a) the engine now EXPOSES its termination cause in stats (depth_exhausted / budget_* /
        certified) — so an UNDECIDED can be told apart as a depth ceiling vs the real budget;
  (L0a) the S9e wall scene LEAKS at config-space corners (a free config the 8000-sample ground
        truth misses), and the Bernstein-sealed scene FIXES it (genuine watertight disconnection);
  (re-measure) the affine witness certifies the SEALED k=3,4,5 disconnections as PROOF + exact
        verify + A32=0 — there is NO affine wall at k=5 (it was an artifact);
  (L1) the face polynomials are UNIFORM degree 3 per active axis ⇒ anisotropic Bernstein gives
        zero gain (ratio 1.0) — measured, left non-default.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from fractions import Fraction as F  # noqa: E402

import wall_bench as wb  # noqa: E402
import wall_resonde_S9f as rs  # noqa: E402
from cnp import certificate as cert, engine, scenes, verify  # noqa: E402


def test_termination_cause_is_exposed():
    """L0a: the engine stats distinguish the three ways a serial run stops."""
    sc = rs.build_scene_sealed(3, s0hi=F(4, 5))
    # certified: a clean watertight run ends with no open cell
    rc = engine.solve(scenes.build_problem(sc), axis="margin")
    assert rc.verdict == "PROOF" and rc.stats["termination"] == "certified"
    assert "max_depth_reached" in rc.stats and "max_depth_limit" in rc.stats
    # depth ceiling: max_depth=0 forces the straddling root to FAIL (NOT a budget result)
    prob_d = scenes.build_problem(sc); prob_d.max_depth = 0
    rd = engine.solve(prob_d, axis="margin")
    assert rd.verdict == "UNDECIDED" and rd.stats["termination"] == "depth_exhausted"
    # budget: a tiny leaf cap stops on budget
    rb = engine.solve(scenes.build_problem(sc), axis="margin",
                      budget=engine.Budget(max_leaves=1))
    assert rb.stats["termination"] == "budget_leaves"


@pytest.mark.parametrize("k", [3, 4, 5])
def test_sealed_scene_is_watertight_and_certifies(k):
    """The Bernstein-sealed disconnection is genuine (0 free in slab incl. corner-biased) AND
    the affine witness certifies it PROOF + exact verify + A32=0 — no k=5 wall."""
    sc = rs.build_scene_sealed(k, s0hi=F(4, 5))
    prob = scenes.build_problem(sc); prob.max_depth = 60
    assert len(engine._global_active(engine.pair_views(prob), prob)) == k
    gt = rs.ground_truth_sealed(sc, n=2500)
    assert gt["start_free"] and gt["goal_free"]
    assert gt["free_in_slab"] == 0 and gt["free_in_slab_corner"] == 0, f"k={k} leaks: {gt}"
    assert gt["free_left"] > 0 and gt["free_right"] > 0
    res = engine.solve(prob, axis="margin",
                       budget=engine.Budget(max_leaves=10000, max_time_s=300))
    assert res.verdict == "PROOF" and res.stats["termination"] == "certified"
    c = cert.make_certificate(sc, res, verify_loop=True)
    ok, _ = verify.verify(c)
    assert ok and c["stats"]["n_reresolve_failed"] == 0


def test_leaky_S9e_scene_leaks_and_seal_fixes_it():
    """L0a diagnostic: the S9e wall scene (bbox of random samples) leaves a FREE config in the
    slab at the config-space corner; the Bernstein-sealed scene makes that same config collide."""
    k = 5
    corner = [-0.0999] + [-0.249] * (k - 1)         # slab edge, other joints near their min
    leaky = scenes.collision_oracle(wb.build_scene(k), n_samples=80)
    sealed = scenes.collision_oracle(rs.build_scene_sealed(k, s0hi=F(4, 5)), n_samples=80)
    assert leaky(corner) is False, "expected the S9e scene to LEAK at the corner (free in slab)"
    assert sealed(corner) is True, "expected the sealed scene to seal the corner (collision)"


def test_anisotropic_bernstein_does_not_pay():
    """L1: per-axis degrees of the face polynomials are UNIFORM (=3) on every active axis ⇒
    anisotropic Bernstein prod(d_i+1) equals the uniform (max+1)^k (ratio 1.0). Measured here
    on the sealed wall and asserted on S4 too (revolute joints ⇒ degree 2 in N and D, +1 for λ)."""
    def per_axis_deg(t):
        nz = np.argwhere(t != 0)
        return [int(nz[:, ax].max()) if len(nz) else 0 for ax in range(t.ndim)]

    def face_degrees(prob, view):
        dD = per_axis_deg(view.D)
        dNum = [0] * prob.n
        for v in view.verts_num:
            for cc in v:
                pa = per_axis_deg(cc)
                for i in range(prob.n):
                    dNum[i] = max(dNum[i], pa[i])
        dphi = per_axis_deg(prob.phi)
        dface = [max(dD[i], dNum[i] + 1, 2 * dphi[i]) for i in range(prob.n)]
        return [dface[i] for i in view.active]

    # sealed wall k=5: all active axes degree 3
    prob = scenes.build_problem(rs.build_scene_sealed(5, s0hi=F(4, 5)))
    da = face_degrees(prob, engine.pair_views(prob)[0])
    assert da and len(set(da)) == 1, f"expected uniform per-axis degree, got {da}"
    aniso = int(np.prod([d + 1 for d in da]))
    uniform = (max(da) + 1) ** len(da)
    assert aniso == uniform, f"anisotropic should not beat uniform here: {aniso} vs {uniform}"

    # real S4 scene: active axes also uniform degree ⇒ anisotropy gives nothing
    sc4, _ = scenes.load("scenes/S4_iiwa_bin.yaml")
    prob4 = scenes.build_problem(sc4)
    for vw in engine.pair_views(prob4):
        if vw.active:
            d4 = face_degrees(prob4, vw)
            assert len(set(d4)) == 1, f"S4 pair {vw.pair.name} non-uniform: {d4}"
