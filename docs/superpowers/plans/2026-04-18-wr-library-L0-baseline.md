# WR ライブラリ化 Phase L-0: 回帰テスト基盤整備 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `wr/` モジュールのライブラリ化（Phase L）に着手する前に、TR と同じ仕組みの回帰テスト基盤を整え、3 ケースのゴールデン dump をベースライン化して `run_tests.sh` で自動比較できるようにする。

**Architecture:** TR と同じ「環境変数ガード付き高精度 dump + Python 比較」パターンを WR にも導入する。WR 本体には `wrregress.f90` を 1 ファイル新規追加し、`wrexec.f90` の `wr_exec` 完了直後に 1 行フックを差す（環境変数 `WR_REGRESS_DUMP=1` のときだけ `wr_regress.dat` を出力、未設定なら完全に no-op）。`test_run/scripts/extract_wr_metrics.py` と `test_run/scripts/check_regression_wr.sh` を新設し、既存の `compare_metrics.py` を再利用する形で共通化する。3 ケース（`wr_iter_lhcd`, `wr_test001`, `wr_tst2_ec`）を `test_definitions.conf` に追加し、`baselines/wr_*/metrics.json` を初回生成して commit。

**Tech Stack:** Fortran 90 (`wrregress.f90` 追加), Bash (既存 `run_tests.sh`), Python 3 標準ライブラリのみ, gfortran, 既存 `wr/wr` バイナリ。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` Phase L-0、`docs/superpowers/specs/2026-04-17-tr-refactoring-design.md` Phase 0 の WR 版。

---

## モジュール調査サマリ

| ファイル | 行数 | 責務 | L-0 で触る? |
|---|---|---|---|
| `wr/wrcomm.f90` | 138 | `MODULE wrcomm_parm` (入力) と `MODULE wrcomm` (`wr_allocate/deallocate` 含むラン状態) | 触らない |
| `wr/wrinit.f90` | 186 | デフォルト値の設定 (`WR_INIT`) | 触らない |
| `wr/wrparm.f90` | 187 | namelist `WR` の読み込み (`WR_PARM, WRNLIN, WR_CHEK`) | 触らない |
| `wr/wrmain.f90` | 63 | `PROGRAM wr` エントリポイント | 触らない |
| `wr/wrmenu.f90` | 87 | 対話メニュー（`R` で `wr_setup → wr_exec` を起動） | 触らない |
| `wr/wrsetup.f90`, `wrsetupr.f90`, `wrsetupb.f90` | 24/246/~150 | ray/beam の初期セットアップ | 触らない |
| `wr/wrexec.f90` | 38 | `wr_exec` ディスパッチ（`mode_beam` で ray/beam 振り分け、`nstat` を返す） | **1 行フック追加** |
| `wr/wrexecr.f90` | 999+ | `wr_exec_rays`, `wr_exec_single_ray`, `wr_calc_pwr`（dump 対象の `pwr_nrs/pwr_nrl/RAYS` を生成） | 触らない |
| `wr/wrexecb.f90` | ~750 | beam 計算 | 触らない |
| `wr/wrsub.f90`, `wrgout.f90`, `wrfile.f90`, `wrview.f90` | ~25k | dispersion/微分/グラフィクス/ファイル I/O | 触らない |
| `wr/Makefile` | 113 | `libwr.a` と `wr` バイナリのビルド | **1 行 SRCS 追加** |

**dump 対象として確定した量** (`wr_calc_pwr` 完了時点で値が入っている):
- 入力スカラー: `RF, RPI, ZPI, PHII, RNZI, RNPHII, RKR0, UUI, NRAYMAX, NSTPMAX, NRSMAX, NRLMAX, MDLWRI, MDLWRQ, mode_beam`
- 派生スカラー: `pos_pwrmax_rs, pwrmax_rs, pos_pwrmax_rl, pwrmax_rl`
- 配列 (per-ray): `NSTPMAX_NRAY(NRAY)`, `pos_pwrmax_rs_nray(NRAY)`, `pwrmax_rs_nray(NRAY)`, `pos_pwrmax_rl_nray(NRAY)`, `pwrmax_rl_nray(NRAY)`, 終端値 `RAYS(0:7, NSTPMAX_NRAY(NRAY), NRAY)`
- プロファイル: `pos_nrs(NRSMAX), pwr_nrs(NRSMAX)`、`pos_nrl(NRLMAX), pwr_nrl(NRLMAX)`

(これらは全て `wrcomm.f90` で宣言済み — Task 2 Step 2 で実機確認する)

**選定した 3 ケース** (`wr/in/test001.in` の構造を踏襲し、出力の `g`/`x`/`s` 等のメニュー選択を最小化):
- `wr_iter_lhcd` — ITER 規模・LH 周波数 (5 GHz 帯)・`MODELG=2`（解析モデル）・`NRAYMAX=2` の小規模 ray tracing。EQ 非依存。
- `wr_test001` — 既存 `wr/in/test001.in` を骨格にし、グラフィクスメニュー部分を削った短縮版（4 ray、`MODELG=5`、ITER 形状）。
- `wr_tst2_ec` — TST-2 サイズ・EC 周波数 (170 GHz)・`MODELG=2`・`NRAYMAX=1` の最短ケース。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `wr/wrregress.f90` | 新規 | 環境変数ガード付き高精度 dump（`1PE24.16` 書式）。`wr_regress_dump_if_enabled` 1 サブルーチン |
| `wr/wrexec.f90` | 修正 | `USE wrregress, ONLY: wr_regress_dump_if_enabled` を追加し、ray/beam 完了後 `RETURN` 直前に 1 行 CALL を挿入 |
| `wr/Makefile` | 修正 | `SRCS` に `wrregress.f90` を追加（`wrexec.f90` より前） |
| `test_run/inputs/wr_iter_lhcd.in` | 新規 | ITER LH ray tracing 入力（メニュー操作: `r`, `q`） |
| `test_run/inputs/wr_test001.in` | 新規 | `wr/in/test001.in` をグラフィクスなしで短縮した入力 |
| `test_run/inputs/wr_tst2_ec.in` | 新規 | TST-2 EC ray tracing 入力 |
| `test_run/scripts/extract_wr_metrics.py` | 新規 | `wr_regress.dat` から指標 JSON 抽出 |
| `test_run/scripts/check_regression_wr.sh` | 新規 | dump 抽出 + 比較ラッパ（既存の `compare_metrics.py` を流用、ただし WR 用は profile 形式が異なるため後述の generic mode を使う） |
| `test_run/scripts/compare_metrics.py` | 修正 | `--schema {tr,wr,generic}` フラグを足し、WR の profile（`pos_nrs/pwr_nrs/pos_nrl/pwr_nrl` のフラット配列）にも対応 |
| `test_run/scripts/tests/fixtures/sample_wr_regress.dat` | 新規 | `extract_wr_metrics.py` の単体テスト用最小サンプル |
| `test_run/scripts/tests/test_extract_wr_metrics.py` | 新規 | `extract_wr_metrics.py` の unittest |
| `test_run/baselines/wr_iter_lhcd/metrics.json` | 新規（生成） | ベースライン（commit 対象） |
| `test_run/baselines/wr_test001/metrics.json` | 新規（生成） | ベースライン |
| `test_run/baselines/wr_tst2_ec/metrics.json` | 新規（生成） | ベースライン |
| `test_run/test_definitions.conf` | 修正 | 3 つの `wr_*` ケースを追加 |
| `test_run/run_tests.sh` | 修正 | `wr` モジュールに `WR_REGRESS_DUMP=1` をエクスポートし、成功時に `check_regression_wr.sh` を呼ぶ。`get_binary` に `wr) echo "$TASK_DIR/wr/wr" ;;` を追加 |
| `test_run/README.md` | 修正 | WR 回帰判定セクションを追記 |

**方針:**
- WR 本体への追加は **`wrregress.f90` 1 ファイル + `wrexec.f90` への 2 行（USE と CALL）+ Makefile への 1 行** に限定。`WR_REGRESS_DUMP` 未設定時は完全に no-op。
- Python は標準ライブラリのみ。
- `compare_metrics.py` の generic スキーマ拡張は TR の既存挙動を完全保持する形で実装（`--schema tr` がデフォルト）。
- 単位番号は TR の `77` と衝突しないよう `78` を使用。

---

## Task 1: 作業用ブランチ作成とビルド確認

**Files:** なし（環境準備）

- [ ] **Step 1: 作業ディレクトリと git 状態を確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git status
git branch --show-current
git log --oneline -3
```
Expected: develop ベースのブランチ（または develop 直接）。HEAD は `c559e06e` 以降。

