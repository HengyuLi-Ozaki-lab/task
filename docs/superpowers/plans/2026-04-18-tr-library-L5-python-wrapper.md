# Phase L-5: Python ラッパ 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-4 で生成された `tr/libtrapi.so` を `ctypes` で呼び、Pythonic な `Trlib` クラスとして公開する `python/trlib/` パッケージを新設する。

**Architecture:** 設計書 §6 の 2 層構成: 下層 `_ffi.py` が `ctypes.CDLL("libtrapi.so")` で 5 関数を直叩き、上層 `trlib.py` が context manager / 辞書一括セット / 例外階層を提供する。`state.py` は C 構造体 → `dataclass` 変換を担当。Python は **標準ライブラリのみ** （Phase 0 と同じ方針、numpy 依存も今回は導入しない）。

**Tech Stack:** Python 3.8+ (stdlib only — `ctypes`, `dataclasses`, `os`, `pathlib`), `tr/libtrapi.so` (L-4 成果物)。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` §6 (Python ラッパ設計), §A.10 (2 層構成採用根拠), §4.2 (構造体レイアウト)。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/trlib/__init__.py` | 新規 | `from .trlib import Trlib`, `from .errors import TrlibError` |
| `python/trlib/_ffi.py` | 新規 | ctypes による低レベル FFI（CDLL ロード、`tr_state_t` Structure 定義、5 関数 prototype） |
| `python/trlib/state.py` | 新規 | `TrState` dataclass（plain Python types に変換） |
| `python/trlib/errors.py` | 新規 | `TrlibError` 例外階層 |
| `python/trlib/trlib.py` | 新規 | `Trlib` class（context manager、`set_params`、`run`、`get_state`） |
| `python/trlib/tests/__init__.py` | 新規 | 空 |
| `python/trlib/tests/test_smoke.py` | 新規 | unittest: `Trlib() as tr: tr.run(0)` でクラッシュしない |
| `python/__init__.py` | 新規 | 空（パッケージマーカー） |

**方針:**
- パッケージは `python/trlib/`（既存の他 Python コードと共存できるよう `python/` 直下）。
- ライブラリパスは `TRLIB_PATH` 環境変数優先、なければ `<repo>/tr/libtrapi.so` を相対参照（設計書 §7.3）。
- L-5 では「ライブラリが import できる、init/run/finalize が呼べる」までを担保。Layer 1〜4 の本格テストは L-6 で実装。
- numpy なし: profile 配列は Python list of list に変換する（`get_state` の中で）。

---

## Task 1: ブランチと前提

- [ ] **Step 1: L-4 完了確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin develop
git log --oneline origin/develop | grep -i "phase l-4" | head -3
ls tr/libtrapi.so 2>&1 || (cd tr && make libtrapi.so 2>&1 | tail -5)
file tr/libtrapi.so
nm -D tr/libtrapi.so | grep -E " T tr_(init|run|set_param|get_state|finalize)$"
```
Expected: L-4 merge commit、`libtrapi.so` あり、5 シンボルがエクスポート済み。

- [ ] **Step 2: ブランチ作成**

Run:
```bash
git checkout -b feature/tr-library-phase-l5 origin/develop
```

- [ ] **Step 3: Python 動作確認**

Run:
```bash
python3 --version
python3 -c "import ctypes; print(ctypes.CDLL('/home/k-yoshimi/program/task/tr/libtrapi.so'))"
```
Expected: Python 3.8+、ライブラリが load できる（`<CDLL '...', handle ...>`）。失敗すれば `LD_LIBRARY_PATH` を追加するか `_ffi.py` で絶対パス resolve に倒す。

---

## Task 2: 例外階層 `errors.py`

**Files:**
- Create: `python/trlib/errors.py`

- [ ] **Step 1: 作成**

作成: `python/trlib/errors.py`

```python
"""Exception hierarchy for trlib."""


class TrlibError(Exception):
    """Base class for all trlib errors."""


class TrlibInitError(TrlibError):
    """Initialization failed (tr_init returned non-zero)."""


class TrlibParamError(TrlibError):
    """Invalid parameter name or index (tr_set_param returned 1)."""


class TrlibStateError(TrlibError):
    """Library not initialized (any call returned 2)."""


class TrlibRunError(TrlibError):
    """Calculation failed (tr_run / tr_get_state returned 3)."""


_CODE_MAP = {
    1: TrlibParamError,
    2: TrlibStateError,
    3: TrlibRunError,
}


