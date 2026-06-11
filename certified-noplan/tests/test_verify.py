"""S4 — soundness of the independent verifier (cnp.verify).

The exit criterion (CLAUDE.md S4): a corpus of >= 20 corrupted certificates, each
breaking a DIFFERENT part of the proof (lambda coeff, mu, cut point, pair, q_star,
delta, condition (i), partition cover, FK geometry, ...), must ALL be rejected. The
honest round-trip (a TRUE certificate is accepted) is in test_certificate.py.

This is a soundness-in-the-act test (CLAUDE.md rule 1), the verify.py counterpart of
test_putinar_sign.py: it proves the verifier refuses falsehoods, not merely that it
accepts the one truth we built.
"""
import copy
import os
import sys
from fractions import Fraction as F

import pytest

sys.path.insert(0, os.path.dirname(__file__))

import cert_scenes  # noqa: E402
from cnp import certificate as cert, verify  # noqa: E402


@pytest.fixture(scope="module")
def good_cert():
    """A true E3 certificate (46 leaves), verified once as the baseline."""
    _, c = cert.certify(cert_scenes.e3_scene(), axis="oracle")
    ok, msg = verify.verify(c)
    assert ok, f"baseline certificate must verify: {msg}"
    return c


def _first(c, status):
    return next(i for i, lf in enumerate(c["leaves"]) if lf["status"] == status)


def _leaf_for_obstacle(c, name):
    return next(i for i, lf in enumerate(c["leaves"])
               if lf["status"] == "collision" and lf["obstacle"] == name)


# --------------------------------------------------------------------------- #
# Mutations. Each takes a fresh (already deep-copied) certificate and corrupts it
# in ONE specific way; the verifier must reject every one.
# --------------------------------------------------------------------------- #

def _m_mu_negative(c):
    c["leaves"][_first(c, "collision")]["mu"][0] = "-5"


def _m_mu_huge(c):
    i = _first(c, "collision")
    c["leaves"][i]["mu"][0] = str(F(c["leaves"][i]["mu"][0]) + 1000)


def _m_lambda_breaks_sum(c):
    lam = c["leaves"][_first(c, "collision")]["lambda"]
    k = next(iter(lam[0]))
    lam[0][k] = str(F(lam[0][k]) + F(1, 3))


def _m_lambda_scaled(c):
    lam = c["leaves"][_first(c, "collision")]["lambda"]
    lam[0] = {k: str(F(v) * 2) for k, v in lam[0].items()}


def _m_lambda_negative(c):
    """Force a lambda to be negative somewhere by flipping the constant term sign
    while keeping the sum identity broken-free is impossible — so this also breaks the
    sum; the point is the verifier rejects either way."""
    lam = c["leaves"][_first(c, "collision")]["lambda"]
    lam[0]["0,0"] = str(F(lam[0].get("0,0", "0")) - 2)


def _m_cut_shifted(c):
    i = _first(c, "collision")
    lo, hi = c["leaves"][i]["cell"][0]
    c["leaves"][i]["cell"][0] = [lo, str(F(hi) + F(1, 7))]


def _m_drop_leaf(c):
    del c["leaves"][_first(c, "outside")]


def _m_duplicate_leaf(c):
    c["leaves"].append(copy.deepcopy(c["leaves"][_first(c, "collision")]))


def _m_qstar(c):
    c["robot"]["q_star"][0] = "1/10"


def _m_delta_x20(c):
    c["delta"] = str(F(c["delta"]) * 20)


def _m_delta_negative(c):
    c["delta"] = "-1/20"


def _m_start_wrong_side(c):
    c["start_s"] = ["1/2", "0"]


def _m_goal_wrong_side(c):
    c["goal_s"] = ["-1/2", "0"]


def _m_phi_sign(c):
    c["phi"]["coeffs"] = {k: str(-F(v)) for k, v in c["phi"]["coeffs"].items()}


def _m_obstacle_b_shrunk(c):
    i = _leaf_for_obstacle(c, "MID")
    obs = c["obstacles"]["MID"]
    obs["b"][0] = str(F(obs["b"][0]) - 1)


def _m_obstacle_a(c):
    c["obstacles"]["MID"]["A"][0] = ["2", "0", "0"]


