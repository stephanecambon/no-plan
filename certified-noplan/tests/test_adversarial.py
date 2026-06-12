"""Adversarial soundness suite (session S6, SPEC §9.5, gate G1').

The whole point of the tool is that it NEVER emits a certificate for a false premise.
These scenes are deliberately *connectable* (a free path exists between start and goal)
and the pipeline must refuse them — UNDECIDED, never PROOF, never a written cert.

The headline test is the **micro-canal**: obstacles shrunk just enough to open a thin
free channel that a coarse sampling grid steps right over (it reports "all collision"),
yet the witness LP catches it and the engine refuses. The grid does not prove anything
(CLAUDE.md rule 9) — the certifier is the sole arbiter of soundness.

Soundness contract (rule 1): this suite is the scene-level negative control of the S6
scene pipeline (scenes.py / cli.py); witness/engine/verify are unchanged in S6, their
own negative controls (test_witness, test_putinar_sign, test_verify) still stand.
"""
import copy
import os
from fractions import Fraction as F

import numpy as np
import pytest

import regref
from cnp import certificate as cert, engine, scenes, verify

SCENES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scenes")


# --------------------------------------------------------------------------- #
# A peigne whose three teeth are shrunk about their centres by a factor f < 1.
# f = 1 is the genuine disconnection (scenes/S2_peigne.yaml); f < 1 opens a path.
# --------------------------------------------------------------------------- #

def _shrink(bb, f):
    xlo, xhi, ylo, yhi = bb
    cx, cy = (xlo + xhi) / 2, (ylo + yhi) / 2
    return (cx - (cx - xlo) * f, cx + (xhi - cx) * f,
            cy - (cy - ylo) * f, cy + (yhi - cy) * f)


def _box3(bb):
    xlo, xhi, ylo, yhi = bb
    A = [[1, 0, 0], [0, 1, 0], [0, 0, 1], [-1, 0, 0], [0, -1, 0], [0, 0, -1]]
    b = [F(xhi).limit_denominator(10000), F(yhi).limit_denominator(10000), F(1),
         -F(xlo).limit_denominator(10000), -F(ylo).limit_denominator(10000), F(1)]
    return A, b


def _peigne(f=1.0):
    obst = {nm: _box3(_shrink(bb, f))
            for nm, bb in zip(["UP", "DOWN", "MID"], [regref.UP, regref.DOWN, regref.MID])}
    return cert.Scene(robot=cert.Robot("planar_revolute", [1, 1, 1], [0, 0, 0]),
                      body_link=1, hull_vertices=[[0, 0, 0], [1, 0, 0]], obstacles=obst,
                      phi={(1, 0, 0): 1}, phi_degree=2, delta=F(1, 20),
                      box=[(-1, 1), (-1, 1), (-1, 1)],
                      start_s=[F(-9, 10), F(0), F(0)], goal_s=[F(9, 10), F(0), F(0)],
                      pairs=["UP", "DOWN", "MID"])


def _solve(scene, max_leaves, max_depth=12):
    # A tight leaf budget + shallow depth is enough to establish the verdict is NOT
    # PROOF (a single FAIL/budget cell already makes it UNDECIDED) — we are not trying
    # to exhaust the tree, only to prove the certifier does not hand out a false proof.
    return engine.solve(cert.scene_to_problem(scene, max_depth=max_depth), axis="margin",
                        budget=engine.Budget(max_leaves=max_leaves))


def _coarse_grid_free_in_slab(scene, n=11):
    """Free points in the slab found by a coarse n-per-axis grid (the sampler that
    'proves nothing'). Returns (free_count, total_in_slab)."""
    oracle = scenes.planar_collision_oracle(scene, n_samples=60)
    g = np.linspace(-1, 1, n)
    delta = float(scene.delta)
    free = tot = 0
    for s0 in [v for v in g if abs(v) <= delta]:
        for s1 in g:
            for s2 in g:
                tot += 1
                if not oracle([s0, s1, s2]):
                    free += 1
    return free, tot


def _dense_free_in_slab(scene, n_pts=15000, seed=0):
    oracle = scenes.planar_collision_oracle(scene, n_samples=30)
    rng = np.random.default_rng(seed)
    S = rng.uniform([-1, -1, -1], [1, 1, 1], size=(n_pts, 3))
    slab = S[np.abs(S[:, 0]) <= float(scene.delta)]
    return sum(1 for s in slab if not oracle(s))


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

def test_shrunk_teeth_open_a_path_no_false_certificate():
    """Teeth shrunk 30 %: a free path opens, the engine must REFUSE (UNDECIDED) and a
    certificate must be impossible to assemble (no false PROOF)."""
    scene = _peigne(0.7)
    res = _solve(scene, max_leaves=80)
    assert res.verdict != "PROOF"
    with pytest.raises(ValueError):
        cert.make_certificate(scene, res)


