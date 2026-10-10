-- Executable core (core Lean only — what the `cnp-verify` binary links).
import CnpVerify.Tensor
import CnpVerify.Bernstein
import CnpVerify.Kinematics
import CnpVerify.Certificate
import CnpVerify.Check
-- Specification layer (Mathlib): reference semantics, the proofs closed in L2 (tensors, Bernstein,
-- coverage of the tiling) and the statements still to prove (L3).
import CnpVerify.Spec.Index
import CnpVerify.Spec.Tensor
import CnpVerify.Spec.Bernstein
import CnpVerify.Spec.Kinematics
import CnpVerify.Soundness
