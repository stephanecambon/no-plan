# Exactly Verifiable Infeasibility Certificates for Robot Motion Planning

**Draft v0.1 — 2026-09-09 — §§ Abstract, 1, 2.** Sections 3–8 and the
reviewer note follow. Working title; alternatives in PAPER-SKELETON.md.
Author line, affiliation and acknowledgements to be set by S. Cambon.
All numbers are read from dated benchmark files in `benchmarks/results/`
(commit hash and dirty-tree flag recorded); none is quoted from memory.

---

## Abstract

When a motion planner fails to find a path, it produces no evidence: a
sampling-based planner simply runs out of time, and an optimizer reports
"infeasible" from a local solve. Yet downstream consumers — task-and-motion
planners pruning a search tree, safety engineers arguing that a robot cannot
reach an operator zone, workcell designers checking reachability — need a
*proof* that no path exists. The infeasibility proofs available today rest on
floating-point pipelines: a learned or triangulated separating manifold,
validated by a numerical collision checker, that the consumer must trust as a
whole. We present, to our knowledge, the first infeasibility certificates for
motion planning of articulated arms that are *exactly re-verifiable a
posteriori*. A certificate is a finite algebraic object; an independent
verifier of 499 lines of standard-library Python, computing in exact rational
arithmetic, re-derives the robot's kinematics from the certificate's own
declaration and checks the proof without trusting the planner, the LP
solver, or any collision checker. The method combines a rational
parametrization of forward kinematics, a low-degree scalar barrier whose
level set separates start from goal inside the obstacle region, and per-cell
witness certificates obtained by linear programming over Bernstein
coefficients — no semidefinite programming anywhere in the trust chain. We
certify disconnection for arms up to 7 DOF on a laptop CPU: in seconds for
5–6-DOF scenes, and in under a minute for a KUKA iiwa7 whose kinematics are
faithful to the published URDF to 2·10⁻⁶ rad and whose trapped link carries
its faithful convex silhouette, proven unable to reach a target behind an
overhead shelf with a 90 mm separation margin; the verifier re-checks that
certificate in 2.4 s. The certified class matches the GPU-scale frontier of
recent infeasibility provers in degrees of freedom, with a certificate of a
different nature. Cost is governed by the number of *active* dimensions of
the trapped body, not by total DOF: redundant joints are covered by the
theorem at negligible cost (a measured 443× reduction of the per-leaf LP on
the 7-DOF flagship). We report two episodes in which the certifier refused
disconnection claims that dense sampling had validated — one authored by us.

---

## 1. Introduction

Completeness is the property motion planning most often gives up. A complete
planner returns a path when one exists and reports non-existence otherwise;
in high-dimensional configuration spaces, practical planners return paths
when they can and time out when they cannot. The asymmetry matters because
non-existence is not a corner case. Task-and-motion planning (TAMP) explores
alternatives whose motion sub-problems are frequently infeasible, and treats
a timeout as a weak, expensive signal [Cambon–Alami–Gravot 2009; Dantam et
al. 2018; Garrett et al. 2018]. Safety cases for collaborative cells must
argue that an arm cannot reach a protected zone under any joint
configuration. Workcell and fixture design must establish that a target is
unreachable *before* the cell is built. In all three, the desired output is a
proof, and the proof must be one the consumer can check.

Recent work has made infeasibility proofs practical for manipulators. Li and
Dantam construct a separating manifold in the obstacle region of the
configuration space — first by learning, later by Coxeter triangulation on a
GPU — and prove that it separates start from goal [Li–Dantam 2021, 2023a,
2023b, 2024]. Henrion, Miller and Safey El Din prove path-disconnectedness of
abstract semialgebraic sets with a moment–sum-of-squares hierarchy [Henrion
et al. 2024]. Dai, Amice and co-authors certify collision-*free* polytopes
in a rational parametrization of the configuration space [Dai et al. 2024].
These results share a property that is easy to overlook: the certificate's
validity rests on a floating-point computation. A triangulated manifold is
declared inside the obstacle region by a numerical collision checker; an SOS
certificate is a semidefinite program's output, accepted at solver tolerance.
The consumer trusts the pipeline. For pruning a TAMP search that is a
reasonable bargain. For a safety argument, or for a reviewer who wants to
recount the proof, it is not what one would want.

