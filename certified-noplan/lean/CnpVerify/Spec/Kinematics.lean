/-
CnpVerify.Spec.Kinematics — reference kinematics over `ℝ` (definitions: L1; K1–K4 proved in L3).

The checker manipulates polynomial numerators `N` and a denominator `D`. This file states what
they mean: the world position of a body-frame point `p` of a link is `eval (N·p) / eval D`,
where the reference position is obtained by composing, along the chain, real rigid motions
`translate(offset) ∘ rotate(axis, angle)` — with NO polynomial in sight. For an unlocked joint
the angle `q` is parametrised by `s = tan (q/2)`, i.e. `cos q = (1-s²)/(1+s²)` and
`sin q = 2s/(1+s²)`; for a locked joint the rational `(cos, sin)` of the certificate is used.
-/
import Mathlib
import CnpVerify.Kinematics
import CnpVerify.Spec.Tensor

namespace CnpVerify

/-- A rational vector seen in `ℝᵐ`. -/
def vecR {m : ℕ} (v : Vector ℚ m) : Fin m → ℝ := fun i => (v[i] : ℝ)

/-- The cross-product matrix of `a` over `ℝ`. -/
def skewR (a : Vec3) : Matrix (Fin 3) (Fin 3) ℝ := Matrix.of fun i j => (skew a i j : ℝ)

/-- Rodrigues' formula `I + sin·K + (1 - cos)·K²`: for a unit axis `a` and
`cos² + sin² = 1`, the rotation about `a` by the angle of cosine `co` and sine `si`. -/
def rodrigues (a : Vec3) (co si : ℝ) : Matrix (Fin 3) (Fin 3) ℝ :=
  1 + si • skewR a + (1 - co) • (skewR a * skewR a)

/-- Rotation of a joint. Unlocked: angle `q` with `s = tan (q/2)`. Locked: the fixed rational
`(cos, sin)` (the value of `s` is ignored). -/
noncomputable def Joint.rotation (j : Joint) (s : ℝ) : Matrix (Fin 3) (Fin 3) ℝ :=
  match j.locked with
  | none => rodrigues j.axis ((1 - s ^ 2) / (1 + s ^ 2)) (2 * s / (1 + s ^ 2))
  | some (co, si) => rodrigues j.axis (co : ℝ) (si : ℝ)

/-- A rigid motion `y ↦ R y + t` of `ℝ³`. -/
structure Rigid where
  rot : Matrix (Fin 3) (Fin 3) ℝ
  trans : Fin 3 → ℝ

/-- Action on a point. -/
def Rigid.apply (g : Rigid) (y : Fin 3 → ℝ) : Fin 3 → ℝ := g.rot.mulVec y + g.trans

/-- `g.comp h` is "`h` first, then `g`". -/
def Rigid.comp (g h : Rigid) : Rigid := ⟨g.rot * h.rot, g.rot.mulVec h.trans + g.trans⟩

/-- Accumulation state of the reference chain: pose so far, next free variable. -/
structure RefState where
  pose : Rigid
  nextVar : ℕ

/-- One joint: `pose ← pose ∘ translate(offset) ∘ rotate`. An unlocked joint reads the next
variable (a variable index `≥ n` reads `0`; the checker excludes that case). -/
noncomputable def refStep {n : ℕ} (s : Fin n → ℝ) (st : RefState) (j : Joint) : RefState :=
  let sVal : ℝ := if h : st.nextVar < n then s ⟨st.nextVar, h⟩ else 0
  let pose := st.pose.comp ⟨j.rotation sVal, vecR j.offset⟩
  match j.locked with
  | none => ⟨pose, st.nextVar + 1⟩
  | some _ => ⟨pose, st.nextVar⟩

/-- Reference world pose of link `link` at the configuration `s` (unlocked joints numbered
`0..n-1` in chain order): the composition of the joint motions `0..link`. -/
noncomputable def linkPose {n : ℕ} (chain : Array Joint) (link : ℕ) (s : Fin n → ℝ) : Rigid :=
  ((chain.extract 0 (link + 1)).foldl (refStep s) ⟨⟨1, 0⟩, 0⟩).pose

