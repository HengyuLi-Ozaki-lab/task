"""tr_mcp: the library's output names are in ``get_state``, in the schema with units, and in ``get_history``.

A name the library lists but the schema does not describe fails here, so a client never reads a number it
cannot interpret. The integration tests need the library Trlib() finds.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
MCP_ROOT = HERE.parents[1]
PYTHON_ROOT = HERE.parents[3]
REPO_ROOT = HERE.parents[4]

for extra in (str(MCP_ROOT.parent), str(PYTHON_ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from tr_mcp import server as srv  # noqa: E402

from trlib import _ffi as _trffi  # noqa: E402

SO = _trffi._default_lib_path()          # Trlib()'s own resolution: MONO_LIB_PATH, TRLIB_PATH, tr/, lib/
needs_lib = pytest.mark.skipif(not SO.exists(), reason=f"libtrapi.so not found at {SO}")
pytestmark = [pytest.mark.forked, needs_lib]


def _library_names(kind):
    from trlib import Trlib
    with Trlib() as t:
        return t.scalar_names() if kind == "scalar" else t.history_names()


def test_every_library_scalar_has_a_schema_entry_with_a_unit():
    props = srv.handle_describe_state_schema()["properties"]["scalars"]["properties"]
    missing = [n for n in _library_names("scalar") if n not in props]
    assert not missing, f"scalars the library exports and the schema does not describe: {missing}"
    for n, entry in props.items():
        assert "unit" in entry and "description" in entry, n


def test_the_schema_describes_no_scalar_the_library_lacks():
    props = srv.handle_describe_state_schema()["properties"]["scalars"]["properties"]
    assert set(props) == set(_library_names("scalar"))


def test_get_state_returns_all_the_scalars():
    names = set(_library_names("scalar"))        # a second live handle is refused: ask before the server opens one
    srv.handle_init()
    try:
        srv.handle_run(6)
        state = srv.handle_get_state()
        assert set(state["scalars"]) == names
        assert state["scalars"]["WPT"] > 0.0
    finally:
        srv.handle_finalize()


def test_a_one_shot_run_of_zero_steps_returns_no_result_of_the_call_before():
    # A run of 0 steps evaluates no step, and finalize then init does not clear TR's global results (CLAUDE.md:
    # module state): the second call would show the first call's PNBT beside its own initial profiles. It returns
    # T only.
    try:
        first = srv.handle_run_and_get_state(params={"PNBTOT": 10.0}, ntmax=20)
        assert first["scalars"]["PNBT"] == pytest.approx(10.0)
        second = srv.handle_run_and_get_state(params={"PNBTOT": 0.0}, ntmax=0)
        assert second["scalars"] == {"T": 0.0}
        assert second["NT"] == 0 and len(second["profile"]) == second["NRMAX"]
    finally:
        srv.STATE.close()


def test_get_state_after_a_one_shot_run_of_zero_steps_returns_no_result_of_the_call_before():
    # The same state read again (get_state on the handle the one-shot call left open) must not show the first
    # call's PNBT either.
    try:
        srv.handle_run_and_get_state(params={"PNBTOT": 10.0}, ntmax=20)
        srv.handle_run_and_get_state(params={"PNBTOT": 0.0}, ntmax=0)
        assert srv.handle_get_state()["scalars"] == {"T": 0.0}
        srv.handle_run(1)
        assert srv.handle_get_state()["scalars"]["PNBT"] == 0.0
    finally:
        srv.STATE.close()


def test_a_changed_parameter_hides_the_results_until_a_step_is_run():
    try:
        srv.handle_init()
        srv.handle_set_param("PNBTOT", 10.0)
        srv.handle_run(5)
        assert srv.handle_get_state()["scalars"]["PNBT"] == pytest.approx(10.0)
        srv.handle_set_param("PNBTOT", 0.0)
        srv.handle_run(0)
        assert srv.handle_get_state()["scalars"] == {"T": 0.0}
    finally:
        srv.STATE.close()