**Our contribution is not a higher degree-of-freedom count; it is a change
in the nature of the certificate.** We produce infeasibility certificates for
articulated arms that an independent program re-verifies in exact rational
arithmetic, from the certificate alone. The verifier is 499 lines of Python
that import nothing beyond the standard library and nothing from the
generator. It re-derives the forward kinematics from the joint chain declared
in the certificate, re-forms the algebraic positivity conditions itself, and
re-proves that the certified cells tile the joint box. An auditor can read
it in an afternoon and recount the proof by hand on a small instance.

The method (§3) rests on three ingredients, none of them new in isolation.
First, the half-angle substitution s = tan((q − q\*)/2) makes the forward
kinematics of a revolute chain a rational function with a common
denominator per link; this is the parametrization used by C-IRIS [Dai et al.
2024] and available in Drake. Second, a low-degree scalar barrier φ defines
a slab {|φ| ≤ δ} in joint space; if the slab lies inside the obstacle region
and start and goal lie strictly on opposite sides, no path connects them.
Third, on each cell of a branch-and-bound partition, a *witness point* moving
with the robot — an affine combination of the vertices of a convex body,
with coefficients that are themselves polynomials in s — is shown to lie
inside an obstacle polytope on the whole cell ∩ slab, by a Putinar-style
product g − μT whose non-negativity is established through Bernstein
coefficients. Every constraint is linear in the unknowns, so each cell is an
LP; no semidefinite program appears in the trust chain, and the only
floating-point computation, the LP solve, is downstream of nothing the
verifier trusts.

The contributions are:

**(C1)** A certificate schema for configuration-space disconnection of
articulated arms — slab-aware Bernstein-LP witnesses over a rational FK
parametrization — with a three-valued verdict: PROOF (exactly verified),
ENGINE-PROOF (accepted by the generator, exact verification unavailable for
the scene class, always flagged), and UNDECIDED, which is never read as
"infeasible".

**(C2)** An independent exact verifier (< 500 lines, standard library only,
zero imports from the generator) that re-derives kinematics, re-forms the
positivity products, re-proves the tiling, and is hardened against 28
adversarial certificate mutations, including moved locked joints, corrupted
rational rotations, removed leaves (holes) and duplicated leaves (overlaps).

**(C3)** A measured cost model: the per-leaf LP grows as (d+1)^k in the number
k of *active* dimensions of the certified body, while passive (redundant)
dimensions are covered by the theorem at almost no cost. On the 7-DOF
flagship the active-dimension reduction is 443×; on a family of sealed
synthetic disconnections the affine witness certifies every k ≤ 7, with the
practical frontier set by the size of a single LP rather than by
certifiability.

**(C4)** Certified scenes from 2-DOF regression cases to a KUKA iiwa7 with
kinematics faithful to the published URDF (2·10⁻⁶ rad) and a faithful convex
link silhouette (40 support vertices, 1.7·10⁻⁶), certified in under a minute
on a laptop CPU and verified in 2.4 s; three use-case scenes (bin picking,
pharmacy shelf, safety guard) on the same robot; and two documented episodes
in which the certifier caught disconnection claims that dense sampling had
validated.

