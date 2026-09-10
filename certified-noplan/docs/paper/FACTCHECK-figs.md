# FACTCHECK-figs — the paper's figures (S14 publication versions) against `paper.tex`

**Session S14 (Claude Code), 10 September 2026.** For each figure of
`docs/paper/latex/paper.tex` (draft v0.3), every number VISIBLE on the S14 figure is compared with
the caption and the body text, and with its source. `paper.tex` is **not** modified (supervision
document): divergences are listed for the supervision to integrate.

Sources:
- **REP**: `benchmarks/results/20260910T152348Z/reproduce.json` — `make reproduce`, commit `8d056e5`,
  `git_dirty_at_start = false`, one process per row, Apple M4 / 24 GB, load average 1.1–2.9.
- **SRC**: `benchmarks/figures/paper/SOURCES.json` (what each figure read).
- **S12**: the benchmarks the draft quotes today (`20260909T092652Z` / `…092748Z` / `…092845Z`,
  commit `dbaaab8`, `git_dirty = true`).

Line numbers `l.NNN` refer to `docs/paper/latex/paper.tex`.

---

## 1. Figure 1 — `fig1.png` (caption l.80, §7.4 l.280-286)

| visible on the figure | figure value (source) | `paper.tex` | verdict |
|---|---|---|---|
| verify time | **2.40 s** (REP `rows.flagship.verify_s = 2.399`) | caption and §7.4: **2.42 s** (S12); abstract: 2.4 s; §5: 2.4 s | **DIVERGENCE (rounding of a different run)**. Either keep 2.42 s and cite S12, or move to 2.40 s and cite REP. A single figure/text source must be chosen. |
| leaves | 2 (2 collision, 0 outside) (REP) | 2 leaves, both collision | OK |
| active dimensions | 3 of 7, q1–q3; q4–q7 passive (REP `active_dims`) | (q1, q2, q3), (q4, …, q7) passive | OK |
| LP rows | 1,070 vs 473,870, 443× (REP `lp_reduced.rows`, `lp_full.rows`, `reduction_x = 442.9`) | 1 070 vs 473 870 (443×) | OK |
| margins | 91.5 mm / 83.3 mm (REP `groundtruth`, 7 × 5 × 7 grid) | 91.5 / 83.3 mm | OK — reproduced with a finer grid than S12 (5 × 3 × 5), same values |
| kinematic fidelity | 1.99e-6 m at the flange; hull 1.67e-6 m (REP `kinematic_fidelity`: 1.985e-6, 1.674e-6) | caption 1.99·10⁻⁶ m at the flange (1 500 configurations); §7.4 hull 1.67·10⁻⁶ m (200 configurations) | OK (units m, A49) |
| joint box | q1 yaw ±70°, q2 pitch ±70°, q3 roll ±70°, q4–q7 ±143° (scene file) | §7.4: "±70° edge of the joint box" | OK |
| slab | \|φ\| ≤ 1/5 (\|q2\| ≤ 22.6°) | caption \|φ\| ≤ 1/5 | OK |
| shelf underside | z = 0.68 m (scene file) | 0.68 m | OK |
| start / goal | q2 = ∓61.9° (panel b markers) | caption ∓61.9° | OK |

Caption items **not drawn** on the figure, checked for provenance:
- "link top at 0.597 m": REP `groundtruth.startgoal_max_body_top_m = 0.5967` — **now in a dated JSON**.
- "upright transit (link top 0.808 m)" and "0.544 m at the ±70° edge" (§7.4): **in no dated JSON** —
  measured in P2 (FACTCHECK-v0.2 §3.1, outside the repository). Under D-P2-B this is a "measured and
  dated journal entry"; to archive it in JSON, add the upright height to the ground-truth record.

Caption text to update:
- **Remove the draft note** "[Draft: the composite shown was generated from the pre-export-contract
  benchmark (verify 3.79 s) and carries French labels…]": the S14 figure is English, has no internal
  codes and reads REP.
- The caption describes three panels (left / centre / right); the figure labels them (a) / (b) / (c)
  — harmonize wording.

## 2. Cost figure — `cost_vs_active_dims.png` (caption l.229, §6.2 l.222)

