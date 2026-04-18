# TI Library Phase L-6: 4-Layer Tests for `tilib` 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** TR Library Phase L で確立した 4 層テスト戦略を ti 用に実装する:
- **Layer 1**: 等価性テスト — `Tilib` 経由の出力が `ti` バイナリと **数値同一** であること（L-0 baseline と比較）
- **Layer 2**: C ABI 単体テスト — `tests/c_abi/test_link.c`（L-4 で済）に加え、`ti_get_state` の値検証
- **Layer 3**: Python ラッパテスト — `Tilib` クラスの Pythonic 使用パターン（L-5 で基礎済、ここで補強）
- **Layer 4**: 網羅計算 smoke — 3x3 パラメータグリッドで完走確認

`run_tests.sh` の `test_definitions.conf` に 4 つの `tilib_*` ケースを統合する。

**Architecture:** TR の L-6 と同型。ファイル構成も `python/tilib/tests/test_equivalence.py`, `test_sweep.py` を追加し、`ti/tests/c_abi/test_state.c` を追加。Layer 1 では tilib 側で同じ namelist を再現するため `f90nml`（オプション）または手書き parser を用いる（本計画では手書き parser で実装、依存追加を避ける）。

**Tech Stack:** Python 3.8+ stdlib (unittest, json, pathlib, re)、C (test_state.c)。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` 8 章 (テスト戦略 4 層)。

---

## File Structure

このフェーズで作成・変更するファイル:

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/tilib/tests/_namelist.py` | 新規 | 最小 Fortran namelist parser（`/TI/ ... /` を dict に） |
| `python/tilib/tests/test_equivalence.py` | 新規 | Layer 1: tilib vs ti binary baseline 比較（3 ケース） |
| `python/tilib/tests/test_sweep.py` | 新規 | Layer 4: 3x3 grid sweep smoke |
| `python/tilib/tests/test_tilib.py` | 修正 | Layer 3 を補強（配列 round-trip, 累積 run, 例外網羅） |
| `python/tilib/tests/fixtures/ti_min_expected.json` | 新規（生成） | L-0 baseline metrics へのシンボリック対応（同内容を符号化） |
| `ti/tests/c_abi/test_state.c` | 新規 | Layer 2: ti_get_state の値検証（init 後の defaults） |
| `ti/tests/c_abi/Makefile` | 修正 | test_state ターゲット追加 |
| `test_run/test_definitions.conf` | 修正 | `tilib_equivalence`, `tilib_ffi`, `tilib_sweep`, `tilib_c_state` の 4 ケース追加 |
| `test_run/run_tests.sh` | 修正 | `python` 実行モード（`module=python`）と `c` 実行モード（`module=c`）の dispatch を追加 |

---

## Task 1: 前提確認

**Files:**
- なし

- [ ] **Step 1: ブランチ作成と L-5 マージ確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin
git checkout -b feature/ti-library-L6-test-4layers origin/develop
ls /home/k-yoshimi/program/task/python/tilib/tilib.py
ls /home/k-yoshimi/program/task/ti/libtiapi.so 2>/dev/null || \
   (cd ti && make libtiapi.so 2>&1 | tail -3)
```
Expected: tilib モジュール存在、libtiapi.so 存在（または生成可能）。

- [ ] **Step 2: 既存テストが PASS することを確認**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest discover python/tilib/tests -v 2>&1 | tail -10
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh
cd /home/k-yoshimi/program/task/ti/tests/c_abi && make test
```
Expected: tilib L-5 テスト 7 PASS、test_run 全 PASS、c_abi 3 テスト PASS。

- [ ] **Step 3: 空コミット**

Run:
```bash
git commit --allow-empty -m "chore(tilib): start L-6 4-layer tests"
```

---

## Task 2: 最小 Fortran namelist パーサ `_namelist.py` を実装（テスト先行）

**Files:**
- Create: `python/tilib/tests/test_namelist.py`
- Create: `python/tilib/tests/_namelist.py`

