! eqcom1_mod.f90
!
! F90 MODULE mirror of eqcom1.inc (global / output state).
!
! Phase F-1 Task F-1-2 (eq F90 modernization plan).
!
! During the transition period this MODULE coexists with the
! classic eqcom1.inc COMMON declarations. Client code should
! migrate incrementally (INCLUDE -> USE). The bundle shims
! eqcom{c,m,q,x}.inc USE this module so cross-module callers
! obtain identical symbols through either path.

MODULE eqcom1_mod
  USE eqcom0_mod, ONLY: NRGM, NZGM, NPSM, NRVM, NSUM, NPFCM
  IMPLICIT NONE
  PUBLIC
  SAVE

  ! --- scalar profile parameters ---
  !   /EQPRM3/ pressure profile coefficients
  REAL(8) :: PP0, PP1, PP2, PROFP0, PROFP1, PROFP2
  !   /EQPRM4/ current profile coefficients
  REAL(8) :: PJ0, PJ1, PJ2, PROFJ0, PROFJ1, PROFJ2
  !   /EQPRM5/ FF' profile coefficients
  REAL(8) :: FF0, FF1, FF2, PROFF0, PROFF1, PROFF2
  !   /EQPRM7/ temperature profile
  REAL(8) :: PT0, PT1, PT2, PROFTP0, PROFTP1, PROFTP2, PTSEQ, PN0EQ
  !   /EQPRM8/ rotation / velocity profile
  REAL(8) :: PV0, PV1, PV2, PROFV0, PROFV1, PROFV2, OTC, HM
  !   /EQPRM9/ rho-axis profile
  REAL(8) :: PROFR0, PROFR1, PROFR2

  ! --- scalar control integers ---
  INTEGER :: NSGMAX, NTGMAX, NUGMAX, NTIMES
  INTEGER :: NRGMAX, NZGMAX, NPSMAX, NRVMAX, NTVMAX
  INTEGER :: NRMAX,  NTHMAX, NSUMAX
  INTEGER :: MDLEQF, MDLEQC, MDLEQA, MDLEQX, MDLEQV, NPRINT

  REAL(8) :: EPSEQ
  INTEGER :: NLPMAX
  REAL(8) :: EPSNW, DELNW
  INTEGER :: NLPNW

  ! --- boundary-driven scalars ---
  REAL(8) :: RGMIN, RGMAX, ZGMIN, ZGMAX
  REAL(8) :: PSIB(0:5)
  REAL(8) :: RIPFC(NPFCM), RPFC(NPFCM), ZPFC(NPFCM), WPFC(NPFCM)
  INTEGER :: NPFCMAX
  REAL(8) :: ZLIMP, ZLIMM, FRBIN

  ! --- global equilibrium scalars ---
  REAL(8) :: RAXIS, ZAXIS, PSI0, PSIPA, PSITA, REDGE
  REAL(8) :: PVOL, RAAVE, BETAT, BETAP, QAXIS, QSURF
  REAL(8) :: TJ, PSIITB
  INTEGER :: IDCALV
  REAL(8) :: RRC, RIPX, RBRA
  REAL(8) :: RXPNT1, ZXPNT1, PSIXPNT1, RXPNT2, ZXPNT2, PSIXPNT2
  INTEGER :: NXPOINT

  ! --- 2D output / flux-surface arrays ---
  REAL(8) :: RG(NRGM), ZG(NZGM), PSIRZ(NRGM, NZGM)
  REAL(8) :: PSIPS(NPSM), PPPS(NPSM), TTPS(NPSM)
  REAL(8) :: DPPPS(NPSM), TTDTTPS(NPSM), QQPS(NPSM), DTTPS(NPSM)
  REAL(8) :: TEPS(NPSM), OMPS(NPSM)
  REAL(8) :: UPSIRZ(4, 4, NRGM, NZGM)
  REAL(8) :: HJTRZ(NRGM, NZGM)
  REAL(8) :: UHJTRZ(4, 4, NRGM, NZGM)

  ! --- averaged / volume profiles (NRVM grid) ---
  REAL(8) :: PSIPV(NRVM), PSIPNV(NRVM), RHOT(NRVM)
  REAL(8) :: PSITV(NRVM), UPSITV(4, NRVM)
  REAL(8) :: QPV(NRVM),   UQPV(4, NRVM)
  REAL(8) :: TTV(NRVM),   UTTV(4, NRVM)
  REAL(8) :: RSV(NRVM),   VPV(NRVM)
  REAL(8) :: AVBB2(NRVM), AVIR2(NRVM), AVRR2(NRVM)
  REAL(8) :: FIPV(NRVM),  UFIPV(4, NRVM)

  ! --- surface / wall curves (NSUM+1 samples) ---
  REAL(8) :: RSU(NSUM+1), ZSU(NSUM+1)
  REAL(8) :: RSW(NSUM+1), ZSW(NSUM+1)

END MODULE eqcom1_mod
