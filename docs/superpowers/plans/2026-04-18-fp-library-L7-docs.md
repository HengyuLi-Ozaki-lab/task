# FP ライブラリ化 Phase L-7: ドキュメンテーション 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-1〜L-6 で完成した fp library + Python wrapper を、新規利用者がゼロから使い始めるためのドキュメントを整備する。`python/fplib/README.md` を本格化、最低限の使い方 + パラメータ sweep の使用例 Jupyter notebook を 1 本同梱する。

**Architecture:** 純粋にドキュメント (`*.md`, `*.ipynb`) のみ。コード変更なし。

**Tech Stack:** Markdown、Jupyter notebook (`.ipynb`)、L-5/L-6 で完成済みの `Fplib` クラス。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 9（L-7）、12 (受け入れ基準)。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/fplib/README.md` | 修正（L-5 で雛形） | full README: install, quickstart, API, examples, troubleshooting |
| `python/fplib/examples/sweep_iter01.ipynb` | 新規 | パラメータスイープ + matplotlib 可視化サンプル（依存: numpy, matplotlib は optional） |
| `python/fplib/examples/sweep_iter01.py` | 新規 | notebook の Python script 版（matplotlib なしで実行可能）|
| `python/fplib/CHANGELOG.md` | 新規 | L-1..L-7 の history を記録 |
| `doc/fp-library.md` | 新規 | task リポジトリ全体ドキュメント側へのエントリポイント（fplib への link） |

**Notebook の「最小依存」方針:** `numpy`, `matplotlib` が無くても `sweep_iter01.py` 単体で完走できるよう、可視化部分は notebook のみに置く。

---

## Task 1: ブランチ作成 + 状態確認

- [ ] **Step 1: ブランチ**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin develop
git checkout -b feature/fp-library-L7-docs origin/develop
```

- [ ] **Step 2: 全 4 層テスト + 既存回帰が PASS**

Run:
```bash
cd /home/k-yoshimi/program/task/fp && make libs_pic && make libfpapi.so 2>&1 | tail -3
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh 2>&1 | tail -10
```
Expected: 全 15 ケース PASS。

---

## Task 2: `python/fplib/README.md` を本格化

**Files:**
- Modify: `python/fplib/README.md`

L-5 で作った雛形を以下の章立てに置き換え:

- [ ] **Step 1: README 全体置換**

`python/fplib/README.md` を以下に置き換え:

````markdown
# fplib — Python wrapper for TASK/FP

In-process Python wrapper for the TASK/FP Fokker-Planck solver via
`ctypes` against `fp/libfpapi.so` (Phase L: library-ization of `fp/`).

## Status

- Layer 1 equivalence test: PASS for `fp_iter01` baseline (tol 1e-10).
- Layer 2 C ABI: PASS (`fp/tests/c_abi/test_abi_full`).
- Layer 3 Python wrapper: PASS (13 unittest cases).
- Layer 4 sweep smoke: PASS (3x3 grid).

The graphics subsystem (`fpgout, fpgsub, fpcont, fpfout`) and `fpmenu`
are intentionally excluded from `libfpapi.so` to keep the surface minimal.

## Installation / build

```bash
# Build dependencies (PIC versions)
cd fp && make libs_pic
# Build the shared library
make libfpapi.so

# Verify symbols
nm -D libfpapi.so | grep ' T fp_'
```

Python uses no third-party packages (stdlib only). Notebook examples
optionally use numpy + matplotlib.

## Quickstart

```python
from fplib import Fplib

with Fplib() as fp:
    fp.set_params(
        MODELG=3, NSMAX=3,
        PA={2: 2.0, 3: 3.0},
        PN={1: 0.8, 2: 0.4, 3: 0.4},
        NRMAX=40, NPMAX=50, NTHMAX=50,
        NTMAX=2, DELT=1.0e-3,
        RMIN=0.4, RMAX=0.8,
    )
    fp.run(ntmax=2)
    state = fp.get_state()

print("TIMEFP =", state.timefp)
print("RNT[NSA=1, NR=1..5] =", state.RNT[0][:5])
```

## API reference

### `Fplib(libpath: str | None = None)`

Construct an in-process FP solver. Calls `fp_init` internally.
If `libpath` is omitted, looks at `$FPLIB_PATH` env var, falling back to
`<repo_root>/fp/libfpapi.so`.

### `Fplib.set_param(name: str, value: float)`

