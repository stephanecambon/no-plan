# LEAN-NOTES — material for the paper section "A machine-checked verifier"

Written by Code (session L4, 2026-10-10) for the supervision, who writes the paper. Nothing in
this file has been put into `PAPER-DRAFT.md`.

**Status of what follows.** Facts read from the repository at commit `9f0366e`, and
measurements archived under `benchmarks/results/`. The Lean extracts and the section copied from
`lean/README.md` are inserted by script, not retyped. Statements about the implementation carry
`file:line` (A48). The timings were taken on a machine that was NOT quiet (see (d)): orders of
magnitude are safe, the last digit is not.

Contents: (a) trust base, verbatim; (b) the definitions to re-read, with what each is meant to
say; (c) what soundness depends on; (d) numbers; (e) prior work, verified.

---

## (a) Trust base — section "Trust base" of `lean/README.md`, word for word

<!-- BEGIN verbatim copy: lean/README.md, section "Trust base" -->

## Trust base

What one relies on when taking a `PROOF` printed by `cnp-verify` as a proof — and, at the end,
what is left of it for a per-scene theorem such as `wallK3_disconnected_ref`.

### Proved — checked by the Lean kernel

* **S2 `soundness_ref`** (above) and **S1 `soundness`** (the same statement on the polynomial
  pair `(N, D)` the checker computes), from: the tensor arithmetic computes the polynomial
  operations it claims (T1–T7); non-negative Bernstein coefficients imply non-negativity on the
  box (B0, B1); an accepted tiling covers the box (C1); an accepted `outside` leaf has
  `|φ| ≥ δ` on its cell (C2); an accepted `collision` leaf is in collision wherever `|φ| ≤ δ` on
  its cell (C3); the common denominator is positive (K1); the polynomial kinematics `N/D` IS the
  reference kinematics (K2, C4); the rational parametrisation `s = tan (q/2)` gives the rotation
  of angle `q` (K3), and Rodrigues' matrix is a rotation for a unit axis (K4).
* `#print axioms soundness` and `#print axioms soundness_ref`: `propext`, `Classical.choice`,
  `Quot.sound` — the three standard axioms, nothing else.
