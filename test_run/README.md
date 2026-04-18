# test_run — TASK モジュール 回帰テスト

`eq`, `tr`, `tx`, `ti`, `fp` など TASK の各モジュールを、あらかじめ用意した入力で実行し、CLOSED メッセージと数値指標の両方でパス/フェイルを判定する仕組み。

## ディレクトリ構成

- `run_tests.sh`            — テストランナ
- `test_definitions.conf`   — テスト定義（`TEST_NAME:MODULE:INPUT:DEPENDS:TIMEOUT:DESC`）
- `inputs/`                 — モジュール用の短縮入力
- `test_output/<name>/`     — 実行ごとのログ・成果物・dump（gitignore 対象）
- `baselines/<name>/`       — 回帰判定用ゴールデン指標（**コミット対象**）
- `scripts/`
  - `extract_tr_metrics.py` — `tr_regress.dat` を JSON に変換
  - `extract_ti_metrics.py` — `ti_regress.dat` を JSON に変換
  - `extract_fp_metrics.py` — `fp_regress.dat` を JSON に変換
  - `compare_metrics.py`    — 2 指標 JSON を相対誤差で比較（tr/ti/fp 共用、デフォルト 1e-10）
  - `check_regression.sh`   — 抽出＋比較（または baseline 生成）。テスト名接頭辞 (`tr_*` / `ti_*` / `fp_*`) でモジュール自動判定
  - `tests/`                — 上記スクリプトの unittest ベースの単体テスト

## 基本使用例

### 全テストを走らせる

    ./run_tests.sh

### 特定のテストのみ

    ./run_tests.sh tr_iter01 tr_m0904

### 詳細ログ

    ./run_tests.sh -v tr_iter01

### スクリプト側の単体テスト

    cd scripts
    python3 -m unittest discover tests -v

pytest ではなく Python 標準ライブラリの `unittest` を使うため、追加の依存インストール不要。

## TR モジュールの回帰判定の仕組み

### 1. 高精度 dump

TR 本体 (`tr/trregress.f90`) は、環境変数 `TR_REGRESS_DUMP=1` が設定されているときに限り、
計算ループ終了時点の主要グローバル量（`WPT, AJT, Q0, BETA0, TAUE1, ALI, RQ1, ...`）と
プロファイル（`RN, RT, AJ, QP` を半径方向 `NRMAX` 点）を `tr_regress.dat` に
`1PE24.16` 書式で書き出す。

通常実行（環境変数未設定）では dump は生成されず、挙動は完全に従来通り。

### 2. 比較フロー

1. `run_tests.sh` は TR モジュールに対してだけ `TR_REGRESS_DUMP=1` をエクスポートして `tr/tr2` を実行。
2. stdout に `CLOSED` が出れば計算は成功。
3. 成功時、`scripts/check_regression.sh` が以下を行う:
    1. `extract_tr_metrics.py` が `tr_regress.dat` を JSON に変換し `test_output/<test>/metrics.json` に保存。
    2. `compare_metrics.py` が `baselines/<test>/metrics.json` と相対誤差 `1e-10` で比較。
4. 不一致なら `REGRESSION (metrics drift; see ...)` を出して FAIL。詳細は `test_output/<test>/regression.log`。

### 3. dump に含まれる値

- スカラー: `NT, NRMAX, NSMAX, T, WPT, AJT, Q0, BETA0, BETAP0, BETAA, BETAN, TAUE1, TAUE2, ZEFF0, ALI, RQ1`
- プロファイル: `NR, RN(NR,1:NSMAX), RT(NR,1:NSMAX), AJ(NR), QP(NR)` を `NR=1..NRMAX` で 1 行ずつ

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
    TR_REGRESS_DUMP=1 ../../tr/tr2 < ../inputs/tr_iter01.in > out.log 2>&1
    cat tr_regress.dat

## 注意事項

- **dump のタイミング**: dump は計算ループが抜けた時点（`9000` ラベル直後）に書き出される。
  ループが異常終了（IERR で goto 9000）しても dump は生成されるため、部分収束状態での dump にも注意。
- **単位番号**: Fortran unit 77 を使用。他のサブルーチンで 77 を使う場合は競合に注意。
- **環境変数**: `TR_REGRESS_DUMP=1` が厳密文字列一致で判定される。`TRUE` や `yes` では有効化されない。

## よく使うトラブルシュート

- **`REGRESSION (metrics drift)`**: `test_output/<name>/regression.log` を確認。物理的に妥当な差分なのか、リファクタのバグなのかを切り分ける。
- **`check_regression: dump not found`**: 該当テストが TR モジュールで走っていない、または `TR_REGRESS_DUMP` がエクスポートされていない。
- **`check_regression: baseline not found`**: `baselines/<test>/metrics.json` が無い。`--generate-baseline` で初回生成するか、別ブランチからマージする。
- **`SKIP (module not built)`**: 該当モジュールを `make` する（例: `cd tr && make`）。
- **`SKIP (input file not found)`**: `test_definitions.conf` のパスと、`inputs/` / `tr/in/` の実ファイル名を照合する。