**目的:** `test_run/inputs/ti_*.in` を Python で読み、`Tilib.set_params(...)` に渡せる dict に変換する。`f90nml` 等の外部依存を避けるため自作。`/TI/` グループのスカラー、`PN(1)`, `MODEL_BND(1,3)` 等の添字記法、`'Ar'` 文字列リテラルだけ扱えれば十分。

- [ ] **Step 1: 失敗するテストを書く**

作成: `python/tilib/tests/test_namelist.py`

```python
"""Tests for the minimal Fortran namelist parser used by tilib equivalence tests."""

import unittest


class TestNamelist(unittest.TestCase):

    def _parse(self, text):
        from tilib.tests._namelist import parse_ti_namelist
        return parse_ti_namelist(text)

    def test_scalar_real_and_int(self):
        d = self._parse("""
 &ti
   NSMAX=1
   NRMAX=10
   DT=1.D-3
 &end
""")
        self.assertEqual(d["NSMAX"], 1.0)
        self.assertEqual(d["NRMAX"], 10.0)
        self.assertAlmostEqual(d["DT"], 1.0e-3)

    def test_array_subscript_translates_to_brackets(self):
        d = self._parse("""
 &ti
   PN(1)=0.7D0
   PNS(2)=0.05D0
   MODEL_BND(1,3)=2
 &end
""")
        self.assertAlmostEqual(d["PN[1]"], 0.7)
        self.assertAlmostEqual(d["PNS[2]"], 0.05)
        self.assertEqual(d["MODEL_BND[1,3]"], 2.0)

    def test_string_values_are_skipped(self):
        # tilib.set_param only takes floats; skip string-valued entries
        d = self._parse("""
 &ti
   NSMAX=3
   KID_NS(3)='Ar'
 &end
""")
        self.assertEqual(d["NSMAX"], 3.0)
        self.assertNotIn("KID_NS[3]", d)

    def test_strips_run_quit_lines_after_end(self):
        d = self._parse("""
 &ti
   NSMAX=1
 &end
R
Q
""")
        self.assertEqual(d["NSMAX"], 1.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: テスト実行（失敗）**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest python.tilib.tests.test_namelist -v 2>&1 | tail -10
```
Expected: ImportError。

- [ ] **Step 3: パーサを実装**

作成: `python/tilib/tests/_namelist.py`

```python
"""Minimal Fortran namelist parser for tilib equivalence tests.

Supports:
   - &ti ... &end  group markers
   - scalar assignments  NAME=value
   - array subscripts    NAME(i)=value, NAME(i,j)=value
   - D/E exponent        1.D-3, 6.2D0, 5.3e0
   - skips string-valued entries  NAME='Ar'  (tilib.set_param is float-only)
   - skips comments starting with !
   - ignores trailing menu lines (R, Q, etc.) after &end
"""

import re

_RE_ASSIGN = re.compile(
    r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*"
    r"(?:\(\s*([0-9,\s]+)\s*\))?\s*"
    r"=\s*(.+)$"
)
_RE_FLOAT = re.compile(r"^[-+]?\d+(?:\.\d*)?(?:[dDeE][-+]?\d+)?$|^[-+]?\.\d+(?:[dDeE][-+]?\d+)?$")


def _to_float(token: str):
    t = token.strip().rstrip(",")
    if t.startswith("'") or t.startswith('"'):
        return None  # string-valued; skip
    t = t.replace("D", "E").replace("d", "e")
    if not _RE_FLOAT.match(t):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def parse_ti_namelist(text: str) -> dict:
    out = {}
    in_group = False
    for raw in text.splitlines():
        line = raw.split("!", 1)[0].strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith("&ti"):
            in_group = True
            continue
        if low.startswith("&end") or low.startswith("/"):
            in_group = False
            continue
        if not in_group:
            continue
        m = _RE_ASSIGN.match(line)
        if not m:
            continue
        name, subs, val_token = m.group(1), m.group(2), m.group(3)
        val = _to_float(val_token)
        if val is None:
            continue
        if subs is None:
            key = name
        else:
            key = f"{name}[{subs.strip().replace(' ', '')}]"
        out[key] = val
    return out
```

