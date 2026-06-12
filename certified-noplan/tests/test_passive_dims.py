"""S8 — passive dimensions "by intervals" (annotation A18, CLAUDE.md S8 task #1).

A PASSIVE joint is one neither the barrier ``phi`` nor the moving body depends on (e.g.
the distal joints of a proximal-trapping arm). The widest-axis heuristic used to waste
depth bisecting it (the S6 comb: ``axis="oracle"`` exploded to 736 leaves / UNDECIDED).
S8 detects passive dims and (a) never branches on them and (b) shrinks each cell LP to
the active dims. This file pins:

  * detection (:func:`cnp.engine.passive_dims`) — the comb's distal joint is passive,
    E3/E4's two joints are both active;
  * the S8 EXIT CRITERION — the comb now certifies with ``axis="oracle"`` and the cert
    re-verifies in exact arithmetic (the partition is coarser but still sound);
  * no verdict change vs ``axis="margin"`` (both PROOF + verify); and
  * the cost-model collapse — ``oracle`` no longer grows with the number of passive dims.

Soundness (CLAUDE.md rule 1): excluding an axis from branching only COARSENS the
partition and reducing the LP only restricts λ — neither can manufacture a proof; the
exact verifier (planar) re-checks the comb certificate at full dimension regardless.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(__file__))

import eng_scenes  # noqa: E402
from cnp import scenes, engine, certificate as cert, verify  # noqa: E402

SCENES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scenes")


def _comb():
    scene, budget = scenes.load(os.path.join(SCENES, "S2_peigne.yaml"))
    return scene, budget


# --------------------------------------------------------------------------- #
# detection
# --------------------------------------------------------------------------- #

def test_comb_distal_joint_is_passive():
    """The comb's middle-link body depends only on s0, s1; the distal joint s2 is passive."""
    scene, budget = _comb()
    prob = scenes.build_problem(scene, max_depth=budget.max_depth)
    assert engine.passive_dims(prob) == (2,)
    assert engine.active_axes(prob) == (0, 1)


def test_e3_e4_have_no_passive_dims():
    """Both regression scenes are fully active ⇒ the S8 reduction is a no-op on them
    (so their exact 46 / 78 leaf partitions are untouched — checked in test_engine)."""
    assert engine.passive_dims(eng_scenes.e3_problem()) == ()
    assert engine.passive_dims(eng_scenes.e4_problem()[0]) == ()


# --------------------------------------------------------------------------- #
# the S8 exit criterion: oracle certifies the comb
# --------------------------------------------------------------------------- #

def test_oracle_certifies_comb_after_mitigation():
    """CLAUDE.md S8 exit: the 3-DOF comb certifies with axis="oracle" once the passive
    distal joint is no longer split (was UNDECIDED / 736 leaves before S8)."""
    scene, _ = _comb()
    prob = scenes.build_problem(scene, max_depth=18)
    res = engine.solve(prob, axis="oracle")
    assert res.verdict == "PROOF"
    assert res.counts()["n_leaves"] < 100        # 46 in practice, vs 736 before


@pytest.mark.parametrize("axis", ["margin", "oracle"])
def test_comb_proof_verifies_exactly_both_axes(axis):
    """No verdict change across heuristics: the comb is PROOF on both axes AND its
    certificate re-verifies in exact arithmetic (the passive-aware partition is a valid
    midpoint-bisection cover the untrusted verifier reconstructs)."""
    scene, _ = _comb()
    prob = scenes.build_problem(scene, max_depth=18)
    res = engine.solve(prob, axis=axis)
    assert res.verdict == "PROOF"
    c = cert.make_certificate(scene, res, verify_loop=True)
    ok, msg = verify.verify(c)
    assert ok, msg


# --------------------------------------------------------------------------- #
# cost-model collapse (the A18 sweep, in miniature)
# --------------------------------------------------------------------------- #

def _trap_problem(n: int) -> engine.Problem:
    """2 active joints (yaw, pitch) + (n-2) passive distal revolutes; body = upper arm."""
    from cnp import witness
    from cnp.ratfk import RevoluteJoint, SympyRatFK

    def tr(x, y, z):
        T = np.eye(4); T[:3, 3] = [x, y, z]; return T

    joints = [RevoluteJoint("j0", tr(0, 0, 0), np.array([0, 0, 1.0])),
              RevoluteJoint("j1", tr(0, 0, 0), np.array([0, 1.0, 0]))]
    L = 0.40
    for k in range(2, n):
        ax = np.array([0, 1.0, 0]) if k % 2 == 0 else np.array([1.0, 0, 0])
        joints.append(RevoluteJoint(f"j{k}", tr(L if k == 2 else 0.2, 0, 0), ax))
    fk = SympyRatFK(joints)
    body = fk.body("j1")
    A = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1],
                  [-1, 0, 0], [0, -1, 0], [0, 0, -1]], float)
    b = np.array([0.20, 0.06, 0.5, -0.15, 0.06, 0.5])
    pair = engine.Pair("PANEL", body.vertex_numerators([[0.0, 0, 0], [L, 0, 0]]),
                       body.D, witness.Polytope(A, b))
    phi = np.zeros((3,) * n)
    phi[(1,) + (0,) * (n - 1)] = 1.0
    box = [(-0.7, 0.7), (-0.4, 0.4)] + [(-0.7, 0.7)] * (n - 2)
    return engine.Problem(box=box, phi=phi, delta=0.1, pairs=[pair],
                          lam_degree="affine", max_depth=22)


def test_oracle_leaf_count_flat_in_passive_dims():
    """A18: before S8, axis="oracle" grew 8/12/20/36 over 0..3 passive dims (it split
    them); after, it detects them and the leaf count stays flat as passive dims are
    added — the passive joints are kept as intervals, not partitioned."""
    counts = []
    for n in (2, 3, 4, 5):
        prob = _trap_problem(n)
        assert engine.passive_dims(prob) == tuple(range(2, n))   # all distal joints passive
        res = engine.solve(prob, axis="oracle", budget=engine.Budget(max_leaves=20000))
        assert res.verdict == "PROOF"
        counts.append(res.counts()["n_leaves"])
    assert counts[0] == counts[-1]          # n=2 (0 passive) == n=5 (3 passive): flat
    assert max(counts) == min(counts)
