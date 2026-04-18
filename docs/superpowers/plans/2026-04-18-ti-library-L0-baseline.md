# TI Library Phase L-0: Regression Test Baseline 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `ti/` モジュールのライブラリ化（Phase L-1 以降）に着手する前に、数値挙動を固定する回帰テスト基盤を `test_run/` に整備し、3 ケース（`ti_min`, `ti_ar`, `ti_w`）のゴールデンテストを CI で実行可能にする。`tr/` Phase 0 と同じ仕組み（環境変数ガード付き高精度 dump + JSON 比較）を `ti` 用に追加する。

**Architecture:** `ti/` 本体に最小限の高精度 dump モジュール `tiregress.f90` を 1 つ追加する（環境変数 `TI_REGRESS_DUMP=1` のときのみ `ti_regress.dat` を書き出す設計、通常実行には影響なし）。既存の `test_run/run_tests.sh` + `test_definitions.conf` を拡張し、TI テスト実行時にこの環境変数を立てて dump を得た上で、ベースラインと相対誤差 `1e-10` で比較する Python スクリプト `extract_ti_metrics.py` を追加する。比較ロジックは既存の `compare_metrics.py` を再利用（中身は scalars + profile という同型スキーマなので互換）。

**Tech Stack:** Fortran 90 (`tiregress.f90` 追加), Bash (既存 `run_tests.sh` 拡張), Python 3 + 標準ライブラリのみ, gfortran, 既存 TI バイナリ `ti/ti`.

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` (4 層テスト戦略、Phase 0 相当の事前準備)、 `docs/superpowers/plans/2026-04-17-tr-refactoring-phase0.md`（参考とする tr 側の実装パターン）。

---

## File Structure

このフェーズで作成・変更するファイル:

| ファイル | 種別 | 責務 |
|---|---|---|
| `ti/tiregress.f90` | 新規 | 環境変数ガード付き高精度 dump（`1PE24.16` 書式） |
| `ti/tiexec.f90` | 修正 | `ti_exec` ループ末尾に `ti_regress_dump_if_enabled` を呼ぶ 1 行フック追加 |
| `ti/Makefile` | 修正 | `SRCS` に `tiregress.f90` を追加（`tiexec.f90` より前に） |
| `test_run/inputs/ti_min.in` | 新規 | NSMAX=1 の最小テスト入力（既存 `ti/tiparm.org` を移植） |
| `test_run/inputs/ti_ar.in` | 新規 | Ar 不純物テスト入力（既存 `ti/tiparm.Ar` を移植） |
| `test_run/inputs/ti_w.in` | 新規 | W 不純物テスト入力（NSMAX=3 with W） |
| `test_run/scripts/extract_ti_metrics.py` | 新規 | `ti_regress.dat` から JSON へ変換 |
| `test_run/scripts/tests/test_extract_ti_metrics.py` | 新規 | extract_ti_metrics.py のユニットテスト |
| `test_run/scripts/tests/fixtures/sample_ti_regress.dat` | 新規 | テスト用 fixture |
| `test_run/baselines/ti_min/metrics.json` | 新規（生成） | ベースライン指標 |
| `test_run/baselines/ti_ar/metrics.json` | 新規（生成） | ベースライン指標 |
| `test_run/baselines/ti_w/metrics.json` | 新規（生成） | ベースライン指標 |
| `test_run/test_definitions.conf` | 修正 | 新ケース 3 件追加 |
| `test_run/run_tests.sh` | 修正 | TI モジュール実行時に `TI_REGRESS_DUMP=1` をエクスポートし、成功時に `check_regression.sh` を呼ぶ（modules テーブル拡張） |
| `test_run/scripts/check_regression.sh` | 修正 | `--module ti` で extract スクリプトを切り替え |
| `test_run/README.md` | 修正 | TI 用テスト運用手順と dump 機構を追記 |

**方針:**
- TI 本体への追加は **`tiregress.f90` 新規 1 ファイル + `tiexec.f90` への 1 行フック + Makefile への 1 行追加** に限定する。通常実行（環境変数未設定）では挙動完全不変。
- Python は標準ライブラリのみ使用（`json`, `re`, `math`, `argparse`）。
- 比較ツールは tr 用と同じ `compare_metrics.py` を再利用（scalars + profile という共通スキーマ）。
- ベースラインは初回 `--generate-baseline` モードで書き出し、以後は比較のみ。

---

## Task 1: 作業用ブランチ確認とビルド前提の確認

**Files:**
- なし（環境準備）

- [ ] **Step 1: 現在の git 状態とブランチを確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git status
git branch --show-current
```
Expected: 専用作業ブランチ（例: `feature/ti-library-L0-baseline`）に居る。uncommitted な重要変更がないこと。

- [ ] **Step 2: ブランチが未作成なら新規作成**

Run:
```bash
git checkout -b feature/ti-library-L0-baseline origin/develop
```
Expected: ブランチが切り替わる（既に居れば飛ばす）。

- [ ] **Step 3: コンパイラ最適化フラグが固定されていることを確認**

Run:
```bash
grep -n "^OFLAGS\|^DFLAGS\|^FFLAGS" /home/k-yoshimi/program/task/make.header | head -10
grep -n "^FFLAGS" /home/k-yoshimi/program/task/ti/Makefile | head -5
```
Expected:
- `make.header` に `OFLAGS = -g -O3 -m64 -std=legacy` 相当の 1 行が有効化されている。
- `ti/Makefile` は `FFLAGS = $(OFLAGS)` を使っている（`$(DFLAGS)` がアンコメントされていないこと）。

異なる場合は L-0 期間中、固定する旨をメモしておく。

- [ ] **Step 4: 依存ライブラリと ti をビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/ti && make 2>&1 | tail -20
ls -la /home/k-yoshimi/program/task/ti/ti
```
Expected: `ti/ti` バイナリが生成される。エラーなし。adpost / open-adas のサブビルドも完走。

- [ ] **Step 5: 既存テスト基盤（tr 系）が PASS することを確認（前提保護）**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tr_iter01
```
Expected: `PASS`。既存 tr 回帰テストを壊していないことを毎タスク後にも確認する。

- [ ] **Step 6: 空コミット（ブランチ初期化マーカー）**

Run:
```bash
git commit --allow-empty -m "chore(ti): start L-0 regression test scaffolding"
```

---

## Task 2: 比較戦略と dump 仕様を確定（決定事項の文書化）

**Files:**
- 調査のみ（この段階ではファイル作成なし）

**決定事項（本計画で確定済み）:**

TI 本体に環境変数ガード付きの高精度 dump モジュール `tiregress.f90` を追加し、そこから得られる固定フォーマットの `ti_regress.dat` を比較対象とする。

- **dump 対象:**
  - スカラー: `NT, NRMAX, NSMAX, nsa_max, T, residual_loop_max, icount_loop_max, icount_mat_max`
  - プロファイル (per-NR): `RNA(1:nsa_max,NR), RTA(1:nsa_max,NR), RUA(1:nsa_max,NR), RBP(NR), RQP(NR), RJP(NR), ZEFF(NR), BETA(NR), BETAP(NR)`
