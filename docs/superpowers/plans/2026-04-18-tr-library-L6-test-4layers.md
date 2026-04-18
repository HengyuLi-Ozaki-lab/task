# Phase L-6: テスト 4 層 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 設計書 §8 の 4 層テストを実装し、`run_tests.sh` に統合する。Layer 1 (等価性) で Phase 0 baseline と libtrapi.so 経由の出力が `1e-10` 以内に一致することを 3 ケースで検証する。

**Architecture:** 4 層を別々のテストファイルに配置:
- **Layer 1 (等価性):** `python/trlib/tests/test_equivalence.py` — namelist を `_ffi` 経由でロード（または `f90nml` 採用判断）→ `Trlib.run` → `to_dict()` を Phase 0 `compare_metrics.py` で baseline と比較。
- **Layer 2 (C ABI):** L-2/L-3 の C スモークを正式テストに昇格。`tr/tests/c_abi/` 配下に `test_smoke / test_param / test_run / test_state_layout` の 4 本。
- **Layer 3 (Python ラッパ):** `python/trlib/tests/test_ffi.py` — `Trlib` class の API 契約（context manager、二重 close、`set_params` の辞書一括）。
- **Layer 4 (網羅計算 smoke):** `python/trlib/tests/test_sweep.py` — 3×3 グリッドで `Trlib` を回し、結果を集めるユースケースが破綻なく回ること。

**Tech Stack:** Python stdlib (`unittest`, `json`, `pathlib`), Phase 0 の `compare_metrics.py`, `extract_tr_metrics.py`, C スモーク (gcc/gfortran), `run_tests.sh` 拡張。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` §8 (テスト戦略), §A.8 (4 層採用根拠), §11 (namelist パーサ未確定事項)。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `python/trlib/tests/test_equivalence.py` | 新規 | Layer 1: baseline JSON との `1e-10` 比較 |
| `python/trlib/tests/test_ffi.py` | 新規 | Layer 3: Trlib class 契約テスト |
| `python/trlib/tests/test_sweep.py` | 新規 | Layer 4: 3×3 パラメータグリッド smoke |
| `python/trlib/tests/fixtures/iter01_params.py` | 新規 | namelist パラメータの Python 辞書（Layer 1/4 で共用） |
| `python/trlib/tests/fixtures/m0904_params.py` | 新規 | 同上 |
| `python/trlib/tests/fixtures/tst2_params.py` | 新規 | 同上 |
| `tr/tests/c_abi/test_state_layout.c` | 新規 | Layer 2: `sizeof(tr_state_t)` 検証 |
| `tr/tests/c_abi/Makefile` | 修正 | `test_state_layout` ターゲット追加 |
| `test_run/test_definitions.conf` | 修正 | `trlib_*` 4 ケースを追加 |
| `test_run/run_tests.sh` | 修正 | Python 実行モードと C 実行モードを追加（既存 Fortran モードと並列） |

**方針:**
- **namelist 入力の取り込み**: 設計書 §11 で「`f90nml` or 既存 `trparm` 経由」が未確定。本サブでは **Python 辞書 fixture** を採用する（依存追加なし、既存 Phase 0 で確認したパラメータと完全一致するよう手書き）。`tr_iter01.in` の主要パラメータ ~20〜30 個を Python 辞書化。残りは TR の default 値が `tr_init` で設定される前提。
- 等価性テストでもし default 値だけでは baseline と一致しなければ、不一致パラメータを追加して fixture を完成させる（イテレーション）。
- Layer 4 は smoke のみ。物理的妥当性は範囲外。
- `run_tests.sh` の拡張は既存ロジックを壊さないよう、`type` 列に `python` / `c_exec` を追加して dispatch する。

---

## Task 1: ブランチと前提

- [ ] **Step 1: L-5 完了確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin develop
git log --oneline origin/develop | grep -i "phase l-5" | head -3
ls python/trlib/__init__.py tr/libtrapi.so
PYTHONPATH=python python3 -c "from trlib import Trlib"
```
Expected: L-5 merge 済み、`Trlib` import OK。

- [ ] **Step 2: ブランチ作成**

Run:
```bash
git checkout -b feature/tr-library-phase-l6 origin/develop
(cd tr && make libtrapi.so 2>&1 | tail -3)
```

---

## Task 2: Layer 1 — fixture と等価性テスト

