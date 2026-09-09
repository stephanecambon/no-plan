"""S10-quinquies — G4' benchmark for the REAL KUKA iiwa7 flagship (scenes/S6_iiwa_real_shelf.yaml).

The HEADLINE flagship: faithful iiwa7 kinematics (frozen chain, ~2e-6 vs URDF, S10-bis) AND faithful
40-vertex convex silhouette (frozen body, ~1.7e-6, S10-ter), a FRANC pitch/shelf disconnection
(~90 mm margin, S10-quater). Certifies once, verifies independently in EXACT arithmetic, re-asserts
a fast subset of the dense CONVEX-BODY ground truth (A43), captures leaves / A32 / timings /
reduced-vs-full leaf LP rows, archives the certificate, writes a dated results dir with commit hash
+ git_dirty (rule 7). Compares MEASURED vs the V6-bis budget PREDICTION (units resolved).

G4' RÉAFFIRMÉE sur le vrai robot. Caveat A41: fidélité physique plafonnée par la précision URDF
(~2e-6), modèle interne EXACT (verify.py recompte en Fraction).

GÉNÉRALISÉ EN S11 : le même banc sert les DEUX cas d'usage du pack démo (bac empilé, capot de
sûreté), qui montent le même robot gelé et la même mécanique mesurée (pitch q2 + surplomb, cf.
``scripts/measure_iiwa7_lever.py``) sur des géométries, limites, dalles, poses et claims distincts.
Le nom de l'obstacle, la barrière et la boîte sont lus DANS LA SCÈNE.

ÉTENDU EN S12 [L6] : le banc chronomètre désormais les TROIS PHASES séparément (build FK sympy /
b&b / export) au lieu d'un seul ``certify_s``, parce que la bascule du contrat d'export a déplacé
le terme dominant. Il consigne aussi les compteurs de la bascule
(``n_leaves_embedded`` / ``n_leaves_resolved`` / ``n_embed_rejected``, A32 étendu) et la réponse
de la condition d'applicabilité PAR PAIRE, telle qu'établie à l'exécution.

Run: ``python scripts/flagship_iiwa_real_bench.py [scene.yaml ...]``
     défaut = le flagship S6 -> scenes/S6_iiwa_real_shelf.cert.json
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
# Budgets PRÉDITS par cas, dans CASES ci-dessous. Unités RESOLVED au gate V6-bis : le « 64 » était
# (d+1)^k de points de contrôle Bernstein par CONTRAINTE (une composante, et il présumait DPAD=3) ;
# le compte réel par contrainte est 5^3 = 125. L'unité comparable est le nombre TOTAL de lignes de
# LP par feuille (le « 766 » du banc iiwa-LIKE) ; ici le corps 40 sommets ajoute ~320 lignes lambda,
# d'où 1070. [A44] le wall-clock se prédit sur lignes × COLONNES avec un modèle superlinéaire
# calibré sur les benchs — jamais par extrapolation linéaire en lignes.


def _git():
    h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip())
    return h, dirty


CASES = {
    "scenes/S6_iiwa_real_shelf.yaml": {
        "key": "flagship_S10_iiwa_real", "session": "S10-quinquies",
        "gate": "G4' (réaffirmée vrai robot)",
        "robot": "7-DOF iiwa7 réel (chaîne+corps gelés), piège pitch-étagère, q*=0",
        "note": "FLAGSHIP d'EN-TÊTE : vrai KUKA iiwa7, cinematique+silhouette fideles, "
                "deconnexion FRANC pitch/etagere certifiee PROOF + verify exact",
        "predicted": {"leaves": 8, "cost_leaf_reduced_rows": 1070,
                      "bern_ctrl_pts_per_constraint": 125, "active_dims": [0, 1, 2],
                      # [S12/L6] budget re-prédit APRÈS la bascule : build FK ~39 s + b&b ~1,5 s
                      # + export « <1 s » (mesure S11 : 0,29 s pour le seul terme LP embedé).
                      "certify_s": 40, "certify_s_before_L6": 726}},
    "scenes/usecase_binpicking_iiwa7.yaml": {
        "key": "usecase_binpicking_iiwa7", "session": "S11",
        "gate": "pack démo (cas non-flagship)",
        "robot": "7-DOF iiwa7 réel (chaîne+corps gelés), piège pitch-bac-empilé, q*=0",
        "note": "CAS BIN-PICKING : élagage PROUVÉ d'une branche TAMP — le colis au fond du bac "
                "bas est inatteignable sans retirer d'abord la caisse du dessus",
        # [A44] budget prédit AVANT le run : le LP pleine dim est IDENTIQUE au flagship (même
        # robot, K=40, n=7, DPAD=4) ⟹ 473870 lignes × 327 colonnes, calibré le 08/09 à 290,8 s
        # par feuille collision sur cette machine ⟹ 39 s (build FK) + 1,5 s (b&b) + 2×291 s.
        "predicted": {"leaves": 2, "cost_leaf_reduced_rows": 1070,
                      "cost_leaf_full_rows": 473870, "cols_full": 327,
                      "certify_s": 40, "certify_s_before_L6": 620, "active_dims": [0, 1, 2]}},
    "scenes/usecase_capot_surete_iiwa7.yaml": {
        "key": "usecase_capot_surete_iiwa7", "session": "S11",
        "gate": "pack démo (cas non-flagship)",
        "robot": "7-DOF iiwa7 réel (chaîne+corps gelés), piège pitch-capot, q*=0",
        "note": "CAS CAPOT DE SÛRETÉ : pièce géométrique EXACTEMENT RECOMPTABLE pour un dossier "
                "de sûreté (l'organisme notifié relance cnp verify) — PAS une certification ISO",
        "predicted": {"leaves": 2, "cost_leaf_reduced_rows": 1070,
                      "cost_leaf_full_rows": 473870, "cols_full": 327,
                      "certify_s": 40, "certify_s_before_L6": 620, "active_dims": [0, 1, 2]}},
}


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
    z0 = -float(sc.obstacles[sc.pairs[0]][1][5])         # underside of the overhead obstacle
    topz = lambda s: max(fk.eval_world_point(v, np.asarray(s, float))[2] for v in hv)
    slab_min_top = min(topz([s0, s1, s2, 0, 0, 0, 0])
                       for s0 in np.linspace(lo[0], hi[0], 5)
                       for s1 in np.linspace(-delta, delta, 3)
                       for s2 in np.linspace(lo[2], hi[2], 5))
    sg_max_top = max(topz(sc.start_s), topz(sc.goal_s))
    return {"start_free": start_free, "goal_free": goal_free, "slab_corner_free": corner_free,
            "redundancy_all_collide": (verdicts == {True}),
            "slab_penetration_mm": round((slab_min_top - z0) * 1000, 1),
            "startgoal_clearance_mm": round((z0 - sg_max_top) * 1000, 1)}


def run_case(scene_path: str) -> int:
    meta = CASES[scene_path]
    predicted = meta["predicted"]
    cert_out = scene_path.replace(".yaml", ".cert.json")
    sc, _ = scenes.load(scene_path)
    t0 = time.monotonic()
    prob = scenes.build_problem(sc)
    # [S12] the sympy FK build is now the dominant term — and it is CACHED PER PROCESS by
    # sympy. Benching several scenes in ONE run therefore measures ~39 s for the first and
    # ~1.3 s for the rest, which is NOT what `cnp certify <scene>` costs (A46: a number that
    # suddenly looks too good is a measurement artefact). Run ONE SCENE PER PROCESS for a
    # cold, quotable end-to-end figure.
    t_build = time.monotonic() - t0
    views = engine.pair_views(prob)
    active = list(engine._global_active(views, prob))
    assert active == predicted["active_dims"], f"active dims {active} != predicted"

    # [S12/L6] the export contract's applicability, established AT RUN TIME on this scene.
    checks = engine.embedding_applicable(prob)
    l6 = {nm: {"applicable": ck.applicable, "active": list(ck.active),
               "passive": list(ck.passive), "a29_removed": list(ck.a29_removed),
               "blocking": list(ck.blocking), "reason": ck.reason}
          for nm, ck in checks.items()}

    gt = _groundtruth_subset(sc)                            # re-assert ground truth (A43)

    t0 = time.monotonic()
    res = engine.solve(prob, axis="margin")
    t_engine = time.monotonic() - t0
    t0 = time.monotonic()
    c = cert.make_certificate(sc, res, verify_loop=True)
    t_export = time.monotonic() - t0
    t_certify = t_build + t_engine + t_export               # what `cnp certify` pays end to end
    t1 = time.monotonic()
    ok, msg = verify.verify(c)
    t_verify = time.monotonic() - t1

    coll = next(lf for lf in res.leaves if lf.status == "collision")
    cell = [(float(lo), float(hi)) for lo, hi in coll.cell]
    vw = views[0]
    reduced = _lp_rows(cell, vw, prob, vw.active)          # 3 active dims (A30 reduced)
    full = _lp_rows(cell, vw, prob, None)                  # all 7 dims (full re-resolution at export)

    cert.save(c, cert_out)

    row = {
        "scene": scene_path,
        "obstacle": sc.pairs[0],
        "robot": meta["robot"],
        "kinematics_parity_urdf": "~2e-6 (S10-bis, A41)", "body_parity": "~1.7e-6 (S10-ter)",
        "verdict": res.verdict, "verify_ok": ok, "verify_msg": msg,
        "n_active": len(active), "active_dims": active,
        "passive_dims": [i for i in range(len(sc.box)) if i not in active],
        "leaves": len(c["leaves"]), "by_status": res.stats["by_status"],
        "n_reresolve_failed": c["stats"]["n_reresolve_failed"],            # A32
        # [S12/L6] export contract
        "l6_applicability": l6,
        "n_leaves_embedded": c["stats"]["n_leaves_embedded"],
        "n_leaves_resolved": c["stats"]["n_leaves_resolved"],
        "n_embed_rejected": c["stats"]["n_embed_rejected"],                # A32 extended
        "cost_leaf_reduced_rows": reduced, "cost_leaf_full_rows": full,
        "reduction_x": round(full / reduced, 1),
        "phases_s": {"build_fk_sympy": round(t_build, 2),
                     "branch_and_bound": round(t_engine, 2),
                     "export_certificate": round(t_export, 2)},
        "certify_s": round(t_certify, 2), "verify_s": round(t_verify, 2),
        "groundtruth": gt, "predicted": predicted,
    }
    h, dirty = _git()
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    outdir = os.path.join("benchmarks", "results", ts)
    os.makedirs(outdir, exist_ok=True)
    payload = {"session": meta["session"], "gate": meta["gate"],
               "commit": h, "git_dirty": dirty, "note": meta["note"], "row": row}
    with open(os.path.join(outdir, meta["key"] + ".json"), "w") as f:
        json.dump(payload, f, indent=2, default=str)

    print(f"verdict={res.verdict} verify_ok={ok} A32={row['n_reresolve_failed']} "
          f"leaves={row['leaves']} {row['by_status']}")
    print(f"ground truth (A43): start_free={gt['start_free']} goal_free={gt['goal_free']} "
          f"slab_corner_free={gt['slab_corner_free']} redundancy_all_collide={gt['redundancy_all_collide']}")
    print(f"franc margins: slab penetration +{gt['slab_penetration_mm']} mm / "
          f"start-goal clearance +{gt['startgoal_clearance_mm']} mm")
    print(f"active_dims={active}  reduced_rows={reduced} "
          f"(predit {predicted['cost_leaf_reduced_rows']})  "
          f"full_rows={full}  reduction={row['reduction_x']}x")
    print(f"[L6] embedded={row['n_leaves_embedded']} resolved={row['n_leaves_resolved']} "
          f"rejected={row['n_embed_rejected']} (attendu 0) | "
          + " ; ".join(f"{nm}: applicable={v['applicable']} passives={v['passive']}"
                       for nm, v in l6.items()))
    print(f"phases: build FK sympy {row['phases_s']['build_fk_sympy']} s + b&b "
          f"{row['phases_s']['branch_and_bound']} s + export "
          f"{row['phases_s']['export_certificate']} s")
    print(f"certify={row['certify_s']}s  verify={row['verify_s']}s"
          + (f"   (prédit A44 ~{predicted['certify_s']} s ⟹ écart "
             f"{100*(row['certify_s']-predicted['certify_s'])/predicted['certify_s']:+.0f} %)"
             if "certify_s" in predicted else ""))
    print(f"cert archived: {cert_out}   results: {outdir}/{meta['key']}.json  "
          f"commit={h} dirty={dirty}")
    okall = (res.verdict == "PROOF" and ok and row["n_reresolve_failed"] == 0
             and row["n_embed_rejected"] == 0
             and gt["start_free"] and gt["goal_free"] and gt["slab_corner_free"] == 0
             and gt["redundancy_all_collide"] and gt["slab_penetration_mm"] > 40
             and gt["startgoal_clearance_mm"] > 40)
    return 0 if okall else 1


def main(argv=None) -> int:
    import sys
    paths = (argv if argv is not None else sys.argv[1:]) or [SCENE]
    rc = 0
    for pth in paths:
        print(f"######## {pth}")
        rc |= run_case(pth)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
