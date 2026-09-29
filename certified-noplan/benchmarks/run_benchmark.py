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
        # [A32] decision<->certificate dissonance: collision-decided leaves that failed
        # full-dim re-resolution (expected 0; a positive count is a benign-but-silent cost).
        row["n_reresolve_failed"] = c["stats"]["n_reresolve_failed"]
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


def dense_free_in_slab(scene, problem, n=DENSE_N) -> int:
    """Soundness cross-check (the S2/S5 ground-truth check): count ``n`` seeded samples in the
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
    S = rng.uniform(lo, hi, size=(n, scene.robot.n))
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


# --------------------------------------------------------------------------- #
# 3. S14 — `make reproduce`: every row of the paper's summary table
# --------------------------------------------------------------------------- #
#
# One PROCESS per row (S12 lesson: the sympy FK build is cached per process, so a second
# scene in the same process would look ~30x faster than `cnp certify` really is). Each row
# times three phases separately — engine (branch-and-bound alone), certify (end to end:
# scene load + symbolic FK build + engine + certificate export) and verify (the exact
# verifier on the finished certificate) — archives the certificate next to its scene, and
# re-checks it twice from OUTSIDE the generator: `cnp.verify.verify_file` in an interpreter
# with site-packages disabled (standard library only), and `cnp verify <cert> <scene>` (the
# command-line form with the scene cross-check). Ground truth is re-asserted AFTER the timed
# phases so that it cannot warm any cache the timings depend on.

ROOT = os.path.abspath(os.path.join(HERE, ".."))
SCRIPTS = os.path.join(ROOT, "scripts")
THIRD_PARTY = ("numpy", "scipy", "sympy", "yaml", "highspy", "pydrake", "cvxpy", "clarabel")

# row id -> (scene file relative to ROOT, ground-truth kind, ground-truth sample count)
REPRODUCE_ROWS = {
    "relay": ("scenes/S1_relais.yaml", None, 0),
    "comb": ("scenes/S2_peigne.yaml", "segment", 300_000),
    "anchor": ("scenes/S3_shoulder_elbow.yaml", "segment", 150_000),
    "bin": ("scenes/S4_iiwa_bin.yaml", "segment", 40_000),
    "flagship": ("scenes/S6_iiwa_real_shelf.yaml", "convex", 40_000),
    "crate": ("scenes/usecase_binpicking_iiwa7.yaml", "convex", 40_000),
    "guard": ("scenes/usecase_capot_surete_iiwa7.yaml", "convex", 40_000),
    **{f"wall_k{k}": (f"scenes/wall/k{k}.yaml", "sealed", 8000) for k in (3, 4, 5, 6, 7)},
    "wall_k8": ("scenes/wall/k8.yaml", "sealed", 3000),
}
# The k=8 point is the frontier: its single LP outlasts the time budget, so the row reports
# the engine verdict and the LP size only (UNDECIDED is not a certificate, and not infeasible).
ENGINE_ONLY = {"wall_k8"}
EXPECTED_OUTPUT_PREFIXES = ("scenes/", "benchmarks/results/")


def _timed(owner, attr: str, bucket: dict):
    """Wrap ``owner.attr`` so each call adds its wall-clock to ``bucket[attr]``. Timing only:
    the original callable runs unchanged and its result (or exception) passes through. The
    caller restores the original with ``setattr(owner, attr, original)``."""
    original = getattr(owner, attr)

    def wrapper(*args, **kw):
        t = time.monotonic()
        try:
            return original(*args, **kw)
        finally:
            bucket[attr] = bucket.get(attr, 0.0) + time.monotonic() - t
            bucket[attr + "_calls"] = bucket.get(attr + "_calls", 0) + 1

    setattr(owner, attr, wrapper)
    return original


def _lp_size(cell, view, problem, active_dims) -> dict:
    lp = witness.build_witness_lp(cell, view.verts_num, view.D, view.pair.obstacle,
                                  phi=problem.phi, delta=problem.delta,
                                  lam_degree=problem.lam_degree, active_dims=active_dims)
    return {"rows": int(lp.face_Az.shape[0] + lp.lam_A.shape[0]),
            "cols": int(lp.nz + lp.nmu + 1)}


def _row_formula(scene, problem) -> int:
    """Per-leaf full-dimension LP rows without building the LP: faces x (DPAD+1)^n Bernstein
    control points + K x (d_lam+1)^n lambda-nonnegativity points, DPAD = max(d_lam + 2,
    2 deg phi) (verify.py:435-436). Cross-checked against the built LP on every row that has
    a collision leaf (see ``reproduce``)."""
    n = scene.robot.n
    d_lam = witness.LAM_DEGREE[scene.lam_degree]
    dpad = max(d_lam + 2, 2 * scene.phi_degree)
    n_faces = sum(len(scene.obstacles[p][1]) for p in scene.pairs[:1])
    return n_faces * (dpad + 1) ** n + len(scene.hull_vertices) * (d_lam + 1) ** n


def _stdlib_verify(cert_path: str) -> dict:
    """Re-prove a certificate with the verifier module alone, site-packages disabled."""
    code = (
        "import json, sys\n"
        f"sys.path.insert(0, {os.path.join(ROOT, 'src')!r})\n"
        "from cnp.verify import verify_file\n"
        f"ok, msg = verify_file({cert_path!r})\n"
        f"tp = sorted(m for m in sys.modules if m.split('.')[0] in {THIRD_PARTY!r})\n"
        "print(json.dumps({'ok': ok, 'msg': msg, 'third_party_modules_loaded': tp,\n"
        "                  'site_disabled': 'site' not in sys.modules}))\n")
    t = time.monotonic()
    out = subprocess.run([sys.executable, "-S", "-I", "-c", code], capture_output=True,
                         text=True, env={"PATH": "/usr/bin:/bin"}, cwd=ROOT)
    res = json.loads(out.stdout.strip().splitlines()[-1]) if out.returncode == 0 else \
        {"ok": False, "msg": out.stderr.strip()[-400:]}
    res["wall_s"] = round(time.monotonic() - t, 2)
    res["command"] = f"python -S -I -c 'from cnp.verify import verify_file; verify_file(...)'"
    return res


def _cli_verify(cert_path: str, scene_path: str) -> dict:
    cnp_bin = os.path.join(os.path.dirname(sys.executable), "cnp")
    out = subprocess.run([cnp_bin, "verify", cert_path, scene_path], capture_output=True,
                         text=True, cwd=ROOT)
    lines = out.stdout.strip().splitlines()
    return {"returncode": out.returncode, "ok": out.returncode == 0,
            "first_lines": lines[:2], "command": f"cnp verify {cert_path} {scene_path}"}


def _ground_truth(kind: str, n: int, scene, problem, scene_path: str) -> dict:
    if kind == "segment":
        free = dense_free_in_slab(scene, problem, n=n)
        return {"oracle": "segment sampling (scenes.collision_oracle, 30 points per link)",
                "n_uniform_in_slab": n, "free_in_slab": free, "seed": SEED}
    if kind == "sealed":
        if SCRIPTS not in sys.path:
            sys.path.insert(0, SCRIPTS)
        import wall_resonde_S9f as rs
        gt = rs.ground_truth_sealed(scene, n=n)
        gt.update({"oracle": "segment sampling (scenes.collision_oracle, 50 points)",
                   "n_uniform_in_slab": n, "n_corner_biased_in_slab": n,
                   "n_per_side": 1500, "seed": rs.GT_SEED + 1})
        return gt
    if kind == "convex":
        if SCRIPTS not in sys.path:
            sys.path.insert(0, SCRIPTS)
        import flagship_iiwa_real_groundtruth as gtm
        gt = gtm.ground_truth(scene_path, nb=n, verbose=False)
        gt["oracle"] = "convex body vs H-rep polytope (scenes.convex_collision_oracle, LP)"
        return gt
    return {"oracle": None, "note": "no ground-truth pass for this row"}


def reproduce_row(row_id: str) -> dict:
    """One row of the paper's summary table, timed in a fresh process (see module note)."""
    rel, gt_kind, gt_n = REPRODUCE_ROWS[row_id]
    scene_path = os.path.join(ROOT, rel)
    row = {"row": row_id, "scene": rel}

    t0 = time.monotonic()
    scene, budget = scenes.load(scene_path)
    problem = scenes.build_problem(scene, max_depth=budget.max_depth)
    t_build = time.monotonic() - t0

    t0 = time.monotonic()
    result = engine.solve(problem, budget=budget.engine_budget(), axis=budget.axis)
    t_engine = time.monotonic() - t0
    counts = result.counts()
    row.update({"dof": scene.robot.n, "axis": budget.axis, "lam_degree": scene.lam_degree,
                "budget": {"max_depth": budget.max_depth, "max_leaves": budget.max_leaves,
                           "max_time_s": budget.max_time_s},
                "verdict_engine": result.verdict, "leaves": counts["n_leaves"],
                "by_status": counts["status"],
                "termination": result.stats.get("termination"),
                "n_lp_solves": result.stats.get("n_lp_solves")})

    phases = {"load_and_fk_build": round(t_build, 3), "engine": round(t_engine, 3)}
    if row_id in ENGINE_ONLY or result.verdict != "PROOF":
        row.update({"verdict": "UNDECIDED" if result.verdict != "PROOF" else "ENGINE-PROOF",
                    "phases_s": phases, "engine_s": round(t_engine, 3),
                    "certificate": None,
                    "note": "engine only: no certificate (UNDECIDED is not a proof and not "
                            "a proof of feasibility)"})
    else:
        bucket = {}
        originals = [(verify, "verify", _timed(verify, "verify", bucket)),
                     (cert._ExactLeafAudit, "__init__",
                      _timed(cert._ExactLeafAudit, "__init__", bucket)),
                     (cert._ExactLeafAudit, "accepts",
                      _timed(cert._ExactLeafAudit, "accepts", bucket))]
        t0 = time.monotonic()
        try:
            c = cert.make_certificate(scene, result, verify_loop=True)
        finally:
            for owner, attr, orig in originals:
                setattr(owner, attr, orig)
        t_export = time.monotonic() - t0
        t0 = time.monotonic()
        ok, msg = verify.verify(c)
        t_verify = time.monotonic() - t0

        cert_rel = rel.replace(".yaml", ".cert.json")
        cert.save(c, os.path.join(ROOT, cert_rel))
        phases["export"] = round(t_export, 3)
        row.update({
            "verdict": "PROOF" if ok else "ENGINE-PROOF", "verify_msg": msg,
            "phases_s": phases,
            "export_breakdown_s": {
                "verify_loop_full_verifier": round(bucket.get("verify", 0.0), 3),
                "verify_loop_calls": bucket.get("verify_calls", 0),
                "per_leaf_exact_audit": round(bucket.get("accepts", 0.0), 3),
                "per_leaf_audit_calls": bucket.get("accepts_calls", 0),
                "audit_setup_fk_rederivation": round(bucket.get("__init__", 0.0), 3)},
            "engine_s": round(t_engine, 3),
            "certify_s": round(t_build + t_engine + t_export, 3),
            "verify_s": round(t_verify, 3),
            "certificate": cert_rel,
            "cert_stats": c["stats"]})
        row["recheck_stdlib_verify_file"] = _stdlib_verify(cert_rel)
        row["recheck_cli_verify_with_scene"] = _cli_verify(cert_rel, rel)

    # --- untimed reporting: active dimensions, LP size, applicability, ground truth ---
    views = engine.pair_views(problem)
    active = list(engine._global_active(views, problem))
    row.update({"active_dims": active, "n_active": len(active),
                "passive_dims": [i for i in range(scene.robot.n) if i not in active]})
    coll = next((lf for lf in result.leaves if lf.status == "collision"), None)
    if coll is not None:
        vw = next((v for v in views if getattr(v.pair, "name", None) == coll.pair), views[0])
        cell = [(float(lo), float(hi)) for lo, hi in coll.cell]
        red, full = _lp_size(cell, vw, problem, vw.active), _lp_size(cell, vw, problem, None)
        row.update({"lp_reduced": red, "lp_full": full,
                    "reduction_x": round(full["rows"] / red["rows"], 1)})
    row["lp_full_rows_formula"] = _row_formula(scene, problem)
    if scene.robot.kind == "spatial_revolute":
        row["embedding_applicable"] = {nm: {"applicable": ck.applicable, "reason": ck.reason}
                                       for nm, ck in engine.embedding_applicable(problem).items()}
    t0 = time.monotonic()
    row["groundtruth"] = _ground_truth(gt_kind, gt_n, scene, problem, scene_path)
    row["groundtruth"]["wall_s"] = round(time.monotonic() - t0, 1)
    return row


