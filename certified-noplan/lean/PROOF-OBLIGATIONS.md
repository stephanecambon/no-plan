# Proof obligations — CnpVerify (state after L3; L4 note below)

L1 delivered an **executable** checker and the **statements** of what it is meant to satisfy:
19 theorems stated in Lean, each with `sorry` for a proof. L2 proved 10 of them. **L3 proved
the remaining 9, among them the main statements `soundness` (S1) and `soundness_ref` (S2).**
`lake build` reports no `declaration uses sorry` warning and no other warning; there is no
`sorry`, `axiom`, `implemented_by`, `native_decide` or `unsafe` in the `CnpVerify` library.
`#print axioms` on each of the 19 theorems lists `propext`, `Classical.choice`, `Quot.sound`
only (`binom_eq_choose`: `propext` only) — asserted by `scripts/lean_axioms.py` since L4.

**L4 note.** L4 added no obligation and changed no statement, no reference definition and no
proof; in the executable core it corrected two stale comments (`Bernstein.lean:7`,
`Kinematics.lean:10`, "sorry in L1"). It added a second library, `Certs/`: shipped certificates
as Lean terms, and for `scenes/wall/k3.cert.json` a proof of the HYPOTHESIS `check c = true` by
evaluation in the kernel, hence `wallK3_disconnected_ref` — the disconnection of that scene as
a theorem with the three standard axioms (`README.md`, "Certificates as Lean terms"). `Certs/`
also contains, in `Certs/Native.lean` and `Certs/DisconnectedNative.lean` ONLY, proofs by
`native_decide`, kept for comparison: each depends on one more axiom, and the audit checks that
no other statement does.

**What is machine-checked**: if the Lean function `check` returns `true` on a `Certificate`,
then no continuous path inside the box joins the start to the goal while keeping the certified
body out of every obstacle — the body being moved by real rigid motions along the declared
chain (S2). What the theorem does NOT cover — the JSON parser, the compiled binary, the reading
of the reference definitions — is listed in the section "Trust base" of `README.md`.

| | obligation | file | state |
|---|---|---|---|
| T1 | `Tensor.evalQ_cast` | `Spec/Tensor.lean` | proved (L2) |
| T2 | `Tensor.eval_const` | `Spec/Tensor.lean` | proved (L2) |
| T3 | `Tensor.eval_add` | `Spec/Tensor.lean` | proved (L2) |
| T4 | `Tensor.eval_scale` | `Spec/Tensor.lean` | proved (L2) |
| T5 | `Tensor.eval_mul` | `Spec/Tensor.lean` | proved (L2) |
| T6 | `Tensor.eval_padTo` | `Spec/Tensor.lean` | proved (L2) |
| T7 | `Tensor.eval_eq_of_beqPoly` | `Spec/Tensor.lean` | proved (L2) |
| B0 | `binom_eq_choose` | `Spec/Bernstein.lean` | proved (L2) |
| B1 | `bernstein_nonneg` | `Spec/Bernstein.lean` | proved (L2) — as stated in L1, on the unchanged checker |
| C1 | `verifyCover_covers` | `Soundness.lean` | proved (L2) |
| K1 | `bodyDenominator_pos` | `Spec/Kinematics.lean` | **proved (L3)** |
| K2 | `body_position` | `Spec/Kinematics.lean` | **proved (L3)** — as stated in L1, reference definitions unchanged |
| K3 | `rotation_half_angle` | `Spec/Kinematics.lean` | **proved (L3)** |
| K4 | `rodrigues_mem_specialOrthogonal` | `Spec/Kinematics.lean` | **proved (L3)** |
| C2 | `checkOutsideLeaf_sound` | `Soundness.lean` | **proved (L3)** |
| C3 | `checkCollisionLeaf_sound` | `Soundness.lean` | **proved (L3)** |
| C4 | `collisionFree_iff_ref` | `Soundness.lean` | **proved (L3)** |
| S1 | `soundness` | `Soundness.lean` | **proved (L3)** |
| S2 | `soundness_ref` | `Soundness.lean` | **proved (L3)** |

