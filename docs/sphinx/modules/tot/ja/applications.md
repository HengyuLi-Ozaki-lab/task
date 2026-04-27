# ライブラリの応用例 (Python ラッパー)

`Tot` は他の 5 モジュール (eq / tr / ti / fp / wr) を 1 プロセス内で
起動するオーケストレータです. ここでは典型的な 3 パターンを示します.

```{admonition} L-6 段階の制約
:class: warning

現在の `Tot` (Phase L-6) は **transport 部分 (TR) のみ実際に時間発展**
させます. `eq` / `ti` / `fp` / `wr` は同じプロセス内で初期化されます
が, `tot.run()` ではそれらの計算は呼ばれません. 言い換えると:

- `tot.set_param("eq:RR", 6.5)` のような **namespaced 設定は 5
  モジュール全部に分配される**.
- `tot.run(ntmax)` は **`tr_api_run(ntmax)` のみを呼ぶ**.
- `tot.get_state()` は **TR の state を集約**して返す
  (`state.tr_present == 1`, `state.ti_present == 0`, ...).

将来の Phase L-7 で `wr` → `tr` (波加熱沈着), `fp` → `tr` (電流駆動)
等の cross-module coupling が実装される予定です.
```

```{admonition} このページの位置付け
:class: note

ここで紹介するのは **`totlib` を Python から使う応用パターン** です.
LLM クライアントから自然言語で操作するシナリオは {doc}`mcp` の
「使用シナリオ」節を参照してください.
```

---

## 1. 統合 init + namespaced セットアップ

`Tot()` は 1 回の `__init__` で 4 つのサブモジュール (tr / ti / fp / wr)
を上げます. 各モジュール用パラメータは `<ns>:<name>` 形式の prefix で
区別:

```python
from totlib import Tot


with Tot() as tot:
    # eq の geometry をセット (各サブモジュールに配信)
    tot.set_param("eq:RR", 6.2)
    tot.set_param("eq:RA", 2.0)
    tot.set_param("eq:BB", 5.3)
    tot.set_param("eq:RIP", 15.0)

    # tr の transport 設定
    tot.set_param("tr:RR", 6.2)
    tot.set_param("tr:RA", 2.0)
    tot.set_param("tr:BB", 5.3)
    tot.set_param("tr:NSMAX", 2)
    tot.set_param("tr:DT", 0.01)
    tot.set_param("tr:NTMAX", 100)

    # 1 ステップだけ進めて state を確認
    tot.run(1)
    state = tot.get_state()
    print(f"tr_present={state.tr_present}, T={state.scalars['T']:.3f}s")
```

期待される出力:

```text
tr_present=1, T=0.010s
```

利用可能な prefix:

| Prefix | 対応モジュール | 備考 |
|---|---|---|
| `eq:` | equilibrium | 解析/EQDSK 共用 geometry |
| `tr:` | transport | 1D 拡散方程式 |
| `ti:` | ion transport | 重イオン輸送 (使用するときのみ) |
| `fp:` | Fokker-Planck | 速度空間分布 |
| `wr:` / `wrx:` | ray tracing | 波の伝搬 |

`describe_parameters` (各モジュール MCP) で名前空間ごとの定義を
列挙できます ({doc}`mcp` 参照).

### 拡張案

- 装置プリセット (ITER / JET / DIIID) を 1 つの dict にまとめて
  `_apply_namespaced(tot, preset)` で一括展開
- 「同じ `RR/RA/BB` を eq と tr と wr に配るのは冗長」と感じたら,
  `geometry_from(preset)` で展開する helper を作るとよい

---

## 2. transport advance のラッピング

L-6 段階では `tot.run(ntmax)` は **TR の transport 計算のみ** を ntmax
ステップ進めます. 失敗時のハンドリングは tr モジュールの applications
ページ (`docs/sphinx/modules/tr/ja/applications.md`) の `StableTrRunner`
と同形になります.

