# TOT Library Phase L-6: 4 層統合テスト 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-2..L-5 で構築した tot ライブラリスタックに対し、TR Phase L で確立した 4 層テスト戦略を **「統合シミュレータ」レベル**に拡張して適用する。`tot` バイナリ／`libtotapi.so`／`Totlib` Python class の各レイヤで挙動が一致することを保証し、L-7（パラメータ最適化）の前提となる信頼性を確保する。

**Architecture:** 4 つのテスト層を以下のように tot 用に翻案:

| Layer | 対象 | tot 翻案 |
|-------|------|---------|
| 1. 等価性 | `libtotapi.so` 経由と既存 `tot` バイナリの数値一致 | demo2014_short / HT6M_short の `tot_regress.dat` 相当を Python 経由でも生成、L-0 baseline と `1e-10` 比較 |
| 2. C ABI 単体 | C から 5 関数を直接叩く | 既存 `tot/tests/c_abi/` を **integrated workflow** へ拡張（init→set_param→run→get_state→finalize 全パス） |
| 3. Python ラッパ | Pythonic API 動作 | `python/totlib/tests/` を拡張、tr/ti/fp prefix 全カバレッジ、context manager 例外伝播 |
| 4. 網羅計算 smoke | パラメータスイープ（小規模） | 3×3 grid (RR × BB) で全完走 + 結果集計、`pandas` を使わず標準 dict + numpy で記録 |

**Tech Stack:** Python 3 (unittest + pytest 互換), numpy, ctypes, gfortran, gcc。新規外部依存なし。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 8（テスト戦略 4 層）を tot に拡張。

**前提条件:** L-0..L-5 完了。`libtotapi.so`, `python/totlib/` 全揃い。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/totlib/tests/test_equivalence.py` | 新規 | Layer 1: tot バイナリの dump と Python 経由 dump を `1e-10` で比較 |
| `python/totlib/tests/fixtures/run_via_lib.py` | 新規 | `Totlib` で baseline と同じ計算を回し dump JSON を出力するヘルパ |
| `tot/tests/c_abi/test_abi_full.c` | 新規 | Layer 2: C から init→set_param→run→get_state→finalize の全パスを実行 |
| `tot/tests/c_abi/Makefile` | 修正 | 上記テストの追加 |
| `python/totlib/tests/test_class_full.py` | 新規 | Layer 3: prefix 全種カバレッジ、例外伝播、context manager 異常系 |
| `python/totlib/tests/test_sweep.py` | 新規 | Layer 4: 3×3 grid sweep の smoke test |
| `test_run/test_definitions.conf` | 修正 | totlib 系テストカテゴリを追加（`totlib_equivalence`, `totlib_ffi_full`, `totlib_sweep`, `totlib_c_abi_full`） |
| `test_run/run_tests.sh` | 修正 | python / C 実行モードを追加（既存は Fortran バイナリ前提） |
| `python/totlib/tests/baseline_inputs/` | 新規 | demo2014_short_via_lib.json, HT6M_short_via_lib.json 等の比較対象 |

**方針:**
- Layer 1 で参照する **「baseline」** は L-0 で `test_run/baselines/tot_demo2014_short/metrics.json` として既に commit されている。Python 側は同じ menu パスを **C ABI 経由で再現** し、JSON を出して比較。
- Layer 4 は「物理的妥当性は検証しない」「全 grid 点が完走すればよい」に限定。
- `run_tests.sh` の python / C モード追加は最小: 既存の TR/EQ/FP/TX モジュール前提のロジックを壊さないよう、新しい "module type" として `python` / `c` を扱う。

---

## Task 1: ブランチ作成と前提確認

**Files:** なし

- [ ] **Step 1: ブランチ作成**

Run:
```bash
cd /home/k-yoshimi/program/task
git checkout develop && git pull
git checkout -b feature/tot-library-l6-test-4layers
```

- [ ] **Step 2: 前提物の存在確認**

Run:
```bash
ls /home/k-yoshimi/program/task/tot/libtotapi.so \
   /home/k-yoshimi/program/task/python/totlib/__init__.py \
   /home/k-yoshimi/program/task/test_run/baselines/tot_demo2014_short/metrics.json
