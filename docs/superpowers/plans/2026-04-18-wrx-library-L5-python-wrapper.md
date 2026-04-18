# WRX ライブラリ化 Phase L-5: Python ラッパ (`python/wrxlib/`) 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-4 で出来た `libwrxapi.so` を Python から自然に使える形にする。`python/wrxlib/` パッケージを新設し、ctypes で C ABI を呼ぶ低レベル `_ffi.py` と、Pythonic な `WrxLib` クラスを提供する `wrxlib.py` の 2 層構成にする。`with WrxLib() as wrx: ... ` パターンと辞書一括セット (`wrx.set_params(RR=6.2, BB=5.3)`) を提供。**`wrlib`（sister wr L-5）と完全並列**で、struct 一発取得 (`wrx_get_state(POINTER(WrxStateC))`) + 単一スカラー setter (`wrx_set_param(name, double)`) という L-2 確定 ABI に合わせる。

**Architecture:** sister wr L-5 と同じ 2 層構成（`_ffi.py` + `wrxlib.py`）。`state.py` で `wrx_state_c` を Python `dataclass` に変換し、`numpy` のオプション依存（あれば numpy 配列、無ければ Python list）。`errors.py` で L-2 の error code (`0=OK, 1=INVALID_PARAM, 2=NOT_INITIALIZED, 3=CALC_FAILED, 4=NOT_IMPLEMENTED`) と 1:1 対応する例外階層 (`WrxlibInvalidParam`, `WrxlibNotInitialized`, `WrxlibCalculationFailed`, `WrxlibNotImplemented`)。標準ライブラリのみで動かすが、numpy が import 出来れば自動的に numpy 配列を返す（テストは標準ライブラリ unittest）。

**Tech Stack:** Python 3.8+, `ctypes`, `dataclasses`（標準ライブラリ）, `numpy`（任意）, unittest。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 6 と Phase L-5（wr 版を wrx 用に翻案）。

---

## 既存 Python レイアウト

`python/` ディレクトリは sister wr L-5 が先行していれば既に存在し、`python/wrlib/` がある可能性がある。`ls /home/k-yoshimi/program/task/python/` で確認し、無ければ新規作成。**`wrlib` ≠ `wrxlib`** — Python パッケージ名は明確に分離する（C ABI シンボルも `wr_*` ≠ `wrx_*` で衝突しない）。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/__init__.py` | 新規（無ければ） | top-level package marker |
| `python/wrxlib/__init__.py` | 新規 | `from .wrxlib import WrxLib`, `from .errors import ...`, `from .state import WrxState` |
| `python/wrxlib/_ffi.py` | 新規 | ctypes 低レベル FFI: `load_lib(path)`, prototypes, `WrxStateC` ctypes Structure |
| `python/wrxlib/state.py` | 新規 | `WrxState` dataclass: scalars / arrays を Python 側で見やすい形に |
| `python/wrxlib/wrxlib.py` | 新規 | `WrxLib` class: context manager, set_param/set_params/run/get_state |
| `python/wrxlib/errors.py` | 新規 | 例外階層 + `raise_for_ierr` |
| `python/wrxlib/tests/__init__.py` | 新規 | empty |
| `python/wrxlib/tests/test_ffi.py` | 新規 | ctypes 直叩きテスト |
| `python/wrxlib/tests/test_wrxlib.py` | 新規 | WrxLib class テスト |
| `python/wrxlib/README.md` | 新規 | 使用例とインストール手順（L-7 で詳細化、本フェーズは雛形のみ） |

**方針:**
- `numpy` は **オプション**: 未インストールなら Python list を返す。`import numpy as np` を try/except で囲む。
- 既定で `WRXLIB_PATH` 環境変数からライブラリパスを取得、なければ `<repo>/wrx/libwrxapi.so` を相対パスで探す（その後 `<repo>/lib/libwrxapi.so`）。
- 例外は `WrxlibError` を基底クラスとして 4 種: `WrxlibInvalidParam` (ierr=1), `WrxlibNotInitialized` (ierr=2), `WrxlibCalculationFailed` (ierr=3), `WrxlibNotImplemented` (ierr=4)。

---

## Task 1: ブランチ作成と初期構造

**Files:**
- Create: `python/__init__.py`（既存なら touch のみ）
- Create: `python/wrxlib/__init__.py`
- Create: `python/wrxlib/tests/__init__.py`

- [ ] **Step 1: develop 最新 + ブランチ作成**

Run:
```bash
cd /home/k-yoshimi/program/task
git checkout develop
git pull origin develop
git checkout -b feature/wrx-library-L5-python
```

- [ ] **Step 2: ディレクトリ作成**

Run:
```bash
mkdir -p /home/k-yoshimi/program/task/python/wrxlib/tests
```

- [ ] **Step 3: 空マーカー作成**

Create `/home/k-yoshimi/program/task/python/__init__.py` (empty file, 既存なら触らない).
Create `/home/k-yoshimi/program/task/python/wrxlib/__init__.py`:
```python
"""TASK/WRX Python wrapper (Phase L-5)."""
from .wrxlib import WrxLib
from .state import WrxState
from .errors import (
    WrxlibError,
    WrxlibNotInitialized,
    WrxlibInvalidParam,
    WrxlibCalculationFailed,
    WrxlibNotImplemented,
)

