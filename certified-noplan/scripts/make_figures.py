"""make figures — certified-partition figures for the regression scenes E3/E4
(CLAUDE.md S3 task 4 + validation V1). Generalises sandbox_reference/make_figure.py
to drive the real cnp.engine instead of the sandbox oracle.

Each scene gets two panels:
  (a) sampled ground-truth C-space (coloured by which obstacle the arm hits) + the
      gold slab band + start/goal — this is INTENTION only (a sample never proves
      anything; the certificate does), here to read the relay story;
  (b) the engine's certified partition: one rectangle per leaf, coloured by the pair
      that certified it (UP/DOWN/MID), outside = grey, FAIL = black. A correct figure
      shows a continuous gold slab band with NO black cell, the three pair colours
      relaying, and refinement concentrated near slab boundaries / relay zones.

Usage:  python scripts/make_figures.py [--out DIR]   (default DIR=benchmarks/figures)
"""
import argparse
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "tests"))

import eng_scenes  # noqa: E402
import phi_scenes  # noqa: E402
import regref  # noqa: E402
from cnp import engine, phifit  # noqa: E402

COLORS = {"UP": "#d62728", "DOWN": "#1f77b4", "MID": "#2ca02c",
          "outside": "#dddddd", "FAIL": "black", "undecided": "#ff7f0e"}
NAMES = ["UP", "DOWN", "MID"]
BOXES = [regref.UP, regref.DOWN, regref.MID]


def _ground_truth(ax, phi, delta, start, goal, n=161):
    s = np.linspace(-1, 1, n)
    img = np.ones((n, n, 3))
    for i, s2 in enumerate(s):
        for j, s1 in enumerate(s):
            th1, th2 = 2 * np.arctan(s1), 2 * np.arctan(s2)
            hits = [regref.seg_box_hit(th1, th2, b, m=25) for b in BOXES]
            if any(hits):
                c = matplotlib.colors.to_rgb(COLORS[NAMES[hits.index(True)]])
                img[i, j] = [0.55 + 0.45 * x for x in c]
    ax.imshow(img, origin="lower", extent=[-1, 1, -1, 1], aspect="auto")
    # gold slab band {|phi| <= delta}; for phi = s1 it is a vertical band, for the
    # learned phi we shade where the sampled |phi| <= delta.
    from cnp.polylin import teval
    band = np.array([[1.0 if abs(teval(phi, [s1, s2])) <= delta else 0.0
                      for s1 in s] for s2 in s])
    ax.contourf(s, s, band, levels=[0.5, 1.5], colors=["gold"], alpha=0.30)
    ax.plot([np.tan(start[0] / 2)], [np.tan(start[1] / 2)], "k*", ms=16)
    ax.plot([np.tan(goal[0] / 2)], [np.tan(goal[1] / 2)], "kP", ms=12)
    ax.set_xlabel("s1"); ax.set_ylabel("s2")


def _partition(ax, result):
    for lf in result.leaves:
        (a1, b1), (a2, b2) = lf.cell
        fc = COLORS.get(lf.pair, COLORS.get(lf.status, "white"))
        ax.add_patch(Rectangle((a1, a2), b1 - a1, b2 - a2, facecolor=fc,
                               edgecolor="k", linewidth=0.3,
                               alpha=0.9 if lf.status == "collision" else 0.35))
    ax.set_xlim(-1, 1); ax.set_ylim(-1, 1)
    ax.set_xlabel("s1")


def figure_for(name, prob, phi, delta, start, goal, out_dir):
    result = engine.solve(prob, axis="oracle")
    c = result.counts()
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2))
    _ground_truth(axes[0], phi, delta, start, goal)
    axes[0].set_title(f"(a) {name} — C-space (vérité terrain échantillonnée)\n"
                      "rouge=UP bleu=DOWN vert=MID, bande or = dalle")
    _partition(axes[1], result)
    by_pair = c["pair"]
    axes[1].set_title(f"(b) {name} — partition certifiée ({result.verdict})\n"
                      f"{c['n_leaves']} feuilles ; UP{by_pair.get('UP',0)} "
                      f"DOWN{by_pair.get('DOWN',0)} MID{by_pair.get('MID',0)}")
    fig.tight_layout()
    path = os.path.join(out_dir, f"partition_{name}.png")
    fig.savefig(path, dpi=120)
    plt.close(fig)
    print(f"{name}: {result.verdict} {c}  ->  {path}")
    return result


# --------------------------------------------------------------------------- #
# V2 (CLAUDE.md S5): C-space + phi level sets + slab, for the FITTED barrier.
# --------------------------------------------------------------------------- #

def _phi_grid(phi, degree, n, S1, S2, fixed=None, axes=(0, 1)):
    """Evaluate the (rational) phi tensor on an (S1 x S2) grid of two chosen s-axes,
    holding the others at ``fixed``. Returns the float field."""
    from cnp.polylin import teval
    pt = np.zeros((degree + 1,) * (len(fixed) if fixed is not None else 2))
    for e, c in phi.items():
        pt[tuple(int(x) for x in e)] = float(c)
    Z = np.zeros((len(S2), len(S1)))
    for i, a in enumerate(S2):
        for j, b in enumerate(S1):
            s = list(fixed) if fixed is not None else [0.0, 0.0]
            s[axes[0]], s[axes[1]] = b, a
            Z[i, j] = teval(pt, np.array(s, dtype=float))
    return Z


