# TOT Library Phase L-0: 統合系回帰テスト基盤整備 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `tot/` 統合シミュレータ（pl/eq/tr/ti/fp/dp/wr/wm をオーケストレーションする層）について、ライブラリ化に着手する前に「統合計算 → 状態取得 → 数値ベースライン化」の回帰テスト基盤を整える。

**Architecture:** TR Phase 0 (`test_run/scripts/run_tests.sh` + `compare_metrics.py`, **PR #2 の develop への merge で導入**) と同じ枠組みを再利用するが、tot は **複数モジュールの状態を統合してダンプする** 必要があるため、新規 `tot/totregress.f90` を導入する。これは TR の `trregress.f90` を雛形にしつつ、TR/TI/FP の状態変数を 1 つの `tot_regress.dat` にまとめて書き出す。環境変数 `TOT_REGRESS_DUMP=1` のときのみ有効化し、通常 `tot` バイナリ実行は完全に挙動不変。

> **Baseline 参照の verify 手順:** PR #2 が merge されたコミット SHA は時間とともに変わり得るため、plan 内では hardcode せず以下で特定する。
>
> ```bash
> # 1. develop 上の TR Phase 0 merge コミット (PR #2) を特定
> git log --oneline develop --grep "Phase 0" | head -1
> # 期待: "Merge pull request #2 ... Phase 0 regression baseline" 等の 1 行
>
> # 2. もしくは tag ベースで参照
> git tag -l 'tr-phase0-baseline'         # この plan 適用時は要確認
> git log --oneline tr-phase0-baseline -1 # tag があればその SHA
> ```
>
> tag `tr-phase0-baseline` が develop に未作成な場合、Task 1 Step 1 で `git tag tr-phase0-baseline <PR#2 merge SHA>` を実行して以後の手順で使える状態にする。

**Tech Stack:** Fortran 90 (`tot/totregress.f90`), Bash (既存 `test_run/run_tests.sh` 拡張), Python 3 標準ライブラリのみ (`extract_tot_metrics.py`, `compare_metrics.py` は既存を再利用), gfortran, 既存 TOT バイナリ `tot/tot`。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md`（Phase 0 の設計思想を tot に拡張）。

**前提条件:** `tot` バイナリが現状でビルドできること。`pl/eq/tr/ti/fp/dp/wr/wm` の各 `lib*.a` が既に存在していること（`tot/Makefile` の `libs` ターゲット参照）。**個別モジュールのライブラリ化（trapi/tiapi/fpapi/wrapi/wrxapi）が L-2 以降の依存となるが、L-0 はそれらに依存せず、既存 `tot` バイナリのままで完結する**。

---

## File Structure

このフェーズで作成・変更するファイル:

| ファイル | 種別 | 責務 |
|---|---|---|
| `tot/totregress.f90` | 新規 | 環境変数ガード付き高精度 dump（TR/TI/FP/WR の状態を統合書き出し） |
| `tot/totmain.f90` | 修正 | `tot_menu` 復帰直後に `tot_regress_dump_if_enabled` を呼ぶ 1 行フック追加 |
| `tot/Makefile` | 修正 | `SRCS` に `totregress.f90` を追加、`tot` リンク時にオブジェクトを含める |
| `test_run/inputs/tot_demo2014_short.in` | 新規 | demo2014 短縮版（NTMAX=10、グラフィクス無効化、TR→FP→TI のミニマム fan-out） |
| `test_run/inputs/tot_ht6m_short.in` | 新規 | HT6M 系短縮版（EQ→TR の典型コース、tot/HT6M/tot.HT6M.in をベースに切り詰め） |
| `test_run/scripts/extract_tot_metrics.py` | 新規 | `tot_regress.dat` から数値指標を JSON に変換 |
| `test_run/scripts/tests/test_extract_tot_metrics.py` | 新規 | 抽出スクリプトのユニットテスト |
| `test_run/scripts/tests/fixtures/sample_tot_regress.dat` | 新規 | 抽出テスト用の最小 dump fixture |
| `test_run/scripts/check_tot_regression.sh` | 新規 | tot 用ラッパ（`extract_tot_metrics.py` + 既存 `compare_metrics.py` を呼ぶ） |
| `test_run/baselines/tot_demo2014_short/metrics.json` | 新規（生成） | ベースライン指標 |
| `test_run/baselines/tot_ht6m_short/metrics.json` | 新規（生成） | ベースライン指標 |
| `test_run/test_definitions.conf` | 修正 | `tot_demo2014_short`, `tot_ht6m_short` を追加 |
| `test_run/run_tests.sh` | 修正 | tot モジュールに対し `TOT_REGRESS_DUMP=1` をエクスポートし、成功時に `check_tot_regression.sh` を呼ぶ（既存 `tr` 分岐に並列で 1 ブロック追加） |
| `test_run/README.md` | 修正 | tot 統合系テストのセクションを追記 |

**方針:**
- TOT 本体への追加は **`totregress.f90` 新規 1 ファイル + `totmain.f90` への 1 行フック + Makefile への 1 行追加** に限定。通常実行（環境変数未設定）では挙動完全不変。
- 比較指標は **TR と TI/FP の状態を「該当モジュールが活性なら出す」方針**。tot は menu 経由で各モジュールが有効化されるとは限らないので、未初期化時はスキップする（IF 句でガード）。
- 既存 `compare_metrics.py` は scalars + profile 構造に依存するため、**そのまま再利用可能**。違いは抽出スクリプトのみ。
- ベースラインは初回 `--generate-baseline` モードで書き出し、以後は比較のみ。

---

## Task 1: 作業用ブランチ作成と既存 tot バイナリのビルド確認

**Files:** なし（環境準備）

- [ ] **Step 1: 現在の git 状態を確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git status
git branch --show-current
```
Expected: develop ベースの作業ブランチに居る（例: `feature/tot-library-l0-baseline`）。uncommitted の重要変更がないこと。

- [ ] **Step 2: L-0 用ブランチを作る**

Run:
```bash
git checkout -b feature/tot-library-l0-baseline develop
```
Expected: ブランチが切り替わる。

- [ ] **Step 3: 既存依存ライブラリと tot をビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/tot
make libs 2>&1 | tail -10
make tot 2>&1 | tail -10
ls -la /home/k-yoshimi/program/task/tot/tot
```
Expected: `tot` バイナリが生成される。エラーなし。

もし依存ライブラリ側でビルドエラーが出る場合は、L-0 を着手する前提条件が満たされていない。develop が壊れていないか確認し、必要なら修正 PR を先行する。

- [ ] **Step 4: コンパイラ最適化フラグの確認**

Run:
```bash
grep -n "^FFLAGS" /home/k-yoshimi/program/task/tot/Makefile
grep -n "^OFLAGS" /home/k-yoshimi/program/task/make.header | head -3
```
Expected:
- `tot/Makefile` は `FFLAGS=$(OFLAGS)` を使っている（`$(DFLAGS)` がアンコメントされていない）。
- `make.header` の `OFLAGS = -g -O3 -m64 -std=legacy` 相当が有効。

- [ ] **Step 5: 既存の tot.demo2014 がインタラクティブに動くことだけ確認**

Run:
```bash
cd /home/k-yoshimi/program/task/tot/demo2014
ls -la tot.demo2014.in eqdata.* 2>&1 | head -10
```
Expected: 入力ファイルとともに `eqdata.demo2014` が存在する（事前計算済み equilibrium データが必要）。

なければ、Task 5 の入力作成時に `eqdata.demo2014` を test_run 配下にコピーする手順を追加する。

- [ ] **Step 6: コミット（ブランチ初期化マーカー）**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "chore(tot): start Phase L-0 regression test scaffolding"
```

---

## Task 2: ダンプ対象の決定（tot 統合状態のスコープ確定）

**Files:** 調査のみ

**決定事項（本計画で確定済み）:**

tot は複数モジュールのオーケストレータなので、dump 対象も「いずれのモジュールが回ったかで内容が変わる」。L-0 では以下を採用:

- **TR 関連スカラー（TR が呼ばれていれば出力）:** `NT, NRMAX, NSMAX, T, WPT, AJT, Q0, BETA0, BETAP0, BETAA, BETAN, TAUE1, TAUE2, ZEFF0, ALI, RQ1`（TR Phase 0 と完全同一）
- **TR プロファイル:** `RN(NR,1:NSMAX), RT(NR,1:NSMAX), AJ(NR), QP(NR)`（同上）
- **TI 関連スカラー（TI が呼ばれていれば出力、L-0 段階では先送り可）:** プレースホルダのみ。L-0 では `TI_PRESENT=0/1` フラグだけ書く
- **FP 関連スカラー（FP が呼ばれていれば出力、L-0 段階では先送り可）:** 同上 `FP_PRESENT=0/1` フラグのみ

**理由:**
- L-0 のミッションは「ベースライン取れる枠を整える」こと。TI/FP の細粒度指標は L-6（テスト 4 層）で必要に応じ追加。
- demo2014 と HT6M は実質 EQ + TR が中心。L-0 入力をその範囲に絞れば、TR Phase 0 と同じ scalars+profile スキーマで足りる。

**書式:** スカラー `1PE24.16`、プロファイル 1 行に NR と `1PE24.16` の連続。TR Phase 0 と完全同一。

**起動条件:** `TOT_REGRESS_DUMP=1` のときのみ `tot_regress.dat` を CWD に書き出す。

**許容誤差:** デフォルト `1e-10`。tot は `mtx_initialize`/MPI 初期化を経由する分、再現性が TR 単体より弱い可能性がある。Task 9 の run-to-run 確認で必要に応じ `1e-8` まで緩める。

- [ ] **Step 1: TR の dump スカラーが TRCOMM 経由で見えることを再確認**

Run:
```bash
grep -n "WPT\|AJT\|Q0\|BETA0\|TAUE1\|ZEFF0\|\bALI\b\|\bRQ1\b" /home/k-yoshimi/program/task/tr/trcomm.f90 | head -20
```
Expected: これらが TRCOMM 内に PUBLIC で宣言されている。

- [ ] **Step 2: TI/FP の "PRESENT" 判定に使える簡易フラグの場所を調査**

Run:
```bash
grep -n "MODULE ticomm\|MODULE fpcomm" /home/k-yoshimi/program/task/ti/ticomm.f90 /home/k-yoshimi/program/task/fp/fpcomm.f90 2>&1 | head -10
```
Expected: ticomm/fpcomm モジュール定義が見つかる。L-0 では「ALLOCATABLE 配列が既に ALLOCATE 済みかを `ALLOCATED(...)` で判定」する戦略を採用するメモを残す。

- [ ] **Step 3: コミット（plan の決定を locked-in する）**

Run:
```bash
git add docs/superpowers/plans/2026-04-18-tot-library-L0-baseline.md
git commit -m "docs(tot): lock L-0 dump scope (TR scalars+profile, TI/FP presence flag)"
```

---

## Task 3: `totregress.f90` を新規作成

**Files:**
- Create: `tot/totregress.f90`

**目的:** 環境変数 `TOT_REGRESS_DUMP=1` のときのみ、tot 統合計算終了時の TR スカラー・プロファイルと、TI/FP の存在フラグを `tot_regress.dat` へ高精度書き出し。

- [ ] **Step 1: `tot/totregress.f90` を新規作成**

作成: `tot/totregress.f90`

```fortran
! totregress.f90
!
! High-precision regression dump for the integrated tot simulator (Phase L-0).
! Emits tot_regress.dat (1PE24.16 format) when TOT_REGRESS_DUMP=1.
! Otherwise does nothing; normal tot runs are unaffected.
!
! Schema (format v1):
!   - TR scalars/profile (always written if TR has been allocated)
!   - TI/FP "presence" flags (1 if module's allocatable state is allocated, else 0)

MODULE totregress

  PRIVATE
  PUBLIC :: tot_regress_dump_if_enabled

CONTAINS

  SUBROUTINE tot_regress_dump_if_enabled
    USE TRCOMM, ONLY: &
         NRMAX, NSMAX, NT, T, &
         WPT, AJT, Q0, BETA0, BETAP0, BETAA, BETAN, &
         TAUE1, TAUE2, ZEFF0, ALI, RQ1, &
         RN, RT, AJ, QP
    IMPLICIT NONE
    INTEGER, PARAMETER :: UNIT_DUMP = 78
    CHARACTER(LEN=16) :: ENV_VAL
    INTEGER :: STAT, NR, NS, IOERR
    LOGICAL :: ENABLED, TR_OK

    CALL GET_ENVIRONMENT_VARIABLE('TOT_REGRESS_DUMP', ENV_VAL, STATUS=STAT)
    ENABLED = (STAT == 0 .AND. TRIM(ENV_VAL) == '1')
    IF (.NOT. ENABLED) RETURN

    OPEN(UNIT=UNIT_DUMP, FILE='tot_regress.dat', &
         STATUS='REPLACE', ACTION='WRITE', IOSTAT=IOERR)
    IF (IOERR /= 0) THEN
       WRITE(6,*) 'XX totregress: cannot open tot_regress.dat, IOSTAT=', IOERR
       RETURN
    END IF

    WRITE(UNIT_DUMP, '(A)') '# TASK/TOT regression dump (format v1)'

    ! TR scalars (assume TR was initialized; menu always calls tr_init)
    TR_OK = ALLOCATED(RN) .AND. ALLOCATED(RT) .AND. ALLOCATED(AJ) .AND. ALLOCATED(QP)
    IF (TR_OK) THEN
       WRITE(UNIT_DUMP, '(A)')           'TR_PRESENT=1'
       WRITE(UNIT_DUMP, '(A,I0)')        'NT=',     NT
       WRITE(UNIT_DUMP, '(A,I0)')        'NRMAX=',  NRMAX
       WRITE(UNIT_DUMP, '(A,I0)')        'NSMAX=',  NSMAX
       WRITE(UNIT_DUMP, '(A,1PE24.16)')  'T=',      T
       WRITE(UNIT_DUMP, '(A,1PE24.16)')  'WPT=',    WPT
       WRITE(UNIT_DUMP, '(A,1PE24.16)')  'AJT=',    AJT
       WRITE(UNIT_DUMP, '(A,1PE24.16)')  'Q0=',     Q0
       WRITE(UNIT_DUMP, '(A,1PE24.16)')  'BETA0=',  BETA0
       WRITE(UNIT_DUMP, '(A,1PE24.16)')  'BETAP0=', BETAP0
       WRITE(UNIT_DUMP, '(A,1PE24.16)')  'BETAA=',  BETAA
       WRITE(UNIT_DUMP, '(A,1PE24.16)')  'BETAN=',  BETAN
       WRITE(UNIT_DUMP, '(A,1PE24.16)')  'TAUE1=',  TAUE1
       WRITE(UNIT_DUMP, '(A,1PE24.16)')  'TAUE2=',  TAUE2
       WRITE(UNIT_DUMP, '(A,1PE24.16)')  'ZEFF0=',  ZEFF0
       WRITE(UNIT_DUMP, '(A,1PE24.16)')  'ALI=',    ALI
       WRITE(UNIT_DUMP, '(A,1PE24.16)')  'RQ1=',    RQ1

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
    ELSE
       WRITE(UNIT_DUMP, '(A)') 'TR_PRESENT=0'
    END IF

    ! TI/FP presence flags (placeholders; richer dump deferred to L-6)
    CALL dump_module_presence(UNIT_DUMP, 'TI_PRESENT', ti_is_allocated())
    CALL dump_module_presence(UNIT_DUMP, 'FP_PRESENT', fp_is_allocated())

    CLOSE(UNIT_DUMP)
  END SUBROUTINE tot_regress_dump_if_enabled

  SUBROUTINE dump_module_presence(unit, label, present)
    INTEGER, INTENT(IN) :: unit
    CHARACTER(LEN=*), INTENT(IN) :: label
    LOGICAL, INTENT(IN) :: present
    IF (present) THEN
       WRITE(unit, '(A,A)') TRIM(label), '=1'
    ELSE
       WRITE(unit, '(A,A)') TRIM(label), '=0'
    END IF
  END SUBROUTINE dump_module_presence

  LOGICAL FUNCTION ti_is_allocated()
    USE ticomm, ONLY: RNI => RN  ! 例: TI 側に同名 ALLOCATABLE がある想定。
    ti_is_allocated = ALLOCATED(RNI)
  END FUNCTION ti_is_allocated

  LOGICAL FUNCTION fp_is_allocated()
    USE fpcomm, ONLY: FNS  ! 例: FP の代表 ALLOCATABLE 配列。
    fp_is_allocated = ALLOCATED(FNS)
  END FUNCTION fp_is_allocated

END MODULE totregress
```

**注:** `ti_is_allocated`/`fp_is_allocated` の `USE` 対象配列名は実際の `ticomm.f90` / `fpcomm.f90` を確認して合わせる。L-0 段階の主目的は「フラグが書ければよい」ので、安全なフラグ判定にできる ALLOCATABLE が無ければ常に `.TRUE.`/`.FALSE.` で書いて L-6 でリッチ化する。

- [ ] **Step 2: ti/fp の代表 ALLOCATABLE 配列名を確認して書き換え**

Run:
```bash
grep -n "ALLOCATABLE.*::.*(" /home/k-yoshimi/program/task/ti/ticomm.f90 | head -5
grep -n "ALLOCATABLE.*::.*(" /home/k-yoshimi/program/task/fp/fpcomm.f90 | head -5
```
Expected: ALLOCATABLE 配列名のリストが取れる。`RNI`/`FNS` に該当する変数名を選び、Step 1 の `USE` 句を書き換える。

- [ ] **Step 3: コミット**

Run:
```bash
git add tot/totregress.f90
git commit -m "feat(tot): add env-guarded high-precision dump module"
```

---

## Task 4: `tot/totmain.f90` にフックを追加

**Files:**
- Modify: `tot/totmain.f90`（USE 文 1 行 + 呼び出し 1 行）

- [ ] **Step 1: `tot/totmain.f90` の USE 文セクションに totregress を追加**

`tot/totmain.f90` の `USE totmenu,ONLY: tot_menu` の **次行** に以下を挿入:

```fortran
  USE totregress, ONLY : tot_regress_dump_if_enabled
```

- [ ] **Step 2: `CALL tot_menu` の **直後** に dump フック呼び出しを挿入**

`tot/totmain.f90` の `CALL tot_menu` 行の直後に以下を挿入:

```fortran
  CALL tot_regress_dump_if_enabled   ! Phase L-0 regression dump (env-guarded)
```

これにより、メニューを `Q` で抜けた直後に dump が走る。

- [ ] **Step 3: 構文確認のためにビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/tot
make 2>&1 | tail -10
```
Expected: `totregress.o` のコンパイル → `totmain.o` のコンパイル → リンクが成功し、`tot` バイナリが更新される。

ビルドエラーが出る場合:
- `ti_is_allocated`/`fp_is_allocated` で USE する配列名が誤っている → 実際の名前に修正
- modパスの問題 → `tot/Makefile` の `MODINCLUDE` に既に `-I../ti/$(MOD) -I../fp/$(MOD)` が含まれているため通常は問題ないはず

- [ ] **Step 4: コミット**

Run:
```bash
git add tot/totmain.f90
git commit -m "feat(tot): hook regression dump after tot_menu returns"
```

---

## Task 5: `tot/Makefile` の SRCS に totregress.f90 を追加

**Files:**
- Modify: `tot/Makefile`

- [ ] **Step 1: `SRCS = totmenu.f90` を 2 行に拡張**

変更前:
```makefile
SRCS = totmenu.f90
```

変更後:
```makefile
SRCS = totmenu.f90 totregress.f90
```

これにより `OBJS = $(SRCS:.f90=.o)` 経由で `totregress.o` が生成される。

- [ ] **Step 2: `tot` リンク行に `totregress.o` を含める**

変更前:
```makefile
tot : $(LIB_MTX) $(LIBS) totmenu.o totmain.o
	$(FLINKER) totmenu.o totmain.o -o $@ $(FFLAGS) $(LIBS) $(FLIBS) $(LIBX_MTX)
```

変更後:
```makefile
tot : $(LIB_MTX) $(LIBS) totmenu.o totregress.o totmain.o
	$(FLINKER) totmenu.o totregress.o totmain.o -o $@ $(FFLAGS) $(LIBS) $(FLIBS) $(LIBX_MTX)

totregress.o: totregress.f90
```

- [ ] **Step 3: 完全リビルドで確認**

Run:
```bash
cd /home/k-yoshimi/program/task/tot
make clean
make tot 2>&1 | tail -15
ls -la tot
```
Expected: `tot` バイナリが新しいタイムスタンプで生成される。

- [ ] **Step 4: コミット**

Run:
```bash
git add tot/Makefile
git commit -m "build(tot): wire totregress.f90 into Makefile"
```

---

## Task 6: 短縮版入力ファイル `tot_demo2014_short.in` を作る

**Files:**
- Create: `test_run/inputs/tot_demo2014_short.in`
- Create: `test_run/inputs/tot_demo2014_short.eqdata` (既存 `tot/demo2014/eqdata.demo2014` のコピー、必要なら)

- [ ] **Step 1: 既存 demo2014 入力を確認**

Run:
```bash
cat /home/k-yoshimi/program/task/tot/demo2014/tot.demo2014.in
ls /home/k-yoshimi/program/task/tot/demo2014/eqdata.* 2>&1 | head -5
```
Expected: 既存入力が表示され、`eqdata.demo2014` も存在する。

- [ ] **Step 2: TR フェーズだけに絞った最小入力を新規作成**

作成: `test_run/inputs/tot_demo2014_short.in`

L-0 の目的は「TR の最終状態を tot 経由で取れるようにする」だけなので、demo2014 入力から WR/FP セクションを削除し、TR の `g` (graphics) を `s` (scan/save) に置換、終了 `q` を 2 つ並べる。

```
0
f
tot.demo2014_short.gs
c
eq
p
 &eq 
   RR=8.5
   RA=2.42
   RKAP=1.65
   RDLT=0.33
   RB=2.60
   BB=5.94
   RIP=12.3
   KNAMEQ='eqdata.demo2014'
 &end
r
c
 0.64/
s
x
s
q
tr
r
s
x
q
q
```

**要点:**
- `eq` セクションで equilibrium を読み、`r` (run) → `c` (continue) → 半径 `0.64/` を入力。
- `s` (save) のみで `g` (graphics) は呼ばない（GS スクリーンショット要求を避ける）。
- `tr` セクションで `r` (run) → `s` (save) のみ。
- `q` を 2 回（tr 抜け、tot 抜け）。

- [ ] **Step 3: eqdata の取り扱いを確定**

Run:
```bash
cp /home/k-yoshimi/program/task/tot/demo2014/eqdata.demo2014 \
   /home/k-yoshimi/program/task/test_run/inputs/eqdata.demo2014
ls -la /home/k-yoshimi/program/task/test_run/inputs/eqdata.demo2014
```

そして Task 11 で `run_tests.sh` 修正時に「tot モジュールの場合は inputs/eqdata.* を test_dir にコピー」する処理を追加する（既存の eq dependency-copy ロジックに準拠）。

- [ ] **Step 4: 短縮入力で tot を手動実行して動作確認**

Run:
```bash
cd /tmp && rm -rf tot_l0_smoke && mkdir tot_l0_smoke && cd tot_l0_smoke
cp /home/k-yoshimi/program/task/test_run/inputs/eqdata.demo2014 .
TOT_REGRESS_DUMP=1 timeout 180 /home/k-yoshimi/program/task/tot/tot \
    < /home/k-yoshimi/program/task/test_run/inputs/tot_demo2014_short.in > out.log 2>&1
echo "exit=$?"
ls -la tot_regress.dat
head -20 tot_regress.dat
grep -i "closed\|error" out.log | head -10
```
Expected:
- exit code 0、`CLOSED` メッセージあり。
- `tot_regress.dat` が生成され、`TR_PRESENT=1` と TR スカラーが書かれている。

もし `CLOSED` が出ない / エラーがある場合は入力 EOF や menu キーシーケンスを微調整する。最低でも「`tot_regress.dat` が生成される」ことが Step 4 の Pass 条件。

- [ ] **Step 5: コミット**

Run:
```bash
git add test_run/inputs/tot_demo2014_short.in test_run/inputs/eqdata.demo2014
git commit -m "test(tot): add demo2014 short-form integration input"
```

---

## Task 7: 2 つ目の入力 `tot_ht6m_short.in` を作る

**Files:**
- Create: `test_run/inputs/tot_ht6m_short.in`

- [ ] **Step 1: 既存 HT6M 入力を確認**

Run:
```bash
cat /home/k-yoshimi/program/task/tot/HT6M/tot.HT6M.in
ls /home/k-yoshimi/program/task/tot/HT6M/ | head -20
```
Expected: 既存入力（`eq`/`tr` 中心、グラフィクス t6/t7/r1/r4/r7/g1 あり）が表示される。

- [ ] **Step 2: グラフィクスを除いた最小版を新規作成**

作成: `test_run/inputs/tot_ht6m_short.in`

```
0
f
tot.HT6M_short.gs
c
eq
r
s
g
c
x
q
tr
r
s
x
q
q
```

**要点:**
- 元入力の `t6 t7 r1 r4 r7 g1` 系列を全削除（グラフィクス出力は不要、CLOSED 判定だけ欲しい）。
- `eq` セクションでも `g`（graphics）はそのまま残し（eq menu 構造の都合上必要なら）、最終的に `tr` で `r`（run）→ `s`（save）の最短経路。

- [ ] **Step 3: HT6M の依存ファイル（eqdata 等）を inputs/ にコピー**

Run:
```bash
ls /home/k-yoshimi/program/task/tot/HT6M/eqdata.* 2>&1 | head
# 必要に応じ
cp /home/k-yoshimi/program/task/tot/HT6M/eqdata.* \
   /home/k-yoshimi/program/task/test_run/inputs/ 2>/dev/null || true
```
Expected: HT6M 用 eqdata がある場合は inputs/ にコピー。なければスキップ（この入力は eq モジュール内で生成する想定）。

- [ ] **Step 4: 短縮入力で tot を手動実行**

Run:
```bash
cd /tmp && rm -rf tot_l0_smoke2 && mkdir tot_l0_smoke2 && cd tot_l0_smoke2
cp /home/k-yoshimi/program/task/test_run/inputs/eqdata.* . 2>/dev/null || true
TOT_REGRESS_DUMP=1 timeout 180 /home/k-yoshimi/program/task/tot/tot \
    < /home/k-yoshimi/program/task/test_run/inputs/tot_ht6m_short.in > out.log 2>&1
echo "exit=$?"
grep -i "closed\|error" out.log | head -10
ls -la tot_regress.dat 2>&1 | head -2
```
Expected: `CLOSED` あり、`tot_regress.dat` 生成。

- [ ] **Step 5: コミット**

Run:
```bash
git add test_run/inputs/tot_ht6m_short.in
git commit -m "test(tot): add HT6M short-form integration input"
```

---

## Task 8: `extract_tot_metrics.py` を実装

**Files:**
- Create: `test_run/scripts/extract_tot_metrics.py`
- Create: `test_run/scripts/tests/test_extract_tot_metrics.py`
- Create: `test_run/scripts/tests/fixtures/sample_tot_regress.dat`

- [ ] **Step 1: サンプル fixture を作成**

作成: `test_run/scripts/tests/fixtures/sample_tot_regress.dat`

```
# TASK/TOT regression dump (format v1)
TR_PRESENT=1
NT=10
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
TI_PRESENT=0
FP_PRESENT=0
```

- [ ] **Step 2: 失敗するテストを書く**

作成: `test_run/scripts/tests/test_extract_tot_metrics.py`

```python
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "extract_tot_metrics.py"
FIXTURE = Path(__file__).parent / "fixtures" / "sample_tot_regress.dat"


def run_extract(dump_path: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(dump_path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def test_extracts_tr_scalars():
    data = run_extract(FIXTURE)
    assert data["NT"] == 10
    assert data["NRMAX"] == 2
    assert data["NSMAX"] == 2
    assert data["scalars"]["T"] == 2.0
    assert data["scalars"]["WPT"] == 41.13
    assert data["scalars"]["Q0"] == 0.579


def test_extracts_module_presence():
    data = run_extract(FIXTURE)
    assert data["modules"]["TR_PRESENT"] == 1
    assert data["modules"]["TI_PRESENT"] == 0
    assert data["modules"]["FP_PRESENT"] == 0


def test_extracts_profile():
    data = run_extract(FIXTURE)
    prof = data["profile"]
    assert len(prof) == 2
    assert prof[0]["NR"] == 1
    assert len(prof[0]["RN"]) == 2
    assert prof[0]["AJ"] == 15.451


def test_handles_tr_absent(tmp_path):
    dump = tmp_path / "no_tr.dat"
    dump.write_text(
        "# TASK/TOT regression dump (format v1)\n"
        "TR_PRESENT=0\n"
        "TI_PRESENT=0\n"
        "FP_PRESENT=0\n"
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(dump)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    assert data["modules"]["TR_PRESENT"] == 0
    assert data["scalars"] == {}
    assert data["profile"] == []
    # NT/NRMAX/NSMAX may be missing — extract should not crash
    assert data["NRMAX"] == 0
```

- [ ] **Step 3: テストを走らせて失敗を確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run/scripts
python3 -m pytest tests/test_extract_tot_metrics.py -v
```
Expected: FAIL（スクリプト未実装）。

- [ ] **Step 4: スクリプト本体を実装**

作成: `test_run/scripts/extract_tot_metrics.py`

```python
#!/usr/bin/env python3
"""Convert tot_regress.dat into a JSON for regression comparison.

Schema:
    {
      "NT": int, "NRMAX": int, "NSMAX": int,
      "modules": {"TR_PRESENT": 0|1, "TI_PRESENT": 0|1, "FP_PRESENT": 0|1},
      "scalars": {...},   # TR scalars when TR_PRESENT=1, else {}
      "profile": [...],   # TR profile rows when TR_PRESENT=1, else []
    }
Compatible with the existing compare_metrics.py (which already inspects
NT/NRMAX/NSMAX/scalars/profile and ignores unknown top-level keys like
"modules").
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
MODULE_KEYS = {"TR_PRESENT", "TI_PRESENT", "FP_PRESENT"}
RE_PROFILE_HEADER = re.compile(r"^#\s*profile columns:")


def parse(dump_path: Path) -> dict:
    lines = dump_path.read_text().splitlines()
    result = {
        "NT": 0, "NRMAX": 0, "NSMAX": 0,
        "modules": {},
        "scalars": {},
        "profile": [],
    }
    in_profile = False
    for raw in lines:
        line = raw.strip()
        if not line:
            # Blank line terminates the current section (e.g. profile block).
            in_profile = False
            continue
        if RE_PROFILE_HEADER.match(line):
            in_profile = True
            continue
        if line.startswith("#"):
            # Any non-profile-header comment line also closes the profile
            # block, so subsequent `KEY = VAL` sections are parsed correctly.
            in_profile = False
            continue
        if not in_profile:
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            if key in MODULE_KEYS:
                result["modules"][key] = int(val)
            elif key in ("NT", "NRMAX", "NSMAX"):
                result[key] = int(val)
            elif key in SCALAR_KEYS:
                result["scalars"][key] = float(val)
            else:
                pass  # ignore unknown
        else:
            parts = line.split()
            if len(parts) < 4:
                continue
            nsmax = result.get("NSMAX", 0)
            if nsmax <= 0:
                raise SystemExit("profile row encountered before NSMAX")
            expected = 1 + 2 * nsmax + 2
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

    if result["modules"].get("TR_PRESENT", 0) == 1:
        if result["NRMAX"] == 0:
            raise SystemExit("TR_PRESENT=1 but NRMAX missing")
        if len(result["profile"]) != result["NRMAX"]:
            raise SystemExit(
                f"profile row count {len(result['profile'])} != NRMAX {result['NRMAX']}"
            )
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

- [ ] **Step 5: 実行権限付与してテストを再実行**

Run:
```bash
chmod +x /home/k-yoshimi/program/task/test_run/scripts/extract_tot_metrics.py
cd /home/k-yoshimi/program/task/test_run/scripts
python3 -m pytest tests/test_extract_tot_metrics.py -v
```
Expected: 4 tests PASS。

- [ ] **Step 6: コミット**

Run:
```bash
git add test_run/scripts/extract_tot_metrics.py \
        test_run/scripts/tests/test_extract_tot_metrics.py \
        test_run/scripts/tests/fixtures/sample_tot_regress.dat
git commit -m "test(tot): add metric extractor for tot_regress.dat"
```

---

## Task 9: `check_tot_regression.sh` ラッパを作る

**Files:**
- Create: `test_run/scripts/check_tot_regression.sh`

- [ ] **Step 1: 既存 `check_regression.sh` を雛形にして tot 用を作成**

作成: `test_run/scripts/check_tot_regression.sh`

```bash
#!/bin/bash
#
# check_tot_regression.sh <test_name> <test_output_dir> <baselines_dir> [tolerance] [--generate-baseline]
#
# Reads <test_output_dir>/tot_regress.dat (produced when tot is run with
# TOT_REGRESS_DUMP=1), extracts metrics to JSON, and compares with
# <baselines_dir>/<test_name>/metrics.json.
#
# Exit codes: 0=match, 1=mismatch, 2=missing dump, 3=missing baseline.
#
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_NAME="${1:?usage: $0 <test_name> <output_dir> <baselines_dir> [tol] [--generate-baseline]}"
OUTPUT_DIR="${2:?}"
BASELINES_DIR="${3:?}"
TOL="${4:-1e-10}"
MODE="${5:-compare}"

DUMP="$OUTPUT_DIR/tot_regress.dat"
METRICS_ACTUAL="$OUTPUT_DIR/metrics.json"
METRICS_BASE="$BASELINES_DIR/$TEST_NAME/metrics.json"

if [[ ! -f "$DUMP" ]]; then
    echo "check_tot_regression: dump not found: $DUMP" >&2
    echo "  did the test run with TOT_REGRESS_DUMP=1 exported?" >&2
    exit 2
fi

if ! python3 "$SCRIPT_DIR/extract_tot_metrics.py" "$DUMP" > "$METRICS_ACTUAL"; then
    echo "check_tot_regression: failed to parse $DUMP" >&2
    exit 2
fi

if [[ "$MODE" == "--generate-baseline" ]]; then
    mkdir -p "$(dirname "$METRICS_BASE")"
    cp "$METRICS_ACTUAL" "$METRICS_BASE"
    echo "Baseline written: $METRICS_BASE"
    exit 0
fi

if [[ ! -f "$METRICS_BASE" ]]; then
    echo "check_tot_regression: baseline not found: $METRICS_BASE" >&2
    echo "  run with --generate-baseline to create it." >&2
    exit 3
fi

python3 "$SCRIPT_DIR/compare_metrics.py" \
    --baseline "$METRICS_BASE" \
    --actual "$METRICS_ACTUAL" \
    --tolerance "$TOL"
```

- [ ] **Step 2: 実行権限付与**

Run:
```bash
chmod +x /home/k-yoshimi/program/task/test_run/scripts/check_tot_regression.sh
```

- [ ] **Step 3: 手動 dump で動作確認**

Run:
```bash
cd /tmp/tot_l0_smoke   # Task 6 で作った作業ディレクトリ
/home/k-yoshimi/program/task/test_run/scripts/check_tot_regression.sh \
    tot_demo2014_short . /tmp/tot_baselines 1e-10 --generate-baseline
ls -la /tmp/tot_baselines/tot_demo2014_short/metrics.json
```
Expected: ベースライン JSON が生成される。

```bash
# 比較モード
/home/k-yoshimi/program/task/test_run/scripts/check_tot_regression.sh \
    tot_demo2014_short . /tmp/tot_baselines 1e-10
echo "exit=$?"
```
Expected: `OK: metrics match within tol=1e-10`、exit=0。

- [ ] **Step 4: コミット**

Run:
```bash
git add test_run/scripts/check_tot_regression.sh
git commit -m "test(tot): add check_tot_regression wrapper script"
```

---

## Task 10: 同一入力の run-to-run 再現性を確認

**Files:** なし（測定のみ）

- [ ] **Step 1: 同じ入力を 2 回流して dump diff**

Run:
```bash
cd /tmp && rm -rf tot_repro && mkdir tot_repro && cd tot_repro
cp /home/k-yoshimi/program/task/test_run/inputs/eqdata.demo2014 .

TOT_REGRESS_DUMP=1 timeout 180 /home/k-yoshimi/program/task/tot/tot \
    < /home/k-yoshimi/program/task/test_run/inputs/tot_demo2014_short.in > /dev/null 2>&1
cp tot_regress.dat /tmp/tot_run1.dat

TOT_REGRESS_DUMP=1 timeout 180 /home/k-yoshimi/program/task/tot/tot \
    < /home/k-yoshimi/program/task/test_run/inputs/tot_demo2014_short.in > /dev/null 2>&1
diff /tmp/tot_run1.dat tot_regress.dat
echo "diff exit=$?"
```
Expected: diff 出力空、exit=0。

- [ ] **Step 2: もし差異が出る場合の対応**

差異の根本原因を切り分け:
- MPI 関連の非決定性 → tot は `mtx_initialize` を呼ぶ。`mpiexec` 経由でないシングルラン前提を文書化。
- 浮動小数の桁落ち → 許容誤差を `1e-8` に緩めて Task 11 以降の `TOL` を調整。
- 入力の非決定パス（乱数、時刻依存）→ 入力を見直す。

差異が許容範囲（`1e-12` 以下）なら Task 11 で `TOL=1e-10` のままで進める。それ以上なら `TOL=1e-8` に緩めて plan に追記コミット。

- [ ] **Step 3: 結果メモをコミット（reproducibility 確認）**

Run:
```bash
echo "tot run-to-run reproducibility verified at TOL=1e-10 (or update if relaxed)" \
    > /tmp/tot_repro_note.txt
# plan の Task 10 に許容誤差確定の追記をして
cd /home/k-yoshimi/program/task
# (plan ファイル編集; 確定値を反映)
git commit --allow-empty -m "test(tot): confirm run-to-run reproducibility (tol=1e-10)"
```

---

## Task 11: `test_definitions.conf` と `run_tests.sh` を拡張

**Files:**
- Modify: `test_run/test_definitions.conf`
- Modify: `test_run/run_tests.sh`

- [ ] **Step 1: `test_definitions.conf` に tot ケース 2 件を追加**

`test_run/test_definitions.conf` の末尾に以下を追加:

```
# =============================================================================
# TOT Module Tests (Integrated simulator orchestrating eq/tr/ti/fp/...)
# Uses local test inputs with shortened menu sequences (graphics suppressed).
# =============================================================================
tot_demo2014_short:tot:@inputs/tot_demo2014_short.in:none:240:DEMO2014 integrated short-form
tot_ht6m_short:tot:@inputs/tot_ht6m_short.in:none:240:HT6M integrated short-form
```

- [ ] **Step 2: `run_tests.sh` の `get_binary` に tot を追加**

`test_run/run_tests.sh` の `get_binary()` を修正:

```bash
get_binary() {
    local module="$1"
    case "$module" in
        eq) echo "$TASK_DIR/eq/eq" ;;
        tr) echo "$TASK_DIR/tr/tr2" ;;
        fp) echo "$TASK_DIR/fp/fp" ;;
        tx) echo "$TASK_DIR/tx/tx2" ;;
        tot) echo "$TASK_DIR/tot/tot" ;;
        *) echo "" ;;
    esac
}
```

- [ ] **Step 3: tot モジュールの環境変数エクスポートと dependency-copy を追加**

`run_tests.sh` の TR モジュール用 `tr_env=()` ブロックの直後に、tot 用ブロックを追加:

変更前（該当箇所）:
```bash
    # For TR module, enable regression dump (env-guarded inside trregress.f90).
    local tr_env=()
    if [[ "$module" == "tr" ]]; then
        tr_env=(env TR_REGRESS_DUMP=1)
    fi
