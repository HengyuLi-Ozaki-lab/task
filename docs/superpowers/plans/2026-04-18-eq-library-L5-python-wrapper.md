# EQ ライブラリ化 Phase L-5: Python Wrapper (`python/eqlib/`) 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-4 で生成された `eq/libeqapi.so` を `ctypes` で呼び、Pythonic な `Eq` context-manager クラスとして公開する `python/eqlib/` パッケージを新設する。最小限の `set_param / run / get_state` ライフサイクルが動くことを `unittest` で確認（4 層フルテストは L-6）。

**Architecture:** TR の `python/trlib/` 設計と同型の 2 層構成:
- **下層** `_ffi.py` — `ctypes.CDLL` で `libeqapi.so` を load し、`EqStateC` Structure と 5 関数 prototype を定義。
- **上層** `eqlib.py` — `Eq` クラス（context manager, `set_params(**kwargs)` 一括 set, `set_param("RPS[i,j]", v)` 配列要素 set, `run(ntmax)`, `get_state()`, `close()`)。
- `state.py` — `EqState` dataclass（plain Python types; numpy なしで list-of-list）と `to_dict()` シリアライザ。
- `errors.py` — `EqLibError` 基底 + `EqLibInitError / EqLibParamError / EqLibStateError / EqLibRunError` 階層。

Python は **標準ライブラリのみ**（`ctypes`, `dataclasses`, `os`, `pathlib`, `unittest`）。numpy はオプショナル扱いにもできるが本 L-5 では未導入（TR L-5 / TI L-5 と合わせる）。

**Tech Stack:** Python 3.8+, stdlib only, `eq/libeqapi.so`（L-4 成果物）。

**出典:**
- `docs/superpowers/specs/2026-04-17-tr-library-design.md` §6 (Python ラッパ設計), §A.10 (2 層構成採用根拠), §4.2 (構造体レイアウト)
- canonical template: `python/trlib/_ffi.py`, `python/trlib/trlib.py`, `python/trlib/state.py`, `python/trlib/errors.py`
- 依存 plan: `docs/superpowers/plans/2026-04-18-tr-library-L5-python-wrapper.md`、`docs/superpowers/plans/2026-04-18-ti-library-L5-python-wrapper.md`、`docs/superpowers/plans/2026-04-18-wr-library-L5-python-wrapper.md`

---

## Prerequisites

| Phase | 状況 | 目的 |
|---|---|---|
| **L-0** | マージ済み | baseline fixtures |
| **L-1** plan | merge 済み / draft 修正待ち | SRCS_CORE/GRAPHICS/MENU 3 分割 |
| **L-2** plan | 未マージ | C ABI (`eq_api.f90` + `eq_api.h`): 5 関数と `eq_state_t` Structure |
| **L-3** plan | 未マージ | `eq_param_registry.f90` + 配列サブスクリプト `[i]`/`[i,j]` parser |
| **L-4** plan | 未マージ（本 plan と同時提出） | `libeqapi.so` ビルド + `eq_api_check_so` PASS |
| **f90 modernization** | in-progress | `equcom.f90`, `equread.f90`, `eqlib.f90` 等 module 化済み。本 L-5 は純 Python 側なので影響なし |

Reference: `L-4 plan 実装済み → libeqapi.so が `make libeqapi.so` で build 可能`、5 C シンボル (`eq_init/eq_run/eq_set_param/eq_get_state/eq_finalize`) が export されている。

---

## State Fields: What `EqState` Exposes

`eq/equcom.f90` (module `equ_params`) と `eq/eqcom0.inc`/`eqcom1.inc` を元に、Python 側から見える EQ 状態を列挙:

### コンパイル時定数（`eqcom0.inc`）
```
NRGM = 513    ! radial grid on (R,Z)
NZGM = 513    ! vertical grid on (R,Z)
NPSM = 513    ! psi-surface count
NRVM = 1001   ! volume-average rho count
NTVM = 1025   ! time-variable rho count
NSUM = 1343   ! surface points
NRM  = 1001   ! psi-mesh radial count  ← used by RPS, ZPS
NTHM = 2049   ! poloidal angle count   ← used by RPS, ZPS
```

### スカラー（`eqcom1.inc` COMMON /EQGLB1/ /EQGLB2/）
- `raxis, zaxis`（磁気軸座標）
- `psi0, psipa, psita, redge`
- `pvol, raave`（プラズマ体積、平均小半径）
- `betat, betap`（トロイダル/ポロイダル β）
- `qaxis, qsurf`（磁気軸 / 境界 q）
- `tj`（fraction）, `psiitb`, `idcalv`

### プロファイル（`eqcom1.inc` COMMON /EQOUT1../EQAVT7/）
- `rg(NRGM), zg(NZGM)`（R,Z 格子）
- `psirz(NRGM, NZGM)`（2D 磁気面）
- `psips(NPSM), ppps(NPSM), ttps(NPSM), dppps(NPSM), qqps(NPSM)`（psi-surface プロファイル）
- `psipv(NRVM), rhot(NRVM), qpv(NRVM), ttv(NRVM), rsv(NRVM), vpv(NRVM)`（flux-surface 平均量）

### θ-ρ 表（`eqcom3.inc` COMMON /EQWMU1/）
- `rps(NTHM+1, NRM), zps(NTHM+1, NRM)`（磁気面の θ,ρ 表現。R = rps(θ,ρ), Z = zps(θ,ρ)）
- `drpsi, dzpsi`（微分量）

### L-5 で公開する最小セット

