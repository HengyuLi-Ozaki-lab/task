"""The registry (equ/equ_param_registry.f90) against itself and the namelist.

Read from the Fortran sources: the CASE names and array bounds of
equ_param_set, the integer list of value_refused, the unused names, and the
variable list of the &EQU namelist in eqnlin (equ/equinit.f90). Every
namelist variable is either registered or unused; every registered name
takes a valid value and refuses what the registry refuses.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from equlib import Equ, EqulibInvalidParamError
from equlib.tests.conftest import requires_lib

pytestmark = requires_lib

EQU = Path(__file__).resolve().parents[3] / "equ"
REG = (EQU / "equ_param_registry.f90").read_text()


def _section(start, end):
    return REG[REG.index(start): REG.index(end, REG.index(start))]


NUMERIC = re.findall(r'CASE \("([A-Z0-9_]+)"\)(?:\s+! \((\d+):(\d+)\))?\s*\n(.*?)(?=\n    CASE|\n    END SELECT)',
                     _section("SUBROUTINE equ_param_set(", "END SUBROUTINE equ_param_set\n"), re.S)
STRINGS = re.findall(r'CASE \("([A-Z0-9_]+)"\)\s+! CHARACTER\(LEN=(\d+)\)',
                     _section("SUBROUTINE equ_param_set_str", "END SUBROUTINE equ_param_set_str"))
INTEGERS = set(re.findall(r'"([A-Z0-9_]+)"', _section("LOGICAL FUNCTION value_refused",
                                                        "END FUNCTION value_refused")))
UNUSED = set(re.findall(r'"([A-Z0-9_]+)"', _section("LOGICAL FUNCTION equ_param_is_unused",
                                                      "END FUNCTION equ_param_is_unused")))


def _namelist_names():
    src = (EQU / "equinit.f90").read_text()
    body = re.search(r"namelist /equ/(.*?)\n!=", src, re.S).group(1)
    return {n.upper() for n in re.findall(r"[A-Za-z][A-Za-z0-9_]*", body)}


def test_registry_covers_the_namelist():
    registered = {n for n, *_ in NUMERIC} | {n for n, _ in STRINGS}
    assert registered | UNUSED == _namelist_names()
    assert not registered & UNUSED


def test_integer_list_is_the_integer_cases():
    int_cases = {n for n, _lo, _hi, body in NUMERIC if "INT(value)" in body}
    assert int_cases == INTEGERS


SCALARS = [n for n, lo, _hi, _b in NUMERIC if not lo]
ARRAYS = [(n, int(lo), int(hi)) for n, lo, hi, _b in NUMERIC if lo]


@pytest.fixture
def equ(workdir):
    with Equ() as e:
        yield e


@pytest.mark.parametrize("name", SCALARS)
def test_scalar_takes_a_value_and_refuses_a_subscript(equ, name):
    equ.set_param(name, 1)
    with pytest.raises(EqulibInvalidParamError):
        equ.set_param(f"{name}[1]", 1)


@pytest.mark.parametrize("name,lo,hi", ARRAYS)
def test_array_bounds(equ, name, lo, hi):
    equ.set_param(f"{name}[{lo}]", 1)
    equ.set_param(f"{name}[{hi}]", 1)
    for bad in (f"{name}[{lo - 1}]" if lo > 0 else f"{name}[-1]", f"{name}[{hi + 1}]", name):
        with pytest.raises(EqulibInvalidParamError):
            equ.set_param(bad, 1)


@pytest.mark.parametrize("name", sorted(INTEGERS))
def test_integers_refuse_fractions_and_huge_values(equ, name):
    target = f"{name}[{dict((a, b) for a, b, _ in ARRAYS)[name]}]" if name not in SCALARS else name
    for bad in (1.5, 2.0 ** 40):
        with pytest.raises(EqulibInvalidParamError):
            equ.set_param(target, bad)


@pytest.mark.parametrize("name", sorted(UNUSED))
def test_unused_names(equ, name):
    with pytest.raises(EqulibInvalidParamError, match="not used by EQU"):
        equ.set_param(name, 0)


@pytest.mark.parametrize("name,length", [(n, int(l)) for n, l in STRINGS])
def test_strings(equ, name, length):
    equ.set_param_str(name, "x" * length)
    with pytest.raises(EqulibInvalidParamError):
        equ.set_param_str(name, "x" * (length + 1))
    with pytest.raises(EqulibInvalidParamError):
        equ.set_param(name, 1)


def test_malformed_names(equ):
    for bad in ("CP[", "CP]", "CP[]", "CP[x]", "CP[1]x", "CP[1,2]", "", "NO_SUCH"):
        with pytest.raises(EqulibInvalidParamError):
            equ.set_param(bad, 1)
