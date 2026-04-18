# TOT Library Phase L-5: Python Wrapper `python/totlib/` 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phase L-4 で作った `libtotapi.so` を `ctypes` で呼ぶ Python パッケージ `python/totlib/` を実装し、Pythonic な `Totlib` class（context manager + dict 一括 set_param + numpy 化された state 取得）を提供する。L-7（パラメータ最適化）の入口となる。

**Architecture:** 既存 `python/trlib/` （TR の Phase L-5 で実装済み想定）と並列構成で、tot は **「個別モジュール Python wrapper を composing する高レベル API」** とする。`python/totlib/_ffi.py` は `libtotapi.so` の直接 ctypes バインディング、`python/totlib/totlib.py` は `Totlib` class（個別 wrapper の `python/trlib.Trlib` 等を内部に持たず、tot 自身の C ABI を直接叩く）。state は `dataclass` + numpy ndarray で表現。

**Tech Stack:** Python 3.8+, ctypes 標準ライブラリ, numpy（ndarray 化のため）, dataclasses, unittest（テスト）。新規依存なし（numpy は基本装備）。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 6（Python ラッパ設計）を tot 用に翻案。

**前提条件:** L-4 完了（`libtotapi.so` がビルド可能）。Python 3.8+ と numpy が利用できる環境。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/totlib/__init__.py` | 新規 | re-export `Totlib`, `TotState`, `TotlibError` |
| `python/totlib/_ffi.py` | 新規 | ctypes 低レベル FFI（`libtotapi.so` ロード、5 関数バインディング） |
| `python/totlib/state.py` | 新規 | `TotState` dataclass + `tot_state_t` ctypes Structure |
| `python/totlib/totlib.py` | 新規 | `Totlib` class（context manager, set_params, run, get_state） |
| `python/totlib/errors.py` | 新規 | `TotlibError`, `TotlibInvalidParamError`, `TotlibNotInitializedError` |
| `python/totlib/tests/__init__.py` | 新規 | 空 |
| `python/totlib/tests/test_ffi.py` | 新規 | 低レベル FFI のユニットテスト |
| `python/totlib/tests/test_class.py` | 新規 | `Totlib` クラスのユニットテスト |
| `python/totlib/README.md` | 新規 | 使用例、API リファレンス |

> **conftest.py は作成しない:** `_ffi.py` は import 時に `ctypes.CDLL` を呼ぶため、pytest fixture (`monkeypatch.setenv`) で `LD_LIBRARY_PATH` を上書きしても **既に手遅れ**（no-op）。代わりに各 Run コマンドでシェル env として `LD_LIBRARY_PATH` を渡す。

**方針:**
- 個別 Python wrapper (`python/trlib`, `python/tilib`, ...) を `Totlib` クラスの中で wrap しない（重複・循環の温床になる）。代わりに **tot 自身の C ABI 直叩き**で済ませる。個別 wrapper を使いたい場合は別途 `from trlib import Trlib` できる。
- パラメータ名は L-3 の prefix 形式 (`TR.RR`, `TI.X`, `EQ.RR` 等) をそのまま Python から渡す。
- `TotState` は per-module フィールド (`tr`, `ti_present`, `fp_present`, `wr_present`) を持つ。`tr` フィールドは numpy ndarray を含む（`RN`, `RT`, `AJ`, `QP`）。
- ライブラリパス解決は `TOTLIB_PATH` 環境変数 → `python/totlib/_ffi.py` 内のデフォルト相対パス (`../../tot/libtotapi.so`) の順。
- 例外階層: `TotlibError` < `TotlibInvalidParamError`, `TotlibNotInitializedError`, `TotlibCalculationError`。

---

## Task 1: ブランチ作成と前提確認

**Files:** なし

- [ ] **Step 1: ブランチ**

Run:
```bash
cd /home/k-yoshimi/program/task
git checkout develop && git pull
git checkout -b feature/tot-library-l5-python-wrapper
```

- [ ] **Step 2: `libtotapi.so` の存在確認**

Run:
```bash
ls -la /home/k-yoshimi/program/task/tot/libtotapi.so
nm -D /home/k-yoshimi/program/task/tot/libtotapi.so | grep -E "^[0-9a-f]+ T tot_"
```
Expected: `.so` が存在、5 シンボル全て公開。

- [ ] **Step 3: Python と numpy のバージョン確認**

Run:
```bash
python3 --version
python3 -c "import numpy; print(numpy.__version__)"
```
Expected: Python 3.8+, numpy 利用可能。

- [ ] **Step 4: 初期コミット**

Run:
```bash
git commit --allow-empty -m "chore(tot): start L-5 Python wrapper"
```

---

## Task 2: ディレクトリと空モジュール作成

**Files:**
- Create: `python/totlib/__init__.py`
- Create: `python/totlib/tests/__init__.py`

- [ ] **Step 1: ディレクトリ作成**

Run:
```bash
mkdir -p /home/k-yoshimi/program/task/python/totlib/tests
```

- [ ] **Step 2: `python/totlib/__init__.py` 作成**

作成: `python/totlib/__init__.py`

```python
"""totlib — Python in-process wrapper for the integrated TOT simulator.

Loads ``libtotapi.so`` and exposes ``Totlib``, ``TotState`` and the
exception hierarchy (``TotlibError`` and subclasses).
"""
from .totlib import Totlib
from .state import TotState
from .errors import (
    TotlibError,
    TotlibInvalidParamError,
    TotlibNotInitializedError,
    TotlibCalculationError,
)

