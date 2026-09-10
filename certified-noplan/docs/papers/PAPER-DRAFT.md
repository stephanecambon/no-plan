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
certify disconnection for arms up to 7 DOF on a laptop CPU: in well under a
second for the 2- to 5-DOF scenes, and in 47 s end to end for a KUKA iiwa7 —
39 s of which is symbolic forward-kinematics construction and 1.3 s the
branch-and-bound proof itself — whose kinematics are faithful to the
published URDF to 2·10⁻⁶ rad and whose trapped link carries its faithful
convex silhouette, proven unable to reach a target behind an overhead shelf,
the trapping band reaching 91.5 mm inside the shelf and start and goal
clearing the obstacle by 83.3 mm; the verifier re-checks that certificate in
2.4 s. The certified class matches the GPU-scale frontier of
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
positivity products, re-proves the tiling, and is hardened against 32
adversarial certificate mutations — 26 on a planar certificate, 6 on a
locked-joint certificate — together with a spatial mutation suite: moved
locked joints, corrupted rational rotations, removed leaves (holes),
duplicated leaves (overlaps), among others.

**(C3)** A measured cost model: the per-leaf LP grows as (d+1)^k in the number
k of *active* dimensions of the certified body, while passive (redundant)
dimensions are covered by the theorem at almost no cost. On the 7-DOF
flagship the active-dimension reduction is 443×; on a family of sealed
synthetic disconnections the affine witness certifies every k from 3 to 7,
with the
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

**Lemma 1 (slab separation).** If {s ∈ P : |φ(s)| < δ} ⊆ C_obs,
φ(s_start) < −δ and φ(s_goal) > δ, then no continuous path in P ∩ C_free
joins s_start to s_goal.

*Proof.* Along any continuous path γ from s_start to s_goal, φ∘γ is continuous
and passes from below −δ to above δ, hence takes the value 0 at some γ(τ),
which therefore lies in the open slab ⊆ C_obs. □

The whole method is a way of proving the premise {|φ| < δ} ⊆ C_obs by a finite,
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
polynomials in (1) and in λ_k ≥ 0 are expanded at a common per-variable degree
d = max(deg λ + deg N, 2·deg φ), where deg N = 2 is fixed by the half-angle
substitution and deg φ is the degree *declared* with the barrier (not its
effective degree — a linear φ declared at degree 2 still yields d = 4). Every
certificate reported here has d = 4 (affine λ, barrier declared quadratic),
and the verifier recomputes the same d from the certificate's own fields.
Every Bernstein coefficient is *linear* in the unknowns
(the coefficients of the λ_k, the μ_j). The cell problem is therefore the
linear program

  maximise t  s.t.  Bern_C(g_j − μ_j T) ≥ t ∀j,  Bern_C(λ_k) ≥ 0 ∀k,
                    Σ_k λ_k ≡ 1,  μ_j ≥ 0,                             (2)

solved with HiGHS. A cell is a *collision leaf* when (2) returns a strictly
positive margin (the shipped tolerance is t\* > 10⁻⁶). That decision is taken
on the floating-point LP; the multipliers are only then made exact (§3.7) and
submitted to the exact verifier, which is the sole arbiter of the final
verdict. No semidefinite program appears anywhere.

### 3.5 Outside leaves and the partition

