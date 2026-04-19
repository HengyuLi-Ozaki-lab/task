# totlib — TASK/TOT 統合シミュレータの Python ラッパ

`totlib` は TASK の統合輸送シミュレータ `tot/libtotapi.so`（Phase L-4
で生成される共有ライブラリ）を `ctypes` で呼び出す Python パッケージ
です。スタンドアロンの `tot` バイナリを起動せず、Python スクリプト
から TOT 計算を駆動するための薄いラッパ層を提供します。

## 概要

TOT は TASK の **統合（オーケストレータ）モジュール**です。`eq`、
`tr`、`fp`、`ti`、`wr`、`wrx` の各モジュールを束ねて 1 本の物理計算
を回す立場にあります。そのため `tot` のパラメータ空間は、6 個の
モジュールのパラメータレジストリの **和集合**になっています。

|  | 従来の CLI | ライブラリ（Phase L） |
|---|---|---|
| バイナリ | `tot/tot` | `tot/libtotapi.so` |
| エントリ | 対話メニュー | 6 個の C ABI 関数 |
| 入出力 | namelist + ASCII 出力 | メモリ上の状態構造体 |
| グラフィクス | PGPlot / Fortran graphics | 含まない（スタブで置換） |
| Python | — | `python/totlib` |

C ABI は `tot/tot_api.h` で定義されており、Fortran バックエンド
（`tot/tot_api.f90`、`tot/tot_param_registry.f90`、
`tot/tot_state.f90`）はそのまま `tot` バイナリにもリンクされる純粋な
Fortran です。`python/totlib` は 6 個の C エントリをラップして、
`tot_state_t` 構造体を純 Python の `TotState` データクラスに詰め直す
だけの役割を担います。

サードパーティ依存はありません。Python 3.8+ の標準ライブラリのみ
（`ctypes`、`dataclasses`、`pathlib`、`os`）で動作します。`numpy` は
任意です（あれば検知しますが必須ではありません）。

## ビルド

共有ライブラリを 1 度だけビルドします。

```bash
cd /path/to/task
make -C tot libtotapi.so
```

これで `tot/libtotapi.so` と、依存ライブラリの PIC 版（`lib*_pic.a`、
`lib*.so`）が生成されます。既存の非 PIC `*.a` アーカイブと `tot`
バイナリは影響を受けません。

ラッパを `PYTHONPATH` に置きます。

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

リポジトリ外に配置されたライブラリを使う場合は `TOTLIB_PATH` で
指定できます。

```bash
export TOTLIB_PATH=/custom/path/libtotapi.so
```

ライブラリ探索順（最初に存在したものを採用）:
`TOTLIB_PATH` 環境変数 → `<repo>/tot/libtotapi.so` →
`<repo>/lib/libtotapi.so`。

## クイックスタート

```python
from totlib import Tot

with Tot() as tot:
    # 名前空間プレフィックスを必ず付けます。
    tot.set_param("eq:RR", 6.2)        # equilibrium 主半径 [m]
    tot.set_param("tr:DT", 0.01)       # transport 時間刻み [s]
    tot.set_param("fp:NSMAX", 2)       # FP 種類数
    tot.set_param("ti:RR", 6.2)        # TI 主半径 [m]
    tot.set_param("wrx:RFIN", 170.0)   # WRX RF 周波数 [GHz]

    # まとめ設定（dict 形式が必須。kwargs にはコロンを書けません）。
    tot.set_params({
        "tr:RA": 2.0,
        "tr:BB": 5.3,
        "eq:RIP": 1.5,
    })

    # L-6 で fan-out が完了したら有効になります（現状はスタブ）。
    # tot.run(ntmax=10)
    # state = tot.get_state()
```

## 名前空間プレフィックス（重要）

TOT では同じ名前のパラメータが複数モジュールに存在します
（例: `RR` は `eq` / `tr` / `ti` / `wrx` のいずれにも存在し、
`DT` は `tr` と `ti` の両方に存在します）。そのため、`Tot.set_param`
に渡す名前は **必ず** `<ns>:<bare>` 形式にしてください。

| プレフィックス | 振り分け先レジストリ | 代表例 |
|---|---|---|
| `eq:` | `eq_param_set` | `eq:RR`, `eq:BB`, `eq:RIP`, `eq:KNAMEQ` |
| `tr:` | `tr_param_set` | `tr:DT`, `tr:NTMAX`, `tr:RR`, `tr:PN[1]` |
| `fp:` | `fp_param_set` | `fp:NSMAX`, `fp:DELT` |
| `ti:` | `ti_param_set` | `ti:RR`, `ti:DT` |
| `wr:` | `wrx_param_set`（エイリアス） | `wr:RFIN` |
| `wrx:` | `wrx_param_set` | `wrx:RFIN`, `wrx:NRAY` |

