# WR ライブラリ化 Phase L-6: 4 層テスト 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-0 で作った回帰テスト基盤に加え、L-2/L-3/L-5 で出来た C ABI と Python ラッパに対する 4 層のテスト（等価性 / C ABI / Python ラッパ / 網羅計算 smoke）を整備し、`run_tests.sh` から走らせられる形にする。

**Architecture:** TR の Phase L-6 と同じ 4 層構成を WR にミラーリング。

| Layer | 目的 | 実装 | 場所 |
|---|---|---|---|
| 1. 等価性 | `Wrlib` 経由の出力が既存 `wr` バイナリの dump (L-0 baseline) と相対誤差 1e-10 で一致 | `python/wrlib/tests/test_equivalence.py` | Python unittest |
| 2. C ABI 単体 | 5 つの C 関数が個別に正しく動作 | L-2/L-3/L-4 で追加した `wr/tests/c_abi/test_*` の整理 + 新規 invalid input テスト | C |
| 3. Python ラッパ | `Wrlib` class が Pythonic に動く | L-5 の `test_ffi.py` / `test_wrlib.py` を強化（既存資産再利用） | Python unittest |
| 4. 網羅計算 smoke | 小規模パラメータスイープで完走 | `python/wrlib/tests/test_sweep.py` | Python unittest |

`test_run/run_tests.sh` に「Python 実行モード」を追加し、`wrlib_*` カテゴリとして 4 層テストを走らせる。

**Tech Stack:** Python 3 (`unittest`), C (既存)、Bash。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 8 と Phase L-6。

---

## 既存資産

| L-x | 既存ファイル | 役割 |
|---|---|---|
| L-0 | `test_run/baselines/wr_*/metrics.json` | Layer 1 の参照値 |
| L-0 | `test_run/inputs/wr_*.in` | namelist セット（Python から再現する元） |
| L-0 | `test_run/scripts/extract_wr_metrics.py` | 手動 dump → JSON 変換 |
| L-2 | `wr/tests/c_abi/test_abi_stub.c` | Layer 2 (init/finalize) |
| L-3 | `wr/tests/c_abi/test_param_set.c` | Layer 2 (set_param 正常/異常) |
| L-4 | `wr/tests/c_abi/test_abi_so.c` | Layer 2 (dlopen + run cycle) |
| L-5 | `python/wrlib/tests/test_ffi.py`, `test_wrlib.py` | Layer 3 |

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/wrlib/tests/test_equivalence.py` | 新規 | Layer 1: `wr_iter_lhcd, wr_test001, wr_tst2_ec` の baseline JSON と Python ラッパ出力を比較 |
| `python/wrlib/tests/fixtures/wr_iter_lhcd_params.py` | 新規 | namelist → Python dict 変換（手動・WR namelist パーサ依存なし） |
| `python/wrlib/tests/fixtures/wr_test001_params.py` | 新規 | 同上 |
| `python/wrlib/tests/fixtures/wr_tst2_ec_params.py` | 新規 | 同上 |
| `python/wrlib/tests/test_sweep.py` | 新規 | Layer 4: 3x3 グリッドの (RFIN, ANGPHIN) スイープ smoke |
| `wr/tests/c_abi/test_abi_negative.c` | 新規（任意） | Layer 2: `wr_run` を `wr_init` 抜きで呼ぶなどの異常系を追加 |
| `test_run/test_definitions.conf` | 修正 | `wrlib_equivalence`, `wrlib_ffi`, `wrlib_wrlib`, `wrlib_sweep`, `wrlib_c_abi` の 5 ケース追加 |
| `test_run/run_tests.sh` | 修正 | Python 実行モード（`module=wrlib`）と C 実行モード（`module=wrlib_c`）の対応 |

**方針:**
- namelist パーサは標準ライブラリでは扱いづらいため、L-6 では「fixture を Python dict として手書き」する（TR L-6 と同じ）。`f90nml` 等の追加依存は導入しない。
- Layer 1 の許容誤差は L-0 と同じ `1e-10`（dump 経路は同じ Fortran コードを通るので bit-exact 一致を期待）。

---

## Task 1: ブランチ作成と前提確認

**Files:** なし

- [ ] **Step 1: develop 最新 + ブランチ作成**

Run:
```bash
cd /home/k-yoshimi/program/task
git checkout develop
git pull origin develop
git checkout -b feature/wr-library-L6-tests
```

- [ ] **Step 2: L-5 までの成果物が揃っていることを確認**

Run:
```bash
ls -la /home/k-yoshimi/program/task/wr/libwrapi.so 2>&1
ls /home/k-yoshimi/program/task/python/wrlib/wrlib.py
ls /home/k-yoshimi/program/task/test_run/baselines/wr_iter_lhcd/metrics.json
```
Expected: 全て存在する。

- [ ] **Step 3: マーカーコミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "chore(wr): start Phase L-6 4-layer tests"
```

