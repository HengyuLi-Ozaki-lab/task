# 前提とビルド

## ライブラリをビルドする

```bash
cd /path/to/task                     # TASK リポジトリのルート
make -C lib  libs_pic
make -C pl   libs_pic
make -C eq   libs_pic
make -C mtxp libs_pic
make -C bpsd libs_pic
make -C wrx  libwrxapi.so
```

最後に `wrx/libwrxapi.so` というファイルが出来ていれば成功です.

## エクスポートされている関数を確認する

`wrx` は **5 関数** ABI です.

```bash
$ nm -D wrx/libwrxapi.so | grep ' T wrx_'
... T wrx_finalize
... T wrx_get_state
... T wrx_init
... T wrx_run
... T wrx_set_param
```

## Python から見えるようにする

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

こうすると `import wrxlib` が通ります.

## `wr` との違い

`wrx` は `wr` (geometric optics) の **拡張版** (eXtended) で, **beam tracing**
機能を持ちます:

- **`wr`**: レイに幅なし (ペンシルビーム). ビームの広がりを多数のレイで
  近似
- **`wrx`**: 各レイに曲率・幅を持たせ, ビーム形状を解析的に展開

計算精度は `wrx` の方が高いですが, コストも大きくなります.

コードベースは一部を `wr` と共有していますが, **別の `.so`** です.