def _cspace_slice(ax, collision, lo, hi, n, fixed, axes):
    """Shade the sampled collision region of a 2-D s-slice (grey = colliding)."""
    S = np.linspace(lo, hi, n)
    img = np.zeros((n, n))  # 0 = free (white); collision -> grey
    for i, a in enumerate(S):
        for j, b in enumerate(S):
            s = list(fixed)
            s[axes[0]], s[axes[1]] = b, a
            if collision(np.array(s, dtype=float)):
                img[i, j] = 0.55
    ax.imshow(img, origin="lower", extent=[lo, hi, lo, hi], aspect="auto",
              cmap="Greys", vmin=0, vmax=1.0)
    return S


def _overlay_phi(ax, phi, degree, S, lo, hi, delta, fixed, axes):
    Z = _phi_grid(phi, degree, len(S), S, S, fixed=fixed, axes=axes)
    ax.contour(S, S, Z, levels=12, colors="#1f77b4", linewidths=0.6, alpha=0.7)
    ax.contourf(S, S, np.abs(Z) <= delta, levels=[0.5, 1.5], colors=["gold"],
                alpha=0.45)
    ax.contour(S, S, Z, levels=[0.0], colors="darkorange", linewidths=1.4)


def phi_figure_e4(out_dir):
    """V2 — E4-planaire: sampled C-space (grey=collision) + phi level sets (blue) +
    slab band {|phi|<=delta} (gold) + start (star) / goal (plus)."""
    fr = phifit.fit_barrier(phi_scenes.e4_collision, phi_scenes.E4_BOX,
                            phi_scenes.E4_START, phi_scenes.E4_GOAL,
                            phi_scenes.e4_build_problem, method="lstsq",
                            n_samples=3000, seed=1, solve_kw={"axis": "oracle"})
    fig, ax = plt.subplots(figsize=(6.2, 5.6))
    S = _cspace_slice(ax, phi_scenes.e4_collision, -1, 1, 161, [0.0, 0.0], (0, 1))
    _overlay_phi(ax, fr.phi, fr.phi_degree, S, -1, 1, float(fr.delta), [0.0, 0.0], (0, 1))
    ax.plot([float(phi_scenes.E4_START[0])], [float(phi_scenes.E4_START[1])],
            "k*", ms=18, label="start")
    ax.plot([float(phi_scenes.E4_GOAL[0])], [float(phi_scenes.E4_GOAL[1])],
            "kP", ms=13, label="goal")
    ax.set_xlabel("s0"); ax.set_ylabel("s1"); ax.legend(loc="upper left")
    n_leaves = len(fr.result.leaves)
    ax.set_title(f"V2 — E4 pipeline (lstsq) : phi appris, {fr.verdict}, "
                 f"{n_leaves} feuilles\ngris=collision échantillonnée, "
                 f"bleu=niveaux de phi, or=dalle |phi|<=delta={float(fr.delta):.3f}")
    fig.tight_layout()
    path = os.path.join(out_dir, "phi_E4.png")
    fig.savefig(path, dpi=120); plt.close(fig)
    print(f"phi_E4: {fr.verdict} {n_leaves} leaves -> {path}")


def phi_figure_3dof(out_dir):
    """V2 — 3-DOF spatial: two C-space slices (s0,s1 at s2=0; s0,s2 at s1=0) with phi
    level sets and the slab. phi ~ s0 (the base-yaw barrier); the gold band must sit
    inside the grey collision region with start/goal free on either side."""
    fr = phifit.fit_barrier(phi_scenes.sp_collision, phi_scenes.SP_BOX,
                            phi_scenes.SP_START, phi_scenes.SP_GOAL,
                            phi_scenes.sp_build_problem, method="lstsq",
                            n_samples=4000, seed=2, solve_kw={"axis": "margin"})
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.4))
    delta = float(fr.delta)
    for ax, (fixed, axpair, lbl) in zip(axes, [([0.0, 0.0, 0.0], (0, 1), ("s0", "s1")),
                                              ([0.0, 0.0, 0.0], (0, 2), ("s0", "s2"))]):
        S = _cspace_slice(ax, phi_scenes.sp_collision, -0.7, 0.7, 121, fixed, axpair)
        _overlay_phi(ax, fr.phi, fr.phi_degree, S, -0.7, 0.7, delta, fixed, axpair)
        ax.plot([float(phi_scenes.SP_START[axpair[0]])],
                [float(phi_scenes.SP_START[axpair[1]])], "k*", ms=18)
        ax.plot([float(phi_scenes.SP_GOAL[axpair[0]])],
                [float(phi_scenes.SP_GOAL[axpair[1]])], "kP", ms=13)
        ax.set_xlabel(lbl[0]); ax.set_ylabel(lbl[1])
    n_leaves = len(fr.result.leaves)
    fig.suptitle(f"V2 — 3-DOF pipeline (lstsq) : phi appris, {fr.verdict}, "
                 f"{n_leaves} feuilles ; gris=collision, bleu=phi, "
                 f"or=dalle |phi|<=delta={delta:.3f}")
    fig.tight_layout()
    path = os.path.join(out_dir, "phi_3dof.png")
    fig.savefig(path, dpi=120); plt.close(fig)
    print(f"phi_3dof: {fr.verdict} {n_leaves} leaves -> {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(_REPO, "benchmarks", "figures"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    from cnp.polylin import mono
    figure_for("E3", eng_scenes.e3_problem(), mono(2, 2, [1, 0]), 0.05,
               (-np.pi / 3, 0.0), (np.pi / 3, 0.0), args.out)

    prob4, start4, goal4 = eng_scenes.e4_problem()
    _phi4, delta4, _s, _g = regref.fit_phi_e4(BOXES)
    figure_for("E4", prob4, prob4.phi, prob4.delta, start4, goal4, args.out)

    phi_figure_e4(args.out)       # V2
    phi_figure_3dof(args.out)     # V2


if __name__ == "__main__":
    main()