def _m_hull_vertex(c):
    c["body"]["hull_vertices"][1] = ["1/2", "0", "0"]


def _m_link_length(c):
    # link_lengths[0] is joint-1's frame offset => it enters the body-link FK
    # (link_lengths[1] would only matter for a link beyond body_link=1).
    c["robot"]["link_lengths"][0] = "1/2"


def _m_body_link(c):
    c["body"]["link"] = 0


def _m_collision_to_outside(c):
    """Relabel an in-slab collision leaf as 'outside' — its cell meets the slab, so
    the Bernstein outside-test must fail."""
    # pick the collision leaf whose cell straddles s0 = 0 (inside the |phi|<=delta slab)
    for lf in c["leaves"]:
        if lf["status"] == "collision":
            lo, hi = (F(x) for x in lf["cell"][0])
            if lo < 0 < hi or abs(lo) < F(c["delta"]) or abs(hi) < F(c["delta"]):
                lf["status"] = "outside"
                lf.pop("obstacle", None); lf.pop("lambda", None); lf.pop("mu", None)
                return
    lf = c["leaves"][_first(c, "collision")]
    lf["status"] = "outside"


def _m_outside_to_collision(c):
    c["leaves"][_first(c, "outside")]["status"] = "collision"


def _m_swap_obstacle(c):
    i = _leaf_for_obstacle(c, "UP")
    c["leaves"][i]["obstacle"] = "DOWN"


def _m_theorem(c):
    c["theorem"] = "feasibility"


def _m_substitution(c):
    c["kinematics"]["substitution"] = "drake_native"


def _m_box_shrunk(c):
    c["box"][0] = ["-1", "1/2"]


def _m_extra_cell_outside_box(c):
    c["leaves"].append({"cell": [["1", "2"], ["-1", "1"]], "status": "outside"})


MUTATIONS = [
    ("mu_negative", _m_mu_negative),
    ("mu_huge", _m_mu_huge),
    ("lambda_breaks_sum", _m_lambda_breaks_sum),
    ("lambda_scaled", _m_lambda_scaled),
    ("lambda_negative", _m_lambda_negative),
    ("cut_shifted", _m_cut_shifted),
    ("drop_leaf_gap", _m_drop_leaf),
    ("duplicate_leaf_overlap", _m_duplicate_leaf),
    ("qstar_changed", _m_qstar),
    ("delta_x20", _m_delta_x20),
    ("delta_negative", _m_delta_negative),
    ("start_wrong_side", _m_start_wrong_side),
    ("goal_wrong_side", _m_goal_wrong_side),
    ("phi_sign_flipped", _m_phi_sign),
    ("obstacle_b_shrunk", _m_obstacle_b_shrunk),
    ("obstacle_a_changed", _m_obstacle_a),
    ("hull_vertex_changed", _m_hull_vertex),
    ("link_length_changed", _m_link_length),
    ("body_link_changed", _m_body_link),
    ("collision_relabelled_outside", _m_collision_to_outside),
    ("outside_relabelled_collision", _m_outside_to_collision),
    ("obstacle_swapped_in_leaf", _m_swap_obstacle),
    ("theorem_changed", _m_theorem),
    ("substitution_changed", _m_substitution),
    ("box_shrunk", _m_box_shrunk),
    ("extra_cell_outside_box", _m_extra_cell_outside_box),
]


def test_at_least_20_mutations():
    assert len(MUTATIONS) >= 20


@pytest.mark.parametrize("name,mutate", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_mutation_is_rejected(good_cert, name, mutate):
    """Every corrupted certificate is rejected in exact arithmetic (CLAUDE.md rule 1).
    The verifier never raises on bad input — it returns (False, reason)."""
    bad = copy.deepcopy(good_cert)
    mutate(bad)
    ok, msg = verify.verify(bad)
    assert ok is False, f"mutation {name!r} was NOT rejected: {msg}"


def test_verifier_never_raises_on_garbage():
    for junk in ({}, {"theorem": "disconnection"}, {"leaves": []}, None):
        ok, _ = verify.verify(junk if isinstance(junk, dict) else {"x": junk})
        assert ok is False
