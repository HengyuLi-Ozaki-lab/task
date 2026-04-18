# WRX ライブラリ化 Phase L-6: 4 層テスト 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-0 で作った回帰テスト基盤に加え、L-2/L-3/L-5 で出来た C ABI と Python ラッパに対する 4 層のテスト（等価性 / C ABI / Python ラッパ / 網羅計算 smoke）を整備し、`run_tests.sh` から走らせられる形にする。

**Architecture:** sister wr Phase L-6 と同じ 4 層構成を WRX にミラーリング。すべての C/Python テストは **L-2 で確定した ABI**（`wrx_set_param(const char*, double)` と `wrx_get_state(wrx_state_t*)`）に従う — 旧版に存在した name+ptr+size 形式や `wrx_get_state("pwr_profile", buf, 101)` 形式の呼び出しは廃止済み。

| Layer | 目的 | 実装 | 場所 |
|---|---|---|---|
| 1. 等価性 | `WrxLib` 経由の出力が既存 `wrx/wr` バイナリの dump (L-0 baseline) と相対誤差 1e-10 で一致 | `python/wrxlib/tests/test_equivalence.py` | Python unittest |
| 2. C ABI 単体 | 5 つの C 関数が個別に正しく動作 | L-2/L-3/L-4 で追加した `wrx/tests/c_abi/test_*` の整理 + 新規 invalid input テスト | C |
| 3. Python ラッパ | `WrxLib` class が Pythonic に動く | L-5 の `test_ffi.py` / `test_wrxlib.py` を強化（既存資産再利用） | Python unittest |
| 4. 網羅計算 smoke | 小規模パラメータスイープで完走 | `python/wrxlib/tests/test_sweep.py` | Python unittest |

`test_run/run_tests.sh` に「Python 実行モード」を追加し、`wrxlib_*` カテゴリとして 4 層テストを走らせる。

**Tech Stack:** Python 3 (`unittest`), C (既存)、Bash。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 8 と Phase L-6（wr 版を wrx 用に翻案）。

---

## 既存資産

| L-x | 既存ファイル | 役割 |
|---|---|---|
| L-0 | `test_run/baselines/wrx_*/metrics.json` | Layer 1 の参照値 |
| L-0 | `test_run/inputs/wrx_*.in` | namelist セット（Python から再現する元） |
| L-0 | `test_run/scripts/extract_wrx_metrics.py` | 手動 dump → JSON 変換 |
| L-2 | `wrx/tests/c_abi/test_abi_stub.c` | Layer 2 (init/finalize) |
| L-3 | `wrx/tests/c_abi/test_param_set.c` | Layer 2 (set_param 正常/異常) |
| L-4 | `wrx/tests/c_abi/test_abi_so.c` | Layer 2 (dlopen + run cycle) |
| L-5 | `python/wrxlib/tests/test_ffi.py`, `test_wrxlib.py` | Layer 3 |

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/wrxlib/tests/test_equivalence.py` | 新規 | Layer 1: `wrx_iter01, wrx_jt60, wrx_demo` の baseline JSON と Python ラッパ出力を比較 |
| `python/wrxlib/tests/fixtures/wrx_iter01_params.py` | 新規 | namelist → Python dict 変換（手動・WRX namelist パーサ依存なし） |
| `python/wrxlib/tests/fixtures/wrx_jt60_params.py` | 新規 | 同上 |
| `python/wrxlib/tests/fixtures/wrx_demo_params.py` | 新規 | 同上 |
| `python/wrxlib/tests/test_sweep.py` | 新規 | Layer 4: 3x3 グリッドの (RFIN, ANGPIN) スイープ smoke |
| `wrx/tests/c_abi/test_abi_negative.c` | 新規（任意） | Layer 2: `wrx_run` を `wrx_init` 抜きで呼ぶなどの異常系を追加 |
| `test_run/test_definitions.conf` | 修正 | `wrxlib_equivalence`, `wrxlib_ffi`, `wrxlib_wrxlib`, `wrxlib_sweep`, `wrxlib_c_abi` の 5 ケース追加 |
| `test_run/run_tests.sh` | 修正 | Python 実行モード（`module=wrxlib`）と C 実行モード（`module=wrxlib_c`）の対応 |

**方針:**
- namelist パーサは標準ライブラリでは扱いづらいため、L-6 では「fixture を Python dict として手書き」する（sister wr L-6 と同じ）。`f90nml` 等の追加依存は導入しない。
- Layer 1 の許容誤差は L-0 と同じ `1e-10`（dump 経路は同じ Fortran コードを通るので bit-exact 一致を期待）。乖離が見つかれば `1e-8` に緩める。

---

## Task 1: ブランチ作成と前提確認

**Files:** なし

- [ ] **Step 1: develop 最新 + ブランチ作成**

Run:
```bash
cd /home/k-yoshimi/program/task
git checkout develop
git pull origin develop
git checkout -b feature/wrx-library-L6-tests
```

- [ ] **Step 2: L-5 までの成果物が揃っていることを確認**

Run:
```bash
ls -la /home/k-yoshimi/program/task/wrx/libwrxapi.so 2>&1
ls /home/k-yoshimi/program/task/python/wrxlib/wrxlib.py
ls /home/k-yoshimi/program/task/test_run/baselines/wrx_iter01/metrics.json
```
Expected: 全て存在する。

- [ ] **Step 3: マーカーコミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "chore(wrx): start Phase L-6 4-layer tests"
```

