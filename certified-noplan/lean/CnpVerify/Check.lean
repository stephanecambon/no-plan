/-
CnpVerify.Check — the checker (L1, executable, no proof).

Port of the five checks of `verify.py`, IN THE ORDER `verify.verify` RUNS THEM:

  (0)  hypotheses: `δ > 0`, non-degenerate box                       (`checkAssumptions`)
  (i)  `φ(s_start) < -δ` and `φ(s_goal) > δ`, STRICT                  (`checkConditionI`)
  (ii) the leaf cells tile the box by midpoint bisections             (`checkPartition`)
  (0') hypotheses of the kinematics, tested where `verify._body_fk` tests them, i.e. AFTER
       (ii): `q* = 0`, exact unit axes, `n` = number of unlocked joints, `cos² + sin² = 1` for
       the locked joints of the body's chain                         (`checkKinematics`)
  (iii) outside leaves: `Bern(φ - δ) ≥ 0` or `Bern(-φ - δ) ≥ 0`, NON-strict (`checkOutsideLeaf`)
  (iv) collision leaves: `Σλ ≡ 1`, `Bern(λ_k) ≥ 0`, `μ_j ≥ 0`, `Bern(g_j - μ_j T) ≥ 0` with
       `g_j = b_j D - a_jᵀ Σ_k λ_k N_k` and `T = δ² - φ²` FORMED HERE     (`checkCollisionLeaf`)

Each check returns `Except Reject Unit`: success, or the reason of the rejection.
`check : Certificate → Bool` is the conjunction; it is the function the soundness theorem
(`CnpVerify/Soundness.lean`) is about.
-/
import CnpVerify.Certificate

namespace CnpVerify

/-- Checker monad: success or a rejection with its reason. -/
abbrev CheckM := Except Reject

def reject {α : Type} (code msg : String) (leaf : Option Nat := none)
    (index : Option Nat := none) : CheckM α :=
  throw { code, leaf, index, msg }

/-! ### (0) hypotheses -/

/-- (0) `δ > 0` and every interval of the box has `lo < hi`. (The two format gates of
`_check_assumptions` — theorem kind, kinematic substitution — and the shape of the obstacles
are enforced by the parser.) -/
def checkAssumptions (c : Certificate) : CheckM Unit := do
  if c.delta ≤ 0 then reject "delta_nonpos" "delta must be > 0"
  if (List.finRange c.n).any (fun i => c.box.hi i ≤ c.box.lo i) then
    reject "degenerate_box" "degenerate box bound"

/-! ### (i) start and goal are strictly on either side of the slab -/

/-- (i) `φ(s_start) < -δ` and `φ(s_goal) > δ`, both strict. -/
def checkConditionI (c : Certificate) : CheckM Unit := do
  if ¬ (c.phi.evalQ (fun i => c.sStart[i]) < -c.delta) then
    reject "cond_i_start" "phi(s_start) is not < -delta (condition i)"
  if ¬ (c.phi.evalQ (fun i => c.sGoal[i]) > c.delta) then
    reject "cond_i_goal" "phi(s_goal) is not > +delta (condition i)"

/-! ### (ii) the leaves tile the box -/

/-- Split `cells` at the midpoint of `box` along `ax`: cells wholly below, cells wholly above.
`none` if a cell straddles the midpoint, or if one side is empty. -/
def splitCells {n : Nat} (box : Box n) (cells : Array (Box n)) (ax : Fin n) :
    Option (Array (Box n) × Array (Box n)) :=
  let mid := box.mid ax
  let sides := cells.foldl (init := some (#[], #[])) fun acc cell =>
    match acc with
    | none => none
    | some (lower, upper) =>
      if cell.hi ax ≤ mid then some (lower.push cell, upper)
      else if mid ≤ cell.lo ax then some (lower, upper.push cell)
      else none
  match sides with
  | some (lower, upper) => if lower.isEmpty || upper.isEmpty then none else some (lower, upper)
  | none => none

/-- `_verify_cover`: `cells` is a disjoint exact cover of `box` obtained by midpoint bisections.
A single cell must BE the box; otherwise the FIRST axis whose midpoint separates the cells
cleanly (both sides non-empty) is taken and both halves are checked recursively. `fuel` bounds
the recursion depth; `cells.size` is always enough since both sides lose at least one cell. -/
def verifyCover {n : Nat} : Nat → Box n → Array (Box n) → CheckM Unit
  | 0, _, _ => reject "tiling_not_bisection" "cells do not tile the box (recursion bound reached)"
  | fuel + 1, box, cells =>
    if cells.size == 1 then
      if cells.getD 0 box == box then pure ()
      else reject "tiling_leaf_mismatch" "leaf cell does not match its region (gap/overlap)"
    else
      match (List.finRange n).findSome? (fun ax => (splitCells box cells ax).map (ax, ·)) with
      | some (ax, lower, upper) => do
        let mid := box.mid ax
        verifyCover fuel (box.set ax.val (box.lo ax, mid) ax.isLt) lower
        verifyCover fuel (box.set ax.val (mid, box.hi ax) ax.isLt) upper
      | none =>
        reject "tiling_not_bisection"
          "cells do not tile the box (not a midpoint-bisection partition)"

/-- (ii) the partition is non-empty and tiles the box. -/
def checkPartition (c : Certificate) : CheckM Unit := do
  let cells := c.leaves.map (·.cell)
  if cells.isEmpty then reject "empty_partition" "empty partition"
  verifyCover cells.size c.box cells

/-! ### (0') hypotheses of the kinematics -/

/-- `a · a`. -/
def normSq (a : Vec3) : Rat := a[0] * a[0] + a[1] * a[1] + a[2] * a[2]

/-- (0') `q* = 0`; every axis is an exact unit vector; `n` is the number of unlocked joints;
every locked joint of the body's chain has `cos² + sin² = 1`; the body link exists. -/
def checkKinematics (c : Certificate) : CheckM Unit := do
  if c.qStar.any (· != 0) then
    reject "qstar_nonzero" "nonzero q_star unsupported by the exact FK"
  if c.chain.any (fun j => normSq j.axis != 1) then
    reject "axis_not_unit" "spatial joint axis is not a unit vector (exact)"
  if (c.chain.filter (·.locked.isNone)).size != c.n then
    reject "n_mismatch" "robot n disagrees with the unlocked joint count"
  let badLock := (c.chain.extract 0 (c.bodyLink + 1)).any fun j =>
    match j.locked with
    | some (co, si) => co * co + si * si != 1
    | none => false
  if badLock then
    reject "lock_not_unit" "locked joint cos^2+sin^2 != 1 (not an exact rotation)"
  if c.bodyLink ≥ c.chain.size then
    reject "malformed" "malformed certificate (body link out of range)"

/-! ### (iii) and (iv) leaves -/

/-- What the leaf checks need from the kinematics: the world-position numerators `N_k` of the
body vertices and the common denominator `D`, both RECOMPUTED from the declared chain. -/
structure Geometry (n : Nat) where
  verts : Array (Vector (Tensor n) 3)
  den : Tensor n

def Certificate.geometry (c : Certificate) : Geometry c.n :=
  let st := bodyFK c.n c.chain c.bodyLink
  { verts := c.hull.map (vertexNumerators st.pose), den := st.den }

/-- All Bernstein coefficients of `p` over `cell`, at degree `d` per variable, are `≥ 0`.
Rejects if `p` has a nonzero coefficient of degree `> d`. -/
def bernNonneg {n : Nat} (p : Tensor n) (d : Nat) (cell : Box n) (leaf : Nat) : CheckM Bool :=
  match p.padTo? d with
  | none =>
    reject "degree_exceeds" "polynomial degree exceeds the declared Bernstein degree" (leaf := leaf)
  | some q => pure (allNonneg (bernsteinCoeffs cell q))

/-- (iii) an outside leaf is disjoint from the slab: `φ ≥ δ` on the cell or `φ ≤ -δ` on the
cell, each established by non-negative Bernstein coefficients (NON-strict). -/
def checkOutsideLeaf (c : Certificate) (i : Nat) (cell : Box c.n) : CheckM Unit := do
  let phiMinus := c.phi + Tensor.const (-c.delta)                    -- φ - δ
  if ← bernNonneg phiMinus c.phiDeg cell i then return
  let negPhiMinus := c.phi.scale (-1) + Tensor.const (-c.delta)      -- -φ - δ
  if ← bernNonneg negPhiMinus c.phiDeg cell i then return
  reject "outside_not_disjoint" "'outside' leaf is NOT disjoint from the slab" (leaf := i)

/-- (iv) a collision leaf certifies ONE pair (body, obstacle) on its cell.
The witness point is `x = Σ_k λ_k v_k` with `Σ_k λ_k ≡ 1` and `λ_k ≥ 0` on the cell; for each
face `aᵀ y ≤ b` of the obstacle, `g = b D - aᵀ Σ_k λ_k N_k` and the checker itself forms
`g - μ T` (the sign is its own) with `T = δ² - φ²`, at degree
`max (deg λ + 2) (2 · declared deg φ)`. -/
def checkCollisionLeaf (c : Certificate) (geo : Geometry c.n) (i : Nat) (cell : Box c.n)
    (obstacle : String) (lam : Array (Tensor c.n)) (mu : Array Rat) : CheckM Unit := do
  let some dLam := c.lamDeg
    | reject "malformed" "malformed certificate (lam_degree missing or unknown)" (leaf := i)
  if lam.size != geo.verts.size then
    reject "lambda_count" "lambda count != number of hull vertices" (leaf := i)
  -- Σ_k λ_k ≡ 1, as an identity of polynomials
  let total := lam.foldl (init := Tensor.zero) (· + ·)
  if !(total.beqPoly (Tensor.const 1)) then
    reject "lambda_sum" "sum_k lambda_k != 1" (leaf := i)
  -- λ_k ≥ 0 on the cell (verify.py tests the degree of λ_k on its LISTED exponents)
  for h : k in [0:lam.size] do
    if lam[k].deg > dLam then
      reject "degree_exceeds" "polynomial degree exceeds the declared Bernstein degree" (leaf := i)
    if !(← bernNonneg lam[k] dLam cell i) then
      reject "lambda_negative" s!"lambda_{k} is not >= 0" (leaf := i) (index := k)
  -- witness numerator X = Σ_k λ_k N_k
  let X : Vector (Tensor c.n) 3 := Vector.ofFn fun r =>
    (List.range lam.size).foldl (init := Tensor.zero) fun acc k =>
      acc + lam.getD k Tensor.zero * (geo.verts.getD k (Vector.replicate 3 Tensor.zero))[r]
  let some obs := c.obstacles.find? (·.name == obstacle)
    | reject "malformed" s!"malformed certificate (unknown obstacle {obstacle.quote})" (leaf := i)
  if mu.size != obs.faces.size then
    reject "mu_count" "mu count != obstacle face count" (leaf := i)
  let T := Tensor.const (c.delta * c.delta) + (c.phi * c.phi).scale (-1)   -- δ² - φ²
  let dPad := max (dLam + 2) (2 * c.phiDeg)
  for h : j in [0:obs.faces.size] do
    let face := obs.faces[j]
    let muJ := mu.getD j 0
    if muJ < 0 then
      reject "mu_negative" s!"mu_{j} < 0" (leaf := i) (index := j)
    -- g_j = b_j D - a_j · X
    let g := (List.finRange 3).foldl (init := geo.den.scale face.b) fun acc r =>
      acc + X[r].scale (-face.a[r])
    -- SIGN: g - μ T (subtract), formed here
    let H := g + T.scale (-muJ)
    if !(← bernNonneg H dPad cell i) then
      reject "face_not_certified"
        s!"face {j} of {obstacle.quote} not certified (Bernstein(g - mu*T) has a negative coefficient)"
        (leaf := i) (index := j)

/-- (iii)/(iv) dispatch on the status of leaf `i`. -/
def checkLeaf (c : Certificate) (geo : Geometry c.n) (i : Nat) (lf : Leaf c.n) : CheckM Unit :=
  match lf.kind with
  | .outside => checkOutsideLeaf c i lf.cell
  | .collision obstacle lam mu => checkCollisionLeaf c geo i lf.cell obstacle lam mu
  | .undecided status =>
    reject "leaf_status" s!"undecided leaf status {status.quote} (not a proof)" (leaf := i)

/-- Every leaf, in file order. -/
def checkLeaves (c : Certificate) : CheckM Unit := do
  let geo := c.geometry
  for h : i in [0:c.leaves.size] do
    checkLeaf c geo i c.leaves[i]

/-! ### The checker -/

/-- All checks, in the order of `verify.verify`; the first failure is the reason. -/
def checkE (c : Certificate) : CheckM Unit := do
  checkAssumptions c
  checkConditionI c
  checkPartition c
  checkKinematics c
  checkLeaves c

/-- The checker: `true` iff every check passes. -/
def check (c : Certificate) : Bool :=
  match checkE c with
  | .ok _ => true
  | .error _ => false

end CnpVerify
