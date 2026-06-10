"""polylin self-tests, ported from sandbox_reference/polylin.py __main__ block
(PROMPT-DEMARRAGE task 2: keep the self-tests, as pytest)."""
from itertools import product as iproduct

import numpy as np

from cnp.polylin import zeros, mono, tmul, teval, bernstein_coeffs


def test_bernstein_bound_vs_dense_grid():
    """Bernstein coeff min/max bracket the true poly min/max on the box."""
    rng = np.random.default_rng(0)
    n, d = 3, 2
    t = rng.normal(size=(d + 1,) * n)
    box = [(-1.0, 1.0), (0.2, 0.9), (-0.5, 0.3)]
    grid = [np.linspace(lo, hi, 13) for lo, hi in box]
    vals = [teval(t, s) for s in iproduct(*grid)]
    bc = bernstein_coeffs(t, box)
    assert bc.min() <= min(vals) + 1e-9, (bc.min(), min(vals))
    assert bc.max() >= max(vals) - 1e-9


def test_bernstein_vertex_exactness_multilinear():
    """For a multilinear poly the Bernstein min equals the true min (at a vertex)."""
    n = 3
    box = [(-1.0, 1.0), (0.2, 0.9), (-0.5, 0.3)]
    tm = np.zeros((2,) * n); tm[(1, 0, 1)] = 2.0; tm[(0, 1, 0)] = -1.0; tm[(0, 0, 0)] = .3
    verts = [teval(tm, s) for s in iproduct(*[(lo, hi) for lo, hi in box])]
    bcm = bernstein_coeffs(tm, box)
    assert abs(bcm.min() - min(verts)) < 1e-9


def test_tmul_pointwise_product():
    """tmul gives the polynomial product: eval(a*b) == eval(a)*eval(b)."""
    rng = np.random.default_rng(0)
    n = 3
    a = rng.normal(size=(2,) * n); b2 = rng.normal(size=(2,) * n)
    ab = tmul(a, b2, 2)
    for _ in range(20):
        s = rng.uniform(-1, 1, n)
        assert abs(teval(ab, s) - teval(a, s) * teval(b2, s)) < 1e-8


def test_mono_and_zeros_shapes():
    """Sanity on the tensor constructors used everywhere downstream."""
    assert zeros(3, 2).shape == (3, 3, 3)
    m = mono(2, 2, [1, 0], 1.0)
    assert m.shape == (3, 3)
    assert teval(m, [0.7, -0.4]) == 0.7  # phi = s1
