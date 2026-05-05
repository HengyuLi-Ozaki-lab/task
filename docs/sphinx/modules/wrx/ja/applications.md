# ライブラリの応用例 (Python ラッパー)

`Wrxlib` を素のまま使うだけでなく, 上に薄いラッパーを被せると実用的に
なります. ここでは典型的な 3 パターンを示します.

```{admonition} このページの位置付け
:class: note

ここで紹介するのは **`wrxlib` を Python から使う応用パターン** です.
LLM クライアントから自然言語で操作するシナリオは {doc}`mcp` を
参照してください.
```

```{note}
かつて `Wrxlib.run()` は `wrcalpwr → libgrf::grd1d` 経路で SEGV する
既知の問題があり, テスト側で `WRX_RUN_OK=1` を明示する必要がありました.
PR #123 で根本原因 (`WRX_NO_GRAPHICS` env を `wrx_api_init` 内で
`setenv` する) を修正し, PR #166 で `WRX_RUN_OK` のデフォルトが `1`
になりました. 本ページのサンプルは特別な環境変数なしで実行できます.
```

---

## 1. 安全実行ラッパー (geometry preflight + safe_run)

`wr` 系と同じく `wrx` でも `run()` 失敗の主因は **入射ジオメトリ** です
(`RPIN[i]` がプラズマ境界 `RR ± (RA + RB)` の外, `ANGTIN[i]` が極端で
trajectory が境界を越えられない, など). 数値積分の失敗ではないため
**DT 半減のような再試行は効きません**. その代わり, 実行前にレイ毎の
ジオメトリを軽く検査し, 失敗したレイ番号と疑わしい入力をログに残す
`safe_run` が実用的です.

```python
from wrxlib import Wrxlib
from wrxlib.errors import WrxlibRunError


def _ray_sanity(ray: dict, *, rr: float, ra: float, rb: float) -> list[str]:
    """1 本のレイの入力を軽くチェックして問題点リストを返す."""
    issues: list[str] = []
    rpi = ray.get("RPI")
    if rpi is None:
        issues.append("RPI 未指定")
    else:
        rmin, rmax = rr - (ra + rb), rr + (ra + rb)
        if not (rmin <= rpi <= rmax):
            issues.append(f"RPI={rpi} がプラズマ境界 [{rmin:.2f},{rmax:.2f}] の外")
    rf = ray.get("RF")
    if rf is None or rf <= 0.0:
        issues.append(f"RF={rf} が非正値")
    angt = ray.get("ANGT", 0.0)
    if abs(angt) > 60.0:
        issues.append(f"ANGT={angt} が ±60 度を超える")
    return issues


def safe_run(wrx: Wrxlib, rays: list[dict], *,
             rr: float, ra: float, rb: float) -> dict:
    """`wrx.run()` を実行. 失敗時は ray-launch sanity report を返す."""
    # 1. preflight (純 Python; ライブラリには触れない)
    report = {"preflight": [], "run_ok": False, "error": None}
    for i, ray in enumerate(rays, start=1):
        issues = _ray_sanity(ray, rr=rr, ra=ra, rb=rb)
        if issues:
            report["preflight"].append({"ray": i, "issues": issues})

    # 2. それでも実行は試みる (preflight は警告止まり)
    try:
        wrx.run(nray_request=0)
        report["run_ok"] = True
        report["state"] = wrx.get_state()
    except WrxlibRunError as e:
        report["error"] = repr(e)
        # 失敗時は preflight で flag が立っていたレイを最有力容疑者として表示
        suspects = [r["ray"] for r in report["preflight"]]
        if suspects:
            print(f"  [safe_run] WrxlibRunError: 疑わしいレイ番号 = {suspects}")
            for r in report["preflight"]:
                print(f"    ray {r['ray']}: {', '.join(r['issues'])}")
        else:
            print(f"  [safe_run] WrxlibRunError: preflight をすり抜けた "
                  f"({e!r}); ANGTIN/MODELP の組合せを再確認")
    return report


# 使用例
BASE = dict(MODELG=2, MODELQ=0, RR=6.2, RA=2.0, RB=2.2, BB=5.3,
            Q0=1.0, QA=3.5, PROFJ=1.0, NSMAX=2, NSTPMAX=2000,
            MDLWRI=2, MDLWRQ=1, MDLWRG=1, MDLWRP=1, MDLWRW=0,
            pne_threshold=1.0e-6, SMAX=2.0, DELS=1.0e-3)
SPECIES = [("PA[1]", 2.0), ("PA[2]", 5.4462e-4),
           ("PZ[1]", 1.0), ("PZ[2]", -1.0),
           ("PN[1]", 1.0), ("PN[2]", 1.0),
           ("PNS[1]", 0.05), ("PNS[2]", 0.05),
           ("PTPR[1]", 10.0), ("PTPP[1]", 10.0),
           ("PTPR[2]", 10.0), ("PTPP[2]", 10.0),
           ("PTS[1]", 0.5), ("PTS[2]", 0.5),
           ("PROFN1[1]", 2.0), ("PROFN1[2]", 2.0),
           ("PROFN2[1]", 1.0), ("PROFN2[2]", 1.0),
           ("PROFT1[1]", 2.0), ("PROFT1[2]", 2.0),
           ("PROFT2[1]", 1.0), ("PROFT2[2]", 1.0),
           ("MODELP[1]", 206), ("MODELP[2]", 206),
           ("MODELV[1]", 3), ("MODELV[2]", 0),
           ("NCMIN[1]", -3), ("NCMIN[2]", -3),
           ("NCMAX[1]", 3),  ("NCMAX[2]", 3)]

bad_rays = [{"RF": 170.0e3, "RPI": 1.0, "ZPI": 0.0, "ANGT": 10.0}]  # RPI が境界外
with Wrxlib() as wrx:
    wrx.set_params(NRAYMAX=1, **BASE)
    for n, v in SPECIES:
        wrx.set_param(n, v)
    for i, r in enumerate(bad_rays, start=1):
        wrx.set_param(f"RFIN[{i}]", r["RF"])
        wrx.set_param(f"RPIN[{i}]", r["RPI"])
        wrx.set_param(f"ZPIN[{i}]", r["ZPI"])
        wrx.set_param(f"PHIIN[{i}]", 0.0)
        wrx.set_param(f"ANGPIN[{i}]", 0.0)
        wrx.set_param(f"ANGTIN[{i}]", r["ANGT"])
        wrx.set_param(f"UUIN[{i}]", 1.0)
        wrx.set_param(f"MODEWIN[{i}]", 1)
    rep = safe_run(wrx, bad_rays, rr=6.2, ra=2.0, rb=2.2)
    print(f"run_ok = {rep['run_ok']}, error = {rep['error']}")
```

