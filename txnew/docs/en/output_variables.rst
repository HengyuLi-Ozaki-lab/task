==================
Output Variables
==================

This section describes the physical quantities computed and output by TXnew.

Global Quantities
=================

Energy-Related
--------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 20

   * - Variable
     - Description
     - Unit
     - Definition
   * - WST(1)
     - Electron stored energy
     - MJ
     - :math:`\int \frac{3}{2} n_e T_e dV`
   * - WST(2)
     - Ion stored energy
     - MJ
     - :math:`\int \frac{3}{2} n_i T_i dV`
   * - WST(3)
     - Impurity stored energy
     - MJ
     - :math:`\int \frac{3}{2} n_z T_z dV`
   * - WFT
     - Fast ion energy
     - MJ
     - Beam particle energy
   * - WPT
     - Total stored energy
     - MJ
     - :math:`W_{tot} = \sum W_s`

Input Power
-----------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15

   * - Variable
     - Description
     - Unit
   * - POHT
     - Ohmic heating power
     - MW
   * - PNBT
     - NBI heating power
     - MW
   * - PRFT
     - RF heating power
     - MW
   * - PNFT
     - Fusion power
     - MW

Loss Power
----------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15

   * - Variable
     - Description
     - Unit
   * - PIET
     - Ionization loss power
     - MW
   * - PCXT
     - Charge exchange loss power
     - MW
   * - PRADT
     - Radiation loss power
     - MW

Current-Related
---------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15

   * - Variable
     - Description
     - Unit
   * - AJT
     - Total plasma current
     - MA
   * - AJOHT
     - Ohmic current
     - MA
   * - AJNBT
     - NBI-driven current
     - MA
   * - AJBST
     - Bootstrap current
     - MA

Confinement Performance
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 30

   * - Variable
     - Description
     - Unit
     - Definition
   * - TAUE1
     - Energy confinement time (definition 1)
     - s
     - :math:`\tau_E = W / P_{loss}`
   * - TAUE2
     - Energy confinement time (definition 2)
     - s
     - :math:`\tau_E = W / P_{in}`
   * - TAUEP
     - Poloidal confinement time
     - s
     -
   * - TAUP
     - Particle confinement time
     - s
     - :math:`\tau_p = N / \Gamma_{out}`

Beta Values
-----------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 30

   * - Variable
     - Description
     - Unit
     - Definition
   * - BETA0
     - On-axis beta
     - %
     - :math:`\beta_0 = 2\mu_0 p_0 / B^2`
   * - BETAA
     - Volume-averaged beta
     - %
     - :math:`\langle \beta \rangle`
   * - BETAP0
     - On-axis poloidal beta
     - \-
     - :math:`\beta_p = 2\mu_0 \langle p \rangle / B_p^2`
   * - BETAPA
     - Average poloidal beta
     - \-
     -
   * - BETAN
     - Normalized beta
     - \-
     - :math:`\beta_N = \beta_t a B / I_p`

Other Global Quantities
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15

   * - Variable
     - Description
     - Unit
   * - VLOOP
     - Loop voltage
     - V
   * - ALI
     - Internal inductance li(3)
     - \-
   * - ZEFF0
     - Effective charge (on-axis)
     - \-
   * - Q(0)
     - Safety factor (on-axis)
     - \-
   * - Q(NRMAX)
     - Safety factor (edge)
     - \-

Radial Distributions
====================

Density Profiles
----------------

.. list-table::
   :header-rows: 1
   :widths: 20 50 15 15

   * - Variable
     - Description
     - Unit
     - Array Dimension
   * - Var(NR,1)%n
     - Electron density :math:`n_e`
     - 10^20 m^-3
     - [0:NRMAX]
   * - Var(NR,2)%n
     - Ion density :math:`n_i`
     - 10^20 m^-3
     - [0:NRMAX]
   * - Var(NR,3)%n
     - Impurity density :math:`n_z`
     - 10^20 m^-3
     - [0:NRMAX]

Temperature Profiles
--------------------

.. list-table::
   :header-rows: 1
   :widths: 20 50 15 15

   * - Variable
     - Description
     - Unit
     - Array Dimension
   * - Var(NR,1)%T
     - Electron temperature :math:`T_e`
     - keV
     - [0:NRMAX]
   * - Var(NR,2)%T
     - Ion temperature :math:`T_i`
     - keV
     - [0:NRMAX]
   * - Var(NR,3)%T
     - Impurity temperature :math:`T_z`
     - keV
     - [0:NRMAX]

Velocity Profiles
-----------------

.. list-table::
   :header-rows: 1
   :widths: 20 50 15 15

   * - Variable
     - Description
     - Unit
     - Array Dimension
   * - Var%Ur
     - Radial velocity
     - m/s
     - [0:NRMAX]
   * - Var%Uth
     - Poloidal velocity
     - m/s
     - [0:NRMAX]
   * - Var%Uph
     - Toroidal velocity
     - m/s
     - [0:NRMAX]

Electromagnetic Field Profiles
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 50 15 15

   * - Variable
     - Description
     - Unit
     - Array Dimension
   * - ErV
     - Radial electric field :math:`E_r`
     - V/m
     - [0:NRMAX]
   * - BthV
     - Poloidal magnetic field :math:`B_\theta`
     - T
     - [0:NRMAX]
   * - BphV
     - Toroidal magnetic field :math:`B_\phi`
     - T
     - [0:NRMAX]

Current Density Profiles
------------------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 15

   * - Variable
     - Description
     - Unit
     - Array Dimension
   * - AJ
     - Total current density
     - MA/m^2
     - [0:NRMAX]
   * - AJOH
     - Ohmic current density
     - MA/m^2
     - [0:NRMAX]
   * - AJNB
     - NBI-driven current density
     - MA/m^2
     - [0:NRMAX]
   * - AJBS
     - Bootstrap current density
     - MA/m^2
     - [0:NRMAX]

Safety Factor and Magnetic Shear
--------------------------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 15

   * - Variable
     - Description
     - Unit
     - Array Dimension
   * - Q
     - Safety factor :math:`q`
     - \-
     - [0:NRMAX]
   * - Shear
     - Magnetic shear :math:`s = (r/q)(dq/dr)`
     - \-
     - [0:NRMAX]

Transport Coefficient Profiles
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 20

   * - Variable
     - Description
     - Unit
     - Array Dimension
   * - Dfs
     - Particle diffusion coefficient :math:`D`
     - m^2/s
     - [0:NRMAX, 1:NSM]
   * - Chis
     - Thermal diffusivity :math:`\chi`
     - m^2/s
     - [0:NRMAX, 1:NSM]
   * - rMus
     - Viscosity coefficient :math:`\mu`
     - m^2/s
     - [0:NRMAX, 1:NSM]

Output Files
============

Binary Save Files
-----------------

Binary files output by the TXSAVE subroutine:

* Complete simulation state preservation
* Can be used for restart
* Included data:
   - All input parameters
   - State variables X(0:NRMAX, 1:NQMAX)
   - Graphics history
   - Global quantities

Text Output
-----------

The following information is output to standard output:

* Statistics for each time step
* Volume-averaged quantities
* Confinement times
* Beta values
* Convergence status

Graphics Output
---------------

Graphics output using the GSAF library:

* Radial profiles
* Time evolution
* 2D contour plots (optional)