* Not among the 19, also proved: `check_eq_true_iff` (`check c = true` iff the sequence of
  checks `checkE c` succeeds, which is what the executable reports);
  `linkPose_rot_mem_specialOrthogonal` (under the kinematic check, the rotation part of the
  reference pose is in `SO(3)`); `skewR_mulVec`, `rodrigues_mulVec` (the reference rotation is
  `v ↦ v + sin · a × v + (1 - cos) · a × (a × v)`, with Mathlib's cross product).

### Defined — to be read

A proof shows that the checker agrees with the definitions the statement is written with; it
does not show that these definitions say what a roboticist means. They are short, contain no
polynomial and do not mention the checker. For `soundness_ref`:

| definition | file | what it says |
|---|---|---|
| `Certificate`, `Joint`, `Face`, `Obstacle`, `Vec3`, `Box` | `Certificate.lean`, `Kinematics.lean`, `Bernstein.lean` | the data. The statement reads `n`, `chain`, `bodyLink`, `hull`, `obstacles`, `box`, `sStart`, `sGoal` only: `φ`, `δ`, the leaves and their multipliers are the material of the proof, not part of the claim |
| `Box.toSet` | `Spec/Bernstein.lean` | `{x \| ∀ i, loᵢ ≤ xᵢ ≤ hiᵢ}` |
| `vecR` | `Spec/Kinematics.lean` | a rational vector seen in `ℝᵐ` |
| `Obstacle.toSet` | `Soundness.lean` | `{y ∈ ℝ³ \| ∀ faces, aᵀ y ≤ b}` (closed) |
| `CollisionFreeRef` | `Soundness.lean` | for every obstacle, the convex hull of the moved body vertices is disjoint from it |
| `Rigid`, `Rigid.apply`, `Rigid.comp` | `Spec/Kinematics.lean` | `y ↦ R y + t` and composition |
| `skew`, `skewR`, `rodrigues` | `Kinematics.lean`, `Spec/Kinematics.lean` | `K = [a]×` and `I + sin · K + (1 - cos) · K²` |
| `Joint.rotation` | `Spec/Kinematics.lean` | unlocked joint: `rodrigues` at `cos = (1-s²)/(1+s²)`, `sin = 2s/(1+s²)`; locked joint: at its rational `(cos, sin)` |
| `RefState`, `refStep`, `linkPose` | `Spec/Kinematics.lean` | `pose ← pose ∘ translate(offset) ∘ rotate`, along joints `0..link`; the `k`-th unlocked joint reads `s_k` |

plus Mathlib's `convexHull`, `Disjoint`, `C(unitInterval, ·)`, `Matrix` and `ℝ`. `soundness`
(S1) reads, instead of `linkPose`, the checker's own `bodyNumerators` / `bodyDenominator`
through `Tensor.eval` — which is why S2 is the statement to quote.

Things the statement says, and things it does not:

* It is a statement in **`s`-space** (`s = tan (q/2)`, as in the certificate): the path, the box,
  the start and the goal are in `s`. The translation of a path in joint angles (inside
  `(-π, π)`) into a path in `s` is not formalised. The field `q_star` does not occur in the
  statement; the checker requires it to be zero, which is what makes `s = tan (q/2)` the right
  reading of the certificate.
* It is about **one body and the listed obstacles**, exact polytopes, static. A path that is
  collision-free for the whole robot is collision-free for that body, so the conclusion
  extends to the robot; the converse is not claimed.
* **Touching is a collision** (obstacles are closed sets).
* If the start or the goal is outside the box, the statement is vacuously true.
* It is **soundness only**. Nothing says the checker accepts every true disconnection, nor
  anything about the program that produced the certificate.

### Outside the statement — trusted, not proved

* **Parsing.** The theorem is about a value of type `Certificate`. `Certificate.ofJson` (JSON
  file → `Certificate`) is ordinary unverified code; `cnp-verify --dump` prints the object that
  was actually checked. That the certificate describes the intended scene and robot (YAML
  scene, URDF) is not a matter for this checker at all.
* **Compilation and run time.** The theorem is about `check` as a Lean term. The binary is what
  the Lean compiler and the C toolchain make of it: the compiler, the run-time arithmetic
  (`Nat`, `Int`, `Rat` on GMP), `Array` and the `@[extern]` / `@[implemented_by]` replacements
  of core library functions are trusted.
* **`Main.lean`**: file reading and printing. It prints `PROOF` exactly when `checkE c`
  succeeds.
* **The proof checker itself**: the Lean 4.34.1 kernel, and Mathlib `v4.34.1` for the
  definitions of `ℝ`, continuity, convex hulls, matrices.

Agreement with `verify.py` is **measured**, not proved (section "Parity with `verify.py`").

### Per-scene theorems — what is left to trust (L4)

For `wallK3_disconnected` and `wallK3_disconnected_ref` (`Certs/Disconnected.lean`) the
hypothesis `check wallK3 = true` is proved by kernel evaluation (`Certs/WallK3Kernel.lean`), so
two items of the list above DROP OUT:

* **no compiler, no run time, no binary, no `Main.lean`**: nothing was compiled to obtain the
  statement (`#print axioms`: the three standard axioms; a `native_decide` proof would show a
  fourth);
* **no parser**: the statement is about the term `wallK3`, written out in `Certs/WallK3.lean`.

What remains: the Lean kernel and Mathlib; the reference definitions of the table above; and
reading the term `wallK3` — for the `_ref` statement, its fields `n`, `chain`, `bodyLink`,
`hull`, `obstacles`, `box`, `sStart`, `sGoal` (3 joints, 2 body vertices, one obstacle of
6 faces, a box, two points). That this term is the content of `scenes/wall/k3.cert.json` is
checked at run time (`CertTermCheck.lean`), not proved, and that the certificate describes the
intended scene is, as before, not a matter for the checker.

For the other shipped certificates the kernel evaluation does not fit in memory (table of the
section "Certificates as Lean terms"): their status is unchanged — a `PROOF` printed by the
binary, under the trust base above. The statements of `Certs/DisconnectedNative.lean` depend on
a `native_decide` axiom and are theorems MODULO THE COMPILER; they must be quoted as such.

<!-- END verbatim copy -->

---

## (b) The reference definitions to re-read

**What re-reading is for.** The kernel has checked that `check c = true` implies the statement
of `soundness_ref` *as written with the definitions below*. It cannot check that these
definitions say what the paper says: that is a reading task, and it is the only part of the
argument that is neither proved nor measured. Three things have already put the definitions
under test, none of which replaces the reading:

* K2 `body_position` proves `linkPose` = the checker's `N/D` (so an error in `linkPose` would
  have to be the SAME error as in the checker's kinematics);
* the checker's `N/D` equals `verify.py`'s on 1 299 exact rational values
  (`scripts/lean_fk_parity.py`, L3), and `verify.py`'s chain was matched to Drake to 2·10⁻⁶ m
  (S10-bis; cited, not re-measured since);
* `skewR_mulVec`, `rodrigues_mulVec`, `rodrigues_mulVec_axis`, K3 and K4 (below) relate the
  hand-written sign table and Rodrigues' matrix to Mathlib's cross product and `SO(3)`.

Each definition comes with the sentence it is meant to formalise and the section of the paper it
corresponds to.

### (b1) The data a certificate declares — paper §3.1 and the hypotheses of Theorem 1 (§4)

`lean/CnpVerify/Kinematics.lean:17`

```lean
/-- A rational vector of `ℝ³` (`v[i]`, `i : Fin 3`). -/
abbrev Vec3 := Vector Rat 3
```

A point or a direction of ℝ³ with rational coordinates.

`lean/CnpVerify/Kinematics.lean:20`

```lean
/-- One revolute joint of the serial chain. `offset` is the translation from the previous joint
frame, `axis` the rotation axis (required to be an exact unit vector by the checker). A locked
joint carries the exact rational `(cos, sin)` of its fixed angle and takes no variable. -/
structure Joint where
  offset : Vec3
  axis : Vec3
  locked : Option (Rat × Rat)
```

One revolute joint: where its frame sits in the previous one (`offset`), the axis it turns about
(`axis`), and — if it is locked — the rational cosine and sine of its fixed angle.

`lean/CnpVerify/Certificate.lean:29`

```lean
/-- One face `aᵀ y ≤ b` of an obstacle. -/
structure Face where
  a : Vec3
  b : Rat
```

`lean/CnpVerify/Certificate.lean:34`

```lean
/-- A static obstacle in H-representation: `{y ∈ ℝ³ | ∀ faces, aᵀ y ≤ b}`. -/
structure Obstacle where
  name : String
  faces : Array Face
```

A static obstacle as a finite intersection of closed half-spaces.

`lean/CnpVerify/Bernstein.lean:20`

```lean
/-- A box `∏ᵢ [loᵢ, hiᵢ]` of `ℚⁿ`, as `n` pairs `(lo, hi)`. -/
abbrev Box (n : Nat) := Vector (Rat × Rat) n
```

A box of ℚⁿ, one interval `(lo, hi)` per variable.

`lean/CnpVerify/Certificate.lean:52`

```lean
/-- A disconnection certificate (SPEC §4), in exact rationals. -/
structure Certificate where
  /-- Number of unlocked joints = number of variables `s₀..s_{n-1}`. -/
  n : Nat
  /-- The serial chain, all joints in order (locked ones included). -/
  chain : Array Joint
  /-- Reference configuration of the unlocked joints; the checker requires it to be zero. -/
  qStar : Array Rat
  /-- Index (in `chain`) of the link carrying the certified body. -/
  bodyLink : Nat
  /-- Vertices of the certified body (a convex polytope), in the frame of `bodyLink`. -/
  hull : Array Vec3
  /-- The obstacles, by name. -/
  obstacles : Array Obstacle
  /-- The barrier polynomial `φ`. -/
  phi : Tensor n
  /-- DECLARED per-variable degree of `φ` (fixes the Bernstein degrees). -/
  phiDeg : Nat
  /-- Half-width `δ` of the slab `{|φ| ≤ δ}`. -/
  delta : Rat
  /-- The joint box `P` in `s`-space. -/
  box : Box n
  /-- Start and goal configurations in `s`-space. -/
  sStart : Vector Rat n
  sGoal : Vector Rat n
  /-- Per-variable degree of the multipliers `λ_k` (`const` 0, `affine` 1, `quadratic` 2);
  `none` when the field is absent or unknown. -/
  lamDeg : Option Nat
  /-- The leaves, in file order. -/
  leaves : Array (Leaf n)
```

The certificate. **`soundness_ref` reads eight of these fields only**: `n`, `chain`, `bodyLink`,
`hull`, `obstacles`, `box`, `sStart`, `sGoal`. `qStar`, `phi`, `phiDeg`, `delta`, `lamDeg` and
`leaves` occur in `check`, hence in the hypothesis, and nowhere in the conclusion: they are the
material of the proof, not part of the claim.

Points to check against the paper:

* ONE body per certificate (`bodyLink`, `hull`; `verify.py:473-476` reads `cert["body"]` once).
  Theorem 1 of the draft says "certified bodies … on named links" (plural): the Lean statement,
  like the certificate format, is about one body and all the listed obstacles.
* `chain` holds ALL the joints, locked ones included; `n` counts the unlocked ones, numbered
  `0..n-1` in chain order.

### (b2) Sets and collision — paper §3.1

`lean/CnpVerify/Spec/Bernstein.lean:22`

```lean
/-- The box as a subset of `ℝⁿ`: `{x | ∀ i, loᵢ ≤ xᵢ ≤ hiᵢ}`. -/
def Box.toSet (b : Box n) : Set (Fin n → ℝ) :=
  {x | ∀ i : Fin n, (b.lo i : ℝ) ≤ x i ∧ x i ≤ (b.hi i : ℝ)}
```

The closed box of ℝⁿ: every coordinate between its two bounds, bounds included. (The paper's
joint box `P`, in `s`-coordinates.)

`lean/CnpVerify/Spec/Kinematics.lean:17`

```lean
/-- A rational vector seen in `ℝᵐ`. -/
def vecR {m : ℕ} (v : Vector ℚ m) : Fin m → ℝ := fun i => (v[i] : ℝ)
```

A rational vector read as a real one, coordinate by coordinate.

`lean/CnpVerify/Soundness.lean:22`

```lean
/-- The obstacle as a subset of `ℝ³`: the points satisfying every face inequality `aᵀ y ≤ b`. -/
def Obstacle.toSet (O : Obstacle) : Set (Fin 3 → ℝ) :=
  {y | ∀ f ∈ O.faces, ∑ i : Fin 3, (f.a[i] : ℝ) * y i ≤ (f.b : ℝ)}
```

The obstacle as a subset of ℝ³: the points satisfying every face inequality. It is CLOSED:
touching an obstacle counts as a collision.

`lean/CnpVerify/Soundness.lean:42`

```lean
/-- Collision-freeness stated on the REFERENCE kinematics (`linkPose`: real rigid motions, no
polynomial): the convex hull of the moved body vertices meets no obstacle. -/
def CollisionFreeRef (c : Certificate) (s : Fin c.n → ℝ) : Prop :=
  ∀ O ∈ c.obstacles,
    Disjoint
      (convexHull ℝ (Set.range fun k : Fin c.hull.size =>
        (linkPose c.chain c.bodyLink s).apply (vecR c.hull[k])))
      O.toSet
```

The configuration `s` is collision-free: for every obstacle of the certificate, the convex hull
of the body vertices — each moved by the rigid motion of the body's link at `s` — does not meet
the obstacle. (The paper's `s ∉ C_obs`, for the certified body.)

Points to check: the body is the CONVEX HULL of the listed vertices (Mathlib's `convexHull ℝ`);
the quantifier is over the obstacles of the certificate, not over those a leaf names; `Disjoint`
on sets means empty intersection.

### (b3) Forward kinematics — paper §3.2

`lean/CnpVerify/Kinematics.lean:50`

```lean
/-- Cross-product matrix `K` of `a`: `K v = a × v`. -/
def skew (a : Vec3) (i j : Fin 3) : Rat :=
  match i.val, j.val with
  | 0, 1 => -a[2]
  | 0, 2 => a[1]
  | 1, 0 => a[2]
  | 1, 2 => -a[0]
  | 2, 0 => -a[1]
  | 2, 1 => a[0]
  | _, _ => 0
```

The matrix `K = [a]×` such that `K v = a × v`, written as a table of signs. This table is shared
by the checker and by the reference; `skewR_mulVec` proves it is Mathlib's cross product.

`lean/CnpVerify/Spec/Kinematics.lean:20`

```lean
/-- The cross-product matrix of `a` over `ℝ`. -/
def skewR (a : Vec3) : Matrix (Fin 3) (Fin 3) ℝ := Matrix.of fun i j => (skew a i j : ℝ)
```

`lean/CnpVerify/Spec/Kinematics.lean:23`

```lean
/-- Rodrigues' formula `I + sin·K + (1 - cos)·K²`: for a unit axis `a` and
`cos² + sin² = 1`, the rotation about `a` by the angle of cosine `co` and sine `si`. -/
def rodrigues (a : Vec3) (co si : ℝ) : Matrix (Fin 3) (Fin 3) ℝ :=
  1 + si • skewR a + (1 - co) • (skewR a * skewR a)
```

Rodrigues' rotation matrix `I + sin·K + (1 − cos)·K²` for an axis `a`, a cosine and a sine.

`lean/CnpVerify/Spec/Kinematics.lean:28`

```lean
/-- Rotation of a joint. Unlocked: angle `q` with `s = tan (q/2)`. Locked: the fixed rational
`(cos, sin)` (the value of `s` is ignored). -/
noncomputable def Joint.rotation (j : Joint) (s : ℝ) : Matrix (Fin 3) (Fin 3) ℝ :=
  match j.locked with
  | none => rodrigues j.axis ((1 - s ^ 2) / (1 + s ^ 2)) (2 * s / (1 + s ^ 2))
  | some (co, si) => rodrigues j.axis (co : ℝ) (si : ℝ)
```

The rotation of a joint at the value `s` of its variable. Unlocked: the rotation of angle `q`
about the axis, with `s = tan(q/2)`, written through `cos q = (1 − s²)/(1 + s²)` and
`sin q = 2s/(1 + s²)`. Locked: the rotation of the declared rational `(cos, sin)`.

`lean/CnpVerify/Spec/Kinematics.lean:35`

```lean
/-- A rigid motion `y ↦ R y + t` of `ℝ³`. -/
structure Rigid where
  rot : Matrix (Fin 3) (Fin 3) ℝ
  trans : Fin 3 → ℝ
```

`lean/CnpVerify/Spec/Kinematics.lean:40`

```lean
/-- Action on a point. -/
def Rigid.apply (g : Rigid) (y : Fin 3 → ℝ) : Fin 3 → ℝ := g.rot.mulVec y + g.trans
```

`lean/CnpVerify/Spec/Kinematics.lean:43`

```lean
/-- `g.comp h` is "`h` first, then `g`". -/
def Rigid.comp (g h : Rigid) : Rigid := ⟨g.rot * h.rot, g.rot.mulVec h.trans + g.trans⟩
```

A rigid motion `y ↦ R y + t`, its action on a point, and composition (`g.comp h`: `h` first).

`lean/CnpVerify/Spec/Kinematics.lean:46`

```lean
/-- Accumulation state of the reference chain: pose so far, next free variable. -/
structure RefState where
  pose : Rigid
  nextVar : ℕ
```

`lean/CnpVerify/Spec/Kinematics.lean:51`

```lean
/-- One joint: `pose ← pose ∘ translate(offset) ∘ rotate`. An unlocked joint reads the next
variable (a variable index `≥ n` reads `0`; the checker excludes that case). -/
noncomputable def refStep {n : ℕ} (s : Fin n → ℝ) (st : RefState) (j : Joint) : RefState :=
  let sVal : ℝ := if h : st.nextVar < n then s ⟨st.nextVar, h⟩ else 0
  let pose := st.pose.comp ⟨j.rotation sVal, vecR j.offset⟩
  match j.locked with
  | none => ⟨pose, st.nextVar + 1⟩
  | some _ => ⟨pose, st.nextVar⟩
```

One joint of the chain: the pose so far is composed, on the right, with "translate by the
joint's offset, then rotate about its axis" — `pose ← pose ∘ translate(offset) ∘ rotate`. An
unlocked joint consumes the next variable; a locked one consumes none.

`lean/CnpVerify/Spec/Kinematics.lean:60`

```lean
/-- Reference world pose of link `link` at the configuration `s` (unlocked joints numbered
`0..n-1` in chain order): the composition of the joint motions `0..link`. -/
noncomputable def linkPose {n : ℕ} (chain : Array Joint) (link : ℕ) (s : Fin n → ℝ) : Rigid :=
  ((chain.extract 0 (link + 1)).foldl (refStep s) ⟨⟨1, 0⟩, 0⟩).pose
```

The pose of link `link` in the world frame at the configuration `s`: the composition of the
joint motions `0, 1, …, link` (inclusive), starting from the identity.

`lean/CnpVerify/Spec/Kinematics.lean:65`

```lean
/-- Number of unlocked joints among joints `0..link`. -/
def unlockedUpTo (chain : Array Joint) (link : ℕ) : ℕ :=
  ((chain.extract 0 (link + 1)).filter (·.locked.isNone)).size
```

(Used by K2 only: the hypothesis "the chain up to the body's link has at most `n` unlocked
joints".)

Conventions to check against §3.2 and against `verify.py:171-219, 261-275`:

1. `skew`: signs of the six off-diagonal entries (`K v = a × v`, right-handed).
2. `rodrigues`: `+ sin · K` (counter-clockwise about `a` for a positive angle), `(1 − cos) · K²`.
3. `Joint.rotation`: the half-angle formulas, and that the LOCKED case ignores `s`.
4. `Rigid.comp`: rotation `g.rot * h.rot`, translation `g.rot · h.trans + g.trans`.
5. `refStep`: the joint motion is `⟨rotation, offset⟩`, i.e. `y ↦ R y + offset` — rotate in the
   joint frame, then place that frame at `offset` in the previous one; composed on the RIGHT of
   the pose so far.
6. `linkPose`: joints `0..link` INCLUSIVE (`extract 0 (link + 1)`), initial pose the identity.
7. Variable numbering: the `k`-th unlocked joint of the chain reads `s_k`.

Proved facts that reduce what has to be taken on reading (all with the three standard axioms):

* `skewR_mulVec` — `(skewR a).mulVec v = vecR a ⨯₃ v`;
* `rodrigues_mulVec` — `R v = v + sin • (a × v) + (1 − cos) • a × (a × v)`;
* `rodrigues_mulVec_axis` — the axis is fixed;
* K3 `rotation_half_angle` — for `|q| < π`, `rodrigues a ((1 − t²)/(1 + t²)) (2t/(1 + t²))` with
  `t = tan(q/2)` equals `rodrigues a (cos q) (sin q)`: the rational parametrisation is the
  rotation of angle `q`;
* K4 `rodrigues_mem_specialOrthogonal` — for a unit axis and `cos² + sin² = 1`, `rodrigues` is
  in `SO(3)`;
* `linkPose_rot_mem_specialOrthogonal` — under the kinematic check, the rotation part of
  `linkPose c.chain c.bodyLink s` is in `SO(3)`.

What is NOT formalised here, to say in the paper: the change of variable from joint angles
`q ∈ (−π, π)` to `s = tan(q/2)` for a PATH (the theorem is stated in `s`-space, like the
certificate), and the correspondence between the declared chain and the physical robot.

### (b4) The theorem — paper §4

`lean/CnpVerify/Soundness.lean:610`

```lean
theorem soundness_ref (c : Certificate) :
    check c = true →
      ¬ ∃ γ : C(unitInterval, Fin c.n → ℝ),
          (∀ t, γ t ∈ c.box.toSet) ∧ γ 0 = vecR c.sStart ∧ γ 1 = vecR c.sGoal
            ∧ ∀ t, CollisionFreeRef c (γ t) := by
```

**S2, the statement to cite.** If the checker accepts the certificate, there is no continuous
map `γ : [0,1] → ℝⁿ` with values in the box, starting at `s_start`, ending at `s_goal`, along
which the body moved by the reference kinematics stays disjoint from every obstacle.

`lean/CnpVerify/Soundness.lean:576`

```lean
theorem soundness (c : Certificate) :
    check c = true →
      ¬ ∃ γ : C(unitInterval, Fin c.n → ℝ),
          (∀ t, γ t ∈ c.box.toSet) ∧ γ 0 = vecR c.sStart ∧ γ 1 = vecR c.sGoal
            ∧ ∀ t, CollisionFree c (γ t) := by
```

**S1, the technical core**: the same statement with the body placed by the checker's own
polynomials. It needs three more definitions:

`lean/CnpVerify/Spec/Tensor.lean:23`

```lean
/-- The real number denoted by the tensor `t` at the point `x`:
`Σ_e coeff(e) · ∏ᵢ xᵢ^eᵢ`, the sum ranging over all exponent vectors `e ∈ {0..deg}ⁿ`. -/
noncomputable def eval (t : Tensor n) (x : Fin n → ℝ) : ℝ :=
  ∑ e : Fin n → Fin (t.deg + 1), (t.coeff (fun i => (e i).val) : ℝ) * ∏ i, x i ^ (e i).val
```

`lean/CnpVerify/Soundness.lean:26`

```lean
/-- World position of the `k`-th vertex of the certified body at the configuration `s`:
`eval (N_k) / eval D`, with `N_k` and `D` the kinematic numerators and the common denominator
of the body's link, computed from the declared chain. -/
noncomputable def Certificate.worldVertex (c : Certificate) (k : Fin c.hull.size)
    (s : Fin c.n → ℝ) : Fin 3 → ℝ :=
  fun i => ((bodyNumerators c.n c.chain c.bodyLink c.hull[k])[i]).eval s
    / (bodyDenominator c.n c.chain c.bodyLink).eval s
```

`lean/CnpVerify/Soundness.lean:34`

```lean
/-- The certified body at the configuration `s`: the convex hull of its world vertices. -/
noncomputable def Certificate.bodyAt (c : Certificate) (s : Fin c.n → ℝ) : Set (Fin 3 → ℝ) :=
  convexHull ℝ (Set.range fun k : Fin c.hull.size => c.worldVertex k s)
```

`lean/CnpVerify/Soundness.lean:38`

```lean
/-- The configuration `s` is collision-free: the certified body meets no obstacle. -/
def CollisionFree (c : Certificate) (s : Fin c.n → ℝ) : Prop :=
  ∀ O ∈ c.obstacles, Disjoint (c.bodyAt s) O.toSet
```

(`Tensor.eval`: the polynomial function of a coefficient tensor; `worldVertex`: `N_k(s)/D(s)`;
`bodyAt`: the convex hull of the world vertices.) S2 follows from S1 and C4
`collisionFree_iff_ref`, itself from K2.

**The per-scene statement (L4)** — `lean/Certs/Disconnected.lean`:

`lean/Certs/Disconnected.lean:30`

```lean
/-- **The scene `wall/k3` is disconnected, on the reference kinematics** (statement of S2: the
body is moved by the real rigid motions `linkPose` of the declared chain). This is the
statement to cite. -/
theorem wallK3_disconnected_ref :
    ¬ ∃ γ : C(unitInterval, Fin wallK3.n → ℝ),
        (∀ t, γ t ∈ wallK3.box.toSet) ∧ γ 0 = vecR wallK3.sStart ∧ γ 1 = vecR wallK3.sGoal
          ∧ ∀ t, CollisionFreeRef wallK3 (γ t) :=
  soundness_ref wallK3 wallK3_proof
```

with `wallK3` the term of `lean/Certs/WallK3.lean` (generated from
`scenes/wall/k3.cert.json`). Its eight fields read by the statement:

`lean/Certs/WallK3.lean:15`

```lean
def wallK3 : Certificate where
  n := 3
  chain := #[
    { offset := #v[0, 0, 0], axis := #v[0, 0, 1], locked := none },
    { offset := #v[(2 : Rat) / 5, 0, 0], axis := #v[0, 1, 0], locked := none },
    { offset := #v[(2 : Rat) / 5, 0, 0], axis := #v[0, 0, 1], locked := none }]
  qStar := #[0, 0, 0]
  bodyLink := 2
  hull := #[
    #v[0, 0, 0],
    #v[(2 : Rat) / 5, 0, 0]]
  obstacles := #[
    { name := "WALL", faces := #[
        { a := #v[1, 0, 0], b := (315131 : Rat) / 222750 },
        { a := #v[0, 1, 0], b := (116591 : Rat) / 257550 },
        { a := #v[0, 0, 1], b := (43 : Rat) / 102 },
        { a := #v[(-1), 0, 0], b := (-61643 : Rat) / 85850 },
        { a := #v[0, (-1), 0], b := (116591 : Rat) / 257550 },
        { a := #v[0, 0, (-1)], b := (43 : Rat) / 102 }] }]
```

```lean
  box := #v[((-4 : Rat) / 5, (4 : Rat) / 5), ((-1 : Rat) / 4, (1 : Rat) / 4), ((-1 : Rat) / 4, (1 : Rat) / 4)]
  sStart := #v[(-3 : Rat) / 4, 0, 0]
  sGoal := #v[(3 : Rat) / 4, 0, 0]
```

In words: a 3R arm — base yaw about `z`, a pitch about `y` at `(2/5, 0, 0)`, a yaw about `z` at
`(2/5, 0, 0)` of the second frame — whose last link carries a segment of length `2/5`; one
box-shaped obstacle; joint box `s₀ ∈ [−4/5, 4/5]`, `s₁, s₂ ∈ [−1/4, 1/4]` (`q = 2·arctan s`:
about ±77.3° and ±28.1°); start `s = (−3/4, 0, 0)`, goal `s = (3/4, 0, 0)`.

**Differences between Theorem 1 of the draft and what Lean states** (for the wording of §4/§5):

| Theorem 1 (draft §4) | Lean (`soundness_ref`) |
|---|---|
| hypotheses (i)–(iv) listed | one hypothesis: `check c = true`; `check` tests (i)–(iv) and more, see (c) |
| "certified bodies … on named links" | one body (`hull` on `bodyLink`) |
| "rational unit axes", locked joints with `cos² + sin² = 1` | tested by `check`, NOT used by the proof of the conclusion; they make the motions rotations (`linkPose_rot_mem_specialOrthogonal`) |
| (ii) tiling "with no gap and no overlap" | the proof uses coverage only (C1 `verifyCover_covers`) |
| path in `P` | `γ : C(unitInterval, Fin c.n → ℝ)` with `∀ t, γ t ∈ c.box.toSet`, in `s`-space |
| proof: IVT on `φ∘γ`, the leaf of `s*` | the same argument, `intermediate_value_univ` on the connected space `[0,1]` |

---

## (c) What soundness depends on

The mechanised proof says which tests of the checker the theorem needs (A53). Lemma names are
those of `lean/CnpVerify/Soundness.lean` and `lean/CnpVerify/Spec/*.lean`; every one of them was
audited by `scripts/lean_axioms.py` (three standard axioms).

| # | finding | where it is visible |
|---|---|---|
| 1 | **S1 does not use the kinematic check (0') at all.** The proof discards its result. S1 is about the pair `(N, D)` recomputed from the chain, whatever the chain is. | `soundness`: `obtain ⟨-, hL⟩ := checkM_seq_ok _ _ hE` (the `-` is `checkKinematics c = .ok ()`). Lemmas used: `checkAssumptions_ok` (δ > 0), `checkConditionI_ok` (i), `checkPartition_ok` ← C1 `verifyCover_covers` (ii), `checkLeaves_ok`, C2 `checkOutsideLeaf_sound` (iii), C3 `checkCollisionLeaf_sound` (iv) ← K1 `bodyDenominator_pos`, B1 `bernstein_nonneg` (through `bernNonneg_sound`), T1–T7; `Tensor.continuous_eval`; Mathlib `intermediate_value_univ`. |
| 2 | **S2 uses ONE fact of (0'): `n` is the number of unlocked joints.** Exact unit axes and `cos² + sin² = 1` are conditions of MEANING — they make `linkPose` a chain of rotations — not conditions of soundness: without them S2 would still be a true statement, about maps that are no longer rigid motions. | `soundness_ref` ← C4 `collisionFree_iff_ref` ← K2 `body_position`, whose only hypothesis is `unlockedUpTo chain link ≤ n` (from `checkKinematics_ok` and `unlockedUpTo_le`). Unit axes and locks are used by `Joint.rotation_mem_specialOrthogonal`, `linkPose_rot_mem_specialOrthogonal` ← K4 `rodrigues_mem_specialOrthogonal`. |
| 3 | **`q* = 0` is outside the formal statement.** No statement reads `Certificate.qStar`. The test guarantees that `s = tan(q/2)` is the right reading of the certificate: it belongs to the correspondence certificate ↔ robot. | `checkKinematics` tests `c.qStar.any (· != 0)` (`Check.lean`); `checkKinematics_ok` does not export it. |
| 4 | **Tests of the checker that no proof uses** — consistency with the generator, not soundness: non-degeneracy of the box (0); disjointness of the cells and the VALUE of the cut, the midpoint (ii); the degree test on `λ_k` and the count of the `μ_j` (iv) — a missing `μ_j` is read as `0`, i.e. `g_j ≥ 0` is then required outright; "the body's link is in the chain" (0'). | C1 `verifyCover_covers` concludes coverage only; `checkCollisionLeaf_sound` uses `mu.getD j 0` and never `lam[k].deg`. Full table: `lean/PROOF-OBLIGATIONS.md`, "Which tests of the checker the proofs use". |
| 5 | **S2 reads `n`, `chain`, `bodyLink`, `hull`, `obstacles`, `box`, `sStart`, `sGoal` only** — neither `φ`, nor `δ`, nor a leaf, nor a tensor appears in the conclusion. | statement of `soundness_ref`; `CollisionFreeRef` |
| 6 | **The hand-written sign table `skew` is Mathlib's cross product, and `rodrigues` is the usual formula; the axis is fixed.** | `skewR_mulVec`, `rodrigues_mulVec`, `rodrigues_mulVec_axis` |

Carried over from L2 (decision 3 of the L2 review): **the value of the cut does not enter the
soundness of the coverage** — the midpoint is what lets the verifier RECONSTRUCT the engine's
tiling, not what the proof needs (contract A14 is practical, not soundness-critical).

New in L4 — the gap between the theorem and the program, measured:

| # | finding | where it is visible |
|---|---|---|
| 7 | **For one shipped scene the hypothesis `check c = true` is itself proved by the kernel**, so its disconnection is a theorem of Lean/Mathlib with the three standard axioms: no compiler, no binary, no JSON parser. | `Certs.wallK3_proof`, `Certs.wallK3_disconnected_ref`; `scripts/lean_axioms.py` |
| 8 | **`by decide` cannot do it, whatever the limits**: the elaborator is blocked by `@[irreducible]` core definitions (`Rat.mul`, `Rat.inv`, `Rat.add`, `Rat.sub`, `Init/Data/Rat/Basic.lean:168, 191, 259, 295`) on the very first test, `δ > 0`. It is a transparency block, not a resource limit. | bench, column `decide` |
| 9 | **`by decide +kernel` in one evaluation exhausts memory on the smallest certificate.** The kernel has no arrays: an `Array` is a list, and the checker's array operations are quadratic there. | bench, column "one evaluation"; table of array operations in (d) |
| 10 | **Cutting the evaluation into stages makes it fit** — each stage is a kernel evaluation with its own memory; the stages are glued by lemmas (`check_of_stages`, `checkLeaf_collision_of`) that are the converse of the unpacking lemmas of L3. The intermediate values are computed by compiled code and are not trusted: each is tied to the checker by an equation the kernel evaluates. | `lean/Certs/Staged.lean`, `lean/Certs/WallK3Kernel.lean` |
| 11 | **It does not scale as is**: cutting finer would not carry it further. On the 4-DOF certificate three kinds of stage each exceed 9 GiB taken alone on literal inputs — the kinematics, the witness numerator, and ONE face, i.e. a single Bernstein test on 5⁴ = 625 coefficients. On the 7-DOF flagship a single polynomial product (`δ² − φ²`) exceeds 9 GiB, and the intermediate values cannot even be written as a term within default limits (262 440 coefficients for the kinematics). The cause is measured: the array operations the checker is written with are quadratic in the kernel — ×25 to ×30 from 125 to 625 entries, against ×5 for a `for` loop or a list fold. Carrying the flagship to the status of `wall/k3` needs a different object: a twin of the checker written for the kernel and PROVED equal to `check` (not attempted). | bench |
| 12 | **`native_decide` is the compiler in the trust base, visibly**: each use adds an axiom `<theorem>._native.native_decide.ax_…` (Lean 4.34; `Lean/Meta/Native.lean`), and here the "native" evaluation is the IR interpreter. The audit refuses such an axiom on a statement meant to be kernel-checked, and requires it on a `…_native` one. | `Certs/Native.lean`, `Certs/DisconnectedNative.lean`, `scripts/lean_axioms.py` |
| 13 | **The JSON parser cannot be evaluated in the kernel** (`Lean.Json.parse` is `partial`: `Lean/Data/Json/Parser.lean`); a per-scene theorem does not need it — it is about the term. That the term is the file's content is checked at run time by two independent readers (`scripts/cert_to_lean.py`, `Certificate.ofJson`), with a negative control. | `lean/CertTermCheck.lean`, `lean/check_certs.sh` |

Suggested sentence for the paper, with its exact scope: *"For the scene `wall/k3` (3 joints,
two leaves) the disconnection is a theorem of Lean 4/Mathlib: the checker's acceptance is
established by evaluation in the Lean kernel, and the statement depends on no axiom beyond
`propext`, `Classical.choice` and `Quot.sound`. For the other certificates, including the 7-DOF
flagship, acceptance is established by the compiled checker; the kernel evaluation of the
unmodified checker does not fit in memory."*

---

## (d) Numbers

**Versions.** Lean 4.34.1 (`lean/lean-toolchain`), Lake 5.0.0, Mathlib tag `v4.34.1` (commit
`d13f23b7…`, `lean/lake-manifest.json`).

**Size** (lines counted with `grep -c ""`, theorems with `^theorem`):

| part | files | lines | theorems |
|---|---|---|---|
| executable core (`Tensor`, `Bernstein`, `Kinematics`, `Certificate`, `Check`, `Main`) — what the binary is made of; unchanged since L1 except two comment lines (L4) | 6 | 1 087 | — |
| proof layer (`Spec/Index`, `Spec/Tensor`, `Spec/Bernstein`, `Spec/Kinematics`, `Soundness`) | 5 | 2 501 | 145, of which the 19 obligations; 0 `sorry` |
| staging lemmas (`Certs/Staged.lean`), core Lean only | 1 | 210 | 8 |
| staged kernel proof of `check wallK3 = true` (`Certs/WallK3Kernel.lean`, generated) | 1 | 241 | 39 (34 kernel evaluations, 5 assembly) |
| per-scene statements (`Certs/Disconnected.lean`) | 1 | 39 | 2 |
| `native_decide` counterparts (`Certs/Native.lean`, `Certs/DisconnectedNative.lean`) | 2 | 62 | 5 |

**Axioms** (`scripts/lean_axioms.py`, asserted): the 19 obligations, 8 cited lemmas, the 3
staging lemmas, `wallK3_proof`, `wallK3_disconnected`, `wallK3_disconnected_ref` — `propext`,
`Classical.choice`, `Quot.sound` (`binom_eq_choose`: `propext` only). The 5 `…_native`
statements: the same three plus one `native_decide` axiom each.

**Kernel evaluation** — `scripts/lean_kernel_bench.py`, one process per attempt, killed beyond
9 GiB of resident memory (1 GiB = 2³⁰ bytes; no attempt reached the time limit). Three archived
runs under `benchmarks/results/`: `20261010T163223Z` (rows k3 and S3 — its S6 rows are
superseded, see the note under the table), `20261010T171636Z` (row S6), `20261010T172639Z`
(array operations). Machine: Apple M4, 24 GB, macOS 26.5; **not quiet** — a game was running on
two of the ten cores during the whole session, load average 4 to 11. To be replayed on a quiet
machine (`make lean-kernel-bench`) before any figure is quoted.

| certificate | n | leaves (collision / outside) | body vertices | `by decide` | `by decide +kernel`, one evaluation | staged kernel proof | `by native_decide` (one axiom more) |
|---|---|---|---|---|---|---|---|
| `scenes/wall/k3.cert.json` | 3 | 2 (2 / 0) | 2 | FAIL at once (stuck on `Rat.blt 0 c.delta`) | FAIL — killed above 9 GiB after 53 s | **proved** — 34 stages, 277–359 s for the file (three runs), peak 5.6 GiB | 2.6 s (evaluation 0.14 s) |
| `scenes/S3_shoulder_elbow.cert.json` | 4 | 8 (4 / 4) | 2 | FAIL at once (stuck on `Rat.blt 0 c.delta`) | FAIL — killed above 9 GiB after 51 s | FAIL — three kinds of stage each exceed 9 GiB: kinematics (after 50 s), witness numerator (53 s), one face (41 s); an outside leaf passes (9 s, 2.2 GiB) | 1.1 s (evaluation 0.19 s) |
| `scenes/S6_iiwa_real_shelf.cert.json` | 7 | 2 (2 / 0) | 40 | FAIL at once (stuck on `Rat.blt 0 c.delta`) | FAIL — killed above 9 GiB after 48 s | FAIL — the staged proof cannot even be written: its literal `G` (262 440 coefficients) does not get through the elaborator, and stages that need no literal already exceed 9 GiB (`δ² − φ²` alone, after 48 s; `Σλ ≡ 1`; `λ_k ≥ 0`); the four global checks pass | 26.3 s (evaluation 24.00 s) |

Note on S6. In the first run every S6 probe was compiled with the whole preamble of the staged
proof, hence with the literal `G`, and failed on it; the bench was fixed (a probe includes only
the literals its statement mentions) and S6 replayed. The four global checks of S6 pass in the
kernel; `native_decide` evaluates the whole check in 24 s.

The file `Certs/WallK3Kernel.lean` was built three times: 277 s, 294 s and 359 s (the third
while another check was running), peak 5.6 GiB each time. The compiled binary answers in 28 ms
on the same certificate (9 ms on a quiet machine, L3).

Stages of the proof of `check wallK3 = true`, one process each (first run):

| stage | kernel s | peak GiB |
|---|---|---|
| `assumptions` | 0.0 | 1.1 |
| `conditionI` | 0.0 | 1.1 |
| `partition` | 0.0 | 1.1 |
| `kinematics` | 0.0 | 1.1 |
| `geometry_eq` | 37.4 | 5.6 |
| `slab_eq` | 0.4 | 1.1 |
| `lamDeg_eq` | 0.0 | 1.1 |
| `leaves_size` | 0.0 | 1.1 |
| `L0_X` | 10.9 | 2.6 |
| `L0_count` | 0.0 | 1.1 |
| `L0_sum` | 0.2 | 1.1 |
| `L0_lam` | 0.3 | 1.1 |
| `L0_obs` | 0.0 | 1.1 |
| `L0_mu` | 0.0 | 1.1 |
| `O0_faces` | 0.0 | 1.1 |
| `L0_face0` | 24.8 | 3.8 |
| `L0_face1` | 22.5 | 3.8 |
| `L0_face2` | 18.4 | 3.3 |
| `L0_face3` | 23.8 | 3.8 |
| `L0_face4` | 23.6 | 3.8 |
| `L0_face5` | 19.0 | 3.3 |
| `L1_X` | 13.4 | 2.6 |
| `L1_count` | 0.0 | 1.1 |
| `L1_sum` | 0.2 | 1.1 |
| `L1_lam` | 0.3 | 1.1 |
| `L1_obs` | 0.0 | 1.1 |
| `L1_mu` | 0.0 | 1.1 |
| `O1_faces` | 0.0 | 1.1 |
| `L1_face0` | 24.6 | 4.0 |
| `L1_face1` | 23.4 | 3.9 |
| `L1_face2` | 18.1 | 3.3 |
| `L1_face3` | 27.8 | 4.0 |
| `L1_face4` | 25.5 | 3.8 |
| `L1_face5` | 19.7 | 3.3 |

What the kernel pays for the array operations the checker is written with — `by decide +kernel` on one operation over an array of N naturals, kernel seconds (third run):

| operation | N = 125 | N = 625 | ratio |
|---|---|---|---|
| `for i in [0:N] (sum)` | 0.026 s | 0.157 s | ×6 |
| `List.range N |>.foldl` | 0.011 s | 0.055 s | ×5 |
| `Array.set! then getD` | 0.046 s | 0.228 s | ×5 |
| `Array.foldl` | 0.793 s | 21.800 s | ×27 |
| `Array.all` | 0.843 s | 21.200 s | ×25 |
| `Array.map` | 0.478 s | 12.800 s | ×27 |
| `Array.ofFn` | 0.482 s | 12.200 s | ×25 |
| `Array ==` | 1.560 s | 44.600 s | ×29 |
| `Array ++` | 1.300 s | 38.500 s | ×30 |

**Agreement with `verify.py`** (measured, not proved): `ARCHIVE=1 make lean-parity`, archived run `benchmarks/results/20261010T173121Z/lean_parity.log` (commit `9f0366e`, clean tree): 13 shipped certificates, PROOF on both sides; adversarial corpus, 43 rejected + 5 accepted, same verdict and same reason; seeded differential fuzz, 1 000 cases: 498 PROOF on both sides, 487 REJECT on both sides, 15 where Python raises and Lean rejects, 0 verdict divergence. The binary is byte-identical to the one of L1 (the two comment edits did not change the generated C). Forward kinematics: Lean `N/D` = `verify.py`'s on 1 299 exact rational values (`scripts/lean_fk_parity.py`, replayed in L4).

**CI** (`.github/workflows/lean.yml`): written and rehearsed locally (the Python side without Drake); its duration on GitHub is measured after the closing push and recorded in `JOURNAL.md`, addendum to the L4 entry.

---

## (e) Prior work — A28 verification pass (2026-10-10)

Bibliographic data read on primary sources (Crossref and DOI records, Springer's citation
export, arXiv, the journal's page, the authors' pages) by a research sub-agent of this session;
items marked ✔ were re-opened by Code itself (arXiv abstract page or Crossref record). The four
references named in the L4 prompt, corrected where needed:

1. **VERIFIED ✔** — C. Muñoz, A. Narkawicz, "Formalization of Bernstein Polynomials and
   Applications to Global Optimization," *Journal of Automated Reasoning* 51(2): 151–196, 2013,
   DOI 10.1007/s10817-012-9256-3. PVS (abstract: "formalized and verified correct in the
   Prototype Verification System (PVS)").
   Traps: published online 18 July 2012, issue dated August 2013 — Crossref's BibTeX says 2012,
   Springer's says 2013: cite 2013. The authors' NASA page titles it "Formalization of a
   Representation of Bernstein Polynomials…"; the published title has no "a Representation of".
2. **VERIFIED** — A. Solovyev, T. C. Hales, "Formal Verification of Nonlinear Inequalities with
   Taylor Interval Approximations," *NASA Formal Methods* (NFM 2013), LNCS 7871, pp. 383–397,
   Springer, 2013, DOI 10.1007/978-3-642-38088-4_26; arXiv:1301.1702. HOL Light, Flyspeck.
   (The volume number 7871 is not in Crossref; it was read in the bibliography of Hales et al.,
   "A formal proof of the Kepler conjecture", arXiv:1501.02155.)
   A DISTINCT paper by the same authors, not to be confused: "Efficient Formal Verification of
   Bounds of Linear Programs," *Intelligent Computer Mathematics* (Calculemus/MKM 2011),
   LNCS 6824, pp. 123–132, 2011, DOI 10.1007/978-3-642-22673-1_9.
3. **CORRECTED (author order) ✔** — V. Magron, X. Allamigeon, S. Gaubert, B. Werner, "Formal
   Proofs for Nonlinear Optimization," *Journal of Formalized Reasoning* 8(1): 1–24, 2015,
   DOI 10.6092/issn.1972-5787/4319; arXiv:1404.7282 (v1 April 2014). Coq (abstract: "It is
   interfaced with Coq"). The prompt gave "Allamigeon–Gaubert–Magron–Werner": that alphabetical
   order is the one of two SIBLING papers (CICM 2013, "Certification of Bounds of Non-linear
   Functions: The Templates Method", DOI 10.1007/978-3-642-39320-4_4; ECC 2013). Not to be
   confused either with Magron, Allamigeon, Gaubert, Werner, "Certification of real
   inequalities: templates and sums of squares," *Mathematical Programming* 151(2): 477–506,
   2015, DOI 10.1007/s10107-014-0834-5.
4. **CORRECTED (the reference as given does not exist) ✔** — "Roux–Voronin–Magron, ValidSDP,
   2018" conflates three papers; V. Magron is an author of none of them.
   * ValidSDP, the Coq tactic: É. Martin-Dorel, P. Roux, "A reflexive tactic for polynomial
     positivity using numerical solvers and floating-point computations," *Proc. 6th ACM SIGPLAN
     Conference on Certified Programs and Proofs (CPP 2017)*, pp. 90–99, 2017,
     DOI 10.1145/3018610.3018622. (The paper names "ValidSDP" its Coq tactic and "OSDP" its
     OCaml implementation.)
   * P. Roux, Y.-L. Voronin, S. Sankaranarayanan, "Validating numerical semidefinite programming
     solvers for polynomial invariants," *Formal Methods in System Design* 53(2): 286–312, 2018,
     DOI 10.1007/s10703-017-0302-y (conference version: SAS 2016, LNCS 9837, pp. 424–446). OSDP,
     OCaml — not a proof-assistant paper.
   * P. Roux, M. Iguernlala, S. Conchon, "A Non-linear Arithmetic Procedure for Control-Command
     Software Verification," TACAS 2018, LNCS 10806, pp. 132–151,
     DOI 10.1007/978-3-319-89963-3_8. Alt-Ergo + OSDP.
   Cite ValidSDP as Martin-Dorel & Roux, CPP 2017; if a 2018 reference on validated SDP is
   wanted, it is Roux, Voronin & Sankaranarayanan, FMSD 2018.

**Neighbours, last 24 months (A51)** — a handful of searches, so "none found" is not proof of
absence:

* a formally verified checker of Bernstein-polynomial positivity certificates in Lean 4, Coq or
  Isabelle: none found;
* machine-checked infeasibility or disconnection certificates for geometric motion planning:
  none found (Li & Dantam, arXiv:2406.04795, and the other recent infeasibility-proof papers
  opened mention no proof assistant);
* adjacent, opened: `leanprover/sos`, a Lean 4 sum-of-squares tactic (software package, no
  paper; https://reservoir.lean-lang.org/@leanprover/sos); Zuo, Zhao, He, Yang, Wang, "From
  LLM-Generated Conjectures to Lean Formalizations: Automated Polynomial Inequality Proving via
  Sum-of-Squares Certificates," arXiv:2605.15445 (2026); Wang & Abdulaziz, "Formally Verified
  Certification of Unsolvability of Temporal Planning Problems," arXiv:2510.10189 (2025),
  Isabelle/HOL — AI temporal planning, not geometric motion planning; Shen, Guo, Liu, Zhi,
  "Automated Tactics for Polynomial Reasoning in Lean 4," arXiv:2604.13514 (2026).

What these works DO beyond their title and abstract has not been read in this pass: any
sentence of the paper comparing our checker with them (what is verified, what is trusted, at
what scale) needs its own reading of the papers first.
