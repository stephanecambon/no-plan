/-
CnpVerify.Kinematics — rational forward kinematics of a serial revolute chain (L1, executable).

Port of `verify.py` `_rot_homog` / `_trans_homog` / `_body_fk` / `_vertex_numerators`.
With `s = tan(q/2)` the rotation of an UNLOCKED joint about a unit axis `a` (`K = skew a`) is
`((1+s²) I + 2s K + 2s² K²) / (1+s²)`; a LOCKED joint is the numeric Rodrigues rotation
`I + sin·K + (1-cos)·K²` and carries no variable. Homogeneous 4×4 NUMERATOR matrices are
accumulated along the chain over the common denominator `D = ∏ (1+sᵢ²)` (unlocked joints of
the chain only); entry `(3,3)` of each factor is its own denominator.
The reference real-valued kinematics and the statement relating it to `N/D` (sorry in L1) are
in `CnpVerify/Spec/Kinematics.lean`.
-/
import CnpVerify.Tensor

namespace CnpVerify

/-- A rational vector of `ℝ³` (`v[i]`, `i : Fin 3`). -/
abbrev Vec3 := Vector Rat 3

/-- One revolute joint of the serial chain. `offset` is the translation from the previous joint
frame, `axis` the rotation axis (required to be an exact unit vector by the checker). A locked
joint carries the exact rational `(cos, sin)` of its fixed angle and takes no variable. -/
structure Joint where
  offset : Vec3
  axis : Vec3
  locked : Option (Rat × Rat)

/-- 4×4 matrix of polynomials (homogeneous transform numerators). -/
abbrev Mat4 (n : Nat) := Vector (Vector (Tensor n) 4) 4

namespace Mat4

variable {n : Nat}

def ofFn (f : Fin 4 → Fin 4 → Tensor n) : Mat4 n :=
  Vector.ofFn fun i => Vector.ofFn fun j => f i j

def get (M : Mat4 n) (i j : Fin 4) : Tensor n := M[i][j]

/-- Identity matrix. -/
def one : Mat4 n := ofFn fun i j => if i = j then Tensor.const 1 else Tensor.zero

/-- Matrix product (entries multiplied as polynomials). -/
def mul (A B : Mat4 n) : Mat4 n :=
  ofFn fun i j => (List.finRange 4).foldl (init := Tensor.zero) fun acc k =>
    acc + A.get i k * B.get k j

end Mat4

/-- Cross-product matrix `K` of `a`: `K v = a × v`. -/
def skew (a : Vec3) (i j : Fin 3) : Rat :=
  match i.val, j.val with
  | 0, 1 => -a[2]
  | 0, 2 => a[1]
  | 1, 0 => a[2]
  | 1, 2 => -a[0]
  | 2, 0 => -a[1]
  | 2, 1 => a[0]
  | _, _ => 0

/-- `K²`. -/
def skewSq (a : Vec3) (i j : Fin 3) : Rat :=
  (List.finRange 3).foldl (init := 0) fun acc t => acc + skew a i t * skew a t j

/-- Exponent array of `s_idx^p` in `n` variables. -/
def unitExp (n idx p : Nat) : Array Nat := (Array.replicate n 0).setIfInBounds idx p

/-- The polynomial `1 + s_idx²`. -/
def onePlusSq (n idx : Nat) : Tensor n := Tensor.const 1 + Tensor.monomial (unitExp n idx 2) 1

