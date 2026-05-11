# 前提とビルド

## ライブラリをビルドする

```bash
cd /path/to/task                     # TASK リポジトリのルート
make -C lib  libs_pic
make -C pl   libs_pic
make -C eq   libs_pic
make -C mtxp libs_pic
make -C bpsd libs_pic
make -C fp   libfpapi.so
```

最後に `fp/libfpapi.so` というファイルが出来ていれば成功です.

## エクスポートされている関数を確認する

`fp` は `eq` と同じ **6 関数** ABI です (5 関数 + `fp_set_param_str`).

```bash
$ nm -D fp/libfpapi.so | grep ' T fp_'
... T fp_finalize
... T fp_get_state
... T fp_init
... T fp_run
... T fp_set_param
... T fp_set_param_str       # <-- 6 番目: 文字列パラメータ用 (KNAMEQ)
```

`fp_set_param_str` が必要な理由は, fp が `pl_*` モジュールから引き継ぐ
`KNAMEQ` (平衡データファイル名) を上書きできるようにするためです.

## Python から見えるようにする

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

こうすると `import fplib` が通ります.
