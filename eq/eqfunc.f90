!     $Id$
!
! Phase F-3 (MED tier): free-form F90 conversion of eqfunc.f.
! Auxiliary profile functions: EQCNVA, EQFUNC, EQFDPP, EQPPSI,
! EQFPSI, EQQPSI, EQJPSI, EQTPSI, EQOPSI. Preserves exact numerical
! semantics of the original fixed-form source.
!
! NOTE: IMPLICIT NONE is NOT added here because the INCLUDEd shim
!       'eqcomc.inc' already supplies an IMPLICIT statement
!       (IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)) and USEs the
!       F-1 MODULEs for the COMMON symbols.
!
!   *************************************
!   *****  Argument Psi conversion  *****
!   *************************************
!
!     ---- PSIN is converted to PSIPN or PSITN ----
!
      SUBROUTINE EQCNVA(PSIPNL,PSINL)

      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom2_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN)  :: PSIPNL
      REAL*8, INTENT(OUT) :: PSINL

      IF(PSIPNL.LE.0.D0) THEN
         PSINL=0.D0
      ELSEIF(PSIPNL.GE.1.D0) THEN
         PSINL=1.D0
      ELSE
         IF(MDLEQA.EQ.0) THEN
            PSINL=PSIPNL
         ELSE
            PSINL=EQPSITN(PSIPNL)
            IF(PSINL.LE.0.D0) PSINL=0.D0
            IF(PSINL.GE.1.D0) PSINL=1.D0
         ENDIF
      ENDIF
      RETURN
      END SUBROUTINE EQCNVA
!
!   ****************************************
!   *****  Calculate Profile Function  *****
!   ****************************************
!
      SUBROUTINE EQFUNC(PSINL,F,DF,F0,FS,F1,F2,PSIITB, &
                        PROFR0,PROFR1,PROFR2,PROFF0,PROFF1,PROFF2)

      USE eqlib
      IMPLICIT REAL*8 (A-H,O-Z)
      REAL*8, INTENT(IN)  :: PSINL, F0, FS, F1, F2, PSIITB
      REAL*8, INTENT(IN)  :: PROFR0, PROFR1, PROFR2
      REAL*8, INTENT(IN)  :: PROFF0, PROFF1, PROFF2
      REAL*8, INTENT(OUT) :: F, DF

      ARG0=FPOW(PSINL,PROFR0)
      ARG1=FPOW(PSINL,PROFR1)
      F = FS &
        + (F0-FS)       *FPOW(1.D0-ARG0,PROFF0) &
        + F1            *FPOW(1.D0-ARG1,PROFF1)
      DF=-(F0-FS)*PROFF0*FPOW(1.D0-ARG0,PROFF0-1.D0) &
                 *PROFR0*FPOW(     PSINL,PROFR0-1.D0) &
         -F1     *PROFF1*FPOW(1.D0-ARG1,PROFF1-1.D0) &
                 *PROFR1*FPOW(     PSINL,PROFR1-1.D0)
      IF(PSINL.LT.PSIITB) THEN
         ARG2=FPOW(PSINL/PSIITB,PROFR2)
         F = F +F2       *FPOW(1.D0-ARG2,  PROFF2)
         DF= DF-F2*PROFF2*FPOW(1.D0-ARG2,  PROFF2-1.D0) &
                  *PROFR2*FPOW(PSINL/PSIITB,PROFR2-1.D0) &
                  /PSIITB
      ENDIF
      RETURN
      END SUBROUTINE EQFUNC
!
!   **************************************************
!   *****  Calculate factor for Psip derivative  *****
!   **************************************************
!
      SUBROUTINE EQFDPP(PSIPNL,FDN)

      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom2_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN)  :: PSIPNL
      REAL*8, INTENT(OUT) :: FDN

      IF(MDLEQA.EQ.0) THEN
         FDN=1.D0/PSIPA
      ELSE
         QPVL=EQQPV(PSIPNL)
         FDN=QPVL/PSITA
      ENDIF
      RETURN
      END SUBROUTINE EQFDPP
