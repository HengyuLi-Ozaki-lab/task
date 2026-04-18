"""Layer 4: 3x3 parameter sweep smoke test.

The goal is *not* numerical validation -- it is to prove that the
``init -> set_param x N -> run -> get_state -> finalize`` cycle can be
driven in a loop without crashing the library (regression guard against
leaked state or dangling SAVE variables inside FPCOMM).

For each ``(RR, BB)`` pair on a 3x3 grid we:

* open a fresh :class:`fplib.Fplib` handle,
* apply the ``fp_iter01`` fixture as a realistic baseline parameter set,
* override ``RR`` and ``BB`` for this grid point,
* shrink the problem (``NRMAX=10, NPMAX=20, NTHMAX=20, NTMAX=1``) so the
  full 9-point sweep finishes well under the ``test_definitions.conf``
  timeout,
* record the post-run ``TIMEFP`` scalar and check it is finite and > 0.

A NaN/Inf on any point signals that FPCOMM state leaked across cycles,
so we fail loudly. Nine successful cycles -> PASS.

Skipped when ``libfpapi.so`` is not built.
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
PYTHON_ROOT = REPO / "python"
DEFAULT_SO = REPO / "fp" / "libfpapi.so"

if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))


def _fplib_importable() -> bool:
    try:
        import fplib  # noqa: F401
    except Exception:
        return False
    return True


@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libfpapi.so not built at {DEFAULT_SO}; run `make -C fp libfpapi.so`",
)
@unittest.skipUnless(_fplib_importable(), "python/fplib not importable")
class TestSweep(unittest.TestCase):
    """3x3 RR x BB grid; smoke-only (no numerical regression)."""

    #: Keep NTMAX tiny so the whole sweep completes well under the
    #: test_definitions.conf timeout (600 s).
    NTMAX = 1

    #: Tiny mesh overrides so 9 cycles of init/run/finalize run in a
    #: reasonable wall-time on CI. Physics is not validated.
    NRMAX_SMALL  = 10
    NPMAX_SMALL  = 20
    NTHMAX_SMALL = 20

    #: Grid centres near the ITER01 defaults so every point is a
    #: physically plausible perturbation rather than a pathological
    #: extreme that could crash for non-regression reasons.
    RR_VALUES = (6.0, 6.5, 7.0)
    BB_VALUES = (5.0, 5.3, 5.6)

    def test_3x3_grid_completes(self):
        from fplib import Fplib
        from fplib.tests.fixtures import fp_iter01_params

        results = []
        for rr in self.RR_VALUES:
            for bb in self.BB_VALUES:
                with Fplib() as fp:
                    # Realistic base parameters from the ITER01 fixture.
                    fp_iter01_params.apply(fp)
                    # Shrink the problem for CI runtime.
                    fp.set_param("NRMAX",  float(self.NRMAX_SMALL))
                    fp.set_param("NPMAX",  float(self.NPMAX_SMALL))
                    fp.set_param("NTHMAX", float(self.NTHMAX_SMALL))
                    fp.set_param("NTMAX",  float(self.NTMAX))
                    # Override the swept axes.
                    fp.set_param("RR", float(rr))
                    fp.set_param("BB", float(bb))
                    fp.run(self.NTMAX)
                    state = fp.get_state()
                    results.append((rr, bb, state.timefp))

        # All 9 points must have completed.
        self.assertEqual(len(results), 9, f"expected 9 results, got {len(results)}")

        # TIMEFP must be finite and > 0 after at least one step. NaN/Inf
        # would indicate state corruption between cycles or a divergent
        # solver.
        for rr, bb, timefp in results:
            with self.subTest(rr=rr, bb=bb):
                self.assertFalse(
                    math.isnan(timefp),
                    f"NaN TIMEFP at RR={rr} BB={bb}",
                )
                self.assertFalse(
                    math.isinf(timefp),
                    f"Inf TIMEFP at RR={rr} BB={bb}",
                )
                self.assertGreater(
                    timefp, 0.0,
                    f"TIMEFP not advanced at RR={rr} BB={bb}: {timefp!r}",
                )


if __name__ == "__main__":
    unittest.main()