> **`wr:` は `wrx:` の別名です。** TOT は `wrx/libwr.a` をリンク
> するため、`wr:` プレフィックスも内部的に `wrx_param_set` に振り
> 分けられます。詳細は `tot/tot_param_registry.f90` の冒頭コメント
> を参照してください。

未対応のプレフィックスや、プレフィックスを付け忘れた名前は、Python
側のガードが先に検出して `TotlibInvalidParamError` を送出します。
誤って Fortran 側まで到達した場合も `rc=1` で同じ例外になります。

```python
tot.set_param("RR", 6.2)
# -> TotlibInvalidParamError: tot parameter name 'RR' is missing a
#    namespace prefix. tot is the orchestrator: every name must be
#    of the form '<ns>:<name>' where <ns> is one of
#    ('eq', 'tr', 'fp', 'ti', 'wr', 'wrx'). ...
```

配列要素は per-module レジストリの構文をそのまま使えます
（例: `tot.set_param("tr:PN[1]", 0.7)`、`tot.set_param("eq:PSIB[0]", 0.0)`）。

## API リファレンス

### `Tot(lib_path: str | None = None)`

コンテキストマネージャです。`__enter__` で `tot_init` が呼ばれ、
`__exit__` / `close()` で `tot_finalize` が呼ばれます。プロセス内に
意味のあるインスタンスは 1 つだけです（TOT バックエンドは COMMON
ブロックと per-module モジュール変数で大域状態を保持しています）。

> **L-3/L-4 時点の注意事項**: `tot_init` と `tot_finalize` は
> `TOT_ERR_NOT_IMPL` を返すスタブです。ラッパは `OK` と `NOT_IMPL`
> の両方を「ライブラリは開いた」とみなして処理を続けるので、
> `set_param` のテストや動作確認は今すぐ可能です。L-6 で fan-out
> 実装が入ると自動的に `OK` 経路に切り替わります。

### `Tot.set_param(name, value) -> None`

数値パラメータを 1 つ設定します。`name` には必ず `<ns>:<bare>`
形式の名前を渡してください。バリデーションは Python 側で先に行い
ます（不正な場合は FFI 呼び出し前に `TotlibInvalidParamError`）。

### `Tot.set_param_str(name, value) -> None`

文字列パラメータを設定します。L-3 時点で文字列レジストリを持って
いるのは `tr:` と `eq:` だけです（`tr:KNAMEQ`、`eq:KNAMEQ` ほか）。
他の名前空間は `rc=1` で `TotlibInvalidParamError` になります。

### `Tot.set_params(*args, **kwargs) -> None`

複数のパラメータをまとめて設定します。Python のキーワード引数には
コロンを書けないため、**必ず dict もしくは `(name, value)` のイテ
ラブルを位置引数として渡してください**。

```python
tot.set_params({"eq:RR": 6.2, "tr:DT": 0.01})
tot.set_params([("fp:NSMAX", 2), ("ti:RR", 6.2)])
```

各キーは `set_param` と同じガードを通ります。

### `Tot.run(ntmax: int) -> None`

統合シミュレーションを `ntmax` ステップ進めます。L-3/L-4 では
`tot_run` がスタブ（`rc=4`）のため、現状は
`TotlibNotImplementedError` が必ず送出されます。L-6 で per-module
の `*_run` 連結が入ると正常終了するようになります。

### `Tot.get_state() -> TotState`

現在の TOT 状態をスナップショットして `TotState` データクラスに
詰めて返します。各配列はランタイムの実サイズ（`[0:nrmax]` /
`[0:nsmax]`）で切り詰めるため、末尾のゼロパディング（`TOT_MAX_*`
までの分）が利用側に漏れることはありません。L-3/L-4 では
`tot_get_state` がスタブのため、現状は
`TotlibNotImplementedError` が必ず送出されます。

### `Tot.close() -> None`

冪等です。コンテキストマネージャから抜けるときに自動で呼ばれます。

## `TotState` フィールド

`tot_state_t`（`tot/tot_api.h`）と 1:1 対応します。`state.to_dict()`
は JSON シリアライズ可能な辞書を返します。

| 属性 | 型 | 意味 |
|---|---|---|
| `tr_present` | int | TR モジュールの初期化済みフラグ（0/1） |
| `ti_present` | int | TI モジュールの初期化済みフラグ |
| `fp_present` | int | FP モジュールの初期化済みフラグ |
| `wr_present` | int | WR モジュールの初期化済みフラグ |
| `nt` | int | 時間ステップカウンタ（TR 由来） |
| `nrmax` | int | 動的な radial 格子点数 |
| `nsmax` | int | 動的な species 数 |
| `scalars` | `dict[str, float]` | 統合スカラー 13 個 |
| `RN` | `list[list[float]]` | `[nrmax][nsmax]` 密度プロファイル |
| `RT` | `list[list[float]]` | `[nrmax][nsmax]` 温度プロファイル |
| `AJ` | `list[float]` | `[nrmax]` 電流プロファイル |
| `QP` | `list[float]` | `[nrmax]` 安全係数プロファイル |