---

## Task 2: namelist → Python dict fixture を作成

**Files:**
- Create: `python/wrxlib/tests/fixtures/__init__.py`
- Create: `python/wrxlib/tests/fixtures/wrx_iter01_params.py`
- Create: `python/wrxlib/tests/fixtures/wrx_jt60_params.py`
- Create: `python/wrxlib/tests/fixtures/wrx_demo_params.py`

各 fixture は `PARAMS: dict[str, float]` を export する。`PN[1]` 形式で配列も含める。L-0 の `test_run/inputs/wrx_*.in` namelist と一致させる（NRAYMAX, NSTPMAX 等を含む）。

- [ ] **Step 1: ディレクトリと __init__**

Run:
```bash
mkdir -p /home/k-yoshimi/program/task/python/wrxlib/tests/fixtures
touch /home/k-yoshimi/program/task/python/wrxlib/tests/fixtures/__init__.py
```

- [ ] **Step 2: `wrx_iter01_params.py` 作成**

Create `/home/k-yoshimi/program/task/python/wrxlib/tests/fixtures/wrx_iter01_params.py`:
```python
"""WRX ITER ECCD case (mirror of test_run/inputs/wrx_iter01.in).

Only scalars and array elements registered in wrx_param_registry.f90 (L-3)
are listed here. Add new keys when the registry grows.
"""
PARAMS = {
    "MODELG":   2,
    "MODELN":   0,    "MODELQ": 0,
    "RR":       6.2,  "RA":  2.0,  "RB":  2.2,
    "BB":       5.3,
    "Q0":       1.0,  "QA":  3.5,
    "PROFJ":    1.0,  "PROFN1": 2.0, "PROFN2": 1.0,
    "PROFT1":   2.0,  "PROFT2": 1.0,
    "pne_threshold": 1.0e-6,
    "NSMAX":    2,
    "PA[1]":    2.0,        "PA[2]": 5.4462e-4,
    "PZ[1]":    1.0,        "PZ[2]": -1.0,
    "PN[1]":    1.0,        "PN[2]":  1.0,
    "PNS[1]":   0.05,       "PNS[2]": 0.05,
    "PTPR[1]": 10.0,        "PTPR[2]":10.0,
    "PTPP[1]": 10.0,        "PTPP[2]":10.0,
    "PTS[1]":   0.5,        "PTS[2]":  0.5,
    "MODELP[1]": 206, "MODELP[2]": 206,
    "MODELV[1]": 3,   "MODELV[2]": 0,
    "NCMIN[1]": -3,   "NCMIN[2]": -3,
    "NCMAX[1]":  3,   "NCMAX[2]":  3,
    "MDLWRI":   2,    "MDLWRQ":   1,
    "MDLWRG":   1,    "MDLWRP":   1,
    "MDLWRW":   0,
    "SMAX":     2.0,  "DELS":     1e-3,
    "NSTPMAX":  2000, "NRAYMAX":  4,
    "RFIN[1]":  170.0e3, "RFIN[2]": 170.0e3, "RFIN[3]": 170.0e3, "RFIN[4]": 170.0e3,
    "RPIN[1]":  8.0,     "RPIN[2]":  8.0,     "RPIN[3]":  8.0,     "RPIN[4]":  8.0,
    "ZPIN[1]":  0.0,     "ZPIN[2]":  0.0,     "ZPIN[3]":  0.0,     "ZPIN[4]":  0.0,
    "PHIIN[1]": 0.0,     "PHIIN[2]": 0.0,     "PHIIN[3]": 0.0,     "PHIIN[4]": 0.0,
    "ANGPIN[1]": 0.0,    "ANGPIN[2]": 5.0,    "ANGPIN[3]":10.0,    "ANGPIN[4]":15.0,
    "ANGTIN[1]":10.0,    "ANGTIN[2]":20.0,    "ANGTIN[3]":30.0,    "ANGTIN[4]":40.0,
    "UUIN[1]":   1.0,    "UUIN[2]":   1.0,    "UUIN[3]":   1.0,    "UUIN[4]":   1.0,
    "MODEWIN[1]":1,      "MODEWIN[2]":1,      "MODEWIN[3]":1,      "MODEWIN[4]":1,
}
```

