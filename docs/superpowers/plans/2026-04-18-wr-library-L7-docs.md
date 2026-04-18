# WR ライブラリ化 Phase L-7: ドキュメント (README + Notebook) 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phase L-0 〜 L-6 で完成した `libwrapi.so` + `python/wrlib/` の使い方を、新規ユーザが「README → Notebook → API リファレンス」の順に読めば 30 分で動かせるレベルにドキュメント化する。

**Architecture:** L-5 で雛形だけ置いた `python/wrlib/README.md` を本格化し、Jupyter notebook `python/wrlib/examples/quickstart.ipynb` を新設、`python/wrlib/docs/api.md` で 5 関数 + Wrlib class の API リファレンスを提供。`test_run/README.md` の WR セクションに「ライブラリ版を使う」リンクを足す。`docs/superpowers/specs/` 直下にも完成報告メモ `2026-04-18-wr-library-completion-notes.md` を残す（任意）。

**Tech Stack:** Markdown, Jupyter Notebook (`.ipynb`)、matplotlib（任意、notebook 用）。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` Phase L-7。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/wrlib/README.md` | 修正 | quickstart / インストール / 5 関数 API 一覧 / トラブルシュート |
| `python/wrlib/docs/api.md` | 新規 | 詳細 API リファレンス（C ABI と Python class 両方） |
| `python/wrlib/examples/quickstart.ipynb` | 新規 | 1) 単発実行 2) 配列パラメータ 3) パラメータスイープ 4) 結果プロット |
| `python/wrlib/examples/sweep_example.py` | 新規 | notebook と等価な .py 版（CI で実行可能） |
| `test_run/README.md` | 修正 | 「Python ライブラリ経由でも同じ計算を再現できる」セクション追加 |
| `docs/superpowers/specs/2026-04-18-wr-library-completion-notes.md` | 新規（任意） | Phase L 全体の振り返り（数値結果保存、設計判断の事後評価） |

**方針:**
- README は「いきなり動かしたい人向け」を意識し、5 分で `Wrlib() → set_params → run → get_state` に到達。
- Notebook は Jupyter なしでも `nbconvert --execute` で CI 検証可能にする。matplotlib は ImportError ガードで optional。
- API リファレンスは Sphinx などは導入せず Markdown で十分（規模が小さい）。

---

## Task 1: ブランチ作成

**Files:** なし

- [ ] **Step 1: develop 最新 + ブランチ作成**

Run:
```bash
cd /home/k-yoshimi/program/task
git checkout develop
git pull origin develop
git checkout -b feature/wr-library-L7-docs
```

- [ ] **Step 2: マーカーコミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "chore(wr): start Phase L-7 documentation"
```

---

## Task 2: `python/wrlib/README.md` を本格化

**Files:**
- Modify: `python/wrlib/README.md`

- [ ] **Step 1: README を全面更新**

Overwrite `/home/k-yoshimi/program/task/python/wrlib/README.md` with:

```markdown
# wrlib — Python wrapper for TASK/WR ray-tracing

`wrlib` is the Python interface to TASK/WR (`task/wr/`), the wave ray-tracing
solver. It calls into the shared library `libwrapi.so` via `ctypes`, so each
ray-tracing run happens in-process with no subprocess or file I/O overhead —
ideal for parameter sweeps and optimization loops.

## Installation

The Python package itself has no required dependencies; you do need to build
the Fortran shared library:

```bash
cd /path/to/task/wr
make libwrapi.so          # builds libwrapi.so + PIC dependencies (~5 minutes)
```

Then point Python at the source tree:

```bash
export PYTHONPATH=/path/to/task:$PYTHONPATH
python3 -c "from python.wrlib import Wrlib; print(Wrlib)"
```

If the library is in a non-default location, set `WRLIB_PATH`:

```bash
export WRLIB_PATH=/custom/path/to/libwrapi.so
```

`numpy` is **optional** — if installed, profile/ray arrays come back as
`np.ndarray`; otherwise they come back as Python lists.

## Quick start

