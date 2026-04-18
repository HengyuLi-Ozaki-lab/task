# TASK/TR ライブラリ化（Phase L）設計書

**日付**: 2026-04-17
**対象**: `tr/` モジュール + 新規 `python/trlib/`
**ブランチ**: 未作成（Phase 2 完了後に `feature/tr-library-phase-l-*` として作成予定）
**前提**: Phase 0 完了、Phase 1 と Phase 2 の完了

## 1. 目的と前提

### 1.1 目的
- TR コードをファイル I/O / subprocess 経由ではなく **in-process ライブラリ** として Python から呼べるようにする
- 網羅計算（パラメータスイープ）やパラメータ制御ループを高効率に実行できる環境を整備する
- 既存の `tr2` 実行バイナリは従来通り温存する

### 1.2 スコープ
- Fortran 側: C ABI (`bind(c)`) を提供する `tr_api.f90` を新設
- Python 側: `ctypes` ベースのラッパ `python/trlib/` を新設
- ビルド: `libtrapi.so` を追加ターゲットとして生成
- テスト: 4 層（等価性 / C ABI / Python ラッパ / 網羅計算 smoke）

### 1.3 非目標
- MPI 対応（シングルプロセス前提）
- 複数 TR インスタンスの同時並行実行（グローバル状態のため 1 プロセス 1 インスタンス）
- EQ モジュール自体のライブラリ化（別 Phase で扱う）
- 物理モデルの変更

### 1.4 制約
- 既存の `tr2` バイナリの数値結果は Phase 0 で確立した許容誤差 `1e-10` 以内で維持する
- 既存開発者の既存 namelist 入力（`tr/in/*.in`）はそのまま使える形を保つ
- TRCOMM のグローバル state は（現段階では）そのまま受け入れる。純粋関数化は別 Phase

## 2. 背景と動機

### 2.1 なぜライブラリ化か
- **網羅計算の性能**: 数千〜数万のパラメータ組に対し、プロセス起動コスト（~50ms × 10,000 = 500 秒）とファイル I/O が累積する
- **パラメータ制御ループ**: 途中でパラメータを書き換えて再実行する実験的用途。ファイル駆動では煩雑
- **Python エコシステム**: scipy, optuna, numpy, matplotlib 等との連携が容易になる
- **標準的なパターン**: IMAS/OMFIT/OMAS 等の既存フレームワークに近い形

### 2.2 なぜ L3 (in-process library) なのか

設計時に以下のレベルを検討:

| Level | 方式 | 工数 | 採否 |
|---|---|---|---|
| L0 | 現状維持 | - | ユーザ要件を満たさず |
| L1 | スクリプトラッパ（file I/O） | 1-2 週 | **却下**: ファイル駆動は避けたい（網羅計算で重い） |
| L2 | ファイル駆動イテレーション | 2-4 週 | **却下**: 同上 |
| L3 | in-process ライブラリ | 2-3 ヶ月 | **採用**: メモリやり取り、低オーバーヘッド |
| L4 | 真のライブラリ API（state object、thread safety） | 6 ヶ月+ | 非スコープ: 過剰 |

### 2.3 なぜ Phase 1-2 の後に実施するのか（Sequencing Option b）

| 選択肢 | 採否 | 理由 |
|---|---|---|
| a. ライブラリ化を先行（Phase 1 の前） | 却下 | 巨大な TRCOMM のままでは `tr_set_param` のテーブル管理が醜くなる |
| **b. Phase 1-2 の後に実施** | **採用** | Phase 2 (TRCOMM submodule 分割) 完了後ならクリーンに設計できる、マージ競合なし |
| c. Phase 1-2 と並行 | 却下 | `trcomm.f90` への同時変更が衝突しやすい |

## 3. 全体アーキテクチャ

