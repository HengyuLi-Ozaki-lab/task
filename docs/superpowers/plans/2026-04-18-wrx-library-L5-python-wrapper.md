# WRX ライブラリ化 Phase L-5: Python ラッパ (`python/wrxlib/`) 実装計画

**位置:** `docs/superpowers/plans/2026-04-18-wrx-library-L5-python-wrapper.md`
**実装スパン:** ~1 週
**前提:** L-4 完了（`libwrxapi.so` がビルド可能・C smoke test 通過）
**目標:** `wrxlib` Python ラッパ（ctypes 2 層）の作成。Layer 3 (Python ラッパ) のスケルトンを完成させ、L-6 で本格的に検証する。

## 設計方針

`tr` の Phase L-5 (`python/trlib/`) と同一構成を `wrx` 用に移植する。`wr` モジュールと並行存在するため、**Python パッケージ名は明確に分離**（`wrlib` ≠ `wrxlib`）。

## File Structure

```
python/wrxlib/
├── __init__.py
├── _ffi.py        # ctypes 低レベル
├── wrxlib.py      # 高レベル class WrxLib
├── state.py       # numpy state helpers
├── errors.py      # WrxError, error code map
├── README.md      # 雛形のみ（L-7 で本体）
└── tests/
    ├── __init__.py
    ├── test_smoke.py
    └── test_init_finalize.py
```

## Task 1: ブランチ作成と初期構造

```bash
mkdir -p python/wrxlib/tests
touch python/wrxlib/{__init__,_ffi,wrxlib,state,errors}.py
touch python/wrxlib/tests/{__init__,test_smoke,test_init_finalize}.py
```

`python/wrxlib/__init__.py`:
```python
from .wrxlib import WrxLib
from .errors import WrxError, ErrorCode
__all__ = ['WrxLib', 'WrxError', 'ErrorCode']
__version__ = '0.1.0'
```

## Task 2: `errors.py` を実装

`tr` の `trlib/errors.py` と同一パターン。エラーコード列挙を `wrx_api.h` の `enum wrx_error_code` と同期させる。

```python
import enum
class ErrorCode(enum.IntEnum):
    OK = 0
    NOT_INITIALIZED = 1
    ALREADY_INITIALIZED = 2
    INVALID_PARAM = 3
    UNKNOWN_PARAM = 4
    SOLVER_FAILURE = 5

class WrxError(RuntimeError):
    def __init__(self, code: int, msg: str = ''):
        self.code = ErrorCode(code) if code in ErrorCode._value2member_map_ else code
        super().__init__(f'WRX error {self.code}: {msg or self.code.name}')
```

## Task 3: `state.py` を実装

レイ追跡固有の状態を numpy で扱う。`wr` と異なりレイ本数が大きい場合があるので `(NRAYMAX, NSTPMAX)` 二次元の扱いを早めに固める。

```python
import numpy as np
from dataclasses import dataclass

@dataclass
class WrxState:
    nraymax: int
    nstpmax_actual: int  # 実際に積分したステップ数
    nrmax: int
    rays_r: np.ndarray   # shape: (nraymax, nstpmax_actual)
    rays_z: np.ndarray
    rays_phi: np.ndarray
    rays_pwr: np.ndarray
    pwr_profile: np.ndarray  # shape: (nrmax,)  driven power profile
```

## Task 4: `_ffi.py` を実装

`tr` の `_ffi.py` パターンに準拠。違いは：
- ライブラリ名: `libwrxapi.so` （`libwrapi.so` ではない）
- 関数 prefix: `wrx_` （`wr_` ではない）— **シンボル衝突しない**

```python
import ctypes
from pathlib import Path

def _load():
    candidates = [
        Path(__file__).parent.parent.parent / 'wrx' / 'libwrxapi.so',
        Path(__file__).parent.parent.parent / 'lib' / 'libwrxapi.so',
        Path('libwrxapi.so'),
    ]
    for p in candidates:
        if p.exists():
            return ctypes.CDLL(str(p))
    raise OSError(f'libwrxapi.so not found in: {candidates}')

_lib = _load()

# 5 関数 C ABI シグネチャ
_lib.wrx_init.argtypes = []
_lib.wrx_init.restype = ctypes.c_int

_lib.wrx_run.argtypes = [ctypes.c_int]   # ntmax (積分ステップ上限)
_lib.wrx_run.restype = ctypes.c_int

_lib.wrx_get_state.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_double), ctypes.c_int]
_lib.wrx_get_state.restype = ctypes.c_int

_lib.wrx_set_param.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_double), ctypes.c_int]
_lib.wrx_set_param.restype = ctypes.c_int

_lib.wrx_finalize.argtypes = []
_lib.wrx_finalize.restype = ctypes.c_int
```