```python
from python.wrlib import Wrlib

with Wrlib() as wr:
    wr.set_params(MODELG=2, RR=6.2, RA=2.0, BB=5.3, NSMAX=2)
    wr.set_params(**{"PA[1]": 2.0, "PA[2]": 1.0,
                     "PZ[1]": 1.0, "PZ[2]": -1.0,
                     "PN[1]": 1.0, "PN[2]": 1.0,
                     "PNS[1]":0.1, "PNS[2]":0.1,
                     "PTPR[1]":10.0, "PTPP[1]":10.0,
                     "PTPR[2]":10.0, "PTPP[2]":10.0,
                     "PTS[1]": 0.5, "PTS[2]": 0.5})
    wr.set_params(NRAYMAX=1, NSTPMAX=1000, MDLWRI=101, MDLWRQ=0,
                  SMAX=5.0, DELS=0.05)
    wr.set_params(**{"RFIN[1]": 5.0e3, "RPIN[1]": 8.0, "ZPIN[1]": 0.0,
                     "PHIIN[1]": 0.0, "ANGZIN[1]": 0.0, "ANGPHIN[1]": 30.0,
                     "UUIN[1]": 1.0, "MODEWIN[1]": 1})
    wr.run(0)
    state = wr.get_state()
    print(f"peak power deposition (minor radius): {state.pwrmax_rs:.4g}"
          f" at rho = {state.pos_pwrmax_rs:.4g}")
```

## Parameter sweep example

```python
import numpy as np
from python.wrlib import Wrlib

results = []
for rf in np.linspace(4.0e3, 6.0e3, 5):
    for ang in np.linspace(20.0, 40.0, 5):
        with Wrlib() as wr:
            wr.set_params(MODELG=2, RR=6.2, BB=5.3, NRAYMAX=1, MDLWRI=101)
            wr.set_param("RFIN[1]", rf)
            wr.set_param("ANGPHIN[1]", ang)
            wr.run(0)
            results.append((rf, ang, wr.get_state().pwrmax_rs))
```

See `examples/quickstart.ipynb` for a runnable notebook with plots.

## API summary

| Method | Returns | Purpose |
|---|---|---|
| `Wrlib(lib_path=None)` | `Wrlib` | Construct (does not call `wr_init`) |
| `.open()` / `__enter__` | `Wrlib` | Call `wr_init` (idempotent) |
| `.set_param(name, value)` | None | Set one namelist parameter (`"PN[1]"` for arrays) |
| `.set_params(**kwargs)` | None | Bulk set; keyword args become parameter names |
| `.run(nray_request=0)` | None | Run `wr_setup → wr_exec`. `0` keeps the namelist `NRAYMAX` |
| `.get_state()` | `WrState` | Snapshot of dimensions + scalars + per-ray + profiles |
| `.close()` / `__exit__` | None | Call `wr_finalize` |

`WrState` fields are documented in `docs/api.md`.

## Exceptions

- `WrlibInvalidParam` (`ierr=1`) — unknown parameter name or out-of-range index
- `WrlibNotInitialized` (`ierr=2`) — call before `wr_init` or after `wr_finalize`
- `WrlibCalculationFailed` (`ierr=3`) — `wr_setup` or `wr_exec` reported failure
- `WrlibError` — base class

## Limitations (Phase L scope)

- **One instance per process.** WR uses module-level globals (`wrcomm`); a
  second `Wrlib()` in the same process shares state with the first.
- **No MPI.** Phase L assumes single-process execution.
- **Beam tracing (`mode_beam /= 0`) is not exposed via the C ABI yet** — the
  underlying solver runs, but `wr_get_state` only returns ray-tracing outputs.
- **Input scalars (`RF, RPI, ...`) are not echoed in `wr_get_state`.** Use
  `set_param` round-trip for confirmation; reading them back is planned for
  a future phase.

## Troubleshooting

- `FileNotFoundError: libwrapi.so not found at ...` — Run `make libwrapi.so`
  in `wr/`, or set `WRLIB_PATH`.
- `OSError: ... undefined symbol: gscls_` — `wrgout.f90` (graphics) leaked
  into the PIC build; rebuild with `make clean-pic && make libwrapi.so`.
- `WrlibInvalidParam: invalid parameter: PN[10]` — Index out of range; check
  `NSMAX` and the size of `PN` (8 by default).

## Test suite

```bash
cd /path/to/task
python3 -m unittest discover python.wrlib.tests -v
```

