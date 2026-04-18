! newton.f90
!
! Phase F-2 (LOW tier): free-form F90 conversion of newton.f.
! Preserves exact numerical semantics of the original fixed-form source.
!
      SUBROUTINE NEWTON4(N,X0,XLAST,SUB,STATUS,COUNTL,DD,TOL,MAXITS)
!
!      NEED  SUBROUTINE SUB(X(N),FX(N),N,IERR)
!      NEED  M=N
!
      IMPLICIT NONE
      INTEGER NWEQM, NWEQM2
      PARAMETER (NWEQM=4, NWEQM2=2*NWEQM)
      INTEGER, INTENT(IN)    :: N
      REAL*8,  INTENT(IN)    :: DD, TOL
      INTEGER, INTENT(IN)    :: MAXITS
      REAL*8,  INTENT(IN)    :: X0(NWEQM)
      REAL*8,  INTENT(OUT)   :: XLAST(NWEQM)
      INTEGER, INTENT(OUT)   :: STATUS, COUNTL
      EXTERNAL SUB

      INTEGER M, IERR
      INTEGER ITRATE, SOLVED, LIMIT, FLAT, ERROR
      INTEGER I, J
      REAL*8 TINY, DFDXMIN, SUML, DDTEMP
      REAL*8 OLDX(NWEQM), NEWX(NWEQM)
      REAL*8 DFDX(NWEQM,NWEQM), INDFDX(NWEQM,NWEQM)
      REAL*8 DX(NWEQM), FX(NWEQM), WORK(NWEQM,NWEQM2)
      REAL*8 WORKS(NWEQM,3)
      PARAMETER (TINY=1D-10)
      PARAMETER (ITRATE=-1, SOLVED=0, LIMIT=1, FLAT=2, ERROR=3)
      INTRINSIC ABS
!
!      TOL=5.D-7
!      TOL=1.D-4
!      MAXITS=100
!
      SUML=1.D0
      DFDXMIN=1.D0
      M=N
!
      DO I=1,N
         NEWX(I)=X0(I)
      END DO

      STATUS=ITRATE
      DO COUNTL=1,MAXITS
!
!        WRITE(*,*) 'QQQQQ',NEWX(1),NEWX(2),NEWX(3),NEWX(4)
!
         DDTEMP=DD
         CALL NEWTON_SUB(N,NWEQM,NEWX,DFDX,SUB,DDTEMP,WORKS,IERR)
         IF(IERR.NE.0) THEN
            STATUS=ERROR
            GOTO 11
         ENDIF
!
         DO I=1,4
         DO J=1,4
            WRITE(*,*) 'DDDDDDDD',DFDX(I,J)
         END DO
         END DO
         CALL INVEMATRIX(N,NWEQM,DFDX,INDFDX,WORK)
         DO I=1,4
         DO J=1,4
            WRITE(*,*) 'BBBBBBBBB',INDFDX(I,J)
         END DO
         END DO
         DO I=1,M
!         DO J=1,N
!            DFDXMIN=MIN(DFDXMIN,ABS(INDFDX(I,J)))
            DFDXMIN=MIN(DFDXMIN,ABS(INDFDX(I,I)))
!         END DO
         END DO

         IF (ABS(DFDXMIN).LE.TINY) THEN
!          {flat spot}
            STATUS=FLAT
         ELSE
!          {perform Newton algorithm}
            DO I=1,M
               OLDX(I)=NEWX(I)
            END DO
            CALL SUB(OLDX,FX,N,IERR)
            IF(IERR.NE.0) THEN
               STATUS=ERROR
               GOTO 11
            ENDIF
!
            WRITE(*,*) 'BBBBB',FX(1)
            DO I=1,M
               DX(I)=0.D0
            END DO
            DO I=1,M
            DO J=1,N
               DX(I)=DX(I)-INDFDX(I,J)*FX(J)
            END DO
            END DO
            DO I=1,M
               NEWX(I)=OLDX(I)+DX(I)
            END DO
!
            SUML=0.D0
            DO I=1,M
               SUML=SUML+(DX(I)/MAX(ABS(OLDX(I)),1.D0))**2
            END DO
            SUML=SQRT(SUML/DBLE(M))
            WRITE(6,'(A,1PE12.4)') '** NEWTON4: SUML=',SUML
            IF (SUML.LE.TOL) STATUS=SOLVED
         END IF
         IF (STATUS.NE.ITRATE) GO TO 11
      END DO
      STATUS=LIMIT

   11 DO I=1,M
         XLAST(I)=NEWX(I)
      END DO
      WRITE(6,*) 'STATUS=',STATUS
      RETURN
      END SUBROUTINE NEWTON4
!
!************************************************************
      SUBROUTINE NEWTON_SUB(N,NM,X,DFDX,SUB,DD,WORKS,IERR)
!
      IMPLICIT NONE
      INTEGER, INTENT(IN)    :: N, NM
      REAL*8,  INTENT(IN)    :: X(N)
      REAL*8,  INTENT(OUT)   :: DFDX(NM,N)
      REAL*8,  INTENT(INOUT) :: WORKS(NM,3)
      REAL*8,  INTENT(IN)    :: DD
      INTEGER, INTENT(OUT)   :: IERR
      EXTERNAL SUB

      INTEGER I, J
!
!     WORKS(I,1) = XNEW(I)
!     WORKS(I,2) = RESULT0(I)
!     WORKS(I,3) = RESULT(I)
!
!      DD=1.D-2
!
      CALL SUB(X,WORKS(1,2),N,IERR)
      IF(IERR.NE.0) RETURN
      DO J=1,N
         DO I=1,N
            WORKS(I,1)=X(I)
         ENDDO
         WORKS(J,1)=X(J)+DD
         CALL SUB(WORKS(1,1),WORKS(1,3),N,IERR)
         IF(IERR.NE.0) RETURN
         WORKS(J,1)=X(J)
         DO I=1,N
            DFDX(I,J)=(WORKS(I,3)-WORKS(I,2))/DD
            WRITE(*,*) 'NNNNNNN',DFDX(I,J)
         END DO
      END DO
      RETURN
      END SUBROUTINE NEWTON_SUB
