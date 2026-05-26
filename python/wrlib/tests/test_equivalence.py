"""Layer 1: equivalence between the libwrapi.so replay and the Phase 0
Fortran baseline, compared at tolerance 1e-10.

For each case (``wr_iter_lhcd``, ``wr_test001``, ``wr_tst2_ec``):

1. open a :class:`wrlib.Wrlib` handle (loads ``wr/libwrapi.so``),
2. replay the registered subset of the namelist fixture via
   :py:meth:`~wrlib.Wrlib.set_param`,
3. call :py:meth:`~wrlib.Wrlib.run` with the fixture's NRAY_REQUEST,
4. snapshot :class:`~wrlib.state.WrState` via ``get_state``,
5. project that state into the ``extract_wr_metrics.py`` JSON schema
   (so ``test_run/scripts/compare_metrics.py`` can diff it), and
6. compare against ``test_run/baselines/<case>/metrics.json`` using
   the shared comparator with tolerance ``1e-10``.

The Fortran ``wr_get_state`` intentionally does **not** expose the
input-only scalars ``RF, RPI, ZPI, PHII, RNZI, RNPHII, RKR0, UUI``
(they are fed in via ``set_param`` and read by the ray tracer, not
read back out). We strip those from both sides before comparing --
the Phase 0 baseline records them from the namelist dump for human
inspection, but they are not a *computed* output.

If ``libwrapi.so`` has not been built (or ``python/wrlib`` is not
available) the whole class is skipped -- this matches the design
contract that Layer 1 is an *integration* test gated on L-4 + L-5.

See ``docs/superpowers/plans/2026-04-18-wr-library-L6-test-4layers.md``
Task 3 for the iteration protocol when the 1e-10 match is not yet met
(fallback to 1e-8 before treating as a real regression).
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
DEFAULT_SO = REPO / "wr" / "libwrapi.so"

# Make ``import wrlib`` work whether tests are launched from the repo
# root (PYTHONPATH=python) or from inside python/wrlib/tests/.
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))


# Input-only scalars that are written via set_param but not read back
# through wr_get_state. The Phase 0 baseline records them (from the
# namelist dump) but we exclude them from the Layer 1 diff since the
# Python replay has no way to round-trip them without a get_param
# (scheduled for a later phase).
INPUT_ONLY_SCALARS = ("RF", "RPI", "ZPI", "PHII", "RNZI", "RNPHII",
                      "RKR0", "UUI")

# Top-level integer headers the baseline records but which are not
# derivable from WrState alone. We set these on the adapter side from
# the fixture SCALARS so the compare_metrics dim-check passes.
HEADER_INT_KEYS = ("NRAYMAX", "NSTPMAX", "NRSMAX", "NRLMAX",
                   "MODELG", "MDLWRI", "MDLWRQ", "mode_beam")


def _state_to_baseline_shape(state, fixture) -> dict:
    """Project :class:`WrState` into the extract_wr_metrics.py schema.

    Why not use ``WrState.to_dict()`` directly? ``to_dict()`` was
    designed for a Python-facing view (``nstp_end`` lowercase, unified
    ``pos``/``pwr`` profile keys) while the baseline JSON uses the
    Fortran dump's flat column names (``NSTP_END``, ``pos_nrs``,
    ``pwr_nrs``, ...). This adapter re-keys into the baseline shape.
    """
    # Build the top-level int dims. Pull them preferentially from the
    # state (runtime truth) and fall back to fixture SCALARS for the
    # ones wr_get_state doesn't return (NSTPMAX, MDLWRI, MDLWRQ,
    # mode_beam, MODELG).
    scalars_cfg = getattr(fixture, "SCALARS", {})
    headers = {
        "NRAYMAX": state.nraymax,
        "NRSMAX":  state.nrsmax,
        "NRLMAX":  state.nrlmax,
        "NSTPMAX": int(scalars_cfg.get("NSTPMAX", 0)),
        "MODELG":  int(scalars_cfg.get("MODELG", 0)),
        "MDLWRI":  int(scalars_cfg.get("MDLWRI", 0)),
        "MDLWRQ":  int(scalars_cfg.get("MDLWRQ", 0)),
        # mode_beam defaults to 0 unless the fixture set it explicitly.
        "mode_beam": int(scalars_cfg.get("mode_beam", 0)),
    }

    # Output-only scalars visible through wr_get_state.
    out_scalars = {
        "pos_pwrmax_rs": state.scalars["pos_pwrmax_rs"],
        "pwrmax_rs":     state.scalars["pwrmax_rs"],
        "pos_pwrmax_rl": state.scalars["pos_pwrmax_rl"],
        "pwrmax_rl":     state.scalars["pwrmax_rl"],
    }

    # Per-ray rows match the baseline schema: NRAY, NSTP_END,
    # pos_pwrmax_rs_nray, RAYS_END[9]. Per-ray pwrmax_* are NOT emitted
    # by extract_wr_metrics.py (see its module docstring), so we omit
    # them here too.
    rays = []
    for i in range(state.nraymax):
        row = {
            "NRAY": i + 1,
            "NSTP_END": int(state.nstp_end[i]),
            "pos_pwrmax_rs_nray": float(state.pos_pwrmax_rs_nray[i]),
            "RAYS_END": [float(x) for x in state.rays_end[i]],
        }
        rays.append(row)

    profile_rs = [
        {"NRS": i + 1,
         "pos_nrs": float(state.pos_nrs[i]),
         "pwr_nrs": float(state.pwr_nrs[i])}
        for i in range(state.nrsmax)
    ]
    profile_rl = [
        {"NRL": i + 1,
         "pos_nrl": float(state.pos_nrl[i]),
         "pwr_nrl": float(state.pwr_nrl[i])}
        for i in range(state.nrlmax)
    ]

    out = dict(headers)
    out["scalars"] = out_scalars
    out["rays"] = rays
    out["profile_rs"] = profile_rs
    out["profile_rl"] = profile_rl
    return out


def _strip_input_scalars(metrics: dict) -> dict:
    """Return a shallow copy with INPUT_ONLY_SCALARS removed from scalars."""
    scalars = {k: v for k, v in metrics.get("scalars", {}).items()
               if k not in INPUT_ONLY_SCALARS}
    out = dict(metrics)
    out["scalars"] = scalars
    return out


def _strip_ray_field(metrics: dict, field: str) -> dict:
    """Return a shallow copy with a named field removed from every ray."""
    rays = []
    for row in metrics.get("rays", []):
        rays.append({k: v for k, v in row.items() if k != field})
    out = dict(metrics)
    out["rays"] = rays
    return out


def _run_case(fixture) -> dict:
    """Drive a single libwrapi.so cycle and return the metrics dict.

    Keeping this outside ``TestEquivalence`` lets Layer 4 reuse the
    same replay helper without importing a TestCase class.
    """
    from wrlib import Wrlib  # noqa: WPS433 (intentional local import)
    with Wrlib() as wr:
        fixture.apply(wr)
        wr.run(int(getattr(fixture, "NRAY_REQUEST", 0)))
        state = wr.get_state()
    return _state_to_baseline_shape(state, fixture)


def _compare_with_baseline(actual: dict, case_name: str,
                           tol: str = "1e-10") -> None:
    """Write ``actual`` to a temp JSON and diff it vs the baseline.

    Raises :class:`AssertionError` on any drift so the unittest
    framework reports it as a FAIL rather than an ERROR.
    """
    baseline_json = BASELINES_DIR / case_name / "metrics.json"
    if not baseline_json.exists():
        raise unittest.SkipTest(f"baseline missing: {baseline_json}")
    baseline = json.loads(baseline_json.read_text())

    # Strip the input-only scalars symmetrically on both sides. Keeping
    # the stripping here (rather than in _state_to_baseline_shape) makes
    # it explicit in the test -- any future get_param wiring can drop
    # this line without touching the adapter.
    b_strip = _strip_input_scalars(baseline)
    a_strip = _strip_input_scalars(actual)

    with tempfile.NamedTemporaryFile(
        "w", suffix=f"_{case_name}_baseline.json", delete=False,
    ) as fh:
        json.dump(b_strip, fh)
        baseline_path = Path(fh.name)
    with tempfile.NamedTemporaryFile(
        "w", suffix=f"_{case_name}_actual.json", delete=False,
    ) as fh:
        json.dump(a_strip, fh)
        actual_path = Path(fh.name)
    try:
        res = subprocess.run(
            [
                sys.executable,
                str(COMPARE_SCRIPT),
                "--baseline", str(baseline_path),
                "--actual",   str(actual_path),
                "--tolerance", str(tol),
            ],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            raise AssertionError(
                f"compare_metrics FAIL for {case_name}:\n"
                f"--- stdout ---\n{res.stdout}\n"
                f"--- stderr ---\n{res.stderr}"
            )
    finally:
        for p in (baseline_path, actual_path):
            try:
                p.unlink()
            except OSError:
                pass


def _wrlib_importable() -> bool:
    """Importable check for wrlib -- libwrapi.so is loaded lazily so we
    only verify the Python package."""
    try:
        import wrlib  # noqa: F401
    except Exception:
        return False
    return True


IS_LINUX = sys.platform.startswith("linux")


@unittest.skipUnless(
    IS_LINUX,
    "Equivalence tests are Linux-canonical. The 1e-10 baselines "
    "live in test_run/baselines/<case>/metrics.json and were "
    "generated on Linux gfortran 13.x (Ubuntu CI runner). macOS / "
    "non-Linux dev runs the libwrapi.so via the Python wrapper; "
    "correctness is verified by Linux CI on every push. See "
    "docs/baseline-policy.md.",
)
@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libwrapi.so not built at {DEFAULT_SO}; run `make -C wr libwrapi.so`",
)
@unittest.skipUnless(_wrlib_importable(), "python/wrlib not importable")
@unittest.skipUnless(COMPARE_SCRIPT.exists(), f"{COMPARE_SCRIPT} missing")
class TestEquivalence(unittest.TestCase):
    """Layer 1: match Phase 0 Fortran baseline at 1e-10."""

    # The tolerance is deliberately exposed as a class attribute so a
    # derived test (e.g. a softer-tol CI job) can override it without
    # re-implementing the body.
    TOLERANCE = "1e-10"

    def _check_case(self, fixture) -> None:
        """Run one fixture and diff vs its baseline."""
        actual = _run_case(fixture)
        _compare_with_baseline(actual, fixture.BASELINE_NAME, self.TOLERANCE)

    def test_iter_lhcd(self):
        from wrlib.tests.fixtures import wr_iter_lhcd_params as f
        self._check_case(f)

    def test_test001(self):
        from wrlib.tests.fixtures import wr_test001_params as f
        self._check_case(f)

    def test_tst2_ec(self):
        from wrlib.tests.fixtures import wr_tst2_ec_params as f
        self._check_case(f)


if __name__ == "__main__":
    unittest.main()