Set one fpcomm parameter. Use `NAME[idx]` (1-origin) for arrays.
Raises `FplibInvalidParamError` if `name` is unknown.

### `Fplib.set_params(**kwargs)`

Bulk setter accepting:

- scalar           → `set_param(NAME, value)`
- `dict {idx: v}`  → `set_param("NAME[idx]", v)` for each entry
- `list/tuple`     → `set_param("NAME[i]", v)` with i = 1, 2, ...

### `Fplib.run(ntmax: int)`

Run NTMAX timesteps via `fp_prep + fp_loop`.
Raises `FplibCalcFailedError` if the solver does not converge.

### `Fplib.get_state() -> FpState`

Snapshot fpcomm into an `FpState` dataclass:

```python
@dataclass
class FpState:
    nrmax: int; nsamax: int; npmax: int; nthmax: int; ntg2: int
    timefp: float
    RNT, RWT, RTT, RJT, RPCT, RPWT: List[List[float]]   # [nsa][nr]
```

### `Fplib.close()`

Calls `fp_finalize`. Implicit on `with`-exit.

## Use cases

### Parameter sweep

```python
import numpy as np
from fplib import Fplib
results = []
for rr in np.linspace(6.0, 7.0, 11):
    for bb in np.linspace(5.0, 5.6, 11):
        with Fplib() as fp:
            fp.set_params(**ITER01_PARAMS, RR=float(rr), BB=float(bb))
            fp.run(ntmax=2)
            results.append((rr, bb, fp.get_state().timefp))
```

See `examples/sweep_iter01.ipynb` for matplotlib visualization.

### Step-wise control

```python
with Fplib() as fp:
    fp.set_params(**base_params)
    for i in range(20):
        fp.run(ntmax=1)
        st = fp.get_state()
        if st.RNT[0][0] < 1e-3:           # density threshold check
            fp.set_param("PABS_WR", 0.5)   # adjust heating mid-run
```

## Registered parameters

The L-3 setter table currently registers ~25 most-used `&FP/` namelist
variables (`fp/fp_param_registry.f90`). Adding a new parameter is a
one-line `CASE` addition. To list them programmatically:

```bash
grep -E '^\s+CASE \(' fp/fp_param_registry.f90
```

If you need a parameter that is not registered yet, open a PR adding the
relevant `CASE` and a unit test in `fp/tests/registry/`.

## Limitations

| Topic | Status |
|---|---|
| MPI | Single-process only (multiprocess via Python `multiprocessing`) |
| Multiple Fplib instances per process | Not supported; fpcomm is a global module |
| Graphics output | Excluded from libfpapi.so (use the standalone `fp` binary) |
| File I/O for fp data files (KNAMFP, etc.) | Bypass via setting empty strings; use `set_param` instead |
| String parameters (KNAMEQ, etc.) | Not yet exposed; coming in a follow-up PR |

## Troubleshooting

- **`OSError: cannot open shared object file`** — `libfpapi.so` not built
  or rpath broken. Set `FPLIB_PATH=/abs/path/to/libfpapi.so` or
  `LD_LIBRARY_PATH=$(pwd)/fp`.
- **`FplibInvalidParamError`** — parameter name typo, or not yet registered
  in `fp_param_registry.f90`.
- **`FplibOverflowError`** — runtime NRMAX exceeds `FP_MAX_NRMAX = 100`.
  Bump in `fp/fp_state.f90` and rebuild.
- **Numerical drift between `Fplib.run()` and the standalone `fp` binary**
  — usually a missing parameter; cross-check with `fp/in/fp.inITER` and
  the registered `CASE` list.

## See also

- Design spec: `docs/superpowers/specs/2026-04-17-tr-library-design.md`
  (TR template; fp follows the same pattern)
- Phase L plans: `docs/superpowers/plans/2026-04-18-fp-library-L*.md`
- Test runner: `test_run/run_tests.sh`
````

---

## Task 3: 使用例 Jupyter notebook

**Files:**
- Create: `python/fplib/examples/sweep_iter01.ipynb`
- Create: `python/fplib/examples/sweep_iter01.py`

- [ ] **Step 1: Python script 版（依存最小）**

`python/fplib/examples/sweep_iter01.py`:

