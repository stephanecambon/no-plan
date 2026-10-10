/-
Certs.Staged — `check c = true` from its stages (L4). Core Lean only (no Mathlib).

Why this file exists. The soundness theorem is about the term `check`. For a certificate `c`
written as a term, `check c = true` can in principle be proved by EVALUATION IN THE KERNEL
(`by decide +kernel`): no compiler involved, no axiom added. In one piece this does not fit in
memory, even on the smallest shipped certificate (journal L4). The lemmas below let the same
evaluation be cut into independent pieces:

  * `check_of_stages` — `check c = true` from the four global checks, the value `G` of the
    kinematics `c.geometry`, and the check of every leaf run on `G`;
  * `checkLeaf_outside_of` — an outside leaf, from its own check;
  * `checkLeaf_collision_of` — a collision leaf, from the tests of `checkCollisionLeaf` taken one
    by one, the witness numerator `X = Σ_k λ_k N_k` and `T = δ² − φ²` being given as values.

They are the converse of the unpacking lemmas of `CnpVerify/Soundness.lean` (there: the check
succeeded, hence each test passed; here: each test passes, hence the check succeeds). Nothing
is assumed about the values `G`, `X`, `T`: the hypotheses are equations (`c.geometry = G`, …)
that the user of the lemma must prove — in `Certs/*Kernel.lean`, by kernel evaluation.

`witnessNumerator`, `slabTensor` and `faceTensor` name three sub-expressions of
`checkCollisionLeaf`; the proof of `checkCollisionLeaf_of` unfolds them and finds the checker's
own terms (no restatement of the checker is trusted: the conclusion is about `checkLeaf`).
-/
import CnpVerify.Check

namespace CnpVerify

/-! ### Decidable equality on the values compared by the stages -/

deriving instance DecidableEq for Tensor
deriving instance DecidableEq for Geometry
deriving instance DecidableEq for Face
deriving instance DecidableEq for Obstacle
deriving instance DecidableEq for Reject
deriving instance DecidableEq for Except

/-! ### Three sub-expressions of `checkCollisionLeaf`, named -/

/-- `X = Σ_k λ_k N_k`: the witness numerator, as `checkCollisionLeaf` forms it. -/
def witnessNumerator {n : Nat} (lam : Array (Tensor n)) (verts : Array (Vector (Tensor n) 3)) :
    Vector (Tensor n) 3 :=
  Vector.ofFn fun r =>
    (List.range lam.size).foldl (init := Tensor.zero) fun acc k =>
      acc + lam.getD k Tensor.zero * (verts.getD k (Vector.replicate 3 Tensor.zero))[r]

/-- `T = δ² − φ²`, as `checkCollisionLeaf` forms it. -/
def slabTensor (c : Certificate) : Tensor c.n :=
  Tensor.const (c.delta * c.delta) + (c.phi * c.phi).scale (-1)

/-- `g_j − μ_j T` with `g_j = b_j D − a_j · X`, as `checkCollisionLeaf` forms it. -/
def faceTensor {n : Nat} (den : Tensor n) (X : Vector (Tensor n) 3) (T : Tensor n) (face : Face)
    (muJ : Rat) : Tensor n :=
  (List.finRange 3).foldl (init := den.scale face.b) (fun acc r => acc + X[r].scale (-face.a[r]))
    + T.scale (-muJ)

/-! ### Plumbing: `Except`, `for` loops -/