`EqStateC` / `EqState` のフィールドは `eq_api.h` (L-2) の `eq_state_t` 定義に従う。設計として:

- **スカラー 10 個**: `raxis, zaxis, psi0, psipa, psita, pvol, betat, betap, qaxis, qsurf`
- **次元スカラー**: `nrgmax, nzgmax, npsmax, nrmax, nthmax`（コンパイル時最大値ではなく runtime アクティブ値）
- **1D 配列**:
  - `rg[NRGM], zg[NZGM]`
  - `psips[NPSM], ppps[NPSM], ttps[NPSM], qqps[NPSM]`
  - `psipv[NRVM], qpv[NRVM], rhot[NRVM]`
- **2D 配列（行優先 C レイアウト, Fortran 側は列優先）**:
  - `psirz[NRGM][NZGM]`
  - `rps[NRM][NTHM+1]` ← 注: Fortran `RPS(NTHMP, NRM)` の列優先 = C `rps[NRM][NTHMP]` の行優先で同じメモリ並び
  - `zps[NRM][NTHM+1]`

**メモリ使用量見積もり:** NRGM=513 で `psirz` 約 2MB（double）、`rps`/`zps` 各 NTHMP×NRM=2050×1001≈16MB → 34MB/struct。ctypes Structure に全部詰むと Python 側のアロケーションコストが気になるため、**L-5 では `psirz`/`rps`/`zps` は含めず**、スカラー + 1D 配列のみに絞る方針でもよい（設計書 §4.2 で再確認）。本 plan は conservative に「全フィールドを含める」設計で書く（必要なら L-5 実装中に縮小）。

---

## File Structure

このフェーズで作成・変更するファイル:

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/__init__.py` | 新規（未作成時のみ） | top-level package marker |
| `python/eqlib/__init__.py` | 新規 | `from .eqlib import Eq`, `from .state import EqState`, errors の re-export |
| `python/eqlib/_ffi.py` | 新規 | `ctypes.CDLL` load、`EqStateC` Structure（`eq_api.h` と 1:1 対応）、5 関数 prototype、`load_library(path)` |
| `python/eqlib/state.py` | 新規 | `EqState` dataclass、`from_c()` クラスメソッド、`to_dict()` シリアライザ |
| `python/eqlib/errors.py` | 新規 | 例外階層（`EqLibError` + 4 サブクラス）、`raise_for_ierr` ヘルパー |
| `python/eqlib/eqlib.py` | 新規 | `Eq` class（context manager、`set_param`/`set_params`/`run`/`get_state`/`close`） |
| `python/eqlib/tests/__init__.py` | 新規 | 空 |
| `python/eqlib/tests/test_ffi.py` | 新規 | `_ffi` 層の unittest（init/finalize cycle、set_param 戻り値、構造体サイズ） |
| `python/eqlib/tests/test_eqlib.py` | 新規 | `Eq` クラスの unittest（with 構文、set_params 辞書、配列 `set_param("RPS[1,1]", v)`、run + get_state） |
| `python/eqlib/README.md` | 新規 | 最小使用例（詳細は L-7 で拡充） |

**方針:**
- パッケージ場所は既存の `python/{trlib,tilib,wrlib,fplib}` と並列に `python/eqlib/`。
- ライブラリパス優先順: `Eq(lib_path=...)` 引数 > `EQLIB_PATH` 環境変数 > `<repo>/eq/libeqapi.so`。
- 2D 配列は Python list of list（numpy なし）。L-6 の sweep で numpy 必要になれば optional import 化。
- `libeqapi.so` 未ビルド時は全テスト `@unittest.skipUnless(...)` で skip（L-4 完了前でも import は通す）。

---

## Task 1: ブランチと前提確認

- [ ] **Step 1: L-4 merge 確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git fetch origin develop
git log --oneline origin/develop | grep -iE "eq.*L-4|eq.*libeqapi" | head -3
ls eq/libeqapi.so 2>&1 || (cd eq && make libeqapi.so 2>&1 | tail -5)
file eq/libeqapi.so
nm -D eq/libeqapi.so | grep -E " T (eq_init|eq_run|eq_set_param|eq_get_state|eq_finalize)$"
```
Expected: L-4 merge 済み、`libeqapi.so` が存在、5 C シンボル export 済み。

- [ ] **Step 2: ブランチ作成**

Run:
```bash
git checkout -b feature/eq-library-L5-python origin/develop
mkdir -p python/eqlib/tests
```

- [ ] **Step 3: Python バージョン確認 + ctypes load テスト**

Run:
```bash
python3 --version
python3 -c "import ctypes; print(ctypes.CDLL('/home/k-yoshimi/program/task-private/eq/libeqapi.so'))"
```
Expected: Python 3.8+、`<CDLL '...', handle ...>`。

- [ ] **Step 4: マーカーコミット**

Run:
```bash
git commit --allow-empty -m "chore(eqlib): start Phase L-5 python wrapper"
```

---

## Task 2: `errors.py` — 例外階層

**Files:**
- Create: `python/eqlib/errors.py`

- [ ] **Step 1: 作成**

Create `/home/k-yoshimi/program/task-private/python/eqlib/errors.py`:

