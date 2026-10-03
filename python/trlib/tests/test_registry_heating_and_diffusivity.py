"""PECTOT, PICTOT, CDH and CNH reach the Fortran registry and change a run.

``tr/tr_param_registry.f90`` has a ``CASE`` entry for each of

* ``PECTOT`` / ``PICTOT``: total EC / IC input power [MW] (default 0);
* ``CDH`` / ``CNH``: the weights of ``chi_s = CDH*chi_turb +
  CNH*chi_NCLASS`` (default 1, the neutral value).

Without its ``CASE`` entry a name is refused (``TrlibParamError``, ierr=1),
so the first test catches a missing entry directly; the others read the
parameters back through the run: the neutral values reproduce the default
run, and RF power or a changed weight moves the stored energy ``WPT``.
No ``subTest``: pytest's ``--forked`` mode reports a failing ``subTest`` as
passed.

Skipped automatically when ``libtrapi.so`` has not been built.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from trlib import Trlib, TrlibParamError  # noqa: E402

REPO = HERE.parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"

# ITER-like fixture (python/trlib/examples/quickstart.py), ten steps.
SCALAR_PARAMS = {"RR": 8.5, "RA": 2.0, "RKAP": 1.7, "BB": 5.3,
                 "NSMAX": 2, "DT": 0.1, "NTSTEP": 10}
ARRAY_PARAMS = (("PN[1]", 1.0), ("PN[2]", 1.0), ("PT[1]", 1.5), ("PT[2]", 1.5))
NAMES_AND_VALUES = (("PECTOT", 10.0), ("PICTOT", 10.0), ("CDH", 3.0), ("CNH", 0.5))


def _wpt(extras: dict) -> float:
    """Stored energy WPT after ten steps with ``extras`` set on the fixture."""
    with Trlib() as tr:
        tr.set_params(**SCALAR_PARAMS)
        for name, value in ARRAY_PARAMS:
            tr.set_param(name, value)
        for name, value in extras.items():
            tr.set_param(name, value)   # TrlibParamError without a CASE entry
        tr.run(ntmax=10)
        return tr.get_state().scalars["WPT"]


@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libtrapi.so not built at {DEFAULT_SO}; run `make -C tr libtrapi.so`",
)
class TestFortranRegistryHeatingAndDiffusivity(unittest.TestCase):
    def test_fortran_registry_accepts_all_four_names(self) -> None:
        refused = {}
        with Trlib() as tr:
            for name, value in NAMES_AND_VALUES:
                try:
                    tr.set_param(name, value)
                except TrlibParamError as exc:
                    refused[name] = str(exc)
        self.assertEqual(refused, {}, f"refused by the Fortran registry: {refused}")

    def test_neutral_values_reproduce_the_default_run(self) -> None:
        neutral = {"PECTOT": 0.0, "PICTOT": 0.0, "CDH": 1.0, "CNH": 1.0}
        self.assertEqual(_wpt({}), _wpt(neutral))

    def test_rf_power_raises_the_stored_energy(self) -> None:
        base = _wpt({})
        ec = _wpt({"PECTOT": 10.0})
        ic = _wpt({"PICTOT": 10.0})
        self.assertGreater(ec, base * 1.1)
        self.assertGreater(ic, base * 1.1)
        # The same power gives a different WPT for EC and IC (measured on
        # this case: EC 1.9 % above IC), which pins each name to its own
        # variable: a registry that swapped the two would reverse this.
        self.assertGreater(ec, ic * 1.005)

    def test_diffusivity_weights_move_the_stored_energy(self) -> None:
        base = _wpt({})
        cdh = _wpt({"CDH": 3.0})
        cnh = _wpt({"CNH": 3.0})
        self.assertLess(cdh, base * 0.9)
        self.assertLess(cnh, base * 0.999)
        # The turbulent weight acts far more strongly than the neoclassical
        # one (measured: 15.3 against 20.8 MJ for 3 each, base 21.2): a
        # registry that wrote one name's value into the other's variable
        # would close the gap.
        self.assertGreater(cnh, cdh * 1.1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