__all__ = [
    "Totlib", "TotState",
    "TotlibError", "TotlibInvalidParamError",
    "TotlibNotInitializedError", "TotlibCalculationError",
]
```

- [ ] **Step 3: `python/totlib/tests/__init__.py` 作成（空ファイル）**

Run:
```bash
touch /home/k-yoshimi/program/task/python/totlib/tests/__init__.py
```

- [ ] **Step 4: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/totlib/__init__.py python/totlib/tests/__init__.py
git commit -m "feat(totlib): scaffold python package skeleton"
```

---

## Task 3: `errors.py` を作成

**Files:**
- Create: `python/totlib/errors.py`

- [ ] **Step 1: 例外階層を作成**

作成: `python/totlib/errors.py`

```python
"""Exception hierarchy for totlib.

ABI return codes mapping:
    0 -> success (no exception)
    1 -> TotlibInvalidParamError
    2 -> TotlibNotInitializedError
    3 -> TotlibCalculationError
"""


class TotlibError(Exception):
    """Base class for all totlib exceptions."""

    def __init__(self, message: str, *, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class TotlibInvalidParamError(TotlibError):
    """Returned when a parameter name is unknown or value is rejected."""


class TotlibNotInitializedError(TotlibError):
    """Returned when an API call is made before tot_init or after tot_finalize."""


class TotlibCalculationError(TotlibError):
    """Returned when a per-module calculation fails inside tot_run."""


def raise_for_code(code: int, *, context: str) -> None:
    """Translate an ABI return code into a typed exception.

    A return code of 0 is a no-op. Anything else raises.
    """
    if code == 0:
        return
    if code == 1:
        raise TotlibInvalidParamError(f"{context}: invalid parameter (code=1)", code=code)
    if code == 2:
        raise TotlibNotInitializedError(f"{context}: not initialized (code=2)", code=code)
    if code == 3:
        raise TotlibCalculationError(f"{context}: calculation failed (code=3)", code=code)
    raise TotlibError(f"{context}: unknown error (code={code})", code=code)
```

- [ ] **Step 2: コミット**

Run:
```bash
git add python/totlib/errors.py
git commit -m "feat(totlib): add error hierarchy"
```

---

## Task 4: `state.py` を作成（`TotState` dataclass + ctypes struct）

**Files:**
- Create: `python/totlib/state.py`

- [ ] **Step 1: 新規作成**

作成: `python/totlib/state.py`