def _machine() -> dict:
    import platform

    def sysctl(key):
        try:
            return subprocess.check_output(["sysctl", "-n", key], text=True).strip()
        except Exception:                               # pragma: no cover
            return None
    return {"platform": platform.platform(), "cpu": sysctl("machdep.cpu.brand_string"),
            "ncpu": sysctl("hw.ncpu"),
            "mem_gb": round(int(sysctl("hw.memsize") or 0) / 2 ** 30, 1),
            "python": platform.python_version()}


def _versions() -> dict:
    from importlib.metadata import version, PackageNotFoundError
    out = {}
    for pkg in ("numpy", "scipy", "sympy", "highspy", "PyYAML", "drake", "matplotlib"):
        try:
            out[pkg] = version(pkg)
        except PackageNotFoundError:                    # pragma: no cover
            out[pkg] = None
    return out


def reproduce(row_ids, allow_dirty: bool = False) -> str:
    """Run every requested row in its own process on a CLEAN tree and write reproduce.json."""
    dirty = _git_dirty()
    if dirty and not allow_dirty:
        raise SystemExit("reproduce: REFUSED — the working tree is dirty; commit first so that "
                         "the recorded commit describes exactly the code that ran")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outdir = os.path.join(RESULTS, stamp)
    os.makedirs(os.path.join(outdir, "rows"), exist_ok=True)
    payload = {"stamp": stamp, "session": "S14", "commit": _commit_hash(),
               "git_dirty_at_start": dirty, "machine": _machine(), "versions": _versions(),
               "load_avg_at_start": [round(x, 2) for x in os.getloadavg()],
               "protocol": "one process per row; phases timed with time.monotonic; ground "
                           "truth re-asserted after the timed phases", "rows": {}}
    print(f"reproduce {stamp}  commit {payload['commit'][:10]}  dirty={dirty}")
    for rid in row_ids:
        path = os.path.join(outdir, "rows", f"{rid}.json")
        load = [round(x, 2) for x in os.getloadavg()]
        t = time.monotonic()
        proc = subprocess.run([sys.executable, os.path.abspath(__file__), "--row", rid,
                               "--out", path], cwd=ROOT)
        if proc.returncode != 0:
            payload["rows"][rid] = {"row": rid, "error": f"worker exit {proc.returncode}"}
            print(f"  {rid:10s} ERROR (exit {proc.returncode})")
            continue
        with open(path) as f:
            r = json.load(f)
        r["process_wall_s"] = round(time.monotonic() - t, 1)
        r["load_avg_before"] = load
        payload["rows"][rid] = r
        print(f"  {rid:10s} {r.get('verdict'):11s} leaves={r.get('leaves'):<4} "
              f"engine={r.get('engine_s')}s certify={r.get('certify_s')}s "
              f"verify={r.get('verify_s')}s gt={r['groundtruth'].get('free_in_slab')}",
              flush=True)

    lever = os.path.join(outdir, "lever_iiwa7.json")
    proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "measure_iiwa7_lever.py"),
                           "scenes/S6_iiwa_real_shelf.yaml", "--json", lever],
                          cwd=ROOT, capture_output=True, text=True)
    payload["lever_measurement"] = (os.path.relpath(lever, ROOT) if proc.returncode == 0
                                    else {"error": proc.stderr[-400:]})

    # kinematic fidelity of the frozen iiwa7 model against Drake (numbers the paper quotes;
    # until S14 they lived in the journal and in test assertions only — D-P2-B)
    fid_code = (
        "import json, sys\n"
        f"sys.path.insert(0, {SCRIPTS!r})\n"
        "import build_iiwa7_chain as c, build_iiwa7_scene as s\n"
        "print(json.dumps({'chain_flange_position_error_m': c.check_parity(),\n"
        "  'chain_configs': 1500,\n"
        "  'chain_sampling': 'uniform +-2.9 rad on all 7 joints (scripts/build_iiwa7_chain.py:172-173)',\n"
        "  'chain_quantity': 'max norm of the flange-origin position error vs Drake (metres)',\n"
        "  'body_vertex_position_error_m': s.check_body_parity(n_cfg=200),\n"
        "  'body_configs': 200,\n"
        "  'body_sampling': 'uniform +-2 rad on all 7 joints, all 40 hull vertices (scripts/build_iiwa7_scene.py:200-203)'}))\n")
    proc = subprocess.run([sys.executable, "-c", fid_code], cwd=ROOT, capture_output=True,
                          text=True)
    payload["kinematic_fidelity"] = (json.loads(proc.stdout.strip().splitlines()[-1])
                                     if proc.returncode == 0 else {"error": proc.stderr[-400:]})

    checks = {}
    for rid, r in payload["rows"].items():
        if "lp_full" in r:
            checks[rid] = r["lp_full"]["rows"] == r["lp_full_rows_formula"]
    payload["lp_row_formula_matches_built_lp"] = checks

    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True,
                            cwd=ROOT).stdout.splitlines()
    changed = [ln[3:] for ln in status]
    rel_prefix = os.path.relpath(ROOT, subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip())
    changed = [p[len(rel_prefix) + 1:] if p.startswith(rel_prefix + "/") else p for p in changed]
    payload["tree_changes_at_end"] = changed
    payload["tree_changes_are_run_outputs_only"] = all(
        p.startswith(EXPECTED_OUTPUT_PREFIXES) and (p.endswith(".cert.json")
                                                     or p.startswith("benchmarks/results/"))
        for p in changed)
    payload["load_avg_at_end"] = [round(x, 2) for x in os.getloadavg()]
    with open(os.path.join(outdir, "reproduce.json"), "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"written {os.path.relpath(outdir, ROOT)}/reproduce.json")
    return outdir


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="certified-noplan benchmark harness")
    ap.add_argument("--reproduce", action="store_true",
                    help="S14: every row of the paper's summary table, one process per row")
    ap.add_argument("--rows", nargs="*", default=None, help="subset of reproduce rows")
    ap.add_argument("--row", default=None, help="(internal) run one reproduce row")
    ap.add_argument("--out", default=None, help="(internal) row JSON output path")
    ap.add_argument("--allow-dirty", action="store_true",
                    help="run on a dirty tree anyway (recorded as git_dirty_at_start=true)")
    a = ap.parse_args()
    if a.row:
        with open(a.out, "w") as f:
            json.dump(reproduce_row(a.row), f, indent=2, default=str)
    elif a.reproduce:
        reproduce(a.rows or list(REPRODUCE_ROWS), allow_dirty=a.allow_dirty)
    else:
        main()