**Scope, stated up front.** The theorem quantifies over a box of joint
values with |q_i − q\*_i| < π (no wrap-around), for serial revolute chains
with q\* = 0 or locked joints at exactly rational (cos, sin); obstacles are
static polytopes in H-representation with rational coefficients; certified
bodies are convex hulls of rational vertices; the barrier φ is supplied with
the scene (an automatic fitting pipeline exists and is validated on planar
scenes, but the certificates we ship use scene-provided barriers). The
kinematic model is exact as an internal object; its fidelity to the physical
robot is bounded by the published URDF, whose joint axes are quaternion-
rounded to about 3.7·10⁻⁶ — we certify a rational kinematics faithful to the
published description to 2·10⁻⁶ rad, not "the exact iiwa" in an absolute
sense, since no such description exists. Finally, the disconnections our
scheme certifies at low cost are *proximal*: a body early in the chain is
trapped and no setting of downstream joints frees it. This is a selection
effect of the method — a low-degree scalar barrier and a slab — and not a
property of disconnections in general; it happens to match the
disconnections that matter in practice (bins, shelves, guards), and we state
it as a scope rather than hide it (§6).

A note on provenance: the TAMP motivation above closes a loop with the first
author's own early work on hybrid task and motion planning [Cambon–Alami–
Gravot 2009], cited as such by Li and Dantam [2024]. The present work was
carried out with AI coding assistants under human direction; every gate,
scene validation and design decision carries a human signature, and the
verifier is the trust anchor precisely because the generation pipeline is
not to be trusted. We return to this in the reviewer note (§9).

---

## 2. Related Work

**Infeasibility proofs for manipulators.** Li and Dantam's line of work is
the closest in aim. Starting from a general framing [Li–Dantam, IROS 2020],
they learn a closed separating manifold in the obstacle region with an SVM
alongside a bidirectional RRT, triangulate it, and check containment in the
obstacle region numerically; proofs for 3- and 4-DOF arms take a few minutes
on a CPU ("less than 4 minutes on average" for a 4-DOF SCARA) [Li–Dantam,
RSS 2021; IJRR 2023a]. Convergence guarantees under sampling assumptions
follow in [Li–Dantam, WAFR 2022]. Coxeter triangulation of the manifold
[Li–Dantam, RA-L 2023b] and its batched GPU implementation [Li–Dantam,
arXiv:2406.04795, 2024] bring the approach to 5- and 6-DoF scenes, "both
6-DoF scenes taking less than a minute on average" on an RTX 4070 with an
i9-13900K. Their certificate is a triangulated manifold whose obstacle
containment is asserted by a floating-point collision pipeline; ours is an
algebraic object checked in exact arithmetic by an independent program. We
make no speed comparison: the scenes, hardware and proof objects differ, and
the scenes we certify exploit passivity that theirs may not. What we do
claim is that we reach the same degree-of-freedom frontier on a laptop CPU,
with a certificate of a different nature.

**Algebraic disconnection.** Henrion, Miller and Safey El Din prove
path-disconnectedness of two subsets of a basic semialgebraic set with
time-dependent barrier functions and the moment–SOS hierarchy [Henrion et
al., arXiv:2404.06985, 2024]. Their scheme is necessary and sufficient, on
abstract sets, with examples up to three variables, and its certificates are
semidefinite-program outputs in floating point. We certify disconnections in
up to seven active dimensions, in a different setting: our scheme is
sufficient-only, specialized to articulated arms, and exactly re-verifiable.
The two are complementary — theirs answers the abstract question completely
in low dimension; ours answers a restricted question at scale, with an
auditable object. Exact symbolic connectivity queries also exist for robot
kinematics, for cuspidal robots and singularity-free paths [Capco, Safey El
Din, Schicho, ISSAC 2020; JSC 2023]; that is a different question — the
connectivity of the kinematic map's domain, with no workspace obstacles.

**Certified free space.** C-IRIS [Amice et al., WAFR 2022; Dai et al., IJRR
2024] answers the complementary question: it grows convex polytopes in a
rational parametrization of the configuration space and certifies them
collision-free with sums of squares. We work in the same rational
parametrization — indeed we call Drake's `RationalForwardKinematics`, which
originates in that work — and we owe the observation that revolute
kinematics become rational under the half-angle substitution to that line.
We differ in the question (disconnection rather than free regions), in the
certificate (linear rather than semidefinite programming, so that
verification reduces to exact rational arithmetic), and in providing an
independent verifier. C-IRIS has been demonstrated on a 7-DOF iiwa; so has
our method.