```python
"""TOT state representation.

TR_State_C / TOT_State_C mirror the Fortran BIND(C) types defined in
tr/tr_state.f90 and tot/tot_state.f90. After tot_get_state populates
the C struct, we convert it into a numpy-friendly TotState dataclass
for ergonomic access from user code.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass, field
import numpy as np

# Upper bounds — must match tr/tr_api.h.
TR_MAX_NRMAX = 500
TR_MAX_NSMAX = 8


class TrStateC(ctypes.Structure):
    """C-layout copy of the tr_state_c BIND(C) type."""

    _fields_ = [
        ("nt", ctypes.c_int),
        ("nrmax", ctypes.c_int),
        ("nsmax", ctypes.c_int),
        ("T", ctypes.c_double),
        ("WPT", ctypes.c_double),
        ("AJT", ctypes.c_double),
        ("Q0", ctypes.c_double),
        ("BETA0", ctypes.c_double),
        ("BETAP0", ctypes.c_double),
        ("BETAA", ctypes.c_double),
        ("BETAN", ctypes.c_double),
        ("TAUE1", ctypes.c_double),
        ("TAUE2", ctypes.c_double),
        ("ZEFF0", ctypes.c_double),
        ("ALI", ctypes.c_double),
        ("RQ1", ctypes.c_double),
        ("RN", (ctypes.c_double * TR_MAX_NSMAX) * TR_MAX_NRMAX),
        ("RT", (ctypes.c_double * TR_MAX_NSMAX) * TR_MAX_NRMAX),
        ("AJ", ctypes.c_double * TR_MAX_NRMAX),
        ("QP", ctypes.c_double * TR_MAX_NRMAX),
    ]


class TotStateC(ctypes.Structure):
    """C-layout copy of tot_state_c."""

    _fields_ = [
        ("tr_present", ctypes.c_int),
        ("ti_present", ctypes.c_int),
        ("fp_present", ctypes.c_int),
        ("wr_present", ctypes.c_int),
        ("tr", TrStateC),
        ("ti_placeholder", ctypes.c_int),
        ("fp_placeholder", ctypes.c_int),
        ("wr_placeholder", ctypes.c_int),
    ]


@dataclass
class TrState:
    """Pythonic TR sub-state (with numpy arrays sliced to actual size)."""

    nt: int
    nrmax: int
    nsmax: int
    T: float
    WPT: float
    AJT: float
    Q0: float
    BETA0: float
    BETAP0: float
    BETAA: float
    BETAN: float
    TAUE1: float
    TAUE2: float
    ZEFF0: float
    ALI: float
    RQ1: float
    RN: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))
    RT: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))
    AJ: np.ndarray = field(default_factory=lambda: np.empty(0))
    QP: np.ndarray = field(default_factory=lambda: np.empty(0))

    @classmethod
    def from_c(cls, c: TrStateC) -> "TrState":
        nr, ns = c.nrmax, c.nsmax
        rn = np.frombuffer(c.RN, dtype=np.float64).reshape(TR_MAX_NRMAX, TR_MAX_NSMAX)[:nr, :ns].copy()
        rt = np.frombuffer(c.RT, dtype=np.float64).reshape(TR_MAX_NRMAX, TR_MAX_NSMAX)[:nr, :ns].copy()
        aj = np.frombuffer(c.AJ, dtype=np.float64)[:nr].copy()
        qp = np.frombuffer(c.QP, dtype=np.float64)[:nr].copy()
        return cls(
            nt=c.nt, nrmax=nr, nsmax=ns,
            T=c.T, WPT=c.WPT, AJT=c.AJT, Q0=c.Q0,
            BETA0=c.BETA0, BETAP0=c.BETAP0, BETAA=c.BETAA, BETAN=c.BETAN,
            TAUE1=c.TAUE1, TAUE2=c.TAUE2, ZEFF0=c.ZEFF0,
            ALI=c.ALI, RQ1=c.RQ1,
            RN=rn, RT=rt, AJ=aj, QP=qp,
        )


@dataclass
class TotState:
    """Pythonic snapshot of the integrated tot state."""

    tr_present: bool
    ti_present: bool
    fp_present: bool
    wr_present: bool
    tr: TrState | None
    # ti/fp/wr sub-states will be added in L-6 once their C ABIs supply richer data.

    @classmethod
    def from_c(cls, c: TotStateC) -> "TotState":
        tr = TrState.from_c(c.tr) if c.tr_present else None
        return cls(
            tr_present=bool(c.tr_present),
            ti_present=bool(c.ti_present),
            fp_present=bool(c.fp_present),
            wr_present=bool(c.wr_present),
            tr=tr,
        )
```

- [ ] **Step 2: コミット**

Run:
```bash
git add python/totlib/state.py
git commit -m "feat(totlib): add TotState dataclass and ctypes layouts"
```

---

## Task 5: `_ffi.py` を作成（ctypes 低レベルバインディング）

**Files:**
- Create: `python/totlib/_ffi.py`

- [ ] **Step 1: 新規作成**

作成: `python/totlib/_ffi.py`

