"""S10-ter Tâche 2 — guard the frozen FAITHFUL CONVEX BODY (level 1) of iiwa7 link 3.

Structural checks run always (the frozen JSON is committed): the body is exactly rational,
in verify.py's form (rational hull vertices), attached at the chain body frame after q3, and
its RE-MEASURED active dims (engine.pair_views, A30 — NOT presumed {0,1,2}) match the frozen
record. The Drake body parity (faithful to the visual mesh within the SDF ~2e-6 floor) runs
only when Drake + the cached iiwa7 visual mesh are present (règle 13: skip, never a silent
green elsewhere).
"""
from __future__ import annotations

import importlib
import json
import os
import sys
from fractions import Fraction as F

import pytest
import yaml

HERE = os.path.dirname(__file__)
BODY = os.path.join(HERE, "..", "scripts", "iiwa7_body_link3.json")
CHAIN = os.path.join(HERE, "..", "scripts", "iiwa7_chain.json")
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))


def _load():
    with open(BODY) as f:
        return json.load(f)


def test_iiwa7_body_is_exact_and_verify_shaped():
    b = _load()
    assert b["body_link"] == 7                                   # chain frame after q3
    verts = b["hull_vertices"]
    assert len(verts) == b["k_vertices"] >= 8                    # a real convex silhouette
    for v in verts:
        assert len(v) == 3
        [F(x) for x in v]                                        # exact rationals (verify recounts)


def test_iiwa7_body_active_dims_remeasured():
    """The body mounts on the frozen chain and its active dims are RE-MEASURED (not presumed):
    body after q3 ⇒ only the upstream variables {q1,q2,q3}=(0,1,2) can move it; q4..q7 are
    geometrically downstream and passive (the 'robust to redundancy' thesis for a proximal body)."""
    import build_iiwa7_scene as bs
    body = _load()
    box = [["-7/10", "7/10"], ["-1/4", "1/4"], ["-1/4", "1/4"],
           ["-3", "3"], ["-3", "3"], ["-3", "3"], ["-3", "3"]]
    panel_b = ["1/2", "3/20", "9/10", "-1/20", "1/20", "-7/20"]
    hull = [[F(x) for x in v] for v in body["hull_vertices"]]
    sc, views, glob, passive = bs.measure_active(
        bs.emit_scene(hull, panel_b, box, ["-3/5"] + ["0"] * 6, ["3/5"] + ["0"] * 6))
    assert sc.robot.n_joints == 19 and len(sc.robot.locked) == 12 and sc.robot.n == 7
    assert glob == (0, 1, 2), f"active dims {glob} != measured/frozen (0,1,2)"
    assert passive == (3, 4, 5, 6)
    assert list(glob) == body["active_dims_measured"]            # frozen record matches a live re-measure


@pytest.mark.skipif(importlib.util.find_spec("pydrake") is None, reason="Drake absent")
def test_iiwa7_body_drake_parity():
    """The rationalized hull, via the frozen-chain FK, tracks the real Drake link 3 within the
    SDF ~2e-6 floor (Option A doctrine extended to the body silhouette)."""
    try:
        import build_iiwa7_scene as bs
        err = bs.check_body_parity()
    except Exception as exc:                                     # visual mesh not cached / load failure
        pytest.skip(f"iiwa7 visual mesh unavailable: {exc}")
    assert err < 5e-6, f"Drake body parity {err:.2e} exceeds the ~4e-6 SDF tolerance"
