"""S9f — re-sonde of the scaling wall in ACTIVE dimensions (L0). Two corrections over S9e:

L0a — termination ceiling. S9e's k=5 UNDECIDED stopped at 48 leaves / 45 s under a 10^4 /
30-min budget because of a THIRD, silent ceiling: ``Problem.max_depth=16`` (diagnosed via the
S9f instrumentation ``termination=depth_exhausted``, NOT budget). The budget was never spent.

L0a — leaky scene. At raised depth + real budget the certifier SOUNDLY refuses the S9e k=5
scene: its WALL obstacle is the axis-aligned bounding box of 4000 RANDOM samples of the last
link's reach + a 0.02 margin, which UNDER-covers the reach at config-space corners (other
joints near +-0.25). Free configs survive in the slab there (link endpoint outside the box by
up to ~0.04); the 8000-sample uniform ground truth misses them (corners are measure-tiny) but
the certifier finds them (rule 9: the grid does not make truth). So the S9e k=5 scene is NOT a
watertight disconnection — UNDECIDED was the SOUND verdict, not an affine-witness wall.

This module rebuilds the family with a PROVABLY watertight obstacle (``build_scene_sealed``):
each WALL face is sized from the Bernstein bound of the link's world coordinate over the band,
``h = max_cp(bcN_cp / bcD_cp)`` (Bernstein is linear in the coeffs, so ``h*bcD_cp >= bcN_cp``
for every control point ⇒ ``h*D - N_i >= 0`` on the whole band ⇒ ``X_i = N_i/D <= h``). The box
contains both hull endpoints over the band and is convex ⇒ the whole link, hence the slab is
PROVABLY all-collision — a genuine k-active-dim disconnection by construction (still seeded
dense ground truth re-asserted, incl. a corner-biased pass). Then it measures, at raised depth
and real budget (10^4 leaves / 30 min), whether the affine witness CERTIFIES it and at what cost.

Run: ``python scripts/wall_resonde_S9f.py [k0 k1 ...]`` (default 3 4 5 6). Stamp date/commit/
git_dirty at the call site (rule 7)."""
from __future__ import annotations

import json
import sys
import time
from fractions import Fraction as F

import numpy as np

from cnp import certificate as cert, engine, scenes, verify
from cnp.polylin import bernstein_coeffs
from cnp.scenes import _body_fk

from wall_bench import build_scene  # the leaky S9e scene (for the geometry + FK)  # noqa: E402

MAX_LEAVES = 10_000
MAX_TIME_S = 1800          # 30 real minutes
MAX_DEPTH = 60             # >> what the budget allows ⇒ the BUDGET binds, not depth
GT_SEED = 7


def _tight_seal(prob, band, eps=F(1, 50)):
    """Provable per-face box bounds sealing the last link's reach over ``band``.

    For each hull-vertex numerator ``N_i`` over the common denominator ``D`` (``D>0``):
    ``Bernstein(h*D - N_i) = h*bcD - bcN`` (linearity), so all control points ``>= 0`` —
    hence ``h*D - N_i >= 0`` on the band, i.e. ``X_i = N_i/D <= h`` — iff
    ``h >= max_cp bcN_cp/bcD_cp``. Symmetric for the lower face. ``eps`` padding leaves the
    witness a strictly positive margin (and only ENLARGES the obstacle ⇒ still sealed)."""
    verts, D = prob.pairs[0].verts_num, prob.pairs[0].D
    dim = len(verts[0])
    bcD = bernstein_coeffs(D, [(float(l), float(h)) for l, h in band]).reshape(-1)
    assert (bcD > 0).all(), "D Bernstein coeffs not all > 0 on the band"
    his, los = [-1e18] * dim, [1e18] * dim
    for v in verts:
        for i in range(dim):
            bcN = bernstein_coeffs(v[i], [(float(l), float(h)) for l, h in band]).reshape(-1)
            r = bcN / bcD
            his[i] = max(his[i], float(r.max()))
            los[i] = min(los[i], float(r.min()))
    ef = float(eps)
    return ([F(l - ef).limit_denominator(10**6) for l in los],
            [F(h + ef).limit_denominator(10**6) for h in his])