## Task 5: `wrxlib.py`（高レベル class）を実装

`tr` の `trlib.py` パターン。状態取り出しは `state.py` に委譲。

```python
import numpy as np
from . import _ffi
from .errors import WrxError, ErrorCode
from .state import WrxState

class WrxLib:
    def __init__(self):
        self._initialized = False

    def __enter__(self):
        self.init()
        return self

    def __exit__(self, *exc):
        self.finalize()
        return False

    def init(self):
        if self._initialized:
            raise WrxError(ErrorCode.ALREADY_INITIALIZED)
        rc = _ffi._lib.wrx_init()
        if rc != 0:
            raise WrxError(rc)
        self._initialized = True

    def run(self, ntmax: int = 0):
        if not self._initialized:
            raise WrxError(ErrorCode.NOT_INITIALIZED)
        rc = _ffi._lib.wrx_run(ntmax)
        if rc != 0:
            raise WrxError(rc)

    def get_state(self, name: str, size: int) -> np.ndarray:
        buf = np.zeros(size, dtype=np.float64)
        rc = _ffi._lib.wrx_get_state(name.encode(), buf.ctypes.data_as(_ffi.ctypes.POINTER(_ffi.ctypes.c_double)), size)
        if rc != 0:
            raise WrxError(rc, f'get_state({name!r})')
        return buf

    def set_param(self, name: str, values):
        arr = np.atleast_1d(np.asarray(values, dtype=np.float64))
        rc = _ffi._lib.wrx_set_param(name.encode(), arr.ctypes.data_as(_ffi.ctypes.POINTER(_ffi.ctypes.c_double)), arr.size)
        if rc != 0:
            raise WrxError(rc, f'set_param({name!r})')

    def finalize(self):
        if not self._initialized:
            return
        rc = _ffi._lib.wrx_finalize()
        if rc != 0:
            raise WrxError(rc)
        self._initialized = False
```

## Task 6: 軽量 unittest を追加

stdlib `unittest` を使用（`pytest` 非導入）。`tr` Phase L-5 と同様に最低限の smoke / init / finalize を確認する。

`tests/test_smoke.py`:
```python
import unittest
from wrxlib import WrxLib

class TestSmoke(unittest.TestCase):
    def test_init_finalize(self):
        lib = WrxLib()
        lib.init()
        lib.finalize()

    def test_context_manager(self):
        with WrxLib() as w:
            self.assertTrue(w._initialized)

    def test_double_init_raises(self):
        lib = WrxLib()
        lib.init()
        try:
            with self.assertRaises(Exception):
                lib.init()
        finally:
            lib.finalize()
```

## Task 7: 簡易 README（雛形のみ、L-7 で本体）

`python/wrxlib/README.md`:
```markdown
# wrxlib — Python wrapper for TASK/WRX (extended ray tracing)

Lightweight ctypes wrapper around `libwrxapi.so`. See L-7 plan for full docs.

## Quick start
\`\`\`python
from wrxlib import WrxLib
with WrxLib() as wrx:
    wrx.set_param('NRAYMAX', 8)
    wrx.run()
    pwr = wrx.get_state('pwr_profile', size=101)
\`\`\`

## Library lookup
By default, looks for `libwrxapi.so` in `task/wrx/` then `task/lib/`. Override
with `WRX_LIB_PATH` env var (planned for L-7).
```

## 完了基準
- [ ] `python -m unittest discover python/wrxlib/tests` が PASS
- [ ] `WrxLib` で init→run→get_state→finalize が成立（L-6 で本格検証）
- [ ] **ライブラリ衝突なし**: `python -c "import wrlib; import wrxlib; print('ok')"` が両方ロードできる

## 撤退条件
- ctypes で `libwrxapi.so` がロードできない場合 → L-4 設計変更（symbol scope, RTLD_GLOBAL 等）に戻る
- `wrlib` との Python 名前空間衝突が見つかった場合 → 別パッケージ名（`taskwrx`）に変更を検討

## 依存
- L-4 完了（`libwrxapi.so` 存在）
- numpy（既存環境前提）
- Python 3.8+ （type hints, dataclass）
