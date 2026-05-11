# 最短 hello-world

```python
from totlib import Tot

with Tot() as tot:
    # サブモジュールパラメータをプレフィックスで指定
    tot.set_param("eq:RR", 6.5)              # eq モジュールの RR
    tot.set_param("eq:BB", 5.3)              # eq の BB
    tot.set_param("tr:NSMAX", 2)             # tr の粒子種数
    tot.set_param("tr:NTMAX", 100)           # tr の時間ステップ数
    tot.run(ntmax=10)                         # 10 ステップ統合シミュレーション
    state = tot.get_state()                   # 統合状態取得
print(state.scalars["T"], state.scalars["BETAN"])
```

## 行ごとの解説

`tot` は **オーケストレータ** で, eq / tr / ti / fp / wr / wrx の各
モジュールを統合実行します. パラメータ名に **`<module>:` プレフィックス**
を付けて, どのサブモジュールに渡すかを指定します:

- `eq:RR` → eq モジュールの `RR`
- `tr:NSMAX` → tr モジュールの `NSMAX`
- `fp:NPMAX` → fp モジュールの `NPMAX`
- など

## 期待される出力例

```
0.1  0.42
```

## tot のサブモジュール構成

`tot` は以下のサブモジュールを順次あるいは並列に呼びます:

| サブモジュール | プレフィックス | 役割 |
|---|---|---|
| `eq`  | `eq:`  | MHD 平衡を解いて磁気面情報を提供 |
| `tr`  | `tr:`  | 1D 輸送計算 |
| `ti`  | `ti:`  | 統合輸送 (代替) |
| `fp`  | `fp:`  | Fokker-Planck (高速イオン分布) |
| `wr`  | `wr:`  | RF レイトレース |
| `wrx` | `wrx:` | RF beam tracing |

例えば「平衡 + 輸送 + ECRH 加熱」というシミュレーションでは:

```python
tot.set_param("eq:RR", 6.5)         # 平衡解析の装置
tot.set_param("tr:NSMAX", 2)        # 輸送の粒子種
tot.set_param("wr:RF", 170e9)       # ECRH 周波数
tot.set_param("wr:RPI", 8.5)        # 入射点
tot.run(ntmax=100)                   # 全部結合して時間発展
```

## 単独モジュールとの違い

| | 単独モジュール (例: `Trlib`) | `tot` |
|---|---|---|
| パラメータ名 | `RR`, `BB`, ... | `tr:RR`, `tr:BB`, ... |
| 平衡データの取得 | `pl_*` 経由で外部から | `eq` を内部で実行して動的取得 |
| RF 加熱の整合性 | 別計算で得たプロファイルを `set_param` | `wr`/`wrx` を実行して動的取得 |
| 計算の自動連携 | なし | あり |

## なぜ `tot` を使うのか

`tot` を使う理由:

- **整合性のあるシミュレーション**: 平衡 (`eq`) → 輸送 (`tr`/`ti`) →
  Fokker-Planck (`fp`) → RF (`wr`/`wrx`) を **同じプラズマ状態** で計算
- **時間発展の整合**: 各サブモジュールが他の最新結果を見ながら更新
- **手動コーディングの省略**: 通常なら `Trlib`, `Eq`, `Wrlib` 等を順番に
  呼ぶプログラムが必要だが, `tot` 1 つで完結
