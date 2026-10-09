/-
CnpVerify.Spec.Kinematics — reference kinematics over `ℝ` (L1: statements only).

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

/-- [K1] The common denominator is positive everywhere. -/
theorem bodyDenominator_pos (n : ℕ) (chain : Array Joint) (link : ℕ) (s : Fin n → ℝ) :
    0 < (bodyDenominator n chain link).eval s := by
  sorry

/-- [K2] The polynomial kinematics is the reference kinematics: the world position of the
body-frame point `p` of link `link` is `eval (N·p) / eval D`. -/
theorem body_position (n : ℕ) (chain : Array Joint) (link : ℕ) (p : Vec3) (s : Fin n → ℝ)
    (hn : unlockedUpTo chain link ≤ n) (i : Fin 3) :
    (linkPose chain link s).apply (vecR p) i
      = ((bodyNumerators n chain link p)[i]).eval s / (bodyDenominator n chain link).eval s := by
  sorry

/-- [K3] The half-angle parametrisation is the rotation of angle `q`: with `s = tan (q/2)` and
`|q| < π`, the rational expressions in `s` are `cos q` and `sin q`. -/
theorem rotation_half_angle (a : Vec3) (q : ℝ) (hq : |q| < Real.pi) :
    rodrigues a ((1 - Real.tan (q / 2) ^ 2) / (1 + Real.tan (q / 2) ^ 2))
        (2 * Real.tan (q / 2) / (1 + Real.tan (q / 2) ^ 2))
      = rodrigues a (Real.cos q) (Real.sin q) := by
  sorry

/-- [K4] For a unit axis and `cos² + sin² = 1`, Rodrigues' matrix is a rotation (orthogonal,
determinant `1`). This is where the hypotheses "exact unit axis" and "`cos² + sin² = 1`" of
the checker are used. -/
theorem rodrigues_mem_specialOrthogonal (a : Vec3) (co si : ℝ)
    (ha : ((a[0] : ℝ)) ^ 2 + (a[1] : ℝ) ^ 2 + (a[2] : ℝ) ^ 2 = 1) (hcs : co ^ 2 + si ^ 2 = 1) :
    rodrigues a co si ∈ Matrix.specialOrthogonalGroup (Fin 3) ℝ := by
  sorry

end CnpVerify
