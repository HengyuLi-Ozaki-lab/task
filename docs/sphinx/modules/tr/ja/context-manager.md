# コンテキストマネージャ `with` の解説

`Trlib` は **コンテキストマネージャ** として設計されており, `with` 文と
組み合わせて使うのが推奨される使い方です. このページでは, なぜ `with`
が必要なのか, 内部で何が起きているのか, そして起こりがちな間違いを
順番に説明します.

## なぜ `with` が必要か

`tr` ライブラリは Fortran 側に **巨大なグローバル状態** (TRCOMM モジュール
変数群) を持っています. 1 プロセス 1 インスタンスのシングルトン制約
({doc}`faq` Q4 参照) があり, さらに `tr_init` で確保した動的配列を
`tr_finalize` で必ず開放しなければなりません. 開放を忘れると:

- メモリリーク (大きな配列が確保されたまま)
- 次に `Trlib()` を作ろうとすると `TrlibStateError` で弾かれる
- 同じプロセスで再シミュレーションができなくなる

`with` 文は **ブロックの出口で必ず後始末を実行する** ことを Python が
言語レベルで保証する仕組みなので, 例外が発生しても確実に
`tr_finalize` が呼ばれます.

```{admonition} Python の `with` 文 (補足)
:class: note

ファイル操作の `with open(...) as f:` と同じ仕組みです. 「入るとき / 出るとき
に必ず何かを実行したい」リソース (ファイル, ロック, データベース接続,
共有ライブラリなど) で使われる慣用パターンです.
```

## 最短の使い方

```python
from trlib import Trlib

with Trlib() as tr:
    tr.set_params(RR=3.0, BB=3.0)
    tr.run(ntmax=10)
    state = tr.get_state()
# ← ブロックを抜けた瞬間に tr_finalize が走る
```

これで `with` ブロックを抜けた直後に `Trlib.close()` (= `tr_finalize` を内部で
呼ぶ) が実行されます.

## 内部で何が起きているか

`Trlib` の実装はおおよそ次のようになっています (`python/trlib/trlib.py`):

```python
class Trlib:
    def __init__(self, *, lib_path=None):
        # ライブラリをロードし tr_init を呼ぶ
        self._lib = _ffi.load_library(lib_path)
        ierr = self._lib.tr_init()
        raise_for_ierr("tr_init", ierr)
        self._closed = False

    def __enter__(self) -> "Trlib":
        return self                        # `with X() as tr:` の `tr` がこの戻り値

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()                       # 例外の有無に関わらず呼ばれる

    def close(self) -> None:
        """Finalise the library. Idempotent."""
        if self._closed:
            return                         # 二重 close は無害
        ierr = self._lib.tr_finalize()
        self._closed = True
        raise_for_ierr("tr_finalize", ierr)

    def __del__(self) -> None:
        try:
            self.close()                   # GC 時の保険
        except Exception:
            pass                           # デストラクタは絶対に raise しない
```

ポイント:

- **`__init__` で `tr_init` を呼ぶ**. `Trlib()` を作った時点でライブラリは
  初期化済み. `__enter__` 自体は何もしません.
- **`__exit__` は例外伝播を阻害しない**. `close()` が呼ばれた後, 元の例外は
  そのまま外に飛びます (`__exit__` が `True` を返さないため).
- **`close()` は冪等 (idempotent)**. `with` の終了, 明示的な `tr.close()`,
  `__del__` (GC) のどれが呼ばれても安全.
- **デストラクタは保険**. `with` を使わずに参照が消えた場合でも `__del__`
  が `close()` を呼ぼうとしますが, GC のタイミングは保証されないので
  **頼ってはいけません**.

## `with` を使わない場合 (非推奨)

`with` の代わりに明示的に書くと次と等価です:

```python
tr = Trlib()                          # ここで tr_init
try:
    tr.set_params(RR=3.0)
    tr.run(ntmax=10)
    state = tr.get_state()
finally:
    tr.close()                        # 例外発生時も必ず実行
```

