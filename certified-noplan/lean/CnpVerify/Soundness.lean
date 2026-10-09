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

/-- [C1] COVERAGE of the tiling check: if `verifyCover` accepts, every point of the box lies in
one of the cells. (Disjointness is also tested by the checker, as in `verify.py`, but the
soundness proof only uses coverage.) -/
theorem verifyCover_covers {n : ℕ} (fuel : ℕ) (box : Box n) (cells : Array (Box n))
    (h : verifyCover fuel box cells = .ok ()) :
    ∀ x ∈ box.toSet, ∃ cell ∈ cells, x ∈ cell.toSet := by
  sorry

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
