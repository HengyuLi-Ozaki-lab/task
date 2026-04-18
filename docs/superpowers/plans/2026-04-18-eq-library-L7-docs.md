# EQ ライブラリ化 Phase L-7: ドキュメント 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-1〜L-6 で完成した `eq/libeqapi.so` + Python ラッパ `python/eqlib/` を、新規利用者（プラズマ研究者 / スクリプト自動化ユーザ）がゼロから使い始めるためのドキュメントを整備する。`python/eqlib/README.md` を本格化（使い方 + API リファレンス + エラー対処）、使用例 Jupyter notebook + Python script を同梱、CHANGELOG と **eq バイナリ CLI → libeqapi.so への移行ノート** を明示する。コード変更なし。

**Architecture:** 純粋にドキュメント (`*.md`, `*.ipynb`, `*.py` の example) のみ。3 層に分けて配置:

1. **`python/eqlib/README.md`** — Python ユーザ向けクイックスタート + API リファレンス + トラブルシュート（最重要）
2. **`docs/eq-library/architecture.md`** — 任意。C ABI 層 / FFI 層 / 高レベル層のアーキテクチャ概説（TR の同等ドキュメントと並ぶ位置）
3. **`python/eqlib/examples/`** — 実行可能な使用例 2〜3 本（quickstart / parameter sweep / eq CLI → libeqapi 移行デモ）
4. **`python/eqlib/CHANGELOG.md`** — L-0〜L-7 のリリースノート
5. **`doc/eq-library.md`** — task リポジトリ全体 doc 側のエントリポイント（相対リンク）

**Tech Stack:** Markdown、Jupyter notebook (JSON)、Python 3 (example scripts)、L-5/L-6 で完成済の `Eqlib` クラス。Notebook は CI で execute しない（nbformat のみ妥当性確認）。

**出典:**
- 設計: `docs/superpowers/specs/2026-04-17-tr-library-design.md` §9 (L-7 行), §12 (受け入れ基準: 「README に使用例」)
- 参照 plan: `docs/superpowers/plans/2026-04-18-tr-library-L7-docs.md` (canonical template, merged)
- 参照 plan: `docs/superpowers/plans/2026-04-18-ti-library-L7-docs.md` (notebook JSON 形式)
- 参照 plan: `docs/superpowers/plans/2026-04-18-fp-library-L7-docs.md` (CHANGELOG / global doc entry 形式)
- 参照 plan: `docs/superpowers/plans/2026-04-18-eq-library-L1-makefile-split.md` (CORE/GRAPHICS/MENU 分割)

---

## Prerequisites

- [ ] **L-6 完了:** 4 層テストが `./run_tests.sh eqlib_*` で 5/5 PASS
- [ ] **L-5 完了:** `python/eqlib/` が import 可能、`Eqlib` クラスが使える
- [ ] **L-4 完了:** `eq/libeqapi.so` がビルド可能

Run:
```bash
cd /home/k-yoshimi/program/task-private
git log --oneline origin/develop | grep -i "phase l-6" | head -3
PYTHONPATH=python python3 -c "from eqlib import Eqlib"
ls eq/libeqapi.so
grep "eqlib_" test_run/test_definitions.conf
```
Expected: L-6 merged、`Eqlib` import OK、`libeqapi.so` 存在、4+ 個の `eqlib_*` エントリ。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/eqlib/README.md` | 修正 | L-5 雛形を本格化: install / quickstart / 5-fn API / params 一覧 / troubleshooting / migration note |
| `python/eqlib/examples/__init__.py` | 新規 | 空パッケージ |
| `python/eqlib/examples/01_basic_run.py` | 新規 | 最小実行（init→set_params→run→get_state→print） |
| `python/eqlib/examples/02_param_sweep.py` | 新規 | RR/BB 3x3 スイープ（matplotlib 不要・JSON 出力） |
| `python/eqlib/examples/03_cli_migration.py` | 新規 | eq binary CLI → libeqapi.so 移行ビフォーアフター |
| `python/eqlib/examples/01_quickstart.ipynb` | 新規 | Jupyter notebook 版 quickstart（output cell 空で commit） |
| `python/eqlib/examples/02_sweep_visualization.ipynb` | 新規 | notebook 版 sweep + matplotlib 可視化（optional dep） |
| `python/eqlib/examples/README.md` | 新規 | examples index |
| `python/eqlib/tests/test_examples.py` | 新規 | `01_basic_run.py` が exit 0 で完走する smoke（他は import のみ） |
| `python/eqlib/CHANGELOG.md` | 新規 | L-0〜L-7 の history |
| `docs/eq-library/architecture.md` | 新規（optional） | アーキテクチャ概説（3 層: C ABI / FFI / 高レベル） |
| `docs/superpowers/notes/2026-04-18-eq-phase-l-completion.md` | 新規 | Phase L 全体受け入れ基準対応マトリクス |
| `doc/eq-library.md` | 新規 | task リポジトリ全体 doc 側エントリ（singular `doc/`） |

**ディレクトリ名の確認 — `doc/` (singular) vs `docs/`:**

- `docs/eq-library/` は **task-private 内の設計ドキュメント** 向け (superpowers 系と同居)
- `doc/eq-library.md` は **task 公開リポジトリ側** の従来慣習（`ls task/doc/` で他モジュールの doc が存在）

両方を作ることで、開発者向け詳細 (`docs/`) とエンドユーザ向け簡易 (`doc/`) を分離。FP L-7 / TI L-7 と整合。

**方針:**
- README は **長すぎない**: クイックスタート → 1 ページ API → troubleshoot → migration note。詳細 spec は spec 文書へリンク。
- examples は **コピペ実行可能**。`PYTHONPATH=python python3 examples/XX.py` で動く。notebook は execute せず commit（CI では走らせない）。
- L-7 は **コード変更なし**（example `.py` を除く）。example 内でバグが出たら L-3〜L-6 に戻して修正、L-7 自体は保留しない。
- **Migration note（CLI → libeqapi.so）は専用セクション**にする。EQ ユーザの多くは既存 `eq` バイナリの `eq.ITER01.in` ベース運用に慣れているため、差分と等価性を明示する。

---

## Task 1: ブランチ作成

- [ ] **Step 1: ブランチ**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git fetch origin develop
git checkout -b feature/eq-library-L7-docs origin/develop
mkdir -p python/eqlib/examples docs/eq-library docs/superpowers/notes
```