**Files:**
- Create: `python/trlib/tests/fixtures/iter01_params.py`

- [ ] **Step 1: ITER01 パラメータ辞書を作る**

`test_run/inputs/tr_iter01.in` を読み、namelist の `&trnlst` ブロックを Python 辞書に書き写す。

作成: `python/trlib/tests/fixtures/iter01_params.py`

```python
"""ITER01 parameters mirroring test_run/inputs/tr_iter01.in.

Edit cautiously: changing values invalidates the equivalence test.
"""
ITER01_PARAMS = {
    # geometry
    "RR":   8.5,
    "RA":   2.0,
    "RKAP": 1.7,
    "RDLT": 0.3,
    "BB":   5.3,
    # plasma species
    "NSMAX": 2,
    # PA, PZ, PN, PNS, PT, PTS — array elements use "PN[1]" style
    # listed via fixture function below to support indexed setters.
    # current
    "RIPS": 1.5,
    "RIPE": 1.5,
    # time
    "DT":     0.1,
    "NTSTEP": 10,
    "NTMAX":  20,
    # transport
    "MDLKAI": 31,
    "MDLETA":  1,
    "MDLAD":   2,
    # …  populate the rest from tr_iter01.in as needed for equivalence
}

ITER01_ARRAYS = {
    "PA":  [1.0, 1.0],
    "PZ":  [-1.0, 1.0],
    "PN":  [1.0, 1.0],
    "PNS": [0.1, 0.1],
    "PT":  [1.5, 1.5],
    "PTS": [0.1, 0.1],
}


def apply(tr) -> None:
    """Apply ITER01 parameters to a Trlib instance."""
    for k, v in ITER01_PARAMS.items():
        tr.set_param(k, v)
    for name, arr in ITER01_ARRAYS.items():
        for i, v in enumerate(arr, start=1):
            tr.set_param(f"{name}[{i}]", v)
```

注: 値は `test_run/inputs/tr_iter01.in` を **見ながら** 一字一句写す（差異が baseline 不一致を生む）。同様に `m0904_params.py`, `tst2_params.py` を作成（`test_run/inputs/tr_m0904.in`, `tr_tst2.in` 由来）。

- [ ] **Step 2: 残り 2 fixture を作成**

`fixtures/m0904_params.py`, `fixtures/tst2_params.py` を `tr_m0904.in` / `tr_tst2.in` の値で同様に作成。

- [ ] **Step 3: Layer 1 テスト本体**

作成: `python/trlib/tests/test_equivalence.py`

```python
"""Layer 1: equivalence with Phase 0 baselines (tol 1e-10)."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BASELINES = REPO / "test_run" / "baselines"
COMPARE = REPO / "test_run" / "scripts" / "compare_metrics.py"
DEFAULT_SO = REPO / "tr" / "libtrapi.so"

sys.path.insert(0, str(REPO / "python"))


def run_case(apply_fn, ntmax: int) -> dict:
    from trlib import Trlib
    with Trlib() as tr:
        apply_fn(tr)
        tr.run(ntmax)
        return tr.get_state().to_dict()


def compare_with_baseline(actual: dict, baseline_dir: Path, tol: str = "1e-10") -> None:
    actual_path = baseline_dir.parent / "_actual.json"
    actual_path.write_text(json.dumps(actual))
    res = subprocess.run(
        [sys.executable, str(COMPARE),
         "--baseline", str(baseline_dir / "metrics.json"),
         "--actual",   str(actual_path),
         "--tolerance", tol],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        raise AssertionError(f"compare_metrics FAIL:\n{res.stdout}\n{res.stderr}")


@unittest.skipUnless(DEFAULT_SO.exists(), "libtrapi.so not built")
class TestEquivalence(unittest.TestCase):
    def test_iter01(self):
        from python.trlib.tests.fixtures.iter01_params import apply
        actual = run_case(apply, ntmax=20)
        compare_with_baseline(actual, BASELINES / "tr_iter01")

    def test_m0904(self):
        from python.trlib.tests.fixtures.m0904_params import apply
        actual = run_case(apply, ntmax=50)
        compare_with_baseline(actual, BASELINES / "tr_m0904")

    def test_tst2(self):
        from python.trlib.tests.fixtures.tst2_params import apply
        actual = run_case(apply, ntmax=10)
        compare_with_baseline(actual, BASELINES / "tr_tst2")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: 走らせる**

Run:
```bash
cd /home/k-yoshimi/program/task
PYTHONPATH=python python3 -m unittest python.trlib.tests.test_equivalence -v 2>&1 | tail -30
```
Expected: 3 tests OK。FAIL した場合は:
- `compare_metrics.py` の出力が「どのスカラー / プロファイル要素」が違うかを示す。
- Fixture に該当パラメータを追加 or default 値が異なるなら fixture に明示。
- iteration を繰り返す（数日〜1 週間想定）。

- [ ] **Step 5: 撤退判断**

5 イテレーションしても baseline と一致しない場合、設計書 §11 の代替案を採用:
- (b) `f90nml` を導入: `pip install f90nml` を許容、namelist パーサで `tr_iter01.in` を直接読み込む。
- (c) `trparm` を C ABI 経由で呼ぶ（`tr_load_namelist(path)` を `tr_api.f90` に追加）。

(b) は依存追加コストが小さく推奨。

---

## Task 3: Layer 2 — C ABI 単体テスト整備

**Files:**
- Create: `tr/tests/c_abi/test_state_layout.c`
- Modify: `tr/tests/c_abi/Makefile`

- [ ] **Step 1: state 構造体サイズ検証**

作成: `tr/tests/c_abi/test_state_layout.c`

```c
/* Layer 2: ensures Fortran tr_state_c and C tr_state_t agree in size/layout.
 * If they ever drift, ctypes wrapper will misread fields. */
