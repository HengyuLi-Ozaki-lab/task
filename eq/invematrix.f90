! invematrix.f90
!
! Phase F-2 (LOW tier): free-form F90 conversion of invematrix.f.
! Gauss-Jordan matrix inversion. Preserves exact numerical semantics
! of the original fixed-form source.
!
      SUBROUTINE INVEMATRIX(NDIM,NDIMM,MATRX,INMATRX,WORK)
!
      IMPLICIT NONE
      INTEGER, INTENT(IN)    :: NDIM, NDIMM
      REAL*8,  INTENT(IN)    :: MATRX(NDIMM,*)
      REAL*8,  INTENT(OUT)   :: INMATRX(NDIMM,*)
      REAL*8,  INTENT(INOUT) :: WORK(NDIMM,*)

      INTEGER I, J, K
!
!      WRITE(*,*) 'INPUT DIMENSION OF MATRIX?'
!      READ(*,*) NDIM
!
      DO I=1,NDIM
         DO J=1,NDIM
!
!            WRITE(*,*) 'INPUT NUMBER OF MATRIX(',I,',',J,')?'
!            READ(*,*) WORK(I,J)
!
            WORK(I,J)=MATRX(I,J)
            IF (I .EQ. J) THEN
               WORK(I,J+NDIM)=1
            ELSE
               WORK(I,J+NDIM)=0
            END IF
         END DO
      END DO
!
      DO K=1,NDIM
         DO I=1,NDIM
            DO J=1,NDIM*2
               IF (K .NE. I) THEN
                  IF (K .NE. J) THEN
                     WORK(I,J)=WORK(I,J) &
                              -WORK(K,J)*(WORK(I,K)/WORK(K,K))
                  END IF
               END IF
            END DO
         END DO
!
         DO J=1,NDIM*2
            IF (K .NE. J) THEN
               WORK(K,J)=WORK(K,J)/WORK(K,K)
            END IF
         END DO
         DO I=1,NDIM
            WORK(I,K)=0
         END DO
         WORK(K,K)=1
      END DO
!
      DO I=1,NDIM
      DO J=1,NDIM
         INMATRX(I,J)=WORK(I,NDIM+J)
      END DO
      END DO
!
! 2000 FORMAT(1X,100F7.2)
!      DO I=1,NDIM
!            WRITE(*,2000) (WORK(I,J),J=NDIM+1,DIM*2)
!      END DO
      RETURN
      END SUBROUTINE INVEMATRIX