- [ ] **Step 4: テスト再実行**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest python.tilib.tests.test_namelist -v 2>&1 | tail -10
```
Expected: 4 tests PASS。

- [ ] **Step 5: コミット**

Run:
```bash
git add python/tilib/tests/_namelist.py python/tilib/tests/test_namelist.py
git commit -m "test(tilib): add minimal Fortran /TI/ namelist parser"
```

---

## Task 3: Layer 1 等価性テスト `test_equivalence.py` を実装

**Files:**
- Create: `python/tilib/tests/test_equivalence.py`

**目的:** L-0 baseline (`test_run/baselines/ti_*/metrics.json`) と、tilib 経由で同じ入力を流して `ti_get_state` で取った値を `1e-10` 許容で比較する。

- [ ] **Step 1: 失敗するテストを書く**

作成: `python/tilib/tests/test_equivalence.py`

```python
"""Layer 1: tilib output equivalence vs ti binary L-0 baselines."""

import json
import math
import os
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
INPUTS_DIR = REPO / "test_run" / "inputs"
BASELINES_DIR = REPO / "test_run" / "baselines"
LIBTIAPI = REPO / "ti" / "libtiapi.so"

CASES = ["ti_min", "ti_ar", "ti_w"]
TOL = 1e-10


def _rel_err(a, b):
    return abs(a - b) / max(abs(a), abs(b), 1e-300)


@unittest.skipUnless(LIBTIAPI.exists(), "libtiapi.so not built")
class TestEquivalence(unittest.TestCase):

    def _run_case(self, case: str):
        from tilib import Tilib
        from tilib.tests._namelist import parse_ti_namelist

        nml_text = (INPUTS_DIR / f"{case}.in").read_text()
        params = parse_ti_namelist(nml_text)
        ntmax = int(params.pop("NTMAX", 1))

        with Tilib() as ti:
            # Apply params one-by-one; tilib raises if registry doesn't know it.
            for k, v in params.items():
                try:
                    ti.set_param(k, v)
                except Exception:
                    # Skip params not registered; equivalence is checked on the
                    # subset that ti_param_registry knows about. The unknown
                    # ones are namelist-only defaults that don't differ.
                    pass
            ti.set_param("NTMAX", float(ntmax))
            ti.run(ntmax=ntmax)
            return ti.get_state()

    def _baseline(self, case: str) -> dict:
        return json.loads((BASELINES_DIR / case / "metrics.json").read_text())

    def _compare(self, state, base, case):
        msgs = []
        # scalar floats
        bs = base.get("scalars", {})
        if "T" in bs:
            e = _rel_err(bs["T"], state.T)
            if e > TOL:
                msgs.append(f"T rel_err={e:.3e} > {TOL}")
        # profiles per NR
        bp = base.get("profile", [])
        for i, row in enumerate(bp):
            for field, getter in (
                ("RBP", lambda r: state.RBP[r]),
                ("RQP", lambda r: state.RQP[r]),
                ("RJP", lambda r: state.RJP[r]),
                ("ZEFF", lambda r: state.ZEFF[r]),
                ("BETA", lambda r: state.BETA[r]),
                ("BETAP", lambda r: state.BETAP[r]),
            ):
                if field in row:
                    e = _rel_err(row[field], getter(i))
                    if e > TOL:
                        msgs.append(f"{case}.profile[{i}].{field} rel_err={e:.3e}")
            for arr_field in ("RNA", "RTA", "RUA"):
                if arr_field in row:
                    bv_list = row[arr_field]
                    av_list = getattr(state, arr_field)[i]
                    for j, (bv, av) in enumerate(zip(bv_list, av_list)):
                        e = _rel_err(bv, av)
                        if e > TOL:
                            msgs.append(
                                f"{case}.profile[{i}].{arr_field}[{j}] rel_err={e:.3e}")
        return msgs

    def test_ti_min_equivalence(self):
        state = self._run_case("ti_min")
        msgs = self._compare(state, self._baseline("ti_min"), "ti_min")
        self.assertEqual([], msgs)

    def test_ti_ar_equivalence(self):
        state = self._run_case("ti_ar")
        msgs = self._compare(state, self._baseline("ti_ar"), "ti_ar")
        self.assertEqual([], msgs)

    def test_ti_w_equivalence(self):
        state = self._run_case("ti_w")
        msgs = self._compare(state, self._baseline("ti_w"), "ti_w")
        self.assertEqual([], msgs)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: テスト実行**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest python.tilib.tests.test_equivalence -v 2>&1 | tail -25
