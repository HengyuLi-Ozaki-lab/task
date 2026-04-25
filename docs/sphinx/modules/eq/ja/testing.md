# テスト

`eq` ライブラリには **4 層の回帰テスト** が用意されています. 各層で何を
検証しているかを具体的に説明します.

## 4 層の役割

| 層 | ターゲット | 何を検証するか | tolerance |
|---|---|---|---|
| **Layer 1** | `eqlib_equivalence` | `libeqapi.so` の出力が Phase 0 の Fortran ベースライン (`eqx2` バイナリ) と完全一致すること | **1e-10** (厳守) |
| **Layer 2** | `eqlib_c_abi`      | C ABI 6 関数 + `eq_validate` が正しい ierr を返すこと | — |
| **Layer 3** | `eqlib_ffi`, `eqlib_wrapper` | `_ffi.py` の ctypes 構造体が C 側とバイト単位で一致, `Eq` クラスのライフサイクル正常性 | — |
| **Layer 4** | `eqlib_sweep`     | `RR`×`BB` を振った 3×3 = 9 ケースで `run()` が落ちないこと (smoke) | — |

Layer 1 がこのライブラリの **生命線** です. 1e-10 で合わないとリリース
できません (`feedback_equivalence_must_pass` 参照).

```{note}
Layer 1 と Layer 4 は **`EQ_RUN_OK` ゲート** が立っていないと skip されます.
これは EQDSK ファイルなど eq に固有の前提が揃っているかを確認するための
環境変数です. `bash test_run/run_tests.sh` 経由で自動判定されます.
```

## 実行方法

### 1 つずつ個別に走らせる

```bash
bash test_run/run_tests.sh eqlib_equivalence  # Layer 1 (最重要)
bash test_run/run_tests.sh eqlib_c_abi        # Layer 2
bash test_run/run_tests.sh eqlib_ffi          # Layer 3 (低レベル)
bash test_run/run_tests.sh eqlib_wrapper      # Layer 3 (高レベル)
bash test_run/run_tests.sh eqlib_sweep        # Layer 4
```

### まとめて走らせる (pytest 直接)

```bash
cd python/eqlib
pytest --forked --timeout=120 --timeout-method=signal tests/
```

`--forked` は各テストを別プロセスで実行するフラグで, `eq_init` を繰り返す
テストが互いの Fortran モジュール状態を汚染するのを防ぎます
({doc}`faq` Q6 のシングルトン制約と関連). `eqfini` の SAVE フラグ
リセット処理 (issue #110, PR #163) も `--forked` 前提で設計されています.

## Layer 1 (等価性テスト) の中身

`eqlib_equivalence` は以下を 2 ケース (`eq_iter01`, `eq_tst2`) で行います:

1. `Eq()` で `libeqapi.so` をロード
2. Phase 0 fixture から登録済みパラメータを `set_param` / `set_param_str`
   で流し込む (`KNAMEQ` 含む)
3. `eq.run(mode=1)` で平衡を解く
4. `EqState.to_dict()` で JSON 出力
5. `test_run/baselines/<case>/metrics.json` と `compare_metrics.py` で
   diff (tolerance `1e-10`)

つまり「`eqx2` バイナリで出した結果と, `libeqapi.so` 経由で出した結果が,
ψ-面プロファイル全体・全スカラーにわたって小数点 10 桁で一致するか」を
見ています. 1 桁でもずれれば FAIL.

```{admonition} eqdata ファイル
:class: note

`MODELG=3` の `eq_iter01` / `eq_tst2` は `eqdata.ITER01` などのファイルを
カレントディレクトリから読むので, テストは `test_run/test_output/<case>/`
に `cd` してから実行されます. このファイルが無い環境ではスキップ
(`EQ_RUN_OK=0`) されます.
```

## Layer 4 (sweep) の中身

`eqlib_sweep` は以下を実行します:

- `RR ∈ {6.0, 6.5, 7.0}`, `BB ∈ {3.0, 5.0, 5.3}` の 9 通り
- 各組合せで `eq.run(mode=1)` が `ierr=0` を返すか
- `EqState.scalars["raxis"]` などが NaN/Inf にならないか

数値結果の正確さは検証しません. 「未知のパラメータ組合せでクラッシュしない
か」のスモークテストです.

## よく使うファイル

- `python/eqlib/tests/test_equivalence.py` — Layer 1
- `python/eqlib/tests/test_eqlib.py` — Layer 3 高レベル
- `python/eqlib/tests/test_ffi.py` — Layer 3 低レベル
- `python/eqlib/tests/test_sweep.py` — Layer 4
- `python/eqlib/tests/test_validate.py` — PR #164 の `validate` API
- `test_run/fixtures/` — namelist / JSON fixture
- `test_run/baselines/<case>/metrics.json` — Phase 0 ベースライン
- `test_run/test_definitions.conf` — ターゲット定義 (`eqlib_*`)

## CI との関係

CI 上でも同じフラグ (`--forked --timeout=120 --timeout-method=signal`) で
実行されます. ローカルで失敗しているものを push しないのが鉄則です
(`CLAUDE.md` の pre-push gate 参照).

```{important}
**等価性テストを `@pytest.mark.skip` で回避するのは禁止**です.
修正できない場合は `@pytest.mark.xfail(strict=True, reason="#<issue>")` と
issue リンクを残してください.
```