```

変更後:
```bash
    # For TR module, enable regression dump (env-guarded inside trregress.f90).
    local tr_env=()
    if [[ "$module" == "tr" ]]; then
        tr_env=(env TR_REGRESS_DUMP=1)
    elif [[ "$module" == "tot" ]]; then
        tr_env=(env TOT_REGRESS_DUMP=1)
        # Stage shared eqdata files referenced by tot inputs.
        cp "$SCRIPT_DIR/inputs/eqdata."* "$test_dir/" 2>/dev/null || true
    fi
```

- [ ] **Step 4: 成功時の dump 比較分岐に tot ブランチを追加**

`run_tests.sh` の `if [[ "$module" == "tr" ]]; then` 既存ブロックの直後に、tot 用 `elif` を追加:

変更前:
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
        if [[ "$module" == "tr" ]]; then
            if ! "$SCRIPT_DIR/scripts/check_regression.sh" \
                    "$test_name" "$test_dir" "$SCRIPT_DIR/baselines" "1e-10" \
                    > "$test_dir/regression.log" 2>&1; then
                reg_ok=0
            fi
        elif [[ "$module" == "tot" ]]; then
            if ! "$SCRIPT_DIR/scripts/check_tot_regression.sh" \
                    "$test_name" "$test_dir" "$SCRIPT_DIR/baselines" "1e-10" \
                    > "$test_dir/regression.log" 2>&1; then
                reg_ok=0
            fi
        fi
```

