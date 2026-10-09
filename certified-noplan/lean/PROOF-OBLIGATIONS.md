# Proof obligations — CnpVerify (state after L1)

L1 delivers an **executable** checker and the **statements** of what it is meant to satisfy.
**Nothing is proved yet.** Every theorem below is stated in Lean, type-checks against Mathlib
(`lake build`), and has `sorry` for a proof. This file lists all of them — 19 — with their exact
statement, extracted from the sources. `lake build` reports the same 19 `declaration uses sorry`
warnings, and there is no other `sorry`, `axiom` or `implemented_by` in the project.

Until these are discharged, the guarantee offered by `cnp-verify` is the same *kind* of guarantee
as `verify.py`: a short program one can read, plus measured agreement with `verify.py`
(`make lean-parity`). It is not a machine-checked proof.

## Dependency sketch

```
T1..T7 (tensor algebra)  ─┬─►  B1 bernstein_nonneg  ─┬─►  C2 outside leaf
                          │                          └─►  C3 collision leaf  ◄─ K1 (D > 0)
                          │                C1 coverage of the tiling ──┐
                          │                                            ▼
                          │                         S1 soundness  (IVT on φ ∘ γ)
                          └─►  K2 body_position ─► C4 ─► S2 soundness_ref
                               K3, K4: the rational parametrisation is a rotation
```

* **L2** (next session): B0, B1 — hence T1–T7 as far as B1 needs them — and C1.
* **L3**: C2, C3, S1.
* K1–K4, C4, S2 make the statement speak about real rigid motions instead of the polynomial
  pair `(N, D)`; S1 does not depend on them (see the remark below).

## Remarks on the statements

* **S1 is stated on the polynomial kinematics**, as required for L1: `CollisionFree` reads the
  world vertices as `eval N_k / eval D`. Its proof does not need the kinematic hypotheses tested
  by the checker (`q* = 0`, unit axes, `cos² + sin² = 1`): those hypotheses are what makes
  `(N, D)` *the forward kinematics of the declared chain* (K2–K4), and they enter through C4 / S2.
  Which of S1 or S2 the paper should cite is a decision for the supervision.
* **The path lives in `s`-space** (`s = tan (q/2)`), like the certificate. Translating a path in
  joint angles into a path in `s` (continuity of `tan (·/2)` on `(-π, π)`) is not stated here.
* **Start and goal are not required to lie in the box** (neither by `verify.py` nor here): if
  one of them is outside, no path "inside the box from start to goal" exists and the statement
  is vacuously true.
* **One body per certificate** (the schema has a single `body`); "every certified body" in the
  paper is that body.
* **B1 is stated at the tensor's own degree.** The checker pads to the working degree with
  `padTo?` first (T6).

## Tensors — reference semantics — `CnpVerify/Spec/Tensor.lean`

`Tensor.eval` (noncomputable, over `ℝ`) is the polynomial function a coefficient tensor denotes. These lemmas say that the executable tensor operations compute what they claim.

### T1 — `evalQ_cast`

The real number denoted by the tensor `t` at the point `x`: `Σ_e coeff(e) · ∏ᵢ xᵢ^eᵢ`, the sum ranging over all exponent vectors `e ∈ {0..deg}ⁿ`. -/ noncomputable def eval (t : Tensor n) (x : Fin n → ℝ) : ℝ := ∑ e : Fin n → Fin (t.deg + 1), (t.coeff (fun i => (e i).val) : ℝ) * ∏ i, x i ^ (e i).val /-- [T1] The computable rational evaluation agrees with the reference semantics.

```lean
theorem evalQ_cast (t : Tensor n) (x : Fin n → ℚ) :
    ((t.evalQ x : ℚ) : ℝ) = t.eval (fun i => (x i : ℝ))
```

### T2 — `eval_const`

The constant tensor denotes the constant function.

```lean
theorem eval_const (c : ℚ) (x : Fin n → ℝ) : (Tensor.const c : Tensor n).eval x = (c : ℝ)
```

### T3 — `eval_add`

`add` denotes the pointwise sum.

```lean
theorem eval_add (a b : Tensor n) (x : Fin n → ℝ) : (a + b).eval x = a.eval x + b.eval x
```

### T4 — `eval_scale`

`scale` denotes the multiplication by a constant.

```lean
theorem eval_scale (a : Tensor n) (c : ℚ) (x : Fin n → ℝ) :
    (a.scale c).eval x = (c : ℝ) * a.eval x
```

