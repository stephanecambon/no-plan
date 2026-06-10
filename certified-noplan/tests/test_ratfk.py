"""S1 exit criteria for cnp.ratfk (rational forward kinematics).

Three required checks (CLAUDE.md S1 "Sortie"):
  1. numeric FK vs numerator tensors: 1000 random iiwa configs, error < 1e-9;
  2. locked joints;
  3. degree <= 2 per variable per joint.

Plus validation of the Drake-free sympy REPLI (SPEC §9.4) against an independent
numeric homogeneous-transform FK, and Drake<->sympy parity on identical kinematics.
"""
import numpy as np
import pytest

from cnp import ratfk
from cnp.ratfk import RevoluteJoint, SympyRatFK

drake = pytest.importorskip("pydrake", reason="Drake not installed (optional [drake] extra)")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _build_iiwa():
    from pydrake.multibody.plant import MultibodyPlant
    from pydrake.multibody.parsing import Parser
    from pydrake.math import RigidTransform

    plant = MultibodyPlant(0.0)
    Parser(plant).AddModelsFromUrl(
        "package://drake_models/iiwa_description/sdf/iiwa7_no_collision.sdf")
    plant.WeldFrames(plant.world_frame(),
                     plant.GetBodyByName("iiwa_link_0").body_frame(), RigidTransform())
    plant.Finalize()
    return plant


@pytest.fixture(scope="module")
def iiwa():
    try:
        return _build_iiwa()
    except Exception as exc:  # pragma: no cover - network/model fetch failure
        pytest.skip(f"iiwa model unavailable: {exc}")


# A few arbitrary body-frame points to exercise R @ p (not just the origin).
_POINTS = np.array([[0.0, 0.0, 0.0],
                    [0.05, -0.03, 0.12],
                    [-0.1, 0.07, -0.04]])

_IIWA_LINKS = [f"iiwa_link_{k}" for k in range(1, 8)]


def _rodrigues(axis, theta):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(theta) * K + (1 - np.cos(theta)) * (K @ K)


def _numeric_chain_fk(joints, q, locked, upto):
    """Independent numeric world transform of link `upto` (homogeneous 4x4)."""
    T = np.eye(4)
    for i in range(upto + 1):
        theta = locked[i] if i in locked else q[i]
        R = _rodrigues(joints[i].axis, theta)
        Ti = np.eye(4)
        Ti[:3, :3] = R
        T = T @ (np.asarray(joints[i].X_pj, float) @ Ti)
    return T


def _random_chain(rng, nq=3):
    """A random spatial serial revolute chain spec."""
    joints = []
    for i in range(nq):
        Xpj = np.eye(4)
        Xpj[:3, 3] = rng.uniform(-0.3, 0.3, 3)
        # small random fixed rotation on the parent offset frame
        Xpj[:3, :3] = _rodrigues(rng.normal(size=3), rng.uniform(-1.0, 1.0))
        axis = rng.normal(size=3)
        joints.append(RevoluteJoint(name=f"link{i}", X_pj=Xpj, axis=axis))
    return joints


# --------------------------------------------------------------------------- #
# 1. FK numeric vs tensors — 1000 random iiwa configs, error < 1e-9
# --------------------------------------------------------------------------- #

def test_fk_numeric_vs_tensors_iiwa(iiwa):
    fk = ratfk.DrakeRatFK(iiwa)
    ctx = iiwa.CreateDefaultContext()
    lo = iiwa.GetPositionLowerLimits()
    hi = iiwa.GetPositionUpperLimits()
    assert np.all(lo > -np.pi) and np.all(hi < np.pi)  # SPEC: limits inside (-pi,pi)
    bodies = {name: fk.body(name) for name in _IIWA_LINKS}

    rng = np.random.default_rng(1)
    max_err = 0.0
    for _ in range(1000):
        q = rng.uniform(lo + 1e-3, hi - 1e-3)
        s = fk.s_value(q)
        iiwa.SetPositions(ctx, q)
        for name in _IIWA_LINKS:
            X_WB = iiwa.EvalBodyPoseInWorld(ctx, iiwa.GetBodyByName(name))
            bfk = bodies[name]
            for p in _POINTS:
                truth = X_WB @ p
                got = bfk.eval_world_point(p, s)
                max_err = max(max_err, float(np.max(np.abs(got - truth))))
    assert max_err < 1e-9, f"max FK error {max_err:.2e}"