- **書式:** スカラーは `1PE24.16`（整数は `I0`）、プロファイルは 1 行につき NR と `1PE24.16` の連続。
- **起動条件:** 環境変数 `TI_REGRESS_DUMP=1` のときのみ `ti_regress.dat` を CWD に書き出す。未設定時は何もしない。
- **許容誤差:** デフォルト `1e-10`（1PE24.16 の有効桁数内）。Task 12 での run-to-run 再現性測定で必要に応じ `1e-12` へ締める、または `1e-8` まで緩める。
- **stdout ログの数値行:** 比較対象外（精度不足）。`CLOSED` マーカーは従来通り完了判定に使う。

- [ ] **Step 1: dump 対象の変数が ticomm に存在することを確認**

Run:
```bash
grep -n "RNA\|RTA\|RUA\|RBP\|RQP\|RJP\|\bZEFF\b\|\bBETA\b\|\bBETAP\b\|residual_loop_max\|icount_loop_max\|icount_mat_max" \
    /home/k-yoshimi/program/task/ti/ticomm.f90 | head -30
```
Expected: これらの変数がすべて `ticomm` または `ticomm_parm` 内に宣言されている。`RNA/RTA/RUA` は `(nsa_max,NRMAX)` の ALLOCATABLE 配列。

存在しない変数があった場合は Task 3 Step 2 の dump コードから除外する。

- [ ] **Step 2: ti が CLOSED マーカーを出すかを確認（既存挙動の確認）**

Run:
```bash
grep -rn "CLOSED" /home/k-yoshimi/program/task/ti/ /home/k-yoshimi/program/task/lib/ 2>/dev/null | head -5
```
Expected: GSCLOS 由来の "CLOSED" 出力が確認できる（既存 tr/tx と同じ仕組み）。出ない場合は run_tests.sh 側の判定に独自パターン追加が必要だが、通常は `GSCLOS` 経由で出るはず。

- [ ] **Step 3: 決定事項を plan に反映してコミット**

Run:
```bash
git add docs/superpowers/plans/2026-04-18-ti-library-L0-baseline.md
git commit -m "docs(ti): lock L-0 comparison strategy (tiregress dump, tol 1e-10)"
```

---

## Task 3: `tiregress.f90` を新規追加し高精度 dump を実装

**Files:**
- Create: `ti/tiregress.f90`
- Modify: `ti/tiexec.f90`（USE 文追加 + 1 行フック）
- Modify: `ti/Makefile`（`SRCS` に 1 ファイル追加）

**目的:** 環境変数 `TI_REGRESS_DUMP=1` のときに限り、`ti_exec` のループ終了時点の主要グローバル量とプロファイルを `ti_regress.dat` へ `1PE24.16` 書式で書き出す。通常実行では何もしない。

- [ ] **Step 1: `ti/tiexec.f90` の `ti_exec` 終了位置を確認**

Run:
```bash
grep -n "END SUBROUTINE ti_exec\|IF(ALLOCATED(v))" /home/k-yoshimi/program/task/ti/tiexec.f90
```
Expected: 既存コードは `IF(ALLOCATED(v)) DEALLOCATE(v)` という単一行（`tiexec.f90:43`）。`DEALLOCATE(v)` 単独パターンで grep しても一致しないので注意。この行の **直後**、`RETURN` の **直前** にフックを差し込めることを確認。

注: 念のため両パターンで確認しておくとよい:
```bash
grep -n "ALLOCATED.*DEALLOCATE\|DEALLOCATE(v)" /home/k-yoshimi/program/task/ti/tiexec.f90
```

- [ ] **Step 2: `ti/tiregress.f90` を新規作成**

作成: `ti/tiregress.f90`

```fortran
! tiregress.f90
!
! High-precision regression dump for TI Phase L-0 regression tests.
! Emits ti_regress.dat (1PE24.16 format) when TI_REGRESS_DUMP=1.
! Otherwise does nothing; normal runs are unaffected.

MODULE tiregress

  PRIVATE
  PUBLIC :: ti_regress_dump_if_enabled

CONTAINS

  SUBROUTINE ti_regress_dump_if_enabled
    USE ticomm, ONLY: &
         NRMAX, NSMAX, nsa_max, NT, T, rkind, &
         residual_loop_max, icount_loop_max, icount_mat_max, &
         RNA, RTA, RUA, RBP, RQP, RJP, ZEFF, BETA, BETAP
    IMPLICIT NONE
    INTEGER, PARAMETER :: UNIT_DUMP = 78
    CHARACTER(LEN=16) :: ENV_VAL
    INTEGER :: STAT, NR, NSA, IOERR
    LOGICAL :: ENABLED

    CALL GET_ENVIRONMENT_VARIABLE('TI_REGRESS_DUMP', ENV_VAL, STATUS=STAT)
    ENABLED = (STAT == 0 .AND. TRIM(ENV_VAL) == '1')
    IF (.NOT. ENABLED) RETURN

    OPEN(UNIT=UNIT_DUMP, FILE='ti_regress.dat', &
         STATUS='REPLACE', ACTION='WRITE', IOSTAT=IOERR)
    IF (IOERR /= 0) THEN
       WRITE(6,*) 'XX tiregress: cannot open ti_regress.dat, IOSTAT=', IOERR
       RETURN
    END IF

    WRITE(UNIT_DUMP, '(A)')          '# TASK/TI regression dump (format v1)'
    WRITE(UNIT_DUMP, '(A,I0)')       'NT=',                NT
    WRITE(UNIT_DUMP, '(A,I0)')       'NRMAX=',             NRMAX
    WRITE(UNIT_DUMP, '(A,I0)')       'NSMAX=',             NSMAX
    WRITE(UNIT_DUMP, '(A,I0)')       'nsa_max=',           nsa_max
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'T=',                 T
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'residual_loop_max=', residual_loop_max
    WRITE(UNIT_DUMP, '(A,I0)')       'icount_loop_max=',   icount_loop_max
    WRITE(UNIT_DUMP, '(A,I0)')       'icount_mat_max=',    icount_mat_max

    WRITE(UNIT_DUMP, '(A)') &
         '# profile columns: NR RNA(1:nsa_max,NR) RTA(1:nsa_max,NR) RUA(1:nsa_max,NR) RBP RQP RJP ZEFF BETA BETAP'
    DO NR = 1, NRMAX
       WRITE(UNIT_DUMP, '(I5)', ADVANCE='NO') NR
       DO NSA = 1, nsa_max
          WRITE(UNIT_DUMP, '(1X,1PE24.16)', ADVANCE='NO') RNA(NSA,NR)
       END DO
       DO NSA = 1, nsa_max
          WRITE(UNIT_DUMP, '(1X,1PE24.16)', ADVANCE='NO') RTA(NSA,NR)
       END DO
       DO NSA = 1, nsa_max
          WRITE(UNIT_DUMP, '(1X,1PE24.16)', ADVANCE='NO') RUA(NSA,NR)
       END DO
       WRITE(UNIT_DUMP, '(6(1X,1PE24.16))') &
            RBP(NR), RQP(NR), RJP(NR), ZEFF(NR), BETA(NR), BETAP(NR)
    END DO

    CLOSE(UNIT_DUMP)
  END SUBROUTINE ti_regress_dump_if_enabled

END MODULE tiregress
```

