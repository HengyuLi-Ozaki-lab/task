!     $Id$
!
! Phase F-3 (MED tier): free-form F90 conversion of eqcalv.f.
! Volume integral / flux-surface average routines for EQCALC:
! EQCALV, EQPSITN, EQQPV, EQTTV, EQIPJP, EQIPQP, EQFIPV.
! Preserves exact numerical semantics of the original fixed-form source.
!
! NOTE: IMPLICIT NONE is NOT added here because the INCLUDEd shim
!       '../eq/eqcomc.inc' already supplies an IMPLICIT statement
!       (IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)) and USEs the
!       F-1 MODULEs (eqcom0/1/2_mod) for the COMMON symbols.
!
!     ***** CALCULATE FLUX AVERAGE FOR EQCALC *****
!
      SUBROUTINE EQCALV(IERR)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom2_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INTEGER, INTENT(OUT) :: IERR

      DIMENSION XA(NTVM),YA(2,NTVM)
      DIMENSION DERIV(NRVM)

      IERR=0

      CALL EQAXIS(IERR)
      IF(IERR.NE.0) RETURN

      DR=(REDGE-RAXIS)/(NRVMAX-1)
      PSIPV(1)=0.D0

      DO NRV=2,NRVMAX
         RINIT=RAXIS+DR*(NRV-1)
         ZINIT=ZAXIS
         PSIL=PSIG(RINIT,ZINIT)
         PSIPL=PSIL-PSI0
         PSIPN=PSIPL/PSIPA
!         IF(PSIPN.GT.1.D0) THEN
!            PSIPL=PSIPA
!            PSIPN=1.D0
!         ENDIF
         PSITN=EQPSITN(PSIPN)
         PSITL=PSITA*PSITN
         RMINL=SQRT(ABS(PSITL/(BB*PI)))
         FIPL=EQTTV(PSIPN)
         IF(MOD(MDLEQF,5).EQ.4) THEN
            CALL EQQPSI(PSIPN,QPSL)
         ELSE
            QPSL=EQQPV(PSIPN)
         ENDIF
         PSIPV(NRV)=PSIPL

         CALL EQMAGS(RINIT,ZINIT,NTVMAX,XA,YA,NA,IERR)

         SUMV=0.D0
         SUMAVBB2=0.D0
         SUMAVIR2=0.D0
         SUMAVRR2=0.D0
         DO N=2,NA
            CALL PSIGD(YA(1,N),YA(2,N),DPSIDR,DPSIDZ)
            R=YA(1,N)
            H=XA(N)-XA(N-1)
            BPL=SQRT(DPSIDR**2+DPSIDZ**2)/(2.D0*PI*R)
            BTL=FIPL/(2.D0*PI*R)
            B2L=BPL**2+BTL**2

            SUMV    =SUMV    +H/BPL
            SUMAVBB2=SUMAVBB2+H*B2L/BPL
            SUMAVIR2=SUMAVIR2+H/(BPL*R*R)
            SUMAVRR2=SUMAVRR2+H*BPL
         ENDDO
         RSV(NRV)=RMINL
         AVBB2(NRV)=SUMAVBB2/(BB**2*SUMV)
         AVIR2(NRV)=SUMAVIR2*RR**2/SUMV
         IF(MOD(MDLEQF,5).EQ.4) THEN
            FACTOR=FIPL*SUMAVIR2/(4.D0*PI**2*QPSL)
            QPV(NRV)=QPSL
!            WRITE(6,'(A,1PE12.4)') 'FACTOR=',FACTOR
         ELSE
            FACTOR=1.D0
            QPV(NRV)=FIPL*SUMAVIR2/(4.D0*PI**2)
         ENDIF
         VPV(NRV)=2.D0*PI*RSV(NRV)*BB*SUMV/QPV(NRV)
         AVRR2(NRV)=SUMAVRR2*QPV(NRV)**2/(RSV(NRV)**2*BB**2*SUMV) &
                    *FACTOR
      ENDDO

      QPV(1)  =(4*QPV(2)  -QPV(3)  )/3.D0
      AVBB2(1)=(4*AVBB2(2)-AVBB2(3))/3.D0
      AVIR2(1)=(4*AVIR2(2)-AVIR2(3))/3.D0
      AVRR2(1)=(4*AVRR2(2)-AVRR2(3))/3.D0
      VPV(1)  =0.D0
      RSV(1)  =0.D0
