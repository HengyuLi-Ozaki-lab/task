# FP ライブラリ化 Phase L-5: Python ラッパ (`python/fplib/`) 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-4 で生成した `fp/libfpapi.so` を `ctypes` で叩く Python パッケージ `python/fplib/` を新設する。`Fplib` クラス（context manager 対応）を `from fplib import Fplib` で import でき、5 関数 API + パラメータ辞書一括設定 + state dataclass を提供する。

**Architecture:** TR Phase L 設計 (`tr_library-design.md` セクション 6) を fp 用に転用。**2 層構成:**

```
python/fplib/
├── __init__.py          # from .fplib import Fplib, FplibError
├── _ffi.py              # ctypes 直バインド層（薄い wrapper）
├── fplib.py             # 高レベル class Fplib
├── state.py             # FpState dataclass（fp_state_c <-> Python）
├── errors.py            # FplibError 例外階層
└── tests/
    ├── __init__.py
    ├── test_ffi.py            # _ffi 層の動作確認（test_abi_link.c の Python 版）
    ├── test_fplib_class.py    # Fplib class の高レベル API 動作確認
    └── fixtures/
        └── base_iter01_params.py    # ITER 互換のパラメータ辞書
```

**Tech Stack:** Python 3.6+ (stdlib のみ: `ctypes`, `dataclasses`, `os`, `pathlib`, `unittest`)。numpy は **使わない**（依存軽量化）。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 6.1, 6.2, 6.3, 6.4。

---

## File Structure

| ファイル | 種別 | 責務 | 行数目安 |
|---|---|---|---|
| `python/fplib/__init__.py` | 新規 | re-export `Fplib`, `FplibError`, `FpState` | 5 |
| `python/fplib/_ffi.py` | 新規 | ctypes 関数定義、`fp_state_c` 構造体定義、`load_library()` ヘルパ | 130 |
| `python/fplib/fplib.py` | 新規 | `Fplib` クラス（context manager, set_param/set_params, run, get_state, close）| 100 |
| `python/fplib/state.py` | 新規 | `FpState` dataclass、`from_c(c_state)` クラスメソッド | 50 |
| `python/fplib/errors.py` | 新規 | `FplibError`, `FplibInvalidParamError`, `FplibNotInitError` 例外階層 | 25 |
| `python/fplib/tests/__init__.py` | 新規 | 空 | 0 |
| `python/fplib/tests/test_ffi.py` | 新規 | `_ffi` の単体テスト（init/finalize cycle, ctypes 型整合）| 80 |
| `python/fplib/tests/test_fplib_class.py` | 新規 | 高レベル API テスト（context manager, set_params 辞書, 配列記法, 例外）| 100 |
| `python/fplib/tests/fixtures/base_iter01_params.py` | 新規 | `ITER01_PARAMS` 辞書（fp.inITER 相当）| 35 |
| `python/fplib/README.md` | 新規（L-7 で本格） | L-5 では最低限の使い方コメント | 30 |

---

## Task 1: ブランチ作成と L-4 完了確認

- [ ] **Step 1: ブランチ**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin develop
git checkout -b feature/fp-library-L5-python-wrapper origin/develop
```

- [ ] **Step 2: `libfpapi.so` の存在確認**

Run:
```bash
cd /home/k-yoshimi/program/task/fp
make libs_pic 2>&1 | tail -3
make libfpapi.so 2>&1 | tail -3
ls -la libfpapi.so
nm -D libfpapi.so | grep ' T fp_'
```
Expected: 5 シンボル全て見える。

- [ ] **Step 3: ディレクトリ作成**

Run:
```bash
mkdir -p /home/k-yoshimi/program/task/python/fplib/tests/fixtures
```

---

## Task 2: 例外階層 `errors.py` を書く

**Files:**
- Create: `python/fplib/errors.py`

- [ ] **Step 1: ファイル作成**

```python
"""Exception hierarchy for fplib.

Maps fp_api.f90 error codes to Python exceptions:
    FP_OK            (0)   -> no exception
    FP_ERR_INVALID   (1)   -> FplibInvalidParamError
    FP_ERR_NOT_INIT  (2)   -> FplibNotInitError
    FP_ERR_CALC_FAIL (3)   -> FplibCalcFailedError
    FP_ERR_OVERFLOW  (4)   -> FplibOverflowError
"""


