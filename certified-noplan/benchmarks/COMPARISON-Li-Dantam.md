# Benchmark B1 — anchoring against Li & Dantam at 4-DOF (gate G3')

*Generated for S7. Raw per-run numbers: `benchmarks/results/<UTC-datetime>/results.json`
(seeded, commit-stamped — CLAUDE.md rule 7). This document is the honest comparison the
S6 review asked for: it states what it **can** compare and what it **cannot**.*

## The reference

The 4-DOF infeasibility benchmark of this line of work is:

> Sihui Li & Neil T. Dantam, **"Learning Proofs of Motion Planning Infeasibility"**,
> RSS 2021 (roboticsproceedings.org/rss17/p064); journal version: *"A sampling and
> learning framework to prove motion planning infeasibility"*, **IJRR 2023**,
> doi:10.1177/02783649231154674.

Their **4-DOF** scenes (RSS 2021 §V, Fig. 7b / Fig. 1a; Tables II–III, means over 24
trials, CPU — the paper predates their later GPU work):

| Their scene | Robot | Why infeasible | Reported time-to-proof |
|---|---|---|---|
| Shoulder-Elbow | 3-DOF spherical shoulder + 1-DOF revolute elbow | arm cannot reach inside a box | **≈ 231 s** (230.82 ± 90.95 s) |
| SCARA | 3 co-planar revolute + 1 prismatic | end-effector cannot reach inside a box | **≈ 433 s** (433.00 ± 220.43 s) |

Their certificate is a **learned separating manifold**: an RBF-kernel SVM trained on
PRM samples, triangulated (tangential Delaunay complex), each facet checked to lie in
C_obs by a numerical penetration-depth / collision query (FCL). It is a *geometric,
numerically-checked* proof of path non-existence, for **arbitrary** mesh geometry.

