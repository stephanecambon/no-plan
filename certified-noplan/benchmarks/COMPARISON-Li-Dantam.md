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
**exactly machine-checkable** (planar today, spatial in S9). The title result of the
project is at **5+ DOF** (S9/S10), where no rigorous prior method operates on serial
manipulators; 4-DOF is the anchor that places us on the same map as the prior art.

## Cost-model data: the passive-dimension blow-up (A18 / S8)

The harness also runs a parametric proximal-trap arm (2 active joints + k passive distal
joints), n = 2..5, certified with both axis heuristics:

| n joints | passive dims | `axis=margin` leaves | `axis=oracle` leaves |
|---|---|---|---|
| 2 | 0 | 8 | 8 |
| 3 | 1 | 8 | 12 |
| 4 | 2 | 8 | 20 |
| 5 | 3 | 8 | 36 |

`margin` (relay-lookahead) stays **flat** — it never splits a passive dimension —
while `oracle` (widest-axis) grows **exponentially** in the passive-dim count. This is
the quantified evidence behind the S6 decision (A10 tranché: `margin` is the default for
new scenes) and the S8 priority-1 task (A18: passive dimensions by intervals, so that
`oracle` no longer wastes depth). It is the single most important lever for G2' (5–6
DOF), measured here two sessions early at zero extra cost.