```python
"""Exception hierarchy for eqlib.

Non-zero ``ierr`` from libeqapi.so is mapped to one of:
    1 -> EqLibParamError    (unknown parameter name or index)
    2 -> EqLibStateError    (library not initialized or already finalized)
    3 -> EqLibRunError      (eq_run / eq_get_state calculation failed)
    4 -> EqLibInitError     (eq_init refused; e.g. already initialized)
Other non-zero values raise the base ``EqLibError``.
"""
from __future__ import annotations


class EqLibError(Exception):
    """Base class for all eqlib errors."""

    def __init__(self, message: str, ierr: int = -1) -> None:
        super().__init__(message)
        self.ierr = ierr


class EqLibInitError(EqLibError):
    """eq_init / eq_finalize lifecycle violation."""


class EqLibParamError(EqLibError):
    """Invalid parameter name or out-of-range array index."""


class EqLibStateError(EqLibError):
    """Library not initialized (any call returned 2)."""


class EqLibRunError(EqLibError):
    """eq_run / eq_get_state returned non-zero (calculation failed)."""


_CODE_MAP = {
    1: EqLibParamError,
    2: EqLibStateError,
    3: EqLibRunError,
    4: EqLibInitError,
}


def raise_for_ierr(func: str, ierr: int) -> None:
    """Raise the matching subclass when ierr != 0."""
    if ierr == 0:
        return
    cls = _CODE_MAP.get(ierr, EqLibError)
    raise cls(f"{func}: ierr={ierr}", ierr=ierr)
```

- [ ] **Step 2: コミット**

Run:
```bash
git add python/eqlib/errors.py
git commit -m "feat(eqlib): add error hierarchy and raise_for_ierr helper"
```

---

## Task 3: `_ffi.py` — ctypes 下層

**Files:**
- Create: `python/eqlib/_ffi.py`

- [ ] **Step 1: `eq/eq_api.h` の `eq_state_t` 定義を確認**

Run:
```bash
grep -nE "typedef struct|} eq_state_t|EQ_MAX_" eq/eq_api.h | head -40
```
Expected: L-2 で定義された `eq_state_t` とコンパイル時最大値マクロ（`EQ_MAX_NRGM=513, EQ_MAX_NZGM=513, EQ_MAX_NPSM=513, EQ_MAX_NRVM=1001, EQ_MAX_NRM=1001, EQ_MAX_NTHMP=2050`）が見える。

以下 `_ffi.py` のテンプレートは **ヘッダと 1:1 対応** が前提。実際の `eq_state_t` と異なる場合は Task 3 Step 2 で調整。

- [ ] **Step 2: `_ffi.py` を作成**

Create `/home/k-yoshimi/program/task-private/python/eqlib/_ffi.py`:

```python
"""Low-level ctypes FFI for libeqapi.so.

Mirrors eq/eq_api.h. Keep field names, orders, and dimensions in lock-step
with the header; ctypes.sizeof(EqStateC) must equal sizeof(eq_state_t) in C.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
from typing import Optional

# Compile-time maxima must match EQ_MAX_* macros in eq/eq_api.h.
# Source of truth: eq/eqcom0.inc (NRGM=513, NZGM=513, NPSM=513, NRVM=1001,
# NRM=1001, NTHM=2049 => NTHMP=NTHM+1=2050).
EQ_MAX_NRGM  = 513
EQ_MAX_NZGM  = 513
EQ_MAX_NPSM  = 513
EQ_MAX_NRVM  = 1001
EQ_MAX_NRM   = 1001
EQ_MAX_NTHMP = 2050


class EqStateC(ctypes.Structure):
    """ctypes Structure mirroring eq_state_t in eq/eq_api.h.

    2D array layouts:
        psirz[NRGM][NZGM]   row-major in C  = Fortran PSIRZ(NRGM, NZGM) column-major
                                              (R fastest in C, R fastest in Fortran -> same memory)
        rps  [NRM ][NTHMP]  row-major in C  = Fortran RPS(NTHMP, NRM) column-major
                                              (NTHMP fastest in C, NTHMP fastest in Fortran -> same memory)
        zps  [NRM ][NTHMP]  same layout as rps
    """
    _fields_ = [
        # --- runtime dimensions (active sizes, not EQ_MAX_*) ---
        ("nrgmax", ctypes.c_int),
        ("nzgmax", ctypes.c_int),
        ("npsmax", ctypes.c_int),
        ("nrvmax", ctypes.c_int),
        ("nrmax",  ctypes.c_int),
        ("nthmax", ctypes.c_int),
        # --- global scalars (COMMON /EQGLB1/ /EQGLB2/) ---
        ("raxis",  ctypes.c_double),
        ("zaxis",  ctypes.c_double),
        ("psi0",   ctypes.c_double),
        ("psipa",  ctypes.c_double),
        ("psita",  ctypes.c_double),
        ("redge",  ctypes.c_double),
        ("pvol",   ctypes.c_double),
        ("raave",  ctypes.c_double),
        ("betat",  ctypes.c_double),
        ("betap",  ctypes.c_double),
        ("qaxis",  ctypes.c_double),
        ("qsurf",  ctypes.c_double),
        # --- 1D grids (COMMON /EQOUT1/) ---
        ("rg", ctypes.c_double * EQ_MAX_NRGM),
        ("zg", ctypes.c_double * EQ_MAX_NZGM),
        # --- psi-surface profiles (COMMON /EQOUT2/ /EQOUT3/) ---
        ("psips", ctypes.c_double * EQ_MAX_NPSM),
        ("ppps",  ctypes.c_double * EQ_MAX_NPSM),
        ("ttps",  ctypes.c_double * EQ_MAX_NPSM),
        ("qqps",  ctypes.c_double * EQ_MAX_NPSM),
        # --- flux-surface averages (COMMON /EQAVT1/ /EQAVT2/ /EQAVT3/) ---
        ("psipv", ctypes.c_double * EQ_MAX_NRVM),
        ("rhot",  ctypes.c_double * EQ_MAX_NRVM),
        ("qpv",   ctypes.c_double * EQ_MAX_NRVM),
        # --- 2D magnetic surface (COMMON /EQOUT1/) ---
        ("psirz", (ctypes.c_double * EQ_MAX_NZGM) * EQ_MAX_NRGM),
        # --- theta-rho parametrisation (COMMON /EQWMU1/) ---
        ("rps",   (ctypes.c_double * EQ_MAX_NTHMP) * EQ_MAX_NRM),
        ("zps",   (ctypes.c_double * EQ_MAX_NTHMP) * EQ_MAX_NRM),
    ]


def _default_lib_path() -> Path:
    """Find libeqapi.so.

    Priority:
        1. ``EQLIB_PATH`` environment variable
        2. ``<repo>/eq/libeqapi.so`` relative to this file
    """
    env = os.environ.get("EQLIB_PATH")
    if env:
        return Path(env)
    # python/eqlib/_ffi.py -> python/eqlib -> python -> repo root
    here = Path(__file__).resolve()
    return here.parents[2] / "eq" / "libeqapi.so"


def load_library(path: Optional[str] = None) -> ctypes.CDLL:
    """Load libeqapi.so and configure argtypes / restype on the 5 entries."""
    p = Path(path) if path else _default_lib_path()
    if not p.exists():
        raise FileNotFoundError(
            f"libeqapi.so not found at {p}. Build via "
            f"`make -C eq libeqapi.so` or set EQLIB_PATH."
        )
    lib = ctypes.CDLL(str(p))

    lib.eq_init.argtypes = []
    lib.eq_init.restype  = ctypes.c_int

    lib.eq_run.argtypes = [ctypes.c_int]
    lib.eq_run.restype  = ctypes.c_int

    lib.eq_set_param.argtypes = [ctypes.c_char_p, ctypes.c_double]
    lib.eq_set_param.restype  = ctypes.c_int

    lib.eq_get_state.argtypes = [ctypes.POINTER(EqStateC)]
    lib.eq_get_state.restype  = ctypes.c_int

    lib.eq_finalize.argtypes = []
    lib.eq_finalize.restype  = ctypes.c_int

    return lib
```

