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

**バッチモード実行：**

.. code-block:: bash

   cd ~/program/task/txnew
   ./txnew < input.dat

**対話モードでの実行：**

.. code-block:: text

   $ ./txnew
   # Welcome to GSAF
   # INPUT DISPLAY TYPE : 1)512x380 2)640x475 ... 0)quiet)
   0
   # INPUT : (C)ONTINUE,(O)PTION,(F)ILE,(H)ELP,(Q)UIT
   c
   ######## TASK/TX V5.52.20 ########
   ## TIME=  0.0000E+00  DT=  1.0000E-03  NEXT TIME =  1.0000E-01
   ## INPUT: R:RUN  C:CONT  P,V:PARM  G:GRAPH  W:STAT  S:SAVE  L:LOAD  I:INIT
             F,FR:FILE  N:PTRB  M:ITG  O:OUT  Q:QUIT
   r
   Calculating...
   NT =   1   T = 1.00E-03   IC =  5
   CPU = 0.01 (sec)   sim time = 1.0E-03 (sec)
   Ne(0) = 3.00E-01  Te(0) = 3.00E+00  Ti(0) = 3.00E+00  Wst = 4.50E-01
   ...
   q
   # CLOSED.

実行結果の見方
--------------

時間ステップごとに以下の情報が出力されます：

.. code-block:: text

   NT =  50   T = 5.00E-02   IC =  3
   CPU = 0.52 (sec)   sim time = 5.0E-02 (sec)  (50.0%)  ICave = 2.50
   Ne(0) = 2.95E-01  UePhi(0)=-1.23E+03  UiPhi(0)= 5.67E+02  N0(RB)= 1.00E+12
   NB(0) = 1.50E-01  NB(0.24)= 1.20E-01  NB(0.60)= 6.00E-02  PF    = 2.50E+00
   Te(0) = 3.20E+00  Ti(0)   = 2.80E+00  Wst     = 4.80E-01

各項目の意味：

* ``NT`` : 時間ステップ番号
* ``T`` : シミュレーション時間 [s]
* ``IC`` : Newton反復回数
* ``Ne(0)`` : 軸上電子密度 [10²⁰ m⁻³]
* ``Te(0)``, ``Ti(0)`` : 軸上温度 [keV]
* ``Wst`` : 蓄積エネルギー [MJ]
* ``NB`` : 高速粒子密度
* ``PF`` : 核融合出力指標

出力グラフ
==========

温度プロファイル
----------------

``G`` コマンドでグラフメニューに入り、``t1`` で電子温度プロファイルを表示：

.. figure:: _static/te_profile_example.png
   :width: 80%
   :align: center
   :alt: 電子温度プロファイル例

   電子温度の径方向分布。横軸は規格化小半径 ρ (0=軸、1=端)、
   縦軸は電子温度 Te [keV]。中心でピークを持ち、端に向かって減少する。

密度プロファイル
----------------

``n1`` で電子密度プロファイルを表示：

.. figure:: _static/ne_profile_example.png
   :width: 80%
   :align: center
   :alt: 電子密度プロファイル例

   電子密度の径方向分布。初期条件で設定したプロファイル形状
   (1-ρ²)^p の形で分布。

時間発展
--------

``gt`` で温度の時間発展を表示：

.. figure:: _static/time_evolution_example.png
   :width: 80%
   :align: center
   :alt: 時間発展例

   各物理量の時間発展。NBI加熱開始後、温度が上昇し、
   輸送損失とバランスして定常状態に達する様子が見られる。

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

期待される結果
--------------

* 中心電子温度: ~15-20 keV
* 中心イオン温度: ~12-15 keV
* 蓄積エネルギー: ~300-400 MJ
* エネルギー閉じ込め時間: ~3-5 s

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

定常判定基準
------------

以下の条件で定常状態と判定できます：

