# テスト

`wr` ライブラリには **4 層の回帰テスト** が用意されています.

## 4 層の役割

| 層 | ターゲット | 何を検証するか | tolerance |
|---|---|---|---|
| **Layer 1** | `wrlib_equivalence` | `libwrapi.so` の出力が Phase 0 の `wrx2` ベースラインと完全一致 | **1e-10** (厳守) |
| **Layer 2** | `wrlib_c_abi`      | C ABI 5 関数が正しい ierr を返す | — |
| **Layer 3** | `wrlib_ffi`, `wrlib_wrapper` | ctypes 構造体, ライフサイクル | — |
| **Layer 4** | `wrlib_sweep`     | パラメータスキャン smoke | — |

Layer 1 がこのライブラリの **生命線** です.

## 実行方法

### 1 つずつ個別に走らせる

```bash
bash test_run/run_tests.sh wrlib_equivalence  # Layer 1 (最重要)
bash test_run/run_tests.sh wrlib_c_abi        # Layer 2
bash test_run/run_tests.sh wrlib_ffi          # Layer 3 (低レベル)
bash test_run/run_tests.sh wrlib_wrapper      # Layer 3 (高レベル)
bash test_run/run_tests.sh wrlib_sweep        # Layer 4
```

### まとめて走らせる (pytest 直接)

```bash
cd python/wrlib
pytest --forked --timeout=120 --timeout-method=signal tests/
```

## Layer 1 (等価性テスト) の中身

`wrlib_equivalence` は以下を実行します:

1. `Wrlib()` で `libwrapi.so` をロード
2. Phase 0 fixture から登録済みパラメータを `set_param` で流し込む
3. `wr.run(nray_request)` でレイトレース実行
4. `WrState.to_dict()` で JSON 出力
5. `test_run/baselines/<case>/metrics.json` と diff (tolerance `1e-10`)

`wrx2` バイナリと `libwrapi.so` 経由の結果が小数点 10 桁で一致するか
を見ています. レイ軌跡は数値感度が高いので, 1e-10 一致は厳しい
ベンチマークです.

## レイトレース固有のテスト課題

`wr` のテストは時間発展しないので, 通常の単体テストよりも初期条件依存
が大きいです. 注意点:

- **数値積分の経路依存**: `EPSRAY`, `DELRAY` 等を変えると経路が微妙に
  変わり, 1e-10 一致が崩れることがあります. テストでは fixture の値を
  そのまま使う前提.
- **共鳴位置依存**: 周波数とプラズマパラメータが共鳴に近いと, 微小な
  パラメータ変動で結果が大きく変わります.

## よく使うファイル

- `python/wrlib/tests/test_equivalence.py` — Layer 1
- `python/wrlib/tests/test_wrlib.py` — Layer 3 高レベル
- `python/wrlib/tests/test_ffi.py` — Layer 3 低レベル
- `python/wrlib/tests/test_sweep.py` — Layer 4

## CI との関係

CI では `--forked --timeout=120 --timeout-method=signal` で実行されます.

```{important}
**等価性テストを `@pytest.mark.skip` で回避するのは禁止**です.
修正できない場合は `@pytest.mark.xfail(strict=True, reason="#<issue>")` と
issue リンクを残してください.
```
