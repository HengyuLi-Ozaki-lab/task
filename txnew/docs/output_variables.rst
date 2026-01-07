==========
出力物理量
==========

TXnewが計算・出力する物理量について説明します。

グローバル量
============

エネルギー関連
--------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 20

   * - 変数名
     - 説明
     - 単位
     - 定義
   * - WST(1)
     - 電子蓄積エネルギー
     - MJ
     - :math:`\int \frac{3}{2} n_e T_e dV`
   * - WST(2)
     - イオン蓄積エネルギー
     - MJ
     - :math:`\int \frac{3}{2} n_i T_i dV`
   * - WST(3)
     - 不純物蓄積エネルギー
     - MJ
     - :math:`\int \frac{3}{2} n_z T_z dV`
   * - WFT
     - 高速イオンエネルギー
     - MJ
     - ビーム粒子のエネルギー
   * - WPT
     - 全蓄積エネルギー
     - MJ
     - :math:`W_{tot} = \sum W_s`

入力電力
--------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15

   * - 変数名
     - 説明
     - 単位
   * - POHT
     - オーミック加熱電力
     - MW
   * - PNBT
     - NBI加熱電力
     - MW
   * - PRFT
     - RF加熱電力
     - MW
   * - PNFT
     - 核融合出力
     - MW

損失電力
--------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15

   * - 変数名
     - 説明
     - 単位
   * - PIET
     - 電離損失電力
     - MW
   * - PCXT
     - 電荷交換損失電力
     - MW
   * - PRADT
     - 放射損失電力
     - MW

電流関連
--------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15

   * - 変数名
     - 説明
     - 単位
   * - AJT
     - 全プラズマ電流
     - MA
   * - AJOHT
     - オーミック電流
     - MA
   * - AJNBT
     - NBI駆動電流
     - MA
   * - AJBST
     - ブートストラップ電流
     - MA

閉じ込め性能
------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 30

   * - 変数名
     - 説明
     - 単位
     - 定義
   * - TAUE1
     - エネルギー閉じ込め時間 (定義1)
     - s
     - :math:`\tau_E = W / P_{loss}`
   * - TAUE2
     - エネルギー閉じ込め時間 (定義2)
     - s
     - :math:`\tau_E = W / P_{in}`
   * - TAUEP
     - ポロイダル閉じ込め時間
     - s
     -
   * - TAUP
     - 粒子閉じ込め時間
     - s
     - :math:`\tau_p = N / \Gamma_{out}`

ベータ値
--------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 30

   * - 変数名
     - 説明
     - 単位
     - 定義
   * - BETA0
     - 軸上ベータ
     - %
     - :math:`\beta_0 = 2\mu_0 p_0 / B^2`
   * - BETAA
     - 体積平均ベータ
     - %
     - :math:`\langle \beta \rangle`
   * - BETAP0
     - 軸上ポロイダルベータ
     - \-
     - :math:`\beta_p = 2\mu_0 \langle p \rangle / B_p^2`
   * - BETAPA
     - 平均ポロイダルベータ
     - \-
     -
   * - BETAN
     - 規格化ベータ
     - \-
     - :math:`\beta_N = \beta_t a B / I_p`

その他グローバル量
------------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15

   * - 変数名
     - 説明
     - 単位
   * - VLOOP
     - ループ電圧
     - V
   * - ALI
     - 内部インダクタンス li(3)
     - \-
   * - ZEFF0
     - 有効電荷数（軸上）
     - \-
   * - Q(0)
     - 安全係数（軸上）
     - \-
   * - Q(NRMAX)
     - 安全係数（端）
     - \-

ラジアル分布
============

密度分布
--------

