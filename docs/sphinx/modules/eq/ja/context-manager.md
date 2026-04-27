# コンテキストマネージャ `with` の解説

`Eq` クラスはコンテキストマネージャとして設計されており, `with` 文と
組み合わせて使うのが推奨です. `tr` と同じ仕組みなので, 詳細な解説は
`tr` 側のコンテキストマネージャページ
(`docs/sphinx/modules/tr/ja/context-manager.md`) も参照してください.

## なぜ `with` が必要か

`eq` の Fortran 側は **EQCOMM 等のグローバルモジュール状態** を持ち,
1 プロセス 1 インスタンスのシングルトン制約があります. `eq_init` で
動的配列を確保し, `eq_finalize` で解放するのを必ずペアにする必要が
あります.

`with` 文は **ブロックの出口で必ず後始末を実行する** ことを Python が
言語レベルで保証する仕組みなので, 例外発生時も確実に `eq_finalize` が
呼ばれます.

## 最短の使い方

```python
from eqlib import Eq

with Eq() as eq:
    eq.set_param("RR", 6.5)
    eq.set_param("BB", 5.3)
    eq.set_param("RIP", 1.5)
    eq.run()
    state = eq.get_state()
# ← ブロックを抜けた瞬間に eq_finalize が走る
```

## 内部で何が起きているか

`Eq` の実装はおおよそ次のようになっています:

```python
class Eq:
    def __init__(self, *, lib_path=None):
        self._lib = _ffi.load_library(lib_path)
        ierr = self._lib.eq_init()
        raise_for_ierr("eq_init", ierr)
        self._closed = False

    def __enter__(self) -> "Eq":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        """Finalise the library. Idempotent."""
        if self._closed:
            return
        ierr = self._lib.eq_finalize()
        self._closed = True
        raise_for_ierr("eq_finalize", ierr)
```

ポイント:

- `__init__` で `eq_init` を呼ぶ. `Eq()` を作った時点でライブラリは初期化
  済み.
- `__exit__` は例外伝播を阻害せず, `close()` を呼んだ後に元の例外をその
  まま外に飛ばす.
- `close()` は冪等 (idempotent). 二重呼び出しは安全.

## `with` を使わない場合 (非推奨)

```python
eq = Eq()                         # ここで eq_init
try:
    eq.set_param("RR", 6.5)
    eq.run()
    state = eq.get_state()
finally:
    eq.close()                    # 例外発生時も必ず実行
```

`try/finally` を毎回書くのは面倒なので, **特別な理由がない限り `with` を
使ってください**.

## 例外が発生したらどうなるか

`with` ブロック内で例外が発生しても, `__exit__` (= `close()`) は **必ず**
実行されます. これでメモリリークや状態の取り残しが起きません.

## 起こりがちな間違い

### `with` の外で `state` を取り直そうとする

```python
with Eq() as eq:
    state = eq.get_state()
print(state.scalars["raxis"])    # OK: state は純 Python オブジェクト

# ↓ NG
with Eq() as eq:
    pass
state = eq.get_state()           # EqlibError: eq は既に閉じている
```

`with` を抜けた後の `eq` ハンドルは閉じています. 結果が必要なら **ブロック
内で取得** してから外で使ってください.

### 同じプロセスで 2 個目を作ろうとする

```python
# ↓ NG (シングルトン違反)
with Eq() as eq1:
    with Eq() as eq2:    # EqlibError
        ...
```

順次なら OK:

```python
with Eq() as eq1:
    ...
with Eq() as eq2:        # OK: eq1 は finalize 済み
    ...
```
