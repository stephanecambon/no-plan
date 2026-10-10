/-
Certs.DisconnectedNative — the same statements for the scenes whose check does NOT fit in the
kernel (L4), obtained through `native_decide`.

Each statement below depends on ONE AXIOM MORE than the three standard ones: the
`…._native.native_decide.ax_…` axiom of the corresponding theorem of `Certs/Native.lean`. They
are theorems of Lean/Mathlib MODULO THE LEAN COMPILER AND RUN-TIME, and must be cited as such.
`wallK3_disconnected_ref` (`Certs/Disconnected.lean`) is the one that needs no such proviso.
-/
import CnpVerify.Soundness
import Certs.Native

namespace CnpVerify.Certs

/-- The 4-DOF shoulder-elbow scene is disconnected, on the reference kinematics — modulo the
compiler (`native_decide`). -/
theorem s3ShoulderElbow_disconnected_ref_native :
    ¬ ∃ γ : C(unitInterval, Fin s3ShoulderElbow.n → ℝ),
        (∀ t, γ t ∈ s3ShoulderElbow.box.toSet) ∧ γ 0 = vecR s3ShoulderElbow.sStart
          ∧ γ 1 = vecR s3ShoulderElbow.sGoal ∧ ∀ t, CollisionFreeRef s3ShoulderElbow (γ t) :=
  soundness_ref s3ShoulderElbow s3ShoulderElbow_proof_native

/-- The 7-DOF iiwa7 shelf scene is disconnected, on the reference kinematics — modulo the
compiler (`native_decide`). -/
theorem s6IiwaRealShelf_disconnected_ref_native :
    ¬ ∃ γ : C(unitInterval, Fin s6IiwaRealShelf.n → ℝ),
        (∀ t, γ t ∈ s6IiwaRealShelf.box.toSet) ∧ γ 0 = vecR s6IiwaRealShelf.sStart
          ∧ γ 1 = vecR s6IiwaRealShelf.sGoal ∧ ∀ t, CollisionFreeRef s6IiwaRealShelf (γ t) :=
  soundness_ref s6IiwaRealShelf s6IiwaRealShelf_proof_native

end CnpVerify.Certs
