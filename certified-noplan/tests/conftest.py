"""Shared fixtures for the S0 regression suite. The planar sandbox scenes (E3/E4)
become reusable fixtures here (PROMPT-DEMARRAGE task 3)."""
import json
import os
import sys

import numpy as np
import pytest

# Ensure the regression oracle (tests/regref.py) is importable regardless of the
# pytest import mode.
sys.path.insert(0, os.path.dirname(__file__))

import regref  # noqa: E402
from cnp.polylin import mono  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXP12_RESULTS = os.path.join(_REPO, "sandbox_reference", "exp12_results.json")


@pytest.fixture(scope="session")
def exp12_reference():
    """The frozen E1/E2 reference rows (t* per n/scene/kind/backend)."""
    with open(EXP12_RESULTS) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def e3_scene():
    """E3: 3 obstacles relaying along the slab, hand barrier phi = s1, delta=0.05."""
    return dict(
        boxes=[regref.UP, regref.DOWN, regref.MID],
        names=["UP", "DOWN", "MID"],
        phi=mono(2, 2, [1, 0]),
        delta=0.05,
        start=(-np.pi / 3, 0.0),
        goal=(np.pi / 3, 0.0),
    )


@pytest.fixture(scope="session")
def e3_negative_scene():
    """Negative control: obstacles shrunk 30% so the slab is NOT fully in collision
    (false premise). The certifier MUST refuse (soundness)."""
    boxes = [regref.shrink(b) for b in (regref.UP, regref.DOWN, regref.MID)]
    return dict(
        boxes=boxes,
        names=["UP", "DOWN", "MID"],
        phi=mono(2, 2, [1, 0]),
        delta=0.05,
    )


@pytest.fixture(scope="session")
def e4_scene():
    """E4: learned barrier (seeded least-squares fit) over the E3 obstacles."""
    boxes = [regref.UP, regref.DOWN, regref.MID]
    phi_fit, delta_f, start, goal = regref.fit_phi_e4(boxes)
    return dict(boxes=boxes, names=["UP", "DOWN", "MID"],
                phi=phi_fit, delta=delta_f, start=start, goal=goal)
