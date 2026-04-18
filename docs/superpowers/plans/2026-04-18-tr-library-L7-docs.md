# Phase L-7: ドキュメント 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-1〜L-6 で実装した libtrapi.so + Python ラッパの使い方を、既存開発者と新規ユーザの両方が読める形でドキュメント化する。

**Architecture:** ドキュメントは 3 つのレイヤに分けて配置する:
1. `python/trlib/README.md` — Python ユーザ向けクイックスタート（インストール / 5 分でやってみる / 5 関数 API リファレンス / よくあるエラー）。
2. `tr/README_libtrapi.md` — Fortran/C 側の責務（`tr_api.h` の使い方、`libtrapi.so` のビルド方法、依存関係）。
3. `python/trlib/examples/` — 実行可能な使用例 3 本（基本ループ、パラメータスイープ、ステップ介入）。

**Tech Stack:** Markdown のみ。例は `Trlib` クラスを使う Python 3 スクリプト（standalone 実行可能）。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` §6.4 (使用例), §9 (L-7 行), §12 (受け入れ基準: 「`python/trlib/README.md` に使用例が記載」)。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/trlib/README.md` | 新規 | Python ユーザ向けクイックスタート + API リファレンス |
| `tr/README_libtrapi.md` | 新規 | C/Fortran 側のビルド・リンク手順、`tr_api.h` の使い方 |
| `python/trlib/examples/01_basic_run.py` | 新規 | 最小実行例（init → set_params → run → get_state → print） |
| `python/trlib/examples/02_param_sweep.py` | 新規 | 設計書 §6.4 パターン 1（網羅計算） |
| `python/trlib/examples/03_step_intervention.py` | 新規 | 設計書 §6.4 パターン 2（DT 動的調整） |
| `docs/superpowers/notes/2026-04-18-phase-l-completion.md` | 新規 | Phase L 全体の完了レポート（受け入れ基準 §12.2 への対応マトリクス） |

**方針:**
- README は **長すぎない**: クイックスタート → 1 ページ API リファレンス → トラブルシュート。詳細設計は spec 文書を参照させる。
- examples は **コピペで動く**。`PYTHONPATH=python python3 examples/XX.py` で実行可能。
- L-7 は **コード変更なし**（example 以外）。本サブで何かバグが出ても L-3〜L-6 に戻して修正することはしない。

---

## Task 1: ブランチと前提

- [ ] **Step 1: L-6 完了確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin develop
git log --oneline origin/develop | grep -i "phase l-6" | head -3
PYTHONPATH=python python3 -m unittest python.trlib.tests.test_smoke -v 2>&1 | tail -5
ls test_run/test_definitions.conf
grep "trlib_" test_run/test_definitions.conf
```
Expected: L-6 merge 済み、smoke OK、4 つの trlib_* エントリが定義済み。

- [ ] **Step 2: ブランチ作成**

Run:
```bash
git checkout -b feature/tr-library-phase-l7 origin/develop
```

---

## Task 2: `python/trlib/README.md`

**Files:**
- Create: `python/trlib/README.md`

- [ ] **Step 1: README 本体**

作成: `python/trlib/README.md`

````markdown
# trlib — Python wrapper for TASK/TR

`trlib` is a thin `ctypes`-based wrapper around the in-process TASK/TR
shared library `libtrapi.so`. It lets you drive transport simulations
from Python without invoking the `tr2` binary or going through files.

## Status

- Single process / single instance (TR has global state).
- Fortran 90 graphics is excluded; this is a numerical-only API.
- Numerical equivalence with the existing `tr2` binary is verified to
  `1e-10` (Layer 1 in `tests/test_equivalence.py`).

## Install

```bash
# 1. build libtrapi.so (one-off)
cd /path/to/task/tr
make libtrapi.so

# 2. add the wrapper to PYTHONPATH
export PYTHONPATH=/path/to/task/python:$PYTHONPATH

# 3. (optional) override library path
export TRLIB_PATH=/path/to/task/tr/libtrapi.so
```

The wrapper has **no third-party dependencies** (Python 3.8+ stdlib only).

## Quick start

```python
from trlib import Trlib

with Trlib() as tr:
    tr.set_params(RR=8.5, BB=5.3, DT=0.1, NTSTEP=10)
    tr.set_param("PN[1]", 1.0)
    tr.set_param("PN[2]", 1.0)
    tr.run(ntmax=100)
    state = tr.get_state()
    print(f"T={state.scalars['T']:.3f}  WPT={state.scalars['WPT']:.3f}")
