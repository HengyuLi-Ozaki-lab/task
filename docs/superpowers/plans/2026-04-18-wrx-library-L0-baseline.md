# WRX Library-ization Phase L-0: Regression Baseline + Test Infra 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `wrx/` モジュール（拡張版 wave ray-tracing solver）のライブラリ化に着手する前に、`test_run/` の既存回帰テスト基盤を WRX に拡張し、`tr/` で確立した dump-and-compare 方式（merge `926b25b4`）を `wrx/` にも適用、2〜3 ケースのゴールデンベースラインを `1e-10` 許容誤差で commit する。

**Architecture:** TR Phase 0 で導入された `trregress.f90` (env-guarded high-precision dump) と同じ pattern を `wrx/wrxregress.f90` として **新規 1 ファイル + `wrmenu.f90` のフック 1 行 + `Makefile` への 1 行追加** だけで実装する。`test_run/run_tests.sh` の TR 専用フック (`TR_REGRESS_DUMP=1` env) を WRX 用 (`WRX_REGRESS_DUMP=1`) に汎用化し、`scripts/check_regression.sh` を WRX に再利用可能な形にリファクタする（後方互換維持）。比較対象は ray 終端の `pwr_tot, pwr_nray(:), pwr_nsa(:), pos_pwrmax_rs_nsa(:)` および各 ray の終端 step 数 `NSTPMAX_NRAY(:)` などスカラー＋小配列。プロファイル `RAYS(:,:,:)` は要素数が大きいので Phase L-0 の比較対象には含めない（必要なら L-6 で追加）。

**Tech Stack:** Fortran 90 (`wrxregress.f90` 追加), Bash (既存 `run_tests.sh` を WRX 対応に拡張), Python 3 標準ライブラリのみ (`extract_wrx_metrics.py` 追加, `compare_metrics.py` 再利用), gfortran 既存 build chain, 既存 WRX バイナリ `wrx/wr` (Makefile target は `wr` という名前で wrx ディレクトリ内に置かれる).

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` をテンプレートとし、wrx 用に翻案。

**Module name collision (critical):** `wr/wrcomm.f90` と `wrx/wrcomm.f90` はどちらも `MODULE wrcomm_parm`、`MODULE wrcomm` を宣言する（同じ名前空間）。これは 2 つのバイナリ（`wr/wr` と `wrx/wr`）が独立にビルドされる前提の設計であり、各バイナリは自分のディレクトリ下の `mod/` を見るため衝突しない。**ただし将来 `libwrxapi.so` を作る際に**、Linker レベルで wr 由来と wrx 由来の `.mod` / シンボルが混入しないよう **wrx 専用の `mod/`, `obj/` ディレクトリ** で完結させる必要がある（既に `wrx/Makefile` は `OBJDIR=./obj`、`MODDIR=mod` 相当で分離されている）。L-0 では現状確認のみ。L-2 以降で `bind(c)` 公開シンボルに `wrx_` プレフィックスを必ず付ける（`wr_` ではなく）方針を確定する。

---

## File Structure

このフェーズで作成・変更するファイル:

| ファイル | 種別 | 責務 |
|---|---|---|
| `wrx/wrxregress.f90` | 新規 | 環境変数ガード付き高精度 dump（`1PE24.16` 書式）。WRX 終了時に `wrx_regress.dat` を CWD に書き出す |
| `wrx/wrmenu.f90` | 修正 | `R` キー（ray exec）後、`wr_exec` 完了直後に `wrx_regress_dump_if_enabled` を呼ぶ 1 行フック追加 |
| `wrx/Makefile` | 修正 | `SRCS` に `wrxregress.f90` を追加（`wrmenu.f90` より前に配置） |
| `test_run/inputs/wrx_iter01.in` | 新規 | ITER 用 ECCD ray-tracing シナリオ（既存 `wrx/in/wr.in` ベース、NRAYMAX=4） |
| `test_run/inputs/wrx_jt60.in` | 新規 | JT-60U 用 ECCD ray-tracing シナリオ（小型機テスト, NRAYMAX=2） |
| `test_run/inputs/wrx_demo.in` | 新規 | デバッグ向け最小 1-ray シナリオ（高速 smoke、NRAYMAX=1, NSTPMAX=2000） |
| `test_run/scripts/extract_wrx_metrics.py` | 新規 | `wrx_regress.dat` から数値指標を JSON に変換（既存 `extract_tr_metrics.py` と独立、構造が違う） |
| `test_run/scripts/check_regression.sh` | 修正 | TR 専用 → モジュール汎用化。`<module>` 引数を追加し dump ファイル名と extractor を切替 |
| `test_run/baselines/wrx_iter01/metrics.json` | 新規（生成） | ベースライン指標 |
| `test_run/baselines/wrx_jt60/metrics.json` | 新規（生成） | ベースライン指標 |
| `test_run/baselines/wrx_demo/metrics.json` | 新規（生成） | ベースライン指標 |
| `test_run/test_definitions.conf` | 修正 | `wrx_iter01`, `wrx_jt60`, `wrx_demo` 3 ケース追加 |
| `test_run/run_tests.sh` | 修正 | `wrx` モジュール binary 解決 (`wrx/wr`) と `WRX_REGRESS_DUMP=1` env、`check_regression.sh` 呼出時に `wrx` モジュール名を渡す |
| `test_run/README.md` | 修正 | WRX セクション追加、`WRX_REGRESS_DUMP` 機構の説明 |

**方針:**
- WRX 本体への追加は **`wrxregress.f90` 新規 1 ファイル + `wrmenu.f90` への 1 行フック + Makefile への 1 行** に限定。通常実行（環境変数未設定）では挙動完全不変。
- Python は標準ライブラリのみ。
- 比較ツール `compare_metrics.py` は TR と WRX で **共通利用可能な汎用 schema**（`scalars: dict, arrays: dict[str, list]` のみで構成）に WRX 側を合わせる。TR 側の既存 schema (`profile: list of dict`) はそのまま温存（後方互換）。
- ベースラインは `--generate-baseline` モードで初回書き出し、以降は比較のみ。

---

## Task 1: 作業用ブランチ確認とビルド可能性確認

**Files:**
- なし（環境準備）

- [ ] **Step 1: ブランチと git 状態を確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git status
git branch --show-current
```
Expected: `feature/wrx-library-L0-baseline`（このフェーズ用に切るブランチ）または `develop` ベース。uncommitted な変更なし。

- [ ] **Step 2: フェーズ用ブランチを切る**

Run:
```bash
git checkout -b feature/wrx-library-L0-baseline
```
Expected: ブランチ切替成功。

- [ ] **Step 3: コンパイラ最適化フラグ確認**

