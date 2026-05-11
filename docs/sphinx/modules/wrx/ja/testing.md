# テスト

`wrx` ライブラリには **4 層の回帰テスト** が用意されています.

## 4 層の役割

| 層 | ターゲット | 何を検証するか | tolerance |
|---|---|---|---|
| **Layer 1** | `wrxlib_equivalence` | `libwrxapi.so` の出力が Phase 0 の `wrx2` ベースラインと完全一致 | **1e-10** (厳守) |
| **Layer 2** | `wrxlib_c_abi`      | C ABI 5 関数が正しい ierr を返す | — |
| **Layer 3** | `wrxlib_ffi`, `wrxlib_wrapper` | ctypes 構造体, ライフサイクル | — |
| **Layer 4** | `wrxlib_sweep`     | パラメータスキャン smoke | — |

## 実行方法

### 1 つずつ個別に走らせる

```bash
bash test_run/run_tests.sh wrxlib_equivalence
bash test_run/run_tests.sh wrxlib_c_abi
bash test_run/run_tests.sh wrxlib_ffi
bash test_run/run_tests.sh wrxlib_wrapper
bash test_run/run_tests.sh wrxlib_sweep
```

### まとめて走らせる (pytest 直接)

```bash
cd python/wrxlib
pytest --forked --timeout=120 --timeout-method=signal tests/
```

## Layer 1 (等価性テスト) の中身

`wrxlib_equivalence` は:

1. `Wrxlib()` で `libwrxapi.so` をロード
2. Phase 0 fixture からパラメータ (ビーム形状含む) を `set_param` で流し込む
3. `wrx.run(nray_request)` で beam tracing 実行
4. `WrxState.to_dict()` で JSON 出力
5. `test_run/baselines/<case>/metrics.json` と diff (tolerance `1e-10`)

`wrx2` と `libwrxapi.so` の結果が小数点 10 桁で一致するかを見ています.

## beam tracing 固有のテスト課題

`wrx` は `wr` よりも数値感度が高いです (曲率テンソルの時間発展が含まれる
ため). 注意点:

- **初期ビーム幅の 0 近傍**: `RBRADAIN` を 1e-6 のような極小値にすると
  `wr` とほぼ一致するはずですが, 数値積分の都合で `wr` と厳密一致は
  しない場合があります.
- **発散ビームの数値不安定**: `RCURVAIN` が発散方向 (正の小値) だと
  ビームが急速に広がり, 計算領域を外れて停止するケースがあります.
  テストでは固定 fixture の値を使用.

## よく使うファイル

- `python/wrxlib/tests/test_equivalence.py` — Layer 1
- `python/wrxlib/tests/test_wrxlib.py` — Layer 3 高レベル
- `python/wrxlib/tests/test_ffi.py` — Layer 3 低レベル
- `python/wrxlib/tests/test_sweep.py` — Layer 4

## CI との関係

CI では `--forked --timeout=120 --timeout-method=signal` で実行.

```{important}
**等価性テストを `@pytest.mark.skip` で回避するのは禁止**です.
修正できない場合は `@pytest.mark.xfail(strict=True, reason="#<issue>")` と
issue リンクを残してください.
```
