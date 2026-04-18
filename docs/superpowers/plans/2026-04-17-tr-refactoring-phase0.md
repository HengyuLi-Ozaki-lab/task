# TR リファクタリング Phase 0: 回帰テスト基盤整備 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `tr/` モジュールのリファクタリング前に、数値挙動を固定する回帰テスト基盤を `test_run/` に整備し、3ケース以上のゴールデンテストを CI で実行可能にする。

**Architecture:** TR 本体に最小限の高精度 dump モジュール `trregress.f90` を 1 つ追加する（環境変数 `TR_REGRESS_DUMP=1` のときのみ `tr_regress.dat` を書き出す設計、通常実行には影響なし）。既存の `test_run/run_tests.sh` + `test_definitions.conf` を拡張し、TR テスト実行時にこの環境変数を立てて dump を得た上で、ベースラインと相対誤差 `1e-10` で比較する Python スクリプトを追加する。ベースラインは `test_run/baselines/tr_*/` に commit。

**Tech Stack:** Fortran 90（`trregress.f90` 追加）, Bash (既存 `run_tests.sh`), Python 3 + 標準ライブラリのみ (依存追加なし), gfortran (既存ビルド), 既存 TR バイナリ `tr/tr2`。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-refactoring-design.md` Phase 0。

---

## File Structure

このフェーズで作成・変更するファイル:

| ファイル | 種別 | 責務 |
|---|---|---|
| `tr/trregress.f90` | 新規 | 環境変数ガード付き高精度 dump（`1PE24.16` 書式） |
| `tr/trloop.f90` | 修正 | 計算ループ終了時に `tr_regress_dump_if_enabled` を呼ぶ1行フック追加 |
| `tr/Makefile` | 修正 | `SRCS` に `trregress.f90` を追加 |
| `test_run/inputs/tr_m0904.in` | 新規 | modelg=2（解析モデル）ベースの TR 回帰入力（EQ 非依存） |
| `test_run/inputs/tr_tst2.in` | 新規 | TST-2 小型機ベースの TR 回帰入力（短縮版） |
| `test_run/scripts/extract_tr_metrics.py` | 新規 | `tr_regress.dat` から数値指標を JSON に変換 |
| `test_run/scripts/compare_metrics.py` | 新規 | 2 つの指標 JSON を相対誤差で比較（デフォルト `1e-10`） |
| `test_run/scripts/check_regression.sh` | 新規 | 抽出＋比較を run_tests.sh から呼び出すラッパ |
| `test_run/baselines/tr_iter01/metrics.json` | 新規（生成） | ベースライン指標（コミット対象） |
| `test_run/baselines/tr_m0904/metrics.json` | 新規（生成） | ベースライン指標 |
| `test_run/baselines/tr_tst2/metrics.json` | 新規（生成） | ベースライン指標 |
| `test_run/test_definitions.conf` | 修正 | 新ケース追加 |
| `test_run/run_tests.sh` | 修正 | TR モジュール実行時に `TR_REGRESS_DUMP=1` をエクスポートし、成功時に `check_regression.sh` を呼ぶ |
| `test_run/README.md` | 新規 | テスト運用手順と dump 機構の説明 |

**方針:**
- TR 本体への追加は **`trregress.f90` 新規 1 ファイル + `trloop.f90` への 1 行フック + Makefile への 1 行追加** に限定する。通常実行（環境変数未設定）では挙動完全不変。
- Python は標準ライブラリのみ使用（`json`, `re`, `math`, `argparse`）。
- 比較ツールは `--tolerance` 引数で相対誤差を調整可能（デフォルト `1e-10`）。
- ベースラインは初回 `--generate-baseline` モードで書き出し、以後は比較のみ。

---

## Task 1: 作業用ブランチ作成とビルド確認

**Files:**
- なし（環境準備）

- [ ] **Step 1: 現在の git 状態を確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git status
git branch --show-current
```
Expected: `fix/tr-dealloc-cleanup` ブランチに居る、または `main` ベース。uncommitted な重要変更がないこと。

- [ ] **Step 2: Phase 0 用ブランチを作る**

Run:
```bash
git checkout -b feature/tr-regression-phase0
```
Expected: ブランチが切り替わる。

- [ ] **Step 3: コンパイラ最適化フラグが固定されていることを確認**

Run:
```bash
grep -n "^OFLAGS\|^DFLAGS\|^FFLAGS" /home/k-yoshimi/program/task/make.header | head -10
grep -n "^FFLAGS" /home/k-yoshimi/program/task/tr/Makefile | head -5
```
Expected:
- `make.header` に `OFLAGS = -g -O3 -m64 -std=legacy` 相当の1行が有効化されている。
- `tr/Makefile` は `FFLAGS = $(OFLAGS)` を使っている（`$(DFLAGS)` がアンコメントされていないこと）。

もし複数の `OFLAGS` がアンコメントされていたら、Phase 0 の期間中は1セットに固定する（別ブランチでは触らないでもらう）ことをメモしておく。

- [ ] **Step 4: eq と tr をビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/eq && make 2>&1 | tail -5
cd /home/k-yoshimi/program/task/tr && make 2>&1 | tail -5
```
Expected: `eq/eq` と `tr/tr2` の両バイナリが生成される。エラーなし。

- [ ] **Step 5: 既存の tr_iter01 テストが通ることを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tr_iter01
```
Expected: `PASS` が表示される。`test_output/tr_iter01/output.log` が生成される。

- [ ] **Step 6: コミット（ブランチ初期化のマーカー）**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "chore: start Phase 0 regression test scaffolding"
```

---

## Task 2: 比較戦略の確認（決定済み項目の文書化）

**Files:**
- 調査のみ（この段階ではファイル作成なし）

**決定事項（本計画で確定済み）:**

TR 本体に環境変数ガード付きの高精度 dump モジュール `trregress.f90` を追加し、そこから得られる固定フォーマットの `tr_regress.dat` を比較対象とする。

- **dump 対象:**
  - スカラー: `NT, NRMAX, NSMAX, T, WPT, AJT, Q0, BETA0, BETAP0, BETAA, BETAN, TAUE1, TAUE2, ZEFF0, ALI, RQ1`
  - プロファイル: `RN(NR,1:NSMAX), RT(NR,1:NSMAX), AJ(NR), QP(NR)` を NR=1..NRMAX
- **書式:** スカラーは `1PE24.16`、プロファイルは1行につき NR と `1PE24.16` の連続。
- **起動条件:** 環境変数 `TR_REGRESS_DUMP=1` のときのみ `tr_regress.dat` を CWD に書き出す。未設定時は何もしない。
- **許容誤差:** デフォルト `1e-10`（1PE24.16 の有効桁数内）。Task 13 での run-to-run 再現性測定で必要に応じ `1e-12` へ締める、または `1e-8` まで緩める。
- **stdout ログの数値行:** 比較対象外（精度不足）。ただし `CLOSED` マーカーは従来通り CLOSED 判定に使う。

- [ ] **Step 1: stdout の数値精度を確認（参考情報）**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
grep -E "T:|TE:|TD:|TT:|TA:|WP:|TAUE:|Q0:" test_output/tr_iter01/output.log | head -6
```
Expected: `# T:  2.000(S)  WP: 41.13(MJ)  TAUE: 2.265(S)  Q0: 0.579` などの行。これらは 3〜4 桁精度で、比較対象としては使わないと確認する目的。

- [ ] **Step 2: dump 対象のグローバル量が TRCOMM に存在することを確認**

Run:
```bash
grep -n "WPT\|AJT\|Q0\|BETA0\|BETAP0\|BETAA\|BETAN\|TAUE1\|TAUE2\|ZEFF0\|\bALI\b\|\bRQ1\b" /home/k-yoshimi/program/task/tr/trcomm.f90 | head -20
```
Expected: これらのスカラーがすべて TRCOMM 内に宣言されていること。