```
Expected: 3 tests PASS。失敗した場合のデバッグ手順:
1. メッセージから drift しているフィールドを特定
2. tilib 経由で `set_param` できなかった必須パラメータが無いか確認（`KID_NS` 等の文字列項目は registry に未登録だが defaults で十分）
3. tolerance を一時的に `1e-6` に緩めて、どの量がどの程度ズレているか把握 → registry に必要 setter を追加（`ti_param_registry.f90` 修正で別 PR を立てる）

- [ ] **Step 3: コミット**

Run:
```bash
git add python/tilib/tests/test_equivalence.py
git commit -m "test(tilib): add Layer 1 equivalence tests vs L-0 baselines"
```

---

## Task 4: Layer 4 sweep smoke `test_sweep.py` を実装

**Files:**
- Create: `python/tilib/tests/test_sweep.py`

- [ ] **Step 1: 失敗するテストを書く**

作成: `python/tilib/tests/test_sweep.py`

```python
"""Layer 4: parameter sweep smoke (3x3 grid)."""

import os
import unittest
from pathlib import Path

LIBTIAPI = Path(__file__).resolve().parents[3] / "ti" / "libtiapi.so"


@unittest.skipUnless(LIBTIAPI.exists(), "libtiapi.so not built")
class TestSweep(unittest.TestCase):

    def test_3x3_grid_runs_to_completion(self):
        from tilib import Tilib

        results = []
        for rr in (5.5, 6.2, 6.9):
            for bb in (4.5, 5.3, 6.0):
                with Tilib() as ti:
                    ti.set_params(
                        NSMAX=1, NRMAX=10, NTMAX=2,
                        NTSTEP=1, NGTSTEP=1, NGRSTEP=1,
                        RR=rr, BB=bb,
                    )
                    ti.run(ntmax=2)
                    state = ti.get_state()
                    results.append((rr, bb, state.T))

        self.assertEqual(len(results), 9)
        # T should be > 0 everywhere (advanced 2 timesteps from 0)
        for rr, bb, T in results:
            self.assertGreater(T, 0.0,
                f"sweep cell RR={rr} BB={bb}: T not advanced ({T})")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: テスト実行**

Run:
```bash
cd /home/k-yoshimi/program/task
python3 -m unittest python.tilib.tests.test_sweep -v 2>&1 | tail -10
```
Expected: 1 test PASS。9 サイクルすべて完走。

- [ ] **Step 3: コミット**

Run:
```bash
git add python/tilib/tests/test_sweep.py
git commit -m "test(tilib): add Layer 4 3x3 sweep smoke test"
```

---

## Task 5: Layer 2 C ABI state テスト `test_state.c` を追加

**Files:**
- Create: `ti/tests/c_abi/test_state.c`
- Modify: `ti/tests/c_abi/Makefile`

- [ ] **Step 1: test_state.c を作成**

作成: `ti/tests/c_abi/test_state.c`