```python
"""Low-level ctypes FFI to libtotapi.so.

This module is intentionally thin: each function is just a typed wrapper
around the C ABI. All higher-level conveniences (dict set, context
manager, exception mapping) live in totlib.py.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path

from .state import TotStateC


def _candidate_paths() -> list[Path]:
    """Locations to try (in order) when locating libtotapi.so."""
    here = Path(__file__).resolve().parent
    env = os.environ.get("TOTLIB_PATH")
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env))
    # Default: developer build in repo
    candidates.append(here.parents[1] / "tot" / "libtotapi.so")
    candidates.append(Path("/usr/local/lib/libtotapi.so"))
    return candidates


def _load_library() -> ctypes.CDLL:
    last_err: Exception | None = None
    for p in _candidate_paths():
        try:
            return ctypes.CDLL(str(p))
        except OSError as e:
            last_err = e
    raise OSError(
        f"libtotapi.so not found. Set TOTLIB_PATH or build it. last error: {last_err}"
    )


_lib = _load_library()


# ---- function prototypes (mirror tot_api.h) ---------------------------

_lib.tot_init.restype = ctypes.c_int
_lib.tot_init.argtypes = []

_lib.tot_run.restype = ctypes.c_int
_lib.tot_run.argtypes = [ctypes.c_int]

_lib.tot_get_state.restype = ctypes.c_int
_lib.tot_get_state.argtypes = [ctypes.POINTER(TotStateC)]

_lib.tot_set_param.restype = ctypes.c_int
_lib.tot_set_param.argtypes = [ctypes.c_char_p, ctypes.c_double]

_lib.tot_finalize.restype = ctypes.c_int
_lib.tot_finalize.argtypes = []


# ---- thin Python wrappers ---------------------------------------------

def tot_init() -> int:
    return _lib.tot_init()


def tot_run(ntmax: int) -> int:
    return _lib.tot_run(int(ntmax))


def tot_get_state() -> tuple[int, TotStateC]:
    state = TotStateC()
    rc = _lib.tot_get_state(ctypes.byref(state))
    return rc, state


def tot_set_param(name: str, value: float) -> int:
    return _lib.tot_set_param(name.encode("utf-8"), float(value))


def tot_finalize() -> int:
    return _lib.tot_finalize()
```

- [ ] **Step 2: コミット**

Run:
```bash
git add python/totlib/_ffi.py
git commit -m "feat(totlib): add ctypes FFI binding to libtotapi.so"
```

---

## Task 6: `totlib.py` の `Totlib` class を作成

**Files:**
- Create: `python/totlib/totlib.py`

- [ ] **Step 1: 新規作成**

作成: `python/totlib/totlib.py`

```python
"""High-level Python class for the TOT integrated simulator."""
from __future__ import annotations

from typing import Any

from . import _ffi
from .errors import raise_for_code
from .state import TotState


class Totlib:
    """In-process wrapper around libtotapi.so.

    Lifecycle:
        with Totlib() as tot:
            tot.set_params(**{"TR.RR": 6.2, "TR.RA": 2.0})
            tot.run(ntmax=10)
            state = tot.get_state()

    Single-instance assumption: tot stores all state in module-level
    Fortran globals, so only one Totlib() can be active per process.
    """

    def __init__(self, *, auto_init: bool = True) -> None:
        self._initialized = False
        if auto_init:
            self.init()

    # ----- lifecycle -----------------------------------------------------

    def init(self) -> None:
        rc = _ffi.tot_init()
        raise_for_code(rc, context="tot_init")
        self._initialized = True

    def finalize(self) -> None:
        if not self._initialized:
            return
        rc = _ffi.tot_finalize()
        raise_for_code(rc, context="tot_finalize")
        self._initialized = False

    def __enter__(self) -> "Totlib":
        if not self._initialized:
            self.init()
        return self

    def __exit__(self, *args: Any) -> None:
        self.finalize()

    # ----- parameters ----------------------------------------------------

    def set_param(self, name: str, value: float) -> None:
        """Set a single parameter, e.g. set_param("TR.RR", 6.2)."""
        rc = _ffi.tot_set_param(name, value)
        raise_for_code(rc, context=f"tot_set_param({name!r})")

    def set_params(self, mapping: dict[str, float] | None = None, /, **kwargs: float) -> None:
        """Set multiple parameters at once.

        Pass either a dict (allows keys with dots, like "TR.RR") or
        keyword arguments. Dict and kwargs may be combined; kwargs win
        on duplicate keys.
        """
        merged: dict[str, float] = {}
        if mapping:
            merged.update(mapping)
        merged.update(kwargs)
        for k, v in merged.items():
            self.set_param(k, v)

    # ----- run + inspect -------------------------------------------------

    def run(self, ntmax: int) -> None:
        rc = _ffi.tot_run(ntmax)
        raise_for_code(rc, context=f"tot_run({ntmax})")

    def get_state(self) -> TotState:
        rc, c_state = _ffi.tot_get_state()
        raise_for_code(rc, context="tot_get_state")
        return TotState.from_c(c_state)
```