Layers (Phase L-6):
1. `test_equivalence.py` — Python output matches L-0 baselines (1e-10).
2. C ABI tests live under `wr/tests/c_abi/` (run via `make run-all`).
3. `test_ffi.py`, `test_wrlib.py` — ctypes and class-level tests.
4. `test_sweep.py` — 3x3 parameter sweep smoke.
```

- [ ] **Step 2: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrlib/README.md
git commit -m "docs(wrlib): expand README with quickstart, sweep example, API summary"
```

---

## Task 3: API リファレンス `docs/api.md` を作成

**Files:**
- Create: `python/wrlib/docs/api.md`

- [ ] **Step 1: ディレクトリ作成 + Markdown**

Run:
```bash
mkdir -p /home/k-yoshimi/program/task/python/wrlib/docs
```

Create `/home/k-yoshimi/program/task/python/wrlib/docs/api.md`:
```markdown
# wrlib API Reference

## C ABI (declared in `wr/wr_api.h`)

All functions return `int` (0 on success). See `errors.py::raise_for_ierr`
for the Python-side mapping.

| Function | Signature | Notes |
|---|---|---|
| `wr_init` | `int wr_init(void)` | Idempotent; subsequent calls return 0 without re-initializing |
| `wr_run` | `int wr_run(int nray_request)` | If `nray_request > 0`, override `NRAYMAX` |
| `wr_set_param` | `int wr_set_param(const char* name, double value)` | Array form: `"PN[1]"` |
| `wr_get_state` | `int wr_get_state(wr_state_t*)` | Caller allocates `wr_state_t` |
| `wr_finalize` | `int wr_finalize(void)` | Releases all `wr_*` allocations |

### Return codes

| Code | Meaning |
|---|---|
| 0 | OK |
| 1 | Invalid parameter (unknown name or out-of-range index) |
| 2 | Not initialized (called before `wr_init` or after `wr_finalize`) |
| 3 | Calculation failed (`wr_setup`/`wr_exec` reported a non-zero IERR) |

### `wr_state_t` fields

```c
typedef struct {
    int    nraymax, nrsmax, nrlmax;
    double pos_pwrmax_rs, pwrmax_rs, pos_pwrmax_rl, pwrmax_rl;
    int    nstp_end          [WR_MAX_NRAYMAX];
    double pos_pwrmax_rs_nray[WR_MAX_NRAYMAX];
    double pwrmax_rs_nray    [WR_MAX_NRAYMAX];
    double pos_pwrmax_rl_nray[WR_MAX_NRAYMAX];
    double pwrmax_rl_nray    [WR_MAX_NRAYMAX];
    double rays_end          [WR_MAX_NRAYMAX][8]; /* RAYS(0:7, end, j) */
    double pos_nrs           [WR_MAX_NRSMAX];
    double pwr_nrs           [WR_MAX_NRSMAX];
    double pos_nrl           [WR_MAX_NRLMAX];
    double pwr_nrl           [WR_MAX_NRLMAX];
} wr_state_t;
```

Active range: only the first `nraymax/nrsmax/nrlmax` entries are meaningful;
remaining slots are zero-initialized.

## Python `Wrlib` class

```python
class Wrlib:
    def __init__(self, lib_path: Optional[Path] = None)
    def open(self) -> "Wrlib"
    def close(self) -> None
    def __enter__(self) -> "Wrlib"
    def __exit__(self, *args) -> None
    def set_param(self, name: str, value: float) -> None
    def set_params(self, **kwargs) -> None
    def run(self, nray_request: int = 0) -> None
    def get_state(self) -> WrState
