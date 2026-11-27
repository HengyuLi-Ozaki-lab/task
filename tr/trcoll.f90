! trcoll.f90 --- collision-time functions for the TR transport module.
!
! FTAUE / FTAUI used to be bare external functions in trcalc.f90.  They are
! collected here as module procedures (P1 Task 3), mirroring bpsi's
! trx/trcoll.f90 layout.  The bodies were moved verbatim in the extraction
! commit; the guard on a zero ion density was added afterwards as a
! separate, deliberate change (RECORDED DECISIONS #3, and its note).
!
! Three deliberate divergences from bpsi's trx/trcoll.f90, per RECORDED
! DECISIONS #3 in docs/superpowers/plans/2026-06-15-trx-tr-consolidation.md:
!
!   * The guard is narrower.  trx returns 1.D8 for ABS(ANIL) <= 1.D-8 at
!     the head of both functions.  Here it is ANIL == 0.D0, and only where
!     the function divides by ANIL: see the comment in FTAUE.
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

!     No ions of this species at all (ANIL exactly 0.D0): the collision time
!     is infinite.  Return a large finite value instead of dividing by zero,
!     which gives Inf (NaN when the temperature or the electron density is
!     zero too), or NaN once that is multiplied by a zero pressure
!     downstream.  Every caller gives FTAUE the density of species 2, so here
!     that means a run with no species 2; it is FTAUI that sees the absent
!     species of a run with fewer ions (TRAJBS asks it for species 3 and 4
!     at NSMAX = 2).
!
!     Narrower than trx on purpose.  trx tests ABS(ANIL) <= 1.D-8 before
!     either branch, and the port first did the same.  That also replaced
!     results that had been finite:
!       - a species present at a trace density (measured: tr_iter01 with
!         helium at 1.D-9, 20 steps, 182 of its 567 state values moved, by
!         up to 2.3e-9);
!       - the impurity branch below, whose denominator is ANEL and never
!         depended on ANIL.
!     So the test is for exactly zero, and it sits in the branch that
!     divides by ANIL.  Every result that was finite before the port is the
!     same number now.

      COEF = 6.D0*PI*SQRT(2.D0*PI)*EPS0**2*SQRT(AME)/(AEE**4*1.D20)
      IF(ZL-PZ(2).LE.1.D-7) THEN
         IF(ANIL.EQ.0.D0) THEN
            FTAUE=1.D8
            RETURN
         ENDIF
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

!     No ions of this species at all -- see FTAUE above.  Exactly zero,
!     not ABS(ANIL) <= 1.D-8 as in trx: a trace density has a finite time.
      IF(ANIL.EQ.0.D0) THEN
         FTAUI=1.D8
         RETURN
      ENDIF

      COEF = 12.D0*PI*SQRT(PI)*EPS0**2*SQRT(PAL*AMM)/(AEE**4*1.D20)
      FTAUI = COEF*(TIL*RKEV)**1.5D0/(ANIL*ZL**4*COULOG(2,2,ANEL,TIL))

      RETURN
      END FUNCTION FTAUI

END MODULE trcoll
