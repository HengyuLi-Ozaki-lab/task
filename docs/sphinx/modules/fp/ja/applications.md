# ライブラリの応用例 (Python ラッパー)

`Fplib` を素のまま使うだけでなく, 上に薄いラッパーを被せると実用的に
なります. ここでは典型的な 3 パターンを示します.

```{admonition} このページの位置付け
:class: note

ここで紹介するのは **`fplib` を Python から使う応用パターン** です.
LLM クライアントから自然言語で操作するシナリオは {doc}`mcp` の
「使用シナリオ」節を参照してください.
```

---

## 1. 自動安定化ラッパー

`run()` が `FplibCalcFailedError` (Fokker-Planck 解の収束失敗 / オーバ
フロー. `FplibOverflowError` は同義のエイリアス) を返した場合に時間刻み
`DELT` を半分にして再試行するラッパーです. 大規模パラメータスイープで
一部の組合せが収束しない場合の受け皿に使えます.

```python
from fplib import Fplib
from fplib.errors import FplibCalcFailedError


class StableFpRunner:
    """`Fplib` を `with` で包み, run() 失敗時に DELT を半減して再試行する.

    Parameters
    ----------
    max_retries : int
        DELT を縮める試行回数の上限 (各試行で DELT は半分になる).
    delt_floor : float
        DELT がこれを下回ったら諦めて RuntimeError.
    """

    def __init__(self, *, max_retries: int = 5, delt_floor: float = 1.0e-6):
        self._fp = Fplib()
        self._fp.__enter__()
        self.delt = 1.0e-3
        self.max_retries = max_retries
        self.delt_floor = delt_floor
        self.retries = 0

    def __enter__(self) -> "StableFpRunner":
        return self

    def __exit__(self, *args) -> None:
        self._fp.__exit__(*args)

    def configure(self, **params) -> None:
        """`set_params` 互換. DELT を覚えておく."""
        self._fp.set_params(**params)
        if "DELT" in params:
            self.delt = float(params["DELT"])

    def run(self, ntmax: int):
        """run() が失敗したら DELT を半減して再試行. 最終的に FpState を返す."""
        for attempt in range(self.max_retries):
            try:
                self._fp.run(ntmax=ntmax)
                return self._fp.get_state()
            except FplibCalcFailedError as e:
                if self.delt <= self.delt_floor:
                    raise RuntimeError(
                        f"DELT={self.delt} まで縮めても収束せず: {e}"
                    ) from e
                self.delt /= 2
                self._fp.set_param("DELT", self.delt)
                self.retries += 1
                print(
                    f"  [retry] {e!r} → DELT={self.delt:.2e} に縮めて再試行 "
                    f"({attempt + 1}/{self.max_retries})"
                )
        raise RuntimeError(
            f"{self.max_retries} 回試行しても収束せず (最後の DELT={self.delt})"
        )


# 使用例
with StableFpRunner() as runner:
    runner.configure(RR=3.0, BB=3.0, NSMAX=1, NPMAX=50, NTHMAX=25, DELT=1.0e-3)
    state = runner.run(ntmax=5)
    print(
        f"完走: timefp={state.timefp:.4f}s, "
        f"RNT[0][0]={state.RNT[0][0]:.4f}, "
        f"RTT[0][0]={state.RTT[0][0]:.4f}, "
        f"再試行数={runner.retries}"
    )
```

期待される出力 (上記パラメータでは安定なので再試行は走りません):

```text
完走: timefp=0.0050s, RNT[0][0]=0.9546, RTT[0][0]=4.5545, 再試行数=0
```

数値発散しがちな組合せ (例: 大きな `DELT` で過渡的に Fokker-Planck 行列が
ill-conditioned になる場合) では `[retry]` ログが混じり, `再試行数` が
1 以上になります:

```text
  [retry] FplibCalcFailedError(...) → DELT=5.00e-04 に縮めて再試行 (1/5)
完走: timefp=..., RNT[0][0]=..., RTT[0][0]=..., 再試行数=1
```

```{admonition} なぜ `DELT` を縮めるのか
:class: note

`fp` の `run()` は `EPSFP` (収束判定閾値) と `LMAXFP` (反復上限) を持つ
非線形 Fokker-Planck ソルバです. 時間刻み `DELT` が大きすぎると 1 ステップ
内の変化量が大きくなり反復が `LMAXFP` 回内に収束しません.
半減すれば多くのケースで救えます. 速度空間メッシュ (`NPMAX`/`NTHMAX`)
が極端に粗いことが原因の場合は, 代わりに細メッシュ化を試してください.
```

### 拡張案

- `EPSFP` を緩めたり `LMAXFP` を増やすことで併せて再試行
- `NTMAX` を分割し, 安定領域に入ったら `DELT` を元に戻す
- 失敗履歴を `failures: List[Dict]` に蓄積して後で分析

---

## 2. パラメータスイープラッパー

`RR × BB` のような格子状スキャンを行い, 結果を辞書のリストに集約します.
`StableFpRunner` と組合せれば一部失敗ケースも自動回避.
モデルは `python/fplib/tests/test_sweep.py` の 3×3 スイープです.

