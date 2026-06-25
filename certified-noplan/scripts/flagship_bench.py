"""S10 — G4' benchmark for the 7-DOF flagship (scenes/S5_iiwa_shelf.yaml, iiwa-LIKE bench A21).

The FIRST non-synthetic 7-DOF certificate of the project (vs synthetic S9d / sealed S9f).
Certifies once, verifies independently in exact arithmetic, captures leaves / A32 / timings /
reduced-vs-full leaf LP rows, archives the certificate, and writes a dated results dir with the
commit hash + git_dirty (rule 7). Compares MEASURED vs the V6 budget PREDICTION.

Run: ``python scripts/flagship_bench.py`` -> scenes/S5_iiwa_shelf.cert.json
                                          + benchmarks/results/<ts>/flagship_S10_iiwa_like.json
"""
from __future__ import annotations

import json
import os
import subprocess
import time

from cnp import certificate as cert, engine, scenes, verify, witness


def _lp_rows(cell, view, prob, active_dims) -> int:
    """Bernstein LP rows (faces + lambda-nonneg) of the pair on one cell (cf. calibrate_g2)."""
    lp = witness.build_witness_lp(cell, view.verts_num, view.D, view.pair.obstacle,
                                  phi=prob.phi, delta=prob.delta,
                                  lam_degree=prob.lam_degree, active_dims=active_dims)
    return int(lp.face_Az.shape[0] + lp.lam_A.shape[0])


SCENE = "scenes/S5_iiwa_shelf.yaml"
CERT_OUT = "scenes/S5_iiwa_shelf.cert.json"
PREDICTED = {"leaves": 8, "cost_leaf_reduced_rows": 766, "active_dims": [0, 1, 2]}


def _git():
    h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip())
    return h, dirty


def main():
    sc, _ = scenes.load(SCENE)
    prob = scenes.build_problem(sc)
    views = engine.pair_views(prob)
    active = list(engine._global_active(views, prob))
    assert active == [0, 1, 2], f"active dims {active} != predicted {{0,1,2}}"

    t0 = time.monotonic()
    res, c = cert.certify(sc, axis="margin")
    t_certify = time.monotonic() - t0
    t1 = time.monotonic()
    ok, msg = verify.verify(c)
    t_verify = time.monotonic() - t1

    coll = next(lf for lf in res.leaves if lf.status == "collision")
    cell = [(float(lo), float(hi)) for lo, hi in coll.cell]
    vw = views[0]
    reduced = _lp_rows(cell, vw, prob, vw.active)        # 3 active dims
    full = _lp_rows(cell, vw, prob, None)               # all 7 dims (pre-reduction)

    cert_save = cert  # certificate module exposes save
    cert.save(c, CERT_OUT)

    row = {
        "scene": SCENE, "robot": "iiwa-LIKE (bac technique A21), 7-DOF tous libres, q*=0",
        "verdict": res.verdict, "verify_ok": ok,
        "n_active": len(active), "active_dims": active,
        "passive_dims": [i for i in range(len(sc.box)) if i not in active],
        "leaves": len(c["leaves"]), "by_status": res.stats["by_status"],
        "n_reresolve_failed": c["stats"]["n_reresolve_failed"],            # A32
        "cost_leaf_reduced_rows": reduced, "cost_leaf_full_rows": full,
        "reduction_x": round(full / reduced, 1),
        "certify_s": round(t_certify, 2), "verify_s": round(t_verify, 2),
        "predicted": PREDICTED,
    }
    h, dirty = _git()
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    outdir = os.path.join("benchmarks", "results", ts)
    os.makedirs(outdir, exist_ok=True)
    payload = {"session": "S10", "gate": "G4'", "commit": h, "git_dirty": dirty,
               "note": "premier certificat 7-DOF NON synthetique (vs S9d synthetique / S9f scelle)",
               "row": row}
    with open(os.path.join(outdir, "flagship_S10_iiwa_like.json"), "w") as f:
        json.dump(payload, f, indent=2, default=str)

    print(f"verdict={res.verdict} verify_ok={ok} A32={row['n_reresolve_failed']} "
          f"leaves={row['leaves']} {row['by_status']}")
    print(f"active_dims={active}  reduced_rows={reduced} (predit {PREDICTED['cost_leaf_reduced_rows']})  "
          f"full_rows={full}  reduction={row['reduction_x']}x")
    print(f"certify={row['certify_s']}s  verify={row['verify_s']}s")
    print(f"cert archived: {CERT_OUT}   results: {outdir}/flagship_S10_iiwa_like.json  "
          f"commit={h} dirty={dirty}")
    return 0 if (res.verdict == "PROOF" and ok and row["n_reresolve_failed"] == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
