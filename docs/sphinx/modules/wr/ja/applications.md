# ライブラリの応用例 (Python ラッパー)

`Wrlib` を素のまま使うだけでなく, 上に薄いラッパーを被せると実用的に
なります. ここでは典型的な 3 パターンを示します.

```{admonition} このページの位置付け
:class: note

ここで紹介するのは **`wrlib` を Python から使う応用パターン** です.
LLM クライアントから自然言語で操作するシナリオは {doc}`mcp` の
「使用シナリオ」節を参照してください.

なお `wr` は `tr` と違って **時間ステップ `DT` のような連続パラメータ
が無く**, `run()` が `WrlibRunError(ierr=3)` を返した場合に「半分にして
リトライ」する自然な軸がありません. 失敗のほとんどは **入射ジオメトリ
のミス** (`RPI/ZPI` がプラズマの外, `RKR0` の符号 / 大きさ, `RF` が
共鳴帯の外, `NSMAX` 不足 など) なので, ここでは `safe_run` として
**失敗時にどのパラメータが怪しいかを診断するラッパー** を示します.
```

---

## 1. 診断付き safe_run ラッパー

`run()` が `WrlibRunError` を返した場合に, 渡されたパラメータをチェック
して **怪しい値を列挙する** ラッパーです. ジオメトリ起因の `ierr=3` は
原因が幾何条件なので, 「リトライ」より「どこを直すべきか」の情報が
価値を持ちます.

```python
from wrlib import Wrlib
from wrlib.errors import WrlibRunError


def safe_run(wr, *, nray_request=0, params_for_diag=None):
    """`wr.run()` を try で囲み, 失敗時は怪しいパラメータをまとめて報告する.

    Parameters
    ----------
    wr : Wrlib
        既に init + set_params 済みの Wrlib インスタンス.
    nray_request : int
        wr.run() に渡すレイ本数 (0 なら NRAYMAX を維持).
    params_for_diag : dict or None
        診断対象のパラメータ. 例: ``{"RR": 6.2, "RA": 2.0, "RPI": 8.0,
        "RKR0": 1.0, "RF": 5.0e9, "NSMAX": 2}``.

    Returns
    -------
    (state, error_msg) のタプル. 成功時は (WrState, None),
    失敗時は (None, "...診断メッセージ...").
    """
    pd = params_for_diag or {}
    try:
        wr.run(nray_request=nray_request)
        return wr.get_state(), None
    except WrlibRunError as e:
        notes = []
        rf = pd.get("RF")
        if rf is not None and not (1.0e9 <= rf <= 3.0e11):
            notes.append(f"RF={rf:g} Hz は 1 GHz - 300 GHz 帯から外れています")
        rkr0 = pd.get("RKR0")
        if rkr0 is not None and abs(rkr0) < 1.0e-3:
            notes.append(f"RKR0={rkr0} は 0 に近すぎます (初期波数が立たない)")
        rpi = pd.get("RPI")
        rr = pd.get("RR")
        ra = pd.get("RA")
        if rpi is not None and rr is not None and ra is not None:
            if not (rr - ra <= rpi <= rr + ra):
                notes.append(
                    f"RPI={rpi} はプラズマ範囲 [{rr - ra}, {rr + ra}] の外側"
                )
        nsmax = pd.get("NSMAX")
        if nsmax is not None and nsmax < 1:
            notes.append(f"NSMAX={nsmax} は 1 以上が必要")
        msg = f"WrlibRunError: {e}"
        if notes:
            msg += "\n  推測される原因:\n    - " + "\n    - ".join(notes)
        return None, msg


# 使用例 1: 健全パラメータ (ITER LHCD fixture)
from wrlib.tests.fixtures import wr_iter_lhcd_params as base
with Wrlib() as wr:
    base.apply(wr)
    wr.set_param("NRAYMAX", 1)
    state, err = safe_run(
        wr, nray_request=0,
        params_for_diag={"RR": 6.2, "RA": 2.0,
                         "RPI": 8.0, "RKR0": 1.0,
                         "NSMAX": 2},
    )
    if err:
        print(err)
    else:
        print(f"OK pos_pwrmax_rl={state.scalars['pos_pwrmax_rl']:.4f}, "
              f"nstp_end={state.nstp_end}")
```

