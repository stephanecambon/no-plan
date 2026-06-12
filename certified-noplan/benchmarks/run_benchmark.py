"""run_benchmark — S7 benchmark harness (gate G3', Li-Dantam anchoring).

Two jobs, both written to a fresh ``benchmarks/results/<UTC-datetime>/`` directory
(never overwritten, stamped with the git commit hash — CLAUDE.md rule 7):

1. **Scene timings** — certify each shipped scene end-to-end and record the SPEC §7
   metrics: verdict, #leaves, max tree depth, #LP solves, witness degree (lam_degree),
   engine time, and (for an exactly-verifiable planar scene) the independent exact
   *verification* time. The 4-DOF spatial S3 scene is the Li-Dantam anchor; it is
   ENGINE-PROOF + a dense-sampling soundness cross-check (exact verify is planar
   until S9), so its row carries the dense free-in-slab count, not an exact-verify time.

2. **Passive-dimension leaf-count sweep** — the cost-model micro-experiment (a mini
   version of the S9 ``feuilles(n)`` task, brought forward because the passive-dim
   blow-up is risk #1 and it bit at n=3 in S6). A parametric proximal-trap arm with
   2 ACTIVE joints (yaw, pitch) and ``k`` PASSIVE distal joints is certified at
   n = 2..5 with both axis heuristics. Through S7 this MOTIVATED A18: ``axis=oracle``
   grew 8/12/20/36 over 0..3 passive dims (it split them) while ``axis=margin`` stayed
   flat at 8. S8 IMPLEMENTED the mitigation (engine detects passive dims, keeps them as
   intervals, and reduces each cell LP to the active dims), so the sweep now VALIDATES
   it: BOTH heuristics stay flat as passive dims are added.

Run: ``python benchmarks/run_benchmark.py`` (or ``make benchmark``). Deterministic
(seeded); the only varying field is the wall-clock ``*_s`` timings.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cnp import engine, scenes, certificate as cert, verify, witness   # noqa: E402
from cnp.ratfk import RevoluteJoint, SympyRatFK                        # noqa: E402

HERE = os.path.dirname(__file__)
SCENES = os.path.join(HERE, "..", "scenes")
RESULTS = os.path.join(HERE, "results")
SEED = 0
DENSE_N = 300_000


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _commit_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=HERE, text=True).strip()
    except Exception:                                  # pragma: no cover
        return "unknown"


def _git_dirty() -> bool:
    """Whether the working tree has uncommitted changes (D15/A27): a benchmark taken on
    a dirty tree must SAY so — its commit hash does not fully describe the code that ran."""
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=HERE, text=True)
        return bool(out.strip())
    except Exception:                                  # pragma: no cover
        return False


def _max_depth(result, box) -> int:
    """Tree depth = number of midpoint bisections from the root box to a leaf, i.e.
    log2(box_width / cell_width) summed is not stored, so recover it per leaf from how
    many times each axis was halved."""
    box_w = [hi - lo for lo, hi in box]
    depth = 0
    for lf in result.leaves:
        d = 0
        for (lo, hi), bw in zip(lf.cell, box_w):
            if bw > 0:
                ratio = bw / (hi - lo)
                d += int(round(np.log2(ratio))) if ratio > 1.0 else 0
        depth = max(depth, d)
    return depth


# --------------------------------------------------------------------------- #
# 1. scene timings
# --------------------------------------------------------------------------- #

def time_scene(name: str) -> dict:
    """Certify one shipped scene and collect SPEC §7 metrics."""
    scene, budget = scenes.load(os.path.join(SCENES, f"{name}.yaml"))
    problem = scenes.build_problem(scene, max_depth=budget.max_depth)

    t0 = time.monotonic()
    result = engine.solve(problem, budget=budget.engine_budget(), axis=budget.axis)
    engine_s = time.monotonic() - t0
    counts = result.counts()

    row = {
        "scene": name, "robot_kind": scene.robot.kind, "n_unlocked": scene.robot.n,
        "axis": budget.axis, "lam_degree": scene.lam_degree,
        "verdict_engine": result.verdict, "n_leaves": counts["n_leaves"],
        "by_status": counts["status"], "max_depth": _max_depth(result, problem.box),
        "n_lp_solves": result.stats.get("n_lp_solves"), "engine_s": round(engine_s, 4),
    }

    if result.verdict == "PROOF" and scenes.is_exactly_verifiable(scene):
        # PROOF path: round to an exact certificate and TIME the independent verifier.
        c = cert.make_certificate(scene, result, verify_loop=True)
        t0 = time.monotonic()
        ok, msg = verify.verify(c)
        row["verify_exact_s"] = round(time.monotonic() - t0, 4)
        row["verdict"] = "PROOF" if ok else "ENGINE-PROOF"
        row["verify_msg"] = msg
    elif result.verdict == "PROOF":
        # ENGINE-PROOF path (spatial before S9): soundness cross-check by dense sampling.
        row["verdict"] = "ENGINE-PROOF"
        row["dense_free_in_slab"] = dense_free_in_slab(scene, problem)
        row["dense_n"] = DENSE_N
    else:
        row["verdict"] = "UNDECIDED"
    return row


def dense_free_in_slab(scene, problem) -> int:
    """Soundness cross-check (the S2/S5 ground-truth check): count seeded samples in the
    slab ``|phi|<=delta`` that are FREE. A genuine disconnection => 0 (the eye/grid does
    not prove it — rule 9; this is intention-level evidence, the engine is the arbiter)."""
    oracle = scenes.collision_oracle(scene, n_samples=30)
    delta = float(scene.delta)
    # phi = s_i barrier => slab is |s_i| <= delta; sample the box with s_i in [-d, d].
    axis = next(iter(scene.phi))               # the single active monomial, e.g. (1,0,0,0)
    i = list(axis).index(1)
    lo = [float(l) for l, _ in scene.box]
    hi = [float(h) for _, h in scene.box]
    lo[i], hi[i] = -delta, delta
    rng = np.random.default_rng(SEED)
    S = rng.uniform(lo, hi, size=(DENSE_N, scene.robot.n))
    return int(sum(1 for s in S if not oracle(s)))


# --------------------------------------------------------------------------- #
# 2. passive-dimension leaf-count sweep
# --------------------------------------------------------------------------- #

def _tr(x, y, z):
    T = np.eye(4)
    T[:3, 3] = [x, y, z]
    return T


def _trap_problem(n: int, axis_unused=None) -> engine.Problem:
    """Parametric proximal-trap arm: 2 ACTIVE joints (yaw z, pitch y) + (n-2) PASSIVE
    distal revolutes. Body = the upper arm (link 1, after pitch): it depends only on the
    2 active joints, so the (n-2) distal joints are passive — exactly the structure that
    makes axis=oracle waste depth and axis=margin stay flat."""
    joints = [RevoluteJoint("j0", _tr(0, 0, 0), np.array([0, 0, 1.0])),    # yaw  active
              RevoluteJoint("j1", _tr(0, 0, 0), np.array([0, 1.0, 0]))]    # pitch active
    L = 0.40
    for k in range(2, n):                          # passive distal revolutes
        ax = np.array([0, 1.0, 0]) if k % 2 == 0 else np.array([1.0, 0, 0])
        joints.append(RevoluteJoint(f"j{k}", _tr(L if k == 2 else 0.2, 0, 0), ax))
    fk = SympyRatFK(joints)
    body = fk.body("j1")                           # upper arm
    vbf = [[0.0, 0, 0], [L, 0, 0]]
    A = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1],
                  [-1, 0, 0], [0, -1, 0], [0, 0, -1]], float)
    b = np.array([0.20, 0.06, 0.5, -0.15, 0.06, 0.5])
    pair = engine.Pair("PANEL", body.vertex_numerators(vbf), body.D,
                       witness.Polytope(A, b))
    box = [(-0.7, 0.7), (-0.4, 0.4)] + [(-0.7, 0.7)] * (n - 2)
    phi = np.zeros((3,) * n)
    phi[(1,) + (0,) * (n - 1)] = 1.0               # phi = s0
    return engine.Problem(box=box, phi=phi, delta=0.1, pairs=[pair],
                          lam_degree="affine", max_depth=22)


def passive_dim_sweep(n_max: int = 5) -> list:
    rows = []
    for n in range(2, n_max + 1):
        prob = _trap_problem(n)
        row = {"n_joints": n, "n_active": 2, "n_passive": n - 2}
        for axis in ("margin", "oracle"):
            t0 = time.monotonic()
            res = engine.solve(prob, budget=engine.Budget(max_leaves=20000), axis=axis)
            row[axis] = {"verdict": res.verdict, "n_leaves": res.counts()["n_leaves"],
                         "s": round(time.monotonic() - t0, 3)}
        rows.append(row)
        print(f"  n={n} (passive={n-2}): "
              f"margin={row['margin']['n_leaves']}lv/{row['margin']['verdict']}  "
              f"oracle={row['oracle']['n_leaves']}lv/{row['oracle']['verdict']}")
    return rows


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def main(scene_names=("S1_relais", "S2_peigne", "S3_shoulder_elbow")) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outdir = os.path.join(RESULTS, stamp)
    os.makedirs(outdir, exist_ok=True)

    dirty = _git_dirty()
    print(f"benchmark run {stamp}  (commit {_commit_hash()[:10]}"
          f"{'  +DIRTY-TREE' if dirty else ''})")
    print("scene timings:")
    scene_rows = []
    for nm in scene_names:
        row = time_scene(nm)
        scene_rows.append(row)
        extra = (f"verify_exact={row.get('verify_exact_s')}s"
                 if "verify_exact_s" in row
                 else f"dense_free_in_slab={row.get('dense_free_in_slab')}/{row.get('dense_n')}")
        print(f"  {nm:20s} {row['verdict']:12s} {row['n_leaves']:4d} leaves  "
              f"engine={row['engine_s']}s  {extra}")

    print("passive-dimension leaf-count sweep (margin vs oracle):")
    sweep_rows = passive_dim_sweep()

    payload = {
        "stamp": stamp, "commit": _commit_hash(), "git_dirty": dirty, "seed": SEED,
        "scenes": scene_rows, "passive_dim_sweep": sweep_rows,
    }
    with open(os.path.join(outdir, "results.json"), "w") as f:
        json.dump(payload, f, indent=2)
    print(f"results written to {os.path.relpath(outdir, os.path.join(HERE, '..'))}/results.json")
    return outdir


if __name__ == "__main__":
    main()
