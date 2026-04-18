# FP ライブラリ化 Phase L-0: 回帰テスト基盤整備とベースライン確立 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `fp/` モジュール（Fokker-Planck ソルバ、46 .f90 / 約 21,000 行）をライブラリ化する Phase L 全体に先立ち、TR Phase 0 と同じ「環境変数ガード付き高精度 dump + Python 比較スクリプト」方式で fp の数値挙動を固定する回帰テスト基盤を整備し、3 ケースのゴールデンベースラインを `test_run/baselines/fp_*/` に commit する。

**Architecture:** TR で確立した `tr_regress.dat` パターンを fp に転用する。fp 本体に環境変数 `FP_REGRESS_DUMP=1` のときのみ `fp_regress.dat` を書き出す `fpregress.f90` を 1 ファイル追加し、`fploop.f90` の `fp_loop` 末尾に 1 行フックを置く。通常実行（環境変数未設定）は完全不変。Python 側は TR 用に既にある `compare_metrics.py` を再利用し、新規の `extract_fp_metrics.py` を追加する。`run_tests.sh` には `fp` モジュール用のブランチを追加する。

**Tech Stack:** Fortran 90（`fpregress.f90` 追加）、Bash（既存 `run_tests.sh` の拡張）、Python 3 + 標準ライブラリのみ、gfortran (既存ビルド)、既存 FP バイナリ `fp/fp`、TR Phase 0 で確立済みの `test_run/scripts/compare_metrics.py`。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` （Phase L 設計を fp に転用）、TR Phase 0 plan `docs/superpowers/plans/2026-04-17-tr-refactoring-phase0.md`、TR Phase 0 PR #2 (merge `926b25b4`)。

---

## Module Survey (fp/)

L-0 開始前に確認した fp モジュールの構造:

| 項目 | 値 | 出典 |
|---|---|---|
| ソースファイル数 | 46 .f90 + 1 .f (`testnewton.f`) | `ls fp/*.f90` |
| 巨大ファイル | `fpgout.f90` 2029 行、`fpsave.f90` 1910 行、`fpprep.f90` 1633 行、`fpcomm.f90` 1405 行 | `wc -l` |
| メインプログラム | `fpmain.f90` (60 行、`PROGRAM fp`) | 同上 |
| メニュードライバ | `fpmenu.f90` (136 行、`MODULE fpmenu`、`fp_menu` SUBROUTINE) | 同上 |
| メインループ | `fploop.f90` (610 行、`MODULE fploop`、`fp_loop`) | 同上 |
| グローバル状態 | `fpcomm.f90` 内の `MODULE fpcomm_parm` + `MODULE fpcomm`（1 ファイル 32 SUBROUTINE） | 同上 |
| パラメータ初期化 | `fpinit.f90` (588 行、`MODULE fpinit`、`fp_init`) | 同上 |
| namelist パーサ | `fpparm.f90` の `fp_nlin` (`NAMELIST /FP/`、~110 変数を網羅) | 同上 |
| メイン allocate ルーチン | `fpsave.f90:342 fp_allocate` / `fp_deallocate` | `grep ALLOCATE` |
| グラフィクス | `fpgout.f90` (2029 行)、`fpgsub.f90`、`fpcont.f90`、`fpfout.f90` | ファイル名 |
| 既存 input サンプル | `fp/in/fp.inITER`、`fp/in/fp.injt60`、`fp/parm/fpparm.{DT1,DT2,DT3,DT4,wmep}` | `ls fp/in fp/parm` |

**ベースライン候補（L-0 で 3 ケース確定する）:**
1. `fp_iter01` ← `fp/in/fp.inITER`（ITER 標準、`NSMAX=3`、NRMAX=40, NPMAX=NTHMAX=50, NTMAX=5）
2. `fp_jt60`  ← `fp/in/fp.injt60`（JT-60、`NSMAX=3`、NRMAX=11, NPMAX=NTHMAX=100, NTMAX=1）
3. `fp_dt1`   ← `fp/parm/fpparm.DT1` を namelist 直渡しモードで（`NSMAX=4`、NRMAX=1）

**比較対象スカラー（fp 主要グローバル量）:**
- 制御: `NT, NRMAX, NSAMAX, NPMAX, NTHMAX, NTG2`
- 時刻: `TIMEFP`
- 各 species (`NSA=1..NSAMAX`) の累積: `RNT(NR,NSA,NTG)`, `RWT`, `RTT`, `RJT`, `RPCT`, `RPWT` の最終 NTG での `(NR=1..NRMAX, NSA=1..NSAMAX)` 配列

L-0 では **集約値（最終時刻の `RNT/RWT/RTT/RJT/RPCT/RPWT`）** をプロファイルとして dump し、これらに加え scalar 1-2 個（`TIMEFP, NT`）を出す。Layer 1（等価性）テストで利用する。

---

## File Structure

このフェーズで作成・変更するファイル:

| ファイル | 種別 | 責務 |
|---|---|---|
| `fp/fpregress.f90` | 新規 | 環境変数ガード付き高精度 dump（`1PE24.16` 書式） |
| `fp/fploop.f90` | 修正 | `fp_loop` 末尾（`9000 RETURN` 直前）に `tr_regress_dump_if_enabled` 相当の 1 行フック |
| `fp/Makefile` | 修正 | `SRCS=` に `fpregress.f90` を追加（依存も）|
| `test_run/inputs/fp_iter01.in` | 新規 | `fp/in/fp.inITER` の短縮版（`NTMAX` 据置 5、graphics/quit 簡略化）|
| `test_run/inputs/fp_jt60.in` | 新規 | `fp/in/fp.injt60` の短縮版 |
| `test_run/inputs/fp_dt1.in` | 新規 | `fp/parm/fpparm.DT1` を `R p ... q` シーケンスで包んだ FP 直起動入力 |
| `test_run/scripts/extract_fp_metrics.py` | 新規 | `fp_regress.dat` から指標 JSON を生成（`extract_tr_metrics.py` をテンプレに）|
| `test_run/scripts/tests/test_extract_fp_metrics.py` | 新規 | extractor の unittest（pytest）|
| `test_run/scripts/tests/fixtures/sample_fp_regress.dat` | 新規 | extractor 用の小型 fixture |
| `test_run/scripts/check_regression.sh` | 修正 | 第 1 引数のテスト名から module を判定し、TR は `extract_tr_metrics.py`、FP は `extract_fp_metrics.py` を呼ぶ。dump ファイル名も切替。 |
| `test_run/run_tests.sh` | 修正 | `module=="fp"` のとき `FP_REGRESS_DUMP=1` を export し、PASS 時に `check_regression.sh` を呼ぶ |
| `test_run/test_definitions.conf` | 修正 | `fp_iter01`, `fp_jt60`, `fp_dt1` の 3 行追加 |
| `test_run/baselines/fp_iter01/metrics.json` | 新規（生成） | ベースライン（コミット対象） |
| `test_run/baselines/fp_jt60/metrics.json` | 新規（生成） | 同上 |
| `test_run/baselines/fp_dt1/metrics.json` | 新規（生成） | 同上 |
| `test_run/README.md` | 修正 | FP 回帰の運用手順を追記（既存 TR セクションに並列で）|

**方針:**
- FP 本体への変更は **`fpregress.f90` 新規 1 ファイル + `fploop.f90` への 1 行フック + `Makefile` の SRCS に 1 ファイル追加** に厳格に限定する。`fp_loop` は MPI 並列で動くため、dump は `nrank == 0` のみで実施する点に注意。
- Python は標準ライブラリのみ。
- TR と同じ `1e-10` を初期許容誤差とする（FP の `-O0` run-to-run 再現性を Task 11 で実測して必要なら緩める）。
- ベースラインは初回 `--generate-baseline` モードで作成、以後は比較のみ。

---

## Task 1: 作業用ブランチ確認とビルド

**Files:** なし（環境準備）

- [ ] **Step 1: 現在の git 状態を確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git branch --show-current
git status --short
```
Expected: `feature/fp-library-L0` 等の作業用ブランチに居る、もしくは `develop` ベースで切る直前。`develop` の最新 (`c559e06e` 以降) が反映されていること。

- [ ] **Step 2: L-0 用ブランチを作る**

Run:
```bash
git fetch origin develop
git checkout -b feature/fp-library-L0 origin/develop
```
Expected: ブランチが切り替わる。

- [ ] **Step 3: コンパイラ最適化フラグが固定されていることを確認**

Run:
```bash
grep -n "^OFLAGS\|^DFLAGS\|^FFLAGS" /home/k-yoshimi/program/task/make.header | head -10
grep -n "^FFLAGS" /home/k-yoshimi/program/task/fp/Makefile
```
Expected:
- `make.header` に `OFLAGS = -g -O3 -m64 -std=legacy` 相当の 1 行が有効化されている。
- `fp/Makefile` の 13 行目が `FFLAGS=$(OFLAGS)` (DFLAGS 側はコメントアウト)。

- [ ] **Step 4: fp が依存するライブラリ（pl, eq, dp, ob, lib, mtxp, bpsd）と fp バイナリをビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/fp && make 2>&1 | tail -20
ls -la /home/k-yoshimi/program/task/fp/fp
```
Expected: `fp/fp` バイナリが生成される。エラーなし。Coverage で言うと `make libs` 経由で bpsd, libtask, libgrf, mtxp, pl, eq, dp, ob が順次ビルドされる（既にビルド済みなら skip）。

- [ ] **Step 5: 既存の fp 入力で手動スモークテスト（dump 機構なし）**

Run:
```bash
mkdir -p /tmp/fp_iter01_smoke
cd /tmp/fp_iter01_smoke
timeout 300 /home/k-yoshimi/program/task/fp/fp \
    < /home/k-yoshimi/program/task/fp/in/fp.inITER > out.log 2>&1
echo "exit=$?"
grep -c "CLOSED\|TASK/FP" out.log
tail -30 out.log
```
Expected: タイムアウトせずに完了。出力 log に `***** TASK/FP 2024/09/04 *****` の起動行と、メニュー処理経由で R (run) → q (quit) の対話が完了したログがある。`fpdata.ITER` が読まれない場合（`KNAMFP='../fp/fpdata.ITER'`）でも `fp_loop` が走ること（場合によっては `KNAMFP` を空にして再試行）。

- [ ] **Step 6: コミット（ブランチ初期化マーカー）**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "chore(fp): start Phase L-0 regression scaffolding"
```

---

## Task 2: 比較戦略の確定（dump 対象の最終決定）

**Files:** 調査のみ（この段階では新規ファイルなし）

**確定事項:**
- **dump 対象 scalar:** `NT, NRMAX, NSAMAX, NPMAX, NTHMAX, NTG2, TIMEFP`
- **dump 対象 profile:** 最終 NTG (`NTG = NTG2`) における
  `RNT(NR, NSA, NTG2)`, `RWT(...)`, `RTT(...)`, `RJT(...)`, `RPCT(...)`, `RPWT(...)`
  を `(NR=1..NRMAX, NSA=1..NSAMAX)` の 2 次元として書き出す。
- **書式:** scalar は `1PE24.16`、profile は 1 行に `NR NSA RNT RWT RTT RJT RPCT RPWT` の 8 列。
- **起動条件:** 環境変数 `FP_REGRESS_DUMP=1` のときのみ `fp_regress.dat` を CWD に書き出す。`nrank /= 0` のプロセスは何もしない。
- **許容誤差:** 初期 `1e-10`。Task 11 で run-to-run 差を実測して必要なら `1e-8` まで緩める。

- [ ] **Step 1: dump 対象配列が `fpcomm.f90` に存在することを確認**

Run:
```bash
grep -nE "^[[:space:]]+real.*allocatable.*::.*RN(T|DRT)\b|^[[:space:]]+real.*allocatable.*::.*R[WTJ]T\b|^[[:space:]]+real.*allocatable.*::.*RP[CW]T\b" /home/k-yoshimi/program/task/fp/fpcomm.f90 | head -10
grep -n "NTG2\b\|TIMEFP\b" /home/k-yoshimi/program/task/fp/fpcomm.f90 | head -10
```
Expected: `RNT, RWT, RTT, RJT, RPCT, RPWT` の `(NRMAX,NSAMAX,NTG2M)` の宣言と、`NTG2`, `TIMEFP` のスカラー宣言が見つかる（`fpcomm.f90` の `MODULE fpcomm` セクション）。

- [ ] **Step 2: `nrank` が `commpi` 経由で参照可能なことを確認**

Run:
```bash
grep -n "nrank\b" /home/k-yoshimi/program/task/fp/fploop.f90 | head -5
grep -n "use commpi\|USE commpi" /home/k-yoshimi/program/task/fp/fpcomm.f90 | head -3
```
Expected: `fploop.f90` 内で `nrank` が使われており、`fpcomm_parm` から transitively に参照できる。

- [ ] **Step 3: コミットで決定を固定**

Run:
```bash
cd /home/k-yoshimi/program/task
git add docs/superpowers/plans/2026-04-18-fp-library-L0-baseline.md
git commit -m "docs(fp): lock L-0 dump strategy (fp_regress.dat, tol 1e-10)"
```

---

## Task 3: `fp/fpregress.f90` を新規追加して高精度 dump を実装

**Files:**
- Create: `fp/fpregress.f90`
- Modify: `fp/fploop.f90`（USE 文 1 行 + 末尾に呼び出し 1 行）
- Modify: `fp/Makefile`（`SRCS` に `fpregress.f90` を追加 + 依存ルール 1 行）

**目的:** 環境変数 `FP_REGRESS_DUMP=1` のときに限り、`fp_loop` 終了時点の主要グローバル量と最終 NTG プロファイルを `fp_regress.dat` へ `1PE24.16` で書き出す。`nrank /= 0` のランクは何もしない。通常実行では何も書かない。

- [ ] **Step 1: `fp/fploop.f90` の `9000` ラベル位置を確認**

Run:
```bash
grep -n "9000\|END SUBROUTINE FP_LOOP\|END SUBROUTINE fp_loop" /home/k-yoshimi/program/task/fp/fploop.f90
```
Expected: `FP_LOOP` SUBROUTINE 末尾の `RETURN` 直前ラベルが見つかる。

- [ ] **Step 2: `fp/fpregress.f90` を新規作成**

作成: `fp/fpregress.f90`

```fortran
! fpregress.f90
!
! High-precision regression dump for Phase L-0 regression tests.
! Emits fp_regress.dat (1PE24.16 format) when FP_REGRESS_DUMP=1.
! Otherwise does nothing; normal runs are unaffected.
!
! Only nrank == 0 writes the dump (MPI-safe).

MODULE fpregress

  PRIVATE
  PUBLIC :: fp_regress_dump_if_enabled

CONTAINS

  SUBROUTINE fp_regress_dump_if_enabled
    USE fpcomm, ONLY: &
         NRMAX, NSAMAX, NPMAX, NTHMAX, NTG2, TIMEFP, &
         RNT, RWT, RTT, RJT, RPCT, RPWT, &
         nrank, rkind
    IMPLICIT NONE
    INTEGER, PARAMETER :: UNIT_DUMP = 87
    CHARACTER(LEN=16) :: ENV_VAL
    INTEGER :: STAT, NR, NSA, IOERR, NTG_LAST
    LOGICAL :: ENABLED

    IF (nrank /= 0) RETURN

    CALL GET_ENVIRONMENT_VARIABLE('FP_REGRESS_DUMP', ENV_VAL, STATUS=STAT)
    ENABLED = (STAT == 0 .AND. TRIM(ENV_VAL) == '1')
    IF (.NOT. ENABLED) RETURN

    NTG_LAST = MAX(NTG2, 1)   ! defensive: in case loop did not advance NTG2

    OPEN(UNIT=UNIT_DUMP, FILE='fp_regress.dat', &
         STATUS='REPLACE', ACTION='WRITE', IOSTAT=IOERR)
    IF (IOERR /= 0) THEN
       WRITE(6,*) 'XX fpregress: cannot open fp_regress.dat, IOSTAT=', IOERR
       RETURN
    END IF

    WRITE(UNIT_DUMP, '(A)')         '# TASK/FP regression dump (format v1)'
    WRITE(UNIT_DUMP, '(A,I0)')      'NRMAX=',  NRMAX
    WRITE(UNIT_DUMP, '(A,I0)')      'NSAMAX=', NSAMAX
    WRITE(UNIT_DUMP, '(A,I0)')      'NPMAX=',  NPMAX
    WRITE(UNIT_DUMP, '(A,I0)')      'NTHMAX=', NTHMAX
    WRITE(UNIT_DUMP, '(A,I0)')      'NTG2=',   NTG2
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'TIMEFP=', TIMEFP

    WRITE(UNIT_DUMP, '(A)') &
         '# profile columns: NR NSA RNT RWT RTT RJT RPCT RPWT (at NTG=NTG2)'
    DO NSA = 1, NSAMAX
       DO NR = 1, NRMAX
          WRITE(UNIT_DUMP, '(I5,1X,I3,6(1X,1PE24.16))') &
               NR, NSA, &
               RNT (NR, NSA, NTG_LAST), &
               RWT (NR, NSA, NTG_LAST), &
               RTT (NR, NSA, NTG_LAST), &
               RJT (NR, NSA, NTG_LAST), &
               RPCT(NR, NSA, NTG_LAST), &
               RPWT(NR, NSA, NTG_LAST)
       END DO
    END DO

    CLOSE(UNIT_DUMP)
  END SUBROUTINE fp_regress_dump_if_enabled

END MODULE fpregress
```

注: Task 2 Step 1 で `RPCT2` などしか存在しない、あるいは `RNT` の shape が `(NRMAX,NSAMAX,NTG2M)` でないと判明した場合は、ここの USE と WRITE 行を実形に合わせて削除/置換する（ビルドエラー回避）。

- [ ] **Step 3: `fp/Makefile` の `SRCS=` に `fpregress.f90` を追加**

`fp/Makefile` の 31〜41 行目の `SRCS = ...` 末尾、`fpmenu.f90` の前に `fpregress.f90` を入れる:

変更前（41 行目付近）:
```
		fpcont.f90 fpfout.f90 fpgsub.f90 fpgout.f90 fpfile.f90 \
		fpmenu.f90
```

変更後:
```
		fpcont.f90 fpfout.f90 fpgsub.f90 fpgout.f90 fpfile.f90 \
		fpregress.f90 \
		fpmenu.f90
```

そして `Makefile` の依存記述ブロック（88 行目以降）に以下を追加（既存の `fploop.o` 依存行の直後あたり）:

```
$(OBJDIR)/fpregress.o : fpregress.f90 fpcomm.f90
```

`fploop.o` の依存に `fpregress.f90` を加える（98-100 行目の `$(OBJDIR)/fploop.o :` を更新）:

変更前:
```
$(OBJDIR)/fploop.o : fpoutdata.f90 fpnfrr.f90 fpsave.f90 fpexec.f90 \
                     fpprep.f90 fpcoef.f90 fpdisrupt.f90 fpreadeg.f90 \
                     fploop.f90 fpcomm.f90 fpoutdata.f90 fplib.f90
```

変更後:
```
$(OBJDIR)/fploop.o : fpoutdata.f90 fpnfrr.f90 fpsave.f90 fpexec.f90 \
                     fpprep.f90 fpcoef.f90 fpdisrupt.f90 fpreadeg.f90 \
                     fploop.f90 fpcomm.f90 fpoutdata.f90 fplib.f90 \
                     fpregress.f90
```

- [ ] **Step 4: `fp/fploop.f90` を修正してフックを追加**

`fp/fploop.f90` の冒頭 USE ブロック（7-19 行目付近、`MODULE fploop` 直下）に追加:

```fortran
      use fpregress, only : fp_regress_dump_if_enabled
```

そして `SUBROUTINE FP_LOOP` 末尾の `9000 ... RETURN` 直前に呼び出しを挿入。具体的には末尾ラベル `9000` の手前で:

```fortran
      CALL fp_regress_dump_if_enabled   ! Phase L-0 regression dump (env-guarded, MPI rank 0)
 9000 CONTINUE
      RETURN
```

`9000` ラベルが既存の文に紐付いている場合は、`CALL` をそのブロックの後・`RETURN` の前に置く。挿入箇所が `9000 RETURN` の単独行なら以下のように置換:

変更前:
```
 9000 RETURN
      END SUBROUTINE FP_LOOP
```

変更後:
```
      CALL fp_regress_dump_if_enabled   ! Phase L-0 regression dump (env-guarded, MPI rank 0)
 9000 RETURN
      END SUBROUTINE FP_LOOP
```

- [ ] **Step 5: FP をリビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/fp
make 2>&1 | tail -10
```
Expected: `fpregress.f90` のコンパイルが実行され、`fp` バイナリが更新される。エラーなし。

- [ ] **Step 6: 通常実行で dump が作られないことを確認（副作用ゼロ）**

Run:
```bash
mkdir -p /tmp/fp_no_dump_check && cd /tmp/fp_no_dump_check
unset FP_REGRESS_DUMP
timeout 300 /home/k-yoshimi/program/task/fp/fp \
    < /home/k-yoshimi/program/task/fp/in/fp.inITER > out.log 2>&1
ls -la fp_regress.dat 2>&1 | head -3
```
Expected: `fp_regress.dat` は **作られない** (`No such file or directory`)。

- [ ] **Step 7: 環境変数を立てると dump が出ることを確認**

Run:
```bash
mkdir -p /tmp/fp_with_dump && cd /tmp/fp_with_dump
FP_REGRESS_DUMP=1 timeout 300 /home/k-yoshimi/program/task/fp/fp \
    < /home/k-yoshimi/program/task/fp/in/fp.inITER > out.log 2>&1
ls -la fp_regress.dat
head -15 fp_regress.dat
tail -5 fp_regress.dat
```
Expected: `fp_regress.dat` が存在。先頭行 `# TASK/FP regression dump (format v1)`、scalar 7 行、profile が `NRMAX*NSAMAX` 行分。

- [ ] **Step 8: 同一入力で 2 回走らせて dump が bit-exact に一致することを確認**

Run:
```bash
cd /tmp/fp_with_dump
FP_REGRESS_DUMP=1 timeout 300 /home/k-yoshimi/program/task/fp/fp \
    < /home/k-yoshimi/program/task/fp/in/fp.inITER > /dev/null 2>&1
cp fp_regress.dat /tmp/fp_dump_run1.dat
FP_REGRESS_DUMP=1 timeout 300 /home/k-yoshimi/program/task/fp/fp \
    < /home/k-yoshimi/program/task/fp/in/fp.inITER > /dev/null 2>&1
diff /tmp/fp_dump_run1.dat fp_regress.dat
echo "diff exit=$?"
```
Expected: `diff` 出力空、`exit=0`。run-to-run で完全一致。

差異が出た場合の **撤退条件**: MPI 起因の非決定性が疑われるなら、Task 2 で設定した `1e-10` を `1e-8` に緩めて Task 11 で改めて測定する。それでも不安定なら本 L-0 を `nrank == 0 && nsize == 1`（シングルプロセス）限定の dump に縮退する。

- [ ] **Step 9: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add fp/fpregress.f90 fp/fploop.f90 fp/Makefile
git commit -m "feat(fp): add env-guarded high-precision dump for L-0 regression"
```

---

## Task 4: 指標抽出スクリプト `extract_fp_metrics.py` を書く

**Files:**
- Create: `test_run/scripts/extract_fp_metrics.py`
- Create: `test_run/scripts/tests/test_extract_fp_metrics.py`
- Create: `test_run/scripts/tests/fixtures/sample_fp_regress.dat`

- [ ] **Step 1: サンプル fixture を作成**

作成: `test_run/scripts/tests/fixtures/sample_fp_regress.dat`

内容（Task 3 の dump 形式に準拠した最小サンプル。NRMAX=2, NSAMAX=2）:
```
# TASK/FP regression dump (format v1)
NRMAX=2
NSAMAX=2
NPMAX=10
NTHMAX=10
NTG2=3
TIMEFP=2.0000000000000000E-03
# profile columns: NR NSA RNT RWT RTT RJT RPCT RPWT (at NTG=NTG2)
    1   1  7.0000000000000007E-01  4.5650000000000004E+00  4.2750000000000004E+00  1.5451000000000000E+01  3.0000000000000001E-01  1.2000000000000000E-01
    2   1  6.5000000000000002E-01  4.2000000000000002E+00  3.9000000000000004E+00  1.4000000000000000E+01  2.8000000000000000E-01  1.1000000000000000E-01
    1   2  3.1500000000000000E-01  2.0000000000000000E+00  2.1000000000000001E+00  3.4000000000000002E+00  4.0000000000000002E-02  3.0000000000000001E-02
    2   2  3.0000000000000004E-01  1.8000000000000000E+00  1.9000000000000001E+00  3.0000000000000000E+00  3.5000000000000003E-02  2.5000000000000001E-02
```

- [ ] **Step 2: 失敗するテストを書く**

作成: `test_run/scripts/tests/test_extract_fp_metrics.py`

```python
import json
import subprocess
import sys
from pathlib import Path

SCRIPT  = Path(__file__).parent.parent / "extract_fp_metrics.py"
FIXTURE = Path(__file__).parent / "fixtures" / "sample_fp_regress.dat"


def run_extract(dump_path: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(dump_path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def test_extracts_scalars():
    data = run_extract(FIXTURE)
    assert data["NRMAX"] == 2
    assert data["NSAMAX"] == 2
    assert data["NPMAX"] == 10
    assert data["NTHMAX"] == 10
    assert data["NTG2"] == 3
    assert data["scalars"]["TIMEFP"] == 2.0e-3


def test_extracts_profile_rows():
    data = run_extract(FIXTURE)
    prof = data["profile"]
    # NRMAX * NSAMAX = 4 rows
    assert len(prof) == 4
    row = prof[0]
    assert row["NR"] == 1 and row["NSA"] == 1
    assert row["RNT"] == 0.7
    assert row["RJT"] == 15.451
    last = prof[-1]
    assert last["NR"] == 2 and last["NSA"] == 2
    assert last["RWT"] == 1.8


def test_rejects_incomplete_dump(tmp_path):
    incomplete = tmp_path / "bad.dat"
    incomplete.write_text("# TASK/FP regression dump (format v1)\nNRMAX=1\n")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(incomplete)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0


def test_rejects_row_count_mismatch(tmp_path):
    bad = tmp_path / "bad.dat"
    bad.write_text(
        "# TASK/FP regression dump (format v1)\n"
        "NRMAX=2\nNSAMAX=2\nNPMAX=10\nNTHMAX=10\nNTG2=1\n"
        "TIMEFP=1.0000000000000000E-03\n"
        "# profile columns: NR NSA RNT RWT RTT RJT RPCT RPWT (at NTG=NTG2)\n"
        "    1   1  1.0E+00  1.0E+00  1.0E+00  1.0E+00  1.0E+00  1.0E+00\n"
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(bad)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
```

- [ ] **Step 3: テストを走らせて失敗を確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run/scripts
python3 -m pytest tests/test_extract_fp_metrics.py -v
```
Expected: FAIL（`extract_fp_metrics.py` 不在）。

- [ ] **Step 4: スクリプト本体を実装**

作成: `test_run/scripts/extract_fp_metrics.py`

```python
#!/usr/bin/env python3
"""Convert fp_regress.dat into a JSON for regression comparison.

Usage:
    extract_fp_metrics.py path/to/fp_regress.dat
Output (stdout JSON):
    NRMAX, NSAMAX, NPMAX, NTHMAX, NTG2 (int),
    scalars (dict[str,float]) — currently {"TIMEFP": ...},
    profile (list[dict]) — one dict per (NR, NSA) row, fields:
        NR, NSA, RNT, RWT, RTT, RJT, RPCT, RPWT.
"""
import argparse
import json
import re
import sys
from pathlib import Path


INT_KEYS    = {"NRMAX", "NSAMAX", "NPMAX", "NTHMAX", "NTG2"}
SCALAR_KEYS = {"TIMEFP"}
PROFILE_FIELDS = ("RNT", "RWT", "RTT", "RJT", "RPCT", "RPWT")
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
            if key in INT_KEYS:
                result[key] = int(val)
            elif key in SCALAR_KEYS:
                result["scalars"][key] = float(val)
            else:
                pass  # ignore unknown
        else:
            parts = line.split()
            expected = 2 + len(PROFILE_FIELDS)  # NR + NSA + 6 fields
            if len(parts) != expected:
                raise SystemExit(
                    f"malformed profile row (expected {expected} cols, got {len(parts)}): {raw}"
                )
            row = {"NR": int(parts[0]), "NSA": int(parts[1])}
            for i, field in enumerate(PROFILE_FIELDS, start=2):
                row[field] = float(parts[i])
            result["profile"].append(row)

    for k in INT_KEYS:
        if k not in result:
            raise SystemExit(f"missing header field: {k}")
    expected_rows = result["NRMAX"] * result["NSAMAX"]
    if len(result["profile"]) != expected_rows:
        raise SystemExit(
            f"profile row count {len(result['profile'])} != NRMAX*NSAMAX {expected_rows}"
        )
    if "TIMEFP" not in result["scalars"]:
        raise SystemExit("missing TIMEFP")
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

- [ ] **Step 5: 実行権限を付けてテスト再実行**

Run:
```bash
chmod +x /home/k-yoshimi/program/task/test_run/scripts/extract_fp_metrics.py
cd /home/k-yoshimi/program/task/test_run/scripts
python3 -m pytest tests/test_extract_fp_metrics.py -v
```
Expected: 4 tests PASS。

- [ ] **Step 6: 実 dump で動作確認**

Run:
```bash
python3 /home/k-yoshimi/program/task/test_run/scripts/extract_fp_metrics.py \
    /tmp/fp_with_dump/fp_regress.dat | head -40
```
Expected: NRMAX/NSAMAX/etc.、scalars に TIMEFP、profile の先頭数行が JSON で出る。

- [ ] **Step 7: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/scripts/extract_fp_metrics.py test_run/scripts/tests/test_extract_fp_metrics.py test_run/scripts/tests/fixtures/sample_fp_regress.dat
git commit -m "test(fp): add metric extractor reading fp_regress.dat"
```

---

## Task 5: 比較スクリプトを再利用するため `compare_metrics.py` の互換性を確認

**Files:**
- 検証のみ。`test_run/scripts/compare_metrics.py` は TR 用のままでも fp の JSON スキーマと互換性があるかを確認する。

`compare_metrics.py` は scalars 辞書と profile (list of dicts) を比較する汎用設計だが、TR 用には profile のフィールドが `RN, RT, AJ, QP` 固定でハードコードされている可能性がある。L-0 では fp の追加フィールドを扱えるよう、汎用化する小さな修正を入れる。

- [ ] **Step 1: 現行の `compare_metrics.py` を読み、profile フィールドのハードコードを確認**

Run:
```bash
grep -n "RN\|RT\|AJ\|QP" /home/k-yoshimi/program/task/test_run/scripts/compare_metrics.py
```
Expected: 文字列リテラルとして `("AJ", "QP")` や `("RN", "RT")` がハードコードされている行が見つかる。

- [ ] **Step 2: `compare_metrics.py` を「profile dict の int 以外の全 key を比較」する汎用版に書き換える失敗テストを書く**

`test_run/scripts/tests/test_compare_metrics.py` の末尾に追記:

```python
def test_passes_on_identical_fp_schema(tmp_path):
    fp_sample = {
        "NRMAX": 2, "NSAMAX": 2, "NPMAX": 10, "NTHMAX": 10, "NTG2": 1,
        "scalars": {"TIMEFP": 1.0e-3},
        "profile": [
            {"NR": 1, "NSA": 1, "RNT": 0.7, "RWT": 4.5, "RTT": 4.2, "RJT": 15.4, "RPCT": 0.3, "RPWT": 0.12},
            {"NR": 2, "NSA": 1, "RNT": 0.65, "RWT": 4.2, "RTT": 3.9, "RJT": 14.0, "RPCT": 0.28, "RPWT": 0.11},
            {"NR": 1, "NSA": 2, "RNT": 0.31, "RWT": 2.0, "RTT": 2.1, "RJT": 3.4, "RPCT": 0.04, "RPWT": 0.03},
            {"NR": 2, "NSA": 2, "RNT": 0.30, "RWT": 1.8, "RTT": 1.9, "RJT": 3.0, "RPCT": 0.035, "RPWT": 0.025},
        ],
    }
    base = tmp_path / "base.json"; act = tmp_path / "act.json"
    write_json(base, fp_sample); write_json(act, fp_sample)
    res = run_compare(act, base)
    assert res.returncode == 0, res.stderr


def test_fails_on_fp_profile_drift(tmp_path):
    base_obj = {
        "NRMAX": 1, "NSAMAX": 1, "NPMAX": 10, "NTHMAX": 10, "NTG2": 1,
        "scalars": {"TIMEFP": 1.0e-3},
        "profile": [{"NR": 1, "NSA": 1, "RNT": 0.7, "RWT": 4.5, "RTT": 4.2, "RJT": 15.4, "RPCT": 0.3, "RPWT": 0.12}],
    }
    act_obj = json.loads(json.dumps(base_obj))
    act_obj["profile"][0]["RWT"] = 4.5 * (1.0 + 1e-7)
    base = tmp_path / "base.json"; act = tmp_path / "act.json"
    write_json(base, base_obj); write_json(act, act_obj)
    res = run_compare(act, base, tol="1e-10")
    assert res.returncode != 0
    assert "RWT" in res.stdout
```

- [ ] **Step 3: テスト実行で失敗を確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run/scripts
python3 -m pytest tests/test_compare_metrics.py -v
```
Expected: 上記 2 テストが FAIL（旧 compare_metrics は `AJ/QP/RN/RT` だけ比較するため新フィールドを見逃すか、逆に存在しないキーで KeyError）。

- [ ] **Step 4: `compare_metrics.py` を汎用化**

`test_run/scripts/compare_metrics.py` の profile 比較ロジックを以下に置換（コア部分）:

```python
    for i, (br, ar) in enumerate(zip(b_prof, a_prof)):
        # integer index keys must match exactly
        for ikey in ("NR", "NSA"):
            if ikey in br or ikey in ar:
                if br.get(ikey) != ar.get(ikey):
                    errors.append(f"profile[{i}].{ikey}: baseline={br.get(ikey)} actual={ar.get(ikey)}")
        # compare any other field (assumed scalar float) present in baseline
        all_keys = set(br) | set(ar)
        for field in sorted(all_keys - {"NR", "NSA"}):
            bv = br.get(field); av = ar.get(field)
            if bv is None or av is None:
                errors.append(f"profile[{i}].{field}: missing")
                continue
            if isinstance(bv, list) or isinstance(av, list):
                # legacy TR shape with list-valued fields (RN, RT)
                if not isinstance(bv, list) or not isinstance(av, list) or len(bv) != len(av):
                    errors.append(f"profile[{i}].{field}: shape differ")
                    continue
                for j, (bvj, avj) in enumerate(zip(bv, av)):
                    _check_scalar(f"profile[{i}].{field}[{j}]", float(bvj), float(avj), tol, errors)
            else:
                _check_scalar(f"profile[{i}].{field}", float(bv), float(av), tol, errors)
```

これにより TR 既存スキーマ（`RN/RT` が list、`AJ/QP` が float）も FP 新スキーマ（全フィールド float、`NSA` キー追加）も同じロジックで比較できる。

- [ ] **Step 5: 全 compare_metrics テスト再実行**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run/scripts
python3 -m pytest tests/test_compare_metrics.py -v
```
Expected: 既存 5 + 新規 2 = 全 7 tests PASS。TR 等価テスト（baselines/tr_iter01 等）が回帰しないことも以下で確認:

```bash
./run_tests.sh tr_iter01 tr_m0904 tr_tst2
```
Expected: 全て PASS（既存 TR ベースラインが許容誤差内）。

- [ ] **Step 6: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/scripts/compare_metrics.py test_run/scripts/tests/test_compare_metrics.py
git commit -m "test: generalize compare_metrics profile field matcher (covers FP schema)"
```

---

## Task 6: `check_regression.sh` をモジュール非依存化

**Files:**
- Modify: `test_run/scripts/check_regression.sh`

第 1 引数のテスト名のプレフィクス（`tr_*` / `fp_*`）または別途渡す `--module` 引数で extractor とダンプファイル名を切り替えられるようにする。

- [ ] **Step 1: 現行スクリプトの I/F を確認**

Run:
```bash
cat /home/k-yoshimi/program/task/test_run/scripts/check_regression.sh
```
Expected: `DUMP="$OUTPUT_DIR/tr_regress.dat"` と `extract_tr_metrics.py` がハードコードされている。

- [ ] **Step 2: スクリプトをモジュール対応に書き換え**

修正版 `test_run/scripts/check_regression.sh`:

```bash
#!/bin/bash
#
# check_regression.sh <test_name> <test_output_dir> <baselines_dir> [tolerance] [--generate-baseline]
#
# テスト名のプレフィクスから対象モジュールを推定する:
#   tr_*  -> tr_regress.dat / extract_tr_metrics.py
#   fp_*  -> fp_regress.dat / extract_fp_metrics.py
# それ以外は失敗扱い。
#
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_NAME="${1:?usage: $0 <test_name> <output_dir> <baselines_dir> [tol] [--generate-baseline]}"
OUTPUT_DIR="${2:?}"
BASELINES_DIR="${3:?}"
TOL="${4:-1e-10}"
MODE="${5:-compare}"

case "$TEST_NAME" in
  tr_*) DUMP_BASENAME="tr_regress.dat"; EXTRACTOR="extract_tr_metrics.py" ;;
  fp_*) DUMP_BASENAME="fp_regress.dat"; EXTRACTOR="extract_fp_metrics.py" ;;
  *)
    echo "check_regression: unsupported test name prefix: $TEST_NAME" >&2
    exit 4
    ;;
esac

DUMP="$OUTPUT_DIR/$DUMP_BASENAME"
METRICS_ACTUAL="$OUTPUT_DIR/metrics.json"
METRICS_BASE="$BASELINES_DIR/$TEST_NAME/metrics.json"

if [[ ! -f "$DUMP" ]]; then
    echo "check_regression: dump not found: $DUMP" >&2
    echo "  did the test run with the *_REGRESS_DUMP=1 env var exported?" >&2
    exit 2
fi

if ! python3 "$SCRIPT_DIR/$EXTRACTOR" "$DUMP" > "$METRICS_ACTUAL"; then
    echo "check_regression: failed to parse $DUMP with $EXTRACTOR" >&2
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

- [ ] **Step 3: TR 既存 3 ケースが従来通り PASS することを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tr_iter01 tr_m0904 tr_tst2
```
Expected: 全 PASS。

- [ ] **Step 4: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/scripts/check_regression.sh
git commit -m "test: route check_regression by tr_/fp_ test name prefix"
```

---

## Task 7: `run_tests.sh` に FP モジュール対応を追加

**Files:**
- Modify: `test_run/run_tests.sh`

`run_single_test` 内で `module == "fp"` のとき `FP_REGRESS_DUMP=1` を export し、PASS 判定後に `check_regression.sh` を呼ぶ。

- [ ] **Step 1: 現行ロジックを確認**

Run:
```bash
grep -n "tr_env\|TR_REGRESS_DUMP\|module == \"tr\"\|module == \"fp\"" /home/k-yoshimi/program/task/test_run/run_tests.sh
```
Expected: TR 用のブランチ（297-301 行目あたり）、検証ブランチ（321-328 行目あたり）が見つかる。

- [ ] **Step 2: TR 用 env 設定を fp にも拡張**

`test_run/run_tests.sh` の以下を変更:

変更前（297-301 行目あたり）:
```bash
    # For TR module, enable regression dump (env-guarded inside trregress.f90).
    local tr_env=()
    if [[ "$module" == "tr" ]]; then
        tr_env=(env TR_REGRESS_DUMP=1)
    fi
```

変更後:
```bash
    # For TR/FP modules, enable regression dump (env-guarded inside the dumper).
    local mod_env=()
    case "$module" in
        tr) mod_env=(env TR_REGRESS_DUMP=1) ;;
        fp) mod_env=(env FP_REGRESS_DUMP=1) ;;
    esac
```

そして実行ブロック（304-310 行目あたり）の `"${tr_env[@]}"` を `"${mod_env[@]}"` に置換。

- [ ] **Step 3: 検証ブランチを fp にも拡張**

変更前（321-328 行目あたり）:
```bash
        local reg_ok=1
        if [[ "$module" == "tr" ]]; then
            if ! "$SCRIPT_DIR/scripts/check_regression.sh" \
                    "$test_name" "$test_dir" "$SCRIPT_DIR/baselines" "1e-10" \
                    > "$test_dir/regression.log" 2>&1; then
                reg_ok=0
            fi
        fi
```

変更後:
```bash
        local reg_ok=1
        if [[ "$module" == "tr" || "$module" == "fp" ]]; then
            if ! "$SCRIPT_DIR/scripts/check_regression.sh" \
                    "$test_name" "$test_dir" "$SCRIPT_DIR/baselines" "1e-10" \
                    > "$test_dir/regression.log" 2>&1; then
                reg_ok=0
            fi
        fi
```

- [ ] **Step 4: TR 既存 3 ケースが従来通り PASS することを確認（regression）**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tr_iter01 tr_m0904 tr_tst2
```
Expected: 全 PASS。

- [ ] **Step 5: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/run_tests.sh
git commit -m "test: wire FP_REGRESS_DUMP and FP regression check into run_tests.sh"
```

---

## Task 8: `fp_iter01` 入力ケースを追加

**Files:**
- Create: `test_run/inputs/fp_iter01.in`

**前提:** `fp/in/fp.inITER` は対話シーケンスが長く、`fpdata.ITER`/`wrdata.ITER` 等の外部入力に依存する可能性がある。回帰テスト用には依存最小・graphics スキップのバリエーションを作る。

- [ ] **Step 1: 元入力を一読**

Run:
```bash
cat /home/k-yoshimi/program/task/fp/in/fp.inITER
```
Expected: 先頭の `0`, `f`, `gsdata.ITER`, `c`, `p` ... `r` ... `f2` ... の順序が確認できる。

- [ ] **Step 2: 短縮版を作成**

作成: `test_run/inputs/fp_iter01.in`

```
0
f
gsdata.ITER
c
p
 &fp
   modelg=3,KNAMEQ='../eq/eqdata.ITER'
   modelw=2,KNAMWR='../wr/wrdata.ITER'
            KNAMFP='../fp/fpdata.ITER'
   NSMAX=3
   PA(2)=2.0,PA(3)=3.0
   PN=0.8,0.4,0.4
   PNS=0.01,0.005,0.005
   PTPR=20.0,20.0,20.0
   PTPP=20.0,20.0,20.0
   PROFN2=0.5
   MODELN=1
   NRMAX=40
   RMIN=0.4D0
   RMAX=0.8D0
   NTMAX=2
   PMAX=10.D0
   NPMAX=50
   NTHMAX=50
   MODELC=4
   MODELR=1
   DELT=1.d-3
   NTSTEP_COLL=1
   NSAMAX=1
   NSBMAX=3
   NS_NSA(1)=1
   NS_NSB(1)=1
   NS_NSB(2)=2
   NS_NSB(3)=3
   PABS_WR=1.D0
 &end
r
q
```

変更点:
- 元の `NTMAX=5` を `NTMAX=2` に短縮（CI 高速化）。
- 元の `v r s g n1 ...` 等のグラフ系を全削除し、`r` (run) 後すぐ `q` (quit)。
- `f` 後の `gsdata.ITER`、`KNAMFP='../fp/fpdata.ITER'` 等の外部入力依存はそのまま温存（手動スモークで読めるか確認）。

- [ ] **Step 3: 手動スモーク**

Run:
```bash
mkdir -p /tmp/fp_iter01_probe && cd /tmp/fp_iter01_probe
FP_REGRESS_DUMP=1 timeout 600 /home/k-yoshimi/program/task/fp/fp \
    < /home/k-yoshimi/program/task/test_run/inputs/fp_iter01.in > out.log 2>&1
echo "exit=$?"
ls -la fp_regress.dat
grep -c "CLOSED" out.log
tail -20 out.log
```
Expected: `fp_regress.dat` が生成、`out.log` 末尾に正常終了の痕跡。`CLOSED` が見つからなくても、`fp_regress.dat` が正しい行数（NRMAX*NSAMAX = 40 行）あれば OK。

`fpdata.ITER` 不在で即 abort する場合: Step 2 の `KNAMFP` 行を `KNAMFP=' '` に変更してリトライ。

- [ ] **Step 4: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/inputs/fp_iter01.in
git commit -m "test(fp): add ITER fp regression input (NSAMAX=1, NTMAX=2)"
```

---

## Task 9: `fp_jt60` 入力ケースを追加

**Files:**
- Create: `test_run/inputs/fp_jt60.in`

- [ ] **Step 1: 元入力を一読**

Run:
```bash
cat /home/k-yoshimi/program/task/fp/in/fp.injt60
```

- [ ] **Step 2: 短縮版を作成**

作成: `test_run/inputs/fp_jt60.in`

`fp/in/fp.injt60` を以下のとおり修正してコピー:
- 末尾の対話シーケンス（graphics 系）を削除し `r` → `q` に。
- `NTMAX=1` のまま維持（既に十分短い）。
- 必要なら `KNAMFP` を空文字列にして外部入力依存を切る。

最低限の構成:
```
0
f
fpjt60.gs
c
p
 &fp
   modelg=3,KNAMEQ='../eq/eqdata.jt60'
   modelw=4,KNAMWM='../wm/wmdata.jt60'
            KNAMFP=' '
   NSMAX=3
   PA(2)=2.0
   PZ(2)=1.0
   PA(3)=1.0
   PZ(3)=1.0
   PN= 0.3,0.285,0.015
   PNS=0.03,0.0285,0.0015
   PROFN2=0.5
   PTPR=3.7,3.7,3.7
   PTPP=3.7,3.7,3.7
   PTS= 0.4,0.4,0.4
   PROFT2=2.0
   RFDW=55
   NRMAX=11
   RMIN=0.1D0
   RMAX=0.4D0
   NTMAX=1
   PMAX=20.D0
   NPMAX=100
   NTHMAX=100
   MODELC=4
 &end
r
q
```

- [ ] **Step 3: 手動スモーク**

Run:
```bash
mkdir -p /tmp/fp_jt60_probe && cd /tmp/fp_jt60_probe
FP_REGRESS_DUMP=1 timeout 600 /home/k-yoshimi/program/task/fp/fp \
    < /home/k-yoshimi/program/task/test_run/inputs/fp_jt60.in > out.log 2>&1
echo "exit=$?"; ls -la fp_regress.dat
head -10 fp_regress.dat
```
Expected: `fp_regress.dat` 生成、`NRMAX=11` の指標。

外部入力 `eqdata.jt60`/`wmdata.jt60` 不在で abort する場合: 当該ファイルを fp/in/ から手動コピー、または Task 8 で使った ITER ベースの 2 番目バリエーション（`NRMAX` 違いなど）に切替検討。

- [ ] **Step 4: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/inputs/fp_jt60.in
git commit -m "test(fp): add JT-60 fp regression input"
```

---

## Task 10: `fp_dt1` 入力ケースを追加（namelist 直渡しモード）

**Files:**
- Create: `test_run/inputs/fp_dt1.in`

`fp/parm/fpparm.DT1` は `&fp ... &end` だけが入った namelist 断片。これを fp の `R p` 直接入力で食わせる:

- [ ] **Step 1: 元 namelist 内容を一読**

Run:
```bash
cat /home/k-yoshimi/program/task/fp/parm/fpparm.DT1
```

- [ ] **Step 2: 入力を組み立て**

作成: `test_run/inputs/fp_dt1.in`

```
0
f
fpdt1.gs
c
p
 &fp
   NSMAX=4
   NSFPMI=1
   NSFPMA=1
   PA(2)=2.D0,3.D0,4.D0
   PZ(2)=1.D0,1.D0,2.D0
   PN(1)=1.D0,0.45D0,0.45D0,0.05D0
   PNS(1)=0.1D0,0.045D0,0.045D0,0.005D0
   PTPR(1)=20.D0,20.D0,20.D0,20.D0
   PTPP(1)=20.D0,20.D0,20.D0,20.D0
   PTS(1)=1.D0,1.D0,1.D0,1.D0
   NRMAX=1
   NTHMAX=50
   NPMAX=50
   PMAX=20.D0
   MODELR=1
   MODELW(1)=0
   DEC=4.0D0
   PEC1=-0.5
   PEC2=0.1
   NTMAX=1
 &end
r
q
```

注: `fpparm.DT1` に `NTMAX` が無ければ default のままになるので、上のように 1 を明示。`NSFPMI/NSFPMA` は元 namelist にあるが fp_nlin で受けないなら IOSTAT エラーになる可能性 → スモークでチェック。

- [ ] **Step 3: 手動スモーク**

Run:
```bash
mkdir -p /tmp/fp_dt1_probe && cd /tmp/fp_dt1_probe
FP_REGRESS_DUMP=1 timeout 300 /home/k-yoshimi/program/task/fp/fp \
    < /home/k-yoshimi/program/task/test_run/inputs/fp_dt1.in > out.log 2>&1
echo "exit=$?"; ls -la fp_regress.dat
head -10 fp_regress.dat
```
Expected: `fp_regress.dat` 生成、`NRMAX=1` で profile が `NRMAX*NSAMAX = 1*1 = 1` 行（`NSAMAX` 既定値次第）。

`NSFPMI` 等が namelist で受け付けられず IOSTAT エラーが出る場合は当該行を削除。それでも厳しい場合は `fpparm.DT2/DT3` で再試行し、Task 10 のケース名を変更する（`fp_dt2` 等）。

- [ ] **Step 4: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/inputs/fp_dt1.in
git commit -m "test(fp): add DT1 fp regression input (NRMAX=1 minimal case)"
```

---

## Task 11: `test_definitions.conf` に 3 ケースを登録、ベースライン生成

**Files:**
- Modify: `test_run/test_definitions.conf`
- Create (生成): `test_run/baselines/fp_iter01/metrics.json`
- Create (生成): `test_run/baselines/fp_jt60/metrics.json`
- Create (生成): `test_run/baselines/fp_dt1/metrics.json`

- [ ] **Step 1: `test_run/test_definitions.conf` の末尾に FP セクションを追加**

`test_run/test_definitions.conf` の末尾に以下を追記:

```
# =============================================================================
# FP Module Tests (Fokker-Planck solver)
# =============================================================================
fp_iter01:fp:@inputs/fp_iter01.in:none:600:ITER FP (NSAMAX=1, NTMAX=2)
fp_jt60:fp:@inputs/fp_jt60.in:none:600:JT-60 FP (NRMAX=11)
fp_dt1:fp:@inputs/fp_dt1.in:none:300:DT1 FP (NRMAX=1 minimal)
```

- [ ] **Step 2: 3 ケースの初回 run でベースラインを生成**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
for case in fp_iter01 fp_jt60 fp_dt1; do
  rm -rf "test_output/$case"
  ./run_tests.sh "$case"
  ./scripts/check_regression.sh "$case" "test_output/$case" "baselines" "1e-10" --generate-baseline
done
ls -la baselines/fp_*/metrics.json
```
Expected: 3 ファイル生成（各々 NRMAX*NSAMAX 行分の profile + scalars が JSON 化されている）。

- [ ] **Step 3: 同じケースを再実行して PASS することを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh fp_iter01 fp_jt60 fp_dt1
```
Expected: 3 ケース全 `PASS`。

