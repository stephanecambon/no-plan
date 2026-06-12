"""S9c — soundness of LOCKED-joint support in the independent verifier (cnp.verify).

The iiwa "deep bin" scenes lock 1-2 joints (SPEC §6 S4). A locked joint is substituted
by its numeric rotation, so the certificate carries its EXACT rational cos/sin (SPEC §4,
``cos^2+sin^2 == 1``) and the verifier RE-DERIVES the Rodrigues rotation independently.

This is a soundness-in-the-act test (CLAUDE.md rule 1), the locked-joint counterpart of
test_verify.py: it proves the verifier (a) accepts an honest locked-joint PROOF, and
(b) rejects every adversarial corruption of the lock —

  * cos/sin CORRUPTED so ``cos^2+sin^2 != 1`` (not an exact rotation);
  * the locked joint MOVED to a different (still valid) rotation — verify re-derives the
    FK, so the trapped wrist relocates out of the wall and the leaves stop certifying;
  * the joint UNLOCKED (removed) — the s-variable count no longer matches.

The honest round-trip uses :func:`cert_scenes.spatial_locked_scene` (pitch joint j1
locked at the Pythagorean 3-4-5 angle), the first scene whose exact proof DEPENDS on a
locked joint's value.
"""
import copy
import os
import sys
from fractions import Fraction as F

import pytest

sys.path.insert(0, os.path.dirname(__file__))

import cert_scenes  # noqa: E402
from cnp import certificate as cert, scenes, verify  # noqa: E402


@pytest.fixture(scope="module")
def locked_cert():
    """An honest locked-joint certificate (j1 locked at 3/4/5), verified as PROOF."""
    res, c = cert.certify(cert_scenes.spatial_locked_scene(), axis="margin")
    assert res.verdict == "PROOF", f"locked scene must be PROOF, got {res.verdict}"
    ok, msg = verify.verify(c)
    assert ok, f"baseline locked certificate must verify: {msg}"
    return c


def test_locked_joint_round_trip_is_proof(locked_cert):
    """A q*=0 spatial scene WITH a locked joint reaches the full PROOF verdict (S9c):
    the cert carries the exact cos/sin and the scene is exactly verifiable."""
    assert locked_cert["robot"]["locked_joints"] == {"1": {"cos": "3/5", "sin": "4/5"}}
    assert int(locked_cert["robot"]["n"]) == 2          # two unlocked joints (s0, s2)
    assert scenes.is_exactly_verifiable(cert_scenes.spatial_locked_scene())


def test_identity_lock_is_proof():
    """A joint locked at angle 0 (cos=1, sin=0, a pure identity rotation) also certifies
    and verifies — the degenerate but valid corner of the Rodrigues substitution."""
    res, c = cert.certify(cert_scenes.spatial_locked_scene(lock1=("1", "0")), axis="margin")
    assert res.verdict == "PROOF"
    assert verify.verify(c)[0]


# --------------------------------------------------------------------------- #
# Adversarial mutations of the lock — the verifier must reject every one.
# --------------------------------------------------------------------------- #

def _m_cos_sin_not_unit(c):
    c["robot"]["locked_joints"]["1"] = {"cos": "1/2", "sin": "1/2"}   # 1/4+1/4 != 1


def _m_lock_moved_flip(c):
    c["robot"]["locked_joints"]["1"] = {"cos": "-3/5", "sin": "4/5"}  # valid, pitched up


def _m_lock_moved_quarter(c):
    c["robot"]["locked_joints"]["1"] = {"cos": "0", "sin": "1"}       # valid, 90 deg


def _m_lock_moved_straight(c):
    c["robot"]["locked_joints"]["1"] = {"cos": "1", "sin": "0"}       # valid, straight


def _m_lock_removed(c):
    c["robot"]["locked_joints"] = {}                                  # n now disagrees


def _m_lock_wrong_index(c):
    c["robot"]["locked_joints"] = {"0": {"cos": "3/5", "sin": "4/5"}}  # locks the wrong joint


LOCK_MUTATIONS = [
    ("cos_sin_not_unit", _m_cos_sin_not_unit),
    ("lock_moved_flip", _m_lock_moved_flip),
    ("lock_moved_quarter", _m_lock_moved_quarter),
    ("lock_moved_straight", _m_lock_moved_straight),
    ("lock_removed", _m_lock_removed),
    ("lock_wrong_index", _m_lock_wrong_index),
]


@pytest.mark.parametrize("name,mutate", LOCK_MUTATIONS, ids=[m[0] for m in LOCK_MUTATIONS])
def test_lock_mutation_is_rejected(locked_cert, name, mutate):
    """Every corrupted lock is rejected in exact arithmetic (CLAUDE.md rule 1). The
    verifier re-derives the FK from cos/sin, so it cannot be fooled by a moved lock."""
    bad = copy.deepcopy(locked_cert)
    mutate(bad)
    ok, msg = verify.verify(bad)
    assert ok is False, f"lock mutation {name!r} was NOT rejected: {msg}"


def test_generator_rejects_non_unit_lock():
    """The generator (:class:`cnp.certificate.Robot`) also fails fast on a lock whose
    cos/sin are not an exact rotation — defence in depth, not only at verify time."""
    with pytest.raises(ValueError, match="cos.2.sin.2"):
        cert.Robot(kind="spatial_revolute", link_lengths=[], q_star=[0],
                   locked={0: {"cos": "1/2", "sin": "1/2"}},
                   joints=[{"offset": ["0", "0", "0"], "axis": ["0", "0", "1"]}])