```

More worked examples in `examples/`.

## API reference

### `Trlib(lib_path: str | None = None)`
Context-manager handle. Calls `tr_init` on entry, `tr_finalize` on exit.

### `set_param(name: str, value: float) -> None`
Set one namelist parameter. Use `"PN[1]"` for array elements (1-origin).

### `set_params(**kwargs) -> None`
Bulk-set scalars. Array elements must use `set_param("PN[1]", ...)`.

### `run(ntmax: int) -> None`
Advance the simulation by `ntmax` time steps using current `DT` /
`NTSTEP`. Cumulative across calls.

### `get_state() -> TrState`
Snapshot current TRCOMM scalars and profile arrays. See `state.py`.

### `close() -> None`
Idempotent. The context manager calls this for you.

## Exceptions

| Class | When |
|---|---|
| `TrlibParamError` | `set_param` saw an unknown name or invalid index |
| `TrlibStateError` | API call before `tr_init` or after `close` |
| `TrlibRunError`   | `tr_run` or `tr_get_state` returned ierr=3 |
| `TrlibInitError`  | `tr_init` failed |
| `TrlibError`      | Base class / generic failure |

## Troubleshooting

- **`FileNotFoundError: libtrapi.so not found`** — run `make -C tr libtrapi.so`,
  or set `TRLIB_PATH`.
- **`OSError: ... cannot open shared object file`** — `LD_LIBRARY_PATH`
  may need to include `tr/`. The wrapper sets `rpath`, but a relocated
  `libtrapi.so` will need help.
- **Numbers don't match `tr2`** — see Layer 1 test
  (`tests/test_equivalence.py`) and bump `--tolerance` only if you have
  a strong reason. The default `1e-10` matches Phase 0 baselines.

## Design

See `docs/superpowers/specs/2026-04-17-tr-library-design.md` (Phase L).
````

---

## Task 3: `tr/README_libtrapi.md`

**Files:**
- Create: `tr/README_libtrapi.md`

- [ ] **Step 1: ビルド・リンクメモ**

作成: `tr/README_libtrapi.md`

````markdown
# libtrapi.so — building & calling from C

The shared library exposes 5 C entry points (see `tr_api.h`). It links
the same Fortran calculation code as `tr2` but **excludes graphics and
the interactive menu**.

## Build

```bash
cd tr
make libtrapi.so
# produces ./libtrapi.so and several lib*_pic.a in dependent dirs
```

The build re-compiles the dependent libraries (`eq`, `pl`, `lib`,
`bpsd`) with `-fPIC` into `*_pic.a`. The existing non-PIC `*.a` and
`tr2` build are unchanged.

## Use from C

```c
#include "tr_api.h"

int main(void) {
    if (tr_init() != 0) return 1;
    tr_set_param("RR", 8.5);
    tr_run(100);
    tr_state_t s;
    tr_get_state(&s);
    printf("T=%g WPT=%g\n", s.T, s.WPT);
    tr_finalize();
    return 0;
}
```

Compile:
```bash
gcc my_driver.c -I/path/to/task/tr -L/path/to/task/tr -ltrapi -Wl,-rpath,/path/to/task/tr -o my_driver
```

## Symbol surface

```bash
nm -D libtrapi.so | grep " T tr_"
```
should list exactly: `tr_init`, `tr_run`, `tr_set_param`,
`tr_get_state`, `tr_finalize`.

## Limitations

- One instance per process (TR globals).
- No MPI / no OpenMP API.
- String parameters (e.g. `KNAMEQ`) are not yet wired; track in design
  spec §4.3.
````

---

## Task 4: 使用例 3 本

**Files:**
- Create: `python/trlib/examples/01_basic_run.py`
- Create: `python/trlib/examples/02_param_sweep.py`
- Create: `python/trlib/examples/03_step_intervention.py`

- [ ] **Step 1: 01_basic_run.py**

作成: `python/trlib/examples/01_basic_run.py`

```python
"""Minimal run: init, set a few params, run 50 steps, print key scalars."""
from trlib import Trlib


