"""S10 — A24 invariant for the 7-DOF flagship interactive HTML.

The widget shows INTENTION (rule 11), but its JS collision logic must not LIE: it must reproduce
the Python collision oracle EXACTLY. This test exports the interactive HTML, extracts its pure
FK+collision JS layer (everything before the `// --- projection` marker), runs it under node on
seeded configs, and asserts byte-for-byte verdict agreement with `scenes.collision_oracle` —
including the slab and the 2^6 distal-corner configs where "robust to redundancy" must hold.

node is optional: the test SKIPS (never fails) when node is absent, like the network tests.
"""
from __future__ import annotations

import itertools
import json
import os
import shutil
import subprocess

import numpy as np
import pytest

from cnp import engine, scenes, viz

SCENES = os.path.join(os.path.dirname(__file__), "..", "scenes")
FLAGSHIP = os.path.join(SCENES, "S5_iiwa_shelf.yaml")


def _export(tmp_path):
    sc, _ = scenes.load(FLAGSHIP)
    prob = scenes.build_problem(sc)
    active = engine._global_active(engine.pair_views(prob), prob)
    out = tmp_path / "flagship.html"
    viz.export_interactive_html(sc, str(out), title="S5 flagship", active_dims=active)
    return sc, out.read_text()


def test_flagship_interactive_structure(tmp_path):
    """7 sliders, 0 locked (pure G3'b base case), active/passive baked (A24/A25)."""
    sc, h = _export(tmp_path)
    assert "src=" not in h and "http://" not in h and "https://" not in h   # self-contained
    assert "fkChain(" in h and "collide(" in h
    data = json.loads(h.split("const SC = ", 1)[1].split(";\n", 1)[0])
    assert len(data["joints"]) == 7
    assert all(j["locked"] is None for j in data["joints"])                 # 0 verrou
    assert data["body_link"] == 2
    assert data["active_dims"] == [0, 1, 2] and data["passive_dims"] == [3, 4, 5, 6]
    assert len(data["limits_deg"]) == 7                                     # A25, one per joint
    assert round(data["limits_deg"][0][1]) == 70                           # lacet +70°


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_flagship_interactive_js_matches_python_oracle(tmp_path):
    """A24 INVARIANT: the JS FK+collision reproduces collision_oracle EXACTLY on seeded
    configs — uniform, start/goal, slab, and the 2^6 distal-extreme corners (redundancy)."""
    sc, h = _export(tmp_path)
    compute = h.split("<script>", 1)[1].split("// --- projection", 1)[0]
    oracle = scenes.collision_oracle(sc, n_samples=41)                     # == JS N=40 -> 41 pts
    lo = np.array([float(l) for l, _ in sc.box])
    hi = np.array([float(hh) for _, hh in sc.box])

    rng = np.random.default_rng(424242)
    cfgs = [list(rng.uniform(lo, hi)) for _ in range(400)]
    cfgs += [[float(x) for x in sc.start_s], [float(x) for x in sc.goal_s]]
    cfgs += [[0.0, 0.0, 0.0, *combo]                                        # slab + distal corners
             for combo in itertools.product(*[(lo[i], hi[i]) for i in range(3, 7)])]

    js = compute + "\nconst CFG=%s;console.log(JSON.stringify(CFG.map(collide)));\n" % json.dumps(cfgs)
    jspath = tmp_path / "node_check.js"
    jspath.write_text(js)
    res = subprocess.run(["node", str(jspath)], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    js_res = json.loads(res.stdout)
    py_res = [oracle(c) for c in cfgs]
    mism = [i for i, (a, b) in enumerate(zip(js_res, py_res)) if a != b]
    assert not mism, f"{len(mism)} JS/Python mismatches, e.g. cfg {mism[0]}: {cfgs[mism[0]]}"

    # the flagship thesis, in the widget: start/goal free, distal corners in the slab all collide
    assert py_res[400] is False and py_res[401] is False                    # start, goal free
    assert all(js_res[402:]), "a distal-corner slab config is free in JS (redundancy escape?)"
