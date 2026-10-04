"""``Fplib.run`` refuses a step count that is negative or does not fit a C ``int``.

``fp_run`` takes its step count as a C ``int``, and ctypes converts a Python
integer to one with no range check: it keeps the low 32 bits. Measured before this check:
``2**32 + 3`` ran three steps, ``1000 - 2**32`` a thousand, ``2**64 + 7`` seven; ``2**31``
arrived as a negative count, which ``fp_run`` refuses.

The tests replace the library's ``fp_run`` by a recorder, so that they show
what the wrapper hands over, or that it hands over nothing, without a run.
One test per case (``parametrize``, never ``subTest``).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
PYTHON_ROOT = REPO / "python"
DEFAULT_SO = REPO / "fp" / "libfpapi.so"

if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from fplib import Fplib, FplibInvalidParamError  # noqa: E402

pytestmark = pytest.mark.skipif(
    not DEFAULT_SO.exists(),
    reason=f"libfpapi.so not built at {DEFAULT_SO}; run `make -C fp libfpapi.so`",
)

C_INT_MAX = 2**31 - 1


def _recorded(monkeypatch, lib):
    """The arguments ``fp_run`` is called with from now on; it answers 0."""
    calls = []

    def fake(value):
        calls.append(value)
        return 0

    monkeypatch.setattr(lib._lib, "fp_run", fake)
    return calls


# The last one is longer than Python prints (4300 digits): the refusal must not try to.
@pytest.mark.parametrize("value", [2**31, 2**32 + 3, 2**64 + 7, 1000 - 2**32, -1, -(2**31) - 1, pytest.param(10**5000, id="10**5000")])
def test_a_step_count_that_is_negative_or_no_c_int_is_refused_before_the_library_is_called(monkeypatch, value):
    with Fplib() as lib:
        calls = _recorded(monkeypatch, lib)
        with pytest.raises(FplibInvalidParamError) as caught:
            lib.run(value)
        assert calls == []
        assert str(C_INT_MAX) in str(caught.value)


@pytest.mark.parametrize("value", [0, 3, 2**31 - 1])
def test_a_step_count_in_range_is_handed_over_as_it_is(monkeypatch, value):
    with Fplib() as lib:
        calls = _recorded(monkeypatch, lib)
        lib.run(value)
        assert calls == [value]