### T5 — `eval_mul`

`mul` denotes the pointwise product.

```lean
theorem eval_mul (a b : Tensor n) (x : Fin n → ℝ) : (a * b).eval x = a.eval x * b.eval x
```

### T6 — `eval_padTo`

Degree padding does not change the polynomial.

```lean
theorem eval_padTo (t q : Tensor n) (d : ℕ) (h : t.padTo? d = some q) (x : Fin n → ℝ) :
    q.eval x = t.eval x
```

### T7 — `eval_eq_of_beqPoly`

`beqPoly` is sound: tensors it identifies denote the same function.

```lean
theorem eval_eq_of_beqPoly (a b : Tensor n) (h : a.beqPoly b = true) (x : Fin n → ℝ) :
    a.eval x = b.eval x
```

## Bernstein test — `CnpVerify/Spec/Bernstein.lean`

`Box.toSet b = {x | ∀ i, loᵢ ≤ xᵢ ≤ hiᵢ}`. B1 is the L2 target.

### B0 — `binom_eq_choose`

The box as a subset of `ℝⁿ`: `{x | ∀ i, loᵢ ≤ xᵢ ≤ hiᵢ}`. -/ def Box.toSet (b : Box n) : Set (Fin n → ℝ) := {x | ∀ i : Fin n, (b.lo i : ℝ) ≤ x i ∧ x i ≤ (b.hi i : ℝ)} /-- [B0] The computable binomial coefficient is `Nat.choose`.

```lean
theorem binom_eq_choose (m k : ℕ) : binom m k = m.choose k
```

### B1 — `bernstein_nonneg`

