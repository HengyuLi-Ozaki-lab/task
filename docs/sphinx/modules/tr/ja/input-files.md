# 入力ファイル

```{admonition} このページの位置付け
:class: note

TR が読み込み得る支援データファイルの地図です — eqdata
(EQDSK 系), ufile (実験プロファイルデータ), およびファイル
配置・パスの制約. canonical な format 仕様は別所に存在し,
本ページは TR がどのフラグでどのファイルを読むかだけを
点で示します.
```

---

## eqdata ファイル (EQDSK 系)

`MODELG ∈ {3, 5, 8, 9}` で TR の BPSD 経由 equilibrium
pull が走ります (`tr/trbpsd.f90:213`). この 4 値はすべて
`eq` 側でも実際に外部 load を駆動しますが, 値ごとに loader
ルーチンが異なります:

- `MODELG = 3` または `MODELG = 9` → `EQRTSK`
  (TASK/EQ バイナリ形式)
- `MODELG = 5` → `EQDSKR` (community EQDSK 形式)
- `MODELG = 8` → `EQJAEAR`

dispatch テーブルは `eq/eqfile.f90:108-115` にあります.
つまり `MODELG = 9` は no-op alias ではなく, `MODELG = 3`
と同じ `EQRTSK` reader を実際に呼びます.

パスは `KNAMEQ` (文字列パラメータ) で指定します. Python
からの設定方法は {doc}`parameter-setting` 参照. ファイル
自体は `eq` 側で読まれ, `tr` は結果の equilibrium / metric
を BPSD broker 経由で pull するだけです (`tr/trbpsd.f90:213-245`
— geometry-aware な pull は `MODELG` で条件分岐).

EQDSK format 自体の canonical な仕様は `eq` chapter および
外部資料 (EQDSK は TASK よりも前から存在する community 形式)
を参照してください. 本ページではフォーマットを再記述しません.

動作する例ファイルは
`test_run/test_output/tot_demo2014_short/eqdata.demo2014`
にあり, Layer 1 equivalence test のベースラインに使われて
います.

---

## ufile (`MDLUF`)

「ufile」は実験プロファイル時系列データ (密度・温度・q
プロファイル等のスナップショット) の community 形式です.
TR は interpretive run の駆動入力として ufile を取り込めます.

読み込みは `MDLUF` で制御 (default `0` = OFF; 非ゼロで
有効化). default の確認は `tr/trinit.f90:641-648`.
`MDLUF` は `tr/tr_param_registry.f90` に登録されており,
`tr.set_param("MDLUF", ...)` で実行時に設定できます.

**ディレクトリパラメータ `KUFDIR` / `KUFDEV` / `KUFDCG`
は namelist 専用です.** legacy `&trn` namelist 入力
(`tr/trparm.f90:108-112`) には登場しますが,
`tr/tr_param_registry.f90` には登録されておらず (registry
側の "future additions" コメントは `:184-186`),
`tr.set_param_str` 経由では設定できません. ufile dir を
変えたいユーザは:

- legacy の namelist 駆動 `tr2` driver から実行する, あるいは
- これらが registry に登録されるまで, Fortran 側
  デフォルト / ソース編集で対処する

reader chain:

- `tr/trufile.f90:70-77` — dispatch stub, `MDLUF` と
  シナリオ種別から下位ルーチンを選択.
- `tr/tr_ufile_task.f90:7` — `TR_TIME_UFILE` /
  `TR_STEADY_UFILE` のエントリポイント.
- `tr/tr_ufile_topics.f90:7` — `TR_TIME_UFILE_TOPICS` の
  topic 別デコーダ.

prescribed profile や analytic geometry のシナリオを走らせる
大半のユーザにとって ufile は不要 — default の
`MDLUF = 0` のままで OK です. このエントリは, 実験データ
入力が必要な研究ワークフローで読者が出会ったときの入口
として置いてあります.

---

## `trmodels/` その他のモデル側データ

一部の輸送モデルは lookup table や係数データを埋め込んで
います (NCLASS 系等). codebase ではこれらを別 runtime
ファイルではなくソース内に持っており: `tr/trmodels.f90` が
コンパイル済の driver ルーチン (`mbgb_driver`,
`mmm95_driver`, `mmm71_driver`) を直接呼び出し, runtime な
モデル側ディレクトリからは `OPEN` / `READ` していません.

実用的に: **runtime の外部データは現在 eqdata + ufile に
限られます**. ライブラリが起動時に読む `trmodels/` 系の
runtime ディレクトリは存在しません.

---

## ファイル配置とパスの制約

`eq` の C 文字列インタフェースは `KNAMEQ` (および類似の
文字列パラメータ) を 80 byte で cap します. 定数は
`python/eqlib/eqlib.py:39-41` で定義され, 長さ拒否
(`EqlibInvalidParamError`, `len(encoded) > max_bytes`) は
`:66-70`. Fortran 側は `CHARACTER(LEN=80)` で受けます.
docstring の `:47-50` には "up to 79 bytes" とありますが
これは stale で, Python は 80 byte をすべて受け付けます.
制約は **byte** (codepoint ではなく encoded バイト) で
扱ってください.

推奨パターン: eqdata ファイルが置いてある作業ディレクトリ
に `chdir` して bare filename を渡す. 既存の
`python/totlib/tests/test_pipeline_*` ファイルがこのパターン
を使っています.

80 byte を超える絶対パスはパラメータ設定時に失敗し
(`run()` 呼び出し前), runtime ではなく即座にエラーが見えます.

---

## 関連項目

- {doc}`parameter-setting` — Python `set_param_str` 経由
  の文字列パラメータ設定方法.
- {doc}`limitations-and-references` — 類似ファイルを消費
  する他のオープン輸送コードとの比較.
- {doc}`design` — `eq` 出力を受け取るための TR 側 BPSD
  broker の配管.
- {doc}`numerical-stability-and-diagnostics` — eqdata
  load が予期しない挙動を見せたときに走行時に何を見るか.
