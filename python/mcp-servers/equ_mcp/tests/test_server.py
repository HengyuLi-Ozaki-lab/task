"""equ_mcp: the registry against the Fortran one, the schema, the handlers,
the bulk-set shapes, the error mapping and the command line."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
for extra in (str(HERE.parents[2]), str(HERE.parents[3])):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from equ_mcp import server as srv  # noqa: E402
from equlib import (EqulibCalculationFailedError, EqulibInvalidParamError,  # noqa: E402
                    EqulibNotImplementedError)

REG = (HERE.parents[4] / "equ" / "equ_param_registry.f90").read_text()


def _fortran_names():
    return set(re.findall(r'^\s+CASE \("([A-Z0-9_]+)"\)', REG, re.M))


def _fortran_arrays():
    return {n: (int(lo), int(hi))
            for n, lo, hi in re.findall(r'CASE \("([A-Z0-9_]+)"\)\s+! \((\d+):(\d+)\)', REG)}


def test_registry_equals_the_fortran_registry():
    assert set(srv.PARAMETER_REGISTRY) == _fortran_names()


def test_array_types_carry_the_fortran_bounds():
    for name, (lo, hi) in _fortran_arrays().items():
        assert srv.PARAMETER_REGISTRY[name]["type"].endswith(f"[{lo}..{hi}]"), name


def test_integer_types_are_the_fortran_integers():
    ints = set(re.findall(r'"([A-Z0-9_]+)"', REG[REG.index("LOGICAL FUNCTION value_refused"):
                                                    REG.index("END FUNCTION value_refused")]))
    declared = {n for n, m in srv.PARAMETER_REGISTRY.items() if m["type"].startswith("int")}
    assert declared == ints


def test_every_entry_is_complete():
    groups = {"device", "mesh", "plasma", "profile", "coils", "boundary", "convergence", "output"}
    for name, meta in srv.PARAMETER_REGISTRY.items():
        assert set(meta) == {"type", "group", "default", "description"}, name
        assert meta["group"] in groups and meta["description"], name


def test_state_schema_lists_every_scalar():
    from equlib.state import PROFILES, SCALARS
    props = srv.STATE_SCHEMA["properties"]
    assert set(props["scalars"]["properties"]) == {s.upper() for s in SCALARS}
    assert set(props["profiles"]["properties"]) == {p.upper() for p in PROFILES}


class _Equ:
    def __init__(self, exc=None):
        self.calls = []
        self._exc = exc
        self.closed = False

    def __getattr__(self, name):
        def call(*args, **kwargs):
            if self._exc is not None:
                raise self._exc
            self.calls.append((name, args, kwargs))
        return call


@pytest.fixture
def fake(monkeypatch):
    equ = _Equ()
    state = srv._ServerState()
    monkeypatch.setattr(state, "ensure_open", lambda: equ)
    monkeypatch.setattr(srv, "STATE", state)
    return equ


def test_bulk_shapes(fake):
    applied = srv.handle_set_params({"TCUR": 0.3, "IVAC": [0, -1, -2], "CP": {10: 0.05},
                                     "KNAMCOIL": "coildata"})["applied"]
    assert applied == ["TCUR", "IVAC[0]", "IVAC[1]", "IVAC[2]", "CP[10]", "KNAMCOIL"]
    assert fake.calls[-1] == ("set_param_str", ("KNAMCOIL", "coildata"), {})


def test_a_list_for_a_scalar_is_refused(fake):
    with pytest.raises(srv.ToolError, match="not an array"):
        srv.handle_set_params({"TCUR": [1, 2]})


@pytest.mark.parametrize("value", [True, "x", float("nan"), None])
def test_numbers_only(fake, value):
    with pytest.raises(srv.ToolError):
        srv.handle_set_param("TCUR", value)


@pytest.mark.parametrize("exc,text", [
    (EqulibInvalidParamError("x"), "invalid parameter"),
    (EqulibCalculationFailedError("x"), "calculation failed"),
    (EqulibNotImplementedError("x"), "not implemented"),
])
def test_error_mapping(monkeypatch, exc, text):
    equ = _Equ(exc)
    state = srv._ServerState()
    monkeypatch.setattr(state, "ensure_open", lambda: equ)
    monkeypatch.setattr(srv, "STATE", state)
    with pytest.raises(srv.ToolError, match=text):
        srv.handle_run(1)


def test_handlers_pass_through(fake, tmp_path):
    srv.handle_read_parm("equparm")
    srv.handle_run(0)
    srv.handle_write_geqdsk("g", overwrite=True)
    assert [c[0] for c in fake.calls] == ["read_parm", "run", "write_geqdsk"]
    assert fake.calls[-1] == ("write_geqdsk", ("g",), {"overwrite": True})


def test_print_tools(capsys):
    assert srv.main(["--print-tools"]) == 0
    assert capsys.readouterr().out.split() == sorted(srv.TOOLS)


@pytest.mark.skipif(not srv.MCP_AVAILABLE, reason="mcp.server.fastmcp not installed")
def test_build_server_registers_every_tool():
    import asyncio
    mcp = srv.build_server()
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert names == set(srv.TOOLS)
