# ライブラリの応用例 (Python ラッパー)

`Tilib` を素のまま使うだけでなく, 上に薄いラッパーを被せると実用的に
なります. ここでは典型的な 3 パターンを示します.

```{admonition} このページの位置付け
:class: note

ここで紹介するのは **`tilib` を Python から使う応用パターン** です.
LLM クライアントから自然言語で操作するシナリオは {doc}`mcp` を
参照してください.
```

```{admonition} 実行前提 (ADPOST / ADF11 データ)
:class: warning

`ti.run()` は内部で ``../adpost/ADPOST-DATA`` と ``./ADF11-bin.data``
を参照します. レポジトリルート以外で動かすときは
``test_run/run_tests.sh`` の ``case ti)`` か
{doc}`testing` の ``TiDataCwdMixin`` を真似て, 作業ディレクトリの隣に
``adpost/ADPOST-DATA`` を, カレントに ``ADF11-bin.data`` を symlink
してください. 以下のサンプル実行値はこの配置で取得しています.
```

---

## 1. 自動安定化ラッパー

`run()` が `TilibRunError` (内部 ``ierr=3``) を返した場合に `DT` を
半分にして再試行するラッパーです. 大規模パラメータスイープで一部の
組合せが収束しない場合の受け皿に使えます.

```python
from tilib import TiLib
from tilib.errors import TilibRunError


class StableTiRunner:
    """`TiLib` を `with` で包み, run() 失敗時に DT を半減して再試行する.

    Parameters
    ----------
    max_retries : int
        DT を縮める試行回数の上限 (各試行で DT は半分になる).
    dt_floor : float
        DT がこれを下回ったら諦めて RuntimeError.
    """

    def __init__(self, *, max_retries: int = 5, dt_floor: float = 1.0e-5):
        self._ti = TiLib()
        self._ti.__enter__()
        self.dt = 0.01           # ti のデフォルト DT と同じ
        self.max_retries = max_retries
        self.dt_floor = dt_floor
        self.retries = 0

    def __enter__(self) -> "StableTiRunner":
        return self

    def __exit__(self, *args) -> None:
        self._ti.__exit__(*args)

    def configure(self, **params) -> None:
        """`set_params` 互換. DT を覚えておく."""
        self._ti.set_params(**params)
        if "DT" in params:
            self.dt = float(params["DT"])

    def run(self, ntmax: int):
        """run() が失敗したら DT を半減して再試行. 最終的に TiState を返す."""
        for attempt in range(self.max_retries):
            try:
                self._ti.run(ntmax=ntmax)
                return self._ti.get_state()
            except TilibRunError as e:
                if self.dt <= self.dt_floor:
                    raise RuntimeError(
                        f"DT={self.dt} まで縮めても安定化せず: {e}"
                    ) from e
                self.dt /= 2
                self._ti.set_param("DT", self.dt)
                self.retries += 1
                print(
                    f"  [retry] {e!r} → DT={self.dt:.2e} に縮めて再試行 "
                    f"({attempt + 1}/{self.max_retries})"
                )
        raise RuntimeError(
            f"{self.max_retries} 回試行しても安定化せず (最後の DT={self.dt})"
        )


# 使用例
with StableTiRunner() as runner:
    runner.configure(RR=3.0, BB=3.0, NSMAX=2, DT=0.01)
    state = runner.run(ntmax=10)
    print(f"完走: T={state.T:.3f}s, "
          f"T0={state.RTA[0][0]:.3f}keV, "
          f"再試行数={runner.retries}")
```

期待される出力 (上記パラメータでは安定なので再試行は走りません):

```
完走: T=0.100s, T0=4.999keV, 再試行数=0
```

数値発散しがちな組合せ (例: 極端に小さい `BB`, 大きな `DT`) では `[retry]`
ログが混じり, `再試行数` が 1 以上になります:

```
[retry] TilibRunError(...) → DT=5.00e-03 に縮めて再試行 (1/5)
完走: T=..., T0=..., 再試行数=1
```

### 拡張案

- `EPSLOOP` や `MAXLOOP` も併せて緩める / 増やす
- `NTMAX` を分割して, 安定化点を抜けたら `DT` を元に戻す
- 失敗履歴を `failures: list[dict]` に蓄積して後で分析

---

## 2. パラメータスイープラッパー

`RR × BB` のような格子状スキャンを行い, 結果を辞書のリストに集約します.
`NSMAX=2` のままなら デフォルトの ``PA / PZ / PN / PT`` シードが効くため
追加設定は不要です. `StableTiRunner` と組合せれば一部失敗ケースも
自動回避.

