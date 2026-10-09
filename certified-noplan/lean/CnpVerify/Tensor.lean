/-
CnpVerify.Tensor — dense rational coefficient tensors (L1, executable, no proof).

A polynomial in `n` variables with degree at most `deg` in EACH variable is stored as the
dense array of its `(deg+1)^n` rational coefficients. The coefficient of
`s₀^e₀ ⋯ s_{n-1}^e_{n-1}` sits at the flat index `Σᵢ eᵢ (deg+1)^(n-1-i)` (first variable most
significant): this is the C-order of the numpy tensors of shape `(deg+1,)*n` in `polylin.py`,
and the exponent tuples `(e₀,…,e_{n-1})` of the sparse dictionaries of `verify.py`.

This file is deliberately Mathlib-free (core `Rat` only) so that the executable does not link
Mathlib. The real-valued reference semantics `Tensor.eval` lives in `CnpVerify/Spec/Tensor.lean`.
-/

namespace CnpVerify

/-- Dense tensor of rational coefficients: `n` variables, degree `≤ deg` per variable.
Reads outside `coeffs` return `0`, so every value of this type denotes a polynomial. -/
structure Tensor (n : Nat) where
  /-- Per-variable degree bound of the storage layout. -/
  deg : Nat
  /-- The `(deg+1)^n` coefficients in C order (first variable most significant). -/
  coeffs : Array Rat
  deriving Repr

namespace Tensor

variable {n : Nat}

/-- Flat index of the exponent vector `e` in a layout of base `base = deg+1` (Horner, first
variable most significant). -/
def flatIndex (base : Nat) (e : Fin n → Nat) : Nat :=
  Fin.foldl n (fun acc i => acc * base + e i) 0

/-- Same as `flatIndex`, on an exponent array (missing entries read as `0`). -/
def encode (n base : Nat) (e : Array Nat) : Nat :=
  Nat.fold n (fun i _ acc => acc * base + e.getD i 0) 0

/-- Exponent array (length `n`) of the flat index `idx` in base `base`. -/
def decode (n base idx : Nat) : Array Nat := Id.run do
  let mut out := Array.replicate n 0
  let mut r := idx
  for k in [0:n] do
    let i := n - 1 - k
    out := out.set! i (r % base)
    r := r / base
  return out

/-- Coefficient of the monomial of exponent vector `e` (`0` outside the layout). -/
def coeff (t : Tensor n) (e : Fin n → Nat) : Rat :=
  if (List.finRange n).all (fun i => e i ≤ t.deg) then
    t.coeffs.getD (flatIndex (t.deg + 1) e) 0
  else 0

/-- The zero polynomial. -/
def zero : Tensor n := ⟨0, #[0]⟩

/-- The constant polynomial `c`. -/
def const (c : Rat) : Tensor n := ⟨0, #[c]⟩

instance : Inhabited (Tensor n) := ⟨zero⟩

/-- Nonzero terms as `(exponent array, coefficient)`, in increasing flat index. -/
def support (t : Tensor n) : Array (Array Nat × Rat) := Id.run do
  let base := t.deg + 1
  let mut out := #[]
  for idx in [0:base ^ n] do
    let c := t.coeffs.getD idx 0
    if c != 0 then
      out := out.push (decode n base idx, c)
  return out

/-- Per-variable maximal exponent over a list of terms. -/
def varDegsOf (n : Nat) (terms : Array (Array Nat × Rat)) : Array Nat := Id.run do
  let mut out := Array.replicate n 0
  for (e, _) in terms do
    for i in [0:n] do
      if e.getD i 0 > out.getD i 0 then
        out := out.set! i (e.getD i 0)
  return out

/-- Largest entry of a degree array (`0` if empty). -/
def maxDeg (ds : Array Nat) : Nat := ds.foldl max 0

/-- Dense tensor of degree `deg` from a list of terms (coefficients of equal exponents are
summed; a term with an exponent `> deg` is DROPPED — callers pass a sufficient `deg`). -/
def ofTerms (deg : Nat) (terms : Array (Array Nat × Rat)) : Tensor n := Id.run do
  let base := deg + 1
  let mut out := Array.replicate (base ^ n) (0 : Rat)
  for (e, c) in terms do
    if (Array.range n).all (fun i => e.getD i 0 ≤ deg) then
      let idx := encode n base e
      out := out.set! idx (out.getD idx 0 + c)
  return ⟨deg, out⟩