def main() -> None:
    with Trlib() as tr:
        # ITER-like geometry (truncated; see fixtures for full set)
        tr.set_params(RR=8.5, RA=2.0, RKAP=1.7, BB=5.3,
                      NSMAX=2, DT=0.1, NTSTEP=10, NTMAX=50)
        tr.set_param("PN[1]", 1.0)
        tr.set_param("PN[2]", 1.0)
        tr.set_param("PT[1]", 1.5)
        tr.set_param("PT[2]", 1.5)

        tr.run(ntmax=50)
        state = tr.get_state()

    print(f"T   = {state.scalars['T']:.4g}")
    print(f"WPT = {state.scalars['WPT']:.4g}")
    print(f"Q0  = {state.scalars['Q0']:.4g}")
    print(f"NRMAX={state.nrmax} NSMAX={state.nsmax}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 02_param_sweep.py**

作成: `python/trlib/examples/02_param_sweep.py`

```python
"""3x3 RR/BB sweep, collecting WPT for each cell.

Mirrors design spec §6.4 pattern 1.
"""
from trlib import Trlib


def main() -> None:
    rr_vals = [7.5, 8.0, 8.5]
    bb_vals = [4.5, 5.0, 5.5]
    print(f"{'RR':>6} {'BB':>6} {'WPT':>10}")
    for rr in rr_vals:
        for bb in bb_vals:
            with Trlib() as tr:
                tr.set_params(RR=rr, BB=bb, RA=2.0, RKAP=1.7,
                              NSMAX=2, DT=0.1, NTSTEP=10, NTMAX=20)
                tr.set_param("PN[1]", 1.0); tr.set_param("PN[2]", 1.0)
                tr.set_param("PT[1]", 1.5); tr.set_param("PT[2]", 1.5)
                tr.run(20)
                wpt = tr.get_state().scalars["WPT"]
            print(f"{rr:6.2f} {bb:6.2f} {wpt:10.4g}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 03_step_intervention.py**

作成: `python/trlib/examples/03_step_intervention.py`

```python
"""Step-by-step run, halving DT once Q0 drops below a threshold.

Mirrors design spec §6.4 pattern 2.
"""
from trlib import Trlib


def main() -> None:
    dt = 0.1
    with Trlib() as tr:
        tr.set_params(RR=8.5, RA=2.0, RKAP=1.7, BB=5.3,
                      NSMAX=2, DT=dt, NTSTEP=1)
        tr.set_param("PN[1]", 1.0); tr.set_param("PN[2]", 1.0)
        tr.set_param("PT[1]", 1.5); tr.set_param("PT[2]", 1.5)

        for step in range(20):
            tr.run(ntmax=1)
            s = tr.get_state()
            print(f"step={step:3d} T={s.scalars['T']:.3g} "
                  f"Q0={s.scalars['Q0']:.3g} DT={dt:.4g}")
            if s.scalars["Q0"] < 1.0 and dt > 1e-3:
                dt *= 0.5
                tr.set_param("DT", dt)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 動作確認**

Run:
```bash
cd /home/k-yoshimi/program/task
PYTHONPATH=python python3 python/trlib/examples/01_basic_run.py
PYTHONPATH=python python3 python/trlib/examples/02_param_sweep.py
PYTHONPATH=python python3 python/trlib/examples/03_step_intervention.py
```
Expected: それぞれ完走して数値が表示される。失敗した場合は L-5/L-6 のテストが取り損ねた問題なので、example を修正するのではなく該当 Phase に戻る。

---

## Task 5: Phase L 完了レポート

**Files:**
- Create: `docs/superpowers/notes/2026-04-18-phase-l-completion.md`

- [ ] **Step 1: 受け入れ基準対応マトリクス**

作成: `docs/superpowers/notes/2026-04-18-phase-l-completion.md`

```markdown
# Phase L completion report

設計書 §12.2 受け入れ基準への対応:

| 受け入れ基準 | サブ Phase | 確認方法 | 状態 |
|---|---|---|---|
| libtrapi.so 生成 | L-4 | `ls tr/libtrapi.so && file tr/libtrapi.so` | OK / FAIL |
| `import trlib` 可能 | L-5 | `python3 -c "from trlib import Trlib"` | OK / FAIL |
| Layer 1 等価性 3 ケース PASS | L-6 | `run_tests.sh trlib_equivalence` | OK / FAIL |
| Layer 2 C ABI PASS | L-6 | `run_tests.sh trlib_c_abi` | OK / FAIL |
| Layer 3 Python wrapper PASS | L-6 | `run_tests.sh trlib_ffi` | OK / FAIL |
| Layer 4 sweep smoke PASS | L-6 | `run_tests.sh trlib_sweep` | OK / FAIL |
| tr2 数値が Phase 0 と一致 | L-0〜L-6 全節 | `run_tests.sh tr_iter01 tr_m0904 tr_tst2` | OK / FAIL |
| `python/trlib/README.md` に使用例 | L-7 | 目視 | OK / FAIL |
| `run_tests.sh` に trlib_* 統合 | L-6 | grep `trlib_` `test_definitions.conf` | OK / FAIL |

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

実行時に各行の状態を埋める（コミット時点では `OK / FAIL` のままで OK）。

---

## Task 6: コミットと PR

- [ ] **Step 1: コミット**

Run:
```bash
git add python/trlib/README.md tr/README_libtrapi.md \
        python/trlib/examples/ \
        docs/superpowers/notes/2026-04-18-phase-l-completion.md
git commit -m "docs(trlib): user guide, build notes, examples, Phase L completion report"
```

- [ ] **Step 2: PR**

Run:
```bash
gh pr create --base develop --title "docs(trlib): Phase L-7 user-facing documentation" \
  --body "Phase L-7: README、ビルドメモ、3 本の使用例、完了レポート。設計書 §12.2 受け入れ基準対応表を含む。"
```

---

## 撤退条件 / フォールバック

| 状況 | 対応 |
|---|---|
| examples 実行中に発覚した不具合 | 該当 Phase (L-3〜L-6) に戻ってバグ修正 PR を立てる。L-7 自体は中止しない |
| README が冗長との review 指摘 | クイックスタートだけ残し、API リファレンスは spec へのリンクに置換 |

## 受け入れ基準

- [ ] `python/trlib/README.md` が存在し、クイックスタート + 5 関数 API リファレンスを含む
- [ ] `tr/README_libtrapi.md` が存在し、C からの呼び出し例とビルド手順を含む
- [ ] `python/trlib/examples/` に実行可能な 3 本のスクリプト
- [ ] 完了レポートの受け入れ基準マトリクスがすべて OK
- [ ] PR が develop に merge 可能

## 依存

- L-6 完了
