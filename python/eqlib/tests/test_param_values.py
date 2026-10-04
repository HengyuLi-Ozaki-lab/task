"""What ``eq_set_param`` refuses before it assigns (``eq/eq_param_registry.f90``).

* **A malformed subscript**, for every name. The registry marked one for the
  array cases only: a scalar's ``CASE`` never looks at the index, so
  ``RR[zz]`` set ``RR``; and list-directed ``READ`` took ``[1,2]``, ``[2 3]``
  and ``[/]``, and text after the closing bracket was ignored (``PSIB[0]x``
  set ``PSIB[0]``).
* **A name the registry cannot hold whole.** It was cut to the 32 characters
  of the registry's buffer, so ``RR`` followed by blanks and anything else was
  the name ``RR``.
* **A value that is not finite**, for every parameter: NaN and the infinities
  were assigned as they came.
* **A value beyond the default integer, for an integer parameter**: ``INT()``
  of it is the compiler's choice (the nearest end of the integer range with
  gfortran on arm64), and what it leaves is then a mesh count or a switch.

Not changed: a subscript that is a whole number still sets a scalar
(``RR[9]`` is ``RR``), as in TR and FP, where upstream's fan-out test relies
on it (``python/trlib/tests/test_property_fanout.py``).

One test per case (``parametrize``, never ``subTest``: under ``--forked`` a
failing ``subTest`` is reported as passed). The tests that go through every
name collect what went wrong and assert once.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
PYTHON_ROOT = REPO / "python"
SERVERS_ROOT = PYTHON_ROOT / "mcp-servers"
DEFAULT_SO = REPO / "eq" / "libeqapi.so"

for _root in (PYTHON_ROOT, SERVERS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from eqlib import Eq, EqlibInvalidParamError  # noqa: E402

pytestmark = pytest.mark.skipif(
    not DEFAULT_SO.exists(),
    reason=f"libeqapi.so not built at {DEFAULT_SO}; run `make -C eq libeqapi.so`",
)

NAN = float("nan")
INF = float("inf")

# Every form but "NAME" and "NAME[<digits>]" (blanks around the digits are taken).
MALFORMED = [
    "[zz]", "[]", "[ ]", "[1", "1]", "]", "[", "[1]x", "[1] x", "[1]]", "[[1]",
    "[1,2]", "[2 3]", "[/]", "[2*3]", "[1.0]", "[+1]", "[-1]", "[1e0]",
    "[99999999999999999999]",
    "[0000000001]", "[1000000000]",      # ten digits: one more than the parser reads
]


def _refused(name, value):
    with Eq() as lib:
        try:
            lib.set_param(name, value)
        except EqlibInvalidParamError:
            return True
    return False


def _int_and_real_names():
    """(integer names, real names) of the MCP server's registry, an array as NAME[1]."""
    from eq_mcp.server import PARAMETER_REGISTRY
    ints, reals = [], []
    for name, entry in PARAMETER_REGISTRY.items():
        kind = entry["type"]
        key = f"{name}[1]" if "[" in kind else name
        if kind.startswith("int"):
            ints.append(key)
        elif kind.startswith("float"):
            reals.append(key)
    return ints, reals


# ------------------------------------------------------------- subscripts

@pytest.mark.parametrize("suffix", MALFORMED)
def test_a_malformed_subscript_is_refused_for_a_scalar(suffix):
    assert _refused("NRMAX" + suffix, 20.0)


@pytest.mark.parametrize("suffix", MALFORMED)
def test_a_malformed_subscript_is_refused_for_an_array(suffix):
    assert _refused("PSIB" + suffix, 1.0)


@pytest.mark.parametrize("name", ["PSIB[0]", "PSIB[5]", "PSIB[ 0 ]", "PSIB[05]", "RIPFC[1]", "PSIB[000000001]"])   # nine digits are read
def test_a_whole_number_subscript_is_taken(name):
    assert not _refused(name, 1.0)


@pytest.mark.parametrize("name", ["PSIB", "PSIB[6]", "RIPFC[0]", "RIPFC", "NOSUCH", "NOSUCH[1]", "rr", ""])
def test_what_was_refused_before_still_is(name):
    assert _refused(name, 1.0)


@pytest.mark.parametrize("name", ["RR[9]", "RR[0]", "NRMAX[1]"])
def test_a_whole_number_subscript_on_a_scalar_is_still_taken(name):
    """Left as it is: the registry takes NAME[i] for a scalar NAME (see the module's text)."""
    assert not _refused(name, 3.0)

# ----------------------------------------------------------------- values

