"""S10 — dense seeded ground truth for the 7-DOF flagship, BEFORE certification (règle 9).

Denser than the S9b plausibility check, and adds the thesis-specific test: NO setting of the
distal joints {3,4,5,6} frees the proximal body (link 2) — "portée 7-DOF robuste à la redondance".
A plausibility step, NOT a proof: the proof is `cnp certify` (PROOF) + `cnp verify` (OK exact).

Checks (seeded, reproducible):
  (0) pair_views ⟹ dims actives = {0,1,2}, distaux {3,4,5,6} prouvés PASSIFS pour la paire ;
  (A) start/goal libres ;
  (B) 0 libre dans la dalle |phi|<=delta sur un grand échantillon UNIFORME ;
  (C) 0 libre dans la dalle sur les 2^6=64 COINS des joints non-barrière {1..6} × niveaux de s0
      dans la bande (extrêmes distaux explicitement balayés, leçon S9f) ;
  (D) INVARIANCE À LA REDONDANCE : à (s0,s1,s2) fixés dans la dalle, les 2^4=16 combinaisons
      d'extrêmes distaux {3,4,5,6} donnent TOUTES le même verdict collision (le corps ne dépend
      pas des distaux) ;
  (E) libre des DEUX côtés de la dalle (deux composantes).
  + A25 : limites des 7 joints en degrés.

Run: ``python scripts/flagship_groundtruth.py [scenes/S5_iiwa_shelf.yaml]``  (exit 0 ⟺ plausible).
"""
from __future__ import annotations

import itertools
import sys

import numpy as np

from cnp import engine, scenes, viz

GT_SEED = 100_010


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "scenes/S5_iiwa_shelf.yaml"
    sc, _ = scenes.load(path)
    prob = scenes.build_problem(sc)
    views = engine.pair_views(prob)
    active = engine._global_active(views, prob)
    n = len(sc.box)
    passive = tuple(i for i in range(n) if i not in active)

    print(f"=== VÉRITÉ-TERRAIN DENSE (plausibilité, PAS une certification) — {path} ===")
    print(f"DOF débloqués : {n}   verrous : {len(sc.robot.locked_angles)}   "
          f"(cas de base G3'b ⟺ 0 verrou)")
    print(f"(0) dims actives = {active} ({len(active)})   distaux passifs = {passive}")
    for vw in views:
        print(f"    paire {getattr(vw.pair, 'name', '?')}: active = {vw.active}")
    assert active == (0, 1, 2), f"dims actives attendues {{0,1,2}}, obtenu {active}"
    assert passive == (3, 4, 5, 6), f"distaux passifs attendus {{3,4,5,6}}, obtenu {passive}"

    print("    A25 limites (degrés, q=2·atan(s)) :")
    for nm, lo, hi in viz.joint_limits_deg(sc):
        print(f"      {nm:14s} [{lo:7.1f}°, {hi:7.1f}°]")

    orac = scenes.collision_oracle(sc, n_samples=64)
    lo = np.array([float(l) for l, _ in sc.box])
    hi = np.array([float(h) for _, h in sc.box])
    delta = float(sc.delta)
    rng = np.random.default_rng(GT_SEED)

    # (A)
    a_start = not orac([float(x) for x in sc.start_s])
    a_goal = not orac([float(x) for x in sc.goal_s])

    # (B) dense uniform in slab
    NB = 120_000
    free_unif = 0
    for _ in range(NB):
        s = rng.uniform(lo, hi)
        s[0] = rng.uniform(-delta, delta)
        if not orac(s):
            free_unif += 1

    # (C) corners of the 6 non-barrier joints {1..6} x s0 levels in the band
    eps = 1e-6
    s0_levels = np.linspace(-delta + eps, delta - eps, 7)
    free_corner = 0
    n_corner = 0
    for combo in itertools.product(*[(lo[i] + eps, hi[i] - eps) for i in range(1, n)]):
        for s0v in s0_levels:
            s = np.array([s0v, *combo])
            n_corner += 1
            if not orac(s):
                free_corner += 1

    # (D) redundancy invariance: fix (s0,s1,s2) in slab, sweep 2^4 distal extremes
    base = np.zeros(n)  # s0=s1=s2=0 (a slab point), distal varied
    verdicts = set()
    for dcombo in itertools.product(*[(lo[i], hi[i]) for i in range(3, n)]):
        s = base.copy()
        s[3:] = dcombo
        verdicts.add(orac(s))
    redundancy_invariant = (verdicts == {True})  # all collide, none free

    # (E) two-sided
    NS = 6000
    free_left = sum(1 for _ in range(NS)
                    if not orac(np.concatenate(([rng.uniform(lo[0], -3 * delta)],
                                                rng.uniform(lo[1:], hi[1:])))))
    free_right = sum(1 for _ in range(NS)
                     if not orac(np.concatenate(([rng.uniform(3 * delta, hi[0])],
                                                 rng.uniform(lo[1:], hi[1:])))))

    print(f"(A) start libre : {a_start}   goal libre : {a_goal}")
    print(f"(B) libre dans la dalle (uniforme {NB}) : {free_unif}   (0 attendu)")
    print(f"(C) libre dans la dalle (coins {n_corner} = 2^6 × {len(s0_levels)} s0) : "
          f"{free_corner}   (0 attendu)")
    print(f"(D) INVARIANCE REDONDANCE : 2^4=16 extrêmes distaux ⟹ verdicts {verdicts}   "
          f"(tous en collision = {redundancy_invariant})")
    print(f"(E) libre à gauche : {free_left}/{NS}   libre à droite : {free_right}/{NS}")

    ok = (a_start and a_goal and free_unif == 0 and free_corner == 0
          and redundancy_invariant and free_left > 0 and free_right > 0)
    print(f"==> PLAUSIBLE (digne de certification) : {ok}" if ok
          else f"==> NON PLAUSIBLE EN L'ÉTAT : {ok} (résultat à documenter)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
