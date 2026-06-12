"""S9d / G2' calibration — cost model of the certified disconnection (A31 / D20 / D31).

Measures, on the SAME iiwa-like bin family (the S4 scene with a varying number of locked
wrist joints, so the ACTIVE joints {0,1,2} are fixed and only the PASSIVE count grows):

  * feuilles(n) and engine wall-clock at n = 3,4,5,6 unlocked joints;
  * cost per leaf = Bernstein LP rows of the WALL pair, REDUCED (to the pair's active dims,
    A18/A30) vs FULL (all n dims, the pre-reduction cost) — the reduction factor is the
    leverage that keeps a 5-6 DOF disconnection as cheap as its 3-active-dim core;
  * the A32 decision<->certificate dissonance counter (must be 0);
  * PER-PAIR proximal vs distal reduction (A30) on a TWO-BODY variant of the scene
    (link 2 proximal vs link 4 distal), since the shipped single-body scene has one pair
    (the global reduction == the per-pair one on it — stated honestly).

Run: ``python scripts/calibrate_g2.py`` (writes benchmarks/results/<stamp>/calibration.json
is left to the caller; this prints the table and returns the dict)."""
from __future__ import annotations

import json
import time

import numpy as np

from cnp import certificate as cert, engine, scenes, verify, witness

# iiwa-like S-R-S chain (same as scenes/S4_iiwa_bin.yaml).
JOINTS = [{"offset": ["0", "0", "0"], "axis": ["0", "0", "1"]},
          {"offset": ["0", "0", "3/10"], "axis": ["0", "1", "0"]},
          {"offset": ["3/10", "0", "0"], "axis": ["0", "1", "0"]},
          {"offset": ["3/10", "0", "0"], "axis": ["0", "0", "1"]},
          {"offset": ["3/10", "0", "0"], "axis": ["0", "1", "0"]},
          {"offset": ["1/5", "0", "0"], "axis": ["0", "0", "1"]},
          {"offset": ["161/2000", "0", "0"], "axis": ["0", "1", "0"]}]
WALL_A = [["1", "0", "0"], ["0", "1", "0"], ["0", "0", "1"],
          ["-1", "0", "0"], ["0", "-1", "0"], ["0", "0", "-1"]]
WALL_B = ["8/25", "1/10", "31/50", "-2/25", "1/10", "1/20"]
Q = cert.Q


def _scene(n_unlocked: int) -> cert.Scene:
    """The bin scene with ``7 - n_unlocked`` distal joints locked at 0 (so n active joints
    are {0,1,2} and the rest are unlocked-but-passive). q*=0, exactly verifiable."""
    locked = {k: {"cos": "1", "sin": "0"} for k in range(n_unlocked, 7)}
    robot = cert.Robot(kind="spatial_revolute", link_lengths=[], q_star=[0] * 7,
                       locked=locked, joints=JOINTS)
    box = [(Q("-7/10"), Q("7/10"))] * 3 + [(Q(-5), Q(5))] * (n_unlocked - 3)
    z = [Q(0)] * (n_unlocked - 1)
    phi = {tuple([1] + [0] * (n_unlocked - 1)): Q(1)}
    return cert.Scene(robot=robot, body_link=2, hull_vertices=[["0", "0", "0"], ["3/10", "0", "0"]],
                      obstacles={"WALL": (WALL_A, WALL_B)}, phi=phi, phi_degree=2,
                      delta=Q("1/10"), box=box,
                      start_s=[Q("-3/5")] + z, goal_s=[Q("3/5")] + z, pairs=["WALL"])


def _lp_rows(cell, view, prob, active_dims) -> int:
    """Bernstein LP row count (face constraints + lambda-nonneg constraints) of the WALL
    pair on one cell, at the given ``active_dims`` (None = full dim)."""
    lp = witness.build_witness_lp(cell, view.verts_num, view.D, view.pair.obstacle,
                                  phi=prob.phi, delta=prob.delta,
                                  lam_degree=prob.lam_degree, active_dims=active_dims)
    return int(lp.face_Az.shape[0] + lp.lam_A.shape[0])


