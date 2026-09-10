"""S10-quater Tâche 3 (généralisé S11) — dense seeded ground truth for ANY of the REAL iiwa7
scenes, BEFORE certification (règle 9): the flagship shelf (S6) and the two S11 use cases
(bac empilé, capot de sûreté). Uses the CONVEX-BODY oracle (A43): the faithful 40-vertex
silhouette needs `scenes.convex_collision_oracle` (LP), NOT the segment-sampling
`collision_oracle`. The obstacle name, the barrier dim and the box are all read FROM THE SCENE
(nothing is hardcoded), so the same checks guard the three cases identically.

Barrier is on s1 = q2 (shoulder PITCH, the big-lever separator — A43; base-yaw is marginal on
the compact real link 3). slab {|s1|<=delta} = arm straight up = proximal body hits the overhead
shelf; start/goal = q2 tilted = body low, clears. A plausibility step, NOT a proof (the proof is
`cnp certify` PROOF + `cnp verify` OK exact).

Checks (seeded, reproducible):
  (0) pair_views ⟹ active dims = {0,1,2}, distal {3,4,5,6} PASSIVE for the pair ;
  (A) start/goal free ;
  (B) 0 free in slab |s1|<=delta on a dense UNIFORM sample ;
  (C) 0 free in slab on the 2^6 CORNERS of the non-barrier joints × s1 levels in the band
      (distal extremes explicitly swept, leçon S9f) ;
  (D) REDUNDANCY INVARIANCE: at a slab point, the 2^4 distal extremes all give the SAME collision
      verdict (the proximal body does not depend on the distal joints) ;
  (E) free on BOTH sides of the slab.
  + the measured franc separation MARGIN ; A25 joint limits in degrees.

Run: ``python scripts/flagship_iiwa_real_groundtruth.py [scene.yaml]``  (défaut : le flagship S6).
"""
from __future__ import annotations

import itertools
import sys

import numpy as np

from cnp import engine, scenes, viz

GT_SEED = 100_011


def _barrier_dim(sc):
    """The single dim phi depends on (linear single-var barrier: exactly one nonzero coeff dim)."""
    dims = {i for e, c in sc.phi.items() for i in range(len(e)) if e[i] and c != 0}
    assert len(dims) == 1, f"expected a single-variable barrier, depends on {dims}"
    return dims.pop()


