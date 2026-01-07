==========
インストール
==========

必要条件
========

* Fortran 95以降のコンパイラ（gfortran, ifort等）
* GSAFグラフィックライブラリ
* X11ライブラリ（グラフィック表示用）
* オプション: LAPACK/BLAS（高速行列計算）

ビルド手順
==========

1. 依存ライブラリのビルド
-------------------------

.. code-block:: bash

   # GSAFライブラリ
   cd ~/program/gsaf/src
   make && make install

   # BPSDライブラリ
   cd ~/program/bpsd
   make

   # TASKライブラリ
   cd ~/program/task/lib
   make

   # 行列ソルバ
   cd ~/program/task/mtxp
   make

   # プラズマプロファイル（txnewの依存）
   cd ~/program/task/pl
   make

   # 平衡計算（txnewの依存）
   cd ~/program/task/eq
   make

2. TXnewのビルド
----------------

.. code-block:: bash

   cd ~/program/task/txnew
   make

3. 動作確認
-----------

.. code-block:: bash

   cd ~/program/task/txnew
   ./txnew

   # プロンプトで:
   # 0 (quiet mode)
   # c (continue)
   # r (run)
   # q (quit)

make.headerの設定
=================

``~/program/task/make.header`` でコンパイラ設定を行います：

.. code-block:: makefile

   # gfortran (64bit) の場合
   FCFIXED = gfortran -ffixed-form
   FCFREE = gfortran -ffree-form
   OFLAGS = -g -O3 -m64 -std=legacy

   # ifort の場合
   # FCFIXED = ifort -fixed
   # FCFREE = ifort -free
   # OFLAGS = -g -O3

トラブルシューティング
======================

リンクエラー
------------

GSAFライブラリのパスが正しく設定されているか確認：

.. code-block:: bash

   ls ~/lib/libg*.a

X11エラー
---------

X11環境から実行するか、quietモード（0）を選択してください。