**Path non-existence, numerical.** Proving that no path exists by labelling
configuration-space cells [Zhang, Kim, Manocha, IJRR 2008], by alpha shapes
over samples [McCarthy, Bretl, Hutchinson, ICRA 2012], by caging analysis of
rigid bodies [Varava et al., IJRR 2021], or by incremental bitmap
segmentation up to 5 DOF [Thomas, Mastrogiovanni, Baglietto, RAS 2025] gives
a detection, in floating point and on a discretization, rather than a
certificate an independent party can re-check. Interval analysis offers
guarantees: Jaulin computes the number of path-connected components of a set
defined by nonlinear inequalities with outward-rounded intervals [Jaulin,
Reliable Computing 2001], which does prove disconnection; the proof, however,
is the paving itself, and the demonstrations are two-dimensional. Canny's
roadmap algorithm is exact and complete but not practical [Canny 1988]. We
sit between these: practical scenes, exact *verification*, with a compact
proof object.

**Why the field is moving.** A June 2026 preprint on learning motion
feasibility from point clouds observes that existing infeasibility
certification "is limited to low-dimensional configuration spaces" and
"often assume[s] simplified geometric environments" [arXiv:2606.26700]. The
7-DOF certificate of §7, on a kinematically faithful iiwa7 with its faithful
link silhouette, is a direct answer to the first half of that sentence; the
second half — polytopal obstacles, one convex hull per certified body — is a
limitation we share and state (§8).

To our knowledge, no prior work produces an infeasibility certificate for
articulated-arm motion planning that an independent program can re-verify
in exact arithmetic.

---

## 3. Method

### 3.1 Setting and notation

A serial revolute chain has joints q = (q_1, …, q_n) constrained to a box
P = ∏[q_i^−, q_i^+] with q_i^± ∈ (q\*_i − π, q\*_i + π). Certain joints may be
*locked* at a fixed angle whose cosine and sine are exact rationals with
cos² + sin² = 1 (0, ±π/2, π, or Pythagorean angles); locked joints carry no
variable. Obstacles are static polytopes O = {x ∈ ℝ³ : A x ≤ b} with rational
A, b. A *certified body* B is the convex hull of finitely many rational
vertices p_1, …, p_K fixed in the frame of one link. A *pair* is a couple
(B, O). Two configurations s_start, s_goal are given; the claim to certify
is that no continuous path inside P joins them without some certified body
intersecting some obstacle.

### 3.2 Rational forward kinematics

With s_i = tan((q_i − q\*_i)/2) one has cos(q_i − q\*_i) = (1 − s_i²)/(1 + s_i²)
and sin(q_i − q\*_i) = 2s_i/(1 + s_i²). Composing homogeneous transforms along
the chain of a link ℓ, every entry of the link's world pose is a polynomial
in s divided by the common denominator

  D_ℓ(s) = ∏_{i ∈ chain(ℓ)} (1 + s_i²) > 0,

with numerators of degree at most 2 in each variable. The world position of a
body-frame point p is X(s)/D_ℓ(s) with X(s) = N(s) p, so the world vertices of
B are v_k(s) = N_k(s)/D_ℓ(s), all over the same positive denominator. A locked
joint contributes a constant rotation matrix with rational entries and no
factor to D_ℓ. Fixed inter-link rotations of a real robot description that
are ±90° or 180° are signed permutation matrices and fit the same form; this
is how the KUKA iiwa7 of §7 is represented exactly (§7.4).

Constant factors are what make the kinematics *exactly* rational; the
verifier (§5) re-derives N and D from the declared chain rather than reading
them from the certificate.