注: `EQ_MAX_NTHMP = NTHM + 1 = 2050` は `eqcom3.inc` の `NTHMP = NTHM+1` と一致。L-2 で `eq_api.h` に明示。

- [ ] **Step 3: 構造体サイズ sanity**

Run:
```bash
cd /home/k-yoshimi/program/task-private
python3 -c "from python.eqlib._ffi import EqStateC; import ctypes; print(ctypes.sizeof(EqStateC), 'bytes')"
```
Expected: 30〜40 MB 程度（2D 配列 2050×1001×8 が 2 個 + psirz 513×513×8）。後で C 側 `sizeof(eq_state_t)` と照合する。

- [ ] **Step 4: コミット**

Run:
```bash
git add python/eqlib/_ffi.py
git commit -m "feat(eqlib): add _ffi.py (EqStateC + load_library)"
```

---

## Task 4: `state.py` — EqState dataclass

**Files:**
- Create: `python/eqlib/state.py`

- [ ] **Step 1: 作成**

Create `/home/k-yoshimi/program/task-private/python/eqlib/state.py`:

```python
"""Python-friendly snapshot of eq_state_t."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from ._ffi import EqStateC


SCALAR_FIELDS = (
    "raxis", "zaxis", "psi0", "psipa", "psita", "redge",
    "pvol", "raave", "betat", "betap", "qaxis", "qsurf",
)


@dataclass
class EqState:
    """Snapshot of EQ global + profile state at a given time.

    Dimensions match the runtime values returned by eq_get_state, not
    the compile-time EQ_MAX_* maxima. Arrays are sliced to the active
    range so callers never see zero-padded tails.
    """

    # --- dimensions ---
    nrgmax: int
    nzgmax: int
    npsmax: int
    nrvmax: int
    nrmax:  int
    nthmax: int

    # --- scalars (dict keyed by Fortran name lower-cased) ---
    scalars: Dict[str, float] = field(default_factory=dict)

    # --- 1D profiles (length = active dim) ---
    rg:    List[float] = field(default_factory=list)   # [nrgmax]
    zg:    List[float] = field(default_factory=list)   # [nzgmax]
    psips: List[float] = field(default_factory=list)   # [npsmax]
    ppps:  List[float] = field(default_factory=list)
    ttps:  List[float] = field(default_factory=list)
    qqps:  List[float] = field(default_factory=list)
    psipv: List[float] = field(default_factory=list)   # [nrvmax]
    rhot:  List[float] = field(default_factory=list)
    qpv:   List[float] = field(default_factory=list)

    # --- 2D arrays ---
    # psirz[i][j] : i in 0..nrgmax-1, j in 0..nzgmax-1
    psirz: List[List[float]] = field(default_factory=list)
    # rps[i][k] : i in 0..nrmax-1, k in 0..nthmax (nthmax+1 points including k=nthmax)
    rps:   List[List[float]] = field(default_factory=list)
    zps:   List[List[float]] = field(default_factory=list)

    @classmethod
    def from_c(cls, s: EqStateC) -> "EqState":
        nrg, nzg = int(s.nrgmax), int(s.nzgmax)
        nps      = int(s.npsmax)
        nrv      = int(s.nrvmax)
        nr, nth  = int(s.nrmax), int(s.nthmax)
        nthp     = nth + 1  # rps/zps use NTHMP = NTHM + 1 points

        scalars = {k: float(getattr(s, k)) for k in SCALAR_FIELDS}

        psirz = [[s.psirz[i][j] for j in range(nzg)] for i in range(nrg)]
        rps   = [[s.rps[i][k]   for k in range(nthp)] for i in range(nr)]
        zps   = [[s.zps[i][k]   for k in range(nthp)] for i in range(nr)]

        return cls(
            nrgmax=nrg, nzgmax=nzg, npsmax=nps, nrvmax=nrv,
            nrmax=nr, nthmax=nth,
            scalars=scalars,
            rg   =[s.rg[i]    for i in range(nrg)],
            zg   =[s.zg[i]    for i in range(nzg)],
            psips=[s.psips[i] for i in range(nps)],
            ppps =[s.ppps[i]  for i in range(nps)],
            ttps =[s.ttps[i]  for i in range(nps)],
            qqps =[s.qqps[i]  for i in range(nps)],
            psipv=[s.psipv[i] for i in range(nrv)],
            rhot =[s.rhot[i]  for i in range(nrv)],
            qpv  =[s.qpv[i]   for i in range(nrv)],
            psirz=psirz, rps=rps, zps=zps,
        )

    def to_dict(self) -> dict:
        """Serializable dict matching the format used by Phase 0 baseline JSON.

        Keeps key names uppercase to match Fortran and the L-6 comparator.
        """
        return {
            "NRGMAX": self.nrgmax, "NZGMAX": self.nzgmax,
            "NPSMAX": self.npsmax, "NRVMAX": self.nrvmax,
            "NRMAX":  self.nrmax,  "NTHMAX": self.nthmax,
            "scalars": {k.upper(): v for k, v in self.scalars.items()},
            "RG": list(self.rg), "ZG": list(self.zg),
            "PSIPS": list(self.psips), "PPPS": list(self.ppps),
            "TTPS":  list(self.ttps),  "QQPS": list(self.qqps),
            "PSIPV": list(self.psipv), "RHOT": list(self.rhot),
            "QPV":   list(self.qpv),
            "PSIRZ": [list(row) for row in self.psirz],
            "RPS":   [list(row) for row in self.rps],
            "ZPS":   [list(row) for row in self.zps],
        }
```

