"""S2 — generic n-dim slab-aware witness LP (cnp.witness).

Exit criteria (CLAUDE.md S2):
  * S1-planar embedded in 3D reproduces the E3 certificate (same leaves/pairs).
  * a minimal 3-DOF *spatial* scene: witness vs sampled ground truth — when the LP
    certifies, NO free configuration is found over 1e5 samples of the cell.

Soundness controls (CLAUDE.md rules 1-2, adversarial suite after touching witness):
  * the Putinar sign is frozen (g - mu*T sound; g + mu*T falsely certifies a
    genuinely-false premise);
  * shrunk obstacles (false premise) are refused.

Back-end isolation (SPEC §3): a second, independent solver (scipy.linprog) consumes
the same solver-agnostic WitnessLP and agrees with the cvxpy back-end.
"""
import itertools
import sys
import os

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(__file__))

import regref  # noqa: E402  (the frozen S0 oracle: planar FK + scenes)
from cnp import witness  # noqa: E402
from cnp.polylin import mono  # noqa: E402
from cnp.ratfk import RevoluteJoint, SympyRatFK  # noqa: E402

TOL = 1e-6
PHI = mono(2, 2, [1, 0])   # E3 hand barrier phi = s1
DELTA = 0.05


# --------------------------------------------------------------------------- #
# S1-planar (E3) embedded in 3D
# --------------------------------------------------------------------------- #

def _e3_body_3d():
    """The 2-link planar arm's distal segment as a 3D body: two vertices (p1, p2)
    at z = 0, numerators over the common denominator D (from the frozen oracle)."""
    D, P1X, P1Y, C12, S12 = regref.fk_tensors()
    Zt = np.zeros_like(P1X)
    p1 = [P1X, P1Y, Zt]
    p2 = [P1X + C12, P1Y + S12, Zt]
    return [p1, p2], D


def _box3(planar_box, zh=1.0):
    """A planar (xlo,xhi,ylo,yhi) obstacle extruded to a 3D box spanning z in [-zh,zh]
    (the arm lives at z=0, so the two z-faces are slack)."""
    xlo, xhi, ylo, yhi = planar_box
    return witness.Polytope.box([xlo, ylo, -zh], [xhi, yhi, zh])


def _bb_witness(boxes, names, verts, D, max_depth=16, tol=TOL):
    """Branch-and-bound driving the generic witness over the 2-D s-box. The control
    flow MIRRORS the frozen oracle regref.certify_slab (same axis heuristic, same
    outside test) so the ONLY variable is the certifier — the real n-dim engine is
    S3. Returns (ok, leaves, failed)."""
    obs = [_box3(b) for b in boxes]
    leaves, failed = [], []

    def rec(cell, depth):
        if regref.cell_outside_slab(cell, PHI, DELTA):
            leaves.append((cell, "outside", None, None))
            return True
        best, bestname = None, None
        for ob, nm in zip(obs, names):
            ts = witness.certify_cell_pair(
                cell, verts, D, ob, phi=PHI, delta=DELTA, lam_degree="affine").t
            if ts is not None and (best is None or ts > best):
                best, bestname = ts, nm
        if best is not None and best > tol:
            leaves.append((cell, "collision", bestname, best))
            return True
        if depth >= max_depth:
            failed.append(cell)
            leaves.append((cell, "FAIL", None, best))
            return False
        i = 0 if (cell[0][1] - cell[0][0]) >= (cell[1][1] - cell[1][0]) else 1
        for ax in (0, 1):
            mid_ = 0.5 * (cell[ax][0] + cell[ax][1])
            for half in ((cell[ax][0], mid_), (mid_, cell[ax][1])):
                cc = [list(c) for c in cell]; cc[ax] = list(half)
                if regref.cell_outside_slab([tuple(x) for x in cc], PHI, DELTA):
                    i = ax; break
            else:
                continue
            break
        mid = 0.5 * (cell[i][0] + cell[i][1])
        c1 = [list(c) for c in cell]; c2 = [list(c) for c in cell]
        c1[i][1] = mid; c2[i][0] = mid
        ok1 = rec([tuple(c) for c in c1], depth + 1)
        ok2 = rec([tuple(c) for c in c2], depth + 1)
        return ok1 and ok2

    ok = rec([tuple(c) for c in regref.LIM], 0)
    return ok, leaves, failed


@pytest.mark.parametrize("cell", [
    [(-0.125, 0.0), (0.875, 1.0)],
    [(0.0, 0.5), (-0.5, 0.5)],
    [(-1.0, 1.0), (-1.0, 1.0)],
])
def test_witness_matches_regref_oracle(cell):
    """The generic 3D witness reproduces the frozen 2D oracle's t* on every pair
    (the extruded z-faces are slack, so the margin is set by the x/y faces)."""
    verts, D = _e3_body_3d()
    cell = [tuple(c) for c in cell]
    for b in (regref.UP, regref.DOWN, regref.MID):
        t_ref = regref.certify_cell_pair(cell, b, PHI, DELTA)
        t_new = witness.certify_cell_pair(
            cell, verts, D, _box3(b), phi=PHI, delta=DELTA, lam_degree="affine").t
        if t_ref is None:
            assert t_new is None
        else:
            assert t_new is not None
            assert abs(t_ref - t_new) < 1e-7