もし一部が存在しない場合は、Task 3 Step 2 の dump コードから除外する。

- [ ] **Step 3: この決定を plan に反映したコミットを作る**

Run:
```bash
cd /home/k-yoshimi/program/task
git add docs/superpowers/plans/2026-04-17-tr-refactoring-phase0.md
git commit -m "docs: lock comparison strategy (trregress dump, tol 1e-10)"
```

---

## Task 3: `trregress.f90` を追加して高精度 dump を実装

**Files:**
- Create: `tr/trregress.f90`
- Modify: `tr/trloop.f90`（USE 文追加 + 1 行フック）
- Modify: `tr/Makefile`（`SRCS` に 1 ファイル追加）

**目的:** 環境変数 `TR_REGRESS_DUMP=1` のときに限り、計算ループ終了時点の主要グローバル量とプロファイルを `tr_regress.dat` へ `1PE24.16` 書式で書き出す。通常実行では何もしない。

- [ ] **Step 1: `tr/trloop.f90` の終了位置 (9000 ラベル) を確認**

Run:
```bash
grep -n "9000\|USE " /home/k-yoshimi/program/task/tr/trloop.f90
```
Expected: `9000 IF(MDLUF.EQ.1...` とそれに続く `RETURN` が見える。既存の `USE` 行のリストが分かる。

- [ ] **Step 2: `tr/trregress.f90` を新規作成**

作成: `tr/trregress.f90`

```fortran
! trregress.f90
!
! High-precision regression dump for Phase 0 regression tests.
! Emits tr_regress.dat (1PE24.16 format) when TR_REGRESS_DUMP=1.
! Otherwise does nothing; normal runs are unaffected.

MODULE trregress

  PRIVATE
  PUBLIC :: tr_regress_dump_if_enabled

CONTAINS

  SUBROUTINE tr_regress_dump_if_enabled
    USE TRCOMM, ONLY: &
         NRMAX, NSMAX, NT, T, rkind, &
         WPT, AJT, Q0, BETA0, BETAP0, BETAA, BETAN, &
         TAUE1, TAUE2, ZEFF0, ALI, RQ1, &
         RN, RT, AJ, QP
    IMPLICIT NONE
    INTEGER, PARAMETER :: UNIT_DUMP = 77
    CHARACTER(LEN=16) :: ENV_VAL
    INTEGER :: STAT, NR, NS, IOERR
    LOGICAL :: ENABLED

    CALL GET_ENVIRONMENT_VARIABLE('TR_REGRESS_DUMP', ENV_VAL, STATUS=STAT)
    ENABLED = (STAT == 0 .AND. TRIM(ENV_VAL) == '1')
    IF (.NOT. ENABLED) RETURN

    OPEN(UNIT=UNIT_DUMP, FILE='tr_regress.dat', &
         STATUS='REPLACE', ACTION='WRITE', IOSTAT=IOERR)
    IF (IOERR /= 0) THEN
       WRITE(6,*) 'XX trregress: cannot open tr_regress.dat, IOSTAT=', IOERR
       RETURN
    END IF

    WRITE(UNIT_DUMP, '(A)')         '# TASK/TR regression dump (format v1)'
    WRITE(UNIT_DUMP, '(A,I0)')      'NT=',     NT
    WRITE(UNIT_DUMP, '(A,I0)')      'NRMAX=',  NRMAX
    WRITE(UNIT_DUMP, '(A,I0)')      'NSMAX=',  NSMAX
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'T=',      T
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'WPT=',    WPT
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'AJT=',    AJT
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'Q0=',     Q0
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'BETA0=',  BETA0
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'BETAP0=', BETAP0
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'BETAA=',  BETAA
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'BETAN=',  BETAN
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'TAUE1=',  TAUE1
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'TAUE2=',  TAUE2
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'ZEFF0=',  ZEFF0
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'ALI=',    ALI
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'RQ1=',    RQ1

    WRITE(UNIT_DUMP, '(A)') '# profile columns: NR RN(NR,1:NSMAX) RT(NR,1:NSMAX) AJ(NR) QP(NR)'
    DO NR = 1, NRMAX
       WRITE(UNIT_DUMP, '(I5)', ADVANCE='NO') NR
       DO NS = 1, NSMAX
          WRITE(UNIT_DUMP, '(1X,1PE24.16)', ADVANCE='NO') RN(NR,NS)
       END DO
       DO NS = 1, NSMAX
          WRITE(UNIT_DUMP, '(1X,1PE24.16)', ADVANCE='NO') RT(NR,NS)
       END DO
       WRITE(UNIT_DUMP, '(1X,1PE24.16,1X,1PE24.16)') AJ(NR), QP(NR)
    END DO

    CLOSE(UNIT_DUMP)
  END SUBROUTINE tr_regress_dump_if_enabled

END MODULE trregress
```

注: Task 2 Step 2 で一部変数が TRCOMM に存在しないと分かった場合は、ここの `USE TRCOMM, ONLY: ...` リストと対応する `WRITE` 行を削除する（ビルドエラー回避）。

- [ ] **Step 3: `tr/Makefile` の SRCS に trregress.f90 を追加**

`tr/Makefile` の `SRCS=` 定義を修正。`trloop.f90` より前に来るように挿入する（Fortran の module 依存のため）。

変更前の該当行（例）:
```
SRCS=trinit.f90 trparm.f90 trview.f90 \
     trmetric.f90 trprof.f90 trprep.f90 \
     trufsub.f90 tr_ufile_task.f90 tr_ufile_topics.f90 trufile.f90 \
     trfile.f90 trhelp.f90 \
     trexec.f90 trcalc.f90 \
     tradat.f90 trcdbm.f90 trmodels.f90 trcoef.f90 tritg.f90 \
     trrslt.f90 trpnb.f90 trprf.f90 trpnf.f90 trpel.f90 trpsc.f90 trmdlt.f90 \
     trgout.f90 trgrar.f90 trgrat.f90 trgrap.f90 trgrae.f90 \
     trgrad.f90 trgram.f90 trgsub.f90 trfout.f90 \
     trloop.f90 trmenu.f90
```

変更後: `trfout.f90 \` の次の行（`trloop.f90 trmenu.f90` のあるライン）を以下に変更:
```
     trfout.f90 trregress.f90 \
     trloop.f90 trmenu.f90
```

- [ ] **Step 4: `tr/trloop.f90` を修正してフックを追加**

`tr/trloop.f90` の `USE libitp` 付近の USE 文群に以下の 1 行を追加:

```fortran
      USE trregress, ONLY : tr_regress_dump_if_enabled
```

そして `9000` ラベルの後、`RETURN` 直前に以下の 1 行を挿入:

```fortran
 9000 IF(MDLUF.EQ.1.OR.MDLUF.EQ.3) THEN
         RIPS=RIP
         RIPE=RIP
      ELSE
         RIPS=RIPE
      ENDIF
      CALL tr_regress_dump_if_enabled   ! Phase 0 regression dump (env-guarded)
      RETURN
```

- [ ] **Step 5: TR をリビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/tr
make 2>&1 | tail -10
```
Expected: `trregress.f90` のコンパイルが実行され、`tr2` バイナリが更新される。エラーなし。

