/-
CnpVerify.Soundness — the theorem the checker is meant to satisfy (L1: STATEMENT ONLY).

`soundness`: if `check c = true`, no continuous path inside the box joins the start to the goal
while keeping the certified body out of every obstacle.

The notions used in the statement (`Box.toSet`, `Obstacle.toSet`, `Certificate.bodyAt`,
`CollisionFree`) are defined below from the kinematic numerators/denominator and the
H-representations only — none of them mentions the checker. NOTHING IS PROVED in L1: every
`sorry` is a proof obligation listed in `lean/PROOF-OBLIGATIONS.md`.
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

/-- [C2] An accepted outside leaf is disjoint from the OPEN slab: `|φ| ≥ δ` on its cell. -/
theorem checkOutsideLeaf_sound (c : Certificate) (i : ℕ) (cell : Box c.n)
    (h : checkOutsideLeaf c i cell = .ok ()) :
    ∀ s ∈ cell.toSet, (c.delta : ℝ) ≤ |c.phi.eval s| := by
  sorry

/-- [C3] An accepted collision leaf is in collision on the slab: at every point of its cell
where `|φ| ≤ δ`, the certified body meets the named obstacle. -/
theorem checkCollisionLeaf_sound (c : Certificate) (i : ℕ) (cell : Box c.n) (obstacle : String)
    (lam : Array (Tensor c.n)) (mu : Array ℚ)
    (h : checkCollisionLeaf c c.geometry i cell obstacle lam mu = .ok ()) :
    ∀ s ∈ cell.toSet, |c.phi.eval s| ≤ (c.delta : ℝ) → ¬ CollisionFree c s := by
  sorry

/-- [C4] Under the kinematic hypotheses tested by the checker, collision-freeness on the
polynomial kinematics IS collision-freeness on the reference kinematics. -/
theorem collisionFree_iff_ref (c : Certificate) (h : checkKinematics c = .ok ())
    (s : Fin c.n → ℝ) : CollisionFree c s ↔ CollisionFreeRef c s := by
  sorry

/-! ### Main statement -/

/-- **[S1] Soundness of the checker.** If `check c = true`, there is no continuous path
`γ : [0,1] → ℝⁿ` that stays in the box, starts at `s_start`, ends at `s_goal`, and is
collision-free at every time. -/
theorem soundness (c : Certificate) :
    check c = true →
      ¬ ∃ γ : C(unitInterval, Fin c.n → ℝ),
          (∀ t, γ t ∈ c.box.toSet) ∧ γ 0 = vecR c.sStart ∧ γ 1 = vecR c.sGoal
            ∧ ∀ t, CollisionFree c (γ t) := by
  sorry

/-- [S2] The same statement on the reference kinematics (corollary of S1 and C4). -/
theorem soundness_ref (c : Certificate) :
    check c = true →
      ¬ ∃ γ : C(unitInterval, Fin c.n → ℝ),
          (∀ t, γ t ∈ c.box.toSet) ∧ γ 0 = vecR c.sStart ∧ γ 1 = vecR c.sGoal
            ∧ ∀ t, CollisionFreeRef c (γ t) := by
  sorry

end CnpVerify
