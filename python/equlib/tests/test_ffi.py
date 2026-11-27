"""The ctypes layer: layout, prototypes, the state's dictionary."""
from __future__ import annotations

import ctypes
import json

from equlib import _ffi
from equlib.state import EquState
from equlib.tests.conftest import lib_path, requires_lib

pytestmark = requires_lib


def test_layout_matches_the_library():
    lib = _ffi.load_library(str(lib_path()))
    assert lib.equ_state_abi_version() == _ffi.EQU_STATE_ABI_VERSION
    assert lib.equ_state_size() == ctypes.sizeof(_ffi.EquStateC)


def test_state_dict_is_json():
    c = _ffi.EquStateC()
    c.nr, c.nz, c.nv, c.nsu = 3, 3, 2, 4
    d = EquState.from_c(c).to_dict()
    json.dumps(d)
    assert d["NR"] == 3 and len(d["RG"]) == 3 and len(d["profiles"]["PRESSURE"]) == 2
