"""Fixtures of the equlib tests: a working directory per test (KNAMCOIL and
the G-EQDSK paths are relative) and the library's presence."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

_SO = Path(__file__).resolve().parents[3] / "equ" / "libequapi.so"


def lib_path() -> Path:
    env = os.environ.get("EQULIB_PATH")
    return Path(env) if env else _SO


requires_lib = pytest.mark.skipif(not lib_path().exists(), reason="libequapi.so not built")


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path