/-- Number of unlocked joints among joints `0..link`. -/
def unlockedUpTo (chain : Array Joint) (link : ℕ) : ℕ :=
  ((chain.extract 0 (link + 1)).filter (·.locked.isNone)).size

/-! ### The polynomials `2 s`, `2 s²`, `1 + s²` of a joint -/

/-- The value the checker's polynomials read for the variable of index `idx`: `s_idx`, and `1`
when the index is out of range (the exponent array of `unitExp` is then all zeros, so the
"monomial" is a constant). The reference kinematics reads `0` there (`refStep`); the two agree
on every index the chain actually uses as soon as `unlockedUpTo chain link ≤ n`. -/
noncomputable def varAt {n : ℕ} (s : Fin n → ℝ) (idx : ℕ) : ℝ :=
  if h : idx < n then s ⟨idx, h⟩ else 1

theorem eval_unit (n idx p : ℕ) (c : ℚ) (s : Fin n → ℝ) :
    (Tensor.monomial (unitExp n idx p) c : Tensor n).eval s = (c : ℝ) * varAt s idx ^ p := by
  rw [Tensor.eval_monomial]
  congr 1
  unfold varAt unitExp
  by_cases h : idx < n
  · rw [dite_eq_left h, Finset.prod_eq_single (⟨idx, h⟩ : Fin n)]
    · simp [Array.getD_eq_getD_getElem?, h]
    · intro b _ hb
      have : ¬ idx = b.val := fun hh => hb (Fin.ext hh.symm)
      simp [Array.getD_eq_getD_getElem?, this]
    · simp
  · rw [dite_eq_right h]
    simp only [one_pow]
    apply Finset.prod_eq_one
    intro b _
    have : ¬ idx = b.val := fun hh => h (hh ▸ b.isLt)
    simp [Array.getD_eq_getD_getElem?, this]

theorem eval_onePlusSq (n idx : ℕ) (s : Fin n → ℝ) :
    (onePlusSq n idx).eval s = 1 + varAt s idx ^ 2 := by
  unfold onePlusSq
  rw [Tensor.eval_add, Tensor.eval_const, eval_unit]
  simp

/-- [K1] The common denominator is positive everywhere.

Proof (L3): `D` is a product of factors `1 + s²` along the chain (invariant of the fold). No
hypothesis is needed: for a variable index out of range the factor is the constant `2`. -/
theorem bodyDenominator_pos (n : ℕ) (chain : Array Joint) (link : ℕ) (s : Fin n → ℝ) :
    0 < (bodyDenominator n chain link).eval s := by
  unfold bodyDenominator bodyFK
  rw [← Array.foldl_toList]
  refine foldl_list_induction _ _ _ (fun st : FKState n => 0 < st.den.eval s) ?_ ?_
  · simp [Tensor.eval_const]
  · intro j _ st hst
    unfold fkStep
    cases j.locked with
    | none =>
      simp only
      rw [Tensor.eval_mul, eval_onePlusSq]
      positivity
    | some _ => exact hst

/-! ### The polynomial matrices represent rigid motions

A `Mat4` evaluated at `s` is `d · [R t; 0 1]` for a real rigid motion `(R, t)` and a scalar `d`
(the common denominator so far). The product of polynomial matrices then represents the
composition of the motions, with the product of the scalars. -/

section Represents

variable {n : ℕ}

theorem Mat4.get_ofFn (f : Fin 4 → Fin 4 → Tensor n) (i j : Fin 4) :
    (Mat4.ofFn f).get i j = f i j := by
  simp [Mat4.get, Mat4.ofFn]

/-- Entries of a product of polynomial matrices, evaluated. -/
theorem Mat4.eval_mul_get (A B : Mat4 n) (i j : Fin 4) (s : Fin n → ℝ) :
    ((A.mul B).get i j).eval s = ∑ k : Fin 4, (A.get i k).eval s * (B.get k j).eval s := by
  unfold Mat4.mul
  rw [Mat4.get_ofFn, Tensor.eval_foldl_add, Tensor.eval_zero, zero_add, Fin.sum_univ_def]
  simp only [Tensor.eval_mul]