**No statement was modified, and none turned out to be false.** The 19 statements are
character-for-character those of L1 (compared by script against the L1 commit `56e1666` and the
L2 commit `01a1c80`), and so are the reference definitions (`Tensor.eval`, `Box.toSet`,
`Obstacle.toSet`, `Certificate.worldVertex`, `Certificate.bodyAt`, `CollisionFree`,
`CollisionFreeRef`, `vecR`, `skewR`, `rodrigues`, `Joint.rotation`, `Rigid`, `Rigid.apply`,
`Rigid.comp`, `RefState`, `refStep`, `linkPose`, `unlockedUpTo`). The executable core
(`Tensor.lean`, `Bernstein.lean`, `Kinematics.lean`, `Certificate.lean`, `Check.lean`,
`Main.lean`) has zero diff since L1: the proofs are about the code that runs, as it was.

## Dependency sketch

```
T1..T7 (tensor algebra) ─┬─►  B1 bernstein_nonneg ─┬─►  C2 outside leaf ───────────┐
                         │                         └─►  C3 collision leaf ◄─ K1    │
                         │              C1 coverage of the tiling ──────────────┐  │
                         │                                                      ▼  ▼
                         │                                 S1 soundness  (IVT on φ ∘ γ)
                         └─►  K2 body_position ─► C4 ─────────────────────────► S2 soundness_ref
                              K3, K4: the rational parametrisation is a rotation
                                      └─► linkPose_rot_mem_specialOrthogonal (not one of the 19)
```

* **L2**: T1–T7, B0, B1, C1, and `bernNonneg_sound` (not one of the 19).
* **L3**: K1, C2, C3, S1 first (the main statement, on the polynomial kinematics); then K2, K3,
  K4, C4, S2 (the same statement on real rigid motions).

## Which tests of the checker the proofs use

This is a by-product of the mechanisation: a test of the checker that no proof uses is not
needed for soundness.

| check | used by S1 | used by S2 only | not used by any proof |
|---|---|---|---|
| (0) hypotheses | `δ > 0` | | non-degenerate box |
| (i) start / goal | `φ(s_start) < -δ`, `φ(s_goal) > δ` | | |
| (ii) tiling | coverage of the box by the cells | | disjointness of the cells; the VALUE of the cut (midpoint) |
| (0') kinematics | nothing | `n` = number of unlocked joints | `q* = 0`; unit axes and `cos² + sin² = 1` (see below); body link in range |
| (iii) outside leaf | one of the two Bernstein tests | | |
| (iv) collision leaf | `λ` count, `Σλ ≡ 1`, `λ_k ≥ 0`, `μ_j ≥ 0`, `g_j - μ_j T ≥ 0` | | the degree test on `λ_k`; the `μ` count (a missing `μ_j` is read as `0`) |

* **S1 does not use the kinematic check at all**: it is a statement about the pair `(N, D)`
  recomputed from the chain, whatever the chain is.
* **S2 uses one kinematic fact**: `n` is the number of unlocked joints, so that every unlocked
  joint of the body's chain reads an actual variable (hypothesis of K2).
* **Unit axes and `cos² + sin² = 1` are not needed for S2 to hold.** They are what makes the
  reference motions `linkPose` proper ROTATIONS: `linkPose_rot_mem_specialOrthogonal` (proved,
  not one of the 19) derives, from the kinematic check and K4, that the rotation part of
  `linkPose c.chain c.bodyLink s` is in `SO(3)`. Without them S2 would still be a true statement,
  about maps that are no longer rigid motions.
* **`q* = 0` is outside the formal statement.** `Certificate` carries `qStar`, the statements
  never read it: they are written in `s`-space with `s = tan (q/2)`. The test `q* = 0` is what
  makes that reading the right one for the certificate at hand.

## How the L3 lemmas were proved

* **K1** (`Spec/Kinematics.lean`). `Tensor.monomial e c` denotes `c · ∏ᵢ sᵢ^(e i)`
  (`toMv_monomial`, from `toMv_ofTerms`), so `onePlusSq` denotes `1 + s²`; `D` is a product of
  such factors along the chain (invariant of the fold). No hypothesis: for a variable index out
  of range the exponent array of `unitExp` is all zeros and the factor is the constant `2`.
* **C2** (`Soundness.lean`). The check succeeds only if one of its two Bernstein tests answers
  `true`; `bernNonneg_sound` with T2, T3, T4 gives `φ - δ ≥ 0` or `-φ - δ ≥ 0` on the cell.
* **C3** (`Soundness.lean`). The do-block is taken apart test by test; the two `for` loops are
  handled by `range_forIn'_ok` (a loop in `Except` that succeeds has run its body successfully
  at every index). On the cell: `Σ_k λ_k = 1` (T7), `λ_k ≥ 0`, and for each face
  `b D - aᵀ Σ_k λ_k N_k - μ (δ² - φ²) ≥ 0` with `μ ≥ 0`. On the slab `δ² - φ² ≥ 0`, hence
  `aᵀ Σ_k λ_k N_k ≤ b D`; dividing by `D > 0` (K1), the point `Σ_k λ_k(s) · N_k(s)/D(s)`
  satisfies every face of the obstacle, and it is a convex combination of the world vertices
  (`Convex.sum_mem`).
* **S1** (`Soundness.lean`), the argument of the paper §4. `φ ∘ γ` is continuous
  (`Tensor.continuous_eval`: `eval` is `MvPolynomial.aeval` of `toMv`, Mathlib's
  `MvPolynomial.continuous_eval`), negative at `0` and positive at `1`; `[0,1]` is connected, so
  it vanishes at some `t` (`intermediate_value_univ`). `γ t` is in the box, hence in the cell of
  a leaf (C1). An `outside` leaf would give `δ ≤ |φ(γ t)| = 0` (C2); a `collision` leaf says
  `γ t` is in collision (C3, since `|φ(γ t)| = 0 ≤ δ`).
* **K2** (`Spec/Kinematics.lean`). `Mat4.Represents M s d g`: the polynomial matrix `M`
  evaluated at `s` is `d · [R t; 0 1]` for the rigid motion `g = (R, t)`. It is stable by product
  (`Represents.mul`: scalars multiply, motions compose), holds for the identity, for
  `transHomog` (scalar `1`), for a locked `rotHomog` (scalar `1`) and for an unlocked one
  (scalar `1 + s²`, by `field_simp`). `fkFold_represents` carries it along the chain, the
  polynomial step `fkStep` against the reference step `refStep`, under the invariant "the next
  variable index plus the number of unlocked joints still to come is `≤ n`". Reading the first
  three columns against a vertex and the last one gives `N/D`.
* **K3**. Mathlib's `Real.cos_eq_two_mul_tan_half_div_one_sub_tan_half_sq` (needs `cos q ≠ -1`,
  which is `|q| < π` here) and `Real.sin_eq_two_mul_tan_half_div_one_add_tan_half_sq`.