/-- The monomial `c · s^e` (stored at degree `max e`). -/
def monomial (e : Array Nat) (c : Rat) : Tensor n :=
  ofTerms (maxDeg (e.extract 0 n)) #[(e, c)]

/-- Effective per-variable degree: largest exponent carried by a nonzero coefficient. -/
def effDeg (t : Tensor n) : Nat := maxDeg (varDegsOf n t.support)

/-- The same polynomial stored at the smallest possible degree. Canonical form: two tensors
denote the same polynomial iff their `trim`s are structurally equal. -/
def trim (t : Tensor n) : Tensor n :=
  let s := t.support
  ofTerms (maxDeg (varDegsOf n s)) s

/-- Degree padding: the same polynomial stored at degree `d`, or `none` if a nonzero coefficient
has an exponent `> d` (the "degree exceeds the declared Bernstein degree" rejection of
`verify.py`, which tests the support of its sparse dictionary). -/
def padTo? (t : Tensor n) (d : Nat) : Option (Tensor n) :=
  let s := t.support
  if maxDeg (varDegsOf n s) ≤ d then some (ofTerms d s) else none

/-- Polynomial sum (result in canonical form). -/
def add (a b : Tensor n) : Tensor n :=
  let s := a.support ++ b.support
  (ofTerms (maxDeg (varDegsOf n s)) s : Tensor n).trim

/-- Scaling by a rational constant (result in canonical form). -/
def scale (a : Tensor n) (c : Rat) : Tensor n :=
  if c == 0 then zero else
  let s := a.support.map (fun (e, v) => (e, c * v))
  ofTerms (maxDeg (varDegsOf n s)) s

/-- Opposite polynomial. -/
def neg (a : Tensor n) : Tensor n := a.scale (-1)

/-- Polynomial difference. -/
def sub (a b : Tensor n) : Tensor n := a.add b.neg

/-- Polynomial product (full convolution; result in canonical form). The working degree is the
tight bound `maxᵢ (degᵢ a + degᵢ b)`, so a product of polynomials in disjoint variables does not
inflate the layout. -/
def mul (a b : Tensor n) : Tensor n := Id.run do
  let sa := a.support
  let sb := b.support
  if sa.isEmpty || sb.isEmpty then return zero
  let da := varDegsOf n sa
  let db := varDegsOf n sb
  let d := maxDeg ((Array.range n).map (fun i => da.getD i 0 + db.getD i 0))
  let base := d + 1
  -- the flat index is linear in the exponents: idx(ea + eb) = idx(ea) + idx(eb)
  let ia := sa.map (fun (e, c) => (encode n base e, c))
  let ib := sb.map (fun (e, c) => (encode n base e, c))
  let mut out := Array.replicate (base ^ n) (0 : Rat)
  for (i, ca) in ia do
    for (j, cb) in ib do
      out := out.set! (i + j) (out.getD (i + j) 0 + ca * cb)
  return (⟨d, out⟩ : Tensor n).trim

instance : Add (Tensor n) := ⟨add⟩
instance : Sub (Tensor n) := ⟨sub⟩
instance : Mul (Tensor n) := ⟨mul⟩
instance : Neg (Tensor n) := ⟨neg⟩

/-- Equality AS POLYNOMIALS (independent of the storage degree). -/
def beqPoly (a b : Tensor n) : Bool :=
  let ta := a.trim
  let tb := b.trim
  ta.deg == tb.deg && ta.coeffs == tb.coeffs

/-- `true` iff the polynomial is identically zero. -/
def isZero (a : Tensor n) : Bool := a.coeffs.all (· == 0)

/-- Computable evaluation at a rational point (used by condition (i) and by the tests). -/
def evalQ (t : Tensor n) (x : Fin n → Rat) : Rat :=
  t.support.foldl (init := 0) fun acc (e, c) =>
    acc + (List.finRange n).foldl (init := c) fun term i => term * x i ^ e.getD i.val 0

end Tensor

end CnpVerify
