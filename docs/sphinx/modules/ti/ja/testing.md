# テスト

`ti` ライブラリには **4 層の回帰テスト** が用意されています.

## 4 層の役割

| 層 | ターゲット | 何を検証するか | tolerance |
|---|---|---|---|
| **Layer 1** | `tilib_equivalence` | `libtiapi.so` の出力が Phase 0 の `tix2` ベースラインと完全一致 | **1e-10** (厳守) |
| **Layer 2** | `tilib_c_abi`      | C ABI 5 関数が正しい ierr を返す | — |
| **Layer 3** | `tilib_ffi`, `tilib_wrapper` | ctypes 構造体の整合, ライフサイクル | — |
| **Layer 4** | `tilib_sweep`     | パラメータスキャンの smoke | — |

Layer 1 がこのライブラリの **生命線** です (`feedback_equivalence_must_pass` 参照).

## 実行方法

### 1 つずつ個別に走らせる

```bash
bash test_run/run_tests.sh tilib_equivalence  # Layer 1 (最重要)
bash test_run/run_tests.sh tilib_c_abi        # Layer 2
bash test_run/run_tests.sh tilib_ffi          # Layer 3 (低レベル)
bash test_run/run_tests.sh tilib_wrapper      # Layer 3 (高レベル)
bash test_run/run_tests.sh tilib_sweep        # Layer 4
```

### まとめて走らせる (pytest 直接)

```bash
cd python/tilib
pytest --forked --timeout=120 --timeout-method=signal tests/
```

`--forked` は各テストを別プロセスで実行し, 共有 `pl_*` 状態の汚染を
防ぎます ({doc}`faq` Q2 のシングルトン制約と関連).

## Layer 1 (等価性テスト) の中身

`tilib_equivalence` は以下を実行します:

1. `Tilib()` で `libtiapi.so` をロード
2. Phase 0 fixture から登録済みパラメータを `set_param` で流し込む
3. fixture の `NTMAX` まで `run()` で時間発展
4. `TiState.to_dict()` で JSON 出力 (scalars + scalars_int + プロファイル)
5. `test_run/baselines/<case>/metrics.json` と diff (tolerance `1e-10`)

`tix2` バイナリと `libtiapi.so` 経由の結果が小数点 10 桁で一致するか
を見ています.

## よく使うファイル

- `python/tilib/tests/test_equivalence.py` — Layer 1
- `python/tilib/tests/test_tilib.py` — Layer 3 高レベル
- `python/tilib/tests/test_ffi.py` — Layer 3 低レベル
- `python/tilib/tests/test_sweep.py` — Layer 4
- `test_run/test_definitions.conf` — `tilib_*` 定義

## CI との関係

CI 上でも `--forked --timeout=120 --timeout-method=signal` で実行されます.
ローカルで失敗しているものを push しないのが鉄則です (`CLAUDE.md` の
pre-push gate 参照).

```{important}
**等価性テストを `@pytest.mark.skip` で回避するのは禁止**です.
修正できない場合は `@pytest.mark.xfail(strict=True, reason="#<issue>")` と
issue リンクを残してください.
```