# --------------------------------------------------------------------------- #
# 2. Locked joints
# --------------------------------------------------------------------------- #

def test_locked_joints_iiwa(iiwa):
    locked = {1: 0.35, 4: -0.6}  # position indices held fixed
    fk = ratfk.DrakeRatFK(iiwa, locked=locked)
    assert fk.n == 5
    ctx = iiwa.CreateDefaultContext()
    lo = iiwa.GetPositionLowerLimits()
    hi = iiwa.GetPositionUpperLimits()
    bodies = {name: fk.body(name) for name in _IIWA_LINKS}

    rng = np.random.default_rng(2)
    max_err = 0.0
    for _ in range(300):
        q = rng.uniform(lo + 1e-3, hi - 1e-3)
        for p_idx, val in locked.items():
            q[p_idx] = val  # plant must use the locked values
        s = fk.s_value(q)            # only the 5 unlocked entries
        assert len(s) == 5
        iiwa.SetPositions(ctx, q)
        for name in _IIWA_LINKS:
            X_WB = iiwa.EvalBodyPoseInWorld(ctx, iiwa.GetBodyByName(name))
            for p in _POINTS:
                truth = X_WB @ p
                got = bodies[name].eval_world_point(p, s)
                max_err = max(max_err, float(np.max(np.abs(got - truth))))
    assert max_err < 1e-9, f"max locked-FK error {max_err:.2e}"


# --------------------------------------------------------------------------- #
# 3. Degree <= 2 per variable per joint
# --------------------------------------------------------------------------- #

def test_degree_le_2_per_var_iiwa(iiwa):
    fk = ratfk.DrakeRatFK(iiwa)
    for name in _IIWA_LINKS:
        bfk = fk.body(name)
        assert bfk.max_degree_per_var() <= 2
        # numerator/denominator tensors are shaped exactly (3,)*n (deg 2 per var)
        assert bfk.D.shape == (3,) * fk.n
        for t in bfk.pos_num:
            assert t.shape == (3,) * fk.n
        # denominator depends only on the chain joints, with degree exactly 2 each
        for sidx in bfk.s_chain:
            e = [0] * fk.n
            e[sidx] = 2
            assert bfk.D[tuple(e)] == 1.0


def test_chain_grows_along_iiwa(iiwa):
    fk = ratfk.DrakeRatFK(iiwa)
    # link_k depends on joints 0..k-1 (the EE depends on all 7).
    assert fk.body("iiwa_link_1").s_chain == (0,)
    assert fk.body("iiwa_link_7").s_chain == tuple(range(7))


# --------------------------------------------------------------------------- #
# Sympy REPLI — validated against independent numeric FK
# --------------------------------------------------------------------------- #

def test_sympy_fallback_vs_numeric():
    pytest.importorskip("sympy")
    rng = np.random.default_rng(3)
    joints = _random_chain(rng, nq=3)
    fk = SympyRatFK(joints)
    max_err = 0.0
    for _ in range(1000):
        q = rng.uniform(-2.5, 2.5, 3)
        s = fk.s_value(q)
        for k in range(3):
            truth = _numeric_chain_fk(joints, q, {}, k)
            bfk = fk.body(k)
            for p in _POINTS:
                got = bfk.eval_world_point(p, s)
                truthp = (truth @ np.append(p, 1.0))[:3]
                max_err = max(max_err, float(np.max(np.abs(got - truthp))))
    assert max_err < 1e-9, f"max sympy-FK error {max_err:.2e}"