注: `to_dict()` のキーは Phase 0 `extract_eq_metrics.py`（L-0 baseline）の出力形式と **1:1 対応**させる。L-6 Layer 1 の `compare_metrics.py` で再利用できる。

- [ ] **Step 2: コミット**

Run:
```bash
git add python/eqlib/state.py
git commit -m "feat(eqlib): add EqState dataclass with from_c / to_dict"
```

---

## Task 5: `eqlib.py` — Eq クラス

**Files:**
- Create: `python/eqlib/eqlib.py`

- [ ] **Step 1: 作成**

Create `/home/k-yoshimi/program/task-private/python/eqlib/eqlib.py`:

```python
"""High-level Eq class wrapping libeqapi.so.

See docs/superpowers/specs/2026-04-17-tr-library-design.md §6.3.
"""
from __future__ import annotations

import ctypes
from typing import Optional

from . import _ffi
from .errors import EqLibError, raise_for_ierr
from .state import EqState


class Eq:
    """In-process handle to libeqapi.so. One per process.

    Usage::

        with Eq() as eq:
            eq.set_params(RR=3.0, BB=3.0, RIP=1.0)
            eq.set_param("PSIB[0]", 0.0)
            eq.run(ntmax=0)
            state = eq.get_state()
            print(state.scalars["qaxis"])
    """

    def __init__(self, lib_path: Optional[str] = None) -> None:
        self._lib = _ffi.load_library(lib_path)
        self._closed = True
        self._open()

    # --- lifecycle -------------------------------------------------------
    def _open(self) -> None:
        if not self._closed:
            return
        ierr = self._lib.eq_init()
        raise_for_ierr("eq_init", ierr)
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        ierr = self._lib.eq_finalize()
        raise_for_ierr("eq_finalize", ierr)
        self._closed = True

    def __enter__(self) -> "Eq":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    # --- parameter setting ----------------------------------------------
    def set_param(self, name: str, value: float) -> None:
        """Set a single parameter by name.

        ``name`` may be a scalar (e.g. ``"RR"``) or an array element using
        square-bracket subscript syntax: ``"PSIB[0]"``, ``"RIPFC[3]"``,
        ``"PSIRZ[1,1]"``. The name is forwarded verbatim to the C ABI
        ``eq_set_param``; parsing happens in ``eq_param_registry.f90``
        (Phase L-3).
        """
        if self._closed:
            raise EqLibError("set_param on closed Eq")
        ierr = self._lib.eq_set_param(name.encode("ascii"), float(value))
        raise_for_ierr(f"eq_set_param({name!r}, {value!r})", ierr)

    def set_params(self, **kwargs) -> None:
        """Bulk-set scalar parameters by keyword.

        Array elements are NOT supported here because Python keyword
        arguments cannot contain ``[`` or ``]``. For array elements use
        :py:meth:`set_param` directly::

            eq.set_param("PSIB[0]", 0.0)
            eq.set_param("RIPFC[1]", 1.0)

        Keys containing ``__`` raise ``EqLibError`` to catch accidental
        attempts at an underscore-encoded array syntax (same rule as
        trlib / tilib).
        """
        for k, v in kwargs.items():
            if "__" in k:
                raise EqLibError(
                    f"set_params() received '{k}' which contains '__'. "
                    "set_params is scalar-only; use "
                    "set_param('NAME[i]', value) for array elements."
                )
            self.set_param(k, v)

    # --- run / state -----------------------------------------------------
    def run(self, ntmax: int = 0) -> None:
        """Run the EQ solver.

        ``ntmax`` follows the Fortran convention: 0 means "use whatever
        NTMAX was last set via set_param". Non-zero overrides it.
        """
        if self._closed:
            raise EqLibError("run on closed Eq")
        ierr = self._lib.eq_run(int(ntmax))
        raise_for_ierr(f"eq_run({ntmax})", ierr)

    def get_state(self) -> EqState:
        if self._closed:
            raise EqLibError("get_state on closed Eq")
        c = _ffi.EqStateC()
        ierr = self._lib.eq_get_state(ctypes.byref(c))
        raise_for_ierr("eq_get_state", ierr)
        return EqState.from_c(c)
```

