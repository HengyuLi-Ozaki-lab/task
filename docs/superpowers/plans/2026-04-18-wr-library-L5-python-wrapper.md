# WR ライブラリ化 Phase L-5: Python ラッパ (`python/wrlib/`) 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-4 で出来た `libwrapi.so` を Python から自然に使える形にする。`python/wrlib/` パッケージを新設し、ctypes で C ABI を呼ぶ低レベル `_ffi.py` と、Pythonic な `Wrlib` クラスを提供する `wrlib.py` の 2 層構成にする。`with Wrlib() as wr: ... ` パターンと辞書一括セット (`wr.set_params(RR=6.2, BB=5.3)`) を提供。

**Architecture:** TR の Phase L-5 と完全に同じ 2 層構成（`_ffi.py` + `wrlib.py`）。`state.py` で `wr_state_t` を Python `dataclass` に変換し、`numpy` のオプション依存（あれば numpy 配列、無ければ Python list）。`errors.py` で `WrlibError`、`WrlibNotInitialized`, `WrlibInvalidParam`, `WrlibCalculationFailed` の例外階層。標準ライブラリのみで動かすが、numpy が import 出来れば自動的に numpy 配列を返す（テストは標準ライブラリ unittest）。

**Tech Stack:** Python 3.8+, `ctypes`, `dataclasses`（標準ライブラリ）, `numpy`（任意）, unittest。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 6 と Phase L-5。

---

## 既存 Python レイアウト

`python/` ディレクトリは現時点では存在しない可能性が高い（TR L-5 が先行しているなら `python/trlib/` がある）。`ls /home/k-yoshimi/program/task/python/` で確認し、無ければ新規作成。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/__init__.py` | 新規（無ければ） | top-level package marker |
| `python/wrlib/__init__.py` | 新規 | `from .wrlib import Wrlib`, `from .errors import WrlibError, ...` |
| `python/wrlib/_ffi.py` | 新規 | ctypes 低レベル FFI：`load_lib(path)`, prototypes, `WrStateC` ctypes Structure |
| `python/wrlib/state.py` | 新規 | `WrState` dataclass：Python 側の dimensions/scalars/rays/profile_rs/profile_rl |
| `python/wrlib/wrlib.py` | 新規 | `Wrlib` class：context manager, set_param/set_params/run/get_state |
| `python/wrlib/errors.py` | 新規 | 例外階層 |
| `python/wrlib/tests/__init__.py` | 新規 | empty |
| `python/wrlib/tests/test_ffi.py` | 新規 | ctypes 直叩きテスト |
| `python/wrlib/tests/test_wrlib.py` | 新規 | Wrlib class テスト |
| `python/wrlib/README.md` | 新規 | 使用例とインストール手順（L-7 で詳細化、本フェーズは雛形のみ） |

**方針:**
- `numpy` は **オプション**：未インストールなら Python list を返す。`import numpy as np` を try/except で囲む。
- 既定で `WRLIB_PATH` 環境変数からライブラリパスを取得、なければ `../wr/libwrapi.so` を相対パスで探す。
- 例外は `WrlibError` を基底クラスとして 3 種：`WrlibNotInitialized` (ierr=2), `WrlibInvalidParam` (ierr=1), `WrlibCalculationFailed` (ierr=3)。

---

## Task 1: ブランチ作成と初期構造

**Files:**
- Create: `python/__init__.py`
- Create: `python/wrlib/__init__.py`
- Create: `python/wrlib/tests/__init__.py`

- [ ] **Step 1: develop 最新 + ブランチ作成**

Run:
```bash
cd /home/k-yoshimi/program/task
git checkout develop
git pull origin develop
git checkout -b feature/wr-library-L5-python
```

- [ ] **Step 2: ディレクトリ作成**

Run:
```bash
mkdir -p /home/k-yoshimi/program/task/python/wrlib/tests
```

- [ ] **Step 3: 空マーカー作成**

Create `/home/k-yoshimi/program/task/python/__init__.py` (empty file).
Create `/home/k-yoshimi/program/task/python/wrlib/__init__.py`:
```python
"""TASK/WR Python wrapper (Phase L-5)."""
from .wrlib import Wrlib
from .state import WrState
from .errors import (
    WrlibError,
    WrlibNotInitialized,
    WrlibInvalidParam,
    WrlibCalculationFailed,
)