/-- `M`, evaluated at `s`, is `d` times the homogeneous matrix `[R t; 0 1]` of the rigid
motion `g = (R, t)`. -/
structure Mat4.Represents (M : Mat4 n) (s : Fin n → ℝ) (d : ℝ) (g : Rigid) : Prop where
  rot : ∀ i j : Fin 3, (M.get i.castSucc j.castSucc).eval s = d * g.rot i j
  trans : ∀ i : Fin 3, (M.get i.castSucc (Fin.last 3)).eval s = d * g.trans i
  bot : ∀ j : Fin 3, (M.get (Fin.last 3) j.castSucc).eval s = 0
  corner : (M.get (Fin.last 3) (Fin.last 3)).eval s = d

theorem Mat4.Represents.mul {A B : Mat4 n} {s : Fin n → ℝ} {d e : ℝ} {g h : Rigid}
    (hA : A.Represents s d g) (hB : B.Represents s e h) :
    (A.mul B).Represents s (d * e) (g.comp h) := by
  constructor
  · intro i j
    rw [Mat4.eval_mul_get, Fin.sum_univ_castSucc]
    simp only [hA.rot, hB.rot, hA.trans, hB.bot, Rigid.comp, Matrix.mul_apply, Finset.mul_sum]
    rw [mul_zero, add_zero]
    exact Finset.sum_congr rfl fun k _ => by ring
  · intro i
    rw [Mat4.eval_mul_get, Fin.sum_univ_castSucc]
    simp only [hA.rot, hB.trans, hA.trans, hB.corner, Rigid.comp, Matrix.mulVec, dotProduct,
      Pi.add_apply, mul_add, Finset.mul_sum]
    congr 1
    · exact Finset.sum_congr rfl fun k _ => by ring
    · ring
  · intro j
    rw [Mat4.eval_mul_get, Fin.sum_univ_castSucc]
    simp only [hA.bot, hB.bot, zero_mul, mul_zero, Finset.sum_const_zero, add_zero]
  · rw [Mat4.eval_mul_get, Fin.sum_univ_castSucc]
    simp only [hA.bot, hA.corner, hB.corner, zero_mul, Finset.sum_const_zero, zero_add]

theorem castSucc_ne_three (i : Fin 3) : i.castSucc ≠ (3 : Fin 4) := Fin.castSucc_ne_last i

theorem represents_one (s : Fin n → ℝ) : (Mat4.one : Mat4 n).Represents s 1 ⟨1, 0⟩ := by
  constructor
  · intro i j
    by_cases hij : i = j <;>
      simp [Mat4.one, Mat4.get_ofFn, Tensor.eval_const, Tensor.eval_zero, Matrix.one_apply, hij]
  · intro i
    simp [Mat4.one, Mat4.get_ofFn, Tensor.eval_zero, castSucc_ne_three i]
  · intro j
    simp [Mat4.one, Mat4.get_ofFn, Tensor.eval_zero, (castSucc_ne_three j).symm]
  · simp [Mat4.one, Mat4.get_ofFn, Tensor.eval_const]

theorem represents_trans (o : Vec3) (s : Fin n → ℝ) :
    (transHomog n o).Represents s 1 ⟨1, vecR o⟩ := by
  constructor
  · intro i j
    by_cases hij : i = j
    · simp [transHomog, Mat4.get_ofFn, Tensor.eval_const, Matrix.one_apply, hij]
    · have hj : ¬ (j : ℕ) = 3 := j.isLt.ne
      simp [transHomog, Mat4.get_ofFn, Tensor.eval_zero, hij, hj]
  · intro i
    simp [transHomog, Mat4.get_ofFn, Tensor.eval_const, castSucc_ne_three i, vecR]
  · intro j
    simp [transHomog, Mat4.get_ofFn, Tensor.eval_zero, (castSucc_ne_three j).symm]
  · simp [transHomog, Mat4.get_ofFn, Tensor.eval_const]