- [ ] **Step 2: コミット**

Run:
```bash
git add python/totlib/totlib.py
git commit -m "feat(totlib): add Totlib high-level class"
```

---

## Task 7: ユニットテスト追加（FFI レベル）

**Files:**
- Create: `python/totlib/tests/test_ffi.py`

> **NOTE:** 当初 `conftest.py` で `monkeypatch.setenv("LD_LIBRARY_PATH", ...)` する fixture を置く案だったが、**`_ffi.py` の `ctypes.CDLL` 呼び出しは pytest fixture が走る前のモジュール import 時点で実行される** ため、fixture による env mutation は no-op であり誤解を招く。`LD_LIBRARY_PATH` は **シェル側で設定する** 前提とし、本 plan の各 Run コマンド (`TOTLIB_PATH=...` を含む形式) がそれを既に正しく行っている。conftest は作成しない。
>
> ```bash
> # 推奨実行形式（既に各 Run ステップで採用済）:
> TOTLIB_PATH=/home/k-yoshimi/program/task/tot/libtotapi.so \
> LD_LIBRARY_PATH=/home/k-yoshimi/program/task/tot:/home/k-yoshimi/program/task/tr:... \
> PYTHONPATH=/home/k-yoshimi/program/task/python \
> python3 -m pytest python/totlib/tests/test_ffi.py -v
> ```
>
> （`TOTLIB_PATH` が絶対パスかつ依存モジュールが同フォルダから自動解決できる場合は `LD_LIBRARY_PATH` 不要なケースもある。失敗したら設定する。）

- [ ] **Step 1: FFI テスト作成**

作成: `python/totlib/tests/test_ffi.py`

```python
"""Tests for the low-level ctypes FFI."""
import pytest

from totlib import _ffi


class TestFfiLifecycle:
    def test_init_returns_zero(self):
        try:
            assert _ffi.tot_init() == 0
        finally:
            _ffi.tot_finalize()

    def test_finalize_when_uninitialized_is_zero(self):
        # tot_finalize is documented as idempotent.
        assert _ffi.tot_finalize() == 0

    def test_init_is_idempotent(self):
        try:
            assert _ffi.tot_init() == 0
            assert _ffi.tot_init() == 0
        finally:
            _ffi.tot_finalize()


class TestFfiSetParam:
    def setup_method(self):
        _ffi.tot_init()

    def teardown_method(self):
        _ffi.tot_finalize()

    def test_unknown_prefix_returns_one(self):
        assert _ffi.tot_set_param("ZZ.NONE", 0.0) == 1

    def test_missing_prefix_returns_one(self):
        assert _ffi.tot_set_param("RR", 6.2) == 1

    def test_known_tr_scalar_returns_zero(self):
        assert _ffi.tot_set_param("TR.RR", 6.2) == 0

    def test_known_tr_array_returns_zero(self):
        assert _ffi.tot_set_param("TR.PN[1]", 0.7) == 0


class TestFfiGetState:
    def setup_method(self):
        _ffi.tot_init()

    def teardown_method(self):
        _ffi.tot_finalize()

    def test_get_state_after_init(self):
        rc, state = _ffi.tot_get_state()
        assert rc == 0
        assert state.tr_present == 1
        assert state.tr.nrmax > 0
        assert state.tr.nsmax > 0
```

- [ ] **Step 2: テスト実行**

Run:
```bash
cd /home/k-yoshimi/program/task
TOTLIB_PATH=/home/k-yoshimi/program/task/tot/libtotapi.so \
PYTHONPATH=/home/k-yoshimi/program/task/python \
python3 -m pytest python/totlib/tests/test_ffi.py -v
```
Expected: 全 PASS。`libtotapi.so` の依存ライブラリ解決でエラーが出る場合は `LD_LIBRARY_PATH` をシェル env に設定（fixture では遅すぎて効かない）。