@pytest.mark.parametrize("name", ["RR", "EPSEQ", "PP0", "NRMAX", "MDLEQF", "PSIB[0]", "RIPFC[1]"])
@pytest.mark.parametrize("value", [NAN, INF, -INF], ids=["nan", "inf", "-inf"])
def test_a_value_that_is_not_finite_is_refused(name, value):
    assert _refused(name, value)


# The range kept is -HUGE .. HUGE, the one every compiler converts alike: -2**31 and the
# fractions just above 2**31 - 1 are refused with the rest.
@pytest.mark.parametrize("value", [2.0**31, -(2.0**31), 2.0**31 - 0.75, -(2.0**31) - 1.0, 1.0e10, -1.0e10, 2.0**64, 1.0e300],
                         ids=["2**31", "-2**31", "2**31-0.75", "-2**31-1", "1e10", "-1e10", "2**64", "1e300"])
def test_an_integer_parameter_refuses_a_value_beyond_the_integer(value):
    assert _refused("NRMAX", value)


@pytest.mark.parametrize("value", [2.0**31 - 1.0, -(2.0**31) + 1.0, 0.0, 30.5],
                         ids=["2**31-1", "-2**31+1", "0", "30.5"])
def test_an_integer_parameter_takes_what_the_integer_holds(value):
    # NPRINT is assigned and nothing else.
    assert not _refused("NPRINT", value)


def test_every_integer_parameter_refuses_a_value_beyond_the_integer():
    """The Fortran list of integer names (value_refused) against the server's registry."""
    ints, _ = _int_and_real_names()
    assert len(ints) >= 25, ints
    with Eq() as lib:
        taken = []
        for name in ints:
            for value in (1.0e10, -1.0e10, NAN):
                try:
                    lib.set_param(name, value)
                except EqlibInvalidParamError:
                    continue
                taken.append((name, value))
    assert not taken, taken


def _integer_names_in_the_source():
    """(the names whose CASE converts to an integer, the names value_refused lists), from eq_param_registry.f90."""
    source = (REPO / "eq" / "eq_param_registry.f90").read_text()

    def code(text):
        """TEXT without comments, a continued statement on one line."""
        lines = [line.split("!", 1)[0].rstrip() for line in text.splitlines()]   # no name or selector holds a "!"
        return re.sub(r"&\s*\n\s*&?", " ", "\n".join(lines))

    def cases(text):
        """[(the names of a CASE selector, the statements it governs)]"""
        marks = list(re.finditer(r"\bCASE\s*\(([^)]*)\)", text, flags=re.I))
        ends = [m.start() for m in marks[1:]] + [len(text)]
        return [([name.upper() for name in re.findall(r"""["']([A-Za-z_0-9]+)["']""", m.group(1))], text[m.end():end])
                for m, end in zip(marks, ends)]

    setter = code(source[source.index("SUBROUTINE eq_param_set(name, value, ierr)"):source.index("END SUBROUTINE eq_param_set")])
    converted = set()
    for names, body in cases(setter):
        if re.search(r"\bN?INT\s*\(\s*value\b", body, flags=re.I):   # either intrinsic, however it is written
            converted.update(names)
    refused = code(source[source.index("FUNCTION value_refused"):source.index("END FUNCTION value_refused")])
    listed = set()
    for names, _ in cases(refused[refused.index("SELECT CASE (TRIM(b))") + len("SELECT CASE (TRIM(b))"):]):   # after the selector
        listed.update(names)
    return converted, listed


def test_the_integer_list_is_the_integer_cases_of_the_setter():
    """value_refused's names against the source: a new integer CASE must be listed.

    A CASE that assigns an integer variable without NINT() or INT() is not seen.

    The run-time test above holds the list to the server's registry; this one
    holds it to the Fortran source, which is what a new CASE changes.
    """
    converted, listed = _integer_names_in_the_source()
    # The count is of today's integer parameters: a new one changes it here too.
    assert len(converted) == 25, sorted(converted)
    assert listed == converted, (sorted(listed - converted), sorted(converted - listed))


def test_no_real_parameter_is_held_to_the_integer_range():
    _, reals = _int_and_real_names()
    assert len(reals) >= 62, reals
    with Eq() as lib:
        refused = []
        for name in reals:
            try:
                lib.set_param(name, 1.0e10)
            except EqlibInvalidParamError:
                refused.append(name)
    assert not refused, refused


LONG = "RR" + " " * 31          # 33 characters: one more than the registry's buffer


@pytest.mark.parametrize("name", [LONG + "junk", LONG + "[1]", "NRMAX" + " " * 28 + "x"])
def test_a_name_longer_than_the_registry_holds_is_refused(name):
    assert _refused(name, 3.0)
