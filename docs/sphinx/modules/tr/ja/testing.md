# テスト

`tr` ライブラリには **4 層の回帰テスト** が用意されています. 各層で何を
検証しているかを具体的に説明します.

## 4 層の役割

| 層 | ターゲット | 何を検証するか | tolerance |
|---|---|---|---|
| **Layer 1** | `trlib_equivalence` | `libtrapi.so` の出力が Phase 0 の Fortran ベースライン (`tr2` CLI 版) と完全一致すること | **1e-10** (厳守) |
| **Layer 2** | `trlib_c_abi`      | C ABI 5 関数が正しい ierr を返すこと (smoke / 正常系 / 異常系) | — |
| **Layer 3** | `trlib_ffi`, `trlib_wrapper` | `_ffi.py` の ctypes 構造体が C 側とバイト単位で一致すること, `Trlib` クラスの `__enter__`/`__exit__` 等ライフサイクルが正しいこと | — |
| **Layer 4** | `trlib_sweep`     | `RR`×`BB` を振った 3×3 = 9 ケースで `run()` が落ちないこと (smoke) | — |

Layer 1 がこのライブラリの **生命線** です. 1e-10 で合わないとリリースでき
ません (`feedback_equivalence_must_pass` 参照).

## 実行方法

### 1 つずつ個別に走らせる

```bash
bash test_run/run_tests.sh trlib_equivalence  # Layer 1 (最重要)
bash test_run/run_tests.sh trlib_c_abi        # Layer 2
bash test_run/run_tests.sh trlib_ffi          # Layer 3 (低レベル)
bash test_run/run_tests.sh trlib_wrapper      # Layer 3 (高レベル)
bash test_run/run_tests.sh trlib_sweep        # Layer 4
```

### まとめて走らせる (pytest 直接)

```bash
cd python/trlib
pytest --forked --timeout=120 --timeout-method=signal tests/
```

`--forked` は各テストを別プロセスで実行するフラグで, `tr_init` を繰り返す
テストが互いの Fortran モジュール状態を汚染するのを防ぎます
({doc}`faq` Q4 の shingleton 制約の理由もこれ).

## Layer 1 (等価性テスト) の中身

`trlib_equivalence` は以下を 2 ケース (`tr_iter01`, `tr_tst2`) で行います:

1. `Trlib()` で `libtrapi.so` をロード
2. Phase 0 fixture (`test_run/fixtures/<case>.nml`) から登録済みパラメータを
   `set_param` / `set_param_str` で流し込む
3. fixture の `NTMAX` まで `run()` で時間発展
4. `TrState.to_dict()` で JSON 出力
5. `test_run/baselines/<case>/metrics.json` と `compare_metrics.py` で diff
   (tolerance `1e-10`)

つまり「 `tr2` バイナリで出した結果と, `libtrapi.so` 経由で出した結果が,
最終時刻・全プロファイル・全スカラーにわたって小数点 10 桁で一致するか」
を見ています. 1 桁でもずれれば FAIL.

```{admonition} eqdata ファイル
:class: note

`MODELG=3` の `tr_iter01` / `tr_tst2` は `eqdata.ITER01` などのファイルを
カレントディレクトリから読むので, テストは `test_run/test_output/<case>/`
に `cd` してから実行されます. このファイルが無い環境ではスキップされます.
```

## よく使うファイル

- `python/trlib/tests/test_equivalence.py` — Layer 1
- `python/trlib/tests/test_trlib.py` — Layer 3 高レベル
- `python/trlib/tests/test_ffi.py` — Layer 3 低レベル
- `python/trlib/tests/test_sweep.py` — Layer 4
- `python/trlib/tests/test_validate.py` — PR #172 の `validate` API
- `test_run/fixtures/` — namelist / JSON fixture
- `test_run/baselines/<case>/metrics.json` — Phase 0 ベースライン
- `test_run/test_definitions.conf` — ターゲット定義 (`trlib_*`)

## CI との関係

CI 上でも同じフラグ (`--forked --timeout=120 --timeout-method=signal`) で
実行されます. ローカルで失敗しているものを push しないのが鉄則です
(`CLAUDE.md` の pre-push gate 参照).

```{important}
**等価性テストを `@pytest.mark.skip` で回避するのは禁止**です.
修正できない場合は `@pytest.mark.xfail(strict=True, reason="#<issue>")` と
issue リンクを残してください.
```