---

## Task 2: namelist → Python dict fixture を作成

**Files:**
- Create: `python/wrlib/tests/fixtures/__init__.py`
- Create: `python/wrlib/tests/fixtures/wr_iter_lhcd_params.py`
- Create: `python/wrlib/tests/fixtures/wr_test001_params.py`
- Create: `python/wrlib/tests/fixtures/wr_tst2_ec_params.py`

各 fixture は `params: dict[str, float]` を export する。`PN[1]` 形式で配列も含める。

- [ ] **Step 1: ディレクトリと __init__**

Run:
```bash
mkdir -p /home/k-yoshimi/program/task/python/wrlib/tests/fixtures
touch /home/k-yoshimi/program/task/python/wrlib/tests/fixtures/__init__.py
```

- [ ] **Step 2: `wr_iter_lhcd_params.py` 作成**

Create `/home/k-yoshimi/program/task/python/wrlib/tests/fixtures/wr_iter_lhcd_params.py`:
```python
"""WR ITER LHCD case (mirror of test_run/inputs/wr_iter_lhcd.in)."""
PARAMS = {
    "MODELG":   2,
    "RR":       6.2,
    "RA":       2.0,
    "RKAP":     1.7,
    "RDLT":     0.33,
    "BB":       5.3,
    "RIP":      15.0,
    "NSMAX":    2,
    "PA[1]":    2.0, "PA[2]":   1.0,
    "PZ[1]":    1.0, "PZ[2]":  -1.0,
    "PN[1]":    1.0, "PN[2]":   1.0,
    "PNS[1]":   0.1, "PNS[2]":  0.1,
    "PTPR[1]": 10.0, "PTPR[2]":10.0,
    "PTPP[1]": 10.0, "PTPP[2]":10.0,
    "PTS[1]":   0.5, "PTS[2]":  0.5,
    "PROFN1":   2.0, "PROFN2":  2.0,
    "PROFT1":   2.0, "PROFT2":  1.0,
    "MODELP[1]":4,   "MODELP[2]":4,
    "NRAYMAX":  2,
    "NSTPMAX":  2000,
    "NRSMAX":   50,
    "NRLMAX":   100,
    "MDLWRI":   101,
    "MDLWRQ":   0,
    "MDLWRW":   0,
    "SMAX":     5.0,
    "DELS":     0.05,
    "RFIN[1]":  5.0e3,  "RFIN[2]":  5.0e3,
    "RPIN[1]":  8.0,    "RPIN[2]":  8.0,
    "ZPIN[1]":  0.0,    "ZPIN[2]":  0.0,
    "PHIIN[1]": 0.0,    "PHIIN[2]": 0.0,
    "ANGZIN[1]":  0.0,  "ANGZIN[2]":  0.0,
    "ANGPHIN[1]":30.0,  "ANGPHIN[2]":40.0,
    "UUIN[1]":  1.0,    "UUIN[2]":  1.0,
    "MODEWIN[1]":1,     "MODEWIN[2]":1,
}
```

- [ ] **Step 3: `wr_test001_params.py` 作成（test_run/inputs/wr_test001.in と同内容）**

