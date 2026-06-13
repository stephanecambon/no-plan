"""S9e — the scaling-wall figure for the paper: cost/leaf (Bernstein LP rows) vs the number
of ACTIVE dimensions k, log scale, with the (d+1)≈5-per-active-dim trend (D40 §3d).

Data are the measured points from scripts/wall_bench.py (affine witness). The point where the
affine scheme stops certifying (UNDECIDED under budget) is marked as the wall. Run after the
bench; writes benchmarks/figures/S9e_wall/cost_vs_active_dims.png."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# (k, cost_leaf_rows, verdict) — filled from scripts/wall_bench.py
def make(points, out="benchmarks/figures/S9e_wall/cost_vs_active_dims.png"):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    ks = [p[0] for p in points]
    rows = [p[1] for p in points]
    proved = [p[0] for p in points if p[2] == "PROOF"]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.semilogy(ks, rows, "o-", color="#1f77b4", lw=2, ms=9, label="coût/feuille mesuré (lignes Bernstein)")
    # (d+1)^k trend anchored at the first point, d+1 = 5
    base = rows[0] / (5 ** ks[0])
    trend = [base * 5 ** k for k in ks]
    ax.semilogy(ks, trend, "--", color="#888", lw=1.5, label=r"tendance $(d{+}1)^k$, $d{+}1=5$")
    for p in points:
        col = "#2ca02c" if p[2] == "PROOF" else "#d62728"
        ax.annotate(p[2], (p[0], p[1]), textcoords="offset points", xytext=(8, -4),
                    color=col, fontsize=9, fontweight="bold")
    wall = [p[0] for p in points if p[2] != "PROOF"]
    if wall:
        ax.axvline(min(wall), color="#d62728", ls=":", lw=1.5)
        ax.text(min(wall) + 0.03, rows[0], "mur du schéma affine", color="#d62728",
                rotation=90, va="bottom", fontsize=9)
    ax.set_xlabel("k = dimensions ACTIVES détectées (pair_views)")
    ax.set_ylabel("coût par feuille — lignes Bernstein du LP (log)")
    ax.set_title("Mur de scaling : coût d'une déconnexion certifiée vs dims actives")
    ax.set_xticks(ks)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    print("wrote", out)


if __name__ == "__main__":
    # affine points (scripts/wall_bench.py); UNDECIDED at k=5 = structural wall (under budget)
    make([(3, 766, "PROOF"), (4, 3782, "PROOF"), (5, 18814, "UNDECIDED")])