- [ ] **Step 5: 構文確認（dry-run）**

Run:
```bash
bash -n /home/k-yoshimi/program/task/test_run/run_tests.sh && echo "syntax OK"
```
Expected: `syntax OK`。

- [ ] **Step 6: コミット**

Run:
```bash
git add test_run/test_definitions.conf test_run/run_tests.sh
git commit -m "test(tot): wire tot regression checks into run_tests.sh"
```

---

## Task 12: ベースラインを生成してコミット

**Files:**
- Create: `test_run/baselines/tot_demo2014_short/metrics.json`
- Create: `test_run/baselines/tot_ht6m_short/metrics.json`

- [ ] **Step 1: テストを `--generate-baseline` モード相当で 1 回流して dump を作る**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tot_demo2014_short
# このとき baselines がまだ無いので REGRESSION で fail するが test_output/tot_demo2014_short/tot_regress.dat は生成される
ls -la test_output/tot_demo2014_short/tot_regress.dat
```
Expected: `tot_regress.dat` が生成される。テスト結果は REGRESSION（baseline 無し）。

- [ ] **Step 2: ベースラインを生成**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./scripts/check_tot_regression.sh tot_demo2014_short \
    test_output/tot_demo2014_short baselines 1e-10 --generate-baseline
ls -la baselines/tot_demo2014_short/metrics.json
```
Expected: `baselines/tot_demo2014_short/metrics.json` が生成される。

