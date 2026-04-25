# 前提とビルド

## ライブラリをビルドする

```bash
cd /path/to/task                     # TASK リポジトリのルート

# 全サブモジュールの PIC アーカイブ
make -C lib  libs_pic
make -C pl   libs_pic
make -C eq   libs_pic
make -C tr   libs_pic
make -C ti   libs_pic
make -C fp   libs_pic
make -C wr   libs_pic
make -C wrx  libs_pic
make -C mtxp libs_pic
make -C bpsd libs_pic

# tot 本体
make -C tot  libtotapi.so
```

`tot` は他のモジュール (eq, tr, ti, fp, wr, wrx) すべてを **静的にリンク**
した最終バイナリです. **すべてのサブモジュールがビルド済みである必要が
あります**.

## エクスポートされている関数を確認する

`tot` は **6 関数** ABI です (`eq`/`fp` と同じ拡張版).

```bash
$ nm -D tot/libtotapi.so | grep ' T tot_'
... T tot_finalize
... T tot_get_state
... T tot_init
... T tot_run
... T tot_set_param
... T tot_set_param_str       # <-- 6 番目: プレフィックス付きパラメータ用
```

## Python から見えるようにする

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

こうすると `import totlib` が通ります.