def build_scene_sealed(k: int, half=F(1, 4), s0hi=F(3, 5), delta=F(1, 10)) -> cert.Scene:
    """Same k-joint chain as ``wall_bench.build_scene`` but with a PROVABLY watertight WALL
    obstacle (Bernstein-sealed reach over the band) ⇒ a genuine k-active-dim disconnection."""
    base = build_scene(k, half=half, s0hi=s0hi, delta=delta)
    prob = scenes.build_problem(base)
    band = [(-delta, delta)] + [(-half, half)] * (k - 1)
    lo, hi = _tight_seal(prob, band)
    A = [["1", "0", "0"], ["0", "1", "0"], ["0", "0", "1"],
         ["-1", "0", "0"], ["0", "-1", "0"], ["0", "0", "-1"]]
    b = [hi[0], hi[1], hi[2], -lo[0], -lo[1], -lo[2]]
    sc = cert.Scene(robot=base.robot, body_link=base.body_link, hull_vertices=base.hull_vertices,
                    obstacles={"WALL": (A, b)}, phi=base.phi, phi_degree=base.phi_degree,
                    delta=delta, box=base.box, start_s=base.start_s, goal_s=base.goal_s,
                    pairs=["WALL"])
    sc.lam_degree = base.lam_degree
    return sc


def ground_truth_sealed(sc: cert.Scene, n: int = 8000) -> dict:
    """Dense seeded check BEFORE certification (rule 9): start/goal free, 0 free in the slab
    (uniform AND corner-biased — the corners are where the leaky box failed), two-sided."""
    orac = scenes.collision_oracle(sc, n_samples=50)
    lo = np.array([float(l) for l, _ in sc.box]); hi = np.array([float(h) for _, h in sc.box])
    k = len(sc.box)
    rng = np.random.default_rng(GT_SEED + 1)
    free_slab = sum(1 for _ in range(n)
                    if not orac(np.concatenate(([rng.uniform(-0.1, 0.1)],
                                                rng.uniform(lo[1:], hi[1:])))))
    free_corner = sum(1 for _ in range(n)
                      if not orac(np.concatenate(([rng.uniform(-0.1, 0.1)],
                                                  rng.choice([-0.25, 0.25], size=k - 1)
                                                  * rng.uniform(0.85, 1.0, size=k - 1)))))
    free_L = sum(1 for _ in range(1500)
                 if not orac(np.concatenate(([rng.uniform(lo[0], -0.2)], rng.uniform(lo[1:], hi[1:])))))
    free_R = sum(1 for _ in range(1500)
                 if not orac(np.concatenate(([rng.uniform(0.2, hi[0])], rng.uniform(lo[1:], hi[1:])))))
    return {"start_free": not orac([float(x) for x in sc.start_s]),
            "goal_free": not orac([float(x) for x in sc.goal_s]),
            "free_in_slab": free_slab, "free_in_slab_corner": free_corner,
            "free_left": free_L, "free_right": free_R}


def _lp_rows(cell, vw, prob, ad) -> int:
    from cnp import witness
    lp = witness.build_witness_lp(cell, vw.verts_num, vw.D, vw.pair.obstacle, phi=prob.phi,
                                  delta=prob.delta, lam_degree=prob.lam_degree, active_dims=ad)
    return int(lp.face_Az.shape[0] + lp.lam_A.shape[0])


