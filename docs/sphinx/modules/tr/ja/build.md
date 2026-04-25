# 前提とビルド

## ライブラリをビルドする

```bash
cd /path/to/task                     # TASK リポジトリのルート
make -C lib  libs_pic                # 下位ライブラリの PIC 版
make -C pl   libs_pic                # プラズマ共通モジュール
make -C eq   libs_pic                # 平衡モジュール
make -C mtxp libs_pic                # 疎行列ソルバ
make -C bpsd libs_pic                # BPSD データ橋渡し
make -C tr   libtrapi.so             # tr モジュールの共有ライブラリ本体
```

最後に `tr/libtrapi.so` というファイルが出来ていれば成功です.

```bash
$ ls -lh tr/libtrapi.so
-rwxr-xr-x 1 user user 8.2M 4月 23 14:00 tr/libtrapi.so
```

ファイルサイズは環境によって違いますが, だいたい 5 〜 10 MB くらいです.

## エクスポートされている関数を確認する

```bash
$ nm -D tr/libtrapi.so | grep ' T tr_'
000000000005a1b0 T tr_finalize
000000000005a090 T tr_get_state
0000000000059e10 T tr_init
0000000000059f80 T tr_run
0000000000059d30 T tr_set_param
0000000000059ca0 T tr_set_param_str
00000000000?????? T tr_validate            # PR #172 以降
```

`T` 列のシンボルが「エクスポートされた関数」を示します.

## Python から見えるようにする

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

こうすると `import trlib` が通ります.
