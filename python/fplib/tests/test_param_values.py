"""What ``fp_set_param`` refuses before it assigns (``fp/fp_param_registry.f90``).

* **A malformed subscript**, for every name. The registry marked one for the
  array cases only: a scalar's ``CASE`` never looks at the index, so
  ``NTHMAX[zz]`` set ``NTHMAX``; and list-directed ``READ`` took ``[1,2]``,
  ``[2 3]`` and ``[/]``, and text after the closing bracket was ignored
  (``PN[1]x`` set ``PN[1]``).
* **A value that is not finite**, for every parameter: NaN and the infinities
  were assigned as they came.
* **A value beyond the default integer, for an integer parameter**: ``NINT()``
  of it is the compiler's choice (the nearest end of the integer range with
  gfortran on arm64), and what it leaves is then a mesh count or a switch.

Not changed: a subscript that is a whole number still sets a scalar
(``NRMAX[3]`` is ``NRMAX``), as upstream's fan-out test for TR relies on
(``python/trlib/tests/test_property_fanout.py``).

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
DEFAULT_SO = REPO / "fp" / "libfpapi.so"

for _root in (PYTHON_ROOT, SERVERS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from fplib import Fplib, FplibInvalidParamError  # noqa: E402

pytestmark = pytest.mark.skipif(
    not DEFAULT_SO.exists(),
    reason=f"libfpapi.so not built at {DEFAULT_SO}; run `make -C fp libfpapi.so`",
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
    with Fplib() as lib:
        try:
            lib.set_param(name, value)
        except FplibInvalidParamError:
            return True
    return False


def _int_and_real_names():
    """(integer names, real names) of the MCP server's registry, an array as NAME[1]."""
    from fp_mcp.server import PARAMETER_REGISTRY
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
    assert _refused("NTHMAX" + suffix, 20.0)


@pytest.mark.parametrize("suffix", MALFORMED)
def test_a_malformed_subscript_is_refused_for_an_array(suffix):
    assert _refused("PN" + suffix, 1.0)


@pytest.mark.parametrize("name", ["PN[1]", "PN[ 2 ]", "PN[02]", "MODELC[1]", "NS_NSA[2]", "PN[000000001]"])   # nine digits are read
def test_a_whole_number_subscript_is_taken(name):
    assert not _refused(name, 1.0)


@pytest.mark.parametrize("name", ["PN", "PN[0]", "PN[101]", "MODELC[0]", "NOSUCH", "NOSUCH[1]", "nthmax", ""])
def test_what_was_refused_before_still_is(name):
    assert _refused(name, 1.0)


def test_a_whole_number_subscript_on_a_scalar_still_sets_it():
    """Left as it is: the registry takes NAME[i] for a scalar NAME (see the module's text)."""
    with Fplib() as lib:
        lib.set_param("NPMAX", 10.0)
        lib.set_param("NTHMAX", 10.0)
        lib.set_param("NRMAX[3]", 2.0)
        lib.run(0)
        assert lib.get_state().nrmax == 2


# ----------------------------------------------------------------- values

@pytest.mark.parametrize("name", ["RR", "DELT", "EPSFP", "NTHMAX", "MODELD", "PN[1]", "MODELC[1]"])
@pytest.mark.parametrize("value", [NAN, INF, -INF], ids=["nan", "inf", "-inf"])
def test_a_value_that_is_not_finite_is_refused(name, value):
    assert _refused(name, value)


# The range kept is -HUGE .. HUGE, the one every compiler converts alike: -2**31 and the
# fractions just above 2**31 - 1 are refused with the rest.
@pytest.mark.parametrize("value", [2.0**31, -(2.0**31), 2.0**31 - 0.75, -(2.0**31) - 1.0, 1.0e10, -1.0e10, 2.0**64, 1.0e300],
                         ids=["2**31", "-2**31", "2**31-0.75", "-2**31-1", "1e10", "-1e10", "2**64", "1e300"])
def test_an_integer_parameter_refuses_a_value_beyond_the_integer(value):
    assert _refused("NTHMAX", value)


@pytest.mark.parametrize("value", [2.0**31 - 1.0, -(2.0**31) + 1.0, 0.0, 30.5],
                         ids=["2**31-1", "-2**31+1", "0", "30.5"])
def test_an_integer_parameter_takes_what_the_integer_holds(value):
    # NTMAX is assigned and nothing else: fp_run steps the count its caller gives.
    assert not _refused("NTMAX", value)


def test_every_integer_parameter_refuses_a_value_beyond_the_integer():
    """The Fortran list of integer names (value_refused) against the server's registry."""
    ints, _ = _int_and_real_names()
    assert len(ints) >= 25, ints
    with Fplib() as lib:
        taken = []
        for name in ints:
            for value in (1.0e10, -1.0e10, NAN):
                try:
                    lib.set_param(name, value)
                except FplibInvalidParamError:
                    continue
                taken.append((name, value))
    assert not taken, taken


def _integer_names_in_the_source():
    """(the names whose CASE converts to an integer, the names value_refused lists), from fp_param_registry.f90."""
    source = (REPO / "fp" / "fp_param_registry.f90").read_text()

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

    setter = code(source[source.index("FUNCTION fp_param_set(name, value)"):source.index("END FUNCTION fp_param_set")])
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

    The run-time test above cannot hold the names that have a range check of
    their own (the species counts): they refuse a huge value either way.
    """
    converted, listed = _integer_names_in_the_source()
    # The count is of today's integer parameters: a new one changes it here too.
    assert len(converted) == 25, sorted(converted)
    assert listed == converted, (sorted(listed - converted), sorted(converted - listed))


def test_no_real_parameter_is_held_to_the_integer_range():
    _, reals = _int_and_real_names()
    assert len(reals) >= 29, reals
    with Fplib() as lib:
        refused = []
        for name in reals:
            try:
                lib.set_param(name, 1.0e10)
            except FplibInvalidParamError:
                refused.append(name)
    assert not refused, refused


def test_a_refused_value_leaves_the_parameter_as_it_was():
    with Fplib() as lib:
        lib.set_param("NPMAX", 10.0)
        lib.set_param("NTHMAX", 10.0)
        lib.set_param("NRMAX", 3.0)
        for name, value in (("NRMAX", NAN), ("NRMAX", 1.0e10), ("NRMAX[zz]", 7.0), ("NRMAX[1]x", 7.0)):
            with pytest.raises(FplibInvalidParamError):
                lib.set_param(name, value)
        lib.run(0)
        assert lib.get_state().nrmax == 3