### 3.3 Barrier, slab, and the disconnection lemma

A *barrier* is a rational polynomial φ(s) of degree at most 2 per variable
together with a rational δ > 0. The *slab* is Σ = {s ∈ P : |φ(s)| ≤ δ}.

**Lemma 1 (slab separation).** If Σ ⊆ C_obs, φ(s_start) < −δ and
φ(s_goal) > δ, then no continuous path in P ∩ C_free joins s_start to s_goal.

*Proof.* Along any continuous path γ from s_start to s_goal, φ∘γ is continuous
and passes from below −δ to above δ, hence takes a value in [−δ, δ] at some
γ(τ) ∈ Σ ⊆ C_obs. □

The whole method is a way of proving the premise Σ ⊆ C_obs by a finite,
exactly checkable argument. In the certificates we ship, φ is supplied with
the scene (typically a single joint coordinate, φ = s_i, whose slab is a
band of that joint); an automatic fitting pipeline (SVM on free samples
labelled by side, then least squares to degree ≤ 2 per variable, rationalized)
exists and reproduces the planar results, but it is not part of the trust
chain and not needed for the results below.

### 3.4 Cell certificates by Bernstein linear programming

Fix a pair (B, O) and a box cell C ⊆ P. A *witness* is a point
x(s) = Σ_k λ_k(s) v_k(s) with polynomial coefficients λ_k(s) — constant,
affine, or quadratic in s — satisfying Σ_k λ_k ≡ 1 as a polynomial identity
and λ_k(s) ≥ 0 on C. Then x(s) ∈ B(s) for every s ∈ C. For each face j of O
define

  g_j(s) = b_j D_ℓ(s) − a_jᵀ Σ_k λ_k(s) N_k(s),   T(s) = δ² − φ(s)².

Since D_ℓ > 0, g_j(s) ≥ 0 is equivalent to a_jᵀ x(s) ≤ b_j, and T(s) ≥ 0
exactly on the slab. If, for each face, there is a constant μ_j ≥ 0 with

  g_j(s) − μ_j T(s) ≥ 0  for all s ∈ C,                                 (1)

then on C ∩ Σ every g_j(s) ≥ μ_j T(s) ≥ 0, so x(s) ∈ B(s) ∩ O and
C ∩ Σ ⊆ C_obs. This is a one-multiplier Putinar-type product in which the
sign is essential: g_j + μ_j T would certify nothing, and the test suite
contains an instance where that sign "certifies" a cell that contains free
configurations.

Non-negativity of a polynomial on a box is established through its Bernstein
coefficients: if all coefficients of the tensor-product Bernstein expansion of
a polynomial on C are non-negative, the polynomial is non-negative on C. All
polynomials in (1) and in λ_k ≥ 0 are expanded at a common degree
d = max(deg λ + deg N, 2·deg φ) per variable (d = 4 for affine λ and
quadratic φ), and every Bernstein coefficient is *linear* in the unknowns
(the coefficients of the λ_k, the μ_j). The cell problem is therefore the
linear program

  maximise t  s.t.  Bern_C(g_j − μ_j T) ≥ t ∀j,  Bern_C(λ_k) ≥ 0 ∀k,
                    Σ_k λ_k ≡ 1,  μ_j ≥ 0,                             (2)

solved with HiGHS. A cell is a *collision leaf* if (2) has t ≥ 0 after exact
rounding (§3.7). No semidefinite program appears anywhere.

### 3.5 Outside leaves and the partition

A cell entirely outside the slab needs no witness: it is an *outside leaf*
if Bern_C(φ − δ) ≥ 0 or Bern_C(−φ − δ) ≥ 0. Starting from P, the generator
tests each cell — outside first, then (2) for each pair — and otherwise
bisects it at the midpoint of one axis: an axis whose split pushes a child
out of the slab if one exists, else the axis with the best one-step
look-ahead margin. Cells are only ever bisected at midpoints; this is a
contract with the verifier, which re-proves the tiling from that rule alone
(§5). The search stops when every cell is a leaf (PROOF), or when a budget
of leaves, time or depth is exhausted, in which case the verdict is
UNDECIDED and the open cells are reported. UNDECIDED is never read as
"feasible": the method is sound, not complete.

