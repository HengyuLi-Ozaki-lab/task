# コンテキストマネージャ `with` の解説

`Tilib` は `tr` / `eq` と同じコンテキストマネージャ設計です. ここでは ti
固有の側面に絞って解説します. 一般的な `with` 文の意味と落とし穴は
`tr` 側のコンテキストマネージャページ
(`docs/sphinx/modules/tr/ja/context-manager.md`) も参照してください.

## 最短の使い方

```python
from tilib import Tilib

with Tilib() as ti:
    ti.set_params(RR=3.0, BB=3.0, NSMAX=2)
    ti.run(ntmax=10)
    state = ti.get_state()
# ← ブロックを抜けた瞬間に ti_finalize が走る
```

## ti 固有の注意点

### 補助物理モジュールの状態

`ti` は内部で `tr`, `eq`, `bpsd` 等の他モジュール状態を参照します.
そのため `Tilib()` を作ると, **裏で `pl_init`, `eq_init` も呼ばれます**.

- `Tilib()` と `Trlib()` を **同一プロセスで同時に作ると衝突します**
  (両方が同じグローバル `pl_*` 状態を握るため)
- `Trlib()` で実験した後 `Tilib()` を作りたい場合は, `Trlib()` のブロックを
  抜けてから (= `tr_finalize` が走ってから) `Tilib()` を作ってください

### 反復ソルバの状態

`ti` の `run()` は内部反復ソルバ (`MAXLOOP` 回まで) を回します. 反復が
収束しなかった場合の状態は **未定義** (実装依存) です. `with` を抜けて
`ti_finalize` で正しくクリアされるので, 次の `Tilib()` セッションには
影響しません.

## `with` を使わない場合 (非推奨)

```python
ti = Tilib()                          # ここで ti_init
try:
    ti.set_params(RR=3.0, NSMAX=2)
    ti.run(ntmax=10)
    state = ti.get_state()
finally:
    ti.close()                        # 例外発生時も必ず実行
```

`try/finally` を毎回書くのは面倒なので, **特別な理由がない限り `with` を
使ってください**.

## 例外時の挙動

`with` ブロック内で例外が発生しても, `__exit__` (= `close()`) が必ず
呼ばれて `ti_finalize` が走ります. これにより:

- 反復ソルバの中途状態が次のセッションに漏れない
- `pl_*` の共有状態が正しくリセットされる
- メモリ確保した配列が解放される