def test_e3_embedded_3d_reproduces_certificate():
    """S2 exit criterion #1: S1-planar embedded in 3D gives the E3 certificate
    (46 leaves: 38 collision UP12/DOWN12/MID14, 8 outside, 0 fail)."""
    verts, D = _e3_body_3d()
    ok, leaves, failed = _bb_witness(
        [regref.UP, regref.DOWN, regref.MID], ["UP", "DOWN", "MID"], verts, D)
    assert ok is True
    assert len(failed) == 0
    assert len(leaves) == 46
    col = sum(1 for l in leaves if l[1] == "collision")
    out = sum(1 for l in leaves if l[1] == "outside")
    used = {}
    for l in leaves:
        if l[1] == "collision":
            used[l[2]] = used.get(l[2], 0) + 1
    assert (col, out) == (38, 8)
    assert used == {"UP": 12, "DOWN": 12, "MID": 14}


def test_witness_sign_is_frozen():
    """CLAUDE.md rule 2: the slab term is g - mu*T. On a genuinely-false premise
    (shrunk UP, a cell with free configs) the SOUND sign refuses while g + mu*T
    falsely certifies. Flipping the default would break this."""
    verts, D = _e3_body_3d()
    up_shrunk = regref.shrink(regref.UP)
    ob = _box3(up_shrunk)
    cell = [(-0.125, 0.0), (0.875, 1.0)]

    # The premise really is false here: free configs exist against shrunk UP.
    free = 0
    for s1 in np.linspace(-0.125, 0.0, 15):
        for s2 in np.linspace(0.875, 1.0, 15):
            if not regref.in_collision(2 * np.arctan(s1), 2 * np.arctan(s2), [up_shrunk]):
                free += 1
    assert free > 0

    t_sound = witness.certify_cell_pair(
        cell, verts, D, ob, phi=PHI, delta=DELTA, _putinar_sign=-1).t
    t_unsound = witness.certify_cell_pair(
        cell, verts, D, ob, phi=PHI, delta=DELTA, _putinar_sign=+1).t
    assert t_sound < 0          # sound sign refuses the false premise
    assert t_unsound > 0        # g + mu*T would falsely certify it


def test_e3_negative_control_refuses_3d():
    """Soundness: obstacles shrunk 30% open free samples in the slab; the witness-
    driven b&b must NOT certify (some FAIL leaf)."""
    verts, D = _e3_body_3d()
    boxes = [regref.shrink(b) for b in (regref.UP, regref.DOWN, regref.MID)]
    ok, leaves, failed = _bb_witness(boxes, ["UP", "DOWN", "MID"], verts, D)
    assert ok is False
    assert len(failed) > 0


# --------------------------------------------------------------------------- #
# Minimal 3-DOF *spatial* scene (sympy fallback FK, no network)
# --------------------------------------------------------------------------- #

def _tr(x, y, z):
    T = np.eye(4)
    T[:3, 3] = [x, y, z]
    return T


@pytest.fixture(scope="module")
def spatial3():
    """A generic 3R spatial chain (axes z, y, y) and its distal segment body.
    Returns (body, verts_num, D, cell, bbox_lo, bbox_hi)."""
    joints = [
        RevoluteJoint("j0", _tr(0, 0, 0),   np.array([0, 0, 1.0])),
        RevoluteJoint("j1", _tr(0, 0, 0.3), np.array([0, 1.0, 0])),
        RevoluteJoint("j2", _tr(0.3, 0, 0), np.array([0, 1.0, 0])),
    ]
    fk = SympyRatFK(joints)
    assert fk.n == 3
    body = fk.body("j2")
    vbf = [[0.0, 0.0, 0.0], [0.3, 0.0, 0.0]]   # link as a segment (2 hull vertices)
    verts = body.vertex_numerators(vbf)
    D = body.D
    cell = [(-0.1, 0.1)] * 3
    # Swept bounding box of the two vertices over a grid of the cell.
    grid = np.linspace(-0.1, 0.1, 7)
    pts = [body.eval_world_point(v, s)
           for s in itertools.product(grid, grid, grid) for v in vbf]
    pts = np.array(pts)
    return body, vbf, verts, D, cell, pts.min(0), pts.max(0)


def test_3dof_spatial_certifies_and_no_free_point(spatial3):
    """S2 exit criterion #2: a 3-DOF spatial cell whose moving link lies inside an
    obstacle is certified, and over 1e5 samples of the cell the witness point is
    ALWAYS inside the obstacle (certifie => aucun point libre)."""
    _body, _vbf, verts, D, cell, lo, hi = spatial3
    eps = 0.03
    ob = witness.Polytope.box(lo - eps, hi + eps)

    res = witness.certify_cell_pair(cell, verts, D, ob, phi=None, lam_degree="affine")
    assert res.t is not None and res.t > TOL

    rng = np.random.default_rng(0)
    S = rng.uniform(-0.1, 0.1, size=(100_000, 3))
    X = witness.eval_witness_point(res, verts, D, S)
    inside = np.all(X @ ob.A.T <= ob.b + 1e-9, axis=1)
    assert int((~inside).sum()) == 0


