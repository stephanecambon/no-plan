"""S3 guard (CLAUDE.md rule 3 / SPEC §9.4): the Drake wheel pulls Mosek in
transitively, but NOTHING on the critical path may wake it. This replaces human
vigilance with a test.

Finding (journalled): merely *importing cvxpy* wakes Mosek — cvxpy enumerates every
installed solver at import, and the Drake-bundled mosek is one of them (even though
we only ever solve with CLARABEL/HiGHS). So the Mosek-free guarantee requires the
critical path to avoid cvxpy. It does: the engine's default back-end is
``HighsBackend`` (scipy.linprog), and ``import cnp.engine`` does not import cvxpy.

Each check runs in a FRESH subprocess so that imports leaked by other tests in the
same pytest process (which DO touch cvxpy → mosek) cannot mask a real regression.
"""
import subprocess
import sys


def _run(code: str):
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, f"guard subprocess failed:\nSTDOUT {r.stdout}\nSTDERR {r.stderr}"


def test_core_import_is_mosek_and_cvxpy_free():
    """Importing the core never wakes mosek (nor cvxpy, which would wake mosek)."""
    _run(
        "import sys\n"
        "import cnp.polylin, cnp.witness, cnp.engine\n"
        "assert 'mosek' not in sys.modules, 'core import woke mosek'\n"
        "assert 'cvxpy' not in sys.modules, 'core import woke cvxpy (which wakes mosek)'\n"
    )


def test_default_engine_solve_is_mosek_free():
    """A real witness solve through the engine's DEFAULT back-end (HiGHS) certifies a
    collision cell without ever importing mosek or cvxpy (CLAUDE.md rule 3)."""
    _run(
        "import sys, numpy as np\n"
        "from cnp import engine, witness\n"
        "from cnp.polylin import mono, zeros\n"
        # a 2-vertex body sitting at the origin, inside a big box ⇒ always collides
        "D = zeros(2, 2); D[0, 0] = 1.0\n"
        "one = mono(2, 2, [0, 0]); z = zeros(2, 2)\n"
        "verts = [[one, one, z], [one, one, z]]\n"
        "ob = witness.Polytope.box([-5, -5, -5], [5, 5, 5])\n"
        "pair = engine.Pair('o', verts, D, ob)\n"
        "prob = engine.Problem(box=[(-0.1, 0.1), (-0.1, 0.1)], phi=mono(2, 2, [1, 0]),"
        " delta=0.05, pairs=[pair], max_depth=2)\n"
        "r = engine.solve(prob, budget=engine.Budget(max_leaves=6))\n"
        "assert any(l.status == 'collision' for l in r.leaves), r.counts()\n"
        "assert 'mosek' not in sys.modules, 'critical-path solve woke mosek (rule 3)'\n"
        "assert 'cvxpy' not in sys.modules, 'critical-path solve woke cvxpy'\n"
    )


def test_cvxpy_backend_wakes_mosek_documented():
    """Documents the finding the engine default avoids: the cvxpy back-end DOES wake
    mosek at solve time. If a future cvxpy stops doing this, update the rationale."""
    _run(
        "import sys\n"
        "import numpy as np\n"
        "from cnp import witness\n"
        "from cnp.polylin import mono, zeros\n"
        "D = zeros(2, 2); D[0, 0] = 1.0\n"
        "one = mono(2, 2, [0, 0]); z = zeros(2, 2)\n"
        "verts = [[one, one, z], [one, one, z]]\n"
        "ob = witness.Polytope.box([-5, -5, -5], [5, 5, 5])\n"
        "witness.certify_cell_pair([(-0.1, 0.1), (-0.1, 0.1)], verts, D, ob,"
        " phi=mono(2, 2, [1, 0]), delta=0.05, backend=witness.CvxpyBackend())\n"
        "assert 'mosek' in sys.modules, 'cvxpy no longer wakes mosek — revisit rule-3 note'\n"
    )
