"""Scene pipeline tests (session S6): YAML parser -> Scene -> certify -> verify, the
scene/cert cross-check, the three-status CLI verdicts, and the viz geometry helpers.

The frozen regression scenes live as YAML under ``scenes/``; certifying them through
the parser must reproduce the oracle (S1 = 46 leaves) and verify exactly, end-to-end.
"""
import json
import os
from fractions import Fraction as F

import pytest

from cnp import certificate as cert, engine, scenes, verify, viz, cli

SCENES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scenes")


def _scene(name):
    return scenes.load(os.path.join(SCENES, name))


# --------------------------------------------------------------------------- #
# Parsing / round-trip
# --------------------------------------------------------------------------- #

def test_s1_roundtrip_reproduces_oracle_and_verifies():
    scene, budget = _scene("S1_relais.yaml")
    res = engine.solve(scenes.build_problem(scene, max_depth=budget.max_depth),
                       axis=budget.axis, budget=budget.engine_budget())
    assert res.verdict == "PROOF"
    assert res.counts()["status"] == {"outside": 8, "collision": 38}   # E3, 46 leaves
    c = cert.make_certificate(scene, res)
    ok, msg = verify.verify(c)
    assert ok, msg


@pytest.mark.slow
def test_peigne_3dof_certifies_and_verifies_exactly():
    scene, budget = _scene("S2_peigne.yaml")
    assert scene.robot.n == 3                                # genuine 3-DOF box
    res = engine.solve(scenes.build_problem(scene, max_depth=budget.max_depth),
                       axis=budget.axis, budget=budget.engine_budget())
    assert res.verdict == "PROOF"
    c = cert.make_certificate(scene, res)
    ok, msg = verify.verify(c)
    assert ok, msg


def test_box_and_hrep_obstacles_are_equivalent():
    box_scene, _ = _scene("S1_relais.yaml")
    A, b = box_scene.obstacles["MID"]
    # re-author MID as raw H-rep and check the parsed obstacle is identical
    hrep = {"hrep": {"A": [[str(x) for x in row] for row in A], "b": [str(x) for x in b]}}
    A2, b2 = scenes._parse_obstacle("MID", hrep)
    assert A2 == A and b2 == b


def test_hull_is_derived_from_link_geometry():
    data = {
        "robot": {"kind": "planar_revolute", "link_lengths": ["1", "1"]},
        "body": {"link": 1},
        "obstacles": {"X": {"box": [["0", "1"], ["0", "1"], ["-1", "1"]]}},
        "phi": {"degree_per_var": 2, "coeffs": {"1,0": "1"}}, "delta": "1/20",
        "box": [["-1", "1"], ["-1", "1"]], "start_s": ["-9/10", "0"],
        "goal_s": ["9/10", "0"], "pairs": ["X"],
    }
    scene, _ = scenes.parse_scene(data)
    assert scene.hull_vertices == [[F(0), F(0), F(0)], [F(1), F(0), F(0)]]


# --------------------------------------------------------------------------- #
# Scene <-> certificate cross-check
# --------------------------------------------------------------------------- #

@pytest.mark.slow
def test_scene_matches_its_own_certificate():
    scene, _ = _scene("S1_relais.yaml")
    res = engine.solve(scenes.build_problem(scene, max_depth=16))
    c = cert.make_certificate(scene, res)
    ok, why = scenes.scene_matches_cert(scene, c)
    assert ok, why


@pytest.mark.slow
def test_cross_check_rejects_a_tampered_certificate():
    scene, _ = _scene("S1_relais.yaml")
    res = engine.solve(scenes.build_problem(scene, max_depth=16))
    c = cert.make_certificate(scene, res)
    for mutate in (
        lambda d: d["obstacles"]["MID"]["b"].__setitem__(0, "999"),
        lambda d: d["start_s"].__setitem__(0, "0"),
        lambda d: d["phi"]["coeffs"].__setitem__("1,0", "2"),
        lambda d: d.__setitem__("delta", "1/2"),
    ):
        bad = json.loads(json.dumps(c))
        mutate(bad)
        ok, _ = scenes.scene_matches_cert(scene, bad)
        assert not ok


# --------------------------------------------------------------------------- #
# Malformed scenes raise cleanly
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("mutate", [
    lambda d: d.pop("phi"),                                  # no barrier
    lambda d: d.__setitem__("box", [["-1", "1"]]),           # dim mismatch
    lambda d: d.__setitem__("pairs", ["GHOST"]),             # unknown obstacle
    lambda d: d["obstacles"]["X"].clear(),                   # obstacle without box/hrep
    lambda d: d.setdefault("budget", {}).__setitem__("axis", "clever"),  # bad axis
])
def test_malformed_scene_raises(mutate):
    data = {
        "robot": {"kind": "planar_revolute", "link_lengths": ["1", "1"]},
        "body": {"link": 1},
        "obstacles": {"X": {"box": [["0", "1"], ["0", "1"], ["-1", "1"]]}},
        "phi": {"degree_per_var": 2, "coeffs": {"1,0": "1"}}, "delta": "1/20",
        "box": [["-1", "1"], ["-1", "1"]], "start_s": ["-9/10", "0"],
        "goal_s": ["9/10", "0"], "pairs": ["X"],
    }
    mutate(data)
    with pytest.raises((ValueError, KeyError)):
        scenes.parse_scene(data)