__all__ = [
    "WrxLib", "WrxState",
    "WrxlibError", "WrxlibNotInitialized",
    "WrxlibInvalidParam", "WrxlibCalculationFailed",
    "WrxlibNotImplemented",
]
__version__ = "0.1.0"
```

Create `/home/k-yoshimi/program/task/python/wrxlib/tests/__init__.py` (empty file).

- [ ] **Step 4: マーカーコミット（このコミットは __init__.py のみで動かない、後続コミットで成立させる）**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrxlib/__init__.py python/wrxlib/tests/__init__.py
test -f python/__init__.py || git add python/__init__.py
git commit -m "chore(wrxlib): scaffold python/wrxlib package"
```

---

## Task 2: `errors.py` を実装

**Files:**
- Create: `python/wrxlib/errors.py`

L-2 で確定したエラーコードに 1:1 対応させる:
| ierr | 意味 | 例外 |
|---|---|---|
| 0 | OK | (raise しない) |
| 1 | invalid parameter (unknown name / out-of-range index) | `WrxlibInvalidParam` |
| 2 | not initialized (`wrx_init` 未呼出 / `wrx_finalize` 後) | `WrxlibNotInitialized` |
| 3 | calculation failed (`wr_prep`/`wr_setup`/`wr_exec` 内部失敗) | `WrxlibCalculationFailed` |
| 4 | not implemented yet (L-2 stub 段階) | `WrxlibNotImplemented` |

- [ ] **Step 1: 例外階層を実装**

