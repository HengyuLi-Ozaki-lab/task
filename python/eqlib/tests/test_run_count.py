"""``Eq.run`` refuses a mode that is not a C ``int``'s.

``eq_run`` takes its mode as a C ``int``, and ctypes converts a Python
integer to one with no range check: it keeps the low 32 bits. So ``2**32`` was mode 0, the
analytic solve, and ``2**32 + 1`` mode 1, the file load. A mode that fits is handed over as it is,
and the library answers for the ones it does not know.

The tests replace the library's ``eq_run`` by a recorder, so that they show
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
DEFAULT_SO = REPO / "eq" / "libeqapi.so"

if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from eqlib import Eq, EqlibInvalidParamError  # noqa: E402

pytestmark = pytest.mark.skipif(
    not DEFAULT_SO.exists(),
    reason=f"libeqapi.so not built at {DEFAULT_SO}; run `make -C eq libeqapi.so`",
)

C_INT_MAX = 2**31 - 1


def _recorded(monkeypatch, lib):
    """The arguments ``eq_run`` is called with from now on; it answers 0."""
    calls = []

    def fake(value):
        calls.append(value)
        return 0

    monkeypatch.setattr(lib._lib, "eq_run", fake)
    return calls


# The last one is longer than Python prints (4300 digits): the refusal must not try to.
@pytest.mark.parametrize("value", [2**31, 2**32, 2**32 + 1, 2**64, -(2**31) - 1, -(2**32), pytest.param(10**5000, id="10**5000")])
def test_a_mode_outside_a_c_int_is_refused_before_the_library_is_called(monkeypatch, value):
    with Eq() as lib:
        calls = _recorded(monkeypatch, lib)
        with pytest.raises(EqlibInvalidParamError) as caught:
            lib.run(value)
        assert calls == []
        assert str(C_INT_MAX) in str(caught.value)


@pytest.mark.parametrize("value", [0, 1, 7, -1, 2**31 - 1, -(2**31)])
def test_a_mode_in_range_is_handed_over_as_it_is(monkeypatch, value):
    with Eq() as lib:
        calls = _recorded(monkeypatch, lib)
        lib.run(value)
        assert calls == [value]