def resonde(k: int, lam_degree="affine", max_depth=MAX_DEPTH,
            max_leaves=MAX_LEAVES, max_time_s=MAX_TIME_S, s0hi=F(4, 5)) -> dict:
    # s0hi = the yaw-away angle of start/goal. Default 4/5 (not the S9e 3/5) so that, as the
    # chain lengthens, start/goal still clear the (larger) sealing obstacle at every k=3..8 —
    # a uniform family. It does not affect cost/leaf ((d+1)^k), only how far start/goal yaw.
    sc = build_scene_sealed(k, s0hi=s0hi); sc.lam_degree = lam_degree
    prob = scenes.build_problem(sc); prob.max_depth = max_depth
    views = engine.pair_views(prob)
    active = list(engine._global_active(views, prob))
    gt = ground_truth_sealed(sc)
    assert len(active) == k, f"k={k}: detected {len(active)} active (expected {k})"
    assert gt["start_free"] and gt["goal_free"], f"k={k}: start/goal not free: {gt}"
    assert gt["free_in_slab"] == 0 and gt["free_in_slab_corner"] == 0, \
        f"k={k}: SEALED scene still leaks: {gt}"
    assert gt["free_left"] > 0 and gt["free_right"] > 0, f"k={k}: not two-sided: {gt}"

    t0 = time.monotonic()
    res = engine.solve(prob, axis="margin",
                       budget=engine.Budget(max_leaves=max_leaves, max_time_s=max_time_s))
    engine_s = time.monotonic() - t0
    st = res.stats
    row = {"k": k, "lam_degree": lam_degree, "n_active_detected": len(active),
           "max_depth_limit": max_depth, "verdict": res.verdict,
           "termination": st.get("termination"), "max_depth_reached": st.get("max_depth_reached"),
           "leaves": st["n_leaves"], "by_status": st["by_status"],
           "engine_s": round(engine_s, 1), "ground_truth": gt}
    coll = next((lf for lf in res.leaves if lf.status == "collision"), None)
    if coll is not None:
        cell = [(float(l), float(h)) for l, h in coll.cell]
        row["cost_leaf_reduced_rows"] = _lp_rows(cell, views[0], prob, views[0].active)
        row["cost_leaf_full_rows"] = _lp_rows(cell, views[0], prob, None)
    if res.verdict == "PROOF":
        t1 = time.monotonic(); c = cert.make_certificate(sc, res, verify_loop=True)
        row["cert_s"] = round(time.monotonic() - t1, 2)
        t2 = time.monotonic(); ok, _ = verify.verify(c)
        row["verify_s"] = round(time.monotonic() - t2, 2)
        row["verify_ok"] = ok
        row["n_reresolve_failed"] = c["stats"]["n_reresolve_failed"]
        assert ok and row["n_reresolve_failed"] == 0, f"k={k}: PROOF but verify/A32 failed: {row}"
    return row


def _fmt(r: dict) -> str:
    g = r["ground_truth"]
    return (f"k={r['k']} active={r['n_active_detected']} verdict={r['verdict']:9s} "
            f"term={r['termination']:14s} depth={r['max_depth_reached']}/{r['max_depth_limit']} "
            f"leaves={r['leaves']:5d} by_status={r['by_status']} "
            f"rows={r.get('cost_leaf_reduced_rows','-')} engine_s={r['engine_s']} "
            f"cert_s={r.get('cert_s','-')} verify_s={r.get('verify_s','-')} "
            f"verify_ok={r.get('verify_ok','-')} A32={r.get('n_reresolve_failed','-')} "
            f"[gt slab={g['free_in_slab']}/corner={g['free_in_slab_corner']} L/R={g['free_left']}/{g['free_right']}]")


def run(ks) -> list:
    rows = []
    for k in ks:
        r = resonde(k)
        print(_fmt(r), flush=True)
        rows.append(r)
        if r["verdict"] != "PROOF":
            print(f"  -> k={k} did not certify (termination={r['termination']}); stopping climb.",
                  flush=True)
            break
    return rows


if __name__ == "__main__":
    ks = [int(a) for a in sys.argv[1:]] or [3, 4, 5, 6]
    rows = run(ks)
    print(json.dumps(rows, indent=2, default=str))