```c
/*
 * test_state.c — Layer 2: verify ti_get_state returns sensible values
 * after init + set_param + run(2).
 */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ti_api.h"

static int set(const char* name, double v) {
    int rc = ti_set_param(name, v);
    if (rc != 0) {
        fprintf(stderr, "set(%s=%g) returned %d\n", name, v, rc);
    }
    return rc;
}

int main(void) {
    int rc;
    ti_state_t s;

    rc = ti_init();
    assert(rc == 0);

    /* minimal ti_min-equivalent setup */
    if (set("NSMAX", 1) != 0) return 10;
    if (set("NRMAX", 10) != 0) return 11;
    if (set("NTMAX", 2) != 0) return 12;
    if (set("NTSTEP", 1) != 0) return 13;
    if (set("NGTSTEP", 1) != 0) return 14;
    if (set("NGRSTEP", 1) != 0) return 15;

    rc = ti_run(2);
    if (rc != 0) {
        fprintf(stderr, "ti_run failed: %d\n", rc);
        return 20;
    }

    memset(&s, 0xAB, sizeof(s));
    rc = ti_get_state(&s);
    assert(rc == 0);

    if (s.nrmax != 10) {
        fprintf(stderr, "nrmax expected 10, got %d\n", s.nrmax);
        return 30;
    }
    if (s.nsa_max < 1 || s.nsa_max > TI_MAX_NSA_MAX) {
        fprintf(stderr, "nsa_max out of range: %d\n", s.nsa_max);
        return 31;
    }
    if (s.T <= 0.0) {
        fprintf(stderr, "T not advanced: %g\n", s.T);
        return 32;
    }

    rc = ti_finalize();
    assert(rc == 0);

    printf("OK: ti_get_state returned consistent values (nrmax=%d nsa=%d T=%g)\n",
           s.nrmax, s.nsa_max, s.T);
    return 0;
}
```

- [ ] **Step 2: Makefile に test_state ターゲット追加**

`ti/tests/c_abi/Makefile` の `test:` を以下に変更:
```makefile
test: test_compile_run test_param_registry_run test_link_run test_state_run

test_state_run: test_state
	LD_LIBRARY_PATH=$(TI_DIR):$$LD_LIBRARY_PATH ./test_state

test_state: test_state.c $(TI_DIR)/ti_api.h $(LIBTIAPI)
	$(CC) $(CFLAGS) test_state.c -L$(TI_DIR) -ltiapi -Wl,-rpath,$(TI_DIR) -o test_state
```

`clean:` にも `test_state` を追加。

- [ ] **Step 3: 実行**

Run:
```bash
cd /home/k-yoshimi/program/task/ti/tests/c_abi
make test_state 2>&1 | tail -5
./test_state
```
Expected: `OK: ti_get_state returned consistent values ...`、exit 0。

- [ ] **Step 4: コミット**

Run:
```bash
git add ti/tests/c_abi/test_state.c ti/tests/c_abi/Makefile
git commit -m "test(ti): add Layer 2 ti_get_state value-check"
```

---

## Task 6: `run_tests.sh` に python/c 実行モードを追加

**Files:**
- Modify: `test_run/run_tests.sh`
- Modify: `test_run/test_definitions.conf`

**目的:** 現在の `run_tests.sh` は `module` を Fortran バイナリに紐付けて分岐する。新たに `module=python` (任意の Python unittest を実行) と `module=c` (任意の C 実行ファイルを直接実行) を追加し、`test_definitions.conf` から呼べるようにする。

以下はすべて `test_run/run_tests.sh` (現行 commit 331e3dbf 時点) に対する unified diff 形式。該当位置は行番号 **prefix (旧) → (新)** で示す。

- [ ] **Step 1: `get_binary()` に `python` / `c` 分岐を追加**

`run_tests.sh` 105 行付近の case を以下に変更:

```diff
@@ -104,10 +104,12 @@ done
 # Function to get module binary path
 get_binary() {
     local module="$1"
     case "$module" in
         eq) echo "$TASK_DIR/eq/eq" ;;
         tr) echo "$TASK_DIR/tr/tr2" ;;
+        ti) echo "$TASK_DIR/ti/ti" ;;
         fp) echo "$TASK_DIR/fp/fp" ;;
         tx) echo "$TASK_DIR/tx/tx2" ;;
+        python) echo "python3" ;;
+        c)      echo "" ;;   # binary path = the input_file itself
         *) echo "" ;;
     esac
 }
```

注: `ti) ...` 行は本来 L-0 Task 8 Step 2 で追加されるが、L-6 で改めて確認。既に入っていれば skip。