期待される出力 (`RPI=1.0` は `RR-(RA+RB)=2.0` を下回るので preflight が
flag を立て, ライブラリは `WrxlibRunError(ierr=3)` を返す):

```text
  [safe_run] WrxlibRunError: 疑わしいレイ番号 = [1]
    ray 1: RPI=1.0 がプラズマ境界 [2.00,10.40] の外
run_ok = False, error = "WrxlibRunError('wrx_run(0): ierr=3')"
```

正常な入射条件 (例: `RPI=8.0, ANGT=10.0`) では `preflight` が空リスト,
`run_ok=True`, `state.scalars["pwr_tot"] ≈ 0.78` が得られます.

### 拡張案

- `MODELP[i]`, `NCMIN[i]`, `NCMAX[i]` の整合性も preflight で見る
  (例: `MODELP=206` (relativistic) なのに `NCMAX < 1` だと吸収ゼロ)
- 失敗履歴を `failures: list[dict]` に蓄積して後で分析
- 大規模 fan で 1 本だけ失敗するケースは, **そのレイを除外して再試行**
  するロジックを足す (`NRAYMAX -= 1`, レイ配列を詰め直し)

---

## 2. multi-ray fan スイープ

`ANGTIN[i]` (トロイダル入射角) を変えながら **複数レイを 1 セッション** で
打ち, レイ毎の吸収パワーと粒子種別吸収を集約します. レイ配列の組立てを
`_apply_rays` ヘルパに切り出すと, レイ数を変えるだけで再利用できます.