!
!   ************************************************
!   ** Plasma pressure                            **
!   **                  P(psin)                   **
!   ************************************************
!
      SUBROUTINE EQPPSI(PSIPNL,PPSI,DPPSI)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom2_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INCLUDE 'eqcom4.inc'
      REAL*8, INTENT(INOUT) :: PSIPNL
      REAL*8, INTENT(OUT)   :: PPSI, DPPSI

      MDLEQFL=MOD(MDLEQF,10)
      IF(MDLEQFL.LT.5) THEN
         CALL EQCNVA(PSIPNL,PSINL)
         CALL EQFUNC(PSINL,F,DF,PP0,0.D0,PP1,PP2,PSIITB, &
                     PROFR0,PROFR1,PROFR2,PROFP0,PROFP1,PROFP2)
         CALL EQFDPP(PSIPNL,FDN)
      ELSE
         IF(PSIPNL.LT.0.D0) PSIPNL=0.D0
         IF(PSIPNL.GT.1.D0) PSIPNL=1.D0
         PSITNL=EQPSITN(PSIPNL)
         CALL SPL1DD(PSITNL,F,DF,PSITRX,UPPSI,NTRMAX,IERR)
         IF(IERR.NE.0) WRITE(6,*) 'XX EQPPSI: SPL1DD : IERR=',IERR
         IF(F.LT.0.D0) F=0.D0
         QPVL=EQQPV(PSIPNL)
         FDN=QPVL/PSITA
      ENDIF

      PPSI  =      F*1.D6
      DPPSI = FDN*DF*1.D6
      RETURN
      END SUBROUTINE EQPPSI
!
!   ************************************************
!   ** Poloidal currenet                          **
!   **                  F(psin)=2*PI*B*R          **
!   ************************************************
!
      SUBROUTINE EQFPSI(PSIPNL,FPSI,DFPSI)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom2_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INCLUDE 'eqcom4.inc'
      REAL*8, INTENT(IN)  :: PSIPNL
      REAL*8, INTENT(OUT) :: FPSI, DFPSI

      MDLEQFL=MOD(MDLEQF,10)
      IF(MDLEQFL.LT.5) THEN
         CALL EQCNVA(PSIPNL,PSINL)
         FS=2.D0*PI*BB*RR
         CALL EQFUNC(PSINL,F,DF,FF0+FS,FS,FF1,FF2,PSIITB, &
                     PROFR0,PROFR1,PROFR2,PROFF0,PROFF1,PROFF2)
         CALL EQFDPP(PSIPNL,FDN)
      ELSE
         PSITNL=EQPSITN(PSIPNL)
         CALL SPL1DD(PSITNL,F,DF,PSITRX,UFPSI,NTRMAX,IERR)
         IF(IERR.NE.0) WRITE(6,*) 'XX EQFPSI: SPL1DD : IERR=',IERR
         QPVL=EQQPV(PSIPNL)
         FDN=QPVL/PSITA
      ENDIF

      FPSI  =      F
      DFPSI = FDN*DF
      RETURN
      END SUBROUTINE EQFPSI
!
!   ************************************************
!   ** Safety factor                              **
!   **                 Q(psin)                    **
!   ************************************************
!
      SUBROUTINE EQQPSI(PSIPNL,QPSI)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom2_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INCLUDE 'eqcom4.inc'
      REAL*8, INTENT(IN)  :: PSIPNL
      REAL*8, INTENT(OUT) :: QPSI

      MDLEQFL=MOD(MDLEQF,10)
      IF(MDLEQFL.LT.5) THEN
         PSITNL=EQPSITN(PSIPNL)
         QPSI=Q0+(QA-Q0)*PSITNL
      ELSE
         PSITNL=EQPSITN(PSIPNL)
         CALL SPL1DD(PSITNL,F,DF,PSITRX,UQPSI,NTRMAX,IERR)
         IF(IERR.NE.0) WRITE(6,*) 'XX EQQPSI: SPL1DD : IERR=',IERR
         QPSI  =      F
      ENDIF
      RETURN
      END SUBROUTINE EQQPSI