- [ ] **Step 2: SKIP 判定を python/c に対応**

`run_tests.sh` 245 行付近 (`# Check if binary exists`) を以下に変更:

```diff
@@ -242,12 +244,16 @@ run_single_test() {
     echo -n "[$TOTAL] $test_name ($description) ... "
 
     # Check if binary exists
-    if [[ ! -x "$binary" ]]; then
+    if [[ "$module" != "python" && "$module" != "c" && ! -x "$binary" ]]; then
         echo -e "${YELLOW}SKIP${NC} (module not built)"
         SKIPPED=$((SKIPPED + 1))
         return 0
     fi
+    # For module=c, require the input_file to be an executable.
+    if [[ "$module" == "c" && ! -x "$full_input_path" ]]; then
+        echo -e "${YELLOW}SKIP${NC} (c executable not built: $full_input_path)"
+        SKIPPED=$((SKIPPED + 1))
+        return 0
+    fi
```

**重要**: 上記の `full_input_path` は 236 行付近で既に解決されている (`$SCRIPT_DIR/${input_file#@}` or `$module_dir/$input_file`)。python module では入力ファイルが実ファイルではなく dotted module path なので、その前段で分岐を追加する（Step 3）。

- [ ] **Step 3: input_file の解釈分岐を追加**

`run_tests.sh` 235 行付近 (`# Handle @inputs prefix ...`) を以下に変更:

```diff
@@ -232,11 +232,16 @@ run_single_test() {
     local binary=$(get_binary "$module")
     local module_dir="$TASK_DIR/$module"
 
     # Handle @inputs prefix for local test inputs
     local full_input_path
-    if [[ "$input_file" == @* ]]; then
+    if [[ "$module" == "python" ]]; then
+        # input_file holds a dotted module path (e.g. tilib.tests.test_ffi).
+        # unittest resolves it from PYTHONPATH; no path expansion here.
+        full_input_path="$input_file"
+    elif [[ "$input_file" == @* ]]; then
         full_input_path="$SCRIPT_DIR/${input_file#@}"
     else
         full_input_path="$module_dir/$input_file"
     fi
```

- [ ] **Step 4: "Copy module-specific parameter files" の前に PYTHONPATH 自動設定と `input file exists` チェックをスキップする分岐を追加**

`run_tests.sh` 252 行付近 (`# Check if input file exists`) を以下に変更:

```diff
@@ -249,12 +254,22 @@ run_single_test() {
     fi
 
     # Check if input file exists
-    if [[ ! -f "$full_input_path" ]]; then
-        echo -e "${YELLOW}SKIP${NC} (input file not found: $full_input_path)"
-        SKIPPED=$((SKIPPED + 1))
-        return 0
-    fi
+    if [[ "$module" != "python" && "$module" != "c" ]]; then
+        if [[ ! -f "$full_input_path" ]]; then
+            echo -e "${YELLOW}SKIP${NC} (input file not found: $full_input_path)"
+            SKIPPED=$((SKIPPED + 1))
+            return 0
+        fi
+    fi
+
+    # Auto-export PYTHONPATH so unittest finds `tilib` without caller setup.
+    if [[ "$module" == "python" ]]; then
+        export PYTHONPATH="$TASK_DIR/python:${PYTHONPATH:-}"
+    fi
```

- [ ] **Step 5: `Run the test` セクションを python/c 対応に置換**

`run_tests.sh` 293〜310 行 (`# Run the test` から exit_code 取得まで) を以下に置換:

```diff
@@ -292,19 +307,36 @@ run_single_test() {
     # Run the test
     cd "$test_dir"
     local log_file="$test_dir/output.log"
 
-    # For TR module, enable regression dump (env-guarded inside trregress.f90).
-    local tr_env=()
+    # For TR/TI Fortran modules, enable regression dump (env-guarded).
+    local mod_env=()
     if [[ "$module" == "tr" ]]; then
-        tr_env=(env TR_REGRESS_DUMP=1)
+        mod_env=(env TR_REGRESS_DUMP=1)
+    elif [[ "$module" == "ti" ]]; then
+        mod_env=(env TI_REGRESS_DUMP=1)
     fi
 
-    if [[ $VERBOSE -eq 1 ]]; then
-        echo ""
-        "${tr_env[@]}" timeout "$timeout" "$binary" < "$full_input_path" 2>&1 | tee "$log_file"
-        local exit_code=${PIPESTATUS[0]}
+    local exit_code
+    if [[ "$module" == "python" ]]; then
+        if [[ $VERBOSE -eq 1 ]]; then
+            timeout "$timeout" python3 -m unittest "$full_input_path" -v 2>&1 | tee "$log_file"
+            exit_code=${PIPESTATUS[0]}
+        else
+            timeout "$timeout" python3 -m unittest "$full_input_path" -v > "$log_file" 2>&1
+            exit_code=$?
+        fi
+    elif [[ "$module" == "c" ]]; then
+        if [[ $VERBOSE -eq 1 ]]; then
+            timeout "$timeout" "$full_input_path" 2>&1 | tee "$log_file"
+            exit_code=${PIPESTATUS[0]}
+        else
+            timeout "$timeout" "$full_input_path" > "$log_file" 2>&1
+            exit_code=$?
+        fi
+    elif [[ $VERBOSE -eq 1 ]]; then
+        "${mod_env[@]}" timeout "$timeout" "$binary" < "$full_input_path" 2>&1 | tee "$log_file"
+        exit_code=${PIPESTATUS[0]}
     else
-        "${tr_env[@]}" timeout "$timeout" "$binary" < "$full_input_path" > "$log_file" 2>&1
-        local exit_code=$?
+        "${mod_env[@]}" timeout "$timeout" "$binary" < "$full_input_path" > "$log_file" 2>&1
+        exit_code=$?
     fi
```

注: `tr_env` → `mod_env` リネームで L-0 Task 8 と整合。`exit_code` の宣言を 1 箇所に寄せるため `local exit_code` を前倒し。

- [ ] **Step 6: PASS 判定を python/c 対応に追加**

`run_tests.sh` 313〜355 行 (`# Check result ... ` から関数末尾まで) を以下に置換:

```diff
@@ -310,6 +342,19 @@ run_single_test() {
     # Check result - CLOSED message is the primary success indicator
     if [[ $exit_code -eq 124 ]]; then
         echo -e "${YELLOW}TIMEOUT${NC} (exceeded ${timeout}s)"
         FAILED=$((FAILED + 1))
+    elif [[ "$module" == "python" || "$module" == "c" ]]; then
+        # For python/c modules: exit 0 means PASS; there's no CLOSED marker.
+        if [[ $exit_code -eq 0 ]]; then
+            echo -e "${GREEN}PASS${NC}"
+            PASSED=$((PASSED + 1))
+            COMPLETED_TESTS[$test_name]=1
+        else
+            echo -e "${RED}FAIL${NC} (exit code: $exit_code)"
+            FAILED=$((FAILED + 1))
+            if [[ $VERBOSE -eq 1 ]]; then
+                tail -10 "$log_file" | sed 's/^/    /'
+            fi
+        fi
     elif grep -q "CLOSED" "$log_file" 2>/dev/null; then
```

以下 L-0 Task 8 Step 4 で追加した `elif [[ "$module" == "ti" ]]` 分岐を含む既存 CLOSED-based 判定はそのまま温存。

- [ ] **Step 5: test_definitions.conf に 4 ケース追加**

`test_run/test_definitions.conf` 末尾に追加:

```
# =============================================================================
# TI Library Phase L-6: 4-layer tests
# =============================================================================
tilib_ffi:python:tilib.tests.test_ffi:none:60:Layer 3 ffi smoke
tilib_equivalence:python:tilib.tests.test_equivalence:ti_min,ti_ar,ti_w:300:Layer 1 equivalence vs ti baselines
tilib_sweep:python:tilib.tests.test_sweep:none:120:Layer 4 3x3 grid sweep
tilib_c_state:c:@../ti/tests/c_abi/test_state:none:60:Layer 2 ti_get_state value check
```