!
!     ----- CALCULATE TOROIDAL FLUX -----
!
      PSITV(1)=0.D0
      DO NRV=2,NRVMAX
         PSITV(NRV)=PSITV(NRV-1) &
              +2.0D0*QPV(NRV)*QPV(NRV-1)/(QPV(NRV)+QPV(NRV-1)) &
                    *(PSIPV(NRV)-PSIPV(NRV-1))
      ENDDO
      PSITA=PSITV(NRVMAX)
      PSIPA=PSIPV(NRVMAX)

      DO NRV=1,NRVMAX
         PSIPNV(NRV)=PSIPV(NRV)/PSIPA
!         WRITE(6,'(A,1P5E12.4)') 'PSIV:',
!     &        PSIPV(NRV),PSIPA,PSIPNV(NRV),PSITV(NRV),QPV(NRV)
      ENDDO

      CALL SPL1D(PSIPNV,PSITV,DERIV,UPSITV,NRVMAX,0,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX SPL1D for PSITV: IERR=',IERR
!
!     ----- calculate PSIITB -----
!
      CALL EQCNVA(RHOITB(1)**2,PSIITB)

!      DO NR=1,11
!         PSIPNL=0.002*(NR-1)
!         CALL EQPPSI(PSIPNL,PPSIL,DPPSIL)
!         PSITNL=EQPSITN(PSIPNL)
!         QPVL=EQQPV(PSIPNL)
!         WRITE(6,'(I5,1P6E12.4)')
!     &        NR,PSIPNL,PSITNL,PPSIL,DPPSIL
!      ENDDO
      RETURN
      END SUBROUTINE EQCALV
!
!     *************************************
!        Convert Psipn to Psitn
!     *************************************
!
      FUNCTION EQPSITN(PSIPNL)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom2_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: PSIPNL
      REAL*8 :: EQPSITN

      CALL SPL1DF(PSIPNL,PSITL,PSIPNV,UPSITV,NRVMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX EQPSITN: SPL1DF: PSITL: IERR=',IERR
      EQPSITN=PSITL/PSITA
      RETURN
      END FUNCTION EQPSITN
!
!     *************************************
!        Calculate QPV
!     *************************************
!
      FUNCTION EQQPV(PSIPNL)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom2_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: PSIPNL
      REAL*8 :: EQQPV

      CALL SPL1DF(PSIPNL,QPVL,PSIPNV,UQPV,NRVMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX EQQPV: SPL1DF: QPVL: IERR=',IERR
      IF(IERR.NE.0) WRITE(6,*) PSIPNL,PSIPNV(1),PSIPNV(NRVMAX)
      EQQPV=QPVL
      RETURN
      END FUNCTION EQQPV
!
!     *************************************
!        Calculate TTV
!     *************************************
!
      FUNCTION EQTTV(PSIPNL)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom2_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: PSIPNL
      REAL*8 :: EQTTV

      CALL SPL1DF(PSIPNL,TTVL,PSIPNV,UTTV,NRVMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX EQQPV: SPL1DF: TTVL: IERR=',IERR
      EQTTV=TTVL
      RETURN
      END FUNCTION EQTTV
!
!     ****************************
!        Calculate IPOL from JP
!     ****************************
!
      SUBROUTINE EQIPJP

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom2_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      DIMENSION DERIV(NRVM)

      FIPV(NRVMAX)=2.D0*PI*BB*RR

      DO NRV=NRVMAX,2,-1
         PSIPL=PSIPV(NRV)
         PSIPNL=PSIPL/PSIPA
!         IF(PSIPNL.GT.1.D0) THEN
!            WRITE(6,*) NRV,PSIPL,PSIPA,PSIPNL
!         ENDIF
         CALL EQPPSI(PSIPNL,PPSI,DPPSI)
         CALL EQJPSI(PSIPNL,HJPSID,HJPSI)
         PSIPLP=PSIPL
         ALP=RMU0*DPPSI/(BB**2*AVBB2(NRV))
         BLP=-RMU0*HJPSI/(BB*AVBB2(NRV))

         PSIPL=PSIPV(NRV-1)
         PSIPNL=PSIPL/PSIPA
!         IF(PSIPNL.GT.1.D0) THEN
!            WRITE(6,*) NRV,PSIPL,PSIPA,PSIPNL
!         ENDIF
         CALL EQPPSI(PSIPNL,PPSI,DPPSI)
         CALL EQJPSI(PSIPNL,HJPSID,HJPSI)
         PSIPLM=PSIPL
         ALM=RMU0*DPPSI/(BB**2*AVBB2(NRV-1))
         BLM=-RMU0*HJPSI/(BB*AVBB2(NRV-1))

         AL=0.5D0*(ALP+ALM)*0.5D0*(PSIPLP-PSIPLM)
         BL=0.5D0*(BLP+BLM)      *(PSIPLP-PSIPLM)
         FIPV(NRV-1)=((1.D0+AL)*FIPV(NRV)-BL)/(1.D0-AL)
      ENDDO

!      DO NRV=1,NRVMAX
!         WRITE(6,'(A,I5,1P2E12.4)') 'NRV:',NRV,PSIPV(NRV),FIPV(NRV)
!      ENDDO
!         WRITE(6,'(A,1P2E12.4)') 'FIPV:',FIPV(1),FIPV(NRVMAX)

      CALL SPL1D(PSIPNV,FIPV,DERIV,UFIPV,NRVMAX,0,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX SPL1D for FIPV: IERR=',IERR
      END SUBROUTINE EQIPJP
!
!     ****************************
!        Calculate IPOL from QP
!     ****************************
!
      SUBROUTINE EQIPQP

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom2_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      DIMENSION DERIV(NRVM)

      FIPV(NRVMAX)=2.D0*PI*BB*RR

      DO NRV=NRVMAX,2,-1
         PSIPL=PSIPV(NRV)
         PSIPNL=PSIPL/PSIPA
         CALL EQPPSI(PSIPNL,PPSI,DPPSI)
         CALL EQQPSI(PSIPNL,QPSI)
!         write(6,'(I5,1P3E12.4)') NRV,PSIPNL,PPSI,QPSI
!         write(6,'(5X,1P3E12.4)') RSV(NRV),AVIR2(NRV),VPV(NRV)
         PSIPLP=PSIPL
         XP=RSV(NRV)/QPSI
         ALP=4.D0*PI**2*BB**2*RR**2*XP/(AVIR2(NRV)*VPV(NRV))
         BLP=4.D0*PI**2*RMU0*RR**2*DPPSI/AVIR2(NRV)
         FLP=VPV(NRV)*AVRR2(NRV)*XP

         PSIPL=PSIPV(NRV-1)
         PSIPNL=PSIPL/PSIPA
         CALL EQPPSI(PSIPNL,PPSI,DPPSI)
         CALL EQQPSI(PSIPNL,QPSI)
!         write(6,'(I5,1P3E12.4)') NRV,PSIPNL,PPSI,QPSI
!         write(6,'(5X,1P3E12.4)') RSV(NRV),AVIR2(NRV),VPV(NRV)
         PSIPLM=PSIPL
         XM=RSV(NRV-1)/QPSI
         IF(NRV.EQ.2) THEN
            ALM=4.D0*PI**2*BB**2*RR**2*XP/(AVIR2(NRV-1)*VPV(NRV))
         ELSE
            ALM=4.D0*PI**2*BB**2*RR**2*XM/(AVIR2(NRV-1)*VPV(NRV-1))
         ENDIF
         BLM=4.D0*PI**2*RMU0*RR**2*DPPSI/AVIR2(NRV-1)
         FLM=VPV(NRV-1)*AVRR2(NRV-1)*XM

         YP=0.5D0*FIPV(NRV)**2
         YM=YP+0.5D0*(BLP+BLM)*(PSIPLP-PSIPLM) &
              +0.5D0*(ALP+ALM)*(FLP-FLM)
!         write(6,'(I5,1P2E12.4)') NRV,YP,YM
         FIPV(NRV-1)=SQRT(2.D0*YM)
      ENDDO

!      DO NRV=1,NRVMAX
!         WRITE(6,'(A,I5,1P2E12.4)') 'NRV:',NRV,PSIPV(NRV),FIPV(NRV)
!      ENDDO
!         WRITE(6,'(A,1P2E12.4)') 'FIPV:',FIPV(1),FIPV(NRVMAX)

      CALL SPL1D(PSIPNV,FIPV,DERIV,UFIPV,NRVMAX,0,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX SPL1D for FIPV: IERR=',IERR
      END SUBROUTINE EQIPQP
!
!     **************************************
!        Calculate bounce-averaged metric
!     **************************************
!
      SUBROUTINE EQFIPV(PSIPNL,FIPL,DFIPL)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom2_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN)  :: PSIPNL
      REAL*8, INTENT(OUT) :: FIPL, DFIPL

      CALL SPL1DD(PSIPNL,FIPL,DFIPL,PSIPNV,UFIPV,NRVMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX EQFIPV: SPL1DD: FIPL: IERR=',IERR
      DFIPL=DFIPL/PSIPA
      RETURN
      END SUBROUTINE EQFIPV
