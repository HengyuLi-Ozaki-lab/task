==========
使用例
==========

基本的な使用例
==============

入力ファイル例
--------------

標準的なトカマクシミュレーションの入力例：

.. code-block:: fortran

   &tx
     ! プラズマ配位
     RR = 3.2          ! 大半径 [m]
     RA = 0.8          ! 小半径 [m]
     BB = 2.68         ! トロイダル磁場 [T]
     rIPs = 1.0        ! プラズマ電流 [MA]
     rIPe = 1.0

     ! 初期プロファイル
     PN0 = 0.3         ! 電子密度（軸） [10^20 m^-3]
     PNa = 0.05        ! 電子密度（端）
     PTe0 = 3.0        ! 電子温度（軸） [keV]
     PTea = 0.2        ! 電子温度（端）
     PTi0 = 3.0        ! イオン温度（軸）
     PTia = 0.2        ! イオン温度（端）

     ! 輸送係数
     Dfs0(1) = 0.1     ! 粒子拡散係数
     Chis0(1) = 1.0    ! 熱拡散係数（電子）
     Chis0(2) = 1.0    ! 熱拡散係数（イオン）

     ! 加熱
     PNBHT1 = 5.0      ! NBI電力 [MW]
     Ebmax = 80.0      ! ビームエネルギー [keV]

     ! 数値パラメータ
     NRMAX = 50        ! 格子点数
     NTMAX = 1000      ! 時間ステップ数
     DT = 1.0D-3       ! 時間刻み [s]
     NTSTEP = 100      ! 出力間隔
   &end

実行方法
--------

.. code-block:: bash

   cd ~/program/task/txnew
   ./txnew < input.dat

対話モードでの実行：

.. code-block:: text

   $ ./txnew
   # INPUT DISPLAY TYPE: 0)quiet
   0
   # INPUT: (C)ONTINUE
   c
   # TX MENU: R/RUN
   r
   # (計算実行)
   # TX MENU: Q/QUIT
   q

NBI加熱シミュレーション
=======================

入力ファイル
------------

.. code-block:: fortran

   &tx
     ! ITER-like configuration
     RR = 6.2
     RA = 2.0
     BB = 5.3
     rIPs = 15.0
     rIPe = 15.0

     ! 初期プロファイル
     PN0 = 1.0
     PNa = 0.1
     PTe0 = 10.0
     PTea = 0.5
     PTi0 = 10.0
     PTia = 0.5

     ! NBI加熱
     PNBHT1 = 16.5     ! 接線NBI
     PNBHT2 = 16.5     ! 接線NBI
     Ebmax = 1000.0    ! 1 MeV ビーム

     ! 輸送
     MDANOM = 1        ! 異常輸送モデル
     FSANOM(1) = 1.0
     FSANOM(2) = 1.0

     NTMAX = 5000
     DT = 1.0D-3
   &end

定常状態計算
============

定常解を求める場合：

.. code-block:: fortran

   &tx
     ! 長時間計算
     NTMAX = 10000
     DT = 1.0D-2       ! 大きめの時間刻み

     ! 収束判定を厳しく
     EPS = 1.0D-5
     ICMAX = 200
   &end

パラメータスキャン
==================

密度スキャン例
--------------

複数の入力ファイルを準備：

.. code-block:: bash

   # scan_n1.dat
   &tx
     PN0 = 0.2
     ...
   &end

   # scan_n2.dat
   &tx
     PN0 = 0.4
     ...
   &end

   # scan_n3.dat
   &tx
     PN0 = 0.6
     ...
   &end

バッチ実行：

.. code-block:: bash

   for f in scan_n*.dat; do
     ./txnew < $f > ${f%.dat}.log
   done

保存・再開
==========

シミュレーション状態の保存
--------------------------

対話モードで：

.. code-block:: text

   # TX MENU: S/SAVE
   s
   # ファイル名入力
   save001.dat

再開
----

.. code-block:: text

   # TX MENU: L/LOAD
   l
   # ファイル名入力
   save001.dat
   # TX MENU: R/RUN
   r

グラフィックス出力
==================

プロファイルプロット
--------------------

.. code-block:: text

   # TX MENU: G/GRAPH
   g
   # グラフメニュー
   # t1: 電子温度プロファイル
   # t2: イオン温度プロファイル
   # n1: 電子密度プロファイル
   # q: 安全係数プロファイル

時間発展プロット
----------------

.. code-block:: text

   # グラフメニュー
   # gt: 温度時間発展
   # gn: 密度時間発展
   # gw: エネルギー時間発展

トラブルシューティング
======================

収束しない場合
--------------

1. 時間刻みを小さくする

   .. code-block:: fortran

      DT = 1.0D-4  ! より小さく

2. 収束判定を緩める

   .. code-block:: fortran

      EPS = 1.0D-2  ! より大きく

3. 反復回数を増やす

   .. code-block:: fortran

      ICMAX = 500

不安定な場合
------------

1. SUPG安定化を有効にする

   .. code-block:: fortran

      iSUPG3 = 1
      iSUPG6 = 1
      iSUPG8 = 1

2. 陰解法を使用

   .. code-block:: fortran

      ADV = 1.0