```python
import itertools
from typing import List, Dict
from fplib import Fplib


def sweep(
    *,
    rr_values: List[float],
    bb_values: List[float],
    ntmax: int = 10,
    fixed_params: Dict | None = None,
) -> List[Dict]:
    """RR × BB の格子スキャン. 各点で fp を 1 セッション独立実行.

    Returns
    -------
    各点の {RR, BB, timefp, RNT0, RTT0, RWT_last, error} のリスト.
    `RNT0` は中心 (NR=1) の粒子数密度, `RWT_last` は端 (NR=NRMAX) の
    エネルギー密度.
    """
    fixed = fixed_params or {
        "NSMAX": 1, "NRMAX": 10, "NPMAX": 30, "NTHMAX": 30, "DELT": 1.0e-3,
    }
    results = []
    for rr, bb in itertools.product(rr_values, bb_values):
        row = {"RR": rr, "BB": bb}
        try:
            with Fplib() as fp:
                fp.set_params(RR=rr, BB=bb, **fixed)
                fp.run(ntmax=ntmax)
                state = fp.get_state()
            row.update(
                timefp=state.timefp,
                RNT0=state.RNT[0][0],
                RTT0=state.RTT[0][0],
                RWT_last=state.RWT[0][-1],
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
    if r.get("error"):
        print(f"  RR={r['RR']}, BB={r['BB']} -> ERROR")
    else:
        print(
            f"  RR={r['RR']}, BB={r['BB']}: "
            f"RNT[0]={r['RNT0']:.4f}, RWT[-1]={r['RWT_last']:.6f}"
        )
```

期待される出力 (抜粋):

```text
  RR=3.0, BB=3.0: RNT[0]=0.9985, RWT[-1]=0.105721
  RR=3.0, BB=5.0: RNT[0]=0.9985, RWT[-1]=0.105721
  RR=3.0, BB=7.0: RNT[0]=0.9985, RWT[-1]=0.105721
  RR=5.0, BB=5.0: RNT[0]=0.9985, RWT[-1]=0.105721
  RR=6.5, BB=7.0: RNT[0]=0.9985, RWT[-1]=0.105721
```

```{admonition} 9 点とも同じ値になる理由
:class: tip

`fp` は **速度空間 (運動量・ピッチ角) の Fokker-Planck 方程式** を解く
ソルバなので, 局所的な `(温度, 密度)` で律速され, 装置寸法 `RR` や磁場
強度 `BB` の影響を直接受けません. 上のスイープでは `PTPR` / `PN` を
固定しているため, 9 点とも同じ熱平衡分布に収束します. RR/BB の効果を
見たい場合は **MHD 平衡経由** (`MODELG=3` で eqdsk を渡す) や
**バウンス平均** (`MODEL_FOW=1`) を有効化するか, 物理量側の軸 (`PTPR`,
`PN`, `E0` など) を振ってください.
```

### 拡張案

- `PTPR × PN` (温度 × 密度) スイープに変えると Maxwellian モーメントが
  すぐ動くのでスイープのスモークテストとして有用
- 結果を `pandas.DataFrame` に流し込んでヒートマップに
- `multiprocessing.Pool` で複数プロセス並列化
  ({doc}`faq` のシングルトン制約より, **プロセスごとに独立な `Fplib`
  インスタンス** になるので並列化が有効)
- `StableFpRunner` を中で使って失敗自動回避

---

## 3. validate 駆動セットアップ

`fp` には `tr` / `eq` のような C ABI 経由の `validate()` がないため,
**ハンドロールで preflight チェック**を行うラッパーです. `run()` の
前にユーザ入力を「サニタイズ」する用途. 装置プリセット ITER / JET /
JT60SA を備えます.

