"""Layer 4: 3x3 parameter sweep smoke test for tilib.

The goal is *not* numerical validation -- it is to prove that the
``init -> set_param x N -> run -> get_state -> finalize`` cycle can be
driven in a loop without crashing the library (regression guard against
leaked state or dangling SAVE variables inside TICOMM).

For each ``(DT, NRMAX)`` pair on a 3x3 grid we:

* open a fresh :class:`tilib.TiLib` handle,
* apply the ``ti_min`` fixture as a realistic baseline parameter set,
* override ``DT`` and ``NRMAX`` for this grid point,
* run a short integration (``NTMAX=2``),
* record the post-run ``T`` scalar and check it is finite.

A NaN/Inf on any point signals that TICOMM state leaked across
cycles, so we fail loudly. Nine successful cycles -> PASS.

Skipped when ``libtiapi.so`` is not built.
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
PYTHON_ROOT = REPO / "python"
DEFAULT_SO = REPO / "ti" / "libtiapi.so"

if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from tilib.tests._data_cwd import TiDataCwdMixin  # noqa: E402


def _tilib_importable() -> bool:
    try:
        import tilib  # noqa: F401
    except Exception:
        return False
    return True


@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libtiapi.so not built at {DEFAULT_SO}; run `make -C ti libtiapi.so`",
)
@unittest.skipUnless(_tilib_importable(), "python/tilib not importable")
class TestSweep(TiDataCwdMixin, unittest.TestCase):
    """3x3 DT x NRMAX grid; smoke-only (no numerical regression)."""

    #: Keep NTMAX tiny so the whole sweep completes well under the
    #: test_definitions.conf timeout (120 s).
    NTMAX = 2

    #: Grid centres sit near the ti_min baseline so every point is a
    #: physically plausible perturbation rather than a pathological
    #: extreme that could crash for non-regression reasons.
    DT_VALUES = (0.005, 0.01, 0.02)
    NRMAX_VALUES = (10, 15, 20)

    def test_3x3_grid_completes(self):
        from tilib import TiLib
        from tilib.tests.fixtures import ti_min_params

        results = []
        for dt in self.DT_VALUES:
            for nrmax in self.NRMAX_VALUES:
                with TiLib() as ti:
                    # Realistic base parameters from the ti_min fixture.
                    ti_min_params.apply(ti)
                    # Override the swept axes.
                    ti.set_param("DT", float(dt))
                    ti.set_param("NRMAX", float(nrmax))
                    # Short run -- smoke only.
                    ti.run(self.NTMAX)
                    state = ti.get_state()
                    results.append((dt, nrmax, state.T))

        # All 9 points must have completed.
        self.assertEqual(len(results), 9, f"expected 9 results, got {len(results)}")

        # All T values must be finite. NaN/Inf would indicate state
        # corruption between cycles or a divergent solver.
        for dt, nrmax, T in results:
            with self.subTest(dt=dt, nrmax=nrmax):
                self.assertFalse(
                    math.isnan(T),
                    f"NaN T at DT={dt} NRMAX={nrmax}",
                )
                self.assertFalse(
                    math.isinf(T),
                    f"Inf T at DT={dt} NRMAX={nrmax}",
                )


if __name__ == "__main__":
    unittest.main()
