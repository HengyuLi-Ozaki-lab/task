! eqcom2_mod.f90
!
! F90 MODULE mirror of eqcom2.inc (mesh / coefficients / RHS state).
!
! Phase F-1 Task F-1-2 (eq F90 modernization plan).
!
! Sizing is driven by eqcom0_mod. The derived PARAMETERs (MLM, MWM,
! NSGMP, NTGMP, NSGPM, NTGPM, NXM, NT) are mirrored from eqcom2.inc
! and exposed PUBLIC so callers can drop INCLUDE 'eqcom2.inc' when
! they switch to USE eqcom2_mod.

MODULE eqcom2_mod
  USE eqcom0_mod, ONLY: NSGM, NTGM, NUGM
  IMPLICIT NONE
  PUBLIC
  SAVE

  ! --- derived PARAMETERs (mirror eqcom2.inc) ---
  INTEGER, PARAMETER :: MLM   = NSGM * NTGM
  INTEGER, PARAMETER :: MWM   = 4 * NTGM - 1
  INTEGER, PARAMETER :: NSGMP = NSGM + 1
  INTEGER, PARAMETER :: NTGMP = NTGM + 1
  INTEGER, PARAMETER :: NSGPM = NSGM + 2
  INTEGER, PARAMETER :: NTGPM = NTGM + 2
  INTEGER, PARAMETER :: NXM   = 2 * NSGM
  INTEGER, PARAMETER :: NT    = 5

  ! --- mesh ---
  REAL(8) :: DSG, DTG
  REAL(8) :: SIGM(NSGM), THGM(NTGM), RHOM(NTGM)
  REAL(8) :: RMG(NSGM, NTGMP), RGM(NSGMP, NTGM)
  REAL(8) :: SIGG(NSGMP), THGG(NTGMP), RHOG(NTGMP)
  REAL(8) :: RMM(NTGM, NSGM), ZMM(NTGM, NSGM)

  ! --- boundary matrix (banded) ---
  REAL(8) :: Q(MWM, MLM)

  ! --- coefficient arrays ---
  REAL(8) :: AA(NSGMP, NTGM), AB(NSGMP, NTGM)
  REAL(8) :: AC(NSGM, NTGMP), AD(NSGM, NTGMP)

  ! --- PSI state (current + history) and delta ---
  REAL(8) :: PSI(NTGM, NSGM), PSIO(NTGM, NSGM, NT)
  REAL(8) :: DELPSI(NTGM, NSGM)

  ! --- RHS: pressure / flux / current densities ---
  REAL(8) :: PP(NTGM, NSGM), TT(NTGM, NSGM)
  REAL(8) :: HJT(NTGM, NSGM), HJP(NTGM, NSGM)
  REAL(8) :: HJP1(NTGM, NSGM), HJP2(NTGM, NSGM)
  REAL(8) :: HJT1(NTGM, NSGM), HJT2(NTGM, NSGM)
  REAL(8) :: RHO(NTGM, NSGM)

  ! --- extended spline tables over NTGPM x NSGPM ---
  REAL(8) :: SIGMX(NSGPM), THGMX(NTGPM)
  REAL(8) :: PSIST(NTGPM, NSGPM)
  REAL(8) :: UPSIST(4, 4, NTGPM, NSGPM)
  REAL(8) :: HJTST(NTGPM, NSGPM)
  REAL(8) :: UHJTST(4, 4, NTGPM, NSGPM)

  ! --- misc scalar ---
  REAL(8) :: ZBRF

  ! --- 1D profile work arrays over NXM ---
  REAL(8) :: XAX(NXM), RPSI(NXM), RPP(NXM), RTT(NXM)
  REAL(8) :: RHJP(NXM), RHJT(NXM)
  REAL(8) :: RPSINT(NXM, NT)

  ! --- uniform-grid Q/J/B splines over NUGM ---
  REAL(8) :: RUGQ(NUGM), URGUQ(4, NUGM)
  REAL(8) :: RUGJ(NUGM), URGUJ(4, NUGM)
  REAL(8) :: RUG1(NUGM), URUG1(4, NUGM)
  REAL(8) :: RUG2(NUGM), URUG2(4, NUGM)
  REAL(8) :: RUG3(NUGM), URUG3(4, NUGM)
  REAL(8) :: RUGB(NUGM), URUGB(4, NUGM)

END MODULE eqcom2_mod
