/-
CnpVerify.Spec.Tensor — reference semantics of coefficient tensors (L1: statements only).

`Tensor.eval` is the real-valued polynomial function a tensor denotes. It is NONCOMPUTABLE and
is never run: it only appears in statements. Every `sorry` below is a proof obligation listed
in `lean/PROOF-OBLIGATIONS.md`.
-/
import Mathlib
import CnpVerify.Tensor

namespace CnpVerify

namespace Tensor

variable {n : ℕ}

/-- The real number denoted by the tensor `t` at the point `x`:
`Σ_e coeff(e) · ∏ᵢ xᵢ^eᵢ`, the sum ranging over all exponent vectors `e ∈ {0..deg}ⁿ`. -/
noncomputable def eval (t : Tensor n) (x : Fin n → ℝ) : ℝ :=
  ∑ e : Fin n → Fin (t.deg + 1), (t.coeff (fun i => (e i).val) : ℝ) * ∏ i, x i ^ (e i).val

/-- [T1] The computable rational evaluation agrees with the reference semantics. -/
theorem evalQ_cast (t : Tensor n) (x : Fin n → ℚ) :
    ((t.evalQ x : ℚ) : ℝ) = t.eval (fun i => (x i : ℝ)) := by
  sorry

/-- [T2] The constant tensor denotes the constant function. -/
theorem eval_const (c : ℚ) (x : Fin n → ℝ) : (Tensor.const c : Tensor n).eval x = (c : ℝ) := by
  sorry

/-- [T3] `add` denotes the pointwise sum. -/
theorem eval_add (a b : Tensor n) (x : Fin n → ℝ) : (a + b).eval x = a.eval x + b.eval x := by
  sorry

/-- [T4] `scale` denotes the multiplication by a constant. -/
theorem eval_scale (a : Tensor n) (c : ℚ) (x : Fin n → ℝ) :
    (a.scale c).eval x = (c : ℝ) * a.eval x := by
  sorry

/-- [T5] `mul` denotes the pointwise product. -/
theorem eval_mul (a b : Tensor n) (x : Fin n → ℝ) : (a * b).eval x = a.eval x * b.eval x := by
  sorry

/-- [T6] Degree padding does not change the polynomial. -/
theorem eval_padTo (t q : Tensor n) (d : ℕ) (h : t.padTo? d = some q) (x : Fin n → ℝ) :
    q.eval x = t.eval x := by
  sorry

/-- [T7] `beqPoly` is sound: tensors it identifies denote the same function. -/
theorem eval_eq_of_beqPoly (a b : Tensor n) (h : a.beqPoly b = true) (x : Fin n → ℝ) :
    a.eval x = b.eval x := by
  sorry

end Tensor

end CnpVerify