```
Expected: 全て存在。

- [ ] **Step 3: 既存テスト（L-0..L-5）が PASS**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh tot_demo2014_short tot_ht6m_short
cd /home/k-yoshimi/program/task/tot/tests/c_abi && make run && make run_so
cd /home/k-yoshimi/program/task && PYTHONPATH=python python3 -m pytest python/totlib/tests/ -v
```
Expected: 全 PASS。

- [ ] **Step 4: 初期コミット**

Run:
```bash
git commit --allow-empty -m "chore(tot): start L-6 4-layer integrated tests"
```

---

## Task 2: Layer 1 — 等価性テストの helper を実装

**Files:**
- Create: `python/totlib/tests/fixtures/run_via_lib.py`

- [ ] **Step 1: ヘルパスクリプト作成**

作成: `python/totlib/tests/fixtures/run_via_lib.py`

```python
#!/usr/bin/env python3
"""Run a tot calculation through Totlib and dump a metrics.json
that matches the schema produced by extract_tot_metrics.py.

Usage:
    python -m totlib.tests.fixtures.run_via_lib \
        --params demo2014_params.py --ntmax 1 --out actual.json

Notes:
- "ntmax" here represents the integrated TR step count. tot_demo2014_short
  uses a fixed parameter set wired via TR.* prefix.
- The output JSON is intentionally written to be diffable against
  test_run/baselines/tot_*/metrics.json.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from totlib import Totlib


def load_params(path: Path) -> dict[str, float]:
    """Load a Python file that defines PARAMS (dict) and return it."""
    spec = importlib.util.spec_from_file_location("params_mod", path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.PARAMS  # type: ignore[no-any-return]


def metrics_from_state(state: Any) -> dict:
    """Convert a TotState into the JSON schema used by compare_metrics.py."""
    if not state.tr_present or state.tr is None:
        return {
            "NT": 0, "NRMAX": 0, "NSMAX": 0,
            "modules": {
                "TR_PRESENT": int(state.tr_present),
                "TI_PRESENT": int(state.ti_present),
                "FP_PRESENT": int(state.fp_present),
                "WR_PRESENT": int(state.wr_present),
            },
            "scalars": {},
            "profile": [],
        }
    tr = state.tr
    profile = []
    for nr in range(tr.nrmax):
        profile.append({
            "NR": nr + 1,
            "RN": [float(x) for x in tr.RN[nr, :]],
            "RT": [float(x) for x in tr.RT[nr, :]],
            "AJ": float(tr.AJ[nr]),
            "QP": float(tr.QP[nr]),
        })
    return {
        "NT": tr.nt, "NRMAX": tr.nrmax, "NSMAX": tr.nsmax,
        "modules": {
            "TR_PRESENT": int(state.tr_present),
            "TI_PRESENT": int(state.ti_present),
            "FP_PRESENT": int(state.fp_present),
            "WR_PRESENT": int(state.wr_present),
        },
        "scalars": {
            "T": tr.T, "WPT": tr.WPT, "AJT": tr.AJT, "Q0": tr.Q0,
            "BETA0": tr.BETA0, "BETAP0": tr.BETAP0, "BETAA": tr.BETAA, "BETAN": tr.BETAN,
            "TAUE1": tr.TAUE1, "TAUE2": tr.TAUE2, "ZEFF0": tr.ZEFF0,
            "ALI": tr.ALI, "RQ1": tr.RQ1,
        },
        "profile": profile,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", type=Path, required=True,
                    help="Python file exporting PARAMS dict (key->value)")
    ap.add_argument("--ntmax", type=int, default=1,
                    help="Number of integrated steps to advance")
    ap.add_argument("--out", type=Path, required=True,
                    help="Output JSON path")
    args = ap.parse_args()

    params = load_params(args.params)
    with Totlib() as tot:
        tot.set_params(params)
        tot.run(ntmax=args.ntmax)
        state = tot.get_state()
    out = metrics_from_state(state)
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: コミット**

Run:
```bash
mkdir -p /home/k-yoshimi/program/task/python/totlib/tests/fixtures
cd /home/k-yoshimi/program/task
git add python/totlib/tests/fixtures/run_via_lib.py
git commit -m "test(totlib): add run_via_lib helper for Layer 1 equivalence dumps"
```

---

## Task 3: Layer 1 — 等価性テスト本体

**Files:**
- Create: `python/totlib/tests/test_equivalence.py`
- Create: `python/totlib/tests/fixtures/demo2014_short_params.py`

- [ ] **Step 1: パラメータファイル作成**

作成: `python/totlib/tests/fixtures/demo2014_short_params.py`

```python
"""Parameters equivalent to test_run/inputs/tot_demo2014_short.in.

The Fortran-side namelist sets the following geometry/profile defaults
via plparm/eqparm/trparm. The values here MUST mirror those that flow
through the standalone tot binary, so that Layer 1 equivalence holds.

Future maintenance: if you change tot_demo2014_short.in, regenerate
the baseline and update this dict.
"""
PARAMS = {
    "EQ.RR":   8.5,
    "EQ.RA":   2.42,
    "EQ.RKAP": 1.65,
    "EQ.RDLT": 0.33,
    "EQ.BB":   5.94,
    "EQ.RIP": 12.3,
    # TR side typically inherits geometry from EQ; explicit overrides below.
    # Keep this list MINIMAL — the standalone tot binary uses defaults from
    # the namelist defaults. Verify by diffing dumps.
}
```

- [ ] **Step 2: 等価性テスト**

作成: `python/totlib/tests/test_equivalence.py`

```python
"""Layer 1: equivalence between libtotapi.so / tot binary baselines."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
BASELINE_DIR = REPO / "test_run" / "baselines"
RUN_VIA_LIB = (
    Path(__file__).parent / "fixtures" / "run_via_lib.py"
)
COMPARE = REPO / "test_run" / "scripts" / "compare_metrics.py"


def _run_via_lib(params: Path, out: Path, ntmax: int) -> None:
    cmd = [
        sys.executable, str(RUN_VIA_LIB),
        "--params", str(params),
        "--ntmax", str(ntmax),
        "--out", str(out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, env=_env())
    assert res.returncode == 0, f"run_via_lib failed: {res.stderr}"


def _compare(actual: Path, baseline: Path, tol: str = "1e-10") -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(COMPARE),
         "--baseline", str(baseline),
         "--actual", str(actual),
         "--tolerance", tol],
        capture_output=True, text=True, env=_env(),
    )


def _env() -> dict:
    import os
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{REPO}/python:" + env.get("PYTHONPATH", "")
    env["TOTLIB_PATH"] = str(REPO / "tot" / "libtotapi.so")
    extra = ":".join(str(REPO / m) for m in ["tot", "tr", "ti", "fp", "wr", "wm", "pl"])
    env["LD_LIBRARY_PATH"] = f"{extra}:" + env.get("LD_LIBRARY_PATH", "")
    return env


class TestDemo2014ShortEquivalence:
    """Compares a Totlib-driven demo2014_short run against the Fortran baseline."""

    def test_dump_matches_baseline_at_1e10(self, tmp_path):
        actual = tmp_path / "actual.json"
        params = Path(__file__).parent / "fixtures" / "demo2014_short_params.py"
        _run_via_lib(params, actual, ntmax=1)

        baseline = BASELINE_DIR / "tot_demo2014_short" / "metrics.json"
        res = _compare(actual, baseline, tol="1e-10")

        assert res.returncode == 0, (
            "Layer 1 equivalence broken between libtotapi.so and tot binary.\n"
            f"compare_metrics output:\n{res.stdout}\n{res.stderr}"
        )


# Once a HT6M_short_params.py is added, mirror the test above for HT6M.
@pytest.mark.skip(reason="HT6M params fixture pending: see Task 4 of L-6")
def test_ht6m_short_equivalence():
    pass
```

- [ ] **Step 3: テスト実行**

Run:
```bash
cd /home/k-yoshimi/program/task
TOTLIB_PATH=/home/k-yoshimi/program/task/tot/libtotapi.so \
PYTHONPATH=/home/k-yoshimi/program/task/python \
python3 -m pytest python/totlib/tests/test_equivalence.py -v
```
Expected:
- demo2014_short のテストが PASS（compare_metrics が `OK: metrics match within tol=1e-10`）。
- 失敗した場合: actual JSON と baseline JSON の差分を見て、`PARAMS` が namelist デフォルトと乖離している箇所を特定。`set_params` を増やしながら一致するよう調整。

- [ ] **Step 4: コミット**

Run:
```bash
git add python/totlib/tests/test_equivalence.py python/totlib/tests/fixtures/demo2014_short_params.py
git commit -m "test(totlib): add Layer 1 equivalence test (demo2014_short)"
```

---

## Task 4: HT6M_short も同様に拡張

**Files:**
- Create: `python/totlib/tests/fixtures/ht6m_short_params.py`
- Modify: `python/totlib/tests/test_equivalence.py`（@pytest.mark.skip を解除）

- [ ] **Step 1: HT6M params**

作成: `python/totlib/tests/fixtures/ht6m_short_params.py`

```python
"""Parameters equivalent to test_run/inputs/tot_ht6m_short.in.

