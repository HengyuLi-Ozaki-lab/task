# コンテキストマネージャ `with` の解説

`Wrlib` は `tr` / `eq` と同じコンテキストマネージャ設計です. ここでは
wr 固有の側面に絞って解説します. 一般的な `with` 文の意味と落とし穴は
`tr` 側のコンテキストマネージャページ
(`docs/sphinx/modules/tr/ja/context-manager.md`) も参照してください.

## 最短の使い方

```python
from wrlib import Wrlib

with Wrlib() as wr:
    wr.set_params(RR=3.0, BB=3.0)
    wr.set_param("RF", 170e9)
    wr.run(nray_request=1)
    state = wr.get_state()
# ← ブロックを抜けた瞬間に wr_finalize が走る
```

## wr 固有の注意点

### レイバッファのサイズ

`wr` は `NRAYMAX × NSTPMAX` のレイ軌跡バッファを確保します. `NSTPMAX`
が大きいと (たとえば 10000 ステップ × 100 レイ), メモリ消費が無視できなく
なります. `with` で finalize を確実に走らせて解放しましょう.

### `wr` と `wrx` の関係

`wr` (geometric optics ray tracing) と `wrx` (beam tracing) はソースコード
が大きく重複していますが, **別の C ABI / 別の `.so`** です. 同一プロセスで
両方ロードできますが, それぞれ別の `Wrlib` / `Wrxlib` インスタンスです.

### 静的状態の取り扱い

`wr` の Fortran 側は他モジュールと同じく `pl_*` を共有します. `Wrlib()` を
作ると `pl_init` も走るので, `tr_mcp` と `wr_mcp` を同時起動しないでください.

## 例外時の挙動

`with` ブロック内で例外が発生しても, `__exit__` で `wr_finalize` が呼ばれ:

- レイバッファが解放
- `pl_*` 状態がリセット
- 次の `Wrlib()` セッションには影響しない

## `with` を使わない場合 (非推奨)

```python
wr = Wrlib()                          # ここで wr_init
try:
    wr.set_params(RR=3.0)
    wr.run(nray_request=1)
    state = wr.get_state()
finally:
    wr.close()
```