注: Task 2 Step 1 で一部変数が ticomm に存在しないと分かった場合は、ここの `USE ticomm, ONLY: ...` リストと対応する `WRITE` 行を削除する（ビルドエラー回避）。

- [ ] **Step 3: `ti/Makefile` の SRCS に tiregress.f90 を追加**

`ti/Makefile` の `SRCS=` 定義を修正。`tiexec.f90` より前に来るように挿入する（Fortran の module 依存のため）。

変更前:
```
SRCS=   ticomm.f90 tiadas.f90 \
	tiinit.f90 tiparm.f90 \
	ticoef.f90 tisource.f90 ticalc.f90 tirecord.f90 \
        tiprep.f90 tiexec.f90 \
        tigout.f90 timenu.f90
```

変更後:
```
SRCS=   ticomm.f90 tiadas.f90 \
	tiinit.f90 tiparm.f90 \
	ticoef.f90 tisource.f90 ticalc.f90 tirecord.f90 \
        tiprep.f90 tiregress.f90 tiexec.f90 \
        tigout.f90 timenu.f90
```

加えて、Makefile 末尾の依存定義に 1 行追加:
```
tiregress.o : tiregress.f90 ticomm.f90
tiexec.o : tiexec.f90 ticomm.f90 tiregress.f90
```
（`tiexec.o` の依存は既存行を上記に置換）

- [ ] **Step 4: `ti/tiexec.f90` を修正してフックを追加**

`ti/tiexec.f90` の `ti_exec` 内、USE 文セクションに以下の 1 行を追加:

```fortran
    USE tiregress, ONLY : ti_regress_dump_if_enabled
```

そして `IF(ALLOCATED(v)) DEALLOCATE(v)` の直後、`RETURN` の直前に以下の 1 行を挿入:

```fortran
    IF(ALLOCATED(v)) DEALLOCATE(v)
    CALL ti_regress_dump_if_enabled   ! Phase L-0 regression dump (env-guarded)
    RETURN
```

- [ ] **Step 5: TI をリビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/ti
make 2>&1 | tail -20
```
Expected: `tiregress.f90` のコンパイルが実行され、`ti` バイナリが更新される。エラーなし。

- [ ] **Step 6: 通常実行では dump が作られないことを確認（副作用ゼロ検証）**

Run:
```bash
mkdir -p /tmp/ti-baseline-check && cd /tmp/ti-baseline-check
unset TI_REGRESS_DUMP
echo -e "R\nQ" | timeout 60 /home/k-yoshimi/program/task/ti/ti < /home/k-yoshimi/program/task/ti/tiparm.org > out.log 2>&1 || true
ls -la ti_regress.dat 2>&1 | head -3
```
Expected: `ti_regress.dat` は **作られない**（`No such file or directory`）。

- [ ] **Step 7: 環境変数を立てると dump が出ることを確認**

Run:
```bash
cd /tmp/ti-baseline-check
TI_REGRESS_DUMP=1 timeout 60 /home/k-yoshimi/program/task/ti/ti < /home/k-yoshimi/program/task/ti/tiparm.org > out.log 2>&1 || true
ls -la ti_regress.dat
head -25 ti_regress.dat
tail -5 ti_regress.dat
```
Expected:
- `ti_regress.dat` が存在する。
- 先頭行は `# TASK/TI regression dump (format v1)`。
- スカラー行が `1.xxxxxxxxxxxxxxxxE+nn` 形式で並んでいる。
- 末尾に NRMAX 行分のプロファイルデータ。

- [ ] **Step 8: 同一入力を 2 回走らせて dump が bit-exact に一致することを確認**

Run:
```bash
cd /tmp/ti-baseline-check
TI_REGRESS_DUMP=1 timeout 60 /home/k-yoshimi/program/task/ti/ti < /home/k-yoshimi/program/task/ti/tiparm.org > /dev/null 2>&1 || true
cp ti_regress.dat /tmp/ti_dump_run1.dat
TI_REGRESS_DUMP=1 timeout 60 /home/k-yoshimi/program/task/ti/ti < /home/k-yoshimi/program/task/ti/tiparm.org > /dev/null 2>&1 || true
diff /tmp/ti_dump_run1.dat ti_regress.dat
echo "diff exit=$?"
```
Expected: `diff` の出力が空、`exit=0`。run-to-run で完全一致。

差異があった場合は Task 12 で許容誤差を `1e-8` 程度に緩める判断。

- [ ] **Step 9: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add ti/tiregress.f90 ti/tiexec.f90 ti/Makefile
git commit -m "feat(ti): add env-guarded high-precision dump for L-0 regression tests"
```

---

## Task 4: 入力ファイル 3 種を `test_run/inputs/` に追加

**Files:**
- Create: `test_run/inputs/ti_min.in`
- Create: `test_run/inputs/ti_ar.in`
- Create: `test_run/inputs/ti_w.in`

**目的:** `tiparm.org`（最小）と `tiparm.Ar`（Ar 不純物）を移植し、加えて W 不純物のケースを 1 つ追加。menu 入力は `R\nQ\n` を namelist の後ろに追記して `<` で stdin に流し込む方式（既存 `tr` 系ケースと同じ。`run_tests.sh` は `< "$full_input_path"` で入力ファイル全体を渡す）。

- [ ] **Step 0: ti の menu 起動方式を実機で検証**

Run:
```bash
# tiparm.org (namelist のみ) に R/Q を後付けして 1 ファイルに結合し、stdin で渡せるか確認
mkdir -p /tmp/ti-menu-check && cd /tmp/ti-menu-check
cat /home/k-yoshimi/program/task/ti/tiparm.org > combined.in
printf 'R\nQ\n' >> combined.in
timeout 60 /home/k-yoshimi/program/task/ti/ti < combined.in > out.log 2>&1 || true
echo "exit=$?"
grep -E "TI MENU|XX|CLOSED" out.log | head -10
```
Expected:
- `## TI MENU: P,V/PARM  R/RUN  L/LOAD  W/WRITE  H/HELP  Q/QUIT` が log に出る。
- `R` で計算が始まり、`Q` で終了。最終的に `CLOSED`（GSCLOS 由来）が出る。
- 異常停止（`XX` 行）が無い。

これが動かない場合（例えば `READ(5,*,ERR=1,END=1) nid` の周りで 1 行追加入力が必要、など）は `timenu.f90` を再確認（`L` ケースで `READ` していることに注意。本テストでは `L` を使わないので問題にはならないはず）。

- [ ] **Step 1: ti を menu モードで実行する手順を確認**

Run:
```bash
head -30 /home/k-yoshimi/program/task/ti/timenu.f90
```
Expected: `'## TI MENU: P,V/PARM  R/RUN  L/LOAD  W/WRITE  H/HELP  Q/QUIT'` メニューが見える。`R` で計算、`Q` で終了。

- [ ] **Step 2: `test_run/inputs/ti_min.in` を作成**

作成: `test_run/inputs/ti_min.in`（既存 `ti/tiparm.org` を移植 + run/quit 操作を末尾に追加）

```
 &ti
   NSMAX=1
   AD0=1.D0
   AK0=0.D0
   AV0=0.D0
   DK0=1.D0
   DKS=1.D0
   NRMAX=10
   NTSTEP=1
   NGTSTEP=1
   NGRSTEP=1
   NTMAX=2
 &end
R
Q
```

