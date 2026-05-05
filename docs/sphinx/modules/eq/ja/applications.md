# ライブラリの応用例 (Python ラッパー)

`Eq` を素のまま使うだけでなく, 上に薄いラッパーを被せると実用的に
なります. ここでは典型的な 3 パターンを示します.

```{admonition} このページの位置付け
:class: note

ここで紹介するのは **`eqlib` を Python から使う応用パターン** です.
LLM クライアントから自然言語で操作するシナリオは {doc}`mcp` を
参照してください.
```

---

## 1. mode 自動選択ラッパー

`eq.run()` には 2 つの経路があります ({doc}`hello-world` 参照):

- `mode=0`: 解析 Grad-Shafranov 解 (`MODELG=2`, EQDSK 不要)
- `mode=1`: EQDSK ファイルを読込 (`MODELG ∈ {3, 5, 8}` + `KNAMEQ`)

ユーザが EQDSK ファイルパスを指定したか否かで自動的に切替えるラッパー.

```python
from pathlib import Path
from eqlib import Eq


def smart_run(eq: Eq, *, eqdsk_file: str | None = None) -> None:
    """EQDSK ファイル指定の有無で mode=0 / mode=1 を切替.

    eqdsk_file が指定されていればファイル読込 (mode=1),
    指定されていなければ解析解 (mode=0) を実行.
    """
    if eqdsk_file is None:
        # 解析 GS 解: MODELG=2 (デフォルト) を確認するだけ
        eq.set_param("MODELG", 2)
        eq.run(mode=0)
    else:
        # EQDSK 読込: ファイル存在確認 + MODELG=3 + KNAMEQ
        if not Path(eqdsk_file).exists():
            raise FileNotFoundError(f"EQDSK file not found: {eqdsk_file}")
        eq.set_param("MODELG", 3)
        eq.set_param_str("KNAMEQ", eqdsk_file)
        eq.run(mode=1)


# 使用例 (解析解)
with Eq() as eq:
    eq.set_params(RR=3.0, RA=1.0, BB=3.0, RIP=1.5)
    smart_run(eq)
    s = eq.get_state().scalars
    print(f"raxis={s['raxis']:.4f}  qaxis={s['qaxis']:.4f}")
```

期待される出力:

```text
raxis=3.0709  qaxis=0.9918
```

EQDSK ファイルを渡す場合は:

```python
with Eq() as eq:
    eq.set_params(RR=6.2, RA=2.0, BB=5.3, RIP=15.0)
    smart_run(eq, eqdsk_file="eqdata.ITER01")
    ...
```

### 拡張案

- `KNAMEQ` から `MODELG` を推測する逆方向 (例: `.eqdsk` 拡張子なら 3,
  `.vmec` なら 7) のロジックを追加
- `eqdsk_file=None` のとき, 与えられた装置パラメータが解析解で安定に
  解けるか軽い preflight (kappa, delta が極端でないか) を入れる

---

## 2. パラメータスイープラッパー

`RR × BB` のような格子状スキャンを行い, 結果を辞書のリストに集約します.
解析 GS 解 (`mode=0`) なので各点が高速 (~50ms 程度).

```python
import itertools
from eqlib import Eq


def sweep(
    *,
    rr_values: list[float],
    bb_values: list[float],
    fixed_params: dict | None = None,
) -> list[dict]:
    """RR × BB の格子スキャン. 各点で eq を 1 セッション独立実行.

    Returns
    -------
    各点の {RR, BB, raxis, qaxis, qsurf, betap, error} のリスト
    """
    fixed = fixed_params or {"RA": 1.0, "RIP": 1.5}
    results = []
    for rr, bb in itertools.product(rr_values, bb_values):
        row = {"RR": rr, "BB": bb}
        try:
            with Eq() as eq:
                eq.set_params(RR=rr, BB=bb, **fixed)
                eq.run(mode=0)
                state = eq.get_state()
            row.update(
                raxis=state.scalars["raxis"],
                qaxis=state.scalars["qaxis"],
                qsurf=state.scalars["qsurf"],
                betap=state.scalars["betap"],
                error=None,
            )
        except Exception as e:
            row["error"] = repr(e)
        results.append(row)
    return results


# 使用例
results = sweep(
    rr_values=[3.0, 5.0, 6.5],
    bb_values=[3.0, 5.0, 7.0],
)
for r in results:
    if r.get("error"):
        print(f"  RR={r['RR']}, BB={r['BB']} -> ERROR")
    else:
        print(f"  RR={r['RR']}, BB={r['BB']}: "
              f"qaxis={r['qaxis']:.3f}, qsurf={r['qsurf']:.3f}")
```

期待される出力（抜粋）:

```text
  RR=3.0, BB=3.0: qaxis=0.992, qsurf=3.767
  RR=3.0, BB=7.0: qaxis=2.269, qsurf=8.789
  RR=5.0, BB=5.0: qaxis=1.003, qsurf=3.437
  RR=6.5, BB=3.0: qaxis=0.473, qsurf=1.555
  RR=6.5, BB=7.0: qaxis=1.082, qsurf=3.628
```

`qaxis × qsurf` の組合せから, 例えば `qaxis > 1` の領域 (古典的 sawtooth
不安定なし) を選別する用途に使えます.

