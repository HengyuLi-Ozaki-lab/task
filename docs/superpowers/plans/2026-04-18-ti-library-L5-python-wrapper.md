# TI Library Phase L-5: Python Wrapper (`python/tilib/`) 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-4 で生成される `libtiapi.so` を Python から ctypes 経由で叩く wrapper パッケージ `python/tilib/` を新設する。下層 `_ffi.py`（ctypes 直叩き）+ 上層 `tilib.py`（Pythonic Tilib クラス）の 2 層構成。最小限の `set_param/run/get_state` ライフサイクルが動くことをテストで確認する（4 層フルテストは L-6）。

**Architecture:** TR の `python/trlib/` 設計と同型。`_ffi.py` で `ctypes.CDLL` ロードと関数シグネチャ定義、`tilib.py` で Tilib class（context manager + 辞書一括 set_params + TiState dataclass）。`state.py` に `TiState` dataclass、`errors.py` に `TilibError` 例外階層。

**Tech Stack:** Python 3.8+, ctypes（標準ライブラリ）, dataclasses, unittest（標準）。numpy オプショナル（無ければ list で OK、L-6 で要否判定）。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` 6 章 (Python ラッパ設計)。

---

## File Structure

このフェーズで作成・変更するファイル:

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/tilib/__init__.py` | 新規 | `from .tilib import Tilib; from .errors import TilibError; from .state import TiState` |
| `python/tilib/_ffi.py` | 新規 | ctypes CDLL ロード、`ti_init/ti_run/ti_get_state/ti_set_param/ti_finalize` シグネチャ、`TiStateC` Structure |
| `python/tilib/state.py` | 新規 | `TiState` dataclass（C struct → Python 表現） |
| `python/tilib/errors.py` | 新規 | `TilibError` 例外階層（`TilibInitError`, `TilibParamError`, `TilibStateError`） |
| `python/tilib/tilib.py` | 新規 | `Tilib` クラス（context manager, set_params, run, get_state, close） |
| `python/tilib/tests/__init__.py` | 新規 | テストパッケージマーカ |
| `python/tilib/tests/test_ffi.py` | 新規 | _ffi.py の最小スモーク（init/finalize cycle, set_param 戻り値） |
| `python/tilib/tests/test_tilib.py` | 新規 | Tilib クラスの最小テスト（with 構文、set_params 辞書、get_state） |
| `python/tilib/README.md` | 新規 | 使い方の最小例（L-7 で本格拡充） |

---

## Task 1: 前提確認

**Files:**
- なし

- [ ] **Step 1: ブランチ作成と L-4 マージ確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin
git checkout -b feature/ti-library-L5-python-wrapper origin/develop
ls /home/k-yoshimi/program/task/ti/libtiapi.so /home/k-yoshimi/program/task/ti/ti_api.h
```
Expected: L-4 マージ後、`libtiapi.so` が存在する（make 済み）か、もしくは `make libtiapi.so` で生成可能。

- [ ] **Step 2: libtiapi.so がない場合はビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/ti
[ -f libtiapi.so ] || make libtiapi.so 2>&1 | tail -5
ls -la libtiapi.so
nm -D libtiapi.so | grep -E " T (ti_init|ti_run|ti_get_state|ti_set_param|ti_finalize)$"
```
Expected: 5 シンボル全て確認できる。

- [ ] **Step 3: Python のバージョン**

Run:
```bash
python3 --version
python3 -c "import ctypes; print(ctypes.__version__ if hasattr(ctypes,'__version__') else 'stdlib')"
```
Expected: Python 3.8 以上。

- [ ] **Step 4: 既存 trlib があれば構造を参照**

Run:
```bash
ls /home/k-yoshimi/program/task/python/trlib 2>/dev/null
```
Expected: あれば実装パターンの参考にできる（同じ TR 設計書に基づく）。

- [ ] **Step 5: 空コミット**