class FplibError(Exception):
    """Base class for all fplib errors."""


class FplibInvalidParamError(FplibError):
    """Unknown parameter name or out-of-range index."""


class FplibNotInitError(FplibError):
    """Operation requires fp_init() but it was not called."""


class FplibCalcFailedError(FplibError):
    """fp_run / fp_prep returned non-zero."""


class FplibOverflowError(FplibError):
    """NRMAX or NSAMAX exceeds compile-time limit (FP_MAX_*)."""


_CODE_TO_EXC = {
    1: FplibInvalidParamError,
    2: FplibNotInitError,
    3: FplibCalcFailedError,
    4: FplibOverflowError,
}


def raise_for_code(rc: int, context: str) -> None:
    """Translate a non-zero error code into the appropriate exception."""
    if rc == 0:
        return
    exc_cls = _CODE_TO_EXC.get(rc, FplibError)
    raise exc_cls(f"{context}: rc={rc}")
```

---

## Task 3: ctypes 層 `_ffi.py` を書く

**Files:**
- Create: `python/fplib/_ffi.py`

- [ ] **Step 1: ファイル作成**

```python
"""Low-level ctypes bindings to libfpapi.so.

Mirrors fp/fp_api.h exactly. Higher-level use should go through fplib.Fplib.
"""
import ctypes
import os
from pathlib import Path
from typing import Optional

# --- ABI constants (must match fp/fp_state.f90 / fp/fp_api.h) ---

FP_MAX_NRMAX  = 100
FP_MAX_NSAMAX = 8

FP_OK            = 0
FP_ERR_INVALID   = 1
FP_ERR_NOT_INIT  = 2
FP_ERR_CALC_FAIL = 3
FP_ERR_OVERFLOW  = 4


# --- C struct layout (mirror fp_state_c) ---

_PROFILE_2D = (ctypes.c_double * FP_MAX_NRMAX) * FP_MAX_NSAMAX

class FpStateC(ctypes.Structure):
    _fields_ = [
        ("nrmax",  ctypes.c_int),
        ("nsamax", ctypes.c_int),
        ("npmax",  ctypes.c_int),
        ("nthmax", ctypes.c_int),
        ("ntg2",   ctypes.c_int),
        ("timefp", ctypes.c_double),
        ("RNT",    _PROFILE_2D),
        ("RWT",    _PROFILE_2D),
        ("RTT",    _PROFILE_2D),
        ("RJT",    _PROFILE_2D),
        ("RPCT",   _PROFILE_2D),
        ("RPWT",   _PROFILE_2D),
    ]


# --- library loader ---

def _default_libpath() -> Path:
    """Resolve fp/libfpapi.so relative to this file."""
    here = Path(__file__).resolve().parent           # python/fplib/
    repo = here.parent.parent                         # repo root
    return repo / "fp" / "libfpapi.so"


def load_library(path: Optional[os.PathLike] = None) -> ctypes.CDLL:
    """Load libfpapi.so. Honors FPLIB_PATH env var if set, else falls back
    to fp/libfpapi.so relative to this file's repository."""
    if path is None:
        env = os.environ.get("FPLIB_PATH")
        path = Path(env) if env else _default_libpath()
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"libfpapi.so not found at {path}. "
            f"Build it with `cd fp && make libfpapi.so`, "
            f"or set FPLIB_PATH=/abs/path/to/libfpapi.so"
        )
    lib = ctypes.CDLL(str(path))

    # Bind prototypes (must match fp_api.h)
    lib.fp_init.argtypes      = []
    lib.fp_init.restype       = ctypes.c_int

    lib.fp_run.argtypes       = [ctypes.c_int]
    lib.fp_run.restype        = ctypes.c_int

    lib.fp_set_param.argtypes = [ctypes.c_char_p, ctypes.c_double]
    lib.fp_set_param.restype  = ctypes.c_int

    lib.fp_get_state.argtypes = [ctypes.POINTER(FpStateC)]
    lib.fp_get_state.restype  = ctypes.c_int

    lib.fp_finalize.argtypes  = []
    lib.fp_finalize.restype   = ctypes.c_int

    return lib