Create `/home/k-yoshimi/program/task/python/wrxlib/errors.py`:
```python
"""Exception hierarchy for the wrxlib package.

Mirrors the C ABI error codes defined in wrx/wrx_api.h:
  0 = OK, 1 = INVALID_PARAM, 2 = NOT_INITIALIZED,
  3 = CALC_FAILED, 4 = NOT_IMPLEMENTED.
"""
import enum


class ErrorCode(enum.IntEnum):
    OK              = 0
    INVALID_PARAM   = 1
    NOT_INITIALIZED = 2
    CALC_FAILED     = 3
    NOT_IMPLEMENTED = 4


class WrxlibError(Exception):
    """Base class for all wrxlib errors."""

    def __init__(self, message: str, ierr: int = -1):
        super().__init__(message)
        self.ierr = ierr


class WrxlibInvalidParam(WrxlibError):
    """C ABI returned ierr=1 (unknown name or out-of-range index)."""

    def __init__(self, name: str):
        super().__init__(f"invalid parameter: {name}", ierr=1)
        self.name = name


class WrxlibNotInitialized(WrxlibError):
    """C ABI returned ierr=2 (called before wrx_init or after wrx_finalize)."""

    def __init__(self):
        super().__init__("wrxlib not initialized; call wrx_init() first", ierr=2)


class WrxlibCalculationFailed(WrxlibError):
    """C ABI returned ierr=3 (wr_prep / wr_setup / wr_exec reported failure)."""

    def __init__(self, hint: str = ""):
        msg = "wrxlib calculation failed"
        if hint:
            msg = f"{msg}: {hint}"
        super().__init__(msg, ierr=3)


class WrxlibNotImplemented(WrxlibError):
    """C ABI returned ierr=4 (L-2 stub returned 'not implemented yet')."""

    def __init__(self, hint: str = ""):
        msg = "wrxlib feature not implemented"
        if hint:
            msg = f"{msg}: {hint}"
        super().__init__(msg, ierr=4)


def raise_for_ierr(ierr: int, *, name: str = "", hint: str = "") -> None:
    """Map a non-zero ierr to the appropriate exception."""
    if ierr == 0:
        return
    if ierr == 1:
        raise WrxlibInvalidParam(name)
    if ierr == 2:
        raise WrxlibNotInitialized()
    if ierr == 3:
        raise WrxlibCalculationFailed(hint)
    if ierr == 4:
        raise WrxlibNotImplemented(hint)
    raise WrxlibError(f"unknown error code from libwrxapi.so: {ierr}", ierr=ierr)
```

- [ ] **Step 2: 軽い構文チェック**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -c "from python.wrxlib.errors import WrxlibInvalidParam, raise_for_ierr; \
            raise_for_ierr(1, name='RR')"
```
Expected: `python.wrxlib.errors.WrxlibInvalidParam: invalid parameter: RR` を raise。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrxlib/errors.py
git commit -m "feat(wrxlib): add exception hierarchy mapped to L-2 error codes"
```

---

## Task 3: `state.py` を実装

**Files:**
- Create: `python/wrxlib/state.py`

`wrx_state_c` 構造体（L-2 確定）の Python 側ビュー。1D 配列は active range にスライス（fixed-size struct のゼロ詰め leak を防ぐ）。

- [ ] **Step 1: dataclass を定義**

