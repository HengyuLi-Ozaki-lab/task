# テスト

`tot` ライブラリには **4 層の回帰テスト** が用意されています.

## 4 層の役割

| 層 | ターゲット | 何を検証するか | tolerance |
|---|---|---|---|
| **Layer 1** | `totlib_equivalence` | `libtotapi.so` の出力が Phase 0 ベースラインと完全一致 | **1e-10** (厳守) |
| **Layer 2** | `totlib_c_abi`      | C ABI 6 関数 (set_param_str 含む) が正しい ierr | — |
| **Layer 3** | `totlib_ffi`, `totlib_wrapper` | プレフィックスルーティング, ライフサイクル | — |
| **Layer 4** | `totlib_sweep`     | `eq:RR × eq:BB` 3×3 sweep | — |

```{note}
Layer 1 と Layer 4 は **`TOT_RUN_OK` ゲート** が立っていないと skip
されます (eq の `EQ_RUN_OK` と同じ仕組み). EQDSK ファイルなど tot に
固有の前提が揃っているかを確認するための環境変数です.
```

## 実行方法

### 1 つずつ個別に走らせる

```bash
bash test_run/run_tests.sh totlib_equivalence  # Layer 1 (最重要)
bash test_run/run_tests.sh totlib_c_abi        # Layer 2
bash test_run/run_tests.sh totlib_ffi          # Layer 3 (低レベル)
bash test_run/run_tests.sh totlib_wrapper      # Layer 3 (高レベル)
bash test_run/run_tests.sh totlib_sweep        # Layer 4
```

### まとめて走らせる (pytest 直接)

```bash
cd python/totlib
pytest --forked --timeout=300 --timeout-method=signal tests/
```

`--forked` は必須. `tot` は全モジュール状態を保持するため, テストの
プロセス分離は他モジュール以上に重要です.

## Layer 1 (等価性テスト) の中身

`totlib_equivalence` は以下を実行します:

1. `Tot()` で `libtotapi.so` をロード (= 全サブモジュール init)
2. Phase 0 fixture からプレフィックス付きパラメータを `set_param` で流し込む
   (`eq:RR`, `tr:NSMAX`, ...)
3. `tot.run(ntmax)` で統合シミュレーション実行
4. `TotState.to_dict()` で JSON 出力 (presence flags + scalars + プロファイル)
5. `test_run/baselines/<case>/metrics.json` と diff (tolerance `1e-10`)

`tot_x2` バイナリと `libtotapi.so` 経由の結果が小数点 10 桁で一致するか
を見ています.

## tot 固有のテスト課題

### サブモジュール間連携の数値再現性

`tot` は eq → tr → wr → fp と複数モジュールを連鎖させるため, 各ステップ
での誤差伝播が問題になります. 単独モジュールが 1e-10 一致しても, tot で
は数値感度が違って 1e-9 程度に劣化することがあります.

### TOT_RUN_OK ゲート

`TOT_RUN_OK` が立っていない環境では Layer 1 と Layer 4 はスキップされます:

- `EQ_RUN_OK` (eq の EQDSK ファイル整備) が前提
- 各サブモジュールの動作確認が前提
- 詳細は `test_run/scripts/check_run_ok.sh` 参照

## よく使うファイル

- `python/totlib/tests/test_equivalence.py` — Layer 1
- `python/totlib/tests/test_totlib.py` — Layer 3 高レベル
- `python/totlib/tests/test_ffi.py` — Layer 3 低レベル
- `python/totlib/tests/test_sweep.py` — Layer 4

## CI との関係

CI では並列実行されますが, tot は単独モジュールのテスト後に走るのが
普通です (依存関係上).

```{important}
**等価性テストを `@pytest.mark.skip` で回避するのは禁止**です.
修正できない場合は `@pytest.mark.xfail(strict=True, reason="#<issue>")` と
issue リンクを残してください.
```