```python
"""Phase L-7 example: tiny RR-BB sweep using ITER fixture.

Run from repo root:
    python3 python/fplib/examples/sweep_iter01.py

Requires: libfpapi.so built (cd fp && make libfpapi.so).
No third-party deps.
"""
import json
import sys
from pathlib import Path

# Allow running from any cwd
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fplib import Fplib                                          # noqa: E402
from fplib.tests.fixtures.base_iter01_params import ITER01_PARAMS  # noqa: E402


def main() -> int:
    rr_grid = [6.0, 6.5, 7.0]
    bb_grid = [5.0, 5.3, 5.6]
    rows = []
    for rr in rr_grid:
        for bb in bb_grid:
            with Fplib() as fp:
                fp.set_params(**ITER01_PARAMS, RR=rr, BB=bb, NTMAX=1)
                fp.run(ntmax=1)
                st = fp.get_state()
                rows.append({
                    "RR": rr, "BB": bb,
                    "TIMEFP": st.timefp,
                    "RNT_axis_NSA1": st.RNT[0][0] if st.RNT else None,
                })
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

実行:
```bash
cd /home/k-yoshimi/program/task
python3 python/fplib/examples/sweep_iter01.py
```
Expected: 9 行の JSON が出力される。

- [ ] **Step 2: Jupyter notebook 版**

`python/fplib/examples/sweep_iter01.ipynb` を作成。
Jupyter UI からのインタラクティブ作成、または `nbformat` Python API でも可。最低限の構造（cell 4 つ）:

1. **Markdown cell:**
   ```markdown
   # FP library: ITER ground sweep example

   Demonstrates a 3x3 sweep over `(RR, BB)` and visualizes the resulting
   `TIMEFP` heat map. Requires `numpy`, `matplotlib`, and `libfpapi.so`.
   ```

2. **Code cell (imports + path setup):**
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path.cwd().parents[1]))   # depending on launch dir

   import numpy as np
   import matplotlib.pyplot as plt
   from fplib import Fplib
   from fplib.tests.fixtures.base_iter01_params import ITER01_PARAMS
   ```

3. **Code cell (sweep):**
   ```python
   rr_grid = np.linspace(6.0, 7.0, 5)
   bb_grid = np.linspace(5.0, 5.6, 5)
   data = np.zeros((len(bb_grid), len(rr_grid)))
   for i, bb in enumerate(bb_grid):
       for j, rr in enumerate(rr_grid):
           with Fplib() as fp:
               fp.set_params(**ITER01_PARAMS, RR=float(rr), BB=float(bb), NTMAX=1)
               fp.run(ntmax=1)
               data[i, j] = fp.get_state().timefp
   ```

4. **Code cell (plot):**
   ```python
   fig, ax = plt.subplots(figsize=(6, 5))
   im = ax.imshow(data, origin="lower",
                  extent=[rr_grid[0], rr_grid[-1], bb_grid[0], bb_grid[-1]],
                  aspect="auto")
   ax.set_xlabel("RR [m]")
   ax.set_ylabel("BB [T]")
   ax.set_title("TIMEFP after 1 timestep, ITER fixture")
   fig.colorbar(im, label="TIMEFP [s]")
   plt.tight_layout()
   ```

ファイル生成は `nbformat` を使った 1-shot Python スクリプトでも可:

```python
# scripts/_build_notebook.py (一時)
import nbformat as nbf
nb = nbf.v4.new_notebook()
nb.cells = [
    nbf.v4.new_markdown_cell("# FP library: ITER ground sweep example\n..."),
    nbf.v4.new_code_cell("import sys\n..."),
    nbf.v4.new_code_cell("rr_grid = ..."),
    nbf.v4.new_code_cell("fig, ax = ..."),
]
nbf.write(nb, "python/fplib/examples/sweep_iter01.ipynb")
```

- [ ] **Step 3: 動作確認（script 版だけ）**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 python/fplib/examples/sweep_iter01.py 2>&1 | head -40
```
Expected: JSON 9 行出力。

Notebook 版は CI では走らせない（依存 numpy/matplotlib があるため）が、ファイルは commit する。

---

## Task 4: CHANGELOG と global doc エントリ

**Files:**
- Create: `python/fplib/CHANGELOG.md`
- Create: `doc/fp-library.md`

- [ ] **Step 1: CHANGELOG**

`python/fplib/CHANGELOG.md`:

```markdown
# fplib changelog

## 2026-04-XX  Phase L-7
- Full README, examples (sweep_iter01.ipynb, sweep_iter01.py)
- This CHANGELOG

## 2026-04-XX  Phase L-6
- Layer 1 equivalence test (`test_equivalence.py`)
- Layer 2 C ABI full lifecycle (`test_abi_full.c`)
- Layer 4 sweep smoke (`test_sweep.py`)
- Wired python/C runners into `test_run/run_tests.sh`

