"""TOT hands a name to the EQ, TR and FP registries, so it gets their checks.

``tot_set_param`` and ``tot_set_param_str`` strip the ``eq:`` / ``tr:`` /
``fp:`` prefix and call the module's registry (``tot/tot_param_registry.f90``),
not its C entry point. What the registries refuse is therefore refused through
TOT as well: a malformed subscript, a value that is not finite, an integer
beyond the default integer, and a string value longer than its parameter
(TOT's own value buffer holds 256 characters, ``KNAMEQ`` 80: a path of 100
characters was cut to its first 80).

``ti:``, ``wr:`` and ``wrx:`` names go to registries that this does not cover.

One test per case (``parametrize``, never ``subTest``).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
PYTHON_ROOT = REPO / "python"
DEFAULT_SO = REPO / "tot" / "libtotapi.so"

if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from totlib import Tot, TotlibInvalidParamError  # noqa: E402

pytestmark = pytest.mark.skipif(
    not DEFAULT_SO.exists(),
    reason=f"libtotapi.so not built at {DEFAULT_SO}; run `make -C tot libtotapi.so`",
)

PARAMETER = 80          # KNAMEQ, CHARACTER(LEN=80)


@pytest.mark.parametrize("name", ["eq:KNAMEQ", "tr:KNAMEQ"])
@pytest.mark.parametrize("length", [PARAMETER + 1, 100, 255])
def test_a_string_value_longer_than_the_parameter_is_refused(name, length):
    with Tot() as tot:
        with pytest.raises(TotlibInvalidParamError):
            tot.set_param_str(name, "a" * length)


@pytest.mark.parametrize("name", ["eq:KNAMEQ", "tr:KNAMEQ"])
def test_a_string_value_that_fills_the_parameter_is_taken(name):
    with Tot() as tot:
        tot.set_param_str(name, "a" * PARAMETER)


@pytest.mark.parametrize("name, value", [
    ("eq:RR[zz]", 3.0), ("tr:RR[1]x", 3.0), ("fp:NTHMAX[1,2]", 20.0),
    ("eq:RR", float("nan")), ("tr:RR", float("inf")), ("fp:RR", float("-inf")),
    ("eq:NRMAX", 1.0e10), ("tr:NTMAX", 2.0**31), ("fp:NTHMAX", -1.0e10),
], ids=["eq:RR[zz]", "tr:RR[1]x", "fp:NTHMAX[1,2]", "eq:RR=nan", "tr:RR=inf", "fp:RR=-inf",
        "eq:NRMAX=1e10", "tr:NTMAX=2**31", "fp:NTHMAX=-1e10"])
def test_what_a_module_registry_refuses_is_refused_through_tot(name, value):
    with Tot() as tot:
        with pytest.raises(TotlibInvalidParamError):
            tot.set_param(name, value)


@pytest.mark.parametrize("name, value", [("eq:RR", 3.0), ("tr:PN[1]", 0.5), ("fp:NTHMAX", 20.0), ("eq:PSIB[0]", 0.0)])
def test_what_a_module_registry_takes_is_taken_through_tot(name, value):
    with Tot() as tot:
        tot.set_param(name, value)