theorem skewR_apply (a : Vec3) (i j : Fin 3) : skewR a i j = ((skew a i j : ℚ) : ℝ) := rfl

/-- `skewSq` is the square of the cross-product matrix. -/
theorem skewR_mul_self_apply (a : Vec3) (i j : Fin 3) :
    (skewR a * skewR a) i j = ((skewSq a i j : ℚ) : ℝ) := by
  unfold skewSq
  rw [Tensor.foldl_add_eq_sum, zero_add, ← Fin.sum_univ_def, Matrix.mul_apply]
  push_cast
  rfl

theorem represents_rot_locked (a : Vec3) (idx : ℕ) (co si : ℚ) (s : Fin n → ℝ) :
    (rotHomog n a idx (some (co, si))).Represents s 1 ⟨rodrigues a (co : ℝ) (si : ℝ), 0⟩ := by
  constructor
  · intro i j
    simp only [rotHomog, Mat4.get_ofFn, Fin.val_castSucc, i.isLt, j.isLt, and_self, dite_true,
      Tensor.eval_const, one_mul, rodrigues, Matrix.add_apply, Matrix.smul_apply, smul_eq_mul,
      Matrix.one_apply, skewR_mul_self_apply, skewR_apply, Fin.castSucc_inj, Fin.eta]
    push_cast
    by_cases hij : i = j <;> simp [hij]
  · intro i
    have hi : ¬ (i : ℕ) = 3 := i.isLt.ne
    simp [rotHomog, Mat4.get_ofFn, Tensor.eval_zero, hi]
  · intro j
    have hj : ¬ (j : ℕ) = 3 := j.isLt.ne
    simp [rotHomog, Mat4.get_ofFn, Tensor.eval_zero, hj]
  · simp [rotHomog, Mat4.get_ofFn, Tensor.eval_const]

theorem represents_rot_unlocked (a : Vec3) (idx : ℕ) (s : Fin n → ℝ) :
    (rotHomog n a idx none).Represents s (1 + varAt s idx ^ 2)
      ⟨rodrigues a ((1 - varAt s idx ^ 2) / (1 + varAt s idx ^ 2))
        (2 * varAt s idx / (1 + varAt s idx ^ 2)), 0⟩ := by
  have hpos : (1 + varAt s idx ^ 2) ≠ 0 := by positivity
  constructor
  · intro i j
    simp only [rotHomog, Mat4.get_ofFn, Fin.val_castSucc, i.isLt, j.isLt, and_self, dite_true,
      Tensor.eval_add, Tensor.eval_scale, eval_unit, rodrigues, Matrix.add_apply,
      Matrix.smul_apply, smul_eq_mul, Matrix.one_apply, skewR_mul_self_apply, skewR_apply,
      Fin.castSucc_inj, Fin.eta]
    by_cases hij : i = j
    · simp only [hij, ite_true, eval_onePlusSq]
      field_simp
      push_cast
      ring
    · simp only [hij, ite_false, Tensor.eval_zero]
      field_simp
      push_cast
      ring
  · intro i
    have hi : ¬ (i : ℕ) = 3 := i.isLt.ne
    simp [rotHomog, Mat4.get_ofFn, Tensor.eval_zero, hi]
  · intro j
    have hj : ¬ (j : ℕ) = 3 := j.isLt.ne
    simp [rotHomog, Mat4.get_ofFn, Tensor.eval_zero, hj]
  · simp [rotHomog, Mat4.get_ofFn, eval_onePlusSq]

theorem Mat4.Represents.congr {M : Mat4 n} {s : Fin n → ℝ} {d d' : ℝ} {g g' : Rigid}
    (h : M.Represents s d g) (hd : d = d') (hg : g = g') : M.Represents s d' g' :=
  hd ▸ hg ▸ h

