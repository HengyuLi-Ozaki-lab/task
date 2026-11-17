!     ***********************************************************

!           Continuous particle source

!     ***********************************************************

      SUBROUTINE TRPSC

      USE TRCOMM, ONLY : MDLPSC
      IMPLICIT NONE

      IF(MDLPSC.EQ.0) RETURN

      IF(MDLPSC.EQ.1) THEN
         CALL TRPSCA
      ENDIF

      RETURN
      END  SUBROUTINE TRPSC

!     ***********************************************************

!           Particle source (GAUSSIAN PROFILE)

!     ***********************************************************

      SUBROUTINE TRPSCA

      USE TRCOMM, ONLY : DR, RA, RM, DVRHO, NRMAX, PZ, &
           NPSCMAX, PSCTOT, PSCR0, PSCRW, NSPSC, SPSC, rkind
      IMPLICIT NONE
      REAL(rkind)    :: SSUM, S0, SPSCL, QMIN
      INTEGER :: NR, NS, NPSC

      DO NPSC=1,NPSCMAX
!        The exponent is taken relative to its smallest value on the mesh.
!        S0*EXP(-Q) is unchanged; a source far from every mesh point
!        (PSCR0 is in metres, RA*RM) no longer underflows SSUM to 0,
!        which made S0 infinite and the run NaN.
         QMIN = MINVAL(((RA*RM(1:NRMAX)-PSCR0(NPSC))/PSCRW(NPSC))**2)
         SSUM = 0.D0
         DO NR=1,NRMAX
            SSUM=SSUM+DEXP(QMIN-((RA*RM(NR)-PSCR0(NPSC))/PSCRW(NPSC))**2) &
                     *DVRHO(NR)*DR
         ENDDO

         S0 = PSCTOT(NPSC)/SSUM
         NS = NSPSC(NPSC)

         DO NR=1,NRMAX
            SPSCL = S0*DEXP(QMIN-((RA*RM(NR)-PSCR0(NPSC))/PSCRW(NPSC))**2)
            SPSC(NR, 1)=SPSC(NR, 1) + PZ(NS)*SPSCL  ! Electron
            SPSC(NR,NS)=SPSC(NR,NS) +        SPSCL  ! Ion
         ENDDO
      ENDDO

      RETURN
    END  SUBROUTINE TRPSCA

