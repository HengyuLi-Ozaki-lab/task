! eqgetp.f90
!
! Phase F-2 (LOW tier): free-form F90 conversion of eqgetp.f.
!
! NOTE: IMPLICIT NONE is NOT added here because the INCLUDEd shim
!       '../eq/eqcomq.inc' already supplies an IMPLICIT statement
!       (IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)) and USEs the
!       F-1 MODULEs (eqcom0/1/3_mod) for the COMMON symbols. Preserves
!       exact numerical semantics of the original fixed-form source.
!
!     ***** GET PARAMETERS *****

      SUBROUTINE EQGETP(RHOT1,PSIP1,NRMAX1)

      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INTEGER, INTENT(IN)  :: NRMAX1
      REAL*8,  INTENT(OUT) :: RHOT1(NRMAX1), PSIP1(NRMAX1)

      DO NR=1,NRMAX1
         RHOT1(NR)=RHOT(NR)
         PSIP1(NR)=PSIP(NR)
!honda         write(6,*) "EQGETP",NR,RHOT(NR)
      ENDDO
      RETURN
      END SUBROUTINE EQGETP

      SUBROUTINE EQGETR(RPS1,DRPSI1,DRCHI1,NTHM1,NTHMAX1,NRMAX1)

      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INTEGER, INTENT(IN)  :: NTHM1, NTHMAX1, NRMAX1
      REAL*8,  INTENT(OUT) :: RPS1(NTHM1,NRMAX1)
      REAL*8,  INTENT(OUT) :: DRPSI1(NTHM1,NRMAX1), DRCHI1(NTHM1,NRMAX1)

      DO NR=1,NRMAX1
      DO NTH=1,NTHMAX1
         RPS1  (NTH,NR)=RPS  (NTH,NR)
         DRPSI1(NTH,NR)=DRPSI(NTH,NR)
         DRCHI1(NTH,NR)=DRCHI(NTH,NR)
