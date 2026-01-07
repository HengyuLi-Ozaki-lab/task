.. TASK/TXnew documentation master file

===================================
TASK/TXnew マニュアル
===================================

TASK/TXnewは、トカマクプラズマの1次元輸送シミュレーションコードです。
電子・イオン・不純物の密度、温度、速度の時間発展を自己無撞着に計算します。

.. toctree::
   :maxdepth: 2
   :caption: 目次

   overview
   installation
   input_parameters
   output_variables
   equations
   examples
   references

概要
====

TXnewモジュールは以下の物理過程を含みます：

* 粒子輸送（拡散・対流）
* 熱輸送（熱伝導・対流）
* ネオクラシカル輸送
* 異常輸送（乱流モデル）
* NBI/RF加熱
* 中性粒子相互作用
* 放射損失

クイックスタート
================

.. code-block:: bash

   # txnewのビルド
   cd ~/program/task/txnew
   make

   # 実行
   ./tx2

   # 入力プロンプトで
   # 0 (quiet mode)
   # c (continue)
   # r (run)
   # q (quit)

インデックス
============

* :ref:`genindex`
* :ref:`search`