## 現時点で登録済みの TR 回帰テスト

| TEST_NAME | 依存 | 用途 |
|---|---|---|
| `tr_iter01` | `eq_iter01` | ITER 相当機（`modelg=3`）、NTMAX=100 短縮版 |
| `tr_m0904`  | なし       | 解析ジオメトリ（`modelg=2`）、NTMAX=50 |
| `tr_tst2`   | `eq_tst2`  | TST-2 小型機（`modelg=3`）、NTMAX=10 |

## TI モジュールの回帰判定の仕組み

TR と同じ dump 機構を `ti/tiregress.f90` で実装。`TI_REGRESS_DUMP=1` のときに限り
`ti_regress.dat` を CWD に書き出す。`run_tests.sh` は ti モジュールテスト実行時に
この変数を自動でエクスポートする。

dump 内容:
- スカラー: `NT, NRMAX, NSMAX, nsa_max, T, residual_loop_max, icount_loop_max, icount_mat_max`
- プロファイル: `NR, RNA(1:nsa_max,NR), RTA(1:nsa_max,NR), RUA(1:nsa_max,NR), RBP, RQP, RJP, ZEFF, BETA, BETAP`

### 登録済みの TI 回帰テスト

| TEST_NAME | 依存 | 用途 |
|---|---|---|
| `ti_min` | なし | 最小ケース (NSMAX=1, NRMAX=10, NTMAX=2) |
| `ti_ar`  | なし | Ar 不純物輸送 (ID_NS=10, NRMAX=20, NTMAX=10) |
| `ti_w`   | なし | W 不純物輸送 (ID_NS=10, NRMAX=20, NTMAX=5) |

### TI ベースラインの再生成

    ./run_tests.sh ti_min ti_ar ti_w   # produces test_output/ti_*/ti_regress.dat
    for c in ti_min ti_ar ti_w; do
        ./scripts/check_regression.sh "$c" \
            "$(pwd)/test_output/$c" "$(pwd)/baselines" 1e-10 --generate-baseline
    done

## FP モジュールの回帰判定の仕組み

TR と完全に同じ「環境変数ガード付き高精度 dump + Python 比較」方式。

### 1. 高精度 dump

FP 本体 (`fp/fpregress.f90`) は、環境変数 `FP_REGRESS_DUMP=1` が設定されているときに限り、
`fp_loop` 終了時点の主要グローバル量を `fp_regress.dat` (`1PE24.16` 書式) に書き出す。
**MPI 並列を考慮し、`nrank == 0` のランクのみ書き出す。**
通常実行（環境変数未設定）では何も生成されず、挙動は完全に従来通り。

### 2. dump に含まれる値

- スカラー: `NRMAX, NSAMAX, NPMAX, NTHMAX, NTG2, TIMEFP`
- プロファイル: 最終 `NTG = NTG2` における
  `RNT, RWT, RTT, RJT, RPCT, RPWT` を `(NR=1..NRMAX, NSA=1..NSAMAX)` の 2 次元として書き出す
  (1 行に `NR NSA RNT RWT RTT RJT RPCT RPWT` の 8 列)。

### 3. 比較フロー

1. `run_tests.sh` は FP モジュールに対して `FP_REGRESS_DUMP=1` をエクスポートして `fp/fp` を実行。
2. stdout に `CLOSED` が出れば計算は成功。
3. 成功時、`scripts/check_regression.sh` がモジュール接頭辞 (`fp_*`) から
   `fp_regress.dat` と `extract_fp_metrics.py` を選び、
   `compare_metrics.py` が `baselines/<test>/metrics.json` と相対誤差 `1e-10` で比較。

### 4. 現時点で登録済みの FP 回帰テスト

| TEST_NAME | 用途 |
|---|---|
| `fp_iter01` | ITER 風入力（`NSAMAX=1, NRMAX=40, NTMAX=2`） |
| `fp_jt60`   | JT-60 風入力（`NRMAX=11, NTMAX=1, NPMAX=NTHMAX=100`） |
| `fp_dt1`    | DT1 namelist 直渡し最小ケース（`NRMAX=1, NTMAX=1`） |

### 5. ベースラインの更新方法

    ./run_tests.sh fp_dt1
    ./scripts/check_regression.sh fp_dt1 \
        "$(pwd)/test_output/fp_dt1" \
        "$(pwd)/baselines" \
        "1e-10" "--generate-baseline"

### 6. 手動 dump

    cd test_output/fp_dt1
    FP_REGRESS_DUMP=1 ../../fp/fp < ../../inputs/fp_dt1.in > out.log 2>&1
    cat fp_regress.dat

### 7. 注意事項

- 単位番号 87 を使用（TR は 77）。`fpregress.f90` 以外で 87 を使う処理に注意。
- `nrank /= 0` のランクは何も書かない。シングルプロセス・MPI 両方で安全。
- `FP_REGRESS_DUMP` は厳密文字列 `1` で判定される。
