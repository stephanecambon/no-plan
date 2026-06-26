"""S10-quater Tâches 2-3 — guard the REAL iiwa7 flagship scene + its franc ground truth.

The frozen scene (scenes/S6_iiwa_real_shelf.yaml) mounts the frozen chain + frozen faithful
40-vertex body, separates on s1=q2 (shoulder pitch, big-lever — A43) and traps the proximal
body with an overhead shelf. A fast subset of the dense ground truth (scripts/flagship_iiwa_real_
groundtruth.py) asserts the disconnection is real and FRANC: 0 free in the slab on the distal-
extreme corners, start/goal free, redundancy invariance, and a robust (~90 mm, NOT ~6 mm) margin.
Uses the CONVEX-BODY oracle (A43), not the segment oracle. Verify-compatible scene (q*=0).
"""
from __future__ import annotations

import itertools

import numpy as np

from cnp import engine, scenes

SCENE = "scenes/S6_iiwa_real_shelf.yaml"


def test_real_flagship_scene_shape():
    sc, _ = scenes.load(SCENE)
    assert sc.robot.kind == "spatial_revolute"
    assert sc.robot.n_joints == 19 and len(sc.robot.locked) == 12 and sc.robot.n == 7
    assert sc.body_link == 7 and len(sc.hull_vertices) == 40
    assert scenes.is_exactly_verifiable(sc)                 # q*=0 ⇒ PROOF-eligible
    prob = scenes.build_problem(sc)
    views = engine.pair_views(prob)
    assert engine._global_active(views, prob) == (0, 1, 2)
    assert engine.passive_dims(prob) == (3, 4, 5, 6)


def test_real_flagship_groundtruth_franc():
    sc, _ = scenes.load(SCENE)
    orac = scenes.convex_collision_oracle(sc)
    n = len(sc.box)
    lo = np.array([float(l) for l, _ in sc.box])
    hi = np.array([float(h) for _, h in sc.box])
    delta = float(sc.delta)
    bdim = 1                                                # barrier on s1 = q2 (pitch)

    # (A) start/goal free
    assert not orac([float(x) for x in sc.start_s])
    assert not orac([float(x) for x in sc.goal_s])

    # (C) 0 free in the slab on the 2^6 corners of the non-barrier joints × s1 levels in the band
    eps = 1e-6
    others = [i for i in range(n) if i != bdim]
    for combo in itertools.product(*[(lo[i] + eps, hi[i] - eps) for i in others]):
        for s1v in np.linspace(-delta + eps, delta - eps, 5):
            s = np.zeros(n)
            s[bdim] = s1v
            for i, v in zip(others, combo):
                s[i] = v
            assert orac(s), f"free config in slab at {s}"

    # (D) redundancy invariance: distal extremes all collide at a slab point
    for dcombo in itertools.product(*[(lo[i], hi[i]) for i in range(3, n)]):
        s = np.zeros(n)
        s[3:] = dcombo
        assert orac(s)

    # franc margin: slab body-top penetrates the shelf; start/goal clear it — both robustly
    fk = scenes._body_fk(sc)
    hv = [[float(c) for c in v] for v in sc.hull_vertices]
    z0 = -float(sc.obstacles["SHELF_PANEL"][1][5])
    topz = lambda s: max(fk.eval_world_point(v, np.asarray(s, float))[2] for v in hv)
    slab_min_top = min(topz([s0, s1, s2, 0, 0, 0, 0])
                       for s0 in np.linspace(-0.7, 0.7, 5)
                       for s1 in np.linspace(-delta, delta, 3)
                       for s2 in np.linspace(-0.7, 0.7, 5))
    sg_max_top = max(topz(sc.start_s), topz(sc.goal_s))
    assert slab_min_top - z0 > 0.04, f"slab penetration {slab_min_top - z0:.3f} not franc"
    assert z0 - sg_max_top > 0.04, f"start/goal clearance {z0 - sg_max_top:.3f} not franc"