.. list-table::
   :header-rows: 1
   :widths: 20 50 15 15

   * - 変数名
     - 説明
     - 単位
     - 配列次元
   * - Var(NR,1)%n
     - 電子密度 :math:`n_e`
     - 10²⁰ m⁻³
     - [0:NRMAX]
   * - Var(NR,2)%n
     - イオン密度 :math:`n_i`
     - 10²⁰ m⁻³
     - [0:NRMAX]
   * - Var(NR,3)%n
     - 不純物密度 :math:`n_z`
     - 10²⁰ m⁻³
     - [0:NRMAX]

温度分布
--------

.. list-table::
   :header-rows: 1
   :widths: 20 50 15 15

   * - 変数名
     - 説明
     - 単位
     - 配列次元
   * - Var(NR,1)%T
     - 電子温度 :math:`T_e`
     - keV
     - [0:NRMAX]
   * - Var(NR,2)%T
     - イオン温度 :math:`T_i`
     - keV
     - [0:NRMAX]
   * - Var(NR,3)%T
     - 不純物温度 :math:`T_z`
     - keV
     - [0:NRMAX]

速度分布
--------

.. list-table::
   :header-rows: 1
   :widths: 20 50 15 15

   * - 変数名
     - 説明
     - 単位
     - 配列次元
   * - Var%Ur
     - 径方向速度
     - m/s
     - [0:NRMAX]
   * - Var%Uth
     - ポロイダル速度
     - m/s
     - [0:NRMAX]
   * - Var%Uph
     - トロイダル速度
     - m/s
     - [0:NRMAX]

電磁場分布
----------

.. list-table::
   :header-rows: 1
   :widths: 20 50 15 15

   * - 変数名
     - 説明
     - 単位
     - 配列次元
   * - ErV
     - 径電場 :math:`E_r`
     - V/m
     - [0:NRMAX]
   * - BthV
     - ポロイダル磁場 :math:`B_\theta`
     - T
     - [0:NRMAX]
   * - BphV
     - トロイダル磁場 :math:`B_\phi`
     - T
     - [0:NRMAX]

電流密度分布
------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 15

   * - 変数名
     - 説明
     - 単位
     - 配列次元
   * - AJ
     - 全電流密度
     - MA/m²
     - [0:NRMAX]
   * - AJOH
     - オーミック電流密度
     - MA/m²
     - [0:NRMAX]
   * - AJNB
     - NBI駆動電流密度
     - MA/m²
     - [0:NRMAX]
   * - AJBS
     - ブートストラップ電流密度
     - MA/m²
     - [0:NRMAX]

安全係数・磁気シア
------------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 15

   * - 変数名
     - 説明
     - 単位
     - 配列次元
   * - Q
     - 安全係数 :math:`q`
     - \-
     - [0:NRMAX]
   * - Shear
     - 磁気シア :math:`s = (r/q)(dq/dr)`
     - \-
     - [0:NRMAX]

輸送係数分布
------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 20

   * - 変数名
     - 説明
     - 単位
     - 配列次元
   * - Dfs
     - 粒子拡散係数 :math:`D`
     - m²/s
     - [0:NRMAX, 1:NSM]
   * - Chis
     - 熱拡散係数 :math:`\chi`
     - m²/s
     - [0:NRMAX, 1:NSM]
   * - rMus
     - 粘性係数 :math:`\mu`
     - m²/s
     - [0:NRMAX, 1:NSM]

出力ファイル
============

バイナリ保存ファイル
--------------------

TXSAVEサブルーチンで出力されるバイナリファイル：

* シミュレーション状態の完全保存
* 再スタートに使用可能
* 含まれるデータ：
   - 全入力パラメータ
   - 状態変数 X(0:NRMAX, 1:NQMAX)
   - グラフィックス履歴
   - グローバル量

テキスト出力
------------

標準出力に以下の情報が出力されます：

* 時間ステップごとの統計情報
* 体積平均量
* 閉じ込め時間
* ベータ値
* 収束状況

グラフィックス出力
------------------

GSAFライブラリを使用したグラフィックス出力：

* ラジアルプロファイル
* 時間発展
* 2D等高線図（オプション）
