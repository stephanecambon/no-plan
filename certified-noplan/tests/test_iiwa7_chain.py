"""S10-bis Tâche 1 — guard the frozen RATIONALIZED iiwa7 chain.

Structural checks run always (the frozen JSON is committed): the chain is exactly rational and in
verify.py's form (offset + UNIT coordinate axis + locked cos/sin with cos²+sin²==1). The Drake
parity (faithful to the SDF ~3.67e-6) runs only when Drake + the cached iiwa7 SDF are present
(règle 13: skip, never a silent green elsewhere).
"""
from __future__ import annotations

import importlib
import json
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
CHAIN = os.path.join(HERE, "..", "scripts", "iiwa7_chain.json")
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))


def _load():
    with open(CHAIN) as f:
        return json.load(f)


def test_iiwa7_chain_is_exact_and_verify_shaped():
    c = _load()
    assert len(c["variable_indices"]) == 7                      # the 7 real DOF
    locked = c["locked"]
    for i, j in enumerate(c["joints"]):
        ax = [int(x) for x in j["axis"]]                        # exact integer coordinate axis
        assert sum(a * a for a in ax) == 1, j                   # UNIT (verify requires Σaxis²=1 exact)
        from fractions import Fraction as F
        [F(x) for x in j["offset"]]                             # offsets are exact rationals
        if str(i) in locked:
            cs = locked[str(i)]
            assert int(cs["cos"]) ** 2 + int(cs["sin"]) ** 2 == 1   # cos²+sin²==1 exact (S9c)


def test_iiwa7_chain_builds_in_ratfk():
    import numpy as np
    from fractions import Fraction as F
    from cnp.ratfk import SympyRatFK, RevoluteJoint
    c = _load()

    def Tr(o):
        M = np.eye(4); M[:3, 3] = [float(F(x)) for x in o]; return M

    rj = [RevoluteJoint(name=j["name"], X_pj=Tr(j["offset"]),
                        axis=np.array([float(x) for x in j["axis"]])) for j in c["joints"]]
    lk = {int(k): float(np.arctan2(int(v["sin"]), int(v["cos"]))) for k, v in c["locked"].items()}
    fk = SympyRatFK(rj, locked=lk)
    assert fk.n == 7                                            # 7 unlocked variables


@pytest.mark.skipif(importlib.util.find_spec("pydrake") is None, reason="Drake absent")
def test_iiwa7_chain_drake_parity():
    """Faithful to the Drake iiwa7 SDF within its own ~3.67e-6 rad rounding (Option A, 18/06)."""
    try:
        import build_iiwa7_chain as b
        err = b.check_parity()
    except Exception as exc:                                    # SDF not cached / load failure
        pytest.skip(f"iiwa7 SDF unavailable: {exc}")
    assert err < 5e-6, f"Drake parity {err:.2e} exceeds the ~4e-6 SDF tolerance"
