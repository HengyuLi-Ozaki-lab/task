! eqcom3_mod.f90
!
! F90 MODULE mirror of eqcom3.inc (1D spline state, Boozer, ripple).
!
! Phase F-1 Task F-1-2 (eq F90 modernization plan).

MODULE eqcom3_mod
  USE eqcom0_mod, ONLY: NRM, NTHM, NPSM, NTVM
  IMPLICIT NONE
  PUBLIC
  SAVE

  ! --- derived PARAMETERs (mirror eqcom3.inc) ---
  INTEGER, PARAMETER :: NTHMP = NTHM + 1
  INTEGER, PARAMETER :: NRMP  = NRM  + 1
  INTEGER, PARAMETER :: NRrpM = 129
  INTEGER, PARAMETER :: NZrpM = 129

  ! --- scalar global flux-surface parameters ---
  REAL(8) :: PSITB, QPSA, SPSA, VPSA, RSTA
  INTEGER :: NRPMAX

  ! --- 2D (NTHMP, NRM) flux-surface geometry ---
  REAL(8) :: RPS(NTHMP, NRM), ZPS(NTHMP, NRM)
  REAL(8) :: DRPSI(NTHMP, NRM), DZPSI(NTHMP, NRM)
  REAL(8) :: DRCHI(NTHMP, NRM), DZCHI(NTHMP, NRM)

  ! --- 1D radial profiles (NRM grid) ---
  REAL(8) :: PSIP(NRM), PSIT(NRM), PPS(NRM), TTS(NRM), RST(NRM)
  REAL(8) :: QPS(NRM),  VPS(NRM),  SPS(NRM), RLEN(NRM)
  REAL(8) :: RRMIN(NRM), RRMAX(NRM), ZZMIN(NRM), ZZMAX(NRM)
  REAL(8) :: BBMIN(NRM), BBMAX(NRM), RZMIN(NRM), RZMAX(NRM)
  REAL(8) :: RRPSI(NRM), RSPSI(NRM)
  REAL(8) :: ELIPPSI(NRM), TRIGPSI(NRM)
  REAL(8) :: DVDPSIP(NRM), DVDPSIT(NRM)

  ! --- magnetic components on (NTHMP, NRM) ---
  REAL(8) :: BPR(NTHMP, NRM), BPZ(NTHMP, NRM)
  REAL(8) :: BPT(NTHMP, NRM), BTP(NTHMP, NRM)

  ! --- 1D spline coefficients (on NPSM / NRM) ---
  REAL(8) :: UPPPS(4, NPSM), UTTPS(4, NPSM)
  REAL(8) :: UDPPPS(4, NPSM), UDTTPS(4, NPSM)
  REAL(8) :: UPSIP(4, NRM), UPSIT(4, NRM)
  REAL(8) :: UPPS(4, NRM),  UTTS(4, NRM)
  REAL(8) :: UQPS(4, NRM),  UVPS(4, NRM), USPS(4, NRM), URLEN(4, NRM)
  REAL(8) :: URRMIN(4, NRM), URRMAX(4, NRM)
  REAL(8) :: UZZMIN(4, NRM), UZZMAX(4, NRM)
  REAL(8) :: UBBMIN(4, NRM), UBBMAX(4, NRM)
  REAL(8) :: URRPSI(4, NRM), URSPSI(4, NRM)
  REAL(8) :: UELIPPSI(4, NRM), UTRIGPSI(4, NRM)
  REAL(8) :: UDVDPSIP(4, NRM), UDVDPSIT(4, NRM)

  ! --- flux-surface averages and their splines ---
  REAL(8) :: AVERR2  (NRM), UAVERR2  (4, NRM)
  REAL(8) :: AVEIR2  (NRM), UAVEIR2  (4, NRM)
  REAL(8) :: AVEBB2  (NRM), UAVEBB2  (4, NRM)
  REAL(8) :: AVEIB2  (NRM), UAVEIB2  (4, NRM)
  REAL(8) :: AVEGV   (NRM), UAVEGV   (4, NRM)
  REAL(8) :: AVEGV2  (NRM), UAVEGV2  (4, NRM)
  REAL(8) :: AVEGVR2 (NRM), UAVEGVR2 (4, NRM)
  REAL(8) :: AVEGP2  (NRM), UAVEGP2  (4, NRM)
  REAL(8) :: AVEJTR  (NRM), UAVEJTR  (4, NRM)
  REAL(8) :: AVEJPR  (NRM), UAVEJPR  (4, NRM)
  REAL(8) :: AVERR   (NRM), UAVERR   (4, NRM)
  REAL(8) :: AVEBB   (NRM), UAVEBB   (4, NRM)
  REAL(8) :: AVEGR   (NRM), UAVEGR   (4, NRM)
  REAL(8) :: AVEGR2  (NRM), UAVEGR2  (4, NRM)
  REAL(8) :: AVEGRR2 (NRM), UAVEGRR2 (4, NRM)
  REAL(8) :: DVDRHO  (NRM), UDVDRHO  (4, NRM)
  REAL(8) :: AVEIR   (NRM), UAVEIR   (4, NRM)
  REAL(8) :: RITOR   (NRM), URITOR   (4, NRM)

  ! --- Boozer coordinates ---
  ! Note: eqcom3.inc declares REAL(rkind) CHIP (explicit) -- use REAL(8)
  !       here to stay byte-compatible with rkind=dp=real64 under the
  !       existing bpsd_kinds defaults.
  REAL(8) :: CHIP(NTHMP)
  REAL(8) :: URPS(4, 4, NTHMP, NRM), UZPS(4, 4, NTHMP, NRM)

  ! --- ripple grids ---
  REAL(8) :: Rrp(NRrpM), Zrp(NZrpM), RpplRZ(NRrpM, NZrpM)
  REAL(8) :: URpplRZ(4, 4, NRrpM, NZrpM)
  ! NOTE: G-starting variables fall OUTSIDE the shim IMPLICIT REAL*8
  ! rule (A,B,D-F,H,O-Z), so the original COMMON-based code treated
  ! them as default REAL (REAL*4). Declaring REAL(8) here would change
  ! storage size and break binary layout for downstream consumers
  ! reading via the eqcomq/eqcomm shim.
  REAL :: GRal(NRM, NTVM), GZal(NRM, NTVM)
  REAL :: GAlpRP(NRM, NTVM)
  INTEGER :: NtrcMAX(NRM)

END MODULE eqcom3_mod
