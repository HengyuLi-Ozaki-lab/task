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

The ITER01 fixture sets ``MODELG=3`` and ``KNAMEQ='eqdata.ITER01'``
(L-6 registry extension). The eqdata file is only present after
Phase-0 has been run; we chdir into ``test_run/test_output/tr_iter01/``
when available and otherwise skip the whole class.

Skipped when ``libtrapi.so`` is not built.
"""
from __future__ import annotations

import math
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
PYTHON_ROOT = REPO / "python"
DEFAULT_SO = REPO / "tr" / "libtrapi.so"
FIXTURES_DIR = HERE.parent / "fixtures"
TEST_OUTPUT_DIR = REPO / "test_run" / "test_output"
KNAMEQ_ITER01 = "eqdata.ITER01"


def _resolve_iter01_cwd() -> Path | None:
    """Resolve cwd for tr_iter01: prefer dev-generated test_output, else committed FIXTURES_DIR."""
    candidate = TEST_OUTPUT_DIR / "tr_iter01"
    if (candidate / KNAMEQ_ITER01).exists():
        return candidate
    if (FIXTURES_DIR / KNAMEQ_ITER01).exists():
        return FIXTURES_DIR
    return None


ITER01_CWD = _resolve_iter01_cwd()

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
@unittest.skipUnless(
    ITER01_CWD is not None,
    f"{KNAMEQ_ITER01} missing under {TEST_OUTPUT_DIR}/tr_iter01 or {FIXTURES_DIR}; "
    f"run `./test_run/run_tests.sh tr_iter01` first (or rely on committed fixture).",
)
# Defensive guard: TR_REGRESS_DUMP=1 and TR_DUMP_STATE write debug artefacts
# to cwd (tr/trregress.f90:30, tr/tr_dump_state.f90:58). If the fallback
# selected FIXTURES_DIR as cwd, those would land inside the committed fixture
# directory — skip the test in that case so the dev's debug session does not
# accidentally pollute the tracked tree.
@unittest.skipIf(
    ITER01_CWD == FIXTURES_DIR and (
        os.environ.get("TR_REGRESS_DUMP") == "1" or os.environ.get("TR_DUMP_STATE")
    ),
    "TR_REGRESS_DUMP/TR_DUMP_STATE would write into committed FIXTURES_DIR; "
    "unset them or generate test_run/test_output/tr_iter01/ first.",
)
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

        # ITER01 sets MODELG=3 + KNAMEQ=eqdata.ITER01; chdir so
        # tr_prep can read the eq data from the Phase-0 output dir.
        prev_cwd = Path.cwd()
        os.chdir(ITER01_CWD)  # resolved at module load (test_output or FIXTURES_DIR)
        try:
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
        finally:
            os.chdir(prev_cwd)

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
