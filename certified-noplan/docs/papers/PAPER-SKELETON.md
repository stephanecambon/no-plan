# PAPER-SKELETON.md — RSS submission draft v0.1 (supervision, 2026-07-02)

Target: RSS 2027 (9 pages + references + 1-page reviewer note). Status: skeleton
with key claims written out verbatim (the sentences that must survive review),
placeholders marked `[PENDING: ...]` for material awaiting S10-quater, and
`[VERIFY: ...]` for citations awaiting the bibliography check (A28).

Working title candidates (pick later):
1. "Exactly Verifiable Infeasibility Certificates for Robot Motion Planning"
2. "No Plan, Provably: Machine-Checkable Infeasibility Certificates for
   Articulated Robots"
3. "Infeasibility Proofs You Can Recount by Hand: Exact Certificates for
   Motion Planning of Articulated Arms"

---

## Abstract (draft, ~180 words)

We present the first infeasibility certificates for motion planning of
articulated robot arms that are *exactly re-verifiable a posteriori*: a
certificate is a finite algebraic object that an independent 499-line
verifier, using only exact rational arithmetic from the Python standard
library, can re-check without trusting the planner, the solver, or any
floating-point collision checker. Our method combines a rational
parametrization of forward kinematics, a scalar barrier function defining a
slab that separates start from goal, and per-cell witness certificates
obtained by linear programming over Bernstein coefficients — no SDP, no
numerical collision checking in the trust chain. We certify disconnection for
arms up to 7 DOF on a laptop CPU — in seconds for 5–6-DOF scenes, and in under
a minute for our flagship: a KUKA iiwa7 with kinematics faithful to the
published URDF (~2e-6 rad) and a faithful convex link silhouette, proven
unable to reach a target behind an overhead shelf with a ~90 mm separation
margin (≈47 s end-to-end, 39 s of which is symbolic kinematics setup; exact
re-verification in 2.4 s). This matches the
DOF frontier of recent GPU-based infeasibility provers while producing a
certificate of a different nature. The cost is driven by the number of
*active* dimensions of the trapped body, not total DOF: redundant joints are
covered by the proof at negligible decision cost (measured LP reduction ×443
on the flagship).

---

## 1. Introduction

Content plan:
- The asymmetry: planners return paths when they exist; when they don't,
  sampling-based methods run forever and optimization-based methods return
  "failed", neither of which is evidence of anything. Downstream consumers
  (TAMP, safety cases, workcell design) need *proof* of infeasibility.
- Existing infeasibility proofs rest on floating-point pipelines (learned
  manifolds validated by numerical collision checkers) — the consumer must
  trust the whole stack. KEY SENTENCE (differentiation, A26): "Our
  contribution is not a higher DOF count; it is a change in the *nature* of
  the certificate: an auditor can recount the proof, in exact arithmetic,
  with 500 lines of standard-library code."
- Contributions list:
  (C1) A certificate schema for C-space disconnection of articulated arms:
       slab-aware Bernstein-LP witnesses over a rational FK parametrization,
       with three-valued verdicts (PROOF / ENGINE-PROOF / UNDECIDED).
  (C2) An independent exact verifier (<500 lines, stdlib `Fraction`, zero
       imports from the generator) that re-derives the FK and re-forms the
       Putinar-style product itself, making the unsound sign impossible to
       smuggle in; hardened against 26+ adversarial certificate mutations.
  (C3) A cost model, measured: per-leaf LP cost scales as (d+1)^k in the
       number k of *active* dimensions of the certified body; passive
       (redundant) dimensions are covered by the theorem at ~zero cost
       (measured reduction up to ×612 on a 7-DOF scene).
  (C4) Scenes and benchmarks up to 7 active dimensions and 7-DOF realistic
       arms [PENDING S10-quater: iiwa7 flagship], including two documented
       episodes where the certifier caught disconnection claims that dense
       sampling had validated — including one authored by us.
- Honest scope up front (one paragraph): static polytopal obstacles, convex
  certified bodies, revolute chains, q*=0 (locked joints with rational
  cos/sin), box joint limits, no wrap-around: the theorem quantifies over
  the full box |q_i − q*_i| < π.

## 2. Related Work

(Sources: docs/BIBLIO-ANTERIORITE.md + BIBLIO-VERIFIED.md — A28 pass done
2026-09-09, all references checked at the source; corrections and
additions listed there.)

