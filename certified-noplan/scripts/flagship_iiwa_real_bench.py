"""S10-quinquies — G4' benchmark for the REAL KUKA iiwa7 flagship (scenes/S6_iiwa_real_shelf.yaml).

The HEADLINE flagship: faithful iiwa7 kinematics (frozen chain, ~2e-6 vs URDF, S10-bis) AND faithful
40-vertex convex silhouette (frozen body, ~1.7e-6, S10-ter), a FRANC pitch/shelf disconnection
(~90 mm margin, S10-quater). Certifies once, verifies independently in EXACT arithmetic, re-asserts
a fast subset of the dense CONVEX-BODY ground truth (A43), captures leaves / A32 / timings /
reduced-vs-full leaf LP rows, archives the certificate, writes a dated results dir with commit hash
+ git_dirty (rule 7). Compares MEASURED vs the V6-bis budget PREDICTION (units resolved).

G4' RÉAFFIRMÉE sur le vrai robot. Caveat A41: fidélité physique plafonnée par la précision URDF
(~2e-6), modèle interne EXACT (verify.py recompte en Fraction).

Run: ``python scripts/flagship_iiwa_real_bench.py`` -> scenes/S6_iiwa_real_shelf.cert.json
                                          + benchmarks/results/<ts>/flagship_S10_iiwa_real.json
"""
from __future__ import annotations

import itertools
import json
import os
import subprocess
import time

import numpy as np

from cnp import certificate as cert, engine, scenes, verify, witness


def _lp_rows(cell, view, prob, active_dims) -> int:
    """Bernstein LP rows (faces + lambda-nonneg) of the pair on one cell (cf. calibrate_g2)."""
    lp = witness.build_witness_lp(cell, view.verts_num, view.D, view.pair.obstacle,
                                  phi=prob.phi, delta=prob.delta,
                                  lam_degree=prob.lam_degree, active_dims=active_dims)
    return int(lp.face_Az.shape[0] + lp.lam_A.shape[0])


SCENE = "scenes/S6_iiwa_real_shelf.yaml"
CERT_OUT = "scenes/S6_iiwa_real_shelf.cert.json"
# V6-bis prediction, units RESOLVED (S10-quinquies gate): the "64" = (d+1)^k per-CONSTRAINT Bernstein
# control points (a component, and it presumed DPAD=3); the real per-constraint count is 5^3=125.
# The comparable unit is TOTAL LP rows per leaf (the "766" of the iiwa-LIKE bench); on S6 the 40-vertex
# body adds ~320 lambda rows, so the reduced leaf LP predicts ~1070 total rows.
PREDICTED = {"leaves": 8, "cost_leaf_reduced_rows": 1070, "bern_ctrl_pts_per_constraint": 125,
             "active_dims": [0, 1, 2]}


def _git():
    h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip())
    return h, dirty


def _groundtruth_subset(sc):
    """Fast re-assertion of the dense CONVEX-BODY ground truth (A43, script S10-quater): start/goal
    free, 0 free in the slab on the 2^6 non-barrier corners × 3 s1 levels, redundancy invariance,
    and the franc body-top margins vs the shelf underside (both robust)."""
    orac = scenes.convex_collision_oracle(sc)
    n = len(sc.box)
    lo = np.array([float(l) for l, _ in sc.box]); hi = np.array([float(h) for _, h in sc.box])
    delta = float(sc.delta)
    start_free = not orac([float(x) for x in sc.start_s])
    goal_free = not orac([float(x) for x in sc.goal_s])
    others = [i for i in range(n) if i != 1]
    corner_free = 0
    for combo in itertools.product(*[(lo[i] + 1e-6, hi[i] - 1e-6) for i in others]):
        for s1v in np.linspace(-delta + 1e-6, delta - 1e-6, 3):
            s = np.zeros(n); s[1] = s1v
            for i, v in zip(others, combo):
                s[i] = v
            corner_free += 0 if orac(s) else 1
    verdicts = {orac(np.concatenate([[0, 0, 0], d]))
                for d in itertools.product(*[(lo[i], hi[i]) for i in range(3, n)])}
    fk = scenes._body_fk(sc)
    hv = [[float(c) for c in v] for v in sc.hull_vertices]
    z0 = -float(sc.obstacles["SHELF_PANEL"][1][5])
    topz = lambda s: max(fk.eval_world_point(v, np.asarray(s, float))[2] for v in hv)
    slab_min_top = min(topz([s0, s1, s2, 0, 0, 0, 0])
                       for s0 in np.linspace(-0.7, 0.7, 5)
                       for s1 in np.linspace(-delta, delta, 3)
                       for s2 in np.linspace(-0.7, 0.7, 5))
    sg_max_top = max(topz(sc.start_s), topz(sc.goal_s))
    return {"start_free": start_free, "goal_free": goal_free, "slab_corner_free": corner_free,
            "redundancy_all_collide": (verdicts == {True}),
            "slab_penetration_mm": round((slab_min_top - z0) * 1000, 1),
            "startgoal_clearance_mm": round((z0 - sg_max_top) * 1000, 1)}