`try/finally` を毎回書くのは面倒ですし, 書き忘れるリスクがあります.
**特別な理由がない限り `with` を使ってください**.

## 例外が発生したらどうなるか

`with` ブロック内で例外が発生しても, `__exit__` (= `close()`) は **必ず**
実行されます.

```python
with Trlib() as tr:
    tr.set_params(RR=3.0, BB=3.0)
    tr.run(ntmax=10)
    raise RuntimeError("意図的にエラー")  # ←
    state = tr.get_state()                 # 実行されない
# ← この行に来る前に tr_finalize は呼ばれている
# RuntimeError はそのまま外に飛ぶ
```

これで例外時もメモリリークやシングルトン状態の取り残しが起きません.

```{admonition} `tr_finalize` 自体が失敗したら?
:class: warning

`__exit__` が `close()` を呼んだとき, `tr_finalize` が ierr を返すと
`raise_for_ierr` が `TrlibError` を投げます. このとき:

- `with` ブロックで既に例外が起きていた場合: その例外は `__context__` に
  保持され, `TrlibError` が新しい例外として伝搬します (Python の
  exception chaining).
- 例外が起きていなかった場合: `TrlibError` がそのまま伝搬します.

実用上 `tr_finalize` が失敗するのは稀ですが, ログ収集などでデバッグできる
ようにしておきましょう.
```

## 起こりがちな間違い

### 間違い 1: 同じプロセスで 2 個目を作ろうとする

```python
with Trlib() as tr1:
    ...
with Trlib() as tr2:    # OK: tr1 は既に finalize 済み
    ...

# ↓ NG
with Trlib() as tr1:
    with Trlib() as tr2:   # TrlibStateError (シングルトン違反)
        ...
```

`tr_finalize` が完了したあとなら次の `Trlib()` は問題なく作れます. 同時に
2 つは不可です ({doc}`faq` Q4).

### 間違い 2: `with` の外で `state` を `get_state` 経由で取り直そうとする

```python
with Trlib() as tr:
    state = tr.get_state()
print(state.scalars["T"])    # OK: state は純 Python オブジェクト

# ↓ NG
with Trlib() as tr:
    pass
state = tr.get_state()       # TrlibStateError: tr は既に閉じている
```

`with` を抜けた後の `tr` ハンドルは閉じています. 結果が必要なら **ブロック
内で取得** してから外で使ってください. `TrState` は `dataclass` なので
ブロック外でも普通に参照できます.

### 間違い 3: 長時間ブロックを抱えたまま放置する

```python
with Trlib() as tr:
    tr.run(ntmax=100000)       # 数十分
    do_something_else()         # この間 Trlib が確保したメモリが居座る
```

シミュレーションが終わったら, 後続処理に入る前に `with` を抜けるのが
無駄が無いです. 結果だけ取り出しておけば十分:

```python
with Trlib() as tr:
    tr.run(ntmax=100000)
    state = tr.get_state()
# ← ここで finalize. 以降は state だけ使う
do_something_else_with(state)
```

## 他言語との対応

`with` 文は他言語の以下のパターンに相当します. C/C++ や Go から来た方は
こちらが直感的かもしれません.

| 言語 | パターン | 対応 |
|---|---|---|
| C++ | RAII (デストラクタで開放) | `Trlib()` のスタックローカル変数のように振る舞う |
| Java | try-with-resources | `try (Trlib tr = new Trlib())` 相当 |
| Go  | `defer tr.Close()` | `with` ブロックの出口に該当 |
| Rust | `Drop` トレイト | スコープ離脱時に自動 drop |

## まとめ

- `Trlib` は必ず `with` で囲むのが推奨.
- `__enter__` は何もしない (返すだけ); 初期化は `__init__` で完了している.
- `__exit__` は例外の有無に関係なく `close()` を呼び, `tr_finalize` を発火.
- `close()` は冪等. 二重に呼んでも安全.
- 結果 (`TrState`) は `with` ブロック内で取り出して, 外で使う.
