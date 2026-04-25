# FAQ — `eq` 固有

## Q1. なぜ `PSIB` だけ 0-origin?

`eqcom1_mod.f90` で `REAL(8) :: PSIB(0:5)` と宣言されており, ψ 境界
条件として $\psi = 0$ (磁気軸) から数えるのが物理的に自然だからです.
PF コイル系配列 (`RIPFC`, `RPFC`, `ZPFC`, `WPFC`) は 1-origin の
慣習に従います.

`set_param` 経由では `"PSIB[0]"` 〜 `"PSIB[5]"` で指定し, 添字無しの
裸の `"PSIB"` はレジストリで明示的に拒否されます
(`EqlibInvalidParamError`).

## Q2. なぜ `eq.run()` のデフォルトが `mode=1`?

`mode=1` は `equnit::eq_load` を呼び, 現在の `KNAMEQ` (EQDSK ファイル)
を読んで平衡を構築する EQDSK 駆動の標準ワークフローだからです. `mode=0`
(直接 EQCALQ 呼び出し) は予約済みで, 現状 `EqlibNotImplementedError`
を返します. `tr`/`ti`/`wr`/`fp` の `run` は時間ステップ数 `ntmax` を
取りますが, EQ は時間発展を持たないため引数の意味が違います.

## Q3. `KNAMEQ` を kwargs で渡すとエラー

`set_params(KNAMEQ="...")` は **NG**. 文字列パラメータは
`set_param_str("KNAMEQ", "...")` を使ってください ({doc}`parameter-setting`
方法 C 参照).

## Q4. `EqlibError: libeqapi.so does not export eq_set_param_str` が出る

Phase L-3 以前の古い `libeqapi.so` を読み込んでいます.
`make -C eq libeqapi.so` で再ビルドしてください.

## Q5. `EqlibCalculationFailedError: ierr=3` が出る

平衡計算が収束しなかったか, EQDSK ファイルが整合しないケースです.
よくある原因:

- `RR`, `RA`, `BB`, `RIP` の組み合わせが物理的にあり得ない (極端な
  低トカマク等)
- `EPSEQ` (収束判定) が厳しすぎる. 既定 `1e-6` を `1e-4` に緩めて再試行
- `NLPMAX` (最大反復数) が小さすぎる. 既定 `100` から増やす
- EQDSK ファイルのフォーマットが合っていない (バージョン違い)

`validate()` で事前にチェックできるのはグリッド寸法とファイル存在まで
で, 物理整合性は `run()` で初めて分かります.

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