| visible | figure value (source) | `paper.tex` | verdict |
|---|---|---|---|
| rows per leaf, k = 3…7 | 766, 3,782, 18,814, 93,878, 469,006 (REP `rows.wall_k*.lp_full.rows`) | caption "766 to 469 006"; §6.2 lists the five values | OK |
| verdicts k = 3…7 | PROOF, exactly verified, 2–4 leaves (REP; each certificate re-checked by the stdlib verifier module and by `cnp verify <cert> <scene>`) | "PROOF with exact verification at every point shown"; §6.2 "2–4 leaves" | OK |
| growth factor | **×4.97 per added active dimension** (geometric mean k = 3…7, SRC `ratio_per_dim = 4.974`) | §6.2 "**×4.99** per added active dimension"; caption "slope (d+1) = 5" | **DIVERGENCE (definition)**: 4.99 is the last step (469 006 / 93 878 = 4.996); the figure prints the mean over the four steps. Both are true; the text should say which it quotes, or both say "tends to d + 1 = 5". |
| k = 8 point | **plotted**, UNDECIDED, "single LP exceeds the 300 s time budget", ≈ 2.34 M rows (REP `wall_k8`: `termination = budget_time`, `lp_full_rows_formula = 2 344 262`) | caption: "The k=8 point (…) **is not plotted**"; §6.2 "about 2.3 million rows" | **DIVERGENCE (caption)**: the S14 figure plots it, as the S14 instruction asked. 2.34 M comes from the row formula faces × (DPAD+1)^k + K × (d_λ+1)^k, **checked equal to the built LP on all 12 certified rows** (REP `lp_row_formula_matches_built_lp`). |
| dashed curve (barrier declared at degree 1, d = 3) | **removed** | caption "Dashed: the same family with the barrier declared at its true degree 1…" | **DIVERGENCE (caption)**: delete that sentence; the curve remains in the repository figure `benchmarks/figures/S9f_wall/cost_vs_active_dims.png`. |

Body text touched by REP:
- §6.2 "it returns after **455 s**" (S9f, 2026-06-13): REP measures **476.7 s** for the same k = 8
  run (`rows.wall_k8.engine_s`). The claim "outlasts the 300 s deadline" holds in both runs; the
  return time is machine noise. Quote one run, and say which.
- Remove the draft note "[Draft: French labels; to be regenerated in English.]".

## 3. Partition figure — `partition_E3.png` (caption l.164, §7.1 l.263)

| visible | figure value (source) | `paper.tex` | verdict |
|---|---|---|---|
| leaves | 46 (certificate `scenes/S1_relais.cert.json`, SRC) | caption "46 leaves"; §7.1 "46 leaves: 38 collision across three pairs, 8 outside" | OK |
| collision leaves per obstacle | upper tooth 12, lower tooth 12, middle tooth 14 (certificate) | caption "12 / 12 / 14" | OK |
| outside leaves | 8 (certificate) | §7.1 "8 outside" | OK |
| slab | boundary \|φ\| = 1/20 | not stated | OK |
| start / goal | q1 = −84° / +84° | not stated | OK |

Caption text to update:
- **The right panel is now a ZOOM on the slab (|q1| ≤ 15°)**: the slab is 11.4° wide in a 180°
  joint box, and at full width the partition was unreadable. The caption should say "Right: zoom on
  the slab"; start and goal are outside the zoom and marked by arrows.
- The left panel now blends **overlapping** obstacle regions (each with its outline) instead of
  painting one obstacle over another: "the three obstacles in red, blue and green" stays true.
- The caption's "grey leaves are outside the slab" matches (dashed grey outlines).
- **The S14 figure hatches** the out-of-slab part of each collision leaf: the draft note
  "[Draft: French labels; the release version hatches…]" is resolved — remove it.
- Axes are joint angles in degrees (not s); the caption does not say either.

## 4. Anchor figures — `scene_S3_shoulder_elbow_{sweep,cspace}.png` (caption l.272, §7.2 l.266)

| visible | figure value (source) | `paper.tex` | verdict |
|---|---|---|---|
| sweep | 3 of 9 interpolated poses in collision (computed by the figure with the segment oracle) | "poses in the band plant the upper arm in the panel" | OK |
| joint limits | yaw ±70°, pitch ±44°, roll ±90°, elbow 0–109° (scene file) | not stated | OK |
| slab | \|φ\| ≤ 1/10 (\|q1\| ≤ 11.4°) | not stated | OK |
| passive joints | roll and elbow | caption "roll and elbow passive"; §7.2 | OK |

No divergence. The caption's "the collision wall spans all admissible pitch and contains the slab" is
what the C-space panel shows.

## 5. Table §7.6 (l.306-313) against the clean-tree run REP

Not a figure; checked because every row now has a clean-tree measurement. "certify" = scene load +
symbolic FK build + engine + certificate export, end to end; GT = free samples in the slab / samples.