```

---

## Task 4: state dataclass `state.py` を書く

**Files:**
- Create: `python/fplib/state.py`

- [ ] **Step 1: ファイル作成**

```python
"""Pythonic view of the C `fp_state_t` struct."""
from dataclasses import dataclass, field
from typing import List

from ._ffi import FpStateC


@dataclass
class FpState:
    nrmax:  int
    nsamax: int
    npmax:  int
    nthmax: int
    ntg2:   int
    timefp: float

    # 2-D profile arrays as nested lists, indexed [nsa][nr] (0-based),
    # truncated to the runtime nrmax/nsamax (do not expose unused slots).
    RNT:  List[List[float]] = field(default_factory=list)
    RWT:  List[List[float]] = field(default_factory=list)
    RTT:  List[List[float]] = field(default_factory=list)
    RJT:  List[List[float]] = field(default_factory=list)
    RPCT: List[List[float]] = field(default_factory=list)
    RPWT: List[List[float]] = field(default_factory=list)

    @classmethod
    def from_c(cls, c: FpStateC) -> "FpState":
        nr  = c.nrmax
        nsa = c.nsamax
        def _slice(arr_2d):
            # arr_2d is FpStateC profile field, shape [FP_MAX_NSAMAX][FP_MAX_NRMAX]
            return [list(arr_2d[ns][:nr]) for ns in range(nsa)]
        return cls(
            nrmax=c.nrmax, nsamax=c.nsamax,
            npmax=c.npmax, nthmax=c.nthmax,
            ntg2=c.ntg2, timefp=float(c.timefp),
            RNT  = _slice(c.RNT),
            RWT  = _slice(c.RWT),
            RTT  = _slice(c.RTT),
            RJT  = _slice(c.RJT),
            RPCT = _slice(c.RPCT),
            RPWT = _slice(c.RPWT),
        )
```

---

## Task 5: 高レベル class `fplib.py` を書く

**Files:**
- Create: `python/fplib/fplib.py`

- [ ] **Step 1: ファイル作成**

```python
"""High-level Pythonic API for the FP Fokker-Planck solver."""
import ctypes
from typing import Mapping, Optional

from . import _ffi
from .errors import (
    FplibError, FplibInvalidParamError, FplibNotInitError, raise_for_code,
)
from .state import FpState


class Fplib:
    """In-process FP solver, callable through ctypes against libfpapi.so.

    Usage::

        with Fplib() as fp:
            fp.set_params(RR=6.5, BB=5.3, NSMAX=3, NTMAX=2,
                          PN={1: 0.8, 2: 0.4, 3: 0.4})
            fp.run(ntmax=2)
            state = fp.get_state()
            print(state.timefp, state.RNT)
    """

    def __init__(self, libpath: Optional[str] = None):
        self._lib = _ffi.load_library(libpath)
        self._initialized = False
        rc = self._lib.fp_init()
        raise_for_code(rc, "fp_init")
        self._initialized = True

    # --- context manager -----------------------------------------------------

    def __enter__(self) -> "Fplib":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # --- core API -----------------------------------------------------------

    def set_param(self, name: str, value: float) -> None:
        """Set a single fpcomm parameter. Use NAME[idx] (1-origin) for arrays."""
        if not self._initialized:
            raise FplibNotInitError("fp_init was not called")
        rc = self._lib.fp_set_param(name.encode("ascii"), float(value))
        if rc != _ffi.FP_OK:
            raise FplibInvalidParamError(
                f"fp_set_param({name!r}, {value!r}) failed (rc={rc})"
            )

    def set_params(self, **kwargs) -> None:
        """Bulk setter. Array values can be:

          - dict {idx: value}        -> set NAME[idx] = value (idx 1-origin)
          - list/tuple [v1, v2, ...] -> set NAME[1]=v1, NAME[2]=v2, ...
          - scalar                   -> set NAME = value
        """
        for k, v in kwargs.items():
            if isinstance(v, dict):
                for idx, vv in v.items():
                    self.set_param(f"{k}[{int(idx)}]", float(vv))
            elif isinstance(v, (list, tuple)):
                for i, vv in enumerate(v, start=1):
                    self.set_param(f"{k}[{i}]", float(vv))
            else:
                self.set_param(k, float(v))

    def run(self, ntmax: int) -> None:
        """Run NTMAX timesteps via fp_prep + fp_loop."""
        if not self._initialized:
            raise FplibNotInitError("fp_init was not called")
        rc = self._lib.fp_run(int(ntmax))
        raise_for_code(rc, f"fp_run({ntmax})")

    def get_state(self) -> FpState:
        """Snapshot the current fpcomm state into a Python dataclass."""
        if not self._initialized:
            raise FplibNotInitError("fp_init was not called")
        c_state = _ffi.FpStateC()
        rc = self._lib.fp_get_state(ctypes.byref(c_state))
        raise_for_code(rc, "fp_get_state")
        return FpState.from_c(c_state)

    def close(self) -> None:
        if self._initialized:
            self._lib.fp_finalize()
            self._initialized = False
