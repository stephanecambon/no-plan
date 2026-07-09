"""S10-quinquies — A40 invariant for the REAL iiwa7 flagship interactive HTML (hull body).

The widget shows INTENTION (rule 11), but its JS collision logic must not LIE: it must reproduce
the Python CONVEX-BODY oracle EXACTLY (A43 — the faithful 40-vertex silhouette, NOT a segment).
This test exports the hull interactive, extracts its pure FK+GJK-collision JS layer (everything
before the 2-D drawing marker), runs it under node on seeded configs, and asserts byte-for-byte
verdict agreement with ``scenes.convex_collision_oracle`` — including the slab and the 2^6
distal-corner configs where "robust to redundancy" must hold.

node is optional: the node test SKIPS (never fails) when node is absent, like the network tests.
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
FLAGSHIP = os.path.join(SCENES, "S6_iiwa_real_shelf.yaml")


def _export(tmp_path):
    sc, _ = scenes.load(FLAGSHIP)
    prob = scenes.build_problem(sc)
    active = engine._global_active(engine.pair_views(prob), prob)
    out = tmp_path / "real_flagship.html"
    viz.export_interactive_html(sc, str(out), title="S6 vrai iiwa7",
                                active_dims=active, body_mode="hull")
    return sc, out.read_text()


def test_real_interactive_structure(tmp_path):
    """Self-contained; 19 chain joints (12 locked, 7 sliders), 40-vertex hull body, barrier on
    s1=q2 (pitch), active/passive baked, A25 limits with CORRECTED physical labels (q2=tangage)."""
    sc, h = _export(tmp_path)
    assert "src=" not in h and "http://" not in h and "https://" not in h    # zero external refs
    assert "function gjk(" in h and "function collide(" in h and "bodyWorld(" in h
    data = json.loads(h.split("const SC = ", 1)[1].split(";\n", 1)[0])
    assert len(data["joints"]) == 19
    assert sum(j["locked"] is not None for j in data["joints"]) == 12         # 12 locked
    assert sum(j["locked"] is None for j in data["joints"]) == 7              # 7 sliders
    assert data["body_link"] == 7 and len(data["hull"]) == 40                 # faithful 40-vertex body
    assert data["barrier_dim"] == 1                                          # separator = s1 = q2 pitch
    assert data["active_dims"] == [0, 1, 2] and data["passive_dims"] == [3, 4, 5, 6]
    assert len(data["limits_deg"]) == 7                                       # A25, one per slider
    # CORRECTED physical labels (finding S10-quater): the 7 DOF read yaw,pitch,yaw,pitch,... and
    # the unlocked-joint names sit at chain slots 1,4,7,9,12,14,17 with the pitch at q2 (slot 4).
    unlocked_names = [data["joint_names"][i]
                      for i, j in enumerate(data["joints"]) if j["locked"] is None]
    assert [n.split()[0] for n in unlocked_names] == \
        ["lacet", "tangage", "lacet", "tangage", "lacet", "tangage", "lacet"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_real_interactive_js_matches_convex_oracle(tmp_path):
    """A40 INVARIANT: the JS FK + GJK(hull, box) reproduces convex_collision_oracle EXACTLY on
    seeded configs — uniform, start/goal, and the slab × 2^6 distal-extreme corners (redundancy).
    GJK on the faithful 40-vertex hull, NOT segment sampling (A43)."""
    sc, h = _export(tmp_path)
    compute = h.split("<script>", 1)[1].split("// ── 2-D convex hull", 1)[0]
    oracle = scenes.convex_collision_oracle(sc)
    n = len(sc.box)
    lo = np.array([float(l) for l, _ in sc.box])
    hi = np.array([float(hh) for _, hh in sc.box])
    delta = float(sc.delta)

    rng = np.random.default_rng(20260709)
    cfgs = [list(rng.uniform(lo, hi)) for _ in range(400)]
    cfgs += [[float(x) for x in sc.start_s], [float(x) for x in sc.goal_s]]   # idx 400, 401
    others = [i for i in range(n) if i != 1]                                  # non-barrier joints
    for combo in itertools.product(*[(lo[i] + 1e-6, hi[i] - 1e-6) for i in others]):
        for s1v in np.linspace(-delta + 1e-6, delta - 1e-6, 3):
            s = [0.0] * n
            s[1] = s1v
            for i, v in zip(others, combo):
                s[i] = v
            cfgs.append(list(s))                                             # slab corners, idx >= 402

    js = compute + "\nconst CFG=%s;console.log(JSON.stringify(CFG.map(collide)));\n" % json.dumps(cfgs)
    jspath = tmp_path / "node_check.js"
    jspath.write_text(js)
    res = subprocess.run(["node", str(jspath)], capture_output=True, text=True, timeout=180)
    assert res.returncode == 0, res.stderr
    js_res = json.loads(res.stdout)
    py_res = [oracle(c) for c in cfgs]
    mism = [i for i, (a, b) in enumerate(zip(js_res, py_res)) if a != b]
    assert not mism, f"{len(mism)} JS/Python mismatches, e.g. cfg {mism[0]}: {cfgs[mism[0]]}"

    # the flagship thesis, in the widget: start/goal free, every distal-corner slab config collides
    assert py_res[400] is False and py_res[401] is False                     # start, goal free
    assert all(js_res[402:]), "a distal-corner slab config is free in JS (redundancy escape?)"
    assert len(js_res[402:]) == 2 ** 6 * 3                                    # 2^6 corners × 3 levels
