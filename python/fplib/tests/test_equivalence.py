"""Layer 1: equivalence between the libfpapi.so replay and the Phase 0
Fortran baseline, compared at tolerance 1e-10.

For each case (``fp_iter01``, ``fp_dt1``):

1. open a :class:`fplib.Fplib` handle (loads ``fp/libfpapi.so``),
2. replay the registered subset of the namelist fixture via
   :py:meth:`~fplib.Fplib.set_param`,
3. advance the simulation for the fixture's ``NTMAX``,
4. serialise the resulting :class:`~fplib.state.FpState`,
5. reshape the profile into the Phase 0 flat ``(NR, NSA)`` row format
   emitted by ``test_run/scripts/extract_fp_metrics.py``,
6. compare against ``test_run/baselines/<case>/metrics.json`` using
   ``test_run/scripts/compare_metrics.py`` with tolerance ``1e-10``.

Profile-shape conversion note
-----------------------------
``FpState.to_dict()`` yields ``profile: [{NSA, RNT: [list of length NR],
RWT: [...], ...}]`` (per-species rows), while the Phase 0 baseline uses
``profile: [{NR, NSA, RNT: float, RWT: float, ...}]`` (one row per
``(NR, NSA)`` pair, scalar values). The :func:`_to_baseline_shape`
helper flattens the former to match the latter so ``compare_metrics.py``
can diff them with no schema-awareness changes.

If ``libfpapi.so`` has not been built (or ``python/fplib`` is not
available) the whole class is skipped -- this matches the design
contract that Layer 1 is an *integration* test gated on L-4 + L-5.

See ``docs/superpowers/plans/2026-04-18-fp-library-L6-test-4layers.md``
Task 3 for the iteration protocol when the 1e-10 match is not yet met.
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
DEFAULT_SO = REPO / "fp" / "libfpapi.so"

# Make ``import fplib`` work whether tests are launched from the repo
# root (PYTHONPATH=python) or from inside python/fplib/tests/.
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))


# Profile fields the FP baseline schema enumerates per (NR, NSA) row.
_FP_PROFILE_FIELDS = ("RNT", "RWT", "RTT", "RJT", "RPCT", "RPWT")


def _to_baseline_shape(state_dict: dict) -> dict:
    """Convert FpState.to_dict() output into the Phase-0 baseline shape.

    Input  (from :py:meth:`fplib.state.FpState.to_dict`)::

        {
          "NRMAX": int, "NSAMAX": int, "NPMAX": int, "NTHMAX": int,
          "NTG2": int, "TIMEFP": float,
          "profile": [
             {"NSA": 1, "RNT": [..NR..], "RWT": [..], ...},
             ...  # len = NSAMAX
          ],
        }

    Output (matches ``test_run/scripts/extract_fp_metrics.py``)::

        {
          "NRMAX": int, "NSAMAX": int, "NPMAX": int, "NTHMAX": int,
          "NTG2": int,
          "scalars": {"TIMEFP": float},
          "profile": [
             {"NR": 1, "NSA": 1, "RNT": float, "RWT": float, ...},
             ...  # len = NRMAX * NSAMAX
          ],
        }
    """
    out = {
        "NRMAX":  int(state_dict["NRMAX"]),
        "NSAMAX": int(state_dict["NSAMAX"]),
        "NPMAX":  int(state_dict["NPMAX"]),
        "NTHMAX": int(state_dict["NTHMAX"]),
        "NTG2":   int(state_dict["NTG2"]),
        "scalars": {"TIMEFP": float(state_dict["TIMEFP"])},
        "profile": [],
    }
    for row in state_dict.get("profile", []):
        nsa = int(row["NSA"])
        # Each field should be a list of length NRMAX.
        for nr_idx in range(out["NRMAX"]):
            flat = {"NR": nr_idx + 1, "NSA": nsa}
            for f in _FP_PROFILE_FIELDS:
                flat[f] = float(row[f][nr_idx])
            out["profile"].append(flat)
    return out


def _run_case(apply_fn, ntmax: int) -> dict:
    """Drive a single libfpapi.so cycle and return the *baseline-shaped* dict.

    Keeping this outside ``TestEquivalence`` lets Layer 4 reuse the
    same replay helper without importing a TestCase class.
    """
    from fplib import Fplib  # noqa: WPS433 (intentional local import)
    with Fplib() as fp:
        apply_fn(fp)
        fp.run(int(ntmax))
        state = fp.get_state()
    return _to_baseline_shape(state.to_dict())


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


def _fplib_importable() -> bool:
    """Importable check for fplib -- libfpapi.so is loaded lazily so we
    only verify the Python package."""
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
@unittest.skipUnless(COMPARE_SCRIPT.exists(), f"{COMPARE_SCRIPT} missing")
class TestEquivalence(unittest.TestCase):
    """Layer 1: match Phase 0 Fortran baseline at 1e-10."""

    # The tolerance is deliberately exposed as a class attribute so a
    # derived test (e.g. a softer-tol CI job) can override it without
    # re-implementing the body.
    TOLERANCE = "1e-10"

    def _check_case(self, fixture_module) -> None:
        """Run one fixture and diff vs its baseline.

        The fixture module must expose ``apply`` / ``NTMAX`` /
        ``BASELINE_NAME`` (see :mod:`fixtures.fp_iter01_params`).
        """
        actual = _run_case(fixture_module.apply, ntmax=fixture_module.NTMAX)
        _compare_with_baseline(actual, fixture_module.BASELINE_NAME, self.TOLERANCE)

    def test_iter01(self):
        # Local import so collection works even if the fixture is
        # syntactically invalid (failure reported per-test, not globally).
        from fplib.tests.fixtures import fp_iter01_params as f
        self._check_case(f)

    def test_dt1(self):
        from fplib.tests.fixtures import fp_dt1_params as f
        self._check_case(f)


if __name__ == "__main__":
    unittest.main()