- [ ] **Step 2: Phase L-0 用ブランチを作る**

Run:
```bash
git checkout develop
git pull origin develop
git checkout -b feature/wr-library-L0-baseline
```
Expected: ブランチ切り替え成功。

- [ ] **Step 3: コンパイラ最適化フラグを確認**

Run:
```bash
grep -n "^OFLAGS\|^DFLAGS\|^FFLAGS" /home/k-yoshimi/program/task/make.header | head -10
grep -n "^FFLAGS" /home/k-yoshimi/program/task/wr/Makefile | head -5
```
Expected:
- `make.header` に `OFLAGS = -g -O3 -m64 -std=legacy` が有効。
- `wr/Makefile` は `FFLAGS = $(OFLAGS)` を使用（`$(DFLAGS)` ではない）。

- [ ] **Step 4: 依存ライブラリ + wr をビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/wr && make 2>&1 | tail -10
```
Expected: `../../bpsd`, `lib`, `mtxp`, `pl`, `eq`, `dp` が順に作られた後、`libwr.a` と `wr` バイナリが生成される。エラーなし。

- [ ] **Step 5: 既存テスト全件が通ることを確認（ベースライン記録）**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh
```
Expected: 既存の TR/EQ/TX テストが全て PASS。ここでの結果が L-0 完了後も維持されること。