- [ ] **Step 4: run-to-run 再現性を 3 回連続で測定**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
for i in 1 2 3; do
  ./run_tests.sh fp_iter01 fp_jt60 fp_dt1 2>&1 | grep -E "PASS|FAIL|REGRESSION"
done
```
Expected: 全試行で 3/3 PASS。`REGRESSION` が出る場合、許容誤差を 1e-10 → 1e-8 に Task 12 で緩める。

- [ ] **Step 5: TR 既存 3 ケースが回帰しないことを最終確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tr_iter01 tr_m0904 tr_tst2
```
Expected: 全 PASS。

- [ ] **Step 6: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/test_definitions.conf test_run/baselines/fp_iter01/metrics.json \
        test_run/baselines/fp_jt60/metrics.json test_run/baselines/fp_dt1/metrics.json
git commit -m "test(fp): register fp_iter01/fp_jt60/fp_dt1 with baselines"
```

---

## Task 12: 許容誤差調整（必要時のみ）

**Files:**
- Modify: `test_run/run_tests.sh`（`1e-10` → `1e-8` のみ、L-0 で run-to-run の差が観測された場合）

- [ ] **Step 1: Task 11 Step 4 で 1 件でも REGRESSION が出たら**、`run_tests.sh` の `check_regression.sh` 呼出引数の `"1e-10"` を `"1e-8"` に書き換える（fp 専用に分けるなら `case "$module"` で 2 系統許容誤差に分岐）。

- [ ] **Step 2: 再度 5 回連続で再現性を確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
for i in 1 2 3 4 5; do
  ./run_tests.sh fp_iter01 fp_jt60 fp_dt1 | grep -E "PASS|FAIL|REGRESSION"
done
```
Expected: 全 5 回全 PASS。

