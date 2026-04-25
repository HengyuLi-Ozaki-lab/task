# テスト

`fp` ライブラリには **4 層の回帰テスト** が用意されています.

## 4 層の役割

| 層 | ターゲット | 何を検証するか | tolerance |
|---|---|---|---|
| **Layer 1** | `fplib_equivalence` | `libfpapi.so` の出力が Phase 0 の `fpx2` ベースラインと完全一致 | **1e-10** (厳守) |
| **Layer 2** | `fplib_c_abi`      | C ABI 6 関数が正しい ierr を返す | — |
| **Layer 3** | `fplib_ffi`, `fplib_wrapper` | ctypes 構造体, ライフサイクル | — |
| **Layer 4** | `fplib_sweep`     | 3×3 RR×BB スキャンの smoke | — |

Layer 1 がこのライブラリの **生命線** です. 1e-10 で合わないとリリース
できません.

```{note}
fp はメモリ消費が大きいため, Layer 1 と Layer 4 のテストは比較的時間が
かかります (typical 5–10 分). タイムアウトは `test_definitions.conf` で
600 秒に設定されています.
```

## 実行方法

### 1 つずつ個別に走らせる

```bash
bash test_run/run_tests.sh fplib_equivalence  # Layer 1 (最重要)
bash test_run/run_tests.sh fplib_c_abi        # Layer 2
bash test_run/run_tests.sh fplib_ffi          # Layer 3 (低レベル)
bash test_run/run_tests.sh fplib_wrapper      # Layer 3 (高レベル)
bash test_run/run_tests.sh fplib_sweep        # Layer 4
```

### まとめて走らせる (pytest 直接)

```bash
cd python/fplib
pytest --forked --timeout=600 --timeout-method=signal tests/
```

`--forked` は `--timeout=600` (10 分) と組み合わせます — fp の reset 状態
管理上, プロセス分離が必須です.

## Layer 1 (等価性テスト) の中身

`fplib_equivalence` は以下を実行します:

1. `Fplib()` で `libfpapi.so` をロード
2. Phase 0 fixture から登録済みパラメータを `set_param` / `set_param_str`
   で流し込む (`KNAMEQ` 含む)
3. fixture の `NTMAX` まで `run()` で時間発展
4. `FpState.to_dict()` で JSON 出力 (モーメント量)
5. `test_run/baselines/<case>/metrics.json` と diff (tolerance `1e-10`)

`fpx2` バイナリと `libfpapi.so` 経由の結果が小数点 10 桁で一致するかを
見ています. fp は分布関数の精密ソルバなので, 微小な数値ノイズも 10 桁
で見えます.

## よく使うファイル

- `python/fplib/tests/test_equivalence.py` — Layer 1
- `python/fplib/tests/test_fplib.py` — Layer 3 高レベル
- `python/fplib/tests/test_ffi.py` — Layer 3 低レベル
- `python/fplib/tests/test_sweep.py` — Layer 4
- `test_run/test_definitions.conf` — `fplib_*` 定義 (timeout=600)

## CI との関係

CI では並列実行されます. メモリ消費の大きい fp テストは, 他の軽い
モジュール (tr, eq) より遅れて完了することがよくあります.

```{important}
**等価性テストを `@pytest.mark.skip` で回避するのは禁止**です.
修正できない場合は `@pytest.mark.xfail(strict=True, reason="#<issue>")` と
issue リンクを残してください.
```