- [ ] **Step 6: 通常実行では dump が作られないことを確認（副作用ゼロ検証）**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
rm -f test_output/tr_iter01/tr_regress.dat
unset TR_REGRESS_DUMP
./run_tests.sh tr_iter01
ls -la test_output/tr_iter01/tr_regress.dat 2>&1 | head -3
```
Expected: `tr_regress.dat` は **作られない**（`No such file or directory`）。テストは従来通り PASS。

- [ ] **Step 7: 環境変数を立てると dump が出ることを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run/test_output/tr_iter01
TR_REGRESS_DUMP=1 timeout 120 /home/k-yoshimi/program/task/tr/tr2 \
    < /home/k-yoshimi/program/task/test_run/inputs/tr_iter01.in > out.log 2>&1
ls -la tr_regress.dat
head -25 tr_regress.dat
tail -5 tr_regress.dat
```
Expected:
- `tr_regress.dat` が存在する。
- 先頭行は `# TASK/TR regression dump (format v1)`。
- スカラー行が `1.xxxxxxxxxxxxxxxxE+nn` 形式で並んでいる。
- 末尾に NRMAX 行分のプロファイルデータ。

- [ ] **Step 8: 同一入力を 2 回走らせて dump が bit-exact に一致することを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run/test_output/tr_iter01
TR_REGRESS_DUMP=1 timeout 120 /home/k-yoshimi/program/task/tr/tr2 \
    < /home/k-yoshimi/program/task/test_run/inputs/tr_iter01.in > /dev/null 2>&1
cp tr_regress.dat /tmp/dump_run1.dat
TR_REGRESS_DUMP=1 timeout 120 /home/k-yoshimi/program/task/tr/tr2 \
    < /home/k-yoshimi/program/task/test_run/inputs/tr_iter01.in > /dev/null 2>&1
diff /tmp/dump_run1.dat tr_regress.dat
echo "diff exit=$?"
```
Expected: `diff` の出力が空、`exit=0`。run-to-run で完全一致。

もし差異があった場合は Task 2 で設定した `1e-10` 許容誤差を `1e-8` 程度に緩めること（Task 13 で最終確認）。

- [ ] **Step 9: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add tr/trregress.f90 tr/trloop.f90 tr/Makefile
git commit -m "feat(tr): add env-guarded high-precision dump for regression tests"
```

---

## Task 4: 指標抽出スクリプト `extract_tr_metrics.py` を書く

**Files:**
- Create: `test_run/scripts/extract_tr_metrics.py`
- Create: `test_run/scripts/tests/test_extract_tr_metrics.py`
- Create: `test_run/scripts/tests/fixtures/sample_tr_regress.dat`

- [ ] **Step 1: サンプル fixture を作成**

作成: `test_run/scripts/tests/fixtures/sample_tr_regress.dat`

内容（Task 3 の dump 形式に準拠した最小サンプル。NRMAX=2, NSMAX=2）:
```
# TASK/TR regression dump (format v1)
NT=100
NRMAX=2
NSMAX=2
T=2.0000000000000000E+00
WPT=4.1130000000000000E+01
AJT=1.5451000000000000E+01
Q0=5.7900000000000000E-01
BETA0=1.2300000000000000E-02
BETAP0=8.9000000000000004E-02
BETAA=2.3400000000000000E-03
BETAN=4.5600000000000003E-02
TAUE1=2.2650000000000001E+00
TAUE2=2.1000000000000001E+00
ZEFF0=1.5000000000000000E+00
ALI=7.5000000000000000E-01
RQ1=1.8000000000000000E+00
# profile columns: NR RN(NR,1:NSMAX) RT(NR,1:NSMAX) AJ(NR) QP(NR)
    1  7.0000000000000007E-01  3.1500000000000000E-01  4.5650000000000004E+00  4.2750000000000004E+00  1.5451000000000000E+01  5.7900000000000000E-01
    2  6.5000000000000002E-01  3.0000000000000004E-01  4.2000000000000002E+00  3.9000000000000004E+00  1.4000000000000000E+01  6.5000000000000002E-01
```

- [ ] **Step 2: 失敗するテストを書く**

作成: `test_run/scripts/tests/test_extract_tr_metrics.py`

```python
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "extract_tr_metrics.py"
FIXTURE = Path(__file__).parent / "fixtures" / "sample_tr_regress.dat"


def run_extract(dump_path: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(dump_path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def test_extracts_scalars():
    data = run_extract(FIXTURE)
    assert data["NT"] == 100
    assert data["NRMAX"] == 2
    assert data["NSMAX"] == 2
    assert data["scalars"]["T"] == 2.0
    assert data["scalars"]["WPT"] == 41.13
    assert data["scalars"]["Q0"] == 0.579
    assert "BETA0" in data["scalars"]
    assert "ALI" in data["scalars"]


def test_extracts_profile_rows():
    data = run_extract(FIXTURE)
    prof = data["profile"]
    assert len(prof) == 2
    # row 1: NR=1, RN (2 species), RT (2 species), AJ, QP
    row = prof[0]
    assert row["NR"] == 1
    assert len(row["RN"]) == 2
    assert len(row["RT"]) == 2
    assert row["RN"][0] == 0.7
    assert row["AJ"] == 15.451
    assert row["QP"] == 0.579


def test_rejects_incomplete_dump(tmp_path):
    incomplete = tmp_path / "bad.dat"
    incomplete.write_text("# TASK/TR regression dump (format v1)\nNT=1\n")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(incomplete)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
```

- [ ] **Step 3: テストを走らせて失敗を確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run/scripts
python3 -m pytest tests/test_extract_tr_metrics.py -v
```
Expected: FAIL（`extract_tr_metrics.py` が存在しないため）。

- [ ] **Step 4: スクリプト本体を実装**

作成: `test_run/scripts/extract_tr_metrics.py`

```python
#!/usr/bin/env python3
"""Convert tr_regress.dat into a JSON for regression comparison.

Usage:
    extract_tr_metrics.py path/to/tr_regress.dat
Output:
    JSON to stdout with keys:
        NT (int), NRMAX (int), NSMAX (int),
        scalars (dict[str,float]),
        profile (list[dict]) — one dict per radial point.
"""
import argparse
import json
import re
import sys
from pathlib import Path


SCALAR_KEYS = {
    "T", "WPT", "AJT", "Q0", "BETA0", "BETAP0", "BETAA", "BETAN",
    "TAUE1", "TAUE2", "ZEFF0", "ALI", "RQ1",
}
RE_PROFILE_HEADER = re.compile(r"^#\s*profile columns:")


def parse(dump_path: Path) -> dict:
    lines = dump_path.read_text().splitlines()
    result = {"scalars": {}, "profile": []}
    in_profile = False
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if RE_PROFILE_HEADER.match(line):
            in_profile = True
            continue
        if line.startswith("#"):
            continue
        if not in_profile:
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            if key in ("NT", "NRMAX", "NSMAX"):
                result[key] = int(val)
            elif key in SCALAR_KEYS:
                result["scalars"][key] = float(val)
            else:
                pass  # ignore unknown scalars
        else:
            parts = line.split()
            if len(parts) < 4:
                continue
            nsmax = result.get("NSMAX", 0)
            if nsmax <= 0:
                raise SystemExit("profile row encountered before NSMAX")
            expected = 1 + 2 * nsmax + 2  # NR + RN(NSMAX) + RT(NSMAX) + AJ + QP
            if len(parts) != expected:
                raise SystemExit(
                    f"malformed profile row (expected {expected} cols, got {len(parts)}): {raw}"
                )
            nr = int(parts[0])
            rn = [float(x) for x in parts[1 : 1 + nsmax]]
            rt = [float(x) for x in parts[1 + nsmax : 1 + 2 * nsmax]]
            aj = float(parts[1 + 2 * nsmax])
            qp = float(parts[2 + 2 * nsmax])
            result["profile"].append({"NR": nr, "RN": rn, "RT": rt, "AJ": aj, "QP": qp})
    # sanity check
    for k in ("NT", "NRMAX", "NSMAX"):
        if k not in result:
            raise SystemExit(f"missing header field: {k}")
    if len(result["profile"]) != result["NRMAX"]:
        raise SystemExit(
            f"profile row count {len(result['profile'])} != NRMAX {result['NRMAX']}"
        )
    if not result["scalars"]:
        raise SystemExit("no scalars parsed")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dump", type=Path)
    args = ap.parse_args()
    json.dump(parse(args.dump), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: 実行権限を付与してテストを再実行**

Run:
```bash
chmod +x /home/k-yoshimi/program/task/test_run/scripts/extract_tr_metrics.py
cd /home/k-yoshimi/program/task/test_run/scripts
python3 -m pytest tests/test_extract_tr_metrics.py -v
```
Expected: 3 tests PASS。

- [ ] **Step 6: 実 dump で動作確認**

Run:
```bash
# Task 3 Step 7 で生成した dump を利用
python3 test_run/scripts/extract_tr_metrics.py \
    test_run/test_output/tr_iter01/tr_regress.dat | head -30
```
Expected: NT/NRMAX/NSMAX と scalars、profile の先頭数行が JSON で出力される。

- [ ] **Step 7: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/scripts/extract_tr_metrics.py test_run/scripts/tests/
git commit -m "test(tr): add metric extractor reading tr_regress.dat"
```

---

## Task 5: 比較スクリプト `compare_metrics.py` を書く

**Files:**
- Create: `test_run/scripts/compare_metrics.py`
- Create: `test_run/scripts/tests/test_compare_metrics.py`

- [ ] **Step 1: 失敗するテストを書く**

作成: `test_run/scripts/tests/test_compare_metrics.py`

```python
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "compare_metrics.py"


def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj))


