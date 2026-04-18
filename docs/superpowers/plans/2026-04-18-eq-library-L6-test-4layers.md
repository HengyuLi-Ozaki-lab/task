# EQ ライブラリ化 Phase L-6: 4 層テスト整備 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-1〜L-5 で揃った `eq/libeqapi.so` と Python ラッパ `python/eqlib/` に対し、TR Phase L 設計 §8 と同じ **4 層テスト** を完備し、`test_run/run_tests.sh` から 1 コマンドで全層が走るようにする。Layer 1 (等価性) は `eq_iter01` / `eq_tst2` の L-0 baseline と `libeqapi.so` 経由出力が `1e-10` 以内で一致することを検証する。

**Architecture:** TR Phase L-6 / TI L-6 / FP L-6 と同型の 4 層に分けてテストを配置:

| Layer | 目的 | 実装場所 | 実行器 |
|---|---|---|---|
| **1. 等価性** | `Eqlib().run()` の `tr_state` 相当スナップショットが L-0 baseline と `1e-10` 一致 | `python/eqlib/tests/test_equivalence.py` | unittest + `compare_metrics.py` |
| **2. C ABI 単体** | 5 関数の単独動作 + pre-init / unknown name / double-finalize の negative | `eq/tests/c_abi/test_smoke.c` `test_param.c` `test_run.c` `test_negative.c` | `make -C eq/tests/c_abi test` |
| **3. Python ラッパ** | `Eqlib` クラス契約 (context manager, 二重 close, `set_params` 辞書一括) | `python/eqlib/tests/test_ffi.py` (L-5 実装済) + 補強 | unittest |
| **4. 網羅計算 smoke** | 3x3 パラメータグリッド (RR/BB/RIP) で `Eqlib` を 9 回回し state 漏れなし | `python/eqlib/tests/test_sweep.py` | unittest |

`run_tests.sh` の `test_definitions.conf` に 4 つの `eqlib_*` ケースを統合する。Python/C の dispatch は TR L-6 / TI L-6 で既に実装されている（`MODULE=python`、`MODULE=c`）前提でそのまま利用する。

**Tech Stack:** Python 3.8+ stdlib (`unittest`, `json`, `pathlib`)、C (gcc)、L-0 で確立した `compare_metrics.py` / `extract_eq_metrics.py`、`run_tests.sh` python/c dispatch。

**出典:**
- 設計: `docs/superpowers/specs/2026-04-17-tr-library-design.md` §8（テスト戦略 4 層）、§A.8（4 層採用根拠）
- 参照 plan: `docs/superpowers/plans/2026-04-18-tr-library-L6-test-4layers.md` (canonical template, merged)
- 参照 plan: `docs/superpowers/plans/2026-04-18-ti-library-L6-test-4layers.md` (python/c dispatch 実装)
- 参照 plan: `docs/superpowers/plans/2026-04-18-fp-library-L6-test-4layers.md` (_helpers.py schema)
- 参照 plan: `docs/superpowers/plans/2026-04-18-eq-library-L1-makefile-split.md` (CORE/GRAPHICS/MENU 分割方針、merged)
- 既存 tr fixture: `python/trlib/tests/fixtures/tr_iter01_params.py`, `tr_tst2_params.py`（L-6 参考用。eq 用は新規作成）

---

## Prerequisites

本 plan は以下が揃っていることを前提とする。未完了ならまずそちら:

- [ ] **L-4 完了:** `eq/libeqapi.so` がビルド可能（`cd eq && make libeqapi.so` が成功、`nm -D libeqapi.so | grep " T eq_"` で 5 関数 `eq_init / eq_run / eq_set_param / eq_get_state / eq_finalize` が露出）。
- [ ] **L-5 完了:** `python/eqlib/{__init__.py,_ffi.py,state.py,errors.py,eqlib.py}` が実装され、`from eqlib import Eqlib` が import 可能。`PYTHONPATH=python python3 -c "from eqlib import Eqlib"` が通る。
- [ ] **L-0 baseline:** `test_run/baselines/eq_iter01/metrics.json`, `test_run/baselines/eq_tst2/metrics.json` が存在。スキーマは `extract_eq_metrics.py` の出力と一致（top-level 次元キー + `scalars` + `profile`）。
- [ ] **TR L-6 merged:** `run_tests.sh` に `MODULE=python` と `MODULE=c` の dispatch が入っている。未マージなら本 plan の Task 6 で diff だけ適用する（ただし衝突回避のため、できれば tr L-6 のマージを先行）。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/eqlib/tests/fixtures/__init__.py` | 新規 | fixture パッケージマーカ |
| `python/eqlib/tests/fixtures/eq_iter01_params.py` | 新規 | `eq.ITER01.in` の namelist を Python 辞書化 |
| `python/eqlib/tests/fixtures/eq_tst2_params.py` | 新規 | `eq.TST-2.in` の namelist を Python 辞書化 |
| `python/eqlib/tests/_helpers.py` | 新規 | `load_baseline()` / `compare_to_baseline()` (fp の `_helpers.py` を eq スキーマに合わせて転用) |
| `python/eqlib/tests/test_equivalence.py` | 新規 | Layer 1: `eq_iter01`, `eq_tst2` 2 ケース vs baseline `1e-10` |
| `python/eqlib/tests/test_sweep.py` | 新規 | Layer 4: RR/BB/RIP 3x3 sweep smoke |
| `eq/tests/c_abi/test_smoke.c` | 新規 | Layer 2: `eq_init → get_state → set_param → finalize` の 4 関数 TR_OK 確認 |
| `eq/tests/c_abi/test_param.c` | 新規 | Layer 2: `eq_set_param` に対する既知 name/配列添字/未登録 name の返り値分岐 |
| `eq/tests/c_abi/test_run.c` | 新規 | Layer 2: `eq_init + set_param + run + get_state` で数値が変化すること |
| `eq/tests/c_abi/test_negative.c` | 新規 | Layer 2 negative: pre-init 呼び出し / unknown name / invalid array index / double-finalize (mirrors `tr/tests/c_abi/test_negative.c`) |
| `eq/tests/c_abi/Makefile` | 新規 or 修正 | 上記 4 テストを build + `make test` ターゲットで一括実行 |
| `test_run/test_definitions.conf` | 修正 | `eqlib_c_abi`, `eqlib_ffi`, `eqlib_equivalence`, `eqlib_sweep` の 4 ケース追加 |
| `test_run/run_tests.sh` | 修正 (必要時のみ) | eq 固有の `mod_env`（`EQ_REGRESS_DUMP=1` 等）が必要なら追加。TR L-6 導入済の python/c dispatch 自体は再利用 |

**方針:**
- **namelist 入力の取り込み** は fp/ti と同じく **Python 辞書 fixture** を採用（依存追加なし）。`eq.ITER01.in` の `&EQ/` ブロックを一字一句写す（差異が baseline 不一致を生む）。1 週間 iteration しても合わない場合のみ `f90nml` を導入する撤退パス（設計書 §11）。
- **UNREGISTERED_KEYS の概念:** fixture 辞書には、`eq_param_registry.f90` に L-3 でまだ登録されていない namelist 変数も **列挙だけしておく** (例: `UNREGISTERED_KEYS = ["MDLEQF", "MDLEQQ", ...]`)。`apply()` 関数は L-3 登録済の key だけ `set_param` し、未登録 key は skip + warning を発する。こうすることで:
  - 将来 L-3+ で CASE を追加した際に fixture 側の変更を最小化できる
  - どの変数が「namelist には出るが registry 未露出」なのかが fixture から一覧できる（将来の registry 拡張 TODO リスト）
- Layer 4 は smoke のみ。物理妥当性は範囲外。
- `run_tests.sh` は TR L-6 / TI L-6 で python/c dispatch が既に入っているため、本 plan では **新規 diff は原則なし**。eq 固有の `EQ_REGRESS_DUMP` を Fortran 側で実装していて Layer 1 でそれが必要なら `mod_env` 分岐に 1 行追加する程度。

---

## Task 1: ブランチ作成と前提確認

- [ ] **Step 1: ブランチ作成**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git fetch origin develop
git checkout -b feature/eq-library-L6-test-4layers origin/develop
```

- [ ] **Step 2: 依存物のビルド確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private/eq
make libs_pic 2>&1 | tail -3     # 依存ライブラリの PIC build
make libeqapi.so 2>&1 | tail -3
nm -D libeqapi.so | grep " T eq_" | sort
PYTHONPATH=/home/k-yoshimi/program/task-private/python python3 -c "from eqlib import Eqlib; print('OK')"
```
Expected: 5 関数（`eq_init/eq_run/eq_set_param/eq_get_state/eq_finalize`）が T で出る、`Eqlib` import 成功。

- [ ] **Step 3: 既存 eq 回帰が green**

Run:
```bash
cd /home/k-yoshimi/program/task-private/test_run
./run_tests.sh eq_iter01 eq_tst2 2>&1 | tail -10
```
Expected: 2/2 PASS（L-0 baseline 基準）。

---

## Task 2: 共通 helper `_helpers.py`

**Files:**
- Create: `python/eqlib/tests/_helpers.py`

**目的:** L-0 の `test_run/baselines/eq_*/metrics.json` をロードし、`Eqlib.get_state()` の返り値と比較する関数群。`fp/tests/_helpers.py` の schema contract を eq スキーマに合わせて転用する。

- [ ] **Step 1: ヘルパ本体**

作成: `python/eqlib/tests/_helpers.py`

```python
"""Internal helpers for eqlib tests.

Schema contract (must match L-0 `extract_eq_metrics.py` output):
    {
        "NRMAX": int, "NTHMAX": int, "NSUMAX": int, "NRGMAX": int, "NSGMAX": int,
        "scalars": {"PSITA": float, "RIP0": float, "BB0": float,
                    "VOLAVP": float, "AREAAVP": float, ...},
        "profile": [
            {"NR": int, "PSI": float, "QPS": float, "TTS": float,
             "PPS": float, "RHO": float, "VPS": float, "AVRR2": float, ...},
            ...  # length = NRMAX
        ],
    }

Exact scalar/profile field names depend on L-0's extract_eq_metrics.py; adjust
EXPECTED_* whitelists below if that script changes.
"""
import json
import math
from pathlib import Path
from typing import Tuple


REPO_ROOT = Path(__file__).resolve().parents[3]
BASELINES_DIR = REPO_ROOT / "test_run" / "baselines"

# Field whitelists, kept in sync with extract_eq_metrics.py (L-0).
EXPECTED_INT_KEYS = {"NRMAX", "NTHMAX", "NSUMAX"}
EXPECTED_SCALAR_KEYS = {"PSITA", "RIP0", "BB0"}
EXPECTED_PROFILE_FIELDS = ("PSI", "QPS", "TTS", "PPS", "RHO")