期待される出力:

```text
OK pos_pwrmax_rl=4.2002, nstp_end=[100]
```

入射点が装置範囲外のケース (`RPI=10.0` だが `RR=3.0, RA=1.0`):

```python
with Wrlib() as wr:
    wr.set_params(RR=3.0, BB=3.0, RA=1.0, NSMAX=1)
    wr.set_param("RF", 170.0e9)
    wr.set_param("RPI", 10.0)   # 装置外: RR-RA=2, RR+RA=4
    wr.set_param("ZPI", 0.0)
    wr.set_param("RKR0", 1.0)
    state, err = safe_run(
        wr, nray_request=1,
        params_for_diag={"RR": 3.0, "RA": 1.0,
                         "RPI": 10.0, "RKR0": 1.0,
                         "RF": 170e9, "NSMAX": 1},
    )
    print(err if err else f"OK pos_pwrmax_rl={state.scalars['pos_pwrmax_rl']}")
```

期待される出力:

```text
WrlibRunError: wr_run(1): ierr=3
  推測される原因:
    - RPI=10.0 はプラズマ範囲 [2.0, 4.0] の外側
```

```{admonition} `pwrmax` 系スカラが 0 の理由
:class: note

現在の `wr` Layer-2 ステージでは, パワー吸収の後処理パイプラインが
配線されていないため `pwrmax_rs` / `pwrmax_rl` は **常に 0.0** が
入ります. 一方 **`pos_pwrmax_*` (位置)** と **`nstp_end` (積分終端
ステップ)** は実際のレイ追跡から得られた意味のある値です.
吸収プロファイルが必要な場合は `wrx` モジュールを参照してください.
```

### 拡張案

- 失敗履歴を `failures: List[Dict]` に蓄積して後で分析
- `WrlibParamError` (`ierr=1`) も同様にトラップして, レジストリに無い
  名前を typo として報告する
- `RKR0` を符号反転して再試行する版 (低域混成では入射方向が反対になる
  ことがある)

---

## 2. パラメータスイープラッパー

`RFIN × ANGPHIN` のような格子状スキャン (周波数 × トロイダル入射角) を
行い, 結果を辞書のリストに集約します. `python/wrlib/tests/test_sweep.py`
の 3×3 グリッドパターンと同じ形です.

```python
import itertools
from typing import List, Dict
from wrlib import Wrlib
from wrlib.tests.fixtures import wr_iter_lhcd_params as base


def sweep(
    *,
    rfin_values: List[float],
    angphin_values: List[float],
    fixed_params: Dict | None = None,
) -> List[Dict]:
    """RFIN × ANGPHIN の格子スキャン. 各点で wr を 1 セッション独立実行.

    各点では ITER-LHCD fixture をベースに NRAYMAX=1 に縮め,
    ``RFIN[1]`` (LH 周波数, MHz) と ``ANGPHIN[1]`` (トロイダル入射角, 度)
    だけ振る.

    Returns
    -------
    各点の {RFIN[1], ANGPHIN[1], pwrmax_rs, pos_pwrmax_rs,
           pwrmax_rl, pos_pwrmax_rl, nstp_end, error} のリスト
    """
    fixed = fixed_params or {}
    results = []
    for rf, ang in itertools.product(rfin_values, angphin_values):
        row = {"RFIN[1]": rf, "ANGPHIN[1]": ang}
        try:
            with Wrlib() as wr:
                base.apply(wr)
                wr.set_param("NRAYMAX", 1)
                for k, v in fixed.items():
                    wr.set_param(k, v)
                wr.set_param("RFIN[1]", float(rf))
                wr.set_param("ANGPHIN[1]", float(ang))
                wr.run(0)
                state = wr.get_state()
            row.update(
                pwrmax_rs=state.scalars["pwrmax_rs"],
                pos_pwrmax_rs=state.scalars["pos_pwrmax_rs"],
                pwrmax_rl=state.scalars["pwrmax_rl"],
                pos_pwrmax_rl=state.scalars["pos_pwrmax_rl"],
                nstp_end=state.nstp_end[0],
                error=None,
            )
        except Exception as e:
            row["error"] = repr(e)
        results.append(row)
    return results


# 使用例: ITER LHCD 周辺 (LH 周波数 4-6 GHz, トロイダル入射角 25-35 度)
results = sweep(
    rfin_values=[4.0e3, 5.0e3, 6.0e3],   # MHz (= 4-6 GHz)
    angphin_values=[25.0, 30.0, 35.0],   # 度
)
for r in results:
    if r.get("error"):
        print(f"  RFIN={r['RFIN[1]']}, ANGPHIN={r['ANGPHIN[1]']} -> {r['error']}")
    else:
        print(
            f"  RFIN={r['RFIN[1]']:>5}, ANGPHIN={r['ANGPHIN[1]']:>4}: "
            f"pos_pwrmax_rl={r['pos_pwrmax_rl']:.4f}, "
            f"nstp_end={r['nstp_end']}"
        )
```

