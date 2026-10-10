/-
CnpVerify.Soundness — the theorem the checker is meant to satisfy (STATEMENT; proof open).

`soundness`: if `check c = true`, no continuous path inside the box joins the start to the goal
while keeping the certified body out of every obstacle.

The notions used in the statement (`Box.toSet`, `Obstacle.toSet`, `Certificate.bodyAt`,
`CollisionFree`) are defined below from the kinematic numerators/denominator and the
H-representations only — none of them mentions the checker.

State: see `lean/PROOF-OBLIGATIONS.md`.
-/
import Mathlib
import CnpVerify.Check
import CnpVerify.Spec.Bernstein
import CnpVerify.Spec.Kinematics

namespace CnpVerify

/-- The obstacle as a subset of `ℝ³`: the points satisfying every face inequality `aᵀ y ≤ b`. -/
def Obstacle.toSet (O : Obstacle) : Set (Fin 3 → ℝ) :=
  {y | ∀ f ∈ O.faces, ∑ i : Fin 3, (f.a[i] : ℝ) * y i ≤ (f.b : ℝ)}

/-- World position of the `k`-th vertex of the certified body at the configuration `s`:
`eval (N_k) / eval D`, with `N_k` and `D` the kinematic numerators and the common denominator
of the body's link, computed from the declared chain. -/
noncomputable def Certificate.worldVertex (c : Certificate) (k : Fin c.hull.size)
    (s : Fin c.n → ℝ) : Fin 3 → ℝ :=
  fun i => ((bodyNumerators c.n c.chain c.bodyLink c.hull[k])[i]).eval s
    / (bodyDenominator c.n c.chain c.bodyLink).eval s

/-- The certified body at the configuration `s`: the convex hull of its world vertices. -/
noncomputable def Certificate.bodyAt (c : Certificate) (s : Fin c.n → ℝ) : Set (Fin 3 → ℝ) :=
  convexHull ℝ (Set.range fun k : Fin c.hull.size => c.worldVertex k s)

/-- The configuration `s` is collision-free: the certified body meets no obstacle. -/
def CollisionFree (c : Certificate) (s : Fin c.n → ℝ) : Prop :=
  ∀ O ∈ c.obstacles, Disjoint (c.bodyAt s) O.toSet

/-- Collision-freeness stated on the REFERENCE kinematics (`linkPose`: real rigid motions, no
polynomial): the convex hull of the moved body vertices meets no obstacle. -/
def CollisionFreeRef (c : Certificate) (s : Fin c.n → ℝ) : Prop :=
  ∀ O ∈ c.obstacles,
    Disjoint
      (convexHull ℝ (Set.range fun k : Fin c.hull.size =>
        (linkPose c.chain c.bodyLink s).apply (vecR c.hull[k])))
      O.toSet

/-! ### Proof obligations of the checks -/

/-- The fold of `splitCells` on an already failed state stays failed. -/
theorem splitFold_none {n : ℕ} (box : Box n) (ax : Fin n) (l : List (Box n)) :
    List.foldl (fun acc cell =>
        match acc with
        | none => none
        | some (lower, upper) =>
          if cell.hi ax ≤ box.mid ax then some (lower.push cell, upper)
          else if box.mid ax ≤ cell.lo ax then some (lower, upper.push cell) else none)
      (none : Option (Array (Box n) × Array (Box n))) l = none := by
  induction l with
  | nil => rfl
  | cons _ _ ih => simpa using ih