注: `AD0/AK0/AV0/DK0/DKS` が現行 namelist に存在しない場合は、`tiparm.f90` の NAMELIST `/TI/` 定義を確認の上、未定義変数の行を削除する（namelist parser はエラーで停止するため）。

- [ ] **Step 3: namelist 定義に AD0/AK0/AV0/DK0/DKS が存在するか確認**

Run:
```bash
grep -n "AD0\|AK0\|AV0\|DK0\|DKS" /home/k-yoshimi/program/task/ti/tiparm.f90 | head -10
```
Expected:
- 含まれていれば `ti_min.in` のまま OK。
- 含まれていなければ、`ti_min.in` から該当行を削除して以下の最小版にする:
```
 &ti
   NSMAX=1
   NRMAX=10
   NTSTEP=1
   NGTSTEP=1
   NGRSTEP=1
   NTMAX=2
 &end
R
Q
```

- [ ] **Step 4: `test_run/inputs/ti_ar.in` を作成（既存 `ti/tiparm.Ar` を移植）**

作成: `test_run/inputs/ti_ar.in`

```
 &ti
   NSMAX=3
   NPA(3)=18
   PM(3)=39.95D0
   ID_NS(3)=10
   KID_NS(3)='Ar'
   NZMIN_NS(3)=15
   NZMAX_NS(3)=18
   MODEL_BND(1,3)=2
   BND_VALUE(1,3)=1.D0
   DN0=0.1D0
   DN0_NS(1)=0.D0
   DN0_NS(2)=0.D0
   DT0=1.D0
   DR0=1.D0
   DRS=3.D0
   NRMAX=20
   NTSTEP=1
   NGTSTEP=1
   NGRSTEP=1
   NTMAX=10
 &end
R
Q
```

- [ ] **Step 5: `test_run/inputs/ti_w.in` を作成（W 不純物 + 短時間）**

作成: `test_run/inputs/ti_w.in`（Ar ベースで W に置換、計算は短く）

```
 &ti
   NSMAX=3
   NPA(3)=74
   PM(3)=183.84D0
   PZ(3)=74.D0
   ID_NS(3)=10
   KID_NS(3)='W'
   NZMIN_NS(3)=20
   NZMAX_NS(3)=45
   MODEL_BND(1,3)=2
   BND_VALUE(1,3)=1.D-3
   DN0=0.1D0
   DN0_NS(1)=0.D0
   DN0_NS(2)=0.D0
   DT0=1.D0
   DR0=1.D0
   DRS=3.D0
   NRMAX=20
   NTSTEP=1
   NGTSTEP=1
   NGRSTEP=1
   NTMAX=5
 &end
R
Q
```

注: ADAS データが利用可能な NZ レンジは設置環境依存。実行時に「ADAS file not found」等で失敗する場合は、`NZMIN_NS(3)=20, NZMAX_NS(3)=45` を `tiparm.f90` のデフォルトに合わせて狭めるか、`ID_NS(3)=5` (ADPOST 経由 average ionization) に切り替える。

- [ ] **Step 6: 3 ケースをローカルで手動実行して完走を確認**

Run:
```bash
mkdir -p /tmp/ti-input-check
for case in ti_min ti_ar ti_w; do
  rm -rf /tmp/ti-input-check/$case && mkdir -p /tmp/ti-input-check/$case
  cd /tmp/ti-input-check/$case
  TI_REGRESS_DUMP=1 timeout 120 /home/k-yoshimi/program/task/ti/ti \
      < /home/k-yoshimi/program/task/test_run/inputs/${case}.in > out.log 2>&1 || true
  echo "=== $case ==="
  grep -E "CLOSED|XX|ERROR" out.log | head -5
  ls -la ti_regress.dat 2>/dev/null | awk '{print $9, $5}'
done
```
Expected:
- 各ケースで `out.log` に `CLOSED` が出る（GSCLOS 由来）。
- `ti_regress.dat` が各 dir に生成され、ファイルサイズが非ゼロ。
- `XX` で始まる致命的エラーが無い（ti_w は ADAS 関連で出る場合あり、その場合は Step 5 注に従い修正）。

- [ ] **Step 7: コミット**

Run:
```bash
git add test_run/inputs/ti_min.in test_run/inputs/ti_ar.in test_run/inputs/ti_w.in
git commit -m "test(ti): add ti_min/ti_ar/ti_w regression inputs"
```

---

## Task 5: 指標抽出スクリプト `extract_ti_metrics.py` を実装

**Files:**
- Create: `test_run/scripts/extract_ti_metrics.py`
- Create: `test_run/scripts/tests/test_extract_ti_metrics.py`
- Create: `test_run/scripts/tests/fixtures/sample_ti_regress.dat`

- [ ] **Step 1: サンプル fixture を作成**

作成: `test_run/scripts/tests/fixtures/sample_ti_regress.dat`

```
# TASK/TI regression dump (format v1)
NT=10
NRMAX=2
NSMAX=2
nsa_max=2
T=1.0000000000000000E-02
residual_loop_max=1.2300000000000000E-08
icount_loop_max=3
icount_mat_max=2
# profile columns: NR RNA(1:nsa_max,NR) RTA(1:nsa_max,NR) RUA(1:nsa_max,NR) RBP RQP RJP ZEFF BETA BETAP
    1  7.0000000000000007E-01  3.1500000000000000E-01  4.5650000000000004E+00  4.2750000000000004E+00  0.0000000000000000E+00  0.0000000000000000E+00  1.0000000000000000E+00  2.0000000000000000E+00  3.0000000000000000E+00  1.0000000000000000E+00  1.2300000000000000E-02  8.9000000000000004E-02
    2  6.5000000000000002E-01  3.0000000000000004E-01  4.2000000000000002E+00  3.9000000000000004E+00  0.0000000000000000E+00  0.0000000000000000E+00  1.5000000000000000E+00  2.5000000000000000E+00  3.5000000000000000E+00  1.1000000000000001E+00  1.1000000000000001E-02  7.5000000000000000E-02
```

- [ ] **Step 2: 失敗するテストを書く**

作成: `test_run/scripts/tests/test_extract_ti_metrics.py`

```python
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "extract_ti_metrics.py"
FIXTURE = Path(__file__).parent / "fixtures" / "sample_ti_regress.dat"


def run_extract(dump_path: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(dump_path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def test_extracts_scalars():
    data = run_extract(FIXTURE)
    assert data["NT"] == 10
    assert data["NRMAX"] == 2
    assert data["NSMAX"] == 2
    assert data["nsa_max"] == 2
    assert data["scalars"]["T"] == 0.01
    assert "residual_loop_max" in data["scalars"]
    assert data["scalars_int"]["icount_loop_max"] == 3
    assert data["scalars_int"]["icount_mat_max"] == 2


def test_extracts_profile_rows():
    data = run_extract(FIXTURE)
    prof = data["profile"]
    assert len(prof) == 2
    row = prof[0]
    assert row["NR"] == 1
    assert len(row["RNA"]) == 2
    assert len(row["RTA"]) == 2
    assert len(row["RUA"]) == 2
    assert row["RNA"][0] == 0.7
    assert row["ZEFF"] == 1.0
    assert row["BETA"] == 0.0123


def test_rejects_incomplete_dump(tmp_path):
    incomplete = tmp_path / "bad.dat"
    incomplete.write_text("# TASK/TI regression dump (format v1)\nNT=1\n")
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
python3 -m pytest tests/test_extract_ti_metrics.py -v
```
Expected: FAIL（`extract_ti_metrics.py` が存在しないため）。