Create `/home/k-yoshimi/program/task/python/wrxlib/state.py`:
```python
"""Python-friendly view of wrx_state_t."""
from dataclasses import dataclass, field
from typing import Any, List

try:
    import numpy as np  # type: ignore
    _HAVE_NUMPY = True
except ImportError:
    np = None  # type: ignore
    _HAVE_NUMPY = False


def _to_array(seq):
    if _HAVE_NUMPY:
        return np.asarray(seq, dtype=float)
    return list(seq)


@dataclass
class WrxState:
    """High-level view of wrx_state_t.

    Dimensions match the active runtime values; arrays are sliced to the
    active range (no zero-padding leak from the fixed-size C struct).
    Field names mirror the C struct (lowercase) defined in wrx/wrx_api.h.
    """
    nraymax: int
    nstpmax: int
    nsamax:  int
    nsmax:   int
    modelg:  int
    mdlwrq:  int
    pwr_tot: float
    nstp_end:           List[int] = field(default_factory=list)  # alias of nstpmax_nray
    pwr_nray:           Any = None
    pwr_nsa:            Any = None
    pwr_nsa_nray:       Any = None  # shape (nsamax, nraymax) - Fortran column-major
    pos_pwrmax_rs_nsa:  Any = None
    pwrmax_rs_nsa:      Any = None
    pos_pwrmax_rl_nsa:  Any = None
    pwrmax_rl_nsa:      Any = None

    @classmethod
    def from_c(cls, c_state) -> "WrxState":
        """Convert a ctypes WrxStateC struct to a WrxState dataclass.

        Slicing to active dims protects against zero-padding leaking from the
        fixed-size struct (WRX_MAX_NRAYMAX, WRX_MAX_NSAMAX upper bounds).
        """
        nr = int(c_state.nraymax)
        ns = int(c_state.nsamax)
        # 2D array: ctypes layout is c_state.pwr_nsa_nray[nray][nsa]
        # because the Fortran (NSAMAX, NRAYMAX) becomes C [NRAYMAX][NSAMAX]
        # under column-major-to-row-major bit-equivalence (see wrx_api.h note).
        if nr > 0 and ns > 0:
            mat2d = [
                [float(c_state.pwr_nsa_nray[j][k]) for k in range(ns)]
                for j in range(nr)
            ]
            if _HAVE_NUMPY:
                pwr_nsa_nray_arr = np.asarray(mat2d, dtype=float)
            else:
                pwr_nsa_nray_arr = mat2d
        else:
            pwr_nsa_nray_arr = _to_array([])

        return cls(
            nraymax=nr,
            nstpmax=int(c_state.nstpmax),
            nsamax =ns,
            nsmax  =int(c_state.nsmax),
            modelg =int(c_state.modelg),
            mdlwrq =int(c_state.mdlwrq),
            pwr_tot=float(c_state.pwr_tot),
            nstp_end=[int(c_state.nstpmax_nray[j]) for j in range(nr)],
            pwr_nray=_to_array([c_state.pwr_nray[j] for j in range(nr)]),
            pwr_nsa =_to_array([c_state.pwr_nsa[j]  for j in range(ns)]),
            pwr_nsa_nray=pwr_nsa_nray_arr,
            pos_pwrmax_rs_nsa=_to_array([c_state.pos_pwrmax_rs_nsa[j] for j in range(ns)]),
            pwrmax_rs_nsa    =_to_array([c_state.pwrmax_rs_nsa[j]     for j in range(ns)]),
            pos_pwrmax_rl_nsa=_to_array([c_state.pos_pwrmax_rl_nsa[j] for j in range(ns)]),
            pwrmax_rl_nsa    =_to_array([c_state.pwrmax_rl_nsa[j]     for j in range(ns)]),
        )
```

- [ ] **Step 2: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrxlib/state.py
git commit -m "feat(wrxlib): add WrxState dataclass with C-struct adapter"
```

---

## Task 4: `_ffi.py` を実装

**Files:**
- Create: `python/wrxlib/_ffi.py`

L-2 の `wrx_state_c` Fortran 構造体・`wrx_api.h` 宣言と完全に同じレイアウトの `WrxStateC` ctypes Structure を定義する。サイズと field 順は C ヘッダと bit-exact に揃える（後で `ctypes.sizeof(WrxStateC)` を `wrx_api.h` 由来の sizeof と突合）。

- [ ] **Step 1: ctypes Structure と関数プロトタイプ**

Create `/home/k-yoshimi/program/task/python/wrxlib/_ffi.py`:
```python
"""ctypes-level FFI for libwrxapi.so.

Mirror of wrx/wrx_api.h. WRX_MAX_NRAYMAX, WRX_MAX_NSAMAX must match the
values in the header (L-2).
"""
import ctypes
import os
from pathlib import Path

WRX_MAX_NRAYMAX = 100
WRX_MAX_NSAMAX  = 8


class WrxStateC(ctypes.Structure):
    # Fields are listed in the same order as wrx_state_t in wrx/wrx_api.h
    # so that ctypes.sizeof(WrxStateC) matches the C struct exactly.
    _fields_ = [
        ("nraymax",            ctypes.c_int),
        ("nstpmax",            ctypes.c_int),
        ("nsamax",             ctypes.c_int),
        ("nsmax",              ctypes.c_int),
        ("modelg",             ctypes.c_int),
        ("mdlwrq",             ctypes.c_int),
        ("pwr_tot",            ctypes.c_double),
        ("nstpmax_nray",       ctypes.c_int    * WRX_MAX_NRAYMAX),
        ("pwr_nray",           ctypes.c_double * WRX_MAX_NRAYMAX),
        ("pwr_nsa",            ctypes.c_double * WRX_MAX_NSAMAX),
        # Fortran (NSAMAX, NRAYMAX) == C [NRAYMAX][NSAMAX] under
        # column-major-to-row-major bit equivalence (see wrx_api.h note).
        ("pwr_nsa_nray",       (ctypes.c_double * WRX_MAX_NSAMAX) * WRX_MAX_NRAYMAX),
        ("pos_pwrmax_rs_nsa",  ctypes.c_double * WRX_MAX_NSAMAX),
        ("pwrmax_rs_nsa",      ctypes.c_double * WRX_MAX_NSAMAX),
        ("pos_pwrmax_rl_nsa",  ctypes.c_double * WRX_MAX_NSAMAX),
        ("pwrmax_rl_nsa",      ctypes.c_double * WRX_MAX_NSAMAX),
    ]


