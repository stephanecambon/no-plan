"""S11 — guard the two NON-flagship use-case scenes carried on the REAL iiwa7.

`scenes/usecase_binpicking_iiwa7.yaml` (bac empilé, élagage TAMP) and
`scenes/usecase_capot_surete_iiwa7.yaml` (capot de sûreté, recomptabilité) mount the SAME
frozen chain + frozen 40-vertex faithful body as the flagship S6, and use the SAME measured
mechanism: separator ``s1 = q2`` (shoulder pitch) + an OVERHEAD obstacle. That sharing is not
laziness — ``scripts/measure_iiwa7_lever.py`` measured, before any scene was written, that on
the compact real link 3 it is the ONLY franc proximal trap (+174.8 mm; base yaw and q3 roll are
NEGATIVE in all six directions, and the "cross a vertical wall" pattern is negative everywhere
because the body stays anchored at the shoulder). The cases differ by obstacle geometry, joint
limits, slab width, poses, narrative and claim.

Checked here: scene shape, the RE-MEASURED active/passive split (never presumed), a fast subset
of the dense convex-oracle ground truth (A43), the FRANC margin (>= 40 mm both sides — the
S10-ter lineage that refused ~6 mm), and the archived certificate re-verified EXACTLY with the
scene cross-check (rule 5) with ``n_reresolve_failed == 0`` (A32).
"""
from __future__ import annotations

import itertools
import json
import os

import numpy as np
import pytest

from cnp import certificate, engine, scenes, verify, viz

CASES = [("scenes/usecase_binpicking_iiwa7.yaml", "CRATE_ABOVE"),
         ("scenes/usecase_capot_surete_iiwa7.yaml", "GUARD_PANEL")]


@pytest.mark.parametrize("path,obstacle", CASES)
def test_usecase_scene_shape(path, obstacle):
    sc, _ = scenes.load(path)
    assert sc.robot.kind == "spatial_revolute"
    assert sc.robot.n_joints == 19 and len(sc.robot.locked) == 12 and sc.robot.n == 7
    assert sc.body_link == 7 and len(sc.hull_vertices) == 40      # frozen faithful body
    assert scenes.is_exactly_verifiable(sc)                       # q*=0 ⇒ PROOF-eligible
    assert sc.pairs == [obstacle]
    prob = scenes.build_problem(sc)
    views = engine.pair_views(prob)
    assert engine._global_active(views, prob) == (0, 1, 2)        # RE-MEASURED, not presumed
    assert engine.passive_dims(prob) == (3, 4, 5, 6)              # redundancy is powerless
    assert viz._barrier_dim(sc) == 1                              # separator = s1 = q2 pitch
    kinds = [n.split(" (")[0] for n, _, _ in viz.joint_limits_deg(sc)]
    assert kinds[1] == "tangage", "the separator must read as shoulder PITCH (A25/S10-quater)"


@pytest.mark.parametrize("path,obstacle", CASES)
def test_usecase_groundtruth_franc(path, obstacle):
    sc, _ = scenes.load(path)
    orac = scenes.convex_collision_oracle(sc)
    n = len(sc.box)
    lo = np.array([float(l) for l, _ in sc.box])
    hi = np.array([float(h) for _, h in sc.box])
    delta = float(sc.delta)
    bdim = 1

    assert not orac([float(x) for x in sc.start_s])
    assert not orac([float(x) for x in sc.goal_s])

    # 0 free in the slab on the 2^6 corners of the non-barrier joints x s1 levels in the band
    eps = 1e-6
    others = [i for i in range(n) if i != bdim]
    for combo in itertools.product(*[(lo[i] + eps, hi[i] - eps) for i in others]):
        for s1v in np.linspace(-delta + eps, delta - eps, 5):
            s = np.zeros(n)
            s[bdim] = s1v
            for i, v in zip(others, combo):
                s[i] = v
            assert orac(s), f"free config in slab at {s}"

    # redundancy invariance: the 2^4 distal extremes all collide at a slab point
    for dcombo in itertools.product(*[(lo[i], hi[i]) for i in range(3, n)]):
        s = np.zeros(n)
        s[3:] = dcombo
        assert orac(s)

    # FRANC margin both sides (>= 40 mm) — the S10-ter lineage refused ~6 mm
    fk = scenes._body_fk(sc)
    hv = [[float(c) for c in v] for v in sc.hull_vertices]
    z0 = -float(sc.obstacles[obstacle][1][5])              # underside (face -z: -z <= b5)
    def topz(s):
        return max(fk.eval_world_point(v, np.asarray(s, float))[2] for v in hv)
    slab_min_top = min(topz([a, s1, c, 0, 0, 0, 0])
                       for a in np.linspace(lo[0], hi[0], 5)
                       for c in np.linspace(lo[2], hi[2], 5)
                       for s1 in np.linspace(-delta, delta, 3))
    sg_max_top = max(topz(sc.start_s), topz(sc.goal_s))
    assert slab_min_top - z0 > 0.04, f"slab penetration {slab_min_top - z0:.3f} not franc"
    assert z0 - sg_max_top > 0.04, f"start/goal clearance {z0 - sg_max_top:.3f} not franc"


@pytest.mark.parametrize("path,obstacle", CASES)
def test_usecase_certificate_verifies_exactly(path, obstacle):
    """Rule 5: the ARCHIVED certificate is what the reader re-counts — re-verify it here in
    exact arithmetic, with the scene cross-check, and assert A32 = 0."""
    cert_path = path.replace(".yaml", ".cert.json")
    assert os.path.exists(cert_path), f"missing archived certificate {cert_path}"
    cert = certificate.load(cert_path)
    ok, msg = verify.verify(cert)
    assert ok, msg
    sc, _ = scenes.load(path)
    match, why = scenes.scene_matches_cert(sc, cert)
    assert match, why
    assert cert["stats"]["n_reresolve_failed"] == 0            # A32
    assert cert["stats"]["n_embed_rejected"] == 0              # A32 étendu (S12/L6)
    assert cert["stats"]["n_collision"] >= 1
    assert cert["obstacles"].keys() == {obstacle}