Run:
```bash
grep -n "^OFLAGS\|^DFLAGS\|^FFLAGS" /home/k-yoshimi/program/task-private/make.header | head -10
grep -n "^FFLAGS" /home/k-yoshimi/program/task-private/wrx/Makefile | head -5
```
Expected:
- `make.header` に `OFLAGS = -g -O3 -m64 -std=legacy` 相当の 1 行が有効。
- `wrx/Makefile` は `FFLAGS = $(OFLAGS)` を使用（`$(DFLAGS)` がアンコメントされていないこと）。

- [ ] **Step 4: 依存ライブラリと wrx をビルド**

Run:
```bash
cd /home/k-yoshimi/program/task-private/wrx && make 2>&1 | tail -10
ls -la wr  # binary は "wr" という名前で wrx/ に作られる
```
Expected: `wrx/wr` バイナリが存在。エラーなし。

- [ ] **Step 5: `wrx/in/wr.in` で対話的に動くことを smoke 確認（手動 1 回でよい）**

Run:
```bash
cd /home/k-yoshimi/program/task-private/wrx
timeout 60 ./wr < in/wr.in > /tmp/wrx_smoke.log 2>&1
tail -30 /tmp/wrx_smoke.log
echo "exit=$?"
```
Expected: ray-tracing が走り、`CLOSED` ログが含まれる、または GSCLOS 経由の終了。exit code 0 か 124（タイムアウト）。**注:** `wr.in` は対話 stdin の連続入力を想定しているので、本ステップは入力ファイルが完走するかの確認のみ。

- [ ] **Step 6: 空コミット（マーカー）**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git commit --allow-empty -m "chore(wrx): start Phase L-0 regression infra scaffolding"
```

---

## Task 2: 比較戦略の確定（決定済み事項の文書化）

**Files:**
- 調査のみ

**決定事項（本計画で確定済み）:**

WRX 本体に環境変数 `WRX_REGRESS_DUMP=1` ガード付きの高精度 dump モジュール `wrxregress.f90` を追加し、そこから得られる固定フォーマット `wrx_regress.dat` を比較対象とする。

- **dump 対象（スカラー）:**
  - `NRAYMAX, NSTPMAX, NSAMAX_WR, NSMAX, MODELG, MDLWRQ` (整数の構成パラメータ; 比較で形状不一致を即座に検知)
  - `pwr_tot` (実数; 全 ray 全 species の合計吸収パワー)
- **dump 対象（配列, 1 次元）:**
  - `NSTPMAX_NRAY(1:NRAYMAX)`: 各 ray 終端 step 数（整数）
  - `pwr_nray(1:NRAYMAX)`: ray ごとの吸収パワー (実数)
  - `pwr_nsa(1:NSAMAX_WR)`: species ごとの吸収パワー (実数)
- **dump 対象（配列, 2 次元 → 平坦化）:**
  - `pwr_nsa_nray(1:NSAMAX_WR, 1:NRAYMAX)`
  - `pos_pwrmax_rs_nsa(1:NSAMAX_WR)`, `pwrmax_rs_nsa(1:NSAMAX_WR)`
  - `pos_pwrmax_rl_nsa(1:NSAMAX_WR)`, `pwrmax_rl_nsa(1:NSAMAX_WR)` (LH absorbed-power peaks; the wrcomm declaration includes both `_rs` and `_rl` variants)
- **dump 対象外（L-0 では含めない、L-6 で必要なら追加）:**
  - `RAYS(0:NEQ, 0:NSTPMAX, NRAYMAX)` 全ステップ位置・運動量履歴（数百〜数万要素、L-0 では過剰）
  - `CEXS, CEYS, CEZS` 複素電場履歴（同上）
- **書式:** 整数は `I0`、実数は `1PE24.16`、配列は `# array <name> n=<len>` 行のあと 1 行 1 要素。
- **起動条件:** 環境変数 `WRX_REGRESS_DUMP=1` のときのみ `wrx_regress.dat` を CWD に書き出す。未設定時は何もしない。
- **許容誤差:** デフォルト `1e-10`。run-to-run 再現性確認後に必要なら `1e-8` まで緩める（ray-tracing は ODE 数値積分のため TR より丸め誤差が出やすい可能性あり）。
- **stdout ログの数値行:** 比較対象外（精度不足）。

- [ ] **Step 1: dump 対象量が wrcomm に存在することを確認**

Run:
```bash
grep -nE "pwr_tot|pwr_nray|pwr_nsa\b|pwr_nsa_nray|pos_pwrmax_r[sl]_nsa|pwrmax_r[sl]_nsa|NSTPMAX_NRAY" \
    /home/k-yoshimi/program/task-private/wrx/wrcomm.f90 | head -20
```
Expected: 上記すべての変数が `wrcomm` モジュール内で宣言されていること。
もし一部が無い場合は Task 3 Step 2 の dump リストから除外。

- [ ] **Step 2: モジュール名衝突 (`wrcomm`, `wrcomm_parm`) を確認**

Run:
```bash
grep -n "^MODULE " /home/k-yoshimi/program/task-private/wr/wrcomm.f90
grep -n "^MODULE " /home/k-yoshimi/program/task-private/wrx/wrcomm.f90
```
Expected: 両方とも `MODULE wrcomm_parm` と `MODULE wrcomm` を宣言（**完全衝突**）。
これにより、L-2 以降で `bind(c)` 関数名は必ず `wrx_` プレフィックスを付ける必要があると確認。

- [ ] **Step 3: 決定をメモ commit**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git commit --allow-empty -m "docs(wrx): lock comparison strategy (wrxregress dump, tol 1e-10)"
```

---

## Task 3: `wrx/wrxregress.f90` を新規作成し dump を実装

**Files:**
- Create: `wrx/wrxregress.f90`
- Modify: `wrx/wrmenu.f90`（USE 文 + フック 1 行）
- Modify: `wrx/Makefile`（`SRCS` に 1 ファイル追加）

**目的:** `WRX_REGRESS_DUMP=1` のときに限り、`wr_exec` 終了直後に主要グローバル量を `wrx_regress.dat` へ書き出す。通常実行では何もしない。

- [ ] **Step 1: `wrx/wrmenu.f90` の `wr_exec` 呼出位置を確認**

Run:
```bash
grep -n "CALL wr_exec\|USE wrexec" /home/k-yoshimi/program/task-private/wrx/wrmenu.f90
```
Expected: `CALL wr_exec(nstat,ierr)` が 1 箇所（KID='R' ブランチ内）に存在。

- [ ] **Step 2: `wrx/wrxregress.f90` を新規作成**

Create: `wrx/wrxregress.f90`

```fortran
! wrxregress.f90
!
! High-precision regression dump for WRX Phase L-0 regression tests.
! Emits wrx_regress.dat (1PE24.16 format) when WRX_REGRESS_DUMP=1.
! Otherwise does nothing; normal runs are unaffected.

MODULE wrxregress

  PRIVATE
  PUBLIC :: wrx_regress_dump_if_enabled