- [ ] **Step 3: `wrx_jt60_params.py` 作成（test_run/inputs/wrx_jt60.in と同内容）**

Create `/home/k-yoshimi/program/task/python/wrxlib/tests/fixtures/wrx_jt60_params.py`:
```python
"""WRX JT-60U ECCD case (mirror of test_run/inputs/wrx_jt60.in)."""
PARAMS = {
    "MODELG":   2,
    "MODELN":   0,   "MODELQ": 0,
    "RR":       3.4, "RA":  1.0, "RB":  1.1,
    "BB":       3.5,
    "Q0":       1.2, "QA":  4.0,
    "PROFJ":    1.0, "PROFN1": 2.0, "PROFN2": 1.0,
    "PROFT1":   2.0, "PROFT2": 1.0,
    "pne_threshold": 1.0e-6,
    "NSMAX":    2,
    "PA[1]":    2.0, "PA[2]":  5.4462e-4,
    "PZ[1]":    1.0, "PZ[2]": -1.0,
    "PN[1]":    0.5, "PN[2]":   0.5,
    "PNS[1]":   0.025, "PNS[2]": 0.025,
    "PTPR[1]":  5.0, "PTPR[2]": 5.0,
    "PTPP[1]":  5.0, "PTPP[2]": 5.0,
    "PTS[1]":   0.3, "PTS[2]":  0.3,
    "MODELP[1]":206, "MODELP[2]":206,
    "MODELV[1]": 3,  "MODELV[2]": 0,
    "NCMIN[1]": -3,  "NCMIN[2]": -3,
    "NCMAX[1]":  3,  "NCMAX[2]":  3,
    "MDLWRI":   2, "MDLWRQ": 1, "MDLWRG": 1, "MDLWRP": 1, "MDLWRW": 0,
    "SMAX":     1.5, "DELS":   1e-3,
    "NSTPMAX":  1500, "NRAYMAX": 2,
    "RFIN[1]":  110.0e3, "RFIN[2]": 110.0e3,
    "RPIN[1]":  4.5,     "RPIN[2]":  4.5,
    "ZPIN[1]":  0.0,     "ZPIN[2]":  0.0,
    "PHIIN[1]": 0.0,     "PHIIN[2]": 0.0,
    "ANGPIN[1]": 0.0,    "ANGPIN[2]":10.0,
    "ANGTIN[1]":15.0,    "ANGTIN[2]":25.0,
    "UUIN[1]":   1.0,    "UUIN[2]":   1.0,
    "MODEWIN[1]":1,      "MODEWIN[2]":1,
}
```

- [ ] **Step 4: `wrx_demo_params.py` 作成（test_run/inputs/wrx_demo.in と同内容）**

