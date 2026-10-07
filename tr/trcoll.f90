! trcoll.f90 --- collision-time functions for the TR transport module.
!
! FTAUE / FTAUI used to be bare external functions in trcalc.f90.  They are
! collected here as module procedures (P1 Task 3), mirroring bpsi's
! trx/trcoll.f90 layout.  The bodies were moved verbatim in the extraction
! commit; the ABS(ANIL) guard below was added afterwards as a separate,
! deliberate change (RECORDED DECISIONS #3).
!
! Two deliberate divergences from bpsi's trx/trcoll.f90, per RECORDED
! DECISIONS #3 in docs/superpowers/plans/2026-06-15-trx-tr-consolidation.md:
!
!   * FTAUI keeps kyoshimi's AMM (trcomm_const.f90) rather than bpsd's AMP.
!     They are NOT the same number any more: bpsd updated AMP to the CODATA
!     2018 value 1.67262192369e-27 while AMM is still 1.672621637e-27, a
!     relative difference of ~1.7e-7.  Using AMP would shift FTAUI by ~8.6e-8
!     and break the 1e-10 equivalence baselines.
!
!   * FTAUE keeps PZ(2) rather than bpsi's PZ(NS_D): kyoshimi's tr defines no
!     NS_D.  For the e/D/T/He4 species ordering NS_D == 2, so the two are
!     numerically identical.

MODULE trcoll

  USE trlib, ONLY : COULOG
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: FTAUE, FTAUI

CONTAINS

!     ***********************************************************

!           COLLISION TIME

!     ***********************************************************

!     between electrons and ions

      FUNCTION FTAUE(ANEL,ANIL,TEL,ZL)

!     ANEL : electron density [10^20 /m^3]
!     ANIL : ion density [10^20 /m^3]
!     TEL  : electron temperature [kev]
!     ZL   : ion charge number

      USE TRCOMM, ONLY : AEE, AME, EPS0, PI, PZ, RKEV, rkind
      IMPLICIT NONE
      REAL(rkind) :: ANEL, ANIL, TEL, ZL, FTAUE
      REAL(rkind) :: COEF

!     Vanishing ion density: the collision time diverges. Return a large
!     finite value instead of dividing by ~0 (which yields Inf, or NaN once
!     multiplied by a zero pressure downstream).
!     NOTE: this guard precedes the impurity branch below, whose denominator
!     uses ANEL (not ANIL) and would stay finite for ANIL~0. Guarding on ANIL
!     for both branches is deliberate -- it reproduces bpsi trx/trcoll.f90
!     exactly, which is what the Task-7 1e-10 comparison is written against.
      IF(ABS(ANIL).LE.1.D-8) THEN
         FTAUE=1.D8
         RETURN
      ENDIF

      COEF = 6.D0*PI*SQRT(2.D0*PI)*EPS0**2*SQRT(AME)/(AEE**4*1.D20)
      IF(ZL-PZ(2).LE.1.D-7) THEN
         FTAUE = COEF*(TEL*RKEV)**1.5D0/(ANIL*ZL**2*COULOG(1,2,ANEL,TEL))
      ELSE
!     If the plasma contains impurities, we need to consider the
!     effective charge number instead of ion charge number.
!     From the definition of Zeff=sum(n_iZ_i^2)/n_e,
!     n_iZ_i^2 is replaced by n_eZ_eff at the denominator of tau_e.
         FTAUE = COEF*(TEL*RKEV)**1.5D0/(ANEL*ZL*COULOG(1,2,ANEL,TEL))
      ENDIF

      RETURN
      END FUNCTION FTAUE

!     between ions and ions

      FUNCTION FTAUI(ANEL,ANIL,TIL,ZL,PAL)

!     ANEL : electron density [10^20 /m^3]
!     ANIL : ion density [10^20 /m^3]
!     TIL  : ion temperature [kev]
!     ZL   : ion charge number
!     PAL  : ion atomic number

      USE TRCOMM, ONLY : AEE, AMM, EPS0, PI, RKEV, rkind
      IMPLICIT NONE
      REAL(rkind):: ANEL, ANIL, PAL, TIL, ZL, FTAUI
      REAL(rkind):: COEF

!     Vanishing ion density -- see FTAUE above.
      IF(ABS(ANIL).LE.1.D-8) THEN
         FTAUI=1.D8
         RETURN
      ENDIF

      COEF = 12.D0*PI*SQRT(PI)*EPS0**2*SQRT(PAL*AMM)/(AEE**4*1.D20)
      FTAUI = COEF*(TIL*RKEV)**1.5D0/(ANIL*ZL**4*COULOG(2,2,ANEL,TIL))

      RETURN
      END FUNCTION FTAUI

END MODULE trcoll
