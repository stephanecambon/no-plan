"""E1 (witness ladder) + E2 (Bernstein-LP vs SOS-SDP), regression against the frozen
sandbox reference exp12_results.json. Gate G0': t* reproduced to 1e-6 (LP).

Each reference row is replayed with the same back-end. The Bernstein-LP is the
critical path (CLAUDE.md rule 3): it must match the stored t* to 1e-6. The SOS-SDP
rows are an interior-point cross-check; they are matched to a looser SDP tolerance
and, per the E2 claim, must agree with the LP optimum.
"""
import json
import os

import pytest

from regref import scene_tensors, solve_bernstein, solve_sos

# a_tot per scene tag (gamma fixed at 0.04 in the sandbox).
_A_TOT = {"collision": 0.44, "NEGATIVE": 0.85}

LP_ATOL = 1e-6     # G0' tolerance for the LP critical path
SOS_ATOL = 1e-5    # interior-point SDP tolerance

_REF_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "sandbox_reference", "exp12_results.json")
with open(_REF_PATH) as _f:
    _REFERENCE = json.load(_f)

_LP_ROWS = [r for r in _REFERENCE if r["backend"] == "bern-LP"]
_SOS_ROWS = [r for r in _REFERENCE if r["backend"] == "SOS-SDP"]


def _rid(r):
    return f"n{r['n']}-{r['scene']}-{r['kind']}"


def test_reference_shape():
    assert len(_LP_ROWS) == 16 and len(_SOS_ROWS) == 14


@pytest.mark.parametrize("r", _LP_ROWS, ids=_rid)
def test_bernstein_lp_reproduces_reference(r):
    verts, _ = scene_tensors(r["n"], _A_TOT[r["scene"]], 0.04)
    t, _dt, _nz = solve_bernstein(r["n"], r["kind"], verts)
    assert t is not None
    assert t == pytest.approx(r["t"], abs=LP_ATOL), (
        f"{_rid(r)}: got {t}, reference {r['t']}")


@pytest.mark.parametrize("r", _SOS_ROWS, ids=_rid)
def test_sos_sdp_reproduces_and_matches_lp(r):
    verts, _ = scene_tensors(r["n"], _A_TOT[r["scene"]], 0.04)
    t_sos, _dt, _sz = solve_sos(r["n"], r["kind"], verts)
    t_lp, _dt2, _nz = solve_bernstein(r["n"], r["kind"], verts)
    assert t_sos is not None
    # reproduces the stored SOS optimum ...
    assert t_sos == pytest.approx(r["t"], abs=SOS_ATOL), (
        f"{_rid(r)}: SOS got {t_sos}, reference {r['t']}")
    # ... and agrees with the LP optimum (E2: zero Bernstein conservatism here).
    assert t_sos == pytest.approx(t_lp, abs=SOS_ATOL)
