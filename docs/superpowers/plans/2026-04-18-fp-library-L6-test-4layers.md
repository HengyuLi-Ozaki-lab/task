# FP ライブラリ化 Phase L-6: 4 層テスト整備 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-1〜L-5 で揃った fp library と Python ラッパに対し、TR Phase L 設計と同じ **4 層テスト** を完備し、`test_run/run_tests.sh` から 1 コマンドで全層が走るようにする。

**Architecture:** TR Phase L 設計 (`tr_library-design.md` セクション 8) を fp 用に転用:

| Layer | 目的 | 実装場所 | テストランナ |
|---|---|---|---|
| **1. 等価性** | `Fplib().run()` の出力が既存 `fp` バイナリと一致 | `python/fplib/tests/test_equivalence.py` | unittest + `compare_metrics.py` |
| **2. C ABI 単体** | 5 つの C 関数の単独動作 | `fp/tests/c_abi/test_abi_link.c` 拡張 | `make link_check` |
| **3. Python ラッパ** | `Fplib` class の I/F | `python/fplib/tests/test_ffi.py` + `test_fplib_class.py` | unittest |
| **4. 網羅計算 smoke** | 3x3 パラメータグリッドが破綻なく回る | `python/fplib/tests/test_sweep.py` | unittest |

L-5 で Layer 3 は実装済み。L-6 では Layer 1, 2, 4 を実装し、`test_definitions.conf` に 4 種を登録する。

**Tech Stack:** Python 3 (stdlib + L-5 の fplib), C, gcc, gfortran, L-0 で確立した `compare_metrics.py`。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 8.1, 8.2, 8.3, 8.4, 8.5。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/fplib/tests/test_equivalence.py` | 新規 | Layer 1: ITER fixture を `Fplib` で run し、`fp_iter01` baseline と比較 |
| `python/fplib/tests/test_sweep.py` | 新規 | Layer 4: 3x3 (`RR, BB`) グリッドで `Fplib` を 9 回回し全完走 |
| `fp/tests/c_abi/test_abi_full.c` | 新規 | Layer 2 拡張: init→set_param→run→get_state→finalize の完全サイクル |
| `fp/tests/c_abi/Makefile` | 修正 | `test_abi_full` ターゲット追加 |
| `test_run/test_definitions.conf` | 修正 | 新 4 ケース登録: `fplib_equivalence`, `fplib_ffi`, `fplib_class`, `fplib_sweep`, `fplib_c_abi` |
| `test_run/run_tests.sh` | 修正 | "python execution mode" と "C execution mode" のサポート追加 |
| `python/fplib/tests/_helpers.py` | 新規 | `load_metrics_baseline()` 等のテスト共通ヘルパ |

---

## Task 1: ブランチ作成 + L-5 完了確認

- [ ] **Step 1: ブランチ**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin develop
git checkout -b feature/fp-library-L6-test-4layers origin/develop
cd fp && make libs_pic && make libfpapi.so 2>&1 | tail -3
ls -la libfpapi.so
```
Expected: `libfpapi.so` 存在。

- [ ] **Step 2: L-5 のテスト全 PASS**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest discover python/fplib/tests -v
```
Expected: 13 tests PASS。

- [ ] **Step 3: 既存 fp 回帰 3 ケース PASS**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh fp_iter01 fp_jt60 fp_dt1
```

---

## Task 2: テスト共通ヘルパ `_helpers.py`

**Files:**
- Create: `python/fplib/tests/_helpers.py`

L-0 で確立した `compare_metrics.py` を Python 関数として呼べるラッパ + baseline ローダ。