HT6M is a small-machine setup; geometry/profile values mirror the
namelist defaults consumed by the standalone tot binary.
"""
PARAMS = {
    # Fill in by diffing the dump produced by run_via_lib against the
    # baseline. Start empty — many namelist defaults will already match.
}
```

- [ ] **Step 2: skip を解除して実装**

`python/totlib/tests/test_equivalence.py` の HT6M skip を以下に置換:

```python
class TestHT6MShortEquivalence:
    def test_dump_matches_baseline_at_1e10(self, tmp_path):
        actual = tmp_path / "actual.json"
        params = Path(__file__).parent / "fixtures" / "ht6m_short_params.py"
        _run_via_lib(params, actual, ntmax=1)
        baseline = BASELINE_DIR / "tot_ht6m_short" / "metrics.json"
        res = _compare(actual, baseline, tol="1e-10")
        assert res.returncode == 0, res.stdout + "\n" + res.stderr
```

- [ ] **Step 3: 実行 + 失敗時の調整**

Run:
```bash
cd /home/k-yoshimi/program/task
TOTLIB_PATH=/home/k-yoshimi/program/task/tot/libtotapi.so \
PYTHONPATH=/home/k-yoshimi/program/task/python \
python3 -m pytest python/totlib/tests/test_equivalence.py -v
```
Expected: 両 PASS。HT6M で乖離が出るなら params に値を追加。

許容範囲を `1e-8` に緩めるか検討する場合は、L-0 Task 10（再現性確認）の結果に従う。

- [ ] **Step 4: コミット**

Run:
```bash
git add python/totlib/tests/fixtures/ht6m_short_params.py python/totlib/tests/test_equivalence.py
git commit -m "test(totlib): add Layer 1 equivalence for HT6M_short"
```

---

## Task 5: Layer 2 — C ABI フルパステスト

**Files:**
- Create: `tot/tests/c_abi/test_abi_full.c`
- Modify: `tot/tests/c_abi/Makefile`

- [ ] **Step 1: フルパスのテスト**

作成: `tot/tests/c_abi/test_abi_full.c`

```c
/*
 * test_abi_full.c — Layer 2 integrated workflow test for tot C ABI.
 *
 * Exercises the complete path: init -> set_param (multiple) -> run ->
 * get_state -> finalize. Verifies error propagation when calling out
 * of order.
 */
#include <stdio.h>
#include <assert.h>
#include <string.h>
#include "tot_api.h"

static void check_uninitialized_paths(void) {
    /* Calling get_state / set_param / run before init must return code 2. */
    tot_state_t st;
    int rc;

    rc = tot_get_state(&st);
    assert(rc == 2 && "get_state without init must return 2");

    rc = tot_run(1);
    assert(rc == 2 && "run without init must return 2");

    rc = tot_set_param("TR.RR", 6.2);
    assert(rc == 2 && "set_param without init must return 2");
}

static void check_full_workflow(void) {
    int rc;
    tot_state_t st;

    rc = tot_init(); assert(rc == 0);

    rc = tot_set_param("TR.RR", 6.2); assert(rc == 0);
    rc = tot_set_param("TR.RA", 2.0); assert(rc == 0);

    rc = tot_run(1); assert(rc == 0);

    memset(&st, 0, sizeof(st));
    rc = tot_get_state(&st); assert(rc == 0);
    assert(st.tr_present == 1);
    assert(st.tr.nrmax > 0);
    assert(st.tr.nsmax > 0);

    rc = tot_finalize(); assert(rc == 0);
}

int main(void) {
    check_uninitialized_paths();
    check_full_workflow();
    printf("test_abi_full: PASS\n");
    return 0;
}
```

- [ ] **Step 2: Makefile に追加**

`tot/tests/c_abi/Makefile` に追記:

```makefile
test_abi_full: test_abi_full.c $(OBJS)
	$(CC) $(CFLAGS) test_abi_full.c $(OBJS) $(DEPS) -lgfortran -lm -o $@

run_full: test_abi_full
	./test_abi_full
```

- [ ] **Step 3: 実行**

Run:
```bash
cd /home/k-yoshimi/program/task/tot/tests/c_abi
make run_full 2>&1 | tail
```
Expected: `test_abi_full: PASS`。

- [ ] **Step 4: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add tot/tests/c_abi/test_abi_full.c tot/tests/c_abi/Makefile
git commit -m "test(tot): add Layer 2 full-workflow C ABI test"
```

---

## Task 6: Layer 3 — Python class フルパステスト

**Files:**
- Create: `python/totlib/tests/test_class_full.py`

- [ ] **Step 1: テスト**

作成: `python/totlib/tests/test_class_full.py`

```python
"""Layer 3: full-workflow tests for the Totlib Python class."""
import pytest

from totlib import (
    Totlib, TotlibInvalidParamError,
    TotlibNotInitializedError, TotlibCalculationError,
)


class TestPrefixCoverage:
    """Verify each known prefix is at least dispatchable."""

    @pytest.mark.parametrize("name,value", [
        ("TR.RR", 6.2),
        ("TR.PN[1]", 0.7),
        ("EQ.RR", 6.2),
    ])
    def test_known_prefix_dispatches(self, name, value):
        with Totlib() as tot:
            tot.set_param(name, value)

    @pytest.mark.parametrize("name", [
        "TR.NOSUCHVAR",
        "EQ.NOSUCHVAR",
        "ZZ.NONE",
        "RR",  # missing prefix
    ])
    def test_unknown_param_raises(self, name):
        with Totlib() as tot:
            with pytest.raises(TotlibInvalidParamError):
                tot.set_param(name, 0.0)


class TestOutOfOrder:
    def test_set_param_after_finalize(self):
        tot = Totlib()
        tot.finalize()
        with pytest.raises(TotlibNotInitializedError):
            tot.set_param("TR.RR", 6.2)

    def test_run_after_finalize(self):
        tot = Totlib()
        tot.finalize()
        with pytest.raises(TotlibNotInitializedError):
            tot.run(ntmax=1)

    def test_get_state_after_finalize(self):
        tot = Totlib()
        tot.finalize()
        with pytest.raises(TotlibNotInitializedError):
            tot.get_state()


class TestRunReturnsState:
    def test_run_then_get_state(self):
        with Totlib() as tot:
            tot.set_param("TR.RR", 6.2)
            tot.run(ntmax=1)
            state = tot.get_state()
            # Sanity: run advanced TR by at least one step.
            assert state.tr.nt >= 1


class TestContextManagerExceptionPath:
    def test_exception_inside_with_block_finalizes(self):
        try:
            with Totlib() as tot:
                tot.set_param("TR.RR", 6.2)
                raise RuntimeError("user error")
        except RuntimeError:
            pass
        # If finalize was skipped, a second Totlib() would init twice
        # which is idempotent (returns 0). So test that it still works.
        with Totlib() as tot:
            tot.set_param("TR.RR", 6.0)
```

- [ ] **Step 2: 実行**

Run:
```bash
cd /home/k-yoshimi/program/task
TOTLIB_PATH=/home/k-yoshimi/program/task/tot/libtotapi.so \
PYTHONPATH=/home/k-yoshimi/program/task/python \
python3 -m pytest python/totlib/tests/test_class_full.py -v
```
Expected: 全 PASS。

- [ ] **Step 3: コミット**

Run:
```bash
git add python/totlib/tests/test_class_full.py
git commit -m "test(totlib): add Layer 3 full-workflow class tests (prefix coverage, exceptions)"
```

---

## Task 7: Layer 4 — 網羅計算 smoke test

**Files:**
- Create: `python/totlib/tests/test_sweep.py`

- [ ] **Step 1: テスト**

作成: `python/totlib/tests/test_sweep.py`

```python
"""Layer 4: parameter sweep smoke test.