#include <stdio.h>
#include <stddef.h>
#include "../../tr_api.h"

extern size_t tr_state_c_sizeof(void);   /* implemented in helper f90 below */

int main(void) {
    size_t c_sz = sizeof(tr_state_t);
    size_t f_sz = tr_state_c_sizeof();
    if (c_sz != f_sz) {
        fprintf(stderr, "size mismatch: C=%zu Fortran=%zu\n", c_sz, f_sz);
        return 1;
    }
    /* Spot-check a few field offsets. */
    if (offsetof(tr_state_t, T) <= offsetof(tr_state_t, nsmax)) {
        fprintf(stderr, "field order: T must follow scalars\n"); return 2;
    }
    printf("OK: layout sizeof=%zu\n", c_sz);
    return 0;
}
```

作成: `tr/tests/c_abi/state_layout_helper.f90`

```fortran
FUNCTION tr_state_c_sizeof() RESULT(sz) BIND(C, NAME="tr_state_c_sizeof")
  USE, INTRINSIC :: ISO_C_BINDING
  USE tr_state, ONLY: tr_state_c
  TYPE(tr_state_c) :: dummy
  INTEGER(C_SIZE_T) :: sz
  sz = C_SIZEOF(dummy)
END FUNCTION
```

- [ ] **Step 2: Makefile に追加**

`tr/tests/c_abi/Makefile` の末尾に追加:

```makefile
$(TR_OBJDIR)/state_layout_helper.o: state_layout_helper.f90 $(API_OBJS)
	$(FCFREE) $(FFLAGS) -I../../mod -c state_layout_helper.f90 -o $(TR_OBJDIR)/state_layout_helper.o

test_state_layout: test_state_layout.c $(API_OBJS) $(TR_OBJDIR)/state_layout_helper.o
	$(CC) -I../.. test_state_layout.c \
	    $(API_OBJS) $(TR_OBJDIR)/state_layout_helper.o \
	    $(TR_LIB) $(DEPS) $(FLIBS) -o test_state_layout

run_layer2: test_smoke test_param test_run test_state_layout
	./test_smoke
	./test_param
	./test_run
	./test_state_layout
```

- [ ] **Step 3: 走らせる**

Run:
```bash
cd /home/k-yoshimi/program/task/tr/tests/c_abi
make run_layer2 2>&1 | tail -10
```
Expected: 4 本すべて `OK:`。

---

## Task 4: Layer 3 — Python ラッパ契約テスト

**Files:**
- Create: `python/trlib/tests/test_ffi.py`

- [ ] **Step 1: 作成**

作成: `python/trlib/tests/test_ffi.py`

```python
"""Layer 3: Trlib class API contracts (no numerics)."""
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"