* **K4**. Two polynomial identities, valid without any hypothesis and proved entry by entry:
  `R Rᵀ = 1 + ((1 - cos² - sin²) - (|a|² - 1)(1 - cos)²) · K²` and
  `det R = (1 - (1 - cos)|a|²)² + sin² |a|²`; then the two hypotheses.
* **C4**. By K2 the world vertices `eval N_k / eval D` are the reference positions, so the two
  bodies are the same set.
* **S2**. S1 and C4.

Also proved in L3, **not among the 19**: `Tensor.continuous_eval`, `Tensor.eval_monomial`,
`check_eq_true_iff` (`check c = true` iff the sequence `checkE c` succeeds, which is what the
executable reports), `skewR_mulVec` and `rodrigues_mulVec` (the sign table `skew` is Mathlib's
cross product; `rodrigues` is `v ↦ v + sin · a × v + (1 - cos) · a × (a × v)`),
`rodrigues_mulVec_axis` (the axis is fixed), `Joint.rotation_mem_specialOrthogonal` and
`linkPose_rot_mem_specialOrthogonal`.

## Remarks on the statements

* **S1 is stated on the polynomial kinematics**: `CollisionFree` reads the world vertices as
  `eval N_k / eval D`. **S2 is stated on real rigid motions** and mentions no polynomial and no
  tensor: `CollisionFreeRef` is built from `linkPose`, `vecR`, `Obstacle.toSet` and Mathlib's
  `convexHull` only. Decision of the supervision (L1 review): the paper cites S2; S1 is the
  technical core.
* **The path lives in `s`-space** (`s = tan (q/2)`), like the certificate. Translating a path in
  joint angles into a path in `s` (continuity of `tan (·/2)` on `(-π, π)`) is not stated here;
  K3 says that the joint rotation at `s = tan (q/2)` is the rotation of angle `q`.
* **Start and goal are not required to lie in the box** (neither by `verify.py` nor here): if
  one of them is outside, no path "inside the box from start to goal" exists and the statement
  is vacuously true.
* **One body per certificate** (the schema has a single `body`); "every certified body" in the
  paper is that body. The statement is about that body and the listed obstacles: a path that is
  collision-free for the whole robot is in particular collision-free for that body.
* **Collision means intersection with a CLOSED obstacle** (`aᵀ y ≤ b` for every face): touching
  counts as a collision.
