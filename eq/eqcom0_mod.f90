! eqcom0_mod.f90
!
! F90 MODULE mirror of eqcom0.inc grid-size PARAMETERs.
!
! Phase F-1 Task F-1-1 (eq F90 modernization plan,
! docs/superpowers/plans/2026-04-18-eq-f90-modernization.md).
!
! Per the Phase F-5 shim policy, eqcom0.inc is kept in place so that
! .f files still using INCLUDE continue to compile. New .f90 code
! should USE this MODULE instead.
!
! All values must remain in lock-step with eqcom0.inc until the
! shim is retired in Phase F-5.

MODULE eqcom0_mod
  IMPLICIT NONE
  PUBLIC

  ! Grid-scale PARAMETERs (mirror of eqcom0.inc)
  INTEGER, PARAMETER :: NRGM  = 513
  INTEGER, PARAMETER :: NZGM  = 513
  INTEGER, PARAMETER :: NPSM  = 513
  INTEGER, PARAMETER :: NRVM  = 1001
  INTEGER, PARAMETER :: NTVM  = 1025
  INTEGER, PARAMETER :: NSUM  = 1343
  INTEGER, PARAMETER :: NSGM  = 128
  INTEGER, PARAMETER :: NTGM  = 128
  INTEGER, PARAMETER :: NUGM  = 128
  INTEGER, PARAMETER :: NRM   = 1001
  INTEGER, PARAMETER :: NTHM  = 2049
  INTEGER, PARAMETER :: NPFCM = 10

  ! Note: NRMP=NRM+1 and NTHMP=NTHM+1 are NOT declared here even though
  ! they are derived from eqcom0 PARAMETERs. They already exist as local
  ! PARAMETERs inside eqcom3.inc (INCLUDEd directly by eqinit.f:EQCHEK);
  ! declaring them here would collide with that local PARAMETER when the
  ! eqcomm.inc shim (which USEs this module) is combined with a direct
  ! INCLUDE of eqcom3.inc in the same scope. Instead, NRMP/NTHMP are
  ! re-exported from eqcom3_mod for consumers who USE that module.

END MODULE eqcom0_mod