__all__ = [
    "Wrlib", "WrState",
    "WrlibError", "WrlibNotInitialized",
    "WrlibInvalidParam", "WrlibCalculationFailed",
]
```

Create `/home/k-yoshimi/program/task/python/wrlib/tests/__init__.py` (empty file).

- [ ] **Step 4: マーカーコミット（このコミットは __init__.py のみで動かない、後続コミットで成立させる）**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/__init__.py python/wrlib/__init__.py python/wrlib/tests/__init__.py
git commit -m "chore(wrlib): scaffold python/wrlib package"
```

---

## Task 2: `errors.py` を実装

**Files:**
- Create: `python/wrlib/errors.py`

- [ ] **Step 1: 例外階層を実装**

Create `/home/k-yoshimi/program/task/python/wrlib/errors.py`:
```python
"""Exception hierarchy for the wrlib package."""


class WrlibError(Exception):
    """Base class for all wrlib errors."""

    def __init__(self, message: str, ierr: int = -1):
        super().__init__(message)
        self.ierr = ierr


class WrlibInvalidParam(WrlibError):
    """C ABI returned ierr=1 (unknown name or out-of-range index)."""

    def __init__(self, name: str):
        super().__init__(f"invalid parameter: {name}", ierr=1)
        self.name = name


class WrlibNotInitialized(WrlibError):
    """C ABI returned ierr=2 (called before wr_init or after wr_finalize)."""

    def __init__(self):
        super().__init__("wrlib not initialized; call wr_init() first", ierr=2)


class WrlibCalculationFailed(WrlibError):
    """C ABI returned ierr=3 (wr_setup or wr_exec reported failure)."""

    def __init__(self, hint: str = ""):
        msg = "wrlib calculation failed"
        if hint:
            msg = f"{msg}: {hint}"
        super().__init__(msg, ierr=3)


def raise_for_ierr(ierr: int, *, name: str = "", hint: str = "") -> None:
    """Map a non-zero ierr to the appropriate exception."""
    if ierr == 0:
        return
    if ierr == 1:
        raise WrlibInvalidParam(name)
    if ierr == 2:
        raise WrlibNotInitialized()
    if ierr == 3:
        raise WrlibCalculationFailed(hint)
    raise WrlibError(f"unknown error code from libwrapi.so: {ierr}", ierr=ierr)
```

- [ ] **Step 2: 軽い構文チェック**

Run:
```bash
python3 -c "from python.wrlib.errors import WrlibError, raise_for_ierr; raise_for_ierr(1, name='RR')"
```
Expected: `wrlib.errors.WrlibInvalidParam: invalid parameter: RR` を raise。

(モジュール解決のため作業ディレクトリは `/home/k-yoshimi/program/task` から実行)

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrlib/errors.py
git commit -m "feat(wrlib): add exception hierarchy"
```

---

## Task 3: `state.py` を実装

**Files:**
- Create: `python/wrlib/state.py`

- [ ] **Step 1: dataclass を定義**

Create `/home/k-yoshimi/program/task/python/wrlib/state.py`:
```python
"""Python-friendly view of wr_state_t."""
from dataclasses import dataclass, field
from typing import Any, List

