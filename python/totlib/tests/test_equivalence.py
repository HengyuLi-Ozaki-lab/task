"""Layer 1: equivalence between the libtotapi.so replay and the Phase 0
Fortran baseline, compared at tolerance 1e-10.

For each case (``tot_demo2014_short``, ``tot_ht6m_short``):

1. open a :class:`totlib.Tot` handle (loads ``tot/libtotapi.so``),
2. replay the registered subset of the namelist fixture via
   :py:meth:`~totlib.Tot.set_param` /
   :py:meth:`~totlib.Tot.set_param_str`,
3. advance the integrated simulation for the fixture's ``NTMAX``,
4. serialise the resulting :class:`~totlib.state.TotState` via
   :py:meth:`~totlib.state.TotState.to_dict`,
5. compare against ``test_run/baselines/<case>/metrics.json`` using
   ``test_run/scripts/compare_metrics.py`` with tolerance ``1e-10``.

Triple-skip gates (all must pass for the class to run):

* ``libtotapi.so`` is importable via :func:`totlib._ffi._candidate_paths`
  (covers both ``tot/libtotapi.so`` and ``lib/libtotapi.so`` and an
  explicit ``TOTLIB_PATH`` override),
* the baseline JSON exists under ``test_run/baselines/``,
* ``TOT_RUN_OK=1`` is set in the environment.

The ``TOT_RUN_OK`` gate is required because L-3 / L-4 / L-5 leave
``tot_init`` / ``tot_run`` / ``tot_get_state`` / ``tot_finalize`` as
stubs that all return ``TOT_ERR_NOT_IMPL`` (rc=4). Until L-6 fan-out
lands inside ``libtotapi.so`` itself, the equivalence test cannot run
end-to-end. We keep the test fully wired so the moment the .so starts
returning real data, simply setting ``TOT_RUN_OK=1`` enables the diff
without any further code change. This mirrors the ``EQ_RUN_OK`` gate
used by ``python/eqlib/tests/test_equivalence.py``.

See ``docs/superpowers/plans/2026-04-18-tot-library-L6-test-4layers.md``
Task 4 for the iteration protocol when the 1e-10 match is not yet met.
"""
from __future__ import annotations

import json
import os
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

# Make ``import totlib`` work whether tests are launched from the repo
# root (PYTHONPATH=python) or from inside python/totlib/tests/.
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from totlib import _ffi  # noqa: E402


# Opt-in gate: tot_init / tot_run / tot_get_state / tot_finalize are
# L-3/L-4/L-5 stubs returning TOT_ERR_NOT_IMPL. CI runs the diff only
# when the orchestrator fan-out is actually wired (TOT_RUN_OK=1).
RUN_OK = os.environ.get("TOT_RUN_OK") == "1"


def _any_so_exists() -> bool:
    """True if libtotapi.so is present at any known candidate path.

    Honours ``TOTLIB_PATH`` so a user-built .so outside the repo is
    picked up without changing the test.
    """
    env = os.environ.get("TOTLIB_PATH")
    if env and Path(env).exists():
        return True
    return any(p.exists() for p in _ffi._candidate_paths())


def _totlib_importable() -> bool:
    """Importable check for totlib -- libtotapi.so is loaded lazily so
    we only verify the Python package."""
    try:
        import totlib  # noqa: F401
    except Exception:
        return False
    return True


def _run_case(apply_fn, ntmax: int) -> dict:
    """Drive a single libtotapi.so cycle and return the to_dict payload.

    Keeping this outside ``TestEquivalence`` lets Layer 4 reuse the
    same replay helper without importing a TestCase class.
    """
    from totlib import Tot  # noqa: WPS433 (intentional local import)

    with Tot() as tot:
        apply_fn(tot)
        tot.run(int(ntmax))
        state = tot.get_state()
    return state.to_dict()


def _compare_with_baseline(actual: dict, case_name: str, tol: str = "1e-10") -> None:
    """Write ``actual`` to a temp JSON and diff it vs the baseline.

    Raises :class:`AssertionError` on any drift so the unittest framework
    reports it as a FAIL rather than an ERROR.
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


@unittest.skipUnless(
    _any_so_exists(),
    "libtotapi.so not built at any candidate path "
    "(tot/libtotapi.so or lib/libtotapi.so); "
    "run `make -C tot libtotapi.so`",
)
@unittest.skipUnless(_totlib_importable(), "python/totlib not importable")
@unittest.skipUnless(COMPARE_SCRIPT.exists(), f"{COMPARE_SCRIPT} missing")
@unittest.skipUnless(
    RUN_OK,
    "TOT_RUN_OK=1 required: tot_init / tot_run / tot_get_state / "
    "tot_finalize are L-3/L-4/L-5 stubs returning TOT_ERR_NOT_IMPL. "
    "Set TOT_RUN_OK=1 once L-6 fan-out lands inside libtotapi.so.",
)
class TestEquivalence(unittest.TestCase):
    """Layer 1: match Phase 0 Fortran baseline at 1e-10."""

    # Tolerance is exposed as a class attribute so a derived test
    # (e.g. a softer-tol CI job) can override it without re-implementing
    # the body.
    TOLERANCE = "1e-10"

    def _check_case(self, fixture_module) -> None:
        """Run one fixture and diff vs its baseline.

        The fixture module must expose ``apply`` / ``NTMAX`` /
        ``BASELINE_NAME`` (see :mod:`fixtures.tot_demo2014_params`).
        """
        actual = _run_case(
            fixture_module.apply,
            ntmax=fixture_module.NTMAX,
        )
        _compare_with_baseline(
            actual, fixture_module.BASELINE_NAME, self.TOLERANCE,
        )

    def test_tot_demo2014_short(self):
        # Local import so collection works even if the fixture is
        # syntactically invalid (failure reported per-test, not globally).
        from totlib.tests.fixtures import tot_demo2014_params as f
        self._check_case(f)

    def test_tot_ht6m_short(self):
        from totlib.tests.fixtures import tot_ht6m_params as f
        self._check_case(f)


if __name__ == "__main__":
    unittest.main()