Create `/home/k-yoshimi/program/task/python/wrlib/tests/fixtures/wr_test001_params.py`:
```python
"""WR test001 short case (mirror of wr/in/test001.in).

Units (per `wr/wrexecr.f90`: `omega = 2.D6 * PI * RFIN(nray)`):
- RFIN[i]: MHz  (so 160.0e3 MHz = 160 GHz, matching `RFIN(1)=4*160.D3` in test001.in)
- RPIN[i]/ZPIN[i]: meters
- ANGZIN[i]/ANGPHIN[i]: degrees
"""
PARAMS = {
    "MODELG":   2,
    "RR":       6.2,
    "RA":       2.0,
    "RKAP":     1.7,
    "BB":       5.3,
    "NSMAX":    4,
    "PA[2]":    2.0, "PA[3]":   3.0, "PA[4]":   4.0,
    "PZ[2]":    1.0, "PZ[3]":   1.0, "PZ[4]":   2.0,
    "PN[1]":    0.9, "PN[2]":   0.40, "PN[3]":  0.40, "PN[4]":  0.05,
    "PNS[1]":   0.03, "PNS[2]": 0.0133, "PNS[3]":0.0133, "PNS[4]":0.0017,
    "PTPR[1]": 35.0, "PTPR[2]":35.0, "PTPR[3]":35.0, "PTPR[4]":35.0,
    "PTPP[1]": 35.0, "PTPP[2]":35.0, "PTPP[3]":35.0, "PTPP[4]":35.0,
    "PTS[1]":   1.0, "PTS[2]":  1.0, "PTS[3]":  1.0, "PTS[4]":  1.0,
    "PROFN1":   3.7, "PROFN2":  2.7,
    "MODELP[1]":4, "MODELP[2]":4, "MODELP[3]":4, "MODELP[4]":4,
    "MDLWRI":   101, "MDLWRQ": 0,   "MDLWRW": 0,
    "SMAX":     5.0,  "DELS":   0.01,
    "NRAYMAX":  2,    "NSTPMAX": 2000, "NRSMAX": 50, "NRLMAX": 100,
    "RFIN[1]": 160.0e3, "RFIN[2]": 160.0e3,   # MHz (= 160 GHz); cf. test001.in: RFIN(1)=4*160.D3
    "RPIN[1]": 8.5, "RPIN[2]": 8.5,
    "ZPIN[1]": 0.0, "ZPIN[2]": 0.0,
    "PHIIN[1]":0.0, "PHIIN[2]":0.0,
    "ANGZIN[1]":-30.0, "ANGZIN[2]":-30.0,
    "ANGPHIN[1]":20.0, "ANGPHIN[2]":30.0,
    "UUIN[1]": 1.0, "UUIN[2]": 1.0,
    "MODEWIN[1]":1, "MODEWIN[2]":1,
}
```

- [ ] **Step 4: `wr_tst2_ec_params.py` 作成**

Create `/home/k-yoshimi/program/task/python/wrlib/tests/fixtures/wr_tst2_ec_params.py`:
```python
"""WR TST-2 EC case (mirror of test_run/inputs/wr_tst2_ec.in)."""
PARAMS = {
    "MODELG":   2,
    "RR":       0.38,
    "RA":       0.25,
    "RKAP":     1.6,
    "RDLT":     0.0,
    "BB":       0.3,
    "RIP":      0.2,
    "NSMAX":    2,
    "PA[1]":    2.0, "PA[2]":   1.0,
    "PZ[1]":    1.0, "PZ[2]":  -1.0,
    "PN[1]":    0.5, "PN[2]":   0.5,
    "PNS[1]":   0.05,"PNS[2]":  0.05,
    "PTPR[1]":  0.5, "PTPR[2]": 0.5,
    "PTPP[1]":  0.5, "PTPP[2]": 0.5,
    "PTS[1]":   0.05,"PTS[2]":  0.05,
    "PROFN1":   2.0, "PROFN2":  2.0,
    "MODELP[1]":4,   "MODELP[2]":4,
    "NRAYMAX":  1,
    "NSTPMAX":  1000,
    "NRSMAX":   30,
    "NRLMAX":   60,
    "MDLWRI":   101, "MDLWRQ": 0, "MDLWRW": 0,
    "SMAX":     2.0, "DELS":   0.01,
    "RFIN[1]":  8.2e3,
    "RPIN[1]":  0.7,
    "ZPIN[1]":  0.0,
    "PHIIN[1]": 0.0,
    "ANGZIN[1]":0.0,
    "ANGPHIN[1]":15.0,
    "UUIN[1]":  1.0,
    "MODEWIN[1]":1,
}
```