def load_baseline(test_name: str) -> dict:
    """Load test_run/baselines/<test_name>/metrics.json (Phase L-0 output).

    Raises FileNotFoundError / KeyError with a clear message on mismatch.
    """
    p = BASELINES_DIR / test_name / "metrics.json"
    if not p.exists():
        raise FileNotFoundError(
            f"baseline not found: {p}. Run L-0 baseline generation first "
            f"(extract_eq_metrics.py)."
        )
    data = json.loads(p.read_text())
    missing = EXPECTED_INT_KEYS - data.keys()
    if missing:
        raise KeyError(
            f"baseline {p} is missing int keys {sorted(missing)}; "
            f"regenerate via test_run/scripts/extract_eq_metrics.py (L-0)"
        )
    if "scalars" not in data or "profile" not in data:
        raise KeyError(
            f"baseline {p} is missing top-level 'scalars' or 'profile'"
        )
    return data


def _rel_err(a: float, b: float) -> float:
    denom = max(abs(a), abs(b), 1e-300)
    return abs(a - b) / denom


def compare_to_baseline(state, baseline: dict, tol: float = 1e-10) -> Tuple[bool, list]:
    """Compare an EqState (Eqlib.get_state()) vs baseline metrics dict.

    Returns (ok, errors).
    """
    errors = []

    # dimensions
    if state.nrmax != baseline["NRMAX"]:
        errors.append(f"NRMAX mismatch: {state.nrmax} vs {baseline['NRMAX']}")
    if hasattr(state, "nthmax") and state.nthmax != baseline["NTHMAX"]:
        errors.append(f"NTHMAX mismatch: {state.nthmax} vs {baseline['NTHMAX']}")
    if errors:
        return False, errors

    # scalars
    for k in EXPECTED_SCALAR_KEYS:
        if k not in baseline.get("scalars", {}):
            continue
        bv = float(baseline["scalars"][k])
        if not hasattr(state, k):
            errors.append(f"state missing scalar '{k}'")
            continue
        av = float(getattr(state, k))
        if math.isnan(bv) or math.isnan(av):
            errors.append(f"{k} NaN: baseline={bv} actual={av}")
        elif _rel_err(bv, av) > tol:
            errors.append(f"{k}: baseline={bv!r} actual={av!r} "
                          f"rel_err={_rel_err(bv, av):.3e} > tol={tol:.3e}")

    # profile
    baseline_by_nr = {int(r["NR"]): r for r in baseline.get("profile", [])}
    for nr_idx in range(state.nrmax):
        nr_key = nr_idx + 1
        br = baseline_by_nr.get(nr_key)
        if br is None:
            errors.append(f"missing baseline profile row at NR={nr_key}")
            continue
        for field in EXPECTED_PROFILE_FIELDS:
            if field not in br:
                continue
            if not hasattr(state, field):
                errors.append(f"state missing profile field '{field}'")
                continue
            bv = float(br[field])
            av = float(getattr(state, field)[nr_idx])
            if _rel_err(bv, av) > tol:
                errors.append(f"{field}[NR={nr_key}]: baseline={bv!r} "
                              f"actual={av!r} rel_err={_rel_err(bv, av):.3e}")
    return (not errors), errors
```

- [ ] **Step 2: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git add python/eqlib/tests/_helpers.py
git commit -m "test(eq): add _helpers.py for baseline loading and comparison"
```

---

## Task 3: Layer 1 fixture — namelist 辞書 + UNREGISTERED_KEYS

**Files:**
- Create: `python/eqlib/tests/fixtures/__init__.py` (空)
- Create: `python/eqlib/tests/fixtures/eq_iter01_params.py`
- Create: `python/eqlib/tests/fixtures/eq_tst2_params.py`

- [ ] **Step 1: ITER01 fixture**

作成: `python/eqlib/tests/fixtures/eq_iter01_params.py`

```python
"""EQ ITER01 parameters mirroring eq/in/eq.ITER01.in (`&EQ/` block).

Edit cautiously: changing values invalidates Layer 1 equivalence.

UNREGISTERED_KEYS lists namelist variables that are present in the input
file but not yet exposed through `eq_param_registry.f90`. `apply()` skips
them with a warning; add the CASE to the registry (L-3 extension) to
enable them here.
"""
import warnings

# Keys registered in eq_param_registry.f90 as of L-3.
EQ_ITER01_PARAMS = {
    # geometry
    "RR":    6.2,
    "RA":    2.0,
    "RKAP":  1.7,
    "RDLT":  0.33,
    "BB":    5.3,
    "RIP":  15.0,
    # profile shape
    "PROFR1": 2.0,  "PROFR2": 1.0,
    "PROFPP": 2.0,
    "PROFTT": 2.0,
    # grid
    "NRMAX":  51,
    "NTHMAX": 65,
    "NSUMAX": 20,
    # equilibrium solver
    "MDLEQF": 5,
    "MDLEQN": 0,
}

# Array elements (if any) — append `NAME[i]` style keys with 1-origin index.
EQ_ITER01_ARRAYS = {
    # e.g. "RHOMIN": [0.0, 0.5]  →  keys RHOMIN[1], RHOMIN[2]
}

# Namelist variables present in eq.ITER01.in but NOT yet in the registry.
# Track them here so a future L-3 extension (adding the CASE entry in
# eq_param_registry.f90) automatically becomes usable from fixtures.
UNREGISTERED_KEYS = [
    # e.g. "MDLEQQ",  "MDLEQC",  "MDLEQZ",  "KNAMEQ",
]


def apply(eq) -> None:
    """Apply ITER01 parameters to an Eqlib instance.

    Silently skips keys listed in UNREGISTERED_KEYS; emits a warning only
    if Eqlib reports EqlibParamError for keys we expected to work.
    """
    from eqlib import EqlibParamError  # local import to avoid hard dep at import time

    for k, v in EQ_ITER01_PARAMS.items():
        if k in UNREGISTERED_KEYS:
            continue
        try:
            eq.set_param(k, v)
        except EqlibParamError as exc:
            warnings.warn(
                f"eq_iter01 fixture: {k} not registered yet: {exc}; "
                f"move it to UNREGISTERED_KEYS or extend eq_param_registry.f90"
            )
    for name, arr in EQ_ITER01_ARRAYS.items():
        for i, v in enumerate(arr, start=1):
            if f"{name}[{i}]" in UNREGISTERED_KEYS:
                continue
            try:
                eq.set_param(f"{name}[{i}]", v)
            except EqlibParamError as exc:
                warnings.warn(f"eq_iter01 fixture: {name}[{i}] not registered: {exc}")
```