- **Li & Dantam lineage** (Colorado School of Mines) — IROS 2020 (towards
  general proofs); RSS 2021 "Learning Proofs of Motion Planning
  Infeasibility" (DOI 10.15607/RSS.2021.XVII.064; 3–4-DOF, SCARA "< 4 min
  on average"); WAFR 2022 (exponential convergence); IJRR 42(10): 938–956,
  2023, "A sampling and learning framework to prove motion planning
  infeasibility" (DOI 10.1177/02783649231154674 — NOTE the journal title
  differs from RSS); RA-L 8(12): 8303–8310, 2023 (Coxeter triangulation);
  arXiv:2406.04795 (2024, still preprint as of Sept 2026): GPU batch
  triangulation, 5–6-DoF scenes, "both 6-DoF scenes take less than a minute
  on average" on RTX 4070 + i9-13900K. Their certificate: a triangulated
  manifold checked by a floating-point pipeline. Ours: an algebraic object
  checked in exact rational arithmetic. NO SPEED-RACE CLAIM (different
  scenes, hardware, proof objects); what we claim: "we reach the same DOF
  frontier on a laptop CPU, with a certificate of a different nature."
  (Intro aside: their ref. [9] is the author's own aSyMov paper —
  Cambon, Alami, Gravot, IJRR 2009 — as TAMP motivation; disclose.)
- **Henrion, Miller & Safey El Din 2024**, "Algebraic Proofs of Path
  Disconnectedness using Time-Dependent Barrier Functions,"
  arXiv:2404.06985 (code: jarmill/set_connected): moment-SOS hierarchy for
  set disconnection, necessary-and-sufficient, on abstract semialgebraic
  sets up to n ≤ 3, floating-point SDP. KEY FENCED SENTENCE (A37): "We
  certify disconnections in up to seven active dimensions, in a different
  setting: their scheme is necessary-and-sufficient on abstract sets; ours
  is sufficient-only, specialized to articulated arms, and exactly
  re-verifiable." Also cite Capco, Safey El Din & Schicho (ISSAC 2020;
  JSC 2023): exact symbolic connectivity queries for robot kinematics
  (singularities), a different question — no workspace obstacles.
- **C-IRIS** — Dai*, Amice*, Werner, Zhang, Tedrake, "Certified Polyhedral
  Decompositions of Collision-Free Configuration Space," IJRR 2024
  (DOI 10.1177/02783649231201437; WAFR 2022 precursor). Certifies
  collision-FREE polytopes (the complement problem) via SOS/SDP, floating
  point, on a 7-DOF iiwa. MUST STATE: C-IRIS works in the SAME rational
  (tan half-angle) parametrization we use — it is the origin of Drake's
  RationalForwardKinematics, which our generator calls. We share the
  parametrization; we differ in the question (free vs disconnected), the
  certificate (SDP float vs LP exact-verified), and the verifier.
- **Path non-existence, classical/floating-point line**: Zhang, Kim &
  Manocha, IJRR 2008 (C-obstacle cell labelling); McCarthy, Bretl &
  Hutchinson, ICRA 2012 (alpha shapes); Varava et al., IJRR 2021 (caging,
  path non-existence); Thomas, Mastrogiovanni & Baglietto, arXiv:2501.11434
  / Robotics and Autonomous Systems 2025 (bitmap discretization, ≤ 5 DOF,
  detection not certificate). One sentence each at most.
- **Interval/reliable robotics** — Jaulin, "Path Planning Using Intervals
  and Graphs," Reliable Computing 7(1): 1–15, 2001: counts path-connected
  components with guaranteed interval arithmetic (so it proves
  disconnection), 2-D example; the proof is the paving itself, no compact
  re-checkable certificate object.
- **Exact algebraic motion planning** (Canny 1988): complete and exact, not
  practical; we occupy a middle point: practical scenes, exact *verification*.
- Recent evidence the field is active: arXiv:2606.26700 (June 2026,
  learning motion feasibility from point clouds) states existing
  infeasibility certification "is limited to low-dimensional configuration
  spaces" with "simplified geometric environments" — precisely the gap our
  7-DOF exact certificate on a faithful iiwa7 addresses.
- Positioning sentence: "To our knowledge, no prior work produces an
  infeasibility certificate for articulated-arm motion planning that an
  independent program can re-verify in exact arithmetic."

## 3. Method

- s = tan((q − q*)/2) parametrization; per-link common denominator
  D(s) = ∏(1+s_i²) > 0; numerators degree ≤ 2/var (rational FK).
- Barrier φ (rational, degree ≤ 2/var), slab {|φ| ≤ δ}; disconnection =
  slab ⊆ C_obs + start/goal strictly on opposite sides (condition (i) at
  rational s_start, s_goal).