* **Out-of-range variable indices.** For an unlocked joint whose variable index is `≥ n`, the
  checker's polynomials read the constant `1` (`varAt`) and the reference reads `0`
  (`refStep`). K2 excludes the case by hypothesis, and the checker by its test on `n`.
* **B1 is stated at the tensor's own degree.** The checker pads to the working degree with
  `padTo?` first (T6); `bernNonneg_sound` puts the two together.
* **The reference definitions were put to the test by K2 and C4** and found right: both were
  provable as stated, with `linkPose`, `refStep`, `Joint.rotation`, `rodrigues`, `Rigid.comp`
  unchanged. They still have to be READ (list in `README.md`, "Trust base"): a proof shows that
  the checker agrees with them, not that they say what a roboticist means.

## How the L2 lemmas were proved

* **Flat layout** (`Spec/Index.lean`). `flatIndex (d+1) e = Σᵢ eᵢ (d+1)^(n-1-i)`; exponent
  vectors of the box and flat indices `< (d+1)^n` are in bijection (Mathlib's
  `finFunctionFinEquiv`, read from the last variable); `encode` is `flatIndex`, `decode` writes
  the digits. The `for` loops of the executable definitions are rewritten as folds
  (`forIn_list_id`, `forIn_array_id`) and handled by invariant.
* **T1–T7** (`Spec/Tensor.lean`). A tensor denotes `toMv t : MvPolynomial (Fin n) ℚ`, the sum of
  its monomials, and `eval t x = aeval x (toMv t)`. `support` lists the monomials of `t`
  (`sum_support`); `ofTerms` sums the listed monomials that fit its layout (`toMv_ofTerms`);
  `varDegsOf` / `maxDeg` bound the listed exponents, so nothing is dropped (`fit_maxDeg`). Then
  `trim`, `padTo?`, `add`, `scale` are immediate, and `mul` is the double accumulation loop
  (`arrPoly_mulAcc`: the flat index is additive in the exponents, and `encode ea + encode eb`
  stays inside the layout because the working degree bounds `ea + eb` per variable).
* **B1, path retained: the DIRECT proof** — the Bernstein coefficients computed by the checker
  are the right ones — **not B1-bis** (re-expand the coefficients at run time and compare). The
  checker is therefore unchanged and pays no extra cost. A coefficient array is read against
  per-axis weights (`arrSum`): with `xᵢ^k` it is the value of the polynomial, with
  `B_{k,d}(tᵢ)` the value of a Bernstein form. Applying a matrix along an axis moves the matrix
  onto the weights of that axis (`arrSum_applyAxis`, the lemma both paths needed). The matrix of
  the checker is `B · S`: `S` is the substitution `s = lo + (hi - lo) t` (`shift_sum`, binomial
  theorem) and `B` the monomial-to-Bernstein change of basis, whose correctness is
  `t^k = Σ_j C(j,k)/C(d,k) · B_{j,d}(t)` (`bern_inverse`: `C(d,j) C(j,k) = C(d,k) C(d-k,j-k)`,
  then the binomial theorem for `(t + (1-t))^(d-k)`). A point `x` of the box is
  `lo + (hi - lo) t` with `t ∈ [0,1]ⁿ`, **including when `lo = hi` on an axis** (`t = 0`), so B1
  holds for every box, as stated.
* **C1** (`Soundness.lean`). Induction on the recursion of `verifyCover` (structural on its
  `fuel`). A single cell is the box; otherwise both sides of the cut are made of cells of the
  input (`splitCells_subset`) and cover their half-box, and a point of the box is on one side
  of the cut. **Coverage only**: that no cell straddles the cut (disjointness) is tested by the
  checker and is not used.

## Tensors — reference semantics — `CnpVerify/Spec/Tensor.lean`

`Tensor.eval` (noncomputable, over `ℝ`) is the polynomial function a coefficient tensor denotes: `eval t x = Σ_e coeff(e) · ∏ᵢ xᵢ^eᵢ`, the sum ranging over all exponent vectors `e ∈ {0..deg}ⁿ`. These lemmas say that the executable tensor operations compute what they claim. **All seven are proved (L2).**

### T1 — `evalQ_cast` — proved (L2)

The computable rational evaluation agrees with the reference semantics.

```lean
theorem evalQ_cast (t : Tensor n) (x : Fin n → ℚ) :
    ((t.evalQ x : ℚ) : ℝ) = t.eval (fun i => (x i : ℝ))
```

### T2 — `eval_const` — proved (L2)