Create `/home/k-yoshimi/program/task/python/wrxlib/tests/fixtures/wrx_demo_params.py`:
```python
"""WRX TST-2 minimal 1-ray case (mirror of test_run/inputs/wrx_demo.in)."""
PARAMS = {
    "MODELG":   2,
    "MODELN":   0,    "MODELQ": 0,
    "RR":       0.52, "RA":  0.3, "RB":  0.35,
    "BB":       0.308,
    "Q0":       1.0e4, "QA": 1.0e4,
    "PROFJ":    1.0, "PROFN1": 2.0, "PROFN2": 1.0,
    "PROFT1":   8.0, "PROFT2": 1.0,
    "pne_threshold": 1.0e-6,
    "NSMAX":    2,
    "PA[1]":    5.4462e-4, "PA[2]":  5.4462e-4,
    "PZ[1]":   -1.0,       "PZ[2]": -1.0,
    "PN[1]":    0.0194,    "PN[2]":  0.0006,
    "PNS[1]":   0.000194,  "PNS[2]": 0.000006,
    "PTPR[1]":  0.03,  "PTPR[2]": 60.0,
    "PTPP[1]":  0.03,  "PTPP[2]": 60.0,
    "PTS[1]":   0.01,  "PTS[2]":   1.0,
    "MODELP[1]":206, "MODELP[2]":206,
    "MODELV[1]": 3,  "MODELV[2]": 0,
    "NCMIN[1]": -2,  "NCMIN[2]": -2,
    "NCMAX[1]":  2,  "NCMAX[2]":  2,
    "MDLWRI":   2, "MDLWRQ": 2, "MDLWRG": 1, "MDLWRP": 1, "MDLWRW": 0,
    "SMAX":     1.0, "DELS":   1e-4,
    "NSTPMAX":  2000, "NRAYMAX": 1,
    "RFIN[1]":  28.0e3,
    "RPIN[1]":  0.85,
    "ZPIN[1]":  0.0,
    "PHIIN[1]": 0.0,
    "ANGPIN[1]": 0.0,
    "ANGTIN[1]":10.0,
    "UUIN[1]":  1.0,
    "MODEWIN[1]":1,
}
```

- [ ] **Step 5: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrxlib/tests/fixtures/
git commit -m "test(wrxlib): add Python params fixtures for 3 wrx baseline cases"
```

---

## Task 3: Layer 1 — 等価性テスト

**Files:**
- Create: `python/wrxlib/tests/test_equivalence.py`

L-0 の `wrx_regress.dat` ベースラインと Python ラッパ出力を比較。`compare_metrics.py --schema wrx` の `compare_wrx` 関数を直接 import して使う（L-0 で導入済み）。`WrxLib.get_state()` の `WrxState` を `extract_wrx_metrics.py` と同じ JSON shape（`scalars`, `arrays`, `arrays2`）に詰め替えて比較する。

- [ ] **Step 1: 等価性テストを書く**

Create `/home/k-yoshimi/program/task/python/wrxlib/tests/test_equivalence.py`:
```python
"""Layer 1: equivalence between WrxLib output and L-0 baselines."""
import importlib
import json
import os
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "test_run" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from python.wrxlib import WrxLib  # noqa: E402

import compare_metrics  # noqa: E402  (test_run/scripts/compare_metrics.py)


CASES = [
    ("wrx_iter01", "python.wrxlib.tests.fixtures.wrx_iter01_params"),
    ("wrx_jt60",   "python.wrxlib.tests.fixtures.wrx_jt60_params"),
    ("wrx_demo",   "python.wrxlib.tests.fixtures.wrx_demo_params"),
]
TOL = 1e-10
LIB_PATH = REPO / "wrx" / "libwrxapi.so"
BASELINES = REPO / "test_run" / "baselines"