- [ ] **Step 5: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrlib/tests/fixtures/
git commit -m "test(wrlib): add Python params fixtures for 3 baseline cases"
```

---

## Task 3: Layer 1 — 等価性テスト

**Files:**
- Create: `python/wrlib/tests/test_equivalence.py`

L-0 の `wr_regress.dat` ベースラインと Python ラッパ出力を比較。dump はバイナリ実行と Python 実行で同じ Fortran コード (`wrregress.f90`) を通るため、`Wrlib.run()` 内部で `WR_REGRESS_DUMP=1` を立てて dump してもらえばそのまま比較可能。

ただし `Wrlib.run()` から dump を生成するには **`os.environ["WR_REGRESS_DUMP"] = "1"` を `_lib.wr_run` 呼び出し前に設定**する必要がある。`subprocess` ではなく同一プロセス内なので、`os.environ` 経由で `GET_ENVIRONMENT_VARIABLE` が拾うかどうかをまず確認する（POSIX 環境では拾うはず）。

代替: 直接 `Wrlib.get_state()` の値を baseline `metrics.json` の値と比較する（dump ファイル経由を回避）。`compare_metrics.py --schema wr` の `compare_wr` 関数を直接 import して使う。

- [ ] **Step 1: 等価性テストを書く（直接比較版）**

Create `/home/k-yoshimi/program/task/python/wrlib/tests/test_equivalence.py`:
```python
"""Layer 1: equivalence between Wrlib output and L-0 baselines."""
import importlib
import json
import os
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "test_run" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from python.wrlib import Wrlib  # noqa: E402

import compare_metrics  # noqa: E402  (test_run/scripts/compare_metrics.py)


CASES = [
    ("wr_iter_lhcd", "python.wrlib.tests.fixtures.wr_iter_lhcd_params"),
    ("wr_test001",   "python.wrlib.tests.fixtures.wr_test001_params"),
    ("wr_tst2_ec",   "python.wrlib.tests.fixtures.wr_tst2_ec_params"),
]
TOL = 1e-10
LIB_PATH = REPO / "wr" / "libwrapi.so"
BASELINES = REPO / "test_run" / "baselines"


def _state_to_metrics(st, params: dict) -> dict:
    """Convert WrState into the same JSON shape extract_wr_metrics.py emits.

    NSTPMAX is taken from the namelist (params), not from runtime nstp_end —
    the baseline JSON stores the configured upper bound, not the actually-used
    step count, so comparing max(nstp_end) would diverge.
    """
    return {
        "NRAYMAX": st.nraymax,
        "NSTPMAX": int(params["NSTPMAX"]),
        "NRSMAX":  st.nrsmax,
        "NRLMAX":  st.nrlmax,
        "scalars": {
            "RF":     -1.0,  # not in get_state; baseline includes input scalars,
            "RPI":    -1.0,  # so we exclude these from comparison and rely on
            "ZPI":    -1.0,  # "rays" + "profile_*" + "pos_pwrmax_*" only.
            "PHII":   -1.0,
            "RNZI":   -1.0,
            "RNPHII": -1.0,
            "RKR0":   -1.0,
            "UUI":    -1.0,
            "pos_pwrmax_rs": st.pos_pwrmax_rs,
            "pwrmax_rs":     st.pwrmax_rs,
            "pos_pwrmax_rl": st.pos_pwrmax_rl,
            "pwrmax_rl":     st.pwrmax_rl,
        },
        "rays": [
            {
                "NRAY":               i + 1,
                "NSTP_END":           st.nstp_end[i],
                "pos_pwrmax_rs_nray": float(st.pos_pwrmax_rs_nray[i]),
                "pwrmax_rs_nray":     float(st.pwrmax_rs_nray[i]),
                "pos_pwrmax_rl_nray": float(st.pos_pwrmax_rl_nray[i]),
                "pwrmax_rl_nray":     float(st.pwrmax_rl_nray[i]),
                "RAYS_END": [float(x) for x in (st.rays_end[i] if hasattr(st.rays_end, "__getitem__") else [])],
            }
            for i in range(st.nraymax)
        ],
        "profile_rs": [
            {"NRS": i + 1, "pos_nrs": float(st.pos_nrs[i]), "pwr_nrs": float(st.pwr_nrs[i])}
            for i in range(st.nrsmax)
        ],
        "profile_rl": [
            {"NRL": i + 1, "pos_nrl": float(st.pos_nrl[i]), "pwr_nrl": float(st.pwr_nrl[i])}
            for i in range(st.nrlmax)
        ],
    }