```python
"""Internal helpers for fplib tests."""
import json
import math
from pathlib import Path
from typing import Tuple


REPO_ROOT = Path(__file__).resolve().parents[3]
BASELINES_DIR = REPO_ROOT / "test_run" / "baselines"


def load_baseline(test_name: str) -> dict:
    """Load test_run/baselines/<test_name>/metrics.json (Phase L-0 output)."""
    p = BASELINES_DIR / test_name / "metrics.json"
    if not p.exists():
        raise FileNotFoundError(
            f"baseline not found: {p}. Run L-0 baseline generation first."
        )
    return json.loads(p.read_text())


def _rel_err(a: float, b: float) -> float:
    denom = max(abs(a), abs(b), 1e-300)
    return abs(a - b) / denom


def compare_to_baseline(state, baseline: dict, tol: float = 1e-10) -> Tuple[bool, list]:
    """Compare an FpState (from Fplib.get_state) against a baseline metrics
    dict (as loaded by load_baseline). Returns (ok, errors).

    Profile fields RNT/RWT/RTT/RJT/RPCT/RPWT are compared per (NR, NSA).
    """
    errors = []

    # dimensions
    if state.nrmax  != baseline["NRMAX"]:  errors.append(f"NRMAX mismatch: {state.nrmax} vs {baseline['NRMAX']}")
    if state.nsamax != baseline["NSAMAX"]: errors.append(f"NSAMAX mismatch: {state.nsamax} vs {baseline['NSAMAX']}")
    if state.npmax  != baseline["NPMAX"]:  errors.append(f"NPMAX mismatch: {state.npmax} vs {baseline['NPMAX']}")
    if state.nthmax != baseline["NTHMAX"]: errors.append(f"NTHMAX mismatch: {state.nthmax} vs {baseline['NTHMAX']}")
    if errors:
        return False, errors

    # scalars (TIMEFP)
    base_ts = float(baseline["scalars"]["TIMEFP"])
    if math.isnan(base_ts) or math.isnan(state.timefp):
        errors.append(f"TIMEFP NaN: baseline={base_ts} actual={state.timefp}")
    elif _rel_err(base_ts, state.timefp) > tol:
        errors.append(f"TIMEFP: baseline={base_ts} actual={state.timefp} > tol={tol}")

    # profile rows in baseline are list-of-dict with {NR, NSA, RNT, RWT, ...}
    baseline_by_key = {(r["NR"], r["NSA"]): r for r in baseline["profile"]}
    for nsa_idx in range(state.nsamax):
        for nr_idx in range(state.nrmax):
            key = (nr_idx + 1, nsa_idx + 1)
            br = baseline_by_key.get(key)
            if br is None:
                errors.append(f"missing baseline row at {key}")
                continue
            for field in ("RNT", "RWT", "RTT", "RJT", "RPCT", "RPWT"):
                actual = getattr(state, field)[nsa_idx][nr_idx]
                base_v = float(br[field])
                if _rel_err(base_v, actual) > tol:
                    errors.append(
                        f"{field}[NR={key[0]},NSA={key[1]}]: "
                        f"baseline={base_v!r} actual={actual!r} "
                        f"rel_err={_rel_err(base_v, actual):.3e} > tol={tol:.3e}"
                    )
    return (not errors), errors
```

---

## Task 3: Layer 1 — 等価性テスト

**Files:**
- Create: `python/fplib/tests/test_equivalence.py`

L-0 で確立した `fp_iter01` baseline と、`Fplib(...).run()` の出力を比較する。

- [ ] **Step 1: テスト本体**

```python
"""Phase L-6 Layer 1: equivalence with fp_iter01 baseline."""
import unittest
from pathlib import Path

from fplib import Fplib
from fplib.tests._helpers import load_baseline, compare_to_baseline
from fplib.tests.fixtures.base_iter01_params import ITER01_PARAMS


LIBPATH = Path(__file__).resolve().parents[3] / "fp" / "libfpapi.so"


@unittest.skipUnless(LIBPATH.exists(), f"libfpapi.so not found at {LIBPATH}")
class TestEquivalenceIter01(unittest.TestCase):

    def test_iter01_matches_baseline(self):
        baseline = load_baseline("fp_iter01")
        with Fplib() as fp:
            fp.set_params(**ITER01_PARAMS)
            fp.run(ntmax=ITER01_PARAMS["NTMAX"])
            state = fp.get_state()
        ok, errors = compare_to_baseline(state, baseline, tol=1e-10)
        if not ok:
            head = "\n  ".join(errors[:10])
            self.fail(f"L1 equivalence failed ({len(errors)} errors):\n  {head}")
```