1. 蓄積エネルギー Wst の変化が 0.1% 以下
2. 中心温度の変化が 1% 以下
3. 入力電力と損失電力がバランス

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

結果の集約スクリプト例：

.. code-block:: bash

   # 各ログファイルから最終時刻の値を抽出
   for f in scan_n*.log; do
     echo -n "$f: "
     grep "Te(0)" $f | tail -1
   done

保存・再開
==========

シミュレーション状態の保存
--------------------------

対話モードで ``S`` コマンド：

.. code-block:: text

   ## INPUT: R:RUN  C:CONT  P,V:PARM  G:GRAPH  W:STAT  S:SAVE  L:LOAD ...
   s
   # INPUT FILE NAME FOR SAVE
   checkpoint_t100.dat
   # SAVE COMPLETED

保存されるデータ：

* 全入力パラメータ
* 状態変数 (密度、温度、速度等)
* 時間情報
* グラフィックス履歴

再開
----

.. code-block:: text

   ## INPUT: R:RUN  C:CONT  P,V:PARM  G:GRAPH  W:STAT  S:SAVE  L:LOAD ...
   l
   # INPUT FILE NAME FOR LOAD
   checkpoint_t100.dat
   # LOAD COMPLETED
   r
   # Calculating from T = 1.00E-01 ...

グラフィックス出力
==================

グラフメニュー
--------------

``G`` コマンドでグラフメニューに入ります：

.. code-block:: text

   ## INPUT: R:RUN  C:CONT  P,V:PARM  G:GRAPH ...
   g
   # GRAPH MENU:
   # t1: Te profile    t2: Ti profile    t3: Tz profile
   # n1: ne profile    n2: ni profile    n3: nz profile
   # u1: Ue profile    u2: Ui profile
   # q: q profile      s: shear profile
   # j: j profile      p: pressure profile
   # gt: T vs time     gn: n vs time     gw: W vs time
   # 2d: 2D contour    q: quit graph menu

プロファイルプロット
--------------------

* ``t1``: 電子温度プロファイル Te(ρ)
* ``t2``: イオン温度プロファイル Ti(ρ)
* ``n1``: 電子密度プロファイル ne(ρ)
* ``q``: 安全係数プロファイル q(ρ)
* ``j``: 電流密度プロファイル j(ρ)

時間発展プロット
----------------

* ``gt``: 温度時間発展 T(t)
* ``gn``: 密度時間発展 n(t)
* ``gw``: エネルギー時間発展 W(t)

トラブルシューティング
======================

収束しない場合
--------------

**症状:** ``IC`` が ``ICMAX`` に達し、計算が進まない

**対策:**

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

**症状:** 値が発散する、NaN が発生する

**対策:**

1. SUPG安定化を有効にする

   .. code-block:: fortran

      iSUPG3 = 1
      iSUPG6 = 1
      iSUPG8 = 1

2. 陰解法を使用

   .. code-block:: fortran

      ADV = 1.0

3. 格子点数を増やす

   .. code-block:: fortran

      NRMAX = 100

LAPACK エラー
-------------

**症状:** ``ERROR(TXLOOP) : GBSV, IERR = -1``

**原因:** LAPACKライブラリが正しくリンクされていない

**対策:**

1. LAPACKをインストール

   .. code-block:: bash

      # Ubuntu/Debian
      sudo apt-get install liblapack-dev libblas-dev

2. make.header で LAPACK を有効化

   .. code-block:: makefile

      LAPACK = lapack.f
      LIBLA = -llapack -lblas

3. txnew を再ビルド

   .. code-block:: bash

      cd ~/program/task/txnew
      make clean
      make

メモリ不足
----------

**症状:** セグメンテーション違反、メモリエラー

**対策:**

1. 格子点数を減らす

   .. code-block:: fortran

      NRMAX = 30  ! デフォルト50から削減

2. 出力間隔を増やす

   .. code-block:: fortran

      NTSTEP = 100  ! メモリ使用量削減