- Per-cell witness: x(s) = Σ λ_k(s)·v_k(s), Σλ_k ≡ 1, λ_k ≥ 0 (Bernstein);
  face j: g_j = b_j·D − a_jᵀX; slab-aware product T = δ² − φ²; constraint
  Bernstein(g_j − μ_j·T) ≥ t, μ_j ≥ 0. All linear in (λ coefficients, μ, t)
  ⟹ pure LP (HiGHS); NO SDP anywhere in the critical path.
- Sign discipline: g − μT (never g + μT); the test suite contains an
  instance where the wrong sign certifies a false premise — and the
  verifier re-forms the product itself (see §5).
- Branch-and-bound over the joint box; slab-aware leaves; axis heuristics
  restricted to ACTIVE dimensions; work-queue parallelism with
  byte-identical certificates vs serial.
- Certificate export: when an execution-time applicability check holds (no
  rational-passivity division for the pair; every passive dimension absent
  from the ORIGINAL denominator, numerators and barrier), the exported leaf
  is the reduced decision witness embedded in full dimension (zero exponents
  on passive axes); otherwise a full-dimension re-solve. Each embedded leaf
  is audited with the verifier's own leaf check before export (a rejection
  falls back to re-solve and is counted, expected zero). The verifier
  arbitrates in full dimension in both cases and cannot tell them apart.
  Measured: export 581 s → 6 s on the flagship; certified leaves
  byte-identical to the re-solved ones on two of three shipped scenes, a
  different (equally verified) optimal witness on the third.
- Verdicts: PROOF (exactly verified) / ENGINE-PROOF (engine OK, exact
  verification unavailable, always flagged) / UNDECIDED (never claimed
  infeasible — SPEC §6 discipline, stated verbatim in the paper).

## 4. Theorem and scope (honest statement)

- Theorem statement (informal + formal): if the certificate verifies, no
  continuous collision-free path connects s_start to s_goal within the box.
  The theorem quantifies over the FULL box including passive dimensions —
  passivity is a cost lever, not a scope restriction. KEY SENTENCE: "the
  proof covers the redundant joints; it does not exclude them."
- Restrictions, each stated as-is: static polytopal obstacles (H-rep,
  exact rationals); convex certified bodies (vertices, rationalized);
  revolute serial chains; q* = 0; locked joints via exact rational
  (cos, sin) with cos²+sin²=1 checked; rational s_start/s_goal; joint box
  within (−π, π) (no wrap-around); barrier is *given* with the scene
  (automatic fitting exists but the shipped certificates use baked φ).
- Kinematic fidelity paragraph (A41, write verbatim): "Our iiwa7 model is
  exact as an internal object; its fidelity to the physical robot is bounded
  by the published URDF itself, whose joint axes are quaternion-rounded to
  ~3.7e-6. We certify a rational kinematics faithful to the published URDF
  to ~2e-6 rad — not 'the exact iiwa' in an absolute sense, because no such
  published description exists."

## 5. The independent verifier (the credibility core)

- 499 lines, Python stdlib only, `fractions.Fraction`, zero imports from the
  generator (AST-audited in CI). Re-derives the FK from the certificate's
  declared chain (half-angle substitution re-implemented from scratch);
  re-forms g − μT itself (a certificate cannot carry the unsound sign);
  re-proves the paving (disjoint cover reconstructed by recursion on
  midpoint bisections — the tree is not stored); checks the five conditions.
- Adversarial hardening: 26 mutations on planar certs + spatial suite +
  locked-joint suite (moved locks, corrupted cos/sin, removed leaves = holes,
  duplicated leaves = overlaps, relabeled leaves, scaled λ, negative μ, ...)
  — all rejected; verifier never raises on corrupted input (returns reasons).
- Two-layer soundness boundary (explain, it will be asked): verify.verify
  checks INTERNAL validity (the robot the certificate declares);
  scene cross-check ties the statement to the authored scene file.
- Verify wall-clock: 2.4 s on the 7-DOF flagship, 0.04 s on 4-DOF. The
  generator also calls the verifier's own leaf check as an export guard
  (no re-implementation, so the guard cannot drift from the arbiter).

## 6. Cost model and scope of low-cost certifiability (the scope section)

- The selection-effect insight (A35, write carefully): "The disconnections
  our scheme certifies at low cost are proximal: a body early in the chain
  is trapped, and no setting of downstream joints frees it. This is a
  selection effect of the method (low-degree scalar barrier + slab), not a
  property of disconnections in general. It matches the disconnections that
  matter in practice — bins, shelves, guards — and we state it as an assumed
  scope, not a hidden one."
