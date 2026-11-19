"""``eq:`` names through tr_mcp: passed to the library as they are (no local check).

Pure-Python tests use a recorder for the library; the integration tests need
``tr/libtrapi.so`` and use the real registry of EQ inside it.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

HERE = Path(__file__).resolve()
MCP_ROOT = HERE.parents[1]
PYTHON_ROOT = HERE.parents[3]
REPO_ROOT = HERE.parents[4]

for extra in (str(MCP_ROOT.parent), str(PYTHON_ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from tr_mcp import server as srv  # noqa: E402

SO = REPO_ROOT / "tr" / "libtrapi.so"


def test_an_eq_name_reaches_the_library_unchanged():
    fake = mock.Mock()
    with mock.patch.object(srv.STATE, "ensure_open", return_value=fake):
        srv.handle_set_param("eq:RB", 2.1)
        srv.handle_set_param_str("eq:KNAMEQ", "x")
        srv._apply_bulk_params(fake, {"eq:NSGMAX": 128})
    fake.set_param.assert_any_call("eq:RB", 2.1)
    fake.set_param.assert_any_call("eq:NSGMAX", 128.0)
    fake.set_param_str.assert_called_once_with("eq:KNAMEQ", "x")


def test_describe_parameters_says_how_eq_names_work():
    assert "eq:" in srv.handle_describe_parameters()["eq_names"]


@pytest.mark.skipif(not SO.exists(), reason="libtrapi.so not built")
@pytest.mark.forked
def test_an_eq_name_is_taken_by_the_real_library():
    try:
        out = srv.handle_set_param("eq:RB", 2.1)
    finally:
        srv.STATE.close()
    assert out == "set eq:RB = 2.1"


@pytest.mark.skipif(not SO.exists(), reason="libtrapi.so not built")
@pytest.mark.forked
def test_an_unknown_eq_name_is_refused_by_the_real_library():
    try:
        with pytest.raises(Exception) as ei:
            srv.handle_set_param("eq:NOSUCHNAME", 1.0)
    finally:
        srv.STATE.close()
    assert "NOSUCHNAME" in str(ei.value) or "ierr=1" in str(ei.value) or "invalid" in str(ei.value).lower()
