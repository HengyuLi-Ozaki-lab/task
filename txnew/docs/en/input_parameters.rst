=================
Input Parameters
=================

TXnew input parameters are specified in Namelist format (&tx ... &end).

Input File Format
=================

.. code-block:: fortran

   &tx
     RR = 3.2
     RA = 0.8
     BB = 2.68
     PTe0 = 2.0
     PTi0 = 2.0
     NTMAX = 1000
     DT = 1.0D-3
   &end

Plasma Configuration Parameters
===============================

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 10 10

   * - Parameter
     - Description
     - Default
     - Unit
     - Range
   * - RR
     - Plasma major radius
     - 3.2
     - m
     - > 0
   * - RA
     - Plasma minor radius (geometric)
     - 0.8
     - m
     - > 0
   * - RB
     - Plasma minor radius (volume-based)
     - 0.8
     - m
     - > 0
   * - BB
     - Toroidal magnetic field (at R=RR)
     - 2.68
     - T
     - > 0
   * - rIPs
     - Plasma current (start)
     - 1.0
     - MA
     -
   * - rIPe
     - Plasma current (end)
     - 1.0
     - MA
     -
   * - rhob
     - Virtual wall position (rho coordinate)
     - 1.1
     - \-
     - > 1
   * - kappa
     - Elongation
     - 1.2
     - \-
     - >= 1
   * - delta
     - Triangularity
     - 0.0
     - \-
     -

Plasma Species Parameters
=========================

.. list-table::
   :header-rows: 1
   :widths: 15 50 20 10

   * - Parameter
     - Description
     - Default
     - Unit
   * - amas(1:3)
     - Atomic mass number [electron, ion, impurity]
     - [m_e/m_p, 2, 12]
     - \-
   * - achg(1:3)
     - Charge number [electron, ion, impurity]
     - [-1, 1, 6]
     - \-
   * - Zeffin
     - Effective charge number (initial)
     - 1.5
     - \-

Initial Profile Parameters
==========================

Density Profile
---------------

Initial density distribution is given by:

.. math::

   n(\rho) = (n_0 - n_a)(1 - \rho^{p_1})^{p_2} + n_a

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 10

   * - Parameter
     - Description
     - Default
     - Unit
   * - PN0
     - Electron density (on-axis)
     - 0.2
     - 10^20 m^-3
   * - PNa
     - Electron density (edge)
     - 0.05
     - 10^20 m^-3
   * - PROFN1
     - Density profile exponent p1
     - 2.0
     - \-
   * - PROFN2
     - Density profile exponent p2
     - 1.0
     - \-

Temperature Profile
-------------------

Initial temperature distribution is given by:

.. math::

   T(\rho) = (T_0 - T_a)(1 - \rho^{p_1})^{p_2} + T_a

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 10

   * - Parameter
     - Description
     - Default
     - Unit
   * - PTe0
     - Electron temperature (on-axis)
     - 2.0
     - keV
   * - PTea
     - Electron temperature (edge)
     - 0.2
     - keV
   * - PTi0
     - Ion temperature (on-axis)
     - 2.0
     - keV
   * - PTia
     - Ion temperature (edge)
     - 0.2
     - keV
   * - PROFT1
     - Temperature profile exponent p1
     - 2.0
     - \-
   * - PROFT2
     - Temperature profile exponent p2
     - 2.0
     - \-

Current Profile
---------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 10

   * - Parameter
     - Description
     - Default
     - Unit
   * - PROFJ
     - Current profile exponent
     - 2.0
     - \-

Transport Coefficient Parameters
================================

Fixed Transport Coefficients
----------------------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 20 10

   * - Parameter
     - Description
     - Default
     - Unit
   * - Dfs0(1:3)
     - Particle diffusion coefficient [e, i, z]
     - [0.1, 0, 0]
     - m^2/s
   * - Chis0(1:3)
     - Thermal diffusivity chi/D [e, i, z]
     - [0.5, 0.5, 0.5]
     - \-
   * - rMus0(1:3)
     - Viscosity coefficient [e, i, z]
     - [0.5, 0.5, 0.5]
     - m^2/s
   * - ChiNC
     - Neoclassical thermal diffusivity
     - 1.0
     - \-

