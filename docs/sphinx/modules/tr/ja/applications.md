# ライブラリの応用例 (Python ラッパー)

`Trlib` を素のまま使うだけでなく, 上に薄いラッパーを被せると実用的に
なります. ここでは典型的な 3 パターンを示します.

```{admonition} このページの位置付け
:class: note

ここで紹介するのは **`trlib` を Python から使う応用パターン** です.
LLM クライアントから自然言語で操作するシナリオは {doc}`mcp` の
「使用シナリオ」節を参照してください.
```

---

## 1. 自動安定化ラッパー

`run()` が `TrlibRunError` を返した場合に `DT` を半分にして再試行する
ラッパーです. 大規模パラメータスイープで一部の組合せが収束しない場合の
受け皿に使えます.

```python
from trlib import Trlib
from trlib.errors import TrlibRunError


class StableTrRunner:
    """`Trlib` を `with` で包み, run() 失敗時に DT を半減して再試行する.

    Parameters
    ----------
    max_retries : int
        DT を縮める試行回数の上限 (各試行で DT は半分になる).
    dt_floor : float
        DT がこれを下回ったら諦めて RuntimeError.
    """

    def __init__(self, *, max_retries: int = 5, dt_floor: float = 1.0e-5):
        self._tr = Trlib()
        self._tr.__enter__()
        self.dt = 0.01
        self.max_retries = max_retries
        self.dt_floor = dt_floor
        self.retries = 0

    def __enter__(self) -> "StableTrRunner":
        return self

    def __exit__(self, *args) -> None:
        self._tr.__exit__(*args)

    def configure(self, **params) -> None:
        """`set_params` 互換. DT を覚えておく."""
        self._tr.set_params(**params)
        if "DT" in params:
            self.dt = float(params["DT"])

    def run(self, ntmax: int):
        """run() が失敗したら DT を半減して再試行. 最終的に TrState を返す."""
        for attempt in range(self.max_retries):
            try:
                self._tr.run(ntmax=ntmax)
                return self._tr.get_state()
            except TrlibRunError as e:
                if self.dt <= self.dt_floor:
                    raise RuntimeError(
                        f"DT={self.dt} まで縮めても安定化せず: {e}"
                    ) from e
                self.dt /= 2
                self._tr.set_param("DT", self.dt)
                self.retries += 1
                print(
                    f"  [retry] {e!r} → DT={self.dt:.2e} に縮めて再試行 "
                    f"({attempt + 1}/{self.max_retries})"
                )
        raise RuntimeError(
            f"{self.max_retries} 回試行しても安定化せず (最後の DT={self.dt})"
        )


# 使用例
with StableTrRunner() as runner:
    runner.configure(RR=3.0, BB=3.0, NSMAX=2, DT=0.01, NTMAX=100)
    state = runner.run(ntmax=100)
    print(f"完走: T={state.scalars['T']:.3f}s, "
          f"BETAN={state.scalars['BETAN']:.3f}, "
          f"再試行数={runner.retries}")
```

期待される挙動:

```
[retry] TrlibRunError(...) → DT=5.00e-03 に縮めて再試行 (1/5)
完走: T=0.500s, BETAN=0.42, 再試行数=1
```

### 拡張案

- `EPSLTR` や `LMAXTR` も併せて緩める / 増やす
- `NTMAX` を分割して, 安定化点を抜けたら `DT` を元に戻す
- 失敗履歴を `failures: List[Dict]` に蓄積して後で分析

---

## 2. パラメータスイープラッパー

`RR × BB` のような格子状スキャンを行い, 結果を辞書のリストに集約します.
`StableTrRunner` と組合せれば一部失敗ケースも自動回避.

```python
import itertools
from typing import List, Dict
from trlib import Trlib


def sweep(
    *,
    rr_values: List[float],
    bb_values: List[float],
    ntmax: int = 10,
    fixed_params: Dict | None = None,
) -> List[Dict]:
    """RR × BB の格子スキャン. 各点で TR を 1 セッション独立実行.

    Returns
    -------
    各点の {RR, BB, T, WPT, BETAN, TAUE1, error} のリスト
    """
    fixed = fixed_params or {"NSMAX": 2}
    results = []
    for rr, bb in itertools.product(rr_values, bb_values):
        row = {"RR": rr, "BB": bb}
        try:
            with Trlib() as tr:
                tr.set_params(RR=rr, BB=bb, **fixed)
                tr.run(ntmax=ntmax)
                state = tr.get_state()
            row.update(
                T=state.scalars["T"],
                WPT=state.scalars["WPT"],
                BETAN=state.scalars["BETAN"],
                TAUE1=state.scalars["TAUE1"],
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
    ntmax=20,
)
for r in results:
    print(r)
```