def run_compare(actual: Path, baseline: Path, tol: str = "1e-10") -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT),
         "--baseline", str(baseline),
         "--actual", str(actual),
         "--tolerance", tol],
        capture_output=True, text=True,
    )


def _sample() -> dict:
    return {
        "NT": 100, "NRMAX": 2, "NSMAX": 2,
        "scalars": {
            "T": 2.0, "WPT": 41.13, "AJT": 15.451, "Q0": 0.579,
            "BETA0": 0.0123, "BETAP0": 0.089, "BETAA": 0.00234, "BETAN": 0.0456,
            "TAUE1": 2.265, "TAUE2": 2.1, "ZEFF0": 1.5, "ALI": 0.75, "RQ1": 1.8,
        },
        "profile": [
            {"NR": 1, "RN": [0.7, 0.315], "RT": [4.565, 4.275], "AJ": 15.451, "QP": 0.579},
            {"NR": 2, "RN": [0.65, 0.3], "RT": [4.2, 3.9],     "AJ": 14.0,   "QP": 0.65},
        ],
    }


def test_passes_on_identical(tmp_path):
    base = tmp_path / "base.json"
    act  = tmp_path / "act.json"
    write_json(base, _sample())
    write_json(act,  _sample())
    res = run_compare(act, base)
    assert res.returncode == 0, res.stderr


def test_fails_on_scalar_drift(tmp_path):
    base = tmp_path / "base.json"
    act  = tmp_path / "act.json"
    write_json(base, _sample())
    drifted = _sample()
    drifted["scalars"]["WPT"] = 41.13 * (1.0 + 1e-7)   # > 1e-10
    write_json(act, drifted)
    res = run_compare(act, base, tol="1e-10")
    assert res.returncode != 0
    assert "WPT" in res.stdout


def test_passes_on_drift_within_tolerance(tmp_path):
    base = tmp_path / "base.json"
    act  = tmp_path / "act.json"
    write_json(base, _sample())
    close = _sample()
    close["scalars"]["WPT"] = 41.13 * (1.0 + 1e-13)   # < 1e-10
    write_json(act, close)
    res = run_compare(act, base, tol="1e-10")
    assert res.returncode == 0, res.stderr


def test_fails_on_profile_drift(tmp_path):
    base = tmp_path / "base.json"
    act  = tmp_path / "act.json"
    write_json(base, _sample())
    drifted = _sample()
    drifted["profile"][1]["RT"][0] = 4.2 * (1.0 + 1e-5)
    write_json(act, drifted)
    res = run_compare(act, base, tol="1e-10")
    assert res.returncode != 0
    assert "RT" in res.stdout


def test_fails_when_dimensions_differ(tmp_path):
    base = tmp_path / "base.json"
    act  = tmp_path / "act.json"
    write_json(base, _sample())
    short = _sample()
    short["NRMAX"] = 1
    short["profile"] = short["profile"][:1]
    write_json(act, short)
    res = run_compare(act, base)
    assert res.returncode != 0
```

- [ ] **Step 2: テストを走らせて失敗を確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run/scripts
python3 -m pytest tests/test_compare_metrics.py -v
```
Expected: FAIL（スクリプト未作成）。

- [ ] **Step 3: スクリプト本体を実装**

作成: `test_run/scripts/compare_metrics.py`

```python
#!/usr/bin/env python3
"""Compare two TR metric JSONs within a relative tolerance.

Expects the schema produced by extract_tr_metrics.py:
    NT, NRMAX, NSMAX, scalars (dict), profile (list of dicts).

Exit code 0 on match, 1 on mismatch.
"""
import argparse
import json
import math
import sys
from pathlib import Path


def _rel_err(a: float, b: float) -> float:
    denom = max(abs(a), abs(b), 1e-300)
    return abs(a - b) / denom


def _check_scalar(label: str, bv: float, av: float, tol: float, out: list) -> None:
    if math.isnan(bv) or math.isnan(av):
        out.append(f"{label}: NaN (baseline={bv} actual={av})")
        return
    e = _rel_err(bv, av)
    if e > tol:
        out.append(f"{label}: baseline={bv!r} actual={av!r} rel_err={e:.3e} > tol={tol:.3e}")


def compare(baseline: dict, actual: dict, tol: float) -> list:
    errors = []
    for k in ("NT", "NRMAX", "NSMAX"):
        if baseline.get(k) != actual.get(k):
            errors.append(f"{k}: baseline={baseline.get(k)} actual={actual.get(k)}")
    if errors:
        return errors  # dimensions differ; further comparison is meaningless

    b_scalars = baseline.get("scalars", {})
    a_scalars = actual.get("scalars", {})
    for k in sorted(set(b_scalars) | set(a_scalars)):
        if k not in b_scalars or k not in a_scalars:
            errors.append(f"scalars.{k}: missing")
            continue
        _check_scalar(f"scalars.{k}", float(b_scalars[k]), float(a_scalars[k]), tol, errors)

    b_prof = baseline.get("profile", [])
    a_prof = actual.get("profile", [])
    if len(b_prof) != len(a_prof):
        errors.append(f"profile length: baseline={len(b_prof)} actual={len(a_prof)}")
        return errors
    for i, (br, ar) in enumerate(zip(b_prof, a_prof)):
        if br.get("NR") != ar.get("NR"):
            errors.append(f"profile[{i}].NR: baseline={br.get('NR')} actual={ar.get('NR')}")
            continue
        for field in ("AJ", "QP"):
            _check_scalar(f"profile[{i}].{field}", float(br[field]), float(ar[field]), tol, errors)
        for field in ("RN", "RT"):
            bv_list = br.get(field, [])
            av_list = ar.get(field, [])
            if len(bv_list) != len(av_list):
                errors.append(f"profile[{i}].{field}: length differ ({len(bv_list)} vs {len(av_list)})")
                continue
            for j, (bv, av) in enumerate(zip(bv_list, av_list)):
                _check_scalar(f"profile[{i}].{field}[{j}]", float(bv), float(av), tol, errors)
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--actual", type=Path, required=True)
    ap.add_argument("--tolerance", type=float, default=1e-10)
    args = ap.parse_args()

    baseline = json.loads(args.baseline.read_text())
    actual   = json.loads(args.actual.read_text())
    errors = compare(baseline, actual, args.tolerance)
    if errors:
        print(f"FAIL: {len(errors)} mismatch(es) (tolerance={args.tolerance:g})")
        for e in errors[:50]:
            print(f"  - {e}")
        if len(errors) > 50:
            print(f"  ... and {len(errors) - 50} more")
        return 1
    print(f"OK: metrics match within tol={args.tolerance:g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: テスト再実行**

Run:
```bash
chmod +x /home/k-yoshimi/program/task/test_run/scripts/compare_metrics.py
cd /home/k-yoshimi/program/task/test_run/scripts
python3 -m pytest tests/test_compare_metrics.py -v
```
Expected: 5 tests PASS。

- [ ] **Step 5: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/scripts/compare_metrics.py test_run/scripts/tests/test_compare_metrics.py
git commit -m "test(tr): add metric comparison tool (default tolerance 1e-10)"
```