def test_3dof_spatial_negative_control(spatial3):
    """Soundness: shrink the obstacle about its centre (false premise). Free configs
    appear (segment entirely outside the box) AND the witness refuses (t <= 0)."""
    body, vbf, verts, D, cell, lo, hi = spatial3
    c = 0.5 * (lo + hi)
    f = 0.5
    obn = witness.Polytope.box(c - (c - lo) * f, c + (hi - c) * f)

    res = witness.certify_cell_pair(cell, verts, D, obn, phi=None, lam_degree="affine")
    assert res.t is None or res.t <= TOL

    free = 0
    grid = np.linspace(-0.1, 0.1, 9)
    ts = np.linspace(0, 1, 40)[:, None]
    for s in itertools.product(grid, grid, grid):
        seg = np.array([body.eval_world_point(v, s) for v in vbf])
        segpts = seg[0] * (1 - ts) + seg[1] * ts
        if not np.all(segpts @ obn.A.T <= obn.b + 1e-12, axis=1).any():
            free += 1
    assert free > 0


# --------------------------------------------------------------------------- #
# API: Polytope, lambda degrees, back-end isolation
# --------------------------------------------------------------------------- #

def test_polytope_box():
    P = witness.Polytope.box([-1, 0, 2], [1, 3, 4])
    assert P.dim == 3 and P.n_faces == 6
    assert P.contains([0, 1, 3])
    assert not P.contains([0, 1, 5])


@pytest.mark.parametrize("kind,expected", [("const", 1), ("affine", 4), ("quadratic", 10)])
def test_lambda_basis_degrees(kind, expected):
    # total-degree-bounded basis in n=3: const 1, affine 1+3, quadratic 1+3+6
    assert len(witness.lambda_basis(3, kind)) == expected


def test_lambda_quadratic_certifies(spatial3):
    """A richer (quadratic) lambda still yields a sound certificate on the positive
    spatial cell (degree is configurable, SPEC §2)."""
    _body, _vbf, verts, D, cell, lo, hi = spatial3
    ob = witness.Polytope.box(lo - 0.03, hi + 0.03)
    res = witness.certify_cell_pair(cell, verts, D, ob, phi=None, lam_degree="quadratic")
    assert res.t is not None and res.t > TOL


class _SciPyBackend(witness.LPBackend):
    """An independent back-end (scipy.linprog) over the SAME WitnessLP, to prove the
    LP container is solver-agnostic (SPEC §3 back-end isolation)."""

    name = "scipy"

    def solve(self, lp):
        from scipy.optimize import linprog

        # variables x = [z (nz, free), mu (nmu, >=0), t (free)], maximize t.
        nz, nmu = lp.nz, lp.nmu
        nv = nz + nmu + 1
        ti = nv - 1
        c = np.zeros(nv); c[ti] = -1.0  # minimize -t
        # equality: eq_A z == eq_b
        A_eq = np.hstack([lp.eq_A, np.zeros((lp.eq_A.shape[0], nmu + 1))])
        b_eq = lp.eq_b
        # lambda >= 0:  -lam_A z <= lam_b
        ub_rows = [np.hstack([-lp.lam_A, np.zeros((lp.lam_A.shape[0], nmu + 1))])]
        ub_b = [lp.lam_b]
        # faces:  face_Az z + face_Amu mu - t >= -face_b  -> negate for <=
        face = np.hstack([face_part for face_part in
                          (lp.face_Az, lp.face_Amu, -np.ones((lp.face_Az.shape[0], 1)))])
        ub_rows.append(-face)
        ub_b.append(lp.face_b)
        A_ub = np.vstack(ub_rows)
        b_ub = np.concatenate(ub_b)
        bounds = [(None, None)] * nz + [(0, None)] * nmu + [(None, None)]
        r = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds,
                    method="highs")
        if not r.success:
            return witness.LPResult(None, r.message, basis=lp.basis, K=lp.K, dim=lp.dim)
        return witness.LPResult(float(-r.fun), "optimal", basis=lp.basis, K=lp.K, dim=lp.dim)


def test_backend_isolation_scipy_agrees():
    """The same WitnessLP solved by cvxpy and by scipy.linprog gives the same t*."""
    verts, D = _e3_body_3d()
    cell = [(-0.125, 0.0), (0.875, 1.0)]
    ob = _box3(regref.UP)
    t_cvxpy = witness.certify_cell_pair(
        cell, verts, D, ob, phi=PHI, delta=DELTA, backend=witness.CvxpyBackend()).t
    t_scipy = witness.certify_cell_pair(
        cell, verts, D, ob, phi=PHI, delta=DELTA, backend=_SciPyBackend()).t
    assert t_cvxpy is not None and t_scipy is not None
    assert abs(t_cvxpy - t_scipy) < 1e-6
