"""S5 — barrier phi pipeline (cnp.phifit): automatic phi + delta, then certify.

Exit criteria (CLAUDE.md S5 "Sortie"):
  * E4-planaire reproduced via the COMPLETE pipeline (sample -> fit -> delta ->
    certify -> verify): phi found automatically, no hand hint, exact verify OK;
  * the 3-DOF spatial scene: phi found automatically and certified (engine PROOF),
    cross-checked by dense sampling (the exact verifier stays planar until S9, so the
    spatial certificate is engine-PROOF + ground-truth, labelled honestly).

Soundness negative control: a shrunk wall opens a free path (false premise) and the
pipeline must NOT return PROOF.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(__file__))

import phi_scenes  # noqa: E402
from cnp import certificate as cert, engine, phifit, polylin, verify  # noqa: E402


# --------------------------------------------------------------------------- #
# E4-planaire: complete pipeline through the EXACT verifier
# --------------------------------------------------------------------------- #

@pytest.mark.slow
@pytest.mark.parametrize("method", ["lstsq", "svm"])
def test_e4_pipeline_certified_and_verified(method):
    """The pipeline fits a barrier (no hand hint) and the disconnection is certified
    end-to-end and verified in EXACT arithmetic — E4 reproduced via the full pipeline."""
    fr = phifit.fit_barrier(phi_scenes.e4_collision, phi_scenes.E4_BOX,
                            phi_scenes.E4_START, phi_scenes.E4_GOAL,
                            phi_scenes.e4_build_problem, method=method,
                            n_samples=3000, seed=1, solve_kw={"axis": "oracle"})
    assert fr.verdict == "PROOF", f"{method}: {fr.verdict}"
    assert fr.delta > 0
    scene = phi_scenes.e4_scene_with(fr.phi, fr.phi_degree, fr.delta)
    c = cert.make_certificate(scene, fr.result)
    ok, msg = verify.verify(c)
    assert ok, f"{method}: {msg}"


# --------------------------------------------------------------------------- #
# 3-DOF spatial: engine PROOF + dense-sampling soundness cross-check
# --------------------------------------------------------------------------- #

def _phi_tensor(fr):
    pt = np.zeros((fr.phi_degree + 1,) * 3)
    for e, c in fr.phi.items():
        pt[tuple(int(x) for x in e)] = float(c)
    return pt


def _fit_3dof(method):
    return phifit.fit_barrier(phi_scenes.sp_collision, phi_scenes.SP_BOX,
                              phi_scenes.SP_START, phi_scenes.SP_GOAL,
                              phi_scenes.sp_build_problem, method=method,
                              n_samples=4000, seed=2, solve_kw={"axis": "margin"})


@pytest.mark.parametrize("method", ["lstsq", "svm"])
def test_3dof_pipeline_proof_and_condition_i(method):
    """phi found automatically for the 3R chain; engine PROOF and condition (i) holds
    in EXACT arithmetic (phi(start) < -delta, phi(goal) > +delta)."""
    fr = _fit_3dof(method)
    assert fr.verdict == "PROOF", f"{method}: {fr.verdict}"
    ps = phifit._phi_eval_exact(fr.phi, list(phi_scenes.SP_START))
    pg = phifit._phi_eval_exact(fr.phi, list(phi_scenes.SP_GOAL))
    assert ps < -fr.delta and pg > fr.delta


@pytest.mark.slow
@pytest.mark.parametrize("method", ["lstsq", "svm"])
def test_3dof_slab_is_collision_dense_sampling(method):
    """Soundness cross-check (verify is planar until S9): over a dense seeded sample
    of the box, EVERY config inside the certified slab {|phi| <= delta} is in
    collision — no free point in the slab (the S2 exit-#2 ground-truth check)."""
    fr = _fit_3dof(method)
    assert fr.verdict == "PROOF"
    pt = _phi_tensor(fr)
    rng = np.random.default_rng(0)
    S = rng.uniform(-0.7, 0.7, size=(60_000, 3))
    inslab = np.array([abs(polylin.teval(pt, s)) <= float(fr.delta) for s in S])
    assert inslab.sum() > 1000  # the slab is non-degenerate (a real band, not a sheet)
    free_in_slab = sum(1 for s in S[inslab] if not phi_scenes.sp_collision(s))
    assert free_in_slab == 0, f"{method}: {free_in_slab} free configs inside the slab"


def test_3dof_negative_control_shrunk_wall_not_proved():
    """Soundness: shrink the wall about its centre (false premise — a free path opens
    around it), and the pipeline must NOT return PROOF."""
    def build(phi, deg, delta):
        return phi_scenes.sp_build_problem(phi, deg, delta, scale=0.4)
    fr = phifit.fit_barrier(phi_scenes.sp_collision, phi_scenes.SP_BOX,
                            phi_scenes.SP_START, phi_scenes.SP_GOAL, build,
                            method="lstsq", n_samples=1500, seed=2, max_retries=1,
                            solve_kw={"axis": "margin",
                                      "budget": engine.Budget(max_leaves=80)})
    # No disconnection exists (free path around the shrunk wall) => the engine can
    # never carve an all-collision slab; it exhausts the budget as UNDECIDED.
    assert fr.verdict != "PROOF"


# --------------------------------------------------------------------------- #
# Pipeline units
# --------------------------------------------------------------------------- #

def test_sample_box_is_seeded_and_labels():
    S1, y1 = phifit.sample_box(phi_scenes.e4_collision, phi_scenes.E4_BOX, 200, 7)
    S2, y2 = phifit.sample_box(phi_scenes.e4_collision, phi_scenes.E4_BOX, 200, 7)
    assert np.array_equal(S1, S2) and np.array_equal(y1, y2)  # seeded => reproducible
    assert set(np.unique(y1)) <= {0.0, 1.0} and 0 < y1.sum() < len(y1)


def test_fit_without_build_problem_returns_candidate():
    """With no build_problem the pipeline just proposes a barrier (for figures)."""
    fr = phifit.fit_barrier(phi_scenes.e4_collision, phi_scenes.E4_BOX,
                            phi_scenes.E4_START, phi_scenes.E4_GOAL,
                            method="lstsq", n_samples=800, seed=3)
    assert fr.verdict is None and fr.delta > 0 and fr.phi