def family_calibration() -> list:
    rows = []
    for n in (3, 4, 5, 6):
        sc = _scene(n)
        prob = scenes.build_problem(sc)
        views = engine.pair_views(prob)
        active = list(engine._global_active(views, prob))
        t0 = time.monotonic()
        res, c = cert.certify(sc, axis="margin")
        dt = time.monotonic() - t0
        ok, _ = verify.verify(c)
        # cost/leaf on the first collision cell: reduced (active) vs full (n dims)
        coll = next(lf for lf in res.leaves if lf.status == "collision")
        cell = [(float(lo), float(hi)) for lo, hi in coll.cell]
        vw = views[0]
        reduced = _lp_rows(cell, vw, prob, vw.active)
        full = _lp_rows(cell, vw, prob, None)
        rows.append({"n": n, "n_active": len(active), "n_passive": n - len(active),
                     "active_dims": active, "leaves": len(c["leaves"]),
                     "verdict": res.verdict, "verify_ok": ok,
                     "n_reresolve_failed": c["stats"]["n_reresolve_failed"],
                     "cost_leaf_reduced_rows": reduced, "cost_leaf_full_rows": full,
                     "reduction_x": round(full / reduced, 1), "engine_s": round(dt, 3)})
    return rows


def per_pair_two_body() -> dict:
    """A30 per-pair reduction: a TWO-BODY variant of the bin (no lock, n=7) with a PROXIMAL
    pair on link 2 ({0,1,2} active) and a DISTAL pair on link 4 ({0..4} active). The per-pair
    reduction gives each pair its OWN active set (proximal LP much smaller than distal),
    finer than the global union — the leverage the single-body shipped scene cannot show."""
    from cnp.scenes import _spatial_joints
    from cnp.ratfk import SympyRatFK
    robot = cert.Robot(kind="spatial_revolute", link_lengths=[], q_star=[0] * 7, joints=JOINTS)
    fk = SympyRatFK(_spatial_joints(robot), locked={}, q_star=[0.0] * 7)
    box = [(-0.7, 0.7)] * 3 + [(-0.7, 0.7)] * 4
    phi = np.zeros((3,) * 7); phi[(1,) + (0,) * 6] = 1.0
    pol = lambda: witness.Polytope(np.array([[float(x) for x in r] for r in WALL_A]),
                                   np.array([float(Q(x)) for x in WALL_B]))
    prox = engine.Pair("PROX_link2", fk.body("j2").vertex_numerators([[0., 0, 0], [0.3, 0, 0]]),
                       fk.body("j2").D, pol())
    dist = engine.Pair("DIST_link4", fk.body("j4").vertex_numerators([[0., 0, 0], [0.3, 0, 0]]),
                       fk.body("j4").D, pol())
    prob = engine.Problem(box=box, phi=phi, delta=0.1, pairs=[prox, dist],
                          lam_degree="affine", max_depth=22)
    views = engine.pair_views(prob)
    glob = list(engine._global_active(views, prob))
    cell = [(-0.1, 0.1)] + [(-0.35, 0.35)] * 6
    out = {"global_active": glob, "pairs": []}
    for vw in views:
        out["pairs"].append({"pair": vw.pair.name, "active": list(vw.active),
                             "lp_rows_per_pair": _lp_rows(cell, vw, prob, vw.active),
                             "lp_rows_global": _lp_rows(cell, vw, prob, tuple(glob))})
    return out


def run() -> dict:
    fam = family_calibration()
    pp = per_pair_two_body()
    print("\n=== iiwa bin family — feuilles(n) & coût/feuille (active {0,1,2} fixed) ===")
    print(f"{'n':>2} {'active':>6} {'passive':>7} {'leaves':>6} {'verdict':>8} "
          f"{'reresolve':>9} {'rows_red':>8} {'rows_full':>9} {'reduc':>6} {'engine_s':>8}")
    for r in fam:
        print(f"{r['n']:>2} {r['n_active']:>6} {r['n_passive']:>7} {r['leaves']:>6} "
              f"{r['verdict']:>8} {r['n_reresolve_failed']:>9} {r['cost_leaf_reduced_rows']:>8} "
              f"{r['cost_leaf_full_rows']:>9} {str(r['reduction_x'])+'x':>6} {r['engine_s']:>8}")
    print("\n=== A30 per-pair (two-body variant, n=7) proximal vs distal ===")
    print(f"global active = {pp['global_active']}")
    for p in pp["pairs"]:
        print(f"  {p['pair']:>12}  active={str(p['active']):>17}  "
              f"LP rows per-pair={p['lp_rows_per_pair']:>4}  (global={p['lp_rows_global']})")
    return {"family": fam, "per_pair": pp}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