- [ ] **Step 2: 実行**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest python.fplib.tests.test_equivalence -v
```
Expected: 1 test PASS。

差異が出る場合の典型原因と対処:
- ITER fixture の `set_params` が baseline 入力と完全等価でない → fixture を見直し（L-5 で作った `base_iter01_params.py`）
- `fp_set_param` で受けていない変数が baseline には含まれている → L-3 の registry に CASE 追加
- `fp_run` 内の `fp_prep` が namelist 入力と異なる初期化を行っている → 許容誤差 `1e-8` に緩めて Layer 1 PASS、Layer 1 strict は L-7 文書化案件として保留

---

## Task 4: Layer 2 拡張 — C 完全サイクル

**Files:**
- Create: `fp/tests/c_abi/test_abi_full.c`
- Modify: `fp/tests/c_abi/Makefile`

- [ ] **Step 1: 完全サイクル C テスト**

`fp/tests/c_abi/test_abi_full.c`:

```c
/* Phase L-6 Layer 2: full lifecycle of the FP library C ABI.
 *
 * init -> set_param (scalar + array) -> run -> get_state -> finalize.
 * Verifies error code propagation for invalid params and double-finalize.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "fp_api.h"

#define EXPECT(cond, msg) do {            \
    if (!(cond)) {                        \
        fprintf(stderr, "FAIL: %s\n", msg); \
        return 1;                         \
    }                                     \
} while (0)

int main(void) {
    int rc;
    fp_state_t st;

    rc = fp_init();
    EXPECT(rc == FP_OK, "fp_init");

    /* Set a tiny ITER-like configuration. */
    EXPECT(fp_set_param("MODELG", 3.0)  == FP_OK, "set MODELG");
    EXPECT(fp_set_param("NSMAX",  3.0)  == FP_OK, "set NSMAX");
    EXPECT(fp_set_param("NRMAX",  10.0) == FP_OK, "set NRMAX");
    EXPECT(fp_set_param("NPMAX",  20.0) == FP_OK, "set NPMAX");
    EXPECT(fp_set_param("NTHMAX", 20.0) == FP_OK, "set NTHMAX");
    EXPECT(fp_set_param("NTMAX",  1.0)  == FP_OK, "set NTMAX");
    EXPECT(fp_set_param("PN[1]",  0.8)  == FP_OK, "set PN[1]");
    EXPECT(fp_set_param("PN[2]",  0.4)  == FP_OK, "set PN[2]");

    /* Invalid name */
    EXPECT(fp_set_param("NO_SUCH_VAR", 1.0) == FP_ERR_INVALID,
           "unknown param must be INVALID");

    /* Run a single timestep */
    rc = fp_run(1);
    EXPECT(rc == FP_OK, "fp_run(1)");

    /* Get state */
    memset(&st, 0, sizeof(st));
    rc = fp_get_state(&st);
    EXPECT(rc == FP_OK, "fp_get_state");
    EXPECT(st.nrmax  == 10, "state.nrmax echoes set value");
    EXPECT(st.nsamax >= 1,  "state.nsamax populated");

    /* Finalize, then verify run after finalize fails. */
    rc = fp_finalize();
    EXPECT(rc == FP_OK, "fp_finalize");

    rc = fp_run(1);
    EXPECT(rc == FP_ERR_NOT_INIT, "fp_run after finalize must be NOT_INIT");

    printf("L-6 Layer 2 (C ABI full cycle) OK\n");
    return 0;
}
```

- [ ] **Step 2: Makefile に target 追加**

`fp/tests/c_abi/Makefile` の末尾に:

```makefile
test_abi_full: test_abi_full.c $(FP_LIB_DIR)/libfpapi.so $(FP_LIB_DIR)/fp_api.h
	$(CC) $(CFLAGS) -I$(FP_LIB_DIR) test_abi_full.c $(LDFLAGS_FPAPI) -o test_abi_full

.PHONY: full_check
full_check: test_abi_full
	./test_abi_full
```

- [ ] **Step 3: 走らせる**

Run:
```bash
cd /home/k-yoshimi/program/task/fp/tests/c_abi
make full_check 2>&1 | tail -10
```
Expected: `L-6 Layer 2 (C ABI full cycle) OK`。

---

## Task 5: Layer 4 — 網羅計算 smoke test

**Files:**
- Create: `python/fplib/tests/test_sweep.py`

- [ ] **Step 1: テスト本体**

```python
"""Phase L-6 Layer 4: small parameter sweep smoke test.

Confirms that constructing/destructing Fplib in a loop, with different
parameters each time, does not crash or leak. Physical validity is NOT
checked (out of scope per design A.8).
"""
import unittest
from pathlib import Path

from fplib import Fplib
from fplib.tests.fixtures.base_iter01_params import ITER01_PARAMS