Run:
```bash
mkdir -p /home/k-yoshimi/program/task/python/tilib/tests
git commit --allow-empty -m "chore(tilib): start L-5 python wrapper"
```

---

## Task 2: `errors.py` を新設

**Files:**
- Create: `python/tilib/errors.py`

- [ ] **Step 1: 例外階層を定義**

作成: `python/tilib/errors.py`

```python
"""Exception hierarchy for tilib.

Returned non-zero ierr from libtiapi.so is mapped to one of these:
   1 -> TilibParamError   (invalid parameter name or index)
   2 -> TilibInitError    (not initialized)
   3 -> TilibRunError     (calculation failed)
   4 -> TilibStateError   (state buffer too small / NRMAX/nsa_max overflow)
"""


class TilibError(Exception):
    """Base class for all tilib errors."""


class TilibInitError(TilibError):
    """Init / finalize lifecycle violation."""


class TilibParamError(TilibError):
    """Invalid parameter name or array index."""


class TilibRunError(TilibError):
    """ti_run returned non-zero (calculation failed)."""


class TilibStateError(TilibError):
    """ti_get_state returned non-zero (typically NRMAX > TI_MAX_NRMAX)."""


def raise_for_ierr(ierr: int, context: str) -> None:
    """Map a non-zero ierr from the C ABI to a Python exception."""
    if ierr == 0:
        return
    msg = f"{context}: ti C ABI returned ierr={ierr}"
    if ierr == 1:
        raise TilibParamError(msg)
    if ierr == 2:
        raise TilibInitError(msg)
    if ierr == 3:
        raise TilibRunError(msg)
    if ierr == 4:
        raise TilibStateError(msg)
    raise TilibError(msg)
```

- [ ] **Step 2: コミット**

Run:
```bash
git add python/tilib/errors.py
git commit -m "feat(tilib): add error hierarchy and raise_for_ierr helper"
```

---

## Task 3: `state.py` を新設

**Files:**
- Create: `python/tilib/state.py`

- [ ] **Step 1: dataclass を定義**

作成: `python/tilib/state.py`

```python
"""TiState dataclass: snapshot of ticomm state from ti_get_state."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class TiState:
    """Snapshot of ticomm state at a given point in time.

    Sizes match runtime nrmax / nsa_max (not the compile-time maxima).
    Profiles are List[List[float]] of shape [nrmax][nsa_max] for RNA/RTA/RUA,
    and List[float] of length nrmax for RBP/RQP/RJP/ZEFF/BETA/BETAP.
    """

    nt: int
    nrmax: int
    nsa_max: int
    nsmax: int
    T: float
    residual_loop_max: float
    icount_loop_max: int
    icount_mat_max: int
    RNA: List[List[float]] = field(default_factory=list)
    RTA: List[List[float]] = field(default_factory=list)
    RUA: List[List[float]] = field(default_factory=list)
    RBP: List[float] = field(default_factory=list)
    RQP: List[float] = field(default_factory=list)
    RJP: List[float] = field(default_factory=list)
    ZEFF: List[float] = field(default_factory=list)
    BETA: List[float] = field(default_factory=list)
    BETAP: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "nt": self.nt, "nrmax": self.nrmax, "nsa_max": self.nsa_max,
            "nsmax": self.nsmax, "T": self.T,
            "residual_loop_max": self.residual_loop_max,
            "icount_loop_max": self.icount_loop_max,
            "icount_mat_max": self.icount_mat_max,
            "RNA": self.RNA, "RTA": self.RTA, "RUA": self.RUA,
            "RBP": self.RBP, "RQP": self.RQP, "RJP": self.RJP,
            "ZEFF": self.ZEFF, "BETA": self.BETA, "BETAP": self.BETAP,
        }
```

- [ ] **Step 2: コミット**

Run:
```bash
git add python/tilib/state.py
git commit -m "feat(tilib): add TiState dataclass"
```

---

## Task 4: `_ffi.py` を新設（テスト先行）