### 拡張案

- 結果を `pandas.DataFrame` に流し込んでヒートマップに
- `RKAP × RDLT` (elongation × triangularity) のスキャンで形状最適化
- `multiprocessing.Pool` で複数プロセス並列化 ({doc}`faq` Q6 の
  シングルトン制約より, **プロセスごとに独立な `Eq` インスタンス**
  になるので並列化が有効)

---

## 3. validate 駆動セットアップ

`validate()` の出力を見ながら, 共通的なミスを自動検出 / 自動補完する関数
です. `run()` の前にユーザ入力を「サニタイズ」する用途.

```python
from eqlib import Eq, EqDiagCode


# 装置プリセット.
# eq は時間平均の equilibrium 解なので RIP は単一値で指定します.
# (tr の場合は時間依存電流のため RIPS / RIPE のペア)
DEVICE_PRESETS = {
    "ITER":  dict(RR=6.2,  RA=2.0,  BB=5.3, RIP=15.0, RKAP=1.7, RDLT=0.5),
    "JET":   dict(RR=2.96, RA=1.0,  BB=3.4, RIP=4.0,  RKAP=1.6, RDLT=0.3),
    "DIIID": dict(RR=1.67, RA=0.67, BB=2.1, RIP=2.0,  RKAP=1.8, RDLT=0.4),
}


def auto_setup(
    device: str = "ITER",
    extra_params: dict | None = None,
    eq_file: str | None = None,
) -> Eq:
    """装置プリセットで eq を初期化し validate でセルフチェック.

    Returns
    -------
    既に init + set_params + validate 済みの Eq インスタンス
    (呼び出し側が `with` か `try/finally` で終了処理).
    """
    eq = Eq()
    try:
        eq.__enter__()
        # 1. プリセット適用
        params = DEVICE_PRESETS[device].copy()
        # RB (壁半径) は RA より大きくする必要がある (デフォルト RB=1.2 の
        # ままだと RA を上げたときに EQMAGS が PAUSE する).
        params.setdefault("RB", params["RA"] * 1.2)
        params.update(extra_params or {})
        eq.set_params(**params)

        # 2. EQDSK 経由なら KNAMEQ を必須としてセット.
        #    eq_file が None なら KNAMEQ を明示的に空文字列にして
        #    validate の FILE_MISSING に拾わせる.
        if params.get("MODELG") in (3, 5, 8):
            eq.set_param_str("KNAMEQ", eq_file or "")

        # 3. validate でチェック
        diags = eq.validate()
        if diags:
            print(f"検出された問題 ({len(diags)} 件):")
            for d in diags:
                code = EqDiagCode(d.code).name
                print(f"  [{code}] {d.param}: {d.message}")
            blocking = [d for d in diags
                        if d.code in (EqDiagCode.FILE_MISSING,
                                      EqDiagCode.MISSING_REQUIRED)]
            if blocking:
                raise RuntimeError(
                    f"修正が必要な問題が {len(blocking)} 件残っています"
                )
        return eq
    except Exception:
        eq.__exit__(None, None, None)
        raise


# 使用例
with auto_setup("ITER") as eq:
    eq.run(mode=0)
    s = eq.get_state().scalars
    print(f"raxis={s['raxis']:.3f}  qaxis={s['qaxis']:.3f}  qsurf={s['qsurf']:.3f}")
```

期待される出力 (ITER プリセット):

```text
raxis=6.249  qaxis=0.596  qsurf=3.565
```

`MODELG=3` を指定したのに `eq_file=None` だった場合:

```text
検出された問題 (1 件):
  [FILE_MISSING] KNAMEQ: MODELG=3/5/8 requires non-blank KNAMEQ (eqdata file)
RuntimeError: 修正が必要な問題が 1 件残っています
```

`extra_params={"NRMAX": 9999}` のように compile-time 上限を超えた値:

```text
検出された問題 (1 件):
  [OUT_OF_RANGE] NRMAX: value 9999 exceeds compile-time maximum 1001
```

(`OUT_OF_RANGE` は blocking 対象外なので警告のみ. ブロックしたい場合は
`blocking` の判定式に追加.)

### 拡張案

- プリセットを `iter_baseline.toml` 等の外部ファイルから読む
- `OUT_OF_RANGE` の自動クランプ (例: `NRMAX=9999` → `NRMAX=1001` に丸める)
- LLM から呼ぶときは, validate の出力をそのまま LLM に渡せば修正提案が
  返ってくる ({doc}`mcp` 参照)

---

## 組合せパターン

3 つは個別にも組合せても使えます:

| 組合せ | 効果 |
|---|---|
| **mode 自動選択 + auto_setup** | `auto_setup` で装置プリセット → `smart_run` で mode 自動切替 |
| **sweep + auto_setup** | プリセットをベースに `RR × BB` や `RKAP × RDLT` を振る |
| **3 つ全部** | 装置プリセット起点の解析的形状スキャン. 設計検討の標準パターン |

各モジュール (`tr`, `ti`, `fp`, `wr`, `wrx`, `tot`) でも同じパターンが
適用できます. 物理量とエラー型 (`TrlibRunError`, `WrlibRunError` など)
を読み替えてください.