---

## Task 6: M0904 入力ケースを追加

**Files:**
- Create: `test_run/inputs/tr_m0904.in`

**理由:** `tr.M0904.in` は `modelg=2`（解析ジオメトリ）なので EQ に依存せず、EQ と別系統の物理モデルをカバーできる。

- [ ] **Step 1: 既存 `tr/in/tr.M0904.in` をベースに短縮版を作る**

作成: `test_run/inputs/tr_m0904.in`

```
0
f
tr.M0904.gs
c
   modelg=2
   RR=8.481D0
   RA=2.574D0
   RKAP=1.816D0
   RDLT=0.3478D0
   BB=5.953D0
   NSMAX=4
   PN=0.1D0,0.045D0,0.045D0,0.005D0
   PNS=0.01D0,0.0045D0,0.0045D0,0.0005D0
   PT=1.0D0,1.0D0,1.0D0,1.0D0
   PTS=0.1D0,0.1D0,0.1D0,0.1D0
   PROFN2=0.15D0
   MDNCLS=1
   MDLNF=1
   PNBCD=1.0D0
   PNBR0=1.0D0
   DT=0.02D0
   NTSTEP=50
   NTMAX=50
   RIPS=2.D0
   RIPE=3.D0
r
q
```

注: `NTSTEP`/`NTMAX` は CI 高速化のため 50 に短縮。元の `tr.M0904.in` の他のパラメータは CI 上で妥当なものをコピー。

- [ ] **Step 2: 手動で走らせて CLOSED を確認**

Run:
```bash
cd /home/k-yoshimi/program/task
mkdir -p /tmp/tr_m0904_probe
cd /tmp/tr_m0904_probe
timeout 180 /home/k-yoshimi/program/task/tr/tr2 \
  < /home/k-yoshimi/program/task/test_run/inputs/tr_m0904.in > out.log 2>&1
grep -c "CLOSED" out.log
tail -20 out.log
```
Expected: `CLOSED` が 1 以上見つかる。数値行 `# T: ... WP: ...` が複数出る。

- [ ] **Step 3: 指標抽出が動くことを確認**

Run:
```bash
python3 /home/k-yoshimi/program/task/test_run/scripts/extract_tr_metrics.py /tmp/tr_m0904_probe/out.log
```
Expected: `time_series` に複数エントリ、`closed: true`。

- [ ] **Step 4: コミット**

```bash
cd /home/k-yoshimi/program/task
git add test_run/inputs/tr_m0904.in
git commit -m "test(tr): add M0904 regression input (modelg=2, EQ-independent)"
```

---

## Task 7: TST-2 入力ケースを追加

**Files:**
- Create: `test_run/inputs/tr_tst2.in`

**前提:** `tr/in/tr2.TST-2.in` は `modelg=3` と `KNAMEQ='eqdata.TST-2'` を使い、EQ モジュールの出力に依存する。また複雑な対話シーケンスが含まれるため、回帰テスト用にはシンプルな run-once + quit に簡略化する。

- [ ] **Step 1: `eq_tst2` が存在することを確認**

Run:
```bash
grep "^eq_tst2" /home/k-yoshimi/program/task/test_run/test_definitions.conf
```
Expected: `eq_tst2:eq:in/eq.TST-2.in:none:60:TST-2 equilibrium calculation` の行があること。これがないと TR の依存を解決できない。

- [ ] **Step 2: 簡略化 TST-2 入力を作成**

作成: `test_run/inputs/tr_tst2.in`

`tr/in/tr2.TST-2.in` 前半の物理パラメータを温存し、対話的な graphic/二回目 run を削除して run-once + quit にした版:

```
0
f
tr2.TST-2.gs
c
   modelg=3
   KNAMEQ='eqdata.TST-2'
   NSMAX=2
   PA(2)=1.D0
   PZ(2)=1.D0
   PN =0.010D0,0.010D0
   PNS=0.001D0,0.001D0
   PT =0.010D0,0.0010D0
   PTS=0.001D0,0.0001D0
   PROFN1=2.D0
   PROFN2=1.D0
   MDLIMP=3
   PNC=0.00001D0
   PLHCD=0.D0
   PLHR0=0.15D0
   PLHRW=0.05D0
   PLHNPR=4.D0
   RIPS=0.015
   RIPE=0.015
   NTSTEP=1
   NGTSTP=1
   NGRSTP=10
   DT=1.D-5
   NTMAX=10
   PLHTOT=0.D0
r
q
```

変更点:
- 元ファイルの `v` (view) と 2 回目の `r ... c ... c g t6 t7 ...` ブロックを削除。
- `NTMAX=10` のまま（もともと短い）維持。
- `q` で即終了。

- [ ] **Step 3: 手動スモーク: EQ 依存を満たしてから TR を走らせる**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh eq_tst2
# 成功したら eqdata.TST-2 が test_output/eq_tst2/ に生成される
mkdir -p /tmp/tr_tst2_probe
cp test_output/eq_tst2/eqdata.TST-2 /tmp/tr_tst2_probe/
cd /tmp/tr_tst2_probe
timeout 120 /home/k-yoshimi/program/task/tr/tr2 \
    < /home/k-yoshimi/program/task/test_run/inputs/tr_tst2.in > out.log 2>&1
grep -c "CLOSED" out.log
grep -E "# T:" out.log | head -5
```
Expected: `CLOSED` が少なくとも 1 個。時刻行 `# T: ... WP: ... TAUE: ... Q0: ...` が複数行出る。

- [ ] **Step 4: 時刻行が抽出できない場合のフォールバック判断**

TST-2 は電子温度が非常に低く（`PT=0.010` keV）、出力書式が ITER/M0904 と異なる可能性がある。
抽出結果が空だった場合:
- 代わりに `test_run/inputs/tr_iter01_long.in` を作る：既存 `tr_iter01.in` をコピーし `NTSTEP=200, NTMAX=200` に変更。
- `test_definitions.conf` には `tr_iter01_long:tr:@inputs/tr_iter01_long.in:eq_iter01:300:ITER transport (long run)` を追加。
- TST-2 はスキップし、本 Task 6 のコミットメッセージを "test(tr): add iter01_long as 3rd regression case (TST-2 skipped)" にする。

- [ ] **Step 5: コミット**

```bash
cd /home/k-yoshimi/program/task
git add test_run/inputs/tr_tst2.in  # または tr_iter01_long.in
git commit -m "test(tr): add TST-2 regression input"
```

---

## Task 8: 回帰判定ラッパ `check_regression.sh` を書く

**Files:**
- Create: `test_run/scripts/check_regression.sh`
- Create: `test_run/scripts/tests/test_check_regression.bats` （省略可: bats が無ければ手動テストでよい）

- [ ] **Step 1: スクリプトを作成**

作成: `test_run/scripts/check_regression.sh`