A cell entirely outside the slab needs no witness: it is an *outside leaf*
if Bern_C(φ − δ) ≥ 0 or Bern_C(−φ − δ) ≥ 0. Starting from P, the generator
tests each cell — outside first, then (2) for each pair — and otherwise
bisects it at the midpoint of one axis: an axis whose split pushes a whole
child out of the slab if one exists, else — in the `margin` mode used by every
scene reported here — the axis with the best one-step look-ahead margin (the
library's own default fallback is simply the widest active axis). The axis
rule affects cost only, never soundness: any midpoint partition is re-proved
by the verifier from the leaf list alone. Cells are only ever bisected at
midpoints; this is a
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
first denominator bound (10⁶); the escalation path has never been taken on a
shipped scene.

Exported leaves carry (cell, pair, λ, μ) in full dimension. When the pair's
passive dimensions are absent from the *original* tensors and no common
factor was divided out, the reduced witness is embedded as-is with zero
exponents on the passive axes — the same polynomial, in n variables; the
verifier accepts it directly. Otherwise the leaf's LP is re-solved in full
dimension. Each embedded leaf is audited before export with the verifier's
own leaf check, so that an incorrect embedding cannot leave the generator:
it would fall back to the full re-solve and be counted. The count of
*rejected* embeddings is zero on every certificate we ship; the fallback
itself is not dead code — it carries all four leaves of the 4-DOF anchor
scene (§7.2), whose coaxial roll makes the embedding condition genuinely
false. Whichever path produced a leaf, the certificate
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

*Proof.* Let γ be such a path. By (i), φ(γ(0)) < −δ < 0 < δ < φ(γ(1)), so by
the intermediate value theorem applied to the continuous map φ∘γ there is τ
with φ(s\*) = 0, where s\* = γ(τ). By (ii) s\* lies in exactly one leaf C. C
cannot be an outside leaf: (iii) would give φ(s\*) ≥ δ or φ(s\*) ≤ −δ, both
impossible since δ > 0. Hence C is a collision leaf with pair (B, O). Since
T(s\*) = δ² − φ(s\*)² = δ² > 0, (iv) gives, for every face j,
g_j(s\*) ≥ μ_j T(s\*) ≥ 0, which after division by D_ℓ(s\*) > 0 reads
a_jᵀ x(s\*) ≤ b_j; and Σ_k λ_k(s\*) = 1 with λ_k(s\*) ≥ 0 puts x(s\*) in B(s\*).
So x(s\*) ∈ B(s\*) ∩ O and γ(τ) is a collision configuration, contradicting
the hypothesis. □

**Remark (what the certificate establishes).** Every s ∈ P with |φ(s)| < δ
lies in a leaf; it cannot be an outside leaf, hence it is a collision leaf,
hence it is in C_obs. The certificate therefore establishes
{s ∈ P : |φ(s)| < δ} ⊆ C_obs — the *open* slab — and Lemma 1 needs no more.
Nothing is claimed about the boundary {|φ| = δ}, and nothing needs to be.
The outside test in (iii) is non-strict, and deliberately so: the proof
selects a point at which φ vanishes, so the slab boundary never has to be
adjudicated; a strict test would reject certificates the non-strict one
accepts and prove nothing more. Condition (iii) is exactly the shipped test.

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
with Drake's link to 1.67·10⁻⁶ over 200 random configurations and all 40
support vertices (1.68·10⁻⁶ over 400).

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
`json`, `fractions` and `math.comb` — three standard-library names, and
nothing else; in particular it imports nothing from the generator, a property
checked in the test suite by walking the module's abstract syntax tree. Every
number it manipulates is a `Fraction`. It has no solver, no floating point,
and no notion of Bernstein bounds beyond a self-contained 53-line block
(38 lines of code) implementing the exact tensor-product Bernstein transform.

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
returns `(False, reason)` rather than raising: malformed inputs are caught as
`KeyError`, `ValueError`, `ZeroDivisionError` or `TypeError` and reported as a
rejection. This is a convenience for callers, not a hardening claim — the
verifier is not a fuzz target, and a sufficiently ill-formed input can still
abort it. Soundness does not depend on it: an aborted verification is not an
accepted certificate.

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

## 6. Cost model and the scope of low-cost certifiability

### 6.1 A selection effect, stated as scope

Every disconnection we certify at low cost has the same shape: a body early
in the kinematic chain is trapped, and no setting of the joints downstream of
it frees it. We call such disconnections *proximal*. This is not a property of
disconnections in general — a whole arm threading a narrow window is a
disconnection in which the collision depends on every joint — but a
selection effect of the method: a low-degree scalar barrier and a slab
certify cheaply exactly those separations that a few joints already realize.
It happens to be the class that matters in practice (bins, shelves, guards),
and we state it as the scope of the low-cost regime rather than leave it to
be discovered.

The effect was measured, not assumed, on the real robot. On the iiwa7 link 3
we swept the three active joints × six directions × two obstacle motifs (a
half-space "ceiling" and a plate "wall to cross") for a robust separation
margin. Exactly one proximal trap is robust: shoulder pitch against an
overhead obstacle (+175 mm at the design stage). Base yaw and arm roll are
negative in every direction (−73 to −299 mm); crossing a vertical wall is
negative everywhere. The compact link is anchored at the shoulder: it rotates
in place without displacing, and it can never lie entirely on one side of a
vertical plane. Our three use-case scenes (§7.5) therefore share one
mechanism and differ in obstacle geometry, joint limits, slab, poses and
claim; we say so in each scene file. A design lesson came with it: the
faithful compact silhouette of the real link removed the lever arm that had
made segment-shaped bodies easy to trap by base yaw (a 6 mm base-yaw
separation was measured and refused as fragile). On a realistic arm, the
robust separator is a joint with real lever on the body — here the shoulder
pitch — or an enclosing obstacle, not the base yaw.

### 6.2 Passive dimensions are free; active dimensions cost (d+1)^k

Two quantities govern cost: the number of leaves in the partition and the
size of each leaf's LP. Measured on the 5-DOF iiwa-like bin (§7.3) with the
number of *passive* joints varied from 0 to 3 while the three active joints
are held fixed, the leaf count is constant at 8 and the reduced LP is
constant at 766 rows; the full-dimension LP that an unreduced solver would
build grows 766 → 3 782 → 18 814 → 93 878 rows, a factor 4.9 per passive
joint, i.e. (d+1) with d = 4. The active-dimension reduction is thus ×122.6
at six joints on that family, and ×443 on the 7-DOF flagship (1 070 rows
reduced against 473 870 full). On a two-body variant the reduction is
*per pair*: the proximal pair pays its own three active dimensions (766 rows)
where a global reduction over the union of active sets would charge it
18 814 — a factor 24.6. Passivity is not a restriction of the theorem (§4);
it is a lever.

Active dimensions are the cost. On a family of synthetic disconnections
sealed by Bernstein bounds — the obstacle is proven to cover the body's reach
on the band, so each scene is a genuine disconnection — with k active joints
and a linear barrier, the affine witness certifies every k from 3 to 7 with
2–4 leaves; the per-leaf full-dimension LP runs 766, 3 782, 18 814, 93 878,
469 006 rows (×4.99 per added active dimension), and at k = 8 (about
2.3 million rows) a single LP exceeds the time budget and the verdict is
UNDECIDED-on-budget [P2: table values from `wall_resonde_S9f.json`]. The
practical frontier of this family is therefore the size of one LP, not
certifiability — and it is a frontier that column generation or a
lazily-materialized Bernstein basis could push, whereas a wall in leaf count
could not. We are careful about what this family shows: barriers are simple
and leaves are few. Disconnections that need many leaves *and* many active
dimensions (cages, windows) sit in the product leaves × (d+1)^k and were not
measured; that is the open regime.

An earlier run of the same family had suggested a wall at k = 5. It was an
artefact: a silent depth cap in the branch-and-bound, and a scene that was
not actually disconnected (the second episode of the soundness box in §7.7).
We report it because the diagnosis changed how the engine reports termination
— every UNDECIDED now names its cause — and because it is the kind of
measurement error a certificate should protect one from.

### 6.3 Where the time goes

After the export contract of §3.7, certifying the 7-DOF flagship takes 46.7 s
on a laptop CPU: 39.1 s building the symbolic forward kinematics, 1.3 s for
the branch-and-bound proof, 6.3 s for export — of which 4.9 s is the exact
verifier running twice, once per leaf as a guard and once on the whole
certificate. The proof itself is a second; the trust chain is five; the rest
is symbolic setup that a cache or a faster kinematics backend would remove.
Before the export contract, re-solving each leaf's LP in full dimension cost
726 s, and the cost was not in rows: at equal row count (473 870 vs 469 006),
the 40-vertex faithful hull multiplies LP columns by 14.2 (327 vs 23) and
solve time per leaf by 39.9 (about columns^1.39). Faithful silhouettes cost
columns in the full-dimension LP and nothing in the reduced one — which is
why the reduced witness, embedded, is the right thing to export.

### 6.4 The nature of the certificate

| | Li–Dantam 2024 (GPU) | Henrion et al. 2024 | C-IRIS 2024 | This work |
|---|---|---|---|---|
| Question | disconnection | disconnection | free regions | disconnection |
| Setting | manipulators, 5–6 DoF | abstract sets, n ≤ 3 | manipulators, 7 DoF | manipulators, ≤ 7 DoF |
| Certificate | triangulated manifold | moment-SOS | SOS | Bernstein-LP witnesses |
| Checked by | float collision checker | SDP solver tolerance | SDP solver tolerance | exact rational arithmetic, independent program |
| Hardware | RTX 4070 + i9 | — | — | laptop CPU |
| Complete? | asymptotically | necessary & sufficient | — | sufficient only |

The table is about kind, not speed. The scenes, hardware and proof objects
differ, and the disconnections we certify exploit passivity theirs may not.

---

## 7. Experiments

All runs: MacBook (Apple Silicon), CPU only, Python 3.12, HiGHS via
`highspy`. Every benchmark is written with its commit hash and a dirty-tree
flag; every sampling step is seeded. Ground truth is always established
*before* certification (start and goal free; no free sample in the slab, with
uniform and corner-biased sampling; free space on both sides), with a
convex-body-versus-polytope oracle (an LP feasibility test) that is
independent of the certificate. Verification times are for the exact
verifier of §5.

### 7.1 Planar regression

Two planar 2-DOF scenes fix the ground: a three-obstacle relay in which the
middle link is trapped by three "teeth" in turn (46 leaves: 38 collision
across three pairs, 8 outside) and a scene with a learned barrier (78
leaves) [P2]. Their certificates reproduce, coefficient for coefficient at
10⁻⁷, an earlier sum-of-squares implementation kept only as a cross-check.
A 3-DOF "comb" lifts the relay by one passive joint (54 leaves) and was the
first scene on which a naive widest-axis heuristic blew up (736 leaves,
UNDECIDED) while the active-axis rule certified — the origin of §3.6.

### 7.2 A 4-DOF anchor

We reproduce the shoulder-elbow 4-DOF scenario of Li and Dantam [2021] —
spherical shoulder plus elbow, target blocked by a panel — as an approximate
reproduction, since they publish topology and task but no geometry; all
dimensions are ours and are tabulated against theirs in the repository. The
upper arm is trapped by a thin vertical panel over a band of base yaw for all
admissible pitch; roll and elbow are passive. PROOF in 8 leaves, engine
0.043 s, verification 0.041 s. Ground truth: 0 free in the slab over 150 000
samples [P2]; the panel shrunk in width gives UNDECIDED. Their reported time
for the same class is minutes on a CPU; we do not compare speeds (§6.4).

### 7.3 A 5-DOF iiwa-like bin

A 7-joint S-R-S chain with iiwa-like link lengths and two wrist joints
locked at 0 (5 DOF), reaching into a deep bin with a sealed front wall. The
trapped body is link 2; joints 3–6 are passive for the pair (3 active
dimensions). Ground truth 0 free over 40 000 samples. PROOF, 8 leaves,
certify + verify ≈ 1.0 s; releasing locks one at a time gives the passive-
dimension calibration of §6.2 (8 leaves throughout; 3.3 s certify at 6 DOF
before the export contract) [P2]. This scene passed our 5–6-DOF gate with
three orders of magnitude of margin on every criterion, and it is where the
proximal insight of §6.1 was first written down.

### 7.4 The KUKA iiwa7 flagship

*Kinematics.* From the iiwa7 SDF distributed with Drake we fold the constant
inter-link transforms into 19 chain entries: 7 variable joints about the
coordinate z-axis and 12 locked joints realizing the signed-permutation
inter-link rotations (±90°, 180°) with cos, sin ∈ {0, ±1}; offsets are
rationalized to denominator 10⁶. The composition convention
T_i(θ) = X_PF,i · Rot(z, θ) · X_ML,i with the constants folded into
G_i = X_ML,i · X_PF,i+1 is what makes this exact; a naive conjugation of the
rotation through the joint frame is wrong because it displaces the
translation. Forward kinematics agrees with Drake's on 1 500 random
configurations in the factory limits to 1.99·10⁻⁶ (maximum position error);
the SDF's own joint axes are aligned with the coordinate axes only to
3.67·10⁻⁶, so this is the fidelity of the published description itself.

*Body.* The certified body is link 3: the convex hull of Drake's visual mesh
(1 301 hull vertices) is reduced by support sampling in 40 directions on a
Fibonacci sphere to 40 true extreme points, expressed in the chain frame
after joint 3 and rationalized. Against Drake's link, the hull agrees to
1.67·10⁻⁶ over 200 random configurations and all vertices.

*Trap.* Designed by measurement (§6.1): φ = s_2 (shoulder pitch), δ = 1/5, an
overhead shelf in H-representation with underside at z = 17/25 = 0.68 m. With
the arm upright the link's top reaches 0.808 m and strikes the shelf; with the
arm inclined at ±62° it clears at 0.545 m and start and goal pass beneath.
Margins: the trapping band penetrates the shelf by 91.5 mm; start and goal
clear it by 83.3 mm. Ground truth with the convex-body oracle: start and goal
free; 0 free in the slab over 40 000 uniform and 448 corner-biased samples;
all 16 combinations of extreme distal-joint values in collision (the
redundancy invariance the proof will make exact); free on both sides.

*Result.* PROOF; exact verification OK; 2 leaves (both collision, none
outside); active dimensions (q_1, q_2, q_3) measured, (q_4, …, q_7) passive;
reduced LP 1 070 rows against 473 870 full (×443); certify 46.7 s (39.1 s
symbolic FK build, 1.3 s branch-and-bound, 6.3 s export), verify 2.42 s;
embedded leaves 2, re-solved 0, rejected 0; dissonance counter 0.

### 7.5 Three use cases, one robot

On the same iiwa7 chain and body, two further scenes with the same measured
mechanism and different geometry, limits, slab and claim [P2: numbers from
the two dated benchmark files]:

- **Bin picking / TAMP pruning.** A stacked euro crate (600 × 400 × 220 mm)
  whose underside at 0.720 m the upright arm strikes: the object below is
  unreachable until the crate above is removed. Joint box ±62°, δ = 3/20,
  measured window 138.7 mm placed to give +66.9 / +71.7 mm. PROOF, 2 leaves,
  verify 2.45 s. The certificate lets a task planner prune the "reach
  directly" branch with a proof rather than a timeout.
- **Safety guard.** A thin horizontal guard (50 mm, ±0.60 m wide, underside
  0.695 m) between the arm and an operator zone. Joint box ±66°, δ = 9/50,
  window 168.4 mm giving +83.1 / +85.3 mm. PROOF, 4 leaves (2 collision, 2
  outside), verify 2.54 s. The claim a safety file may carry is precisely the
  theorem: within the declared joint box, with static obstacles as declared,
  no continuous motion brings the certified body past the guard — nothing
  about dynamics, sensing or configurations outside the box.

The original bin-picking storyboard ("cross the crate wall") was abandoned
after the lever measurement showed it infeasible on the faithful body; the
stacked-crate version is what the geometry supports.

### 7.6 Summary

| Scene | DOF | active | leaves | certify | verify | ground truth |
|---|---|---|---|---|---|---|
| Planar relay (E3) | 2 | 2 | 46 | < 1 s | 0.09 s [P2] | — |
| Comb | 3 | 2 | 54 | ~1 s | 0.18 s [P2] | 0 / 300k |
| Shoulder-elbow (anchor) | 4 | 2 | 8 | 0.04 s | 0.04 s | 0 / 150k [P2] |
| iiwa-like bin | 5 | 3 | 8 | ~1 s | 0.16 s | 0 / 40k |
| iiwa7 shelf (flagship) | 7 | 3 | 2 | 46.7 s | 2.42 s | 0 / 40k + 448 |
| iiwa7 stacked crate | 7 | 3 | 2 | ~46 s | 2.45 s | 0 / 40k + 448 |
| iiwa7 safety guard | 7 | 3 | 4 | ~47 s | 2.54 s | 0 / 40k + 448 |
| Sealed wall, k = 3…7 | k | k | 2–4 | 0.1 s – 72 s | OK | 0 / 8k + corners |

All PROOF, all exactly verified, dissonance counters zero.

### 7.7 Two episodes the certifier refused

We record two occasions on which dense sampling declared a disconnection and
the certifier did not, and the certifier was right.

1. **The micro-channel (planar).** A regression scene with teeth shrunk by
   5 %: an 11³ grid finds no free sample in the slab; a denser sampling finds
   free configurations through a channel a few millimetres wide; the engine
   refuses (UNDECIDED) and never writes a certificate. The grid was fooled;
   the certifier was not. This is now a permanent test.
2. **The leaky scene (7-DOF synthetic, authored by us).** A wall-bench scene
   at five active joints whose obstacle was the bounding box of 4 000 random
   samples of the body's reach plus a margin. Ground truth: 0 free over 8 000
   uniform samples. The certifier refused, and at higher depth and full
   budget still refused. Free configurations survived in the corners of the
   joint box — the link's tip protruded 8 to 40 mm past the box — a region of
   measure too small for uniform sampling to hit. We had written a scene that
   was not disconnected and a ground truth that said it was; the tool
   believed neither. The fix — sealing the obstacle by Bernstein bounds so
   that it provably covers the reach — is what made §6.2 possible, and
   corner-biased sampling became part of every ground-truth script.

A third episode belongs to the same family though it involves no certificate:
two visualization artefacts (a figure that drew only the certified hull, a 3-D
page whose replay moved a single joint) passed every automated
fidelity check and were caught by the human validation gate. Correctness of
what is drawn and sufficiency of what is drawn are different properties; the
verifier guarantees the first for certificates, and only a person checked the
second for figures. We return to this in §9.

### 7.8 Reproducibility

The verifier, the certificates and the scene files are released with the
paper; `cnp verify <cert> <scene>` reproduces every PROOF in the tables in
exact arithmetic on a standard Python installation with no third-party
package. Generating the certificates requires the generator's dependencies
(Drake, HiGHS). Each figure's numbers are read from the dated benchmark
files, not retyped.

---

## 8. Limitations and future work

**Not measured.** Disconnections requiring many leaves at many active
dimensions — the product leaves × (d+1)^k — remain the open regime (§6.2).
Our sealed-wall family has few leaves; our real scenes have three active
dimensions. A cage or a window would test both at once.

**Geometry.** One convex hull per certified body; a full mesh would need a
convex decomposition and one pair per piece — the multi-pair machinery
exists and the per-pair reduction applies, but the leaf count is unmeasured.
Obstacles are static polytopes; dynamics, sensing and moving obstacles are
out of scope, as is wrap-around (the theorem is about a declared box within
one turn).

**Kinematics.** Serial revolute chains; prismatic joints are not handled.
Fidelity to a physical robot is bounded by the published URDF (§4).

**Barrier.** The certificates we ship use scene-provided barriers, all
linear in one joint. The automatic fitting pipeline is validated on planar
scenes only; on a passive joint it over-fits (a structured fit that zeroes
passive coefficients is the obvious next step).

**Time.** The dominant cost is now symbolic kinematics construction (39 s of
47), built twice per run; caching per scene, or Drake's rational kinematics
directly, would remove most of it. The verifier runs twice as a guard.
Single-LP size at k ≥ 8 is the frontier of the active-dimension regime;
column generation, a Kronecker-structured lazy Bernstein basis, or a
correlative-sparsity analogue of Waki et al. for Bernstein-LP are candidate
levers, the last of which is open.

**Toward cages.** A separator made of several low-dimensional slab pieces
glued by exactly certified overlaps — a slab complex — would address
disconnections a single scalar barrier cannot; conceptually it is the
triangulated separator of Li and Dantam, made exact. That is a second paper.

---

## 9. Note to reviewers

**Provenance.** This work was carried out by AI coding assistants under human
direction: the implementation by an autonomous coding agent working in
sessions from a written specification, the sessions supervised and reviewed
by a second AI system, and every gate, every scene validation, every design
decision and the go/no-go decision signed by the human author. We disclose
this for two reasons. First, because it is true. Second, because it explains
the design: the verifier is the trust anchor *precisely because* the
generation pipeline is not to be trusted — a 499-line exact program a person
can read is the only component whose correctness we ask anyone to take on
inspection, and its adversarial test suite is the evidence for that. The
episodes of §7.7 are the other half of the argument: the pipeline produced a
wrong scene and a wrong ground truth, and the artefact designed to be
independent of it caught both. Two artefacts that did lie — figures — were
caught only by the human gate; we take that as a statement about what tests
can and cannot establish, and we state the two properties (fidelity and
sufficiency) separately for that reason.

**Objections we expect.**

*"This is 3-DOF in disguise."* The theorem quantifies over the full
7-dimensional joint box; passive dimensions are covered by the proof, not
excluded from it (§4). What is 3-dimensional is the cost.

*"The scenes are chosen to work."* They are — that is §6.1, stated as scope.
The selection was also measured: on the real link, one robust proximal trap
exists, and we say so instead of dressing three scenes as three mechanisms.

*"Why not SOS?"* Because verification would then rest on a semidefinite
solver's tolerance. Linear programming over Bernstein coefficients is what
makes the verification chain exact and the verifier small.

*"The iiwa is not exact."* Correct, and neither is its URDF (§4). We certify
a rational kinematics faithful to the published description to 2·10⁻⁶ rad.

*"The speed comparison is unfair."* We make none (§6.4).

*"The proof of Theorem 1 has a boundary case."* It does not: the proof picks
a point where φ = 0, strictly inside the slab; the outside test is non-strict
and correct. An earlier draft of this paper got that wrong, and the code was
right; the fact-check against the implementation that found it is part of
how the paper was written.

---

*End of draft v0.2 — all sections present. Pending: P2 fact-check of the
§7 tables against the dated benchmark files; Figure 1 composite (produced,
S11); title; author line.*