def test_sympy_fallback_locked():
    pytest.importorskip("sympy")
    rng = np.random.default_rng(4)
    joints = _random_chain(rng, nq=3)
    locked = {1: 0.4}
    fk = SympyRatFK(joints, locked=locked)
    assert fk.n == 2
    max_err = 0.0
    for _ in range(300):
        q = rng.uniform(-2.5, 2.5, 3)
        q[1] = locked[1]
        s = fk.s_value(q)
        assert len(s) == 2
        for k in range(3):
            truth = _numeric_chain_fk(joints, q, locked, k)
            for p in _POINTS:
                got = fk.body(k).eval_world_point(p, s)
                truthp = (truth @ np.append(p, 1.0))[:3]
                max_err = max(max_err, float(np.max(np.abs(got - truthp))))
    assert max_err < 1e-9, f"max locked sympy-FK error {max_err:.2e}"


def test_sympy_degree_le_2_per_var():
    pytest.importorskip("sympy")
    rng = np.random.default_rng(5)
    joints = _random_chain(rng, nq=4)
    fk = SympyRatFK(joints)
    for k in range(4):
        assert fk.body(k).max_degree_per_var() <= 2


# --------------------------------------------------------------------------- #
# Drake <-> sympy parity on identical kinematics (network-free programmatic plant)
# --------------------------------------------------------------------------- #

def _build_drake_chain(joints):
    """Build a Drake plant with the SAME kinematics as the RevoluteJoint spec."""
    from pydrake.multibody.plant import MultibodyPlant
    from pydrake.multibody.tree import (SpatialInertia, UnitInertia,
                                        RevoluteJoint as DrakeRevolute)
    from pydrake.multibody.tree import FixedOffsetFrame
    from pydrake.math import RigidTransform, RotationMatrix

    plant = MultibodyPlant(0.0)
    M = SpatialInertia(1.0, np.zeros(3), UnitInertia(1.0, 1.0, 1.0))
    parent = plant.world_body()
    for jt in joints:
        body = plant.AddRigidBody(jt.name, M)
        Xpj = RigidTransform(RotationMatrix(np.asarray(jt.X_pj)[:3, :3]),
                             np.asarray(jt.X_pj)[:3, 3])
        F = plant.AddFrame(FixedOffsetFrame(
            jt.name + "_F", parent.body_frame(), Xpj))
        axis = np.asarray(jt.axis, float)
        axis = axis / np.linalg.norm(axis)
        plant.AddJoint(DrakeRevolute(jt.name + "_j", F, body.body_frame(), axis))
        parent = body
    plant.Finalize()
    return plant


def test_drake_sympy_parity():
    pytest.importorskip("sympy")
    rng = np.random.default_rng(6)
    joints = _random_chain(rng, nq=3)
    plant = _build_drake_chain(joints)
    fk_d = ratfk.DrakeRatFK(plant)
    fk_s = SympyRatFK(joints)
    # tensors agree entrywise
    for k in range(3):
        bd, bs = fk_d.body(joints[k].name), fk_s.body(k)
        assert bd.s_chain == bs.s_chain
        assert np.allclose(bd.D, bs.D, atol=1e-9)
        for i in range(3):
            assert np.allclose(bd.pos_num[i], bs.pos_num[i], atol=1e-9)
    # and both reproduce the numeric FK
    max_err = 0.0
    for _ in range(200):
        q = rng.uniform(-2.5, 2.5, 3)
        s = fk_d.s_value(q)
        for k in range(3):
            truth = _numeric_chain_fk(joints, q, {}, k)[:3, 3]
            max_err = max(max_err, float(np.max(np.abs(fk_d.body(joints[k].name).eval_world_point([0, 0, 0], s) - truth))))
    assert max_err < 1e-9