- [ ] **Step 4: スクリプト本体を実装**

作成: `test_run/scripts/extract_ti_metrics.py`

```python
#!/usr/bin/env python3
"""Convert ti_regress.dat into a JSON for regression comparison.

Usage:
    extract_ti_metrics.py path/to/ti_regress.dat
Output schema (same scalars+profile shape as extract_tr_metrics.py so
compare_metrics.py can be reused unchanged):
    NT, NRMAX, NSMAX, nsa_max (top-level ints),
    scalars (dict[str,float]) — float scalars,
    scalars_int (dict[str,int]) — int counters (compared exactly),
    profile (list[dict]) — one dict per radial point.
"""
import argparse
import json
import re
import sys
from pathlib import Path


SCALAR_FLOAT_KEYS = {"T", "residual_loop_max"}
SCALAR_INT_KEYS = {"icount_loop_max", "icount_mat_max"}
RE_PROFILE_HEADER = re.compile(r"^#\s*profile columns:")


def parse(dump_path: Path) -> dict:
    lines = dump_path.read_text().splitlines()
    result = {"scalars": {}, "scalars_int": {}, "profile": []}
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
            if key in ("NT", "NRMAX", "NSMAX", "nsa_max"):
                result[key] = int(val)
            elif key in SCALAR_FLOAT_KEYS:
                result["scalars"][key] = float(val)
            elif key in SCALAR_INT_KEYS:
                result["scalars_int"][key] = int(val)
            else:
                pass  # ignore unknown
        else:
            parts = line.split()
            if len(parts) < 4:
                continue
            nsa = result.get("nsa_max", 0)
            if nsa <= 0:
                raise SystemExit("profile row encountered before nsa_max")
            # NR + RNA(nsa) + RTA(nsa) + RUA(nsa) + RBP + RQP + RJP + ZEFF + BETA + BETAP
            expected = 1 + 3 * nsa + 6
            if len(parts) != expected:
                raise SystemExit(
                    f"malformed profile row (expected {expected} cols, got {len(parts)}): {raw}"
                )
            nr = int(parts[0])
            off = 1
            rna = [float(x) for x in parts[off:off + nsa]]; off += nsa
            rta = [float(x) for x in parts[off:off + nsa]]; off += nsa
            rua = [float(x) for x in parts[off:off + nsa]]; off += nsa
            rbp, rqp, rjp, zeff, beta, betap = (float(x) for x in parts[off:off + 6])
            result["profile"].append({
                "NR": nr, "RNA": rna, "RTA": rta, "RUA": rua,
                "RBP": rbp, "RQP": rqp, "RJP": rjp,
                "ZEFF": zeff, "BETA": beta, "BETAP": betap,
            })
    for k in ("NT", "NRMAX", "NSMAX", "nsa_max"):
        if k not in result:
            raise SystemExit(f"missing header field: {k}")
    if len(result["profile"]) != result["NRMAX"]:
        raise SystemExit(
            f"profile row count {len(result['profile'])} != NRMAX {result['NRMAX']}"
        )
    if not result["scalars"]:
        raise SystemExit("no float scalars parsed")
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
chmod +x /home/k-yoshimi/program/task/test_run/scripts/extract_ti_metrics.py
cd /home/k-yoshimi/program/task/test_run/scripts
python3 -m pytest tests/test_extract_ti_metrics.py -v
```
Expected: 3 tests PASS。

- [ ] **Step 6: 実 dump で動作確認**

Run:
```bash
python3 /home/k-yoshimi/program/task/test_run/scripts/extract_ti_metrics.py \
    /tmp/ti-input-check/ti_min/ti_regress.dat | head -40
```
Expected: NT/NRMAX/NSMAX/nsa_max と scalars/scalars_int、profile の先頭数行が JSON で出力される。

- [ ] **Step 7: コミット**

Run:
```bash
git add test_run/scripts/extract_ti_metrics.py test_run/scripts/tests/test_extract_ti_metrics.py test_run/scripts/tests/fixtures/sample_ti_regress.dat
git commit -m "test(ti): add metric extractor reading ti_regress.dat"
```

---

## Task 6: `compare_metrics.py` を ti スキーマに対応させる

**Files:**
- Modify: `test_run/scripts/compare_metrics.py`
- Create: `test_run/scripts/tests/test_compare_metrics_ti.py`

**目的:** 既存 `compare_metrics.py` は `profile[*].RN/RT/AJ/QP` という tr スキーマ前提のループを持つ。ti スキーマ（`RNA/RTA/RUA/RBP/RQP/RJP/ZEFF/BETA/BETAP`）にも対応させるため、profile dict 内のリスト型キーと float 型キーを **動的に判定** する汎用化を入れる。これにより tr/ti 両方を 1 スクリプトで扱える。

- [ ] **Step 1: 既存 compare_metrics.py の構造を確認**

Run:
```bash
sed -n '40,80p' /home/k-yoshimi/program/task/test_run/scripts/compare_metrics.py
```
Expected: `for field in ("AJ", "QP")` と `for field in ("RN", "RT")` のハードコード行が見える。

- [ ] **Step 2: ti 用の比較テストを失敗側で書く**

作成: `test_run/scripts/tests/test_compare_metrics_ti.py`

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


def _ti_sample() -> dict:
    return {
        "NT": 10, "NRMAX": 2, "NSMAX": 2, "nsa_max": 2,
        "scalars": {"T": 0.01, "residual_loop_max": 1.23e-8},
        "scalars_int": {"icount_loop_max": 3, "icount_mat_max": 2},
        "profile": [
            {"NR": 1, "RNA": [0.7, 0.315], "RTA": [4.565, 4.275], "RUA": [0.0, 0.0],
             "RBP": 1.0, "RQP": 2.0, "RJP": 3.0, "ZEFF": 1.0, "BETA": 0.0123, "BETAP": 0.089},
            {"NR": 2, "RNA": [0.65, 0.30], "RTA": [4.20, 3.90], "RUA": [0.0, 0.0],
             "RBP": 1.5, "RQP": 2.5, "RJP": 3.5, "ZEFF": 1.1, "BETA": 0.011, "BETAP": 0.075},
        ],
    }


def test_passes_on_identical_ti(tmp_path):
    base = tmp_path / "b.json"; act = tmp_path / "a.json"
    write_json(base, _ti_sample()); write_json(act, _ti_sample())
    res = run_compare(act, base)
    assert res.returncode == 0, res.stderr


def test_fails_on_ti_profile_drift(tmp_path):
    base = tmp_path / "b.json"; act = tmp_path / "a.json"
    write_json(base, _ti_sample())
    drifted = _ti_sample()
    drifted["profile"][0]["RNA"][1] = 0.315 * (1.0 + 1e-5)
    write_json(act, drifted)
    res = run_compare(act, base, tol="1e-10")
    assert res.returncode != 0
    assert "RNA" in res.stdout