def _default_lib_path() -> Path:
    """Find libwrxapi.so. Priority: WRXLIB_PATH env > <repo>/wrx > <repo>/lib."""
    env = os.environ.get("WRXLIB_PATH")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    # python/wrxlib/_ffi.py -> python/wrxlib -> python -> repo root
    repo_root = here.parents[2]
    for cand in (repo_root / "wrx" / "libwrxapi.so",
                 repo_root / "lib" / "libwrxapi.so"):
        if cand.exists():
            return cand
    return repo_root / "wrx" / "libwrxapi.so"  # for the error message


def load_lib(path: Path = None) -> ctypes.CDLL:
    """Load libwrxapi.so and configure prototypes."""
    if path is None:
        path = _default_lib_path()
    if not Path(path).exists():
        raise FileNotFoundError(
            f"libwrxapi.so not found at {path}. Build with `make libwrxapi.so` "
            f"in wrx/, or set WRXLIB_PATH env var."
        )
    lib = ctypes.CDLL(str(path))

    lib.wrx_init.argtypes = []
    lib.wrx_init.restype  = ctypes.c_int

    lib.wrx_run.argtypes = [ctypes.c_int]
    lib.wrx_run.restype  = ctypes.c_int

    # L-2 confirmed signature: const char* name, double value (single scalar).
    lib.wrx_set_param.argtypes = [ctypes.c_char_p, ctypes.c_double]
    lib.wrx_set_param.restype  = ctypes.c_int

    # L-2 confirmed signature: takes a pointer to caller-allocated wrx_state_t.
    lib.wrx_get_state.argtypes = [ctypes.POINTER(WrxStateC)]
    lib.wrx_get_state.restype  = ctypes.c_int

    lib.wrx_finalize.argtypes = []
    lib.wrx_finalize.restype  = ctypes.c_int
    return lib
```

- [ ] **Step 2: 軽い import チェック**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -c "from python.wrxlib._ffi import WrxStateC; import ctypes; \
            print(ctypes.sizeof(WrxStateC), 'bytes')"
```
Expected: 数千バイト程度の数値（`6*4 + 8 + 100*4 + 100*8 + 8*8 + 100*8*8 + 4*8*8` ≒ 8 KB 強）。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrxlib/_ffi.py
git commit -m "feat(wrxlib): add ctypes FFI (_ffi.py) with WrxStateC mirroring L-2 ABI"
```

---

## Task 5: `wrxlib.py`（高レベル class）を実装

**Files:**
- Create: `python/wrxlib/wrxlib.py`

sister wr `Wrlib` と同じパターン: context manager / `set_param(name, value)` / `set_params(**kwargs)` / `run(nstpmax=0)` / `get_state() -> WrxState`。

- [ ] **Step 1: WrxLib class を実装**

Create `/home/k-yoshimi/program/task/python/wrxlib/wrxlib.py`:
```python
"""High-level WrxLib API."""
from pathlib import Path
from typing import Optional

from . import _ffi
from .errors import raise_for_ierr, WrxlibError
from .state import WrxState


