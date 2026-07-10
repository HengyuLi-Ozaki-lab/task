!     ***********************************************************
!
!     Electric resistivity (extracted from trcoef.f90, Phase 5 step 3)
!
!     ***********************************************************

      MODULE trcoef_resistivity

      IMPLICIT NONE
      PRIVATE
      PUBLIC :: TRCFET

      CONTAINS

      SUBROUTINE TRCFET

      USE TRCOMM, ONLY : AEE, AME, BB, BP, EPS0, EPSRHO, ETA, ETANC, MDLETA, MDLTPF, MDNCLS, NRMAX, NT, PI, Q0, QP, RKEV, &
     &                   RN, RR, RT, ZEFF, rkind
      USE trlib, ONLY : COULOG
      USE trcoll, ONLY : FTAUE
      IMPLICIT NONE
      INTEGER:: NR
      REAL(rkind)   :: ANE, ANI, CH, CR, EPS, EPSS, ETAS, F33, F33TEFF, FT, FTPF, H, PHI, QL, RK33E, RLNLAME, &
     &             RNUE, RNUSE, RNZ, SGMSPTZ, TAUE, TAUEL, TE, TEL, VTE, XI, ZEFFL
      REAL(rkind):: RK33=1.83D0, RA33=0.68D0, RB33=0.32D0, RC33=0.66D0


      DO NR=1,NRMAX
         EPS=EPSRHO(NR)
         EPSS=SQRT(EPS)**3

!        ****** CLASSICAL RESISTIVITY (Spitzer) from JAERI Report ******

         ANE=RN(NR,1)
         ANI=RN(NR,2)
         TE =RT(NR,1)
         ZEFFL=ZEFF(NR)
         TAUE = FTAUE(ANE,ANI,TE,ZEFFL)

         ETA(NR) = AME/(ANE*1.D20*AEE**2*TAUE)*(0.29D0+0.46D0/(1.08D0+ZEFFL))

!        ****** NEOCLASSICAL RESISTIVITY (Hinton, Hazeltine) ******

         select case(MDLETA)
         case(1)
            IF(NR.EQ.1) THEN
               QL= 0.25D0*(3.D0*Q0+QP(NR))
            ELSE
               QL= 0.5D0*(QP(NR-1)+QP(NR))
            ENDIF
            VTE=SQRT(ABS(TE)*RKEV/AME)
            RNUE=ABS(QP(NR)*RR/(TAUE*VTE*EPSS))
            RK33E=RK33/(1.D0+RA33*SQRT(RNUE)+RB33*RNUE)/(1.D0+RC33*RNUE*EPSS)

            H      = BB/SQRT(BB**2+BP(NR)**2)
            FT     = 1.D0/H-SQRT(EPS)*RK33E
            ETA(NR)= ETA(NR)/FT

!        ****** NEOCLASSICAL RESISTIVITY (Hirshman, Hawryluk) ******

         case(2)
            IF(NR.EQ.1) THEN
               QL=ABS(0.25D0*(3.D0*Q0+QP(NR)))
            ELSE
               QL=ABS(0.5D0*(QP(NR-1)+QP(NR)))
            ENDIF
            ZEFFL=ZEFF(NR)
            VTE=SQRT(ABS(TE)*RKEV/AME)
            FT=FTPF(MDLTPF,EPS)
            TAUEL=6.D0*PI*SQRT(2.D0*PI)*EPS0**2*SQRT(AME)*(TE*RKEV)**1.5D0/(ANE*1.D20*AEE**4*COULOG(1,2,ANE,TE))
            RNUSE=RR*QL/(VTE*TAUEL*EPSS)
            PHI=FT/(1.D0+(0.58D0+0.20D0*ZEFFL)*RNUSE)
            ETAS=1.65D-9*COULOG(1,2,ANE,TE)/(ABS(TE)**1.5D0)
            CH=0.56D0*(3.D0-ZEFFL)/((3.D0+ZEFFL)*ZEFFL)

            ETA(NR)=ETAS*ZEFFL*(1.D0+0.27D0*(ZEFFL-1.D0))/((1.D0-PHI)*(1.D0-CH*PHI)*(1.D0+0.47D0*(ZEFFL-1.D0)))

!        ****** NEOCLASSICAL RESISTIVITY (Sauter)  ******

         case(3)
            IF(NR.EQ.1) THEN
               QL= 0.25D0*(3.D0*Q0+QP(NR))
            ELSE
               QL= 0.5D0*(QP(NR-1)+QP(NR))
            ENDIF
            ZEFFL=ZEFF(NR)
            rLnLame=31.3D0-LOG(SQRT(ANE*1.D20)/ABS(TE*1.D3))
            RNZ=0.58D0+0.74D0/(0.76D0+ZEFFL)
            SGMSPTZ=1.9012D4*(TE*1.D3)**1.5D0/(ZEFFL*RNZ*rLnLame)
            FT=FTPF(MDLTPF,EPS)
            RNUE=6.921D-18*ABS(QL)*RR*ANE*1.D20*ZEFFL*rLnLame /((TE*1.D3)**2*EPSS)
            F33TEFF=FT/(1.D0+(0.55D0-0.1D0*FT)*SQRT(RNUE) +0.45D0*(1.D0-FT)*RNUE/ZEFFL**1.5D0)
            ETA(NR)=1.D0/(SGMSPTZ*F33(F33TEFF,ZEFFL))

!        ****** NEOCLASSICAL RESISTIVITY (Hirshman, Sigmar)  ******

         case(4)
            IF(NR.EQ.1) THEN
               QL= 0.25D0*(3.D0*Q0+QP(NR))
            ELSE
               QL= 0.5D0*(QP(NR-1)+QP(NR))
            ENDIF
            ZEFFL=ZEFF(NR)
            ANE  =RN(NR,1)
            TEL  =ABS(RT(NR,1))

!     p1157 (7.36)
            ETAS = AME/(ANE*1.D20*AEE*AEE*TAUE)*( (1.D0+1.198D0*ZEFFL+0.222D0*ZEFFL**2) &
     &             /(1.D0+2.966D0*ZEFFL+0.753D0*ZEFFL**2))

            FT=FTPF(MDLTPF,EPS)
            XI=0.58D0+0.2D0*ZEFFL
            CR=0.56D0/ZEFFL*(3.D0-ZEFFL)/(3.D0+ZEFFL)
!     RNUE expressions is given by the paper by Hirshman, Hawryluk.
            RNUE=SQRT(2.D0)/EPSS*RR*QL/SQRT(2.D0*TEL*RKEV/AME)/TAUE
!     p1158 (7.41)
            ETA(NR)=ETAS/(1.D0-FT/(1.D0+XI*RNUE))/(1.D0-CR*FT/(1.D0+XI*RNUE))
         end select
      ENDDO

!        ****** NEOCLASSICAL RESISTIVITY BY NCLASS  ******

      IF(NT.NE.0.AND.MDNCLS.NE.0) ETA(1:NRMAX)=ETANC(1:NRMAX)

      RETURN
      END SUBROUTINE TRCFET

      END MODULE trcoef_resistivity