```python
from typing import Dict, List, Tuple
from fplib import Fplib


# 装置プリセット.
# fp は Fokker-Planck ソルバなので RIP は単一値で指定します.
# (tr の場合は時間依存電流のため RIPS / RIPE のペア)
DEVICE_PRESETS = {
    "ITER":   dict(RR=6.2,  RA=2.0,  BB=5.3,  RIP=15.0, RKAP=1.7,  RDLT=0.5),
    "JET":    dict(RR=2.96, RA=1.0,  BB=3.4,  RIP=4.0,  RKAP=1.6,  RDLT=0.3),
    "JT60SA": dict(RR=2.97, RA=1.18, BB=2.25, RIP=5.5,  RKAP=1.95, RDLT=0.5),
}


def validate_fp_params(params: Dict) -> List[Tuple[str, str]]:
    """fp 入力を preflight チェックし `(param, message)` のリストを返す.

    `fp` には C ABI 経由の `validate()` がないので, 典型的なミスだけ
    ハンドロールで拾います:

    * `NSMAX >= 1` (粒子種が 1 つもないと fp_init が STOP)
    * `NPMAX > 5`, `NTHMAX > 5` (運動量・ピッチ角の解像度が低すぎると
      Fokker-Planck 演算子が無意味)
    * `NRMAX > 5` (径方向解像度が低すぎると分布関数の空間勾配が解けない)
    """
    diags: List[Tuple[str, str]] = []
    nsmax = int(params.get("NSMAX", 1))
    if nsmax < 1:
        diags.append(("NSMAX", f"NSMAX={nsmax} は 1 以上必要"))
    npmax = int(params.get("NPMAX", 50))
    if npmax <= 5:
        diags.append(("NPMAX",
                      f"NPMAX={npmax} は 6 以上推奨 (運動量空間の解像度不足)"))
    nthmax = int(params.get("NTHMAX", 25))
    if nthmax <= 5:
        diags.append(("NTHMAX",
                      f"NTHMAX={nthmax} は 6 以上推奨 (ピッチ角解像度不足)"))
    nrmax = int(params.get("NRMAX", 10))
    if nrmax <= 5:
        diags.append(("NRMAX",
                      f"NRMAX={nrmax} は 6 以上推奨 (径方向解像度不足)"))
    return diags


def auto_setup(
    device: str = "ITER",
    extra_params: Dict | None = None,
) -> Fplib:
    """装置プリセットで fp を初期化し validate_fp_params でセルフチェック.

    Returns
    -------
    既に init + set_params 済みの Fplib インスタンス
    (呼び出し側が `with` か `try/finally` で終了処理).
    """
    fp = Fplib()
    try:
        fp.__enter__()
        # 1. プリセット適用 + fp 既定の安全な mesh / 時間刻み
        params = DEVICE_PRESETS[device].copy()
        params.update(NSMAX=1, NPMAX=30, NTHMAX=30, NRMAX=10, DELT=1.0e-3)
        params.update(extra_params or {})

        # 2. ハンドロール preflight チェック
        diags = validate_fp_params(params)
        if diags:
            print(f"検出された問題 ({len(diags)} 件):")
            for name, msg in diags:
                print(f"  [INVALID] {name}: {msg}")
            raise RuntimeError(
                f"修正が必要な問題が {len(diags)} 件残っています"
            )

        # 3. パラメータ設定 (preflight 通過後)
        fp.set_params(**params)
        return fp
    except Exception:
        fp.__exit__(None, None, None)
        raise


# 使用例
with auto_setup("ITER") as fp:
    fp.run(ntmax=10)
    state = fp.get_state()
    print(
        f"timefp={state.timefp:.4f}s, "
        f"RNT[0][0]={state.RNT[0][0]:.4f}, "
        f"RTT[0][0]={state.RTT[0][0]:.4f}"
    )
```

期待される出力 (ITER プリセット, `ntmax=10`):

```text
timefp=0.0100s, RNT[0][0]=0.9985, RTT[0][0]=4.9807
```

`NPMAX=4` のように粗すぎる速度空間メッシュを渡した場合:

```text
検出された問題 (1 件):
  [INVALID] NPMAX: NPMAX=4 は 6 以上推奨 (運動量空間の解像度不足)
RuntimeError: 修正が必要な問題が 1 件残っています
```

```{admonition} `fp` 固有の preflight ポイント
:class: warning

- **`NSMAX < 1`**: `fp_init` 内部で停止 (CLAUDE.md 関連 issue #142,
  ライブラリ到達 `STOP` の代表例). preflight で必ず弾いてください.
- **`NPMAX/NTHMAX < 6`**: ライブラリ自体は走ってしまうことがあります
  が, 速度空間積分が無意味になりモーメントが発散します. preflight 段で
  止めるのが安全.
- **device の `BB`/`RR`/`RIP` は値だけ通します**: `fp` は速度空間
  ソルバなので幾何依存性が弱く (上の sweep 例参照), プリセット値が
  外れていても `run()` 自体は通ります.
```

### 拡張案

- プリセットを `iter_baseline.toml` 等の外部ファイルから読む
- `fp_iter01_params` フィクスチャ (`python/fplib/tests/fixtures/`) を
  そのまま `auto_setup` のベースに流用してリアルな ITER01 物理ケースを
  再現
- LLM から呼ぶときは, `validate_fp_params` の出力をそのまま LLM に渡せば
  修正提案が返ってくる ({doc}`mcp` の「使用シナリオ」参照)

---

## 組合せパターン

3 つは個別にも組合せても使えます:

| 組合せ | 効果 |
|---|---|
| **スイープ + 安定化** | `sweep()` の中で `StableFpRunner` を使うと, 数値発散する点も自動回避 |
| **validate セットアップ + スイープ** | `auto_setup` でベース設定 → `PTPR × PN` 等を振る |
| **3 つ全部** | 装置プリセットを起点にした安定スイープ. 大規模 Fokker-Planck 解析の標準パターン |

各モジュール (`tr`, `eq`, `ti`, `wr`, `wrx`, `tot`) でも同じパターンが
適用できます. 物理量とエラー型 (`TrlibRunError`, `EqlibInvalidParamError`
など) を読み替えてください.
