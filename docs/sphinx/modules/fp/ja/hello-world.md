# 最短 hello-world

```python
from fplib import Fplib

with Fplib() as fp:
    fp.set_params(RR=3.0, BB=3.0, NSMAX=1)        # (1) 装置 + 1 種
    fp.set_param("NPMAX", 50)                       # (2) 運動量メッシュ
    fp.set_param("NTHMAX", 25)                      # (3) ピッチ角メッシュ
    fp.run(ntmax=5)                                 # (4) 5 ステップ計算
    state = fp.get_state()                          # (5) 状態取得
print(state.timefp, state.nsamax)
```

## 行ごとの解説

- **(1) `set_params`**: 幾何 (`RR`, `BB`) + 粒子種数 (`NSMAX`) を設定.
- **(2) `NPMAX`**: 運動量空間のメッシュ点数. fp は 5D (位置 1D × 運動量 1D ×
  ピッチ角 1D × 種別 × 時間) で離散化するため, 運動量・ピッチ角の解像度が
  重要.
- **(3) `NTHMAX`**: ピッチ角空間のメッシュ点数.
- **(4) `run(ntmax=5)`**: 5 ステップ時間発展. ステップ幅は `DELT` (`tr`/`ti` の
  `DT` に相当) 既定 0.001 s.
- **(5) `get_state()`**: `FpState` dataclass に結果を写し取ります.

## 期待される出力例

```
0.005  1
```

## fp の独自性

`tr`, `ti`, `eq` と違って `fp` は **粒子分布関数 $f(r, p, \theta)$ を
直接解く** モジュールです.

- 出力は積分量 (温度・密度) ではなく **モーメント** (`RNT`=粒子数密度,
  `RWT`=エネルギー密度, `RTT`=温度, `RJT`=電流密度, `RPCT`=衝突パワー,
  `RPWT`=波動パワー)
- 高速イオン (NBI 起源, fusion 起源) や非熱化分布の精密解析に使う
- 計算コストは `tr`/`ti` より大きい (5D グリッド)
