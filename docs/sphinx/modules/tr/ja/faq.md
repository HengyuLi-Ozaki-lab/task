# FAQ / つまずきどころ

## Q1. `FileNotFoundError: libtrapi.so not found ...` が出る

まだビルドしていないか, 場所が違います. 次を試してください:

1. `ls tr/libtrapi.so` が存在するか確認
2. 無ければ `make -C tr libtrapi.so` を実行
3. どうしても別の場所に置きたければ
   `export TRLIB_PATH=/path/to/libtrapi.so`

## Q2. `TrlibParamError: ierr=1` が出る

存在しないパラメータ名を指定した, または配列の添字が範囲外です.
`tr/tr_param_registry.f90` の `SELECT CASE` 節に登録されているかを
確認してください. 追加するには Fortran 側に 1 行足すだけです
(再ビルドが必要).

## Q3. `set_params(PN__1=1.0)` と書いてしまった

`__` (アンダースコア 2 つ) を含むキーは, 配列構文の書き間違いとみなして
明示的にエラーを出します. 正しくは `tr.set_param("PN[1]", 1.0)` です.

## Q4. 同じプロセスで 2 個の `Trlib()` を作れる?

**作れません**. #171 以降, `Trlib` は weakref でシングルトン境界を
明示的に守ります. 2 つ目の `Trlib()` は `TrlibStateError` を上げます.
マルチインスタンスが必要な場合は `multiprocessing` でプロセス分離
してください.

## Q5. 結果が `tr2` (CLI 版) と一致しない

回帰テスト `trlib_equivalence` を実行して Phase 0 ベースラインとの
差分を確認してください.

```bash
bash test_run/run_tests.sh trlib_equivalence
```

tolerance は `1e-10`. 許容値以上ずれる場合は, おそらく登録漏れの
パラメータを指定していません.

## Q6. NumPy が必要?

**不要**. `TrState` は Python の `list` です. NumPy を使いたい場合は
`import numpy as np; np.array(state.RT)` で変換できます.
