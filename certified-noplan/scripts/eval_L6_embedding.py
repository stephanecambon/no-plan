"""S11 ouverture — ÉVALUATION [L6] : export du certificat RÉDUIT *embedé* en pleine dimension.

**MESURE SEULE — HORS CHEMIN PAR DÉFAUT.** Ce script ne modifie NI ``certificate.make_certificate``
NI aucun module de ``src/cnp`` ; il assemble un certificat candidat dans son propre coin, le soumet
à l'arbitre exact ``verify.verify`` + au cross-check de scène, et chronomètre. La décision de
basculer (ou non) le contrat d'export est une décision de PILOTAGE (revue de supervision), pas une
décision de Code (CLAUDE.md S11, D58).

LA QUESTION (revue S10-quinquies). Le chemin par défaut décide chaque feuille sur un LP RÉDUIT aux
dims actives (A30) puis **re-résout le LP en PLEINE dimension** pour exporter (λ, μ) — c'est ce
terme qui domine le wall-clock (726 s sur le flagship S6, ~99,5 %). Quand les dims passives
n'entrent **ni dans D ni dans N** (cas proximal : le lien 3 de l'iiwa est en amont de q4..q7), le
polynôme plein est **constant** le long de ces axes : le LP plein est le MÊME problème avec
``(d+1)^4`` fois plus de points de contrôle. On devrait alors pouvoir **embarquer** la solution
réduite en pleine dim (exposants nuls sur les axes passifs) au lieu de re-résoudre.

L'ARGUMENT (pourquoi c'est sound quoi qu'il arrive). ``verify`` reste l'arbitre en pleine dimension
et ne partage aucun code avec le générateur : un embedding faux est REJETÉ ⟹ le verdict retombe à
ENGINE-PROOF / UNDECIDED, jamais un faux PROOF (c'est exactement l'argument S8/A30).

CONDITION D'APPLICABILITÉ à vérifier ici (pas à présumer) : A29 ne doit avoir divisé AUCUN facteur
``(1+s_i^2)`` de la chaîne du corps. Si A29 a divisé, la géométrie réduite n'est plus la géométrie
originale restreinte (``D_plein = P(s) · D_réduit``) alors que ``T = delta^2 - phi^2`` n'est PAS
divisé — l'embedding direct ne vaut plus et la re-résolution reste obligatoire. Un rejet dans ce
cas serait un RÉSULTAT, pas un bug.

SORTIE : un bench DATÉ (règle 7) sous ``benchmarks/results/<horodatage>/L6_eval.json`` avec le
commit et l'état git, la condition d'applicabilité, les tailles de LP (lignes ET colonnes, A44),
les temps par phase, et le verdict de ``verify``.

Usage :
    python scripts/eval_L6_embedding.py [scene.yaml] [--with-default]

``--with-default`` re-mesure AUSSI, dans le même run et sur la même machine, le chemin par
défaut (re-résolution pleine dim) pour que la comparaison soit apparaît-à-apparaît (~11 min sur
le flagship S6). Sans ce drapeau, seul le candidat L6 est mesuré.
"""
from __future__ import annotations

import json
import os
import sys
import time
from fractions import Fraction

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cnp import certificate as _cert          # noqa: E402
from cnp import engine as _engine             # noqa: E402
from cnp import scenes as _scenes             # noqa: E402
from cnp import verify as _verify             # noqa: E402
from cnp import witness as _witness           # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SCENE = os.path.join(HERE, "..", "scenes", "S6_iiwa_real_shelf.yaml")


# --------------------------------------------------------------------------- #
# Condition d'applicabilité (A29 + géométrie originale)
# --------------------------------------------------------------------------- #

