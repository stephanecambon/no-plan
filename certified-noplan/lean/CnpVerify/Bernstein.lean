/-
CnpVerify.Bernstein — exact tensor-product Bernstein transform over a box (L1, executable).

Port of `verify.py` `_shift_matrix` / `_bern_matrix` / `_apply_axis` /
`_bernstein_control_points` / `_bern_all_nonneg`: per variable, the affine substitution
`s = lo + (hi - lo) x` followed by the monomial-to-Bernstein change of basis on `[0,1]` at
degree `d` (binomial formula). The soundness statement `bernstein_nonneg` (proved in L2) is in
`CnpVerify/Spec/Bernstein.lean`.
-/
import CnpVerify.Tensor

namespace CnpVerify

/-- Binomial coefficient `C(m, k)`, by the multiplicative recurrence
`C(m, k+1) = C(m, k) (m - k) / (k + 1)` (exact in `Nat`; `0` when `k > m`). -/
def binom (m : Nat) : Nat → Nat
  | 0 => 1
  | k + 1 => binom m k * (m - k) / (k + 1)

/-- A box `∏ᵢ [loᵢ, hiᵢ]` of `ℚⁿ`, as `n` pairs `(lo, hi)`. -/
abbrev Box (n : Nat) := Vector (Rat × Rat) n

namespace Box

variable {n : Nat}

/-- Lower bound along axis `i`. -/
def lo (b : Box n) (i : Fin n) : Rat := b[i].1

/-- Upper bound along axis `i`. -/
def hi (b : Box n) (i : Fin n) : Rat := b[i].2

/-- Midpoint along axis `i`. -/
def mid (b : Box n) (i : Fin n) : Rat := (b.lo i + b.hi i) / 2

end Box

/-- A dense `(d+1) × (d+1)` rational matrix, row-major (`M[q][p]`). -/
abbrev RatMatrix := Array (Array Rat)

/-- `S[q][p] = C(p,q) lo^(p-q) (hi-lo)^q` for `q ≤ p`: monomial coefficients of
`a(lo + (hi-lo) x)` from those of `a(s)`, in one variable, at degree `d`. -/
def shiftMatrix (d : Nat) (lo hi : Rat) : RatMatrix :=
  let w := hi - lo
  Array.ofFn (n := d + 1) fun q => Array.ofFn (n := d + 1) fun p =>
    if q.val ≤ p.val then (binom p.val q.val : Rat) * lo ^ (p.val - q.val) * w ^ q.val else 0

/-- `B[i][j] = C(i,j) / C(d,j)` for `j ≤ i`: Bernstein coefficients on `[0,1]` at degree `d`
from monomial coefficients. -/
def bernMatrix (d : Nat) : RatMatrix :=
  Array.ofFn (n := d + 1) fun i => Array.ofFn (n := d + 1) fun j =>
    if j.val ≤ i.val then (binom i.val j.val : Rat) / (binom d j.val : Rat) else 0

/-- Product of two square matrices of size `d+1`. -/
def matMul (d : Nat) (A B : RatMatrix) : RatMatrix :=
  Array.ofFn (n := d + 1) fun i => Array.ofFn (n := d + 1) fun j =>
    (List.range (d + 1)).foldl (init := 0) fun acc t =>
      acc + (A.getD i.val #[]).getD t 0 * (B.getD t #[]).getD j.val 0

/-- Apply the matrix `M` along axis `ax` of a dense coefficient array of layout `(d+1)^n`
(the `_apply_axis` of `verify.py`: only nonzero entries contribute). -/
def applyAxis (n d : Nat) (coeffs : Array Rat) (ax : Nat) (M : RatMatrix) : Array Rat := Id.run do
  let base := d + 1
  let stride := base ^ (n - 1 - ax)
  let total := base ^ n
  let mut out := Array.replicate total (0 : Rat)
  for idx in [0:total] do
    let c := coeffs.getD idx 0
    if c != 0 then
      let p := (idx / stride) % base
      let idx0 := idx - p * stride
      for q in [0:base] do
        let m := (M.getD q #[]).getD p 0
        if m != 0 then
          let j := idx0 + q * stride
          out := out.set! j (out.getD j 0 + m * c)
  return out

/-- Bernstein coefficients of `p` over the box `b`, at the tensor's own degree `p.deg` in every
variable (dense array of `(p.deg+1)^n` control points, same layout as the coefficients). -/
def bernsteinCoeffs {n : Nat} (b : Box n) (p : Tensor n) : Array Rat := Id.run do
  let d := p.deg
  let B := bernMatrix d
  let mut cur := Array.ofFn (n := (d + 1) ^ n) fun i => p.coeffs.getD i.val 0
  for h : ax in [0:n] do
    let i : Fin n := ⟨ax, h.2.1⟩
    cur := applyAxis n d cur ax (matMul d B (shiftMatrix d (b.lo i) (b.hi i)))
  return cur

/-- All control points are `≥ 0`. -/
def allNonneg (cp : Array Rat) : Bool := cp.all (fun v => decide (0 ≤ v))

end CnpVerify