def test_fails_on_ti_int_counter_drift(tmp_path):
    base = tmp_path / "b.json"; act = tmp_path / "a.json"
    write_json(base, _ti_sample())
    drifted = _ti_sample()
    drifted["scalars_int"]["icount_loop_max"] = 4
    write_json(act, drifted)
    res = run_compare(act, base)
    assert res.returncode != 0
    assert "icount_loop_max" in res.stdout
```

- [ ] **Step 3: テストを走らせて失敗を確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run/scripts
python3 -m pytest tests/test_compare_metrics_ti.py -v
```
Expected: FAIL（compare_metrics.py が ti スキーマ未対応）。

- [ ] **Step 4: compare_metrics.py を汎用化**

`test_run/scripts/compare_metrics.py` の `compare()` 関数を書き換える。差分の方針:

1. profile 各行について、`NR` 以外の dict キーをイテレートし、値の型で `list` か `float` かを判定して再帰比較する。
2. 上位辞書に `scalars_int` があれば、その辞書は完全一致（不一致でエラー）として比較する。
3. tr スキーマ（`scalars_int` 無し、`RN/RT/AJ/QP` のみ）でも引き続き動くようにする（互換性）。

具体的な置換:

`compare_metrics.py` の `compare()` を以下に置換:

```python
def compare(baseline: dict, actual: dict, tol: float) -> list:
    errors = []
    for k in ("NT", "NRMAX", "NSMAX", "nsa_max"):
        if k in baseline or k in actual:
            if baseline.get(k) != actual.get(k):
                errors.append(f"{k}: baseline={baseline.get(k)} actual={actual.get(k)}")
    if errors:
        return errors  # dimensions differ; further comparison meaningless

    # float scalars (tolerance comparison)
    b_scalars = baseline.get("scalars", {})
    a_scalars = actual.get("scalars", {})
    for k in sorted(set(b_scalars) | set(a_scalars)):
        if k not in b_scalars or k not in a_scalars:
            errors.append(f"scalars.{k}: missing")
            continue
        _check_scalar(f"scalars.{k}", float(b_scalars[k]), float(a_scalars[k]), tol, errors)

    # int scalars (exact match required)
    b_int = baseline.get("scalars_int", {})
    a_int = actual.get("scalars_int", {})
    for k in sorted(set(b_int) | set(a_int)):
        if b_int.get(k) != a_int.get(k):
            errors.append(f"scalars_int.{k}: baseline={b_int.get(k)} actual={a_int.get(k)}")

    # profiles
    b_prof = baseline.get("profile", [])
    a_prof = actual.get("profile", [])
    if len(b_prof) != len(a_prof):
        errors.append(f"profile length: baseline={len(b_prof)} actual={len(a_prof)}")
        return errors
    for i, (br, ar) in enumerate(zip(b_prof, a_prof)):
        if br.get("NR") != ar.get("NR"):
            errors.append(f"profile[{i}].NR: baseline={br.get('NR')} actual={ar.get('NR')}")
            continue
        keys = sorted(set(br) | set(ar))
        for field in keys:
            if field == "NR":
                continue
            bv = br.get(field); av = ar.get(field)
            if bv is None or av is None:
                errors.append(f"profile[{i}].{field}: missing in one side")
                continue
            if isinstance(bv, list) or isinstance(av, list):
                if not isinstance(bv, list) or not isinstance(av, list):
                    errors.append(f"profile[{i}].{field}: type mismatch")
                    continue
                if len(bv) != len(av):
                    errors.append(f"profile[{i}].{field}: length differ ({len(bv)} vs {len(av)})")
                    continue
                for j, (bx, ax) in enumerate(zip(bv, av)):
                    _check_scalar(f"profile[{i}].{field}[{j}]", float(bx), float(ax), tol, errors)
            else:
                _check_scalar(f"profile[{i}].{field}", float(bv), float(av), tol, errors)
    return errors
```

- [ ] **Step 5: ti と tr 両方のテストが通ることを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run/scripts
python3 -m pytest tests/ -v
```
Expected: tr 用 (`test_compare_metrics.py`) と ti 用 (`test_compare_metrics_ti.py`) の全テストが PASS。tr 互換性が壊れていない。

- [ ] **Step 6: コミット**

Run:
```bash
git add test_run/scripts/compare_metrics.py test_run/scripts/tests/test_compare_metrics_ti.py
git commit -m "test(ti): generalize compare_metrics.py for ti profile schema"
```

---

## Task 7: `check_regression.sh` を multi-module 対応させる

**Files:**
- Modify: `test_run/scripts/check_regression.sh`

**目的:** 既存 `check_regression.sh` は `extract_tr_metrics.py` 固定で `tr_regress.dat` のみを読む。tr/ti を切り替えできるよう、最初の引数の前に optional `--module {tr|ti}` を受け付ける（デフォルト `tr` で後方互換）。

- [ ] **Step 1: 既存仕様を確認**

Run:
```bash
cat /home/k-yoshimi/program/task/test_run/scripts/check_regression.sh
```
Expected: 4 番目までが `<test_name> <output_dir> <baselines_dir> [tol]`、5 番目が `--generate-baseline` または省略。

- [ ] **Step 2: 拡張版に書き換え**

`test_run/scripts/check_regression.sh` を以下に置換:

```bash
#!/bin/bash
#
# check_regression.sh [--module {tr|ti}] <test_name> <test_output_dir> <baselines_dir> [tolerance] [--generate-baseline]
#
# Reads <test_output_dir>/<module>_regress.dat (produced when the binary is run
# with <MODULE>_REGRESS_DUMP=1), extracts metrics to JSON, and compares with
# <baselines_dir>/<test_name>/metrics.json. Exits 0 on match, 1 on mismatch,
# 2 on missing dump, 3 on missing baseline.
#
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

MODULE="tr"
if [[ "${1:-}" == "--module" ]]; then
    MODULE="$2"
    shift 2
fi

TEST_NAME="${1:?usage: $0 [--module {tr|ti}] <test_name> <output_dir> <baselines_dir> [tol] [--generate-baseline]}"
OUTPUT_DIR="${2:?}"
BASELINES_DIR="${3:?}"
TOL="${4:-1e-10}"
MODE="${5:-compare}"

case "$MODULE" in
    tr) DUMP_NAME="tr_regress.dat"; EXTRACT="extract_tr_metrics.py" ;;
    ti) DUMP_NAME="ti_regress.dat"; EXTRACT="extract_ti_metrics.py" ;;
    *)  echo "check_regression: unknown module: $MODULE" >&2; exit 2 ;;
esac

DUMP="$OUTPUT_DIR/$DUMP_NAME"
METRICS_ACTUAL="$OUTPUT_DIR/metrics.json"
METRICS_BASE="$BASELINES_DIR/$TEST_NAME/metrics.json"

if [[ ! -f "$DUMP" ]]; then
    echo "check_regression: dump not found: $DUMP" >&2
    echo "  did the test run with ${MODULE^^}_REGRESS_DUMP=1 exported?" >&2
    exit 2
fi