```

## `WrState` dataclass

| Field | Type | Description |
|---|---|---|
| `nraymax` | int | Active number of rays |
| `nrsmax` | int | Minor-radius profile bin count |
| `nrlmax` | int | Major-radius profile bin count |
| `pos_pwrmax_rs` / `pwrmax_rs` | float | Global peak deposition (minor radius) |
| `pos_pwrmax_rl` / `pwrmax_rl` | float | Global peak deposition (major radius) |
| `nstp_end[i]` | int | Steps used for ray `i` |
| `pos_pwrmax_*_nray[i]` / `pwrmax_*_nray[i]` | float | Per-ray peak |
| `rays_end[i][k]` | float | `RAYS(k, end, i)` for `k=0..7` (s, R, phi, Z, kR, kphi, kZ, U) |
| `pos_nrs[j]` / `pwr_nrs[j]` | float | Minor-radius bin position / power |
| `pos_nrl[j]` / `pwr_nrl[j]` | float | Major-radius bin position / power |

When numpy is installed, list-typed fields are returned as `np.ndarray`.

## Registered parameters (Phase L-3)

See `wr/wr_param_registry.f90` for the complete `SELECT CASE` table.
Groups:

- **Geometry** (plcomm): `RR, RA, RB, RKAP, RDLT, BB, Q0, QA, RIP`
- **Plasma** (plcomm): `NSMAX`, `PA[i], PZ[i], PN[i], PNS[i], PTPR[i], PTPP[i], PTS[i], PU[i], PUS[i], PZCL[i]`
- **Profile shape**: `PROFN1, PROFN2, PROFT1, PROFT2, PROFU1, PROFU2`, ITB params, edge params
- **Model switches**: `MODELG, MODELQ, MODEL_PROF, MODEL_NPROF, MODEFW, MODEFR, IDEBUG, MODELP[i], MODELV[i], NCMIN[i], NCMAX[i]`
- **WR control**: `NRAYMAX, NSTPMAX, NRSMAX, NRLMAX, MDLWRI/G/P/Q/W, SMAX, DELS, EPSRAY, ...`
- **Per-ray initial conditions**: `RFIN[i], RPIN[i], ZPIN[i], PHIIN[i], RKRIN[i], RNZIN[i], RNPHIIN[i], ANGZIN[i], ANGPHIN[i], UUIN[i], MODEWIN[i]`

To add a new parameter, edit `wr/wr_param_registry.f90` and add a `CASE`
entry; rebuild `libwrapi.so`.
```