def raise_for_ierr(func: str, ierr: int) -> None:
    """Raise the matching subclass when ierr != 0."""
    if ierr == 0:
        return
    cls = _CODE_MAP.get(ierr, TrlibError)
    raise cls(f"{func}: ierr={ierr}")
```

---

## Task 3: 低レベル FFI `_ffi.py`

**Files:**
- Create: `python/trlib/_ffi.py`

- [ ] **Step 1: ctypes 構造体と prototype**

作成: `python/trlib/_ffi.py`

```python
"""Low-level ctypes FFI for libtrapi.so.

Mirrors tr/tr_api.h. Higher-level helpers live in trlib.py.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path

# Layout constants must match tr_api.h exactly.
TR_MAX_NRMAX = 500
TR_MAX_NSMAX = 8


class TrStateC(ctypes.Structure):
    _fields_ = [
        ("nt",     ctypes.c_int),
        ("nrmax",  ctypes.c_int),
        ("nsmax",  ctypes.c_int),
        ("T",      ctypes.c_double),
        ("WPT",    ctypes.c_double),
        ("AJT",    ctypes.c_double),
        ("Q0",     ctypes.c_double),
        ("BETA0",  ctypes.c_double),
        ("BETAP0", ctypes.c_double),
        ("BETAA",  ctypes.c_double),
        ("BETAN",  ctypes.c_double),
        ("TAUE1",  ctypes.c_double),
        ("TAUE2",  ctypes.c_double),
        ("ZEFF0",  ctypes.c_double),
        ("ALI",    ctypes.c_double),
        ("RQ1",    ctypes.c_double),
        ("RN",     (ctypes.c_double * TR_MAX_NSMAX) * TR_MAX_NRMAX),
        ("RT",     (ctypes.c_double * TR_MAX_NSMAX) * TR_MAX_NRMAX),
        ("AJ",     ctypes.c_double * TR_MAX_NRMAX),
        ("QP",     ctypes.c_double * TR_MAX_NRMAX),
    ]


def _default_lib_path() -> Path:
    env = os.environ.get("TRLIB_PATH")
    if env:
        return Path(env)
    # python/trlib/_ffi.py -> repo root is two parents up
    here = Path(__file__).resolve()
    return here.parents[2] / "tr" / "libtrapi.so"


def load_library(path: str | None = None) -> ctypes.CDLL:
    p = Path(path) if path else _default_lib_path()
    if not p.exists():
        raise FileNotFoundError(
            f"libtrapi.so not found at {p}. Build it via `make -C tr libtrapi.so` "
            f"or set TRLIB_PATH."
        )
    lib = ctypes.CDLL(str(p))

    lib.tr_init.restype  = ctypes.c_int
    lib.tr_init.argtypes = []

    lib.tr_run.restype   = ctypes.c_int
    lib.tr_run.argtypes  = [ctypes.c_int]

    lib.tr_set_param.restype  = ctypes.c_int
    lib.tr_set_param.argtypes = [ctypes.c_char_p, ctypes.c_double]

    lib.tr_get_state.restype  = ctypes.c_int
    lib.tr_get_state.argtypes = [ctypes.POINTER(TrStateC)]

    lib.tr_finalize.restype  = ctypes.c_int
    lib.tr_finalize.argtypes = []

    return lib
```

注: `RN/RT` のレイアウトは設計書 §4.2 と一致 (`RN[NRMAX][NSMAX]` 行優先 = Fortran `RN(NSMAX, NRMAX)` 列優先で同じメモリ並び)。

---

## Task 4: Python dataclass `state.py`

**Files:**
- Create: `python/trlib/state.py`

- [ ] **Step 1: 作成**

作成: `python/trlib/state.py`

```python
"""Pythonic snapshot of tr_state_t."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ._ffi import TrStateC


SCALAR_FIELDS = (
    "T", "WPT", "AJT", "Q0", "BETA0", "BETAP0", "BETAA", "BETAN",
    "TAUE1", "TAUE2", "ZEFF0", "ALI", "RQ1",
)