## 2026-04-XX  Phase L-5
- python/fplib/ package: `Fplib` class, `_ffi`, `state`, `errors`
- Layer 3 unit tests (13 cases)

## 2026-04-XX  Phase L-4
- `fp/libfpapi.so` shared-library build
- PIC build of bpsd, lib, mtxp, pl, dp, eq, ob deps
- C link smoke test (`test_abi_link.c`)

## 2026-04-XX  Phase L-3
- `fp_param_registry.f90`: ~25 namelist parameters as setters
- `fp_set_param` C ABI implementation

## 2026-04-XX  Phase L-2
- `fp_state.f90`, `fp_api.f90` (5-fn stub), `fp_api.h`
- C compile-only smoke test

## 2026-04-XX  Phase L-1
- `fp/Makefile`: SRCS split into CORE/GRAPHICS/MENU groups

## 2026-04-XX  Phase L-0
- `fpregress.f90` (env-guarded high-precision dump)
- 3 baseline test cases: `fp_iter01, fp_jt60, fp_dt1`
- `test_run/scripts/extract_fp_metrics.py`
```

- [ ] **Step 2: グローバル doc エントリ**

`doc/fp-library.md`:

```markdown
# TASK/FP Library API

The fp module is callable as an in-process library via:

- C ABI: `fp/fp_api.h` + `fp/libfpapi.so` (5 functions: `fp_init/fp_run/fp_set_param/fp_get_state/fp_finalize`)
- Python wrapper: `python/fplib/` (`from fplib import Fplib`)

See:
- Python README: [`python/fplib/README.md`](../python/fplib/README.md)
- Design spec: [`docs/superpowers/specs/2026-04-17-tr-library-design.md`](../docs/superpowers/specs/2026-04-17-tr-library-design.md) (TR design, fp follows the same pattern)
- Phase plans: [`docs/superpowers/plans/2026-04-18-fp-library-L*.md`](../docs/superpowers/plans/)
- Examples: [`python/fplib/examples/sweep_iter01.ipynb`](../python/fplib/examples/sweep_iter01.ipynb)

The standalone `fp` binary (with graphics + interactive menu) is preserved
unchanged; the library is an additional build target.
```

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/fplib/README.md python/fplib/CHANGELOG.md \
        python/fplib/examples/sweep_iter01.py \
        python/fplib/examples/sweep_iter01.ipynb \
        doc/fp-library.md
git commit -m "docs(fp): add full README, sweep example, CHANGELOG, global doc entry"
```

---

## Task 5: 受け入れ確認 — 全 4 層テスト + 例 script を最終 run

- [ ] **Step 1: 例 script が動く**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 python/fplib/examples/sweep_iter01.py 2>&1 | head -20
```
Expected: JSON 出力 9 行。

- [ ] **Step 2: 全テスト最終 run**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh 2>&1 | tail -15
```
Expected: 15 ケース全 PASS。

---

## 受け入れ基準（Phase L 全体完了）

`tr_library-design.md` 12.2 節を fp に転用:

- [ ] `fp/libfpapi.so` が生成される
- [ ] `python -c "from fplib import Fplib"` 相当が動く
- [ ] Layer 1 等価性テスト 1 ケース以上 PASS（許容誤差 `1e-10` または合意で緩めた値）
- [ ] Layer 2 C ABI 単体テスト PASS
- [ ] Layer 3 Python ラッパテスト PASS（13 cases）
- [ ] Layer 4 網羅計算 smoke test PASS
- [ ] 既存 `fp` バイナリの数値結果が L-0 ベースラインと一致
- [ ] `python/fplib/README.md` に使用例・API リファレンス・トラブルシューティングが記載されている
- [ ] `run_tests.sh` に `fplib_*` カテゴリが統合され、全テスト 15 ケース PASS

## 撤退条件 / フォールバック

| 状況 | 対応 |
|---|---|
| Notebook を CI で走らせろ要件が出る | `nbconvert --execute` を別 GitHub Action で（このスコープ外） |
| `numpy`/`matplotlib` 依存の説明が冗長 | notebook を `optional_examples/` 下に移し、README はスクリプト版のみ参照 |
| L-7 単独で 1 週超 | README + sweep_iter01.py だけ commit、notebook は別 PR |

## 依存

- 上流: L-6 (4 層テスト全 PASS) マージ済み
- 後続: なし（Phase L 完了）