- [ ] **Step 6: 空コミットでマーカー**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "chore(wr): start Phase L-0 regression test scaffolding"
```

---

## Task 2: dump 対象変数の存在確認と単位番号の選定

**Files:** 調査のみ

- [ ] **Step 1: dump 対象スカラーが `wrcomm.f90` に揃っていることを確認**

Run:
```bash
grep -nE "RF|RPI|ZPI|PHII|RNZI|RNPHII|RKR0|UUI|NRAYMAX|NSTPMAX|NRSMAX|NRLMAX|MDLWRI|MDLWRQ|mode_beam|pos_pwrmax_rs|pwrmax_rs|pos_pwrmax_rl|pwrmax_rl" /home/k-yoshimi/program/task/wr/wrcomm.f90
```
Expected: 上記すべてのシンボルが宣言されている（`wrcomm_parm` または `wrcomm`）。

もし一部が無ければ Task 3 Step 2 の dump コードからその行を削除する。

- [ ] **Step 2: dump 対象配列の宣言を確認**

Run:
```bash
grep -nE "NSTPMAX_NRAY|pos_pwrmax_rs_nray|pwrmax_rs_nray|pos_pwrmax_rl_nray|pwrmax_rl_nray|pos_nrs|pwr_nrs|pos_nrl|pwr_nrl|RAYS" /home/k-yoshimi/program/task/wr/wrcomm.f90
```
Expected: 全て ALLOCATABLE として宣言済み。

- [ ] **Step 3: 単位番号 78 が他で使われていないか確認**

Run:
```bash
grep -nE "UNIT[ ]*=[ ]*78|^[^!]*\b78\b" /home/k-yoshimi/program/task/wr/*.f90 | head -10
```
Expected: 78 をハードコードしている既存箇所がないこと。あれば 79 に切り替える。

- [ ] **Step 4: 戦略確定をコミット（plan 自体の更新がなければ skip）**

Run:
```bash
cd /home/k-yoshimi/program/task
git status
```

---

## Task 3: `wrregress.f90` を追加して高精度 dump を実装

**Files:**
- Create: `wr/wrregress.f90`
- Modify: `wr/wrexec.f90`
- Modify: `wr/Makefile`

- [ ] **Step 1: `wr/wrregress.f90` を新規作成**

Create `/home/k-yoshimi/program/task/wr/wrregress.f90`:
```fortran
! wrregress.f90
!
! High-precision regression dump for Phase L-0 regression tests.
! Emits wr_regress.dat (1PE24.16 format) when WR_REGRESS_DUMP=1.
! Otherwise does nothing; normal runs are unaffected.

MODULE wrregress

  PRIVATE
  PUBLIC :: wr_regress_dump_if_enabled

CONTAINS

  SUBROUTINE wr_regress_dump_if_enabled(nstat)
    USE wrcomm, ONLY: rkind, &
         RF, RPI, ZPI, PHII, RNZI, RNPHII, RKR0, UUI, &
         NRAYMAX, NSTPMAX, NRSMAX, NRLMAX, &
         MDLWRI, MDLWRQ, mode_beam, &
         NSTPMAX_NRAY, RAYS, &
         pos_nrs, pwr_nrs, pos_nrl, pwr_nrl, &
         pos_pwrmax_rs, pwrmax_rs, pos_pwrmax_rl, pwrmax_rl, &
         pos_pwrmax_rs_nray, pwrmax_rs_nray, &
         pos_pwrmax_rl_nray, pwrmax_rl_nray
    IMPLICIT NONE
    INTEGER, INTENT(IN) :: nstat
    INTEGER, PARAMETER :: UNIT_DUMP = 78
    CHARACTER(LEN=16) :: ENV_VAL
    INTEGER :: STAT, NRAY, NRS, NRL, NSTP_END, IOERR, I
    LOGICAL :: ENABLED

    CALL GET_ENVIRONMENT_VARIABLE('WR_REGRESS_DUMP', ENV_VAL, STATUS=STAT)
    ENABLED = (STAT == 0 .AND. TRIM(ENV_VAL) == '1')
    IF (.NOT. ENABLED) RETURN

    ! Dump only for ray tracing path (nstat==1). Beam path (nstat==2) is
    ! intentionally out of scope for L-0; will be re-evaluated in L-6.
    IF (nstat /= 1) RETURN

    OPEN(UNIT=UNIT_DUMP, FILE='wr_regress.dat', &
         STATUS='REPLACE', ACTION='WRITE', IOSTAT=IOERR)
    IF (IOERR /= 0) THEN
       WRITE(6,*) 'XX wrregress: cannot open wr_regress.dat, IOSTAT=', IOERR
       RETURN
    END IF

    WRITE(UNIT_DUMP, '(A)')          '# TASK/WR regression dump (format v1)'
    WRITE(UNIT_DUMP, '(A,I0)')       'NRAYMAX=', NRAYMAX
    WRITE(UNIT_DUMP, '(A,I0)')       'NSTPMAX=', NSTPMAX
    WRITE(UNIT_DUMP, '(A,I0)')       'NRSMAX=',  NRSMAX
    WRITE(UNIT_DUMP, '(A,I0)')       'NRLMAX=',  NRLMAX
    WRITE(UNIT_DUMP, '(A,I0)')       'MDLWRI=',  MDLWRI
    WRITE(UNIT_DUMP, '(A,I0)')       'MDLWRQ=',  MDLWRQ
    WRITE(UNIT_DUMP, '(A,I0)')       'mode_beam=', mode_beam
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'RF=',     RF
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'RPI=',    RPI
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'ZPI=',    ZPI
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'PHII=',   PHII
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'RNZI=',   RNZI
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'RNPHII=', RNPHII
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'RKR0=',   RKR0
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'UUI=',    UUI
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'pos_pwrmax_rs=', pos_pwrmax_rs
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'pwrmax_rs=',     pwrmax_rs
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'pos_pwrmax_rl=', pos_pwrmax_rl
    WRITE(UNIT_DUMP, '(A,1PE24.16)') 'pwrmax_rl=',     pwrmax_rl

    WRITE(UNIT_DUMP, '(A)') '# rays: NRAY NSTP_END pos_pwrmax_rs_nray pwrmax_rs_nray pos_pwrmax_rl_nray pwrmax_rl_nray RAYS(0:7,end)'
    DO NRAY = 1, NRAYMAX
       NSTP_END = NSTPMAX_NRAY(NRAY)
       WRITE(UNIT_DUMP, '(I5,1X,I7)', ADVANCE='NO') NRAY, NSTP_END
       WRITE(UNIT_DUMP, '(1X,1PE24.16)', ADVANCE='NO') pos_pwrmax_rs_nray(NRAY)
       WRITE(UNIT_DUMP, '(1X,1PE24.16)', ADVANCE='NO') pwrmax_rs_nray(NRAY)
       WRITE(UNIT_DUMP, '(1X,1PE24.16)', ADVANCE='NO') pos_pwrmax_rl_nray(NRAY)
       WRITE(UNIT_DUMP, '(1X,1PE24.16)', ADVANCE='NO') pwrmax_rl_nray(NRAY)
       DO I = 0, 7
          WRITE(UNIT_DUMP, '(1X,1PE24.16)', ADVANCE='NO') RAYS(I, NSTP_END, NRAY)
       END DO
       WRITE(UNIT_DUMP, '(A)') ''
    END DO

    WRITE(UNIT_DUMP, '(A)') '# minor radius profile: NRS pos_nrs pwr_nrs'
    DO NRS = 1, NRSMAX
       WRITE(UNIT_DUMP, '(I5,1X,1PE24.16,1X,1PE24.16)') NRS, pos_nrs(NRS), pwr_nrs(NRS)
    END DO

    WRITE(UNIT_DUMP, '(A)') '# major radius profile: NRL pos_nrl pwr_nrl'
    DO NRL = 1, NRLMAX
       WRITE(UNIT_DUMP, '(I5,1X,1PE24.16,1X,1PE24.16)') NRL, pos_nrl(NRL), pwr_nrl(NRL)
    END DO

    CLOSE(UNIT_DUMP)
  END SUBROUTINE wr_regress_dump_if_enabled

END MODULE wrregress
```

- [ ] **Step 2: `wr/Makefile` の SRCS に追加**

Modify `/home/k-yoshimi/program/task/wr/Makefile` line 37-42 (`SRCS = ...`).

Old:
```
SRCS = wrcomm.f90 wrinit.f90 wrparm.f90 wrview.f90 \
       wrsub.f90 \
       wrsetupr.f90 wrexecr.f90 wrsetupb.f90 wrexecb.f90 \
       wrsetup.f90 wrexec.f90 \
       wrgout.f90 wrfile.f90 \
       wrmenu.f90
```

New:
```
SRCS = wrcomm.f90 wrinit.f90 wrparm.f90 wrview.f90 \
       wrsub.f90 \
       wrsetupr.f90 wrexecr.f90 wrsetupb.f90 wrexecb.f90 \
       wrsetup.f90 wrregress.f90 wrexec.f90 \
       wrgout.f90 wrfile.f90 \
       wrmenu.f90
```

Also add a dependency line near the bottom (before `WRCOMM=...`):
```
$(OBJDIR)/wrregress.o: wrregress.f90 $(WRCOMM)
$(OBJDIR)/wrexec.o:wrexec.f90 $(WRCOMM) wrexecr.f90 wrexecb.f90 wrregress.f90
```
Replace the existing `$(OBJDIR)/wrexec.o:` line so the dep on `wrregress.f90` is recorded.

- [ ] **Step 3: `wr/wrexec.f90` を修正してフックを追加**

Modify `/home/k-yoshimi/program/task/wr/wrexec.f90`.

Old:
```fortran
  SUBROUTINE wr_exec(nstat,ierr)

    USE wrcomm
    USE dpprep
    USE wrexecr
    USE wrexecb
    IMPLICIT NONE
    INTEGER,INTENT(OUT):: nstat,ierr
```

New:
```fortran
  SUBROUTINE wr_exec(nstat,ierr)

    USE wrcomm
    USE dpprep
    USE wrexecr
    USE wrexecb
    USE wrregress, ONLY: wr_regress_dump_if_enabled
    IMPLICIT NONE
    INTEGER,INTENT(OUT):: nstat,ierr
```

And at the end of `wr_exec`, before `END SUBROUTINE wr_exec`:

Old:
```fortran
    IF(mode_beam.EQ.0) THEN
       CALL wr_exec_rays(ierr)
       nstat=1
    ELSE
       CALL wr_exec_beams(ierr)
       nstat=2
    END IF
  END SUBROUTINE wr_exec
```

New:
```fortran
    IF(mode_beam.EQ.0) THEN
       CALL wr_exec_rays(ierr)
       nstat=1
    ELSE
       CALL wr_exec_beams(ierr)
       nstat=2
    END IF
    CALL wr_regress_dump_if_enabled(nstat)   ! Phase L-0 regression dump (env-guarded)
  END SUBROUTINE wr_exec
```

- [ ] **Step 4: WR をリビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/wr && make 2>&1 | tail -10
```
Expected: `wrregress.f90` のコンパイル → `wrexec.f90` の再コンパイル → `wr` バイナリ更新。エラーなし。

- [ ] **Step 5: 通常実行で dump が作られないことを確認**

Run:
```bash
cd /tmp && rm -f wr_regress.dat
unset WR_REGRESS_DUMP
echo -e "0\nf\nq\n" | /home/k-yoshimi/program/task/wr/wr > /tmp/wr_smoke.log 2>&1
ls -la /tmp/wr_regress.dat 2>&1 | head -3
```
Expected: `wr_regress.dat` は存在しない。`wr_smoke.log` には起動メッセージが記録されている（メニューで `q` で終了）。

- [ ] **Step 6: 環境変数を立てて dump が出ることを確認（既存 test001 を流用）**

Run:
```bash
mkdir -p /tmp/wr_dump_test && cd /tmp/wr_dump_test
cp /home/k-yoshimi/program/task/wr/in/test001.in input.in
WR_REGRESS_DUMP=1 timeout 180 /home/k-yoshimi/program/task/wr/wr < input.in > out.log 2>&1
ls -la wr_regress.dat
head -25 wr_regress.dat
tail -5 wr_regress.dat
```
Expected:
- `wr_regress.dat` が存在する。
- 先頭行は `# TASK/WR regression dump (format v1)`。
- スカラー / per-ray / minor profile / major profile セクションが順に並んでいる。

注: `wr/in/test001.in` は EFIT データ参照や対話的グラフィクス選択を含むので、out.log でエラーがあっても dump 行が出ていれば OK（エラー終了の場合は Task 4 で `wr_iter_lhcd.in` を使う）。dump が出ない場合は `nstat /= 1` を疑い、`mode_beam=0` であることを確認。

- [ ] **Step 7: run-to-run で bit-exact 一致を確認**

Run:
```bash
cd /tmp/wr_dump_test
WR_REGRESS_DUMP=1 timeout 180 /home/k-yoshimi/program/task/wr/wr < input.in > /dev/null 2>&1
cp wr_regress.dat /tmp/wr_run1.dat
WR_REGRESS_DUMP=1 timeout 180 /home/k-yoshimi/program/task/wr/wr < input.in > /dev/null 2>&1
diff /tmp/wr_run1.dat wr_regress.dat
echo "diff exit=$?"
```
Expected: diff の出力が空、`exit=0`。

run-to-run で差が出る場合、許容誤差を `1e-8` まで緩める（Task 7 で最終確認）。

- [ ] **Step 8: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add wr/wrregress.f90 wr/wrexec.f90 wr/Makefile
git commit -m "feat(wr): add env-guarded high-precision dump for regression tests"
```

---

## Task 4: 3 つの WR 入力ケースを `test_run/inputs/` に追加

**Files:**
- Create: `test_run/inputs/wr_iter_lhcd.in`
- Create: `test_run/inputs/wr_test001.in`
- Create: `test_run/inputs/wr_tst2_ec.in`

WR の入力は「namelist 行 + メニュー操作」を混在させた stdin 形式（既存 `wr/in/test001.in` を参照）。
構造:
```
0          ← MENU? の最初の入力（"P,V,R,..." メニューでの選択前のダミー、wr/in/test001.in に倣う）
f          ← 続くコマンド (wr/in/test001 と同じ慣例)
gs/test001.gs   ← gs ファイル指定
c          ← namelist start
   <namelist body>
v          ← view
r          ← run (wr_setup → wr_exec → dump)
q          ← quit
```

ただし test001.in の冒頭は実は `0\nf\ngs/...\nc\n` ではなく `wr_menu` 起動時に読まれる行群。確実に動かすため、**最低限のメニュー操作 = `c`(namelist) + `r`(run) + `q`(quit) のみ** に絞る。

- [ ] **Step 1: `test_run/inputs/wr_iter_lhcd.in` を作成**

Create with content:
```
c
   modelg=2
   RR=6.2D0
   RA=2.0D0
   RKAP=1.7D0
   RDLT=0.33D0
   BB=5.3D0
   RIP=15.0D0
   NSMAX=2
   PA=2.0D0,1.0D0
   PZ=1.0D0,-1.0D0
   PN=1.0D0,1.0D0
   PNS=0.1D0,0.1D0
   PTPR=10.0D0,10.0D0
   PTPP=10.0D0,10.0D0
   PTS=0.5D0,0.5D0
   PROFN1=2.0D0
   PROFN2=2.0D0
   PROFT1=2.0D0
   PROFT2=1.0D0
   MODELP(1)=4,4
   NRAYMAX=2
   NSTPMAX=2000
   NRSMAX=50
   NRLMAX=100
   MDLWRI=101
   MDLWRQ=0
   MDLWRW=0
   SMAX=5.0D0
   DELS=0.05D0
   RFIN(1)=2*5.0D3
   RPIN(1)=2*8.0D0
   ZPIN(1)=2*0.0D0
   PHIIN(1)=2*0.0D0
   ANGZIN(1)=0.D0,0.D0
   ANGPHIN(1)=30.D0,40.D0
   UUIN(1)=2*1.D0
   MODEWIN(1)=2*1
r
q
```

注: ITER 規模の LH 周波数 (5 GHz) で 2 ray、`MODELG=2`（解析モデル、EQ 不要）。`MDLWRQ=0`（固定ステップ Runge-Kutta、最も単純）。

- [ ] **Step 2: `test_run/inputs/wr_test001.in` を作成**

Create with content (test001.in からグラフィクス操作 `g\n1\n2\n...` を削除したもの):
```
c
   modelg=2
   RR=6.2D0
   RA=2.0D0
   RKAP=1.7D0
   BB=5.3D0
   NSMAX=4
   PA(2)=2.D0,3.D0,4.D0
   PZ(2)=1.D0,1.D0,2.D0
   PN(1)=0.9D0,0.40D0,0.40D0,0.05D0
   PNS(1)=0.03D0,0.0133D0,0.0133D0,0.0017D0
   PTPR(1)=35.D0,35.D0,35.D0,35.D0
   PTPP(1)=35.D0,35.D0,35.D0,35.D0
   PTS(1)=1.D0,1.D0,1.D0,1.D0
   PROFN1=3.7D0
   PROFN2=2.7D0
   MODELP(1)=4,4,4,4
   MDLWRI=101
   MDLWRQ=0
   MDLWRW=0
   SMAX=5.D0
   DELS=0.01D0
   NRAYMAX=2
   NSTPMAX=2000
   NRSMAX=50
   NRLMAX=100
   RFIN(1)=2*160.D3
   RPIN(1)=2*8.5D0
   ZPIN(1)=2*0.0D0
   PHIIN(1)=2*0.0D0
   ANGZIN(1)=2*-30.D0
   ANGPHIN(1)=20.D0,30.D0
   UUIN(1)=2*1.D0
   MODEWIN(1)=2*1
r
q
```

注: 元の test001.in は EFIT データに依存していたが、ここでは EQ 非依存にするため `modelg=2`（解析）に変更し、`KNAMEQ` は使わない。これにより test_run 環境で確実に再現できる。

- [ ] **Step 3: `test_run/inputs/wr_tst2_ec.in` を作成**

Create with content:
```
c
   modelg=2
   RR=0.38D0
   RA=0.25D0
   RKAP=1.6D0
   RDLT=0.0D0
   BB=0.3D0
   RIP=0.2D0
   NSMAX=2
   PA=2.0D0,1.0D0
   PZ=1.0D0,-1.0D0
   PN=0.5D0,0.5D0
   PNS=0.05D0,0.05D0
   PTPR=0.5D0,0.5D0
   PTPP=0.5D0,0.5D0
   PTS=0.05D0,0.05D0
   PROFN1=2.0D0
   PROFN2=2.0D0
   MODELP(1)=4,4
   NRAYMAX=1
   NSTPMAX=1000
   NRSMAX=30
   NRLMAX=60
   MDLWRI=101
   MDLWRQ=0
   MDLWRW=0
   SMAX=2.0D0
   DELS=0.01D0
   RFIN(1)=8.2D3
   RPIN(1)=0.7D0
   ZPIN(1)=0.0D0
   PHIIN(1)=0.0D0
   ANGZIN(1)=0.D0
   ANGPHIN(1)=15.D0
   UUIN(1)=1.D0
   MODEWIN(1)=1
r
q
```

注: TST-2 サイズ・8.2 GHz EC・1 ray の最短ケース。

- [ ] **Step 4: 3 入力を手動実行して CLOSED が出ることを確認**

Run:
```bash
mkdir -p /tmp/wr_l0_check
for case in wr_iter_lhcd wr_test001 wr_tst2_ec; do
  workdir=/tmp/wr_l0_check/$case
  mkdir -p "$workdir" && cd "$workdir"
  WR_REGRESS_DUMP=1 timeout 180 /home/k-yoshimi/program/task/wr/wr \
    < /home/k-yoshimi/program/task/test_run/inputs/$case.in > out.log 2>&1
  echo "=== $case ==="
  grep -E "CLOSED|XX |error" out.log | head -5
  ls -la wr_regress.dat 2>&1 | head -1
done
```
Expected:
- 3 ケース全てで `CLOSED` が出力 (wr バイナリは終了時に GSCLOS の影響で CLOSED 行を吐く想定)。
- `wr_regress.dat` が各 workdir に生成されている。

もし CLOSED が出ない場合: WR は GSCLOS マーカーが TR と異なる可能性があるので、`run_tests.sh` での成功判定には Task 6 でカスタム判定を入れる。

- [ ] **Step 5: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/inputs/wr_iter_lhcd.in test_run/inputs/wr_test001.in test_run/inputs/wr_tst2_ec.in
git commit -m "test(wr): add 3 WR regression input cases (lhcd, test001, tst2_ec)"
```

---

## Task 5: 指標抽出スクリプト `extract_wr_metrics.py` を書く

**Files:**
- Create: `test_run/scripts/extract_wr_metrics.py`
- Create: `test_run/scripts/tests/fixtures/sample_wr_regress.dat`
- Create: `test_run/scripts/tests/test_extract_wr_metrics.py`

- [ ] **Step 1: サンプル fixture を作成**

Create `/home/k-yoshimi/program/task/test_run/scripts/tests/fixtures/sample_wr_regress.dat`:
```
# TASK/WR regression dump (format v1)
NRAYMAX=2
NSTPMAX=10
NRSMAX=2
NRLMAX=2
MDLWRI=101
MDLWRQ=0
mode_beam=0
RF=1.6000000000000000E+05
RPI=8.5000000000000000E+00
ZPI=0.0000000000000000E+00
PHII=0.0000000000000000E+00
RNZI=0.0000000000000000E+00
RNPHII=5.0000000000000000E-01
RKR0=-1.0000000000000000E+03
UUI=1.0000000000000000E+00
pos_pwrmax_rs=2.5000000000000000E-01
pwrmax_rs=1.2300000000000000E-01
pos_pwrmax_rl=8.0000000000000000E+00
pwrmax_rl=4.5600000000000000E-02
# rays: NRAY NSTP_END pos_pwrmax_rs_nray pwrmax_rs_nray pos_pwrmax_rl_nray pwrmax_rl_nray RAYS(0:7,end)
    1       8  2.5000000000000000E-01  6.0000000000000000E-02  8.0000000000000000E+00  2.0000000000000000E-02  4.0000000000000000E+00  6.0000000000000000E+00  0.0000000000000000E+00  0.0000000000000000E+00 -1.0000000000000000E+03  0.0000000000000000E+00  0.0000000000000000E+00  9.0000000000000000E-01
    2       9  2.5000000000000000E-01  6.3000000000000000E-02  8.0000000000000000E+00  2.5600000000000000E-02  4.5000000000000000E+00  6.5000000000000000E+00  0.0000000000000000E+00  0.0000000000000000E+00 -1.0000000000000000E+03  0.0000000000000000E+00  0.0000000000000000E+00  8.5000000000000000E-01
# minor radius profile: NRS pos_nrs pwr_nrs
    1  2.5000000000000000E-01  6.0000000000000000E-02
    2  7.5000000000000000E-01  3.0000000000000000E-02
# major radius profile: NRL pos_nrl pwr_nrl
    1  6.5000000000000000E+00  4.0000000000000000E-02
    2  8.5000000000000000E+00  2.0000000000000000E-02
```

- [ ] **Step 2: 失敗するテストを書く**

Create `/home/k-yoshimi/program/task/test_run/scripts/tests/test_extract_wr_metrics.py`:
```python
"""Unit tests for extract_wr_metrics.py."""
import json
import subprocess
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent.parent / "scripts" / "extract_wr_metrics.py"
FIXTURE = HERE / "fixtures" / "sample_wr_regress.dat"


class TestExtract(unittest.TestCase):
    def setUp(self):
        out = subprocess.run(
            ["python3", str(SCRIPT), str(FIXTURE)],
            capture_output=True, text=True, check=True,
        )
        self.data = json.loads(out.stdout)

    def test_dimensions(self):
        self.assertEqual(self.data["NRAYMAX"], 2)
        self.assertEqual(self.data["NSTPMAX"], 10)
        self.assertEqual(self.data["NRSMAX"], 2)
        self.assertEqual(self.data["NRLMAX"], 2)

    def test_scalars(self):
        s = self.data["scalars"]
        self.assertAlmostEqual(s["RF"], 1.6e5)
        self.assertAlmostEqual(s["RPI"], 8.5)
        self.assertAlmostEqual(s["pos_pwrmax_rs"], 0.25)
        self.assertAlmostEqual(s["pwrmax_rs"], 0.123)

    def test_rays(self):
        rays = self.data["rays"]
        self.assertEqual(len(rays), 2)
        self.assertEqual(rays[0]["NRAY"], 1)
        self.assertEqual(rays[0]["NSTP_END"], 8)
        self.assertEqual(len(rays[0]["RAYS_END"]), 8)

    def test_profile_rs(self):
        p = self.data["profile_rs"]
        self.assertEqual(len(p), 2)
        self.assertEqual(p[0]["NRS"], 1)
        self.assertAlmostEqual(p[1]["pos_nrs"], 0.75)
        self.assertAlmostEqual(p[1]["pwr_nrs"], 0.030)

    def test_profile_rl(self):
        p = self.data["profile_rl"]
        self.assertEqual(len(p), 2)
        self.assertEqual(p[1]["NRL"], 2)
        self.assertAlmostEqual(p[0]["pos_nrl"], 6.5)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: テストを走らせて失敗を確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run/scripts
python3 -m unittest tests.test_extract_wr_metrics -v
```
Expected: `extract_wr_metrics.py not found` でエラー。

- [ ] **Step 4: `extract_wr_metrics.py` を実装**

Create `/home/k-yoshimi/program/task/test_run/scripts/extract_wr_metrics.py`:
```python
#!/usr/bin/env python3
"""Convert wr_regress.dat into a JSON for regression comparison.

Output schema:
    NRAYMAX, NSTPMAX, NRSMAX, NRLMAX (ints),
    scalars (dict[str,float]),
    rays    (list[dict] one per ray with NRAY, NSTP_END, pos_pwrmax_rs_nray,
             pwrmax_rs_nray, pos_pwrmax_rl_nray, pwrmax_rl_nray, RAYS_END[8]),
    profile_rs (list[dict] one per minor-radius bin: NRS, pos_nrs, pwr_nrs),
    profile_rl (list[dict] one per major-radius bin: NRL, pos_nrl, pwr_nrl).
"""
import argparse
import json
import re
import sys
from pathlib import Path


INT_KEYS = {"NRAYMAX", "NSTPMAX", "NRSMAX", "NRLMAX", "MDLWRI", "MDLWRQ", "mode_beam"}
SCALAR_KEYS = {
    "RF", "RPI", "ZPI", "PHII", "RNZI", "RNPHII", "RKR0", "UUI",
    "pos_pwrmax_rs", "pwrmax_rs", "pos_pwrmax_rl", "pwrmax_rl",
}

RE_HDR_RAYS  = re.compile(r"^#\s*rays:")
RE_HDR_RS    = re.compile(r"^#\s*minor radius profile:")
RE_HDR_RL    = re.compile(r"^#\s*major radius profile:")


def parse(path: Path) -> dict:
    lines = path.read_text().splitlines()
    out = {"scalars": {}, "rays": [], "profile_rs": [], "profile_rl": []}
    section = "header"
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if RE_HDR_RAYS.match(line):
            section = "rays"
            continue
        if RE_HDR_RS.match(line):
            section = "profile_rs"
            continue
        if RE_HDR_RL.match(line):
            section = "profile_rl"
            continue
        if line.startswith("#"):
            continue
        if section == "header":
            if "=" not in line:
                continue
            key, val = (s.strip() for s in line.split("=", 1))
            if key in INT_KEYS:
                out[key] = int(val)
            elif key in SCALAR_KEYS:
                out["scalars"][key] = float(val)
        elif section == "rays":
            parts = line.split()
            if len(parts) < 14:
                raise SystemExit(f"malformed ray row: {raw}")
            out["rays"].append({
                "NRAY": int(parts[0]),
                "NSTP_END": int(parts[1]),
                "pos_pwrmax_rs_nray": float(parts[2]),
                "pwrmax_rs_nray": float(parts[3]),
                "pos_pwrmax_rl_nray": float(parts[4]),
                "pwrmax_rl_nray": float(parts[5]),
                "RAYS_END": [float(x) for x in parts[6:14]],
            })
        elif section == "profile_rs":
            parts = line.split()
            if len(parts) != 3:
                raise SystemExit(f"malformed minor profile row: {raw}")
            out["profile_rs"].append({
                "NRS": int(parts[0]),
                "pos_nrs": float(parts[1]),
                "pwr_nrs": float(parts[2]),
            })
        elif section == "profile_rl":
            parts = line.split()
            if len(parts) != 3:
                raise SystemExit(f"malformed major profile row: {raw}")
            out["profile_rl"].append({
                "NRL": int(parts[0]),
                "pos_nrl": float(parts[1]),
                "pwr_nrl": float(parts[2]),
            })
    for k in ("NRAYMAX", "NSTPMAX", "NRSMAX", "NRLMAX"):
        if k not in out:
            raise SystemExit(f"missing header field: {k}")
    if len(out["rays"]) != out["NRAYMAX"]:
        raise SystemExit(f"ray count {len(out['rays'])} != NRAYMAX {out['NRAYMAX']}")
    if len(out["profile_rs"]) != out["NRSMAX"]:
        raise SystemExit(
            f"profile_rs count {len(out['profile_rs'])} != NRSMAX {out['NRSMAX']}"
        )
    if len(out["profile_rl"]) != out["NRLMAX"]:
        raise SystemExit(
            f"profile_rl count {len(out['profile_rl'])} != NRLMAX {out['NRLMAX']}"
        )
    return out


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

Make it executable:
```bash
chmod +x /home/k-yoshimi/program/task/test_run/scripts/extract_wr_metrics.py
```

- [ ] **Step 5: テストを走らせて成功を確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run/scripts
python3 -m unittest tests.test_extract_wr_metrics -v
```
Expected: 5 tests OK。

- [ ] **Step 6: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/scripts/extract_wr_metrics.py \
        test_run/scripts/tests/fixtures/sample_wr_regress.dat \
        test_run/scripts/tests/test_extract_wr_metrics.py
git commit -m "test(wr): add extract_wr_metrics.py and unit tests"
```

---

## Task 6: 比較スクリプト `compare_metrics.py` を WR スキーマに対応

**Files:**
- Modify: `test_run/scripts/compare_metrics.py`

WR スキーマは TR と異なる（rays / profile_rs / profile_rl の 3 セクション）。互換性を保つため `--schema` フラグを追加する。

- [ ] **Step 1: 現状の `compare_metrics.py` を確認**

Run:
```bash
cat /home/k-yoshimi/program/task/test_run/scripts/compare_metrics.py
```
Expected: TR 用の `compare(baseline, actual, tol)` が実装されている (NT/NRMAX/NSMAX、scalars、profile)。

- [ ] **Step 2: `--schema {tr,wr}` 引数を追加し、WR 用比較関数を実装**

Modify `/home/k-yoshimi/program/task/test_run/scripts/compare_metrics.py`. Add the following at the end of the file (before `def main`):

```python
def _check_int(label: str, bv, av, out: list) -> None:
    if bv != av:
        out.append(f"{label}: baseline={bv} actual={av}")


def compare_wr(baseline: dict, actual: dict, tol: float) -> list:
    errors = []
    for k in ("NRAYMAX", "NSTPMAX", "NRSMAX", "NRLMAX"):
        _check_int(k, baseline.get(k), actual.get(k), errors)
    if errors:
        return errors

    b_scalars = baseline.get("scalars", {})
    a_scalars = actual.get("scalars", {})
    for k in sorted(set(b_scalars) | set(a_scalars)):
        if k not in b_scalars or k not in a_scalars:
            errors.append(f"scalars.{k}: missing")
            continue
        _check_scalar(f"scalars.{k}", float(b_scalars[k]), float(a_scalars[k]), tol, errors)

    b_rays = baseline.get("rays", [])
    a_rays = actual.get("rays", [])
    if len(b_rays) != len(a_rays):
        errors.append(f"rays length: baseline={len(b_rays)} actual={len(a_rays)}")
        return errors
    for i, (br, ar) in enumerate(zip(b_rays, a_rays)):
        _check_int(f"rays[{i}].NRAY", br.get("NRAY"), ar.get("NRAY"), errors)
        _check_int(f"rays[{i}].NSTP_END", br.get("NSTP_END"), ar.get("NSTP_END"), errors)
        for f in ("pos_pwrmax_rs_nray", "pwrmax_rs_nray",
                  "pos_pwrmax_rl_nray", "pwrmax_rl_nray"):
            _check_scalar(f"rays[{i}].{f}", float(br[f]), float(ar[f]), tol, errors)
        for j, (bv, av) in enumerate(zip(br.get("RAYS_END", []), ar.get("RAYS_END", []))):
            _check_scalar(f"rays[{i}].RAYS_END[{j}]", float(bv), float(av), tol, errors)

    for sect, key_int, fields in (
        ("profile_rs", "NRS", ("pos_nrs", "pwr_nrs")),
        ("profile_rl", "NRL", ("pos_nrl", "pwr_nrl")),
    ):
        b_prof = baseline.get(sect, [])
        a_prof = actual.get(sect, [])
        if len(b_prof) != len(a_prof):
            errors.append(f"{sect} length: baseline={len(b_prof)} actual={len(a_prof)}")
            continue
        for i, (br, ar) in enumerate(zip(b_prof, a_prof)):
            _check_int(f"{sect}[{i}].{key_int}", br.get(key_int), ar.get(key_int), errors)
            for f in fields:
                _check_scalar(f"{sect}[{i}].{f}", float(br[f]), float(ar[f]), tol, errors)
    return errors
```

And modify `main()` to accept `--schema`:

Old:
```python
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--actual", type=Path, required=True)
    ap.add_argument("--tolerance", type=float, default=1e-10)
    args = ap.parse_args()

    baseline = json.loads(args.baseline.read_text())
    actual   = json.loads(args.actual.read_text())
    errors = compare(baseline, actual, args.tolerance)
```

New:
```python
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--actual", type=Path, required=True)
    ap.add_argument("--tolerance", type=float, default=1e-10)
    ap.add_argument("--schema", choices=("tr", "wr"), default="tr")
    args = ap.parse_args()

    baseline = json.loads(args.baseline.read_text())
    actual   = json.loads(args.actual.read_text())
    if args.schema == "wr":
        errors = compare_wr(baseline, actual, args.tolerance)
    else:
        errors = compare(baseline, actual, args.tolerance)
```

- [ ] **Step 3: TR の既存テストを走らせて回帰なしを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run/scripts
python3 -m unittest discover tests -v
```
Expected: 既存 TR テスト + 新 WR テスト全件 OK。

- [ ] **Step 4: WR スキーマで自己一致を手動確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run/scripts
python3 extract_wr_metrics.py tests/fixtures/sample_wr_regress.dat > /tmp/wr_self.json
python3 compare_metrics.py --schema wr --baseline /tmp/wr_self.json --actual /tmp/wr_self.json
echo "exit=$?"
```
Expected: `OK: metrics match within tol=1e-10` / `exit=0`.

- [ ] **Step 5: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/scripts/compare_metrics.py
git commit -m "feat(test_run): add --schema wr to compare_metrics.py"
```

---

## Task 7: `check_regression_wr.sh` ラッパを追加

**Files:**
- Create: `test_run/scripts/check_regression_wr.sh`

- [ ] **Step 1: スクリプト作成**

Create `/home/k-yoshimi/program/task/test_run/scripts/check_regression_wr.sh`:
```bash
#!/bin/bash
#
# check_regression_wr.sh <test_name> <output_dir> <baselines_dir> [tolerance] [--generate-baseline]
#
# Reads <output_dir>/wr_regress.dat (produced when wr is run with
# WR_REGRESS_DUMP=1), extracts metrics to JSON, and compares with
# <baselines_dir>/<test_name>/metrics.json (schema=wr).
#
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_NAME="${1:?usage: $0 <test_name> <output_dir> <baselines_dir> [tol] [--generate-baseline]}"
OUTPUT_DIR="${2:?}"
BASELINES_DIR="${3:?}"
TOL="${4:-1e-10}"
MODE="${5:-compare}"

DUMP="$OUTPUT_DIR/wr_regress.dat"
METRICS_ACTUAL="$OUTPUT_DIR/metrics.json"
METRICS_BASE="$BASELINES_DIR/$TEST_NAME/metrics.json"

if [[ ! -f "$DUMP" ]]; then
    echo "check_regression_wr: dump not found: $DUMP" >&2
    echo "  did the test run with WR_REGRESS_DUMP=1 exported?" >&2
    exit 2
fi

if ! python3 "$SCRIPT_DIR/extract_wr_metrics.py" "$DUMP" > "$METRICS_ACTUAL"; then
    echo "check_regression_wr: failed to parse $DUMP" >&2
    exit 2
fi

if [[ "$MODE" == "--generate-baseline" ]]; then
    mkdir -p "$(dirname "$METRICS_BASE")"
    cp "$METRICS_ACTUAL" "$METRICS_BASE"
    echo "Baseline written: $METRICS_BASE"
    exit 0
fi

if [[ ! -f "$METRICS_BASE" ]]; then
    echo "check_regression_wr: baseline not found: $METRICS_BASE" >&2
    echo "  run with --generate-baseline to create it." >&2
    exit 3
fi

python3 "$SCRIPT_DIR/compare_metrics.py" \
    --schema wr \
    --baseline "$METRICS_BASE" \
    --actual "$METRICS_ACTUAL" \
    --tolerance "$TOL"
```

```bash
chmod +x /home/k-yoshimi/program/task/test_run/scripts/check_regression_wr.sh
```

- [ ] **Step 2: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/scripts/check_regression_wr.sh
git commit -m "feat(test_run): add check_regression_wr.sh wrapper"
```

---

## Task 8: `test_definitions.conf` と `run_tests.sh` を WR 対応に拡張

**Files:**
- Modify: `test_run/test_definitions.conf`
- Modify: `test_run/run_tests.sh`

- [ ] **Step 1: `test_definitions.conf` に 3 ケース追加**

Append to `/home/k-yoshimi/program/task/test_run/test_definitions.conf`:
```
# =============================================================================
# WR Module Tests (Wave Ray Tracing)
# =============================================================================
wr_iter_lhcd:wr:@inputs/wr_iter_lhcd.in:none:180:ITER LH ray tracing (analytic geom)
wr_test001:wr:@inputs/wr_test001.in:none:180:WR test001 short (analytic geom)
wr_tst2_ec:wr:@inputs/wr_tst2_ec.in:none:120:TST-2 EC ray tracing
```

- [ ] **Step 2: `run_tests.sh` の `get_binary` に wr を追加**

Modify `/home/k-yoshimi/program/task/test_run/run_tests.sh`.

Old (line ~107):
```bash
get_binary() {
    local module="$1"
    case "$module" in
        eq) echo "$TASK_DIR/eq/eq" ;;
        tr) echo "$TASK_DIR/tr/tr2" ;;
        fp) echo "$TASK_DIR/fp/fp" ;;
        tx) echo "$TASK_DIR/tx/tx2" ;;
        *) echo "" ;;
    esac
}
```

New:
```bash
get_binary() {
    local module="$1"
    case "$module" in
        eq) echo "$TASK_DIR/eq/eq" ;;
        tr) echo "$TASK_DIR/tr/tr2" ;;
        fp) echo "$TASK_DIR/fp/fp" ;;
        tx) echo "$TASK_DIR/tx/tx2" ;;
        wr) echo "$TASK_DIR/wr/wr" ;;
        *) echo "" ;;
    esac
}
```

- [ ] **Step 3: TR と同じ要領で WR 用の env と回帰チェックを `run_single_test` に組み込む**

Find the block (line ~297-301):
```bash
    # For TR module, enable regression dump (env-guarded inside trregress.f90).
    local tr_env=()
    if [[ "$module" == "tr" ]]; then
        tr_env=(env TR_REGRESS_DUMP=1)
    fi
```

Replace with:
```bash
    # For TR/WR modules, enable regression dump (env-guarded inside *regress.f90).
    local tr_env=()
    if [[ "$module" == "tr" ]]; then
        tr_env=(env TR_REGRESS_DUMP=1)
    elif [[ "$module" == "wr" ]]; then
        tr_env=(env WR_REGRESS_DUMP=1)
    fi
```

Then find the regression check block (line ~318-340):
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
```

Replace the `if [[ "$module" == "tr" ]]; then ... fi` block with:
```bash
        if [[ "$module" == "tr" ]]; then
            if ! "$SCRIPT_DIR/scripts/check_regression.sh" \
                    "$test_name" "$test_dir" "$SCRIPT_DIR/baselines" "1e-10" \
                    > "$test_dir/regression.log" 2>&1; then
                reg_ok=0
            fi
        elif [[ "$module" == "wr" ]]; then
            if ! "$SCRIPT_DIR/scripts/check_regression_wr.sh" \
                    "$test_name" "$test_dir" "$SCRIPT_DIR/baselines" "1e-10" \
                    > "$test_dir/regression.log" 2>&1; then
                reg_ok=0
            fi
        fi
```

- [ ] **Step 4: 一覧表示で WR ケースが出るか確認**

Run:
```bash
/home/k-yoshimi/program/task/test_run/run_tests.sh -l
```
Expected: 既存ケースに加え `wr_iter_lhcd`, `wr_test001`, `wr_tst2_ec` が listed。

- [ ] **Step 5: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/test_definitions.conf test_run/run_tests.sh
git commit -m "test(wr): wire WR cases into run_tests.sh with regression check"
```

---

## Task 9: ベースラインを生成して commit

**Files:**
- Create: `test_run/baselines/wr_iter_lhcd/metrics.json`
- Create: `test_run/baselines/wr_test001/metrics.json`
- Create: `test_run/baselines/wr_tst2_ec/metrics.json`

- [ ] **Step 1: 一度走らせて dump を生成**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh wr_iter_lhcd wr_test001 wr_tst2_ec 2>&1 | tail -30
```
Expected:
- 各ケースは `REGRESSION` で FAIL する（baseline がまだ無い→ exit 3）。
- `test_output/<case>/wr_regress.dat` が存在する。

- [ ] **Step 2: 各ケースのベースラインを生成**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
for case in wr_iter_lhcd wr_test001 wr_tst2_ec; do
  ./scripts/check_regression_wr.sh "$case" \
      "$(pwd)/test_output/$case" \
      "$(pwd)/baselines" \
      "1e-10" "--generate-baseline"
done
ls baselines/wr_*
```
Expected: 3 つの `baselines/wr_*/metrics.json` が作成される。

- [ ] **Step 3: 再実行して全て PASS することを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh wr_iter_lhcd wr_test001 wr_tst2_ec 2>&1 | tail -10
```
Expected: 3 ケースとも PASS。