- [ ] **Step 2: 全テストが PASS（出発点固定）**

Run:
```bash
cd /home/k-yoshimi/program/task-private
(cd eq && make libeqapi.so) 2>&1 | tail -3
cd test_run && ./run_tests.sh 2>&1 | tail -10
```
Expected: 全 PASS（eqlib_* 含む）。

---

## Task 2: `python/eqlib/README.md` 本格化

**Files:**
- Modify: `python/eqlib/README.md`（L-5 の雛形を全面書き換え）

- [ ] **Step 1: README 本体**

`python/eqlib/README.md` を以下で上書き:

````markdown
# eqlib — Python wrapper for TASK/EQ

`eqlib` is a `ctypes`-based in-process Python wrapper around
`eq/libeqapi.so` (Phase L library-ization of the TASK/EQ equilibrium
solver). It lets you drive MHD equilibrium calculations from Python —
with no `subprocess`/file I/O overhead — from Jupyter, optimization
loops, and parameter sweeps.

## Status

- Single process / single instance (EQ has global state in `eqcomm`).
- Fortran graphics (GSAF) and the interactive `eqmenu` are **excluded**
  from `libeqapi.so`. This is a numerical-only API.
- Layer 1 equivalence: PASS vs `eq_iter01` / `eq_tst2` L-0 baselines
  (tol `1e-10`).

## Install / build

```bash
# 1. Build libeqapi.so (one-off, includes PIC dependency builds)
cd /path/to/task/eq
make libs_pic
make libeqapi.so

# 2. Add the wrapper to PYTHONPATH
export PYTHONPATH=/path/to/task/python:$PYTHONPATH

# 3. (optional) override library path
export EQLIB_PATH=/path/to/task/eq/libeqapi.so
```

No third-party Python dependencies (stdlib only, Python 3.8+). Notebook
examples optionally use `numpy` and `matplotlib`.

## Quickstart

```python
from eqlib import Eqlib

with Eqlib() as eq:
    eq.set_params(RR=6.2, RA=2.0, RKAP=1.7, RDLT=0.33,
                  BB=5.3, RIP=15.0,
                  NRMAX=51, NTHMAX=65, MDLEQF=5)
    eq.run(ntmax=1)
    state = eq.get_state()
    print(f"nrmax={state.nrmax}  PSITA={state.PSITA:.4g}")
```

See `examples/` for full scripts and notebooks.

## 5-function C ABI

The library exposes exactly 5 symbols (see `eq/eq_api.h`):

| Function | Purpose |
|---|---|
| `eq_init()` | Initialize eq globals (eqinit). Idempotent until `eq_finalize`. |
| `eq_set_param(name, value)` | Set one namelist parameter. |
| `eq_run(ntmax)` | Run one or more equilibrium iterations. |
| `eq_get_state(&state)` | Snapshot the current `eqcomm` state. |
| `eq_finalize()` | Release resources. |

`Eqlib` wraps all 5 via `ctypes` and adds a dataclass (`EqState`) + Python
exception hierarchy.

## `Eqlib` API reference

### `Eqlib(lib_path: str | None = None)`
Context-manager handle. `__enter__` calls `eq_init`; `__exit__` calls
`eq_finalize`. `lib_path` resolution order:

1. explicit argument
2. `EQLIB_PATH` env var
3. `<repo_root>/eq/libeqapi.so`

### `set_param(name: str, value: float) -> None`
Set one parameter. Use `"PA[1]"` for array elements (1-origin).

### `set_params(**kwargs) -> None`
Bulk scalar setter; accepts dict-of-index (`PA={1: 1.0, 2: 2.0}`) for arrays.

### `run(ntmax: int) -> None`
Advance the equilibrium calculation by `ntmax` iterations. For EQ this
typically means one full Grad-Shafranov solve per `ntmax`. Cumulative.

### `get_state() -> EqState`
Snapshot current eqcomm scalars + profile arrays into the `EqState`
dataclass:

```python
@dataclass
class EqState:
    nrmax: int; nthmax: int; nsumax: int
    PSITA: float; RIP0: float; BB0: float
    PSI:   List[float]   # [nrmax]
    QPS:   List[float]
    TTS:   List[float]
    PPS:   List[float]
    RHO:   List[float]
    # ...
```

### `close() -> None`
Idempotent. `__exit__` calls this automatically.

## Exception hierarchy

| Class | When raised |
|---|---|
| `EqlibError` | base class |
| `EqlibInitError` | `eq_init` returned non-zero |
| `EqlibParamError` | `eq_set_param` saw unknown name or bad index |
| `EqlibRunError` | `eq_run` failed to converge |
| `EqlibStateError` | API call before init or after close |

## Registered parameters

Registered in `eq/eq_param_registry.f90` as of L-3. Highlights:

- **Geometry:** `RR`, `RA`, `RKAP`, `RDLT`, `BB`, `RIP`
- **Grid:** `NRMAX`, `NTHMAX`, `NSUMAX`, `NRGMAX`, `NSGMAX`
- **Profile shape:** `PROFR1`, `PROFR2`, `PROFPP`, `PROFTT`
- **Solver switches:** `MDLEQF`, `MDLEQN`, `MDLEQQ`, `MDLEQC`

To list the full set:
```bash
grep -E '^\s+CASE \(' eq/eq_param_registry.f90
```

**Adding a new parameter:**
1. Edit `eq/eq_param_registry.f90` and add `CASE ("MY_PARAM")` in the
   `SELECT CASE` block.
2. Rebuild: `cd eq && make libeqapi.so`.
3. Use: `eq.set_param("MY_PARAM", 1.23)`.

No Python changes required.

## Migration: from `eq` binary to `libeqapi.so`

If you currently drive TASK/EQ as a subprocess with a namelist file:

**Before (CLI-driven):**
```bash
cd /path/to/task/eq
./eq < in/eq.ITER01.in      # interactive or scripted stdin
```

**After (in-process Python):**
```python
from eqlib import Eqlib

with Eqlib() as eq:
    # Translate &EQ/ namelist values to set_param calls.
    eq.set_param("RR", 6.2)
    eq.set_param("BB", 5.3)
    eq.set_param("RIP", 15.0)
    # ... one set_param per namelist key, or eq.set_params(**dict)
    eq.run(ntmax=1)
    state = eq.get_state()
# Use state.PSI, state.QPS, etc. directly — no file I/O.
```

### Equivalence guarantees

- `eq/libeqapi.so` links the same Fortran physics code as the `eq`
  binary; only graphics and the interactive menu are excluded.
- Layer 1 equivalence tests (`python/eqlib/tests/test_equivalence.py`)
  verify `1e-10` bit-for-bit match on all scalar + profile fields for
  `eq_iter01` and `eq_tst2`.
- **Not migrated:** output plots (use matplotlib in Python instead),
  `eqmenu` interactive tree (use Python control flow).

### Common translation patterns

| Namelist | Python |
|---|---|
| `RR = 6.2` | `eq.set_param("RR", 6.2)` |
| `PA(1) = 1.0` | `eq.set_param("PA[1]", 1.0)` |
| `KNAMEQ = 'my.eqdsk'` | **Not yet supported** (string params: future work) |
| `&EQ / RUN /` | `eq.run(1)` |
| `&END` + `Q` | `# implicit via context manager exit` |

### Known limitations

- Single `Eqlib` instance per process (global fortran state).
- No MPI. For parallel sweeps use `multiprocessing` — each worker
  process gets its own libeqapi.so load.
- String namelist parameters (`KNAMEQ`, etc.) are not yet exposed
  through `set_param`; file-based `.eqdsk` load requires using the
  standalone binary for now. Tracked in design spec §4.3.
- Plotting: use matplotlib directly against `state.PSI` / `QPS` / `TTS`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `FileNotFoundError: libeqapi.so not found` | not built | `cd eq && make libeqapi.so` |
| `OSError: cannot open shared object file` | dependent libs (MUMPS, etc.) missing from `LD_LIBRARY_PATH` | export `LD_LIBRARY_PATH` with their install path |
| `EqlibParamError` on a name that should work | not yet in `eq_param_registry.f90` | see "Adding a new parameter" |
| Numerical drift vs `eq` binary | param missing from registry or fixture | extend `eq_param_registry.f90` and re-run Layer 1 tests |
| `EqlibRunError` at `eq.run(1)` | convergence failure / invalid geometry | check `MDLEQF`, `NRMAX`, geometry parameters |

## Tests

```bash
# All 4 layers
PYTHONPATH=python python3 -m unittest discover python/eqlib/tests -v

# Via run_tests.sh
cd test_run && ./run_tests.sh eqlib_ffi eqlib_sweep eqlib_c_abi eqlib_equivalence
```

Layers:
- L1 (`test_equivalence.py`) — bit-equivalence vs eq binary baselines
- L2 (`eq/tests/c_abi/`) — C ABI smoke/param/run/negative
- L3 (`test_ffi.py`) — Pythonic interface contracts
- L4 (`test_sweep.py`) — 3x3 sweep smoke

## See also

- Design spec: `docs/superpowers/specs/2026-04-17-tr-library-design.md`
  (TR template; eq follows the same pattern with `eq_*` symbols).
- Phase L plans: `docs/superpowers/plans/2026-04-18-eq-library-L*.md`
- Architecture overview: `docs/eq-library/architecture.md`
- Global doc entry: `doc/eq-library.md`
- Changelog: `python/eqlib/CHANGELOG.md`
````

- [ ] **Step 2: 構造チェック**

Run:
```bash
python3 -c "
import re
t = open('/home/k-yoshimi/program/task-private/python/eqlib/README.md').read()
print('headers:', len(re.findall(r'^#', t, re.MULTILINE)))
print('code blocks:', t.count('\`\`\`'))
"
```
Expected: headers > 10, code blocks は偶数。

- [ ] **Step 3: コミット**

Run:
```bash
git add python/eqlib/README.md
git commit -m "docs(eq): expand README with full API/params/migration note (L-7)"
```

---

## Task 3: 使用例 Python script 3 本

**Files:**
- Create: `python/eqlib/examples/__init__.py`（空）
- Create: `python/eqlib/examples/01_basic_run.py`
- Create: `python/eqlib/examples/02_param_sweep.py`
- Create: `python/eqlib/examples/03_cli_migration.py`

- [ ] **Step 1: 01_basic_run.py**

作成: `python/eqlib/examples/01_basic_run.py`