- [ ] **Step 2: `__init__.py` を更新**

Create `/home/k-yoshimi/program/task-private/python/eqlib/__init__.py`:

```python
"""eqlib: Python wrapper for libeqapi.so (TASK/EQ, Phase L-5)."""
from .eqlib import Eq
from .state import EqState
from .errors import (
    EqLibError, EqLibInitError, EqLibParamError,
    EqLibStateError, EqLibRunError, raise_for_ierr,
)

__all__ = [
    "Eq", "EqState",
    "EqLibError", "EqLibInitError", "EqLibParamError",
    "EqLibStateError", "EqLibRunError",
    "raise_for_ierr",
]
```

Create empty `/home/k-yoshimi/program/task-private/python/eqlib/tests/__init__.py` (may already exist from `mkdir -p`).

`/home/k-yoshimi/program/task-private/python/__init__.py` — already exists (TR L-5 added it); skip if present.

- [ ] **Step 3: import sanity**

Run:
```bash
cd /home/k-yoshimi/program/task-private
PYTHONPATH=python python3 -c "from eqlib import Eq, EqState, EqLibError; print('ok')"
```
Expected: `ok`。

- [ ] **Step 4: コミット**

Run:
```bash
git add python/eqlib/eqlib.py python/eqlib/__init__.py python/eqlib/tests/__init__.py
git commit -m "feat(eqlib): add Eq class + package __init__"
```

---

## Task 6: Unittest

**Files:**
- Create: `python/eqlib/tests/test_ffi.py`
- Create: `python/eqlib/tests/test_eqlib.py`

- [ ] **Step 1: `tests/test_ffi.py` を作成**

Create `/home/k-yoshimi/program/task-private/python/eqlib/tests/test_ffi.py`:

```python
"""Smoke tests for eqlib._ffi (ctypes layer)."""
from __future__ import annotations

import ctypes
import os
import unittest
from pathlib import Path


def _lib_path() -> Path:
    env = os.environ.get("EQLIB_PATH")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    return here.parents[3] / "eq" / "libeqapi.so"


@unittest.skipUnless(_lib_path().exists(), f"libeqapi.so not built ({_lib_path()})")
class TestFfi(unittest.TestCase):

    def setUp(self) -> None:
        from eqlib import _ffi
        self._ffi = _ffi
        self.lib = _ffi.load_library(str(_lib_path()))

    def tearDown(self) -> None:
        # Best-effort cleanup; ignore errors.
        try:
            self.lib.eq_finalize()
        except Exception:
            pass

    def test_init_finalize_cycle(self) -> None:
        self.assertEqual(self.lib.eq_init(), 0)
        self.assertEqual(self.lib.eq_finalize(), 0)

    def test_set_param_unknown_nonzero(self) -> None:
        self.assertEqual(self.lib.eq_init(), 0)
        rc = self.lib.eq_set_param(b"NO_SUCH_PARAM", 1.0)
        self.assertNotEqual(rc, 0)

    def test_set_param_known_zero(self) -> None:
        self.assertEqual(self.lib.eq_init(), 0)
        rc = self.lib.eq_set_param(b"RR", 3.0)
        self.assertEqual(rc, 0)

    def test_state_struct_roundtrip(self) -> None:
        """Size of EqStateC is non-trivial and get_state fills dimensions."""
        self.assertGreater(ctypes.sizeof(self._ffi.EqStateC), 1024)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: `tests/test_eqlib.py` を作成**

Create `/home/k-yoshimi/program/task-private/python/eqlib/tests/test_eqlib.py`:

```python
"""Smoke tests for the high-level Eq class."""
from __future__ import annotations

import os
import unittest
from pathlib import Path


def _lib_path() -> Path:
    env = os.environ.get("EQLIB_PATH")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    return here.parents[3] / "eq" / "libeqapi.so"