if ! python3 "$SCRIPT_DIR/$EXTRACT" "$DUMP" > "$METRICS_ACTUAL"; then
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

- [ ] **Step 3: 後方互換性（tr 既定動作）を手動で確認**

Run:
```bash
bash /home/k-yoshimi/program/task/test_run/scripts/check_regression.sh \
    tr_iter01 \
    /home/k-yoshimi/program/task/test_run/test_output/tr_iter01 \
    /home/k-yoshimi/program/task/test_run/baselines \
    1e-10
echo "exit=$?"
```
Expected: `OK: metrics match within tol=1e-10`、`exit=0`。tr 既存テストが引き続き動く。

(`test_output/tr_iter01/tr_regress.dat` が無い場合は先に `./run_tests.sh tr_iter01` を実行)

- [ ] **Step 4: コミット**

Run:
```bash
git add test_run/scripts/check_regression.sh
git commit -m "test(ti): extend check_regression.sh to dispatch by --module"
```

---

## Task 8: `run_tests.sh` に TI モジュール対応を追加

**Files:**
- Modify: `test_run/run_tests.sh`

**目的:** `get_binary` に `ti) echo "$TASK_DIR/ti/ti"` 行を加え、TI モジュール実行時に `TI_REGRESS_DUMP=1` をエクスポートし、`check_regression.sh --module ti` を呼ぶ。tr 用ロジックはそのまま温存（重複ではなく cases で並列分岐）。

- [ ] **Step 1: 既存 get_binary の場所を確認**

Run:
```bash
grep -n "get_binary\|tr_env\|TR_REGRESS_DUMP\|--module" /home/k-yoshimi/program/task/test_run/run_tests.sh
```
Expected: `get_binary` 関数（103-114 行付近）、`TR_REGRESS_DUMP=1` のセット箇所（299 行付近）、`check_regression.sh` 呼び出し（323 行付近）が見える。

- [ ] **Step 2: get_binary に ti を追加**

`test_run/run_tests.sh` の以下箇所:
```bash
        tr) echo "$TASK_DIR/tr/tr2" ;;
        fp) echo "$TASK_DIR/fp/fp" ;;
```
を以下に変更:
```bash
        tr) echo "$TASK_DIR/tr/tr2" ;;
        ti) echo "$TASK_DIR/ti/ti" ;;
        fp) echo "$TASK_DIR/fp/fp" ;;
```

- [ ] **Step 3: 環境変数エクスポートを ti にも対応**

`test_run/run_tests.sh` の以下ブロック:
```bash
    # For TR module, enable regression dump (env-guarded inside trregress.f90).
    local tr_env=()
    if [[ "$module" == "tr" ]]; then
        tr_env=(env TR_REGRESS_DUMP=1)
    fi
```
を以下に置換:
```bash
    # For TR/TI modules, enable regression dump (env-guarded inside *regress.f90).
    local mod_env=()
    if [[ "$module" == "tr" ]]; then
        mod_env=(env TR_REGRESS_DUMP=1)
    elif [[ "$module" == "ti" ]]; then
        mod_env=(env TI_REGRESS_DUMP=1)
    fi
```

そして `${tr_env[@]}` を使っている 2 箇所をそれぞれ `${mod_env[@]}` に書き換える。

- [ ] **Step 4: regression check を ti でも呼ぶ**

`test_run/run_tests.sh` の以下ブロック:
```bash
        if [[ "$module" == "tr" ]]; then
            if ! "$SCRIPT_DIR/scripts/check_regression.sh" \
                    "$test_name" "$test_dir" "$SCRIPT_DIR/baselines" "1e-10" \
                    > "$test_dir/regression.log" 2>&1; then
                reg_ok=0
            fi
        fi
```
を以下に置換:
```bash
        if [[ "$module" == "tr" ]]; then
            if ! "$SCRIPT_DIR/scripts/check_regression.sh" \
                    "$test_name" "$test_dir" "$SCRIPT_DIR/baselines" "1e-10" \
                    > "$test_dir/regression.log" 2>&1; then
                reg_ok=0
            fi
        elif [[ "$module" == "ti" ]]; then
            if ! "$SCRIPT_DIR/scripts/check_regression.sh" \
                    --module ti \
                    "$test_name" "$test_dir" "$SCRIPT_DIR/baselines" "1e-10" \
                    > "$test_dir/regression.log" 2>&1; then
                reg_ok=0
            fi
        fi
```

- [ ] **Step 5: ti が --list に出ることを確認（test_definitions に未追加でも get_binary だけは効く）**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh -l 2>&1 | head -20
```
Expected: tr_iter01 等が表示される。エラー無し（ti 用ケースは Task 9 で追加するためまだ出ない）。

- [ ] **Step 6: tr 既存テストが壊れていないことを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tr_iter01
```
Expected: `PASS`。`tr_env` → `mod_env` リネームで挙動不変。

- [ ] **Step 7: コミット**

Run:
```bash
git add test_run/run_tests.sh
git commit -m "test(ti): wire ti module into run_tests.sh with regression dump env"
```

---

## Task 9: `test_definitions.conf` に ti ケースを追加

**Files:**
- Modify: `test_run/test_definitions.conf`

- [ ] **Step 1: ti セクションを追加**

`test_run/test_definitions.conf` の末尾（TX セクションの後）に以下を追加:

```
# =============================================================================
# TI Module Tests (Impurity transport calculation)
# Standalone - no dependencies (analytic profile, no EQ data needed)
# =============================================================================
ti_min:ti:@inputs/ti_min.in:none:60:Minimum ti run (NSMAX=1, NRMAX=10)
ti_ar:ti:@inputs/ti_ar.in:none:120:Ar impurity transport (NRMAX=20, NTMAX=10)
ti_w:ti:@inputs/ti_w.in:none:120:W impurity transport (NRMAX=20, NTMAX=5)
```

- [ ] **Step 2: --list で 3 ケースが出ることを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh -l | grep "^ti_"
```
Expected: `ti_min`, `ti_ar`, `ti_w` の 3 行が表示される。

- [ ] **Step 3: コミット**

Run:
```bash
git add test_run/test_definitions.conf
git commit -m "test(ti): register ti_min/ti_ar/ti_w in test_definitions.conf"
```

---

## Task 10: ベースラインを生成してコミット

**Files:**
- Create: `test_run/baselines/ti_min/metrics.json`
- Create: `test_run/baselines/ti_ar/metrics.json`
- Create: `test_run/baselines/ti_w/metrics.json`

- [ ] **Step 1: 各ケースを 1 回走らせて dump を得る**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
rm -rf test_output/ti_min test_output/ti_ar test_output/ti_w
./run_tests.sh ti_min ti_ar ti_w
```
Expected: 各ケースが完走する（baseline が無いため `REGRESSION` で FAIL するが `tr_regress.dat` は残る）。`test_output/ti_*/ti_regress.dat` が存在する。

- [ ] **Step 2: 3 ケース分の baseline を生成**

