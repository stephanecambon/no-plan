"""S9b — PLAUSIBILITY sanity-check for the use-case portfolio scenes (NOT a certification).

For a scene YAML this script answers, with a dense SEEDED ground truth (rule 9 / micro-canal
lesson), the only question S9b is allowed to answer: *is this scene a plausible disconnection
worth certifying later?* — never *is it proven infeasible?* (that is S10/S11, via `cnp certify`
+ `cnp verify` in exact arithmetic).

Checks (all seeded, reproducible):
  - active dims of each collision pair (the PROXIMAL-trap claim: few active dims, A18/A30);
  - start/goal collision-free;
  - 0 free in the slab |phi|<=delta over a dense UNIFORM grid;
  - 0 free in the slab over a CORNER-BIASED grid (S9f lesson: uniform grids miss the
    measure-tiny free pockets at the box corners that sank the S9e leaky scene);
  - free on BOTH sides of the slab (a genuine two-component disconnection, not a dead end).
A scene that does NOT pass is a RESULT, not a failure: it is reported, not hidden.

Run: ``python scripts/usecase_sanity.py scenes/usecase_etagere_pharma.yaml`` (add ``--aabb``
to also print the certified body's world bounding box over the slab — used to size obstacles).
"""
from __future__ import annotations

import sys

import numpy as np

from cnp import engine, scenes

GT_SEED = 90210  # S9b ground-truth seed (reproducible)


def _box_bounds(sc):
    lo = np.array([float(l) for l, _ in sc.box])
    hi = np.array([float(h) for _, h in sc.box])
    return lo, hi


def body_aabb_over_slab(sc, n=20000):
    """World AABB of the certified body segment over the slab (obstacle-sizing aid)."""
    body = scenes._body_fk(sc)
    hull = np.array([[float(c) for c in v] for v in sc.hull_vertices])
    lo, hi = _box_bounds(sc)
    delta = float(sc.delta)
    rng = np.random.default_rng(GT_SEED + 7)
    pts = []
    for _ in range(n):
        s = rng.uniform(lo, hi)
        s[0] = rng.uniform(-delta, delta)  # inside the slab on the barrier axis s0
        for v in hull:
            p = body.eval_world_point(v, s)
            # also sample along the segment for a tight hull
        p0 = body.eval_world_point(hull[0], s)
        p1 = body.eval_world_point(hull[-1], s)
        for t in np.linspace(0, 1, 6):
            pts.append(p0 * (1 - t) + p1 * t)
    P = np.array(pts)
    return P.min(axis=0), P.max(axis=0)


def sanity(sc, n=30000, n_side=4000):
    orac = scenes.collision_oracle(sc, n_samples=60)
    lo, hi = _box_bounds(sc)
    delta = float(sc.delta)
    rng = np.random.default_rng(GT_SEED)

    start_free = not orac([float(x) for x in sc.start_s])
    goal_free = not orac([float(x) for x in sc.goal_s])

    # dense UNIFORM slab
    free_uniform = 0
    for _ in range(n):
        s = rng.uniform(lo, hi)
        s[0] = rng.uniform(-delta, delta)
        if not orac(s):
            free_uniform += 1

    # CORNER-BIASED slab (S9f): push the non-barrier dims toward their box corners
    free_corner = 0
    for _ in range(n):
        s = np.where(rng.random(len(lo)) < 0.5, lo, hi) * rng.uniform(0.9, 1.0, len(lo))
        s[0] = rng.uniform(-delta, delta)
        if not orac(s):
            free_corner += 1

    # two-sided free (left and right of the slab on s0)
    free_left = sum(1 for _ in range(n_side)
                    if not orac(np.concatenate(([rng.uniform(lo[0], -3 * delta)],
                                                rng.uniform(lo[1:], hi[1:])))))
    free_right = sum(1 for _ in range(n_side)
                     if not orac(np.concatenate(([rng.uniform(3 * delta, hi[0])],
                                                 rng.uniform(lo[1:], hi[1:])))))
    return {"start_free": start_free, "goal_free": goal_free,
            "free_in_slab_uniform": free_uniform, "free_in_slab_corner": free_corner,
            "free_left": free_left, "free_right": free_right,
            "n_slab": n, "n_side": n_side}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = args[0]
    sc, _ = scenes.load(path)
    prob = scenes.build_problem(sc)
    views = engine.pair_views(prob)
    active = engine._global_active(views, prob)

    print(f"=== PLAUSIBILITÉ (PAS une certification) — {path} ===")
    print(f"DOF débloqués : {len(sc.box)}   |   dims actives globales : {active} "
          f"({len(active)})   [certification = S10/S11]")
    for vw in views:
        print(f"  paire {getattr(vw.pair, 'name', '?'):12s} dims actives = {vw.active}")

    if "--aabb" in sys.argv:
        amin, amax = body_aabb_over_slab(sc)
        print("  body AABB over slab : "
              f"x[{amin[0]:.3f},{amax[0]:.3f}] y[{amin[1]:.3f},{amax[1]:.3f}] "
              f"z[{amin[2]:.3f},{amax[2]:.3f}]")

    r = sanity(sc)
    ok = (r["start_free"] and r["goal_free"]
          and r["free_in_slab_uniform"] == 0 and r["free_in_slab_corner"] == 0
          and r["free_left"] > 0 and r["free_right"] > 0)
    print(f"  start libre : {r['start_free']}   goal libre : {r['goal_free']}")
    print(f"  libre dans la dalle (uniforme {r['n_slab']}) : {r['free_in_slab_uniform']}  "
          f"(0 attendu)")
    print(f"  libre dans la dalle (biaisé-coins {r['n_slab']}) : {r['free_in_slab_corner']}  "
          f"(0 attendu — leçon S9f)")
    print(f"  libre à gauche : {r['free_left']}/{r['n_side']}   "
          f"libre à droite : {r['free_right']}/{r['n_side']}   (>0 des deux côtés attendu)")
    print(f"  ==> PLAUSIBLE : {ok}   (déconnexion candidate digne d'une certification S10/S11)"
          if ok else f"  ==> NON PLAUSIBLE EN L'ÉTAT : {ok}   (résultat à documenter, pas un échec)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