from ._ffi import WR_MAX_NRAY_EQ

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
class WrState:
    """High-level view of wr_state_t.

    Dimensions match the active runtime values; arrays are sliced to the
    active range (no zero-padding leak from the fixed-size C struct).
    """
    nraymax: int
    nrsmax: int
    nrlmax: int
    pos_pwrmax_rs: float
    pwrmax_rs: float
    pos_pwrmax_rl: float
    pwrmax_rl: float
    nstp_end: List[int] = field(default_factory=list)
    pos_pwrmax_rs_nray: Any = None
    pwrmax_rs_nray:     Any = None
    pos_pwrmax_rl_nray: Any = None
    pwrmax_rl_nray:     Any = None
    rays_end:           Any = None  # shape (nraymax, WR_MAX_NRAY_EQ) = (nraymax, 9)
    pos_nrs:            Any = None
    pwr_nrs:            Any = None
    pos_nrl:            Any = None
    pwr_nrl:            Any = None

    @classmethod
    def from_c(cls, c_state) -> "WrState":
        """Convert a ctypes WrStateC struct to a WrState dataclass."""
        n = int(c_state.nraymax)
        nrs = int(c_state.nrsmax)
        nrl = int(c_state.nrlmax)
        # ctypes arrays slice naturally; convert to list/numpy.
        # rays_end second dim is WR_MAX_NRAY_EQ (=NEQ+1=9) to mirror Fortran RAYS(0:NEQ,...)
        rays_end_2d = [
            [float(c_state.rays_end[j][k]) for k in range(WR_MAX_NRAY_EQ)] for j in range(n)
        ]
        if _HAVE_NUMPY:
            rays_end_arr = np.asarray(rays_end_2d, dtype=float)
        else:
            rays_end_arr = rays_end_2d
        return cls(
            nraymax=n,
            nrsmax=nrs,
            nrlmax=nrl,
            pos_pwrmax_rs=float(c_state.pos_pwrmax_rs),
            pwrmax_rs=float(c_state.pwrmax_rs),
            pos_pwrmax_rl=float(c_state.pos_pwrmax_rl),
            pwrmax_rl=float(c_state.pwrmax_rl),
            nstp_end=[int(c_state.nstp_end[j]) for j in range(n)],
            pos_pwrmax_rs_nray=_to_array([c_state.pos_pwrmax_rs_nray[j] for j in range(n)]),
            pwrmax_rs_nray    =_to_array([c_state.pwrmax_rs_nray[j]     for j in range(n)]),
            pos_pwrmax_rl_nray=_to_array([c_state.pos_pwrmax_rl_nray[j] for j in range(n)]),
            pwrmax_rl_nray    =_to_array([c_state.pwrmax_rl_nray[j]     for j in range(n)]),
            rays_end          =rays_end_arr,
            pos_nrs=_to_array([c_state.pos_nrs[j] for j in range(nrs)]),
            pwr_nrs=_to_array([c_state.pwr_nrs[j] for j in range(nrs)]),
            pos_nrl=_to_array([c_state.pos_nrl[j] for j in range(nrl)]),
            pwr_nrl=_to_array([c_state.pwr_nrl[j] for j in range(nrl)]),
        )
```

- [ ] **Step 2: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrlib/state.py
git commit -m "feat(wrlib): add WrState dataclass with C-struct adapter"
```

---

## Task 4: `_ffi.py` を実装

**Files:**
- Create: `python/wrlib/_ffi.py`

- [ ] **Step 1: ctypes Structure と関数プロトタイプ**

