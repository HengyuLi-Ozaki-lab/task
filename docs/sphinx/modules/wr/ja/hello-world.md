# 最短 hello-world

```python
from wrlib import Wrlib

with Wrlib() as wr:
    wr.set_params(RR=3.0, BB=3.0, NSMAX=1)        # (1) 装置 + 1 種
    wr.set_param("RF", 170.0e9)                    # (2) 周波数 170 GHz
    wr.set_param("RPI", 3.5)                       # (3) 入射点 R [m]
    wr.set_param("ZPI", 0.0)                       # (4) 入射点 Z [m]
    wr.set_param("RKR0", 1.0)                      # (5) 初期 k_R
    wr.run(nray_request=1)                          # (6) 1 本の光線追跡
    state = wr.get_state()                          # (7) 状態取得
print(state.scalars["pwrmax_rs"], state.nraymax)
```

## 行ごとの解説

- **(1) `set_params`**: 装置パラメータ (`RR`, `BB`) と粒子種数 (`NSMAX`).
- **(2) `RF`**: 波の周波数 (Hz). ECRH/ECCD なら 100–200 GHz, LH なら 1–10 GHz.
- **(3)–(4) `RPI`, `ZPI`**: レイの入射点 (R, Z 座標 [m]).
- **(5) `RKR0`**: 初期波数 k_R (規格化形式).
- **(6) `run(nray_request=1)`**: **1 本のレイをトレース**. `tr`/`ti`/`fp` の
  `ntmax` (時間ステップ) と違って, **`nray_request` は追跡するレイの本数**.
- **(7) `get_state()`**: 結果を `WrState` dataclass に写し取ります.
  `pwrmax_rs` は r-座標方向のピークパワー強度.

## 期待される出力例

```
0.85  1
```

## wr の独自性

`tr`/`ti`/`fp` と違い `wr` は **時間発展せず**, **空間方向の光線追跡** を行います.

- 入力: プラズマ平衡 + 入射波 (周波数, 位置, 波数ベクトル)
- 計算: 幾何光学的にレイを伝搬させ, 電力吸収位置を求める
- 出力: ピークパワー位置 / 値, レイ軌跡, 半径方向プロファイル

主用途:

- **ECRH/ECCD** (電子サイクロトロン加熱・電流駆動) のレイトレース
- **LH** (低域混成波) のパワー堆積位置解析
- 加熱パラメータ (周波数, 入射角度) の最適化

複数のレイ (`NRAYMAX > 1`) を一度に走らせることで, **ビーム** の効果を
近似的に取り込めます (より精密な beam tracing は `wrx` モジュール参照).