class WrxLib:
    """Pythonic interface to libwrxapi.so.

    Usage:
        with WrxLib() as wrx:
            wrx.set_params(MODELG=2, RR=6.2, BB=5.3, NSMAX=2)
            wrx.set_param("RFIN[1]", 5.0e3)
            wrx.run(nstpmax=0)        # 0 = use whatever NSTPMAX is set to
            state = wrx.get_state()
            print(state.pwr_tot, state.pwrmax_rl_nsa.sum())
    """

    def __init__(self, lib_path: Optional[Path] = None):
        self._lib = _ffi.load_lib(lib_path)
        self._initialized = False
        self._executed = False

    # ---- lifecycle ----
    def open(self) -> "WrxLib":
        ierr = self._lib.wrx_init()
        raise_for_ierr(ierr)
        self._initialized = True
        return self

    def close(self) -> None:
        if self._initialized:
            ierr = self._lib.wrx_finalize()
            self._initialized = False
            self._executed = False
            raise_for_ierr(ierr)

    def __enter__(self) -> "WrxLib":
        return self.open()

    def __exit__(self, exc_type, exc_val, tb) -> None:
        self.close()

    # ---- parameter setting (single scalar at a time, per L-2 ABI) ----
    def set_param(self, name: str, value: float) -> None:
        ierr = self._lib.wrx_set_param(name.encode("utf-8"), float(value))
        raise_for_ierr(ierr, name=name)

    def set_params(self, **kwargs) -> None:
        for k, v in kwargs.items():
            self.set_param(k, v)

    # ---- run / get_state ----
    def run(self, nstpmax: int = 0) -> None:
        """Execute WRX. nstpmax=0 means: use the current NSTPMAX value
        (set via set_param("NSTPMAX", ...) or kept at the wrx_init default)."""
        ierr = self._lib.wrx_run(int(nstpmax))
        raise_for_ierr(ierr, hint="wrx_run")
        self._executed = True

    def get_state(self) -> WrxState:
        if not self._executed:
            raise WrxlibError("get_state() called before run()", ierr=2)
        c_state = _ffi.WrxStateC()
        ierr = self._lib.wrx_get_state(c_state)
        raise_for_ierr(ierr, hint="wrx_get_state")
        return WrxState.from_c(c_state)
```

- [ ] **Step 2: import チェック**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -c "from python.wrxlib import WrxLib; print(WrxLib)"
```
Expected: `<class 'python.wrxlib.wrxlib.WrxLib'>` 等が表示。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrxlib/wrxlib.py
git commit -m "feat(wrxlib): add high-level WrxLib class with context manager"
```

---

## Task 6: 軽量 unittest を追加

**Files:**
- Create: `python/wrxlib/tests/test_ffi.py`
- Create: `python/wrxlib/tests/test_wrxlib.py`

- [ ] **Step 1: ctypes 直叩き smoke test**

Create `/home/k-yoshimi/program/task/python/wrxlib/tests/test_ffi.py`:
```python
"""Low-level ctypes FFI tests (require libwrxapi.so to be built)."""
import ctypes
import os
import unittest
from pathlib import Path

from python.wrxlib import _ffi


def _lib_path() -> Path:
    env = os.environ.get("WRXLIB_PATH")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    return here.parents[3] / "wrx" / "libwrxapi.so"


@unittest.skipUnless(_lib_path().exists(), "libwrxapi.so not built")
class TestFfi(unittest.TestCase):
    def setUp(self):
        self.lib = _ffi.load_lib(_lib_path())

    def tearDown(self):
        self.lib.wrx_finalize()

    def test_init_finalize(self):
        self.assertEqual(self.lib.wrx_init(), 0)
        self.assertEqual(self.lib.wrx_init(), 0)  # idempotent
        self.assertEqual(self.lib.wrx_finalize(), 0)
        # After finalize, set_param should return 2 (not initialized).
        self.assertEqual(self.lib.wrx_set_param(b"RR", 6.2), 2)

    def test_set_param_invalid_name(self):
        self.assertEqual(self.lib.wrx_init(), 0)
        self.assertEqual(self.lib.wrx_set_param(b"BOGUS_NAME", 0.0), 1)

    def test_get_state_before_run(self):
        self.assertEqual(self.lib.wrx_init(), 0)
        st = _ffi.WrxStateC()
        # Before wrx_run: L-3 returns ierr=2 (not run yet) per the
        # g_run_called guard. Earlier L-2 stub returned 4. Accept either
        # to keep the smoke test stable across L-2/L-3 transition.
        self.assertIn(self.lib.wrx_get_state(ctypes.byref(st)), (2, 4))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: WrxLib class テスト**