> NOTE. The two arXiv preprints named in the original S7 plan (2406.04795, 2501.11434)
> are **not** the 4-DOF source. 2406.04795 (Li & Dantam, "Scaling MP Infeasibility
> Proofs") is a **5–6-DOF GPU** follow-up with no 4-DOF result; 2501.11434 is a
> different group (Thomas et al., Genoa) using a bitmap/segmentation method. The 4-DOF
> benchmark lives in the RSS 2021 / IJRR 2023 papers above. (Journaled in S7.)

## Our reproduction

No public code, scene file, URDF, or numeric start/goal exists for their scenes, so
this is a **documented approximate reproduction** (the S6 review "Vigilances S7"
anticipated exactly this). We reproduce their **4-DOF Shoulder-Elbow robot** — a
spherical shoulder (yaw z / pitch y / roll x, concurrent at the base) + a revolute
elbow (y) — as `scenes/S3_shoulder_elbow.yaml`, with an infeasible reaching task of the
same flavour (target unreachable, blocked by a panel). We adapt the *task* so our
algebraic machinery applies: a thin front panel traps the **upper-arm link** over a band
of base yaw, for every pitch and all configurations of the passive roll + elbow — a
*proximal* trap (a distal-joint barrier is defeated by the arm's redundancy; the S5/S6
lesson). This is a genuine disconnection of a **4-DOF** configuration space.

The exact paper↔YAML geometry correspondence (what is faithful vs chosen by us, since
Li-Dantam publish no numbers) is archived in `benchmarks/GEOMETRY-S3-vs-LiDantam.md`
(A21). The V4 figures pre-empt the viewer's natural objections (A23): the side view
`figures/scene_S3_shoulder_elbow_side.png` shows the panel is taller than the arm's
reach (so "over the top" is impossible — a wall-height block, not a joint-limit one),
and the C-space figure shows the collision wall spans every pitch (no yaw/pitch detour).

Our certificate is a **Bernstein-LP disconnection proof**: a low-degree polynomial
barrier φ (here φ = s0, the base-yaw coordinate) whose slab `{|φ|≤δ}` is certified
entirely in collision by a branch-and-bound partition, each leaf carrying an
exact-rational LP witness. At **planar** robots it is re-checked in **exact rational
arithmetic** by an independent verifier (`cnp verify`); at **spatial** robots (this
scene) exact verification is an S9 task, so the verdict is **ENGINE-PROOF** plus a dense
300k-sample soundness cross-check (0 free configs in the slab).

## The numbers (this machine — Apple M-series, single core; see results.json)

| Scene | DOF | Verdict | Leaves | Engine time | Exact-verify time |
|---|---|---|---|---|---|
| S1_relais (planar relay) | 2 | PROOF | 46 | ~0.8 s | ~0.09 s |
| S2_peigne (planar comb) | 3 | PROOF | 54 | ~5 s | ~0.18 s |
| **S3_shoulder_elbow** | **4** | **ENGINE-PROOF** | **8** | **~0.5 s** | S9 (dense: 0 free / 300k) |
| Li-Dantam Shoulder-Elbow | 4 | manifold + collision-check | ~8188 facets | **≈ 231 s** (their CPU) | — (numerical) |

## What this comparison CAN and CANNOT say

**It is NOT an apples-to-apples speed race**, and we do not claim "≈400× faster":

- **Different problem.** Their method learns an *arbitrary* separating manifold from
  samples on *arbitrary* mesh geometry — no analytic barrier assumed. Ours exploits a
  *low-degree algebraic barrier* (here hand-baked into the scene; our S5 φ-pipeline can
  also fit it automatically). When such a barrier exists, certification is cheap; when
  it does not, our method needs a higher-degree or piecewise φ (SPEC §9.1, S10).
- **Different hardware and metric.** Their ~231 s is a multi-trial CPU mean on their
  machine (and includes PRM sampling + SVM training + triangulation + penetration-depth
  checks); our ~0.5 s is a single-core engine solve on a different machine. The wall
  clocks are not directly comparable.
- **Different certificate strength.** Theirs is verified by *numerical* collision /
  penetration-depth queries. Ours is verified — at planar robots, today — in **exact
  rational arithmetic** by an independent < 500-line checker (`cnp verify`); at spatial
  robots the exact checker arrives in S9. Exact machine-checkability is the credibility
  axis we add that their pipeline does not have.

**What it CAN say**, honestly: we produce a **4-DOF infeasibility certificate in the
same regime Li & Dantam pioneered**, of a fundamentally different (algebraic, slab-aware,
LP) kind, **orders of magnitude cheaper when a low-degree barrier exists**, and
**exactly machine-checkable** (planar today, spatial in S9). 4-DOF is the anchor that
places us on the same map as the prior art.

## Scaling lineage and our repositioning (A26, verified S8)

A correction to an earlier framing of this project (journaled in the S7 supervision
review, A26). Li & Dantam did **not** stop at 4-DOF: their line of work scaled up.

> Sihui Li & Neil T. Dantam, **"Scaling Motion Planning Infeasibility Proofs"**,
> arXiv:2406.04795 (2024). *Verified S8 (CLAUDE.md rule 9 / A28):* a manifold
> triangulation algorithm on **GPUs** (Coxeter triangulation, batch processing), reported
> as **~two orders of magnitude faster than their previous method**, evaluated on
> **5-DoF and 6-DoF** manipulator scenes.

So the claim "rigorous infeasibility proofs plateau at 4-DOF" is **periodic/false** and is
retired here. Our differentiation is therefore **not** "alone beyond 4-DOF" but the
**NATURE of the certificate**:

- **algebraic and exactly re-checkable** — an independent < 500-line verifier recomputes
  the proof in exact rational arithmetic (planar today, spatial in S9); their facets are
  validated by *floating-point* collision / penetration-depth queries;
- **pure CPU / LP** — no GPU, no SDP, no Mosek (CLAUDE.md rule 3); their scaling result
  needs a GPU;
- **reusable walls** — once a slab is certified, membership queries are microseconds.

Reframed gates (SPEC §8, A26): **G2' (5-6 DOF)** = reaching Li-Dantam's GPU frontier on a
**laptop CPU with an exactly-verifiable certificate**; **G4' (7-DOF)** = beyond them **in
DOF *and* in certificate strength** (to confirm against their exact published numbers).
"The auditor can recount" vs "trust the pipeline."

## Cost-model data: the passive-dimension blow-up, and its S8 fix (A18)

The harness runs a parametric proximal-trap arm (2 active joints + k passive distal
joints), n = 2..5, with both axis heuristics. **Before S8** (the motivation for A18):

| n joints | passive dims | `axis=margin` leaves | `axis=oracle` leaves (pre-S8) |
|---|---|---|---|
| 2 | 0 | 8 | 8 |
| 3 | 1 | 8 | 12 |
| 4 | 2 | 8 | 20 |
| 5 | 3 | 8 | 36 |

`margin` (relay-lookahead) stayed **flat** — it never split a passive dimension — while
`oracle` (widest-axis) grew **exponentially** in the passive-dim count. This was the
quantified evidence behind the S6 decision (A10: `margin` is the default for new scenes)
and the S8 priority-1 task.

**S8 delivered the fix** (A18, "passive dimensions by intervals"): the engine detects
passive joints (`engine.passive_dims`), never branches on them, and reduces each cell LP
to the active dimensions — `(d+1)^k` Bernstein rows instead of `(d+1)^n`. After S8 the
sweep is **flat for BOTH heuristics** (oracle 8/8/8/8), and the 3-DOF comb now certifies
with `axis=oracle` in 46 leaves + exact-verify (was UNDECIDED/736). It is the single most
important lever for G2' (5-6 DOF), implemented two sessions early.

**Perf, honestly (S8 finding, to be ratified by the review).** Two distinct effects,
not to be conflated. (1) The LP **back-end
swap** to direct highspy (S8 default) is a **~2× constant factor** over cvxpy on these LPs
— *not* 10×. (2) The **`(d+1)^k` row reduction** is the order-of-magnitude win: on the
trap arm, cvxpy-at-full-dim vs highspy-reduced measures **7× at 1 passive dim, 28× at 2,
133× at 3, 733× at 4** (the reduced margin `t` matches the full margin exactly — no
decision changes). On `S3_shoulder_elbow` (n=4, but only **1** dim is *detected* passive —
the distal roll is geometrically passive yet formally present in the FK tensor, so the
conservative detector keeps it), the end-to-end gain is **~6×**. A sharper detector that
recognises geometrically-passive-but-formally-present axes would push S3 higher — a
follow-up. The independent exact verifier re-checks every certificate at **full**
dimension regardless of the reduction, so none of this can affect soundness.