Leaves may be certified against different pairs; a disconnection in which
a body is trapped by one obstacle in part of the slab and by another
elsewhere is certified by a relay of pairs across leaves.

### 3.6 Active dimensions

For a pair whose body sits on link ℓ, the joints downstream of ℓ do not
enter N_k or D_ℓ. After exactly dividing N_k and D_ℓ by every factor
(1 + s_i²) they share (which removes joints that are in the chain but leave
the body's geometry unchanged, such as a roll about the body's own axis),
the variables absent from φ, from every N_k and from D_ℓ are the pair's
*passive* dimensions; the others are *active*. Along a passive axis every
polynomial in (2) is constant, so the LP is built in the k active variables
only, with (d+1)^k Bernstein coefficients per constraint instead of (d+1)^n.
The partition never bisects a passive axis, since no test depends on it.
This is a cost lever, not a restriction of the theorem: a leaf certified in k
active variables certifies the full n-dimensional cell, because the
polynomials are literally constant along the other axes. Different pairs
have different passive sets; each leaf's LP is reduced to *its* pair's
active dimensions, while the branching axis is chosen among the union.

### 3.7 Exact rounding and export

The LP returns floating-point λ, μ. They are made exact as follows. The
coefficients of each λ_k are blended toward the uniform barycentre,
λ ← (1 − α)λ + α/K with α a small fraction of the measured face margin, so
that structural zeros of Bern(λ_k) — the witness typically sits on a body
vertex — become strictly positive; all but one vertex's coefficients are
rounded to rationals with a bounded denominator, and the last is set by
subtraction so that Σ_k λ_k ≡ 1 holds exactly. The exact verifier is run on
the result; if it rejects, the denominator bound is raised and the leaf is
re-rounded. In every certificate reported here this loop accepted at the
first or second denominator bound.

Exported leaves carry (cell, pair, λ, μ) in full dimension. When the pair's
passive dimensions are absent from the *original* tensors and no common
factor was divided out, the reduced witness is embedded as-is with zero
exponents on the passive axes — the same polynomial, in n variables; the
verifier accepts it directly. Otherwise the leaf's LP is re-solved in full
dimension. Each embedded leaf is audited before export with the verifier's
own leaf check, so that an incorrect embedding cannot leave the generator:
it would fall back to the full re-solve and be counted (the count is zero on
every certificate we ship). Whichever path produced a leaf, the certificate
has the same format and the verifier cannot tell.

The branch-and-bound runs on a work queue of cells over several processes;
the tree it explores is the deterministic tree of the serial algorithm, so
parallel and serial runs produce byte-identical certificates.

---

## 4. Theorem and scope

**Theorem 1 (certified disconnection).** Let a certificate declare a joint
box P, a serial revolute chain with rational unit axes, rational offsets and
locked joints with rational (cos, sin), cos² + sin² = 1; rational polytopal
obstacles; certified bodies as rational vertex sets on named links; a
barrier (φ, δ) with δ > 0; two rational configurations s_start, s_goal; and a
finite set of leaves, each a sub-box of P labelled *outside* or *collision*
with a pair and exact rational (λ, μ). Suppose

 (i)  φ(s_start) < −δ and φ(s_goal) > δ;
 (ii) the leaves are exactly the cells of a tiling of P obtained by
      repeated midpoint bisections, with no gap and no overlap;
 (iii) every outside leaf C satisfies Bern_C(φ − δ) ≥ 0 or Bern_C(−φ − δ) ≥ 0;
 (iv) every collision leaf C with pair (B, O) satisfies Σ_k λ_k ≡ 1,
      Bern_C(λ_k) ≥ 0 for all k, μ_j ≥ 0 and Bern_C(g_j − μ_j T) ≥ 0 for
      every face j of O, where g_j, T are formed from the declared chain,
      body, obstacle and barrier as in §3.4.

