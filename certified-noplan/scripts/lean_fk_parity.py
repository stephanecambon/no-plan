#!/usr/bin/env python3
"""L3 control — exact parity of the forward kinematics, Lean checker vs ``verify.py``.

    .venv/bin/python scripts/lean_fk_parity.py [--perturb] [cert.json ...]

For every certificate (default: all shipped ones) and three fixed rational configurations,
compares VALUE FOR VALUE (exact rationals, as strings) the common denominator ``D`` and the
world position ``N_k / D`` of every body vertex, as computed by

  * the Lean checker's kinematics (``lean/FkDump.lean``, run with ``lake env lean --run``);
  * ``verify.py``'s own ``_body_fk`` / ``_vertex_numerators`` (imported read-only).

The Lean theorem K2 (``body_position``) proves that the Lean REFERENCE kinematics ``linkPose``
equals the Lean ``N/D``; this script measures that the Lean ``N/D`` equals the Python one.
Both sides are exact, so exact equality is the expected outcome (not a noise-level
coincidence): the reference is taken OUTSIDE the tested object and every variable is nonzero.

``--perturb`` is the control of the control: it flips the sign of the FIRST variable (the base
joint, on which every body depends) on the Python side only; the comparison must then FAIL
(exit code 1) on every certificate.

Exit code 0 iff the two outputs are identical (without ``--perturb``).
"""
import argparse
import glob
import json
import os
import subprocess
import sys
from fractions import Fraction

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from cnp import verify as V  # noqa: E402  (read-only use of the arbiter's own FK)


def point(n, p, perturb):
    out = []
    for i in range(n):
        v = Fraction(i + 1, p + 3 + 2 * i)
        out.append(v if (i + p) % 2 == 0 else -v)
    if perturb and n:
        out[0] = -out[0]
    return out


def ev(t, x):
    tot = Fraction(0)
    for e, c in t.items():
        term = Fraction(c)
        for i, ei in enumerate(e):
            term *= x[i] ** ei
        tot += term
    return tot


def fmt(q):
    q = Fraction(q)
    return str(q.numerator) if q.denominator == 1 else f"{q.numerator}/{q.denominator}"


def python_lines(paths, perturb):
    lines = []
    for path in paths:
        with open(path) as f:
            cert = json.load(f)
        T, D, n = V._body_fk(cert["robot"], int(cert["body"]["link"]))
        verts = V._vertex_numerators(T, D, cert["body"]["hull_vertices"], n)
        for p in (0, 1, 2):
            x = point(n, p, perturb)
            d = ev(D, x)
            lines.append(f"{path} p{p} D {fmt(d)}")
            for k, v in enumerate(verts):
                for r in range(3):
                    lines.append(f"{path} p{p} v{k} {r} {fmt(ev(v[r], x) / d)}")
    return lines


def lean_lines(paths):
    out = subprocess.run(["lake", "env", "lean", "--run", "FkDump.lean", *paths],
                         cwd=os.path.join(ROOT, "lean"), capture_output=True, text=True, check=True)
    return out.stdout.splitlines()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("certs", nargs="*")
    ap.add_argument("--perturb", action="store_true")
    args = ap.parse_args()
    paths = [os.path.abspath(p) for p in args.certs] or sorted(
        glob.glob(os.path.join(ROOT, "scenes", "*.cert.json"))
        + glob.glob(os.path.join(ROOT, "scenes", "wall", "*.cert.json")))
    py = python_lines(paths, args.perturb)
    ln = lean_lines(paths)
    n_diff = sum(a != b for a, b in zip(py, ln)) + abs(len(py) - len(ln))
    n_den = sum(" D " in s for s in ln)
    print(f"certificates: {len(paths)}; values compared: {len(ln)} "
          f"({n_den} denominators, {len(ln) - n_den} coordinates); differing: {n_diff}")
    if n_diff:
        bad = sorted({a.split()[0] for a, b in zip(py, ln) if a != b})
        print("differing certificates: " + ", ".join(os.path.relpath(b, ROOT) for b in bad))
    print("IDENTICAL" if n_diff == 0 else "DIFFERENT")
    return 0 if n_diff == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
