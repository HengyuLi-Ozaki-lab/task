==========
Examples
==========

Basic Usage
===========

Input File Example
------------------

Standard tokamak simulation input:

.. code-block:: fortran

   &tx
     ! Plasma configuration
     RR = 3.2          ! Major radius [m]
     RA = 0.8          ! Minor radius [m]
     BB = 2.68         ! Toroidal field [T]
     rIPs = 1.0        ! Plasma current [MA]
     rIPe = 1.0

     ! Initial profiles
     PN0 = 0.3         ! Electron density (axis) [10^20 m^-3]
     PNa = 0.05        ! Electron density (edge)
     PTe0 = 3.0        ! Electron temperature (axis) [keV]
     PTea = 0.2        ! Electron temperature (edge)
     PTi0 = 3.0        ! Ion temperature (axis)
     PTia = 0.2        ! Ion temperature (edge)

     ! Transport coefficients
     Dfs0(1) = 0.1     ! Particle diffusion coefficient
     Chis0(1) = 1.0    ! Thermal diffusivity (electron)
     Chis0(2) = 1.0    ! Thermal diffusivity (ion)

     ! Heating
     PNBHT1 = 5.0      ! NBI power [MW]
     Ebmax = 80.0      ! Beam energy [keV]

     ! Numerical parameters
     NRMAX = 50        ! Number of grid points
     NTMAX = 1000      ! Number of time steps
     DT = 1.0D-3       ! Time step [s]
     NTSTEP = 100      ! Output interval
   &end

Execution
---------

.. code-block:: bash

   cd ~/program/task/txnew
   ./txnew < input.dat

Interactive mode execution:

.. code-block:: text

   $ ./txnew
   # INPUT DISPLAY TYPE: 0)quiet
   0
   # INPUT: (C)ONTINUE
   c
   # TX MENU: R/RUN
   r
   # (calculation runs)
   # TX MENU: Q/QUIT
   q

NBI Heating Simulation
======================

Input File
----------

.. code-block:: fortran

   &tx
     ! ITER-like configuration
     RR = 6.2
     RA = 2.0
     BB = 5.3
     rIPs = 15.0
     rIPe = 15.0

     ! Initial profiles
     PN0 = 1.0
     PNa = 0.1
     PTe0 = 10.0
     PTea = 0.5
     PTi0 = 10.0
     PTia = 0.5

     ! NBI heating
     PNBHT1 = 16.5     ! Tangential NBI
     PNBHT2 = 16.5     ! Tangential NBI
     Ebmax = 1000.0    ! 1 MeV beam

     ! Transport
     MDANOM = 1        ! Anomalous transport model
     FSANOM(1) = 1.0
     FSANOM(2) = 1.0

     NTMAX = 5000
     DT = 1.0D-3
   &end

Steady-State Calculation
========================

For finding steady-state solutions:

.. code-block:: fortran

   &tx
     ! Long-time calculation
     NTMAX = 10000
     DT = 1.0D-2       ! Larger time step

     ! Strict convergence criteria
     EPS = 1.0D-5
     ICMAX = 200
   &end

Parameter Scan
==============

Density Scan Example
--------------------

Prepare multiple input files:

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

Batch execution:

.. code-block:: bash

   for f in scan_n*.dat; do
     ./txnew < $f > ${f%.dat}.log
   done

Save and Restart
================

Saving Simulation State
-----------------------

In interactive mode:

.. code-block:: text

   # TX MENU: S/SAVE
   s
   # Enter filename
   save001.dat

Restart
-------

.. code-block:: text

   # TX MENU: L/LOAD
   l
   # Enter filename
   save001.dat
   # TX MENU: R/RUN
   r

Graphics Output
===============

Profile Plots
-------------

.. code-block:: text

   # TX MENU: G/GRAPH
   g
   # Graph menu
   # t1: Electron temperature profile
   # t2: Ion temperature profile
   # n1: Electron density profile
   # q: Safety factor profile

Time Evolution Plots
--------------------

.. code-block:: text

   # Graph menu
   # gt: Temperature time evolution
   # gn: Density time evolution
   # gw: Energy time evolution

Troubleshooting
===============

Convergence Issues
------------------

1. Reduce time step size

   .. code-block:: fortran

      DT = 1.0D-4  ! Smaller

2. Relax convergence criteria

   .. code-block:: fortran

      EPS = 1.0D-2  ! Larger

3. Increase iteration count

   .. code-block:: fortran

      ICMAX = 500

Instability Issues
------------------

1. Enable SUPG stabilization

   .. code-block:: fortran

      iSUPG3 = 1
      iSUPG6 = 1
      iSUPG8 = 1

2. Use implicit scheme

   .. code-block:: fortran

      ADV = 1.0
