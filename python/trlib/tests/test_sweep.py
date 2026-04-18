"""Layer 4: 3x3 parameter sweep smoke test.

The goal is *not* numerical validation -- it is to prove that the
``init -> set_param x N -> run -> get_state -> finalize`` cycle can be
driven in a loop without crashing the library (regression guard against
leaked state or dangling SAVE variables inside TRCOMM).

For each ``(RR, BB)`` pair on a 3x3 grid we:

* open a fresh :class:`trlib.Trlib` handle,
* apply the ``tr_iter01`` fixture as a realistic baseline parameter set,
* override ``RR`` and ``BB`` for this grid point,
* run a short integration (``NTMAX=5``),
* record the post-run ``WPT`` scalar and check it is finite.

A NaN/Inf on any point signals that TRCOMM state leaked across cycles,
so we fail loudly. Nine successful cycles -> PASS.

Skipped when ``libtrapi.so`` is not built.
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
PYTHON_ROOT = REPO / "python"
DEFAULT_SO = REPO / "tr" / "libtrapi.so"

if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))


def _trlib_importable() -> bool:
    try:
        import trlib  # noqa: F401
    except Exception:
        return False
    return True


@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libtrapi.so not built at {DEFAULT_SO}; run `make -C tr libtrapi.so`",
)
@unittest.skipUnless(_trlib_importable(), "python/trlib not importable")
class TestSweep(unittest.TestCase):
    """3x3 RR x BB grid; smoke-only (no numerical regression)."""

    #: Keep NTMAX tiny so the whole sweep completes well under the
    #: test_definitions.conf timeout (180 s).
    NTMAX = 5

    #: Grid centres sit near the ITER01 baseline so every point is a
    #: physically plausible perturbation rather than a pathological
    #: extreme that could crash for non-regression reasons.
    RR_VALUES = (7.5, 8.0, 8.5)
    BB_VALUES = (4.5, 5.0, 5.5)

    def test_3x3_grid_completes(self):
        from trlib import Trlib
        from trlib.tests.fixtures import tr_iter01_params

        results = []
        for rr in self.RR_VALUES:
            for bb in self.BB_VALUES:
                with Trlib() as tr:
                    # Realistic base parameters from the ITER01 fixture.
                    tr_iter01_params.apply(tr)
                    # Override the swept axes.
                    tr.set_param("RR", float(rr))
                    tr.set_param("BB", float(bb))
                    # Short run -- smoke only.
                    tr.run(self.NTMAX)
                    state = tr.get_state()
                    wpt = state.scalars.get("WPT", float("nan"))
                    results.append((rr, bb, wpt))

        # All 9 points must have completed.
        self.assertEqual(len(results), 9, f"expected 9 results, got {len(results)}")

        # All WPT values must be finite. NaN/Inf would indicate state
        # corruption between cycles or a divergent solver.
        for rr, bb, wpt in results:
            with self.subTest(rr=rr, bb=bb):
                self.assertFalse(
                    math.isnan(wpt),
                    f"NaN WPT at RR={rr} BB={bb}",
                )
                self.assertFalse(
                    math.isinf(wpt),
                    f"Inf WPT at RR={rr} BB={bb}",
                )


if __name__ == "__main__":
    unittest.main()