LIBPATH = Path(__file__).resolve().parents[3] / "fp" / "libfpapi.so"


@unittest.skipUnless(LIBPATH.exists(), f"libfpapi.so not found at {LIBPATH}")
class TestSweep(unittest.TestCase):

    def test_3x3_grid(self):
        # Tiny 3x3 sweep on (RR, BB), 1 step each. Should complete in <1 min.
        rr_grid = [6.0, 6.5, 7.0]
        bb_grid = [5.0, 5.3, 5.6]
        results = []
        for rr in rr_grid:
            for bb in bb_grid:
                with Fplib() as fp:
                    fp.set_params(**ITER01_PARAMS, RR=rr, BB=bb, NTMAX=1)
                    fp.run(ntmax=1)
                    st = fp.get_state()
                    results.append((rr, bb, st.timefp))
        self.assertEqual(len(results), 9)
        # all timefp values should be > 0 after 1 step
        for rr, bb, ts in results:
            self.assertGreater(ts, 0.0, f"timefp not advanced for RR={rr} BB={bb}")
```

- [ ] **Step 2: 走らせる**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest python.fplib.tests.test_sweep -v
```
Expected: 1 test PASS（時間がかかるかも、最大 5 分）。

タイムアウトする場合: `NTHMAX=20, NPMAX=20, NRMAX=10, NTMAX=1` に縮小（fixture 側で sweep 用パラメータを別途用意）。

---

## Task 6: `run_tests.sh` に Python / C 実行モード追加

**Files:**
- Modify: `test_run/run_tests.sh`
- Modify: `test_run/test_definitions.conf`

`run_tests.sh` は現状 Fortran バイナリ (`get_binary` 関数) 前提。Python と C テストを走らせるための新たなブランチを足す。

- [ ] **Step 1: 新しい "module" 種別を導入**

`test_definitions.conf` の MODULE フィールドに `fplib` (python unittest) と `fpc` (C executable) を加える。`run_tests.sh` の `get_binary` を拡張:

`run_tests.sh` の `get_binary()` を以下に置換:

```bash
get_binary() {
    local module="$1"
    case "$module" in
        eq)    echo "$TASK_DIR/eq/eq" ;;
        tr)    echo "$TASK_DIR/tr/tr2" ;;
        fp)    echo "$TASK_DIR/fp/fp" ;;
        tx)    echo "$TASK_DIR/tx/tx2" ;;
        fplib) echo "python3" ;;          # Python unittest module name in INPUT_FILE
        fpc)   echo "$TASK_DIR/fp/tests/c_abi/$(basename "$INPUT_FILE")" ;;
        *)     echo "" ;;
    esac
}
```

そして `run_single_test` の実行ブロック直前で module 別に呼出方法を分岐:

```bash
    # Run the test
    cd "$test_dir"
    local log_file="$test_dir/output.log"

    case "$module" in
        fplib)
            # Python execution: $input_file is interpreted as `python -m <pkg>` arg.
            "${mod_env[@]}" timeout "$timeout" python3 -m unittest "$input_file" -v \
                > "$log_file" 2>&1
            local exit_code=$?
            ;;
        fpc)
            # C executable: $input_file is the binary basename in fp/tests/c_abi/.
            "${mod_env[@]}" timeout "$timeout" "$TASK_DIR/fp/tests/c_abi/$input_file" \
                > "$log_file" 2>&1
            local exit_code=$?
            ;;
        *)
            # Existing behaviour (Fortran with stdin namelist).
            "${mod_env[@]}" timeout "$timeout" "$binary" < "$full_input_path" > "$log_file" 2>&1
            local exit_code=$?
            ;;
    esac
```

PASS 判定も module 別に: `fplib`/`fpc` は `exit_code == 0` だけで判断（CLOSED マーカーは fp 専用で対象外）。`grep -q "CLOSED"` のブロックを `case` で囲む。

- [ ] **Step 2: `test_definitions.conf` に新規 5 ケースを追加**

```
# =============================================================================
# FP Library Tests (Phase L-6, 4-layer)
# =============================================================================
fplib_equivalence:fplib:python.fplib.tests.test_equivalence:none:300:L1 equivalence vs fp_iter01 baseline
fplib_ffi:fplib:python.fplib.tests.test_ffi:none:60:L3 ctypes _ffi tests
fplib_class:fplib:python.fplib.tests.test_fplib_class:none:60:L3 high-level Fplib class tests
fplib_sweep:fplib:python.fplib.tests.test_sweep:none:600:L4 3x3 parameter sweep smoke
fplib_c_abi:fpc:test_abi_full:none:120:L2 C ABI full lifecycle
```