@dataclass
class TrState:
    nt:    int
    nrmax: int
    nsmax: int
    scalars: dict
    RN: List[List[float]] = field(default_factory=list)   # [nrmax][nsmax]
    RT: List[List[float]] = field(default_factory=list)
    AJ: List[float]       = field(default_factory=list)   # [nrmax]
    QP: List[float]       = field(default_factory=list)

    @classmethod
    def from_c(cls, s: TrStateC) -> "TrState":
        scalars = {k: getattr(s, k) for k in SCALAR_FIELDS}
        nr, ns = s.nrmax, s.nsmax
        rn = [[s.RN[i][j] for j in range(ns)] for i in range(nr)]
        rt = [[s.RT[i][j] for j in range(ns)] for i in range(nr)]
        aj = [s.AJ[i] for i in range(nr)]
        qp = [s.QP[i] for i in range(nr)]
        return cls(
            nt=s.nt, nrmax=nr, nsmax=ns,
            scalars=scalars,
            RN=rn, RT=rt, AJ=aj, QP=qp,
        )

    def to_dict(self) -> dict:
        """Serializable dict matching the format used by Phase 0 baseline JSON."""
        return {
            "NT":    self.nt,
            "NRMAX": self.nrmax,
            "NSMAX": self.nsmax,
            "scalars": dict(self.scalars),
            "profile": [
                {"NR": i + 1, "RN": list(self.RN[i]), "RT": list(self.RT[i]),
                 "AJ": self.AJ[i], "QP": self.QP[i]}
                for i in range(self.nrmax)
            ],
        }
```

注: `to_dict()` の出力形式は **Phase 0 `extract_tr_metrics.py` の出力と完全一致** させる。これにより L-6 Layer 1 で同じ `compare_metrics.py` を再利用できる。

---

## Task 5: 高レベル `Trlib` クラス

**Files:**
- Create: `python/trlib/trlib.py`

- [ ] **Step 1: 作成**

作成: `python/trlib/trlib.py`

```python
"""High-level Trlib class. See docs/superpowers/specs/2026-04-17-tr-library-design.md §6.3."""
from __future__ import annotations

import ctypes
from typing import Optional

from . import _ffi
from .errors import TrlibError, raise_for_ierr
from .state import TrState


class Trlib:
    """In-process handle to libtrapi.so. One per process.

    Usage::

        with Trlib() as tr:
            tr.set_params(RR=7.5, BB=5.3)
            tr.run(ntmax=100)
            state = tr.get_state()
    """

    def __init__(self, lib_path: Optional[str] = None) -> None:
        self._lib = _ffi.load_library(lib_path)
        self._closed = True
        self._open()

    # --- lifecycle -------------------------------------------------------
    def _open(self) -> None:
        if not self._closed:
            return
        ierr = self._lib.tr_init()
        raise_for_ierr("tr_init", ierr)
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        ierr = self._lib.tr_finalize()
        raise_for_ierr("tr_finalize", ierr)
        self._closed = True

    def __enter__(self) -> "Trlib":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    # --- parameters ------------------------------------------------------
    def set_param(self, name: str, value: float) -> None:
        if self._closed:
            raise TrlibError("set_param on closed Trlib")
        ierr = self._lib.tr_set_param(name.encode("ascii"), float(value))
        if ierr != 0:
            raise_for_ierr(f"tr_set_param('{name}', {value})", ierr)

    def set_params(self, **kwargs) -> None:
        for k, v in kwargs.items():
            # Allow PN_1 -> PN[1] convenience for Python keyword args
            name = k.replace("__", "[", 1).replace("__end__", "]")
            if name.endswith("__end__"):
                name = name[:-7] + "]"
            self.set_param(name, v)

    # --- run / state -----------------------------------------------------
    def run(self, ntmax: int) -> None:
        if self._closed:
            raise TrlibError("run on closed Trlib")
        ierr = self._lib.tr_run(int(ntmax))
        raise_for_ierr(f"tr_run({ntmax})", ierr)

    def get_state(self) -> TrState:
        if self._closed:
            raise TrlibError("get_state on closed Trlib")
        c = _ffi.TrStateC()
        ierr = self._lib.tr_get_state(ctypes.byref(c))
        raise_for_ierr("tr_get_state", ierr)
        return TrState.from_c(c)