- [ ] **Step 3: コミット（実施した場合のみ）**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/run_tests.sh
git commit -m "test(fp): relax FP regression tolerance to 1e-8"
```

---

## Task 13: `test_run/README.md` に FP 回帰の運用手順を追記

**Files:**
- Modify: `test_run/README.md`

- [ ] **Step 1: 既存 README を確認**

Run:
```bash
head -60 /home/k-yoshimi/program/task/test_run/README.md
```

- [ ] **Step 2: TR セクションと並列に FP セクションを追記**

`test_run/README.md` の TR 関連セクションの直後に以下のような節を追加:

```markdown
## FP regression dump

The fp module emits a high-precision dump `fp_regress.dat` (format `1PE24.16`)
into the test working directory **only** when the env var `FP_REGRESS_DUMP=1`
is set. Normal runs do nothing extra.

`run_tests.sh` exports `FP_REGRESS_DUMP=1` automatically for any test whose
module is `fp`, then invokes `scripts/check_regression.sh <test_name>` after
the binary returns 0. Comparison uses `scripts/extract_fp_metrics.py` +
`scripts/compare_metrics.py` against the JSON baseline at
`baselines/<test_name>/metrics.json`.

To regenerate baselines (e.g. after intended numerical changes):

    ./scripts/check_regression.sh fp_iter01 test_output/fp_iter01 baselines 1e-10 --generate-baseline