- [ ] **Step 3: 全 fplib_* テストを走らせる**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh fplib_ffi fplib_class fplib_c_abi fplib_sweep fplib_equivalence 2>&1 | tail -20
```
Expected: 5/5 PASS。

- [ ] **Step 4: 全テスト（既存 + 新規）を一括実行**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh 2>&1 | tail -20
```
Expected: 既存 (eq/tr/tx/fp 計 10 ケース) + 新規 (fplib 5 ケース) = 計 15 ケース全 PASS。

- [ ] **Step 5: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/fplib/tests/_helpers.py \
        python/fplib/tests/test_equivalence.py \
        python/fplib/tests/test_sweep.py \
        fp/tests/c_abi/test_abi_full.c fp/tests/c_abi/Makefile \
        test_run/run_tests.sh test_run/test_definitions.conf
git commit -m "test(fp): add Layer 1/2/4 fplib tests and wire python/C runners"
```

---

## Task 7: README 拡張

- [ ] **Step 1: `test_run/README.md` の FP セクションに 4 層構成を明記**

```markdown
### FP library 4-layer test stack (Phase L-6)

| Layer | Test | Run |
|---|---|---|
| 1 (equivalence) | python/fplib/tests/test_equivalence.py | ./run_tests.sh fplib_equivalence |
| 2 (C ABI)       | fp/tests/c_abi/test_abi_full.c         | ./run_tests.sh fplib_c_abi |
| 3 (Python wrap) | python/fplib/tests/test_ffi.py + test_fplib_class.py | ./run_tests.sh fplib_ffi fplib_class |
| 4 (sweep smoke) | python/fplib/tests/test_sweep.py       | ./run_tests.sh fplib_sweep |

Prerequisites: `cd fp && make libs_pic && make libfpapi.so`
```

- [ ] **Step 2: コミット**

```bash
cd /home/k-yoshimi/program/task
git add test_run/README.md
git commit -m "docs(fp): document 4-layer fplib test stack"
```

---

## 受け入れ基準

- [ ] `./run_tests.sh fplib_ffi fplib_class fplib_c_abi fplib_sweep fplib_equivalence` で 5/5 PASS。
- [ ] `./run_tests.sh` で全 15 ケース PASS（既存 10 + fplib 5）。
- [ ] Layer 1 (`fplib_equivalence`) が `fp_iter01` baseline と `1e-10` 以内で一致する。
- [ ] `fp` バイナリ・`tr2` バイナリの数値結果が L-0/Phase 0 ベースラインと一致（巻き込み事故なし）。

## 撤退条件 / フォールバック

| 状況 | 対応 |
|---|---|
| Layer 1 (`fplib_equivalence`) がどう調整しても `1e-10` 内に収まらない | 許容誤差を `1e-8`、それでもダメなら `1e-6` に緩める。**ただし** baseline 値そのものは触らない |
| `Fplib(...).run()` が baseline と異なる初期化を行う（たとえば `pl_parm` を読まずに defaults だけ） | L-3 の `fp_param_set` で受ける CASE を増やし、ITER fixture の網羅性を高める。最悪、Layer 1 を「TIMEFP のみ比較」に縮退 |
| Layer 4 (`fplib_sweep`) が 10 分超 | grid を 2x2 に縮小、`NTHMAX=NPMAX=10` 等にさらに小型化 |
| `run_tests.sh` の Python 実行ブランチで `unittest` の終了コードが期待と違う | `python -m unittest -v ... 2>&1 | tee log; rc=${PIPESTATUS[0]}` で取得 |
| Layer 2 の `test_abi_full` が double-finalize で SEGV | `g_initialized` フラグだけで保護されている設計を踏まえ、L-2 plan に戻って `fp_finalize_c` の冪等性を確認 |

## 依存

- 上流: L-5 (Python ラッパ) マージ済み、L-4 (`libfpapi.so`) ビルド可能
- 後続: L-7 (ドキュメンテーション) — 4 層テスト整備された状態で sample notebook を書く
