# Proof obligations — CnpVerify (state after L2)

L1 delivered an **executable** checker and the **statements** of what it is meant to satisfy:
19 theorems stated in Lean, each with `sorry` for a proof. **L2 proved 10 of them; 9 are still
`sorry`, among them the main statement `soundness`.** `lake build` reports exactly those 9
`declaration uses sorry` warnings, and there is no other `sorry`, `axiom` or `implemented_by` in
the project. `#print axioms` on each closed theorem lists `propext`, `Classical.choice`,
`Quot.sound` only (no `sorryAx`).

Until S1 is discharged, the guarantee offered by `cnp-verify` is the same *kind* of guarantee
as `verify.py`: a short program one can read, plus measured agreement with `verify.py`
(`make lean-parity`). **It is not a machine-checked proof of soundness.** What IS machine-checked
after L2: the tensor arithmetic of the checker computes the polynomial operations it claims
(T1–T7), its Bernstein test implies non-negativity on the box (B1), and its tiling test implies
that the leaves cover the box (C1).

| | obligation | file | state |
|---|---|---|---|
| T1 | `Tensor.evalQ_cast` | `Spec/Tensor.lean` | **proved (L2)** |
| T2 | `Tensor.eval_const` | `Spec/Tensor.lean` | **proved (L2)** |
| T3 | `Tensor.eval_add` | `Spec/Tensor.lean` | **proved (L2)** |
| T4 | `Tensor.eval_scale` | `Spec/Tensor.lean` | **proved (L2)** |
| T5 | `Tensor.eval_mul` | `Spec/Tensor.lean` | **proved (L2)** |
| T6 | `Tensor.eval_padTo` | `Spec/Tensor.lean` | **proved (L2)** |
| T7 | `Tensor.eval_eq_of_beqPoly` | `Spec/Tensor.lean` | **proved (L2)** |
| B0 | `binom_eq_choose` | `Spec/Bernstein.lean` | **proved (L2)** |
| B1 | `bernstein_nonneg` | `Spec/Bernstein.lean` | **proved (L2)** — as stated in L1, on the unchanged checker |
| C1 | `verifyCover_covers` | `Soundness.lean` | **proved (L2)** |
| K1 | `bodyDenominator_pos` | `Spec/Kinematics.lean` | open (`sorry`) |
| K2 | `body_position` | `Spec/Kinematics.lean` | open (`sorry`) |
| K3 | `rotation_half_angle` | `Spec/Kinematics.lean` | open (`sorry`) |
| K4 | `rodrigues_mem_specialOrthogonal` | `Spec/Kinematics.lean` | open (`sorry`) |
| C2 | `checkOutsideLeaf_sound` | `Soundness.lean` | open (`sorry`) |
| C3 | `checkCollisionLeaf_sound` | `Soundness.lean` | open (`sorry`) |
| C4 | `collisionFree_iff_ref` | `Soundness.lean` | open (`sorry`) |
| S1 | `soundness` | `Soundness.lean` | open (`sorry`) |
| S2 | `soundness_ref` | `Soundness.lean` | open (`sorry`) |

**No statement was modified.** The 19 statements are character-for-character those of L1
(compared against commit `56e1666`), and no reference definition (`Tensor.eval`, `Box.toSet`,
`Obstacle.toSet`, `CollisionFree`, `linkPose`, …) was touched. The executable core
(`Tensor.lean`, `Bernstein.lean`, `Kinematics.lean`, `Certificate.lean`, `Check.lean`,
`Main.lean`) has zero diff since L1: the proofs are about the code that runs, as it was.

## Dependency sketch

```
T1..T7 (tensor algebra) ✔ ─┬─►  B1 bernstein_nonneg ✔ ─┬─►  C2 outside leaf
                           │                           └─►  C3 collision leaf  ◄─ K1 (D > 0)
                           │                C1 coverage of the tiling ✔ ──┐
                           │                                              ▼
                           │                         S1 soundness  (IVT on φ ∘ γ)
                           └─►  K2 body_position ─► C4 ─► S2 soundness_ref
                                K3, K4: the rational parametrisation is a rotation
```