Create `/home/k-yoshimi/program/task/python/wrlib/_ffi.py`:
```python
"""ctypes-level FFI for libwrapi.so.

Mirror of wr/wr_api.h. WR_MAX_NRAYMAX, WR_MAX_NRSMAX, WR_MAX_NRLMAX must
match the values in the header.
"""
import ctypes
import os
from pathlib import Path

WR_MAX_NRAYMAX = 100
WR_MAX_NRSMAX  = 200
WR_MAX_NRLMAX  = 400
# Must equal NEQ+1 in wrcomm.f90 (NEQ=8 ⇒ 9). Mirrors WR_MAX_NRAY_EQ in wr_api.h.
WR_MAX_NRAY_EQ = 9


class WrStateC(ctypes.Structure):
    _fields_ = [
        ("nraymax",            ctypes.c_int),
        ("nrsmax",             ctypes.c_int),
        ("nrlmax",             ctypes.c_int),
        ("pos_pwrmax_rs",      ctypes.c_double),
        ("pwrmax_rs",          ctypes.c_double),
        ("pos_pwrmax_rl",      ctypes.c_double),
        ("pwrmax_rl",          ctypes.c_double),
        ("nstp_end",           ctypes.c_int    * WR_MAX_NRAYMAX),
        ("pos_pwrmax_rs_nray", ctypes.c_double * WR_MAX_NRAYMAX),
        ("pwrmax_rs_nray",     ctypes.c_double * WR_MAX_NRAYMAX),
        ("pos_pwrmax_rl_nray", ctypes.c_double * WR_MAX_NRAYMAX),
        ("pwrmax_rl_nray",     ctypes.c_double * WR_MAX_NRAYMAX),
        ("rays_end",           (ctypes.c_double * WR_MAX_NRAY_EQ) * WR_MAX_NRAYMAX),
        ("pos_nrs",            ctypes.c_double * WR_MAX_NRSMAX),
        ("pwr_nrs",            ctypes.c_double * WR_MAX_NRSMAX),
        ("pos_nrl",            ctypes.c_double * WR_MAX_NRLMAX),
        ("pwr_nrl",            ctypes.c_double * WR_MAX_NRLMAX),
    ]


def _default_lib_path() -> Path:
    """Find libwrapi.so. Priority: WRLIB_PATH env > <repo>/wr/libwrapi.so."""
    env = os.environ.get("WRLIB_PATH")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    # python/wrlib/_ffi.py -> python/wrlib -> python -> repo root
    repo_root = here.parents[2]
    return repo_root / "wr" / "libwrapi.so"


def load_lib(path: Path = None) -> ctypes.CDLL:
    """Load libwrapi.so and configure prototypes."""
    if path is None:
        path = _default_lib_path()
    if not Path(path).exists():
        raise FileNotFoundError(
            f"libwrapi.so not found at {path}. Build with `make libwrapi.so` "
            f"in wr/, or set WRLIB_PATH env var."
        )
    lib = ctypes.CDLL(str(path))

    lib.wr_init.argtypes = []
    lib.wr_init.restype  = ctypes.c_int

    lib.wr_run.argtypes = [ctypes.c_int]
    lib.wr_run.restype  = ctypes.c_int

    lib.wr_set_param.argtypes = [ctypes.c_char_p, ctypes.c_double]
    lib.wr_set_param.restype  = ctypes.c_int

    lib.wr_get_state.argtypes = [ctypes.POINTER(WrStateC)]
    lib.wr_get_state.restype  = ctypes.c_int

    lib.wr_finalize.argtypes = []
    lib.wr_finalize.restype  = ctypes.c_int
    return lib
```

- [ ] **Step 2: 軽い import チェック**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -c "from python.wrlib._ffi import WrStateC, load_lib; import ctypes; print(ctypes.sizeof(WrStateC), 'bytes')"
```
Expected: 数千バイト程度の数値が表示される。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrlib/_ffi.py
git commit -m "feat(wrlib): add ctypes FFI (_ffi.py) for libwrapi.so"
```

---

## Task 5: `wrlib.py`（高レベル class）を実装

**Files:**
- Create: `python/wrlib/wrlib.py`

- [ ] **Step 1: Wrlib class を実装**

Create `/home/k-yoshimi/program/task/python/wrlib/wrlib.py`:
```python
"""High-level Wrlib API."""
from pathlib import Path
from typing import Optional

from . import _ffi
from .errors import raise_for_ierr, WrlibError
from .state import WrState


class Wrlib:
    """Pythonic interface to libwrapi.so.

    Usage:
        with Wrlib() as wr:
            wr.set_params(RR=6.2, BB=5.3, NSMAX=2)
            wr.set_param("RFIN[1]", 5.0e3)
            wr.run(nray_request=1)
            state = wr.get_state()
            print(state.pwrmax_rs)
    """

    def __init__(self, lib_path: Optional[Path] = None):
        self._lib = _ffi.load_lib(lib_path)
        self._initialized = False
        self._executed = False

    # ---- lifecycle ----
    def open(self) -> "Wrlib":
        ierr = self._lib.wr_init()
        raise_for_ierr(ierr)
        self._initialized = True
        return self

    def close(self) -> None:
        if self._initialized:
            ierr = self._lib.wr_finalize()
            self._initialized = False
            self._executed = False
            raise_for_ierr(ierr)

    def __enter__(self) -> "Wrlib":
        return self.open()

    def __exit__(self, exc_type, exc_val, tb) -> None:
        self.close()

    # ---- parameter setting ----
    def set_param(self, name: str, value: float) -> None:
        ierr = self._lib.wr_set_param(name.encode("utf-8"), float(value))
        raise_for_ierr(ierr, name=name)

    def set_params(self, **kwargs) -> None:
        for k, v in kwargs.items():
            self.set_param(k, v)

    # ---- run / get_state ----
    def run(self, nray_request: int = 0) -> None:
        ierr = self._lib.wr_run(int(nray_request))
        raise_for_ierr(ierr, hint="wr_run")
        self._executed = True

    def get_state(self) -> WrState:
        if not self._executed:
            raise WrlibError("get_state() called before run()", ierr=2)
        c_state = _ffi.WrStateC()
        ierr = self._lib.wr_get_state(c_state)
        raise_for_ierr(ierr, hint="wr_get_state")
        return WrState.from_c(c_state)
```