!
!   ************************************************
!   ** Plasma current density                     **
!   **                  J(psin)                   **
!   ************************************************
!
      SUBROUTINE EQJPSI(PSIPNL,HJPSID,HJPSI)

      USE eqlib
      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom2_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INCLUDE 'eqcom4.inc'
      REAL*8, INTENT(IN)  :: PSIPNL
      REAL*8, INTENT(OUT) :: HJPSID, HJPSI

      MDLEQFL=MOD(MDLEQF,10)
      IF(MDLEQFL.LT.5) THEN
         CALL EQCNVA(PSIPNL,PSINL)
         ARG0=FPOW(PSINL,PROFR0)
         ARG1=FPOW(PSINL,PROFR1)
         ARG2=FPOW(PSINL,PROFR2)
         FD=-PJ0*FPOW(1.D0-ARG0,PROFJ0+1.D0) &
                      /(PROFR0*(PROFJ0+1.D0)) &
            -PJ1*FPOW(1.D0-ARG1,PROFJ1+1.D0) &
                      /(PROFR1*(PROFJ1+1.D0)) &
            -PJ2*FPOW(1.D0-ARG2,PROFJ2+1.D0) &
                      /(PROFR2*(PROFJ2+1.D0))
         F = PJ0*FPOW(1.D0-ARG0,PROFJ0) &
                *FPOW(PSINL,PROFR0-1.D0) &
            +PJ1*FPOW(1.D0-ARG1,PROFJ1) &
                *FPOW(PSINL,PROFR1-1.D0) &
            +PJ2*FPOW(1.D0-ARG2,PROFJ2) &
                *FPOW(PSINL,PROFR2-1.D0)
         FD=FD*1.D6
         F =F *1.D6
         CALL EQFDPP(PSIPNL,FDN)
      ELSE
         PSITNL=EQPSITN(PSIPNL)
         CALL SPL1DI(PSITNL,FD,PSITRX,UJPSI,UJPSI0,NTRMAX,IERR)
         IF(IERR.NE.0) WRITE(6,*) 'XX EQJPSI: SPL1DI : IERR=',IERR
         CALL SPL1DF(PSITNL,F,PSITRX,UJPSI,NTRMAX,IERR)
         IF(IERR.NE.0) WRITE(6,*) 'XX EQJPSI: SPL1DF : IERR=',IERR
         QPVL=EQQPV(PSIPNL)
         FDN=QPVL/PSITA
      ENDIF

      HJPSID= FD/FDN
      HJPSI =  F
!      WRITE(6,'(1P4E12.4)') PSIPNL,PSINL,HJPSI,HJPSID
      RETURN
      END SUBROUTINE EQJPSI
!
!   ************************************************
!   ** Plasma tempertature                        **
!   **                  T(psin)                   **
!   ************************************************
!
      SUBROUTINE EQTPSI(PSIPNL,TPSI,DTPSI)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom2_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INCLUDE 'eqcom4.inc'
      REAL*8, INTENT(IN)  :: PSIPNL
      REAL*8, INTENT(OUT) :: TPSI, DTPSI

      MDLEQFL=MOD(MDLEQF,10)
      IF(MDLEQFL.LT.5) THEN
         CALL EQCNVA(PSIPNL,PSINL)
         CALL EQFUNC(PSINL,F,DF,PT0,PTSEQ,PT1,PT2,PSIITB, &
                     PROFR0,PROFR1,PROFR2,PROFTP0,PROFTP1,PROFTP2)
         CALL EQFDPP(PSIPNL,FDN)
      ELSE
         PSITNL=EQPSITN(PSIPNL)
         CALL SPL1DD(PSITNL,F,DF,PSITRX,UTPSI,NTRMAX,IERR)
         IF(IERR.NE.0) WRITE(6,*) 'XX EQTPSI: SPL1DD : IERR=',IERR
         QPVL=EQQPV(PSIPNL)
         FDN=QPVL/PSITA
      ENDIF

      TPSI=      F*1.D3*AEE
      DTPSI=FDN*DF*1.D3*AEE
      RETURN
      END SUBROUTINE EQTPSI
!
!   ************************************************
!   ** Toroidal rotation angular velocisty        **
!   **               OPSI(psin)                   **
!   ************************************************
!
      SUBROUTINE EQOPSI(PSIPNL,OMGPSI,DOMGPSI)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom2_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INCLUDE 'eqcom4.inc'
      REAL*8, INTENT(IN)  :: PSIPNL
      REAL*8, INTENT(OUT) :: OMGPSI, DOMGPSI

      MDLEQFL=MOD(MDLEQF,10)
      IF(MDLEQFL.LT.5) THEN
         CALL EQCNVA(PSIPNL,PSINL)
         CALL EQFUNC(PSINL,F,DF,PV0,0.D0,PV1,PV2,PSIITB, &
                     PROFR0,PROFR1,PROFR2,PROFV0,PROFV1,PROFV2)
         CALL EQFDPP(PSIPNL,FDN)
      ELSE
         PSITNL=EQPSITN(PSIPNL)
         CALL SPL1DD(PSITNL,F,DF,PSITRX,UVTPSI,NTRMAX,IERR)
         IF(IERR.NE.0) WRITE(6,*) 'XX EQOPSI: SPL1DD : IERR=',IERR
         QPVL=EQQPV(PSIPNL)
         FDN=QPVL/PSITA
      ENDIF

      OMGPSI=      F/RAXIS
      DOMGPSI=FDN*DF/RAXIS
      RETURN
      END SUBROUTINE EQOPSI