/-- A stateless `for` loop over a list in `Except` succeeds if every iteration continues. -/
theorem list_forIn'_ok_of {α ε : Type} (l : List α)
    (f : (a : α) → a ∈ l → PUnit → Except ε (ForInStep PUnit))
    (hf : ∀ a ha, f a ha PUnit.unit = .ok (.yield PUnit.unit)) :
    forIn' l PUnit.unit f = .ok PUnit.unit := by
  induction l with
  | nil => rfl
  | cons a l ih =>
    rw [List.forIn'_cons, hf a List.mem_cons_self]
    exact ih _ (fun a' ha' => hf a' _)

/-- The same for a loop `for h : k in [0:N]`. -/
theorem range_forIn'_ok_of {ε : Type} (N : Nat)
    (f : (k : Nat) → k ∈ [:N] → PUnit → Except ε (ForInStep PUnit))
    (hf : ∀ k hk, f k hk PUnit.unit = .ok (.yield PUnit.unit)) :
    forIn' [:N] PUnit.unit f = .ok PUnit.unit := by
  rw [Std.Legacy.Range.forIn'_eq_forIn'_range']
  exact list_forIn'_ok_of _ _ (fun a ha => hf a _)

/-- A successful step followed by a successful continuation. -/
theorem bind_ok_of {α β ε : Type} (a : Except ε α) (f : α → Except ε β) (x : α) (b : β)
    (ha : a = .ok x) (hf : f x = .ok b) : (a >>= f) = .ok b := by
  subst ha
  exact hf

/-! ### The leaf checks from their tests -/

/-- (iv) succeeds if each of its tests does, `X` and `T` being the values of the witness
numerator and of `δ² − φ²`. -/
theorem checkCollisionLeaf_of (c : Certificate) (geo : Geometry c.n) (i : Nat) (cell : Box c.n)
    (obstacle : String) (lam : Array (Tensor c.n)) (mu : Array Rat)
    (dLam : Nat) (obs : Obstacle) (X : Vector (Tensor c.n) 3) (T : Tensor c.n)
    (hdeg : c.lamDeg = some dLam)
    (hcount : lam.size = geo.verts.size)
    (hsum : (lam.foldl (init := Tensor.zero) (· + ·)).beqPoly (Tensor.const 1) = true)
    (hlam : ∀ k (hk : k < lam.size), lam[k].deg ≤ dLam ∧ bernNonneg lam[k] dLam cell i = .ok true)
    (hX : witnessNumerator lam geo.verts = X)
    (hobs : c.obstacles.find? (·.name == obstacle) = some obs)
    (hmu : mu.size = obs.faces.size)
    (hT : slabTensor c = T)
    (hface : ∀ j (hj : j < obs.faces.size), ¬ mu.getD j 0 < 0 ∧
      bernNonneg (faceTensor geo.den X T obs.faces[j] (mu.getD j 0))
        (max (dLam + 2) (2 * c.phiDeg)) cell i = .ok true) :
    checkCollisionLeaf c geo i cell obstacle lam mu = .ok () := by
  subst hX hT
  unfold checkCollisionLeaf
  simp only [hdeg]
  rw [ite_eq_right (by simp [hcount]), ite_eq_right (by simp [hsum])]
  refine bind_ok_of _ _ PUnit.unit _ ?_ ?_
  · apply range_forIn'_ok_of
    intro k hk
    obtain ⟨h1, h2⟩ := hlam k hk.2.1
    rw [ite_eq_right (Nat.not_lt.2 h1), h2]
    rfl
  · simp only [hobs]
    rw [ite_eq_right (by simp [hmu])]
    refine bind_ok_of _ _ PUnit.unit _ ?_ rfl
    apply range_forIn'_ok_of
    intro j hj
    obtain ⟨hm, hb⟩ := hface j hj.2.1
    unfold faceTensor witnessNumerator slabTensor at hb
    rw [ite_eq_right hm, hb]
    rfl

/-- Multipliers, obstacle name and `μ` of a leaf (empty unless the leaf is a `collision` leaf). -/
def Leaf.lam {n : Nat} (lf : Leaf n) : Array (Tensor n) :=
  match lf.kind with
  | .collision _ lam _ => lam
  | _ => #[]

def Leaf.mu {n : Nat} (lf : Leaf n) : Array Rat :=
  match lf.kind with
  | .collision _ _ mu => mu
  | _ => #[]

def Leaf.obstacle {n : Nat} (lf : Leaf n) : String :=
  match lf.kind with
  | .collision o _ _ => o
  | _ => ""

def Leaf.isCollision {n : Nat} (lf : Leaf n) : Bool :=
  match lf.kind with
  | .collision .. => true
  | _ => false

def Leaf.isOutside {n : Nat} (lf : Leaf n) : Bool :=
  match lf.kind with
  | .outside => true
  | _ => false

/-- An outside leaf passes if `checkOutsideLeaf` does. -/
theorem checkLeaf_outside_of (c : Certificate) (geo : Geometry c.n) (i : Nat) (lf : Leaf c.n)
    (hk : lf.isOutside = true) (h : checkOutsideLeaf c i lf.cell = .ok ()) :
    checkLeaf c geo i lf = .ok () := by
  obtain ⟨cell, kind⟩ := lf
  cases kind with
  | outside => exact h
  | collision o lam mu => simp [Leaf.isOutside] at hk
  | undecided s => simp [Leaf.isOutside] at hk

/-- A collision leaf passes if each test of `checkCollisionLeaf` does (`checkCollisionLeaf_of`,
stated on the leaf). -/
theorem checkLeaf_collision_of (c : Certificate) (geo : Geometry c.n) (i : Nat) (lf : Leaf c.n)
    (dLam : Nat) (obs : Obstacle) (X : Vector (Tensor c.n) 3) (T : Tensor c.n)
    (hk : lf.isCollision = true)
    (hdeg : c.lamDeg = some dLam)
    (hcount : lf.lam.size = geo.verts.size)
    (hsum : (lf.lam.foldl (init := Tensor.zero) (· + ·)).beqPoly (Tensor.const 1) = true)
    (hlam : ∀ k (hk : k < lf.lam.size),
      lf.lam[k].deg ≤ dLam ∧ bernNonneg lf.lam[k] dLam lf.cell i = .ok true)
    (hX : witnessNumerator lf.lam geo.verts = X)
    (hobs : c.obstacles.find? (·.name == lf.obstacle) = some obs)
    (hmu : lf.mu.size = obs.faces.size)
    (hT : slabTensor c = T)
    (hface : ∀ j (hj : j < obs.faces.size), ¬ lf.mu.getD j 0 < 0 ∧
      bernNonneg (faceTensor geo.den X T obs.faces[j] (lf.mu.getD j 0))
        (max (dLam + 2) (2 * c.phiDeg)) lf.cell i = .ok true) :
    checkLeaf c geo i lf = .ok () := by
  obtain ⟨cell, kind⟩ := lf
  cases kind with
  | outside => simp [Leaf.isCollision] at hk
  | undecided s => simp [Leaf.isCollision] at hk
  | collision o lam mu =>
    exact checkCollisionLeaf_of c geo i cell o lam mu dLam obs X T hdeg hcount hsum hlam hX hobs hmu
      hT hface

/-! ### The checker from its stages -/

/-- Every leaf passes on the value `G` of the kinematics. -/
theorem checkLeaves_of (c : Certificate) (G : Geometry c.n) (hG : c.geometry = G)
    (hL : ∀ i (hi : i < c.leaves.size), checkLeaf c G i c.leaves[i] = .ok ()) :
    checkLeaves c = .ok () := by
  subst hG
  unfold checkLeaves
  refine bind_ok_of _ _ PUnit.unit _ ?_ rfl
  apply range_forIn'_ok_of
  intro i hi
  rw [hL i hi.2.1]
  rfl

/-- **`check c = true` from its stages.** -/
theorem check_of_stages (c : Certificate) (G : Geometry c.n)
    (hA : checkAssumptions c = .ok ()) (hI : checkConditionI c = .ok ())
    (hP : checkPartition c = .ok ()) (hK : checkKinematics c = .ok ())
    (hG : c.geometry = G)
    (hL : ∀ i (hi : i < c.leaves.size), checkLeaf c G i c.leaves[i] = .ok ()) :
    check c = true := by
  unfold check checkE
  rw [hA, hI, hP, hK, checkLeaves_of c G hG hL]
  rfl

end CnpVerify