```python
#!/usr/bin/env python3
"""eqlib example 1: minimal equilibrium run + print.

Usage:
    PYTHONPATH=python python3 python/eqlib/examples/01_basic_run.py
"""
from eqlib import Eqlib


def main() -> int:
    with Eqlib() as eq:
        # ITER-like geometry (truncated; see fixtures for full set).
        eq.set_params(
            RR=6.2, RA=2.0, RKAP=1.7, RDLT=0.33,
            BB=5.3, RIP=15.0,
            NRMAX=51, NTHMAX=65,
            MDLEQF=5,
        )
        eq.run(ntmax=1)
        state = eq.get_state()

    print(f"nrmax   = {state.nrmax}")
    print(f"nthmax  = {state.nthmax}")
    print(f"PSITA   = {state.PSITA:.6g}")
    print(f"RIP0    = {state.RIP0:.6g}")
    print(f"BB0     = {state.BB0:.6g}")
    print("\nFirst 5 rows of radial profile (NR, PSI, QPS, TTS):")
    for i in range(min(5, state.nrmax)):
        print(f"  {i+1:3d}  {state.PSI[i]: .4e}  "
              f"{state.QPS[i]: .4e}  {state.TTS[i]: .4e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 02_param_sweep.py**

作成: `python/eqlib/examples/02_param_sweep.py`

```python
#!/usr/bin/env python3
"""eqlib example 2: 3x3 RR/BB sweep with JSON output.

No matplotlib dependency — prints a JSON array of dicts.

Usage:
    PYTHONPATH=python python3 python/eqlib/examples/02_param_sweep.py
"""
import json

from eqlib import Eqlib


def run_one(rr: float, bb: float) -> dict:
    with Eqlib() as eq:
        eq.set_params(
            RR=rr, RA=2.0, RKAP=1.7, RDLT=0.33,
            BB=bb, RIP=15.0,
            NRMAX=51, NTHMAX=65, MDLEQF=5,
        )
        eq.run(ntmax=1)
        s = eq.get_state()
    return {
        "RR": rr, "BB": bb,
        "PSITA": float(s.PSITA),
        "BB0":   float(s.BB0),
        "nrmax": s.nrmax,
    }


def main() -> int:
    rows = []
    for rr in (5.8, 6.2, 6.6):
        for bb in (5.0, 5.3, 5.6):
            rows.append(run_one(rr, bb))
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: 03_cli_migration.py**

作成: `python/eqlib/examples/03_cli_migration.py`

```python
#!/usr/bin/env python3
"""eqlib example 3: eq binary CLI → libeqapi.so migration demo.

Shows the "before" (subprocess call to eq binary) and "after" (in-process
Eqlib) patterns side-by-side. Only the "after" path is actually executed
(the "before" is printed as a shell command for reference).

Usage:
    PYTHONPATH=python python3 python/eqlib/examples/03_cli_migration.py
"""
from eqlib import Eqlib


BEFORE_CLI = """
# Before: subprocess + namelist file
cd /path/to/task/eq
./eq < in/eq.ITER01.in
# — produces graphics window, no structured data output
"""


def after_in_process() -> None:
    """After: in-process call, returns data directly."""
    with Eqlib() as eq:
        eq.set_params(
            RR=6.2, RA=2.0, RKAP=1.7, RDLT=0.33,
            BB=5.3, RIP=15.0,
            NRMAX=51, NTHMAX=65, MDLEQF=5,
        )
        eq.run(ntmax=1)
        state = eq.get_state()
    print("== AFTER (in-process) ==")
    print(f"  PSITA = {state.PSITA:.6g}")
    print(f"  RIP0  = {state.RIP0:.6g}")
    print(f"  BB0   = {state.BB0:.6g}")
    print("  (data is now a Python dataclass, ready for numpy/matplotlib)")


def main() -> int:
    print("== BEFORE (CLI subprocess) ==")
    print(BEFORE_CLI.strip())
    print()
    after_in_process()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 空 __init__.py**

Run:
```bash
: > /home/k-yoshimi/program/task-private/python/eqlib/examples/__init__.py
```

- [ ] **Step 5: 3 本実行確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private
PYTHONPATH=python python3 python/eqlib/examples/01_basic_run.py
PYTHONPATH=python python3 python/eqlib/examples/02_param_sweep.py
PYTHONPATH=python python3 python/eqlib/examples/03_cli_migration.py
```
Expected: 3 本すべて exit 0、数値が表示される。

- [ ] **Step 6: コミット**

Run:
```bash
git add python/eqlib/examples/__init__.py \
        python/eqlib/examples/01_basic_run.py \
        python/eqlib/examples/02_param_sweep.py \
        python/eqlib/examples/03_cli_migration.py
git commit -m "docs(eq): add 3 Python example scripts (basic, sweep, migration)"
```

---

## Task 4: Jupyter notebook 2 本

**Files:**
- Create: `python/eqlib/examples/01_quickstart.ipynb`
- Create: `python/eqlib/examples/02_sweep_visualization.ipynb`

**方針:** `.py` の内容を cell 化し markdown 説明を添える。execute せず commit（output cells 空のまま）。CI で nbformat JSON 妥当性だけ確認。

- [ ] **Step 1: 01_quickstart.ipynb**