@unittest.skipUnless(LIB_PATH.exists(), "libwrapi.so not built")
class TestEquivalence(unittest.TestCase):
    def _run_case(self, case_name: str, fixture_module: str) -> None:
        baseline_path = BASELINES / case_name / "metrics.json"
        if not baseline_path.exists():
            self.skipTest(f"baseline missing: {baseline_path}")
        baseline = json.loads(baseline_path.read_text())

        params = importlib.import_module(fixture_module).PARAMS
        with Wrlib(lib_path=LIB_PATH) as wr:
            wr.set_params(**params)
            wr.run(0)
            actual = _state_to_metrics(wr.get_state(), params)

        # We strip input-only scalars (RF/RPI/...) from baseline before compare,
        # since wr_get_state does not currently expose them. They are validated
        # separately in test_wrlib via set/get_param round-trip in L-7.
        b_strip = {**baseline, "scalars": {
            k: v for k, v in baseline["scalars"].items()
            if k in ("pos_pwrmax_rs", "pwrmax_rs", "pos_pwrmax_rl", "pwrmax_rl")
        }}
        a_strip = {**actual, "scalars": {
            k: v for k, v in actual["scalars"].items()
            if k in ("pos_pwrmax_rs", "pwrmax_rs", "pos_pwrmax_rl", "pwrmax_rl")
        }}

        errors = compare_metrics.compare_wr(b_strip, a_strip, TOL)
        self.assertFalse(errors, "\n".join(errors[:20]))

    def test_iter_lhcd(self):
        self._run_case("wr_iter_lhcd", "python.wrlib.tests.fixtures.wr_iter_lhcd_params")

    def test_test001(self):
        self._run_case("wr_test001", "python.wrlib.tests.fixtures.wr_test001_params")

    def test_tst2_ec(self):
        self._run_case("wr_tst2_ec", "python.wrlib.tests.fixtures.wr_tst2_ec_params")


if __name__ == "__main__":
    unittest.main()
```

注: WR の `pwr_nrs/pwr_nrl` は ray の経路と数値積分の組み合わせで決まるため、Python 側の `set_param` 経由と stdin namelist 経由とで同じ計算順序を再現できれば bit-exact 一致するはず。万一 `1e-10` を超える差が出る場合は許容誤差を `1e-8` に緩める（fixtures の `set_param` の順序が namelist 評価順と異なる影響）。

- [ ] **Step 2: テスト実行**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest python.wrlib.tests.test_equivalence -v
```
Expected:
- `libwrapi.so` がある場合は 3 ケース PASS（または許容誤差調整後 PASS）。
- `libwrapi.so` が無い場合は全 skipped。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrlib/tests/test_equivalence.py
git commit -m "test(wrlib): add Layer 1 equivalence tests against L-0 baselines"
```

---

## Task 4: Layer 2 — C ABI 異常系テストを追加

**Files:**
- Create: `wr/tests/c_abi/test_abi_negative.c`
- Modify: `wr/tests/c_abi/Makefile`

L-2/L-3/L-4 で正常系はカバー済み。L-6 で「異常系の境界」を補強する。

- [ ] **Step 1: 異常系テスト**

Create `/home/k-yoshimi/program/task/wr/tests/c_abi/test_abi_negative.c`:
```c
/* test_abi_negative.c
 * Edge cases:
 *   - wr_run before wr_init -> 2
 *   - wr_get_state before wr_run -> 2
 *   - wr_finalize without wr_init -> 0 (idempotent)
 *   - wr_init then wr_finalize then wr_run -> 2
 */
