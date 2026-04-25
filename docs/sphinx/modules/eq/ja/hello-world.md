# 最短 hello-world

```python
from eqlib import Eq

with Eq() as eq:
    eq.set_param("RR", 6.5)                    # (1) 大半径 [m]
    eq.set_param("BB", 5.3)                    # (2) 磁場 [T]
    eq.set_param("RIP", 1.5)                   # (3) 電流 [MA]
    eq.set_param("MODELG", 3)                  # (4) EQDSK 経路を指定
    eq.set_param_str("KNAMEQ", "eqdata.ITER")  # (5) ファイル名 (専用 API)
    eq.run()                                   # (6) mode=1 で平衡を解く
    st = eq.get_state()                        # (7) 状態取得 (型は EqState)
print(f"raxis={st.scalars['raxis']:.4f}  qaxis={st.scalars['qaxis']:.4f}")
```

## 行ごとの解説

- **(1)–(3)**: 装置の幾何と動作点を指定. `RR` (大半径), `BB` (トロイダル磁場),
  `RIP` (プラズマ電流) は EQ 計算で必須.
- **(4) `MODELG=3`**: 平衡データを EQDSK ファイルから読み込むモードに設定.
  `MODELG=2` (解析的) なら `KNAMEQ` 不要だがデフォルトはこれです.
- **(5) `set_param_str`**: 文字列パラメータは **専用 API** が必須. 通常の
  `set_param` には渡せません ({doc}`parameter-setting` 方法 C 参照).
- **(6) `eq.run()`**: 引数なしだと `mode=1` (= EQDSK ファイル読み込んで
  平衡を構築する標準フロー). `tr` と違って **時間発展しません**.
- **(7) `eq.get_state()`**: 計算結果を `EqState` dataclass にコピーして
  返します. 詳細は {doc}`state` を参照.

## 期待される出力例

```bash
raxis=6.4321  qaxis=0.9876
```

完全な実行可能 notebook: {doc}`quickstart`.

## `tr` との違い

- **時間発展なし**: `eq.run()` は時間ステップを進めるのではなく `mode`
  (動作モード) を取ります. `mode=1` がデフォルト (詳細は {doc}`faq`).
- **6 個目の C ABI**: `eq_set_param_str` で文字列パラメータを受け付けます.
  `tr` も最近追加されましたが, EQ では設計初期から必要不可欠でした
  (EQDSK ファイル名を扱うため).
