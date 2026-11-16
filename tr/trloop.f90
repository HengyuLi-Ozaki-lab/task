! trloop.f90

MODULE trloop

  PRIVATE
  PUBLIC tr_loop

CONTAINS

!     ***********************************************************

!           MAIN ROUTINE FOR TRANSPORT CALCULATION

!     ***********************************************************

  SUBROUTINE tr_loop(ierr)

      USE TRCOMM, ONLY: NT, NTMAX, NRMAX, MDLUF, NTEQIT, MODELG, &
                        PI, DT, &
                        DIPDT, RIP, RIPS, RIPE, &
                        Q0, QP, QPINV, RG, TST, TPRST, &
                        RDPVRHOG, TTRHOG, ARRHOG, T, WPT, RT, NSMAX
      USE TRCOM1, ONLY : NTAMAX
      USE trbpsd, ONLY: tr_bpsd_put, tr_bpsd_get
      USE trexec
      USE libitp
      USE equnit
      USE trfailure
      USE, INTRINSIC :: ieee_arithmetic, ONLY: ieee_is_finite
      USE trregress, ONLY : tr_regress_dump_if_enabled
      IMPLICIT NONE
      INTEGER,INTENT(OUT):: IERR
      INTEGER:: nr

      ierr=0
      IF(NT.GE.NTMAX) GOTO 9000
      CALL tr_eval(NT,IERR)
      IF(IERR.NE.0) GOTO 9000

      IF(MDLUF.EQ.1.OR.MDLUF.EQ.3) THEN
         IF(NTMAX.GT.NTAMAX) NTMAX=NTAMAX
         DIPDT=0.D0
      ELSE
         RIP=RIPS
         IF(NTMAX.GT.NT) DIPDT=(RIPE-RIPS)/(DBLE(NTMAX-NT)*DT)  ! over this call (tr2: NT=0)
         write(6,'(A,1P4E12.4)') "**RIP,RIPS,RIPE,DIP=",RIP,RIPS,RIPE,DIPDT
      ENDIF

      call tr_bpsd_get(ierr)
      if(ierr.ne.0) GOTO 9000

 1000 CONTINUE

      CALL tr_exec(DT,IERR)
      IF(IERR.NE.0) GOTO 9000

      DO nr=1,nrmax
         QPINV(nr)=(4.D0*PI**2*RDPVRHOG(nr))/(TTRHOG(nr)*ARRHOG(nr))
      END DO

!     /* Sawtooth Oscillation */
      Q0=FCTR(RG(1),RG(2),QP(1),QP(2))
      IF(Q0.LT.1.D0) TST=TST+DT

      IF(TST+0.5D0*DT.GT.TPRST) THEN
         CALL TRSAWT
         TST=0.D0
      ENDIF

      call tr_bpsd_put(IERR)
      if(ierr.ne.0) GOTO 9000
      NT=NT+1

!     Refresh metric-derived quantities on the current metric and record a
!     CONSISTENT snapshot BEFORE updating the equilibrium, so the recorded Ip
!     is not the transient (new metric x not-yet-re-equilibrated psi_p) state.
      call tr_bpsd_get(IERR)
      if(ierr.ne.0) return
      CALL tr_eval(NT,IERR)
      IF(IERR.NE.0) GOTO 9000

!     Library mode only: a state that is no longer finite ends the run here,
!     with a record, instead of being stepped on (tr2 never does this).
      IF(tr_library_mode) THEN
         IF(.NOT.(ieee_is_finite(Q0) .AND. ieee_is_finite(WPT) .AND. &
                  ALL(ieee_is_finite(RT(1,1:NSMAX))))) THEN
            CALL tr_failure_record(TRF_NONFINITE, -3, NT, T, &
                 'Q0, WPT or a central temperature is not finite')
            IERR=-3
            GOTO 9000
         ENDIF
      ENDIF

!     *** SET GEOMETRY VIA TASK/EQ (metric update for the NEXT step) ***

      IF(NTEQIT.NE.0) THEN
         IF(MOD(NT,NTEQIT).EQ.0) THEN
            IF(modelg.eq.9) THEN
               IF(tr_library_mode) THEN
!                 Library mode: the outcome of the periodic re-solve is tested,
!                 and a failed one ends the run (tr2 below does not test it).
                  call eq_calc(ierr)
                  IF(ierr.NE.0) THEN
                     CALL tr_failure_record(TRF_EQ_FAILED, ierr, NT, T, &
                          'eq_calc in tr_loop (NTEQIT)')
                     GOTO 9000
                  ENDIF
               ELSE
                  call eq_calc
               ENDIF
               call tr_bpsd_get(IERR)
               if(ierr.ne.0) return
!              Re-prepare transport coefficients on the updated metric
               CALL TRCALC(IERR)
               IF(IERR.NE.0) GOTO 9000
            ENDIF
         ENDIF
      ENDIF

!     *** READING DATA FROM UFILES FOR NEXT STEP ***

      IF(MDLUF.EQ.1.OR.MDLUF.EQ.3) CALL TR_UFREAD
!      IF(MDLUF.EQ.2.AND.MODEP.EQ.3) CALL TR_UFREAD_S
      IF(MDLUF.EQ.2) CALL TR_UFREAD_S

!     ***

      IF(NT.LT.NTMAX) GOTO 1000

 9000 IF(MDLUF.EQ.1.OR.MDLUF.EQ.3) THEN
         RIPS=RIP
         RIPE=RIP
      ELSE
         RIPS=RIPE
      ENDIF
      CALL tr_regress_dump_if_enabled   ! Phase 0 regression dump (env-guarded)
      RETURN
    END SUBROUTINE tr_loop
  END MODULE trloop