- The selection effect, MEASURED on the real robot (S11, write as a result):
  "On the iiwa7 link 3 we swept 3 active axes × 6 directions × 2 obstacle
  motifs for a robust separation margin. Exactly one proximal trap is robust:
  shoulder pitch against an overhead obstacle (+175 mm). Base yaw and arm roll
  are negative in every direction; 'crossing a vertical wall' is negative
  everywhere — the compact link is anchored at the shoulder and can never lie
  entirely on one side of a vertical plane. Our three use-case scenes therefore
  share one mechanism and differ in obstacle geometry, joint limits, slab,
  poses, and claim. We state this rather than disguise it: it is the
  selection effect of §6 observed on real geometry." (Also feeds the A43
  design finding: faithful compact silhouettes remove the lever arm that made
  segment bodies easy to trap.)
- Cost model, measured: leaves ≈ constant in passive dims; per-leaf LP
  lines = (d+1)^k in ACTIVE dims k (measured ×4.99/dim over 766 → 469,006,
  k=3..7); active-dims reduction ×612 on the 7-DOF flagship (full 469k
  lines → 766); certify wall-clock dominated by the full-dim re-solve at
  export (soundness architecture), itself parallelizable.
- The wall that isn't (S9f, fence it — A38): "On our family of synthetic
  sealed benchmarks with a simple barrier, the affine witness certifies
  every k ≤ 7 (2–4 leaves); the practical frontier is the size of a single
  LP (~470k rows at k=7; at k=8 one LP exceeds the time budget). We did NOT
  measure disconnections requiring many leaves at high k (cages, windows) —
  the product leaves × (d+1)^k remains the open regime." Figure: S9f wall
  (log cost vs active dims).
- Comparison table vs Li-Dantam (from DECISION-G2 §4, keep all caveats).

## 7. Experiments

- Planar regression (E3/E4, multi-pair relay, learned-φ pipeline).
- 4-DOF shoulder-elbow anchor (Li-Dantam scenario reproduction, approximate,
  documented; PROOF exact since S9a; 0.043 s engine + 0.041 s verify).