```python
from wrxlib import Wrxlib


def _apply_rays(wrx: Wrxlib, rays: list[dict]) -> None:
    """List-of-dict 形式のレイを 1-origin の配列要素に書き込む.

    `rays[k]` の各キー (RF, RPI, ZPI, ANGPHI, ANGT, MODEW, UU)
    を `RFIN[k+1]`, `RPIN[k+1]`, ... に変換. 未指定キーには既定値を
    入れる. NRAYMAX は呼び出し側で `set_params(NRAYMAX=len(rays))`.
    """
    DEFAULTS = {"PHII": 0.0, "ANGPHI": 0.0, "ANGT": 10.0,
                "UU": 1.0, "MODEW": 1, "ZPI": 0.0}
    for i, ray in enumerate(rays, start=1):
        merged = {**DEFAULTS, **ray}
        wrx.set_param(f"RFIN[{i}]",   float(merged["RF"]))
        wrx.set_param(f"RPIN[{i}]",   float(merged["RPI"]))
        wrx.set_param(f"ZPIN[{i}]",   float(merged["ZPI"]))
        wrx.set_param(f"PHIIN[{i}]",  float(merged["PHII"]))
        wrx.set_param(f"ANGPIN[{i}]", float(merged["ANGPHI"]))
        wrx.set_param(f"ANGTIN[{i}]", float(merged["ANGT"]))
        wrx.set_param(f"UUIN[{i}]",   float(merged["UU"]))
        wrx.set_param(f"MODEWIN[{i}]", float(merged["MODEW"]))


def fan_sweep(angles: list[float], *, base_params: dict,
              species_params: list, rpi: float = 8.0,
              freq_hz: float = 170.0e3) -> dict:
    """ANGTIN を `angles` で振った fan 1 発. `pwr_tot` と `pwr_nsa` を集計."""
    rays = [{"RF": freq_hz, "RPI": rpi, "ZPI": 0.0, "ANGT": a} for a in angles]
    with Wrxlib() as wrx:
        wrx.set_params(NRAYMAX=len(rays), **base_params)
        for n, v in species_params:
            wrx.set_param(n, v)
        _apply_rays(wrx, rays)
        wrx.run(nray_request=0)
        s = wrx.get_state()
    return {
        "angles": angles,
        "pwr_tot": s.scalars["pwr_tot"],
        "pwr_nsa": list(s.pwr_nsa),                 # 種別吸収 (合計)
        "pwr_nsa_nray": [list(r) for r in s.pwr_nsa_nray],  # ray × 種別
    }


# 使用例 (BASE / SPECIES は §1 と同じ)
res = fan_sweep([8.0, 10.0, 12.0], base_params=BASE, species_params=SPECIES)
print(f"pwr_tot      = {res['pwr_tot']:.4f}")
print(f"pwr_nsa      = {res['pwr_nsa']}")
for i, row in enumerate(res["pwr_nsa_nray"], start=1):
    print(f"  ray {i} (ANGT={res['angles'][i-1]:+.1f}): {row}")
```

期待される出力 (`170 GHz`, ITER 形状, ANGTIN=8/10/12 deg の 3 本 fan):

```text
pwr_tot      = 1.9122
pwr_nsa      = [1.9122187578892103, 0.0]
  ray 1 (ANGT=+8.0): [0.1333348100650216, 0.0]
  ray 2 (ANGT=+10.0): [0.7839621620662179, 0.0]
  ray 3 (ANGT=+12.0): [0.9949217857579706, 0.0]
```

レイ番号と入射角の対応が一目で分かり, 角度を変えた感度が見えます. なお
`pwr_nray[i]` は本ビルドでは常に `0.0` を返す既知の制約があります — レイ
別吸収は `pwr_nsa_nray[i][isa]` を `sum` する経路を使ってください.

### 拡張案

- 結果を `pandas.DataFrame` に流し込んで angle スイープ曲線を描く
- `multiprocessing.Pool` で複数プロセス並列化
  ({doc}`faq` のシングルトン制約より, **プロセスごとに独立な `Wrxlib`
  インスタンス** になるので並列化が有効)
- §1 の `safe_run` を中で使い, 一部のレイが失敗しても残りを集計

---

## 3. auto_setup with hand-rolled validate + multi-ray preset

`wrx` は `validate()` API を持たないので, **自前 preflight** + **装置プリセット**
で代用します. プリセットは「装置形状 (RR/BB/...)」と「レイの list」を
分けて持ち, 設計時の差分管理がしやすい構造に.