作成: `python/eqlib/examples/01_quickstart.ipynb`

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# eqlib Quickstart\n",
    "\n",
    "In-process Python wrapper around `eq/libeqapi.so`. Equivalent to running the standalone `eq` binary with `eq.ITER01.in`, but returns structured data instead of writing a plot."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": ["from eqlib import Eqlib"]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Lifecycle\n",
    "\n",
    "Use `Eqlib()` as a context manager. `__enter__` calls `eq_init`; `__exit__` calls `eq_finalize`. Only one `Eqlib` may be live per process (Fortran globals)."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "with Eqlib() as eq:\n",
    "    eq.set_params(\n",
    "        RR=6.2, RA=2.0, RKAP=1.7, RDLT=0.33,\n",
    "        BB=5.3, RIP=15.0,\n",
    "        NRMAX=51, NTHMAX=65, MDLEQF=5,\n",
    "    )\n",
    "    eq.run(ntmax=1)\n",
    "    state = eq.get_state()\n",
    "    print(f'PSITA = {state.PSITA:.4g}   nrmax = {state.nrmax}')"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Profiles\n",
    "\n",
    "`state.PSI / QPS / TTS / PPS / RHO` are length-`nrmax` lists, ready for numpy / matplotlib."
   ]
  }
 ],
 "metadata": {
  "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
  "language_info": {"name": "python", "version": "3"}
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
```

- [ ] **Step 2: 02_sweep_visualization.ipynb**

作成: `python/eqlib/examples/02_sweep_visualization.ipynb`

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# RR / BB sweep with matplotlib heatmap\n",
    "\n",
    "Requires `numpy` and `matplotlib` (optional dependencies; not required for the library itself)."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import numpy as np\n",
    "import matplotlib.pyplot as plt\n",
    "from eqlib import Eqlib"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "rr_grid = np.linspace(5.8, 6.6, 5)\n",
    "bb_grid = np.linspace(5.0, 5.6, 5)\n",
    "data = np.zeros((len(bb_grid), len(rr_grid)))\n",
    "for i, bb in enumerate(bb_grid):\n",
    "    for j, rr in enumerate(rr_grid):\n",
    "        with Eqlib() as eq:\n",
    "            eq.set_params(RR=float(rr), RA=2.0, RKAP=1.7, RDLT=0.33,\n",
    "                          BB=float(bb), RIP=15.0,\n",
    "                          NRMAX=51, NTHMAX=65, MDLEQF=5)\n",
    "            eq.run(ntmax=1)\n",
    "            data[i, j] = eq.get_state().PSITA"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "fig, ax = plt.subplots(figsize=(6, 5))\n",
    "im = ax.imshow(data, origin='lower',\n",
    "               extent=[rr_grid[0], rr_grid[-1], bb_grid[0], bb_grid[-1]],\n",
    "               aspect='auto')\n",
    "ax.set_xlabel('RR [m]')\n",
    "ax.set_ylabel('BB [T]')\n",
    "ax.set_title('PSITA over RR/BB grid')\n",
    "fig.colorbar(im, label='PSITA')\n",
    "plt.tight_layout()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Each sweep cell creates a fresh `Eqlib`; init/finalize cycles ensure global state is reset between cells."
   ]
  }
 ],
 "metadata": {
  "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
  "language_info": {"name": "python", "version": "3"}
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
```

- [ ] **Step 3: JSON 妥当性**

Run:
```bash
python3 -c "import json; json.load(open('/home/k-yoshimi/program/task-private/python/eqlib/examples/01_quickstart.ipynb'))"
python3 -c "import json; json.load(open('/home/k-yoshimi/program/task-private/python/eqlib/examples/02_sweep_visualization.ipynb'))"
```
Expected: 何も出力されず exit 0。

- [ ] **Step 4: コミット**

Run:
```bash
git add python/eqlib/examples/01_quickstart.ipynb \
        python/eqlib/examples/02_sweep_visualization.ipynb
git commit -m "docs(eq): add 2 Jupyter notebooks (quickstart, sweep heatmap)"
```

---

## Task 5: `examples/README.md` index

**Files:**
- Create: `python/eqlib/examples/README.md`

- [ ] **Step 1: index**

作成: `python/eqlib/examples/README.md`

````markdown
# eqlib examples

| File | Kind | Notes |
|---|---|---|
| `01_basic_run.py` | script | Minimal equilibrium run, prints scalars + first 5 profile rows |
| `02_param_sweep.py` | script | 3x3 (RR, BB) sweep, JSON output, no matplotlib dep |
| `03_cli_migration.py` | script | "Before (eq binary)" vs "After (Eqlib)" side-by-side |
| `01_quickstart.ipynb` | notebook | `.py` version of quickstart with markdown commentary |
| `02_sweep_visualization.ipynb` | notebook | Sweep + matplotlib heatmap (requires numpy, matplotlib) |

## Run a script

```bash
PYTHONPATH=python python3 python/eqlib/examples/01_basic_run.py
PYTHONPATH=python python3 python/eqlib/examples/02_param_sweep.py
PYTHONPATH=python python3 python/eqlib/examples/03_cli_migration.py
```

## Open a notebook

```bash
PYTHONPATH=python jupyter lab python/eqlib/examples/
```

Notebooks are committed **unevaluated** (no output cells); execute them
locally to populate output. CI does not run them.
````

- [ ] **Step 2: コミット**

Run:
```bash
git add python/eqlib/examples/README.md
git commit -m "docs(eq): add examples/README.md index"
```

---

## Task 6: examples smoke test

**Files:**
- Create: `python/eqlib/tests/test_examples.py`

- [ ] **Step 1: smoke**

作成: `python/eqlib/tests/test_examples.py`

```python
"""Smoke tests for eqlib.examples.*

01_basic_run is short enough to run end-to-end here; 02/03 are import-only.
"""
import importlib
import unittest
from pathlib import Path

LIBEQAPI = Path(__file__).resolve().parents[3] / "eq" / "libeqapi.so"


@unittest.skipUnless(LIBEQAPI.exists(), "libeqapi.so not built")
class TestExamples(unittest.TestCase):

    def test_basic_run_ends_with_zero(self):
        mod = importlib.import_module("eqlib.examples.01_basic_run")
        self.assertEqual(mod.main(), 0)

    def test_param_sweep_imports(self):
        mod = importlib.import_module("eqlib.examples.02_param_sweep")
        self.assertTrue(callable(mod.main))
        self.assertTrue(callable(mod.run_one))

    def test_cli_migration_imports(self):
        mod = importlib.import_module("eqlib.examples.03_cli_migration")
        self.assertTrue(callable(mod.main))


if __name__ == "__main__":
    unittest.main()
```

注: モジュール名の先頭が数字のため `importlib.import_module` を使う必要がある（`import eqlib.examples.01_basic_run` は構文エラー）。

- [ ] **Step 2: 実行**

Run:
```bash
cd /home/k-yoshimi/program/task-private
PYTHONPATH=python python3 -m unittest eqlib.tests.test_examples -v 2>&1 | tail -10
```
Expected: 3 tests PASS。

- [ ] **Step 3: test_definitions に登録**

`test_run/test_definitions.conf` の EQ Library セクション末尾に追記:

```
eqlib_examples:python:eqlib.tests.test_examples:none:120:Layer L-7 examples smoke
```

Run:
```bash
cd /home/k-yoshimi/program/task-private/test_run
./run_tests.sh eqlib_examples
```
Expected: PASS。

- [ ] **Step 4: コミット**

Run:
```bash
git add python/eqlib/tests/test_examples.py test_run/test_definitions.conf
git commit -m "test(eq): add examples smoke + register eqlib_examples case"
```

---

## Task 7: CHANGELOG / release notes

**Files:**
- Create: `python/eqlib/CHANGELOG.md`

- [ ] **Step 1: CHANGELOG**

作成: `python/eqlib/CHANGELOG.md`

```markdown
# eqlib changelog

Library-ization of TASK/EQ. Versions follow Phase L sub-stages.

## 2026-04-XX  Phase L-7 (this release)

### Added
- Full `README.md`: install, quickstart, 5-fn API reference, registered
  parameter list, migration note (eq binary CLI → libeqapi.so), troubleshooting
- 3 Python example scripts (`examples/01_basic_run.py`,
  `examples/02_param_sweep.py`, `examples/03_cli_migration.py`)
- 2 Jupyter notebooks (`examples/01_quickstart.ipynb`,
  `examples/02_sweep_visualization.ipynb`)
- `examples/README.md` index
- Smoke test `tests/test_examples.py`; `eqlib_examples` case wired into
  `run_tests.sh`
- `docs/eq-library/architecture.md` (C ABI / FFI / high-level layer overview)
- `doc/eq-library.md` global doc entry

### Notes for EQ users
- Existing `eq` binary behavior is unchanged. `libeqapi.so` is a new
  build target alongside.
- Layer 1 equivalence (`1e-10`) has been verified vs `eq_iter01` /
  `eq_tst2` L-0 baselines.

## 2026-04-XX  Phase L-6
- 4-layer tests: equivalence, C ABI, Python wrapper, sweep smoke
- `run_tests.sh` integration: 5 `eqlib_*` cases

## 2026-04-XX  Phase L-5
- `python/eqlib/` package: `Eqlib` class + `_ffi` + `state` + `errors`
- Layer 3 unit tests

## 2026-04-XX  Phase L-4
- `eq/libeqapi.so` shared-library build
- PIC build of bpsd, pl, lib dependencies
- C link smoke

## 2026-04-XX  Phase L-3
- `eq/eq_param_registry.f90` — namelist parameters exposed as setters
- `eq_set_param` C ABI

## 2026-04-XX  Phase L-2
- `eq_state.f90`, `eq_api.f90` (5-fn stub), `eq_api.h`
- C compile-only smoke

## 2026-04-XX  Phase L-1
- `eq/Makefile`: SRCS split into CORE / GRAPHICS / MENU groups

## 2026-04-XX  Phase L-0
- `eqregress.f90` high-precision dump
- Baseline cases `eq_iter01`, `eq_tst2`
- `test_run/scripts/extract_eq_metrics.py`
```

- [ ] **Step 2: コミット**

Run:
```bash
git add python/eqlib/CHANGELOG.md
git commit -m "docs(eq): add CHANGELOG for eqlib L-0..L-7"
```

---

## Task 8: Architecture overview (optional)

**Files:**
- Create: `docs/eq-library/architecture.md`

- [ ] **Step 1: architecture.md**

作成: `docs/eq-library/architecture.md`

````markdown
# eq library architecture

Three-layer stack (mirrors TR / FP / TI library-ization):

```
+---------------------------------------------------+
|  High-level Python:  eqlib.Eqlib                  |  ← users' entry point
+---------------------------------------------------+
|  FFI layer:          eqlib._ffi (ctypes)          |
+---------------------------------------------------+
|  C ABI:              eq/eq_api.h (5 functions)    |  ← stable contract
|                      eq/libeqapi.so               |
+---------------------------------------------------+
|  Fortran core:       eq/eq_api.f90 + eq_param_*   |
|                      + eqcalc, eqcalq, eqcalv ... |  (unchanged from eq binary)
+---------------------------------------------------+
```

## C ABI (5 functions)

All return `int` status codes; see `eq/eq_api.h` for constants.

| Symbol | Purpose |
|---|---|
| `eq_init()` | Initialize eq globals (one-time per process) |
| `eq_set_param(name, value)` | Dispatch to `eq_param_registry.f90` |
| `eq_run(ntmax)` | Call eqinit + eqcalc loop for ntmax iterations |
| `eq_get_state(*state)` | Snapshot eqcomm into opaque struct |
| `eq_finalize()` | Release resources (idempotent) |

## Layer responsibilities

- **Fortran core:** unchanged from the `eq` binary. Graphics (`eqgout`,
  `eqg2d`, `eqg3d`, `eqgsub`, `eqfile`) and the interactive menu
  (`eqmenu`) are excluded from `libeqapi.so` (see Makefile SRCS_CORE /
  SRCS_GRAPHICS / SRCS_MENU split from L-1).
- **C ABI:** frozen 5-function interface, ISO_C_BINDING. This is what
  third-party code (including Python) calls.
- **FFI layer (`eqlib._ffi`):** `ctypes.CDLL` load, argtypes/restype
  declarations, raw `eq_*` calls.
- **High-level (`eqlib.Eqlib`):** context manager, exception mapping,
  `set_params(**kwargs)` sugar, `EqState` dataclass construction.

## Test layers

See `docs/superpowers/plans/2026-04-18-eq-library-L6-test-4layers.md`:

1. **Equivalence** (`python/eqlib/tests/test_equivalence.py`) — bit-level
   match vs eq binary baselines (tol 1e-10).
2. **C ABI** (`eq/tests/c_abi/`) — smoke, param dispatch, run, negative.
3. **Python contract** (`tests/test_ffi.py`) — context manager, set_params,
   exception hierarchy.
4. **Sweep** (`tests/test_sweep.py`) — 3x3 RR/BB/RIP grid smoke.

## Related design docs

- Canonical spec: `docs/superpowers/specs/2026-04-17-tr-library-design.md` (TR)
- Phase plans: `docs/superpowers/plans/2026-04-18-eq-library-L*.md`
````

- [ ] **Step 2: コミット**

Run:
```bash
git add docs/eq-library/architecture.md
git commit -m "docs(eq): add architecture overview for library-ization (L-7)"
```

---

## Task 9: Global doc entry + Phase L completion report

**Files:**
- Create: `doc/eq-library.md`
- Create: `docs/superpowers/notes/2026-04-18-eq-phase-l-completion.md`

- [ ] **Step 1: `doc/eq-library.md`**

作成: `doc/eq-library.md`

```markdown
# TASK/EQ Library API

The eq module is callable as an in-process library via:

- **C ABI:** `eq/eq_api.h` + `eq/libeqapi.so` (5 functions:
  `eq_init`, `eq_set_param`, `eq_run`, `eq_get_state`, `eq_finalize`)
- **Python wrapper:** `python/eqlib/` (`from eqlib import Eqlib`)

See:
- Python README: [`python/eqlib/README.md`](../python/eqlib/README.md)
- Architecture: [`docs/eq-library/architecture.md`](../docs/eq-library/architecture.md)
- Design spec (TR template, eq follows the same pattern): [`docs/superpowers/specs/2026-04-17-tr-library-design.md`](../docs/superpowers/specs/2026-04-17-tr-library-design.md)
- Phase plans: [`docs/superpowers/plans/2026-04-18-eq-library-L*.md`](../docs/superpowers/plans/)
- Examples: [`python/eqlib/examples/`](../python/eqlib/examples/)
- Changelog: [`python/eqlib/CHANGELOG.md`](../python/eqlib/CHANGELOG.md)

The standalone `eq` binary (with graphics + interactive menu) is preserved
unchanged; the library is an additional build target.
```

- [ ] **Step 2: completion report**

作成: `docs/superpowers/notes/2026-04-18-eq-phase-l-completion.md`

```markdown
# EQ Phase L completion report

Acceptance criteria from design spec §12.2, eq-adapted:

| 受け入れ基準 | サブ Phase | 確認方法 | 状態 |
|---|---|---|---|
| `eq/libeqapi.so` 生成 | L-4 | `ls eq/libeqapi.so && file eq/libeqapi.so` | OK / FAIL |
| `from eqlib import Eqlib` 可能 | L-5 | `python3 -c "from eqlib import Eqlib"` | OK / FAIL |
| Layer 1 等価性 (eq_iter01, eq_tst2) PASS | L-6 | `./run_tests.sh eqlib_equivalence` | OK / FAIL |
| Layer 2 C ABI (smoke/param/run/negative) PASS | L-6 | `make -C eq/tests/c_abi test` | OK / FAIL |
| Layer 3 Python wrapper PASS | L-6 | `./run_tests.sh eqlib_ffi` | OK / FAIL |
| Layer 4 sweep smoke PASS | L-6 | `./run_tests.sh eqlib_sweep` | OK / FAIL |
| eq バイナリ数値が L-0 baseline と一致 | L-0〜L-6 全節 | `./run_tests.sh eq_iter01 eq_tst2` | OK / FAIL |
| `python/eqlib/README.md` に使用例 + migration note | L-7 | 目視 | OK / FAIL |
| `run_tests.sh` に `eqlib_*` 統合 | L-6 | `grep eqlib_ test_definitions.conf` | OK / FAIL |
| 3 example scripts + 2 notebooks 実行可能 | L-7 | `PYTHONPATH=python python3 python/eqlib/examples/01_basic_run.py` | OK / FAIL |
| `CHANGELOG.md` に L-0..L-7 の履歴 | L-7 | 目視 | OK / FAIL |
| `doc/eq-library.md` global entry | L-7 | 目視 | OK / FAIL |

## サブ Phase 別 PR

- L-0: <PR URL>
- L-1: <PR URL>
- L-2: <PR URL>
- L-3: <PR URL>
- L-4: <PR URL>
- L-5: <PR URL>
- L-6: <PR URL>
- L-7: <PR URL>
```

- [ ] **Step 3: コミット**

Run:
```bash
git add doc/eq-library.md docs/superpowers/notes/2026-04-18-eq-phase-l-completion.md
git commit -m "docs(eq): add global doc entry + Phase L completion report"
```

---

## Task 10: 最終確認 + PR

- [ ] **Step 1: examples + tests が PASS**

Run:
```bash
cd /home/k-yoshimi/program/task-private
PYTHONPATH=python python3 python/eqlib/examples/01_basic_run.py 2>&1 | tail -10
PYTHONPATH=python python3 python/eqlib/examples/02_param_sweep.py 2>&1 | head -30
PYTHONPATH=python python3 python/eqlib/examples/03_cli_migration.py 2>&1 | tail -10
cd test_run && ./run_tests.sh 2>&1 | tail -10
```
Expected: 3 本の example が完走、`run_tests.sh` 全 PASS（`eqlib_examples` を含む）。

- [ ] **Step 2: 変更ファイル確認**

Run:
```bash
git diff --stat origin/develop..HEAD
```
Expected:
- 修正: `python/eqlib/README.md`, `test_run/test_definitions.conf`
- 新規: `python/eqlib/examples/` (3 `.py` + 2 `.ipynb` + `__init__.py` + `README.md`),
  `python/eqlib/tests/test_examples.py`, `python/eqlib/CHANGELOG.md`,
  `docs/eq-library/architecture.md`, `doc/eq-library.md`,
  `docs/superpowers/notes/2026-04-18-eq-phase-l-completion.md`

- [ ] **Step 3: push + PR**

Run:
```bash
git push -u origin feature/eq-library-L7-docs
gh pr create --base develop \
  --title "docs(eq): Phase L-7 README + examples + CHANGELOG + migration note" \
  --body "Phase L-7: Expanded README with 5-fn API and CLI→libeqapi.so migration note. 3 example scripts + 2 Jupyter notebooks. CHANGELOG covers L-0..L-7. Architecture doc under docs/eq-library/. Completion report with §12.2 matrix. Closes the EQ library project."
```

---

## Risk / Mitigation

| Risk | Mitigation |
|---|---|
| `01_basic_run.py` が実行時に `EqlibParamError` を出す | registry 未露出パラメータを removed / ifguard — fixture (`eq_iter01_params.py`) と整合 |
| Notebook の JSON が手書きで壊れる | `json.load()` 妥当性チェックを Task 4 Step 3 で実施。CI で再度検証 |
| Migration note が既存 `eq` ユーザにミスリーディング | 「CLI 側の出力 (graphics) は失われる」「string parameters は未対応」を明示 |
| CHANGELOG の日付が仮置き（`2026-04-XX`） | L-7 merge 時に実日付に置換する最終コミット |
| `docs/eq-library/architecture.md` の内容が L-6 と重複 | architecture は「構造の俯瞰」、L-6 plan は「テスト手順」と責務分離を明示 |
| `doc/eq-library.md` から相対リンクが壊れる | `task-private` ↔ `task` 公開リポジトリで path を確認。worktree 移動時に再評価 |
| Notebook の JSON で先頭に数字のモジュール名を使えない | `01_basic_run.py` は `importlib.import_module` で load する運用（test_examples.py 側で対応済） |
| examples 実行で発覚したバグ | L-3〜L-6 の該当 Phase に戻して別 PR。L-7 自体は保留しない |

## Testing strategy

- **Pre-merge:**
  1. 3 example `.py` が exit 0
  2. 2 `.ipynb` が `json.load()` 成功
  3. `eqlib.tests.test_examples` の 3 tests PASS
  4. `eqlib_examples` ケースが `./run_tests.sh eqlib_examples` で PASS
  5. `./run_tests.sh` 全体で既存 + eqlib_* すべて PASS
  6. `python/eqlib/README.md` の code blocks が偶数（開閉ペア）

- **Post-merge:**
  - Completion report マトリクスを「OK / FAIL」→ 実態に埋める

## 受け入れ基準

- [ ] `python/eqlib/README.md` に install / quickstart / 5-fn API / params / migration note / troubleshooting が揃っている
- [ ] `python/eqlib/examples/` に 3 script + 2 notebook + README.md が存在
- [ ] `python/eqlib/CHANGELOG.md` に L-0〜L-7 の記述
- [ ] `eqlib_examples` ケースが `./run_tests.sh` に統合され PASS
- [ ] `doc/eq-library.md` と `docs/eq-library/architecture.md` が存在、相対リンク妥当
- [ ] `docs/superpowers/notes/2026-04-18-eq-phase-l-completion.md` マトリクスが全 OK
- [ ] 既存 `eq_iter01`, `eq_tst2` および L-6 `eqlib_*` が regression なく PASS
- [ ] PR が develop にマージ可能

## Deliverables checklist

- [ ] `python/eqlib/README.md` 本格化（quickstart + 5-fn API + migration note）
- [ ] `python/eqlib/examples/__init__.py`
- [ ] `python/eqlib/examples/01_basic_run.py`
- [ ] `python/eqlib/examples/02_param_sweep.py`
- [ ] `python/eqlib/examples/03_cli_migration.py`
- [ ] `python/eqlib/examples/01_quickstart.ipynb`
- [ ] `python/eqlib/examples/02_sweep_visualization.ipynb`
- [ ] `python/eqlib/examples/README.md`
- [ ] `python/eqlib/tests/test_examples.py`
- [ ] `python/eqlib/CHANGELOG.md`
- [ ] `docs/eq-library/architecture.md` (optional but recommended)
- [ ] `doc/eq-library.md`
- [ ] `docs/superpowers/notes/2026-04-18-eq-phase-l-completion.md`
- [ ] `test_run/test_definitions.conf` に `eqlib_examples` 追加

## 依存

- 上流: L-6 (4 層テスト + `eqlib_*` 統合) マージ済
- 後続: なし（Phase L 完了）