CONTAINS

  SUBROUTINE wrx_regress_dump_if_enabled
    USE wrcomm, ONLY: &
         NRAYMAX, NSTPMAX, NSAMAX_WR, NSMAX, MODELG, MDLWRQ, &
         pwr_tot, pwr_nray, pwr_nsa, pwr_nsa_nray, &
         pos_pwrmax_rs_nsa, pwrmax_rs_nsa, &
         pos_pwrmax_rl_nsa, pwrmax_rl_nsa, &
         NSTPMAX_NRAY, rkind
    IMPLICIT NONE
    INTEGER, PARAMETER :: UNIT_DUMP = 78
    CHARACTER(LEN=16) :: ENV_VAL
    INTEGER :: STAT, NRAY, NSA, IOERR
    LOGICAL :: ENABLED

    CALL GET_ENVIRONMENT_VARIABLE('WRX_REGRESS_DUMP', ENV_VAL, STATUS=STAT)
    ENABLED = (STAT == 0 .AND. TRIM(ENV_VAL) == '1')
    IF (.NOT. ENABLED) RETURN

    OPEN(UNIT=UNIT_DUMP, FILE='wrx_regress.dat', &
         STATUS='REPLACE', ACTION='WRITE', IOSTAT=IOERR)
    IF (IOERR /= 0) THEN
       WRITE(6,*) 'XX wrxregress: cannot open wrx_regress.dat, IOSTAT=', IOERR
       RETURN
    END IF

    WRITE(UNIT_DUMP,'(A)')         '# TASK/WRX regression dump (format v1)'
    WRITE(UNIT_DUMP,'(A,I0)')      'NRAYMAX=',  NRAYMAX
    WRITE(UNIT_DUMP,'(A,I0)')      'NSTPMAX=',  NSTPMAX
    WRITE(UNIT_DUMP,'(A,I0)')      'NSAMAX_WR=',NSAMAX_WR
    WRITE(UNIT_DUMP,'(A,I0)')      'NSMAX=',    NSMAX
    WRITE(UNIT_DUMP,'(A,I0)')      'MODELG=',   MODELG
    WRITE(UNIT_DUMP,'(A,I0)')      'MDLWRQ=',   MDLWRQ
    WRITE(UNIT_DUMP,'(A,1PE24.16)') 'pwr_tot=', pwr_tot

    WRITE(UNIT_DUMP,'(A,I0)') '# array NSTPMAX_NRAY n=', NRAYMAX
    DO NRAY = 1, NRAYMAX
       WRITE(UNIT_DUMP,'(I0)') NSTPMAX_NRAY(NRAY)
    END DO

    WRITE(UNIT_DUMP,'(A,I0)') '# array pwr_nray n=', NRAYMAX
    DO NRAY = 1, NRAYMAX
       WRITE(UNIT_DUMP,'(1PE24.16)') pwr_nray(NRAY)
    END DO

    WRITE(UNIT_DUMP,'(A,I0)') '# array pwr_nsa n=', NSAMAX_WR
    DO NSA = 1, NSAMAX_WR
       WRITE(UNIT_DUMP,'(1PE24.16)') pwr_nsa(NSA)
    END DO

    WRITE(UNIT_DUMP,'(A,I0,A,I0)') '# array2 pwr_nsa_nray rows=', NSAMAX_WR, ' cols=', NRAYMAX
    DO NSA = 1, NSAMAX_WR
       DO NRAY = 1, NRAYMAX
          WRITE(UNIT_DUMP,'(1PE24.16,1X)',ADVANCE='NO') pwr_nsa_nray(NSA,NRAY)
       END DO
       WRITE(UNIT_DUMP,'(A)') ''
    END DO

    WRITE(UNIT_DUMP,'(A,I0)') '# array pos_pwrmax_rs_nsa n=', NSAMAX_WR
    DO NSA = 1, NSAMAX_WR
       WRITE(UNIT_DUMP,'(1PE24.16)') pos_pwrmax_rs_nsa(NSA)
    END DO

    WRITE(UNIT_DUMP,'(A,I0)') '# array pwrmax_rs_nsa n=', NSAMAX_WR
    DO NSA = 1, NSAMAX_WR
       WRITE(UNIT_DUMP,'(1PE24.16)') pwrmax_rs_nsa(NSA)
    END DO

    WRITE(UNIT_DUMP,'(A,I0)') '# array pos_pwrmax_rl_nsa n=', NSAMAX_WR
    DO NSA = 1, NSAMAX_WR
       WRITE(UNIT_DUMP,'(1PE24.16)') pos_pwrmax_rl_nsa(NSA)
    END DO

    WRITE(UNIT_DUMP,'(A,I0)') '# array pwrmax_rl_nsa n=', NSAMAX_WR
    DO NSA = 1, NSAMAX_WR
       WRITE(UNIT_DUMP,'(1PE24.16)') pwrmax_rl_nsa(NSA)
    END DO

    CLOSE(UNIT_DUMP)
  END SUBROUTINE wrx_regress_dump_if_enabled

END MODULE wrxregress
```

注: Task 2 Step 1 で見つからない変数があれば `USE` 句および `WRITE` 行から削除。

- [ ] **Step 3: `wrx/Makefile` の SRCS に追加**

`wrx/Makefile` の `SRCS = ...` を以下のように修正（`wrmenu.f90` の前に挿入し、modulo 依存を満たす）:

変更前:
```
SRCS = wrcomm.f90 wrinit.f90 wrparm.f90 wrprep.f90 wrview.f90 \
       wrsub.f90 \
       wrsetup.f90 wrcalpwr.f90 wrfdrv.f90 wroxb.f90 \
       wrexecr.f90 wrexecb.f90 \
       wrexec.f90 \
       wrgout.f90 wrfile.f90 \
       wrmenu.f90
```
変更後:
```
SRCS = wrcomm.f90 wrinit.f90 wrparm.f90 wrprep.f90 wrview.f90 \
       wrsub.f90 \
       wrsetup.f90 wrcalpwr.f90 wrfdrv.f90 wroxb.f90 \
       wrexecr.f90 wrexecb.f90 \
       wrexec.f90 \
       wrgout.f90 wrfile.f90 \
       wrxregress.f90 \
       wrmenu.f90
```

そして Makefile 末尾の依存セクションに追加:
```
$(OBJDIR)/wrxregress.o: wrxregress.f90 $(WRCOMM)
$(OBJDIR)/wrmenu.o: wrxregress.f90
```

- [ ] **Step 4: `wrx/wrmenu.f90` を修正してフックを追加**

`wrx/wrmenu.f90` の USE 文群（`USE wrexec,ONLY: wr_exec` の直下）に追加:
```fortran
    USE wrxregress, ONLY: wrx_regress_dump_if_enabled