@unittest.skipUnless(DEFAULT_SO.exists(), "libtrapi.so not built")
class TestTrlibContract(unittest.TestCase):
    def test_context_manager(self):
        from trlib import Trlib
        with Trlib() as tr:
            tr.run(0)
        # second close should be a no-op
        tr.close()

    def test_set_params_dict(self):
        from trlib import Trlib
        with Trlib() as tr:
            tr.set_params(RR=7.5, BB=5.3, DT=0.05)
            tr.set_param("PN[1]", 0.7)
            tr.set_param("PN[2]", 0.3)

    def test_unknown_param_raises(self):
        from trlib import Trlib, TrlibParamError
        with Trlib() as tr:
            with self.assertRaises(TrlibParamError):
                tr.set_param("DOES_NOT_EXIST", 1.0)

    def test_call_after_close_raises(self):
        from trlib import Trlib, TrlibError
        tr = Trlib()
        tr.close()
        with self.assertRaises(TrlibError):
            tr.run(1)

    def test_repeated_run_accumulates(self):
        from trlib import Trlib
        with Trlib() as tr:
            tr.set_param("DT", 0.01)
            s0 = tr.get_state()
            tr.run(3); s1 = tr.get_state()
            tr.run(3); s2 = tr.get_state()
            self.assertGreater(s1.scalars["T"], s0.scalars["T"])
            self.assertGreater(s2.scalars["T"], s1.scalars["T"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 実行**

Run:
```bash
PYTHONPATH=python python3 -m unittest python.trlib.tests.test_ffi -v
```
Expected: 5 tests OK。

---

## Task 5: Layer 4 — 網羅計算 smoke

**Files:**
- Create: `python/trlib/tests/test_sweep.py`

- [ ] **Step 1: 作成**

作成: `python/trlib/tests/test_sweep.py`

```python
"""Layer 4: parameter sweep smoke (3x3 grid, no physics validation)."""
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"


@unittest.skipUnless(DEFAULT_SO.exists(), "libtrapi.so not built")
class TestSweep(unittest.TestCase):
    def test_3x3_grid(self):
        from trlib import Trlib
        from python.trlib.tests.fixtures.iter01_params import apply as apply_iter01

        rr_values = [7.5, 8.0, 8.5]
        bb_values = [4.5, 5.0, 5.5]
        results = []
        for rr in rr_values:
            for bb in bb_values:
                with Trlib() as tr:
                    apply_iter01(tr)
                    tr.set_param("RR", rr)
                    tr.set_param("BB", bb)
                    tr.run(5)         # short run; smoke only
                    state = tr.get_state()
                    results.append((rr, bb, state.scalars["WPT"]))
        self.assertEqual(len(results), 9)
        # Sanity: all WPT finite
        for rr, bb, wpt in results:
            self.assertFalse(wpt != wpt, f"NaN WPT at RR={rr} BB={bb}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 実行**

Run:
```bash
PYTHONPATH=python python3 -m unittest python.trlib.tests.test_sweep -v
```
Expected: 1 test OK。所要 60〜120 秒程度。

---

## Task 6: `run_tests.sh` 統合

**Files:**
- Modify: `test_run/test_definitions.conf`
- Modify: `test_run/run_tests.sh`

### 既存仕様の確認（review #9 反映）

現行 `test_run/run_tests.sh` の dispatch 仕様:

```bash
# run_tests.sh:104-114
get_binary() {
    local module="$1"
    case "$module" in
        eq) echo "$TASK_DIR/eq/eq" ;;
        tr) echo "$TASK_DIR/tr/tr2" ;;
        fp) echo "$TASK_DIR/fp/fp" ;;
        tx) echo "$TASK_DIR/tx/tx2" ;;
        *) echo "" ;;   # ←  python は空文字 → "module not built" 扱いになり SKIP
    esac
}
```

`test_definitions.conf` の **第 3 列 (`INPUT_FILE`) は本来「namelist 入力ファイルへの相対パス」** として解釈され、`run_single_test()` 内では `$module_dir/$input_file` または `$TEST_RUN_DIR/inputs/$input_file` に展開される。よって本 plan が新導入する `MODULE=python` ＋「第 3 列にシェル/make コマンド文字列」という運用は、**現行コードでは確実に SKIP または ENOENT で落ちる**。

そのため Step 1（conf 追加）と Step 2（run_tests.sh 拡張）は **同一コミットでアトミックに投入** する。**もし片方しか入っていないリビジョンが develop に存在するとリグレッションが発生する**ので、リビジョン順序の入れ替えは禁止（必ず Step 2 のスクリプト変更を先に書き、Step 1 の conf 追加と一緒に commit する）。

dispatch のあいまいさ解消方針:

- `MODULE=python` のとき、第 3 列を **shell command** として解釈する（既存 `tr`/`eq`/`fp`/`tx` のときは従来どおり INPUT_FILE）。
- 区別の起点は `MODULE` 列の値のみ。コロン区切りはそのまま 6 列を維持し、構造変更は行わない（既存パーサ `IFS=':' read -r TEST_NAME MODULE INPUT_FILE DEPENDS TIMEOUT DESCRIPTION` を変えない）。
- `python` ケースでは `INPUT_FILE` 変数を「シェルコマンド文字列」として再利用するため、コメントで明示する。

- [ ] **Step 1 + Step 2: アトミックコミットでの conf 追加 + dispatch 拡張**

両方の変更を **同一コミット** で入れる（順序逆転禁止）。

(a) `test_run/test_definitions.conf` の末尾に追加:

```
# Phase L-6: Python/C-ABI test integration.
# For MODULE=python, the 3rd column (normally INPUT_FILE) is reinterpreted
# as a shell command line executed via "sh -c" with PYTHONPATH=python.
trlib_c_abi:python:make -C tr/tests/c_abi run_layer2:none:120:Layer 2 C ABI tests
trlib_ffi:python:python3 -m unittest python.trlib.tests.test_ffi:none:60:Layer 3 Python wrapper
trlib_equivalence:python:python3 -m unittest python.trlib.tests.test_equivalence:none:300:Layer 1 equivalence (tol 1e-10)
trlib_sweep:python:python3 -m unittest python.trlib.tests.test_sweep:none:180:Layer 4 sweep smoke
```

注: 第 3 列の `make -C tr/tests/c_abi run_layer2` のような空白を含むコマンドはそのまま「シェルに渡す 1 トークン」として扱われる。ただし `:` をコマンド中に書くと `IFS=':' read` で分割されるため、**コマンド文字列内に `:` を入れない**こと（必要なら `sh -c` で `\$(...)` にラップして回避）。

(b) `test_run/run_tests.sh` の `get_binary()` を拡張し、`run_single_test()` の入口で `python` モジュールを先取り分岐させる。具体的差分:

```diff
--- a/test_run/run_tests.sh
+++ b/test_run/run_tests.sh
@@ -104,6 +104,8 @@ get_binary() {
     local module="$1"
     case "$module" in
         eq) echo "$TASK_DIR/eq/eq" ;;
         tr) echo "$TASK_DIR/tr/tr2" ;;
         fp) echo "$TASK_DIR/fp/fp" ;;
         tx) echo "$TASK_DIR/tx/tx2" ;;
