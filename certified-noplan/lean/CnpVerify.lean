-- Executable core (core Lean only — what the `cnp-verify` binary links).
import CnpVerify.Tensor
import CnpVerify.Bernstein
import CnpVerify.Kinematics
import CnpVerify.Certificate
import CnpVerify.Check
-- Specification layer (Mathlib): reference semantics and the statements to prove (L2/L3).
import CnpVerify.Spec.Tensor
import CnpVerify.Spec.Bernstein
import CnpVerify.Spec.Kinematics
import CnpVerify.Soundness
