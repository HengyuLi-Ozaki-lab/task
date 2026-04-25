# 最短 hello-world

```python
from wrxlib import Wrxlib

with Wrxlib() as wrx:
    wrx.set_params(RR=3.0, BB=3.0, NSMAX=1)      # (1) 装置 + 1 種
    wrx.set_param("NRAYMAX", 1)                    # (2) レイ本数
    wrx.set_param("RFIN[1]", 170.0e9)              # (3) 1 番目レイ: 周波数
    wrx.set_param("RPIN[1]", 3.5)                  # (4) 入射点 R
    wrx.set_param("ZPIN[1]", 0.0)                  # (5) 入射点 Z
    wrx.run(nray_request=1)                         # (6) beam tracing 実行
    state = wrx.get_state()                         # (7) 状態取得
print(state.scalars["pwr_tot"])
```

## 行ごとの解説

- **(1) `set_params`**: 装置 (`RR`, `BB`) + 粒子種数 (`NSMAX`).
- **(2) `NRAYMAX`**: レイ本数. ビーム近似の精度を決める.
- **(3)–(5) `*IN[i]`**: i 番目レイの初期条件 (1-origin).
- **(6) `run`**: beam tracing 実行. **引数は最大ステップ数の上書き** として
  `nstpmax_arg` を取りますが, Python ラッパでは `nray_request` 名で公開
  されています (下記の注意参照).
- **(7) `get_state()`**: `WrxState` dataclass を返します. 詳細は {doc}`state`.

```{note}
`wrx` の `run()` 引数名について: 内部シンボルは `nstpmax_arg` ですが,
MCP/Python ラッパでは **`nray_request`** として公開されています
(`wr` との API 互換性のため). 実際の挙動は対応コードを確認してください.
```

## 期待される出力例

```
1.5e-02
```

## `wr` との違い (実用)

`wr` と `wrx` の同じ入射条件で比較:

| | `wr` (geometric optics) | `wrx` (beam tracing) |
|---|---|---|
| レイ本数で必要な数 | 多い (10–50 本で beam 近似) | 少ない (1 レイで完結) |
| ビーム曲率・幅 | 別のレイとして近似 | **レイ 1 本で解析的** |
| 計算コスト (1 レイ) | 低 | 高 |
| 計算コスト (同精度) | 高 (多数レイ必要) | 低 |
| 集束ビームの精度 | 劣 | **優** |

集束ビームを使う ECRH や LHRD のシミュレーションでは `wrx` 推奨.