Create `/home/k-yoshimi/program/task/python/wrxlib/tests/test_wrxlib.py`:
```python
"""High-level WrxLib class tests (require libwrxapi.so to be built)."""
import os
import unittest
from pathlib import Path

from python.wrxlib import (
    WrxLib, WrxlibInvalidParam, WrxState,
)


def _lib_path() -> Path:
    env = os.environ.get("WRXLIB_PATH")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    return here.parents[3] / "wrx" / "libwrxapi.so"


def _setup_iter_eccd(wrx: WrxLib) -> None:
    """Mirror of test_run/inputs/wrx_iter01.in (small NRAYMAX for speed)."""
    wrx.set_params(MODELG=2, RR=6.2, RA=2.0, BB=5.3, NSMAX=2,
                   NRAYMAX=1, NSTPMAX=2000, MDLWRI=2, MDLWRQ=1,
                   SMAX=2.0, DELS=1e-3)
    for i, (pa, pz, pn, pns, pt, pts) in enumerate([
            (2.0, 1.0, 1.0, 0.05, 10.0, 0.5),
            (5.4462e-4, -1.0, 1.0, 0.05, 10.0, 0.5)], start=1):
        wrx.set_param(f"PA[{i}]",   pa)
        wrx.set_param(f"PZ[{i}]",   pz)
        wrx.set_param(f"PN[{i}]",   pn)
        wrx.set_param(f"PNS[{i}]",  pns)
        wrx.set_param(f"PTPR[{i}]", pt); wrx.set_param(f"PTPP[{i}]", pt)
        wrx.set_param(f"PTS[{i}]",  pts)
    wrx.set_params(**{"RFIN[1]": 170.0e3, "RPIN[1]": 8.0, "ZPIN[1]": 0.0,
                      "PHIIN[1]": 0.0, "ANGPIN[1]": 0.0, "ANGTIN[1]": 10.0,
                      "UUIN[1]": 1.0, "MODEWIN[1]": 1})


@unittest.skipUnless(_lib_path().exists(), "libwrxapi.so not built")
class TestWrxLib(unittest.TestCase):
    def test_context_manager(self):
        with WrxLib(lib_path=_lib_path()) as wrx:
            self.assertIsInstance(wrx, WrxLib)

    def test_invalid_param_raises(self):
        with WrxLib(lib_path=_lib_path()) as wrx:
            with self.assertRaises(WrxlibInvalidParam):
                wrx.set_param("BOGUS_NAME", 0.0)

    def test_get_state_before_run_raises(self):
        with WrxLib(lib_path=_lib_path()) as wrx:
            with self.assertRaises(Exception):
                wrx.get_state()

    def test_iter_eccd_run(self):
        with WrxLib(lib_path=_lib_path()) as wrx:
            _setup_iter_eccd(wrx)
            wrx.run(nstpmax=0)
            st = wrx.get_state()
            self.assertIsInstance(st, WrxState)
            self.assertEqual(st.nraymax, 1)
            self.assertGreater(st.nsamax, 0)
            self.assertEqual(len(st.nstp_end), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: テスト実行**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest python.wrxlib.tests.test_ffi python.wrxlib.tests.test_wrxlib -v
```
Expected:
- `libwrxapi.so` が存在しない場合は全テスト skipped。
- 存在する場合は全 PASS。

