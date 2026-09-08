"""S11 Tâche 3 — COMPOSITE « Figure 1 » du papier (flagship vrai iiwa7).

Trois panneaux, une histoire lisible sans légende orale (critère V7) :

  (a) **rendu 3-D** : l'étagère en surplomb, le CORPS CERTIFIÉ (coque 40 sommets du
      certificat, verbatim) aux poses start et goal — basses, libres, de part et d'autre —
      et au TRANSIT ``q2≈0`` où le bras se redresse et percute l'étagère (rouge) ;
  (b) **coupe C-space** sur l'axe SÉPARATEUR (tangage d'épaule ``s1 = q2``) × le lacet de
      base : la dalle ``|φ| ≤ δ`` est un MUR de collision PLEINE HAUTEUR entre start et goal
      — c'est la déconnexion, et la redondance distale n'y change rien ;
  (c) **encadré de chiffres**, lus DANS le JSON de benchmark archivé (jamais retapés : critère
      V7 « les chiffres des tables correspondent aux JSON de benchmarks/results/ »).

Les couleurs de collision viennent de l'oracle CORPS-CONVEXE (A43) ; la figure ne peut donc
pas dessiner un corps libre dans l'obstacle (A40).

Run: python scripts/make_paper_fig1.py  ->  benchmarks/figures/paper/fig1.png
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np

from cnp import certificate as _cert
from cnp import scenes, viz

SCENE = "scenes/S6_iiwa_real_shelf.yaml"
CERT = "scenes/S6_iiwa_real_shelf.cert.json"
OUT = os.path.join("benchmarks", "figures", "paper", "fig1.png")
BENCH_GLOB = "benchmarks/results/*/flagship_S10_iiwa_real.json"
ESCAPE = [(-0.6, 0.0), (-0.3, 0.45), (-0.1, 0.6), (0.0, 0.62), (0.1, 0.6), (0.3, 0.45),
          (0.6, 0.0)]


def _latest_bench() -> dict:
    paths = sorted(glob.glob(BENCH_GLOB))
    if not paths:
        raise SystemExit(f"aucun bench archivé ({BENCH_GLOB}) — lancer "
                         "scripts/flagship_iiwa_real_bench.py d'abord (règle 7)")
    return json.load(open(paths[-1]))


def _hull_faces(V):
    from scipy.spatial import ConvexHull
    return ConvexHull(V).simplices


def _panel_3d(ax, sc, oracle):
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    body = scenes._body_fk(sc)
    hv = [[float(c) for c in v] for v in sc.hull_vertices]
    st = np.array([float(v) for v in sc.start_s])
    go = np.array([float(v) for v in sc.goal_s])
    mid = 0.5 * (st + go)

    for nm, (A, b) in sc.obstacles.items():
        bnds = viz._box_bounds(A, b)
        if bnds is None:
            continue
        (x0, x1), (y0, y1), (z0, z1) = bnds
        x1 = min(x1, 0.5); y1 = min(y1, 0.42); x0 = max(x0, -0.5); y0 = max(y0, -0.42)
        z1 = min(z1, z0 + 0.05)                       # on ne dessine que le dessous utile
        c = [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
             [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]]
        faces = [[c[i] for i in f] for f in
                 ([0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6],
                  [1, 2, 6, 5], [0, 3, 7, 4])]
        ax.add_collection3d(Poly3DCollection(faces, facecolor="0.55", edgecolor="0.3",
                                             alpha=0.30, lw=0.5))
        ax.text(0, y1, z1 + 0.035, nm, fontsize=7.5, weight="bold", ha="center")

    for s, colour, lbl in ((st, "#1f77b4", "start (q2<0, bras incliné — LIBRE)"),
                           (mid, "#d62728", "transit q2≈0 (bras DROIT — COLLISION)"),
                           (go, "#2ca02c", "goal (q2>0, bras incliné — LIBRE)")):
        W = np.array([body.eval_world_point(v, s) for v in hv])
        assert (colour == "#d62728") == bool(oracle(s)), "la figure mentirait (A40)"
        tri = [[W[i] for i in f] for f in _hull_faces(W)]
        ax.add_collection3d(Poly3DCollection(tri, facecolor=colour, edgecolor=colour,
                                             alpha=0.75, lw=0.3))
        # trait épaule→corps seulement : le squelette complet (19 repères de chaîne) part
        # loin hors cadre et brouille la lecture ; ici on situe le CORPS certifié, rien d'autre.
        c = W.mean(axis=0)
        ax.plot([0, c[0]], [0, c[1]], [0, c[2]], "-", color=colour, lw=1.4, alpha=0.6)
        ax.plot([], [], [], "-", color=colour, lw=6, alpha=0.85, label=lbl)
    ax.plot([0], [0], [0], "ks", ms=5)

    ax.set_xlim(-0.42, 0.42); ax.set_ylim(-0.42, 0.42); ax.set_zlim(0, 0.88)
    ax.set_box_aspect((1, 1, 1.15))
    ax.view_init(elev=13, azim=-58)
    ax.set_xlabel("x (m)", labelpad=-8, fontsize=7)
    ax.set_ylabel("y (m)", labelpad=-8, fontsize=7)
    ax.set_zlabel("z (m)", labelpad=-6, fontsize=7)
    ax.tick_params(labelsize=5.5, pad=-3)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.02), fontsize=6.8,
              framealpha=0.94, borderpad=0.35, handlelength=1.4)
    ax.set_title("(a) vrai KUKA iiwa7 — le corps proximal certifié\nne peut pas se redresser",
                 fontsize=9, pad=0)


def _panel_cspace(ax, sc, oracle, n=110):
    bdim, other = 1, 0
    xs = np.linspace(float(sc.box[bdim][0]), float(sc.box[bdim][1]), n)
    ys = np.linspace(float(sc.box[other][0]), float(sc.box[other][1]), n)
    grid = np.zeros((n, n))
    s = np.zeros(sc.robot.n)
    for b, sy in enumerate(ys):
        for a, sx in enumerate(xs):
            s[:] = 0.0
            s[bdim], s[other] = sx, sy
            grid[b, a] = 1.0 if oracle(s) else 0.0
    ax.imshow(grid, origin="lower", extent=[xs[0], xs[-1], ys[0], ys[-1]], aspect="auto",
              cmap="Greys", vmin=0, vmax=1.7, alpha=0.85)
    delta = float(sc.delta)
    ax.axvspan(-delta, delta, color="gold", alpha=0.35, zorder=2)
    ax.text(0, ys[-1] * 0.82, f"dalle |φ| ≤ {sc.delta}\nMUR pleine hauteur", ha="center",
            fontsize=7.5, weight="bold", zorder=6,
            bbox=dict(boxstyle="round", fc="#fff7e0", ec="#e0c060", alpha=0.95))
    P = np.asarray(ESCAPE, float)
    ax.plot(P[:, 0], P[:, 1], "--", lw=1.8, color="#7f0000", zorder=4,
            label="tentative d'évasion (détour par le lacet)")
    st = [float(v) for v in sc.start_s]
    go = [float(v) for v in sc.goal_s]
    ax.plot(st[bdim], st[other], "*", color="#1f77b4", ms=17, mec="k", zorder=5, label="start")
    ax.plot(go[bdim], go[other], "P", color="#2ca02c", ms=13, mec="k", zorder=5, label="goal")
    names = [nm for nm, _, _ in viz.joint_limits_deg(sc)]
    ax.set_xlabel(f"{names[bdim]}  s1  (q2 = 2·arctan s1)   ★ SÉPARATEUR", fontsize=8)
    ax.set_ylabel(f"{names[other]}  s0  (q1)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.30), ncol=3, fontsize=6.8,
              framealpha=0.95)
    ax.set_title("(b) coupe C-space — start et goal sont\ndans DEUX composantes libres",
                 fontsize=9)
    ax.text(0.5, -0.155, "le cadre de ce graphe = les limites articulaires (la boîte P)",
            transform=ax.transAxes, ha="center", fontsize=6.6, style="italic")


def _panel_stats(ax, sc, bench, cert):
    import textwrap
    row = bench["row"]
    gt = row["groundtruth"]
    ax.axis("off")
    st = row["by_status"]
    st_txt = ", ".join(f"{v} {k}" for k, v in st.items()) if isinstance(st, dict) else str(st)
    lines = [
        ("verdict", f"PROOF — re-vérifié en arithmétique EXACTE par un programme "
                    f"indépendant, en {row['verify_s']} s"),
        ("certificat", f"{row['leaves']} feuilles ({st_txt}) · dissonance "
                       f"décision↔certificat A32 = {row['n_reresolve_failed']}"),
        ("réduction A30", f"LP de feuille : {row['cost_leaf_reduced_rows']} lignes (réduit "
                          f"aux 3 dims actives) contre {row['cost_leaf_full_rows']} en "
                          f"pleine dim — ×{row['reduction_x']}"),
        ("marge FRANCHE", f"+{gt['slab_penetration_mm']} mm de pénétration dans la dalle · "
                          f"+{gt['startgoal_clearance_mm']} mm de dégagement aux poses "
                          f"(le marginal a été refusé, cf. les ~6 mm du lacet de base)"),
        ("fidélité au robot", f"cinématique {row['kinematics_parity_urdf']} · silhouette "
                              f"convexe {row['body_parity']} — modèle interne EXACT "
                              f"(verify recompte en Fraction)"),
        ("redondance", "les 4 joints distaux sont PROUVÉS passifs pour cette paire : ils ne "
                       "peuvent pas dégager le corps. C'est la thèse."),
        ("limites (A25)", viz.limits_caption(sc)),
    ]
    y = 0.985
    ax.text(0.0, y, "(c) ce que le certificat établit", fontsize=10.5, weight="bold",
            va="top")
    y -= 0.075
    for k, v in lines:
        ax.text(0.0, y, k, fontsize=8.0, weight="bold", va="top", color="#1a237e")
        y -= 0.036
        for chunk in textwrap.wrap(v, 62):
            ax.text(0.025, y, chunk, fontsize=7.4, va="top")
            y -= 0.031
        y -= 0.018
    y -= 0.01
    ax.text(0.0, y, "ce que le certificat NE prouve PAS", fontsize=8.0, weight="bold",
            va="top", color="#7a2020")
    y -= 0.036
    for chunk in textwrap.wrap(
            "rien hors de ces limites articulaires ni hors de la géométrie modélisée ; "
            "rien de dynamique (vitesses, capteurs, arrêts). UNDECIDED ≠ infaisable. "
            "Fidèle à l'URDF iiwa7 à ~2e-6 près — PAS « le iiwa exact ».", 62):
        ax.text(0.025, y, chunk, fontsize=7.4, va="top", style="italic", color="#7a2020")
        y -= 0.031
    ax.text(0.0, y - 0.02, f"source : commit {bench.get('commit','?')} · "
                           f"benchmarks/results/ · {CERT}", fontsize=6.2, va="top",
            color="#666")


def main() -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    sc, _ = scenes.load(SCENE)
    cert = _cert.load(CERT)
    bench = _latest_bench()
    oracle = scenes.convex_collision_oracle(sc)

    fig = plt.figure(figsize=(14.4, 6.2))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.0, 1.05], wspace=0.20,
                          left=0.02, right=0.985, top=0.86, bottom=0.13)
    _panel_3d(fig.add_subplot(gs[0, 0], projection="3d"), sc, oracle)
    _panel_cspace(fig.add_subplot(gs[0, 1]), sc, oracle)
    _panel_stats(fig.add_subplot(gs[0, 2]), sc, bench, cert)
    fig.suptitle("Infaisabilité CERTIFIÉE sur un vrai bras redondant 7 axes : "
                 "start et goal sont libres, et pourtant AUCUN chemin ne les relie",
                 fontsize=12.5, y=0.975)
    fig.savefig(OUT, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {OUT}  ({os.path.getsize(OUT)/1024:.0f} ko)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
