"""S10-quinquies — V6-bis figures for the REAL iiwa7 flagship (scenes/S6_iiwa_real_shelf.yaml).

Two static complements to the interactive A24 artifact, both driven by the CONVEX-BODY oracle
(A43 — the faithful 40-vertex silhouette, NOT the segment oracle; a figure that used the segment
would LIE about a 40-vertex body):

  - C-space cut (shoulder pitch s1 = SEPARATOR on x × base yaw s0 on y): the slab |s1|<=delta in
    gold is a full-height COLLISION WALL separating start (q2<0, body low, free) from goal (q2>0,
    body low, free); a dashed escape attempt detours in yaw yet still plunges into the wall (A20:
    shows why one would believe a path exists). A25 joint limits footer with CORRECTED physical
    labels (q2 = tangage/pitch, not the raw chain 'lacet z').
  - SWEEP (A20 NON NÉGOCIABLE), side view x–z: the arm interpolated start->goal swings UP through
    q2≈0, where every mid pose plunges the proximal body into the overhead shelf (red). One SEES
    the free space under the shelf (where start/goal sit) and why the redundant arm looks like it
    should pass — then every intermediate pose collides.

PLAUSIBILITÉ / intention (rule 11). The proof is `cnp certify` + `cnp verify` (exact).
Run: ``python scripts/make_real_flagship_figures.py`` -> benchmarks/figures/S10_real_flagship/*.png
"""
from __future__ import annotations

import os

import numpy as np

from cnp import scenes, viz

OUT = os.path.join("benchmarks", "figures", "S10_real_flagship")
SCENE = os.path.join("scenes", "S6_iiwa_real_shelf.yaml")


def _sweep_hull_silhouette(sc, oracle, path, n=11, project=(0, 2), title=None):
    """Faithful side-view sweep: at each of ``n`` poses interpolated start->goal, draw the
    CERTIFIED 40-vertex body silhouette (convex hull of its FK-transformed vertices, projected)
    coloured by the CONVEX oracle — green free / red colliding — over the shelf rectangle, plus
    a faint proximal arm line for context. Unlike a full-skeleton fan, this shows exactly the
    geometry the certificate reasons about (only the proximal body is an obstacle here), so a
    free pose never draws its body inside the shelf (A20/A40: the figure must not lie)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Rectangle
    from scipy.spatial import ConvexHull

    i, j = project
    body = scenes._body_fk(sc)
    hv = [[float(c) for c in v] for v in sc.hull_vertices]
    st = np.array([float(v) for v in sc.start_s])
    go = np.array([float(v) for v in sc.goal_s])

    fig, ax = plt.subplots(figsize=(7.8, 7.2))
    for nm, (A, b) in sc.obstacles.items():
        bnds = viz._box_bounds(A, b)
        if bnds is None:
            continue
        (xlo, xhi), (ylo, yhi) = bnds[i], bnds[j]
        ax.add_patch(Rectangle((xlo, ylo), xhi - xlo, yhi - ylo,
                               facecolor="0.6", edgecolor="0.3", alpha=0.85, zorder=1))
        ax.text((xlo + xhi) / 2, yhi + 0.02, nm, ha="center", va="bottom",
                fontsize=8, weight="bold", zorder=6)

    n_coll = 0
    for k in range(n):
        s = st + (go - st) * (k / (n - 1))
        colliding = bool(oracle(s))
        n_coll += colliding
        colour = "#d62728" if colliding else "#2ca02c"
        W = np.array([body.eval_world_point(v, s) for v in hv])            # 40 world verts
        base = W.mean(axis=0)
        ax.plot([0, base[i]], [0, base[j]], "-", color=colour, lw=0.8, alpha=0.35, zorder=2)
        P = W[:, [i, j]]
        try:
            poly = P[ConvexHull(P).vertices]
            ax.add_patch(Polygon(poly, closed=True, facecolor=colour, edgecolor=colour,
                                 alpha=0.45, lw=1.0, zorder=3))
        except Exception:
            ax.plot(P[:, 0], P[:, 1], "o", color=colour, ms=2, zorder=3)
    ax.plot(0, 0, "ks", ms=9, zorder=7)
    ax.set_aspect("equal")
    ax.grid(True, ls=":", alpha=0.5)
    ax.set_xlabel(f"axe monde {i} (m)")
    ax.set_ylabel(f"axe monde {j} (m)")
    ax.set_title(title or f"balayage start->goal : {n_coll}/{n} corps en collision (rouge)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path

# escape attempt in (s1 = pitch, s0 = yaw): detour in base yaw over the top, yet every route from
# start (s1=-0.6) to goal (s1=+0.6) must cross the vertical collision wall at |s1|<=delta.
ESCAPE = [(-0.6, 0.0), (-0.3, 0.45), (-0.1, 0.6), (0.0, 0.62), (0.1, 0.6), (0.3, 0.45), (0.6, 0.0)]


def main():
    os.makedirs(OUT, exist_ok=True)
    sc, _ = scenes.load(SCENE)
    oracle = scenes.convex_collision_oracle(sc)                 # A43: faithful 40-vertex body

    cpath = os.path.join(OUT, "S6_real_shelf_cspace.png")
    viz.save_cspace_figure(
        sc, oracle, cpath, axes=(1, 0), n=90,                  # s1 (barrier) on x -> vertical gold wall
        title="FLAGSHIP vrai iiwa7 — changer le SIGNE du pitch d'épaule q2 est IMPOSSIBLE"
              "\n[apparence faisable A20 ; plausibilité — preuve : cnp certify + cnp verify]",
        axis_labels=("tangage épaule  s1  (q2 = 2·arctan s1)  ★ SÉPARATEUR",
                     "lacet base  s0  (q1)"),
        paths=[("tentative d'évasion (détour par le lacet)", ESCAPE)],
        footer=viz.limits_caption(sc),
    )
    print("wrote", cpath)

    spath = os.path.join(OUT, "S6_real_shelf_sweep.png")
    _sweep_hull_silhouette(
        sc, oracle, spath, n=11, project=(0, 2),               # side view x–z (pitch / height)
        title="Sweep start->goal (vue de CÔTÉ x–z) — le CORPS proximal (silhouette 40 sommets)"
              "\nmonte par q2≈0 et percute l'étagère : corps en collision en ROUGE (A20)")
    print("wrote", spath)


if __name__ == "__main__":
    main()
