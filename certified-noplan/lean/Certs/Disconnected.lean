/-
Certs.Disconnected — the disconnection of a shipped scene as a theorem of Lean/Mathlib (L4).

`soundness` (S1) and `soundness_ref` (S2) say: if `check c = true`, no continuous collision-free
path joins the start to the goal inside the box. `Certs/WallK3Kernel.lean` proves
`check wallK3 = true` by kernel evaluation. Together: the statements below, which depend on no
axiom beyond `propext`, `Classical.choice`, `Quot.sound` — neither on the compiler nor on the
`cnp-verify` binary nor on the JSON parser.

What a reader still has to read to know what is proved: the term `wallK3`
(`Certs/WallK3.lean` — for `wallK3_disconnected_ref`, only its fields `n`, `chain`, `bodyLink`,
`hull`, `obstacles`, `box`, `sStart`, `sGoal`) and the reference definitions listed in
`lean/README.md`, "Trust base". That `wallK3` is the content of `scenes/wall/k3.cert.json` is
checked by `CertTermCheck.lean` (run time, not a proof), and can be read off the two files.
-/
import CnpVerify.Soundness
import Certs.WallK3Kernel

namespace CnpVerify.Certs

/-- **The scene `wall/k3` is disconnected** (statement of S1, on the kinematic numerators and
denominator): no continuous path in the joint box goes from the start to the goal with the
certified body out of the obstacle at every time. -/
theorem wallK3_disconnected :
    ¬ ∃ γ : C(unitInterval, Fin wallK3.n → ℝ),
        (∀ t, γ t ∈ wallK3.box.toSet) ∧ γ 0 = vecR wallK3.sStart ∧ γ 1 = vecR wallK3.sGoal
          ∧ ∀ t, CollisionFree wallK3 (γ t) :=
  soundness wallK3 wallK3_proof

/-- **The scene `wall/k3` is disconnected, on the reference kinematics** (statement of S2: the
body is moved by the real rigid motions `linkPose` of the declared chain). This is the
statement to cite. -/
theorem wallK3_disconnected_ref :
    ¬ ∃ γ : C(unitInterval, Fin wallK3.n → ℝ),
        (∀ t, γ t ∈ wallK3.box.toSet) ∧ γ 0 = vecR wallK3.sStart ∧ γ 1 = vecR wallK3.sGoal
          ∧ ∀ t, CollisionFreeRef wallK3 (γ t) :=
  soundness_ref wallK3 wallK3_proof

end CnpVerify.Certs
