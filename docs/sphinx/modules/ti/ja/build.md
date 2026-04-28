# 前提とビルド

## ライブラリをビルドする

```bash
cd /path/to/task                     # TASK リポジトリのルート
make -C lib  libs_pic                # 下位ライブラリの PIC 版
make -C pl   libs_pic                # プラズマ共通モジュール
make -C eq   libs_pic                # 平衡モジュール
make -C mtxp libs_pic                # 疎行列ソルバ
make -C bpsd libs_pic                # BPSD データ橋渡し
make -C ti   libtiapi.so             # ti モジュールの共有ライブラリ本体
```

最後に `ti/libtiapi.so` というファイルが出来ていれば成功です.

## エクスポートされている関数を確認する

`tr` と同じ **5 関数** がエクスポートされます ([共通アーキテクチャ](../../../portal/ja/common/architecture.md) の標準パターン).

```bash
$ nm -D ti/libtiapi.so | grep ' T ti_'
... T ti_finalize
... T ti_get_state
... T ti_init
... T ti_run
... T ti_set_param
```

`T` 列のシンボルが「エクスポートされた関数」を示します.

## Python から見えるようにする

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

こうすると `import tilib` が通ります.
