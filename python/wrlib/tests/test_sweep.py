"""Layer 4: small parameter-sweep smoke test.

The goal is *not* numerical validation -- it is to prove that the
``init -> set_param x N -> run -> get_state -> finalize`` cycle can be
driven in a loop without crashing the library. This is a regression
guard against leaked state or dangling SAVE variables inside WRCOMM /
wr_allocate (the Bugbot HIGH on PR #36 found exactly this class of
bug; test_reinit.c exercises the same invariant at the C layer).

For each ``(RFIN[1], ANGPHIN[1])`` pair on a 3x3 grid we:

* open a fresh :class:`wrlib.Wrlib` handle,
* apply the ``wr_iter_lhcd`` fixture as a realistic baseline,
* reduce NRAYMAX to 1 so each sweep point completes in a few seconds,
* override ``RFIN[1]`` (LH frequency) and ``ANGPHIN[1]`` (toroidal
  injection angle) for this grid point,
* run the ray-tracing with the namelist NSTPMAX,
* record the post-run ``pwrmax_rs`` scalar and check it is finite and
  non-negative.

A NaN / negative peak on any point signals that WRCOMM state leaked
across cycles or the ray diverged, so we fail loudly. Nine successful
cycles -> PASS.

Skipped when ``libwrapi.so`` is not built.
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
PYTHON_ROOT = REPO / "python"
DEFAULT_SO = REPO / "wr" / "libwrapi.so"

if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))


def _wrlib_importable() -> bool:
    try:
        import wrlib  # noqa: F401
    except Exception:
        return False
    return True


@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libwrapi.so not built at {DEFAULT_SO}; run `make -C wr libwrapi.so`",
)
@unittest.skipUnless(_wrlib_importable(), "python/wrlib not importable")
class TestSweep(unittest.TestCase):
    """3x3 RFIN x ANGPHIN grid; smoke-only (no numerical regression)."""

    #: LH frequency sweep around the ITER baseline (5 GHz). Values are
    #: in MHz per wr namelist convention.
    RFIN_VALUES = (4.0e3, 5.0e3, 6.0e3)

    #: Toroidal injection angle in degrees.
    ANGPHIN_VALUES = (25.0, 30.0, 35.0)

    def test_3x3_grid_completes(self):
        from wrlib import Wrlib
        from wrlib.tests.fixtures import wr_iter_lhcd_params as base

        results = []
        for rf in self.RFIN_VALUES:
            for ang in self.ANGPHIN_VALUES:
                with Wrlib() as wr:
                    # Realistic base parameters from the ITER-LHCD fixture.
                    base.apply(wr)
                    # Reduce to 1 ray so each sweep point finishes in a
                    # few seconds even with NSTPMAX=2000.
                    wr.set_param("NRAYMAX", 1)
                    # Override the swept axes (1-origin subscript).
                    wr.set_param("RFIN[1]", float(rf))
                    wr.set_param("ANGPHIN[1]", float(ang))
                    wr.run(0)
                    state = wr.get_state()
                    peak = state.scalars.get("pwrmax_rs", float("nan"))
                    results.append((rf, ang, peak))

        # All 9 points must have completed.
        self.assertEqual(
            len(results), 9, f"expected 9 results, got {len(results)}",
        )

        # Peak power must be finite and physically non-negative at
        # every sweep point. NaN/Inf or a negative value indicates
        # state corruption between cycles or a divergent integrator.
        for rf, ang, peak in results:
            with self.subTest(rf=rf, ang=ang):
                self.assertFalse(
                    math.isnan(peak),
                    f"NaN pwrmax_rs at RFIN={rf} ANGPHIN={ang}",
                )
                self.assertFalse(
                    math.isinf(peak),
                    f"Inf pwrmax_rs at RFIN={rf} ANGPHIN={ang}",
                )
                self.assertGreaterEqual(
                    peak, 0.0,
                    f"negative pwrmax_rs at RFIN={rf} ANGPHIN={ang}",
                )


if __name__ == "__main__":
    unittest.main()
