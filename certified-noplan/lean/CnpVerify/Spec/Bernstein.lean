/-
CnpVerify.Spec.Bernstein — what the Bernstein test proves (L1: statement only).

If every Bernstein coefficient of `p` over the box `b` is non-negative, then `p ≥ 0` on `b`.
Target of L2 (monomial-to-Bernstein identity by induction on the variables, from
`bernsteinPolynomial.sum` and the non-negativity of the univariate Bernstein polynomials on
`[0,1]`).
-/
import Mathlib
import CnpVerify.Bernstein
import CnpVerify.Spec.Tensor

namespace CnpVerify

variable {n : ℕ}

/-- The box as a subset of `ℝⁿ`: `{x | ∀ i, loᵢ ≤ xᵢ ≤ hiᵢ}`. -/
def Box.toSet (b : Box n) : Set (Fin n → ℝ) :=
  {x | ∀ i : Fin n, (b.lo i : ℝ) ≤ x i ∧ x i ≤ (b.hi i : ℝ)}

/-- [B0] The computable binomial coefficient is `Nat.choose`. -/
theorem binom_eq_choose (m k : ℕ) : binom m k = m.choose k := by
  sorry

/-- [B1] Soundness of the Bernstein test: non-negative Bernstein coefficients over the box `b`
(at the tensor's own degree) imply that the polynomial is non-negative on `b`. -/
theorem bernstein_nonneg (b : Box n) (p : Tensor n) :
    (bernsteinCoeffs b p).all (· ≥ 0) → ∀ x ∈ b.toSet, 0 ≤ p.eval x := by
  sorry

end CnpVerify