期待される出力（抜粋）:

```text
{'RR': 3.0, 'BB': 3.0, 'T': 0.2, 'WPT': 8.3e+05, 'BETAN': 0.42, ...}
{'RR': 6.5, 'BB': 5.3, 'T': 0.2, 'WPT': 3.1e+06, 'BETAN': 0.85, ...}
```

### 拡張案

- 結果を `pandas.DataFrame` に流し込んでヒートマップに
- `multiprocessing.Pool` で複数プロセス並列化
  ({doc}`faq` Q4 のシングルトン制約より, **プロセスごとに独立な `Trlib` インスタンス**
  になるので並列化が有効)
- `StableTrRunner` を中で使って失敗自動回避

---

## 3. validate 駆動セットアップ

`validate()` の出力を見ながら, 共通的なミスを自動検出 / 自動補完する関数
です. `run()` の前にユーザ入力を「サニタイズ」する用途.

```python
from trlib import Trlib, TrDiagCode


# 装置プリセット
DEVICE_PRESETS = {
    "ITER": dict(RR=6.2, RA=2.0, BB=5.3, RIP=15.0, RKAP=1.7, RDLT=0.5),
    "JET":  dict(RR=2.96, RA=1.0, BB=3.4, RIP=4.0, RKAP=1.6, RDLT=0.3),
    "DIIID": dict(RR=1.67, RA=0.67, BB=2.1, RIP=2.0, RKAP=1.8, RDLT=0.4),
}


def auto_setup(
    device: str = "ITER",
    extra_params: Dict | None = None,
    eq_file: str | None = None,
) -> Trlib:
    """装置プリセットで TR を初期化し validate でセルフチェック.

    Returns
    -------
    既に init + set_params + validate 済みの Trlib インスタンス
    (呼び出し側が `with` か `try/finally` で終了処理).
    """
    tr = Trlib()
    try:
        tr.__enter__()
        # 1. プリセット適用
        params = DEVICE_PRESETS[device].copy()
        params.update(NSMAX=2, DT=0.01, NTMAX=100)
        params.update(extra_params or {})
        tr.set_params(**params)

        # 2. EQDSK 経由なら KNAMEQ を必須としてセット
        if params.get("MODELG") in (3, 5, 7, 8) and eq_file:
            tr.set_param_str("KNAMEQ", eq_file)

        # 3. validate でチェック
        diags = tr.validate()
        if diags:
            print(f"検出された問題 ({len(diags)} 件):")
            for d in diags:
                code = TrDiagCode(d.code).name
                print(f"  [{code}] {d.param}: {d.message}")
            blocking = [d for d in diags
                        if d.code in (TrDiagCode.FILE_MISSING,
                                      TrDiagCode.MISSING_REQUIRED)]
            if blocking:
                raise RuntimeError(
                    f"修正が必要な問題が {len(blocking)} 件残っています"
                )
        return tr
    except Exception:
        tr.__exit__(None, None, None)
        raise


# 使用例
with auto_setup("ITER") as tr:
    tr.run(ntmax=10)
    state = tr.get_state()
    print(f"BETAN = {state.scalars['BETAN']:.3f}")
```

期待される出力:

```text
BETAN = 0.852
```

`MODELG=3` を指定したのに `eq_file=None` だった場合:

```text
検出された問題 (1 件):
  [FILE_MISSING] KNAMEQ: MODELG=3/5/7/8 requires non-blank KNAMEQ ...
RuntimeError: 修正が必要な問題が 1 件残っています
```

### 拡張案

- プリセットを `iter_baseline.toml` 等の外部ファイルから読む
- `OUT_OF_RANGE` の自動クランプ (例: `NSMAX=10` → `NSMAX=8` に丸める)
- LLM から呼ぶときは, validate の出力をそのまま LLM に渡せば修正提案が
  返ってくる ({doc}`mcp` の「使用シナリオ」参照)

---

## 組合せパターン

3 つは個別にも組合せても使えます:

| 組合せ | 効果 |
|---|---|
| **スイープ + 安定化** | `sweep()` の中で `StableTrRunner` を使うと, 数値発散する点も自動回避 |
| **validate セットアップ + スイープ** | `auto_setup` でベース設定 → `RR × BB` 等を振る |
| **3 つ全部** | 装置プリセットを起点にした安定スイープ. 大規模解析の標準パターン |

各モジュール (`eq`, `ti`, `fp`, `wr`, `wrx`, `tot`) でも同じパターンが
適用できます. 物理量とエラー型 (`EqlibInvalidParamError`, `WrlibRunError`
など) を読み替えてください.