- [ ] **Step 4: 全テスト走破で既存テストへの回帰がないことを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh
```
Expected: 全件 PASS。

- [ ] **Step 5: ベースラインを commit**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/baselines/wr_iter_lhcd/metrics.json \
        test_run/baselines/wr_test001/metrics.json \
        test_run/baselines/wr_tst2_ec/metrics.json
git commit -m "test(wr): commit initial regression baselines (lhcd, test001, tst2_ec)"
```

---

## Task 10: README 更新と最終確認

**Files:**
- Modify: `test_run/README.md`

- [ ] **Step 1: README に WR セクション追記**

Append to `/home/k-yoshimi/program/task/test_run/README.md` (after the existing TR section):

```markdown

## WR モジュールの回帰判定の仕組み

### 1. 高精度 dump

WR 本体 (`wr/wrregress.f90`) は、環境変数 `WR_REGRESS_DUMP=1` が設定されているときに限り、
`wr_exec` 完了時点の主要入力スカラー、ピーク吸収パワー、各 ray の終端値、
minor/major radius 方向の吸収パワープロファイルを `wr_regress.dat` に
`1PE24.16` 書式で書き出す。Beam tracing (`mode_beam/=0`) は L-0 では対象外。

通常実行（環境変数未設定）では dump は生成されず、挙動は完全に従来通り。

### 2. 比較フロー

1. `run_tests.sh` は WR モジュールに対して `WR_REGRESS_DUMP=1` をエクスポートして `wr/wr` を実行。
2. `CLOSED` で計算成功を判定。
3. 成功時、`scripts/check_regression_wr.sh` が `extract_wr_metrics.py` で JSON 化し、
   `compare_metrics.py --schema wr` で baselines と相対誤差 1e-10 比較。

### 3. dump に含まれる値

- スカラー: `RF, RPI, ZPI, PHII, RNZI, RNPHII, RKR0, UUI, pos_pwrmax_rs/rl, pwrmax_rs/rl`
- per-ray: `NSTP_END, pos_pwrmax_*_nray, pwrmax_*_nray, RAYS(0:7, end)`
- minor radius profile: `NRS, pos_nrs, pwr_nrs` (NRSMAX 行)
- major radius profile: `NRL, pos_nrl, pwr_nrl` (NRLMAX 行)

### 4. 登録済みケース

| TEST_NAME | 用途 |
|---|---|
| `wr_iter_lhcd` | ITER 規模・5 GHz LH・2 ray、`MODELG=2`（解析モデル） |
| `wr_test001`   | `wr/in/test001.in` 由来・160 GHz・2 ray、`MODELG=2` |
| `wr_tst2_ec`   | TST-2 規模・8.2 GHz EC・1 ray、`MODELG=2` |
```