/-- Homogeneous rotation numerator of a joint. Unlocked (`locked = none`): numerator over
`1 + s²` where `s` is the variable of index `sIdx`, and entry `(3,3)` is `1 + s²`. Locked:
constant Rodrigues rotation, denominator `1`. -/
def rotHomog (n : Nat) (axis : Vec3) (sIdx : Nat) (locked : Option (Rat × Rat)) : Mat4 n :=
  match locked with
  | none =>
    let den : Tensor n := onePlusSq n sIdx
    let s1 : Tensor n := Tensor.monomial (unitExp n sIdx 1) 2   -- 2 s
    let s2 : Tensor n := Tensor.monomial (unitExp n sIdx 2) 2   -- 2 s²
    Mat4.ofFn fun i j =>
      if h : i.val < 3 ∧ j.val < 3 then
        let i' : Fin 3 := ⟨i.val, h.1⟩
        let j' : Fin 3 := ⟨j.val, h.2⟩
        (if i = j then den else Tensor.zero) + s1.scale (skew axis i' j')
          + s2.scale (skewSq axis i' j')
      else if i.val = 3 ∧ j.val = 3 then den else Tensor.zero
  | some (c, s) =>
    Mat4.ofFn fun i j =>
      if h : i.val < 3 ∧ j.val < 3 then
        let i' : Fin 3 := ⟨i.val, h.1⟩
        let j' : Fin 3 := ⟨j.val, h.2⟩
        Tensor.const ((if i = j then 1 else 0) + s * skew axis i' j' + (1 - c) * skewSq axis i' j')
      else if i.val = 3 ∧ j.val = 3 then Tensor.const 1 else Tensor.zero

/-- Homogeneous translation by the constant vector `o`. -/
def transHomog (n : Nat) (o : Vec3) : Mat4 n :=
  Mat4.ofFn fun i j =>
    if i = j then Tensor.const 1
    else if h : i.val < 3 ∧ j.val = 3 then Tensor.const o[i.val]
    else Tensor.zero

/-- Homogeneous transform numerator of one joint: `Trans(offset) · Rot(axis, ·)`; `sIdx` is the
index of the joint's variable (ignored when the joint is locked). -/
def Joint.homog (n : Nat) (j : Joint) (sIdx : Nat) : Mat4 n :=
  (transHomog n j.offset).mul (rotHomog n j.axis sIdx j.locked)

/-- State of the chain accumulation: pose numerator, common denominator, next free variable. -/
structure FKState (n : Nat) where
  pose : Mat4 n
  den : Tensor n
  nextVar : Nat

/-- One step of `_body_fk`: `T ← T · (Trans(offset) · Rot)`, `D ← D (1+s²)` if unlocked.
(`verify.py` associates `(T · Trans) · Rot`; the product is the same matrix of polynomials.) -/
def fkStep (n : Nat) (st : FKState n) (j : Joint) : FKState n :=
  let pose := st.pose.mul (j.homog n st.nextVar)
  match j.locked with
  | none => ⟨pose, st.den * onePlusSq n st.nextVar, st.nextVar + 1⟩
  | some _ => ⟨pose, st.den, st.nextVar⟩

/-- Forward kinematics of link `link`: product along joints `0..link` (unlocked joints are
numbered `0..n-1` in chain order). -/
def bodyFK (n : Nat) (chain : Array Joint) (link : Nat) : FKState n :=
  (chain.extract 0 (link + 1)).foldl (fkStep n) ⟨Mat4.one, Tensor.const 1, 0⟩

/-- World pose NUMERATOR matrix of link `link`. -/
def bodyPose (n : Nat) (chain : Array Joint) (link : Nat) : Mat4 n := (bodyFK n chain link).pose

/-- Common denominator `D = ∏ (1+sᵢ²)` over the unlocked joints of the chain of `link`. -/
def bodyDenominator (n : Nat) (chain : Array Joint) (link : Nat) : Tensor n :=
  (bodyFK n chain link).den

/-- Numerators `N·p` of the world position of the body-frame point `p`, from a pose matrix. -/
def vertexNumerators {n : Nat} (T : Mat4 n) (p : Vec3) : Vector (Tensor n) 3 :=
  Vector.ofFn fun i =>
    let r : Fin 4 := ⟨i.val, by omega⟩
    (T.get r 0).scale p[0] + (T.get r 1).scale p[1] + (T.get r 2).scale p[2] + T.get r 3

/-- Numerators of the world position of the body-frame point `p` of link `link`: the world
position is `eval (N·p) / eval D` (statement in `Spec/Kinematics.lean`). -/
def bodyNumerators (n : Nat) (chain : Array Joint) (link : Nat) (p : Vec3) : Vector (Tensor n) 3 :=
  vertexNumerators (bodyPose n chain link) p

end CnpVerify