**Files:**
- Create: `python/tilib/tests/__init__.py` (empty)
- Create: `python/tilib/tests/test_ffi.py`
- Create: `python/tilib/_ffi.py`

- [ ] **Step 1: `tests/__init__.py` を空ファイルで作成**

Run:
```bash
: > /home/k-yoshimi/program/task/python/tilib/tests/__init__.py
```

- [ ] **Step 2: 失敗するテストを書く**

作成: `python/tilib/tests/test_ffi.py`

```python
"""Smoke tests for tilib._ffi (direct ctypes layer)."""

import os
import unittest


@unittest.skipUnless(
    os.path.exists(os.environ.get(
        "TILIB_PATH",
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "ti", "libtiapi.so"))),
    "libtiapi.so not built; run `make libtiapi.so` in ti/")
class TestFfi(unittest.TestCase):

    def setUp(self):
        from tilib import _ffi
        self.lib = _ffi.load_library()

    def test_init_finalize_cycle(self):
        rc = self.lib.ti_init()
        self.assertEqual(rc, 0)
        rc = self.lib.ti_finalize()
        self.assertEqual(rc, 0)

    def test_set_param_unknown_returns_nonzero(self):
        self.lib.ti_init()
        try:
            rc = self.lib.ti_set_param(b"NO_SUCH_PARAM", 1.0)
            self.assertNotEqual(rc, 0)
        finally:
            self.lib.ti_finalize()

    def test_set_param_known_returns_zero(self):
        self.lib.ti_init()
        try:
            rc = self.lib.ti_set_param(b"RR", 6.2)
            self.assertEqual(rc, 0)
        finally:
            self.lib.ti_finalize()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: テスト実行（失敗確認）**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest python.tilib.tests.test_ffi -v 2>&1 | tail -15
```
Expected: ImportError（_ffi.py が無い）。

- [ ] **Step 4: `_ffi.py` を実装**

作成: `python/tilib/_ffi.py`

```python
"""Low-level ctypes FFI for libtiapi.so.

Provides:
   - load_library() -> CDLL with function signatures bound
   - TiStateC: ctypes Structure mirroring ti_state_t in ti/ti_api.h
"""

import ctypes
import os
from ctypes import (
    CDLL, POINTER, Structure,
    c_char_p, c_double, c_int,
)

TI_MAX_NRMAX = 200
TI_MAX_NSA_MAX = 20


class TiStateC(Structure):
    _fields_ = [
        ("nt", c_int),
        ("nrmax", c_int),
        ("nsa_max", c_int),
        ("nsmax", c_int),
        ("T", c_double),
        ("residual_loop_max", c_double),
        ("icount_loop_max", c_int),
        ("icount_mat_max", c_int),
        ("RNA", (c_double * TI_MAX_NSA_MAX) * TI_MAX_NRMAX),
        ("RTA", (c_double * TI_MAX_NSA_MAX) * TI_MAX_NRMAX),
        ("RUA", (c_double * TI_MAX_NSA_MAX) * TI_MAX_NRMAX),
        ("RBP", c_double * TI_MAX_NRMAX),
        ("RQP", c_double * TI_MAX_NRMAX),
        ("RJP", c_double * TI_MAX_NRMAX),
        ("ZEFF", c_double * TI_MAX_NRMAX),
        ("BETA", c_double * TI_MAX_NRMAX),
        ("BETAP", c_double * TI_MAX_NRMAX),
    ]


def _default_lib_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", "ti", "libtiapi.so"))


def load_library(path: str = None) -> CDLL:
    """Load libtiapi.so and bind argument/return types.

    Path resolution:
       1. `path` argument (if given)
       2. TILIB_PATH env var
       3. <repo>/ti/libtiapi.so
    """
    lib_path = path or os.environ.get("TILIB_PATH") or _default_lib_path()
    if not os.path.exists(lib_path):
        raise FileNotFoundError(
            f"libtiapi.so not found at {lib_path}; "
            "run `make libtiapi.so` in ti/, or set TILIB_PATH"
        )
    lib = CDLL(lib_path)

    lib.ti_init.argtypes = []
    lib.ti_init.restype = c_int

    lib.ti_run.argtypes = [c_int]
    lib.ti_run.restype = c_int

    lib.ti_get_state.argtypes = [POINTER(TiStateC)]
    lib.ti_get_state.restype = c_int

    lib.ti_set_param.argtypes = [c_char_p, c_double]
    lib.ti_set_param.restype = c_int

    lib.ti_finalize.argtypes = []
    lib.ti_finalize.restype = c_int

    return lib
```

