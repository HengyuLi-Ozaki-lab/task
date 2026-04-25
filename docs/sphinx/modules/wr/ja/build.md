# 前提とビルド

## ライブラリをビルドする

```bash
cd /path/to/task                     # TASK リポジトリのルート
make -C lib  libs_pic
make -C pl   libs_pic
make -C eq   libs_pic
make -C mtxp libs_pic
make -C bpsd libs_pic
make -C wr   libwrapi.so
```

最後に `wr/libwrapi.so` というファイルが出来ていれば成功です.

## エクスポートされている関数を確認する

`wr` は **5 関数** ABI です (`tr` と同じ標準パターン).

```bash
$ nm -D wr/libwrapi.so | grep ' T wr_'
... T wr_finalize
... T wr_get_state
... T wr_init
... T wr_run
... T wr_set_param
```

## Python から見えるようにする

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

こうすると `import wrlib` が通ります.