```python
import itertools
from tilib import TiLib


def sweep(
    *,
    rr_values: list[float],
    bb_values: list[float],
    ntmax: int = 10,
    fixed_params: dict | None = None,
) -> list[dict]:
    """RR × BB の格子スキャン. 各点で TI を 1 セッション独立実行.

    Returns
    -------
    各点の {RR, BB, T, T0, n0, residual, iters, error} のリスト
    (T0 = 中心電子温度 RTA[0][0], n0 = 中心電子密度 RNA[0][0])
    """
    fixed = fixed_params or {"NSMAX": 2}
    results = []
    for rr, bb in itertools.product(rr_values, bb_values):
        row = {"RR": rr, "BB": bb}
        try:
            with TiLib() as ti:
                ti.set_params(RR=rr, BB=bb, **fixed)
                ti.run(ntmax=ntmax)
                state = ti.get_state()
            row.update(
                T=state.T,
                T0=state.RTA[0][0] if state.RTA else None,
                n0=state.RNA[0][0] if state.RNA else None,
                residual=state.residual_loop_max,
                iters=state.icount_loop_max,
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
    ntmax=10,
)
for r in results:
    print(r)
```

期待される出力（抜粋, `T` の単位は s, `T0` は keV, `n0` は 10²⁰ m⁻³）:

```text
{'RR': 3.0, 'BB': 3.0, 'T': 0.1, 'T0': 4.9995, 'n0': 0.9986, 'residual': 0.0, 'iters': 0, ...}
{'RR': 5.0, 'BB': 5.0, 'T': 0.1, 'T0': 4.9995, 'n0': 0.9986, 'residual': 0.0, 'iters': 0, ...}
{'RR': 6.5, 'BB': 7.0, 'T': 0.1, 'T0': 4.9995, 'n0': 0.9986, 'residual': 0.0, 'iters': 0, ...}
```

```{admonition} 注: デフォルト設定では RR / BB 感度が小さい
:class: tip

`NSMAX=2` の最小セットでは加熱・電流駆動・新古典輸送がすべて
``MODEL_*=0`` (off) で動くため, 中心 ``T0/n0`` は ``RR``, ``BB``
にほとんど依存しません. 物理感度を見るには ``MODEL_NB``, ``MODEL_NC``
等を有効化するか, ``ti_ar`` のような重不純物セットアップに切替えて
ください ({doc}`parameters` 参照).
```

### 拡張案

- 結果を `pandas.DataFrame` に流し込んでヒートマップに
- `multiprocessing.Pool` で複数プロセス並列化
  ({doc}`faq` のシングルトン制約より, **プロセスごとに独立な `TiLib`
  インスタンス** になるので並列化が有効)
- `StableTiRunner` を中で使って失敗自動回避

---

## 3. validate 駆動セットアップ + 多粒子種ヘルパー

`ti` には `tr` / `eq` のような native `validate()` がまだありません.
そこで Python 側で hand-rolled な検査関数を組み, さらに 1-origin 配列
``PA[i] / PZ[i] / PN[i] / PT[i]`` を覚えなくても済むよう
**species 辞書 → 配列展開ヘルパー** をかぶせます.