def _ground_truth(path, nb):
    sc, _ = scenes.load(path)
    prob = scenes.build_problem(sc)
    views = engine.pair_views(prob)
    active = engine._global_active(views, prob)
    n = len(sc.box)
    passive = tuple(i for i in range(n) if i not in active)
    bdim = _barrier_dim(sc)

    print(f"=== VÉRITÉ-TERRAIN DENSE (oracle CORPS-CONVEXE, plausibilité PAS certification) — {path} ===")
    print(f"DOF débloqués : {n}   verrous : {len(sc.robot.locked_angles)}   corps : {len(sc.hull_vertices)} sommets")
    print(f"(0) dims actives = {active} ({len(active)})   distaux passifs = {passive}   barrière sur s{bdim} (q{bdim+1})")
    assert active == (0, 1, 2) and passive == (3, 4, 5, 6), (active, passive)
    assert bdim == 1, f"barrière attendue sur s1 (q2 pitch), obtenu s{bdim}"
    obstacle = sc.pairs[0]
    print(f"    obstacle certifié : {obstacle!r}")

    print("    A25 limites (degrés, q=2·atan(s)) :")
    for nm, lo_, hi_ in viz.joint_limits_deg(sc):
        print(f"      {nm:14s} [{lo_:7.1f}°, {hi_:7.1f}°]")

    orac = scenes.convex_collision_oracle(sc)
    lo = np.array([float(l) for l, _ in sc.box])
    hi = np.array([float(h) for _, h in sc.box])
    delta = float(sc.delta)
    rng = np.random.default_rng(GT_SEED)

    # (A)
    a_start = not orac([float(x) for x in sc.start_s])
    a_goal = not orac([float(x) for x in sc.goal_s])

    # (B) dense uniform in slab
    free_unif = 0
    for _ in range(nb):
        s = rng.uniform(lo, hi)
        s[bdim] = rng.uniform(-delta, delta)
        if not orac(s):
            free_unif += 1

    # (C) corners of the 6 non-barrier joints × s1 levels in the band
    eps = 1e-6
    others = [i for i in range(n) if i != bdim]
    s1_levels = np.linspace(-delta + eps, delta - eps, 7)
    free_corner = 0
    n_corner = 0
    for combo in itertools.product(*[(lo[i] + eps, hi[i] - eps) for i in others]):
        for s1v in s1_levels:
            s = np.zeros(n)
            s[bdim] = s1v
            for i, v in zip(others, combo):
                s[i] = v
            n_corner += 1
            if not orac(s):
                free_corner += 1

    # (D) redundancy invariance: fix active (0,1,2) at a slab point, sweep 2^4 distal extremes
    verdicts = set()
    for dcombo in itertools.product(*[(lo[i], hi[i]) for i in range(3, n)]):
        s = np.zeros(n)
        s[3:] = dcombo
        verdicts.add(orac(s))
    redundancy_invariant = (verdicts == {True})

    # (E) two-sided on the barrier dim
    NS = 4000
    def side(a, b):
        c = 0
        for _ in range(NS):
            s = rng.uniform(lo, hi)
            s[bdim] = rng.uniform(a, b)
            if not orac(s):
                c += 1
        return c
    free_left = side(lo[bdim], -3 * delta)
    free_right = side(3 * delta, hi[bdim])

    # franc separation margin (body-top z vs shelf underside)
    fk = scenes._body_fk(sc)
    hv = [[float(c) for c in v] for v in sc.hull_vertices]
    z0 = -float(sc.obstacles[obstacle][1][5])              # underside (face -z: -z <= b5)
    def topz(s):
        return max(fk.eval_world_point(v, np.asarray(s, float))[2] for v in hv)
    slab_min_top = min(topz([s0, s1, s2, 0, 0, 0, 0])
                       for s0 in np.linspace(lo[0], hi[0], 7)
                       for s1 in np.linspace(-delta, delta, 5)
                       for s2 in np.linspace(lo[2], hi[2], 7))
    sg_max_top = max(topz([float(x) for x in sc.start_s]), topz([float(x) for x in sc.goal_s]))

    print(f"(A) start libre : {a_start}   goal libre : {a_goal}")
    print(f"(B) libre dans la dalle (uniforme {nb}) : {free_unif}   (0 attendu)")
    print(f"(C) libre dans la dalle (coins {n_corner} = 2^6 × {len(s1_levels)} s1) : {free_corner}   (0 attendu)")
    print(f"(D) INVARIANCE REDONDANCE : 2^4=16 extrêmes distaux ⟹ verdicts {verdicts}   (tous collision = {redundancy_invariant})")
    print(f"(E) libre à gauche : {free_left}/{NS}   libre à droite : {free_right}/{NS}")
    print(f"MARGE FRANCHE : {obstacle} dessous z0={z0:.3f} ; slab min top-corps={slab_min_top:.3f} (+{slab_min_top-z0:.3f} pénétration) ; "
          f"start/goal max top-corps={sg_max_top:.3f} ({z0-sg_max_top:+.3f} dégagement)")

    ok = (a_start and a_goal and free_unif == 0 and free_corner == 0
          and redundancy_invariant and free_left > 0 and free_right > 0
          and slab_min_top > z0 and sg_max_top < z0)
    print(f"==> PLAUSIBLE (digne de certification) : {ok}" if ok
          else f"==> NON PLAUSIBLE EN L'ÉTAT : {ok}")
    # [S14, D-P2-B] the same counts as a record, so they live in a dated JSON, not the journal
    return {"start_free": a_start, "goal_free": a_goal,
            "n_uniform_in_slab": nb, "free_in_slab": free_unif,
            "n_slab_corners": n_corner, "free_at_slab_corners": free_corner,
            "slab_corner_construction": f"2^{len(others)} extremes of the non-barrier joints "
                                        f"x {len(s1_levels)} barrier levels",
            "n_distal_extreme_combinations": 2 ** (n - 3),
            "redundancy_all_collide": redundancy_invariant,
            "n_per_side": NS, "free_left": free_left, "free_right": free_right,
            "obstacle": obstacle, "obstacle_underside_z_m": round(z0, 4),
            "slab_min_body_top_m": round(float(slab_min_top), 4),
            "startgoal_max_body_top_m": round(float(sg_max_top), 4),
            "slab_penetration_mm": round(float(slab_min_top - z0) * 1000, 1),
            "startgoal_clearance_mm": round(float(z0 - sg_max_top) * 1000, 1),
            "margin_grid": "q1 x q2-in-slab x q3 = 7 x 5 x 7, distal joints at 0",
            "seed": GT_SEED, "plausible": bool(ok)}


def ground_truth(path="scenes/S6_iiwa_real_shelf.yaml", nb=40_000, verbose=True) -> dict:
    """Run every check above on ``path`` and return the counts as a dict (S14)."""
    if verbose:
        return _ground_truth(path, nb)
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        return _ground_truth(path, nb)


def main(nb=40_000):
    path = sys.argv[1] if len(sys.argv) > 1 else "scenes/S6_iiwa_real_shelf.yaml"
    return 0 if ground_truth(path, nb)["plausible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