```
                        [Python]
                           │
                           │ import trlib
                           ▼
                 ┌─────────────────────┐
                 │  trlib (Python)     │   ← Python ラッパ (ctypes)
                 │  - Trlib class      │
                 │  - tr_init/run/...  │
                 └─────────┬───────────┘
                           │ ctypes FFI
                           ▼
                 ┌─────────────────────┐
                 │  libtrapi.so        │
                 │  ┌─────────────────┐│
                 │  │ tr_api.f90      ││  ← C ABI wrapper (new)
                 │  │  bind(c) 5 fns  ││
                 │  └────────┬────────┘│
                 │           │          │
                 │  ┌────────▼────────┐│
                 │  │ libtr2.a 部品   ││  ← 既存計算コード (共有)
                 │  │  (graphics 除外) ││     trexec, trcalc, trcoef, ...
                 │  └─────────────────┘│
                 └─────────────────────┘

                 ┌─────────────────────┐
                 │  tr2 (既存バイナリ)  │   ← 既存のまま温存
                 │  trmain + libtr2.a  │
                 │  + graphics         │
                 └─────────────────────┘
```

**構成要素の役割:**

| ユニット | 責務 | 依存 |
|---|---|---|
| `tr/tr_api.f90` | C ABI 5 関数を提供 | `tr_param_registry`, TRCOMM, `trloop` |
| `tr/tr_param_registry.f90` | パラメータ名 → TRCOMM 変数の setter テーブル | TRCOMM |
| `tr/tr_state.f90` | `tr_state_c` 構造体（C 互換）定義 | ISO_C_BINDING, TRCOMM |
| `tr/tr_api.h` | C ヘッダ | - |
| `tr/libtrapi.so` | Shared library（graphics 除外、PIC ビルド） | libeq, libpl, libmds, bpsd 等（PIC） |
| `python/trlib/_ffi.py` | ctypes 低レベル FFI | libtrapi.so |
| `python/trlib/trlib.py` | Trlib クラス（高レベル API） | `_ffi` |
| `python/trlib/state.py` | TrState dataclass（tr_state_c → Python dict） | - |
| `python/trlib/errors.py` | TrlibError など例外階層 | - |

## 4. C ABI シグネチャ

### 4.1 Fortran 側 (`tr/tr_api.f90`)

```fortran
MODULE tr_api
  USE, INTRINSIC :: ISO_C_BINDING
  USE tr_state, ONLY: tr_state_c
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: tr_init, tr_run, tr_get_state, tr_set_param, tr_finalize

CONTAINS

  FUNCTION tr_init() RESULT(ierr) BIND(C, NAME="tr_init")
    INTEGER(C_INT) :: ierr
    ! ALLOCATE_TRCOMM + 初期プロファイル生成（既存 tr_init サブルーチンを呼ぶ）

  FUNCTION tr_run(ntmax) RESULT(ierr) BIND(C, NAME="tr_run")
    INTEGER(C_INT), VALUE, INTENT(IN) :: ntmax
    INTEGER(C_INT) :: ierr
    ! NTMAX ステップの時間発展（既存 tr_loop を呼び出し）

  FUNCTION tr_set_param(name, value) RESULT(ierr) BIND(C, NAME="tr_set_param")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    ! tr_param_registry を参照して TRCOMM 変数に書き込み

  FUNCTION tr_get_state(state) RESULT(ierr) BIND(C, NAME="tr_get_state")
    TYPE(tr_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    ! TRCOMM の現在値を tr_state_c 構造体にコピー

  FUNCTION tr_finalize() RESULT(ierr) BIND(C, NAME="tr_finalize")
    INTEGER(C_INT) :: ierr
    ! DEALLOCATE_TRCOMM

END MODULE tr_api
```

### 4.2 C ヘッダ (`tr/tr_api.h`)

```c
#ifndef TR_API_H
#define TR_API_H

/* Upper bounds for fixed-size state struct.
 * Actual runtime NRMAX/NSMAX are in state.nrmax/state.nsmax and must be <= these.
 * TR_MAX_NSMAX follows trcom0.f90: NSTM=8 (max total species incl. impurities/neutrals).
 * TR_MAX_NRMAX is a generous upper bound; typical inputs use NRMAX=50-100.
 */
#define TR_MAX_NRMAX 500
#define TR_MAX_NSMAX 8

typedef struct {
    int nt, nrmax, nsmax;
    double T, WPT, AJT, Q0, BETA0, BETAP0, BETAA, BETAN;
    double TAUE1, TAUE2, ZEFF0, ALI, RQ1;
    double RN[TR_MAX_NRMAX][TR_MAX_NSMAX];
    double RT[TR_MAX_NRMAX][TR_MAX_NSMAX];
    double AJ[TR_MAX_NRMAX];
    double QP[TR_MAX_NRMAX];
} tr_state_t;

int tr_init(void);
int tr_run(int ntmax);
int tr_set_param(const char* name, double value);
int tr_get_state(tr_state_t* state);
int tr_finalize(void);

#endif
```