Then no continuous path in P from s_start to s_goal keeps every certified
body out of every obstacle.

*Proof.* Let γ be such a path. By (i) and continuity of φ∘γ there is
s\* = γ(τ) with |φ(s\*)| ≤ δ, i.e. T(s\*) ≥ 0. By (ii) s\* lies in a leaf C. If
C were an outside leaf, (iii) would give φ(s\*) ≥ δ or φ(s\*) ≤ −δ; with
|φ(s\*)| ≤ δ this forces φ(s\*) = ±δ, still on the slab boundary — we
therefore require in (iii) the strict form Bern_C(φ − δ) > 0 or
Bern_C(−φ − δ) > 0 on at least one coefficient, or equivalently we treat
boundary cells as collision leaves; the shipped verifier uses the strict
test. Hence C is a collision leaf with pair (B, O). By (iv), x(s\*) =
Σ_k λ_k(s\*) v_k(s\*) is a convex combination of the world vertices of B at
s\*, so x(s\*) ∈ B(s\*); and for every face j, g_j(s\*) ≥ μ_j T(s\*) ≥ 0, which
after division by D_ℓ(s\*) > 0 reads a_jᵀ x(s\*) ≤ b_j. So x(s\*) ∈ B(s\*) ∩ O
and γ(τ) is a collision configuration, contradicting the hypothesis. □

Three remarks. First, the theorem quantifies over the *whole* box P,
passive dimensions included: passivity means the tiling never needed to
split those axes, not that they were excluded from the claim. Second,
soundness rests only on (i)–(iv), each of which is decidable in exact
rational arithmetic from the certificate's own data; nothing about how the
certificate was found enters the proof. Third, nothing is claimed when the
generator returns UNDECIDED.

**Restrictions.** Serial revolute chains (prismatic joints are outside the
present scope); q\* = 0 for free joints, or locked joints with exactly
rational (cos, sin); the box P lies within (q\*_i − π, q\*_i + π) per joint, so
there is no wrap-around and the theorem is about the declared box, which
may be smaller than the factory limits (every figure and interactive
artefact states the box in degrees); static obstacles in H-representation
with rational data; convex certified bodies with rational vertices;
rational s_start and s_goal (a demonstration angle with irrational
tan(θ/2) is replaced by a nearby rational configuration, and the strict
inequality (i) is checked there). The barrier is part of the certificate's
statement, not of its proof: the theorem is "given this φ, the slab lies in
C_obs and separates", and the consumer may inspect φ.

**Kinematic fidelity.** Our robot models are exact as internal objects. Their
fidelity to a physical robot is bounded by the published description: the
joint axes of the iiwa7 SDF distributed with Drake are quaternion-rounded and
aligned with the coordinate axes only to about 3.7·10⁻⁶ rad. We certify a
rational kinematics whose forward kinematics agrees with Drake's on 1 500
random configurations to 1.99·10⁻⁶ (§7.4) — faithful to the published URDF
at that level, not "the exact iiwa" in an absolute sense, because no such
description exists. The same holds for link geometry: the certified body of
§7 is a 40-vertex convex hull of the visual mesh, rationalized, agreeing
with Drake's link to 1.67·10⁻⁶.

**What is proven about what.** The verifier establishes Theorem 1 about the
robot and obstacles *declared in the certificate*. A separate cross-check
program compares that declaration, field by field, with the scene file the
user authored; a certificate whose declared geometry has been perturbed is
internally valid and is rejected by the cross-check, which is the intended
division of labour. Tying the scene file to a physical cell remains a human
responsibility, as with any model-based safety argument.

---

## 5. The independent verifier

The verifier is the reason to prefer this certificate over a
floating-point one, so we describe it in some detail.