- [ ] **Step 3: コミット**

Run:
```bash
git add python/totlib/tests/test_ffi.py
git commit -m "test(totlib): add FFI lifecycle and dispatcher tests"
```

---

## Task 8: 高レベル Class のユニットテスト

**Files:**
- Create: `python/totlib/tests/test_class.py`

- [ ] **Step 1: テスト作成**

作成: `python/totlib/tests/test_class.py`

```python
"""Tests for the high-level Totlib class."""
import pytest
import numpy as np

from totlib import Totlib, TotlibInvalidParamError, TotlibNotInitializedError


class TestLifecycle:
    def test_context_manager(self):
        with Totlib() as tot:
            assert tot._initialized
        assert not tot._initialized

    def test_manual_init_finalize(self):
        tot = Totlib(auto_init=False)
        assert not tot._initialized
        tot.init()
        try:
            assert tot._initialized
        finally:
            tot.finalize()
        assert not tot._initialized

    def test_set_param_after_finalize_raises(self):
        tot = Totlib()
        tot.finalize()
        with pytest.raises(TotlibNotInitializedError):
            tot.set_param("TR.RR", 6.2)


class TestSetParam:
    def test_invalid_param_raises(self):
        with Totlib() as tot:
            with pytest.raises(TotlibInvalidParamError):
                tot.set_param("ZZ.NONE", 0.0)

    def test_set_params_via_dict(self):
        with Totlib() as tot:
            tot.set_params({"TR.RR": 6.2, "TR.RA": 2.0})

    def test_set_params_dict_with_dotted_keys(self):
        with Totlib() as tot:
            # kwargs cannot express "TR.RR" (dots illegal in kwarg names)
            # so dotted keys MUST go through the dict argument.
            tot.set_params({"TR.RR": 6.2, "TR.PN[1]": 0.7})

    def test_set_params_mixed(self):
        with Totlib() as tot:
            # No kwarg keys with dots, but plain keys still work via kwargs
            # if the per-module registry happens to accept them.
            tot.set_params({"TR.RR": 6.2})


class TestGetState:
    def test_state_returns_dataclass(self):
        with Totlib() as tot:
            state = tot.get_state()
            assert state.tr_present
            assert state.tr is not None
            assert state.tr.nrmax > 0

    def test_state_arrays_are_numpy(self):
        with Totlib() as tot:
            state = tot.get_state()
            assert isinstance(state.tr.RN, np.ndarray)
            assert state.tr.RN.shape == (state.tr.nrmax, state.tr.nsmax)
            assert isinstance(state.tr.AJ, np.ndarray)
            assert state.tr.AJ.shape == (state.tr.nrmax,)
```

- [ ] **Step 2: テスト実行**

Run:
```bash
cd /home/k-yoshimi/program/task
TOTLIB_PATH=/home/k-yoshimi/program/task/tot/libtotapi.so \
PYTHONPATH=/home/k-yoshimi/program/task/python \
python3 -m pytest python/totlib/tests/test_class.py -v
```
Expected: 全 PASS。

- [ ] **Step 3: コミット**

Run:
```bash
git add python/totlib/tests/test_class.py
git commit -m "test(totlib): add Totlib class tests (context manager, set_params, get_state)"
```

---

## Task 9: README 作成（ユーザ向けドキュメント）

**Files:**
- Create: `python/totlib/README.md`

- [ ] **Step 1: README 新規作成**

作成: `python/totlib/README.md`

````markdown
# totlib — Python wrapper for the TASK/TOT integrated simulator

`totlib` is an in-process Python wrapper for the integrated transport
simulator (`tot`), exposing initialization, parameter setting, time
advancement, and state retrieval through a Pythonic API.

## Installation

```sh
# 1. Build libtotapi.so (Phase L-4)
cd <repo>/tot && make libtotapi.so

# 2. Add the python/ directory to PYTHONPATH (no pip install needed)
export PYTHONPATH=<repo>/python:$PYTHONPATH

# 3. (Optional) override the library path
export TOTLIB_PATH=<repo>/tot/libtotapi.so
```

## Quick start