期待される出力:

```text
  RFIN=4000.0, ANGPHIN=25.0: pos_pwrmax_rl=4.2002, nstp_end=100
  RFIN=4000.0, ANGPHIN=30.0: pos_pwrmax_rl=4.2002, nstp_end=100
  RFIN=4000.0, ANGPHIN=35.0: pos_pwrmax_rl=4.2002, nstp_end=100
  RFIN=5000.0, ANGPHIN=25.0: pos_pwrmax_rl=4.2002, nstp_end=98
  RFIN=5000.0, ANGPHIN=30.0: pos_pwrmax_rl=4.2002, nstp_end=100
  RFIN=5000.0, ANGPHIN=35.0: pos_pwrmax_rl=4.2002, nstp_end=100
  RFIN=6000.0, ANGPHIN=25.0: pos_pwrmax_rl=4.2002, nstp_end=97
  RFIN=6000.0, ANGPHIN=30.0: pos_pwrmax_rl=4.2002, nstp_end=100
  RFIN=6000.0, ANGPHIN=35.0: pos_pwrmax_rl=4.2002, nstp_end=100
```

`nstp_end` が `NSTPMAX` (=100, ITER fixture の `NSTPMAX=2000` を Layer-2
スタブが内部 100 にクリップ) より小さい点は **早期に積分が終端した**
ことを意味します (例: レイがプラズマから抜ける, 共鳴吸収など). 今回の
スイープでは `RFIN=5000, ANGPHIN=25` と `RFIN=6000, ANGPHIN=25` が
それぞれ 98 / 97 ステップで終了しています.

### 拡張案

- 結果を `pandas.DataFrame` に流し込んでヒートマップに
- `multiprocessing.Pool` で複数プロセス並列化
  ({doc}`faq` Q4 のシングルトン制約より, **プロセスごとに独立な `Wrlib`
  インスタンス** になるので並列化が有効)
- `safe_run` を中で使って失敗自動回避

---

## 3. preflight 駆動セットアップ (auto_setup)

`wr` には `tr` / `eq` のような native `validate()` が無いため,
**自前の preflight 関数** をラッパーで提供します. 装置プリセットを起点に,
入射ジオメトリ/周波数の物理的合理性を `set_param` 前にチェックする
パターンです.

