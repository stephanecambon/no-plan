#!/usr/bin/env python3
"""L4 — axiom audit of the Lean development (`#print axioms`, asserted).

    python3 scripts/lean_axioms.py [--no-certs]

Runs ``#print axioms`` on every statement the project cites and FAILS (exit code 1) unless:

  * the 19 proof obligations, the cited lemmas outside the 19, the staging lemmas and the
    per-scene statements proved by KERNEL evaluation depend on nothing but the three standard
    axioms ``propext``, ``Classical.choice``, ``Quot.sound`` — in particular no ``sorryAx``, no
    ``Lean.ofReduceBool`` / ``Lean.trustCompiler``, no ``native_decide`` axiom;
  * the statements proved through ``native_decide`` (kept for comparison, named ``…_native``)
    depend on the three standard axioms plus EXACTLY ONE axiom ``…._native.native_decide.ax_…``
    — the audit also fails if that axiom is missing, so that the two kinds of statements can
    never be confused.

The audit first checks that it can fail: a statement closed by ``sorry`` and one closed by
``native_decide`` are submitted as if they were kernel statements and must both be flagged.

Stdlib only; needs ``lake`` (elan) and a built project (``lake build``; ``lake build Certs``
unless ``--no-certs``).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEAN = os.path.join(ROOT, "lean")
STANDARD = {"propext", "Classical.choice", "Quot.sound"}
NATIVE_AX = re.compile(r"\._native\.native_decide\.ax(_\d+)+$")

# The 19 proof obligations (lean/PROOF-OBLIGATIONS.md), in namespace CnpVerify.
OBLIGATIONS = [
    ("T1", "Tensor.evalQ_cast"), ("T2", "Tensor.eval_const"), ("T3", "Tensor.eval_add"),
    ("T4", "Tensor.eval_scale"), ("T5", "Tensor.eval_mul"), ("T6", "Tensor.eval_padTo"),
    ("T7", "Tensor.eval_eq_of_beqPoly"), ("B0", "binom_eq_choose"), ("B1", "bernstein_nonneg"),
    ("C1", "verifyCover_covers"), ("K1", "bodyDenominator_pos"), ("K2", "body_position"),
    ("K3", "rotation_half_angle"), ("K4", "rodrigues_mem_specialOrthogonal"),
    ("C2", "checkOutsideLeaf_sound"), ("C3", "checkCollisionLeaf_sound"),
    ("C4", "collisionFree_iff_ref"), ("S1", "soundness"), ("S2", "soundness_ref"),
]
# Lemmas outside the 19 that the documentation cites.
CITED = [
    "bernNonneg_sound", "Tensor.continuous_eval", "check_eq_true_iff",
    "Joint.rotation_mem_specialOrthogonal", "linkPose_rot_mem_specialOrthogonal",
    "skewR_mulVec", "rodrigues_mulVec", "rodrigues_mulVec_axis",
]
# Certs/: staging lemmas and per-scene statements proved by kernel evaluation.
KERNEL = [
    "check_of_stages", "checkLeaf_collision_of", "checkLeaf_outside_of",
    "Certs.wallK3_proof", "Certs.wallK3_disconnected", "Certs.wallK3_disconnected_ref",
]
# Certs/: statements that go through native_decide (comparison only).
NATIVE = [
    "Certs.wallK3_proof_native", "Certs.s3ShoulderElbow_proof_native",
    "Certs.s6IiwaRealShelf_proof_native", "Certs.s3ShoulderElbow_disconnected_ref_native",
    "Certs.s6IiwaRealShelf_disconnected_ref_native",
]


def print_axioms(imports, names, prelude=""):
    """{name: set of axioms} from one `lake env lean` run."""
    src = "".join(f"import {m}\n" for m in imports) + prelude
    src += "".join(f"#print axioms {n}\n" for n in names)
    with tempfile.NamedTemporaryFile("w", suffix=".lean", delete=False, encoding="utf-8") as f:
        f.write(src)
        path = f.name
    try:
        run = subprocess.run(["lake", "env", "lean", path], cwd=LEAN, capture_output=True, text=True)
    finally:
        os.unlink(path)
    out = run.stdout + run.stderr
    found = {}
    for m in re.finditer(r"'([^']+)' depends on axioms: \[([^\]]*)\]", out, re.S):
        found[m.group(1)] = {a.strip() for a in m.group(2).split(",") if a.strip()}
    for m in re.finditer(r"'([^']+)' does not depend on any axioms", out):
        found[m.group(1)] = set()
    missing = [n for n in names if n not in found]
    if missing:
        print(out)
        raise SystemExit(f"axiom audit: no answer for {missing} (is the project built?)")
    return found


def verdict(axioms, kind):
    """'' if the axiom set is acceptable for `kind` ('kernel' or 'native'), else the reason."""
    extra = axioms - STANDARD
    if kind == "kernel":
        return "" if not extra else "non-standard axiom(s): " + ", ".join(sorted(extra))
    native = {a for a in extra if NATIVE_AX.search(a)}
    if extra - native:
        return "non-standard axiom(s): " + ", ".join(sorted(extra - native))
    if len(native) != 1:
        return f"expected exactly one native_decide axiom, found {len(native)}"
    return ""


def self_test():
    """The audit must flag `sorry` and `native_decide` when they are passed off as kernel proofs."""
    prelude = ("theorem auditSelfTestSorry : (2 : Nat) + 2 = 5 := sorry\n"
               "theorem auditSelfTestNative : (2 : Nat) + 2 = 4 := by native_decide\n"
               "theorem auditSelfTestPlain : (2 : Nat) + 2 = 4 := by decide\n")
    ax = print_axioms([], ["auditSelfTestSorry", "auditSelfTestNative", "auditSelfTestPlain"], prelude)
    ok = (verdict(ax["auditSelfTestSorry"], "kernel") != ""
          and verdict(ax["auditSelfTestNative"], "kernel") != ""
          and verdict(ax["auditSelfTestNative"], "native") == ""
          and verdict(ax["auditSelfTestPlain"], "kernel") == ""
          and verdict(ax["auditSelfTestPlain"], "native") != "")
    print("self-test (the audit can fail): sorry -> "
          f"{sorted(ax['auditSelfTestSorry'])}, native_decide -> {sorted(ax['auditSelfTestNative'])}"
          f" : {'flagged, OK' if ok else 'NOT FLAGGED'}")
    return ok


def main(argv) -> int:
    certs = "--no-certs" not in argv
    ok = self_test()
    groups = [("the 19 obligations", ["CnpVerify"],
               [(f"{tag} {n}", f"CnpVerify.{n}") for tag, n in OBLIGATIONS], "kernel"),
              ("cited lemmas outside the 19", ["CnpVerify"],
               [(n, f"CnpVerify.{n}") for n in CITED], "kernel")]
    if certs:
        groups += [("Certs: kernel evaluation", ["Certs.Disconnected"],
                    [(n, f"CnpVerify.{n}") for n in KERNEL], "kernel"),
                   ("Certs: native_decide (comparison)", ["Certs.DisconnectedNative"],
                    [(n, f"CnpVerify.{n}") for n in NATIVE], "native")]
    for title, imports, items, kind in groups:
        print(f"\n{title} — expected: the three standard axioms"
              + (" + exactly one native_decide axiom" if kind == "native" else " only"))
        ax = print_axioms(imports, [full for _, full in items])
        for label, full in items:
            why = verdict(ax[full], kind)
            shown = ", ".join(sorted(ax[full], key=lambda a: (a not in STANDARD, a))) or "(none)"
            print(f"  {'ok  ' if not why else 'FAIL'}  {label}: {shown}" + (f"   <-- {why}" if why else ""))
            ok = ok and not why
    print("\naxiom audit: " + ("OK" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