**Size and dependencies.** `verify.py` is 499 lines of Python. It imports
`fractions`, `json`, and nothing else; in particular it imports nothing from
the generator, a property checked in the test suite by walking the module's
abstract syntax tree. Every number it manipulates is a `Fraction`. It has no
solver, no floating point, and no notion of Bernstein bounds beyond a
40-line exact implementation of the tensor-product Bernstein transform.

**What it recomputes rather than reads.** From the declared chain it
re-implements the half-angle substitution and composes exact homogeneous
transforms, so N_k and D_ℓ are its own; a certificate cannot supply
convenient numerators. From λ and μ it *forms* g_j − μ_j T itself; the
certificate carries only λ and μ, so the unsound sign of §3.4 cannot be
smuggled in. From the leaf list alone it re-proves condition (ii): since the
generator only ever bisects at midpoints, the tiling is reconstructed by
recursion — a cell is either a leaf or splits at its midpoint along some axis
into two cells that must each be covered — and both a missing leaf (a hole)
and a duplicated leaf (an overlap) are detected. The Bernstein expansions are
computed at the same degree the generator used, which is part of the
generator–verifier contract; a lower degree would yield looser bounds and
false rejections (never false acceptances).

**The five checks**, in order: (0) hypotheses — rational unit axes,
cos² + sin² = 1 for locked joints, δ > 0, box within the no-wrap-around
range; (i) the strict side conditions on s_start and s_goal; (ii) the exact
tiling; (iii) every outside leaf; (iv) every collision leaf. On any failure it
returns `(False, reason)`; it never raises on a corrupted certificate.

**Adversarial hardening.** The test suite mutates valid certificates and
requires rejection: negative or oversized μ; Σλ ≠ 1; scaled or negative λ;
a shifted cut; a removed leaf (hole); a duplicated leaf (overlap); q\* ≠ 0;
δ scaled by 20; δ < 0; s_start or s_goal on the wrong side; the sign of φ;
obstacle A or b; a hull vertex; a link length; the body's link index; a
collision leaf relabelled outside and vice versa; permuted obstacles;
corrupted theorem and substitution fields; a shrunk box; a cell outside the
box — 26 mutations on planar certificates, plus a spatial suite (non-unit
axis; wrong axis; offset that moves the body out of the trapping band) and a
locked-joint suite. The locked-joint suite is the most instructive: a
certificate whose locked pitch is moved to another exactly rational angle
must be rejected, but only if the proof *depends* on that angle. On a scene
where the witness sits on a proximal point unaffected by the lock, moving it
is not detected — and that is correct, the proof does not use it. We
therefore constructed a scene in which the lock displaces the trapped wrist
out of a narrow wall, and there the mutation is rejected. Testing a verifier
means testing the mechanism, not ticking a box.

**Two layers.** As noted in §4, `verify.verify` checks internal validity;
`scene_matches_cert` ties the declaration to the authored scene. Both are
run by the command-line `verify`. Keeping them separate keeps the sacred
module small and its contract clean.

**Reuse as a guard.** Since the S12 export contract (§3.7) the generator
calls the verifier's own collision-leaf check on every embedded leaf before
writing the certificate. We chose this over a re-implementation on purpose: a
guard that *is* the arbiter cannot drift from it. The price is that the
verifier runs twice per certificate — once per leaf as a guard, once on the
whole file — about 4.9 s on the flagship. We consider that cheap.

**Cost.** Verification of the 7-DOF flagship certificate (two collision
leaves, 40-vertex body, 7 free joints) takes 2.4 s; the 4-DOF anchor scene
of §7.2 takes 0.04 s. Verification time grows with the number of leaves and
with (d+1)^n, since the verifier expands in full dimension; it has never
been the bottleneck.

---

*[§6 Cost model and scope · §7 Experiments · §8 Limitations · §9 Reviewer
note — to follow.]*
