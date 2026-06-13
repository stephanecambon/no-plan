"""S9e — regression for the active-dimension scaling-wall bench (scripts/wall_bench.py).

Locks in the synthetic construction whose numbers DECISION-G2.md §3d (the signed dossier)
cites: a k-joint chain whose certified body is the last link has exactly k DETECTED active
dims (no passive padding), and each point is a REAL disconnection (dense ground truth). Only
the fast certified points (k=3,4) run here; k=5 (the affine wall, ~45 s UNDECIDED) is left to
the bench script."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import wall_bench as wb  # noqa: E402
from cnp import engine, scenes, certificate as cert, verify  # noqa: E402


@pytest.mark.parametrize("k", [3, 4])
def test_wall_point_is_a_real_certified_disconnection(k):
    sc = wb.build_scene(k)
    prob = scenes.build_problem(sc)
    active = engine._global_active(engine.pair_views(prob), prob)
    assert len(active) == k, f"k={k}: detected {len(active)} active dims, expected {k}"

    gt = wb.ground_truth(sc, n=3000)
    assert gt["start_free"] and gt["goal_free"], f"k={k}: start/goal not free: {gt}"
    assert gt["free_in_slab"] == 0, f"k={k}: {gt['free_in_slab']} free points in the slab"
    assert gt["free_left"] > 0 and gt["free_right"] > 0, f"k={k}: not two components: {gt}"

    res = engine.solve(prob, axis="margin", budget=engine.Budget(max_leaves=10_000))
    assert res.verdict == "PROOF"
    c = cert.make_certificate(sc, res, verify_loop=True)
    assert c["stats"]["n_reresolve_failed"] == 0
    assert verify.verify(c)[0]
