# 前提とビルド

## ライブラリをビルドする

```bash
cd /path/to/task                     # TASK リポジトリのルート
make -C lib   libs_pic
make -C pl    libs_pic
make -C bpsd  libs_pic
make -C mtxp  libs_pic
make -C eq    libeqapi.so
```

成功すると `eq/libeqapi.so` が出来ていれば OK です.

## エクスポートされている関数を確認する

`nm` で **6 個** のシンボルが確認できます (eq だけは 6 個, 他モジュールは 5 個):

```bash
$ nm -D eq/libeqapi.so | grep ' T eq_'
... T eq_finalize
... T eq_get_state
... T eq_init
... T eq_run
... T eq_set_param
... T eq_set_param_str       # <-- 6 番目: EQ 固有 (文字列パラメータ用)
... T eq_validate            # PR #164 以降
```

`T` 列のシンボルが「エクスポートされた関数」を示します. 6 番目の
`eq_set_param_str` は `KNAMEQ` 等の `CHARACTER(LEN=80)` 文字列パラメータを
受け取る専用 API です ({ref}`共通アーキテクチャ <portal:common-architecture>`
の 5 関数 ABI から拡張).

## Python から見えるようにする

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

こうすると `import eqlib` が通ります.