- [ ] **Step 2: import チェック**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -c "from python.wrlib import Wrlib; print(Wrlib)"
```
Expected: `<class 'python.wrlib.wrlib.Wrlib'>` 等が表示。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrlib/wrlib.py
git commit -m "feat(wrlib): add high-level Wrlib class with context manager"
```

---

## Task 6: 軽量 unittest を追加

**Files:**
- Create: `python/wrlib/tests/test_ffi.py`
- Create: `python/wrlib/tests/test_wrlib.py`

- [ ] **Step 1: ctypes 直叩き smoke test**

Create `/home/k-yoshimi/program/task/python/wrlib/tests/test_ffi.py`:
```python
"""Low-level ctypes FFI tests (require libwrapi.so to be built)."""
import ctypes
import os
import unittest
from pathlib import Path

from python.wrlib import _ffi


def _lib_path() -> Path:
    env = os.environ.get("WRLIB_PATH")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    return here.parents[3] / "wr" / "libwrapi.so"


@unittest.skipUnless(_lib_path().exists(), "libwrapi.so not built")
class TestFfi(unittest.TestCase):
    def setUp(self):
        self.lib = _ffi.load_lib(_lib_path())

    def tearDown(self):
        self.lib.wr_finalize()

    def test_init_finalize(self):
        self.assertEqual(self.lib.wr_init(), 0)
        self.assertEqual(self.lib.wr_init(), 0)  # idempotent
        self.assertEqual(self.lib.wr_finalize(), 0)
        # After finalize, set_param should return 2 (not initialized).
        self.assertEqual(self.lib.wr_set_param(b"RR", 6.2), 2)

    def test_set_param_invalid_name(self):
        self.assertEqual(self.lib.wr_init(), 0)
        self.assertEqual(self.lib.wr_set_param(b"BOGUS", 0.0), 1)

    def test_get_state_before_run(self):
        self.assertEqual(self.lib.wr_init(), 0)
        st = _ffi.WrStateC()
        self.assertEqual(self.lib.wr_get_state(ctypes.byref(st)), 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Wrlib class テスト**

Create `/home/k-yoshimi/program/task/python/wrlib/tests/test_wrlib.py`:
```python
"""High-level Wrlib class tests (require libwrapi.so to be built)."""
import os
import unittest
from pathlib import Path

from python.wrlib import (
    Wrlib, WrlibInvalidParam, WrlibNotInitialized, WrState,
)


def _lib_path() -> Path:
    env = os.environ.get("WRLIB_PATH")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    return here.parents[3] / "wr" / "libwrapi.so"


def _setup_iter_lhcd(wr: Wrlib) -> None:
    wr.set_params(MODELG=2, RR=6.2, RA=2.0, BB=5.3, NSMAX=2)
    for i, (pa, pz, pn, pns, pt, pts) in enumerate([(2.0,1.0,1.0,0.1,10.0,0.5),
                                                    (1.0,-1.0,1.0,0.1,10.0,0.5)],
                                                   start=1):
        wr.set_param(f"PA[{i}]",  pa)
        wr.set_param(f"PZ[{i}]",  pz)
        wr.set_param(f"PN[{i}]",  pn)
        wr.set_param(f"PNS[{i}]", pns)
        wr.set_param(f"PTPR[{i}]",pt); wr.set_param(f"PTPP[{i}]", pt)
        wr.set_param(f"PTS[{i}]", pts)
    wr.set_params(NRAYMAX=1, NSTPMAX=1000, MDLWRI=101, MDLWRQ=0,
                  SMAX=5.0, DELS=0.05)
    wr.set_params(**{"RFIN[1]": 5.0e3, "RPIN[1]": 8.0, "ZPIN[1]": 0.0,
                     "PHIIN[1]": 0.0, "ANGZIN[1]": 0.0, "ANGPHIN[1]": 30.0,
                     "UUIN[1]": 1.0, "MODEWIN[1]": 1})