```python
from totlib import Tot
from totlib.errors import TotlibCalculationFailedError


def transport_step(tot: Tot, *, ntmax: int = 100) -> dict:
    """tot 経由で transport を進めて主要 scalar を返す."""
    try:
        tot.run(ntmax)
        state = tot.get_state()
        return {
            "tr_present": bool(state.tr_present),
            "T":     state.scalars["T"],
            "WPT":   state.scalars["WPT"],
            "BETAN": state.scalars["BETAN"],
            "TAUE1": state.scalars["TAUE1"],
            "Q0":    state.scalars["Q0"],
        }
    except TotlibCalculationFailedError as e:
        return {"error": repr(e)}


with Tot() as tot:
    tot.set_param("tr:RR", 6.2)
    tot.set_param("tr:RA", 2.0)
    tot.set_param("tr:BB", 5.3)
    tot.set_param("tr:NSMAX", 2)
    tot.set_param("tr:DT", 0.01)
    tot.set_param("tr:NTMAX", 100)
    out = transport_step(tot, ntmax=10)
    for k, v in out.items():
        if isinstance(v, float):
            print(f"  {k} = {v:.4g}")
        else:
            print(f"  {k} = {v}")
```

期待される出力:

```text
  tr_present = True
  T = 0.1
  WPT = 10.01
  BETAN = 0.2872
  TAUE1 = 11.42
  Q0 = 2.519
```

### 拡張案

- `state.scalars` 全 13 項目 (`T, WPT, AJT, Q0, BETA0, BETAP0, BETAA,
  BETAN, TAUE1, TAUE2, ZEFF0, ALI, RQ1`) をすべて返すよう拡張
- 各 ntmax ごとに state.scalars をリストに蓄積して時系列分析

---

## 3. 将来の coupling pipeline (L-7 予定)

L-7 では `wr` → `tr` (RF 加熱沈着), `fp` → `tr` (RF 電流駆動),
`eq` → `tr` (時刻ごとの平衡更新) 等を coupling する pipeline が想定
されています. 現状はまだ実装されていませんが, クライアント側のコード
形を示しておくと L-7 移行が滑らかになります.

```python
from totlib import Tot

# 注意: 以下は L-7 で実装される想定の pseudo-code です.
# 現状 (L-6) の `tot.run()` は TR transport のみを進めます.

def integrated_step(tot: Tot, *, ntmax: int = 1) -> dict:
    """eq + wr + fp + tr を 1 サイクル進める想定の pipeline."""
    # 1. eq solve (今の plasma current/pressure から平衡更新)
    # tot.run_module("eq", mode=0)            # ← L-7 で追加予定

    # 2. wr ray-trace (今の n/T から RF 沈着 profile を計算)
    # tot.run_module("wr", nray=8)            # ← L-7 で追加予定

    # 3. fp Fokker-Planck (RF 沈着 → 電流駆動)
    # tot.run_module("fp", ntmax=10)          # ← L-7 で追加予定

    # 4. tr transport (上記 source を反映して 1 step 進める)
    tot.run(ntmax)                              # ← L-6 でも動く

    return tot.get_state().scalars


# 現時点では (4) のみ動作:
with Tot() as tot:
    tot.set_param("tr:RR", 6.2)
    tot.set_param("tr:RA", 2.0)
    tot.set_param("tr:BB", 5.3)
    tot.set_param("tr:NSMAX", 2)
    tot.set_param("tr:DT", 0.01)
    tot.set_param("tr:NTMAX", 100)
    sc = integrated_step(tot, ntmax=10)
    print(f"T={sc['T']:.3f}s WPT={sc['WPT']:.3f}MJ BETAN={sc['BETAN']:.4f}")
```

期待される出力 (L-6 段階, TR のみ):

```text
T=0.100s WPT=10.007MJ BETAN=0.2872
```

### L-7 で追加される予定の API (案)

| 追加 API | 役割 |
|---|---|
| `tot.run_module(name, **kwargs)` | 単一モジュールだけを進める |
| `tot.run_pipeline(steps)` | 複数モジュールを順序指定で 1 サイクル |
| `state.{eq,wr,fp,ti}_*` | 各モジュールの aggregated state |
| `tot.couple(src, dst)` | source → sink のデータフロー宣言 |

仕様は L-7 着手時に固まります.

---

## 組合せパターン

| 組合せ | 効果 |
|---|---|
| **namespaced setup + transport_step** | `Tot` 1 つで TR ベースの定常解析 (eq の geometry も同時に init される) |
| **transport_step + sweep** | RR × BB のような格子スキャンで, TR transport の感度を評価 |
| **L-7 pipeline placeholder** | 現時点で書いておくと, L-7 リリース時の移行が一括で済む |

各サブモジュール単体の応用パターンは各モジュールの `applications.md`
(例: `docs/sphinx/modules/tr/ja/applications.md`,
`docs/sphinx/modules/eq/ja/applications.md` 等) を参照. `Tot` 経由でも
同等の prefix 付きパラメータでセットアップできます.
