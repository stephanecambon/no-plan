"""S9f — re-measured scaling-wall figure: cost/leaf (Bernstein LP rows) vs the number of ACTIVE
dimensions k on PROVABLY WATERTIGHT disconnections (scripts/wall_resonde_S9f.py), affine witness.

Corrects the S9e figure (which marked a 'mur du schéma affine à k=5'): that wall was an artifact
of (1) a silent max_depth=16 ceiling and (2) a leaky obstacle (bbox of a random sample of the
reach) leaving free configs in the slab. On sealed scenes the affine witness certifies cleanly
(PROOF + exact verify) at every measured k; the cost is the SINGLE-LP size (d+1)^k with a tiny
leaf count (2-4), NOT a leaf explosion. Two cost curves: the engine's effective DPAD=4 (5^k,
φ padded to degree 2) and the tight φ-degree DPAD=3 (4^k, φ at its true linear degree) — both
certify; the (5/4)^k gap is the φ-padding, not per-axis anisotropy (which gives 0, degrees are
uniform). Writes benchmarks/figures/S9f_wall/cost_vs_active_dims.png."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def make(points, out="benchmarks/figures/S9f_wall/cost_vs_active_dims.png"):
    """points: list of (k, rows_DPAD4, rows_DPAD3, verdict)."""
    os.makedirs(os.path.dirname(out), exist_ok=True)
    ks = [p[0] for p in points]
    rows4 = [p[1] for p in points]
    rows3 = [p[2] for p in points]
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    ax.semilogy(ks, rows4, "o-", color="#1f77b4", lw=2, ms=9,
                label=r"coût/feuille livré — DPAD=4 ($5^k$, φ deg 2)")
    ax.semilogy(ks, rows3, "s--", color="#2ca02c", lw=1.8, ms=7,
                label=r"coût/feuille φ tendu — DPAD=3 ($4^k$, φ deg 1)")
    base5 = rows4[0] / (5 ** ks[0])
    ax.semilogy(ks, [base5 * 5 ** k for k in ks], ":", color="#aaa", lw=1.3,
                label=r"tendance $(d{+}1)^k$, $d{+}1=5$")
    for p in points:
        ax.annotate(p[3], (p[0], p[1]), textcoords="offset points", xytext=(7, 5),
                    color="#2ca02c" if p[3] == "PROOF" else "#d62728",
                    fontsize=8.5, fontweight="bold")
    ax.set_xlabel("k = dimensions ACTIVES détectées (pair_views)")
    ax.set_ylabel("coût par feuille — lignes Bernstein du LP (log)")
    ax.set_title("Mur re-mesuré (S9f) : déconnexions WATERTIGHT, témoin affine\n"
                 "PROOF + verify exact à chaque k ; pas de mur affine — coût = LP unique $(d{+}1)^k$, "
                 "feuilles 2-4")
    ax.set_xticks(ks)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    print("wrote", out)


if __name__ == "__main__":
    # measured points (scripts/wall_resonde_S9f.py): (k, rows_DPAD4, rows_DPAD3_tight_phi, verdict)
    make([(3, 766, 400, "PROOF"), (4, 3782, 1568, "PROOF"), (5, 18814, 6208, "PROOF"),
          (6, 93878, 24704, "PROOF"), (7, 469006, 98560, "PROOF")])