def applicability(problem) -> dict:
    """La projection S8/A30 est-elle exacte sur la géométrie ORIGINALE, pair par pair ?

    Deux volets, tous deux nécessaires :
      * ``a29_removed`` — les axes dont A29 a dû diviser un facteur ``(1+s_i^2)`` pour
        révéler la passivité. NON VIDE ⟹ embedding direct attendu INVALIDE.
      * ``original_independent`` — les axes passifs dont ni ``D`` ni AUCUN numérateur
        ORIGINAL ne dépend (avant toute simplification). C'est la condition L6.
    """
    n = problem.n
    out = []
    for pr in problem.pairs:
        _v, _D, removed = _engine._simplify_geometry(pr.verts_num, pr.D, n)
        view = [w for w in _engine.pair_views(problem) if w.pair.name == pr.name][0]
        passive = tuple(i for i in range(n) if i not in view.active)
        orig_indep = tuple(
            i for i in passive
            if not _engine._tensor_depends(pr.D, i)
            and not any(_engine._tensor_depends(c, i) for v in pr.verts_num for c in v)
            and not _engine._tensor_depends(problem.phi, i))
        out.append({"pair": pr.name, "active": view.active, "passive": passive,
                    "a29_removed": removed, "original_independent": orig_indep,
                    "l6_applicable": (not removed) and set(orig_indep) == set(passive)})
    return {"per_pair": out, "applicable": all(p["l6_applicable"] for p in out)}


# --------------------------------------------------------------------------- #
# Taille RÉELLE des LP (A44 : lignes ET colonnes)
# --------------------------------------------------------------------------- #

def lp_shapes(cell, view, problem) -> dict:
    """Lignes ET colonnes du LP de feuille, réduit vs plein (discipline A44)."""
    def shape(active):
        lp = _witness.build_witness_lp(
            cell, view.verts_num if active is not None else view.pair.verts_num,
            view.D if active is not None else view.pair.D,
            view.pair.obstacle, phi=problem.phi, delta=problem.delta,
            lam_degree=problem.lam_degree, active_dims=active)
        rows = lp.lam_A.shape[0] + lp.face_Az.shape[0]
        return {"rows_total": int(rows), "rows_lambda": int(lp.lam_A.shape[0]),
                "rows_faces": int(lp.face_Az.shape[0]),
                "cols_total": int(lp.nz + lp.nmu + 1), "cols_lambda": int(lp.nz),
                "cols_mu": int(lp.nmu), "K": int(lp.K), "basis": int(len(lp.basis))}
    return {"reduced": shape(view.active), "full": shape(None)}


# --------------------------------------------------------------------------- #
# Export EMBEDÉ (le candidat L6)
# --------------------------------------------------------------------------- #

def _embed_expo(e_red, active, n_full):
    e = [0] * n_full
    for pos, ax in enumerate(active):
        e[ax] = int(e_red[pos])
    return tuple(e)


def embedded_leaf(lf, view, problem, backend, n_full, max_den):
    """Résout le LP RÉDUIT de la feuille et embarque (λ, μ) en pleine dimension.

    L'embedding : chaque coefficient λ d'exposant ``e`` sur les dims actives devient le même
    coefficient d'exposant ``e`` complété par des ZÉROS sur les dims passives — c.-à-d. le même
    polynôme, vu comme constant le long des axes passifs. μ (un par face) est inchangé."""
    cell = [(float(lo), float(hi)) for lo, hi in lf.cell]
    lp = _witness.build_witness_lp(cell, view.verts_num, view.D, view.pair.obstacle,
                                   phi=problem.phi, delta=problem.delta,
                                   lam_degree=problem.lam_degree,
                                   active_dims=view.active)
    res = backend.solve(lp)
    if res.z is None or res.t is None or res.t <= 0:
        raise RuntimeError(f"leaf {lf.cell}: reduced LP has no positive margin "
                           f"(status={res.status})")
    lam_red, mu = _cert._export_multipliers(res, lp, max_den)
    lam_full = [{_embed_expo(e, view.active, n_full): c for e, c in tk.items()}
                for tk in lam_red]
    return {"cell": [[str(lo), str(hi)] for lo, hi in lf.cell], "status": "collision",
            "obstacle": lf.pair, "lambda": [_cert._tensor_str(t) for t in lam_full],
            "mu": [str(m) for m in mu],
            "margin": str(Fraction(float(res.t)).limit_denominator(max_den))}


