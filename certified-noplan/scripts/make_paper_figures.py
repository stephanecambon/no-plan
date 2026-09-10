"""S14 — every figure of the paper, publication mode (`make paper-figures`).

Writes into ``benchmarks/figures/paper/`` at 300 dpi, English labels, no internal annotation
codes:

  fig1.png                            the iiwa7 flagship composite (scripts/make_paper_fig1.py)
  cost_vs_active_dims.png             per-leaf LP rows vs active dimensions, sealed family
  partition_E3.png                    the planar relay: sampled C-space + certified partition
  scene_S3_shoulder_elbow_sweep.png   4-DOF anchor, top view of the base-yaw sweep
  scene_S3_shoulder_elbow_cspace.png  4-DOF anchor, configuration-space cut (yaw x pitch)
  SOURCES.json                        which benchmark / certificate / scene each figure read

Every benchmark number drawn is READ from the latest ``benchmarks/results/*/reproduce.json`` or
from an archived certificate, never retyped. Geometric quantities (joint limits, obstacle
extents) are read from the scene files. Collision shading comes from oracles independent of
the certificates.

Run: python scripts/make_paper_figures.py [--reproduce PATH]
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cnp import scenes, viz                           # noqa: E402
import make_paper_fig1 as fig1                         # noqa: E402

OUT_DIR = os.path.join("benchmarks", "figures", "paper")
DPI = 300
deg = fig1.deg


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
                         "legend.fontsize": 8, "font.family": "DejaVu Sans"})
    return plt


def _limits_text(sc) -> str:
    names = fig1.english_joint_names(sc)
    parts = []
    for nm, (lo, hi) in zip(names, sc.box):
        a, b = deg(lo), deg(hi)
        parts.append(f"{nm} ±{round(max(abs(a), abs(b)))}°" if abs(a + b) < 1.0
                     else f"{nm} {round(a)}–{round(b)}°")
    return "joint limits: " + ", ".join(parts)


# --------------------------------------------------------------------------- #
# cost vs active dimensions
# --------------------------------------------------------------------------- #

def cost_vs_active_dims(rep: dict, out: str) -> dict:
    plt = _plt()
    rows = rep["rows"]
    ks, full = [], []
    for k in (3, 4, 5, 6, 7):
        r = rows[f"wall_k{k}"]
        assert r["verdict"] == "PROOF" and r["recheck_stdlib_verify_file"]["ok"], r["row"]
        ks.append(k)
        full.append(r["lp_full"]["rows"])
    r8 = rows["wall_k8"]
    assert r8["verdict"] == "UNDECIDED", r8
    rows8 = r8["lp_full_rows_formula"]
    ratio = float(np.exp(np.mean(np.diff(np.log(full)))))

    fig, ax = plt.subplots(figsize=(5.6, 4.1))
    ax.semilogy(ks, full, "o-", color="#1f4e8c", lw=2, ms=7,
                label="PROOF, exactly verified (2–4 leaves)")
    ax.semilogy([7, 8], [full[-1], rows8], ":", color="0.55", lw=1.4)
    ax.semilogy([8], [rows8], "X", color="#c62828", ms=10, mec="k", mew=0.6,
                label=f"UNDECIDED: single LP exceeds the {int(r8['budget']['max_time_s'])} s "
                      f"time budget")
    for k, v in zip(ks, full):
        ax.annotate(f"{v:,}", (k, v), textcoords="offset points", xytext=(-6, 8),
                    ha="right", fontsize=7.5)
    ax.annotate(f"≈ {rows8 / 1e6:.2f} M rows", (8, rows8), textcoords="offset points",
                xytext=(-12, -10), ha="right", va="top", fontsize=7.5, color="#7a1010")
    ax.text(0.03, 0.80, f"×{ratio:.2f} per added active dimension\n(geometric mean, "
            f"k = 3…7; d + 1 = 5 with d = 4)", transform=ax.transAxes, ha="left", va="top",
            fontsize=8, bbox=dict(boxstyle="round", fc="white", ec="0.75"))
    ax.set_xticks(ks + [8])
    ax.set_xlim(2.6, 8.5)
    ax.set_xlabel("active dimensions k")
    ax.set_ylabel("LP rows per leaf (log scale)")
    ax.set_title("Per-leaf LP size on sealed synthetic disconnections")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="lower right", framealpha=0.95)
    fig.tight_layout()
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    return {"rows_k3_k7": full, "rows_k8_formula": rows8, "ratio_per_dim": round(ratio, 3),
            "k8_termination": r8["termination"], "k8_engine_s": r8["engine_s"]}


# --------------------------------------------------------------------------- #
# planar relay partition
# --------------------------------------------------------------------------- #

PAIR_STYLE = {"UP": ("#c62828", "upper tooth"), "DOWN": ("#1565c0", "lower tooth"),
              "MID": ("#2e7d32", "middle tooth")}


def _per_obstacle_oracles(sc, n_samples=40):
    body = scenes._body_fk(sc)
    hull = np.array([[float(c) for c in v] for v in sc.hull_vertices])
    ts = np.linspace(0.0, 1.0, n_samples)[:, None]
    obst = {nm: (np.array([[float(x) for x in row] for row in A]),
                 np.array([float(x) for x in b])) for nm, (A, b) in sc.obstacles.items()}

    def hits(s):
        """Every obstacle the link meets at ``s`` (overlaps are kept, not prioritised)."""
        pts = [body.eval_world_point(v, np.asarray(s, float)) for v in hull]
        seg = pts[0] * (1 - ts) + pts[-1] * ts
        return {nm for nm, (A, b) in obst.items()
                if np.any(np.all(seg @ A.T <= b + 1e-12, axis=1))}
    return hits


def partition_e3(scene_path: str, cert_path: str, out: str, n=241) -> dict:
    plt = _plt()
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Rectangle

    sc, _ = scenes.load(scene_path)
    with open(cert_path) as f:
        cert = json.load(f)
    leaves = cert["leaves"]
    pairs = list(sc.pairs)
    counts = {p: sum(1 for lf in leaves if lf["status"] == "collision" and lf["obstacle"] == p)
              for p in pairs}
    n_out = sum(1 for lf in leaves if lf["status"] == "outside")

    qx = np.linspace(deg(sc.box[0][0]), deg(sc.box[0][1]), n)
    qy = np.linspace(deg(sc.box[1][0]), deg(sc.box[1][1]), n)
    xs = np.tan(np.radians(qx) / 2)
    ys = np.tan(np.radians(qy) / 2)
    ext = [qx[0], qx[-1], qy[0], qy[-1]]
    half = deg(sc.delta)
    st = [deg(v) for v in sc.start_s]
    go = [deg(v) for v in sc.goal_s]

    hits = _per_obstacle_oracles(sc)
    masks = {p: np.zeros((n, n), dtype=bool) for p in pairs}
    for b, y in enumerate(ys):
        for a, x in enumerate(xs):
            for nm in hits([x, y]):
                masks[nm][b, a] = True

    # right panel: a ZOOM on the slab (the slab is 11° wide in a 180° box), on its own grid
    zoom = 15.0
    qxz = np.linspace(-zoom, zoom, 361)
    xsz = np.tan(np.radians(qxz) / 2)
    extz = [qxz[0], qxz[-1], qy[0], qy[-1]]
    certified, in_slab, leaf_of = viz.certified_collision_mask(sc, leaves, (0, 1), xsz, ys)
    pair_img = np.full(certified.shape, np.nan)
    for b in range(certified.shape[0]):
        for a in range(certified.shape[1]):
            if certified[b, a]:
                pair_img[b, a] = pairs.index(leaves[leaf_of[b, a]]["obstacle"])
    cmap = ListedColormap([PAIR_STYLE[p][0] for p in pairs])

    fig, (axl, axr) = plt.subplots(1, 2, figsize=(10.2, 4.7), sharey=True)
    for p in pairs:                               # overlaps blend; each region keeps its outline
        axl.imshow(np.where(masks[p], 1.0, np.nan), origin="lower", extent=ext, aspect="auto",
                   cmap=ListedColormap([PAIR_STYLE[p][0]]), vmin=0, vmax=1, alpha=0.38,
                   zorder=1)
        axl.contour(qx, qy, masks[p].astype(float), levels=[0.5],
                    colors=[PAIR_STYLE[p][0]], linewidths=1.3, zorder=3)
    axl.axvspan(-half, half, color="gold", alpha=0.18, zorder=2)
    axl.set_title("sampled configuration space: collision with each obstacle\n"
                  "(overlapping regions blend)", fontsize=9.5)

    axr.imshow(pair_img, origin="lower", extent=extz, aspect="auto", cmap=cmap,
               vmin=-0.5, vmax=len(pairs) - 0.5, alpha=0.85, zorder=2)
    for lf in leaves:
        (x0, x1), (y0, y1) = [(float(eval_frac(lo)), float(eval_frac(hi)))
                              for lo, hi in lf["cell"]]
        X0, X1, Y0, Y1 = deg(x0), deg(x1), deg(y0), deg(y1)
        if lf["status"] == "collision":
            axr.add_patch(Rectangle((X0, Y0), X1 - X0, Y1 - Y0, fill=False, hatch="////",
                                    edgecolor="0.35", lw=0.0, zorder=3, clip_on=True))
            axr.add_patch(Rectangle((X0, Y0), X1 - X0, Y1 - Y0, fill=False,
                                    edgecolor="#1a1a1a", lw=0.7, zorder=5))
        else:
            axr.add_patch(Rectangle((X0, Y0), X1 - X0, Y1 - Y0, facecolor="0.88",
                                    edgecolor="0.55", lw=0.6, ls="--", zorder=1))
    # the certified (in-slab) part is painted OVER the hatching, so only the out-of-slab part
    # of each collision leaf stays hatched
    axr.imshow(pair_img, origin="lower", extent=extz, aspect="auto", cmap=cmap,
               vmin=-0.5, vmax=len(pairs) - 0.5, alpha=1.0, zorder=4)
    for ax in (axl, axr):
        ax.axvline(-half, color="#b8860b", lw=1.8, zorder=6)
        ax.axvline(half, color="#b8860b", lw=1.8, zorder=6)
        ax.set_ylim(ext[2], ext[3])
    axl.plot(st[0], st[1], "*", color="#1f77b4", ms=15, mec="k", zorder=7)
    axl.plot(go[0], go[1], "P", color="#2ca02c", ms=12, mec="k", zorder=7)
    axl.set_xlim(ext[0], ext[1])
    axl.set_xlabel("q1, first joint (deg)")
    axr.set_xlim(-zoom, zoom)
    axr.set_xlabel(f"q1, first joint (deg) — zoom on |q1| ≤ {zoom:.0f}°")
    axr.text(0.01, 0.5, f"← start\n(q1 = {st[0]:.0f}°)", transform=axr.transAxes, ha="left",
             va="center", fontsize=7.5, color="#1f77b4", zorder=8,
             bbox=dict(boxstyle="round", fc="white", ec="0.8", alpha=0.9))
    axr.text(0.99, 0.5, f"goal →\n(q1 = +{go[0]:.0f}°)", transform=axr.transAxes, ha="right",
             va="center", fontsize=7.5, color="#2ca02c", zorder=8,
             bbox=dict(boxstyle="round", fc="white", ec="0.8", alpha=0.9))
    axl.set_ylabel("q2, second joint (deg)")
    axr.set_title(f"certified partition ({len(leaves)} leaves), zoom on the slab",
                  fontsize=9.5)

    handles = [plt.Rectangle((0, 0), 1, 1, fc=PAIR_STYLE[p][0])
               for p in pairs]
    labels = [f"{PAIR_STYLE[p][1]}: {counts[p]} collision leaves" for p in pairs]
    handles += [plt.Rectangle((0, 0), 1, 1, fc="white", ec="0.35", hatch="////"),
                plt.Rectangle((0, 0), 1, 1, fc="0.88", ec="0.55", ls="--"),
                plt.Line2D([0], [0], color="#b8860b", lw=1.8),
                plt.Line2D([0], [0], ls="", marker="*", color="#1f77b4", ms=11, mec="k"),
                plt.Line2D([0], [0], ls="", marker="P", color="#2ca02c", ms=9, mec="k")]
    labels += ["part of a collision leaf outside the slab (nothing asserted)",
               f"outside leaves ({n_out})", f"slab boundary |φ| = {sc.delta}",
               "start", "goal"]
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=7.6, framealpha=0.95,
               bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("Planar relay: the middle link is trapped by three obstacles in turn "
                 "(left: the frame is the joint box)", fontsize=10.5)
    fig.tight_layout(rect=(0, 0.12, 1, 0.95))
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    return {"leaves": len(leaves), "collision_by_pair": counts, "outside": n_out}


def eval_frac(x):
    from fractions import Fraction
    return Fraction(x)


# --------------------------------------------------------------------------- #
# 4-DOF anchor: sweep + C-space
# --------------------------------------------------------------------------- #

def anchor_figures(scene_path: str, out_sweep: str, out_cspace: str, n_c=161) -> dict:
    plt = _plt()
    from matplotlib.patches import Rectangle

    sc, _ = scenes.load(scene_path)
    oracle = scenes.collision_oracle(sc, n_samples=30)
    fk, _names, _bn, _tip = viz._fk_and_names(sc)
    L_UP = float(sc.hull_vertices[-1][0])
    L_FORE = 0.30                                         # forearm drawn for context only
    limits = _limits_text(sc)
    box_style = dict(boxstyle="round", fc="#fff7e0", ec="#e0c060")
    st = np.array([float(v) for v in sc.start_s])
    go = np.array([float(v) for v in sc.goal_s])
    (xlo, xhi), (ylo, yhi), _ = viz._box_bounds(*sc.obstacles[sc.pairs[0]])

    def full_arm(s):
        elbow = fk.body("j2").eval_world_point([L_UP, 0, 0], s)
        hand = fk.body("j3").eval_world_point([L_FORE, 0, 0], s)
        return np.array([[0, 0, 0], elbow, hand])

    fig, ax = plt.subplots(figsize=(5.4, 5.8))
    ax.add_patch(Rectangle((xlo, ylo), xhi - xlo, yhi - ylo, facecolor="0.55",
                           edgecolor="0.3", alpha=0.85, zorder=1))
    ax.text((xlo + xhi) / 2, yhi + 0.02, "panel", ha="center", fontsize=8, weight="bold")
    n, n_coll = 9, 0
    for k in range(n):
        s = st + (go - st) * (k / (n - 1))
        hit = bool(oracle(s))
        n_coll += hit
        col = "#d62728" if hit else "#2ca02c"
        pts = full_arm(s)
        ax.plot(pts[:2, 0], pts[:2, 1], "-", color=col, lw=3.0, alpha=0.85, zorder=3)
        ax.plot(pts[1:, 0], pts[1:, 1], "-", color=col, lw=1.1, alpha=0.75, zorder=3)
        ax.plot(pts[:, 0], pts[:, 1], "o", color=col, ms=3.5, zorder=4)
    for lbl, sv, col in (("start (free)", st, "#1f77b4"), ("goal (free)", go, "#2ca02c")):
        gp = full_arm(sv)
        ax.plot(gp[:2, 0], gp[:2, 1], "-", color=col, lw=4.2, alpha=0.95, zorder=5)
        ax.plot(gp[1:, 0], gp[1:, 1], "-", color=col, lw=1.6, alpha=0.95, zorder=5)
        ax.annotate(lbl, (gp[-1, 0], gp[-1, 1]), color=col, fontsize=9, weight="bold",
                    xytext=(6, 0), textcoords="offset points", va="center", zorder=6)
    ax.plot(0, 0, "ks", ms=8, zorder=7)
    ax.set_aspect("equal")
    ax.grid(True, ls=":", alpha=0.5)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(f"Top view: base-yaw sweep from start to goal,\n{n_coll} of {n} poses in "
                 "collision (red)", fontsize=9.5)
    ax.text(0.5, -0.11, "thick: upper arm (certified body); thin: forearm (drawn only)\n"
            + limits, transform=ax.transAxes, fontsize=7.0, ha="center", va="top",
            bbox=box_style, zorder=10)
    fig.tight_layout()
    fig.savefig(out_sweep, dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    names = fig1.english_joint_names(sc)
    qx = np.linspace(deg(sc.box[0][0]), deg(sc.box[0][1]), n_c)
    qy = np.linspace(deg(sc.box[1][0]), deg(sc.box[1][1]), n_c)
    grid = np.zeros((n_c, n_c))
    s = np.zeros(sc.robot.n)
    for b, y in enumerate(qy):
        for a, x in enumerate(qx):
            s[0], s[1] = math.tan(math.radians(x) / 2), math.tan(math.radians(y) / 2)
            grid[b, a] = 1.0 if oracle(s) else 0.0
    half = deg(sc.delta)
    fig, ax = plt.subplots(figsize=(5.4, 5.2))
    ax.imshow(grid, origin="lower", extent=[qx[0], qx[-1], qy[0], qy[-1]], aspect="auto",
              cmap="Greys", vmin=0, vmax=1.6, alpha=0.85)
    ax.axvspan(-half, half, color="gold", alpha=0.40, zorder=2,
               label=f"slab |φ| ≤ {sc.delta} (|q1| ≤ {half:.1f}°)")
    ax.plot(deg(st[0]), deg(st[1]), "*", color="#1f77b4", ms=17, mec="k", zorder=5,
            label="start")
    ax.plot(deg(go[0]), deg(go[1]), "P", color="#2ca02c", ms=13, mec="k", zorder=5,
            label="goal")
    ax.set_xlabel(f"q1, base {names[0]} (deg)")
    ax.set_ylabel(f"q2, shoulder {names[1]} (deg)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=3, framealpha=0.95,
              fontsize=7.5)
    ax.set_title(f"Configuration space, yaw × pitch (grey = collision);\n{names[2]} and "
                 f"{names[3]} are passive for the upper arm", fontsize=9.5)
    ax.text(0.015, 0.015, limits + "\nframe = the joint box; cut at roll = elbow = 0",
            transform=ax.transAxes, fontsize=6.8, va="bottom", bbox=box_style, zorder=10)
    fig.tight_layout()
    fig.savefig(out_cspace, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return {"sweep_poses": n, "sweep_poses_in_collision": n_coll, "limits": limits}


def main(reproduce_path=None) -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    rep, rep_path = fig1.latest_reproduce(reproduce_path)
    assert rep.get("git_dirty_at_start") is False, "figures must come from a clean-tree run"
    sources = {"reproduce": rep_path, "commit": rep["commit"], "stamp": rep["stamp"]}

    p = os.path.join(OUT_DIR, "cost_vs_active_dims.png")
    sources["cost_vs_active_dims.png"] = cost_vs_active_dims(rep, p)
    print("written", p)

    relay = rep["rows"]["relay"]
    p = os.path.join(OUT_DIR, "partition_E3.png")
    sources["partition_E3.png"] = {"scene": relay["scene"], "certificate": relay["certificate"],
                                   **partition_e3(relay["scene"], relay["certificate"], p)}
    print("written", p)

    anchor = rep["rows"]["anchor"]
    ps = os.path.join(OUT_DIR, "scene_S3_shoulder_elbow_sweep.png")
    pc = os.path.join(OUT_DIR, "scene_S3_shoulder_elbow_cspace.png")
    sources["scene_S3_shoulder_elbow_{sweep,cspace}.png"] = {
        "scene": anchor["scene"], **anchor_figures(anchor["scene"], ps, pc)}
    print("written", ps, pc)

    sources["fig1.png"] = fig1.main(rep_path)
    with open(os.path.join(OUT_DIR, "SOURCES.json"), "w") as f:
        json.dump(sources, f, indent=2, ensure_ascii=False)
    print("written", os.path.join(OUT_DIR, "SOURCES.json"))
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--reproduce", default=None)
    raise SystemExit(main(ap.parse_args().reproduce))