def main():
    sc, _ = scenes.load(SCENE)
    prob = scenes.build_problem(sc)
    views = engine.pair_views(prob)
    active = list(engine._global_active(views, prob))
    assert active == [0, 1, 2], f"active dims {active} != predicted {{0,1,2}}"

    gt = _groundtruth_subset(sc)                            # re-assert ground truth (A43)

    t0 = time.monotonic()
    res, c = cert.certify(sc, axis="margin")
    t_certify = time.monotonic() - t0
    t1 = time.monotonic()
    ok, msg = verify.verify(c)
    t_verify = time.monotonic() - t1

    coll = next(lf for lf in res.leaves if lf.status == "collision")
    cell = [(float(lo), float(hi)) for lo, hi in coll.cell]
    vw = views[0]
    reduced = _lp_rows(cell, vw, prob, vw.active)          # 3 active dims (A30 reduced)
    full = _lp_rows(cell, vw, prob, None)                  # all 7 dims (full re-resolution at export)

    cert.save(c, CERT_OUT)

    row = {
        "scene": SCENE,
        "robot": "7-DOF iiwa7 réel (chaîne+corps gelés), piège pitch-étagère, q*=0",
        "kinematics_parity_urdf": "~2e-6 (S10-bis, A41)", "body_parity": "~1.7e-6 (S10-ter)",
        "verdict": res.verdict, "verify_ok": ok, "verify_msg": msg,
        "n_active": len(active), "active_dims": active,
        "passive_dims": [i for i in range(len(sc.box)) if i not in active],
        "leaves": len(c["leaves"]), "by_status": res.stats["by_status"],
        "n_reresolve_failed": c["stats"]["n_reresolve_failed"],            # A32
        "cost_leaf_reduced_rows": reduced, "cost_leaf_full_rows": full,
        "reduction_x": round(full / reduced, 1),
        "certify_s": round(t_certify, 2), "verify_s": round(t_verify, 2),
        "groundtruth": gt, "predicted": PREDICTED,
    }
    h, dirty = _git()
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    outdir = os.path.join("benchmarks", "results", ts)
    os.makedirs(outdir, exist_ok=True)
    payload = {"session": "S10-quinquies", "gate": "G4' (réaffirmée vrai robot)",
               "commit": h, "git_dirty": dirty,
               "note": "FLAGSHIP d'EN-TÊTE : vrai KUKA iiwa7, cinematique+silhouette fideles, "
                       "deconnexion FRANC pitch/etagere certifiee PROOF + verify exact",
               "row": row}
    with open(os.path.join(outdir, "flagship_S10_iiwa_real.json"), "w") as f:
        json.dump(payload, f, indent=2, default=str)

    print(f"verdict={res.verdict} verify_ok={ok} A32={row['n_reresolve_failed']} "
          f"leaves={row['leaves']} {row['by_status']}")
    print(f"ground truth (A43): start_free={gt['start_free']} goal_free={gt['goal_free']} "
          f"slab_corner_free={gt['slab_corner_free']} redundancy_all_collide={gt['redundancy_all_collide']}")
    print(f"franc margins: slab penetration +{gt['slab_penetration_mm']} mm / "
          f"start-goal clearance +{gt['startgoal_clearance_mm']} mm")
    print(f"active_dims={active}  reduced_rows={reduced} (predit {PREDICTED['cost_leaf_reduced_rows']})  "
          f"full_rows={full}  reduction={row['reduction_x']}x")
    print(f"certify={row['certify_s']}s  verify={row['verify_s']}s")
    print(f"cert archived: {CERT_OUT}   results: {outdir}/flagship_S10_iiwa_real.json  "
          f"commit={h} dirty={dirty}")
    okall = (res.verdict == "PROOF" and ok and row["n_reresolve_failed"] == 0
             and gt["start_free"] and gt["goal_free"] and gt["slab_corner_free"] == 0
             and gt["redundancy_all_collide"] and gt["slab_penetration_mm"] > 40
             and gt["startgoal_clearance_mm"] > 40)
    return 0 if okall else 1


if __name__ == "__main__":
    raise SystemExit(main())