@unittest.skipUnless(_lib_path().exists(), f"libeqapi.so not built ({_lib_path()})")
class TestEq(unittest.TestCase):

    def test_context_manager(self) -> None:
        from eqlib import Eq
        with Eq(lib_path=str(_lib_path())) as eq:
            self.assertIsNotNone(eq)

    def test_set_params_scalar(self) -> None:
        from eqlib import Eq
        with Eq(lib_path=str(_lib_path())) as eq:
            eq.set_params(RR=3.0, BB=3.0, RIP=1.0,
                          NRGMAX=65, NZGMAX=65, NPSMAX=65)

    def test_set_params_rejects_double_underscore(self) -> None:
        from eqlib import Eq, EqLibError
        with Eq(lib_path=str(_lib_path())) as eq:
            with self.assertRaises(EqLibError):
                eq.set_params(PSIB__0=0.0)

    def test_set_param_array_subscript(self) -> None:
        from eqlib import Eq
        with Eq(lib_path=str(_lib_path())) as eq:
            # Array element set via explicit bracket syntax.
            eq.set_param("PSIB[0]", 0.0)

    def test_set_param_unknown_raises(self) -> None:
        from eqlib import Eq, EqLibParamError
        with Eq(lib_path=str(_lib_path())) as eq:
            with self.assertRaises(EqLibParamError):
                eq.set_param("NOT_A_PARAM", 0.0)

    def test_run_and_get_state_minimal(self) -> None:
        from eqlib import Eq
        with Eq(lib_path=str(_lib_path())) as eq:
            eq.set_params(MDLEQF=0, RR=3.0, BB=3.0, RIP=1.0,
                          NRGMAX=65, NZGMAX=65, NPSMAX=65)
            eq.run(ntmax=0)
            st = eq.get_state()
            self.assertGreater(st.nrgmax, 0)
            self.assertGreater(st.nzgmax, 0)
            self.assertEqual(len(st.rg), st.nrgmax)
            self.assertEqual(len(st.zg), st.nzgmax)
            # psirz sliced to active size
            self.assertEqual(len(st.psirz), st.nrgmax)
            if st.psirz:
                self.assertEqual(len(st.psirz[0]), st.nzgmax)
            # to_dict round-trip
            d = st.to_dict()
            self.assertIn("PSIRZ", d)
            self.assertEqual(d["NRGMAX"], st.nrgmax)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: テスト実行**

Run:
```bash
cd /home/k-yoshimi/program/task-private
PYTHONPATH=python python3 -m unittest python.eqlib.tests.test_ffi python.eqlib.tests.test_eqlib -v 2>&1 | tail -25
```
Expected: 10 tests PASS（または `libeqapi.so` 未ビルド時は全 SKIP）。

失敗パターン:
- `EqStateC` のサイズが C 側 `sizeof(eq_state_t)` と不一致 → `_ffi.py` の `_fields_` 順序か `EQ_MAX_*` 値を再確認（L-2 `eq_api.h` と照合）
- `eq_set_param("RR", 3.0)` が `ierr != 0` → L-3 の param registry に `RR` が未登録の可能性（L-3 plan 再点検）
- `test_run_and_get_state_minimal` で `ierr=3` → NRGMAX=65 のような最小 case が MDLEQF=0 で動かない。baseline で使われている入力を参照して再調整

- [ ] **Step 4: コミット**

Run:
```bash
git add python/eqlib/tests/test_ffi.py python/eqlib/tests/test_eqlib.py
git commit -m "test(eqlib): unittest-based ffi/class smoke tests"
```

---

## Task 7: README（最小）

**Files:**
- Create: `python/eqlib/README.md`

- [ ] **Step 1: 最小 README**

Create `/home/k-yoshimi/program/task-private/python/eqlib/README.md`:

````markdown
# eqlib — Python wrapper for TASK/EQ

Phase L-5 minimum viable package. Detailed documentation lands in L-7.

## Build

```bash
cd /path/to/task/eq && make libeqapi.so
```

## Quick start

```python
from eqlib import Eq

with Eq() as eq:
    eq.set_params(MDLEQF=0, RR=3.0, BB=3.0, RIP=1.0,
                  NRGMAX=65, NZGMAX=65, NPSMAX=65)
    eq.run(ntmax=0)
    state = eq.get_state()
    print("qaxis =", state.scalars["qaxis"],
          "raxis =", state.scalars["raxis"])
```

## Library path resolution

`Eq(lib_path=...)` argument > `EQLIB_PATH` env var > `<repo>/eq/libeqapi.so`.

## Limitations (Phase L-5)

- Single-instance only (Fortran globals are shared in one process).
- No MPI.
- `set_params(**kwargs)` is scalar-only. For array elements use
  `set_param("PSIB[0]", 0.0)` directly. Keys containing `__` are
  rejected as likely array-syntax mistakes.
- Parameter names supported are those registered in
  `eq/eq_param_registry.f90` (Phase L-3).
- 2D arrays (`psirz`, `rps`, `zps`) are returned as plain
  `list[list[float]]`. numpy integration lands in L-6 if needed.
````

- [ ] **Step 2: コミット**

Run:
```bash
git add python/eqlib/README.md
git commit -m "docs(eqlib): add minimal README (Phase L-5 stub for L-7)"
```

---

## Task 8: 回帰テスト + PR

- [ ] **Step 1: eq バイナリと L-0 回帰**

Run:
```bash
cd /home/k-yoshimi/program/task-private/test_run
./run_tests.sh eq_* tr_iter01 tr_m0904 tr_tst2 2>&1 | tail -5
```
Expected: 全 PASS（Python 側の変更は Fortran ビルドに無関係）。

- [ ] **Step 2: eqlib unittest 全 PASS**

Run:
```bash
cd /home/k-yoshimi/program/task-private
PYTHONPATH=python python3 -m unittest discover python/eqlib/tests -v 2>&1 | tail -15
```
Expected: 10 tests PASS（`libeqapi.so` 未ビルド時は SKIP）。

- [ ] **Step 3: 変更ファイル確認**

Run:
```bash
git diff --stat origin/develop..HEAD
```
Expected: 新規 `python/eqlib/` 配下 9 ファイル + `python/__init__.py`（未作成時）。既存ファイル修正なし。

- [ ] **Step 4: push と PR**