def _state_to_metrics(st) -> dict:
    """Convert WrxState into the same JSON shape extract_wrx_metrics.py emits.

    Mirrors test_run/scripts/extract_wrx_metrics.py output schema:
      {
        NRAYMAX, NSTPMAX, NSAMAX_WR, NSMAX, MODELG, MDLWRQ,
        scalars: {pwr_tot},
        arrays:  {NSTPMAX_NRAY, pwr_nray, pwr_nsa,
                  pos_pwrmax_rs_nsa, pwrmax_rs_nsa,
                  pos_pwrmax_rl_nsa, pwrmax_rl_nsa},
        arrays2: {pwr_nsa_nray}
      }
    """
    def _list(x):
        # Accept both numpy arrays and Python lists.
        return [float(v) for v in x]

    pwr_nsa_nray_2d = [
        [float(st.pwr_nsa_nray[j][k]) for k in range(st.nsamax)]
        for j in range(st.nraymax)
    ] if st.nsamax > 0 and st.nraymax > 0 else []
    # extract_wrx_metrics emits rows=NSAMAX_WR cols=NRAYMAX (Fortran order),
    # whereas WrxState.from_c stores [nray][nsa]. Transpose to match.
    pwr_nsa_nray_baseline_shape = (
        [list(col) for col in zip(*pwr_nsa_nray_2d)] if pwr_nsa_nray_2d else []
    )

    return {
        "NRAYMAX":   st.nraymax,
        "NSTPMAX":   st.nstpmax,
        "NSAMAX_WR": st.nsamax,
        "NSMAX":     st.nsmax,
        "MODELG":    st.modelg,
        "MDLWRQ":    st.mdlwrq,
        "scalars":   {"pwr_tot": float(st.pwr_tot)},
        "arrays": {
            "NSTPMAX_NRAY":      [int(v) for v in st.nstp_end],
            "pwr_nray":          _list(st.pwr_nray),
            "pwr_nsa":           _list(st.pwr_nsa),
            "pos_pwrmax_rs_nsa": _list(st.pos_pwrmax_rs_nsa),
            "pwrmax_rs_nsa":     _list(st.pwrmax_rs_nsa),
            "pos_pwrmax_rl_nsa": _list(st.pos_pwrmax_rl_nsa),
            "pwrmax_rl_nsa":     _list(st.pwrmax_rl_nsa),
        },
        "arrays2": {
            "pwr_nsa_nray": pwr_nsa_nray_baseline_shape,
        },
    }


@unittest.skipUnless(LIB_PATH.exists(), "libwrxapi.so not built")
class TestEquivalence(unittest.TestCase):
    def _run_case(self, case_name: str, fixture_module: str) -> None:
        baseline_path = BASELINES / case_name / "metrics.json"
        if not baseline_path.exists():
            self.skipTest(f"baseline missing: {baseline_path}")
        baseline = json.loads(baseline_path.read_text())

        params = importlib.import_module(fixture_module).PARAMS
        with WrxLib(lib_path=LIB_PATH) as wrx:
            wrx.set_params(**params)
            wrx.run(0)
            actual = _state_to_metrics(wrx.get_state())

        errors = compare_metrics.compare_wrx(baseline, actual, TOL)
        self.assertFalse(errors, "\n".join(errors[:20]))

    def test_iter01(self):
        self._run_case("wrx_iter01", "python.wrxlib.tests.fixtures.wrx_iter01_params")

    def test_jt60(self):
        self._run_case("wrx_jt60", "python.wrxlib.tests.fixtures.wrx_jt60_params")

    def test_demo(self):
        self._run_case("wrx_demo", "python.wrxlib.tests.fixtures.wrx_demo_params")


if __name__ == "__main__":
    unittest.main()
