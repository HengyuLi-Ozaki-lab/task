# TI Library Phase L-7: Documentation 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-5 で書いた最小 README を拡充し、エンドユーザ（プラズマ研究者）が `tilib` を使い始められるドキュメントと使用例を整える。`python/tilib/README.md` を本格化、`python/tilib/examples/` に 2 本の Jupyter ノートブック（最小例 + 不純物パラメータスイープ）と 1 本の Python スクリプト例を追加する。CI 統合では notebook の execute は重いのでスキップし、pytest 経由で `.py` 例だけ smoke を回す。

**Architecture:** ドキュメントのみのフェーズ。コード（Fortran/Python wrapper）は変更しない。Jupyter notebook は `nbformat` で書ける範囲の最小 cell 構成（`%matplotlib inline` を含めない、execute せず view 可能）。

**Tech Stack:** Markdown, Jupyter notebook (json), Python 3。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` 9 章 L-7 (ドキュメント)、12 章 受け入れ基準 (`README.md` に使用例)。

---

## File Structure

このフェーズで作成・変更するファイル:

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/tilib/README.md` | 修正 | L-5 の最小版を拡充（API リファレンス、サンプル、トラブルシューティング） |
| `python/tilib/examples/quickstart.py` | 新規 | 最小実行可能 Python スクリプト |
| `python/tilib/examples/sweep_impurity.py` | 新規 | Ar 不純物パラメータスイープ Python スクリプト |
| `python/tilib/examples/01_quickstart.ipynb` | 新規 | Jupyter notebook 版 quickstart |
| `python/tilib/examples/02_impurity_sweep.ipynb` | 新規 | Jupyter notebook 版 impurity sweep |
| `python/tilib/examples/README.md` | 新規 | examples ディレクトリの index |
| `python/tilib/tests/test_examples.py` | 新規 | examples/*.py が import + run できることの smoke test |
| `docs/superpowers/specs/2026-04-17-tr-library-design.md` | 修正（任意） | ti 用補足セクション追加（または `tilib-design.md` を別途新設） — 本計画では追加しない判断、L-7 はあくまで利用ドキュメント |

---

## Task 1: 前提確認

**Files:**
- なし

- [ ] **Step 1: ブランチ作成と L-6 マージ確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin
git checkout -b feature/ti-library-L7-docs origin/develop
ls /home/k-yoshimi/program/task/python/tilib/tests/test_equivalence.py
```
Expected: L-6 がマージされている。

- [ ] **Step 2: 既存の最小 README を読む**

Run:
```bash
cat /home/k-yoshimi/program/task/python/tilib/README.md
```
Expected: L-5 で書いた quickstart 記述。

- [ ] **Step 3: examples ディレクトリ作成**

Run:
```bash
mkdir -p /home/k-yoshimi/program/task/python/tilib/examples
```

- [ ] **Step 4: 空コミット**

Run:
```bash
git commit --allow-empty -m "chore(tilib): start L-7 documentation"
```

---

## Task 2: `examples/quickstart.py` を新設

**Files:**
- Create: `python/tilib/examples/quickstart.py`

- [ ] **Step 1: スクリプト作成**

作成: `python/tilib/examples/quickstart.py`

```python
#!/usr/bin/env python3
"""tilib quickstart example.

Equivalent to running the standalone `ti` binary with `tiparm.org`:
    NSMAX=1, NRMAX=10, NTMAX=2 — minimum sanity case.

Usage:
    cd python && python -m tilib.examples.quickstart
or
    PYTHONPATH=python python python/tilib/examples/quickstart.py
"""

from tilib import Tilib


def main() -> int:
    with Tilib() as ti:
        ti.set_params(
            NSMAX=1,
            NRMAX=10,
            NTMAX=2,
            NTSTEP=1,
            NGTSTEP=1,
            NGRSTEP=1,
        )
        ti.run(ntmax=2)
        state = ti.get_state()

        print(f"NT     = {state.nt}")
        print(f"T      = {state.T:.6e} s")
        print(f"NRMAX  = {state.nrmax}")
        print(f"nsa    = {state.nsa_max}")
        print(f"residual_loop_max = {state.residual_loop_max:.3e}")
        print(f"icount_loop_max   = {state.icount_loop_max}")

        print("\nradial profile (NR, RBP, RQP, RJP, ZEFF):")
        for r in range(state.nrmax):
            print(f"  {r+1:3d}  {state.RBP[r]: .3e}  {state.RQP[r]: .3e}"
                  f"  {state.RJP[r]: .3e}  {state.ZEFF[r]: .3e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 手動実行確認**

Run:
```bash
cd /home/k-yoshimi/program/task
[ -f ti/libtiapi.so ] || (cd ti && make libtiapi.so) > /dev/null 2>&1
PYTHONPATH=python python3 python/tilib/examples/quickstart.py
```
Expected: NT/T/NRMAX 等の値が表示され、profile が 10 行印字される。エラーなし。

- [ ] **Step 3: コミット**

Run:
```bash
git add python/tilib/examples/quickstart.py
git commit -m "docs(tilib): add examples/quickstart.py"
```

---

## Task 3: `examples/sweep_impurity.py` を新設

**Files:**
- Create: `python/tilib/examples/sweep_impurity.py`

- [ ] **Step 1: スクリプト作成**

作成: `python/tilib/examples/sweep_impurity.py`

```python
#!/usr/bin/env python3
"""Argon impurity transport: small parameter sweep over NRMAX and BB.

For each (NRMAX, BB) cell, advance NTMAX=5 steps and report:
   - icount_loop_max (convergence iterations)
   - residual_loop_max (largest residual seen)
   - max(ZEFF[NR]) (rough impurity loading)

This is a smoke-level example, not a physically meaningful scan.
"""

from tilib import Tilib


# Base parameters mirroring test_run/inputs/ti_ar.in (without RUN/QUIT lines).
BASE = dict(
    NSMAX=3,
    DT0=1.0,
    DR0=1.0,
    DRS=3.0,
    NTSTEP=1, NGTSTEP=1, NGRSTEP=1,
    NTMAX=5,
)

# Per-impurity-species (NS=3 = Ar) settings via array subscript syntax.
AR_SETUP = {
    "NPA[3]":     18.0,
    # Atomic mass: plcomm true name is PA; the ti namelist's `PM` is a local
    # alias via `USE plcomm, pm=>pa`. The C ABI registry registers PA only.
    "PA[3]":      39.95,
    "ID_NS[3]":   10.0,
    "NZMIN_NS[3]": 15.0,
    "NZMAX_NS[3]": 18.0,
    "MODEL_BND[1,3]": 2.0,
    "BND_VALUE[1,3]": 1.0,
}


def run_one(nrmax: int, bb: float) -> dict:
    with Tilib() as ti:
        ti.set_params(**BASE, NRMAX=nrmax, BB=bb)
        for k, v in AR_SETUP.items():
            ti.set_param(k, v)
        ti.run(ntmax=int(BASE["NTMAX"]))
        s = ti.get_state()
        return {
            "NRMAX": s.nrmax,
            "BB": bb,
            "icount_loop_max": s.icount_loop_max,
            "residual_loop_max": s.residual_loop_max,
            "ZEFF_max": max(s.ZEFF) if s.ZEFF else 0.0,
        }


def main() -> int:
    rows = []
    for nrmax in (10, 15, 20):
        for bb in (4.5, 5.3, 6.0):
            rows.append(run_one(nrmax, bb))

    print(f"{'NRMAX':>5}  {'BB':>5}  {'iters':>6}  {'residual':>12}  {'ZEFF_max':>10}")
    for r in rows:
        print(f"{r['NRMAX']:>5d}  {r['BB']:>5.2f}  {r['icount_loop_max']:>6d}"
              f"  {r['residual_loop_max']:>12.3e}  {r['ZEFF_max']:>10.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 手動実行確認**

Run:
```bash
cd /home/k-yoshimi/program/task
PYTHONPATH=python python3 python/tilib/examples/sweep_impurity.py
```
Expected: 9 行のテーブル表示。エラーなし。実行時間は ~1-2 分。

- [ ] **Step 3: コミット**

Run:
```bash
git add python/tilib/examples/sweep_impurity.py
git commit -m "docs(tilib): add examples/sweep_impurity.py (Ar sweep)"
```

---

## Task 4: examples 用 smoke test を追加

**Files:**
- Create: `python/tilib/tests/test_examples.py`

**目的:** `examples/*.py` が import 段階で壊れていないこと、`quickstart.py` を実際に走らせると exit 0 になることを確認。`sweep_impurity.py` は重いので import smoke のみ。

- [ ] **Step 1: テスト作成**

作成: `python/tilib/tests/test_examples.py`

```python
"""Smoke tests for tilib.examples.*

quickstart.py is short enough to run end-to-end here; sweep_impurity.py is
import-only (the actual run takes ~1 minute and is exercised by
test_sweep.py separately).
"""

import importlib
import os
import unittest
from pathlib import Path

LIBTIAPI = Path(__file__).resolve().parents[3] / "ti" / "libtiapi.so"


@unittest.skipUnless(LIBTIAPI.exists(), "libtiapi.so not built")
class TestExamples(unittest.TestCase):

    def test_quickstart_imports_and_runs(self):
        mod = importlib.import_module("tilib.examples.quickstart")
        rc = mod.main()
        self.assertEqual(rc, 0)

    def test_sweep_imports(self):
        # import only — actual run is too slow for unit tests
        mod = importlib.import_module("tilib.examples.sweep_impurity")
        self.assertTrue(callable(mod.run_one))
        self.assertTrue(callable(mod.main))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: examples/__init__.py を作成**

Run:
```bash
: > /home/k-yoshimi/program/task/python/tilib/examples/__init__.py
```

- [ ] **Step 3: テスト実行**

Run:
```bash
cd /home/k-yoshimi/program/task
PYTHONPATH=python python3 -m unittest python.tilib.tests.test_examples -v 2>&1 | tail -10
```
Expected: 2 tests PASS。

- [ ] **Step 4: コミット**

Run:
```bash
git add python/tilib/examples/__init__.py python/tilib/tests/test_examples.py
git commit -m "test(tilib): add smoke for examples (quickstart run, sweep import)"
```

---

## Task 5: Jupyter notebook 2 本を追加

**Files:**
- Create: `python/tilib/examples/01_quickstart.ipynb`
- Create: `python/tilib/examples/02_impurity_sweep.ipynb`

**方針:** Notebook は `.py` の内容を cell 化したものに markdown 説明を追加するだけ。execute せず（CI で重いため）、出力 cell は空のまま commit。

- [ ] **Step 1: 01_quickstart.ipynb を作成**

作成: `python/tilib/examples/01_quickstart.ipynb`

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# tilib Quickstart\n",
    "\n",
    "In-process Python wrapper around `ti/libtiapi.so`. Equivalent to running the standalone `ti` binary with `tiparm.org`."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "from tilib import Tilib"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Lifecycle\n",
    "\n",
    "Use `Tilib()` as a context manager. On entry it calls `ti_init`; on exit it calls `ti_finalize`. Only one Tilib may be live per process at a time (Fortran globals)."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "with Tilib() as ti:\n",
    "    ti.set_params(\n",
    "        NSMAX=1, NRMAX=10, NTMAX=2,\n",
    "        NTSTEP=1, NGTSTEP=1, NGRSTEP=1,\n",
    "    )\n",
    "    ti.run(ntmax=2)\n",
    "    state = ti.get_state()\n",
    "    print(f'T = {state.T:.6e} s   nt = {state.nt}   NRMAX = {state.nrmax}')"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Profiles\n",
    "\n",
    "`state.RBP / RQP / RJP / ZEFF / BETA / BETAP` are length-`nrmax` lists. `state.RNA / RTA / RUA` are nested `[nrmax][nsa_max]`."
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
```

- [ ] **Step 2: 02_impurity_sweep.ipynb を作成**

作成: `python/tilib/examples/02_impurity_sweep.ipynb`

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Argon Impurity Parameter Sweep\n",
    "\n",
    "Same intent as `test_run/inputs/ti_ar.in`, but driven from Python without spawning subprocesses. Sweeps `(NRMAX, BB)` over a 3x3 grid."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "from tilib import Tilib\n",
    "\n",
    "BASE = dict(\n",
    "    NSMAX=3, DT0=1.0, DR0=1.0, DRS=3.0,\n",
    "    NTSTEP=1, NGTSTEP=1, NGRSTEP=1,\n",
    "    NTMAX=5,\n",
    ")\n",
    "AR_SETUP = {\n",
    "    'NPA[3]': 18.0, 'PA[3]': 39.95, 'ID_NS[3]': 10.0,\n",
    "    'NZMIN_NS[3]': 15.0, 'NZMAX_NS[3]': 18.0,\n",
    "    'MODEL_BND[1,3]': 2.0, 'BND_VALUE[1,3]': 1.0,\n",
    "}"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "rows = []\n",
    "for nrmax in (10, 15, 20):\n",
    "    for bb in (4.5, 5.3, 6.0):\n",
    "        with Tilib() as ti:\n",
    "            ti.set_params(**BASE, NRMAX=nrmax, BB=bb)\n",
    "            for k, v in AR_SETUP.items():\n",
    "                ti.set_param(k, v)\n",
    "            ti.run(ntmax=int(BASE['NTMAX']))\n",
    "            s = ti.get_state()\n",
    "            rows.append((nrmax, bb, s.icount_loop_max, max(s.ZEFF)))\n",
    "for r in rows: print(r)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Note: each sweep cell creates a fresh Tilib; init/finalize cycles ensure global state is reset between cells."
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

- [ ] **Step 3: notebook の JSON 妥当性を確認**

Run:
```bash
python3 -c "import json; json.load(open('/home/k-yoshimi/program/task/python/tilib/examples/01_quickstart.ipynb'))"
python3 -c "import json; json.load(open('/home/k-yoshimi/program/task/python/tilib/examples/02_impurity_sweep.ipynb'))"
```
Expected: 何も出力されず exit 0（JSON 妥当）。

- [ ] **Step 4: コミット**

Run:
```bash
git add python/tilib/examples/01_quickstart.ipynb python/tilib/examples/02_impurity_sweep.ipynb
git commit -m "docs(tilib): add 2 Jupyter notebooks (quickstart, Ar sweep)"
```

---

## Task 6: `examples/README.md` を新設

**Files:**
- Create: `python/tilib/examples/README.md`

- [ ] **Step 1: index 作成**

作成: `python/tilib/examples/README.md`

````markdown
# tilib examples

| File | Kind | Notes |
|---|---|---|
| `quickstart.py` | script | Minimal NSMAX=1 sanity run, prints scalar + profile. |
| `sweep_impurity.py` | script | 3x3 (NRMAX, BB) Ar impurity sweep, prints table. |
| `01_quickstart.ipynb` | notebook | Same as quickstart.py with markdown commentary. |
| `02_impurity_sweep.ipynb` | notebook | Same as sweep_impurity.py with markdown commentary. |

## Run a script

```bash
PYTHONPATH=python python3 python/tilib/examples/quickstart.py
PYTHONPATH=python python3 python/tilib/examples/sweep_impurity.py
```

## Open a notebook

```bash
PYTHONPATH=python jupyter lab python/tilib/examples/
```

Notebooks are committed unevaluated (no output cells); execute them locally
to populate output. CI does not run them.
````

- [ ] **Step 2: コミット**

Run:
```bash
git add python/tilib/examples/README.md
git commit -m "docs(tilib): add examples/README.md index"
```

---

## Task 7: `python/tilib/README.md` を本格化

**Files:**
- Modify: `python/tilib/README.md`

- [ ] **Step 1: README を全面書き換え**

`python/tilib/README.md` を以下で上書き:

````markdown
# tilib — Python wrapper for TASK/TI

In-process Python wrapper around `ti/libtiapi.so` (a shared library built from
the TASK/TI Fortran code). Lets you drive impurity-transport runs from Python
with no `subprocess` overhead — useful for parameter sweeps, optimization, and
Jupyter exploration.

## Status

Phase L-7 of the TI library project. APIs are stable for the L-3 parameter set
(~35 names registered in `ti/ti_param_registry.f90`).

## Build

The shared library is built with the rest of TI:

```bash
cd ti
make libtiapi.so
```

This produces `ti/libtiapi.so`. The `tilib` Python package finds it via:
1. `Tilib(lib_path="...")` argument
2. `TILIB_PATH` env var
3. `<repo>/ti/libtiapi.so` (default)

## Quick start

```python
from tilib import Tilib

with Tilib() as ti:
    ti.set_params(NSMAX=1, NRMAX=10, NTMAX=10,
                  NTSTEP=1, NGTSTEP=1, NGRSTEP=1)
    ti.run(ntmax=10)
    state = ti.get_state()
    print(state.T, state.RQP)
```

See `examples/` for full scripts and notebooks.

## API reference

### `Tilib`

| Method | Returns | Notes |
|---|---|---|
| `Tilib(lib_path=None)` | Tilib | Calls `ti_init`. Use as context manager. |
| `ti.set_param(name, value)` | None | `value` is float; ints are converted with `INT(value)`. |
| `ti.set_params(**kwargs)` | None | Bulk set via keyword args. |
| `ti.run(ntmax)` | None | Calls `ti_prep` on first call, then `ti_exec(ntmax)`. |
| `ti.get_state()` | TiState | Snapshot of current ticomm state. |
| `ti.close()` | None | Calls `ti_finalize`. Auto-called on `__exit__`. |

Exceptions raised on non-zero `ierr`:
| ierr | Exception |
|---|---|
| 1 | `TilibParamError` (unknown name or bad index) |
| 2 | `TilibInitError` (lifecycle violation) |
| 3 | `TilibRunError` (calculation failed) |
| 4 | `TilibStateError` (NRMAX > TI_MAX_NRMAX) |

### `TiState` dataclass

Fields (sized to runtime nrmax / nsa_max):

| Field | Type | Shape |
|---|---|---|
| `nt`, `nrmax`, `nsa_max`, `nsmax` | int | scalar |
| `T`, `residual_loop_max` | float | scalar |
| `icount_loop_max`, `icount_mat_max` | int | scalar |
| `RNA`, `RTA`, `RUA` | List[List[float]] | [nrmax][nsa_max] |
| `RBP`, `RQP`, `RJP`, `ZEFF`, `BETA`, `BETAP` | List[float] | [nrmax] |

## Parameter names

Registered in `ti/ti_param_registry.f90`. Highlights:

- Geometry: `RR`, `RA`, `RKAP`, `RDLT`, `BB`, `RIP`
- Profile shape: `PROFN1/2`, `PROFT1/2`, `PROFU1/2`
- Plasma: `NSMAX`, `PA[NS]` (atomic mass; ti namelist alias `PM`), `PZ[NS]`, `PN[NS]`, `PNS[NS]`, `PT[NS]`, `PTPR[NS]`, `PTPP[NS]`, `PTS[NS]`, `PU[NS]`, `PUS[NS]`
- Species type: `NPA[NS]`, `ID_NS[NS]`, `NZMIN_NS[NS]`, `NZMAX_NS[NS]`, `NZINI_NS[NS]`
- Time: `DT`, `NRMAX`, `NTMAX`, `NTSTEP`, `NGTSTEP`, `NGRSTEP`, `MAXLOOP`, `EPSLOOP`, `EPSMAT`, `MATTYPE`
- Transport switches: `MODELG/Q/_PROF/_NPROF/_KAI/_DRR/_VR/_NC/_NF/_NB/_EC/_LH/_IC/_CD/_SYNC/_PEL/_PSC`
- Boundary: `MODEL_BND[1..3,NS]`, `BND_VALUE[1..3,NS]`

For unsupported names see "Adding a new parameter" below.

## Limitations

- **Single-instance**: Fortran globals are shared in one process. Don't create
  two `Tilib()` objects concurrently. For parallel sweeps use Python's
  `multiprocessing` (each worker gets its own libtiapi.so state).
- **No MPI**.
- **String parameters** (e.g., `KID_NS[3]='Ar'`) are not yet supported through
  `set_param`. Set them via the standalone `ti` binary's namelist or wait for a
  future `ti_set_string_param` extension.

## Adding a new parameter

1. Edit `ti/ti_param_registry.f90` and add a `CASE ("MY_NEW_PARAM")` entry
   in the `SELECT CASE (TRIM(base))` block.
2. Rebuild: `cd ti && make libtiapi.so`.
3. Use it: `ti.set_param("MY_NEW_PARAM", 1.23)`.

No Python changes are needed.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `FileNotFoundError: libtiapi.so not found` | not built | `cd ti && make libtiapi.so` |
| `OSError: ... cannot open shared object` | libtiapi.so depends on shared `libmpi`/`libmumps` not in `LD_LIBRARY_PATH` | export `LD_LIBRARY_PATH` to include MUMPS install path |
| `TilibParamError` on a name you expect | not registered yet | see "Adding a new parameter" |
| `TilibStateError: ierr=4` | `NRMAX > TI_MAX_NRMAX` (200) | reduce NRMAX or raise `TI_MAX_NRMAX` in `ti/ti_state.f90` and `ti/ti_api.h` |
| Numerical drift vs `ti` binary | param missing from registry | add the missing one and re-run |

## Tests

```bash
PYTHONPATH=python python3 -m unittest discover python/tilib/tests -v
```

Layers:
- L3 (`test_ffi.py`, `test_tilib.py`) — Pythonic interface
- L1 (`test_equivalence.py`) — bit-equivalent vs ti binary baselines
- L4 (`test_sweep.py`) — 3x3 grid completes
- examples (`test_examples.py`) — quickstart runs end-to-end
- C-side (`ti/tests/c_abi/`) — `make test` covers compile/link/state/registry

## See also

- `docs/superpowers/specs/2026-04-17-tr-library-design.md` — architecture (TR;
  ti follows the same pattern with `ti_*` symbols).
- `docs/superpowers/plans/2026-04-18-ti-library-L*.md` — implementation plans.
````

- [ ] **Step 2: README の Markdown 構造確認**

Run:
```bash
python3 -c "
import re
text = open('/home/k-yoshimi/program/task/python/tilib/README.md').read()
print('headers:', len(re.findall(r'^#', text, re.MULTILINE)))
print('code blocks:', text.count('```'))
"
```
Expected: headers > 5, code blocks は偶数（開閉ペア）。

- [ ] **Step 3: コミット**

Run:
```bash
git add python/tilib/README.md
git commit -m "docs(tilib): expand README with full API/params/troubleshooting"
```

---

## Task 8: examples を test_definitions に登録（任意）

**Files:**
- Modify: `test_run/test_definitions.conf`

- [ ] **Step 1: examples 用ケースを追加**

`test_run/test_definitions.conf` の TI Library セクション末尾に追記:

```
tilib_examples:python:tilib.tests.test_examples:none:120:Layer L-7 examples smoke
```

- [ ] **Step 2: 実行確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tilib_examples
```
Expected: PASS（quickstart.py 実行完走、sweep import OK）。

- [ ] **Step 3: コミット**

Run:
```bash
git add test_run/test_definitions.conf
git commit -m "test(tilib): register tilib_examples case in test_definitions"
```

---

## Task 9: 全 ti/tilib テスト最終確認 + PR

- [ ] **Step 1: フル回帰**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh
```
Expected: 全テスト PASS（FAILED=0）。tilib_* も含めて。

- [ ] **Step 2: 変更ファイル確認**

Run:
```bash
git diff --stat origin/develop..HEAD
```
Expected:
- 新規: `python/tilib/examples/*.py` (3), `python/tilib/examples/*.ipynb` (2), `python/tilib/examples/__init__.py`, `python/tilib/examples/README.md`, `python/tilib/tests/test_examples.py`
- 修正: `python/tilib/README.md`, `test_run/test_definitions.conf`

- [ ] **Step 3: push と PR**

Run:
```bash
git push -u origin feature/ti-library-L7-docs
gh pr create --base develop \
  --title "docs(tilib): expand README + 4 examples + smoke test (L-7)" \
  --body "Phase L-7 (final): full README with API/params/troubleshooting, 2 .py examples + 2 Jupyter notebooks, smoke test for examples. Closes the TI library project."
```

---

## Dependencies

- 前段階: L-6 マージ済み（4 層テスト + tilib_* run_tests.sh 統合）。
- 後段階: なし（Phase L 完了）。

## Fallback

| 障害 | 対処 |
|---|---|
| `quickstart.py` の `set_params(NSMAX=1, ...)` が ierr=1 を返す | `ti_param_registry.f90` に `NSMAX` 登録漏れ → L-3 を再点検 |
| sweep_impurity の `MODEL_BND[1,3]=2` が ierr=2 を返す | `parse_subscript` のカンマ処理確認 → L-3 Task 4 のテストが通っているか |
| Jupyter notebook の JSON が壊れる | `python -c "import json; json.load(open(...))"` で検証。修正は手動 |
| `tilib_examples` ケースで quickstart の出力が長すぎ log で埋まる | quickstart.py の print 量を絞る、または run_tests.sh 側で head 制限 |
| README の link が壊れる | 相対パスで書いてあるので worktree 移動時は再評価。本フェーズは worktree 内で完結なので発生しない想定 |