```

---

## Task 6: `__init__.py` で公開 API を re-export

**Files:**
- Create: `python/fplib/__init__.py`

```python
"""TASK/FP Python wrapper (Phase L-5)."""
from .fplib import Fplib
from .state import FpState
from .errors import (
    FplibError, FplibInvalidParamError, FplibNotInitError,
    FplibCalcFailedError, FplibOverflowError,
)

__all__ = [
    "Fplib", "FpState",
    "FplibError", "FplibInvalidParamError", "FplibNotInitError",
    "FplibCalcFailedError", "FplibOverflowError",
]
```

---

## Task 7: テスト fixture と _ffi 層テスト

**Files:**
- Create: `python/fplib/tests/__init__.py` (空ファイル)
- Create: `python/fplib/tests/fixtures/base_iter01_params.py`
- Create: `python/fplib/tests/test_ffi.py`

- [ ] **Step 1: 空 init**

```bash
touch /home/k-yoshimi/program/task/python/fplib/tests/__init__.py
touch /home/k-yoshimi/program/task/python/fplib/tests/fixtures/__init__.py
```

- [ ] **Step 2: ITER fixture**

`python/fplib/tests/fixtures/base_iter01_params.py`:

```python
"""Parameter dict equivalent to test_run/inputs/fp_iter01.in.

Parameter names here must be uppercase strings that match the L-3
`fp_param_registry.f90` SELECT CASE table. All entries below are verified
against the registry with module sourcing:

  - MODELG, NSMAX, PA/PN/PNS/PTPR/PTPP -> plcomm_parm
  - NSAMAX, NSBMAX, NS_NSA, NS_NSB, MODELC, MODELR, NRMAX, NPMAX, NTHMAX,
    NTMAX, DELT, PMAX, RMIN, RMAX, PABS_WR                -> fpcomm_parm

L-3 adds explicit `USE plcomm_parm, ONLY: ...` in fp_param_registry.f90 so
both groups are settable via the single C ABI entry point.
"""

ITER01_PARAMS = {
    # --- plcomm_parm scalar int ---
    "MODELG": 3,
    "NSMAX":  3,
    # --- plcomm_parm species arrays (NSM 1-origin) ---
    "PA":  {2: 2.0, 3: 3.0},
    "PN":  {1: 0.8, 2: 0.4, 3: 0.4},
    "PNS": {1: 0.01, 2: 0.005, 3: 0.005},
    "PTPR": {1: 20.0, 2: 20.0, 3: 20.0},
    "PTPP": {1: 20.0, 2: 20.0, 3: 20.0},
    # --- fpcomm_parm mesh / radial ---
    "NRMAX": 40,
    "RMIN":  0.4,
    "RMAX":  0.8,
    "NTMAX": 2,
    "PMAX":  {1: 10.0, 2: 10.0, 3: 10.0},
    "NPMAX":  50,
    "NTHMAX": 50,
    # --- fpcomm_parm model switches ---
    "MODELC": {1: 4, 2: 4, 3: 4},
    "MODELR": 1,
    # --- fpcomm_parm time / species count / mapping ---
    "DELT":   1.0e-3,
    "NSAMAX": 1,   # registry maps UPPER -> lower-case `nsamax`
    "NSBMAX": 3,   # registry maps UPPER -> lower-case `nsbmax`
    "NS_NSA": {1: 1},          # registry maps UPPER -> lower-case `ns_nsa`
    "NS_NSB": {1: 1, 2: 2, 3: 3},
    # --- fpcomm_parm wave heating ---
    "PABS_WR": 1.0,
}
```

- [ ] **Step 3: _ffi unittest（失敗するテスト）**

`python/fplib/tests/test_ffi.py`:

```python
"""Phase L-5 _ffi-layer tests."""
import ctypes
import os
import unittest
from pathlib import Path