+        python) echo "PYTHON_DISPATCH" ;;   # marker; not a real path
         *) echo "" ;;
     esac
 }
@@ -210,6 +212,21 @@ run_single_test() {
     local test_name="$1"
     local module="$2"
-    local input_file="$3"
+    local input_file="$3"   # for MODULE=python this is reinterpreted as a shell command
     local depends="$4"
     local timeout="$5"
     local description="$6"

     # Skip if already completed
     if [[ "${COMPLETED_TESTS[$test_name]}" == "1" ]]; then
         return 0
     fi

     TOTAL=$((TOTAL + 1))

+    # Phase L-6: python / c-abi dispatch. The 3rd column is treated as a shell
+    # command line, executed from $TASK_DIR with PYTHONPATH=python.
+    if [[ "$module" == "python" ]]; then
+        local cmd="$input_file"
+        local outdir="$RESULT_DIR/$test_name"
+        mkdir -p "$outdir"
+        ( cd "$TASK_DIR" && PYTHONPATH=python timeout "$timeout" sh -c "$cmd" ) \
+            > "$outdir/output.log" 2>&1
+        local rc=$?
+        if [[ $rc -eq 0 ]]; then
+            echo -e "${GREEN}PASS${NC}"
+            COMPLETED_TESTS[$test_name]=1
+            PASSED=$((PASSED + 1))
+        else
+            echo -e "${RED}FAIL${NC} (rc=$rc)"
+            FAILED=$((FAILED + 1))
+        fi
+        return 0
+    fi
+
     # Override timeout if specified
     if [[ -n "$TIMEOUT_OVERRIDE" ]]; then
         timeout="$TIMEOUT_OVERRIDE"
     fi
```

注:
- `get_binary()` で `python` に `PYTHON_DISPATCH` というマーカ文字列を返すのは、`list_tests()` の `[[ ! -x "$binary" ]]` チェックで「not built」と誤判定されるのを避けるため（実体ファイルではないのでマーカで OK；実行時には使わない）。
- 既存の `tr`/`eq`/`fp`/`tx` の処理パスは一切変更していない。`python` 分岐は早期 return するので副作用なし。
- `RESULT_DIR` 変数名は実物 `run_tests.sh` のローカル名に合わせて差分を整える（実装時に `grep -n RESULT_DIR test_run/run_tests.sh` で確認）。

- [ ] **Step 3: ローカル実行**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh trlib_c_abi trlib_ffi trlib_equivalence trlib_sweep 2>&1 | tail -10
```
Expected: 4/4 PASS。

- [ ] **Step 4: 既存ケースの後方互換**

Run:
```bash
./run_tests.sh tr_iter01 tr_m0904 tr_tst2 eq_tst2 2>&1 | tail -10
```
Expected: 既存ケースも引き続き PASS。

---

## Task 7: コミットと PR

- [ ] **Step 1: 段階コミット**

Run:
```bash
git add python/trlib/tests/fixtures/
git commit -m "test(trlib): namelist fixture dicts for ITER01/M0904/TST2"

git add python/trlib/tests/test_equivalence.py
git commit -m "test(trlib): Layer 1 equivalence vs Phase 0 baselines"

git add tr/tests/c_abi/test_state_layout.c tr/tests/c_abi/state_layout_helper.f90 tr/tests/c_abi/Makefile
git commit -m "test(tr): Layer 2 add state-layout C/Fortran size check"

git add python/trlib/tests/test_ffi.py
git commit -m "test(trlib): Layer 3 Trlib class contract tests"

git add python/trlib/tests/test_sweep.py
git commit -m "test(trlib): Layer 4 3x3 sweep smoke"

git add test_run/test_definitions.conf test_run/run_tests.sh
git commit -m "ci(test_run): integrate trlib_* cases (python dispatch mode)"
```

注（review #9 反映）: 上記の最後のコミットは `test_definitions.conf` への新エントリ追加と `run_tests.sh` の `python` dispatch 拡張を **必ず同一コミットに含める**。順序を入れ替えて conf だけ先に merge すると `MODULE=python` が `get_binary()` で空文字となり既存ケースが SKIP される（regression）。

- [ ] **Step 2: PR**

Run:
```bash
gh pr create --base develop --title "test(tr): Phase L-6 four-layer test integration" \
  --body "Phase L-6: Layer 1〜4 を実装し、run_tests.sh に trlib_* 4 ケースを追加。設計書 §8。"
```

---

## 撤退条件 / フォールバック

| 状況 | 対応 |
|---|---|
| Layer 1 が baseline と一致せず収束しない | `f90nml` 採用 (§11)。`pip install f90nml` を README に明示。 |
| Layer 4 が timeout (>180s) | 2x2 グリッドに縮小、もしくは `NTMAX` をさらに縮める |
| `run_tests.sh` の python dispatch が既存ケースを壊す | dispatch を別スクリプト `run_python_tests.sh` に分け、`run_tests.sh` からはそれを呼ぶだけにする |
| conf だけ先に入って `run_tests.sh` 拡張が遅れる | 撤退ではなく **予防策**: Task 6 の Step 1+2 を必ず同一コミットで投入（順序逆転禁止）。CI で trlib_ffi が SKIP になっていたら conf/script の片側 merge を疑う |

## 受け入れ基準

- [ ] Layer 1: `tr_iter01`, `tr_m0904`, `tr_tst2` 3 ケース PASS（tol `1e-10`）
- [ ] Layer 2: C スモーク 4 本 PASS
- [ ] Layer 3: Trlib 契約テスト 5 本 PASS
- [ ] Layer 4: 3x3 sweep 完走、すべて finite
- [ ] `run_tests.sh trlib_*` で 4 ケースすべて PASS
- [ ] 既存 `run_tests.sh tr_iter01 ...` も引き続き PASS

## 依存

- L-5 完了