```python
from typing import Dict, List
from wrlib import Wrlib


# 装置プリセット (実 fixture から派生).
# 単位: RFIN は MHz (wr/wrexecr.f90 の omega = 2.D6 * PI * RFIN(nray)),
#       RPIN/ZPIN は m, ANGZIN/ANGPHIN は度, BB は T, RR/RA は m.
DEVICE_PRESETS = {
    "ITER_LHCD": dict(
        scalars=dict(MODELG=2, RR=6.2, RA=2.0, RKAP=1.7, RDLT=0.33,
                     BB=5.3, RIP=15.0, NSMAX=2,
                     PROFN1=2.0, PROFN2=2.0, PROFT1=2.0, PROFT2=1.0,
                     NRAYMAX=1, NSTPMAX=2000, NRSMAX=50, NRLMAX=100,
                     MDLWRI=101, MDLWRQ=0, MDLWRW=0,
                     SMAX=5.0, DELS=0.05),
        arrays=dict(PA=[2.0, 1.0], PZ=[1.0, -1.0],
                    PN=[1.0, 1.0], PNS=[0.1, 0.1],
                    PTPR=[10.0, 10.0], PTPP=[10.0, 10.0],
                    PTS=[0.5, 0.5], MODELP=[4, 4],
                    RFIN=[5.0e3], RPIN=[8.0], ZPIN=[0.0],
                    PHIIN=[0.0], ANGZIN=[0.0], ANGPHIN=[30.0],
                    UUIN=[1.0], MODEWIN=[1]),
    ),
    "TST2_EC": dict(
        scalars=dict(MODELG=2, RR=0.38, RA=0.16, RKAP=1.0, RDLT=0.0,
                     BB=0.3, RIP=0.2, NSMAX=2,
                     PROFN1=2.0, PROFN2=2.0,
                     NRAYMAX=1, NSTPMAX=2000, NRSMAX=30, NRLMAX=60,
                     MDLWRI=101, MDLWRQ=0, MDLWRW=0,
                     SMAX=1.0, DELS=0.005),
        arrays=dict(PA=[2.0, 1.0], PZ=[1.0, -1.0],
                    PN=[0.5, 0.5], PNS=[0.05, 0.05],
                    PTPR=[0.5, 0.5], PTPP=[0.5, 0.5],
                    PTS=[0.05, 0.05], MODELP=[4, 4],
                    RFIN=[8.2e3], RPIN=[0.5], ZPIN=[0.0],
                    PHIIN=[0.0], ANGZIN=[0.0], ANGPHIN=[0.0],
                    UUIN=[1.0], MODEWIN=[1]),
    ),
}


def preflight(scalars: Dict, arrays: Dict) -> List[str]:
    """`wr` 用の自前 validate. 一覧で問題を返す (空なら健全).

    `tr` / `eq` の `validate()` 相当を Python 側で再現. `[REQUIRED]`
    と `[ARRAY_LEN]` を blocking, `[OUT_OF_RANGE]` を warning として
    扱う想定.
    """
    issues = []
    # 必須スカラ
    if scalars.get("NSMAX", 0) < 1:
        issues.append(f"[REQUIRED] NSMAX={scalars.get('NSMAX')} は 1 以上が必要")
    if scalars.get("RR", 0) <= 0:
        issues.append(f"[REQUIRED] RR={scalars.get('RR')} は正値が必要")
    if scalars.get("BB", 0) == 0:
        issues.append("[REQUIRED] BB=0 は不可 (磁場ゼロ)")
    nraymax = scalars.get("NRAYMAX", 1)
    if nraymax < 1:
        issues.append(f"[REQUIRED] NRAYMAX={nraymax} は 1 以上が必要")

    # レイ別配列の長さチェック (NRAYMAX 本ぶん必要)
    rfin = arrays.get("RFIN", [])
    if len(rfin) < nraymax:
        issues.append(
            f"[ARRAY_LEN] RFIN は {nraymax} 要素必要 (現在 {len(rfin)})"
        )
    rpin = arrays.get("RPIN", [])
    if len(rpin) < nraymax:
        issues.append(
            f"[ARRAY_LEN] RPIN は {nraymax} 要素必要 (現在 {len(rpin)})"
        )

    # 物理的合理性 (warning レベル)
    rr = scalars.get("RR")
    ra = scalars.get("RA")
    for i, rp in enumerate(rpin[:nraymax], start=1):
        if rp <= 0:
            issues.append(f"[OUT_OF_RANGE] RPIN[{i}]={rp} は正値が必要")
        if rr is not None and ra is not None:
            if not (rr - ra <= rp <= rr + ra * 4):  # 入射点は外側可
                issues.append(
                    f"[OUT_OF_RANGE] RPIN[{i}]={rp} はプラズマ近傍から離れすぎ"
                    f" ({rr - ra} ~ {rr + ra * 4})"
                )
    for i, rf in enumerate(rfin[:nraymax], start=1):
        if not (1.0 <= rf <= 3.0e5):  # MHz: 1 MHz - 300 GHz
            issues.append(
                f"[OUT_OF_RANGE] RFIN[{i}]={rf} MHz は 1 MHz - 300 GHz 帯外"
            )
    return issues


def auto_setup(device: str = "ITER_LHCD", *, extra_scalars=None) -> Wrlib:
    """装置プリセットで wrlib を初期化し preflight でセルフチェック.

    Returns
    -------
    既に init + set_params 済みの Wrlib インスタンス
    (呼び出し側が `with` か `try/finally` で終了処理).
    """
    preset = DEVICE_PRESETS[device]
    scalars = dict(preset["scalars"])
    arrays = {k: list(v) for k, v in preset["arrays"].items()}
    scalars.update(extra_scalars or {})

    # 1. preflight (set_param 前にチェック)
    issues = preflight(scalars, arrays)
    if issues:
        print(f"検出された問題 ({len(issues)} 件):")
        for msg in issues:
            print(f"  {msg}")
        blocking = [m for m in issues if "[REQUIRED]" in m or "[ARRAY_LEN]" in m]
        if blocking:
            raise RuntimeError(
                f"修正が必要な問題が {len(blocking)} 件残っています"
            )

    # 2. 適用
    wr = Wrlib()
    try:
        for k, v in scalars.items():
            wr.set_param(k, float(v))
        for name, arr in arrays.items():
            for i, v in enumerate(arr, start=1):
                wr.set_param(f"{name}[{i}]", float(v))
        return wr
    except Exception:
        wr.close()
        raise


# 使用例 1: ITER LHCD プリセット
with auto_setup("ITER_LHCD") as wr:
    wr.run(0)
    s = wr.get_state()
    print(f"ITER_LHCD: pos_pwrmax_rl={s.scalars['pos_pwrmax_rl']:.4f}, "
          f"nstp_end={s.nstp_end[0]}")

# 使用例 2: TST-2 EC プリセット
with auto_setup("TST2_EC") as wr:
    wr.run(0)
    s = wr.get_state()
    print(f"TST2_EC:   pos_pwrmax_rl={s.scalars['pos_pwrmax_rl']:.4f}, "
          f"nstp_end={s.nstp_end[0]}")
```