```

注: `set_params` の Python キーワード引数では `[]` が使えないため、ドット記法は不採用。配列要素は `set_param("PN[1]", 0.7)` を直接呼ぶ運用とする。`set_params(**kwargs)` は **スカラーパラメータ専用**。配列指定が必要な場合は明示的に `set_param` を使う旨を docstring に書く（次タスクで README）。

---

## Task 6: `__init__.py` パッケージ初期化

**Files:**
- Create: `python/trlib/__init__.py`
- Create: `python/__init__.py`
- Create: `python/trlib/tests/__init__.py`

- [ ] **Step 1: それぞれを作成**

作成: `python/trlib/__init__.py`

```python
"""trlib: Python wrapper for libtrapi.so."""
from .trlib import Trlib
from .state import TrState
from .errors import (
    TrlibError, TrlibInitError, TrlibParamError, TrlibStateError, TrlibRunError,
)

__all__ = [
    "Trlib", "TrState",
    "TrlibError", "TrlibInitError", "TrlibParamError",
    "TrlibStateError", "TrlibRunError",
]
```

作成: `python/__init__.py`（空でよい、なければ `python.trlib` パスで import 不可な OS もあるため）

```python
```

作成: `python/trlib/tests/__init__.py`（空）

```python
```

---

## Task 7: スモークテスト

**Files:**
- Create: `python/trlib/tests/test_smoke.py`

- [ ] **Step 1: テスト本体**

作成: `python/trlib/tests/test_smoke.py`

```python
"""L-5 smoke: load library, init/run(0)/finalize without crash."""
import os
import unittest
from pathlib import Path

# Make sure libtrapi.so resolves.
REPO = Path(__file__).resolve().parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"


@unittest.skipUnless(DEFAULT_SO.exists(), f"libtrapi.so not built ({DEFAULT_SO})")
class TestSmoke(unittest.TestCase):
    def test_init_run_finalize(self):
        from trlib import Trlib
        with Trlib() as tr:
            tr.run(0)              # L-3 stub may be no-op; just verify ierr=0
            state = tr.get_state()
            self.assertGreater(state.nrmax, 0)
            self.assertGreater(state.nsmax, 0)

    def test_invalid_param_raises(self):
        from trlib import Trlib, TrlibParamError
        with Trlib() as tr:
            with self.assertRaises(TrlibParamError):
                tr.set_param("NOT_A_PARAM", 0.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 走らせる**

Run:
```bash
cd /home/k-yoshimi/program/task
PYTHONPATH=python python3 -m unittest python.trlib.tests.test_smoke -v
```
Expected: 2 tests OK。`libtrapi.so` が無ければ skip（L-4 完了前でも import まで通ることを担保）。

- [ ] **Step 3: import sanity**

Run:
```bash
PYTHONPATH=python python3 -c "from trlib import Trlib, TrState, TrlibError; print('ok')"
```
Expected: `ok`。

---

## Task 8: 回帰テスト

- [ ] **Step 1: tr2 の不変**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tr_iter01 tr_m0904 tr_tst2 2>&1 | tail -5
```
Expected: 3/3 PASS（Python 側の追加は Fortran ビルドに無関係）。

---

## Task 9: コミットと PR

- [ ] **Step 1: コミット**

Run:
```bash
git add python/__init__.py python/trlib/
git commit -m "feat(trlib): Python ctypes wrapper for libtrapi.so

Two-layer design (_ffi + Trlib class), context manager,
TrState dataclass with to_dict() matching Phase 0 baseline format."
```

- [ ] **Step 2: PR**

Run:
```bash
gh pr create --base develop --title "feat(trlib): Phase L-5 Python ctypes wrapper" \
  --body "Phase L-5: python/trlib/ パッケージ追加。標準ライブラリのみ依存。設計書 §6。"
```

---

## 撤退条件 / フォールバック

| 状況 | 対応 |
|---|---|
| `ctypes.CDLL` ロード失敗 | `LD_LIBRARY_PATH` 設定手順を README で案内、または `os.environ` を `_ffi.py` 内で操作 |
| 構造体サイズが C 側と不一致 | `ctypes.sizeof(TrStateC)` と `sizeof(tr_state_t)` を比較する別 C テストを追加し、原因究明 |
| `set_params(**kwargs)` で `[]` 不可問題が顕在化 | README に「配列要素は明示 `set_param` 推奨」と記載、エイリアス記法は廃止可 |

## 受け入れ基準

- [ ] `from trlib import Trlib` が成功
- [ ] `with Trlib() as tr: tr.run(0)` が例外なし
- [ ] `tr.get_state().to_dict()` が Phase 0 baseline と同じキー構造
- [ ] 不正な `set_param` で `TrlibParamError`
- [ ] 回帰 3 ケース PASS

## 依存

- L-4 完了（`libtrapi.so` が存在）