from fplib import _ffi


HERE = Path(__file__).resolve().parent
LIBPATH = Path(__file__).resolve().parents[3] / "fp" / "libfpapi.so"


@unittest.skipUnless(LIBPATH.exists(), f"libfpapi.so not found at {LIBPATH}")
class TestFfi(unittest.TestCase):

    def test_load_library_returns_cdll(self):
        lib = _ffi.load_library()
        self.assertIsInstance(lib, ctypes.CDLL)

    def test_init_finalize_cycle(self):
        lib = _ffi.load_library()
        rc = lib.fp_init()
        self.assertEqual(rc, _ffi.FP_OK)
        rc = lib.fp_finalize()
        self.assertEqual(rc, _ffi.FP_OK)

    def test_set_param_unknown_returns_invalid(self):
        lib = _ffi.load_library()
        try:
            lib.fp_init()
            rc = lib.fp_set_param(b"NO_SUCH_VAR", 1.0)
            self.assertEqual(rc, _ffi.FP_ERR_INVALID)
        finally:
            lib.fp_finalize()

    def test_set_param_known_returns_ok(self):
        lib = _ffi.load_library()
        try:
            lib.fp_init()
            rc = lib.fp_set_param(b"RR", 6.5)
            self.assertEqual(rc, _ffi.FP_OK)
        finally:
            lib.fp_finalize()

    def test_get_state_struct_fields(self):
        lib = _ffi.load_library()
        try:
            lib.fp_init()
            st = _ffi.FpStateC()
            rc = lib.fp_get_state(ctypes.byref(st))
            self.assertEqual(rc, _ffi.FP_OK)
            # post-init values are defaults; just verify the struct is populated
            self.assertGreaterEqual(st.nrmax, 0)
            self.assertGreaterEqual(st.nsamax, 0)
        finally:
            lib.fp_finalize()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: テスト実行**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest python.fplib.tests.test_ffi -v
```
Expected: 5 tests PASS（`libfpapi.so` 存在前提）。`libfpapi.so` 未ビルドなら全 SKIP。

---

## Task 8: 高レベル class テスト

**Files:**
- Create: `python/fplib/tests/test_fplib_class.py`

- [ ] **Step 1: テスト作成**

```python
"""Phase L-5 high-level Fplib class tests."""
import unittest
from pathlib import Path

from fplib import Fplib, FplibError, FplibInvalidParamError
from fplib.tests.fixtures.base_iter01_params import ITER01_PARAMS


LIBPATH = Path(__file__).resolve().parents[3] / "fp" / "libfpapi.so"


@unittest.skipUnless(LIBPATH.exists(), f"libfpapi.so not found at {LIBPATH}")
class TestFplibClass(unittest.TestCase):

    def test_context_manager(self):
        with Fplib() as fp:
            self.assertTrue(fp._initialized)
        # closed after with-block
        self.assertFalse(fp._initialized)

    def test_set_param_scalar(self):
        with Fplib() as fp:
            fp.set_param("RR", 7.5)  # should not raise
            fp.set_param("NTMAX", 5)

    def test_set_param_array_bracket(self):
        with Fplib() as fp:
            fp.set_param("PN[1]", 0.8)
            fp.set_param("PN[2]", 0.4)

    def test_set_params_bulk_dict(self):
        with Fplib() as fp:
            fp.set_params(
                RR=6.5, BB=5.3, NSMAX=3,
                PN={1: 0.8, 2: 0.4, 3: 0.4},
            )

    def test_set_params_bulk_list(self):
        with Fplib() as fp:
            fp.set_params(PN=[0.8, 0.4, 0.4])  # interpreted as PN[1..3]

    def test_unknown_param_raises(self):
        with Fplib() as fp:
            with self.assertRaises(FplibInvalidParamError):
                fp.set_param("NO_SUCH_VAR", 1.0)

    def test_get_state_returns_dataclass(self):
        with Fplib() as fp:
            st = fp.get_state()
            self.assertIsInstance(st.nrmax, int)
            self.assertIsInstance(st.timefp, float)

    def test_iter_params_can_be_applied(self):
        # Smoke test: applying the ITER fixture must not raise.
        # (We don't run() yet -- that can take minutes; covered in L-6 sweep.)
        with Fplib() as fp:
            fp.set_params(**ITER01_PARAMS)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: テスト実行**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest python.fplib.tests.test_fplib_class -v