```python
from tilib import TiLib


# 装置プリセット (ti は equilibrium 解を持たないため RIP 系は不要).
DEVICE_PRESETS = {
    "ITER":  dict(RR=6.2,  BB=5.3),
    "JET":   dict(RR=2.96, BB=3.4),
    "DIIID": dict(RR=1.67, BB=2.1),
}


# Species プリセット. キーは 1-origin の NS 番号.
# 1: 電子, 2: 主イオン, 3+: 不純物.
# (n は 10²⁰ m⁻³, T は keV)
SPECIES_PRESETS = {
    "DD": {
        1: {"A": 0.0005486, "Z": -1.0, "n": 1.0,  "T": 5.0},   # e
        2: {"A": 2.0,       "Z":  1.0, "n": 1.0,  "T": 5.0},   # D
    },
    "DT_with_C": {
        1: {"A": 0.0005486, "Z": -1.0, "n": 1.0,    "T": 5.0},  # e
        2: {"A": 2.5,       "Z":  1.0, "n": 0.475,  "T": 5.0},  # D+T 平均
        3: {"A": 12.0,      "Z":  6.0, "n": 0.05/6, "T": 5.0},  # C
    },
}


def _apply_species(ti: TiLib, species: dict[int, dict[str, float]]) -> None:
    """``{ns: {'A','Z','n','T'}}`` 形式の辞書を ``PA[i]/PZ[i]/PN[i]/PT[i]``
    の 1-origin 配列に展開して TiLib に流し込む.

    1-origin の subscript syntax (``PA[1]`` = 電子, ``PA[2]`` = 主イオン)
    を呼び出し側に意識させないためのヘルパー. ``set_params(**kwargs)`` は
    Python 識別子の制約で ``PA[1]`` を受けられないので ``set_param`` を
    順次呼ぶ.
    """
    for ns, sp in species.items():
        ti.set_param(f"PA[{ns}]", sp["A"])
        ti.set_param(f"PZ[{ns}]", sp["Z"])
        ti.set_param(f"PN[{ns}]", sp["n"])
        ti.set_param(f"PT[{ns}]", sp["T"])


def hand_validate(
    species: dict[int, dict[str, float]],
    nsmax: int,
) -> list[tuple[str, str]]:
    """``ti`` には native validate が無いので, よくあるミスを Python 側で検査.

    返り値は ``(対象, メッセージ)`` のリスト. 空なら問題なし.

    検査項目:
      * ``NSMAX >= 1``
      * ``len(species) == NSMAX``
      * 各 species 辞書に ``A / Z / n / T`` が全て存在
      * Species 番号が 1-origin で連続している (1, 2, ..., NSMAX)
    """
    diags: list[tuple[str, str]] = []
    if nsmax < 1:
        diags.append(("NSMAX", f"NSMAX={nsmax} は 1 未満"))
    if len(species) != nsmax:
        diags.append(
            ("species",
             f"species 数 ({len(species)}) が NSMAX ({nsmax}) と一致しない")
        )
    expected_keys = set(range(1, nsmax + 1))
    if set(species.keys()) != expected_keys:
        diags.append(
            ("species",
             f"species キーは {sorted(expected_keys)} を期待 "
             f"(1-origin 連続); 実際: {sorted(species.keys())}")
        )
    for ns, sp in species.items():
        for k in ("A", "Z", "n", "T"):
            if k not in sp:
                diags.append((f"species[{ns}]", f"必須キー {k!r} が欠落"))
    return diags


def auto_setup(
    device: str = "ITER",
    species_preset: str = "DD",
    extra_params: dict | None = None,
) -> TiLib:
    """装置プリセット + species プリセットで TI を初期化し, hand-rolled
    validate でセルフチェック.

    Returns
    -------
    既に init + set_params + validate 済みの TiLib インスタンス
    (呼び出し側が `with` か `try/finally` で終了処理).
    """
    ti = TiLib()
    try:
        ti.__enter__()
        # 1. プリセット適用 (装置スカラー)
        params = DEVICE_PRESETS[device].copy()
        species = SPECIES_PRESETS[species_preset]
        params["NSMAX"] = len(species)
        params.update(extra_params or {})
        ti.set_params(**params)

        # 2. Species 配列を 1-origin 展開
        _apply_species(ti, species)

        # 3. hand-rolled validate
        diags = hand_validate(species, params["NSMAX"])
        if diags:
            print(f"検出された問題 ({len(diags)} 件):")
            for who, msg in diags:
                print(f"  [{who}] {msg}")
            raise RuntimeError(
                f"修正が必要な問題が {len(diags)} 件あります"
            )
        return ti
    except Exception:
        ti.__exit__(None, None, None)
        raise


# 使用例
with auto_setup("ITER", species_preset="DD") as ti:
    ti.run(ntmax=10)
    s = ti.get_state()
    print(f"T={s.T:.3f}s  T0={s.RTA[0][0]:.3f}keV  n0={s.RNA[0][0]:.4f}")
```

期待される出力 (ITER + DD プリセット, `ntmax=10`):

```text
T=0.100s  T0=4.999keV  n0=0.9986
```

`species_preset="DT_with_C"` を選べば 3 種混合 (e + D/T + C) になります:

```text
T=0.050s  T0=4.999keV  n0=0.9997
```

`species` 辞書のキーが歯抜けの場合 (例: ``{1: {...}, 3: {...}}``) は
validate で検出されます:

```text
検出された問題 (1 件):
  [species] species キーは [1, 2] を期待 (1-origin 連続); 実際: [1, 3]
RuntimeError: 修正が必要な問題が 1 件あります
```

### 拡張案

- プリセットを `iter_baseline.toml` 等の外部ファイルから読む
- ``MODEL_NB`` / ``MODEL_NC`` 等のスイッチ群もプリセット化する
- 不純物セットなら ``NPA[i] / ID_NS[i] / NZMIN_NS[i] / NZMAX_NS[i]`` も
  ``_apply_species`` に拡張 (Ar セットアップは ``examples/parameter_sweep.py``
  が参考)
- LLM から呼ぶときは, validate の出力をそのまま LLM に渡せば修正提案が
  返ってくる ({doc}`mcp` 参照)

---

## 組合せパターン

3 つは個別にも組合せても使えます:

| 組合せ | 効果 |
|---|---|
| **スイープ + 安定化** | `sweep()` の中で `StableTiRunner` を使うと, 数値発散する点も自動回避 |
| **auto_setup + スイープ** | `auto_setup` でベース設定 → `RR × BB` 等を振る |
| **3 つ全部** | 装置プリセットを起点にした安定スイープ. 大規模解析の標準パターン |

各モジュール (`tr`, `eq`, `fp`, `wr`, `wrx`, `tot`) でも同じパターンが
適用できます. 物理量とエラー型 (`TrlibRunError`, `WrlibRunError`,
`EqlibInvalidParamError` など) を読み替えてください.
