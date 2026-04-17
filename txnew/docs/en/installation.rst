==========
Installation
==========

Requirements
============

* Fortran 95 or later compiler (gfortran, ifort, etc.)
* GSAF graphics library
* X11 library (for graphics display)
* Optional: LAPACK/BLAS (for high-performance matrix operations)

Build Procedure
===============

1. Build Dependencies
---------------------

.. code-block:: bash

   # GSAF library
   cd ~/program/gsaf/src
   make && make install

   # BPSD library
   cd ~/program/bpsd
   make

   # TASK library
   cd ~/program/task/lib
   make

   # Matrix solver
   cd ~/program/task/mtxp
   make

   # Plasma profiles (txnew dependency)
   cd ~/program/task/pl
   make

   # Equilibrium (txnew dependency)
   cd ~/program/task/eq
   make

2. Build TXnew
--------------

.. code-block:: bash

   cd ~/program/task/txnew
   make

3. Verify Installation
----------------------

.. code-block:: bash

   cd ~/program/task/txnew
   ./txnew

   # At prompt:
   # 0 (quiet mode)
   # c (continue)
   # r (run)
   # q (quit)

make.header Configuration
=========================

Configure compiler settings in ``~/program/task/make.header``:

.. code-block:: makefile

   # For gfortran (64bit)
   FCFIXED = gfortran -ffixed-form
   FCFREE = gfortran -ffree-form
   OFLAGS = -g -O3 -m64 -std=legacy

   # For ifort
   # FCFIXED = ifort -fixed
   # FCFREE = ifort -free
   # OFLAGS = -g -O3

Troubleshooting
===============

Link Errors
-----------

Verify GSAF library paths are correctly configured:

.. code-block:: bash

   ls ~/lib/libg*.a

X11 Errors
----------

Either run from an X11 environment or select quiet mode (0) at startup.
