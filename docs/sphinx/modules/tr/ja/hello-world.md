# 最短 hello-world (5 行)

```python
from trlib import Trlib            # (1) インポート
with Trlib() as tr:                # (2) 初期化 (= tr_init 自動)
    tr.set_params(RR=3.0, BB=3.0)  # (3) 大半径 3m, 磁場 3T
    tr.run(ntmax=10)               # (4) 10 ステップ時間発展
    state = tr.get_state()         # (5) 状態を取得 (型は TrState)
print(state.scalars["T"])          # 最終時刻 (秒)
```

## 行ごとの解説

- **(1) `from trlib import Trlib`** — パッケージ `trlib` からクラス
  `Trlib` を読み込みます. `Trlib` は共有ライブラリのハンドル (持ち手)
  です.
- **(2) `with Trlib() as tr:`** — `with` 文は Python のコンテキスト
  マネージャ機能. 入る時に `__enter__` (= `tr_init`), 抜けるときに
  `__exit__` (= `tr_finalize`) が自動で呼ばれ, 後片付けを忘れる
  心配がありません.
- **(3) `tr.set_params(RR=3.0, BB=3.0)`** — スカラー値を一括でセット
  するヘルパー. Fortran の `/TR/` ネームリストと同じ名前 (`RR` = 大半径,
  `BB` = トロイダル磁場) をキーワード引数で指定します.
- **(4) `tr.run(ntmax=10)`** — 時間発展を 10 ステップ進めます. ステップ幅
  は `DT` (デフォルト 0.01 秒) です.
- **(5) `state = tr.get_state()`** — 現在の状態を `TrState` dataclass に
  写し取ります. `state.scalars["T"]` で現在時刻, `state.RT[i][j]` で温度
  プロファイルが取れます.

## 期待される出力例

```bash
$ PYTHONPATH=python python3 examples/quickstart.py
NT=50  NRMAX=50  NSMAX=2
T    = 0.5
WPT  = 8.3e+05
Q0   = 0.96
BETAA= 0.42
```

完全な実行可能 notebook: {doc}`quickstart`.