- [ ] **Step 2: TST-2 fixture**

作成: `python/eqlib/tests/fixtures/eq_tst2_params.py`

同上。`eq/in/eq.TST-2.in` を見て値を写す。主要パラメータ例:

```python
"""EQ TST-2 parameters mirroring eq/in/eq.TST-2.in."""
import warnings

EQ_TST2_PARAMS = {
    "RR":   0.38,
    "RA":   0.25,
    "RKAP": 1.7,
    "RDLT": 0.3,
    "BB":   0.3,
    "RIP":  0.2,
    "NRMAX":  51,
    "NTHMAX": 65,
    "MDLEQF": 5,
    # …populate from eq.TST-2.in
}
EQ_TST2_ARRAYS = {}
UNREGISTERED_KEYS = []

def apply(eq) -> None:
    from eqlib import EqlibParamError
    for k, v in EQ_TST2_PARAMS.items():
        if k in UNREGISTERED_KEYS: continue
        try: eq.set_param(k, v)
        except EqlibParamError as exc:
            warnings.warn(f"eq_tst2: {k} unregistered: {exc}")
    for name, arr in EQ_TST2_ARRAYS.items():
        for i, v in enumerate(arr, start=1):
            try: eq.set_param(f"{name}[{i}]", v)
            except EqlibParamError: pass
```

- [ ] **Step 3: fixtures/__init__.py**

Run:
```bash
: > /home/k-yoshimi/program/task-private/python/eqlib/tests/fixtures/__init__.py
```

- [ ] **Step 4: コミット**

Run:
```bash
git add python/eqlib/tests/fixtures/
git commit -m "test(eq): namelist fixture dicts for ITER01 and TST-2 (L-6)"
```

---

## Task 4: Layer 1 等価性テスト `test_equivalence.py`

**Files:**
- Create: `python/eqlib/tests/test_equivalence.py`

- [ ] **Step 1: テスト本体**

作成: `python/eqlib/tests/test_equivalence.py`

```python
"""Phase L-6 Layer 1: Eqlib output vs eq_iter01 / eq_tst2 L-0 baselines.

Tolerance 1e-10 mirrors TR / FP / TI L-6. If drift exceeds this, either:
  - extend the fixture dict to cover a missing parameter, or
  - extend eq_param_registry.f90 with a new CASE entry (L-3 follow-up).
"""
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LIBEQAPI = REPO / "eq" / "libeqapi.so"


@unittest.skipUnless(LIBEQAPI.exists(), "libeqapi.so not built")
class TestEquivalence(unittest.TestCase):

    def _run_case(self, apply_fn, ntmax: int = 1):
        from eqlib import Eqlib
        with Eqlib() as eq:
            apply_fn(eq)
            eq.run(ntmax=ntmax)
            return eq.get_state()

    def test_eq_iter01(self):
        from eqlib.tests._helpers import load_baseline, compare_to_baseline
        from eqlib.tests.fixtures.eq_iter01_params import apply
        baseline = load_baseline("eq_iter01")
        state = self._run_case(apply, ntmax=1)
        ok, errs = compare_to_baseline(state, baseline, tol=1e-10)
        if not ok:
            head = "\n  ".join(errs[:10])
            self.fail(f"eq_iter01 drift ({len(errs)} errors):\n  {head}")

    def test_eq_tst2(self):
        from eqlib.tests._helpers import load_baseline, compare_to_baseline
        from eqlib.tests.fixtures.eq_tst2_params import apply
        baseline = load_baseline("eq_tst2")
        state = self._run_case(apply, ntmax=1)
        ok, errs = compare_to_baseline(state, baseline, tol=1e-10)
        if not ok:
            head = "\n  ".join(errs[:10])
            self.fail(f"eq_tst2 drift ({len(errs)} errors):\n  {head}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 実行**

Run:
```bash
cd /home/k-yoshimi/program/task-private
PYTHONPATH=python python3 -m unittest eqlib.tests.test_equivalence -v 2>&1 | tail -30
```
Expected: 2 tests PASS。

失敗時のデバッグ:
1. エラーメッセージから drift フィールドを特定
2. fixture に該当パラメータ追加 or registry 未登録なら L-3 追加 PR
3. 許容を `1e-8` に一時緩和して drift 量把握（本番 commit は `1e-10` を維持）

- [ ] **Step 3: コミット**

Run:
```bash
git add python/eqlib/tests/test_equivalence.py
git commit -m "test(eq): Layer 1 equivalence vs eq_iter01/eq_tst2 L-0 baselines"
```

---

## Task 5: Layer 2 C ABI 4 本

**Files:**
- Create: `eq/tests/c_abi/test_smoke.c`
- Create: `eq/tests/c_abi/test_param.c`
- Create: `eq/tests/c_abi/test_run.c`
- Create: `eq/tests/c_abi/test_negative.c`
- Create or Modify: `eq/tests/c_abi/Makefile`

TR L-6 の smoke/param/run と同じ骨格。さらに `test_negative.c` で:
  1. `eq_set_param` を `eq_init` より前に呼ぶと `EQ_ERR_NOT_INIT` 相当が返る
  2. 不明な name で `EQ_ERR_INVALID`
  3. 無効な配列添字 (`"PA[-1]"`, `"PA[9999]"`) で `EQ_ERR_INVALID`
  4. `eq_finalize` を連続 2 回呼んでも 2 回目は冪等に成功 (または明確な `EQ_ERR_NOT_INIT`)

- [ ] **Step 1: test_smoke.c**

作成: `eq/tests/c_abi/test_smoke.c`

```c
/* Phase L-6 Layer 2 smoke: verify the 5 eq_api entry points return EQ_OK. */
#include <stdio.h>
#include "eq_api.h"