@unittest.skipUnless(_lib_path().exists(), "libwrapi.so not built")
class TestWrlib(unittest.TestCase):
    def test_context_manager(self):
        with Wrlib(lib_path=_lib_path()) as wr:
            self.assertIsInstance(wr, Wrlib)

    def test_invalid_param_raises(self):
        with Wrlib(lib_path=_lib_path()) as wr:
            with self.assertRaises(WrlibInvalidParam):
                wr.set_param("BOGUS", 0.0)

    def test_get_state_before_run_raises(self):
        with Wrlib(lib_path=_lib_path()) as wr:
            with self.assertRaises(Exception):
                wr.get_state()

    def test_iter_lhcd_run(self):
        with Wrlib(lib_path=_lib_path()) as wr:
            _setup_iter_lhcd(wr)
            wr.run(nray_request=0)
            st = wr.get_state()
            self.assertIsInstance(st, WrState)
            self.assertEqual(st.nraymax, 1)
            self.assertGreater(st.nrsmax, 0)
            self.assertGreater(st.nrlmax, 0)
            self.assertEqual(len(st.nstp_end), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: テスト実行**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest python.wrlib.tests.test_ffi python.wrlib.tests.test_wrlib -v
```
Expected:
- `libwrapi.so` が存在しない場合は全テスト skipped。
- 存在する場合は全 PASS。

- [ ] **Step 4: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrlib/tests/test_ffi.py python/wrlib/tests/test_wrlib.py
git commit -m "test(wrlib): add unittest-based ffi/class tests"
```

---

## Task 7: 簡易 README（雛形のみ、L-7 で本体）

**Files:**
- Create: `python/wrlib/README.md`

- [ ] **Step 1: 最小 README**

Create `/home/k-yoshimi/program/task/python/wrlib/README.md`:
```markdown
# wrlib — Python wrapper for TASK/WR

Phase L-5 minimum viable package. Full documentation lands in L-7.

## Quick start

```bash
cd /path/to/task/wr && make libwrapi.so
cd /path/to/task
python3 -c "
from python.wrlib import Wrlib
with Wrlib() as wr:
    wr.set_params(MODELG=2, RR=6.2, BB=5.3, NRAYMAX=1, MDLWRI=101)
    wr.set_param('RFIN[1]', 5.0e3)
    wr.run(0)
    print(wr.get_state().pwrmax_rs)
"
```

## Library lookup

`WRLIB_PATH` env var > `<repo>/wr/libwrapi.so` (default).
```

- [ ] **Step 2: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrlib/README.md
git commit -m "docs(wrlib): add minimal README (Phase L-5 stub for L-7)"
```

---

## 完了基準

- [ ] `python/wrlib/` パッケージが作られ、`from python.wrlib import Wrlib` で import 可能
- [ ] `_ffi.py` の `WrStateC` のサイズが `wr_api.h` の `wr_state_t` と一致（ctypes の sizeof で検証）
- [ ] `with Wrlib() as wr: wr.set_params(...).run(0).get_state()` が動く
- [ ] unittest 全件 PASS（`libwrapi.so` 未ビルド時は skip）
- [ ] 例外階層が機能（`WrlibInvalidParam, WrlibNotInitialized, WrlibCalculationFailed`）
- [ ] numpy のオプション依存：未インストールでも import 可能

## 撤退条件

- ctypes の Structure サイズが C 側と合わない → `_fields_` の順序、padding、`WR_MAX_*` 値を再確認
- `dlopen` で symbol not found → `WRLIB_PATH` を絶対パスで指定し、`ldd` で依存解決を再確認
- numpy ありで配列形状が壊れる → `state.py` の `_to_array` を `dtype=float` 固定に

## 依存

- 前提: L-4 完了（`wr/libwrapi.so` がビルド可能）
- 後続: L-6 (4 層テスト)、L-7 (README + notebook)