Default tolerance is `1e-10`; raise to `1e-8` if MPI nondeterminism shows up.
The dump is restricted to MPI rank 0 inside `fpregress.f90`.
```

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/README.md
git commit -m "docs(test_run): document FP regression dump workflow"
```

---

## 受け入れ基準（L-0 完了時）

- [ ] `fp/fpregress.f90` が追加され、`FP_REGRESS_DUMP=1` のときだけ `fp_regress.dat` を nrank==0 で書き出す。
- [ ] 通常 fp 実行（`unset FP_REGRESS_DUMP`）で `fp_regress.dat` が **作られない**。
- [ ] `test_run/test_definitions.conf` に `fp_iter01, fp_jt60, fp_dt1` の 3 ケースが登録されている。
- [ ] `test_run/baselines/fp_*/metrics.json` 3 ファイルがコミット済み。
- [ ] `./run_tests.sh fp_iter01 fp_jt60 fp_dt1` を 5 回連続で走らせて全 PASS。
- [ ] `./run_tests.sh tr_iter01 tr_m0904 tr_tst2` が引き続き全 PASS（TR 既存ベースライン非回帰）。
- [ ] `test_run/README.md` に FP 回帰運用が記載されている。

## 撤退条件 / フォールバック

| 状況 | 対応 |
|---|---|
| `RNT/RWT/RTT/...` 配列が想定 shape と異なる | dump フィールドを実形に合わせて削減（最低でも `TIMEFP, NTG2`, `RNT(NR,NSA,NTG2)` のみ）|
| MPI run-to-run で bit-exact 一致しない | `nsize == 1` 限定で dump、または許容誤差 `1e-8` まで緩める。それでも不安定なら `1e-6`。本 L-0 は **シングルプロセス前提** に限定する旨を README に明記 |
| `fp/in/fp.inITER` が外部 `fpdata.ITER` 等を要求して走らない | 問題のある `KNAMFP/KNAMWR` を空文字列にして再実行。それでもダメなら `fp_dt1` を主軸に 3 ケース確保（`fp_dt2/DT3` を追加）|
| `fp_jt60` ケースの確立が困難 | `fp_iter01_short`（NTMAX=1 / NRMAX=20 等）を 3 番目に追加して撤退 |
| L-0 の総工数が 2 週超 | `fp_jt60` を skip し、`fp_iter01 + fp_dt1` の 2 ケースで L-1 へ進む（最低 2 ケース） |

## 依存

- 上流 PR: なし（develop の `c559e06e` が起点。TR Phase 0 PR #2 (`926b25b4`) の成果物 = `compare_metrics.py`, `check_regression.sh`, `run_tests.sh` の TR 用ロジックが既にあること）
- 後続 PR: L-1（fp graphics 分離）はこの L-0 が green に揃ってから着手する。
