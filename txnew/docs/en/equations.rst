===============
Basic Equations
===============

This section describes the basic equations solved in TXnew.

Transport Equations
===================

Particle Continuity Equation
----------------------------

For each plasma species :math:`s`:

.. math::

   \frac{\partial n_s}{\partial t} + \nabla \cdot \Gamma_s = S_s

where:

* :math:`n_s` : Density
* :math:`\Gamma_s` : Particle flux
* :math:`S_s` : Particle source term

The particle flux is:

.. math::

   \Gamma_s = -D_s \nabla n_s + n_s V_s

* :math:`D_s` : Diffusion coefficient
* :math:`V_s` : Convective velocity (pinch)

Energy Equation
---------------

.. math::

   \frac{3}{2}\frac{\partial (n_s T_s)}{\partial t} + \nabla \cdot q_s + p_s \nabla \cdot \mathbf{u}_s = Q_s

where:

* :math:`T_s` : Temperature
* :math:`q_s` : Heat flux
* :math:`p_s = n_s T_s` : Pressure
* :math:`Q_s` : Heating/cooling term

The heat flux is:

.. math::

   q_s = -n_s \chi_s \nabla T_s + \frac{5}{2} T_s \Gamma_s

* :math:`\chi_s` : Thermal diffusivity

Momentum Equation
-----------------

.. math::

   m_s n_s \frac{\partial \mathbf{u}_s}{\partial t} = -\nabla p_s + \mathbf{F}_s - \nabla \cdot \boldsymbol{\pi}_s

* :math:`\mathbf{u}_s` : Fluid velocity
* :math:`\mathbf{F}_s` : External forces (electromagnetic, etc.)
* :math:`\boldsymbol{\pi}_s` : Viscosity tensor

Transport Coefficients
======================

Neoclassical Transport
----------------------

Neoclassical transport coefficients are calculated using the NCLASS code:

.. math::

   D^{NC} = D^{NC}(n, T, q, \epsilon, \nu_*)

* :math:`\epsilon = r/R` : Inverse aspect ratio
* :math:`\nu_* = \nu_{ei} q R / (\epsilon^{3/2} v_{th})` : Collisionality

Three collisionality regimes:

* **Banana regime** (:math:`\nu_* \ll 1`)
* **Plateau regime** (:math:`\nu_* \sim 1`)
* **Pfirsch-Schluter regime** (:math:`\nu_* \gg 1`)

Anomalous Transport
-------------------

Anomalous (turbulent) transport coefficients:

**Bohm diffusion**

.. math::

   D_B = \frac{1}{16} \frac{T_e}{eB}

**gyro-Bohm diffusion**

.. math::

   D_{gB} = \frac{\rho_s^2}{a} \frac{c_s}{a}

* :math:`\rho_s = c_s / \Omega_i` : Ion Larmor radius
* :math:`c_s = \sqrt{T_e/m_i}` : Ion sound speed

Heating Models
==============

NBI Heating
-----------

Beam particle slowing-down process:

.. math::

   \frac{dE_b}{dt} = -\frac{E_b}{\tau_s}

* :math:`\tau_s` : Slowing-down time

Energy partition to electrons and ions:

.. math::

   P_e = P_{NBI} \frac{E_c^{3/2}}{E_c^{3/2} + E_b^{3/2}}

.. math::

   P_i = P_{NBI} - P_e

* :math:`E_c` : Critical energy

Ohmic Heating
-------------

.. math::

   P_{OH} = \eta j^2

* :math:`\eta` : Resistivity (Spitzer resistivity)
* :math:`j` : Current density

Radiation Losses
================

Bremsstrahlung
--------------

.. math::

   P_{brem} = C_B n_e^2 \sqrt{T_e} Z_{eff}

Line Radiation
--------------

.. math::

   P_{line} = n_e n_z L_z(T_e)

* :math:`L_z(T_e)` : Radiative cooling function

Collision Processes
===================

Electron-Ion Collisions
-----------------------

Energy exchange:

.. math::

   Q_{ei} = \frac{3 m_e}{m_i} \nu_{ei} n_e (T_e - T_i)

Collision frequency:

.. math::

   \nu_{ei} = \frac{4\sqrt{2\pi}}{3} \frac{n_i Z^2 e^4 \ln\Lambda}{m_e^{1/2} T_e^{3/2}}

Charge Exchange
---------------

.. math::

   Q_{CX} = n_i n_0 \langle \sigma v \rangle_{CX} T_i

* :math:`n_0` : Neutral particle density
* :math:`\langle \sigma v \rangle_{CX}` : Charge exchange reaction rate

Numerical Methods
=================

Spatial Discretization
----------------------

Finite Element Method (FEM) is used:

* Linear elements
* SUPG stabilization (for advection terms)

Time Integration
----------------

BDF (Backward Differentiation Formula) methods:

* 1st order BDF (backward Euler)
* 2nd order BDF

Nonlinear equations are solved using Newton-Raphson iteration:

.. math::

   \mathbf{J} \delta \mathbf{x} = -\mathbf{F}(\mathbf{x})

* :math:`\mathbf{J}` : Jacobian matrix
* :math:`\mathbf{F}` : Residual vector