- [ ] **Step 2: 最終的に全テストが green であることを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh 2>&1 | tail -15
```
Expected: TR, EQ, TX, WR を含む全件 PASS。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/README.md
git commit -m "docs(test_run): document WR regression workflow"
```

---

## 完了基準

- [ ] `wr/wrregress.f90` が追加され、`WR_REGRESS_DUMP=1` のときだけ `wr_regress.dat` を出力する
- [ ] 通常実行（env 未設定）で `wr/wr` の挙動が完全に従来通り
- [ ] `test_run/inputs/wr_*.in` 3 ケースが追加されている
- [ ] `test_run/scripts/extract_wr_metrics.py` と `check_regression_wr.sh` が機能する
- [ ] `compare_metrics.py --schema wr` が正しく WR の rays / profile_rs / profile_rl を比較する
- [ ] `test_run/baselines/wr_*/metrics.json` が 3 ファイル commit されている
- [ ] `run_tests.sh` で WR 3 ケースが全て PASS する
- [ ] `run_tests.sh` の既存 TR/EQ/TX ケースが全て PASS する（回帰なし）

## 撤退条件

- run-to-run で 1e-10 を超える差が出る場合 → 許容誤差を `1e-8` に緩める（`run_tests.sh` の `check_regression_wr.sh` 呼び出し行を編集）
- WR が `CLOSED` を出さない場合 → `run_tests.sh` の成功判定に `# DATA WAS SUCCESSFULLY` 等の WR 固有マーカーを追加判定
- 3 ケース中 EQ 依存ケースが必要になった場合 → `wr_iter_efit:wr:@inputs/wr_iter_efit.in:eq_iter01:240` のように depends を付けて追加（既存テストとの整合性は L-1 で再評価）

## 依存

- 前提: develop ブランチが `c559e06e` 以降であること（TR Phase 0 と Phase L 設計が merge 済み）
- 後続: L-1 (Graphics 分離) の前提となる