**注意:** 固定サイズ配列は扱いやすさ優先。メモリ占有は RN+RT で `2 × 500 × 8 × 8 = 64 KB`、AJ+QP で `2 × 500 × 8 = 8 KB` 程度。将来 NRMAX 上限超過が必要になった場合は動的サイズ getter (`tr_get_profile(name, buf, size)`) に移行可能。

### 4.3 設計決定の根拠

| 項目 | 決定 | 根拠 |
|---|---|---|
| 関数数 | 5 つに統一 | 一括実行・ステップ介入・網羅計算の 3 パターン全てカバー可能 |
| パラメータ型 | `double` 統一 | 整数も `INT(value)` で受ける。API を単純化 |
| 文字列パラメータ | 別 API `tr_set_string_param` を後で追加 | 初期スコープから除外、KNAMEQ 等は実装段階で追加判断 |
| `tr_state_t` | 固定サイズ配列 | TR の NRMAX は最大 200 以下、NSMAX は最大 10 以下に収まる。動的サイズ getter は後で必要なら追加 |
| エラーコード | 0=OK, 1=invalid param, 2=not initialized, 3=calculation failed | 標準的な非零エラー方式 |

## 5. パラメータテーブル機構

### 5.1 採用方式: 手書きテーブル

```fortran
MODULE tr_param_registry
  USE trcomm, ONLY: rkind, RR, RA, BB, NSMAX, PN, PNS, PT, PTS, DT, NTMAX, &
                    EPSLTR, LMAXTR, MDLKAI, MDLETA, MDLAD, ...
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: tr_param_set

CONTAINS

  FUNCTION tr_param_set(name, value) RESULT(ierr)
    CHARACTER(LEN=*), INTENT(IN) :: name
    REAL(rkind), INTENT(IN) :: value
    INTEGER :: ierr
    INTEGER :: idx
    CHARACTER(LEN=32) :: base_name

    ierr = 0
    CALL parse_array_subscript(name, base_name, idx)

    SELECT CASE (TRIM(base_name))
    ! --- scalar reals ---
    CASE ("RR");    RR = value
    CASE ("RA");    RA = value
    CASE ("BB");    BB = value
    CASE ("DT");    DT = value
    CASE ("EPSLTR"); EPSLTR = value
    ! --- scalar integers ---
    CASE ("NSMAX");  NSMAX  = INT(value)
    CASE ("NTMAX");  NTMAX  = INT(value)
    CASE ("LMAXTR"); LMAXTR = INT(value)
    CASE ("MDLKAI"); MDLKAI = INT(value)
    ! --- array reals (indexed) ---
    CASE ("PN");   PN(idx)  = value
    CASE ("PNS");  PNS(idx) = value
    CASE ("PT");   PT(idx)  = value
    CASE ("PTS");  PTS(idx) = value
    ! ... 続く
    CASE DEFAULT;  ierr = 1
    END SELECT
  END FUNCTION tr_param_set

  SUBROUTINE parse_array_subscript(full_name, base, idx)
    ! "PN[1]" → base="PN", idx=1
    ! "RR"    → base="RR", idx=0
    CHARACTER(LEN=*), INTENT(IN) :: full_name
    CHARACTER(LEN=*), INTENT(OUT) :: base
    INTEGER, INTENT(OUT) :: idx
    ! ...
  END SUBROUTINE

END MODULE tr_param_registry
```

### 5.2 配列パラメータの記法

Python 側:
```python
trlib.tr_set_param("PN[1]", 0.7)   # PN(1)
trlib.tr_set_param("PN[2]", 0.3)
```

インデックスは Fortran 側の 1-origin で統一。

### 5.3 パラメータ一覧（初期セット）

既存の `trparm.f90` namelist と `trcomm.f90` の ALLOCATABLE 配列を精査し、L-3 で以下のセットを登録する（実装時に最終確定）:

- 幾何: `RR, RA, RKAP, RDLT, BB, PHIA`
- プラズマ: `NSMAX, PA[], PZ[], PN[], PNS[], PT[], PTS[]`
- 電流: `RIPS, RIPE, RIPSS`
- 時間発展: `DT, NTMAX, NTSTEP, EPSLTR, LMAXTR`
- 輸送モデル: `MDLKAI, MDLETA, MDLAD, MDLAVK, CDW[], CHP, CK0, CK1`
- ソース: `PNBTOT, PECTOT, PLHTOT, PICTOT, PELTOT, PSCTOT[]`
- モデルスイッチ: `MDLNB, MDLEC, MDLLH, MDLIC, MDLPEL, MDLJBS, MDLST, MDLNF, MDLUF, ...`

**パラメータ追加時のメンテ:** `tr_param_registry.f90` の `SELECT CASE` に 1 行追加するだけ。

## 6. Python ラッパ設計

### 6.1 ファイル構成

```
python/trlib/
├── __init__.py         # from .trlib import Trlib, TrlibError
├── _ffi.py             # ctypes 低レベル FFI
├── trlib.py            # Trlib class
├── state.py            # TrState dataclass
├── errors.py           # TrlibError 例外階層
└── tests/
    ├── __init__.py
    ├── test_ffi.py           # Layer 3
    ├── test_equivalence.py   # Layer 1
    ├── test_sweep.py         # Layer 4
    └── fixtures/             # ITER01_PARAMS 等のパラメータ辞書
```

### 6.2 2 層構成の理由

下層 `_ffi.py`（ctypes 直呼び）と上層 `trlib.py`（高レベル class）を分離。理由:
- 将来 ctypes → cffi や別 FFI に切り替える際に影響範囲が `_ffi.py` だけに収まる
- テストで下層だけ直接叩きたいケース（Layer 3）に対応
- 高レベル class は Pythonic な使い勝手（context manager, 例外, 辞書一括セット）を提供

### 6.3 主要クラス

```python
class Trlib:
    def __init__(self): ...                    # tr_init 呼び出し
    def set_param(self, name: str, value: float): ...
    def set_params(self, **kwargs): ...        # 辞書一括
    def run(self, ntmax: int): ...
    def get_state(self) -> TrState: ...
    def close(self): ...                       # tr_finalize 呼び出し
    def __enter__(self): ...
    def __exit__(self, *a): ...
```

### 6.4 使用例

```python
from trlib import Trlib

# パターン 1: 網羅計算
import numpy as np
results = []
for rr, bb in np.ndindex(100, 100):
    with Trlib() as tr:
        tr.set_params(**base_params, RR=rr, BB=bb)
        tr.run(ntmax=100)
        results.append(tr.get_state())

# パターン 2: ステップ介入
with Trlib() as tr:
    tr.set_params(**base_params)
    for i in range(100):
        tr.run(ntmax=1)
        if tr.get_state().Q0 < 1.0:
            tr.set_param("DT", tr.get_state().T / 10)  # DT を動的調整
```

## 7. ビルドシステム

### 7.1 新規ビルドターゲット

`tr/Makefile`:

```makefile
# 既存
SRCS_CORE = trinit.f90 trparm.f90 trview.f90 trmetric.f90 trprof.f90 \
            trprep.f90 trufsub.f90 tr_ufile_task.f90 tr_ufile_topics.f90 \
            trufile.f90 trfile.f90 trhelp.f90 trexec.f90 trcalc.f90 \
            tradat.f90 trcdbm.f90 trmodels.f90 trcoef.f90 tritg.f90 \
            trrslt.f90 trpnb.f90 trprf.f90 trpnf.f90 trpel.f90 trpsc.f90 \
            trmdlt.f90 trfout.f90 trregress.f90 trloop.f90

SRCS_GRAPHICS = trgout.f90 trgrar.f90 trgrat.f90 trgrap.f90 trgrae.f90 \
                trgrad.f90 trgram.f90 trgsub.f90 trg2d.f90

SRCS_MENU = trmenu.f90

SRCS_API = tr_state.f90 tr_param_registry.f90 tr_api.f90

SRCS = $(SRCM) $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)
SRCS_LIB = $(SRCM) $(SRCS_CORE) $(SRCS_API)

# 既存 tr2 ターゲット（従来通り）
tr2: $(OBJ_ALL)
	$(FC) ... -o tr2

# 新規 libtrapi.so ターゲット
libtrapi.so: $(OBJ_LIB_PIC)
	$(FC) -shared -fPIC $(OBJ_LIB_PIC) \
	    ../eq/libeq.a ../pl/libpl_pic.a ../lib/libmds_pic.a ../lib/libtask_pic.a \
	    ../../bpsd/libbpsd_pic.a \
	    $(LIB_MTX_PIC) ... \
	    -o libtrapi.so

# PIC 用ビルドルール
$(OBJDIR)/lib/%.o: %.f90
	$(FCFREE) $(FFLAGS) -fPIC -c $< -o $@ -Jmod_pic -I./mod_pic -I../pl/mod_pic ...
```