- [ ] **Step 3: もう 1 件も同様**

Run:
```bash
./run_tests.sh tot_ht6m_short
./scripts/check_tot_regression.sh tot_ht6m_short \
    test_output/tot_ht6m_short baselines 1e-10 --generate-baseline
ls -la baselines/tot_ht6m_short/metrics.json
```
Expected: 2 件目のベースラインも生成。

- [ ] **Step 4: 両ケース PASS を確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tot_demo2014_short tot_ht6m_short
```
Expected: 両方 `PASS`。

- [ ] **Step 5: コミット**

Run:
```bash
git add test_run/baselines/tot_demo2014_short/metrics.json \
        test_run/baselines/tot_ht6m_short/metrics.json
git commit -m "test(tot): commit initial regression baselines (demo2014, HT6M)"
```

---

## Task 13: README 更新と最終確認

**Files:**
- Modify: `test_run/README.md`

- [ ] **Step 1: README に tot セクションを追記**

`test_run/README.md` に以下のセクションを追加:

```markdown
## TOT Integrated Tests (Phase L-0)

The `tot` module is the integrated transport simulator orchestrating
`pl/eq/tr/ti/fp/dp/wr/wm`. Regression tests use the same dump-and-compare
mechanism as TR Phase 0:

- `tot/totregress.f90` writes `tot_regress.dat` when `TOT_REGRESS_DUMP=1`.
- `run_tests.sh` exports the env var automatically for `tot` module tests
  and stages `inputs/eqdata.*` into the test directory.