/-- The fold of `splitCells` only moves cells of the list into its two sides. -/
theorem splitFold_subset {n : ℕ} (box : Box n) (ax : Fin n) (cells : Array (Box n))
    (l : List (Box n)) (a b a' b' : Array (Box n))
    (ha : ∀ c ∈ a, c ∈ cells) (hb : ∀ c ∈ b, c ∈ cells) (hl : ∀ c ∈ l, c ∈ cells)
    (h : List.foldl (fun acc cell =>
        match acc with
        | none => none
        | some (lower, upper) =>
          if cell.hi ax ≤ box.mid ax then some (lower.push cell, upper)
          else if box.mid ax ≤ cell.lo ax then some (lower, upper.push cell) else none)
      (some (a, b)) l = some (a', b')) :
    (∀ c ∈ a', c ∈ cells) ∧ (∀ c ∈ b', c ∈ cells) := by
  induction l generalizing a b with
  | nil =>
    simp only [List.foldl_nil, Option.some.injEq, Prod.mk.injEq] at h
    obtain ⟨rfl, rfl⟩ := h
    exact ⟨ha, hb⟩
  | cons c l ih =>
    simp only [List.foldl_cons] at h
    have hc : c ∈ cells := hl c (by simp)
    have hl' : ∀ c ∈ l, c ∈ cells := fun c hc => hl c (by simp [hc])
    split_ifs at h with h1 h2
    · refine ih _ _ ?_ hb hl' h
      intro c' hc'
      rcases Array.mem_push.1 hc' with h | rfl
      · exact ha _ h
      · exact hc
    · refine ih _ _ ha ?_ hl' h
      intro c' hc'
      rcases Array.mem_push.1 hc' with h | rfl
      · exact hb _ h
      · exact hc
    · rw [splitFold_none] at h
      exact absurd h (by simp)

/-- Both sides returned by `splitCells` are made of cells of the input. -/
theorem splitCells_subset {n : ℕ} (box : Box n) (cells : Array (Box n)) (ax : Fin n)
    (lower upper : Array (Box n)) (h : splitCells box cells ax = some (lower, upper)) :
    (∀ c ∈ lower, c ∈ cells) ∧ (∀ c ∈ upper, c ∈ cells) := by
  unfold splitCells at h
  simp only at h
  split at h
  · rename_i lo up hfold
    split at h
    · exact absurd h (by simp)
    · simp only [Option.some.injEq, Prod.mk.injEq] at h
      obtain ⟨rfl, rfl⟩ := h
      rw [← Array.foldl_toList] at hfold
      exact splitFold_subset box ax cells cells.toList #[] #[] _ _ (by simp) (by simp) (by simp)
        hfold
  · exact absurd h (by simp)

/-- Two successive checks both succeed iff each does. -/
theorem checkM_seq_ok (a b : CheckM Unit) (h : (a >>= fun _ => b) = Except.ok ()) :
    a = Except.ok () ∧ b = Except.ok () := by
  cases a with
  | error e => simp [bind, Except.bind] at h
  | ok u => cases u; exact ⟨rfl, by simpa [bind, Except.bind] using h⟩

/-- [C1] COVERAGE of the tiling check: if `verifyCover` accepts, every point of the box lies in
one of the cells. (Disjointness is also tested by the checker, as in `verify.py`, but the
soundness proof only uses coverage.)

