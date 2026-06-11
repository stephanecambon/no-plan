"""S7 — the 4-DOF Li-Dantam anchor scene (gate G3') and the benchmark harness.

``scenes/S3_shoulder_elbow.yaml`` reproduces the Li-Dantam RSS 2021 §V-B 4-DOF
shoulder-elbow robot (spherical shoulder + elbow) with an infeasible reaching task.
The verdict is ENGINE-PROOF (the independent EXACT verifier is planar until S9), so the
soundness evidence here is: the engine PROVES the disconnection AND a dense seeded
sample finds 0 free configs in the slab (the S2/S5 ground-truth check — the grid proves
nothing, rule 9; the engine is the arbiter). A shrunk panel opens a free path and the
engine must REFUSE (no false certificate).
"""
import copy
import os
import sys
from fractions import Fraction as F

import numpy as np
import pytest

from cnp import certificate as cert, engine, scenes, cli, viz

SCENES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scenes")
BENCH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "benchmarks")


def _s3():
    return scenes.load(os.path.join(SCENES, "S3_shoulder_elbow.yaml"))


def _solve(scene, budget, max_leaves=4000):
    prob = scenes.build_problem(scene, max_depth=budget.max_depth)
    return engine.solve(prob, axis=budget.axis,
                        budget=engine.Budget(max_leaves=max_leaves))


def _free_in_slab(scene, n_pts, seed=0, n_samples=20):
    """Count seeded samples in the slab |s0|<=delta that are FREE (0 == disconnection)."""
    oracle = scenes.collision_oracle(scene, n_samples=n_samples)
    delta = float(scene.delta)
    lo = [float(l) for l, _ in scene.box]
    hi = [float(h) for _, h in scene.box]
    lo[0], hi[0] = -delta, delta                      # phi = s0 => slab is |s0|<=delta
    rng = np.random.default_rng(seed)
    S = rng.uniform(lo, hi, size=(n_pts, scene.robot.n))
    return sum(1 for s in S if not oracle(s))


# --------------------------------------------------------------------------- #
# The anchor scene: ENGINE-PROOF + dense-sampling soundness
# --------------------------------------------------------------------------- #

def test_s3_is_4dof_spatial_engine_proof():
    scene, budget = _s3()
    assert scene.robot.kind == "spatial_revolute"
    assert scene.robot.n == 4                                  # genuine 4-DOF
    assert not scenes.is_exactly_verifiable(scene)             # spatial -> ENGINE-PROOF (S9)
    res = _solve(scene, budget)
    assert res.verdict == "PROOF"                              # engine proves it


def test_s3_start_goal_free_and_disconnected():
    """Start and goal are FREE (the task looks feasible, A20) but sit in different free
    components: free configs exist on both yaw sides, and the slab between them is fully
    in collision (dense soundness cross-check; the engine PROOF is the actual proof)."""
    scene, _ = _s3()
    oracle = scenes.collision_oracle(scene, n_samples=30)
    assert not oracle([float(v) for v in scene.start_s])       # start free
    assert not oracle([float(v) for v in scene.goal_s])        # goal free
    assert _free_in_slab(scene, 4_000) == 0                    # slab all-collision (fast)


@pytest.mark.slow
def test_s3_dense_300k_zero_free_in_slab():
    """The full S2/S5-style ground-truth check (300k seeded samples, 0 free in slab)."""
    scene, _ = _s3()
    assert _free_in_slab(scene, 300_000) == 0


def test_s3_cli_certify_is_engine_proof(capsys):
    rc = cli.main(["certify", os.path.join(SCENES, "S3_shoulder_elbow.yaml")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ENGINE-PROOF" in out and "NOT" in out              # warning always present
    assert "spatial_revolute" in out and "S9" in out           # honest scope note


# --------------------------------------------------------------------------- #
# Negative control (soundness): a shrunk panel opens a path -> no false certificate
# --------------------------------------------------------------------------- #

@pytest.mark.slow
def test_s3_shrunk_panel_opens_path_no_false_certificate():
    scene, budget = _s3()
    neg = copy.deepcopy(scene)
    A, b = neg.obstacles["PANEL"]                              # shrink the panel in y (open a gap)
    b = list(b)
    b[1] = F(1, 100)                                           # +y face  y <= 1/100
    b[4] = F(1, 100)                                           # -y face  -y <= 1/100
    neg.obstacles["PANEL"] = (A, b)
    res = _solve(neg, budget, max_leaves=200)
    assert res.verdict != "PROOF"                              # engine refuses
    assert _free_in_slab(neg, 8_000) > 0                       # premise is genuinely false


# --------------------------------------------------------------------------- #
# Benchmark harness (smoke): the passive-dimension cost-model sweep
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
# Interactive validation widget (A24): self-contained, correct baked geometry
# --------------------------------------------------------------------------- #

def test_interactive_html_is_self_contained_with_baked_scene(tmp_path):
    """`cnp show --interactive` exports a self-contained HTML (no external src/http
    references) whose baked scene matches the YAML: 4 joints, the panel box, start/goal,
    and the certified upper-arm length."""
    import json
    import re

    out = tmp_path / "s3.html"
    rc = cli.main(["show", os.path.join(SCENES, "S3_shoulder_elbow.yaml"),
                   "--interactive", str(out)])
    assert rc == 0
    h = out.read_text()
    # self-contained: no external script/style/img sources
    assert "src=" not in h and "http://" not in h and "https://" not in h
    assert "<script>" in h and "fkChain(" in h and "collide(" in h
    data = json.loads(re.search(r"const SC = (\{.*?\});", h).group(1))
    assert len(data["joints"]) == 4 and data["body_link"] == 2
    assert abs(data["upper_len"] - 0.4) < 1e-9
    assert data["start_s"][0] == -0.6 and data["goal_s"][0] == 0.6
    assert data["panels"] and data["panels"][0]["hi"][2] == 0.6     # panel top z=3/5
    assert data["joint_names"][3] == "coude (y)"                    # elbow named


def test_interactive_html_rejects_planar_scene():
    scene, _ = scenes.load(os.path.join(SCENES, "S1_relais.yaml"))
    with pytest.raises(NotImplementedError):
        viz.export_interactive_html(scene, "/dev/null")


@pytest.mark.slow
def test_benchmark_passive_dim_sweep_margin_flat_oracle_grows():
    """The harness' cost-model experiment (A18 data): axis=margin stays flat in the
    passive-dim count while axis=oracle grows. Run only n=2,3,4 to keep the test fast."""
    if BENCH not in sys.path:
        sys.path.insert(0, BENCH)
    import run_benchmark as rb

    leaves = {}
    for n in (2, 3, 4):
        prob = rb._trap_problem(n)
        m = engine.solve(prob, axis="margin", budget=engine.Budget(max_leaves=20000))
        o = engine.solve(prob, axis="oracle", budget=engine.Budget(max_leaves=20000))
        assert m.verdict == "PROOF" and o.verdict == "PROOF"
        leaves[n] = (m.counts()["n_leaves"], o.counts()["n_leaves"])
    # margin is constant across passive dims; oracle strictly grows with them.
    margin = [leaves[n][0] for n in (2, 3, 4)]
    oracle = [leaves[n][1] for n in (2, 3, 4)]
    assert margin[0] == margin[1] == margin[2]                 # flat
    assert oracle[0] < oracle[1] < oracle[2]                   # grows with passive dims