Anomalous Transport Model
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15

   * - Parameter
     - Description
     - Default
   * - MDANOM
     - Anomalous transport model selection
     - 1
   * - FSDFIX(1:3)
     - Fixed transport coefficient flag
     - [1, 1, 1]
   * - FSANOM(1:3)
     - Anomalous transport multiplier
     - [0, 0, 0]
   * - rG1
     - ExB shear factor
     - 10.0

MDANOM options:

* 0: Fixed transport coefficients only
* 1: Simple model
* 2: Bohm/gyro-Bohm mixed model
* 3: ITG model

Heating Parameters
==================

NBI Heating
-----------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 10

   * - Parameter
     - Description
     - Default
     - Unit
   * - PNBHP
     - NBI power (perpendicular injection)
     - 0.0
     - MW
   * - PNBHT1
     - NBI power (tangential injection 1)
     - 0.0
     - MW
   * - PNBHT2
     - NBI power (tangential injection 2)
     - 0.0
     - MW
   * - Ebmax
     - Beam energy
     - 80.0
     - keV
   * - esps(1:3)
     - Energy fractions [E, E/2, E/3]
     - [0.75, 0.15, 0.10]
     - \-
   * - RNBP
     - NBI deposition position (rho coordinate)
     - 0.6
     - \-

RF Heating
----------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 10

   * - Parameter
     - Description
     - Default
     - Unit
   * - PRFHe
     - RF power (electron heating)
     - 0.0
     - MW
   * - PRFHi
     - RF power (ion heating)
     - 0.0
     - MW
   * - RRF
     - RF deposition position (rho coordinate)
     - 0.6
     - \-

Neutral Particle Parameters
===========================

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 10

   * - Parameter
     - Description
     - Default
     - Unit
   * - PN0s
     - Initial neutral density (hydrogen)
     - 1e-8
     - 10^20 m^-3
   * - V0
     - Neutral particle thermal velocity
     - 1.7e4
     - m/s
   * - rGASPF
     - Gas puff particle flux
     - 0.2
     - 10^20 m^-2 s^-1
   * - rGamm0
     - Recycling coefficient
     - 0.98
     - \-

Numerical Parameters
====================

Time Integration
----------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 10

   * - Parameter
     - Description
     - Default
     - Unit
   * - NTMAX
     - Maximum number of time steps
     - 10
     - \-
   * - DT
     - Time step size
     - 1e-3
     - s
   * - ADV
     - Time differencing scheme (0: explicit, 1: implicit)
     - 1.0
     - \-
   * - IGBDF
     - BDF method mode
     - 1
     - \-

Spatial Discretization
----------------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15 10

   * - Parameter
     - Description
     - Default
     - Unit
   * - NRMAX
     - Number of radial grid points
     - 50
     - \-
   * - iSUPG3
     - SUPG stabilization (density)
     - 0
     - \-
   * - iSUPG6
     - SUPG stabilization (momentum)
     - 0
     - \-
   * - iSUPG8
     - SUPG stabilization (energy)
     - 1
     - \-

Convergence Criteria
--------------------

.. list-table::
   :header-rows: 1
   :widths: 15 50 15

   * - Parameter
     - Description
     - Default
   * - EPS
     - Convergence tolerance
     - 1e-3
   * - ICMAX
     - Maximum iteration count
     - 100

Output Control Parameters
=========================

.. list-table::
   :header-rows: 1
   :widths: 15 50 15

   * - Parameter
     - Description
     - Default
   * - NTSTEP
     - Statistics output interval (time steps)
     - 10
   * - NGRSTP
     - Graph save interval (spatial)
     - 1
   * - NGTSTP
     - Graph save interval (temporal)
     - 1
   * - NGVSTP
     - Graph save interval (velocity)
     - 1

Model Selection Parameters
==========================

.. list-table::
   :header-rows: 1
   :widths: 15 50 15

   * - Parameter
     - Description
     - Default
   * - ieqread
     - Equilibrium read mode (0: analytic, 1: approximate, 2: file)
     - 0
   * - MDLPCK
     - LAPACK usage (0: built-in, 1: MKL, 2: F77)
     - 0
   * - MDOSQZ
     - Compression mode
     - 11
