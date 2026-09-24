"""libfpapi is a .dll on Windows and needs its directory on the DLL search path."""
import os
import sys

import pytest

from fplib import _ffi


def test_windows_candidates_are_dlls(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert [p.relative_to(_ffi._repo_root()).parts for p in _ffi._candidate_paths()] == [
        ("fp", "libfpapi.dll"),
        ("lib", "libfpapi.dll"),
    ]


def test_macos_and_linux_candidates_are_so(monkeypatch):
    for platform in ("darwin", "linux"):
        monkeypatch.setattr(sys, "platform", platform)
        assert [p.name for p in _ffi._candidate_paths()] == ["libfpapi.so", "libfpapi.so"]


def test_windows_registers_dll_directory_before_loading(monkeypatch, tmp_path):
    lib = tmp_path / "libfpapi.dll"
    lib.write_bytes(b"")
    calls = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(_ffi, "_DLL_DIR_HANDLES", {})
    monkeypatch.setattr(_ffi.os, "add_dll_directory",
                        lambda d: calls.append(("dir", d)) or object(), raising=False)

    class FakeCDLL:
        def __init__(self, path, mode=0):
            calls.append(("load", path))

    monkeypatch.setattr(_ffi.ctypes, "CDLL", FakeCDLL)
    monkeypatch.setattr(_ffi, "_apply_prototypes", lambda handle: handle)
    _ffi.load_library(str(lib))
    assert calls == [("dir", str(tmp_path)), ("load", str(lib))]
    assert len(_ffi._DLL_DIR_HANDLES) == 1


def test_windows_registers_each_directory_once(monkeypatch, tmp_path):
    lib = tmp_path / "libfpapi.dll"
    lib.write_bytes(b"")
    calls = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(_ffi, "_DLL_DIR_HANDLES", {})
    monkeypatch.setattr(_ffi.os, "add_dll_directory",
                        lambda d: calls.append(("dir", d)) or object(), raising=False)

    class FakeCDLL:
        def __init__(self, path, mode=0):
            calls.append(("load", path))

    monkeypatch.setattr(_ffi.ctypes, "CDLL", FakeCDLL)
    monkeypatch.setattr(_ffi, "_apply_prototypes", lambda handle: handle)
    _ffi.load_library(str(lib))
    _ffi.load_library(str(lib))
    assert [c for c in calls if c[0] == "dir"] == [("dir", str(tmp_path))]
    assert [c for c in calls if c[0] == "load"] == [("load", str(lib)), ("load", str(lib))]
    assert len(_ffi._DLL_DIR_HANDLES) == 1


def test_windows_relative_path_is_made_absolute(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    lib = tmp_path / "libfpapi.dll"
    lib.write_bytes(b"")
    calls = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(_ffi, "_DLL_DIR_HANDLES", {})
    monkeypatch.setattr(_ffi.os, "add_dll_directory",
                        lambda d: calls.append(("dir", d)) or object(), raising=False)

    class FakeCDLL:
        def __init__(self, path, mode=0):
            calls.append(("load", path))

    monkeypatch.setattr(_ffi.ctypes, "CDLL", FakeCDLL)
    monkeypatch.setattr(_ffi, "_apply_prototypes", lambda handle: handle)
    _ffi.load_library("libfpapi.dll")
    assert calls[0] == ("dir", os.path.realpath(str(tmp_path)))


def test_windows_missing_library_names_the_dll(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    missing = tmp_path / "libfpapi.dll"
    with pytest.raises(FileNotFoundError, match=r"^libfpapi\.dll not found"):
        _ffi.load_library(str(missing))


def test_non_windows_never_touches_dll_directory(monkeypatch, tmp_path):
    lib = tmp_path / "libfpapi.so"
    lib.write_bytes(b"")

    def forbidden(_directory):
        raise AssertionError("os.add_dll_directory must not be called off Windows")

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(_ffi.os, "add_dll_directory", forbidden, raising=False)
    monkeypatch.setattr(_ffi.ctypes, "CDLL", lambda path, mode=0: object())
    monkeypatch.setattr(_ffi, "_apply_prototypes", lambda handle: handle)
    _ffi.load_library(str(lib))
