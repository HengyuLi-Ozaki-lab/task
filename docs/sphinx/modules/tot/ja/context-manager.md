# コンテキストマネージャ `with` の解説

`Tot` は `tr` / `eq` と同じコンテキストマネージャ設計です. ここでは
tot 固有の側面に絞って解説します. 一般的な `with` 文の意味と落とし穴は
`tr` 側のコンテキストマネージャページ
(`docs/sphinx/modules/tr/ja/context-manager.md`) も参照してください.

## 最短の使い方

```python
from totlib import Tot

with Tot() as tot:
    tot.set_param("eq:RR", 6.5)
    tot.set_param("tr:NSMAX", 2)
    tot.run(ntmax=10)
    state = tot.get_state()
# ← ブロックを抜けた瞬間に tot_finalize が走る
```

## tot 固有の注意点

### 全サブモジュール同時 init

`Tot()` を作ると, 内部で **eq / tr / ti / fp / wr / wrx を全部 init します**.
そのため:

- 単独で `Trlib()`, `Wrxlib()` などを並行して使えません — 既に tot が
  握っているため衝突
- メモリ消費は単独モジュールの単純な合計より大きい

### `with` を抜けるときの順次 finalize

`__exit__` で `tot_finalize` が走ると, 内部で各サブモジュールも順次
finalize されます. 順序は:

```
wr/wrx → fp → ti → tr → eq → pl
```

(後で初期化されたものから先に finalize する LIFO 規則)

### サブモジュールの present フラグ

`Tot()` でロードされたサブモジュールは `state.tr_present`, `state.fp_present`
等のフラグで確認できます. 全部 1 なら全モジュールが正常に init されて
います ({doc}`state` 参照).

## 例外時の挙動

`with` ブロック内で例外が発生しても, `__exit__` で `tot_finalize` が
呼ばれ, **すべてのサブモジュール状態がリセット** されます. これにより:

- 大量メモリ確保 (特に fp の 5D グリッド) が解放
- 各サブモジュールの SAVE フラグが再起動
- 次の `Tot()` セッションには影響しない

## `with` を使わない場合 (非推奨)

```python
tot = Tot()                         # 全モジュール init
try:
    tot.set_param("eq:RR", 6.5)
    tot.run(ntmax=10)
    state = tot.get_state()
finally:
    tot.close()                      # 全モジュール finalize
```

`tot` は確保するメモリが多いので, `with` の使用が **特に重要** です.