- [ ] **Step 5: `__init__.py` を作成（最小）**

作成: `python/tilib/__init__.py`

```python
"""tilib: Python wrapper around libtiapi.so."""

from .errors import (
    TilibError, TilibInitError, TilibParamError,
    TilibRunError, TilibStateError, raise_for_ierr,
)
from .state import TiState

__all__ = [
    "TilibError", "TilibInitError", "TilibParamError",
    "TilibRunError", "TilibStateError",
    "TiState",
    "raise_for_ierr",
]
```

(Tilib クラス追加は Task 5)

- [ ] **Step 6: テスト再実行**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest python.tilib.tests.test_ffi -v 2>&1 | tail -15
```
Expected: 3 tests PASS（または `libtiapi.so` 未ビルドなら全 SKIP）。

- [ ] **Step 7: コミット**

Run:
```bash
git add python/tilib/_ffi.py python/tilib/__init__.py \
        python/tilib/tests/__init__.py python/tilib/tests/test_ffi.py
git commit -m "feat(tilib): add _ffi.py ctypes layer with TiStateC and load_library"
```

---

## Task 5: `tilib.py` Tilib クラスを新設（テスト先行）

**Files:**
- Create: `python/tilib/tests/test_tilib.py`
- Create: `python/tilib/tilib.py`
- Modify: `python/tilib/__init__.py`

- [ ] **Step 1: 失敗するテストを書く**

作成: `python/tilib/tests/test_tilib.py`

```python
"""Smoke tests for the high-level Tilib class."""

import os
import unittest


@unittest.skipUnless(
    os.path.exists(os.environ.get(
        "TILIB_PATH",
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "ti", "libtiapi.so"))),
    "libtiapi.so not built")
class TestTilib(unittest.TestCase):

    def test_context_manager_lifecycle(self):
        from tilib import Tilib
        with Tilib() as ti:
            self.assertIsNotNone(ti)
        # After context exit, calling set_param should raise
        with self.assertRaises(Exception):
            ti.set_param("RR", 6.2)

    def test_set_param_known_and_unknown(self):
        from tilib import Tilib, TilibParamError
        with Tilib() as ti:
            ti.set_param("RR", 6.2)              # OK
            ti.set_param("PN[1]", 0.7)           # array OK
            with self.assertRaises(TilibParamError):
                ti.set_param("NO_SUCH_PARAM", 1.0)

    def test_set_params_dict(self):
        from tilib import Tilib
        with Tilib() as ti:
            ti.set_params(RR=6.2, BB=5.3, NTMAX=2)

    def test_run_and_get_state_minimal(self):
        from tilib import Tilib
        with Tilib() as ti:
            ti.set_params(NSMAX=1, NRMAX=10, NTMAX=2,
                          NTSTEP=1, NGTSTEP=1, NGRSTEP=1)
            ti.run(ntmax=2)
            state = ti.get_state()
            self.assertEqual(state.nrmax, 10)
            self.assertEqual(state.nsa_max >= 1, True)
            self.assertEqual(len(state.RBP), 10)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: テスト実行（失敗）**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest python.tilib.tests.test_tilib -v 2>&1 | tail -15
```
Expected: ImportError（`from tilib import Tilib` が解決しない）。

- [ ] **Step 3: `tilib.py` 本実装**

作成: `python/tilib/tilib.py`

```python
"""High-level Tilib class wrapping libtiapi.so."""