Run:
```bash
git push -u origin feature/eq-library-L5-python
gh pr create --base develop \
  --title "feat(eqlib): Phase L-5 Python ctypes wrapper for libeqapi.so" \
  --body "Phase L-5: 2-layer Python wrapper (_ffi + Eq class) for libeqapi.so. 10 unittests included; skip gracefully when libeqapi.so is not built. eq binary and L-0 regression unchanged. Design spec §6."
```

---

## Risk / Mitigation

| リスク | 影響 | 緩和策 |
|---|---|---|
| `EqStateC` のサイズが C `eq_state_t` と不一致 | `eq_get_state` で segfault | unittest でサイズ sanity（`ctypes.sizeof`）を確認。不一致なら `_fields_` 順序と `EQ_MAX_*` 値を `eq_api.h` と突き合わせ |
| `libeqapi.so` の dlopen 時に rpath が足りず fail | import で `OSError` | `Eq(lib_path=...)` で絶対パス / `EQLIB_PATH` env / デフォルト 3 段で解決。README に明記 |
| 2D 配列のコピーが遅い（NRGM=513, NTHM+1=2050） | `get_state()` が数秒 | L-5 では list-of-list 許容。L-6 で numpy 化を検討（ctypes `numpy.ctypeslib.as_array`） |
| `set_param("PSIRZ[1,1]", v)` のような 2D subscript | L-3 の parser 未対応 | L-3 plan で `[i,j]` 対応を明記。本 L-5 はパーサ任せ、失敗時は `EqLibParamError` が自然に raise |
| `set_params(**kwargs)` で `[]` 不可問題 | 配列要素設定不能 | scalar-only に確定（trlib/tilib と同じルール）。`__` を含むキーは即 `EqLibError`。配列は `set_param` を直接呼ぶ |
| Phase 0 baseline JSON の key 名が大文字/小文字ミスマッチ | L-6 で compare_metrics が fail | `to_dict()` で uppercase に統一 |
| 複数 `Eq()` インスタンスを同プロセスで作る | Fortran globals で状態破壊 | README に「single-instance only」明記。将来必要なら pid-per-process 隔離を検討 |
| numpy 未インストール環境 | テスト環境で import 失敗 | L-5 は numpy 依存なし。stdlib のみで完結 |

### フォールバック

| 状況 | 対応 |
|---|---|
| `ctypes.CDLL` ロード失敗 | `LD_LIBRARY_PATH` 設定、または `Eq(lib_path="/abs/path")` |
| 構造体サイズ不一致 | C 側に `size_t eq_state_t_sizeof(void)` 関数を追加し、Python test で比較（L-6 で検討） |
| テスト実行で Fortran 側 `STOP` | L-2/L-3 の ABI 実装が `STOP` を返す経路を潰せていない。`eq_api.f90` に `IOSTAT` ベースの guard 追加 |

---

## Testing Strategy

| レベル | テスト | 期待 |
|---|---|---|
| Import | `from eqlib import Eq, EqState, EqLibError` | 全 symbol が resolvable |
| Library load | `Eq(lib_path=...)` in test_ffi setUp | `libeqapi.so` が load 可能、5 prototype が bind |
| Init/finalize | `test_init_finalize_cycle` | return 0 / 0 |
| Invalid param | `test_set_param_unknown_nonzero`, `test_set_param_unknown_raises` | ierr != 0 / `EqLibParamError` raise |
| Valid scalar | `test_set_param_known_zero`, `test_set_params_scalar` | ierr = 0 |
| Array subscript | `test_set_param_array_subscript` | `PSIB[0]` が通る |
| Keyword sanity | `test_set_params_rejects_double_underscore` | `__` を含む key で `EqLibError` |
| Full cycle | `test_run_and_get_state_minimal` | ierr=0、`nrgmax > 0`、`psirz[i]` 長さ = `nzgmax`、`to_dict()["PSIRZ"]` が serializable |
| Struct size | `test_state_struct_roundtrip` | `ctypes.sizeof(EqStateC) > 1KB` |

L-6 で Layer 1（既存 eq バイナリ vs Python 経由の数値一致）と Layer 4（パラメータ sweep）を追加。本 L-5 は layer 2/3（C ABI / .so load）までを担保。

---

## Deliverables

- [ ] `python/eqlib/` パッケージが作られ、`from eqlib import Eq` が成功
- [ ] `_ffi.py` の `EqStateC` が `eq_api.h` の `eq_state_t` と 1:1 対応（サイズ一致、フィールド順一致）
- [ ] `EqState` dataclass が scalars / 1D / 2D (`psirz`, `rps`, `zps`) を保持
- [ ] `Eq` class が context manager として動き、`set_params`/`set_param`/`run`/`get_state`/`close` を提供
- [ ] `set_param("PSIB[0]", v)` のような配列要素設定が動く（L-3 parser 経由）
- [ ] 例外階層が機能（`EqLibInitError`/`EqLibParamError`/`EqLibStateError`/`EqLibRunError`）
- [ ] `unittest` 10 ケース全 PASS（`libeqapi.so` 未ビルド時は skip）
- [ ] `EQLIB_PATH` env var と `<repo>/eq/libeqapi.so` デフォルトの両方で library が解決される
- [ ] `to_dict()` が Phase 0 baseline JSON と同じキー構造（L-6 で再利用可能）
- [ ] `python/eqlib/README.md` が存在（L-7 で拡充）

## 依存

- 前段階: L-4 完了（`libeqapi.so` がビルド可能、5 C シンボル export 済み）
- 後段階: L-6（4 層テスト: baseline / L-2 C / L-4 .so / L-5 Python の等価性検証）、L-7（README / notebook / docs 本体）