- `scripts/check_tot_regression.sh` parses the dump via
  `extract_tot_metrics.py` and compares against
  `baselines/<test_name>/metrics.json` (default tolerance 1e-10).

### Adding a new tot test case

1. Create a short-form input under `test_run/inputs/tot_<name>.in` that ends
   with the menu `Q` sequence and avoids graphics commands.
2. Stage required equilibrium / boundary data into `test_run/inputs/`
   (typically `eqdata.<case>`).
3. Run `./run_tests.sh tot_<name>` once to generate
   `test_output/tot_<name>/tot_regress.dat`.
4. Generate the baseline:
   `./scripts/check_tot_regression.sh tot_<name> test_output/tot_<name> baselines 1e-10 --generate-baseline`
5. Add the entry to `test_definitions.conf` and commit baseline JSON.
```

- [ ] **Step 2: 全 tot テストを通す最終確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tot_demo2014_short tot_ht6m_short
```
Expected: 2/2 PASS。

- [ ] **Step 3: 既存 TR/EQ テストが壊れていないことを確認**

Run:
```bash
./run_tests.sh
```
Expected: `tot_*` を含む全ケースで FAIL ゼロ。

- [ ] **Step 4: コミット**

Run:
```bash
git add test_run/README.md
git commit -m "docs(tot): document Phase L-0 integrated regression workflow"
```