```

そして `KID.EQ.'R'` ブランチの `CALL wr_exec(nstat,ierr)` の直後に 1 行追加:
```fortran
      ELSEIF(KID.EQ.'R') THEN
         CALL wr_prep(ierr)
         IF(ierr.NE.0) GO TO 1
         CALL wr_allocate
         CALL wr_setup(ierr)
         IF(ierr.NE.0) GO TO 1
         CALL wr_exec(nstat,ierr)
         CALL wrx_regress_dump_if_enabled   ! Phase L-0 regression dump (env-guarded)
```

- [ ] **Step 5: WRX をリビルド**

Run:
```bash
cd /home/k-yoshimi/program/task-private/wrx
make 2>&1 | tail -15
```
Expected: `wrxregress.f90` のコンパイルが実行され、`wr` バイナリが更新される。エラーなし。

- [ ] **Step 6: 通常実行で dump が作られないことを確認（副作用ゼロ）**

Run:
```bash
cd /tmp && mkdir -p wrx_test && cd wrx_test
rm -f wrx_regress.dat
unset WRX_REGRESS_DUMP
timeout 60 /home/k-yoshimi/program/task-private/wrx/wr \
    < /home/k-yoshimi/program/task-private/wrx/in/wr.in > out.log 2>&1
ls -la wrx_regress.dat 2>&1 | head -3
```
Expected: `wrx_regress.dat` は作られない (`No such file or directory`)。

- [ ] **Step 7: 環境変数を立てると dump が出ることを確認**

Run:
```bash
cd /tmp/wrx_test
WRX_REGRESS_DUMP=1 timeout 60 /home/k-yoshimi/program/task-private/wrx/wr \
    < /home/k-yoshimi/program/task-private/wrx/in/wr.in > out.log 2>&1
ls -la wrx_regress.dat
head -25 wrx_regress.dat
```
Expected:
- `wrx_regress.dat` が存在。
- 1 行目: `# TASK/WRX regression dump (format v1)`。
- スカラー、`# array ... n=N` ヘッダ、データ行が並ぶ。

- [ ] **Step 8: 同一入力 2 回で dump が bit-exact に一致**

Run:
```bash
cd /tmp/wrx_test
WRX_REGRESS_DUMP=1 timeout 60 /home/k-yoshimi/program/task-private/wrx/wr \
    < /home/k-yoshimi/program/task-private/wrx/in/wr.in > /dev/null 2>&1
cp wrx_regress.dat /tmp/wrx_dump_run1.dat
WRX_REGRESS_DUMP=1 timeout 60 /home/k-yoshimi/program/task-private/wrx/wr \
    < /home/k-yoshimi/program/task-private/wrx/in/wr.in > /dev/null 2>&1
diff /tmp/wrx_dump_run1.dat wrx_regress.dat
echo "diff exit=$?"
```
Expected: `diff` 出力空、`exit=0`。差異あれば許容誤差を Task 8 で `1e-8` に緩める。

- [ ] **Step 9: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git add wrx/wrxregress.f90 wrx/wrmenu.f90 wrx/Makefile
git commit -m "feat(wrx): add env-guarded high-precision dump for regression tests"
```

---

## Task 4: 指標抽出スクリプト `extract_wrx_metrics.py` を書く

**Files:**
- Create: `test_run/scripts/extract_wrx_metrics.py`
- Create: `test_run/scripts/tests/test_extract_wrx_metrics.py`
- Create: `test_run/scripts/tests/fixtures/sample_wrx_regress.dat`

- [ ] **Step 1: サンプル fixture を作成**

Create: `test_run/scripts/tests/fixtures/sample_wrx_regress.dat`

```
# TASK/WRX regression dump (format v1)
NRAYMAX=2
NSTPMAX=10
NSAMAX_WR=2
NSMAX=2
MODELG=2
MDLWRQ=1
pwr_tot=1.0000000000000000E+00
# array NSTPMAX_NRAY n=2
8
9
# array pwr_nray n=2
6.0000000000000000E-01
4.0000000000000000E-01
# array pwr_nsa n=2
7.0000000000000000E-01
3.0000000000000000E-01
# array2 pwr_nsa_nray rows=2 cols=2
3.0000000000000000E-01 4.0000000000000000E-01 
2.0000000000000000E-01 1.0000000000000000E-01 
# array pos_pwrmax_rs_nsa n=2
5.0000000000000000E-01
6.0000000000000000E-01
# array pwrmax_rs_nsa n=2
1.5000000000000000E-01
1.2000000000000000E-01
# array pos_pwrmax_rl_nsa n=2
5.5000000000000000E-01
6.5000000000000000E-01
# array pwrmax_rl_nsa n=2
1.6000000000000000E-01
1.3000000000000000E-01
```

- [ ] **Step 2: 失敗するテストを書く**

Create: `test_run/scripts/tests/test_extract_wrx_metrics.py`

```python
import json, subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "extract_wrx_metrics.py"
FIX = Path(__file__).parent / "fixtures" / "sample_wrx_regress.dat"

class TestExtract(unittest.TestCase):
    def test_basic(self):
        r = subprocess.run([sys.executable, str(SCRIPT), str(FIX)],
                           capture_output=True, text=True, check=True)
        d = json.loads(r.stdout)
        self.assertEqual(d["NRAYMAX"], 2)
        self.assertEqual(d["NSAMAX_WR"], 2)
        self.assertAlmostEqual(d["scalars"]["pwr_tot"], 1.0)
        self.assertEqual(d["arrays"]["NSTPMAX_NRAY"], [8, 9])
        self.assertEqual(len(d["arrays"]["pwr_nray"]), 2)
        self.assertAlmostEqual(d["arrays"]["pwr_nray"][0], 0.6)
        self.assertEqual(d["arrays2"]["pwr_nsa_nray"], [[0.3, 0.4], [0.2, 0.1]])

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: テストが失敗することを確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private
python3 -m unittest test_run.scripts.tests.test_extract_wrx_metrics -v
```
Expected: FAIL（`extract_wrx_metrics.py` が無い）。

- [ ] **Step 4: `extract_wrx_metrics.py` を実装**

Create: `test_run/scripts/extract_wrx_metrics.py`

```python
#!/usr/bin/env python3
"""Extract metrics from wrx_regress.dat (Phase L-0 dump format v1).

Output schema:
  {
    "NRAYMAX": int, "NSTPMAX": int, "NSAMAX_WR": int, "NSMAX": int,
    "MODELG": int, "MDLWRQ": int,
    "scalars": {"pwr_tot": float, ...},
    "arrays":  {"NSTPMAX_NRAY": [int...], "pwr_nray": [float...], ...},
    "arrays2": {"pwr_nsa_nray": [[float...], ...], ...}
  }
"""
import json
import re
import sys
from pathlib import Path

INT_KEYS = {"NRAYMAX", "NSTPMAX", "NSAMAX_WR", "NSMAX", "MODELG", "MDLWRQ"}
FLOAT_SCALARS = {"pwr_tot"}
INT_ARRAYS = {"NSTPMAX_NRAY"}