static int expect_ok(const char *name, int rc) {
    if (rc == EQ_OK) { printf("OK  %-14s returned EQ_OK\n", name); return 0; }
    fprintf(stderr, "FAIL %s returned %d, expected EQ_OK (=%d)\n", name, rc, EQ_OK);
    return 1;
}

int main(void) {
    int f = 0;
    eq_state_t st;
    f += expect_ok("eq_init",       eq_init());
    f += expect_ok("eq_get_state",  eq_get_state(&st));
    f += expect_ok("eq_set_param",  eq_set_param("RR", 6.2));
    f += expect_ok("eq_run",        eq_run(1));
    f += expect_ok("eq_finalize",   eq_finalize());
    if (f) { fprintf(stderr, "%d failures\n", f); return 1; }
    printf("Phase L-6 Layer 2 smoke OK: 5/5 entry points returned EQ_OK\n");
    return 0;
}
```

- [ ] **Step 2: test_param.c**

作成: `eq/tests/c_abi/test_param.c`

```c
/* Phase L-6 Layer 2 param dispatch: check scalar, array subscript, and
 * unknown-name paths of eq_set_param.
 */
#include <stdio.h>
#include "eq_api.h"

#define EXPECT(cond, msg) do { \
    if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); return 1; } \
} while (0)

int main(void) {
    EXPECT(eq_init() == EQ_OK, "eq_init");

    /* scalar set */
    EXPECT(eq_set_param("RR", 6.2)   == EQ_OK, "set RR");
    EXPECT(eq_set_param("BB", 5.3)   == EQ_OK, "set BB");
    EXPECT(eq_set_param("RIP", 15.0) == EQ_OK, "set RIP");

    /* array subscript (if eqlib registers arrays; adjust to real names) */
    /* EXPECT(eq_set_param("PA[1]", 1.0) == EQ_OK, "set PA[1]"); */

    /* unknown name -> invalid */
    EXPECT(eq_set_param("NO_SUCH_PARAM", 1.0) == EQ_ERR_INVALID,
           "unknown name must return EQ_ERR_INVALID");

    EXPECT(eq_finalize() == EQ_OK, "eq_finalize");
    printf("L-6 Layer 2 param dispatch OK\n");
    return 0;
}
```

- [ ] **Step 3: test_run.c**

作成: `eq/tests/c_abi/test_run.c`

```c
/* Phase L-6 Layer 2 run: init + set_param + run + get_state, verify that
 * eq_run changes at least one scalar from its post-init default.
 */
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "eq_api.h"

int main(void) {
    eq_state_t before, after;
    if (eq_init() != EQ_OK) return 10;
    if (eq_get_state(&before) != EQ_OK) return 11;

    if (eq_set_param("RR", 6.2)  != EQ_OK) return 12;
    if (eq_set_param("BB", 5.3)  != EQ_OK) return 13;
    if (eq_set_param("RIP", 15.0) != EQ_OK) return 14;

    if (eq_run(1) != EQ_OK) return 20;
    if (eq_get_state(&after) != EQ_OK) return 21;

    /* Sanity: the run must have populated psi / q profiles. */
    if (after.nrmax <= 0) { fprintf(stderr, "nrmax=%d\n", after.nrmax); return 30; }
    /* further content checks depend on eq_state_t layout */

    if (eq_finalize() != EQ_OK) return 40;
    printf("L-6 Layer 2 run OK (nrmax=%d)\n", after.nrmax);
    return 0;
}
```

- [ ] **Step 4: test_negative.c**

作成: `eq/tests/c_abi/test_negative.c` (mirrors `tr/tests/c_abi/test_negative.c` planned template)

```c
/* Phase L-6 Layer 2 negative: pre-init calls, unknown/invalid names,
 * double-finalize. All must return documented error codes without SEGV.
 */
#include <stdio.h>
#include "eq_api.h"

#define EXPECT_EQ(actual, expected, msg) do { \
    if ((actual) != (expected)) { \
        fprintf(stderr, "FAIL: %s (got %d, expected %d)\n", msg, (int)(actual), (int)(expected)); \
        return 1; \
    } \
} while (0)

