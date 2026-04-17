==========
Overview
==========

What is TXnew?
==============

TXnew is a 1-dimensional radial transport code for tokamak plasmas included in the TASK code suite. It solves time-dependent transport equations for particle density, energy, and momentum for multiple plasma species (electrons, ions, impurities).

Features
========

Multi-species Transport
-----------------------

* Electrons (species 1)
* Main ions (species 2)
* Impurity ions (species 3)

Equations solved for each species:

* Particle continuity equation
* Energy transport equation
* Momentum transport equation

Heating Models
--------------

* **NBI heating**: Tangential and perpendicular injection with beam deposition calculation
* **RF heating**: Electron and ion heating with specified deposition profiles
* **Ohmic heating**: Self-consistent calculation based on plasma resistivity

Transport Models
----------------

* **Neoclassical transport**: Banana, plateau, and Pfirsch-Schluter regimes via NCLASS
* **Anomalous transport**: Bohm, gyro-Bohm, ITG models
* **Fixed transport coefficients**: User-specified D, chi, mu

Equilibrium
-----------

* Analytic equilibrium (circular, elliptic, D-shaped)
* External equilibrium file input (EQDSK format)

Code Structure
==============

Main Variables
--------------

TXnew manages transport variables through a systematic numbering scheme:

**MHD variables (LQm1-5)**:

* LQm1: Poloidal flux
* LQm2: Toroidal flux
* LQm3: Radial magnetic field
* LQm4: Poloidal current
* LQm5: Toroidal current

**Electron variables (LQe1-8)**:

* LQe1: Density
* LQe2: Parallel momentum
* LQe3: Energy
* LQe4-8: Higher moments

**Ion variables (LQi1-8)**: Same structure as electrons

**Impurity variables (LQz1-8)**: Same structure as electrons

Numerical Methods
-----------------

* **Spatial discretization**: Finite Element Method with linear elements
* **SUPG stabilization**: For advection-dominated problems
* **Time integration**: BDF (Backward Differentiation Formula) methods
* **Nonlinear solver**: Newton-Raphson iteration

Related Modules
===============

* **EQ**: MHD equilibrium calculation
* **TR**: 2D transport analysis
* **FP**: Fokker-Planck calculation
* **WR**: Wave propagation and absorption