Proof (L2): induction on the recursion of `verifyCover`. A single cell IS the box. Otherwise the
cells were split at the midpoint `m` of an axis into two sides, each made of cells of the input
(`splitCells_subset`) and each accepted as a cover of its half-box; a point `x` of the box has
`x ≤ m` or `m ≤ x` on that axis, so it lies in one of the two half-boxes. The value of the cut is
never used: coverage only needs that the two half-boxes share it. That the two sides are
DISJOINT (no cell straddles the cut) is tested by the checker but does not enter this proof. -/
theorem verifyCover_covers {n : ℕ} (fuel : ℕ) (box : Box n) (cells : Array (Box n))
    (h : verifyCover fuel box cells = .ok ()) :
    ∀ x ∈ box.toSet, ∃ cell ∈ cells, x ∈ cell.toSet := by
  induction fuel generalizing box cells with
  | zero => simp [verifyCover, reject, throw, throwThe, MonadExceptOf.throw] at h
  | succ fuel ih =>
    unfold verifyCover at h
    split_ifs at h with h1 h2
    · intro x hx
      have hsz : cells.size = 1 := by simpa using h1
      have h0 : cells.getD 0 box = box := by simpa using h2
      refine ⟨cells.getD 0 box, ?_, by rw [h0]; exact hx⟩
      rw [Array.getD_eq_getD_getElem?]
      simp [hsz]
    · simp [reject, throw, throwThe, MonadExceptOf.throw] at h
    · split at h
      · rename_i ax lower upper hfind
        obtain ⟨ax', -, hsplit⟩ := List.exists_of_findSome?_eq_some hfind
        simp only [Option.map_eq_some_iff, Prod.mk.injEq] at hsplit
        obtain ⟨⟨lo, up⟩, hsp, rfl, rfl, rfl⟩ := hsplit
        obtain ⟨hlo, hup⟩ := splitCells_subset box cells ax' lower upper hsp
        obtain ⟨hL, hU⟩ := checkM_seq_ok _ _ h
        intro x hx
        rcases le_total (x ax') ((box.mid ax' : ℚ) : ℝ) with hle | hge
        · obtain ⟨cell, hcell, hxc⟩ := ih _ _ hL x (by
            intro i
            have := hx i
            simp only [Box.lo, Box.hi, Fin.getElem_fin, Vector.getElem_set] at this ⊢
            by_cases hi : ax'.val = i.val
            · have : ax' = i := Fin.ext hi
              subst this
              simpa using ⟨(hx ax').1, hle⟩
            · simpa [hi] using this)
          exact ⟨cell, hlo _ hcell, hxc⟩
        · obtain ⟨cell, hcell, hxc⟩ := ih _ _ hU x (by
            intro i
            have := hx i
            simp only [Box.lo, Box.hi, Fin.getElem_fin, Vector.getElem_set] at this ⊢
            by_cases hi : ax'.val = i.val
            · have : ax' = i := Fin.ext hi
              subst this
              simpa using ⟨hge, (hx ax').2⟩
            · simpa [hi] using this)
          exact ⟨cell, hup _ hcell, hxc⟩
      · simp [reject, throw, throwThe, MonadExceptOf.throw] at h

/-- The Bernstein test as the leaf checks call it: if `bernNonneg p d cell` answers `true`,
then `p ≥ 0` on the cell. Corollary of T6 (the tensor padded to degree `d` denotes the same
polynomial) and B1 (stated at the tensor's own degree). Not one of the 19 obligations: it is the
form in which C2 and C3 (L3) use them. -/
theorem bernNonneg_sound {n : ℕ} (p : Tensor n) (d : ℕ) (cell : Box n) (leaf : ℕ)
    (h : bernNonneg p d cell leaf = .ok true) : ∀ x ∈ cell.toSet, 0 ≤ p.eval x := by
  unfold bernNonneg at h
  split at h
  · simp [reject, throw, throwThe, MonadExceptOf.throw] at h
  · rename_i q hq
    have hall : allNonneg (bernsteinCoeffs cell q) = true := by
      simpa [pure, Except.pure] using h
    intro x hx
    rw [← Tensor.eval_padTo p q d hq x]
    exact bernstein_nonneg cell q hall x hx

/-! ### Plumbing for the leaf checks: the `Except` monad, `for` loops, sums -/

/-- A rejection is never a success. -/
theorem reject_ne_ok {α : Type} (code msg : String) (leaf index : Option ℕ) (a : α) :
    (reject code msg leaf index : CheckM α) ≠ Except.ok a := by
  simp [reject, throw, throwThe, MonadExceptOf.throw]

/-- A `for` loop over a list in `Except`, with no state, that succeeds: if the body can only
succeed by continuing, and then establishes `P`, then `P` holds for every element. -/
theorem list_forIn'_ok {α ε : Type} (l : List α) (P : α → Prop)
    (f : (a : α) → a ∈ l → PUnit → Except ε (ForInStep PUnit))
    (hf : ∀ a ha r, f a ha PUnit.unit = .ok r → r = .yield PUnit.unit ∧ P a)
    (h : forIn' l PUnit.unit f = .ok PUnit.unit) : ∀ a ∈ l, P a := by
  induction l with
  | nil => simp
  | cons a l ih =>
    rw [List.forIn'_cons] at h
    cases hfa : f a List.mem_cons_self PUnit.unit with
    | error e => rw [hfa] at h; simp [bind, Except.bind] at h
    | ok r =>
      obtain ⟨rfl, hP⟩ := hf _ _ _ hfa
      rw [hfa] at h
      simp only [bind, Except.bind] at h
      intro b hb
      rcases List.mem_cons.1 hb with rfl | hb
      · exact hP
      · exact ih _ (fun a' ha' r hr => hf a' _ r hr) h b hb

/-- The same for a loop `for h : k in [0:N]`. -/
theorem range_forIn'_ok {ε : Type} (N : ℕ) (P : ℕ → Prop)
    (f : (k : ℕ) → k ∈ [:N] → PUnit → Except ε (ForInStep PUnit))
    (hf : ∀ k hk r, f k hk PUnit.unit = .ok r → r = .yield PUnit.unit ∧ P k)
    (h : forIn' [:N] PUnit.unit f = .ok PUnit.unit) : ∀ k, k < N → P k := by
  rw [Std.Legacy.Range.forIn'_eq_forIn'_range'] at h
  intro k hk
  refine list_forIn'_ok _ P _ (fun a ha r hr => hf a _ r hr) h k ?_
  simp [Std.Legacy.Range.size, List.mem_range']
  omega

theorem list_sum_getD {α : Type} (l : List α) (f : α → ℝ) (d : α) :
    (l.map f).sum = ∑ k ∈ Finset.range l.length, f (l.getD k d) := by
  induction l with
  | nil => simp
  | cons a l ih => simp [Finset.sum_range_succ', ih, add_comm]

theorem array_sum_getD {α : Type} (a : Array α) (f : α → ℝ) (d : α) :
    (a.toList.map f).sum = ∑ k ∈ Finset.range a.size, f (a.getD k d) := by
  rw [list_sum_getD a.toList f d]
  simp [Array.getD_eq_getD_getElem?, List.getD_eq_getElem?_getD]

theorem eval_foldl_add {n : ℕ} {α : Type} (l : List α) (F : α → Tensor n) (init : Tensor n)
    (s : Fin n → ℝ) :
    (l.foldl (fun acc a => acc + F a) init).eval s
      = init.eval s + (l.map fun a => (F a).eval s).sum := by
  induction l generalizing init with
  | nil => simp
  | cons a l ih => simp [ih, Tensor.eval_add, add_assoc]

/-- [C2] An accepted outside leaf is disjoint from the OPEN slab: `|φ| ≥ δ` on its cell.

Proof (L3): the check succeeds only if one of its two Bernstein tests answers `true`
(`bernNonneg_sound`): `φ - δ ≥ 0` on the cell, or `-φ - δ ≥ 0` on the cell (T2, T3, T4). -/
theorem checkOutsideLeaf_sound (c : Certificate) (i : ℕ) (cell : Box c.n)
    (h : checkOutsideLeaf c i cell = .ok ()) :
    ∀ s ∈ cell.toSet, (c.delta : ℝ) ≤ |c.phi.eval s| := by
  intro s hs
  unfold checkOutsideLeaf at h
  simp only [] at h
  cases h1 : bernNonneg (c.phi + Tensor.const (-c.delta)) c.phiDeg cell i with
  | error e => rw [h1] at h; simp [bind, Except.bind] at h
  | ok b1 =>
    cases b1 with
    | true =>
      have := bernNonneg_sound _ _ _ _ h1 s hs
      rw [Tensor.eval_add, Tensor.eval_const] at this
      push_cast at this
      exact le_trans (by linarith) (le_abs_self _)
    | false =>
      rw [h1] at h
      simp only [bind, Except.bind] at h
      cases h2 : bernNonneg (c.phi.scale (-1) + Tensor.const (-c.delta)) c.phiDeg cell i with
      | error e => rw [h2] at h; simp at h
      | ok b2 =>
        cases b2 with
        | true =>
          have := bernNonneg_sound _ _ _ _ h2 s hs
          rw [Tensor.eval_add, Tensor.eval_const, Tensor.eval_scale] at this
          push_cast at this
          exact le_trans (by linarith) (neg_le_abs _)
        | false =>
          rw [h2] at h
          exact absurd h (by simp [reject, throw, throwThe, MonadExceptOf.throw])


theorem bind_ok {α β : Type} (a : CheckM α) (f : α → CheckM β) (b : β)
    (h : (a >>= f) = Except.ok b) : ∃ x, a = Except.ok x ∧ f x = Except.ok b := by
  cases a with
  | error e => simp [bind, Except.bind] at h
  | ok x => exact ⟨x, rfl, by simpa [bind, Except.bind] using h⟩

/-- [C3] An accepted collision leaf is in collision on the slab: at every point of its cell
where `|φ| ≤ δ`, the certified body meets the named obstacle.

Proof (L3). The check gives, on the cell: `Σ_k λ_k = 1` as polynomials (T7), `λ_k ≥ 0`
(`bernNonneg_sound`), and for each face `aᵀ y ≤ b` of the obstacle, `μ ≥ 0` and
`b D - aᵀ Σ_k λ_k N_k - μ (δ² - φ²) ≥ 0`. On the slab `δ² - φ² ≥ 0`, hence
`aᵀ Σ_k λ_k N_k ≤ b D`, and dividing by `D > 0` (K1) the point `y = Σ_k λ_k(s) · N_k(s)/D(s)`
satisfies every face. It is a convex combination of the world vertices, so it lies in the body:
the body and the obstacle share `y`. The degree test on `λ_k` is not used. -/
theorem checkCollisionLeaf_sound (c : Certificate) (i : ℕ) (cell : Box c.n) (obstacle : String)
    (lam : Array (Tensor c.n)) (mu : Array ℚ)
    (h : checkCollisionLeaf c c.geometry i cell obstacle lam mu = .ok ()) :
    ∀ s ∈ cell.toSet, |c.phi.eval s| ≤ (c.delta : ℝ) → ¬ CollisionFree c s := by
  intro s hs hslab hfree
  unfold checkCollisionLeaf at h
  simp only [] at h
  split at h
  swap
  · exact reject_ne_ok _ _ _ _ _ h
  rename_i dLam hdLam
  split at h
  · simp [reject, throw, throwThe, MonadExceptOf.throw, bind, Except.bind] at h
  rename_i hsz
  split at h
  · simp [reject, throw, throwThe, MonadExceptOf.throw, bind, Except.bind] at h
  rename_i hsum
  obtain ⟨hloop1, hrest⟩ := checkM_seq_ok _ _ h
  clear h
  have hlam : ∀ k, k < lam.size → ∀ hk : k < lam.size, 0 ≤ (lam[k]).eval s := by
    refine range_forIn'_ok lam.size _ _ ?_ hloop1
    intro k hk r hr
    split at hr
    · simp [reject, throw, throwThe, MonadExceptOf.throw, bind, Except.bind] at hr
    cases hb : bernNonneg lam[k] dLam cell i with
    | error e => rw [hb] at hr; simp [bind, Except.bind] at hr
    | ok b =>
      rw [hb] at hr
      cases b with
      | false => simp [reject, throw, throwThe, MonadExceptOf.throw, bind, Except.bind] at hr
      | true =>
        have hr' : ForInStep.yield PUnit.unit = r := by
          simpa [bind, Except.bind, pure, Except.pure] using hr
        exact ⟨hr'.symm, fun _ => bernNonneg_sound _ _ _ _ hb s hs⟩
  clear hloop1
  split at hrest
  swap
  · exact reject_ne_ok _ _ _ _ _ hrest
  rename_i obs hobs
  split at hrest
  · simp [reject, throw, throwThe, MonadExceptOf.throw, bind, Except.bind] at hrest
  rename_i hmu
  obtain ⟨hloop2, -⟩ := checkM_seq_ok _ _ hrest
  clear hrest
  have hDpos : 0 < c.geometry.den.eval s := bodyDenominator_pos c.n c.chain c.bodyLink s
  let X : Fin 3 → ℝ := fun r => ∑ k ∈ Finset.range lam.size,
      (lam.getD k Tensor.zero).eval s
        * ((c.geometry.verts.getD k (Vector.replicate 3 Tensor.zero))[r]).eval s
  have hface : ∀ j, j < obs.faces.size → ∀ hj : j < obs.faces.size,
      ∑ r : Fin 3, (obs.faces[j].a[r] : ℝ) * X r
        ≤ (obs.faces[j].b : ℝ) * c.geometry.den.eval s := by
    refine range_forIn'_ok obs.faces.size _ _ ?_ hloop2
    intro j hj r hr
    split at hr
    · simp [reject, throw, throwThe, MonadExceptOf.throw, bind, Except.bind] at hr
    rename_i hmuj
    obtain ⟨b, hb, hr⟩ := bind_ok _ _ _ hr
    cases b with
    | false => simp [reject, throw, throwThe, MonadExceptOf.throw, bind, Except.bind] at hr
    | true =>
      have hr' : ForInStep.yield PUnit.unit = r := by simpa [pure, Except.pure] using hr
      refine ⟨hr'.symm, fun hj' => ?_⟩
      have h0 := bernNonneg_sound _ _ _ _ hb s hs
      simp only [Tensor.eval_add, Tensor.eval_scale, Tensor.eval_const, Tensor.eval_mul,
        eval_foldl_add, Tensor.eval_zero, Fin.getElem_fin, Vector.getElem_ofFn, zero_add,
        list_sum_range, ← Fin.sum_univ_def] at h0
      have hT : 0 ≤ (c.delta : ℝ) * c.delta - c.phi.eval s * c.phi.eval s := by
        have := abs_le.1 hslab
        nlinarith [this.1, this.2]
      have hm : (0 : ℝ) ≤ ((mu.getD j 0 : ℚ) : ℝ) := by exact_mod_cast not_lt.1 hmuj
      change 0 ≤ (obs.faces[j].b : ℝ) * c.geometry.den.eval s
        + ∑ a : Fin 3, ((-obs.faces[j].a[a] : ℚ) : ℝ) * X a + _ at h0
      push_cast at h0
      simp only [neg_mul, Finset.sum_neg_distrib] at h0
      linarith [mul_nonneg hm hT]
  clear hloop2
  -- the witness point: the convex combination of the world vertices with weights `λ_k(s)`
  have hsz' : lam.size = c.hull.size := by
    have h1 : lam.size = c.geometry.verts.size := by simpa using hsz
    rw [h1]
    simp [Certificate.geometry]
  have hone : ∑ k ∈ Finset.range lam.size, (lam.getD k Tensor.zero).eval s = 1 := by
    have hb : (Array.foldl (fun x1 x2 => x1 + x2) Tensor.zero lam).beqPoly (Tensor.const 1)
        = true := by
      simpa using hsum
    have h1 := Tensor.eval_eq_of_beqPoly _ _ hb s
    rw [Tensor.eval_const, ← Array.foldl_toList] at h1
    have h2 : (List.foldl (fun x1 x2 => x1 + x2) Tensor.zero lam.toList).eval s = _ :=
      eval_foldl_add lam.toList id Tensor.zero s
    rw [h2, Tensor.eval_zero, zero_add] at h1
    rw [← array_sum_getD lam (fun t => t.eval s) Tensor.zero]
    simpa using h1
  have hnn : ∀ k ∈ Finset.range lam.size, 0 ≤ (lam.getD k Tensor.zero).eval s := by
    intro k hk
    have hk' : k < lam.size := Finset.mem_range.1 hk
    have : lam.getD k Tensor.zero = lam[k] := by simp [Array.getD_eq_getD_getElem?, hk']
    rw [this]
    exact hlam k hk' hk'
  let z : ℕ → Fin 3 → ℝ := fun k r =>
    ((c.geometry.verts.getD k (Vector.replicate 3 Tensor.zero))[r]).eval s / c.geometry.den.eval s
  have hz : ∀ k ∈ Finset.range lam.size,
      z k ∈ convexHull ℝ (Set.range fun k : Fin c.hull.size => c.worldVertex k s) := by
    intro k hk
    have hk' : k < c.hull.size := hsz' ▸ Finset.mem_range.1 hk
    refine subset_convexHull ℝ _ ⟨⟨k, hk'⟩, ?_⟩
    funext r
    simp [Certificate.worldVertex, z, Certificate.geometry, bodyNumerators, bodyPose,
      bodyDenominator, Array.getD_eq_getD_getElem?, hk']
  have hy1 := (convex_convexHull ℝ _).sum_mem hnn hone hz
  have hyr : ∀ r : Fin 3, (∑ k ∈ Finset.range lam.size, (lam.getD k Tensor.zero).eval s • z k) r
      = X r / c.geometry.den.eval s := by
    intro r
    simp only [Finset.sum_apply, Pi.smul_apply, smul_eq_mul, z, X, Finset.sum_div, mul_div_assoc]
  have hy2 : (∑ k ∈ Finset.range lam.size, (lam.getD k Tensor.zero).eval s • z k) ∈ obs.toSet := by
    intro f hf
    obtain ⟨j, hj, rfl⟩ := Array.mem_iff_getElem.1 hf
    have h1 := hface j hj hj
    simp only [hyr]
    rw [show ∑ r : Fin 3, (obs.faces[j].a[r] : ℝ) * (X r / c.geometry.den.eval s)
        = (∑ r : Fin 3, (obs.faces[j].a[r] : ℝ) * X r) / c.geometry.den.eval s by
      rw [Finset.sum_div]; exact Finset.sum_congr rfl fun r _ => by ring]
    exact (div_le_iff₀ hDpos).2 h1
  exact Set.disjoint_left.1 (hfree obs (Array.mem_of_find?_eq_some hobs)) hy1 hy2

/-- [C4] Under the kinematic hypotheses tested by the checker, collision-freeness on the
polynomial kinematics IS collision-freeness on the reference kinematics. -/
theorem collisionFree_iff_ref (c : Certificate) (h : checkKinematics c = .ok ())
    (s : Fin c.n → ℝ) : CollisionFree c s ↔ CollisionFreeRef c s := by
  sorry

/-! ### What each check of `checkE` gives -/

/-- (0) gives `δ > 0`. (The non-degeneracy of the box is tested too; it is not used.) -/
theorem checkAssumptions_ok (c : Certificate) (h : checkAssumptions c = .ok ()) :
    0 < c.delta := by
  unfold checkAssumptions at h
  by_contra hd
  have hd' : c.delta ≤ 0 := not_lt.1 hd
  simp [hd', reject, throw, throwThe, MonadExceptOf.throw, bind, Except.bind] at h

/-- (i) gives `φ(s_start) < -δ` and `δ < φ(s_goal)`, on the reference semantics (T1). -/
theorem checkConditionI_ok (c : Certificate) (h : checkConditionI c = .ok ()) :
    c.phi.eval (vecR c.sStart) < -(c.delta : ℝ) ∧ (c.delta : ℝ) < c.phi.eval (vecR c.sGoal) := by
  unfold checkConditionI at h
  have h1 : c.phi.evalQ (fun i => c.sStart[i]) < -c.delta := by
    by_contra hn
    rw [ite_eq_left hn] at h
    exact absurd h (by simp [reject, throw, throwThe, MonadExceptOf.throw, bind, Except.bind])
  rw [ite_eq_right (not_not.2 h1)] at h
  have h2 : c.phi.evalQ (fun i => c.sGoal[i]) > c.delta := by
    by_contra hn
    rw [ite_eq_left hn] at h
    exact absurd h (by simp [reject, throw, throwThe, MonadExceptOf.throw])
  have e1 := Tensor.evalQ_cast c.phi (fun i => c.sStart[i])
  have e2 := Tensor.evalQ_cast c.phi (fun i => c.sGoal[i])
  refine ⟨?_, ?_⟩
  · change c.phi.eval (fun i => ((c.sStart[i] : ℚ) : ℝ)) < _
    rw [← e1]
    exact_mod_cast h1
  · change _ < c.phi.eval (fun i => ((c.sGoal[i] : ℚ) : ℝ))
    rw [← e2]
    exact_mod_cast h2

/-- (ii) gives the coverage of the box by the cells of the leaves (C1). -/
theorem checkPartition_ok (c : Certificate) (h : checkPartition c = .ok ()) :
    ∀ x ∈ c.box.toSet, ∃ lf ∈ c.leaves, x ∈ lf.cell.toSet := by
  unfold checkPartition at h
  simp only [] at h
  split at h
  · simp [reject, throw, throwThe, MonadExceptOf.throw, bind, Except.bind] at h
  intro x hx
  obtain ⟨cell, hcell, hxc⟩ := verifyCover_covers _ _ _ h x hx
  obtain ⟨lf, hlf, rfl⟩ := Array.mem_map.1 hcell
  exact ⟨lf, hlf, hxc⟩

/-- (iii)/(iv): every leaf passes its own check. -/
theorem checkLeaves_ok (c : Certificate) (h : checkLeaves c = .ok ()) :
    ∀ i, i < c.leaves.size → ∀ hi : i < c.leaves.size,
      checkLeaf c c.geometry i c.leaves[i] = .ok () := by
  unfold checkLeaves at h
  simp only [] at h
  obtain ⟨hloop, -⟩ := checkM_seq_ok _ _ h
  refine range_forIn'_ok c.leaves.size _ _ ?_ hloop
  intro i hi r hr
  obtain ⟨u, hu, hr⟩ := bind_ok _ _ _ hr
  have hr' : ForInStep.yield PUnit.unit = r := by simpa [pure, Except.pure] using hr
  exact ⟨hr'.symm, fun _ => hu⟩

/-! ### Main statement -/

/-- **[S1] Soundness of the checker.** If `check c = true`, there is no continuous path
`γ : [0,1] → ℝⁿ` that stays in the box, starts at `s_start`, ends at `s_goal`, and is
collision-free at every time.

Proof (L3), the argument of the paper §4. Suppose such a path `γ`. `φ ∘ γ` is continuous
(`Tensor.continuous_eval`), `< -δ < 0` at `0` and `> δ > 0` at `1` (check (i), `δ > 0` by check
(0)), so it vanishes at some time `t` (intermediate value theorem, `intermediate_value_univ` on
the connected space `[0,1]`). The point `s* = γ t` is in the box, hence in the cell of a leaf
(check (ii), C1). That leaf is not `outside`: C2 would give `δ ≤ |φ(s*)| = 0`. So it is a
`collision` leaf, and since `|φ(s*)| = 0 ≤ δ`, C3 says `s*` is in collision — contradicting the
collision-freeness of `γ` at time `t`.

The kinematic check (0') is NOT used: this statement is about the pair `(N, D)` recomputed from
the chain, whatever the chain is. That `(N, D)` is the forward kinematics of the declared chain
is K2, and enters through C4 / S2. -/
theorem soundness (c : Certificate) :
    check c = true →
      ¬ ∃ γ : C(unitInterval, Fin c.n → ℝ),
          (∀ t, γ t ∈ c.box.toSet) ∧ γ 0 = vecR c.sStart ∧ γ 1 = vecR c.sGoal
            ∧ ∀ t, CollisionFree c (γ t) := by
  rintro hc ⟨γ, hbox, h0, h1, hfree⟩
  have hE : checkE c = .ok () := by
    unfold check at hc
    cases hce : checkE c with
    | ok u => rfl
    | error e => rw [hce] at hc; simp at hc
  unfold checkE at hE
  obtain ⟨hA, hE⟩ := checkM_seq_ok _ _ hE
  obtain ⟨hI, hE⟩ := checkM_seq_ok _ _ hE
  obtain ⟨hP, hE⟩ := checkM_seq_ok _ _ hE
  obtain ⟨-, hL⟩ := checkM_seq_ok _ _ hE
  have hδ : (0 : ℝ) < c.delta := by exact_mod_cast checkAssumptions_ok c hA
  obtain ⟨hs, hg⟩ := checkConditionI_ok c hI
  have hcont : Continuous fun t : unitInterval => c.phi.eval (γ t) :=
    (Tensor.continuous_eval c.phi).comp γ.continuous
  obtain ⟨t, ht⟩ : ∃ t, c.phi.eval (γ t) = 0 := by
    have hiv := intermediate_value_univ (0 : unitInterval) 1 hcont
    exact hiv ⟨by simp only [h0]; linarith, by simp only [h1]; linarith⟩
  obtain ⟨lf, hlf, hcell⟩ := checkPartition_ok c hP (γ t) (hbox t)
  obtain ⟨i, hi, rfl⟩ := Array.mem_iff_getElem.1 hlf
  have hleaf := checkLeaves_ok c hL i hi hi
  unfold checkLeaf at hleaf
  split at hleaf
  · have := checkOutsideLeaf_sound c i _ hleaf (γ t) hcell
    rw [ht, abs_zero] at this
    linarith
  · exact checkCollisionLeaf_sound c i _ _ _ _ hleaf (γ t) hcell
      (by rw [ht, abs_zero]; exact hδ.le) (hfree t)
  · exact reject_ne_ok _ _ _ _ _ hleaf

/-- [S2] The same statement on the reference kinematics (corollary of S1 and C4). -/
theorem soundness_ref (c : Certificate) :
    check c = true →
      ¬ ∃ γ : C(unitInterval, Fin c.n → ℝ),
          (∀ t, γ t ∈ c.box.toSet) ∧ γ 0 = vecR c.sStart ∧ γ 1 = vecR c.sGoal
            ∧ ∀ t, CollisionFreeRef c (γ t) := by
  sorry

end CnpVerify