!$$$         IF(NR.LE.5) THEN
!$$$            WRITE(6,'(2I5,1P3E12.4)')
!$$$     &           NR,NTH,RPS(NTH,NR),DRPSI(NTH,NR),DRCHI(NTH,NR)
!$$$         ENDIF
      ENDDO
      ENDDO
      RETURN
      END SUBROUTINE EQGETR

      SUBROUTINE EQGETZ(ZPS1,DZPSI1,DZCHI1,NTHM1,NTHMAX1,NRMAX1)

      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INTEGER, INTENT(IN)  :: NTHM1, NTHMAX1, NRMAX1
      REAL*8,  INTENT(OUT) :: ZPS1(NTHM1,NRMAX1)
      REAL*8,  INTENT(OUT) :: DZPSI1(NTHM1,NRMAX1), DZCHI1(NTHM1,NRMAX1)

      DO NR=1,NRMAX1
      DO NTH=1,NTHMAX1
         ZPS1  (NTH,NR)=ZPS  (NTH,NR)
         DZPSI1(NTH,NR)=DZPSI(NTH,NR)
         DZCHI1(NTH,NR)=DZCHI(NTH,NR)
      ENDDO
      ENDDO
      RETURN
      END SUBROUTINE EQGETZ

      SUBROUTINE EQGETQ(PPS1,QPS1,RBPS1,VPS1,RLEN1,NRMAX1)

      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INTEGER, INTENT(IN)  :: NRMAX1
      REAL*8,  INTENT(OUT) :: PPS1(NRMAX1), QPS1(NRMAX1), RBPS1(NRMAX1)
      REAL*8,  INTENT(OUT) :: VPS1(NRMAX1), RLEN1(NRMAX1)

      DO NR=1,NRMAX1
         PPS1(NR) =PPS(NR)
         QPS1(NR) =QPS(NR)
         RBPS1(NR)=TTS(NR)
         VPS1(NR) =VPS(NR)
         RLEN1(NR)=RLEN(NR)
      ENDDO
      RETURN
      END SUBROUTINE EQGETQ

      SUBROUTINE EQGETQN(PPS1,QPS1,RBPS1,VPS1,RLEN1,RITOR1,NRMAX1)

      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INTEGER, INTENT(IN)  :: NRMAX1
      REAL*8,  INTENT(OUT) :: PPS1(NRMAX1), QPS1(NRMAX1), RBPS1(NRMAX1)
      REAL*8,  INTENT(OUT) :: VPS1(NRMAX1), RLEN1(NRMAX1), RITOR1(NRMAX1)

      DO NR=1,NRMAX1
         PPS1(NR) =PPS(NR)
         QPS1(NR) =QPS(NR)
         RBPS1(NR)=TTS(NR)
         VPS1(NR) =VPS(NR)
         RLEN1(NR)=RLEN(NR)
         RITOR1(NR)=RITOR(NR)
      ENDDO
      RETURN
      END SUBROUTINE EQGETQN

      SUBROUTINE EQGETU(RSU1,ZSU1,RSW1,ZSW1,NSUMAX1)

      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INTEGER, INTENT(IN)  :: NSUMAX1
      REAL*8,  INTENT(OUT) :: RSU1(NSUMAX1), ZSU1(NSUMAX1)
      REAL*8,  INTENT(OUT) :: RSW1(NSUMAX1), ZSW1(NSUMAX1)

      DO NSU=1,NSUMAX1
         RSU1(NSU)=RSU(NSU)
         ZSU1(NSU)=ZSU(NSU)
         RSW1(NSU)=RSW(NSU)
         ZSW1(NSU)=ZSW(NSU)
      ENDDO
      RETURN
      END SUBROUTINE EQGETU

      SUBROUTINE EQGETF(RGMIN1,RGMAX1,ZGMIN1,ZGMAX1)

      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(OUT) :: RGMIN1, RGMAX1, ZGMIN1, ZGMAX1

      RGMIN1=RGMIN
      RGMAX1=RGMAX
      ZGMIN1=ZGMIN
      ZGMAX1=ZGMAX
      RETURN
      END SUBROUTINE EQGETF

      SUBROUTINE EQGETA(RAXIS1,ZAXIS1,PSIPA1,PSITA1,Q01,QA1)

      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(OUT) :: RAXIS1, ZAXIS1, PSIPA1, PSITA1, Q01, QA1

      RAXIS1=RAXIS
      ZAXIS1=ZAXIS
      PSIPA1=PSIPA
      PSITA1=PSITA
      Q01   =QAXIS
      QA1   =QSURF
      RETURN
      END SUBROUTINE EQGETA

      SUBROUTINE EQGETG(RPS1,ZPS1,NTHM1,NTHMAX1,NRMAX1)

      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INTEGER, INTENT(IN)  :: NTHM1, NTHMAX1, NRMAX1
      REAL*8,  INTENT(OUT) :: RPS1(NTHM1,NRMAX1)
      REAL*8,  INTENT(OUT) :: ZPS1(NTHM1,NRMAX1)

      DO NR=1,NRMAX1
      DO NTH=1,NTHMAX1
         RPS1  (NTH,NR)=RPS  (NTH,NR)
         ZPS1  (NTH,NR)=ZPS  (NTH,NR)
      ENDDO
      ENDDO
      RETURN
      END SUBROUTINE EQGETG

      SUBROUTINE EQGETBB(BPR1,BPZ1,BPT1,BTP1,NTHM1,NTHMAX1,NRMAX1)

      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INTEGER, INTENT(IN)  :: NTHM1, NTHMAX1, NRMAX1
      REAL*8,  INTENT(OUT) :: BPR1(NTHM1,NRMAX1)
      REAL*8,  INTENT(OUT) :: BPZ1(NTHM1,NRMAX1)
      REAL*8,  INTENT(OUT) :: BPT1(NTHM1,NRMAX1)
      REAL*8,  INTENT(OUT) :: BTP1(NTHM1,NRMAX1)

      DO NR=1,NRMAX1
      DO NTH=1,NTHMAX1
         BPR1(NTH,NR)=BPR(NTH,NR)
         BPZ1(NTH,NR)=BPZ(NTH,NR)
         BPT1(NTH,NR)=BPT(NTH,NR)
         BTP1(NTH,NR)=BTP(NTH,NR)
      ENDDO
      ENDDO
      RETURN
      END SUBROUTINE EQGETBB