```python
from totlib import Totlib

with Totlib() as tot:
    tot.set_params({"TR.RR": 6.2, "TR.RA": 2.0, "TR.BB": 5.3})
    tot.run(ntmax=10)
    state = tot.get_state()
    print("Q0 =", state.tr.Q0)
    print("WPT =", state.tr.WPT, "MJ")
    print("RN profile shape =", state.tr.RN.shape)
```

## Parameter naming

Parameters are routed by `<MODULE>.<NAME>`:

| Prefix | Owner module |
|--------|--------------|
| `TR.X` | TR transport solver |
| `TI.X` | TI module |
| `FP.X` | FP Fokker-Planck |
| `WR.X` | WR ray tracing |
| `WM.X` | WM full-wave |
| `PL.X` | PL plasma profiles |
| `EQ.X` | EQ equilibrium (limited subset) |

Array parameters use 1-origin indexing: `TR.PN[1]`, `TR.PT[2]`, etc.

## Error model

| Code | Exception |
|------|-----------|
| 0    | (no exception) |
| 1    | `TotlibInvalidParamError` |
| 2    | `TotlibNotInitializedError` |
| 3    | `TotlibCalculationError` |

All inherit from `TotlibError`.

## Limitations

- Single instance per process (TOT relies on Fortran module-level globals).
- Linux x86_64 only (Phase L-4 build).
- Graphics calls are excluded — use the standalone `tot` binary if you need
  GS visualization.
- `TI.*`, `FP.*`, `WR.*`, `WM.*` parameter coverage depends on each
  module's own Phase L-3 progress.

## Parameter optimization (preview)

See `docs/superpowers/plans/2026-04-18-tot-library-L7-optimization.md`
for the upcoming scipy/optuna integration.
````

- [ ] **Step 2: コミット**

Run:
```bash
git add python/totlib/README.md
git commit -m "docs(totlib): add user-facing README"
```

---

## Task 10: 全テスト最終確認

**Files:** なし

- [ ] **Step 1: Python ユニットテスト全実行**

Run:
```bash
cd /home/k-yoshimi/program/task
TOTLIB_PATH=/home/k-yoshimi/program/task/tot/libtotapi.so \
PYTHONPATH=/home/k-yoshimi/program/task/python \
python3 -m pytest python/totlib/tests/ -v
```
Expected: 全 PASS。

- [ ] **Step 2: 既存 Fortran テスト不変**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh tot_demo2014_short tot_ht6m_short
cd /home/k-yoshimi/program/task/tot/tests/c_abi && make run && make run_so
```
Expected: 全 PASS、L-4 と数値完全一致。

- [ ] **Step 3: コミット（L-5 完了マーカー）**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "test(totlib): L-5 verification complete (all tests green)"
```

---

## Verification (Phase L-5 完了基準)

- [ ] `python/totlib/` パッケージが完成し、`from totlib import Totlib` できる。
- [ ] `python/totlib/tests/test_ffi.py` 全 PASS。
- [ ] `python/totlib/tests/test_class.py` 全 PASS。
- [ ] context manager で init/finalize が回り、`set_param`/`get_state` が動作。
- [ ] state の numpy 配列が actual size (NRMAX × NSMAX) にスライスされている。
- [ ] 既存 tot regression / C ABI テスト全て不変。

---

## Dependencies & Fallback

**前提:** L-4 完了。Python 3.8+ と numpy。

**産出物:** L-6 (4 層テスト) で Layer 1 (等価性) と Layer 4 (網羅計算 smoke) を Python から直接書ける。L-7 (パラメータ最適化) の入口。

**Fallback:**
- `libtotapi.so` のロード失敗 → `TOTLIB_PATH` 環境変数を指定するエラーメッセージで誘導済み。
- numpy が無い → state の `RN`/`RT` 等を `list[list[float]]` で返す代替実装に切り替え（注: ベンチマーク性能低下、L-7 で要再検討）。
- ctypes の Structure サイズが Fortran 側と不一致 → `tr/tr_api.h` の `TR_MAX_NRMAX/TR_MAX_NSMAX` を `state.py` に同期する自動 sync スクリプトを `python/totlib/_sync.py` として追加。

---

## Out of scope（次フェーズ送り）

- 4 層テスト統合（Layer 1/2/3/4） → L-6
- パラメータ最適化ワークフロー → L-7
- 個別モジュール wrapper との統合・依存整理 → L-7 まで先送り
- pip パッケージ化 → 別 phase