The constant tensor denotes the constant function.

```lean
theorem eval_const (c : ℚ) (x : Fin n → ℝ) : (Tensor.const c : Tensor n).eval x = (c : ℝ)
```

### T3 — `eval_add` — proved (L2)

`add` denotes the pointwise sum.

```lean
theorem eval_add (a b : Tensor n) (x : Fin n → ℝ) : (a + b).eval x = a.eval x + b.eval x
```

### T4 — `eval_scale` — proved (L2)

`scale` denotes the multiplication by a constant.

```lean
theorem eval_scale (a : Tensor n) (c : ℚ) (x : Fin n → ℝ) :
    (a.scale c).eval x = (c : ℝ) * a.eval x
```

### T5 — `eval_mul` — proved (L2)

`mul` denotes the pointwise product.

```lean
theorem eval_mul (a b : Tensor n) (x : Fin n → ℝ) : (a * b).eval x = a.eval x * b.eval x
```

### T6 — `eval_padTo` — proved (L2)

Degree padding does not change the polynomial.

```lean
theorem eval_padTo (t q : Tensor n) (d : ℕ) (h : t.padTo? d = some q) (x : Fin n → ℝ) :
    q.eval x = t.eval x
```

### T7 — `eval_eq_of_beqPoly` — proved (L2)

`beqPoly` is sound: tensors it identifies denote the same function.

```lean
theorem eval_eq_of_beqPoly (a b : Tensor n) (h : a.beqPoly b = true) (x : Fin n → ℝ) :
    a.eval x = b.eval x
```

## Bernstein test — `CnpVerify/Spec/Bernstein.lean`

`Box.toSet b = {x | ∀ i, loᵢ ≤ xᵢ ≤ hiᵢ}`. **Both are proved (L2).**

### B0 — `binom_eq_choose` — proved (L2)

The computable binomial coefficient is `Nat.choose`.

```lean
theorem binom_eq_choose (m k : ℕ) : binom m k = m.choose k
```

### B1 — `bernstein_nonneg` — proved (L2), direct path