int main(void) {
    eq_state_t st;

    /* 1. pre-init: every call but eq_init must report NOT_INIT. */
    EXPECT_EQ(eq_set_param("RR", 6.2), EQ_ERR_NOT_INIT, "set_param before init");
    EXPECT_EQ(eq_run(1),               EQ_ERR_NOT_INIT, "eq_run before init");
    EXPECT_EQ(eq_get_state(&st),       EQ_ERR_NOT_INIT, "eq_get_state before init");
    EXPECT_EQ(eq_finalize(),           EQ_ERR_NOT_INIT, "eq_finalize before init");

    EXPECT_EQ(eq_init(), EQ_OK, "eq_init");

    /* 2. unknown name after init */
    EXPECT_EQ(eq_set_param("ZZZ_UNKNOWN", 1.0), EQ_ERR_INVALID, "unknown name");

    /* 3. invalid array index */
    EXPECT_EQ(eq_set_param("RR[-1]", 1.0), EQ_ERR_INVALID, "negative index");
    EXPECT_EQ(eq_set_param("RR[9999]", 1.0), EQ_ERR_INVALID, "out-of-range index");

    /* 4. double-finalize: second call should be idempotent (OK) or report
     *    NOT_INIT. Either is acceptable as long as there's no crash. */
    EXPECT_EQ(eq_finalize(), EQ_OK, "first finalize");
    int rc2 = eq_finalize();
    if (rc2 != EQ_OK && rc2 != EQ_ERR_NOT_INIT) {
        fprintf(stderr, "FAIL: double-finalize returned %d\n", rc2);
        return 1;
    }

    printf("L-6 Layer 2 negative OK\n");
    return 0;
}
```

- [ ] **Step 5: Makefile**

作成 or 修正: `eq/tests/c_abi/Makefile` (fp/ti のものを参考に)

```makefile
# Phase L-6 Layer 2 tests for eq library
EQ_DIR     := ../..
LIBEQAPI   := $(EQ_DIR)/libeqapi.so
CC         ?= gcc
CFLAGS     ?= -O0 -g -Wall
LDFLAGS    := -L$(EQ_DIR) -leqapi -Wl,-rpath,$(EQ_DIR)

TESTS := test_smoke test_param test_run test_negative

all: $(TESTS)

test_smoke: test_smoke.c $(EQ_DIR)/eq_api.h $(LIBEQAPI)
	$(CC) $(CFLAGS) -I$(EQ_DIR) $< $(LDFLAGS) -o $@

test_param: test_param.c $(EQ_DIR)/eq_api.h $(LIBEQAPI)
	$(CC) $(CFLAGS) -I$(EQ_DIR) $< $(LDFLAGS) -o $@

test_run: test_run.c $(EQ_DIR)/eq_api.h $(LIBEQAPI)
	$(CC) $(CFLAGS) -I$(EQ_DIR) $< $(LDFLAGS) -o $@

test_negative: test_negative.c $(EQ_DIR)/eq_api.h $(LIBEQAPI)
	$(CC) $(CFLAGS) -I$(EQ_DIR) $< $(LDFLAGS) -o $@

.PHONY: test clean all
test: $(TESTS)
	./test_smoke
	./test_param
	./test_run
	./test_negative

clean:
	rm -f $(TESTS)
```

- [ ] **Step 6: 実行**

Run:
```bash
cd /home/k-yoshimi/program/task-private/eq/tests/c_abi
make clean && make test 2>&1 | tail -20
```
Expected: 4 本すべて `OK` で終わる。

- [ ] **Step 7: コミット**

Run:
```bash
git add eq/tests/c_abi/
git commit -m "test(eq): Layer 2 C ABI smoke/param/run/negative (L-6)"
```

---

## Task 6: Layer 4 sweep

**Files:**
- Create: `python/eqlib/tests/test_sweep.py`

- [ ] **Step 1: テスト本体**

作成: `python/eqlib/tests/test_sweep.py`

```python
"""Phase L-6 Layer 4: parameter sweep smoke (3x3 on RR/BB, with RIP).

Confirms that constructing/destructing Eqlib in a loop, with different
parameters each time, does not crash or leak global state. Physical
validity is NOT checked (out of scope per design §A.8).
"""
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LIBEQAPI = REPO / "eq" / "libeqapi.so"