```bash
#!/bin/bash
#
# check_regression.sh <test_name> <test_output_dir> <baselines_dir> [tolerance] [--generate-baseline]
#
# Reads <test_output_dir>/tr_regress.dat (produced when tr2 is run with
# TR_REGRESS_DUMP=1), extracts metrics to JSON, and compares with
# <baselines_dir>/<test_name>/metrics.json. Exits 0 on match, 1 on mismatch,
# 2 on missing dump, 3 on missing baseline.
#
# With --generate-baseline, the extracted JSON is written as baseline instead.
#
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_NAME="${1:?usage: $0 <test_name> <output_dir> <baselines_dir> [tol] [--generate-baseline]}"
OUTPUT_DIR="${2:?}"
BASELINES_DIR="${3:?}"
TOL="${4:-1e-10}"
MODE="${5:-compare}"

DUMP="$OUTPUT_DIR/tr_regress.dat"
METRICS_ACTUAL="$OUTPUT_DIR/metrics.json"
METRICS_BASE="$BASELINES_DIR/$TEST_NAME/metrics.json"

if [[ ! -f "$DUMP" ]]; then
    echo "check_regression: dump not found: $DUMP" >&2
    echo "  did the test run with TR_REGRESS_DUMP=1 exported?" >&2
    exit 2
fi

if ! python3 "$SCRIPT_DIR/extract_tr_metrics.py" "$DUMP" > "$METRICS_ACTUAL"; then
    echo "check_regression: failed to parse $DUMP" >&2
    exit 2
fi

if [[ "$MODE" == "--generate-baseline" ]]; then
    mkdir -p "$(dirname "$METRICS_BASE")"
    cp "$METRICS_ACTUAL" "$METRICS_BASE"
    echo "Baseline written: $METRICS_BASE"
    exit 0
fi

if [[ ! -f "$METRICS_BASE" ]]; then
    echo "check_regression: baseline not found: $METRICS_BASE" >&2
    echo "  run with --generate-baseline to create it." >&2
    exit 3
fi

python3 "$SCRIPT_DIR/compare_metrics.py" \
    --baseline "$METRICS_BASE" \
    --actual "$METRICS_ACTUAL" \
    --tolerance "$TOL"
```

- [ ] **Step 2: 実行権限**

Run:
```bash
chmod +x /home/k-yoshimi/program/task/test_run/scripts/check_regression.sh
```

- [ ] **Step 3: 手動スモークテスト（dump 付きで実行しベースライン生成）**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
rm -rf test_output/tr_iter01
# 既存 run_tests.sh はまだ env var を設定しない。ここでは手動で run。
mkdir -p test_output/tr_iter01
cp test_output/eq_iter01/eqdata.ITER01 test_output/tr_iter01/ 2>/dev/null || {
    ./run_tests.sh eq_iter01   # 依存テストを先に走らせる
    cp test_output/eq_iter01/eqdata.ITER01 test_output/tr_iter01/
}
cd test_output/tr_iter01
TR_REGRESS_DUMP=1 timeout 120 /home/k-yoshimi/program/task/tr/tr2 \
    < /home/k-yoshimi/program/task/test_run/inputs/tr_iter01.in > output.log 2>&1
ls -la tr_regress.dat
cd /home/k-yoshimi/program/task/test_run
./scripts/check_regression.sh tr_iter01 \
    "$(pwd)/test_output/tr_iter01" \
    "$(pwd)/baselines" \
    "1e-10" "--generate-baseline"
head -30 baselines/tr_iter01/metrics.json
```
Expected: `Baseline written: .../baselines/tr_iter01/metrics.json` と JSON の中身が確認できる。

- [ ] **Step 4: 手動スモークテスト（比較）**

Run:
```bash
./scripts/check_regression.sh tr_iter01 \
    "$(pwd)/test_output/tr_iter01" \
    "$(pwd)/baselines" "1e-10"
```
Expected: `OK: metrics match within tol=1e-10`。

- [ ] **Step 5: 故意に壊して FAIL することを確認**

Run:
```bash
cp baselines/tr_iter01/metrics.json /tmp/saved.json
python3 -c "
import json, pathlib
p = pathlib.Path('baselines/tr_iter01/metrics.json')
d = json.loads(p.read_text())
d['scalars']['WPT'] *= 1.5
p.write_text(json.dumps(d))
"
./scripts/check_regression.sh tr_iter01 \
    "$(pwd)/test_output/tr_iter01" \
    "$(pwd)/baselines" "1e-10"
echo "exit=$?"
# restore
cp /tmp/saved.json baselines/tr_iter01/metrics.json
```
Expected: `FAIL: ... scalars.WPT: baseline=... actual=... rel_err=...`。`exit=1`。

- [ ] **Step 6: コミット**

```bash
cd /home/k-yoshimi/program/task
git add test_run/scripts/check_regression.sh
git commit -m "test(tr): add regression check wrapper script"
```

---

## Task 9: `test_definitions.conf` に新規テストを追加

**Files:**
- Modify: `test_run/test_definitions.conf`

- [ ] **Step 1: 設定ファイルを編集**

追加する行（既存の `tr_iter01` 行の下）:

```
tr_m0904:tr:@inputs/tr_m0904.in:none:120:M0904 transport (analytic geometry)
tr_tst2:tr:@inputs/tr_tst2.in:none:120:TST-2 transport
```

Task 6 で TST-2 をスキップした場合は代わりに:
```
tr_iter01_long:tr:@inputs/tr_iter01_long.in:eq_iter01:180:ITER transport (long)
```

- [ ] **Step 2: 一覧表示で追加が見えることを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh -l
```
Expected: `tr_m0904` と `tr_tst2`（または `tr_iter01_long`）が一覧に出る。

- [ ] **Step 3: 全 TR テストを走らせて CLOSED を確認**

Run:
```bash
./run_tests.sh tr_iter01 tr_m0904 tr_tst2
```
Expected: すべて `PASS`。

- [ ] **Step 4: コミット**

```bash
cd /home/k-yoshimi/program/task
git add test_run/test_definitions.conf
git commit -m "test(tr): register M0904 and TST-2 regression cases"
```

---

## Task 10: `run_tests.sh` に回帰チェック統合

**Files:**
- Modify: `test_run/run_tests.sh`

**目的:** (1) TR モジュールの実行時に `TR_REGRESS_DUMP=1` をエクスポートして dump を有効化し、(2) CLOSED 判定で PASS となった後に `check_regression.sh` を呼んでベースラインと比較する。不一致なら RED に落とす。

- [ ] **Step 1: TR 実行コマンドに環境変数を追加**