```python
from wrxlib import Wrxlib


REQUIRED_RAY_KEYS = ("RF", "RPI", "ZPI", "ANGT")


# 装置プリセット. shape は set_params 直行, rays は _apply_rays 経由.
DEVICE_PRESETS = {
    "ITER_LHCD_2ray": {
        "shape": dict(MODELG=2, MODELQ=0,
                      RR=6.2, RA=2.0, RB=2.2, BB=5.3,
                      Q0=1.0, QA=3.5, PROFJ=1.0,
                      NSMAX=2, NSTPMAX=2000,
                      MDLWRI=2, MDLWRQ=1, MDLWRG=1, MDLWRP=1, MDLWRW=0,
                      pne_threshold=1.0e-6, SMAX=2.0, DELS=1.0e-3),
        "rays": [
            {"RF": 170.0e3, "RPI": 8.0, "ZPI":  0.5, "ANGT": 10.0},
            {"RF": 170.0e3, "RPI": 8.0, "ZPI": -0.5, "ANGT": 10.0},
        ],
    },
}


def _hand_validate(shape: dict, rays: list[dict]) -> list[str]:
    """`wrx` 用 validate 代替. ブロッキング問題のリストを返す."""
    diags: list[str] = []
    nsmax = int(shape.get("NSMAX", 0))
    if nsmax < 1:
        diags.append(f"[NSMAX] NSMAX={nsmax} は >= 1 が必要")
    if not rays:
        diags.append("[NRAYMAX] rays が空")
    for i, ray in enumerate(rays, start=1):
        missing = [k for k in REQUIRED_RAY_KEYS if k not in ray]
        if missing:
            diags.append(f"[ray {i}] 必須キーが不足: {missing}")
    return diags


def auto_setup(device: str = "ITER_LHCD_2ray",
               extra_shape: dict | None = None,
               extra_rays: list[dict] | None = None) -> Wrxlib:
    """装置プリセットで wrx を初期化し, hand-rolled validate でセルフチェック."""
    preset = DEVICE_PRESETS[device]
    shape = {**preset["shape"], **(extra_shape or {})}
    rays = list(preset["rays"]) + list(extra_rays or [])

    # 1. validate (init 前に純 Python で検査)
    diags = _hand_validate(shape, rays)
    if diags:
        print(f"検出された問題 ({len(diags)} 件):")
        for d in diags:
            print(f"  {d}")
        raise RuntimeError(f"修正が必要な問題が {len(diags)} 件残っています")

    # 2. NRAYMAX を rays に合わせる (検証で len(rays)==NRAYMAX を保証する別解
    #    もあるが, ユーザの NRAYMAX 直指定を許容するため auto-derive)
    shape["NRAYMAX"] = len(rays)

    wrx = Wrxlib()
    try:
        wrx.__enter__()
        wrx.set_params(**shape)
        # 3. 種別パラメータ (このサンプルでは外部から差し替え可能にしたいので
        #    extra_shape で species を渡す想定. ここでは §1 の SPECIES を流用).
        for n, v in SPECIES:
            wrx.set_param(n, v)
        _apply_rays(wrx, rays)
        return wrx
    except Exception:
        wrx.__exit__(None, None, None)
        raise


# 使用例
with auto_setup("ITER_LHCD_2ray") as wrx:
    wrx.run(nray_request=0)
    s = wrx.get_state()
    print(f"pwr_tot = {s.scalars['pwr_tot']:.4f}")
    print(f"pwr_nsa = {s.pwr_nsa}")
    print(f"per-ray per-species:")
    for i, row in enumerate(s.pwr_nsa_nray, start=1):
        print(f"  ray {i}: {row}")
```

期待される出力 (`ITER_LHCD_2ray`, 2 本 fan):

```text
pwr_tot = 1.0073
pwr_nsa = [1.0073080764455387, 0.0]
per-ray per-species:
  ray 1: [0.9990350770648171, 0.0]
  ray 2: [0.008272999380721565, 0.0]
```

`extra_rays=[{"RF": 170.0e3}]` のように **必須キーが不足** した場合:

```text
検出された問題 (1 件):
  [ray 3] 必須キーが不足: ['RPI', 'ZPI', 'ANGT']
RuntimeError: 修正が必要な問題が 1 件残っています
```

`extra_shape={"NSMAX": 0}` の場合:

```text
検出された問題 (1 件):
  [NSMAX] NSMAX=0 は >= 1 が必要
RuntimeError: 修正が必要な問題が 1 件残っています
```

### 拡張案

- プリセットを `iter_lhcd_2ray.toml` 等の外部ファイルから読む
- `RBRADAIN[i]` / `RCURVAIN[i]` を `rays[i]` の追加キーとして取り回し,
  beam tracing 固有のビーム形状もプリセット化
- LLM から呼ぶときは, `_hand_validate` の出力をそのまま LLM に渡せば
  修正提案が返ってくる ({doc}`mcp` 参照)

---

## 組合せパターン

3 つは個別にも組合せても使えます:

| 組合せ | 効果 |
|---|---|
| **fan + safe_run** | `fan_sweep` の中で `safe_run` を使うと, 1 本だけ失敗しても残りで `pwr_tot` を出せる |
| **auto_setup + fan** | `auto_setup` でベース設定 → `fan_sweep` で `ANGTIN` や `RPIN` を振る |
| **3 つ全部** | 装置プリセットを起点にした安定 multi-ray スキャン. ECCD/LHCD 設計検討の標準パターン |

各モジュール (`tr`, `eq`, `ti`, `fp`, `wr`, `tot`) でも同じパターンが
適用できます. 物理量とエラー型 (`TrlibRunError`, `EqlibInvalidParamError`,
`WrlibRunError` など) を読み替えてください.