期待される出力:

```text
ITER_LHCD: pos_pwrmax_rl=4.2002, nstp_end=100
TST2_EC:   pos_pwrmax_rl=0.2200, nstp_end=200
```

`extra_scalars={"NSMAX": 0}` のように blocking レベルの不正値を渡すと:

```python
try:
    with auto_setup("ITER_LHCD", extra_scalars={"NSMAX": 0}) as wr:
        wr.run(0)
except RuntimeError as e:
    print(f"RuntimeError: {e}")
```

期待される出力:

```text
検出された問題 (1 件):
  [REQUIRED] NSMAX=0 は 1 以上が必要
RuntimeError: 修正が必要な問題が 1 件残っています
```

### 拡張案

- プリセットを `iter_lhcd.toml` 等の外部ファイルから読む
- `[OUT_OF_RANGE]` の自動クランプ (例: `RFIN=0.1` MHz → `RFIN=1.0` に
  丸める)
- `wr` で native `validate()` が実装された暁には, `preflight()` を
  `wr.validate()` に置き換える (issue #143 の batch validation を
  参照)
- LLM から呼ぶときは, preflight の出力をそのまま LLM に渡せば修正提案
  が返ってくる ({doc}`mcp` の「使用シナリオ」参照)

---

## 組合せパターン

3 つは個別にも組合せても使えます:

| 組合せ | 効果 |
|---|---|
| **safe_run + sweep** | `sweep()` の中で `safe_run` を使うと, 失敗点に診断メッセージが付く |
| **auto_setup + sweep** | プリセットをベースに `RFIN × ANGPHIN` を振る (典型的な加熱パラメータ最適化) |
| **3 つ全部** | 装置プリセット起点の安定スイープ + 失敗診断. ECRH/LH 設計検討の標準パターン |

各モジュール (`tr`, `eq`, `ti`, `fp`, `wrx`, `tot`) でも同じパターンが
適用できます. 物理量とエラー型 (`TrlibRunError`, `EqlibRunError`,
`WrxlibRunError` など) を読み替えてください.