Run:
```bash
for case in ti_min ti_ar ti_w; do
  bash /home/k-yoshimi/program/task/test_run/scripts/check_regression.sh \
      --module ti \
      "$case" \
      "/home/k-yoshimi/program/task/test_run/test_output/$case" \
      "/home/k-yoshimi/program/task/test_run/baselines" \
      1e-10 \
      --generate-baseline
done
ls /home/k-yoshimi/program/task/test_run/baselines/ti_*/metrics.json
```
Expected: `Baseline written: ...` が 3 回出力される。`baselines/ti_min/metrics.json`, `baselines/ti_ar/metrics.json`, `baselines/ti_w/metrics.json` が存在する。

- [ ] **Step 3: 直後に再実行して PASS することを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh ti_min ti_ar ti_w
```
Expected: 3 ケースとも `PASS`（生成 baseline と完全一致）。

- [ ] **Step 4: ベースライン JSON を git add**

Run:
```bash
git add test_run/baselines/ti_min/metrics.json \
        test_run/baselines/ti_ar/metrics.json \
        test_run/baselines/ti_w/metrics.json
git commit -m "test(ti): commit initial regression baselines (ti_min, ti_ar, ti_w)"
```

---

## Task 11: README 更新

**Files:**
- Modify: `test_run/README.md`

- [ ] **Step 1: 既存の README に TI セクションを追記**

`test_run/README.md` の末尾（または「Modules」セクション付近）に以下を追記:

```markdown
## TI Module Regression Tests

Same dump mechanism as TR: `ti/tiregress.f90` writes `ti_regress.dat` only when
`TI_REGRESS_DUMP=1`. `run_tests.sh` exports this variable for `ti` module tests.

Cases:
- `ti_min` — Minimum NSMAX=1, NRMAX=10, NTMAX=2 sanity case
- `ti_ar` — Ar impurity (ID_NS=10), NRMAX=20, NTMAX=10
- `ti_w`  — W impurity (ID_NS=10), NRMAX=20, NTMAX=5

Baselines live under `baselines/ti_*/metrics.json`. To regenerate after an
intended numerical change:

    ./run_tests.sh ti_min ti_ar ti_w   # produces test_output/ti_*/ti_regress.dat
    for c in ti_min ti_ar ti_w; do
        ./scripts/check_regression.sh --module ti "$c" \
            test_output/$c baselines 1e-10 --generate-baseline
    done

Default tolerance: `1e-10`. Adjust via the 4th arg to `check_regression.sh`.
```

- [ ] **Step 2: コミット**

Run:
```bash
git add test_run/README.md
git commit -m "docs(test_run): document TI regression workflow"
```

---

## Task 12: 許容誤差の最終確認と run-to-run 安定性検証

**Files:**
- なし（検証のみ）

- [ ] **Step 1: 各ケースを 3 回連続で走らせて全て PASS することを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
for i in 1 2 3; do
  echo "--- run $i ---"
  ./run_tests.sh ti_min ti_ar ti_w | tail -10
done
```
Expected: 3 回とも 3/3 PASS。

- [ ] **Step 2: dump の bit-exact 性を再確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh ti_ar > /dev/null
cp test_output/ti_ar/ti_regress.dat /tmp/ti_ar_run1.dat
./run_tests.sh ti_ar > /dev/null
diff /tmp/ti_ar_run1.dat test_output/ti_ar/ti_regress.dat
echo "diff exit=$?"
```
Expected: `exit=0`、差分なし。

- [ ] **Step 3: 全 tr/ti/tx テストが PASS することを最終確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh
```
Expected: 全テスト（既存 eq/tr/tx 含む）PASS。FAILED=0。

- [ ] **Step 4: 1e-10 で run-to-run が壊れている場合のみ tolerance を緩める判断**

差分があった場合:
1. `compare_metrics.py` を `1e-8` に緩めて再判定。
2. `test_run/README.md` と `run_tests.sh` の tolerance を `1e-8` に統一。
3. `git commit -m "test(ti): relax regression tolerance to 1e-8 (run-to-run drift observed)"`

問題なければ:
```bash
git commit --allow-empty -m "test(ti): confirmed 1e-10 tolerance stable across runs"
```

---

## Task 13: PR 作成と最終チェック

**Files:**
- なし（マージ準備）

- [ ] **Step 1: 全コミットを確認**

Run:
```bash
git log --oneline origin/develop..HEAD
```
Expected: Phase L-0 のコミット履歴がきれいに並ぶ（およそ 10〜13 コミット）。

- [ ] **Step 2: 変更ファイルのリストを確認**

Run:
```bash
git diff --stat origin/develop..HEAD
```
Expected:
- 新規: `ti/tiregress.f90`, `test_run/inputs/ti_*.in`, `test_run/scripts/extract_ti_metrics.py`, `test_run/scripts/tests/test_extract_ti_metrics.py`, `test_run/scripts/tests/test_compare_metrics_ti.py`, `test_run/scripts/tests/fixtures/sample_ti_regress.dat`, `test_run/baselines/ti_*/metrics.json`
- 修正: `ti/Makefile`, `ti/tiexec.f90`, `test_run/run_tests.sh`, `test_run/test_definitions.conf`, `test_run/scripts/check_regression.sh`, `test_run/scripts/compare_metrics.py`, `test_run/README.md`
- ti 既存ファイル `ticomm.f90` などへの変更が無いこと。

- [ ] **Step 3: push と PR 作成**

Run:
```bash
git push -u origin feature/ti-library-L0-baseline
gh pr create --base develop \
  --title "test(ti): add Phase L-0 regression test baseline" \
  --body "Phase L-0 of the ti module library-ization. Adds env-guarded high-precision dump (tiregress.f90), 3 regression test cases (ti_min/ti_ar/ti_w), and baselines under test_run/baselines/ti_*/. Tolerance 1e-10. No changes to existing ti runtime behavior."
```

- [ ] **Step 4: PR URL を記録**

Expected: PR が develop に向けて作成される。

---

## Dependencies

- 前段階: なし（develop の現状から開始可能）。develop は以下の TR Phase 0 関連 PR がマージ済みの想定:
  - PR #2 (`926b25b4`) — `feat(tr): env-guarded high-precision dump + 3 baselines`（参照する `compare_metrics.py` / `check_regression.sh` / `extract_tr_metrics.py` の出所）
  - PR #3 (`c559e06e`) — `docs(tr): add Phase L library-ization design spec`（本 ti 計画群の設計根拠）
- 後段階: L-1 以降、すべての Phase L サブが本 baseline に依存する。

## Fallback

| 障害 | 対処 |
|---|---|
| `tiregress.f90` の `USE ticomm, ONLY: ...` で未定義変数 | Task 2 Step 1 で確認、未定義変数を dump 対象から除外 |
| `ti_w.in` で ADAS データ取得に失敗 | `ID_NS(3)=5` (ADPOST) に切り替えるか、テストから除外して 2 ケースで継続 |
| run-to-run で `1e-10` を超える差分が出る | tolerance を `1e-8` に緩めて再生成。Task 12 Step 4 参照 |
| `ti` バイナリが menu モードで stdin EOF を待ち続ける | `.in` 末尾に `R\nQ\n` が確実に入っていることを確認（namelist `&end` の後） |
| `compare_metrics.py` 汎用化で tr 既存テストが壊れる | tr スキーマでは `scalars_int` が無い前提を確認、リスト型分岐が誤判定していないかを確認。最悪は tr/ti 用に別関数化 |
