# コンテキストマネージャ `with` の解説

`Wrxlib` は `tr` / `eq` / `wr` と同じコンテキストマネージャ設計です. ここでは
wrx 固有の側面に絞って解説します. 一般的な `with` 文の意味と落とし穴は
`tr` 側のコンテキストマネージャページ
(`docs/sphinx/modules/tr/ja/context-manager.md`) も参照してください.

## 最短の使い方

```python
from wrxlib import Wrxlib

with Wrxlib() as wrx:
    wrx.set_params(RR=3.0, BB=3.0, NSMAX=1)
    wrx.set_param("NRAYMAX", 1)
    wrx.set_param("RFIN[1]", 170e9)
    wrx.set_param("RPIN[1]", 3.5)
    wrx.run(nray_request=1)
    state = wrx.get_state()
# ← ブロックを抜けた瞬間に wrx_finalize が走る
```

## wrx 固有の注意点

### ビーム曲率・幅データのメモリ

`wrx` は各レイに対してビーム形状 (曲率テンソル + 波束展開係数) を追跡
するため, `wr` よりも **レイ 1 本あたりのメモリ消費が多い** です.

```
wr: レイ状態 ≈ 20 double per step
wrx: レイ状態 ≈ 40–50 double per step  (曲率・幅情報含む)
```

大きな `NRAYMAX × NSTPMAX` では数百 MB に達することもあります.
`with` を抜けないと解放されません.

### `wr` と `wrx` を同一プロセスで使う

`wr` (libwrapi.so) と `wrx` (libwrxapi.so) は **別の `.so`** なので, 同一
プロセスでロード自体は可能です. ただし両方とも `pl_*` 状態を共有するので,
**同時に `init` 状態にはできません**. 順次使う形になります:

```python
with Wrlib() as wr:
    wr.set_param("RF", 170e9)
    wr.run(nray_request=1)

# wr_finalize 後
with Wrxlib() as wrx:
    wrx.set_param("RFIN[1]", 170e9)
    wrx.run(nray_request=1)
```

### `run` の引数名

Python API では `run(nray_request=N)` と書きますが, 内部 C ABI では
`nstpmax_arg` (最大ステップ数の上書き値) として扱われている場合が
あります. 挙動が `wr` と違う場合は `wrxlib` のドキュメンテーション
文字列 ({doc}`api-reference`) を確認してください.

## 例外時の挙動

`with` ブロック内で例外が発生しても, `__exit__` で `wrx_finalize` が呼ばれ:

- レイ軌跡バッファ + ビーム形状データが解放
- `pl_*` 状態がリセット
- 次のセッションには影響しない

## `with` を使わない場合 (非推奨)

```python
wrx = Wrxlib()
try:
    wrx.set_params(RR=3.0, NSMAX=1)
    wrx.run(nray_request=1)
    state = wrx.get_state()
finally:
    wrx.close()
```