@pytest.mark.slow
def test_cli_certify_refuses_false_premise(tmp_path, capsys):
    """End-to-end through the CLI: a false-premise scene yields UNDECIDED (exit 1) and
    writes no certificate file."""
    import yaml as _yaml
    from cnp import cli

    scene = _peigne(0.7)
    data = {
        "robot": {"kind": "planar_revolute", "link_lengths": ["1", "1", "1"],
                  "q_star": ["0", "0", "0"]},
        "body": {"link": 1},
        "obstacles": {nm: {"hrep": {"A": [[str(x) for x in row] for row in A],
                                    "b": [str(x) for x in b]}}
                      for nm, (A, b) in scene.obstacles.items()},
        "phi": {"degree_per_var": 2, "coeffs": {"1,0,0": "1"}},
        "delta": "1/20", "box": [["-1", "1"]] * 3,
        "start_s": ["-9/10", "0", "0"], "goal_s": ["9/10", "0", "0"],
        "pairs": ["UP", "DOWN", "MID"], "budget": {"max_depth": 18, "axis": "margin"},
    }
    data["budget"]["max_leaves"] = 80
    scene_path = tmp_path / "bad.yaml"
    scene_path.write_text(_yaml.safe_dump(data))
    out = tmp_path / "bad.cert.json"
    rc = cli.main(["certify", str(scene_path), "-o", str(out)])
    assert rc == 1
    assert "UNDECIDED" in capsys.readouterr().out
    assert not out.exists()


@pytest.mark.slow
def test_micro_canal_caught_by_certifier_missed_by_grid():
    """The signature soundness story. Teeth shrunk 5 % open a thin free channel:

      * a coarse 11-per-axis grid finds ZERO free configs in the slab (it misses it);
      * a dense random sampling DOES find free configs (the premise is genuinely false);
      * the engine REFUSES (UNDECIDED) and no certificate can be built.

    The grid does not prove disconnection; the witness LP does, and here it correctly
    declines."""
    scene = _peigne(0.95)

    coarse_free, coarse_tot = _coarse_grid_free_in_slab(scene, n=11)
    assert coarse_tot > 0 and coarse_free == 0          # the grid is fooled

    assert _dense_free_in_slab(scene) > 0               # premise is genuinely false

    res = _solve(scene, max_leaves=400)
    assert res.verdict != "PROOF"                        # the certifier is not fooled
    with pytest.raises(ValueError):
        cert.make_certificate(scene, res)


# --------------------------------------------------------------------------- #
# Spatial exact verifier (G3'b, S9): verify.py now re-derives the 3-D FK from the
# cert's joint offsets/axes. It must REJECT any cert whose declared geometry breaks
# the collision proof — i.e. the joints are genuinely consumed, not rubber-stamped.
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def spatial_cert():
    scene, budget = scenes.load(os.path.join(SCENES, "S2b_spatial3.yaml"))
    res = engine.solve(scenes.build_problem(scene, max_depth=budget.max_depth),
                       axis=budget.axis, budget=budget.engine_budget())
    c = cert.make_certificate(scene, res, verify_loop=True)
    ok, _ = verify.verify(c)
    assert ok                                            # honest cert verifies exactly
    return scene, c


def _first_collision(c):
    return next(lf for lf in c["leaves"] if lf["status"] == "collision")


def test_spatial_verifier_consumes_the_joint_geometry(spatial_cert):
    """A wrong axis or a large offset shift breaks the collision proof => REJECT.
    Proof that verify.py actually re-derives the 3-D FK from the joints (not ignoring
    them): mutate the geometry and the stored lambda/mu no longer bound g - mu*T."""
    _, base = spatial_cert

    def rejected(mut):
        c = copy.deepcopy(base)
        mut(c)
        ok, _ = verify.verify(c)
        return not ok

    # j0 yaw axis +z flipped to +y: the whole chain rotates differently.
    assert rejected(lambda c: c["robot"]["joints"][0].__setitem__("axis", ["0", "1", "0"]))
    # j1 lifted far up in z so the distal segment clears the wall band.
    assert rejected(lambda c: c["robot"]["joints"][1].__setitem__("offset", ["0", "0", "5"]))
    # a non-unit axis makes the Rodrigues numerator unsound -> refused outright.
    assert rejected(lambda c: c["robot"]["joints"][2].__setitem__("axis", ["0", "2", "0"]))


def test_spatial_verifier_rejects_corrupted_multipliers(spatial_cert):
    """The usual witness/partition mutations, on a SPATIAL cert."""
    _, base = spatial_cert

    def rejected(mut):
        c = copy.deepcopy(base)
        mut(c)
        return not verify.verify(c)[0]

    def bust_lambda(c):
        lf = _first_collision(c)
        lf["lambda"][0][next(iter(lf["lambda"][0]))] = "7"

    assert rejected(bust_lambda)                                  # sum_k lambda_k != 1
    assert rejected(lambda c: _first_collision(c).__setitem__("mu",
                    ["-1"] + _first_collision(c)["mu"][1:]))      # mu < 0
    assert rejected(lambda c: c["leaves"].pop())                 # partition no longer tiles
    assert rejected(lambda c: _first_collision(c).update(status="outside"))  # mislabelled


def test_spatial_cross_check_catches_a_geometry_swap(spatial_cert):
    """Two-layer defence: a small offset perturbation yields a cert that is INTERNALLY a
    valid proof (verify.verify accepts — it certifies whatever robot the cert declares),
    but scene_matches_cert ties it to the authored scene and catches the joint swap."""
    scene, base = spatial_cert
    c = copy.deepcopy(base)
    c["robot"]["joints"][1]["offset"] = ["0", "0", "1/4"]        # was 3/10
    assert verify.verify(c)[0]                                    # internally still a proof
    assert not scenes.scene_matches_cert(scene, c)[0]            # but not THIS scene
    assert scenes.scene_matches_cert(scene, base)[0]            # honest cert matches
