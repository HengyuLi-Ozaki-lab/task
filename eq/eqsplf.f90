!     $Id$
!
! Phase F-4 (HIGH tier): free-form F90 conversion of eqsplf.f.
! Spline-evaluation helper functions (FNPSIN/FNRHON/FNPSIPT/FNPSIP/...)
! that interpolate flux-surface quantities cached in eqcom3 via the
! eqcomq.inc shim. Preserves exact numerical semantics of the original
! fixed-form source.
!
! NOTE: IMPLICIT NONE is NOT added here because the INCLUDEd shim
!       '../eq/eqcomq.inc' already supplies an IMPLICIT statement
!       (IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)) and USEs the
!       F-1 MODULEs (eqcom0/1/3_mod) for the COMMON symbols.
!
!     ***** INTERPOLATE FUNCTIONS *****
!
!     FNPSIN: evaluate normalized poloidal flux funcion (PSIN=psip/psipa)
!             corresponding to RHON (i.e. PSIN(RHON))
!
      FUNCTION FNPSIN(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      PSITL=PSITA*RHON*RHON
      CALL SPL1DF(PSITL,PSIPL,PSIT,UPSIP,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNPSIN: SPL1DF ERROR : IERR=',IERR
      FNPSIN=PSIPL/PSIPA
      RETURN
      END
!
!     FNRHON: evaluate rho corresponding to normalized psi, PSIN
!             (i.e. rho(PSIN))
!
      FUNCTION FNRHON(PSIN)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: PSIN

      IF(PSIN.LT.0.D0) THEN
         PSIPL=PSIPA*PSIN
         CALL SPL1DF(PSIPL,PSITL,PSIP,UPSIT,NRMAX,IERR)
         IF(IERR.NE.0) &
              WRITE(6,*) 'XX FNRHON: SPL1DF ERROR : IERR=',IERR
         IF(PSITL.LE.0.D0) THEN
            FNRHON=0.D0
         ELSE
            FNRHON=SQRT(PSITL/PSITA)
         ENDIF
      ELSE
         FNRHON=SQRT(PSIN)
      ENDIF
      RETURN
      END
!
!     FNPSIPT: evaluate PSIP corresponding to toroidal flux function
!            (PSIT) (i.e. PSIP(PSIT))
!
      FUNCTION FNPSIPT(PSITL1)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: PSITL1

      PSITL=PSITL1
      IF(PSITL.LT.PSIT(1))     PSITL=PSIT(1)
      IF(PSITL.GT.PSIT(NRMAX)) PSITL=PSIT(NRMAX)
      CALL SPL1DF(PSITL,PSIPL,PSIT,UPSIP,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNPSIPT: SPL1DF ERROR : IERR=',IERR
      FNPSIPT=PSIPL
      RETURN
      END
!
!     FNPSIP: evaluate PSI corresponding to RHON (i.e. psi(RHON))
!
      FUNCTION FNPSIP(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      PSITL=PSITA*RHON*RHON
      IF(PSITL.LT.PSIT(1))     PSITL=PSIT(1)
      IF(PSITL.GT.PSIT(NRMAX)) PSITL=PSIT(NRMAX)
      CALL SPL1DF(PSITL,PSIPL,PSIT,UPSIP,NRMAX,IERR)
      IF(IERR.NE.0) THEN
         WRITE(6,*) 'XX FNPSIP: SPL1DF ERROR : IERR=',IERR
         WRITE(6,'(A,1P3E12.4)') 'PSIT:',PSITL,PSIT(1),PSIT(NRMAX)
         WRITE(6,'(A,1P2E12.4)') 'PSITAB:',PSITA,PSITB
      ENDIF
      FNPSIP=PSIPL
      RETURN
      END
!
!     FNPSIP: evaluate PSIP-derivative corresponding to RHON (i.e. dpsi/dRHON)
!
      FUNCTION FNDPSIP(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      PSITL=PSITA*RHON*RHON
      IF(PSITL.LT.PSIT(1))     PSITL=PSIT(1)
      IF(PSITL.GT.PSIT(NRMAX)) PSITL=PSIT(NRMAX)
      CALL SPL1DD(PSITL,PSIPL,DPSIPL,PSIT,UPSIP,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNPSIN: SPL1DF ERROR : IERR=',IERR
      FNDPSIP=2.D0*PSITA*RHON*DPSIPL
      RETURN
      END
!
!     FNPSIT: evaluate PSIT corresponding to RHON (i.e. PSIT(RHON))
!
      FUNCTION FNPSIT(RHON)

      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      FNPSIT=PSITA*RHON*RHON
      RETURN
      END
!
!     ************************************************************************
!
!     FNPPS: evaluate PPS corresponding to RHON (i.e. PPS(RHON))
!
      FUNCTION FNPPS(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),PPL,PSIP,UPPS,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNPPS: SPL1DF ERROR : IERR=',IERR
      FNPPS=PPL
      RETURN
      END
!
!     FNTTS: evaluate TTS corresponding to RHON (i.e. TTS(RHON))
!
      FUNCTION FNTTS(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      IF(RHON.LT.1.D0) THEN
         CALL SPL1DF(FNPSIP(RHON),TTL,PSIP,UTTS,NRMAX,IERR)
         IF(IERR.NE.0) WRITE(6,*) 'XX FNTTS: SPL1DF ERROR : IERR=',IERR
         FNTTS=TTL
      ELSE
         FNTTS=2.D0*PI*BB*RR
      ENDIF
      RETURN
      END
!
!     FNQPS: evaluate QPS corresponding to RHON (i.e. QPS(RHON))
!
      FUNCTION FNQPS(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      PSIPL=FNPSIP(RHON)
      CALL SPL1DF(PSIPL,QPL,PSIP,UQPS,NRMAX,IERR)
      IF(IERR.NE.0) THEN
         WRITE(6,*) 'XX FNQPS: SPL1DF ERROR : IERR=',IERR
         WRITE(6,'(A,1PE12.4)') 'RHON:',RHON
         WRITE(6,'(A,1P3E12.4)') 'PSIP:',PSIPL,PSIP(1),PSIP(NRMAX)
      ENDIF
      FNQPS=QPL
      RETURN
      END
!
!     FNVPS: evaluate VPS corresponding to RHON (i.e. VPS(RHON))
!
      FUNCTION FNVPS(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),VPL,PSIP,UVPS,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNVPS: SPL1DF ERROR : IERR=',IERR
      FNVPS=VPL
      RETURN
      END
!
!     FNSPS: evaluate SPS corresponding to RHON (i.e. SPS(RHON))
!
      FUNCTION FNSPS(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),SPL,PSIP,USPS,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNSPS: SPL1DF ERROR : IERR=',IERR
      FNSPS=SPL
      RETURN
      END
!
!     FNRLEN: evaluate RLEN corresponding to RHON (i.e. RLEN(RHON))
!
      FUNCTION FNRLEN(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),RLENL,PSIP,URLEN,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNRLEN: SPL1DF ERROR : IERR=',IERR
      FNRLEN=RLENL
      RETURN
      END
!
!     FNRRMN: evaluate RRMIN corresponding to RHON (i.e. RRMIN(RHON))
!
      FUNCTION FNRRMN(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),RRMINL,PSIP,URRMIN,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNRRMN: SPL1DF ERROR : IERR=',IERR
      FNRRMN=RRMINL
      RETURN
      END
!
!     FNRRMX: evaluate RRMAX corresponding to RHON (i.e. RRMAX(RHON))
!
      FUNCTION FNRRMX(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),RRMAXL,PSIP,URRMAX,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNRRMX: SPL1DF ERROR : IERR=',IERR
      FNRRMX=RRMAXL
      RETURN
      END
!
!     FNZZMN: evaluate ZZMIN corresponding to RHON (i.e. ZZMIN(RHON))
!
      FUNCTION FNZZMN(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),ZZMINL,PSIP,UZZMIN,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNRRMN: SPL1DF ERROR : IERR=',IERR
      FNZZMN=ZZMINL
      RETURN
      END
!
!     FNZZMX: evaluate ZZMAX corresponding to RHON (i.e. ZZMAX(RHON))
!
      FUNCTION FNZZMX(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),ZZMAXL,PSIP,UZZMAX,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNRRMX: SPL1DF ERROR : IERR=',IERR
      FNZZMX=ZZMAXL
      RETURN
      END
!
!     FNBBMN: evaluate BBMIN corresponding to RHON (i.e. BBMIN(RHON))
!
      FUNCTION FNBBMN(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),BBMINL,PSIP,UBBMIN,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNBBMN: SPL1DF ERROR : IERR=',IERR
      FNBBMN=BBMINL
      RETURN
      END
!
!     FNBBMX: evaluate BBMAX corresponding to RHON (i.e. BBMAX(RHON))
!
      FUNCTION FNBBMX(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),BBMAXL,PSIP,UBBMAX,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNBBMX: SPL1DF ERROR : IERR=',IERR
      FNBBMX=BBMAXL
      RETURN
      END
!
!     FNAVRR2: evaluate AVERR2 corresponding to RHON (i.e. AVERR2(RHON))
!
      FUNCTION FNAVRR2(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,UAVERR2,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNAVRR2: SPL1DF ERROR : IERR=',IERR
      FNAVRR2=DAT
      RETURN
      END
!
!     FNAVIR2: evaluate AVEIR2 corresponding to RHON (i.e. AVEIR2(RHON))
!
      FUNCTION FNAVIR2(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,UAVEIR2,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNAVIR2: SPL1DF ERROR : IERR=',IERR
      FNAVIR2=DAT
      RETURN
      END
!
!     FNAVBB2: evaluate AVEBB2 corresponding to RHON (i.e. AVEBB2(RHON))
!
      FUNCTION FNAVBB2(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,UAVEBB2,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNAVBB2: SPL1DF ERROR : IERR=',IERR
      FNAVBB2=DAT
      RETURN
      END
!
!     FNAVIB2: evaluate AVEIB2 corresponding to RHON (i.e. AVEIB2(RHON))
!
      FUNCTION FNAVIB2(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,UAVEIB2,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNAVIB2: SPL1DF ERROR : IERR=',IERR
      FNAVIB2=DAT
      RETURN
      END
!
!     FNAVBB: evaluate AVEBB corresponding to RHON (i.e. AVEBB(RHON))
!
      FUNCTION FNAVBB(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,UAVEBB,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNAVBB: SPL1DF ERROR : IERR=',IERR
      FNAVBB=DAT
      RETURN
      END
!
!     FNAVGV: evaluate AVEGV corresponding to RHON (i.e. AVEGV(RHON))
!
      FUNCTION FNAVGV(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,UAVEGV,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNAVGV: SPL1DF ERROR : IERR=',IERR
      FNAVGV=DAT
      RETURN
      END
!
!     FNAVGV2: evaluate AVEGV2 corresponding to RHON (i.e. AVEGV2(RHON))
!
      FUNCTION FNAVGV2(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,UAVEGV2,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNAVGV2: SPL1DF ERROR : IERR=',IERR
      FNAVGV2=DAT
      RETURN
      END
!
!     FNAVGR2: evaluate AVEGVR2 corresponding to RHON (i.e. AVEGVR2(RHON))
!
      FUNCTION FNAVGVR2(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,UAVEGVR2,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNAVGVR2: SPL1DF ERROR : IERR=',IERR
      FNAVGVR2=DAT
      RETURN
      END
!
!     FNAVGP2: evaluate AVEGP2 corresponding to RHON (i.e. AVEGP2(RHON))
!
      FUNCTION FNAVGP2(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,UAVEGP2,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNAVGP2: SPL1DF ERROR : IERR=',IERR
      FNAVGP2=DAT
      RETURN
      END
!
!     FNRRPS: evaluate RRPSI corresponding to RHON (i.e. RRPSI(RHON))
!
      FUNCTION FNRRPS(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,URRPSI,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNRRPS: SPL1DF ERROR : IERR=',IERR
      FNRRPS=DAT
      RETURN
      END
!
!     FNRSPS: evaluate RSPSI corresponding to RHON (i.e. RSPSI(RHON))
!
      FUNCTION FNRSPS(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,URSPSI,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNRSPS: SPL1DF ERROR : IERR=',IERR
      FNRSPS=DAT
      RETURN
      END
!
!     FNELPPS: evaluate ELIPPSI corresponding to RHON (i.e. ELIPPSI(RHON))
!
      FUNCTION FNELPPS(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,UELIPPSI,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNELPPS: SPL1DF ERROR : IERR=',IERR
      FNELPPS=DAT
      RETURN
      END
!
!     FNTRGPS: evaluate TRIGPSI corresponding to RHON (i.e. TRIGPSI(RHON))
!
      FUNCTION FNTRGPS(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,UTRIGPSI,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNTRGPS: SPL1DF ERROR : IERR=',IERR
      FNTRGPS=DAT
      RETURN
      END
!
!     FNDVDPSP: evaluate DVDPSIP corresponding to RHON (i.e. DVDPSIP(RHON))
!
      FUNCTION FNDVDPSP(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,UDVDPSIP,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNDVDPSP: SPL1DF ERROR : IERR=',IERR
      FNDVDPSP=DAT
      RETURN
      END
!
!     FNDVDPST: evaluate DVDPSIT corresponding to RHON (i.e. DVDPSIT(RHON))
!
      FUNCTION FNDVDPST(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,UDVDPSIT,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNDVDPST: SPL1DF ERROR : IERR=',IERR
      FNDVDPST=DAT
      RETURN
      END
!
!     FNAVGR: evaluate AVEGR corresponding to RHON (i.e. AVEGR(RHON))
!
      FUNCTION FNAVGR(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,UAVEGR,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNAVGR: SPL1DF ERROR : IERR=',IERR
      FNAVGR=DAT
      RETURN
      END
!
!     FNAVGR2: evaluate AVEGR2 corresponding to RHON (i.e. AVEGR2(RHON))
!
      FUNCTION FNAVGR2(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,UAVEGR2,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNAVGR2: SPL1DF ERROR : IERR=',IERR
      FNAVGR2=DAT
      RETURN
      END
!
!     FNAVGRR2: evaluate AVEGVRR2 corresponding to RHON (i.e. AVEGVRR2(RHON))
!
      FUNCTION FNAVGRR2(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,UAVEGRR2,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNAVGRR2: SPL1DF ERROR : IERR=',IERR
      FNAVGRR2=DAT
      RETURN
      END
!
!     FNAVIR2: evaluate AVEIR corresponding to RHON (i.e. AVEIR(RHON))
!
      FUNCTION FNAVIR(RHON)

      USE libspl1d
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: RHON

      CALL SPL1DF(FNPSIP(RHON),DAT,PSIP,UAVEIR,NRMAX,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX FNAVIR: SPL1DF ERROR : IERR=',IERR
      FNAVIR=DAT
      RETURN
      END