Soundness of the Bernstein test: non-negative Bernstein coefficients over the box `b` (at the tensor's own degree) imply that the polynomial is non-negative on `b`.

```lean
theorem bernstein_nonneg (b : Box n) (p : Tensor n) :
    (bernsteinCoeffs b p).all (· ≥ 0) → ∀ x ∈ b.toSet, 0 ≤ p.eval x
```

## Kinematics — `CnpVerify/Spec/Kinematics.lean`

`linkPose` is the reference kinematics: a composition of real rigid motions `translate(offset) ∘ rotate(axis, angle)`, defined without any polynomial. K1–K2 tie the polynomial numerators / denominator of the checker to it; K3–K4 tie the rational parametrisation to actual rotations.

### K1 — `bodyDenominator_pos`

A rational vector seen in `ℝᵐ`. -/ def vecR {m : ℕ} (v : Vector ℚ m) : Fin m → ℝ := fun i => (v[i] : ℝ) /-- The cross-product matrix of `a` over `ℝ`. -/ def skewR (a : Vec3) : Matrix (Fin 3) (Fin 3) ℝ := Matrix.of fun i j => (skew a i j : ℝ) /-- Rodrigues' formula `I + sin·K + (1 - cos)·K²`: for a unit axis `a` and `cos² + sin² = 1`, the rotation about `a` by the angle of cosine `co` and sine `si`. -/ def rodrigues (a : Vec3) (co si : ℝ) : Matrix (Fin 3) (Fin 3) ℝ := 1 + si • skewR a + (1 - co) • (skewR a * skewR a) /-- Rotation of a joint. Unlocked: angle `q` with `s = tan (q/2)`. Locked: the fixed rational `(cos, sin)` (the value of `s` is ignored). -/ noncomputable def Joint.rotation (j : Joint) (s : ℝ) : Matrix (Fin 3) (Fin 3) ℝ := match j.locked with | none => rodrigues j.axis ((1 - s ^ 2) / (1 + s ^ 2)) (2 * s / (1 + s ^ 2)) | some (co, si) => rodrigues j.axis (co : ℝ) (si : ℝ) /-- A rigid motion `y ↦ R y + t` of `ℝ³`. -/ structure Rigid where rot : Matrix (Fin 3) (Fin 3) ℝ trans : Fin 3 → ℝ /-- Action on a point. -/ def Rigid.apply (g : Rigid) (y : Fin 3 → ℝ) : Fin 3 → ℝ := g.rot.mulVec y + g.trans /-- `g.comp h` is "`h` first, then `g`". -/ def Rigid.comp (g h : Rigid) : Rigid := ⟨g.rot * h.rot, g.rot.mulVec h.trans + g.trans⟩ /-- Accumulation state of the reference chain: pose so far, next free variable. -/ structure RefState where pose : Rigid nextVar : ℕ /-- One joint: `pose ← pose ∘ translate(offset) ∘ rotate`. An unlocked joint reads the next variable (a variable index `≥ n` reads `0`; the checker excludes that case). -/ noncomputable def refStep {n : ℕ} (s : Fin n → ℝ) (st : RefState) (j : Joint) : RefState := let sVal : ℝ := if h : st.nextVar < n then s ⟨st.nextVar, h⟩ else 0 let pose := st.pose.comp ⟨j.rotation sVal, vecR j.offset⟩ match j.locked with | none => ⟨pose, st.nextVar + 1⟩ | some _ => ⟨pose, st.nextVar⟩ /-- Reference world pose of link `link` at the configuration `s` (unlocked joints numbered `0..n-1` in chain order): the composition of the joint motions `0..link`. -/ noncomputable def linkPose {n : ℕ} (chain : Array Joint) (link : ℕ) (s : Fin n → ℝ) : Rigid := ((chain.extract 0 (link + 1)).foldl (refStep s) ⟨⟨1, 0⟩, 0⟩).pose /-- Number of unlocked joints among joints `0..link`. -/ def unlockedUpTo (chain : Array Joint) (link : ℕ) : ℕ := ((chain.extract 0 (link + 1)).filter (·.locked.isNone)).size /-- [K1] The common denominator is positive everywhere.

```lean
theorem bodyDenominator_pos (n : ℕ) (chain : Array Joint) (link : ℕ) (s : Fin n → ℝ) :
    0 < (bodyDenominator n chain link).eval s
```

### K2 — `body_position`

The polynomial kinematics is the reference kinematics: the world position of the body-frame point `p` of link `link` is `eval (N·p) / eval D`.

```lean
theorem body_position (n : ℕ) (chain : Array Joint) (link : ℕ) (p : Vec3) (s : Fin n → ℝ)
    (hn : unlockedUpTo chain link ≤ n) (i : Fin 3) :
    (linkPose chain link s).apply (vecR p) i
      = ((bodyNumerators n chain link p)[i]).eval s / (bodyDenominator n chain link).eval s
```

### K3 — `rotation_half_angle`

The half-angle parametrisation is the rotation of angle `q`: with `s = tan (q/2)` and `|q| < π`, the rational expressions in `s` are `cos q` and `sin q`.

```lean
theorem rotation_half_angle (a : Vec3) (q : ℝ) (hq : |q| < Real.pi) :
    rodrigues a ((1 - Real.tan (q / 2) ^ 2) / (1 + Real.tan (q / 2) ^ 2))
        (2 * Real.tan (q / 2) / (1 + Real.tan (q / 2) ^ 2))
      = rodrigues a (Real.cos q) (Real.sin q)
```

### K4 — `rodrigues_mem_specialOrthogonal`

For a unit axis and `cos² + sin² = 1`, Rodrigues' matrix is a rotation (orthogonal, determinant `1`). This is where the hypotheses "exact unit axis" and "`cos² + sin² = 1`" of the checker are used.

```lean
theorem rodrigues_mem_specialOrthogonal (a : Vec3) (co si : ℝ)
    (ha : ((a[0] : ℝ)) ^ 2 + (a[1] : ℝ) ^ 2 + (a[2] : ℝ) ^ 2 = 1) (hcs : co ^ 2 + si ^ 2 = 1) :
    rodrigues a co si ∈ Matrix.specialOrthogonalGroup (Fin 3) ℝ
```

## Checks and main statement — `CnpVerify/Soundness.lean`

`CollisionFree c s` is defined from `bodyNumerators` / `bodyDenominator` and the H-representations only (no reference to the checker); `CollisionFreeRef` is the same notion on the reference kinematics.

### C1 — `verifyCover_covers`

The obstacle as a subset of `ℝ³`: the points satisfying every face inequality `aᵀ y ≤ b`. -/ def Obstacle.toSet (O : Obstacle) : Set (Fin 3 → ℝ) := {y | ∀ f ∈ O.faces, ∑ i : Fin 3, (f.a[i] : ℝ) * y i ≤ (f.b : ℝ)} /-- World position of the `k`-th vertex of the certified body at the configuration `s`: `eval (N_k) / eval D`, with `N_k` and `D` the kinematic numerators and the common denominator of the body's link, computed from the declared chain. -/ noncomputable def Certificate.worldVertex (c : Certificate) (k : Fin c.hull.size) (s : Fin c.n → ℝ) : Fin 3 → ℝ := fun i => ((bodyNumerators c.n c.chain c.bodyLink c.hull[k])[i]).eval s / (bodyDenominator c.n c.chain c.bodyLink).eval s /-- The certified body at the configuration `s`: the convex hull of its world vertices. -/ noncomputable def Certificate.bodyAt (c : Certificate) (s : Fin c.n → ℝ) : Set (Fin 3 → ℝ) := convexHull ℝ (Set.range fun k : Fin c.hull.size => c.worldVertex k s) /-- The configuration `s` is collision-free: the certified body meets no obstacle. -/ def CollisionFree (c : Certificate) (s : Fin c.n → ℝ) : Prop := ∀ O ∈ c.obstacles, Disjoint (c.bodyAt s) O.toSet /-- Collision-freeness stated on the REFERENCE kinematics (`linkPose`: real rigid motions, no polynomial): the convex hull of the moved body vertices meets no obstacle. -/ def CollisionFreeRef (c : Certificate) (s : Fin c.n → ℝ) : Prop := ∀ O ∈ c.obstacles, Disjoint (convexHull ℝ (Set.range fun k : Fin c.hull.size => (linkPose c.chain c.bodyLink s).apply (vecR c.hull[k]))) O.toSet /-! ### Proof obligations of the checks -/ /-- [C1] COVERAGE of the tiling check: if `verifyCover` accepts, every point of the box lies in one of the cells. (Disjointness is also tested by the checker, as in `verify.py`, but the soundness proof only uses coverage.)

```lean
theorem verifyCover_covers {n : ℕ} (fuel : ℕ) (box : Box n) (cells : Array (Box n))
    (h : verifyCover fuel box cells = .ok ()) :
    ∀ x ∈ box.toSet, ∃ cell ∈ cells, x ∈ cell.toSet
```

### C2 — `checkOutsideLeaf_sound`

An accepted outside leaf is disjoint from the OPEN slab: `|φ| ≥ δ` on its cell.

```lean
theorem checkOutsideLeaf_sound (c : Certificate) (i : ℕ) (cell : Box c.n)
    (h : checkOutsideLeaf c i cell = .ok ()) :
    ∀ s ∈ cell.toSet, (c.delta : ℝ) ≤ |c.phi.eval s|
```

### C3 — `checkCollisionLeaf_sound`

An accepted collision leaf is in collision on the slab: at every point of its cell where `|φ| ≤ δ`, the certified body meets the named obstacle.

```lean
theorem checkCollisionLeaf_sound (c : Certificate) (i : ℕ) (cell : Box c.n) (obstacle : String)
    (lam : Array (Tensor c.n)) (mu : Array ℚ)
    (h : checkCollisionLeaf c c.geometry i cell obstacle lam mu = .ok ()) :
    ∀ s ∈ cell.toSet, |c.phi.eval s| ≤ (c.delta : ℝ) → ¬ CollisionFree c s
```

### C4 — `collisionFree_iff_ref`

Under the kinematic hypotheses tested by the checker, collision-freeness on the polynomial kinematics IS collision-freeness on the reference kinematics.

```lean
theorem collisionFree_iff_ref (c : Certificate) (h : checkKinematics c = .ok ())
    (s : Fin c.n → ℝ) : CollisionFree c s ↔ CollisionFreeRef c s
```

### S1 — `soundness`

**Soundness of the checker.** If `check c = true`, there is no continuous path `γ : [0,1] → ℝⁿ` that stays in the box, starts at `s_start`, ends at `s_goal`, and is collision-free at every time.

```lean
theorem soundness (c : Certificate) :
    check c = true →
      ¬ ∃ γ : C(unitInterval, Fin c.n → ℝ),
          (∀ t, γ t ∈ c.box.toSet) ∧ γ 0 = vecR c.sStart ∧ γ 1 = vecR c.sGoal
            ∧ ∀ t, CollisionFree c (γ t)
```

### S2 — `soundness_ref`

The same statement on the reference kinematics (corollary of S1 and C4).

```lean
theorem soundness_ref (c : Certificate) :
    check c = true →
      ¬ ∃ γ : C(unitInterval, Fin c.n → ℝ),
          (∀ t, γ t ∈ c.box.toSet) ∧ γ 0 = vecR c.sStart ∧ γ 1 = vecR c.sGoal
            ∧ ∀ t, CollisionFreeRef c (γ t)
```