from typing import Optional

from . import _ffi
from .errors import (
    TilibInitError, raise_for_ierr,
)
from .state import TiState


class Tilib:
    """Single-instance handle to libtiapi.so.

    Lifecycle:
        with Tilib() as ti:
            ti.set_params(NSMAX=1, NTMAX=10)
            ti.run(ntmax=10)
            state = ti.get_state()

    Notes:
        - Library state is global on the Fortran side; do NOT instantiate
          two Tilib objects concurrently in the same process.
    """

    def __init__(self, lib_path: Optional[str] = None):
        self._lib = _ffi.load_library(lib_path)
        self._initialized = False
        rc = self._lib.ti_init()
        raise_for_ierr(rc, "ti_init")
        self._initialized = True

    def __enter__(self) -> "Tilib":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def set_param(self, name: str, value: float) -> None:
        if not self._initialized:
            raise TilibInitError("Tilib is not initialized (already closed?)")
        rc = self._lib.ti_set_param(name.encode("ascii"), float(value))
        raise_for_ierr(rc, f"ti_set_param({name!r}, {value!r})")

    def set_params(self, **kwargs) -> None:
        for k, v in kwargs.items():
            self.set_param(k, v)

    def run(self, ntmax: int) -> None:
        if not self._initialized:
            raise TilibInitError("Tilib is not initialized (already closed?)")
        rc = self._lib.ti_run(int(ntmax))
        raise_for_ierr(rc, f"ti_run({ntmax})")

    def get_state(self) -> TiState:
        if not self._initialized:
            raise TilibInitError("Tilib is not initialized (already closed?)")
        buf = _ffi.TiStateC()
        rc = self._lib.ti_get_state(buf)
        raise_for_ierr(rc, "ti_get_state")
        return _from_c(buf)

    def close(self) -> None:
        if not self._initialized:
            return
        rc = self._lib.ti_finalize()
        self._initialized = False
        raise_for_ierr(rc, "ti_finalize")


def _from_c(buf: "_ffi.TiStateC") -> TiState:
    nr = buf.nrmax
    nsa = buf.nsa_max
    rna = [[buf.RNA[r][s] for s in range(nsa)] for r in range(nr)]
    rta = [[buf.RTA[r][s] for s in range(nsa)] for r in range(nr)]
    rua = [[buf.RUA[r][s] for s in range(nsa)] for r in range(nr)]
    return TiState(
        nt=buf.nt, nrmax=nr, nsa_max=nsa, nsmax=buf.nsmax,
        T=buf.T,
        residual_loop_max=buf.residual_loop_max,
        icount_loop_max=buf.icount_loop_max,
        icount_mat_max=buf.icount_mat_max,
        RNA=rna, RTA=rta, RUA=rua,
        RBP=[buf.RBP[r] for r in range(nr)],
        RQP=[buf.RQP[r] for r in range(nr)],
        RJP=[buf.RJP[r] for r in range(nr)],
        ZEFF=[buf.ZEFF[r] for r in range(nr)],
        BETA=[buf.BETA[r] for r in range(nr)],
        BETAP=[buf.BETAP[r] for r in range(nr)],
    )
```

- [ ] **Step 4: `__init__.py` を Tilib も export するよう更新**

`python/tilib/__init__.py` の `__all__` に `"Tilib"` を加え、import 行を追加:

```python
"""tilib: Python wrapper around libtiapi.so."""

from .errors import (
    TilibError, TilibInitError, TilibParamError,
    TilibRunError, TilibStateError, raise_for_ierr,
)
from .state import TiState
from .tilib import Tilib

__all__ = [
    "Tilib",
    "TilibError", "TilibInitError", "TilibParamError",
    "TilibRunError", "TilibStateError",
    "TiState",
    "raise_for_ierr",
]
```

- [ ] **Step 5: テスト再実行**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest python.tilib.tests.test_tilib -v 2>&1 | tail -25
```
Expected: 4 tests PASS（または libtiapi.so 未ビルドなら SKIP）。

