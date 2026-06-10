"""Tensor polynomials with per-variable bounded degree + Bernstein bounds.

Ported verbatim from sandbox_reference/polylin.py (campagne E1-E4). The numerical
behaviour MUST stay identical to the sandbox — it is the shared kernel of the
generator. The Bernstein transform is re-implemented independently in verify.py
(in exact rationals); see SPEC §5. The self-tests that lived in the sandbox
``__main__`` block are now tests/test_polylin.py.

A polynomial in n variables with degree <= d per variable is a coefficient
tensor of shape (d+1,)*n  (entry [e1,...,en] = coeff of s1^e1...sn^en).

PolyLin: a polynomial whose coefficients are AFFINE in a vector of decision
variables z:  P(s; z) = C0(s) + sum_j z_j * Cj(s).
Stored as {'const': tensor, j: tensor}.
"""
import numpy as np
from itertools import product as iproduct


# ---------- fixed-tensor utilities ----------

def zeros(n, d):
    return np.zeros((d + 1,) * n)

def mono(n, d, expo, coeff=1.0):
    t = zeros(n, d)
    t[tuple(expo)] = coeff
    return t

def tmul(a, b, d_out):
    """Multiply two coefficient tensors (full convolution), output degree d_out per var."""
    n = a.ndim
    out = zeros(n, d_out)
    nz_a = np.argwhere(a != 0)
    nz_b = np.argwhere(b != 0)
    for ea in nz_a:
        ca = a[tuple(ea)]
        for eb in nz_b:
            e = ea + eb
            if np.any(e > d_out):
                raise ValueError("degree overflow")
            out[tuple(e)] += ca * b[tuple(eb)]
    return out

def teval(t, s):
    """Evaluate tensor polynomial at point s (len n)."""
    n = t.ndim
    d = t.shape[0] - 1
    pw = [np.array([si ** k for k in range(d + 1)]) for si in s]
    out = t
    for i in range(n):
        out = np.tensordot(out, pw[n - 1 - i], axes=([out.ndim - 1], [0]))
    return float(out)


# ---------- Bernstein ----------

def _shift_matrix(d, lo, hi):
    """Matrix S with a'_q = sum_p S[q,p] a_p  for substitution s = lo + (hi-lo)*x."""
    from math import comb
    S = np.zeros((d + 1, d + 1))
    w = hi - lo
    for p in range(d + 1):
        # (lo + w x)^p = sum_q C(p,q) lo^(p-q) w^q x^q
        for q in range(p + 1):
            S[q, p] += comb(p, q) * (lo ** (p - q)) * (w ** q)
    return S

def _bern_matrix(d):
    """b_i = sum_j C(i,j)/C(d,j) a_j   (monomial on [0,1] -> Bernstein coeffs)."""
    from math import comb
    B = np.zeros((d + 1, d + 1))
    for i in range(d + 1):
        for j in range(i + 1):
            B[i, j] = comb(i, j) / comb(d, j)
    return B

def _apply_mode(t, M, axis):
    t = np.moveaxis(t, axis, 0)
    shp = t.shape
    t = M @ t.reshape(shp[0], -1)
    t = t.reshape((M.shape[0],) + shp[1:])
    return np.moveaxis(t, 0, axis)

def bernstein_coeffs(t, box):
    """Bernstein coefficient tensor of t over box=[(lo,hi)]*n. min(b) <= min poly."""
    n = t.ndim
    d = t.shape[0] - 1
    out = t.astype(float)
    B = _bern_matrix(d)
    for i in range(n):
        lo, hi = box[i]
        out = _apply_mode(out, B @ _shift_matrix(d, lo, hi), i)
    return out


# ---------- linear-in-z polynomials ----------

class PolyLin:
    """P(s; z) with coefficients affine in decision vector entries (by integer id)."""
    def __init__(self, n, d):
        self.n, self.d = n, d
        self.terms = {}  # key: 'const' or int var id -> tensor

    def add(self, key, tensor):
        if key in self.terms:
            self.terms[key] = self.terms[key] + tensor
        else:
            self.terms[key] = tensor.copy()
        return self

    def mul_fixed(self, fixed, d_out):
        """Multiply by a FIXED tensor polynomial."""
        q = PolyLin(self.n, d_out)
        for k, t in self.terms.items():
            q.add(k, tmul(t, fixed, d_out))
        return q

    def __add__(self, other):
        d = max(self.d, other.d)
        q = PolyLin(self.n, d)
        for src in (self, other):
            for k, t in src.terms.items():
                tt = zeros(self.n, d)
                sl = tuple(slice(0, t.shape[0]) for _ in range(self.n))
                tt[sl] = t
                q.add(k, tt)
        return q

    def scale(self, c):
        q = PolyLin(self.n, self.d)
        for k, t in self.terms.items():
            q.add(k, c * t)
        return q

    def bernstein_rows(self, box, nvars):
        """Return (A, b): Bernstein coeffs = A @ z + b   (A: m x nvars)."""
        m = (self.d + 1) ** self.n
        A = np.zeros((m, nvars))
        b = np.zeros(m)
        for k, t in self.terms.items():
            bc = bernstein_coeffs(t, box).reshape(-1)
            if k == 'const':
                b += bc
            else:
                A[:, k] += bc
        return A, b

    def coeff_rows(self, nvars):
        """Return (A, b): flattened raw coefficients = A @ z + b."""
        m = (self.d + 1) ** self.n
        A = np.zeros((m, nvars))
        b = np.zeros(m)
        for k, t in self.terms.items():
            fc = t.reshape(-1)
            if k == 'const':
                b += fc
            else:
                A[:, k] += fc
        return A, b