def columns_check(results_dir: str) -> dict:
    """[A44] Confirmer/infirmer l'explication « COLONNES » de l'écart de wall-clock.

    Le témoin S9f k=7 (banc du mur, corps-SEGMENT K=2) et le flagship S6 (vrai iiwa7, coque
    K=40) ont des LP pleine dim de MÊME hauteur (~470 k lignes) : la seule différence
    structurelle est le nombre de COLONNES λ (``nz = K · |basis|``). Si le temps d'export par
    feuille diverge d'un grand facteur à lignes constantes, l'explication « colonnes » tient.

    Lit les DEUX benchs archivés — aucune nouvelle mesure, aucune extrapolation."""
    root = os.path.join(HERE, "..")
    s9f = json.load(open(os.path.join(
        root, "benchmarks/results/20260613T014131Z/wall_resonde_S9f.json")))
    k7 = [r for r in s9f["rows"] if r["k"] == 7][0]
    l6 = json.load(open(os.path.join(results_dir, "L6_eval.json")))
    full = l6["lp_shapes"]["full"]
    # S9f k=7 : corps-SEGMENT K=2, base affine en 7 dims = 8 ⟹ nz = 16 colonnes λ (+6 μ +1 t)
    s9f_cols = 2 * 8 + 6 + 1
    s9f_per_leaf = k7["cert_s"] / k7["leaves"]
    s6_per_leaf = l6["export_default_fulldim_s"] / l6["n_leaves"]
    out = {"witness_S9f_k7": {"rows": k7["cost_leaf_rows"] if "cost_leaf_rows" in k7
                              else 469006, "cols": s9f_cols, "K": 2,
                              "export_s_per_leaf": s9f_per_leaf, "source":
                              "benchmarks/results/20260613T014131Z/wall_resonde_S9f.json"},
           "flagship_S6": {"rows": full["rows_total"], "cols": full["cols_total"],
                           "K": full["K"], "export_s_per_leaf": s6_per_leaf,
                           "source": os.path.relpath(results_dir, root) + "/L6_eval.json"},
           "ratio_rows": full["rows_total"] / 469006,
           "ratio_cols": full["cols_total"] / s9f_cols,
           "ratio_export_time": s6_per_leaf / s9f_per_leaf}
    out["implied_exponent_in_cols"] = (
        np.log(out["ratio_export_time"]) / np.log(out["ratio_cols"]))
    out["verdict"] = ("hypothèse COLONNES CONFIRMÉE : à lignes quasi identiques "
                      f"(×{out['ratio_rows']:.3f}), ×{out['ratio_cols']:.1f} colonnes "
                      f"⟹ ×{out['ratio_export_time']:.0f} de temps d'export par feuille "
                      f"(≈ colonnes^{out['implied_exponent_in_cols']:.2f})"
                      if out["ratio_rows"] < 1.05 else "lignes trop différentes : non concluant")
    dest = os.path.join(results_dir, "A44_columns_check.json")
    with open(dest, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\n→ {os.path.relpath(dest, root)}")
    return out


def _git() -> dict:
    import subprocess
    def run(*a):
        return subprocess.run(a, capture_output=True, text=True,
                              cwd=os.path.join(HERE, "..")).stdout.strip()
    return {"commit": run("git", "rev-parse", "--short", "HEAD"),
            "git_dirty": bool(run("git", "status", "--porcelain"))}


def main(scene_path: str, with_default: bool = False) -> int:
    print("=" * 78)
    print("ÉVALUATION [L6] — export du certificat RÉDUIT embedé en pleine dimension")
    print("MESURE SEULE : le chemin par défaut (make_certificate) n'est PAS modifié.")
    print("=" * 78)
    t0 = time.perf_counter()
    scene, sbudget = _scenes.load(scene_path)
    problem = _scenes.build_problem(scene, max_depth=sbudget.max_depth)
    t_build = time.perf_counter() - t0
    n = problem.n
    backend = _engine.ENGINE_BACKEND
    print(f"\nscène   : {scene_path}")
    print(f"robot   : {scene.robot.kind}, n={n} dims-s, corps = link {scene.body_link}, "
          f"K={len(scene.hull_vertices)} sommets")
    print(f"build FK (sympy) + parse : {t_build:.1f} s  (commun aux deux chemins)")

    # --- 1. condition d'applicabilité -------------------------------------- #
    ap = applicability(problem)
    print("\n[1] CONDITION D'APPLICABILITÉ (A29 + géométrie ORIGINALE)")
    for p in ap["per_pair"]:
        print(f"    pair {p['pair']!r}: actives={p['active']} passives={p['passive']}")
        print(f"        A29 a divisé (1+s^2) sur : {p['a29_removed'] or '∅'}  "
              f"{'⟹ embedding direct ATTENDU INVALIDE' if p['a29_removed'] else '(aucun)'}")
        print(f"        passives absentes de D ET N ORIGINAUX : {p['original_independent']}")
        print(f"        ⟹ L6 applicable pour cette paire : {p['l6_applicable']}")
    print(f"    VERDICT applicabilité : {ap['applicable']}")

    # --- 2. décision (b&b) -------------------------------------------------- #
    print("\n[2] DÉCISION (b&b, chemin normal — commun aux deux exports)")
    t0 = time.perf_counter()
    result = _engine.solve(problem, budget=sbudget.engine_budget(), axis=sbudget.axis)
    t_engine = time.perf_counter() - t0
    print(f"    verdict={result.verdict}  feuilles={len(result.leaves)}  "
          f"({result.counts()})  wall-clock = {t_engine:.2f} s")
    if result.verdict != "PROOF":
        print("    STOP : pas un PROOF, rien à exporter.")
        return 1

    # --- 3. taille RÉELLE des LP (A44) -------------------------------------- #
    views = _engine.pair_views(problem)
    coll = [lf for lf in result.leaves if lf.status == "collision"]
    view0 = [w for w in views if w.pair.name == coll[0].pair][0]
    sh = lp_shapes([(float(lo), float(hi)) for lo, hi in coll[0].cell], view0, problem)
    print("\n[3] TAILLE RÉELLE DU LP DE FEUILLE (A44 : lignes ET colonnes)")
    for tag in ("reduced", "full"):
        s = sh[tag]
        print(f"    {tag:8s}: {s['rows_total']:>7d} lignes "
              f"({s['rows_lambda']} λ + {s['rows_faces']} faces) × "
              f"{s['cols_total']:>4d} colonnes "
              f"({s['cols_lambda']} λ = K{s['K']}×{s['basis']} + {s['cols_mu']} μ + 1 t)")
    print(f"    ratio lignes = ×{sh['full']['rows_total']/sh['reduced']['rows_total']:.1f}"
          f"   ratio colonnes = ×{sh['full']['cols_total']/sh['reduced']['cols_total']:.1f}")

    # --- 4. export EMBEDÉ + verify ------------------------------------------ #
    print("\n[4] EXPORT EMBEDÉ (candidat L6) + arbitrage par verify (pleine dim)")
    t0 = time.perf_counter()
    leaves = []
    for lf in result.leaves:
        if lf.status == "outside":
            leaves.append({"cell": [[str(lo), str(hi)] for lo, hi in lf.cell],
                           "status": "outside"})
        else:
            v = [w for w in views if w.pair.name == lf.pair][0]
            leaves.append(embedded_leaf(lf, v, problem, backend, n,
                                        _cert.DEFAULT_MAX_DEN))
    t_export = time.perf_counter() - t0

    # en-tête du certificat : STRICTEMENT celui du chemin par défaut (seules les
    # feuilles changent) — on isole ainsi exactement l'objet évalué.
    cert = _header_only(scene, result)
    cert["leaves"] = leaves
    cert["stats"] = {"n_leaves": len(leaves),
                     "n_collision": sum(1 for l in leaves if l["status"] == "collision"),
                     "n_outside": sum(1 for l in leaves if l["status"] == "outside"),
                     "n_reresolve_failed": 0,
                     "export": "L6_embedded_reduced (EVALUATION ONLY)"}
    print(f"    export embedé : {t_export:.2f} s "
          f"({len(leaves)} feuilles, {cert['stats']['n_collision']} collision)")

    t0 = time.perf_counter()
    ok, msg = _verify.verify(cert)
    t_verify = time.perf_counter() - t0
    print(f"    verify.verify : {'ACCEPTÉ' if ok else 'REJETÉ'} — {msg}")
    print(f"    verify wall-clock = {t_verify:.2f} s")

    xmatch, xwhy = _scenes.scene_matches_cert(scene, cert)
    print(f"    cross-check scène : {'OK' if xmatch else 'REJET'} — {xwhy}")

    # --- 5. chemin par DÉFAUT (re-résolution pleine dim), pour la comparaison ------ #
    t_default = None
    if with_default:
        print("\n[5] CHEMIN PAR DÉFAUT (re-résolution pleine dim) — comparaison même machine")
        t0 = time.perf_counter()
        cert_def = _cert.make_certificate(scene, result, verify_loop=True)
        t_default = time.perf_counter() - t0
        okd, msgd = _verify.verify(cert_def)
        print(f"    export pleine dim : {t_default:.1f} s  (verify {'OK' if okd else 'REJET'})")
        print(f"    ⟹ GAIN sur le TERME D'EXPORT : ×{t_default / max(t_export, 1e-9):.0f}")
        print(f"    ⟹ GAIN sur le certify BOUT-EN-BOUT (build FK + décision + export) : "
              f"×{(t_build + t_engine + t_default) / (t_build + t_engine + t_export):.1f}"
              f"   (le build FK sympy, {t_build:.1f} s, devient le terme dominant)")

    out = {"session": "S11-ouverture", **_git(),
           "scene": os.path.relpath(scene_path),
           "t_build_fk_s": t_build,
           "applicability": {k: (v if k != "per_pair" else
                                 [{kk: (list(vv) if isinstance(vv, tuple) else vv)
                                   for kk, vv in p.items()} for p in v])
                             for k, v in ap.items()},
           "engine_s": t_engine, "export_embedded_s": t_export, "verify_s": t_verify,
           "export_default_fulldim_s": t_default,
           "lp_shapes": sh, "verify_accepted": bool(ok), "verify_msg": msg,
           "scene_crosscheck": bool(xmatch),
           "n_leaves": len(leaves)}
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    dest = os.path.join(HERE, "..", "benchmarks", "results", stamp, "L6_eval.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\n    → {os.path.relpath(dest)}")
    return 0 if ok and xmatch else 2


def _header_only(scene, result):
    """L'en-tête EXACT du chemin par défaut (mêmes champs, mêmes rationnels), sans les
    feuilles — obtenu en assemblant un certificat dont toutes les feuilles collision sont
    retirées, puis en vidant ``leaves``. Aucune duplication de la sérialisation."""
    stub = _engine.EngineResult(
        verdict="PROOF",
        leaves=[lf for lf in result.leaves if lf.status == "outside"],
        failed=[], stats={})
    cert = _cert._assemble_certificate(scene, stub, _engine.ENGINE_BACKEND,
                                       _cert.DEFAULT_MAX_DEN)
    cert["leaves"] = []
    return cert


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--columns-check" in sys.argv:
        columns_check(args[0])
        sys.exit(0)
    sys.exit(main(args[0] if args else DEFAULT_SCENE,
                  with_default="--with-default" in sys.argv))