- 5–6-DOF iiwa-like bin (G2'): PROOF + exact verify, 1.0 s / 3.9 s, 8 leaves,
  A32 = 0, laptop CPU, no GPU.
- Active-dims wall bench (S9f): table k=3..8 with termination causes.
- 7-DOF flagship (ACQUIRED, S10-quinquies, bench 20260908T121907Z):
  KUKA iiwa7, kinematics faithful to the published URDF (parity 1.99e-6 vs
  Drake; the SDF itself is axis-aligned only to ~3.7e-6), convex link-3
  silhouette from the Drake visual mesh (40 support vertices, parity
  1.67e-6), rationalized. Trap: barrier φ = shoulder pitch (q2), overhead
  shelf (exact H-rep); slab = upright arm; start/goal pass beneath with the
  arm inclined. Separation margins +91.5 mm (slab penetration) / +83.3 mm
  (start/goal clearance) — a 6 mm base-yaw trap was refused as fragile.
  Dense ground truth with a convex-body oracle: 0 free / 40k uniform + 448
  corner samples; 16 distal-joint extremes all in collision (redundancy
  invariance); free on both sides. Result: PROOF, exact verify OK, A32 = 0,
  2 leaves (2 collision, 0 outside). Active dims measured (q1,q2,q3),
  passive (q4..q7). Per-leaf LP: 1,070 rows reduced vs 473,870 full (×443).
  Wall-clock (S12 export contract, bench 20260909T092652Z, cold, one
  process per scene): certify 46.7 s = 39.1 s symbolic FK build + 1.3 s
  branch-and-bound + 6.3 s export (of which 4.9 s is the exact per-leaf audit
  plus the full verify loop — the verifier deliberately runs twice as a
  guard); verify 2.42 s. Same order on the two other use-case scenes (46–47 s).
  Before the export switch, the full-dimension re-solve cost 726 s. Design finding worth a sentence:
  the faithful compact silhouette removed the lever arm that made segment
  bodies easy to trap by base yaw; the working separator was shoulder pitch,
  found by measuring per-joint z-lever before choosing. THIS IS FIGURE 1 +
  the headline. (iiwa-like bench flagship from S10 kept as methodology
  validation, ×612 reduction, certify 16 s.)
- SOUNDNESS BOX (the credibility anecdote, write as a numbered box):
  (1) micro-channel: an 11³ grid finds 0 free samples in the slab; dense
  sampling finds free configs; the certifier REFUSES. (2) leaky-scene k=5:
  WE authored a scene, dense ground truth said 0/8000 free, the certifier
  refused — free configs survived in corners of measure ~0. "The tool
  believes no one, including its authors."
- Reproducibility: all benchmarks dated + commit hash + git-dirty flag;
  seeds fixed; verifier public.

## 8. Limitations and future work

- Not measured: many-leaf disconnections at high active dims (cages,
  windows) — the honest open regime (product leaves × (d+1)^k).
- Barrier is scene-provided in shipped certificates (auto-fit exists,
  planar-validated; structured fitting for passive dims is future work).
- Geometry: one convex hull per certified body today; convex decomposition
  of full meshes = future work with a cost to measure (multi-pair machinery
  A30 is in place). Level-2 realism explicitly future work.
- Static obstacles; no dynamics; polytopes only.
- LP size at high k: single-LP frontier (~2.3M rows at k=8) — column
  generation / Kronecker-structured lazy Bernstein / correlative sparsity in
  Bernstein-LP form = open (paper #2 candidates: slab complexes for cages).
- URDF precision ceiling (A41) — restate.

## 9. Reviewer note (1 page, appendix or cover letter — Stéphane decides)

- Genesis disclosure: project executed by an AI coding agent (Claude Code)
  under AI supervision (Claude) directed and signed off by the human author;
  every gate, scene validation, and the G2' GO decision carry a human
  signature; the verifier is the trust anchor precisely because the
  generation pipeline should not be trusted.
- Skepticism map (anticipate and answer): "3-DOF in disguise" → the theorem
  quantifies over the full box (§4); "cherry-picked scenes" → selection
  effect stated as scope (§6) + wall bench; "why not just SOS" → exact LP
  verification chain, no SDP; "URDF exactness" → A41 paragraph; "speed
  comparison unfair" → we make no speed claim.

---

## Figure plan

- Fig 1: real-iiwa7 flagship — 3D render (Drake meshes, certified hull
  highlighted per A40 legend) at start/goal + upright transit into the shelf;
  C-space cut on pitch q2 with full-height wall; certificate stats box
  (2 leaves, ×443, verify 3.8 s). THE figure. Source assets: S10-quinquies
  figures + Meshcat render.
- Fig 2: method overview (slab in C-space, witness on a leaf, certificate
  pipeline generator vs verifier).
- Fig 3: S9f wall (log per-LP cost vs active dims, PROOF k≤7, budget point k=8).
- Fig 4: passive-dims calibration (leaves constant, ×612 reduction bar).
- Fig 5 (or box): soundness episodes.
- Table 1: scenes summary (DOF, active dims, leaves, certify/verify s, A32).
- Table 2: comparison to Li-Dantam lineage + Henrion (nature-of-certificate
  table, from DECISION-G2 §4 with caveats verbatim).

## Writing conventions (binding for all sections)

- Never: speed-race claims ("×15"), "we gained N dimensions", "the exact
  iiwa", UNDECIDED implied infeasible.
- Always: "different settings" fence next to any Henrion comparison;
  "on our family of sealed synthetic benchmarks" next to any k≤7 claim;
  URDF-precision fence next to any fidelity claim; "selection effect"
  framing for the proximal class.
- Numbers only from dated benchmark JSONs (commit + git_dirty); no numbers
  from memory.
- Timing: "seconds" applies to 5–6-DOF scenes and to the decision path;
  the 7-DOF real-geometry flagship is "under a minute, dominated by symbolic
  kinematics setup" (≈47 s, 83% FK build); verification is always seconds
  (2.4 s). Never blur the three. Never quote the pre-S12 "minutes" as
  current. Future work (honest, stated in §8): cache or replace the symbolic
  FK build (Drake RationalFK); the FK is currently built twice per certify.
- Column effect (A44, measured): at equal row count (473,870 vs 469,006),
  the 40-vertex hull multiplies LP columns ×14.2 (327 vs 23) and export time
  ×39.9 per leaf ≈ columns^1.39. Faithful silhouettes cost columns in the
  full-dim LP, nothing in the reduced one (1,070 rows).

## Open items

1. DONE — Figure 1 + headline resolved (S10-quinquies, 2026-09-08). Remaining:
   produce the actual Fig 1 composite (render + C-space + stats box) — S11
   viz task.
2. DONE — A28 bibliography pass (2026-09-09), see BIBLIO-VERIFIED.md.
   Residual at drafting: author list of arXiv:2606.26700; pick the Bernstein-
   bounds reference.
3. Title choice; venue confirm (RSS 2027; arXiv timestamp preprint earlier —
   schedule to be decided with Stéphane given three active groups converging).
4. Reviewer-note placement (appendix vs cover letter).
5. Friendly review list: Toulouse network; Henrion (LAAS) = maximal stress
   test; Jared Miller (ETH).
