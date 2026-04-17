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

**Batch mode execution:**

.. code-block:: bash

   cd ~/program/task/txnew
   ./txnew < input.dat

**Interactive mode execution:**

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

Understanding Output
--------------------

Each time step outputs the following information:

.. code-block:: text

   NT =  50   T = 5.00E-02   IC =  3
   CPU = 0.52 (sec)   sim time = 5.0E-02 (sec)  (50.0%)  ICave = 2.50
   Ne(0) = 2.95E-01  UePhi(0)=-1.23E+03  UiPhi(0)= 5.67E+02  N0(RB)= 1.00E+12
   NB(0) = 1.50E-01  NB(0.24)= 1.20E-01  NB(0.60)= 6.00E-02  PF    = 2.50E+00
   Te(0) = 3.20E+00  Ti(0)   = 2.80E+00  Wst     = 4.80E-01

Meaning of each item:

* ``NT`` : Time step number
* ``T`` : Simulation time [s]
* ``IC`` : Number of Newton iterations
* ``Ne(0)`` : On-axis electron density [10^20 m^-3]
* ``Te(0)``, ``Ti(0)`` : On-axis temperatures [keV]
* ``Wst`` : Stored energy [MJ]
* ``NB`` : Fast particle density
* ``PF`` : Fusion power indicator

Output Graphs
=============

Temperature Profile
-------------------

Enter graph menu with ``G`` command, then ``t1`` for electron temperature profile:

.. figure:: _static/te_profile_example.png
   :width: 80%
   :align: center
   :alt: Electron temperature profile example

   Radial distribution of electron temperature. Horizontal axis is normalized
   minor radius rho (0=axis, 1=edge), vertical axis is electron temperature Te [keV].
   Peaks at center and decreases toward the edge.

Density Profile
---------------

``n1`` displays electron density profile:

.. figure:: _static/ne_profile_example.png
   :width: 80%
   :align: center
   :alt: Electron density profile example

   Radial distribution of electron density. Profile shape (1-rho^2)^p
   as set in initial conditions.

Time Evolution
--------------

``gt`` displays temperature time evolution:

.. figure:: _static/time_evolution_example.png
   :width: 80%
   :align: center
   :alt: Time evolution example

   Time evolution of various quantities. After NBI heating starts,
   temperature rises and reaches steady state when balanced with transport losses.

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

Expected Results
----------------

* Central electron temperature: ~15-20 keV
* Central ion temperature: ~12-15 keV
* Stored energy: ~300-400 MJ
* Energy confinement time: ~3-5 s

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

Steady-State Criteria
---------------------

Steady state can be determined when:

1. Change in stored energy Wst is less than 0.1%
2. Change in central temperature is less than 1%
3. Input power and loss power are balanced

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

Result aggregation script example:

.. code-block:: bash

   # Extract final values from each log file
   for f in scan_n*.log; do
     echo -n "$f: "
     grep "Te(0)" $f | tail -1
   done

Save and Restart
================

Saving Simulation State
-----------------------

Use ``S`` command in interactive mode:

.. code-block:: text

   ## INPUT: R:RUN  C:CONT  P,V:PARM  G:GRAPH  W:STAT  S:SAVE  L:LOAD ...
   s
   # INPUT FILE NAME FOR SAVE
   checkpoint_t100.dat
   # SAVE COMPLETED

Saved data includes:

* All input parameters
* State variables (density, temperature, velocity, etc.)
* Time information
* Graphics history

Restart
-------

.. code-block:: text

   ## INPUT: R:RUN  C:CONT  P,V:PARM  G:GRAPH  W:STAT  S:SAVE  L:LOAD ...
   l
   # INPUT FILE NAME FOR LOAD
   checkpoint_t100.dat
   # LOAD COMPLETED
   r
   # Calculating from T = 1.00E-01 ...

Graphics Output
===============

Graph Menu
----------

Enter graph menu with ``G`` command:

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

Profile Plots
-------------

* ``t1``: Electron temperature profile Te(rho)
* ``t2``: Ion temperature profile Ti(rho)
* ``n1``: Electron density profile ne(rho)
* ``q``: Safety factor profile q(rho)
* ``j``: Current density profile j(rho)

Time Evolution Plots
--------------------

* ``gt``: Temperature time evolution T(t)
* ``gn``: Density time evolution n(t)
* ``gw``: Energy time evolution W(t)

Troubleshooting
===============

Convergence Issues
------------------

**Symptom:** ``IC`` reaches ``ICMAX`` and calculation does not progress

**Solutions:**

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

**Symptom:** Values diverge, NaN occurs

**Solutions:**

1. Enable SUPG stabilization

   .. code-block:: fortran

      iSUPG3 = 1
      iSUPG6 = 1
      iSUPG8 = 1

2. Use implicit scheme

   .. code-block:: fortran

      ADV = 1.0

3. Increase number of grid points

   .. code-block:: fortran

      NRMAX = 100

LAPACK Error
------------

**Symptom:** ``ERROR(TXLOOP) : GBSV, IERR = -1``

**Cause:** LAPACK library is not properly linked

**Solutions:**

1. Install LAPACK

   .. code-block:: bash

      # Ubuntu/Debian
      sudo apt-get install liblapack-dev libblas-dev

2. Enable LAPACK in make.header

   .. code-block:: makefile

      LAPACK = lapack.f
      LIBLA = -llapack -lblas

3. Rebuild txnew

   .. code-block:: bash

      cd ~/program/task/txnew
      make clean
      make

Memory Issues
-------------

**Symptom:** Segmentation fault, memory error

**Solutions:**

1. Reduce number of grid points

   .. code-block:: fortran

      NRMAX = 30  ! Reduced from default 50

2. Increase output interval

   .. code-block:: fortran

      NTSTEP = 100  ! Reduces memory usage
