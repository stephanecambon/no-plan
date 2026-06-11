"""S4 — exact-rational certificate generator (cnp.certificate) + round-trip.

Exit criteria (CLAUDE.md S4): generate -> verify OK on every regression scene; the
certificate is pure exact rationals; verify.py is sacred (independent, no numpy / no
generator import, < 500 lines). The mutation soundness suite lives in test_verify.py.
"""
import os
import sys
from fractions import Fraction

import pytest

sys.path.insert(0, os.path.dirname(__file__))

import cert_scenes  # noqa: E402
from cnp import certificate as cert, verify  # noqa: E402

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "src", "cnp")


# --------------------------------------------------------------------------- #
# Round-trip: generate -> verify, reproducing the frozen oracle partition
# --------------------------------------------------------------------------- #

def test_e3_roundtrip_46_leaves():
    """E3 via the exact scene model: 46 leaves (38 collision, 8 outside), verified
    exactly by the independent verifier. Kept in test-fast (~0.7 s) so the full
    generate->verify path is covered daily."""
    result, c = cert.certify(cert_scenes.e3_scene(), axis="oracle")
    assert result.verdict == "PROOF"
    assert c["stats"] == {"n_leaves": 46, "n_collision": 38, "n_outside": 8}
    ok, msg = verify.verify(c)
    assert ok, msg


@pytest.mark.slow
def test_e4_roundtrip_78_leaves():
    """E4 (learned barrier, rationalised to denominators <= 1e6) via the exact scene
    model: 78 leaves, 76 collision, verified exactly — reproducing the oracle."""
    result, c = cert.certify(cert_scenes.e4_scene(), axis="oracle")
    assert result.verdict == "PROOF"
    assert c["stats"]["n_leaves"] == 78
    assert c["stats"]["n_collision"] == 76
    ok, msg = verify.verify(c)
    assert ok, msg


# --------------------------------------------------------------------------- #
# The certificate is pure exact rationals (SPEC §4)
# --------------------------------------------------------------------------- #

def test_certificate_numbers_are_exact_rationals():
    """Every numeric field is a string parseable as an exact Fraction — no floats
    leak into the certificate (SPEC §4)."""
    _, c = cert.certify(cert_scenes.e3_scene(), axis="oracle")

    def is_rat(x):
        try:
            Fraction(x)
            return "e" not in x and "E" not in x  # reject float exponent notation
        except (ValueError, ZeroDivisionError):
            return False

    assert is_rat(c["delta"])
    for v in c["start_s"] + c["goal_s"]:
        assert is_rat(v)
    for lo, hi in c["box"]:
        assert is_rat(lo) and is_rat(hi)
    for v in c["robot"]["link_lengths"] + c["robot"]["q_star"]:
        assert is_rat(v)
    for coeff in c["phi"]["coeffs"].values():
        assert is_rat(coeff)
    for obs in c["obstacles"].values():
        for row in obs["A"]:
            assert all(is_rat(x) for x in row)
        assert all(is_rat(x) for x in obs["b"])
    for lf in c["leaves"]:
        for lo, hi in lf["cell"]:
            assert is_rat(lo) and is_rat(hi)
        if lf["status"] == "collision":
            assert is_rat(lf["margin"])
            assert all(is_rat(m) for m in lf["mu"])
            for lam in lf["lambda"]:
                assert all(is_rat(v) for v in lam.values())


def test_save_load_roundtrip(tmp_path):
    _, c = cert.certify(cert_scenes.e3_scene(), axis="oracle")
    p = str(tmp_path / "cert.json")
    cert.save(c, p)
    ok, _ = verify.verify_file(p)
    assert ok


def test_make_certificate_refuses_undecided():
    """An UNDECIDED engine result is not certifiable (SPEC §1, CLAUDE.md rule 6)."""
    from cnp import engine
    scene = cert_scenes.e3_scene()
    problem = cert.scene_to_problem(scene)
    result = engine.solve(problem, axis="oracle", budget=engine.Budget(max_leaves=4))
    assert result.verdict == "UNDECIDED"
    with pytest.raises(ValueError, match="non-PROOF"):
        cert.make_certificate(scene, result)


# --------------------------------------------------------------------------- #
# verify.py is SACRED (CLAUDE.md rule 4)
# --------------------------------------------------------------------------- #

def test_verify_under_500_lines():
    with open(os.path.join(_SRC, "verify.py")) as f:
        n = sum(1 for _ in f)
    assert n < 500, f"verify.py has {n} lines (rule 4: < 500)"


def test_verify_imports_are_isolated():
    """verify.py imports ONLY the standard library — no numpy, no import from the
    generator (cnp.polylin / ratfk / witness / engine / certificate). SPEC §5."""
    import ast
    with open(os.path.join(_SRC, "verify.py")) as f:
        src = f.read()
    allowed = {"__future__", "json", "fractions", "math"}
    mods = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            mods.add((node.module or "").split(".")[0])
    bad = mods - allowed
    assert not bad, f"verify.py must not import {bad} (rule 4 / SPEC §5)"
    assert "numpy" not in mods and "cnp" not in mods