```

注: WRX の ray-tracing は ODE 数値積分のため、Python 側 `set_param` 経由と stdin namelist 経由とで `set_param` の評価順が違う影響で `1e-10` を超える差が出る可能性。万一その場合は `TOL = 1e-8` に緩める（fixtures の `set_params` の dict 順序が namelist 評価順と異なる影響を別途調査）。

- [ ] **Step 2: テスト実行**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest python.wrxlib.tests.test_equivalence -v
```
Expected:
- `libwrxapi.so` がある場合は 3 ケース PASS（または許容誤差調整後 PASS）。
- `libwrxapi.so` が無い場合は全 skipped。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrxlib/tests/test_equivalence.py
git commit -m "test(wrxlib): add Layer 1 equivalence tests against L-0 baselines"
```

---

## Task 4: Layer 2 — C ABI 異常系テストを追加

**Files:**
- Create: `wrx/tests/c_abi/test_abi_negative.c`
- Modify: `wrx/tests/c_abi/Makefile`

L-2/L-3/L-4 で正常系はカバー済み。L-6 で「異常系の境界」を補強する。すべて L-2 確定 ABI（struct-based `wrx_get_state(wrx_state_t*)`、scalar `wrx_set_param(name, double)`）に従う。

- [ ] **Step 1: 異常系テスト**

Create `/home/k-yoshimi/program/task/wrx/tests/c_abi/test_abi_negative.c`:
```c
/* test_abi_negative.c
 * Edge cases for the WRX C ABI (Phase L-2/L-3 contract):
 *   - wrx_run before wrx_init -> 2 (NOT_INITIALIZED)
 *   - wrx_get_state before wrx_run -> 2 (NOT_INITIALIZED, via L-3 g_run_called)
 *     (older L-2 stub returned 4; accept either 2 or 4 here for transition)
 *   - wrx_finalize without wrx_init -> 0 (idempotent)
 *   - wrx_init then wrx_finalize then wrx_run -> 2
 *   - wrx_init then wrx_finalize (no run): no segfault from wr_deallocate
 *     (verified by ALLOCATED guard added in L-3 finalize)
 */
#include <stdio.h>
#include "../../wrx_api.h"