def parse(path: Path) -> dict:
    out = {"scalars": {}, "arrays": {}, "arrays2": {}}
    lines = path.read_text().splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln or ln.startswith("# TASK"):
            i += 1
            continue
        m = re.match(r"# array2\s+(\w+)\s+rows=(\d+)\s+cols=(\d+)", ln)
        if m:
            name, rows, cols = m.group(1), int(m.group(2)), int(m.group(3))
            i += 1
            mat = []
            for _ in range(rows):
                row = [float(x) for x in lines[i].split()]
                if len(row) != cols:
                    raise ValueError(f"array2 {name}: expected {cols} cols, got {len(row)}")
                mat.append(row)
                i += 1
            out["arrays2"][name] = mat
            continue
        m = re.match(r"# array\s+(\w+)\s+n=(\d+)", ln)
        if m:
            name, n = m.group(1), int(m.group(2))
            i += 1
            vals = []
            for _ in range(n):
                v = lines[i].strip()
                vals.append(int(v) if name in INT_ARRAYS else float(v))
                i += 1
            out["arrays"][name] = vals
            continue
        if "=" in ln and not ln.startswith("#"):
            k, v = ln.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k in INT_KEYS:
                out[k] = int(v)
            elif k in FLOAT_SCALARS:
                out["scalars"][k] = float(v)
            else:
                # forward-compat: unknown scalar
                try:
                    out["scalars"][k] = float(v)
                except ValueError:
                    pass
            i += 1
            continue
        i += 1
    return out


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: extract_wrx_metrics.py <wrx_regress.dat>", file=sys.stderr)
        return 2
    print(json.dumps(parse(Path(sys.argv[1])), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: テストを再実行して PASS を確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private
python3 -m unittest test_run.scripts.tests.test_extract_wrx_metrics -v
```
Expected: OK (1 test passed).

- [ ] **Step 6: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git add test_run/scripts/extract_wrx_metrics.py \
        test_run/scripts/tests/test_extract_wrx_metrics.py \
        test_run/scripts/tests/fixtures/sample_wrx_regress.dat
git commit -m "feat(test_run): add wrx metrics extractor with unit tests"
```

---

## Task 5: `compare_metrics.py` を WRX schema に拡張（後方互換）

**Files:**
- Modify: `test_run/scripts/compare_metrics.py`
- Create: `test_run/scripts/tests/test_compare_metrics_wrx.py`

**目的:** 既存 TR schema (`scalars`, `profile`) に加えて WRX schema (`scalars`, `arrays`, `arrays2`) も扱える `--schema {tr,wrx}` 切替を追加（または auto 判定）。デフォルトは TR (後方互換)。

- [ ] **Step 1: 失敗するテストを書く**

Create: `test_run/scripts/tests/test_compare_metrics_wrx.py`

```python
import json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "compare_metrics.py"

WRX_BASE = {
    "NRAYMAX": 2, "NSAMAX_WR": 2,
    "scalars": {"pwr_tot": 1.0},
    "arrays":  {"NSTPMAX_NRAY": [8, 9], "pwr_nray": [0.6, 0.4]},
    "arrays2": {"pwr_nsa_nray": [[0.3, 0.4], [0.2, 0.1]]}
}

class TestCompareWrx(unittest.TestCase):
    def _run(self, baseline, actual, tol="1e-10"):
        with tempfile.TemporaryDirectory() as d:
            bp, ap = Path(d)/"b.json", Path(d)/"a.json"
            bp.write_text(json.dumps(baseline))
            ap.write_text(json.dumps(actual))
            return subprocess.run(
                [sys.executable, str(SCRIPT),
                 "--baseline", str(bp), "--actual", str(ap),
                 "--tolerance", tol, "--schema", "wrx"],
                capture_output=True, text=True)

    def test_match(self):
        r = self._run(WRX_BASE, WRX_BASE)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_pwr_tot_drift(self):
        actual = json.loads(json.dumps(WRX_BASE))
        actual["scalars"]["pwr_tot"] = 1.0 + 1e-5
        r = self._run(WRX_BASE, actual)
        self.assertNotEqual(r.returncode, 0)

    def test_array2_mismatch(self):
        actual = json.loads(json.dumps(WRX_BASE))
        actual["arrays2"]["pwr_nsa_nray"][0][1] = 0.4 + 1e-5
        r = self._run(WRX_BASE, actual)
        self.assertNotEqual(r.returncode, 0)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: テストが失敗することを確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private
python3 -m unittest test_run.scripts.tests.test_compare_metrics_wrx -v
```
Expected: FAIL（`--schema` が未対応）。

- [ ] **Step 3: `compare_metrics.py` に `--schema` を追加**

Edit: `test_run/scripts/compare_metrics.py`

argparse 部分（`ap.add_argument("--tolerance", ...)` の直後）に追加:
```python
    ap.add_argument("--schema", choices=("tr", "wrx"), default="tr",
                    help="Metrics schema (default: tr for back-compat).")
```

`compare()` 関数の手前に新規関数を追加:
```python
def compare_wrx(baseline: dict, actual: dict, tol: float) -> list:
    errors = []
    for k in ("NRAYMAX", "NSAMAX_WR", "NSMAX", "NSTPMAX", "MODELG", "MDLWRQ"):
        if k in baseline and baseline.get(k) != actual.get(k):
            errors.append(f"{k}: baseline={baseline.get(k)} actual={actual.get(k)}")
    if errors:
        return errors
    bs = baseline.get("scalars", {}); a_s = actual.get("scalars", {})
    for k in sorted(set(bs) | set(a_s)):
        if k not in bs or k not in a_s:
            errors.append(f"scalars.{k}: missing"); continue
        _check_scalar(f"scalars.{k}", float(bs[k]), float(a_s[k]), tol, errors)
    ba = baseline.get("arrays", {}); aa = actual.get("arrays", {})
    for k in sorted(set(ba) | set(aa)):
        if k not in ba or k not in aa:
            errors.append(f"arrays.{k}: missing"); continue
        bv, av = ba[k], aa[k]
        if len(bv) != len(av):
            errors.append(f"arrays.{k}: length {len(bv)} vs {len(av)}"); continue
        for i,(b,a) in enumerate(zip(bv,av)):
            if isinstance(b, int) and isinstance(a, int):
                if b != a:
                    errors.append(f"arrays.{k}[{i}]: baseline={b} actual={a}")
            else:
                _check_scalar(f"arrays.{k}[{i}]", float(b), float(a), tol, errors)
    b2 = baseline.get("arrays2", {}); a2 = actual.get("arrays2", {})
    for k in sorted(set(b2) | set(a2)):
        if k not in b2 or k not in a2:
            errors.append(f"arrays2.{k}: missing"); continue
        bm, am = b2[k], a2[k]
        if len(bm) != len(am):
            errors.append(f"arrays2.{k}: rows {len(bm)} vs {len(am)}"); continue
        for i,(br,ar) in enumerate(zip(bm,am)):
            if len(br) != len(ar):
                errors.append(f"arrays2.{k}[{i}]: cols {len(br)} vs {len(ar)}"); continue
            for j,(b,a) in enumerate(zip(br,ar)):
                _check_scalar(f"arrays2.{k}[{i}][{j}]", float(b), float(a), tol, errors)
    return errors
```

`main()` 内で `compare()` を呼んでいる行を以下に置換:
```python
    if args.schema == "wrx":
        errs = compare_wrx(baseline, actual, args.tolerance)
    else:
        errs = compare(baseline, actual, args.tolerance)
```

- [ ] **Step 4: WRX テスト + 既存 TR テスト両方とも PASS することを確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private
python3 -m unittest test_run.scripts.tests.test_compare_metrics_wrx -v
python3 -m unittest discover -s test_run/scripts/tests -p 'test_compare_metrics*.py' -v
```
Expected: 両方とも OK。

- [ ] **Step 5: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git add test_run/scripts/compare_metrics.py \
        test_run/scripts/tests/test_compare_metrics_wrx.py
git commit -m "feat(test_run): extend compare_metrics with wrx schema (back-compat)"
```

---

## Task 6: `check_regression.sh` をモジュール汎用化

**Files:**
- Modify: `test_run/scripts/check_regression.sh`

**目的:** TR 専用 (`tr_regress.dat`, `extract_tr_metrics.py`) から `--module {tr,wrx}` 切替に変更。デフォルト `tr` で後方互換維持。

- [ ] **Step 1: 修正**

Edit: `test_run/scripts/check_regression.sh`

ファイル冒頭付近のヘッダコメントの直後の引数解析 (`TEST_NAME=...` 等) を以下に置換:
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_NAME="${1:?usage: $0 <test_name> <output_dir> <baselines_dir> [tol] [mode] [module]}"
OUTPUT_DIR="${2:?}"
BASELINES_DIR="${3:?}"
TOL="${4:-1e-10}"
MODE="${5:-compare}"
MODULE="${6:-tr}"

case "$MODULE" in
    tr)
        DUMP_NAME="tr_regress.dat"
        EXTRACT="extract_tr_metrics.py"
        SCHEMA="tr"
        ;;
    wrx)
        DUMP_NAME="wrx_regress.dat"
        EXTRACT="extract_wrx_metrics.py"
        SCHEMA="wrx"
        ;;
    *)
        echo "check_regression: unknown module: $MODULE" >&2
        exit 4
        ;;
