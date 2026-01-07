==========
基礎方程式
==========

TXnewで解く基礎方程式について説明します。

輸送方程式
==========

粒子連続方程式
--------------

各プラズマ種 :math:`s` について：

.. math::

   \frac{\partial n_s}{\partial t} + \nabla \cdot \Gamma_s = S_s

ここで：

* :math:`n_s` : 密度
* :math:`\Gamma_s` : 粒子フラックス
* :math:`S_s` : 粒子ソース項

粒子フラックスは：

.. math::

   \Gamma_s = -D_s \nabla n_s + n_s V_s

* :math:`D_s` : 拡散係数
* :math:`V_s` : 対流速度（ピンチ）

エネルギー方程式
----------------

.. math::

   \frac{3}{2}\frac{\partial (n_s T_s)}{\partial t} + \nabla \cdot q_s + p_s \nabla \cdot \mathbf{u}_s = Q_s

ここで：

* :math:`T_s` : 温度
* :math:`q_s` : 熱フラックス
* :math:`p_s = n_s T_s` : 圧力
* :math:`Q_s` : 加熱・冷却項

熱フラックスは：

.. math::

   q_s = -n_s \chi_s \nabla T_s + \frac{5}{2} T_s \Gamma_s

* :math:`\chi_s` : 熱拡散係数

運動量方程式
------------

.. math::

   m_s n_s \frac{\partial \mathbf{u}_s}{\partial t} = -\nabla p_s + \mathbf{F}_s - \nabla \cdot \boldsymbol{\pi}_s

* :math:`\mathbf{u}_s` : 流体速度
* :math:`\mathbf{F}_s` : 外力（電磁力など）
* :math:`\boldsymbol{\pi}_s` : 粘性テンソル

輸送係数
========

ネオクラシカル輸送
------------------

ネオクラシカル輸送係数はNCLASSコードで計算されます：

.. math::

   D^{NC} = D^{NC}(n, T, q, \epsilon, \nu_*)

* :math:`\epsilon = r/R` : 逆アスペクト比
* :math:`\nu_* = \nu_{ei} q R / (\epsilon^{3/2} v_{th})` : 衝突度

3つのレジーム：

* **バナナレジーム** (:math:`\nu_* \ll 1`)
* **プラトーレジーム** (:math:`\nu_* \sim 1`)
* **Pfirsch-Schlüterレジーム** (:math:`\nu_* \gg 1`)

異常輸送
--------

異常（乱流）輸送係数：

**Bohm拡散**

.. math::

   D_B = \frac{1}{16} \frac{T_e}{eB}

**gyro-Bohm拡散**

.. math::

   D_{gB} = \frac{\rho_s^2}{a} \frac{c_s}{a}

* :math:`\rho_s = c_s / \Omega_i` : イオンラーマー半径
* :math:`c_s = \sqrt{T_e/m_i}` : イオン音速

加熱モデル
==========

NBI加熱
-------

ビーム粒子の減速過程：

.. math::

   \frac{dE_b}{dt} = -\frac{E_b}{\tau_s}

* :math:`\tau_s` : 減速時間

電子・イオンへのエネルギー分配：

.. math::

   P_e = P_{NBI} \frac{E_c^{3/2}}{E_c^{3/2} + E_b^{3/2}}

.. math::

   P_i = P_{NBI} - P_e

* :math:`E_c` : 臨界エネルギー

オーミック加熱
--------------

.. math::

   P_{OH} = \eta j^2

* :math:`\eta` : 抵抗率（スピッツァー抵抗）
* :math:`j` : 電流密度

放射損失
========

制動放射
--------

.. math::

   P_{brem} = C_B n_e^2 \sqrt{T_e} Z_{eff}

線放射
------

.. math::

   P_{line} = n_e n_z L_z(T_e)

* :math:`L_z(T_e)` : 放射冷却関数

衝突過程
========

電子-イオン衝突
---------------

エネルギー交換：

.. math::

   Q_{ei} = \frac{3 m_e}{m_i} \nu_{ei} n_e (T_e - T_i)

衝突周波数：

.. math::

   \nu_{ei} = \frac{4\sqrt{2\pi}}{3} \frac{n_i Z^2 e^4 \ln\Lambda}{m_e^{1/2} T_e^{3/2}}

電荷交換
--------

.. math::

   Q_{CX} = n_i n_0 \langle \sigma v \rangle_{CX} T_i

* :math:`n_0` : 中性粒子密度
* :math:`\langle \sigma v \rangle_{CX}` : 電荷交換反応率

数値解法
========

空間離散化
----------

有限要素法（FEM）を使用：

* 線形要素
* SUPG安定化（移流項）

時間積分
--------

BDF (Backward Differentiation Formula) 法：

* 1次BDF（後退Euler法）
* 2次BDF

非線形方程式はNewton-Raphson法で解く：

.. math::

   \mathbf{J} \delta \mathbf{x} = -\mathbf{F}(\mathbf{x})

* :math:`\mathbf{J}` : ヤコビアン行列
* :math:`\mathbf{F}` : 残差ベクトル