- [ ] **Step 2: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrlib/docs/api.md
git commit -m "docs(wrlib): add API reference (C ABI + Python class + parameter table)"
```

---

## Task 4: Notebook `examples/quickstart.ipynb` を作成

**Files:**
- Create: `python/wrlib/examples/quickstart.ipynb`
- Create: `python/wrlib/examples/sweep_example.py`

- [ ] **Step 1: ディレクトリ作成**

Run:
```bash
mkdir -p /home/k-yoshimi/program/task/python/wrlib/examples
```

- [ ] **Step 2: notebook を JSON として作成**

Create `/home/k-yoshimi/program/task/python/wrlib/examples/quickstart.ipynb` with:
```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# wrlib quickstart\n",
    "\n",
    "Run a single ITER LH ray-tracing case, then a small parameter sweep."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import sys\n",
    "from pathlib import Path\n",
    "REPO = Path('..').resolve().parents[1]  # python/wrlib/examples -> repo root\n",
    "sys.path.insert(0, str(REPO))\n",
    "from python.wrlib import Wrlib"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 1. Single ITER LHCD case"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "BASE = {\n",
    "    'MODELG': 2, 'RR': 6.2, 'RA': 2.0, 'BB': 5.3, 'NSMAX': 2,\n",
    "    'PA[1]': 2.0, 'PA[2]': 1.0, 'PZ[1]': 1.0, 'PZ[2]': -1.0,\n",
    "    'PN[1]': 1.0, 'PN[2]': 1.0, 'PNS[1]': 0.1, 'PNS[2]': 0.1,\n",
    "    'PTPR[1]':10.0,'PTPP[1]':10.0,'PTPR[2]':10.0,'PTPP[2]':10.0,\n",
    "    'PTS[1]':0.5, 'PTS[2]':0.5,\n",
    "    'NRAYMAX': 1, 'NSTPMAX': 1000, 'MDLWRI': 101, 'MDLWRQ': 0,\n",
    "    'SMAX': 5.0, 'DELS': 0.05,\n",
    "    'RFIN[1]': 5.0e3, 'RPIN[1]': 8.0, 'ZPIN[1]': 0.0,\n",
    "    'PHIIN[1]': 0.0, 'ANGZIN[1]': 0.0, 'ANGPHIN[1]': 30.0,\n",
    "    'UUIN[1]': 1.0, 'MODEWIN[1]': 1,\n",
    "}\n",
    "with Wrlib() as wr:\n",
    "    wr.set_params(**BASE)\n",
    "    wr.run(0)\n",
    "    st = wr.get_state()\n",
    "    print(f'pos_pwrmax_rs = {st.pos_pwrmax_rs:.4g}')\n",
    "    print(f'pwrmax_rs     = {st.pwrmax_rs:.4g}')\n",
    "    print(f'NRSMAX        = {st.nrsmax}')\n",
    "    print(f'first 5 pos_nrs = {list(st.pos_nrs[:5])}')\n",
    "    print(f'first 5 pwr_nrs = {list(st.pwr_nrs[:5])}')"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 2. Profile plot (matplotlib optional)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "try:\n",
    "    import matplotlib.pyplot as plt\n",
    "    with Wrlib() as wr:\n",
    "        wr.set_params(**BASE)\n",
    "        wr.run(0)\n",
    "        s = wr.get_state()\n",
    "    fig, ax = plt.subplots(figsize=(6,4))\n",
    "    ax.plot(s.pos_nrs[:s.nrsmax], s.pwr_nrs[:s.nrsmax], '-o', label='dP/dV (minor)')\n",
    "    ax.set_xlabel(r'$\\rho$'); ax.set_ylabel('Power deposition'); ax.legend()\n",
    "    plt.show()\n",
    "except ImportError:\n",
    "    print('matplotlib not installed; skip plot')"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 3. 3x3 parameter sweep (RFIN x ANGPHIN)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "results = []\n",
    "for rf in [4.0e3, 5.0e3, 6.0e3]:\n",
    "    for ang in [25.0, 30.0, 35.0]:\n",
    "        with Wrlib() as wr:\n",
    "            wr.set_params(**BASE)\n",
    "            wr.set_param('RFIN[1]', rf)\n",
    "            wr.set_param('ANGPHIN[1]', ang)\n",
    "            wr.run(0)\n",
    "            results.append((rf, ang, wr.get_state().pwrmax_rs))\n",
    "for rf, ang, peak in results:\n",
    "    print(f'RF={rf:>7.1f} GHz, ANG={ang:>5.1f} deg -> peak={peak:.4g}')"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
  "language_info": {"name": "python", "version": "3.10"}
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
```

- [ ] **Step 3: 等価な .py ファイル**

Create `/home/k-yoshimi/program/task/python/wrlib/examples/sweep_example.py`:
```python
#!/usr/bin/env python3
"""Notebook-equivalent sweep example, for CI / non-Jupyter use."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from python.wrlib import Wrlib

BASE = {
    "MODELG": 2, "RR": 6.2, "RA": 2.0, "BB": 5.3, "NSMAX": 2,
    "PA[1]": 2.0, "PA[2]": 1.0, "PZ[1]": 1.0, "PZ[2]": -1.0,
    "PN[1]": 1.0, "PN[2]": 1.0, "PNS[1]": 0.1, "PNS[2]": 0.1,
    "PTPR[1]": 10.0, "PTPP[1]": 10.0, "PTPR[2]": 10.0, "PTPP[2]": 10.0,
    "PTS[1]": 0.5, "PTS[2]": 0.5,
    "NRAYMAX": 1, "NSTPMAX": 1000, "MDLWRI": 101, "MDLWRQ": 0,
    "SMAX": 5.0, "DELS": 0.05,
    "RFIN[1]": 5.0e3, "RPIN[1]": 8.0, "ZPIN[1]": 0.0, "PHIIN[1]": 0.0,
    "ANGZIN[1]": 0.0, "ANGPHIN[1]": 30.0, "UUIN[1]": 1.0, "MODEWIN[1]": 1,
}


def main() -> int:
    for rf in [4.0e3, 5.0e3, 6.0e3]:
        for ang in [25.0, 30.0, 35.0]:
            with Wrlib() as wr:
                wr.set_params(**BASE)
                wr.set_param("RFIN[1]", rf)
                wr.set_param("ANGPHIN[1]", ang)
                wr.run(0)
                st = wr.get_state()
                print(f"RF={rf:>7.1f} GHz  ANG={ang:>5.1f} deg  peak={st.pwrmax_rs:.4g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 動作確認**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 python/wrlib/examples/sweep_example.py 2>&1 | tail -15
```
Expected:
- `libwrapi.so` がある場合: 9 行の結果が表示される。
- 無い場合: `FileNotFoundError: libwrapi.so not found at ...` で失敗（OK）。

Notebook は `jupyter` 未インストールなら手動レビューのみ。あれば:
```bash
jupyter nbconvert --to notebook --execute python/wrlib/examples/quickstart.ipynb --output /tmp/quickstart_out.ipynb 2>&1 | tail -5
```

- [ ] **Step 5: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrlib/examples/quickstart.ipynb python/wrlib/examples/sweep_example.py
git commit -m "docs(wrlib): add quickstart notebook and sweep example script"
```

---

## Task 5: `test_run/README.md` に「ライブラリ版」リンクを追加

**Files:**
- Modify: `test_run/README.md`

- [ ] **Step 1: ライブラリ版セクション追記**

Append to `/home/k-yoshimi/program/task/test_run/README.md`:
```markdown

## WR をライブラリとして使う（Phase L 完了後）

`wr/wr` バイナリ経由ではなく、Python からも同じ計算を実行できる。設計の詳細
は `docs/superpowers/specs/2026-04-17-tr-library-design.md` を参照。

```bash
cd /path/to/task/wr
make libwrapi.so
cd /path/to/task
python3 python/wrlib/examples/sweep_example.py
```

`run_tests.sh wrlib_*` で 4 層テスト（等価性 / C ABI / Python ラッパ / 網羅
計算 smoke）をまとめて走らせられる。詳細は `python/wrlib/README.md`。
```

- [ ] **Step 2: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/README.md
git commit -m "docs(test_run): link to wrlib library usage from README"
```

---

## Task 6: 完成報告メモ（任意）

**Files:**
- Create (optional): `docs/superpowers/specs/2026-04-18-wr-library-completion-notes.md`

実施判断: PR レビュー前に「Phase L 全体の数値結果がベースラインと一致した」「PIC リビルドが各依存で動いた / 動かず案 X にフォールバック」等の事後評価を残しておくと有用。スキップ可。

- [ ] **Step 1: 完成報告 (任意)**

Create `/home/k-yoshimi/program/task/docs/superpowers/specs/2026-04-18-wr-library-completion-notes.md`:
```markdown
# TASK/WR ライブラリ化 (Phase L) 完了メモ

**日付**: <implementation date>
**対象**: `wr/`, `python/wrlib/`, `test_run/baselines/wr_*`

## 数値結果
- L-0 baselines (`wr_iter_lhcd, wr_test001, wr_tst2_ec`): ライブラリ経由出力と相対誤差 <tol> で一致
- 既存 `wr` バイナリの数値結果は不変

## 設計判断の事後評価
- A.1 5 関数 ABI: <評価>
- A.2 C ABI + Python: <評価>
- A.4 Graphics 別モジュール: <評価>
- A.6 PIC リビルド: <案 a/b/c のどれを採用したか>

## 既知の制限
- 一プロセス一インスタンス（グローバル状態）
- beam tracing (`mode_beam /= 0`) は ABI 未対応
- 入力スカラー (`RF, RPI, ...`) は `get_state` 未公開（`set_param` 経由のみ）
- MPI 非対応

## 次フェーズ候補
- beam tracing の C ABI 化
- `wr_get_param` の追加
- 複数インスタンス化（state struct で局所化）
```

- [ ] **Step 2: コミット (任意)**

Run:
```bash
cd /home/k-yoshimi/program/task
git add docs/superpowers/specs/2026-04-18-wr-library-completion-notes.md
git commit -m "docs(wr): add Phase L completion notes"
```

---

## 完了基準

- [ ] `python/wrlib/README.md` がインストール / quickstart / sweep / API summary / トラブルシュートを網羅
- [ ] `python/wrlib/docs/api.md` が C ABI + Python class + パラメータ表を網羅
- [ ] `python/wrlib/examples/quickstart.ipynb` が 4 セル以上で構成され、実行可能
- [ ] `python/wrlib/examples/sweep_example.py` が標準ライブラリのみで動く
- [ ] `test_run/README.md` から `python/wrlib/` への導線がある

## 撤退条件

- notebook の実行で詰まる場合 → README + .py のみで完結させ、notebook はスケルトンのまま commit してアノテーションを足す
- jupyter 環境がない場合 → notebook はファイルとしてコミットしておき、CI でのレンダリング検証は別タスクで

## 依存

- 前提: L-6 完了（4 層テストが PASS する状態）
- 後続: なし（Phase L 完了）
