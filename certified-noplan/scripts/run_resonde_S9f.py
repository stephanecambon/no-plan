"""S9f — consolidate the re-measured wall (L0a) into a reproducible results dir (rule 7).

Runs the sealed-scene re-sonde k=3..7 at FULL protocol (PROOF + exact verify + A32=0) and an
ENGINE-ONLY, time-bounded k=8 (the ~2.3M-row LP frontier: exact verify there exceeds a single
laptop run, so we report the engine verdict + leaves + cost/leaf only). Stamps commit + git_dirty.

Run: ``python scripts/run_resonde_S9f.py`` → writes benchmarks/results/<ts>/wall_resonde_S9f.json."""
from __future__ import annotations

import json
import os
import subprocess
import time
from fractions import Fraction as F

from cnp import engine, scenes

import wall_resonde_S9f as rs


def _git():
    h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip())
    return h, dirty


def engine_only(k: int, s0hi, max_time_s=300) -> dict:
    """k=8 frontier point: certify (engine) only, no exact verify (it exceeds a laptop run)."""
    sc = rs.build_scene_sealed(k, s0hi=s0hi); sc.lam_degree = "affine"
    prob = scenes.build_problem(sc); prob.max_depth = 60
    views = engine.pair_views(prob)
    active = list(engine._global_active(views, prob))
    gt = rs.ground_truth_sealed(sc, n=3000)
    assert len(active) == k and gt["start_free"] and gt["goal_free"]
    assert gt["free_in_slab"] == 0 and gt["free_in_slab_corner"] == 0
    t0 = time.monotonic()
    res = engine.solve(prob, axis="margin",
                       budget=engine.Budget(max_leaves=10000, max_time_s=max_time_s))
    dt = time.monotonic() - t0
    coll = next((lf for lf in res.leaves if lf.status == "collision"), None)
    rows = rs._lp_rows([(float(l), float(h)) for l, h in coll.cell], views[0], prob,
                       views[0].active) if coll else None
    return {"k": k, "n_active_detected": len(active), "verdict": res.verdict,
            "termination": res.stats.get("termination"),
            "max_depth_reached": res.stats.get("max_depth_reached"),
            "leaves": res.stats["n_leaves"], "by_status": res.stats["by_status"],
            "engine_s": round(dt, 1), "cost_leaf_reduced_rows": rows,
            "exact_verify": "not run (>= laptop single-run budget at ~2.3M rows)",
            "ground_truth": gt}


def main():
    h, dirty = _git()
    rows = rs.run([3, 4, 5, 6, 7])          # full protocol, s0hi=4/5
    rows.append(engine_only(8, s0hi=F(1, 1)))
    print(rs._fmt({**rows[-1], "max_depth_limit": 60,
                   "cost_leaf_full_rows": None, "verify_ok": "-", "n_reresolve_failed": "-"})
          if False else f"k=8 (engine-only): {json.dumps(rows[-1], default=str)}")
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = os.path.join("benchmarks", "results", ts)
    os.makedirs(out, exist_ok=True)
    payload = {"session": "S9f", "commit": h, "git_dirty": dirty,
               "scene": "sealed wall (Bernstein-watertight), affine witness, axis=margin",
               "budget": {"max_leaves": rs.MAX_LEAVES, "max_time_s": rs.MAX_TIME_S, "max_depth": rs.MAX_DEPTH},
               "rows": rows}
    path = os.path.join(out, "wall_resonde_S9f.json")
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print("wrote", path, "commit", h, "dirty", dirty)


if __name__ == "__main__":
    main()