esac

DUMP="$OUTPUT_DIR/$DUMP_NAME"
METRICS_ACTUAL="$OUTPUT_DIR/metrics.json"
METRICS_BASE="$BASELINES_DIR/$TEST_NAME/metrics.json"
```

そして `python3 ... compare_metrics.py` 呼出に `--schema "$SCHEMA"` を追加:
```bash
python3 "$SCRIPT_DIR/compare_metrics.py" \
    --baseline "$METRICS_BASE" \
    --actual "$METRICS_ACTUAL" \
    --tolerance "$TOL" \
    --schema "$SCHEMA"
```

extractor 呼出も $EXTRACT 変数を使う:
```bash
if ! python3 "$SCRIPT_DIR/$EXTRACT" "$DUMP" > "$METRICS_ACTUAL"; then
```

- [ ] **Step 2: TR は引数なしで動く（後方互換）ことを確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private/test_run
./run_tests.sh tr_iter01
```
Expected: PASS（TR 既存 baseline と一致）。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git add test_run/scripts/check_regression.sh
git commit -m "refactor(test_run): generalize check_regression.sh to take module arg"
```

---

## Task 7: `run_tests.sh` に WRX サポートを追加

**Files:**
- Modify: `test_run/run_tests.sh`

- [ ] **Step 1: `get_binary()` に wrx を追加**

Edit: `test_run/run_tests.sh`

`get_binary()` の `case` 文に追加:
```bash
        wrx) echo "$TASK_DIR/wrx/wr" ;;
```
（注: wrx の binary は wrx ディレクトリ内に `wr` という名前で生成される）

- [ ] **Step 2: WRX 用 env と regression hook を追加**

`run_single_test()` 内、TR の env 設定箇所:
```bash
    local tr_env=()
    if [[ "$module" == "tr" ]]; then
        tr_env=(env TR_REGRESS_DUMP=1)
    fi
```
を以下に置換:
```bash
    local mod_env=()
    case "$module" in
        tr)  mod_env=(env TR_REGRESS_DUMP=1) ;;
        wrx) mod_env=(env WRX_REGRESS_DUMP=1) ;;
    esac
```
そして `${tr_env[@]}` の使用箇所 2 箇所を `${mod_env[@]}` に置換。

regression check の if 文も拡張:
```bash
        local reg_ok=1
        case "$module" in
            tr)
                if ! "$SCRIPT_DIR/scripts/check_regression.sh" \
                        "$test_name" "$test_dir" "$SCRIPT_DIR/baselines" "1e-10" \
                        compare tr \
                        > "$test_dir/regression.log" 2>&1; then
                    reg_ok=0
                fi
                ;;
            wrx)
                if ! "$SCRIPT_DIR/scripts/check_regression.sh" \
                        "$test_name" "$test_dir" "$SCRIPT_DIR/baselines" "1e-10" \
                        compare wrx \
                        > "$test_dir/regression.log" 2>&1; then
                    reg_ok=0
                fi
                ;;
        esac
```

- [ ] **Step 3: TR 既存テストが引き続き動くことを確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private/test_run
./run_tests.sh tr_iter01
```
Expected: PASS（regression check も PASS）。