- [ ] **Step 4: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrxlib/tests/test_ffi.py python/wrxlib/tests/test_wrxlib.py
git commit -m "test(wrxlib): add unittest-based ffi/class tests"
```

---

## Task 7: 簡易 README（雛形のみ、L-7 で本体）

**Files:**
- Create: `python/wrxlib/README.md`

- [ ] **Step 1: 最小 README**

Create `/home/k-yoshimi/program/task/python/wrxlib/README.md`:
```markdown
# wrxlib — Python wrapper for TASK/WRX (extended ray tracing)

Phase L-5 minimum viable package. Full documentation lands in L-7.

## Quick start

```bash
cd /path/to/task/wrx && make libwrxapi.so
cd /path/to/task
python3 -c "
from python.wrxlib import WrxLib
with WrxLib() as wrx:
    wrx.set_params(MODELG=2, RR=6.2, BB=5.3, NSMAX=2,
                   NRAYMAX=1, NSTPMAX=2000, MDLWRI=2)
    wrx.set_param('RFIN[1]', 170.0e3)
    wrx.run(0)
    st = wrx.get_state()
    print(st.pwr_tot, st.pwrmax_rl_nsa)
"
```

## Library lookup

`WRXLIB_PATH` env var > `<repo>/wrx/libwrxapi.so` > `<repo>/lib/libwrxapi.so`.

## Independence from `wrlib`

`wrlib` (sister wr Phase L-5 package) and `wrxlib` use distinct C symbol
prefixes (`wr_*` vs `wrx_*`) and distinct shared libraries
(`libwrapi.so` vs `libwrxapi.so`). They can coexist in the same Python
process without conflict.
```

- [ ] **Step 2: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrxlib/README.md
git commit -m "docs(wrxlib): add minimal README (Phase L-5 stub for L-7)"
```

---

## 完了基準

- [ ] `python/wrxlib/` パッケージが作られ、`from python.wrxlib import WrxLib` で import 可能
- [ ] `_ffi.py` の `WrxStateC` のサイズが `wrx_api.h` の `wrx_state_t` と一致（ctypes の sizeof で検証、L-6 で C 側 `sizeof(wrx_state_t)` と突合）
- [ ] `with WrxLib() as wrx: wrx.set_params(...).run(0).get_state()` が動く
- [ ] `set_param(name, value)` シグネチャが L-2 ABI と一致（**単一 double**、ポインタ＋size 形式は L-2 で却下されているため使わない）
- [ ] `get_state()` が `WrxState` dataclass を返し、`pos_pwrmax_rs_nsa` / `pwrmax_rs_nsa` / `pos_pwrmax_rl_nsa` / `pwrmax_rl_nsa` 4 フィールドが揃っている
- [ ] unittest 全件 PASS（`libwrxapi.so` 未ビルド時は skip）
- [ ] 例外階層が機能（`WrxlibInvalidParam, WrxlibNotInitialized, WrxlibCalculationFailed, WrxlibNotImplemented`）
- [ ] numpy のオプション依存：未インストールでも import 可能
- [ ] `wrlib` と同一 Python プロセスから両方 import 可能（`python3 -c "from python.wrlib import Wrlib; from python.wrxlib import WrxLib"`）

## 撤退条件

- ctypes の Structure サイズが C 側と合わない → `_fields_` の順序、padding、`WRX_MAX_*` 値を `wrx_api.h` と再確認
- `dlopen` で symbol not found → `WRXLIB_PATH` を絶対パスで指定し、`ldd` で依存解決を再確認
- numpy ありで配列形状が壊れる → `state.py` の `_to_array` を `dtype=float` 固定に
- `wrlib` と同時 import で SEGV → L-4 (PIC build) で `RTLD_LOCAL` か symbol scope を見直し

## 依存

- 前提: L-2/L-3 完了（`wrx_state_c` Fortran 構造体、5 関数 ABI、param registry）、L-4 完了（`wrx/libwrxapi.so` がビルド可能）
- 後続: L-6 (4 層テスト)、L-7 (README + notebook)