`run_tests.sh` の `run_single_test` 関数内、`tr2` バイナリ実行部分 (行 299 / 302 付近の `timeout "$timeout" "$binary" < "$full_input_path"` を、TR の時のみ環境変数付きで実行するように変更。

変更前:
```bash
    if [[ $VERBOSE -eq 1 ]]; then
        echo ""
        timeout "$timeout" "$binary" < "$full_input_path" 2>&1 | tee "$log_file"
        local exit_code=${PIPESTATUS[0]}
    else
        timeout "$timeout" "$binary" < "$full_input_path" > "$log_file" 2>&1
        local exit_code=$?
    fi
```

変更後:
```bash
    # For TR module, enable regression dump (env-guarded inside trregress.f90).
    local tr_env=()
    if [[ "$module" == "tr" ]]; then
        tr_env=(env TR_REGRESS_DUMP=1)
    fi

    if [[ $VERBOSE -eq 1 ]]; then
        echo ""
        "${tr_env[@]}" timeout "$timeout" "$binary" < "$full_input_path" 2>&1 | tee "$log_file"
        local exit_code=${PIPESTATUS[0]}
    else
        "${tr_env[@]}" timeout "$timeout" "$binary" < "$full_input_path" > "$log_file" 2>&1
        local exit_code=$?
    fi
```

- [ ] **Step 2: CLOSED 判定後に回帰チェックを挿入**

同じファイルの `elif grep -q "CLOSED" "$log_file" 2>/dev/null; then` ブロックを以下のように変更:

変更前:
```bash
    elif grep -q "CLOSED" "$log_file" 2>/dev/null; then
        # CLOSED message found - calculation completed successfully
        if [[ $exit_code -ne 0 ]]; then
            echo -e "${GREEN}PASS${NC} (warning: exit code $exit_code)"
        else
            echo -e "${GREEN}PASS${NC}"
        fi
        PASSED=$((PASSED + 1))
        COMPLETED_TESTS[$test_name]=1
```

変更後:
```bash
    elif grep -q "CLOSED" "$log_file" 2>/dev/null; then
        # CLOSED message found - calculation completed successfully.
        # For TR module, also verify numerical metrics against baseline.
        local reg_ok=1
        if [[ "$module" == "tr" ]]; then
            if ! "$SCRIPT_DIR/scripts/check_regression.sh" \
                    "$test_name" "$test_dir" "$SCRIPT_DIR/baselines" "1e-10" \
                    > "$test_dir/regression.log" 2>&1; then
                reg_ok=0
            fi
        fi
        if [[ $reg_ok -eq 0 ]]; then
            echo -e "${RED}REGRESSION${NC} (metrics drift; see $test_dir/regression.log)"
            FAILED=$((FAILED + 1))
        elif [[ $exit_code -ne 0 ]]; then
            echo -e "${GREEN}PASS${NC} (warning: exit code $exit_code)"
            PASSED=$((PASSED + 1))
            COMPLETED_TESTS[$test_name]=1
        else
            echo -e "${GREEN}PASS${NC}"
            PASSED=$((PASSED + 1))
            COMPLETED_TESTS[$test_name]=1
        fi
```

- [ ] **Step 3: シェル構文チェック**

Run:
```bash
bash -n /home/k-yoshimi/program/task/test_run/run_tests.sh
```
Expected: エラーなし。

- [ ] **Step 4: ベースラインがまだ無い状態で失敗することを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
rm -f baselines/tr_m0904/metrics.json baselines/tr_tst2/metrics.json 2>/dev/null || true
./run_tests.sh tr_m0904
```
Expected: `REGRESSION` が表示される（ベースライン無しなので exit 3）。

- [ ] **Step 5: dump ファイルが生成されていることを確認**

Run:
```bash
ls -la test_output/tr_m0904/tr_regress.dat
```
Expected: ファイルが存在し、サイズが数 KB〜。

- [ ] **Step 6: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/run_tests.sh
git commit -m "test(tr): enable TR_REGRESS_DUMP and wire regression check into run_tests.sh"
```

---

## Task 11: ベースラインを生成してコミット

**Files:**
- Create: `test_run/baselines/tr_iter01/metrics.json`
- Create: `test_run/baselines/tr_m0904/metrics.json`
- Create: `test_run/baselines/tr_tst2/metrics.json`

- [ ] **Step 1: 各テストを走らせて output を作成**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tr_iter01 tr_m0904 tr_tst2 2>&1 | tee /tmp/phase0_first_run.log
# REGRESSION になる（ベースライン無し）のが正常。CLOSED さえ出ればよい。
```
Expected: CLOSED は全て出ている。REGRESSION エラーになっていることをログで確認。

- [ ] **Step 2: ベースラインを一括生成**

Run:
```bash
for t in tr_iter01 tr_m0904 tr_tst2; do
    ./scripts/check_regression.sh "$t" \
        "$(pwd)/test_output/$t" \
        "$(pwd)/baselines" \
        "1e-10" "--generate-baseline"
done
ls -la baselines/tr_*/metrics.json
```
Expected: 3 件すべて `Baseline written: ...`。JSON が生成される。

- [ ] **Step 3: 再実行してすべて PASS になることを確認**

Run:
```bash
./run_tests.sh tr_iter01 tr_m0904 tr_tst2
```
Expected: すべて `PASS`。`Failed: 0`。

- [ ] **Step 4: run-to-run 再現性を確認（1e-10 が現実的か検証）**

Run:
```bash
# 2 回走らせて両方 PASS になることを確認
./run_tests.sh tr_iter01 tr_m0904 tr_tst2 && \
./run_tests.sh tr_iter01 tr_m0904 tr_tst2
```
Expected: 両実行とも全 PASS。

**もし REGRESSION になる場合（run-to-run 差が 1e-10 を超える場合）:**
- `regression.log` を見て最大誤差を把握。
- `run_tests.sh` の `"1e-10"` を `"1e-8"` に緩める（実測最大差 +1 桁を目安）。
- 緩和した理由を commit メッセージに記載。

- [ ] **Step 5: ベースラインをコミット**

```bash
cd /home/k-yoshimi/program/task
git add test_run/baselines/
git commit -m "test(tr): commit initial regression baselines (iter01, m0904, tst2)"
```

---

## Task 12: 運用ドキュメント `test_run/README.md` を書く

**Files:**
- Create: `test_run/README.md`

- [ ] **Step 1: README を作成**

作成: `test_run/README.md`

````markdown
# test_run — TASK モジュール 回帰テスト

`eq`, `tr`, `tx`, `fp` など TASK の各モジュールを、あらかじめ用意した入力で実行し、CLOSED メッセージと数値指標の両方でパス/フェイルを判定する仕組み。

## ディレクトリ構成

- `run_tests.sh`            — テストランナ
- `test_definitions.conf`   — テスト定義（`TEST_NAME:MODULE:INPUT:DEPENDS:TIMEOUT:DESC`）
- `inputs/`                 — モジュール用の短縮入力
- `test_output/<name>/`     — 実行ごとのログ・成果物・dump（gitignore 対象）
- `baselines/<name>/`       — 回帰判定用ゴールデン指標（**コミット対象**）
- `scripts/`
  - `extract_tr_metrics.py` — `tr_regress.dat` を JSON に変換
  - `compare_metrics.py`    — 2 指標 JSON を相対誤差で比較（デフォルト 1e-10）
  - `check_regression.sh`   — 抽出＋比較（または baseline 生成）

## 基本使用例

### 全テストを走らせる

    ./run_tests.sh

### 特定のテストのみ

    ./run_tests.sh tr_iter01 tr_m0904

### 詳細ログ

    ./run_tests.sh -v tr_iter01

## TR モジュールの回帰判定の仕組み

### 1. 高精度 dump の仕組み

TR 本体 (`tr/trregress.f90`) は、環境変数 `TR_REGRESS_DUMP=1` が設定されているときに限り、
計算ループ終了時点の主要グローバル量（`WPT, AJT, Q0, BETA0, TAUE1, ...` 等）と
プロファイル（`RN, RT, AJ, QP` を半径方向 NRMAX 点）を `tr_regress.dat` に
`1PE24.16` 書式で書き出す。

通常実行（環境変数未設定）では dump は生成されず、挙動は完全に従来通り。

### 2. 比較フロー

1. `run_tests.sh` は TR モジュールに対してだけ `TR_REGRESS_DUMP=1` をエクスポートして `tr/tr2` を実行。
2. stdout に `CLOSED` が出れば計算は成功。
3. 成功時、`scripts/check_regression.sh` が以下を行う:
    1. `extract_tr_metrics.py` が `tr_regress.dat` を JSON に変換し `test_output/<test>/metrics.json` に保存。
    2. `compare_metrics.py` が `baselines/<test>/metrics.json` と相対誤差 `1e-10` で比較。
4. 不一致なら `REGRESSION (metrics drift)` を出して FAIL。詳細は `test_output/<test>/regression.log`。

## ベースラインの更新方法

物理モデルや入力の意図的な変更でベースラインを更新するとき:

    ./run_tests.sh tr_iter01     # dump が test_output/tr_iter01/tr_regress.dat に出る
    ./scripts/check_regression.sh tr_iter01 \
        "$(pwd)/test_output/tr_iter01" \
        "$(pwd)/baselines" \
        "1e-10" "--generate-baseline"

変更差分をレビューしてから `baselines/<name>/metrics.json` を commit すること。

## 許容誤差について

- デフォルトは `1e-10`（dump は 16 桁精度なので十分余裕がある）。
- コンパイラ/最適化を変更すると run-to-run で 1e-10 を超える差が出る場合がある。その場合は許容誤差を `1e-8` 程度に緩める。
- 許容誤差は `run_tests.sh` 内の `check_regression.sh` 呼び出し行で指定している。

## dump を手動で再現する

デバッグで dump だけ欲しい場合:

    cd test_output/tr_iter01   # あるいは任意の作業ディレクトリ
    TR_REGRESS_DUMP=1 ../tr/tr2 < ../inputs/tr_iter01.in > out.log 2>&1
    cat tr_regress.dat

## よく使うトラブルシュート

- **`REGRESSION (metrics drift)`**: `test_output/<name>/regression.log` を確認。物理的に妥当な差分なのか、リファクタのバグなのかを切り分ける。
- **`check_regression: dump not found`**: 該当テストが TR モジュールで走っていない、または `TR_REGRESS_DUMP` がエクスポートされていない。
- **`SKIP (module not built)`**: 該当モジュールを `make` する（例: `cd tr && make`）。
- **`SKIP (input file not found)`**: `test_definitions.conf` のパスと、`inputs/` / `tr/in/` の実ファイル名を照合する。
````

- [ ] **Step 2: コミット**

```bash
cd /home/k-yoshimi/program/task
git add test_run/README.md
git commit -m "docs(test_run): document regression workflow"
```

---

## Task 13: test_output を gitignore

**Files:**
- Modify or Create: `test_run/.gitignore`

- [ ] **Step 1: 既存 `.gitignore` を確認**

Run:
```bash
ls -la /home/k-yoshimi/program/task/test_run/.gitignore 2>/dev/null
cat /home/k-yoshimi/program/task/.gitignore | grep -i test_output 2>/dev/null
```

- [ ] **Step 2: `test_run/.gitignore` を作成（存在しなければ）または追記**

作成/追記: `test_run/.gitignore`

```
test_output/
__pycache__/
*.pyc
scripts/tests/__pycache__/
```

- [ ] **Step 3: 状態確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git status test_run/
```
Expected: `test_output/` が untracked リストから消えている。`baselines/` は tracked のまま。

- [ ] **Step 4: コミット**

```bash
git add test_run/.gitignore
git commit -m "chore(test_run): ignore generated outputs"
```

---

## Task 14: 最終確認とブランチの push

**Files:**
- なし（検証のみ）

- [ ] **Step 1: 全 TR 回帰テストを連続 3 回走らせて全パスを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
for i in 1 2 3; do
    echo "=== run $i ==="
    ./run_tests.sh tr_iter01 tr_m0904 tr_tst2 || { echo "run $i FAILED"; break; }
done
```
Expected: 3 回とも `All tests passed!`。

- [ ] **Step 2: Python テスト群をまとめて走らせる**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run/scripts
python3 -m pytest tests/ -v
```
Expected: すべて PASS。

- [ ] **Step 3: 故意リファクタ疑似（微小な数値改変）で REGRESSION を検出できることを確認**

Run:
```bash
cd /home/k-yoshimi/program/task
# 一時バックアップ
cp tr/trcomm.f90 /tmp/trcomm.bak.f90
# 相対誤差 1e-3 レベルの小さな改変で検出されることを確認（1e-10 許容なら余裕で FAIL）
sed -i 's|REAL(rkind), PARAMETER :: RKEV = AEE\*1.D3|REAL(rkind), PARAMETER :: RKEV = AEE*1.0005D3|' tr/trcomm.f90
(cd tr && make 2>&1 | tail -3)
cd test_run
./run_tests.sh tr_iter01 || true
echo "---"
head -30 test_output/tr_iter01/regression.log
echo "---"
# リストア
cp /tmp/trcomm.bak.f90 /home/k-yoshimi/program/task/tr/trcomm.f90
(cd /home/k-yoshimi/program/task/tr && make 2>&1 | tail -3)
./run_tests.sh tr_iter01
```
Expected:
- 改変ビルド時: `REGRESSION` が出て、`regression.log` に `scalars.WPT` や `scalars.TE*` などの mismatch が並ぶ。
- リストア後: `PASS`。

- [ ] **Step 4: ログ・仮ファイルを削除**

Run:
```bash
rm -f /tmp/trcomm.bak.f90 /tmp/saved.json /tmp/phase0_first_run.log
rm -rf /tmp/tr_m0904_probe /tmp/tr_tst2_probe
```

- [ ] **Step 5: ブランチを push して PR を作成（ユーザ承認後）**

ユーザに確認:
> Phase 0 の全タスクが完了し、回帰テスト 3 ケースがローカルで全て PASS します。ブランチ `feature/tr-regression-phase0` を push して PR を作成しますか？

ユーザから明示の承認を得てから:

```bash
cd /home/k-yoshimi/program/task
git push -u origin feature/tr-regression-phase0
gh pr create --title "test(tr): Phase 0 - regression test infrastructure" \
    --body "$(cat <<'EOF'
## Summary
- TR モジュールのリファクタリング前に、回帰テスト基盤を整備。
- `tr/trregress.f90` を追加。環境変数 `TR_REGRESS_DUMP=1` のときのみ高精度 dump (`1PE24.16`) を書き出す。通常実行は挙動不変。
- `test_run/` の Python スクリプトで dump から指標抽出・ベースライン比較（相対誤差 `1e-10`）。
- 対象ケース: `tr_iter01` (ITER), `tr_m0904` (analytic), `tr_tst2` (TST-2)。

## Test plan
- [x] 通常実行（環境変数なし）で `tr_regress.dat` が生成されないことを確認
- [x] `./run_tests.sh tr_iter01 tr_m0904 tr_tst2` が 3 連続で PASS
- [x] `python3 -m pytest test_run/scripts/tests/` が PASS
- [x] 故意の数値改変（例: RKEV の 0.05% 改変）で `REGRESSION` が検出される

本 PR は仕様書 `docs/superpowers/specs/2026-04-17-tr-refactoring-design.md` の Phase 0 に対応。

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## 受け入れ基準（Phase 0 完了判定）

- [ ] `tr/trregress.f90` が追加され、通常実行では `tr_regress.dat` が生成されないことが確認済み（Task 3 Step 6）
- [ ] `TR_REGRESS_DUMP=1` 付き実行で同一入力の run-to-run が許容誤差内で一致（Task 3 Step 8 / Task 11 Step 4）
- [ ] `test_run/test_definitions.conf` に TR 回帰テストが **3 ケース以上** 登録されている
- [ ] `test_run/baselines/tr_*/metrics.json` が 3 ケース分コミットされている
- [ ] `run_tests.sh` が TR モジュールで自動的に環境変数をセットし、回帰判定を行う
- [ ] 故意の数値改変で `REGRESSION` が検出される（Task 14 Step 3 で確認）
- [ ] `python3 -m pytest test_run/scripts/tests/` が全 PASS
- [ ] `test_run/README.md` に dump 機構と運用手順が記載されている
- [ ] ブランチが push され PR が作成されている（または作成準備完了）

---

## 次のフェーズ

Phase 0 完了後、次は **Phase 1: `USE TRCOMM` への ONLY 句付与** に進む。
対象ファイル: `trfout.f90`, `trloop.f90`, `trparm.f90`, `trrslt.f90`。
Phase 1 の実装計画は別文書 `docs/superpowers/plans/` に後日作成する。