- [ ] **Step 4: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git add test_run/run_tests.sh
git commit -m "feat(test_run): add wrx module support to run_tests.sh"
```

---

## Task 8: WRX 入力ファイル 3 ケースを作成

**Files:**
- Create: `test_run/inputs/wrx_iter01.in`
- Create: `test_run/inputs/wrx_jt60.in`
- Create: `test_run/inputs/wrx_demo.in`

**目的:** ベースライン用に 3 ケース（重め/中/最小）を用意。すべて modelg=2（解析モデル、EQ 非依存）または modelg=3 で eqdsk 不要にする。

- [ ] **Step 1: `wrx_iter01.in` 作成（既存 wr.in を参考に NRAYMAX=4 で短縮）**

Create: `test_run/inputs/wrx_iter01.in`

内容（`wrx/in/wr.in` をベースに NSTPMAX を抑える）:
```
0
f
wrx_iter01.gs
c
p
&wr
BB=5.3
RA=2.0
RR=6.2
RB=2.2
NSMAX=2
MODELG=2
MODELN=0
MODELP=206,206
MODELV=3,0
MDLWRQ=1
MODELQ=0
Q0=1.0
QA=3.5
PROFJ=1
PROFN1=2
PROFN2=1
PROFT1=2
PROFT2=1
PN=1.0,1.0
PNS=0.05,0.05
PTPR=10.0,10.0
PTPP=10.0,10.0
PTS=0.5,0.5
PA=2.0,5.4462e-4
PZ=1.0,-1.0
NCMIN(1)=-3, NCMIN(2)=-3
NCMAX(1)=3,  NCMAX(2)=3
MDLWRI=2
MDLWRW=0
MDLWRG=1
MDLWRP=1
pne_threshold=1.D-6
DELS=1e-3
SMAX=2.0
NSTPMAX=2000
NRAYMAX=4
RFIN(1)=4*170.D3
RPIN(1)=4*8.0D0
ZPIN(1)=4*0.0D0
PHIIN(1)=4*0.0D0
ANGPIN(1)=0.D0,5.D0,10.D0,15.D0
ANGTIN(1)=10.D0,20.D0,30.D0,40.D0
UUIN(1)=4*1.D0
MODEWIN(1)=4*1
KNAMWR='wrx_iter01.data'
/
v
r
g
1
x
s
q
```
**注:** Step 5 の smoke で完走できないなら NSTPMAX や SMAX を半分にする。

- [ ] **Step 2: `wrx_jt60.in` 作成**

Create: `test_run/inputs/wrx_jt60.in`

内容（JT-60U 想定、NRAYMAX=2）:
```
0
f
wrx_jt60.gs
c
p
&wr
BB=3.5
RA=1.0
RR=3.4
RB=1.1
NSMAX=2
MODELG=2
MODELN=0
MODELP=206,206
MODELV=3,0
MDLWRQ=1
MODELQ=0
Q0=1.2
QA=4.0
PROFJ=1
PROFN1=2
PROFN2=1
PROFT1=2
PROFT2=1
PN=0.5,0.5
PNS=0.025,0.025
PTPR=5.0,5.0
PTPP=5.0,5.0
PTS=0.3,0.3
PA=2.0,5.4462e-4
PZ=1.0,-1.0
NCMIN(1)=-3, NCMIN(2)=-3
NCMAX(1)=3,  NCMAX(2)=3
MDLWRI=2
MDLWRW=0
MDLWRG=1
MDLWRP=1
pne_threshold=1.D-6
DELS=1e-3
SMAX=1.5
NSTPMAX=1500
NRAYMAX=2
RFIN(1)=2*110.D3
RPIN(1)=2*4.5D0
ZPIN(1)=2*0.0D0
PHIIN(1)=2*0.0D0
ANGPIN(1)=0.D0,10.D0
ANGTIN(1)=15.D0,25.D0
UUIN(1)=2*1.D0
MODEWIN(1)=2*1
KNAMWR='wrx_jt60.data'
/
v
r
g
1
x
s
q
```

- [ ] **Step 3: `wrx_demo.in` 作成（最小 1-ray smoke）**

Create: `test_run/inputs/wrx_demo.in`

内容（既存 `wrx/in/wr.in` の TST-2 ベースを 1 ray に絞る）:
```
0
f
wrx_demo.gs
c
p
&wr
BB=0.308
RA=0.3
RR=0.52
RB=0.35
NSMAX=2
MODELG=2
MODELN=0
MODELP=206,206
MODELV=3,0
MDLWRQ=2
MODELQ=0
Q0=1.D4
QA=1.D4
PROFJ=1
PROFN1=2
PROFN2=1
PROFT1=8
PROFT2=1
PN=0.0194,0.0006
PNS=0.000194,0.000006
PTPR=0.03,60
PTPP=0.03,60
PTS=0.01,1
PA=5.4462e-4,5.4462e-4
PZ=-1.0,-1.0
NCMIN(1)=-2, NCMIN(2)=-2
NCMAX(1)=2,  NCMAX(2)=2
MDLWRI=2
MDLWRW=0
MDLWRG=1
MDLWRP=1
pne_threshold=1.D-6
DELS=1e-4
SMAX=1.0
NSTPMAX=2000
NRAYMAX=1
RFIN(1)=28.D3
RPIN(1)=0.85D0
ZPIN(1)=0.0D0
PHIIN(1)=0.0D0
ANGPIN(1)=0.D0
ANGTIN(1)=10.D0
UUIN(1)=1.D0
MODEWIN(1)=1
KNAMWR='wrx_demo.data'
/
v
r
g
1
x
s
q
```

- [ ] **Step 4: 各入力で smoke 確認（1 ケースずつ手で）**

Run:
```bash
cd /tmp && rm -rf wrx_smoke && mkdir wrx_smoke && cd wrx_smoke
for case in wrx_iter01 wrx_jt60 wrx_demo; do
    rm -f wrx_regress.dat out.log
    WRX_REGRESS_DUMP=1 timeout 120 /home/k-yoshimi/program/task-private/wrx/wr \
        < /home/k-yoshimi/program/task-private/test_run/inputs/${case}.in > out.log 2>&1
    echo "=== $case exit=$? has_dump=$(test -f wrx_regress.dat && echo yes || echo no) ==="
    grep -c 'CLOSED' out.log
done
```
Expected: 各ケース exit 0、`wrx_regress.dat` が生成、`CLOSED` が log に出る。
失敗するケースがあれば Task 8 内で `NSTPMAX` や `SMAX` を調整。

- [ ] **Step 5: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git add test_run/inputs/wrx_iter01.in test_run/inputs/wrx_jt60.in test_run/inputs/wrx_demo.in
git commit -m "test(wrx): add 3 regression input cases (iter01, jt60, demo)"
```

---

## Task 9: `test_definitions.conf` に WRX ケース追加

**Files:**
- Modify: `test_run/test_definitions.conf`

- [ ] **Step 1: WRX 3 ケースを追加**

Edit: `test_run/test_definitions.conf`

ファイル末尾に追加:
```
# =============================================================================
# WRX Module Tests (Extended wave ray-tracing solver, parallel to wr/)
# Uses local test inputs with shortened ray length
# =============================================================================
wrx_iter01:wrx:@inputs/wrx_iter01.in:none:120:WRX ITER ECCD ray-tracing (analytic eq)
wrx_jt60:wrx:@inputs/wrx_jt60.in:none:120:WRX JT-60U ECCD ray-tracing (analytic eq)
wrx_demo:wrx:@inputs/wrx_demo.in:none:60:WRX TST-2 minimal 1-ray smoke
```

- [ ] **Step 2: list で見えることを確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private/test_run
./run_tests.sh -l | grep wrx
```
Expected: 3 行表示される。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git add test_run/test_definitions.conf
git commit -m "test(wrx): register 3 wrx regression cases in test_definitions.conf"
```

---

## Task 10: ベースライン生成と commit

**Files:**
- Create: `test_run/baselines/wrx_iter01/metrics.json`
- Create: `test_run/baselines/wrx_jt60/metrics.json`
- Create: `test_run/baselines/wrx_demo/metrics.json`