| row | `paper.tex` engine / certify / verify / GT | REP engine / certify / verify / GT | note |
|---|---|---|---|
| planar relay | 0.48 s / — / 0.09 s / — | 0.45 s / **0.87 s** / 0.09 s / — | "—" filled |
| comb | 1.36 s / — / 0.17 s / 0/300k | 1.35 s / **1.91 s** / 0.17 s / 0/300 000 | "—" filled |
| anchor | 0.04 s / — / 0.04 s / 0/150k | **0.10 s** / **0.38 s** / 0.04 s / 0/150 000 | engine 0.043 → 0.096 s (§7.2 quotes 0.043 s); certify filled; the anchor exercises the full-dimension FALLBACK (4 leaves re-solved) |
| iiwa-like bin | 0.15 s / 0.77 s† / 0.16 s / 0/40k | 0.20 s / **1.14 s** / 0.15 s / 0/40 000 | **the † value was not end to end**: `scripts/calibrate_g2.py:71-73` times `cert.certify` AFTER the scene build, so 0.77 s excludes load and FK build. REP, post-export-contract, end to end: 0.54 s load+FK + 0.20 s engine + 0.40 s export. The † can go. |
| iiwa7 shelf | 1.3 s / 46.7 s / 2.42 s | 1.39 s / **46.1 s** / **2.40 s** | FK build 38.2 s; export 6.4 s, of which verify-loop 2.43 s + per-leaf audit 2.48 s = **4.9 s** (§5, §6.3: confirmed, now in JSON) |
| iiwa7 crate | 1.3 s / 46.1 s / 2.43 s | **1.95 s / 59.3 s / 3.24 s** | **measured under higher load** (load average 2.86 when the row started, vs 1.67 for the flagship): FK build 48.7 s vs 38.2 s. Machine noise, not a regression. Do not quote this row as a speed without saying so; a quiet re-run is the supervision's call. |
| iiwa7 guard | 1.6 s / 47.1 s / 2.50 s | 1.73 s / **50.0 s** / 2.61 s | load average 2.10 |
| sealed wall k = 3…7 | 0.1–65 s / 0.15–80 s / 0.01–6.8 s | 0.12–70.7 s / 0.37–96.2 s / 0.011–7.28 s | certify now includes scene load + FK build |
| ground truth iiwa7 | 0 / 40k + 448 corners | 0 / 40 000 + 0 / 448 corners; 16/16 distal extremes collide; 4 000 / 4 000 free per side | **now in JSON** (D-P2-B) |

All 12 certified rows: PROOF, `n_reresolve_failed = 0`, `n_embed_rejected = 0`, re-proved by the
stdlib verifier module (no third-party module loaded) AND by `cnp verify <cert> <scene>`. The three
iiwa7 certificates regenerated by REP are **byte-identical** to the committed S12 certificates.

## 6. Text claims touched by the new archived JSONs (not figures)

1. **§6.1 (l.217) "Base yaw and arm roll are negative in every direction (−73 to −299 mm)"** —
   `benchmarks/results/20260910T152348Z/lever_iiwa7.json`: for base yaw (q1) and arm roll (q3) the
   **half-space margin in direction −z is exactly 0.0 mm**, not negative; the other five directions
   are negative (q1: −73.5 to −299.0 mm; q3: −199.7 to −268.2 mm), and the "wall to cross" (plate)
   motif is negative in all six directions for both. A 0 mm margin is still not a usable separator,
   so the conclusion stands, but "negative in every direction" is literally false: say
   "non-positive in every direction (at best 0 mm)". Shoulder pitch +z = +174.8 mm is confirmed.
2. **§7 (l.260)** "the three iiwa7 benchmarks quoted below were run from a tree whose certificates
   were not yet committed": REP is a clean-tree run of every row; if the table moves to REP, the
   sentence can say so.
3. **§7.8 (l.329)** "the certificates of the three iiwa7 scenes are released": certificates of
   **every certified row** are now in the repository (`scenes/S1_relais`, `S2_peigne`,
   `S3_shoulder_elbow`, `S4_iiwa_bin`, `S6_iiwa_real_shelf`, the two use cases, `scenes/wall/k3…k7`),
   each with its scene file (the wall family was frozen as `scenes/wall/k*.yaml` in S14) and double
   re-verification recorded in REP. `S5_iiwa_shelf.cert.json` stays outside "released"
   (iiwa-LIKE methodological artefact). **Also a precondition**: `benchmarks/results/` was
   git-ignored until S14 — the dated JSONs the paper cites were not in the repository before
   commit `95fa854`.
4. **§7.8** "Figure 1 reads its numbers from the dated benchmark file": true for all four figure
   files now (SRC), not only Figure 1.

## 7. Summary

- **Numbers on the figures that match `paper.tex`**: all except the three below.
- **Divergences to integrate (supervision)**: (1) Fig. 1 verify 2.40 s (REP) vs 2.42 s (S12) — pick
  one source; (2) cost figure: ×4.97 mean vs ×4.99 last step; k = 8 now plotted; dashed curve
  removed; (3) partition figure: right panel is a zoom.
- **Captions**: remove the three "[Draft: …]" notes, which S14 resolved.
- **Table §7.6**: "—" can be filled from REP; the bin's † value was not end to end; the crate row of
  REP ran under higher load.
- **Text**: §6.1 "negative in every direction" → "non-positive (at best 0 mm)"; §6.2 455 s vs
  476.7 s; §7.8 released certificates now 8/8 table lines.