スカラー（標準順序）: `T`, `WPT`, `AJT`, `Q0`, `BETA0`, `BETAP0`,
`BETAA`, `BETAN`, `TAUE1`, `TAUE2`, `ZEFF0`, `ALI`, `RQ1`。

## 例外階層

すべての `tot_*` リターンコードは `TotlibError` のサブクラスに
マッピングされます。

| rc | クラス | 意味 |
|---|---|---|
| 0 | — | 成功 |
| 1 | `TotlibInvalidParamError` | 不正なパラメータ名（プレフィックス無し / 不明な名前空間 / 不明なベア名） |
| 2 | `TotlibNotInitializedError` | `tot_init` 前の呼び出し |
| 3 | `TotlibCalculationFailedError` | `tot_run` / `tot_get_state` の計算失敗 |
| 4 | `TotlibNotImplementedError` | 実装待ちのスタブ（L-3/L-4 時点の `init` / `run` / `get_state` / `finalize`） |

スペック準拠のエイリアス（`TotLibError`、`TotLibInvalidParam`、
`TotLibNotInitialized`、`TotLibCalculationFailed`、
`TotLibNotImplemented`）も同時にエクスポートしています。

## CLI からの移行ガイド

| `tot` CLI 操作 | `totlib.Tot` 相当 |
|---|---|
| `eqparm` / `trparm` namelist を編集 | `tot.set_param("eq:...", ...)` / `tot.set_param("tr:...", ...)` |
| EQDSK ファイル指定 | `tot.set_param_str("eq:KNAMEQ", path)` |
| メニュー（実行） | `tot.run(ntmax)`（L-6 以降で利用可能） |
| 出力ファイルを確認 | `tot.get_state()`（L-6 以降で利用可能） |
| メニュー `Q`（終了） | `with` を抜ける / `tot.close()` |
| バッチパラメータ走査 | Python の `for` ループで `tot.set_params(...)` |

ラッパは **graphics、ファイル出力、対話メニューをラップしません**
（それらは `tot/tot` バイナリ専用です）。

## 既知の制限

- **プロセスあたり 1 インスタンス**: TOT バックエンドは COMMON
  ブロックを使うため、同一プロセス内に 2 つの `Tot()` を立てると
  お互いの状態を破壊します。
- **`run` / `get_state` は L-6 待ち**: 現状の `tot_init` /
  `tot_run` / `tot_get_state` / `tot_finalize` はスタブで
  `rc=4`（`TotlibNotImplementedError`）を返します。L-6 で per-module
  fan-out が入ると順次有効になります。
- **graphics / MPI / OpenMP API なし**: graphics シンボルは
  スタブで置換済みです。loader は `RTLD_LAZY` を使うため、未到達
  のシンボルは解決されません。
- **`wr:` は `wrx:` の別名**: TOT のリンクグラフ上の都合で `wr:`
  プレフィックスは `wrx_param_set` に振り分けられます。`wr/`
  ツリーの非 wrx レジストリを使いたい場合は `libwrapi.so` を直接
  叩くか、`python/wrlib` を使ってください。
- **未登録の bare 名**: 各 per-module レジストリに未登録の名前は
  `TotlibInvalidParamError` になります。新規追加は Fortran 側で
  行ってください。

## テスト

```bash
cd python/totlib/tests
python3 -m unittest discover -v
```

`libtotapi.so` を必要とするテストは、共有ライブラリが存在しない
場合は自動的に SKIP されます。純 Python テスト（ctypes レイアウ
ト、エラー配線、namespace ガード、`TotState.from_c` / `to_dict`
の形状）は常に実行されます。

## ライセンス・コントリビュート

`totlib` は TASK コードの一部であり、リポジトリトップのライセンス
に従います。バグ報告と PR を歓迎します。ラッパの変更は最小限に
保ってください（C ABI が安定レイヤなので、新規パラメータはまず
per-module Fortran レジストリに追加するのが基本方針です）。

## 関連ドキュメント

- `docs/superpowers/specs/2026-04-17-tr-library-design.md` — 全体
  設計仕様
- `docs/superpowers/plans/2026-04-18-tot-library-L5-python-wrapper.md`
  — 本フェーズの計画
- `tot/tot_api.h` — C ABI ヘッダ
- `tot/tot_param_registry.f90` — namespaced パラメータディスパッチャ
- `python/trlib/README.md`、`python/eqlib/README.md` — 同型のラッパ
  実装（参考）