static int fail = 0;
#define EXPECT(call, want) do { int r = (call); if (r != (want)) { \
    fprintf(stderr, "FAIL %s = %d, want %d\n", #call, r, want); fail++; } } while (0)
#define EXPECT_IN(call, w1, w2) do { int r = (call); \
    if (r != (w1) && r != (w2)) { \
      fprintf(stderr, "FAIL %s = %d, want %d or %d\n", #call, r, w1, w2); fail++; } \
    } while (0)

int main(void) {
    /* (1) run before init -> NOT_INITIALIZED */
    EXPECT(wrx_run(1), 2);

    /* (2) get_state before init -> NOT_INITIALIZED */
    wrx_state_t st;
    EXPECT(wrx_get_state(&st), 2);

    /* (3) finalize without init -> 0 (idempotent, ALLOCATED-guarded) */
    EXPECT(wrx_finalize(), 0);

    /* (4) init then immediate finalize (no run): must not segfault. */
    EXPECT(wrx_init(),     0);
    EXPECT(wrx_finalize(), 0);  /* ALLOCATED guard prevents wr_deallocate */

    /* (5) operations after finalize -> NOT_INITIALIZED */
    EXPECT(wrx_run(1), 2);

    /* (6) get_state after init but before run: 2 (L-3) or 4 (L-2 stub). */
    EXPECT(wrx_init(), 0);
    EXPECT_IN(wrx_get_state(&st), 2, 4);
    EXPECT(wrx_finalize(), 0);

    return fail ? 1 : 0;
}
```

- [ ] **Step 2: Makefile に追加**

Modify `/home/k-yoshimi/program/task/wrx/tests/c_abi/Makefile`. Append:
```make
test_abi_negative: test_abi_negative.c $(WRX_LIB)
	$(CC) $(CFLAGS) test_abi_negative.c $(WRX_LIB) $(DEPS) $(LIB_MTX) $(LIBX_MTX) \
	    $(FLIBS) -lm -o $@
```

Update `run-all`:
```
run-all: test_abi_stub test_param_set test_abi_negative
	./test_abi_stub && ./test_param_set && ./test_abi_negative
```

- [ ] **Step 3: ビルドと実行**

Run:
```bash
cd /home/k-yoshimi/program/task/wrx/tests/c_abi
make test_abi_negative && ./test_abi_negative
echo "exit=$?"
```
Expected: 全 EXPECT OK、exit 0。

- [ ] **Step 4: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add wrx/tests/c_abi/test_abi_negative.c wrx/tests/c_abi/Makefile
git commit -m "test(wrx): add Layer 2 C ABI negative-path tests"
```

---

## Task 5: Layer 4 — 網羅計算 smoke test

**Files:**
- Create: `python/wrxlib/tests/test_sweep.py`

`pwr_profile` 等の存在しないキーは使わず、`get_state()` で返される `WrxState` の合計吸収パワー (`pwr_tot`) と `pwrmax_rl_nsa.sum()`（または `pwr_nsa.sum()`）が有限・非負であることを検証する。

- [ ] **Step 1: 3x3 グリッドスイープ**

Create `/home/k-yoshimi/program/task/python/wrxlib/tests/test_sweep.py`:
```python
"""Layer 4: small parameter-sweep smoke test."""
import os
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LIB_PATH = REPO / "wrx" / "libwrxapi.so"

from python.wrxlib import WrxLib  # noqa: E402
from python.wrxlib.tests.fixtures.wrx_iter01_params import PARAMS as BASE


def _sum(seq) -> float:
    """Works for both numpy arrays and Python lists."""
    total = 0.0
    for v in seq:
        total += float(v)
    return total


@unittest.skipUnless(LIB_PATH.exists(), "libwrxapi.so not built")
class TestSweep(unittest.TestCase):
    def test_3x3_grid(self):
        rfin_grid = [140.0e3, 170.0e3, 200.0e3]   # EC frequency sweep
        ang_grid  = [0.0, 5.0, 10.0]              # poloidal injection angle
        results = []
        for rf in rfin_grid:
            for ang in ang_grid:
                with WrxLib(lib_path=LIB_PATH) as wrx:
                    wrx.set_params(**BASE)
                    # Reduce cost: 1 ray per sweep point.
                    wrx.set_params(NRAYMAX=1)
                    wrx.set_param("RFIN[1]",  rf)
                    wrx.set_param("ANGPIN[1]", ang)
                    wrx.run(0)
                    st = wrx.get_state()
                    pk = _sum(st.pwrmax_rl_nsa)  # LH-side absorbed peak sum
                    tot = float(st.pwr_tot)
                    results.append((rf, ang, tot, pk))
        self.assertEqual(len(results), 9)
        for rf, ang, tot, pk in results:
            self.assertGreaterEqual(tot, 0.0)
            self.assertGreaterEqual(pk,  0.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 実行**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest python.wrxlib.tests.test_sweep -v
```
Expected: 9 ケース完走、PASS。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrxlib/tests/test_sweep.py
git commit -m "test(wrxlib): add Layer 4 3x3 parameter-sweep smoke test"
```

---

## Task 6: `run_tests.sh` に Python/C モードを追加

**Files:**
- Modify: `test_run/run_tests.sh`
- Modify: `test_run/test_definitions.conf`

- [ ] **Step 1: `test_definitions.conf` に追加**

Append to `/home/k-yoshimi/program/task/test_run/test_definitions.conf`:
```
# =============================================================================
# WRX Library (Phase L) Tests
# =============================================================================
wrxlib_ffi:wrxlib:python.wrxlib.tests.test_ffi:none:120:Layer 3 ctypes FFI tests
wrxlib_wrxlib:wrxlib:python.wrxlib.tests.test_wrxlib:none:120:Layer 3 WrxLib class tests
wrxlib_equivalence:wrxlib:python.wrxlib.tests.test_equivalence:none:600:Layer 1 equivalence vs baselines
wrxlib_sweep:wrxlib:python.wrxlib.tests.test_sweep:none:600:Layer 4 parameter sweep smoke
wrxlib_c_abi:wrxlib_c:test_abi_stub test_param_set test_abi_negative test_abi_so:none:120:Layer 2 C ABI tests
```

- [ ] **Step 2: `run_tests.sh` を更新**

Modify `/home/k-yoshimi/program/task/test_run/run_tests.sh`. After the existing `get_binary` block, add a helper:

```bash
# For wrxlib (Python) and wrxlib_c (C) "modules", input_file is interpreted as
# the unittest module path (wrxlib) or whitespace-separated test binary names (wrxlib_c).
run_python_test_wrxlib() {
    local timeout="$1"; shift
    local module_path="$1"
    cd "$TASK_DIR"
    timeout "$timeout" python3 -m unittest "$module_path" -v
}

run_c_abi_tests_wrxlib() {
    local timeout="$1"; shift
    local tests=$1
    cd "$TASK_DIR/wrx/tests/c_abi"
    make $tests 2>&1 | tail -5
    for t in $tests; do
        if ! timeout "$timeout" "./$t"; then
            return 1
        fi
    done
}
```

Then in `run_single_test`, after the existing TR/WR module branches, add a special path before the `binary` execution:

```bash
    # Special handling: wrxlib (Python) / wrxlib_c (C ABI tests).
    if [[ "$module" == "wrxlib" ]]; then
        echo -n "[$TOTAL] $test_name ($description) ... "
        local log_file="$TEST_OUTPUT_DIR/$test_name.log"
        mkdir -p "$TEST_OUTPUT_DIR"
        if run_python_test_wrxlib "$timeout" "$input_file" > "$log_file" 2>&1; then
            echo -e "${GREEN}PASS${NC}"; PASSED=$((PASSED+1)); COMPLETED_TESTS[$test_name]=1
        else
            echo -e "${RED}FAIL${NC} (see $log_file)"; FAILED=$((FAILED+1))
        fi
        return 0
    elif [[ "$module" == "wrxlib_c" ]]; then
        echo -n "[$TOTAL] $test_name ($description) ... "
        local log_file="$TEST_OUTPUT_DIR/$test_name.log"
        mkdir -p "$TEST_OUTPUT_DIR"
        if run_c_abi_tests_wrxlib "$timeout" "$input_file" > "$log_file" 2>&1; then
            echo -e "${GREEN}PASS${NC}"; PASSED=$((PASSED+1)); COMPLETED_TESTS[$test_name]=1
        else
            echo -e "${RED}FAIL${NC} (see $log_file)"; FAILED=$((FAILED+1))
        fi
        return 0
    fi
```

注: 入力位置は既存の `get_binary "$module"` の前後で OK。`get_binary` を回避する分岐として早期 return する設計。sister wr L-6 と並列の helper 名（`_wrxlib` suffix）にして衝突を回避する。

- [ ] **Step 3: 実行**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh wrxlib_ffi wrxlib_wrxlib wrxlib_equivalence wrxlib_sweep wrxlib_c_abi
```
Expected: 5 ケースとも PASS。

- [ ] **Step 4: 全件実行で既存への影響なしを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh
```
Expected: 全件 PASS。

- [ ] **Step 5: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/run_tests.sh test_run/test_definitions.conf
git commit -m "test(wrx): wire wrxlib 4-layer tests into run_tests.sh"
```

---

## 完了基準

- [ ] Layer 1 (`test_equivalence.py`) — 3 ケースの Python ラッパ出力が L-0 baseline と相対誤差 1e-10 一致
- [ ] Layer 2 — `test_abi_stub, test_param_set, test_abi_so, test_abi_negative` 4 つの C テスト全 PASS（`wrx_get_state(&st)` struct 形式、`wrx_set_param(name, double)` scalar 形式）
- [ ] Layer 3 (`test_ffi.py`, `test_wrxlib.py`) — Python ラッパの単体テスト全 PASS
- [ ] Layer 4 (`test_sweep.py`) — 3x3 = 9 ケースのスイープが完走
- [ ] `run_tests.sh wrxlib_*` で 5 ケース全件 PASS
- [ ] 既存 TR/EQ/TX/WR/WRX 回帰テストへの影響なし
- [ ] sister wr `wrlib_*` と wrx `wrxlib_*` が同一 `run_tests.sh` 実行で衝突しない

## 撤退条件

- Layer 1 で 1e-10 を超える差 → 許容誤差を `1e-8` に緩める。`set_params` の順序を namelist 評価順に揃える試みは別タスクで（最低でも commit して動かす）
- Layer 2 で `test_abi_negative` が seg-fault → L-3 で導入した `g_run_called` + `ALLOCATED(pwr_nray)` ガードが効いていない可能性。`wrx_finalize` 実装を再確認
- Layer 4 sweep で特定パラメータでクラッシュ → fixture の `RFIN/ANGPIN` 範囲を狭める or `NSTPMAX` を半減

## 依存

- 前提: L-0, L-2, L-3, L-4, L-5 完了
- 後続: L-7 (README + notebook)
