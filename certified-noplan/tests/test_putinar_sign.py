"""FREEZE the Putinar sign: the slab-aware constraint is Bernstein(g - mu*T) >= t.
g + mu*T is UNSOUND (CLAUDE.md rule 2 / SPEC §2 / E3 historical bug).

Construction (found by scanning the negative-control scene): a single cell + pair
where the obstacle does NOT cover the slab portion of the cell — the premise
"cell ⊆ C_obs (via this pair)" is FALSE (free configurations exist inside it). On
such an instance:

  * the SOUND sign (g - mu*T, the production default) REFUSES (t* <= 0); flipping
    the production default to + would make ``test_default_sign_refuses_false_premise``
    fail. That is the freeze.
  * the WRONG sign (g + mu*T) returns a positive margin — it would emit a FALSE
    certificate. ``test_wrong_sign_would_falsely_certify`` pins down the unsoundness.
"""
import numpy as np

import regref as R
from cnp.polylin import mono

PHI = mono(2, 2, [1, 0])     # phi = s1
DELTA = 0.05
TOL = 1e-6

# Pair = shrunken UP obstacle (negative control); cell straddling the slab where
# UP fails to cover. Provenance: scan in JOURNAL.md (S0).
BOX = R.shrink(R.UP)                       # (1.0195, 1.2505, 0.2255, 0.9045)
CELL = ((-0.125, 0.0), (0.875, 1.0))


def test_premise_is_actually_false():
    """Sanity: the cell genuinely contains collision-free configs vs this pair, so
    any positive certificate against it is a lie (not just a numerical artefact)."""
    free = 0
    for s1 in np.linspace(*CELL[0], 11):
        for s2 in np.linspace(*CELL[1], 11):
            if not R.in_collision(2 * np.arctan(s1), 2 * np.arctan(s2), [BOX]):
                free += 1
    assert free > 0


def test_default_sign_refuses_false_premise():
    """The production default (g - mu*T) must NOT certify a false premise.
    If someone flips the default sign to '+', this assertion breaks — the freeze."""
    t = R.certify_cell_pair(CELL, BOX, PHI, DELTA)  # default putinar_sign=-1
    assert t is None or t <= TOL, f"sound sign should refuse, got t*={t}"


def test_wrong_sign_would_falsely_certify():
    """Documents WHY the sign is frozen: g + mu*T spuriously certifies (unsound)."""
    t_bad = R.certify_cell_pair(CELL, BOX, PHI, DELTA, putinar_sign=+1)
    assert t_bad is not None and t_bad > TOL, (
        f"wrong sign should (unsoundly) certify, got t*={t_bad}")


def test_sound_strictly_below_unsound():
    """The two signs genuinely disagree on this instance (no ambiguity)."""
    t_ok = R.certify_cell_pair(CELL, BOX, PHI, DELTA, putinar_sign=-1)
    t_bad = R.certify_cell_pair(CELL, BOX, PHI, DELTA, putinar_sign=+1)
    assert t_ok < TOL < t_bad