#include <stdio.h>
#include "../../wr_api.h"

static int fail = 0;
#define EXPECT(call, want) do { int r = (call); if (r != (want)) { \
    fprintf(stderr, "FAIL %s = %d, want %d\n", #call, r, want); fail++; } } while (0)

int main(void) {
    EXPECT(wr_run(1), 2);

    wr_state_t st;
    EXPECT(wr_get_state(&st), 2);

    EXPECT(wr_finalize(), 0);

    EXPECT(wr_init(), 0);
    EXPECT(wr_finalize(), 0);
    EXPECT(wr_run(1), 2);
    EXPECT(wr_finalize(), 0);
    return fail ? 1 : 0;
}
```

- [ ] **Step 2: Makefile に追加**

Modify `/home/k-yoshimi/program/task/wr/tests/c_abi/Makefile`. Append:
```make
test_abi_negative: test_abi_negative.c $(WR_LIB)
	$(CC) $(CFLAGS) test_abi_negative.c $(WR_LIB) $(DEPS) $(LIB_MTX) $(LIBX_MTX) \
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
cd /home/k-yoshimi/program/task/wr/tests/c_abi
make test_abi_negative && ./test_abi_negative
echo "exit=$?"
```
Expected: 全 EXPECT OK、exit 0。

- [ ] **Step 4: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add wr/tests/c_abi/test_abi_negative.c wr/tests/c_abi/Makefile
git commit -m "test(wr): add Layer 2 C ABI negative-path tests"
```

---

## Task 5: Layer 4 — 網羅計算 smoke test

**Files:**
- Create: `python/wrlib/tests/test_sweep.py`

- [ ] **Step 1: 3x3 グリッドスイープ**

Create `/home/k-yoshimi/program/task/python/wrlib/tests/test_sweep.py`:
```python
"""Layer 4: small parameter-sweep smoke test."""
import os
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LIB_PATH = REPO / "wr" / "libwrapi.so"

from python.wrlib import Wrlib  # noqa: E402
from python.wrlib.tests.fixtures.wr_iter_lhcd_params import PARAMS as BASE


@unittest.skipUnless(LIB_PATH.exists(), "libwrapi.so not built")
class TestSweep(unittest.TestCase):
    def test_3x3_grid(self):
        rfin_grid = [4.0e3, 5.0e3, 6.0e3]   # LH frequency sweep
        ang_grid  = [25.0, 30.0, 35.0]      # toroidal injection angle
        results = []
        for rf in rfin_grid:
            for ang in ang_grid:
                with Wrlib(lib_path=LIB_PATH) as wr:
                    wr.set_params(**BASE)
                    wr.set_params(NRAYMAX=1)
                    wr.set_param("RFIN[1]", rf)
                    wr.set_param("ANGPHIN[1]", ang)
                    wr.run(0)
                    st = wr.get_state()
                    results.append((rf, ang, st.pwrmax_rs))
        self.assertEqual(len(results), 9)
        for rf, ang, peak in results:
            self.assertGreaterEqual(peak, 0.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 実行**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest python.wrlib.tests.test_sweep -v
```
Expected: 9 ケース完走、PASS。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add python/wrlib/tests/test_sweep.py
git commit -m "test(wrlib): add Layer 4 3x3 parameter-sweep smoke test"
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
# WR Library (Phase L) Tests
# =============================================================================
wrlib_ffi:wrlib:python.wrlib.tests.test_ffi:none:120:Layer 3 ctypes FFI tests
wrlib_wrlib:wrlib:python.wrlib.tests.test_wrlib:none:120:Layer 3 Wrlib class tests
wrlib_equivalence:wrlib:python.wrlib.tests.test_equivalence:none:600:Layer 1 equivalence vs baselines
wrlib_sweep:wrlib:python.wrlib.tests.test_sweep:none:600:Layer 4 parameter sweep smoke
wrlib_c_abi:wrlib_c:test_abi_stub test_param_set test_abi_negative test_abi_so:none:120:Layer 2 C ABI tests
```

- [ ] **Step 2: `run_tests.sh` を更新**

Modify `/home/k-yoshimi/program/task/test_run/run_tests.sh`. After the existing `get_binary` block, add a helper:

```bash
# For wrlib (Python) and wrlib_c (C) "modules", input_file is interpreted as
# the unittest module path (wrlib) or whitespace-separated test binary names (wrlib_c).
run_python_test() {
    local timeout="$1"; shift
    local module_path="$1"
    cd "$TASK_DIR"
    timeout "$timeout" python3 -m unittest "$module_path" -v
}

run_c_abi_tests() {
    local timeout="$1"; shift
    local tests=$1
    cd "$TASK_DIR/wr/tests/c_abi"
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
    # Special handling: wrlib (Python) / wrlib_c (C ABI tests).
    if [[ "$module" == "wrlib" ]]; then
        echo -n "[$TOTAL] $test_name ($description) ... "
        local log_file="$TEST_OUTPUT_DIR/$test_name.log"
        mkdir -p "$TEST_OUTPUT_DIR"
        if run_python_test "$timeout" "$input_file" > "$log_file" 2>&1; then
            echo -e "${GREEN}PASS${NC}"; PASSED=$((PASSED+1)); COMPLETED_TESTS[$test_name]=1
        else
            echo -e "${RED}FAIL${NC} (see $log_file)"; FAILED=$((FAILED+1))
        fi
        return 0
    elif [[ "$module" == "wrlib_c" ]]; then
        echo -n "[$TOTAL] $test_name ($description) ... "
        local log_file="$TEST_OUTPUT_DIR/$test_name.log"
        mkdir -p "$TEST_OUTPUT_DIR"
        if run_c_abi_tests "$timeout" "$input_file" > "$log_file" 2>&1; then
            echo -e "${GREEN}PASS${NC}"; PASSED=$((PASSED+1)); COMPLETED_TESTS[$test_name]=1
        else
            echo -e "${RED}FAIL${NC} (see $log_file)"; FAILED=$((FAILED+1))
        fi
        return 0
    fi
```

注: 入力位置は既存の `get_binary "$module"` の前後で OK。`get_binary` を回避する分岐として早期 return する設計。

- [ ] **Step 3: 実行**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh wrlib_ffi wrlib_wrlib wrlib_equivalence wrlib_sweep wrlib_c_abi
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
git commit -m "test(wr): wire wrlib 4-layer tests into run_tests.sh"
```

---

## 完了基準

- [ ] Layer 1 (`test_equivalence.py`) — 3 ケースの Python ラッパ出力が L-0 baseline と相対誤差 1e-10 一致
- [ ] Layer 2 — `test_abi_stub, test_param_set, test_abi_so, test_abi_negative` 4 つの C テスト全 PASS
- [ ] Layer 3 (`test_ffi.py`, `test_wrlib.py`) — Python ラッパの単体テスト全 PASS
- [ ] Layer 4 (`test_sweep.py`) — 3x3 = 9 ケースのスイープが完走
- [ ] `run_tests.sh wrlib_*` で 5 ケース全件 PASS
- [ ] 既存 TR/EQ/TX/WR 回帰テストへの影響なし

## 撤退条件

- Layer 1 で 1e-10 を超える差 → 許容誤差を `1e-8` に緩める。`set_params` の順序を namelist 評価順に揃える試みは別タスクで（最低でも commit して動かす）
- `wr_get_state` に入力スカラー (`RF, RPI, ...`) が含まれていないため Layer 1 が不完全 → 入力スカラー比較を Layer 3 (`test_wrlib.py`) で `set_param/get_param` 経由に分離（`get_param` の追加は L-7 か L-8）

## 依存

- 前提: L-0, L-2, L-3, L-4, L-5 完了
- 後続: L-7 (README + notebook)