```
Expected: 8 tests PASS。

---

## Task 9: README 雛形（L-7 で本格化）

**Files:**
- Create: `python/fplib/README.md`

- [ ] **Step 1: 最小 README**

`python/fplib/README.md`:

```markdown
# fplib (Phase L-5)

In-process Python wrapper for the TASK/FP Fokker-Planck solver via
ctypes against `fp/libfpapi.so`.

## Quick start

    cd fp && make libs_pic && make libfpapi.so
    cd python && python3 -m unittest fplib.tests.test_ffi -v

    >>> from fplib import Fplib
    >>> with Fplib() as fp:
    ...     fp.set_params(RR=6.5, BB=5.3, NTMAX=2)
    ...     fp.run(ntmax=2)
    ...     st = fp.get_state()
    ...     print(st.timefp, len(st.RNT))

## Files

- `_ffi.py`     ctypes layer (mirror of `fp/fp_api.h`)
- `fplib.py`    high-level `Fplib` class
- `state.py`    `FpState` dataclass
- `errors.py`   exception hierarchy

Full docs in L-7.
```

---

## Task 10: 全テスト実行 + コミット

- [ ] **Step 1: Python tests 全部**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest discover python/fplib/tests -v
```
Expected: 計 13 tests PASS（5 + 8）。

- [ ] **Step 2: 既存 fp 回帰テストが green**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh fp_iter01 fp_jt60 fp_dt1
```
Expected: 全 PASS（fp バイナリ無変更）。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/fplib/
git commit -m "feat(fp): add Python ctypes wrapper python/fplib/ for libfpapi.so"
```

---

## 受け入れ基準

- [ ] `python -c "from fplib import Fplib; print(Fplib)"` がエラーなく実行できる（`libfpapi.so` 必須）。
- [ ] `python -m unittest discover python/fplib/tests` で 13 tests 全 PASS。
- [ ] `with Fplib() as fp: fp.set_param("RR", 6.5)` の使い方が動く。
- [ ] `fp_iter01/jt60/dt1` の既存回帰テスト全 PASS。
- [ ] `FPLIB_PATH` 環境変数で `libfpapi.so` の場所を上書きできる。

## 撤退条件 / フォールバック

| 状況 | 対応 |
|---|---|
| `ctypes.CDLL` が `libfpapi.so` をロードできない（依存 `.so` 不足） | `LD_LIBRARY_PATH` 案内を README に追加、または L-4 で `-Wl,-rpath` を入れ直す |
| `FpStateC` の `_PROFILE_2D` shape が `fp_api.h` と一致せず get_state がゴミを返す | `nm -D` と `pahole` で C struct sizeof を fortran 側と突き合わせ修正 |
| ITER fixture を `set_params` した後 `run()` で abort | `set_param` がパラメータを受け取れていても `fp_prep` 内で必須変数が未設定なケース。L-5 では `set_params` の単体検証だけ行い、`run()` 込みは L-6 で実施する |
| Python パッケージのインストール方式（pip vs PYTHONPATH） | L-5 では `python -m unittest python.fplib.tests.*` 方式（PYTHONPATH なし）。`setup.py`/`pyproject.toml` は L-7 で検討 |

## 依存

- 上流: L-4 (`libfpapi.so`)
- 後続: L-6 (4 層テスト)、L-7 (ドキュメント)