* **L2** (done): T1–T7, B0, B1, C1. Also `bernNonneg_sound` (`Soundness.lean`), not one of the
  19: the Bernstein test in the form the leaf checks call it (pad to the declared degree, then
  test), a corollary of T6 and B1.
* **L3**: C2, C3, S1; K1–K4, C4, S2.
* K1–K4, C4, S2 make the statement speak about real rigid motions instead of the polynomial
  pair `(N, D)`; S1 does not depend on them (see the remark below).

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

## Remarks on the statements

* **S1 is stated on the polynomial kinematics**, as required for L1: `CollisionFree` reads the
  world vertices as `eval N_k / eval D`. Its proof does not need the kinematic hypotheses tested
  by the checker (`q* = 0`, unit axes, `cos² + sin² = 1`): those hypotheses are what makes
  `(N, D)` *the forward kinematics of the declared chain* (K2–K4), and they enter through C4 / S2.
  Decision of the supervision (L1 review): the paper cites S2 `soundness_ref`; S1 is the
  technical core.
* **The path lives in `s`-space** (`s = tan (q/2)`), like the certificate. Translating a path in
  joint angles into a path in `s` (continuity of `tan (·/2)` on `(-π, π)`) is not stated here.
* **Start and goal are not required to lie in the box** (neither by `verify.py` nor here): if
  one of them is outside, no path "inside the box from start to goal" exists and the statement
  is vacuously true.
* **One body per certificate** (the schema has a single `body`); "every certified body" in the
  paper is that body.
* **B1 is stated at the tensor's own degree.** The checker pads to the working degree with
  `padTo?` first (T6); `bernNonneg_sound` puts the two together.
* **The reference definitions of the open part are still validated by reading and typing only**
  (`linkPose`, `rodrigues`, `CollisionFree`, …). L2 exercised `Tensor.eval`, `Tensor.coeff`,
  `flatIndex` and `Box.toSet`, and found them right: the statements T1–T7, B0, B1, C1 were
  provable as written.

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

`linkPose` is the reference kinematics: a composition of real rigid motions `translate(offset) ∘ rotate(axis, angle)`, defined without any polynomial (`rodrigues`, `Joint.rotation`, `Rigid`, `refStep`, `linkPose`, `unlockedUpTo` in the file). K1–K2 tie the polynomial numerators / denominator of the checker to it; K3–K4 tie the rational parametrisation to actual rotations. **All four are open (L3).**

### K1 — `bodyDenominator_pos` — open

The common denominator is positive everywhere.

```lean
theorem bodyDenominator_pos (n : ℕ) (chain : Array Joint) (link : ℕ) (s : Fin n → ℝ) :
    0 < (bodyDenominator n chain link).eval s
```

### K2 — `body_position` — open

The polynomial kinematics is the reference kinematics: the world position of the body-frame point `p` of link `link` is `eval (N·p) / eval D`.

```lean
theorem body_position (n : ℕ) (chain : Array Joint) (link : ℕ) (p : Vec3) (s : Fin n → ℝ)
    (hn : unlockedUpTo chain link ≤ n) (i : Fin 3) :
    (linkPose chain link s).apply (vecR p) i
      = ((bodyNumerators n chain link p)[i]).eval s / (bodyDenominator n chain link).eval s
```

### K3 — `rotation_half_angle` — open

The half-angle parametrisation is the rotation of angle `q`: with `s = tan (q/2)` and `|q| < π`, the rational expressions in `s` are `cos q` and `sin q`.

```lean
theorem rotation_half_angle (a : Vec3) (q : ℝ) (hq : |q| < Real.pi) :
    rodrigues a ((1 - Real.tan (q / 2) ^ 2) / (1 + Real.tan (q / 2) ^ 2))
        (2 * Real.tan (q / 2) / (1 + Real.tan (q / 2) ^ 2))
      = rodrigues a (Real.cos q) (Real.sin q)
```

### K4 — `rodrigues_mem_specialOrthogonal` — open

For a unit axis and `cos² + sin² = 1`, Rodrigues' matrix is a rotation (orthogonal, determinant `1`). This is where the hypotheses "exact unit axis" and "`cos² + sin² = 1`" of the checker are used.

