"""S9e — the "scaling wall" bench: cost of a certified disconnection vs the number of
ACTIVE dimensions k (D40, pilotage Stéphane "apporter des mesures aux limitations").

Synthetic family parameterised by k = active dims actually DETECTED (asserted via
``pair_views`` / ``passive_dims``, not declared). Construction: a k-joint generic spatial
chain (alternating yaw/pitch axes) whose CERTIFIED body is the LAST link — so its geometry
depends on ALL k joints (k active dims, no passive padding). The base yaw s0 is the barrier
(φ=s0); a box obstacle is sized to the last link's reach over the band {|s0|<=δ, other joints
in their small range}, so every config in the slab collides while start/goal (large |s0|, the
arm yawed away) are free — a genuine k-active-dim disconnection.

Each k is a REAL disconnection (dense seeded ground truth BEFORE certification). Budget is
CAPPED per point (10^4 leaves / 30 min): an UNDECIDED-on-budget is DATA (the wall position),
not a failure. Measures per k: detected active dims, feuilles, cost/leaf (Bernstein LP rows,
reduced A30 and full), wall-clock certif + verify, n_reresolve_failed (A32, expect 0), verdict.

Run: ``python scripts/wall_bench.py`` — prints the table and returns the rows. Stamp the
result (date, commit, git_dirty) at the call site (rule 7)."""
from __future__ import annotations

import time
from fractions import Fraction as F

import numpy as np

from cnp import certificate as cert, engine, scenes, verify, witness
from cnp.ratfk import SympyRatFK
from cnp.scenes import _spatial_joints

MAX_LEAVES = 10_000
MAX_TIME_S = 1800
GT_SEED = 7
_ff = lambda x: float(F(x))


def build_scene(k: int, half=F(1, 4), s0hi=F(3, 5), delta=F(1, 10)) -> cert.Scene:
    """k-joint chain, body = last link (depends on all k joints). WALL = bounding box of the
    last link's reach over the band, so the slab is fully in collision (real disconnection)."""
    axes = [["0", "0", "1"] if i % 2 == 0 else ["0", "1", "0"] for i in range(k)]
    offs = [["0", "0", "0"]] + [["2/5", "0", "0"]] * (k - 1)
    joints = [{"offset": offs[i], "axis": axes[i]} for i in range(k)]
    robot = cert.Robot(kind="spatial_revolute", link_lengths=[], q_star=[0] * k, joints=joints)
    hull = [["0", "0", "0"], ["2/5", "0", "0"]]
    fk = SympyRatFK(_spatial_joints(robot), locked={}, q_star=[0.0] * k)
    body = fk.body(f"j{k-1}")
    rng = np.random.default_rng(GT_SEED)
    pts = []
    lob = [-_ff(delta)] + [-_ff(half)] * (k - 1)
    hib = [_ff(delta)] + [_ff(half)] * (k - 1)
    for _ in range(4000):
        s = rng.uniform(lob, hib)
        for v in hull:
            pts.append(body.eval_world_point([_ff(x) for x in v], s))
    pts = np.array(pts)
    lo, hi, m = pts.min(0), pts.max(0), 0.02
    A = [["1", "0", "0"], ["0", "1", "0"], ["0", "0", "1"],
         ["-1", "0", "0"], ["0", "-1", "0"], ["0", "0", "-1"]]
    b = [F(hi[0] + m).limit_denominator(10**6), F(hi[1] + m).limit_denominator(10**6),
         F(hi[2] + m).limit_denominator(10**6), F(-(lo[0] - m)).limit_denominator(10**6),
         F(-(lo[1] - m)).limit_denominator(10**6), F(-(lo[2] - m)).limit_denominator(10**6)]
    box = [(-s0hi, s0hi)] + [(-half, half)] * (k - 1)
    z = [F(0)] * (k - 1)
    return cert.Scene(robot=robot, body_link=k - 1, hull_vertices=hull,
                      obstacles={"WALL": (A, b)}, phi={tuple([1] + [0] * (k - 1)): F(1)},
                      phi_degree=2, delta=delta, box=box,
                      start_s=[-s0hi + F(1, 20)] + z, goal_s=[s0hi - F(1, 20)] + z, pairs=["WALL"])