### 7.2 依存ライブラリの PIC 対応

`eq/Makefile`, `pl/Makefile`, `lib/Makefile`, `mtxp/Makefile`, `../bpsd/Makefile` に以下のターゲットを追加:

```makefile
libeq_pic.a: $(OBJ_EQ_PIC)
	$(AR) rcs libeq_pic.a $(OBJ_EQ_PIC)

$(OBJDIR)/pic/%.o: %.f
	$(FCFIXED) $(FFLAGS) -fPIC -c $< -o $@ -Jmod_pic -I./mod_pic
```

（各ライブラリの Makefile に 5-10 行追加）

### 7.3 インストール位置

- `libtrapi.so` は `tr/` ディレクトリに生成（既存 `tr2` と同じ場所）
- Python ラッパは `TRLIB_PATH` 環境変数でパスを指定可能（デフォルトは `tr/libtrapi.so` を相対参照）

### 7.4 PIC ビルド失敗時のフォールバック

| 試行 | 条件 | フォールバック先 |
|---|---|---|
| PIC rebuild (案 a) | 一部コンパイラで動かない | b or c |
| `-Wl,--whole-archive` (案 c) | 古い gfortran でリンク失敗 | b |
| 直接ソース統合 (案 b) | - | - |

L-4 で検証し、a が機能すれば採用。

## 8. テスト戦略（4 層）

### 8.1 Layer 1: 等価性テスト

**目的:** ライブラリ経由の出力が既存 `tr2` バイナリと同一数値になること

- 実装: `python/trlib/tests/test_equivalence.py`
- 比較対象: Phase 0 の `test_run/baselines/tr_iter01/metrics.json` 等
- 許容誤差: `1e-10`（Phase 0 と同じ）
- 対象ケース: `tr_iter01`, `tr_m0904`, `tr_tst2`
- namelist パーサ: Python 側で `f90nml` ライブラリ、または既存の trparm を C ABI 経由で呼ぶ（L-6 で最終決定）

### 8.2 Layer 2: C ABI 単体テスト

**目的:** 5 つの C 関数が個別に正しく動作すること

- 実装: `tr/tests/c_abi/test_abi.c` + `Makefile`
- 軽量な main.c で assert ベースの検証
- init/finalize サイクル、invalid param 戻り値、state 構造体の正当性

### 8.3 Layer 3: Python ラッパテスト

**目的:** `Trlib` class のインターフェースが Pythonic に使えること

- 実装: `python/trlib/tests/test_ffi.py` (stdlib unittest)
- context manager、辞書一括セット、配列パラメータ記法 `PN[1]`、無効パラメータで例外、run の累積挙動

### 8.4 Layer 4: 網羅計算 smoke test

**目的:** パラメータスイープのユースケースが破綻なく回ること

- 実装: `python/trlib/tests/test_sweep.py`
- 小規模 3x3 グリッドで完走を確認
- 物理的妥当性は検証対象外（設計範疇外）

### 8.5 CI 統合

`test_run/test_definitions.conf` に新ケース追加:

```
trlib_equivalence:trlib:python -m unittest python.trlib.tests.test_equivalence:none:300:Library equivalence test
trlib_ffi:trlib:python -m unittest python.trlib.tests.test_ffi:none:60:Python wrapper test
trlib_sweep:trlib:python -m unittest python.trlib.tests.test_sweep:none:120:Parameter sweep smoke test
trlib_c_abi:trlib:tr/tests/c_abi/test_abi:none:60:C ABI unit test
```

`run_tests.sh` に「python 実行モード」「C 実行モード」対応を追加（現在は Fortran バイナリ前提）。

## 9. Phase L サブフェーズ計画

各サブは単独の PR とし、develop に直接マージ（stack せず）。

| サブ | 内容 | 成果物 | 所要 | 依存 |
|---|---|---|---|---|
| L-0 | ベースライン確認 | Phase 2 完了後、回帰テスト全 PASS を確認 | 数日 | Phase 2 完了 |
| L-1 | Graphics 分離 | `SRCS_GRAPHICS`/`SRCS_CORE`/`SRCS_MENU` 分離。既存 `tr2` は変わらず動作 | 1 週 | L-0 |
| L-2 | C ABI foundation | `tr_state.f90`、`tr_api.f90` (stub)、`tr_api.h` | 1 週 | L-1 |
| L-3 | Parameter registry | `tr_param_registry.f90` に namelist 変数の setter 登録 | 1〜2 週 | L-2 |
| L-4 | libtrapi.so ビルド | Makefile 改修、依存の PIC 対応、shared library 生成 | 1 週 | L-3 |
| L-5 | Python ラッパ | `python/trlib/` 全ファイル | 1 週 | L-4 |
| L-6 | テスト 4 層 | Layer 1/2/3/4 の実装 | 1〜2 週 | L-5 |
| L-7 | ドキュメント | `python/trlib/README.md`, 使用例 notebook | 数日 | L-6 |

**合計目安: 6〜9 週**

**撤退条件:**
- L-4 PIC リビルド困難 → フォールバック案を本設計書 7.4 に従って切り替え
- L-3 のパラメータ数が想定を大幅超過 → 最小セット (10〜15 個) で L-5/L-6 まで回す

## 10. リスクと緩和策

| リスク | 深刻度 | 緩和策 |
|---|---|---|
| PIC リビルドで依存ライブラリが動かない | 中 | 段階的検証、フォールバック策あり（7.4 節） |
| Python numpy と C double の ABI 不一致 | 低 | Linux x86_64 で動作を前提、他 OS は後回し |
| TRCOMM state の init/finalize サイクル不正 | 高 | L-3 で完全リセット保証、Layer 1 等価性テストで検知 |
| namelist パーサ不整合 | 中 | `f90nml` 採用 or 既存 trparm 経由。L-6 で最終決定 |
| `libtrapi.so` のシンボル衝突 | 中 | `ldd`/`nm` でチェック、公開シンボルを `tr_*` 限定 |
| GIL ボトルネック | 低 | 並列化は `multiprocessing` で対応 |
| Fortran allocatable モジュール変数の shared lib 挙動 | 中 | gfortran は対応済み。他コンパイラは L-4 で検証 |
| 既存 `tr2` バイナリの数値が変わる | 高 | Phase 0 回帰テストで即検知、revert |
| グローバル状態により並列呼び出し不可 | 低 | 既知の制限として明文化、multiprocessing 推奨 |

## 11. 未確定事項

以下はサブ Phase 実装時に確定する:

- 登録する namelist パラメータの最終リスト（L-3）
- Layer 1 の namelist パーサ実装方針（`f90nml` or 既存 trparm 経由、L-6）
- PIC リビルドが全コンパイラで動くかの確認（L-4）
- Layer 4 の smoke test で使う基準 params セット（L-6）

## 12. 成果物と受け入れ基準

### 12.1 成果物

- `docs/superpowers/specs/2026-04-17-tr-library-design.md`（本書）
- `docs/superpowers/plans/2026-04-17-tr-library-phase-l-*.md`（writing-plans で作成、L-x ごと）
- 新規 Fortran ファイル: `tr/tr_state.f90`, `tr/tr_param_registry.f90`, `tr/tr_api.f90`, `tr/tr_api.h`
- 新規 Python パッケージ: `python/trlib/`
- 新規テスト: `tr/tests/c_abi/`, `python/trlib/tests/`
- 各 L-x の PR