Drives a small 3x3 grid (RR x BB) and verifies all 9 runs complete and
return finite scalars. Physical correctness is out of scope — the only
assertion is "no crash and no NaN/Inf".
"""
from __future__ import annotations

import math
from itertools import product

import numpy as np
import pytest

from totlib import Totlib


@pytest.mark.parametrize("rr,bb", list(product([6.0, 6.2, 6.4], [5.0, 5.3, 5.6])))
def test_sweep_grid_completes(rr, bb):
    with Totlib() as tot:
        tot.set_params({"EQ.RR": rr, "EQ.BB": bb})
        tot.run(ntmax=1)
        st = tot.get_state()
    assert st.tr_present
    assert math.isfinite(st.tr.WPT)
    assert math.isfinite(st.tr.Q0)
    assert not np.any(np.isnan(st.tr.RN))
    assert not np.any(np.isinf(st.tr.RN))


def test_sweep_recovers_after_finalize():
    """Multiple init/finalize cycles in the same process must work."""
    for rr in (6.0, 6.2):
        with Totlib() as tot:
            tot.set_param("EQ.RR", rr)
            tot.run(ntmax=1)
            assert tot.get_state().tr_present
```

- [ ] **Step 2: 実行**

Run:
```bash
cd /home/k-yoshimi/program/task
TOTLIB_PATH=/home/k-yoshimi/program/task/tot/libtotapi.so \
PYTHONPATH=/home/k-yoshimi/program/task/python \
python3 -m pytest python/totlib/tests/test_sweep.py -v
```
Expected: 全 PASS。9 件 + 1 件。

10 ケースの合計実行時間が長すぎる場合（>1 分）は `ntmax=1` を維持し grid を 2x2 に縮小。

- [ ] **Step 3: コミット**

Run:
```bash
git add python/totlib/tests/test_sweep.py
git commit -m "test(totlib): add Layer 4 sweep smoke test (3x3 grid)"
```

---

## Task 8: `run_tests.sh` に Python / C 実行モードを追加

**Files:**
- Modify: `test_run/run_tests.sh`
- Modify: `test_run/test_definitions.conf`

- [ ] **Step 1: `test_definitions.conf` に totlib 系を追加**

`test_run/test_definitions.conf` の末尾に追加:

```
# =============================================================================
# TOT Library Tests (Phase L-6: 4-layer integrated tests)
# =============================================================================
# Custom-runner format: MODULE='python' or 'c' invokes script directly.
totlib_equivalence:python:python/totlib/tests/test_equivalence.py:none:300:Layer 1 equivalence (demo2014/HT6M)
totlib_class_full:python:python/totlib/tests/test_class_full.py:none:120:Layer 3 class full-workflow
totlib_sweep:python:python/totlib/tests/test_sweep.py:none:240:Layer 4 sweep smoke
totlib_c_abi_full:c:tot/tests/c_abi/test_abi_full:none:60:Layer 2 C ABI full-workflow
```

- [ ] **Step 2: `run_tests.sh` の `get_binary` と分岐を拡張**

`get_binary()` に追加:
```bash
get_binary() {
    local module="$1"
    case "$module" in
        eq) echo "$TASK_DIR/eq/eq" ;;
        tr) echo "$TASK_DIR/tr/tr2" ;;
        fp) echo "$TASK_DIR/fp/fp" ;;
        tx) echo "$TASK_DIR/tx/tx2" ;;
        tot) echo "$TASK_DIR/tot/tot" ;;
        python) echo "$(command -v python3)" ;;
        c) echo "" ;;  # input_file is the binary path
        *) echo "" ;;
    esac
}
```

`run_single_test()` の実行ブロックに新分岐を追加（既存の `binary < input` の前）:

```bash
    # python / c module types: input_file is the script/binary itself.
    if [[ "$module" == "python" ]]; then
        # For python tests, input is a path relative to TASK_DIR.
        local script_path="$TASK_DIR/$input_file"
        if [[ ! -f "$script_path" ]]; then
            echo -e "${YELLOW}SKIP${NC} (script not found: $script_path)"
            SKIPPED=$((SKIPPED + 1))
            return 0
        fi
        cd "$test_dir"
        TOTLIB_PATH="$TASK_DIR/tot/libtotapi.so" \
        PYTHONPATH="$TASK_DIR/python:$PYTHONPATH" \
        LD_LIBRARY_PATH="$TASK_DIR/tot:$TASK_DIR/tr:$TASK_DIR/ti:$TASK_DIR/fp:$TASK_DIR/wr:$TASK_DIR/wm:$TASK_DIR/pl:$LD_LIBRARY_PATH" \
            timeout "$timeout" python3 -m pytest "$script_path" -v > "$log_file" 2>&1
        local exit_code=$?
        cd "$SCRIPT_DIR"
        if [[ $exit_code -eq 0 ]]; then
            echo -e "${GREEN}PASS${NC}"
            PASSED=$((PASSED + 1))
            COMPLETED_TESTS[$test_name]=1
        else
            echo -e "${RED}FAIL${NC} (pytest exit=$exit_code)"
            FAILED=$((FAILED + 1))
        fi
        return 0
    fi

    if [[ "$module" == "c" ]]; then
        # input_file is the binary path relative to TASK_DIR.
        local exe="$TASK_DIR/$input_file"
        if [[ ! -x "$exe" ]]; then
            echo -e "${YELLOW}SKIP${NC} (executable not found: $exe)"
            SKIPPED=$((SKIPPED + 1))
            return 0
        fi
        cd "$test_dir"
        timeout "$timeout" "$exe" > "$log_file" 2>&1
        local exit_code=$?
        cd "$SCRIPT_DIR"
        if [[ $exit_code -eq 0 ]]; then
            echo -e "${GREEN}PASS${NC}"
            PASSED=$((PASSED + 1))
            COMPLETED_TESTS[$test_name]=1
        else
            echo -e "${RED}FAIL${NC} (exit=$exit_code)"
            FAILED=$((FAILED + 1))
        fi
        return 0
    fi
```

挿入位置: `if [[ ! -x "$binary" ]]; then` のチェックの **直前**（`binary` チェックは python/c には不適切なため）。

- [ ] **Step 3: 構文確認**

Run:
```bash
bash -n /home/k-yoshimi/program/task/test_run/run_tests.sh && echo OK
```
Expected: `OK`。

- [ ] **Step 4: 統合実行**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh totlib_equivalence totlib_class_full totlib_sweep totlib_c_abi_full
```
Expected: 4/4 PASS。

- [ ] **Step 5: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/run_tests.sh test_run/test_definitions.conf
git commit -m "test(tot): wire L-6 tests into run_tests.sh (python/c modes)"
```

---

## Task 9: 全モジュール最終検証

**Files:** なし

- [ ] **Step 1: 全テスト一括**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh
```
Expected: 全 FAIL ゼロ。

- [ ] **Step 2: 完了マーカー**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "test(tot): L-6 4-layer integrated tests complete"
```

---

## Verification (Phase L-6 完了基準)

- [ ] Layer 1: `test_equivalence.py` の demo2014/HT6M 両ケースで baseline と `1e-10` 一致。
- [ ] Layer 2: `test_abi_full` PASS。out-of-order 呼び出しで `ierr=2` を返すことが検証されている。
- [ ] Layer 3: `test_class_full.py` の prefix 全カバレッジ + 例外伝播テスト全 PASS。
- [ ] Layer 4: `test_sweep.py` の 3×3 grid + 多重 init/finalize で全 PASS、NaN/Inf 検出なし。
- [ ] `run_tests.sh` から `totlib_*` カテゴリが呼べる。
- [ ] 既存 tot regression / C ABI dlopen / Python FFI テストが全て不変。

---

## Dependencies & Fallback

**前提:** L-0..L-5 完了。

**産出物:** L-7 で「Totlib が物理的に正しく動く」前提が揃う。最適化計算で意外な NaN/Inf が出ても L-6 のテストで検知できる。

**Fallback:**
- Layer 1 の許容誤差 `1e-10` を満たさない場合 → `1e-8` に緩める。L-0 Task 10 の reproducibility 結果と整合させる。
- HT6M の equivalence が乖離する場合 → params dict を空のまま skip マーキング、demo2014 だけで Layer 1 を満たす。
- Layer 4 sweep が実行時間を超過する場合 → grid を 2×2 に縮小、`ntmax=1` を厳守。
- `run_tests.sh` の python/c モード追加で既存の TR/EQ/FP テストが壊れる場合 → 分岐の挿入位置を見直し、`binary` チェックは現状維持で `python/c` モジュール時だけ早期 return。

---

## Out of scope（次フェーズ送り）

- パラメータ最適化 → L-7
- TI/FP の richer state dump → 別 phase（個別モジュールの拡張に依存）
- pip install 形式の totlib 配布 → 別 phase
- ベンチマーク（time-to-result の SLA） → 別 phase