---

## Verification (Phase L-0 完了基準)

以下が満たされれば L-0 完了:

- [ ] `tot/totregress.f90` が新規追加され、env-guarded で動作（`TOT_REGRESS_DUMP=1` 時のみ dump）。
- [ ] `tot/totmain.f90` への変更は USE 1 行 + CALL 1 行のみ。通常実行は完全に挙動不変。
- [ ] `tot/Makefile` に `totregress.f90` が SRCS に追加されている。
- [ ] `tot_demo2014_short` と `tot_ht6m_short` の 2 ケースで `tot_regress.dat` が再現性 `1e-10` で生成される。
- [ ] `test_run/baselines/tot_*/metrics.json` が commit されている。
- [ ] `./run_tests.sh tot_demo2014_short tot_ht6m_short` が PASS。
- [ ] 既存 TR/EQ テストの結果に変化なし（tot 変更が他モジュールに波及していないこと）。

---

## Dependencies & Fallback

**この plan の前提:**
- `tot` バイナリが現状 develop でビルドできる。
- `pl/eq/tr/ti/fp/dp/wr/wm` の各 lib は変更不要（L-0 はリンク方式に手を付けない）。

**この plan が産出するもの:**
- L-2 以降が `tot_api.f90` を実装する際に「数値挙動が壊れていないか」を機械的に検知する**回帰ネット**。
- L-1 で graphics を分離した際の数値不変性の検証手段。

**Fallback:**
- demo2014 入力が menu 操作の都合で短縮しきれない場合 → 入力 1 件（HT6M）だけで L-0 を確定し、もう 1 件は L-6 の Layer 1 で増やす。
- run-to-run 差異が `1e-10` で吸収できない場合 → TOL を `1e-8` まで緩める。tot は MPI 経由で初期化するため TR 単体より厳しい可能性は許容する。
- TI/FP の `ALLOCATED(...)` 判定が安全に書けない場合 → Task 3 の presence フラグを定数 `0` で書き出して L-6 でリッチ化を後回し。

---

## Out of scope（次フェーズ送り）

- TI/FP の数値スカラー dump → L-6（テスト 4 層）
- WR/WM の dump → L-6（必要に応じ）
- Python ラッパからの dump 検証 → L-5/L-6
- パラメータスイープ → L-7
