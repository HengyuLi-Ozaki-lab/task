# 最短 hello-world

`eq` には 2 通りの最短形があります — **Grad-Shafranov 方程式を解く (`mode=0`)** と
**平衡ファイルを読み込む (`mode=1`)** です. それぞれ示します.

## A. Grad-Shafranov 方程式を解く (`mode=0`)

ファイル不要. 装置パラメータと圧力・電流プロファイルから, 固定境界の
Grad-Shafranov 方程式を数値的に解きます (`EQCALC` が `EPSEQ` まで反復).

```python
from eqlib import Eq

with Eq() as eq:
    eq.set_params(RR=3.0, RA=1.0, BB=3.0, RIP=1.5)  # (1) 装置パラメータ
    eq.run(mode=0)                                    # (2) Grad-Shafranov 求解 + post-process
    st = eq.get_state()                               # (3) 状態取得
print(f"raxis={st.scalars['raxis']:.4f}  qaxis={st.scalars['qaxis']:.4f}")
```

期待される出力:

```text
raxis=3.0709  qaxis=0.9918
```

### 行ごとの解説

- **(1) `set_params`**: 装置の幾何と動作点 — `RR` (大半径), `RA` (小半径),
  `BB` (トロイダル磁場), `RIP` (プラズマ電流). `MODELG=2` (トロイダル形状) は既定値
  なので明示不要.
- **(2) `eq.run(mode=0)`**: `EQCALC` (Grad-Shafranov 求解) → `EQCALQ`
  (post-processing) を順次実行. 元 `eqx2` CLI の `R` (Run) → `F` (Fields)
  コマンドに対応.
- **(3) `eq.get_state()`**: 計算結果を `EqState` に写し取ります. 詳細は
  {doc}`state`.

## B. 平衡ファイルを読み込む (`mode=1`)

平衡がすでにファイルにあるときの定石 (ここでは TASK/EQ 形式, `MODELG=3`).

```python
from eqlib import Eq

with Eq() as eq:
    eq.set_param("RR", 6.5)                    # (1) 大半径 [m]
    eq.set_param("BB", 5.3)                    # (2) 磁場 [T]
    eq.set_param("RIP", 1.5)                   # (3) 電流 [MA]
    eq.set_param("MODELG", 3)                  # (4) 3: TASK/EQ 形式のファイル
    eq.set_param_str("KNAMEQ", "eqdata.ITER01")  # (5) ファイル名 (専用 API)
    eq.run()                                   # (6) mode=1 (既定) で読み込み
    st = eq.get_state()                        # (7) 状態取得
print(f"raxis={st.scalars['raxis']:.4f}  qaxis={st.scalars['qaxis']:.4f}")
```

### 行ごとの解説

- **(1)–(3)**: 装置パラメータ. TASK/EQ 形式のファイルは自身の値を持ち, 読み込みは
  `RR`, `BB`, `RIP` (と `RA`, `RKAP`, `RDLT`, `RB`) をファイルから読みます.
- **(4) `MODELG=3`**: ファイル形式の指定. 3 (と 9) は TASK/EQ 形式,
  5 (と 25) は G-EQDSK 形式で, いずれも `KNAMEQ` のファイル. 8 は QST/JAEA
  形式の 2 ファイル (`KNAMEQ`, `KNAMEQ2`). 固定の `eqdb.dat` を読む 15 は拒否されます.
  `mode=1` にはこのどれかが必要で, 既定の `MODELG=2` では失敗します.
- **(5) `set_param_str`**: 文字列パラメータは **専用 API** が必須
  ({doc}`parameter-setting` 方法 C 参照).
- **(6) `eq.run()`**: 引数なしだと `mode=1` (ファイル読み込み). 元 `eqx2`
  CLI の `L` (Load) コマンドに対応.

## モード選択のフローチャート

```text
平衡はファイルにある?
  ├─ No  → mode=0 (MODELG=2, デフォルト): プロファイルから解く
  └─ Yes → mode=1 (MODELG ∈ {3, 5, 8, 9, 25} + KNAMEQ 指定)
```

完全な実行可能 notebook: {doc}`quickstart`.

## `tr` との違い

- **時間発展なし**: `eq.run()` は時間ステップを進めるのではなく `mode`
  (動作モード) を取ります. デフォルトは `mode=1` (ファイル読み込み)
  ですが, Grad-Shafranov 求解には `mode=0` を渡してください ({doc}`faq` Q2).
- **6 個目の C ABI**: `eq_set_param_str` で文字列パラメータを受け付けます.
  `tr` も最近追加されましたが, EQ では設計初期から必要不可欠でした
  (平衡ファイル名 `KNAMEQ` を扱うため).