Soundness of the Bernstein test: non-negative Bernstein coefficients over the box `b` (at the tensor's own degree) imply that the polynomial is non-negative on `b`.

```lean
theorem bernstein_nonneg (b : Box n) (p : Tensor n) :
    (bernsteinCoeffs b p).all (· ≥ 0) → ∀ x ∈ b.toSet, 0 ≤ p.eval x
```

## Kinematics — `CnpVerify/Spec/Kinematics.lean`

`linkPose` is the reference kinematics: a composition of real rigid motions `translate(offset) ∘ rotate(axis, angle)`, defined without any polynomial (`rodrigues`, `Joint.rotation`, `Rigid`, `refStep`, `linkPose`, `unlockedUpTo` in the file). K1–K2 tie the polynomial numerators / denominator of the checker to it; K3–K4 tie the rational parametrisation to actual rotations. **All four are proved (L3).**

### K1 — `bodyDenominator_pos` — proved (L3)

The common denominator is positive everywhere.

```lean
theorem bodyDenominator_pos (n : ℕ) (chain : Array Joint) (link : ℕ) (s : Fin n → ℝ) :
    0 < (bodyDenominator n chain link).eval s
```

### K2 — `body_position` — proved (L3)

The polynomial kinematics is the reference kinematics: the world position of the body-frame point `p` of link `link` is `eval (N·p) / eval D`.

```lean
theorem body_position (n : ℕ) (chain : Array Joint) (link : ℕ) (p : Vec3) (s : Fin n → ℝ)
    (hn : unlockedUpTo chain link ≤ n) (i : Fin 3) :
    (linkPose chain link s).apply (vecR p) i
      = ((bodyNumerators n chain link p)[i]).eval s / (bodyDenominator n chain link).eval s
```

### K3 — `rotation_half_angle` — proved (L3)

The half-angle parametrisation is the rotation of angle `q`: with `s = tan (q/2)` and `|q| < π`, the rational expressions in `s` are `cos q` and `sin q`.

```lean
theorem rotation_half_angle (a : Vec3) (q : ℝ) (hq : |q| < Real.pi) :
    rodrigues a ((1 - Real.tan (q / 2) ^ 2) / (1 + Real.tan (q / 2) ^ 2))
        (2 * Real.tan (q / 2) / (1 + Real.tan (q / 2) ^ 2))
      = rodrigues a (Real.cos q) (Real.sin q)
```

### K4 — `rodrigues_mem_specialOrthogonal` — proved (L3)

For a unit axis and `cos² + sin² = 1`, Rodrigues' matrix is a rotation (orthogonal, determinant `1`). This is where the hypotheses "exact unit axis" and "`cos² + sin² = 1`" of the checker are used.

```lean
theorem rodrigues_mem_specialOrthogonal (a : Vec3) (co si : ℝ)
    (ha : ((a[0] : ℝ)) ^ 2 + (a[1] : ℝ) ^ 2 + (a[2] : ℝ) ^ 2 = 1) (hcs : co ^ 2 + si ^ 2 = 1) :
    rodrigues a co si ∈ Matrix.specialOrthogonalGroup (Fin 3) ℝ
```

## Checks and main statement — `CnpVerify/Soundness.lean`

`CollisionFree c s` is defined from `bodyNumerators` / `bodyDenominator` and the H-representations only (no reference to the checker), through `Obstacle.toSet`, `Certificate.worldVertex` and `Certificate.bodyAt` (convex hull of the world vertices); `CollisionFreeRef` is the same notion on the reference kinematics. **C1 is proved (L2); C2, C3, C4, S1, S2 are proved (L3).**

### C1 — `verifyCover_covers` — proved (L2)

COVERAGE of the tiling check: if `verifyCover` accepts, every point of the box lies in one of the cells. (Disjointness is also tested by the checker, as in `verify.py`, but the soundness proof only uses coverage.)

```lean
theorem verifyCover_covers {n : ℕ} (fuel : ℕ) (box : Box n) (cells : Array (Box n))
    (h : verifyCover fuel box cells = .ok ()) :
    ∀ x ∈ box.toSet, ∃ cell ∈ cells, x ∈ cell.toSet
```

### C2 — `checkOutsideLeaf_sound` — proved (L3)

An accepted outside leaf is disjoint from the OPEN slab: `|φ| ≥ δ` on its cell.

```lean
theorem checkOutsideLeaf_sound (c : Certificate) (i : ℕ) (cell : Box c.n)
    (h : checkOutsideLeaf c i cell = .ok ()) :
    ∀ s ∈ cell.toSet, (c.delta : ℝ) ≤ |c.phi.eval s|
```

### C3 — `checkCollisionLeaf_sound` — proved (L3)

An accepted collision leaf is in collision on the slab: at every point of its cell where `|φ| ≤ δ`, the certified body meets the named obstacle.

```lean
theorem checkCollisionLeaf_sound (c : Certificate) (i : ℕ) (cell : Box c.n) (obstacle : String)
    (lam : Array (Tensor c.n)) (mu : Array ℚ)
    (h : checkCollisionLeaf c c.geometry i cell obstacle lam mu = .ok ()) :
    ∀ s ∈ cell.toSet, |c.phi.eval s| ≤ (c.delta : ℝ) → ¬ CollisionFree c s
```

### C4 — `collisionFree_iff_ref` — proved (L3)

Under the kinematic hypotheses tested by the checker, collision-freeness on the polynomial kinematics IS collision-freeness on the reference kinematics.

```lean
theorem collisionFree_iff_ref (c : Certificate) (h : checkKinematics c = .ok ())
    (s : Fin c.n → ℝ) : CollisionFree c s ↔ CollisionFreeRef c s
```

### S1 — `soundness` — proved (L3)

**Soundness of the checker.** If `check c = true`, there is no continuous path `γ : [0,1] → ℝⁿ` that stays in the box, starts at `s_start`, ends at `s_goal`, and is collision-free at every time.

```lean
theorem soundness (c : Certificate) :
    check c = true →
      ¬ ∃ γ : C(unitInterval, Fin c.n → ℝ),
          (∀ t, γ t ∈ c.box.toSet) ∧ γ 0 = vecR c.sStart ∧ γ 1 = vecR c.sGoal
            ∧ ∀ t, CollisionFree c (γ t)
```

### S2 — `soundness_ref` — proved (L3)

The same statement on the reference kinematics (corollary of S1 and C4): the certified body is moved by the real rigid motions `linkPose` of the declared chain.

```lean
theorem soundness_ref (c : Certificate) :
    check c = true →
      ¬ ∃ γ : C(unitInterval, Fin c.n → ℝ),
          (∀ t, γ t ∈ c.box.toSet) ∧ γ 0 = vecR c.sStart ∧ γ 1 = vecR c.sGoal
            ∧ ∀ t, CollisionFreeRef c (γ t)
```
