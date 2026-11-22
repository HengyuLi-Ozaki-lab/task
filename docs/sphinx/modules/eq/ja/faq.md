# FAQ — `eq` 固有

## Q1. なぜ `PSIB` だけ 0-origin?

`eqcom1_mod.f90` で `REAL(8) :: PSIB(0:5)` と宣言されており, ψ 境界
条件として $\psi = 0$ (磁気軸) から数えるのが物理的に自然だからです.
PF コイル系配列 (`RIPFC`, `RPFC`, `ZPFC`, `WPFC`) は 1-origin の
慣習に従います.

`set_param` 経由では `"PSIB[0]"` 〜 `"PSIB[5]"` で指定し, 添字無しの
裸の `"PSIB"` はレジストリで明示的に拒否されます
(`EqlibInvalidParamError`).

## Q2. `eq.run()` の `mode` 引数の意味は?

`eq.run(mode)` には現在 2 つの動作モードがあります. 両方とも元の
`eqx2` CLI のメニューコマンドに対応します:

| `mode` | 用途 | 元 CLI コマンド | 必要な設定 |
|---|---|---|---|
| `0` | **Grad-Shafranov 求解** (`EQCALC` を `EPSEQ` まで反復 + post-processing) | `R` (Run) → `F` (Fields) | `MODELG ∈ {0, 1, 2}`, プロファイル係数 (`PP*`, `PJ*`, `FF*` 等) |
| `1` (既定) | **平衡ファイル読み込み** (`equnit::eq_load`) | `L` (Load) | ファイル形式: `MODELG` 3 か 9 (TASK/EQ), 5 か 25 (G-EQDSK) と `KNAMEQ` (ファイル名), 8 (QST/JAEA) と `KNAMEQ`, `KNAMEQ2`. `MODELG = 15` は `eqdb.dat` を読む |

`mode=1` がデフォルトなのは **ファイル駆動の標準ワークフロー** だからです
(既定の `MODELG=2` はファイル形式を指さないので失敗します).
平衡を解きたい場合 (装置パラメータと圧力・電流プロファイル係数だけ
与える場合) は `mode=0` を使います. 負の `mode` は `EqlibInvalidParamError`,
1 より大きい `mode` は `EqlibNotImplementedError` になります (C の `int` に
収まらない数はライブラリを呼ぶ前に `EqlibInvalidParamError`).

```{note}
`tr`/`ti`/`wr`/`fp` の `run` は時間ステップ数 `ntmax` を取りますが,
EQ は時間発展を持たないため引数の意味が違います.
```

## Q3. `KNAMEQ` を kwargs で渡すとエラー

`set_params(KNAMEQ="...")` は **NG**. 文字列パラメータは
`set_param_str("KNAMEQ", "...")` を使ってください ({doc}`parameter-setting`
方法 C 参照).

## Q4. `EqlibError: libeqapi.so does not export eq_set_param_str` が出る

Phase L-3 以前の古い `libeqapi.so` を読み込んでいます.
`make -C eq libeqapi.so` で再ビルドしてください.

## Q5. `EqlibCalculationFailedError: ierr=3` が出る

平衡計算が収束しなかったか, 平衡ファイルが整合しないケースです.
よくある原因:

- `RR`, `RA`, `BB`, `RIP` の組み合わせが物理的にあり得ない (極端な
  低トカマク等)
- `EPSEQ` (収束判定) が厳しすぎる. 既定 `1e-6` を `1e-4` に緩めて再試行
- `NLPMAX` (最大反復数) が小さすぎる. 既定 `100` から増やす
- 読み込み (`mode=1`) がファイルを開けない (ファイルが無い). 例外の
  メッセージの末尾に理由があります (`eq.last_error()`). `MODELG` が 3, 5, 9, 25
  のとき, ファイルはあってもその形式でない場合は例外になりません: 読み込み
  ルーチン (3 と 9 は `EQRTSK`, 5 と 25 は `EQDSKR`) は読み込みを
  検査せず, Fortran の実行時エラーでプロセスが止まります (`MODELG` 3, 5 で確認).
  8 (`EQJAEAR`) と 15 (`eqdb.dat`) の読み込みルーチンは検査してエラーを返します

`validate()` で事前にチェックできるのはグリッド寸法, 読み込むファイルの欠落 (空, または存在しないファイルを指す
`KNAMEQ`, `MODELG=8` の `KNAMEQ2`, `MODELG=15` の `eqdb.dat`), Grad-Shafranov 求解
では壁がプラズマの内側にあること, 負の電流, ソルバーが使えない箱
(`MDLEQF >= 10`) までで, 物理整合性は `run()` で初めて分かります.

## Q6. 同じプロセスで 2 個の `Eq()` を作れる?

**作れません**. シングルトン境界で守られています. 2 つ目の `Eq()` は
`EqlibError` を上げます. マルチインスタンスが必要な場合は
`multiprocessing` でプロセス分離してください.

## Q7. 結果が `eqx2` (CLI 版) と一致しない

回帰テスト `eqlib_equivalence` を実行して Phase 0 ベースラインとの
差分を確認してください.

```bash
bash test_run/run_tests.sh eqlib_equivalence
```

tolerance は `1e-10`. 許容値以上ずれる場合は, 登録漏れのパラメータを
指定していないか確認してください.

## Q8. NumPy が必要?

**不要**. `EqState` は Python の `list` です. NumPy を使いたい場合は
`import numpy as np; np.array(state.psips)` で変換できます.