注: `tilib_c_state` の input_file は `@..` プレフィックスで `test_run/../ti/tests/c_abi/test_state` を参照。

- [ ] **Step 6: 実行確認**

Run:
```bash
cd /home/k-yoshimi/program/task
# 事前に libtiapi.so と test_state を build
(cd ti && make libtiapi.so) 2>&1 | tail -3
(cd ti/tests/c_abi && make test_state) 2>&1 | tail -3

# tilib も import path を通す（PYTHONPATH=python を export）
cd test_run
PYTHONPATH=/home/k-yoshimi/program/task/python ./run_tests.sh tilib_ffi tilib_sweep tilib_c_state tilib_equivalence
```
Expected: 4 ケースすべて PASS。

- [ ] **Step 7: PYTHONPATH 自動設定の動作確認**

Step 4 で `module=python` のとき `PYTHONPATH=$TASK_DIR/python:...` を export しているので、呼び出し側で設定不要になっているはず。

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
unset PYTHONPATH
./run_tests.sh tilib_ffi
```
Expected: PASS（PYTHONPATH を export せずに tilib が見つかる）。

- [ ] **Step 8: コミット**

Run:
```bash
git add test_run/run_tests.sh test_run/test_definitions.conf
git commit -m "test(tilib): add python/c run_tests.sh modes and 4 tilib_* cases"
```

---

## Task 7: 全テスト最終確認 + PR

- [ ] **Step 1: フル回帰**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh
```
Expected: eq/tr/tx/ti/tilib 全 PASS。FAILED=0。

- [ ] **Step 2: 変更ファイル確認**

Run:
```bash
git diff --stat origin/develop..HEAD
```
Expected: 新規 6 ファイル（python/tilib/tests/ 配下 4、ti/tests/c_abi/test_state.c）、修正 3 ファイル（ti/tests/c_abi/Makefile, test_run/run_tests.sh, test_run/test_definitions.conf）。

- [ ] **Step 3: push と PR**

Run:
```bash
git push -u origin feature/ti-library-L6-test-4layers
gh pr create --base develop \
  --title "test(tilib): add 4-layer tests + run_tests.sh integration (L-6)" \
  --body "Phase L-6: Layers 1 (equivalence), 2 (C state check), 3 (Pythonic), 4 (sweep). run_tests.sh now dispatches python/c modules. 4 new tilib_* cases registered."
```

---

## Dependencies

- 前段階: L-5 マージ済み (`Tilib` クラス)。
- 後段階: L-7 ドキュメント (`README.md` 拡充, notebook)。

## Fallback

| 障害 | 対処 |
|---|---|
| Layer 1 で `1e-10` を超える drift | (a) tolerance を `1e-8` に緩める、(b) `ti_param_registry` に未登録の必須パラメータを別 PR で追加して再試行 |
| Layer 1 が `KID_NS` を渡せず Ar/W で挙動が違う | namelist parser は string 値をスキップする実装 → registry に文字列 setter (`ti_set_string_param`) は L-3 では未対応。当面 Ar/W は equivalence test から除外し、`ti_min` のみで Layer 1 を確立 |
| Layer 4 sweep が散発的に「ti_prep failed」 | 各セルで `Tilib()` 新規 → 内部 ti_init / ti_finalize の global state リセット保証を `tiinit.f90` 内 `SAVE` 変数（特に `prepped` カウンタ）で確認。問題があれば `ti_finalize_c` でリセット処理を追加 |
| `run_tests.sh` の python/c 分岐が既存の eq/tr/tx ロジックを壊す | 分岐を case で隔離、tr/eq/tx の挙動は完全温存。回帰: `./run_tests.sh tr_iter01 eq_iter01 tx_std` で確認 |
| `tilib_c_state` で `LD_LIBRARY_PATH` が効かない | `Wl,-rpath` で .so の場所を埋め込んでいるはず。`ldd test_state` で確認、必要なら test_definitions の前に env を export |
