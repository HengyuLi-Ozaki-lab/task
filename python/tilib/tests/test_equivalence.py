"""Layer 1: equivalence between the libtiapi.so replay and the Phase 0
Fortran baseline, compared at tolerance 1e-10.

For each registered case (``ti_min``, ``ti_ar``):

1. open a :class:`tilib.TiLib` handle (loads ``ti/libtiapi.so``),
2. replay the registered subset of the namelist fixture via
   :py:meth:`~tilib.TiLib.set_param`,
3. advance the simulation for the fixture's ``NTMAX``,
4. serialise the resulting :class:`~tilib.state.TiState` via
   :py:meth:`~tilib.state.TiState.to_dict`,
5. compare against ``test_run/baselines/<case>/metrics.json`` using
   ``test_run/scripts/compare_metrics.py`` with tolerance ``1e-10``.

If ``libtiapi.so`` has not been built (or ``python/tilib`` is not
available) the whole class is skipped -- this matches the design
contract that Layer 1 is an *integration* test gated on L-4 + L-5.

Missing baseline JSON files are skipped individually (rather than
failed) so the suite does not go red when a new case is being brought
online.

See ``docs/superpowers/plans/2026-04-18-ti-library-L6-test-4layers.md``
for the iteration protocol when the 1e-10 match is not yet met.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
PYTHON_ROOT = REPO / "python"
BASELINES_DIR = REPO / "test_run" / "baselines"
COMPARE_SCRIPT = REPO / "test_run" / "scripts" / "compare_metrics.py"
DEFAULT_SO = REPO / "ti" / "libtiapi.so"

# Make ``import tilib`` work whether tests are launched from the repo
# root (PYTHONPATH=python) or from inside python/tilib/tests/.
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from tilib.tests._data_cwd import TiDataCwdMixin  # noqa: E402


def _run_case(apply_fn, ntmax: int) -> dict:
    """Drive a single libtiapi.so cycle and return the metrics dict.

    Keeping this outside :class:`TestEquivalence` lets Layer 4 reuse
    the same replay helper without importing a TestCase class.
    """
    from tilib import TiLib  # noqa: WPS433 (intentional local import)
    with TiLib() as ti:
        apply_fn(ti)
        ti.run(int(ntmax))
        state = ti.get_state()
    return state.to_dict()


def _compare_with_baseline(actual: dict, case_name: str, tol: str = "1e-10") -> None:
    """Write ``actual`` to a temp JSON and diff it vs the baseline.

    Raises :class:`AssertionError` on any drift so the unittest
    framework reports it as a FAIL rather than an ERROR. If the
    baseline JSON does not exist we raise :class:`SkipTest` so the
    suite is green on a fresh checkout without L-0 baselines.
    """
    baseline_json = BASELINES_DIR / case_name / "metrics.json"
    if not baseline_json.exists():
        raise unittest.SkipTest(f"baseline missing: {baseline_json}")
    with tempfile.NamedTemporaryFile(
        "w", suffix=f"_{case_name}_actual.json", delete=False
    ) as fh:
        json.dump(actual, fh)
        actual_path = Path(fh.name)
    try:
        res = subprocess.run(
            [
                sys.executable,
                str(COMPARE_SCRIPT),
                "--baseline", str(baseline_json),
                "--actual",   str(actual_path),
                "--tolerance", str(tol),
            ],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            # Echo full stdout so test output shows *which* fields drifted.
            raise AssertionError(
                f"compare_metrics FAIL for {case_name}:\n"
                f"--- stdout ---\n{res.stdout}\n"
                f"--- stderr ---\n{res.stderr}"
            )
    finally:
        try:
            actual_path.unlink()
        except OSError:
            pass


def _tilib_importable() -> bool:
    """Importable check for tilib -- libtiapi.so is loaded lazily so
    we only verify the Python package."""
    try:
        import tilib  # noqa: F401
    except Exception:
        return False
    return True


IS_LINUX = sys.platform.startswith("linux")


@unittest.skipUnless(
    IS_LINUX,
    "Equivalence tests are Linux-canonical. The 1e-10 baselines "
    "live in test_run/baselines/<case>/metrics.json and were "
    "generated on Linux gfortran 13.x (Ubuntu CI runner). macOS / "
    "non-Linux dev runs the libtiapi.so via the Python wrapper; "
    "correctness is verified by Linux CI on every push. See "
    "docs/baseline-policy.md.",
)
@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libtiapi.so not built at {DEFAULT_SO}; run `make -C ti libtiapi.so`",
)
@unittest.skipUnless(_tilib_importable(), "python/tilib not importable")
@unittest.skipUnless(COMPARE_SCRIPT.exists(), f"{COMPARE_SCRIPT} missing")
class TestEquivalence(TiDataCwdMixin, unittest.TestCase):
    """Layer 1: match Phase 0 Fortran baseline at 1e-10."""

    # The tolerance is deliberately exposed as a class attribute so a
    # derived test (e.g. a softer-tol CI job) can override it without
    # re-implementing the body.
    TOLERANCE = "1e-10"

    def _check_case(self, fixture_module) -> None:
        """Run one fixture and diff vs its baseline.

        The fixture module must expose ``apply`` / ``NTMAX`` /
        ``BASELINE_NAME`` (see :mod:`fixtures.ti_iter01_params`).
        """
        actual = _run_case(fixture_module.apply, ntmax=fixture_module.NTMAX)
        _compare_with_baseline(actual, fixture_module.BASELINE_NAME, self.TOLERANCE)

    def test_ti_min(self):
        # Local import so collection works even if the fixture is
        # syntactically invalid (failure reported per-test, not globally).
        from tilib.tests.fixtures import ti_iter01_params as f
        self._check_case(f)

    def test_ti_ar(self):
        from tilib.tests.fixtures import ti_ar_params as f
        self._check_case(f)


if __name__ == "__main__":
    unittest.main()