@unittest.skipUnless(LIBEQAPI.exists(), "libeqapi.so not built")
class TestSweep(unittest.TestCase):

    def test_3x3_grid(self):
        from eqlib import Eqlib
        from eqlib.tests.fixtures.eq_iter01_params import apply as apply_iter01

        rr_values = [5.8, 6.2, 6.6]
        bb_values = [5.0, 5.3, 5.6]
        rip_value = 15.0
        results = []
        for rr in rr_values:
            for bb in bb_values:
                with Eqlib() as eq:
                    apply_iter01(eq)
                    eq.set_param("RR",  rr)
                    eq.set_param("BB",  bb)
                    eq.set_param("RIP", rip_value)
                    eq.run(ntmax=1)
                    state = eq.get_state()
                    results.append((rr, bb, state))
        self.assertEqual(len(results), 9)
        # Sanity: nrmax must be populated and equal across cells (no leak).
        nrmax0 = results[0][2].nrmax
        for rr, bb, st in results:
            self.assertEqual(st.nrmax, nrmax0,
                             f"nrmax leak at RR={rr} BB={bb}: {st.nrmax} vs {nrmax0}")
            self.assertGreater(st.nrmax, 0, f"RR={rr} BB={bb} nrmax=0")

    def test_rip_sweep_independent(self):
        """Vary RIP alone; all cells must complete and produce distinct PSITA."""
        from eqlib import Eqlib
        from eqlib.tests.fixtures.eq_iter01_params import apply as apply_iter01

        seen = []
        for rip in (12.0, 15.0, 18.0):
            with Eqlib() as eq:
                apply_iter01(eq)
                eq.set_param("RIP", rip)
                eq.run(ntmax=1)
                st = eq.get_state()
                if hasattr(st, "PSITA"):
                    seen.append(st.PSITA)
        # If PSITA is exposed, three distinct RIP should give three distinct values.
        if seen:
            self.assertEqual(len(set(seen)), len(seen),
                             f"PSITA did not vary with RIP: {seen}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 実行**

Run:
```bash
cd /home/k-yoshimi/program/task-private
PYTHONPATH=python python3 -m unittest eqlib.tests.test_sweep -v 2>&1 | tail -10
```
Expected: 2 tests PASS（所要 60〜120 秒）。

タイムアウト時: grid を 2x2 に縮小、`NRMAX` を小さく（fixture 側で sweep 用パラメータを別途用意）。

- [ ] **Step 3: コミット**

Run:
```bash
git add python/eqlib/tests/test_sweep.py
git commit -m "test(eq): Layer 4 3x3 sweep smoke over RR/BB/RIP (L-6)"
```

---

## Task 7: Layer 3 `test_ffi.py` 補強

**Files:**
- Modify: `python/eqlib/tests/test_ffi.py` (L-5 で作成済) — 追加テストを注入

以下を既存 `test_ffi.py` に追記:

- [ ] **Step 1: 契約テストの追加**

追記内容（クラスに追加する形で）:

```python
    def test_context_manager_double_close(self):
        from eqlib import Eqlib
        with Eqlib() as eq:
            eq.run(0)
        # explicit close after __exit__ must be a no-op, not an error
        eq.close()

    def test_set_params_bulk_dict(self):
        from eqlib import Eqlib
        with Eqlib() as eq:
            eq.set_params(RR=6.2, BB=5.3, RIP=15.0)

    def test_unknown_param_raises(self):
        from eqlib import Eqlib, EqlibParamError
        with Eqlib() as eq:
            with self.assertRaises(EqlibParamError):
                eq.set_param("DOES_NOT_EXIST", 1.0)

    def test_call_after_close_raises(self):
        from eqlib import Eqlib, EqlibError
        eq = Eqlib()
        eq.close()
        with self.assertRaises(EqlibError):
            eq.run(1)
```

- [ ] **Step 2: 実行**

Run:
```bash
cd /home/k-yoshimi/program/task-private
PYTHONPATH=python python3 -m unittest eqlib.tests.test_ffi -v 2>&1 | tail -10
```
Expected: 既存 + 新規すべて PASS。

- [ ] **Step 3: コミット**

Run:
```bash
git add python/eqlib/tests/test_ffi.py
git commit -m "test(eq): reinforce Layer 3 Eqlib contract tests (L-6)"
```

---

## Task 8: `test_definitions.conf` + run_tests.sh 統合

**Files:**
- Modify: `test_run/test_definitions.conf`
- Modify (optional): `test_run/run_tests.sh`

TR L-6 / TI L-6 で python/c dispatch は既に統合済の前提。本 plan は **conf への 4 行追加のみ**（dispatch は再利用）。万一 tr L-6 がまだマージされていない場合は、tr L-6 Task 6 と同じ diff（`MODULE=python`/`MODULE=c` 分岐）を同一コミットに含める（コンフィグだけ先に入れると `get_binary()` で空文字となり SKIP 扱いになり regression）。

- [ ] **Step 1: conf 追加**

`test_run/test_definitions.conf` 末尾に追加:

```
# =============================================================================
# EQ Library Phase L-6: 4-layer tests
# =============================================================================
eqlib_c_abi:c:@../eq/tests/c_abi/test_smoke:none:60:Layer 2 C ABI smoke
eqlib_c_abi_full:c:@../eq/tests/c_abi/test_negative:none:60:Layer 2 C ABI negative
eqlib_ffi:python:eqlib.tests.test_ffi:none:60:Layer 3 Eqlib contract
eqlib_equivalence:python:eqlib.tests.test_equivalence:eq_iter01,eq_tst2:300:Layer 1 equivalence (tol 1e-10)
eqlib_sweep:python:eqlib.tests.test_sweep:none:180:Layer 4 3x3 sweep smoke
```

注:
- `@../eq/tests/c_abi/test_smoke` は SCRIPT_DIR 相対 (`$SCRIPT_DIR/../eq/tests/c_abi/test_smoke`) に展開される（TI L-6 の `@..` 前置と同じ規約）。
- `eqlib_equivalence` の depends は既存 `eq_iter01,eq_tst2` を指定（baseline が先に生成されている保証のため）。

- [ ] **Step 2: eq 固有の mod_env (optional)**

Layer 1 で `eqregress.f90` のような high-precision dump が必要なら、`run_tests.sh` の `mod_env` 分岐に以下を追加:

```diff
     elif [[ "$module" == "ti" ]]; then
         mod_env=(env TI_REGRESS_DUMP=1)
+    elif [[ "$module" == "eq" ]]; then
+        mod_env=(env EQ_REGRESS_DUMP=1)
     fi
```

（本 plan の Layer 1 は baseline JSON 比較で完結するため不要。既存の eq binary 側で L-0 baseline 生成に必要だった場合のみ該当）

- [ ] **Step 3: ビルド前提のセットアップ**

Run:
```bash
cd /home/k-yoshimi/program/task-private
(cd eq && make libs_pic && make libeqapi.so) 2>&1 | tail -3
(cd eq/tests/c_abi && make all) 2>&1 | tail -3
```

- [ ] **Step 4: 実行確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private/test_run
./run_tests.sh eqlib_c_abi eqlib_c_abi_full eqlib_ffi eqlib_sweep eqlib_equivalence 2>&1 | tail -20
```
Expected: 5/5 PASS。

- [ ] **Step 5: 既存テストが壊れていないこと**

Run:
```bash
./run_tests.sh
```
Expected: 全テスト PASS（eq_iter01, eq_tst2, tr_*, tx_std, fp_*, ti_*, wr_*, eqlib_*）。

- [ ] **Step 6: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git add test_run/test_definitions.conf
# run_tests.sh に変更があれば同時に add
[ -n "$(git diff --stat test_run/run_tests.sh)" ] && git add test_run/run_tests.sh
git commit -m "ci(test_run): integrate eqlib_* 5 cases (L-6)"
```

---

## Task 9: PR 作成

- [ ] **Step 1: push**

Run:
```bash
git push -u origin feature/eq-library-L6-test-4layers
```

- [ ] **Step 2: PR**

Run:
```bash
gh pr create --base develop \
  --title "test(eq): Phase L-6 four-layer tests + run_tests.sh integration" \
  --body "Phase L-6: Layer 1 equivalence (eq_iter01/eq_tst2 vs L-0, tol 1e-10), Layer 2 C ABI (smoke/param/run/negative), Layer 3 Eqlib contract reinforced, Layer 4 RR/BB/RIP 3x3 sweep. 5 eqlib_* cases registered in test_definitions.conf. Design spec §8."
```

---

## Risk / Mitigation

| Risk | Mitigation |
|---|---|
| Layer 1 で `1e-10` を超える drift が出る | fixture に UNREGISTERED_KEYS を移す → L-3 にフォローアップ PR で CASE 追加。一時的に `1e-8` に緩和するオプションを `compare_to_baseline` に用意。**baseline 側は絶対に触らない** |
| `eq.ITER01.in` の namelist をひたすら写すコストが高い | 設計書 §11 代替案 (b): `pip install f90nml` を allow し `load_namelist_file()` ヘルパを作る。本 plan では一次 fixture 手書き、それでダメなら撤退パスとして採用 |
| `run_tests.sh` の python/c dispatch が未マージ | tr L-6 のマージを先行。もし独立実装するなら tr L-6 Task 6 Step 1+2 を **同一コミット**で投入（順序逆転で regression） |
| `eqlib_c_abi_full (test_negative)` が SEGV で落ちる | `eq_api.f90` の lifecycle ガード (`state_initialized` フラグ) を確認。L-2 に戻って init ガードを入れる |
| Layer 4 sweep が 3 分超 | grid を 2x2 に縮小。`NRMAX=31` 等 fixture 側で小型化 |
| `run_tests.sh` が既存 `eq_iter01`/`eq_tst2` を壊す | 本 plan は conf 追加のみで既存 MODULE=`eq` 分岐は一切触らない。push 前に必ず `./run_tests.sh eq_iter01 eq_tst2 tr_iter01` で確認 |
| `UNREGISTERED_KEYS` が肥大化して後から「どれを追加すべきか」不明になる | fixture に `# priority: high/low` コメントを併記、registry 拡張 PR で参照する |

## Testing strategy

**Pre-merge local:**
1. `make -C eq libs_pic && make -C eq libeqapi.so` が成功
2. `make -C eq/tests/c_abi test` が 4/4 PASS
3. `PYTHONPATH=python python3 -m unittest eqlib.tests -v` が全 PASS
4. `./run_tests.sh eqlib_*` が 5/5 PASS
5. `./run_tests.sh` 全体が PASS（regression なし）

**Per-layer自動化:**
- Layer 1: `compare_to_baseline()` で relative error `1e-10` 閾値
- Layer 2: exit 0 で PASS、stderr に `FAIL:` が出ないこと
- Layer 3: `unittest.TestCase.assertRaises` で例外契約
- Layer 4: `nrmax` の不変性 + 9 cells 完走

## 受け入れ基準

- [ ] `./run_tests.sh eqlib_c_abi eqlib_c_abi_full eqlib_ffi eqlib_sweep eqlib_equivalence` で 5/5 PASS
- [ ] Layer 1 `eqlib_equivalence` が `eq_iter01` + `eq_tst2` に対し `1e-10` 以内で一致
- [ ] Layer 2 C ABI テスト 4 本 (smoke/param/run/negative) が全 PASS
- [ ] Layer 3 `test_ffi.py` 契約テスト全 PASS
- [ ] Layer 4 `test_sweep.py` 3x3 sweep 完走（nrmax 不変）
- [ ] `./run_tests.sh` 全体で既存 eq/tr/tx/fp/ti/wr を含めて regression なし
- [ ] PR が develop にマージ可能（conflict なし）

## Deliverables checklist

- [ ] `python/eqlib/tests/_helpers.py`
- [ ] `python/eqlib/tests/fixtures/__init__.py`
- [ ] `python/eqlib/tests/fixtures/eq_iter01_params.py`（UNREGISTERED_KEYS 欄あり）
- [ ] `python/eqlib/tests/fixtures/eq_tst2_params.py`（UNREGISTERED_KEYS 欄あり）
- [ ] `python/eqlib/tests/test_equivalence.py` (2 tests)
- [ ] `python/eqlib/tests/test_sweep.py` (2 tests)
- [ ] `python/eqlib/tests/test_ffi.py` 補強（L-5 既存に 4 テスト追加）
- [ ] `eq/tests/c_abi/test_smoke.c`
- [ ] `eq/tests/c_abi/test_param.c`
- [ ] `eq/tests/c_abi/test_run.c`
- [ ] `eq/tests/c_abi/test_negative.c`
- [ ] `eq/tests/c_abi/Makefile`
- [ ] `test_run/test_definitions.conf` に `eqlib_*` 5 ケース
- [ ] (optional) `test_run/run_tests.sh` に `EQ_REGRESS_DUMP` env 分岐

## 依存

- 上流: L-4 (`libeqapi.so`) + L-5 (`python/eqlib/`) マージ済
- 後続: L-7 (ドキュメント) — 4 層テスト整備された状態で README / notebook / changelog を書く