### 12.2 受け入れ基準（Phase L 全体完了時）

- [ ] `libtrapi.so` が生成される
- [ ] `python -m trlib` 相当で `Trlib` クラスが import できる
- [ ] Layer 1 等価性テスト 3 ケース全て PASS（許容誤差 `1e-10`）
- [ ] Layer 2 C ABI 単体テスト PASS
- [ ] Layer 3 Python ラッパテスト PASS
- [ ] Layer 4 網羅計算 smoke test PASS
- [ ] 既存 `tr2` バイナリの数値結果が Phase 0 ベースラインと一致
- [ ] `python/trlib/README.md` に使用例が記載されている
- [ ] `run_tests.sh` に `trlib_*` カテゴリが統合されている

---

## 付録 A: 設計決定の根拠一覧

### A.1 API 粒度（質問 1）
- 検討: (a) 一括実行 / (b) ステップ型 / (c) 両方
- 議論: ユーザが初期 b を選択後、一括実行 (a) を何度も呼べばステップ型相当の動作が可能という議論があり、**unified 5 関数 API** に統一
- 採用: ステートフルな `tr_init / tr_run(NTMAX) / tr_get_state / tr_set_param / tr_finalize`

### A.2 Driver 言語と ABI（質問 2）
- 検討: (a) Python 専用 (f2py) / (b) C ABI + Python wrapper / (c) 両方
- 採用: **(b) C ABI + Python wrapper**
- 理由: 将来 Julia/MATLAB/R 等からも同じ .so を呼べる。f2py はメンテナンスモード

### A.3 Sequencing（質問 3）
- 検討: (a) 先行 / (b) Phase 1-2 の後 / (c) 並行
- 採用: **(b) Phase 1-2 の後**
- 理由: `tr_set_param` のテーブルが TRCOMM submodule 化後でクリーンに設計できる

### A.4 Graphics（質問 4）
- 検討: (a) 完全バイパス / (b) ランタイム切替 / (c) コンパイル時切替 / (d) 別モジュール化
- 採用: **(d) 別モジュール化**
- 理由: Phase 5 のリファクタと相性が良く、最もクリーン

### A.5 パラメータスコープ（質問 5）
- 検討: (a) namelist 全て / (b) 最小セット / (c) TRCOMM 全変数 / (d) namelist + 制御変数
- 採用: **(a) namelist 全て**
- 理由: 既存ユーザの学習コスト最小、Phase 2 submodule と対応

### A.6 ビルド構成（質問 6）
- 検討: (a) 共通 libtr2.a + tr_api.f90 / (b) サブディレクトリ分離 / (c) tr_main を lib 経由に書き換え
- 採用: **(a)**
- 理由: 既存成果物を最大活用、新規ファイル 1 つで済む

### A.7 get_state スコープ（質問 7）
- 検討: (a) Phase 0 dump と同じ / (b) 全変数 name-based / (c) 全プロファイル + 全グローバル
- 採用: **(a) Phase 0 dump と同じ**
- 理由: Layer 1 等価性テストで既存 baseline JSON がそのまま使える

### A.8 テスト戦略（質問 8）
- 検討: (a) 4 層全て / (b) Layer 1 + 3 / (c) Layer 1 + 3 + 4
- 採用: **(a) 4 層全て**
- 理由: ユーザ要件「テストもきちんと付ける」、多層検証で網羅性確保

### A.9 パラメータテーブル機構（section 3）
- 検討: (a) 手書き / (b) コード生成 / (c) namelist 再利用
- 採用: **(a) 手書き**
- 理由: パラメータ追加頻度は高くない、1 箇所集中で十分

### A.10 Python ラッパ層構成（section 4）
- 検討: 1 層 / 2 層（ffi + trlib）
- 採用: **2 層**
- 理由: 将来 FFI 実装切替容易、下層単独テスト可能

### A.11 ビルド PIC 対応（section 5）
- 検討: (a) PIC 付き再ビルド / (b) ソース取り込み / (c) whole-archive
- 採用: **(a) PIC 付き再ビルド**（フォールバックあり）
- 理由: 最もクリーン、各 Makefile に数行追加で済む