def ground_truth(sc: cert.Scene, n: int = 8000) -> dict:
    """Dense seeded check BEFORE certification (rule 9): start/goal free, 0 free in the slab,
    free on both sides (two components)."""
    orac = scenes.collision_oracle(sc, n_samples=50)
    lo = np.array([_ff(l) for l, _ in sc.box]); hi = np.array([_ff(h) for _, h in sc.box])
    rng = np.random.default_rng(GT_SEED + 1)
    free_slab = sum(1 for _ in range(n)
                    if not orac(np.concatenate(([rng.uniform(-0.1, 0.1)],
                                                rng.uniform(lo[1:], hi[1:])))))
    free_L = sum(1 for _ in range(1500)
                 if not orac(np.concatenate(([rng.uniform(lo[0], -0.2)], rng.uniform(lo[1:], hi[1:])))))
    free_R = sum(1 for _ in range(1500)
                 if not orac(np.concatenate(([rng.uniform(0.2, hi[0])], rng.uniform(lo[1:], hi[1:])))))
    return {"start_free": not orac([_ff(x) for x in sc.start_s]),
            "goal_free": not orac([_ff(x) for x in sc.goal_s]),
            "free_in_slab": free_slab, "free_left": free_L, "free_right": free_R}


def _lp_rows(cell, vw, prob, ad) -> int:
    lp = witness.build_witness_lp(cell, vw.verts_num, vw.D, vw.pair.obstacle, phi=prob.phi,
                                  delta=prob.delta, lam_degree=prob.lam_degree, active_dims=ad)
    return int(lp.face_Az.shape[0] + lp.lam_A.shape[0])


def measure(k: int, lam_degree: str = "affine") -> dict:
    sc = build_scene(k)
    sc.lam_degree = lam_degree
    prob = scenes.build_problem(sc)
    views = engine.pair_views(prob)
    active = list(engine._global_active(views, prob))
    gt = ground_truth(sc)
    t0 = time.monotonic()
    res = engine.solve(prob, axis="margin",
                       budget=engine.Budget(max_leaves=MAX_LEAVES, max_time_s=MAX_TIME_S))
    engine_s = time.monotonic() - t0
    row = {"k": k, "lam_degree": lam_degree, "n_active_detected": len(active),
           "active_dims": active, "verdict": res.verdict,
           "leaves": res.counts()["n_leaves"], "engine_s": round(engine_s, 2),
           "ground_truth": gt}
    coll = next((lf for lf in res.leaves if lf.status == "collision"), None)
    if coll is not None:
        cell = [(float(l), float(h)) for l, h in coll.cell]
        vw = views[0]
        row["cost_leaf_reduced_rows"] = _lp_rows(cell, vw, prob, vw.active)
        row["cost_leaf_full_rows"] = _lp_rows(cell, vw, prob, None)
    if res.verdict == "PROOF":
        t1 = time.monotonic(); c = cert.make_certificate(sc, res, verify_loop=True)
        row["cert_s"] = round(time.monotonic() - t1, 2)
        t2 = time.monotonic(); ok, _ = verify.verify(c)
        row["verify_s"] = round(time.monotonic() - t2, 2)
        row["verify_ok"] = ok
        row["n_reresolve_failed"] = c["stats"]["n_reresolve_failed"]
    return row


def run(ks=(3, 4, 5)) -> list:
    rows = []
    for k in ks:
        r = measure(k)
        gt = r["ground_truth"]
        assert r["n_active_detected"] == k, f"k={k}: detected {r['n_active_detected']} active"
        assert gt["start_free"] and gt["goal_free"] and gt["free_in_slab"] == 0, \
            f"k={k}: not a clean disconnection: {gt}"
        assert gt["free_left"] > 0 and gt["free_right"] > 0, f"k={k}: not two-sided: {gt}"
        print(f"k={r['k']} active={r['n_active_detected']} verdict={r['verdict']:9s} "
              f"leaves={r['leaves']:5d} rows_red={r.get('cost_leaf_reduced_rows','-')} "
              f"rows_full={r.get('cost_leaf_full_rows','-')} engine_s={r['engine_s']} "
              f"cert_s={r.get('cert_s','-')} verify_s={r.get('verify_s','-')} "
              f"reresolve={r.get('n_reresolve_failed','-')} "
              f"[gt free_slab={gt['free_in_slab']} L/R={gt['free_left']}/{gt['free_right']}]",
              flush=True)
        rows.append(r)
    return rows


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, default=str))