`test_run_and_get_state_minimal` が「ti_prep failed」で落ちる場合は `set_params` のキー欠落（必須パラメータが未設定）の可能性。`tiparm.org` のデフォルト相当を `set_params` に追加。

- [ ] **Step 6: コミット**

Run:
```bash
git add python/tilib/tilib.py python/tilib/__init__.py \
        python/tilib/tests/test_tilib.py
git commit -m "feat(tilib): add Tilib class with context manager + set_params/run/get_state"
```

---

## Task 6: 最小 README を作成

**Files:**
- Create: `python/tilib/README.md`

- [ ] **Step 1: README 作成（L-7 で詳細化、ここでは最小版）**

作成: `python/tilib/README.md`

````markdown
# tilib — Python wrapper for TASK/TI

In-process Python wrapper around `ti/libtiapi.so` using ctypes.

## Build

```bash
cd ti && make libtiapi.so
```

## Quick start

```python
from tilib import Tilib

with Tilib() as ti:
    ti.set_params(NSMAX=1, NRMAX=10, NTMAX=10,
                  NTSTEP=1, NGTSTEP=1, NGRSTEP=1)
    ti.run(ntmax=10)
    state = ti.get_state()
    print("nt =", state.nt, " T =", state.T)
```

## Library path resolution

`Tilib(lib_path=...)` argument > `TILIB_PATH` env var > `<repo>/ti/libtiapi.so`.

## Limitations (Phase L-5)

- Single-instance only (Fortran globals shared in one process).
- No MPI.
- ti_set_param supports the ~35 names registered in
  `ti/ti_param_registry.f90`. Use `PN[1]`, `MODEL_BND[1,3]` for arrays.
````

- [ ] **Step 2: コミット**

Run:
```bash
git add python/tilib/README.md
git commit -m "docs(tilib): add minimal README"
```

---

## Task 7: 全 ti テスト最終確認 + PR

- [ ] **Step 1: ti binary と L-0 が壊れていないこと**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh
```
Expected: 全テスト PASS。

- [ ] **Step 2: tilib テスト全 PASS**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest discover python/tilib/tests -v 2>&1 | tail -15
```
Expected: 7 tests PASS。

- [ ] **Step 3: 変更ファイル確認**

Run:
```bash
git diff --stat origin/develop..HEAD
```
Expected: 新規 `python/tilib/` 配下 8 ファイル。既存ファイルへの修正は無し。

- [ ] **Step 4: push と PR**

Run:
```bash
git push -u origin feature/ti-library-L5-python-wrapper
gh pr create --base develop \
  --title "feat(tilib): add Python ctypes wrapper for libtiapi.so (L-5)" \
  --body "Phase L-5: 2-layer Python wrapper (_ffi + Tilib class) for libtiapi.so. Includes 7 unittests; skips gracefully when libtiapi.so is not built. ti binary and L-0 regression unchanged."
```

---

## Dependencies

- 前段階: L-4 マージ済み（`libtiapi.so` ビルド可能）。
- 後段階: L-6 で 4 層テスト（特に Layer 1 等価性 / Layer 4 sweep）の実装。

## Fallback

| 障害 | 対処 |
|---|---|
| `OSError: libtiapi.so: cannot open shared object` | rpath 不在 → `LD_LIBRARY_PATH` を export、または `Tilib(lib_path=...)` で絶対パス指定 |
| `test_run_and_get_state_minimal` で ti_prep が失敗 | デフォルト namelist の必須項目が足りない。`tiparm.org` の最小セットを `set_params` で全部入れる |
| `numpy` が無い環境 | 本実装は標準 list を使うので numpy 不要。L-6 の sweep test で必要になれば import optional 化 |
| `ti_set_param("PN[1]", 0.7)` が ierr=2 を返す | L-3 の `parse_subscript` の動作確認。`name` の bytes encoding を `ascii` 限定にし、`b"PN[1]"` を渡せていることを確認 |