- [ ] **Step 1: 3 ケースを WRX_REGRESS_DUMP=1 付きで実行し dump を取得**

Run:
```bash
cd /home/k-yoshimi/program/task-private/test_run
rm -rf test_output/wrx_*
./run_tests.sh wrx_iter01 wrx_jt60 wrx_demo
```
Expected: 3 ケースとも dump が生成される（baseline がまだ無いため REGRESSION 失敗だが、`tr_regress.dat` 同様 `wrx_regress.dat` は出来る）。

- [ ] **Step 2: 各ケースで baseline を生成**

Run:
```bash
cd /home/k-yoshimi/program/task-private/test_run
for case in wrx_iter01 wrx_jt60 wrx_demo; do
    scripts/check_regression.sh "$case" "test_output/$case" "baselines" "1e-10" \
        --generate-baseline wrx
done
ls -la baselines/wrx_*/metrics.json
```
Expected: 3 つの `metrics.json` が `baselines/wrx_*/` に作られる。

- [ ] **Step 3: 再実行で PASS することを確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private/test_run
rm -rf test_output/wrx_*
./run_tests.sh wrx_iter01 wrx_jt60 wrx_demo
```
Expected: 3 ケースとも `PASS`。

- [ ] **Step 4: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git add test_run/baselines/wrx_iter01 test_run/baselines/wrx_jt60 test_run/baselines/wrx_demo
git commit -m "test(wrx): commit initial regression baselines (iter01, jt60, demo)"
```

---

## Task 11: README 更新

**Files:**
- Modify: `test_run/README.md`

- [ ] **Step 1: WRX セクション追加**

Edit: `test_run/README.md`

TR セクションの直後に追加（既存 TR の説明をテンプレートに使う）:
```markdown
## WRX module regression workflow

WRX (extended wave ray-tracing solver) uses the same dump-and-compare design as TR.

When `run_tests.sh` runs a WRX test, it sets `WRX_REGRESS_DUMP=1` so that
`wrx/wrxregress.f90` writes `wrx_regress.dat` (1PE24.16 format) at end of
`wr_exec`. After successful completion (CLOSED log), the metrics are extracted
by `scripts/extract_wrx_metrics.py` and compared against the baseline JSON in
`baselines/<test_name>/metrics.json` with relative tolerance `1e-10`.

WRX baselines compare:
- scalars: `pwr_tot`
- 1D arrays: `NSTPMAX_NRAY`, `pwr_nray`, `pwr_nsa`,
  `pos_pwrmax_rs_nsa`, `pwrmax_rs_nsa`,
  `pos_pwrmax_rl_nsa`, `pwrmax_rl_nsa`
- 2D arrays: `pwr_nsa_nray`

Full step-by-step ray history (`RAYS`, `CEXS`, etc.) is intentionally excluded
from L-0 to keep dump size small; can be added in L-6 if regression resolution
is insufficient.

To regenerate WRX baselines:
```bash
./run_tests.sh wrx_iter01 wrx_jt60 wrx_demo  # produces wrx_regress.dat
for c in wrx_iter01 wrx_jt60 wrx_demo; do
    scripts/check_regression.sh "$c" "test_output/$c" "baselines" "1e-10" \
        --generate-baseline wrx
done
```
```

- [ ] **Step 2: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git add test_run/README.md
git commit -m "docs(test_run): document wrx regression workflow"
```

---

## Task 12: 全体回帰テストを通す（merge ready check）

**Files:**
- なし

- [ ] **Step 1: 全テスト実行**

Run:
```bash
cd /home/k-yoshimi/program/task-private/test_run
rm -rf test_output
./run_tests.sh
```
Expected: TR 3 ケース + WRX 3 ケース + EQ + TX 全部 PASS（or SKIP if module not built）。

- [ ] **Step 2: 出力に Inf/NaN 警告が無いことを確認**

Run:
```bash
grep -E "Inf|NaN" test_output/wrx_*/regression.log 2>/dev/null
```
Expected: マッチなし。

- [ ] **Step 3: PR への準備（push 等は本フェーズの担当外）**

---

## Verification Checklist (Phase L-0 完了基準)

- [ ] `wrx/wrxregress.f90` が新規追加されている（環境変数ガードあり）
- [ ] `WRX_REGRESS_DUMP` 未設定時は `wrx_regress.dat` が作られない（副作用ゼロ）
- [ ] `WRX_REGRESS_DUMP=1` で `wrx_regress.dat` が `1PE24.16` 形式で作られる
- [ ] 同一入力 2 回で dump が bit-exact 一致
- [ ] `extract_wrx_metrics.py` 単体テスト PASS
- [ ] `compare_metrics.py --schema wrx` の単体テスト PASS
- [ ] `check_regression.sh` の TR モード（後方互換）が引き続き PASS
- [ ] 3 つの WRX 入力ケース（iter01, jt60, demo）が完走する
- [ ] 3 つの WRX baseline が `test_run/baselines/wrx_*/metrics.json` に存在
- [ ] `./run_tests.sh wrx_iter01 wrx_jt60 wrx_demo` が PASS
- [ ] `./run_tests.sh`（全ケース）が TR + WRX 両方とも PASS
- [ ] `test_run/README.md` に WRX セクションあり

---

## Dependencies

- `develop` ブランチ HEAD（base）
- TR Phase 0 (merge `926b25b4`) で導入された `test_run/` 基盤
- `wrx/` ディレクトリの既存ビルドが PASS すること（依存ライブラリ含む）

## Fallback / Risk Mitigation

| リスク | 緩和策 |
|---|---|
| run-to-run で dump が一致しない（ODE 数値積分のため） | Task 8 で許容誤差を `1e-8` に緩める。原因が ODE solver の非決定性なら fixed seed の議論を L-6 で再考 |
| `wrx/in/wr.in` ベース入力で完走しないシナリオがある | Task 8 Step 4 で `NSTPMAX` `SMAX` を半減。最小 `wrx_demo` だけは必ず動かす |
| 既存 `wrcomm` モジュール衝突で `wrx/wr` build に影響 | wrx は独自 `mod/` `obj/` ディレクトリ管理のため発生しない（Task 1 Step 4 で確認） |
| `wrxregress` USE 句で参照する変数の一部が wrcomm に存在しない | Task 2 Step 1 の grep で検出し、Task 3 Step 2 の dump リストから除外 |
| TR の既存 baseline が崩れる | Task 5/6/7 で `--schema tr`（デフォルト）が後方互換であることを CI 経由で常時確認 |

## Out of Scope (Phase L-0 では扱わない)

- C ABI / shared library (`libwrxapi.so`) の作成（L-2, L-4）
- Python ラッパ作成（L-5）
- `RAYS`, `CEXS` 等のフルプロファイル比較（必要なら L-6 で追加）
- Graphics (`wrgout.f90`) 分離（L-1）
- パラメータ registry（L-3）
