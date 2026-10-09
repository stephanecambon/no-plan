"""L1 — export the adversarial certificate corpus as JSON files for the Lean checker.

The Lean executable ``cnp-verify`` (certified-noplan/lean/) must return the SAME verdict as
``cnp.verify.verify`` on every certificate of the repo and on every adversarial mutation of the
test suite. The mutations only exist as Python functions applied to in-memory certificates; this
script WRITES each mutated certificate to a directory, next to a ``manifest.json`` recording what
the Python verifier answers (verdict + message). It does not touch the tests: the mutation
functions are imported from them, never copied — except the spatial suite, whose mutations are
lambdas local to the test bodies of ``tests/test_adversarial.py`` and are transcribed below with
their line of origin.

Corpus (each entry: one certificate, one expected verdict):
  * ``planar``  — the 26 mutations of ``tests/test_verify.py`` on the E3 certificate (46 leaves);
  * ``locked``  — the 6 mutations of ``tests/test_locked_joints.py`` on the locked-joint certificate;
  * ``spatial`` — the 7 rejected mutations of ``tests/test_adversarial.py`` on the S2b certificate,
    plus the geometry swap that the verifier must ACCEPT (internally valid, caught by the scene
    cross-check only);
  * ``garbage`` — the 4 junk inputs of ``test_verifier_never_raises_on_garbage``;
  * ``baseline`` — the unmutated certificates of the three suites and the identity lock (PROOF).

Usage:  .venv/bin/python scripts/export_mutations.py <out_dir>
"""
from __future__ import annotations

import copy
import json
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "tests"))

import cert_scenes  # noqa: E402
import test_locked_joints  # noqa: E402
import test_verify  # noqa: E402
from cnp import certificate as cert, engine, scenes, verify  # noqa: E402


def _first_collision(c):
    return next(lf for lf in c["leaves"] if lf["status"] == "collision")


def _bust_lambda(c):                                   # test_adversarial.py:209-211
    lf = _first_collision(c)
    lf["lambda"][0][next(iter(lf["lambda"][0]))] = "7"


# (name, mutation, verifier must accept?) — tests/test_adversarial.py, lines in comments.
SPATIAL_MUTATIONS = [
    ("axis_flipped_to_y",                              # :193
     lambda c: c["robot"]["joints"][0].__setitem__("axis", ["0", "1", "0"]), False),
    ("offset_lifted",                                  # :195
     lambda c: c["robot"]["joints"][1].__setitem__("offset", ["0", "0", "5"]), False),
    ("axis_not_unit",                                  # :197
     lambda c: c["robot"]["joints"][2].__setitem__("axis", ["0", "2", "0"]), False),
    ("lambda_busted", _bust_lambda, False),            # :213
    ("mu_negative",                                    # :214-215
     lambda c: _first_collision(c).__setitem__("mu", ["-1"] + _first_collision(c)["mu"][1:]),
     False),
    ("leaf_popped", lambda c: c["leaves"].pop(), False),                       # :216
    ("collision_relabelled_outside",                   # :217
     lambda c: _first_collision(c).update(status="outside"), False),
    ("geometry_swap_internally_valid",                 # :226-227 — verify ACCEPTS
     lambda c: c["robot"]["joints"][1].__setitem__("offset", ["0", "0", "1/4"]), True),
]

GARBAGE = [("empty", {}), ("theorem_only", {"theorem": "disconnection"}),
           ("leaves_only", {"leaves": []}), ("null_field", {"x": None})]  # test_verify.py:223-224


def _baselines():
    _, planar = cert.certify(cert_scenes.e3_scene(), axis="oracle")
    _, locked = cert.certify(cert_scenes.spatial_locked_scene(), axis="margin")
    _, identity = cert.certify(cert_scenes.spatial_locked_scene(lock1=("1", "0")), axis="margin")
    scene, budget = scenes.load(os.path.join(_REPO, "scenes", "S2b_spatial3.yaml"))
    res = engine.solve(scenes.build_problem(scene, max_depth=budget.max_depth),
                       axis=budget.axis, budget=budget.engine_budget())
    spatial = cert.make_certificate(scene, res, verify_loop=True)
    return planar, locked, identity, spatial


def build_corpus():
    """Return ``[(suite, name, certificate, must_accept)]`` — nothing is written here."""
    planar, locked, identity, spatial = _baselines()
    corpus = [("baseline", "planar_E3", planar, True),
              ("baseline", "locked_345", locked, True),
              ("baseline", "locked_identity", identity, True),
              ("baseline", "spatial_S2b", spatial, True)]
    for name, mutate in test_verify.MUTATIONS:
        bad = copy.deepcopy(planar)
        mutate(bad)
        corpus.append(("planar", name, bad, False))
    for name, mutate in test_locked_joints.LOCK_MUTATIONS:
        bad = copy.deepcopy(locked)
        mutate(bad)
        corpus.append(("locked", name, bad, False))
    for name, mutate, accept in SPATIAL_MUTATIONS:
        bad = copy.deepcopy(spatial)
        mutate(bad)
        corpus.append(("spatial", name, bad, accept))
    for name, junk in GARBAGE:
        corpus.append(("garbage", name, junk, False))
    return corpus


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    out_dir = argv[0]
    os.makedirs(out_dir, exist_ok=True)
    manifest = []
    for i, (suite, name, c, must_accept) in enumerate(build_corpus()):
        ok, msg = verify.verify(c)
        if ok is not must_accept:
            raise SystemExit(f"{suite}/{name}: Python verdict {ok} but the test suite expects "
                             f"{must_accept} — the corpus is out of sync with the tests")
        fname = f"{i:02d}_{suite}__{name}.cert.json"
        with open(os.path.join(out_dir, fname), "w") as f:
            json.dump(c, f, indent=1, sort_keys=True)
        manifest.append({"file": fname, "suite": suite, "name": name,
                         "python_ok": ok, "python_message": msg})
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    n_rej = sum(1 for m in manifest if not m["python_ok"])
    print(f"{len(manifest)} certificates written to {out_dir} "
          f"({n_rej} rejected by Python, {len(manifest) - n_rej} accepted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