```lean
theorem rodrigues_mem_specialOrthogonal (a : Vec3) (co si : ℝ)
    (ha : ((a[0] : ℝ)) ^ 2 + (a[1] : ℝ) ^ 2 + (a[2] : ℝ) ^ 2 = 1) (hcs : co ^ 2 + si ^ 2 = 1) :
    rodrigues a co si ∈ Matrix.specialOrthogonalGroup (Fin 3) ℝ
```

## Checks and main statement — `CnpVerify/Soundness.lean`

`CollisionFree c s` is defined from `bodyNumerators` / `bodyDenominator` and the H-representations only (no reference to the checker), through `Obstacle.toSet`, `Certificate.worldVertex` and `Certificate.bodyAt` (convex hull of the world vertices); `CollisionFreeRef` is the same notion on the reference kinematics. **C1 is proved (L2); C2, C3, C4, S1, S2 are open (L3).**

### C1 — `verifyCover_covers` — proved (L2)

COVERAGE of the tiling check: if `verifyCover` accepts, every point of the box lies in one of the cells. (Disjointness is also tested by the checker, as in `verify.py`, but the soundness proof only uses coverage.)

```lean
theorem verifyCover_covers {n : ℕ} (fuel : ℕ) (box : Box n) (cells : Array (Box n))
    (h : verifyCover fuel box cells = .ok ()) :
    ∀ x ∈ box.toSet, ∃ cell ∈ cells, x ∈ cell.toSet
```

### C2 — `checkOutsideLeaf_sound` — open

An accepted outside leaf is disjoint from the OPEN slab: `|φ| ≥ δ` on its cell.

```lean
theorem checkOutsideLeaf_sound (c : Certificate) (i : ℕ) (cell : Box c.n)
    (h : checkOutsideLeaf c i cell = .ok ()) :
    ∀ s ∈ cell.toSet, (c.delta : ℝ) ≤ |c.phi.eval s|
```

### C3 — `checkCollisionLeaf_sound` — open

An accepted collision leaf is in collision on the slab: at every point of its cell where `|φ| ≤ δ`, the certified body meets the named obstacle.

```lean
theorem checkCollisionLeaf_sound (c : Certificate) (i : ℕ) (cell : Box c.n) (obstacle : String)
    (lam : Array (Tensor c.n)) (mu : Array ℚ)
    (h : checkCollisionLeaf c c.geometry i cell obstacle lam mu = .ok ()) :
    ∀ s ∈ cell.toSet, |c.phi.eval s| ≤ (c.delta : ℝ) → ¬ CollisionFree c s
```

### C4 — `collisionFree_iff_ref` — open

Under the kinematic hypotheses tested by the checker, collision-freeness on the polynomial kinematics IS collision-freeness on the reference kinematics.

```lean
theorem collisionFree_iff_ref (c : Certificate) (h : checkKinematics c = .ok ())
    (s : Fin c.n → ℝ) : CollisionFree c s ↔ CollisionFreeRef c s
```

### S1 — `soundness` — open

**Soundness of the checker.** If `check c = true`, there is no continuous path `γ : [0,1] → ℝⁿ` that stays in the box, starts at `s_start`, ends at `s_goal`, and is collision-free at every time.

```lean
theorem soundness (c : Certificate) :
    check c = true →
      ¬ ∃ γ : C(unitInterval, Fin c.n → ℝ),
          (∀ t, γ t ∈ c.box.toSet) ∧ γ 0 = vecR c.sStart ∧ γ 1 = vecR c.sGoal
            ∧ ∀ t, CollisionFree c (γ t)
```

### S2 — `soundness_ref` — open

The same statement on the reference kinematics (corollary of S1 and C4).

```lean
theorem soundness_ref (c : Certificate) :
    check c = true →
      ¬ ∃ γ : C(unitInterval, Fin c.n → ℝ),
          (∀ t, γ t ∈ c.box.toSet) ∧ γ 0 = vecR c.sStart ∧ γ 1 = vecR c.sGoal
            ∧ ∀ t, CollisionFreeRef c (γ t)
```