# --------------------------------------------------------------------------- #
# Three verdicts (A17): PROOF / ENGINE-PROOF / UNDECIDED
# --------------------------------------------------------------------------- #

def test_spatial_scene_is_now_exactly_verifiable_g3b():
    """G3'b (S9): the spatial builtin is re-checked by the INDEPENDENT exact verifier
    (verify.py re-derives the 3-D FK from the cert's offsets/axes), so S2b flips from
    ENGINE-PROOF to PROOF. The ENGINE-PROOF placeholder ('exact verifier arrives in S9')
    is retired for spatial scenes."""
    scene, budget = _scene("S2b_spatial3.yaml")
    assert scenes.is_exactly_verifiable(scene)                # spatial -> PROOF now
    res = engine.solve(scenes.build_problem(scene, max_depth=budget.max_depth),
                       axis=budget.axis, budget=budget.engine_budget())
    assert res.verdict == "PROOF"
    c = cert.make_certificate(scene, res, verify_loop=True)
    assert "joints" in c["robot"]                             # spatial geometry serialized
    ok, _ = verify.verify(c)
    assert ok                                                 # re-checked in exact arithmetic


@pytest.mark.slow
def test_cli_certify_then_verify_s1(tmp_path, capsys):
    out = tmp_path / "s1.cert.json"
    rc = cli.main(["certify", os.path.join(SCENES, "S1_relais.yaml"), "-o", str(out)])
    assert rc == 0
    assert "verdict: PROOF" in capsys.readouterr().out
    rc = cli.main(["verify", str(out), os.path.join(SCENES, "S1_relais.yaml")])
    assert rc == 0
    assert "PROOF" in capsys.readouterr().out


def test_cli_certify_spatial_is_proof_g3b(tmp_path, capsys):
    out = tmp_path / "s2b.cert.json"
    rc = cli.main(["certify", os.path.join(SCENES, "S2b_spatial3.yaml"), "-o", str(out)])
    txt = capsys.readouterr().out
    assert rc == 0
    assert "verdict: PROOF" in txt and "ENGINE-PROOF" not in txt   # G3'b: exact now
    rc = cli.main(["verify", str(out), os.path.join(SCENES, "S2b_spatial3.yaml")])
    assert rc == 0 and "PROOF" in capsys.readouterr().out


@pytest.mark.slow
def test_cli_verify_rejects_cert_against_wrong_scene(tmp_path, capsys):
    out = tmp_path / "s1.cert.json"
    cli.main(["certify", os.path.join(SCENES, "S1_relais.yaml"), "-o", str(out)])
    capsys.readouterr()
    rc = cli.main(["verify", str(out), os.path.join(SCENES, "S2b_spatial3.yaml")])
    assert rc == 1
    assert "REJECT" in capsys.readouterr().out                # scene/cert mismatch


# --------------------------------------------------------------------------- #
# viz geometry (no Meshcat server)
# --------------------------------------------------------------------------- #

def test_spatial_oracle_and_viz_geometry():
    """Spatial builtin: collision oracle + viz skeleton work, and the scene is a
    genuine 'free start/goal, colliding slab' (the V3 unreachability story in 3-D)."""
    scene, _ = _scene("S2b_spatial3.yaml")
    oracle = scenes.collision_oracle(scene, n_samples=30)
    assert not oracle([float(v) for v in scene.start_s])      # start is free
    assert not oracle([float(v) for v in scene.goal_s])       # goal is free
    assert oracle([0.0, 0.0, 0.0])                            # in-slab (s0=0): collision
    pts = viz._joint_world_positions(scene, viz._config_q_to_s(scene, "start"))
    assert pts.shape == (4, 3)                                # 3 joints + distal tip


def test_viz_joint_positions_and_box_bounds():
    scene, _ = _scene("S1_relais.yaml")
    pts = viz._joint_world_positions(scene, viz._config_q_to_s(scene, "start"))
    assert pts.shape == (3, 3)                                # 2 joints + EE, 3-D
    assert abs(pts[0][0]) < 1e-9 and abs(pts[0][1]) < 1e-9    # base at origin
    A, b = scene.obstacles["MID"]
    assert viz._box_bounds(A, b) == [(1.8, 2.1), (-0.45, 0.45), (-1.0, 1.0)]