/-- One joint: the polynomial step and the reference step stay in correspondence, provided an
unlocked joint reads a variable index `< n`. -/
theorem fkStep_represents (s : Fin n → ℝ) (j : Joint) (st : FKState n) (rs : RefState)
    (hvar : st.nextVar = rs.nextVar)
    (hrep : st.pose.Represents s (st.den.eval s) rs.pose)
    (hlt : j.locked = none → rs.nextVar < n) :
    (fkStep n st j).nextVar = (refStep s rs j).nextVar
      ∧ (fkStep n st j).pose.Represents s ((fkStep n st j).den.eval s) (refStep s rs j).pose := by
  rcases hj : j.locked with _ | ⟨co, si⟩
  · have hlt' := hlt hj
    have hv : varAt s st.nextVar = s ⟨rs.nextVar, hlt'⟩ := by
      simp [varAt, hvar, hlt']
    refine ⟨by simp [fkStep, refStep, hj, hvar], ?_⟩
    simp only [fkStep, refStep, hj, Joint.homog, Joint.rotation, dite_eq_left hlt']
    refine (hrep.mul ((represents_trans j.offset s).mul
      (represents_rot_unlocked j.axis st.nextVar s))).congr ?_ ?_
    · rw [Tensor.eval_mul, eval_onePlusSq, one_mul]
    · simp [Rigid.comp, hv]
  · refine ⟨by simp [fkStep, refStep, hj, hvar], ?_⟩
    simp only [fkStep, refStep, hj, Joint.homog, Joint.rotation]
    refine (hrep.mul ((represents_trans j.offset s).mul
      (represents_rot_locked j.axis st.nextVar co si s))).congr ?_ ?_
    · rw [one_mul, mul_one]
    · simp [Rigid.comp]

theorem refStep_nextVar (s : Fin n → ℝ) (rs : RefState) (j : Joint) :
    (refStep s rs j).nextVar = rs.nextVar + (if j.locked.isNone then 1 else 0) := by
  unfold refStep
  cases j.locked <;> simp

/-- The invariant along the chain. -/
theorem fkFold_represents (s : Fin n → ℝ) (l : List Joint) (st : FKState n) (rs : RefState)
    (hvar : st.nextVar = rs.nextVar)
    (hrep : st.pose.Represents s (st.den.eval s) rs.pose)
    (hcount : rs.nextVar + (l.filter (·.locked.isNone)).length ≤ n) :
    (l.foldl (fkStep n) st).pose.Represents s ((l.foldl (fkStep n) st).den.eval s)
      (l.foldl (refStep s) rs).pose := by
  induction l generalizing st rs with
  | nil => exact hrep
  | cons j l ih =>
    simp only [List.foldl_cons]
    have hlt : j.locked = none → rs.nextVar < n := by
      intro hj
      simp [hj] at hcount
      omega
    obtain ⟨h1, h2⟩ := fkStep_represents s j st rs hvar hrep hlt
    refine ih _ _ h1 h2 ?_
    rw [refStep_nextVar]
    by_cases hj : j.locked.isNone <;> simp [hj] at hcount ⊢ <;> omega

end Represents

/-- [K2] The polynomial kinematics is the reference kinematics: the world position of the
body-frame point `p` of link `link` is `eval (N·p) / eval D`.

Proof (L3): along the chain, the pose numerator matrix of the checker evaluated at `s` is `D(s)`
times the homogeneous matrix of the reference pose (`fkFold_represents`, by induction on the
joints: `Trans(offset) · Rot` on one side, `translate(offset) ∘ rotate` on the other, the factor
`1 + s²` of an unlocked joint going to `D`). The hypothesis `unlockedUpTo chain link ≤ n` is what
makes every unlocked joint of the chain read an actual variable: beyond `n`, the checker's
polynomials read the constant `1` and the reference reads `0`. `D(s) ≠ 0` is K1. -/
theorem body_position (n : ℕ) (chain : Array Joint) (link : ℕ) (p : Vec3) (s : Fin n → ℝ)
    (hn : unlockedUpTo chain link ≤ n) (i : Fin 3) :
    (linkPose chain link s).apply (vecR p) i
      = ((bodyNumerators n chain link p)[i]).eval s / (bodyDenominator n chain link).eval s := by
  have hD := bodyDenominator_pos n chain link s
  have hrep : (bodyPose n chain link).Represents s ((bodyDenominator n chain link).eval s)
      (linkPose chain link s) := by
    unfold bodyPose bodyDenominator bodyFK linkPose
    rw [← Array.foldl_toList, ← Array.foldl_toList]
    refine fkFold_represents s _ _ _ rfl ?_ ?_
    · simpa [Tensor.eval_const] using represents_one (n := n) s
    · change 0 + _ ≤ n
      rw [Nat.zero_add, ← Array.toList_filter, Array.length_toList]
      exact hn
  rw [eq_div_iff hD.ne']
  have e0 : ((bodyPose n chain link).get ⟨i.val, by omega⟩ 0).eval s = _ := hrep.rot i 0
  have e1 : ((bodyPose n chain link).get ⟨i.val, by omega⟩ 1).eval s = _ := hrep.rot i 1
  have e2 : ((bodyPose n chain link).get ⟨i.val, by omega⟩ 2).eval s = _ := hrep.rot i 2
  have e3 : ((bodyPose n chain link).get ⟨i.val, by omega⟩ 3).eval s = _ := hrep.trans i
  simp only [bodyNumerators, vertexNumerators, Fin.getElem_fin, Vector.getElem_ofFn,
    Tensor.eval_add, Tensor.eval_scale, Rigid.apply, Matrix.mulVec, dotProduct,
    Fin.sum_univ_three, Pi.add_apply, vecR, e0, e1, e2, e3, Fin.val_zero, Fin.val_one,
    Fin.val_two]
  ring

/-- [K3] The half-angle parametrisation is the rotation of angle `q`: with `s = tan (q/2)` and
`|q| < π`, the rational expressions in `s` are `cos q` and `sin q`.

Proof (L3): Mathlib's `Real.cos_eq_two_mul_tan_half_div_one_sub_tan_half_sq` (which needs
`cos q ≠ -1`, i.e. `|q| < π` here) and `Real.sin_eq_two_mul_tan_half_div_one_add_tan_half_sq`. -/
theorem rotation_half_angle (a : Vec3) (q : ℝ) (hq : |q| < Real.pi) :
    rodrigues a ((1 - Real.tan (q / 2) ^ 2) / (1 + Real.tan (q / 2) ^ 2))
        (2 * Real.tan (q / 2) / (1 + Real.tan (q / 2) ^ 2))
      = rodrigues a (Real.cos q) (Real.sin q) := by
  have hcos : Real.cos q ≠ -1 := by
    have h : Real.cos Real.pi < Real.cos |q| :=
      Real.cos_lt_cos_of_nonneg_of_le_pi (abs_nonneg q) le_rfl hq
    rw [Real.cos_pi, Real.cos_abs] at h
    exact ne_of_gt h
  rw [← Real.cos_eq_two_mul_tan_half_div_one_sub_tan_half_sq q hcos,
    ← Real.sin_eq_two_mul_tan_half_div_one_add_tan_half_sq q]

/-- `|a|²` over `ℝ`. -/
def normSqR (a : Vec3) : ℝ := (a[0] : ℝ) ^ 2 + (a[1] : ℝ) ^ 2 + (a[2] : ℝ) ^ 2

/-- `R Rᵀ` for Rodrigues' matrix, as a polynomial identity (no hypothesis): the defect from the
identity is a multiple of `K²` whose coefficient vanishes when `|a| = 1` and `cos² + sin² = 1`. -/
theorem rodrigues_mul_transpose (a : Vec3) (co si : ℝ) :
    rodrigues a co si * (rodrigues a co si).transpose
      = 1 + ((1 - co ^ 2 - si ^ 2) - (normSqR a - 1) * (1 - co) ^ 2) • (skewR a * skewR a) := by
  ext i j
  fin_cases i <;> fin_cases j <;>
    simp [rodrigues, skewR, skew, normSqR, Matrix.mul_apply, Fin.sum_univ_three,
      Matrix.one_apply] <;>
    ring

/-- The determinant of Rodrigues' matrix, as a polynomial identity (no hypothesis). -/
theorem rodrigues_det (a : Vec3) (co si : ℝ) :
    (rodrigues a co si).det = (1 - (1 - co) * normSqR a) ^ 2 + si ^ 2 * normSqR a := by
  simp only [Matrix.det_fin_three, rodrigues, skewR, skew, normSqR, Matrix.mul_apply,
    Fin.sum_univ_three, Matrix.add_apply, Matrix.smul_apply, Matrix.one_apply, Matrix.of_apply,
    smul_eq_mul]
  simp
  ring

/-- [K4] For a unit axis and `cos² + sin² = 1`, Rodrigues' matrix is a rotation (orthogonal,
determinant `1`). This is where the hypotheses "exact unit axis" and "`cos² + sin² = 1`" of
the checker are used.

Proof (L3): the two polynomial identities above, then the two hypotheses. -/
theorem rodrigues_mem_specialOrthogonal (a : Vec3) (co si : ℝ)
    (ha : ((a[0] : ℝ)) ^ 2 + (a[1] : ℝ) ^ 2 + (a[2] : ℝ) ^ 2 = 1) (hcs : co ^ 2 + si ^ 2 = 1) :
    rodrigues a co si ∈ Matrix.specialOrthogonalGroup (Fin 3) ℝ := by
  rw [Matrix.mem_specialOrthogonalGroup_iff, Matrix.mem_orthogonalGroup_iff]
  have ha' : normSqR a = 1 := ha
  refine ⟨?_, ?_⟩
  · have h0 : (1 - co ^ 2 - si ^ 2) - (normSqR a - 1) * (1 - co) ^ 2 = 0 := by
      rw [ha']
      linear_combination -hcs
    rw [rodrigues_mul_transpose, h0, zero_smul, add_zero]
  · rw [rodrigues_det, ha']
    linear_combination hcs

/-! ### Reading aids for the reference definitions (not among the 19 obligations)

`skew` is a hand-written sign table shared by the checker and by `skewR`. The lemmas below tie
it to Mathlib's cross product, so that `rodrigues` is Rodrigues' formula as usually written. -/

section CrossProduct

open Matrix

/-- The matrix `skewR a` is the cross product by `a` (Mathlib's `crossProduct`). -/
theorem skewR_mulVec (a : Vec3) (v : Fin 3 → ℝ) : (skewR a).mulVec v = vecR a ⨯₃ v := by
  ext i
  fin_cases i <;>
    simp [skewR, skew, Matrix.mulVec, dotProduct, Fin.sum_univ_three, cross_apply, vecR] <;> ring

/-- Rodrigues' formula in vector form: `R v = v + sin · (a × v) + (1 - cos) · a × (a × v)`. -/
theorem rodrigues_mulVec (a : Vec3) (co si : ℝ) (v : Fin 3 → ℝ) :
    (rodrigues a co si).mulVec v
      = v + si • (vecR a ⨯₃ v) + (1 - co) • (vecR a ⨯₃ (vecR a ⨯₃ v)) := by
  unfold rodrigues
  rw [Matrix.add_mulVec, Matrix.add_mulVec, Matrix.one_mulVec, Matrix.smul_mulVec,
    Matrix.smul_mulVec, ← Matrix.mulVec_mulVec, skewR_mulVec, skewR_mulVec]

/-- A Rodrigues matrix fixes its axis. -/
theorem rodrigues_mulVec_axis (a : Vec3) (co si : ℝ) :
    (rodrigues a co si).mulVec (vecR a) = vecR a := by
  rw [rodrigues_mulVec, cross_self]
  simp

end CrossProduct

/-- The rotation part of the reference pose after one more joint. -/
theorem refStep_pose_rot {n : ℕ} (s : Fin n → ℝ) (rs : RefState) (j : Joint) :
    (refStep s rs j).pose.rot
      = rs.pose.rot * j.rotation (if h : rs.nextVar < n then s ⟨rs.nextVar, h⟩ else 0) := by
  unfold refStep
  cases j.locked <;> rfl

end CnpVerify
