!     ***********************************************************
!
!     Ad-hoc transport coefficient closure (extracted from trcoef.f90, Phase 5 step 4)
!
!     ***********************************************************

      MODULE trcoef_adhoc

      IMPLICIT NONE
      PRIVATE
      PUBLIC :: TRCFAD

      CONTAINS

      SUBROUTINE TRCFAD

      USE TRCOMM, ONLY : AD, AD0, ADDW, ADDWD, ADDWP, ADLD, ADLP, ADNC, ADNCP, ADNCT, AEE, AKDW, ALP, AME, AMM, AV, AV0,    &
     &                   AVDW, AVK, AVKDW, AVKNC, AVNC, BB, BP, CDH, CDP, CHP, CNH, CNN, CNP, CSPRS, EPSRHO, EZOH, MDDIAG,  &
     &                   MDDW, MDEDGE, MDLAD, MDLAVK, MDNCLS, NREDGE, NRMAX, NSLMAX, NSM, PA, PN, PNSS, PROFN1, PROFN2, PTS,&
     &                   PZ, QP, RA, RHOG, RKEV, RN, RM, RR, RT, ZEFF, rkind
      IMPLICIT NONE
      INTEGER:: NR, NS, NS1, NA, NB
      REAL(rkind)   :: ANA, ANDX, ANE, ANED, ANI, ANT, BPL, CFNCI, CFNCNC, CFNCNH, CFNHI, CFNHNC, CFNHNH, DPROF, EDCM, EPS, EPSS,&
     &             EZOHL, FTAUE, FTAUI, H, PROF, PROF0, PROF1, PROF2, QPL, RHOE2, RK11E, RK13E, RK23E, RK3D, RNUD, RNUE, RX, &
     &             SGMNI, SGMNN, SUMA, SUMB, TAUD, TAUE, TD, TE, VNC, VNH, VNI, VTD, VTE, ZEFFL
      REAL(rkind),DIMENSION(2):: ACOEF
      REAL(rkind),DIMENSION(5):: BCOEF
      REAL(rkind) :: RK11=1.04D0, RA11=2.01D0, RB11=1.53D0, RC11=0.89D0
      REAL(rkind) :: RK13=2.30D0, RA13=1.02D0, RB13=1.07D0, RC13=1.07D0
      REAL(rkind) :: RK23=4.19D0, RA23=0.57D0, RB23=0.61D0, RC23=0.61D0
      REAL(rkind),SAVE :: CDPSV

!     ZEFF=1

!        ****** AD : PARTICLE DIFFUSION ******
!        ****** AV : PARTICLE PINCH ******

      IF(MDEDGE.EQ.1) CDPSV=CDP
      DO NR=1,NRMAX
         AVDW(NR,1:NSM) = 0.D0
         ADDW(NR,1:NSM) = 0.D0
      END DO

      IF(MDNCLS.EQ.0) THEN
      select case(MDLAD)
      case(1)
         DO NR=1,NRMAX
            IF(NR.EQ.NRMAX) THEN
               ANE =PNSS(1)
               ANDX=PNSS(2)
               ANT =PNSS(3)
               ANA =PNSS(4)
            ELSE
               ANE    = 0.5D0*(RN(NR+1,1)+RN(NR  ,1))
               ANDX   = 0.5D0*(RN(NR+1,2)+RN(NR  ,2))
               ANT    = 0.5D0*(RN(NR+1,3)+RN(NR  ,3))
               ANA    = 0.5D0*(RN(NR+1,4)+RN(NR  ,4))
            ENDIF
            ADDW(NR,2) = PA(2)**ALP(2)*PZ(2)**ALP(3)*AD0*ALP(4)
            ADDW(NR,3) = PA(3)**ALP(2)*PZ(3)**ALP(3)*AD0*ALP(5)
            ADDW(NR,4) = PA(4)**ALP(2)*PZ(4)**ALP(3)*AD0*ALP(6)
            ADDW(NR,1) =(PZ(2)*ANDX*ADDW(NR,2) &
                        +PZ(3)*ANT *ADDW(NR,3) &
                        +PZ(4)*ANA *ADDW(NR,4))/(ANDX+ANT+ANA)

!    ALP(4)~ALP(6) is arbitrary coef for deuterium,tritium,helium, respectively
!            RX   = ALP(1)*RHOG(NR)
!            PROF0 = 1.D0-RX**PROFN1
!            IF(PROF0.LE.0.D0) THEN
!               PROF1=0.D0
!               PROF2=0.D0
!            ELSE
!               PROF1=PROF0**PROFN2
!               PROF2=PROFN2*PROF0**(PROFN2-1.D0)
!            ENDIF
!            PROF   = PROF1+PNSS(1)/(PN(1)-PNSS(1))
!            DPROF  =-PROFN1*RX**(PROFN1-1.D0)*PROF2

            AVDW(NR,1:NSM) = -AV0*(RHOG(NR)/RA)*ADDW(NR,1:NSM)
         ENDDO
      case(2)
         DO NR=1,NRMAX
            IF(NR.EQ.NRMAX) THEN
               ANE =PNSS(1)
               ANDX=PNSS(2)
               ANT =PNSS(3)
               ANA =PNSS(4)
            ELSE
               ANE = 0.5D0*(RN(NR+1,1)+RN(NR  ,1))
               ANDX= 0.5D0*(RN(NR+1,2)+RN(NR  ,2))
               ANT = 0.5D0*(RN(NR+1,3)+RN(NR  ,3))
               ANA = 0.5D0*(RN(NR+1,4)+RN(NR  ,4))
            ENDIF
            ADDW(NR,2) = AD0*AKDW(NR,2)*ALP(4)
            ADDW(NR,3) = AD0*AKDW(NR,3)*ALP(5)
            ADDW(NR,4) = AD0*AKDW(NR,4)*ALP(6)
            ADDW(NR,1) =(PZ(2)*ANDX*ADDW(NR,2) &
                        +PZ(3)*ANT *ADDW(NR,3) &
                        +PZ(4)*ANA *ADDW(NR,4))/(ANDX+ANT+ANA)

!            RX   = ALP(1)*RHOG(NR)
!            PROF0 = 1.D0-RX**PROFN1
!            IF(PROF0.LE.0.D0) THEN
!               PROF1=0.D0
!               PROF2=0.D0
!            ELSE
!               PROF1=PROF0**PROFN2
!               PROF2=PROFN2*PROF0**(PROFN2-1.D0)
!            ENDIF
!            PROF   = PROF1*(PN(1)-PNSS(1))+PNSS(1)
!            DPROF  = -PROFN1*RX**(PROFN1-1.D0)*PROF2*(PN(1) &
!                     -PNSS(1))*ALP(1)/RA *1.5D0

            AVDW(NR,1:NSM) = -AV0*(RHOG(NR)/RA)*ADDW(NR,1:NSM)
         ENDDO
      case(3)
!     *** Hinton & Hazeltine model w/o anomalous part of ***
!     *** transport effect of heat pinch ***
         DO NR=1,NRMAX
            IF(NR.EQ.NRMAX) THEN
               ANE = PNSS(1)
               ANI = PNSS(2)
               TE  = PTS(1)
            ELSE
               ANE = 0.5D0*(RN(NR+1,1)+RN(NR  ,1))
               ANI = 0.5D0*(RN(NR+1,2)+RN(NR  ,2))
               TE  = 0.5D0*(RT(NR+1,1)+RT(NR  ,1))
            ENDIF

            IF(MDDW.EQ.0) ADDW(NR,1:NSM) = AD0*AKDW(NR,1:NSM)

            ZEFFL = ZEFF(NR)
            BPL   = BP(NR)
            QPL   = QP(NR)
            IF(QPL.GT.100.D0) QPL=100.D0
            EZOHL = EZOH(NR)
            EPS   = EPSRHO(NR)
            EPSS  = SQRT(EPS)**3
            VTE   = SQRT(TE*RKEV/AME)
            TAUE  = FTAUE(ANE,ANI,TE,ZEFFL)
            RNUE  = ABS(QPL)*RR/(TAUE*VTE*EPSS)
            RHOE2 = 2.D0*AME*TE*RKEV/(PZ(1)*AEE*BPL)**2

            RK13E = RK13/(1.D0+RA13*SQRT(RNUE)+RB13*RNUE)/(1.D0+RC13*RNUE*EPSS)

            H     = BB/SQRT(BB**2+BPL**2)

            RK11E=RK11*(1.D0/(1.D0+RA11*SQRT(RNUE)+RB11*RNUE)+(EPSS*RC11)**2/RB11*RNUE/(1.D0+RC11*RNUE*EPSS))

            IF(MDEDGE.EQ.1.AND.NR.GE.NREDGE) CDP=CSPRS
            AVNC(NR,1:NSM) = -(RK13E*SQRT(EPS)*EZOHL)/BPL/H
            ADNC(NR,1:NSM) = SQRT(EPS)*RHOE2/TAUE*RK11E
            AD  (NR,1:NSM) = CDP*ADDW(NR,1:NSM)+CNP*ADNC(NR,1:NSM)
            AVDW(NR,1:NSM) = 0.D0

         ENDDO
      case(4)
!     *** Hinton & Hazeltine model with anomalous part of ***
!     *** transport effect of heat pinch ***
         DO NR=1,NRMAX
            IF(NR.EQ.NRMAX) THEN
               ANE = PNSS(1)
               ANI = PNSS(2)
               TE  = PTS(1)
            ELSE
               ANE = 0.5D0*(RN(NR+1,1)+RN(NR  ,1))
               ANI = 0.5D0*(RN(NR+1,2)+RN(NR  ,2))
               TE  = 0.5D0*(RT(NR+1,1)+RT(NR  ,1))
            ENDIF

            IF(MDDW.EQ.0) ADDW(NR,1:NSM) = AD0*AKDW(NR,1:NSM)

            ZEFFL = ZEFF(NR)
            BPL   = BP(NR)
            QPL   = QP(NR)
            IF(QPL.GT.100.D0) QPL=100.D0
            EZOHL = EZOH(NR)
            EPS   = EPSRHO(NR)
            EPSS  = SQRT(EPS)**3
            VTE   = SQRT(TE*RKEV/AME)
            TAUE  = FTAUE(ANE,ANI,TE,ZEFFL)
            RNUE  = ABS(QPL)*RR/(TAUE*VTE*EPSS)
            RHOE2 = 2.D0*AME*TE*RKEV/(PZ(1)*AEE*BPL)**2

            RK13E = RK13/(1.D0+RA13*SQRT(RNUE)+RB13*RNUE)/(1.D0+RC13*RNUE*EPSS)

            H     = BB/SQRT(BB**2+BPL**2)

            RK11E=RK11*(1.D0/(1.D0+RA11*SQRT(RNUE)+RB11*RNUE)+(EPSS*RC11)**2/RB11*RNUE/(1.D0+RC11*RNUE*EPSS))

            IF(MDEDGE.EQ.1.AND.NR.GE.NREDGE) CDP=CSPRS
            AVNC(NR,1:NSM) =-(RK13E*SQRT(EPS)*EZOHL)/BPL/H
            ADNC(NR,1:NSM) = SQRT(EPS)*RHOE2/TAUE*RK11E
            AVDW(NR,1:NSM) =-AV0*ADDW(NR,1:NSM)*RHOG(NR)/RA
         ENDDO
!!$      case(5)
!!$         ADNC(1:NRMAX,1:NSM)=0.D0
!!$         ADDW(1:NRMAX,1:NSM)=0.D0
!!$         DO NS=1,NSM
!!$            DO NR=1,NRMAX
!!$               AVNC(NR,NS)=RG(NR)*(RG(NR)-1.D0)
!!$            END DO
!!$         END DO
!!$         AVDW(1:NRMAX,1:NSM)=0.D0
      case default
         IF(MDLAD.NE.0) WRITE(6,*) 'XX INVALID MDLAD : ',MDLAD
         AD  (1:NRMAX,1:NSM)=0.D0
         AV  (1:NRMAX,1:NSM)=0.D0
         ADNC(1:NRMAX,1:NSM)=0.D0
         AVNC(1:NRMAX,1:NSM)=0.D0
         AVDW(1:NRMAX,1:NSM)=0.D0
      end select
      ENDIF
      IF(MDEDGE.EQ.1) CDP=CDPSV

!     ***** NET PARTICLE PINCH *****

      DO NS=1,NSLMAX
         DO NR=1,NRMAX
            IF(MDEDGE.EQ.1.AND.NR.GE.NREDGE) CDP=CSPRS
            AD(NR,NS)=CNP*ADNC(NR,NS)+CDP*ADDW(NR,NS)
            AV(NR,NS)=CNP*AVNC(NR,NS)+CDP*AVDW(NR,NS)
         ENDDO
      ENDDO
      IF(MDEDGE.EQ.1) CDP=CDPSV

!     ***** OFF-DIAGONAL TRANSPORT COEFFICIENTS *****

!     ADLP : particle flux coefficient for pressure gradient
!     ADLD : particle flux coefficient for density gradient

      select case(MDDIAG)
      case(1)
         DO NR=1,NRMAX
            IF(MDEDGE.EQ.1.AND.NR.GE.NREDGE) CDP=CSPRS
            DO NS=1,NSLMAX
               IF(MDDW.EQ.0) ADDW(NR,NS) = AD0*AKDW(NR,NS)
               DO NS1=1,NSLMAX
                  IF(NS.EQ.NS1) THEN
                     ADLD(NR,NS,NS1)= CDP*  ADDW(NR,NS) +CNP*(-ADNCT(NR,NS,NS1))
                     ADLP(NR,NS,NS1)= CNP*( ADNCT(NR,NS,NS1)+ADNCP(NR,NS,NS1))
                  ELSE
                     ADLD(NR,NS,NS1)= CNP*(-ADNCT(NR,NS,NS1))
                     ADLP(NR,NS,NS1)= CNP*( ADNCT(NR,NS,NS1)+ADNCP(NR,NS,NS1))
                  ENDIF
               ENDDO
            ENDDO
         ENDDO
      case(2)
         DO NR=1,NRMAX
            IF(MDEDGE.EQ.1.AND.NR.GE.NREDGE) CDP=CSPRS
            DO NS=1,NSLMAX
               DO NS1=1,NSLMAX
                  IF(NS.EQ.NS1) THEN
                     ADLD(NR,NS,NS1)= CDP*ADDWD(NR,NS,NS1)+CNP*ADNC(NR,NS)
                     ADLP(NR,NS,NS1)= CDP*ADDWP(NR,NS,NS1)
                  ELSE
                     ADLD(NR,NS,NS1)= CDP*ADDWD(NR,NS,NS1)
                     ADLP(NR,NS,NS1)= CDP*ADDWP(NR,NS,NS1)
                  ENDIF
               ENDDO
            ENDDO
         ENDDO
      case(3)
         DO NR=1,NRMAX
            IF(MDEDGE.EQ.1.AND.NR.GE.NREDGE) CDP=CSPRS
            DO NS=1,NSLMAX
               DO NS1=1,NSLMAX
                  ADLD(NR,NS,NS1)= CDP*ADDWD(NR,NS,NS1)+CNP*(-ADNCT(NR,NS,NS1))
                  ADLP(NR,NS,NS1)= CDP*ADDWP(NR,NS,NS1)+CNP*( ADNCT(NR,NS,NS1) +ADNCP(NR,NS,NS1))
               ENDDO
            ENDDO
         ENDDO
      end select
      IF(MDEDGE.EQ.1) CDP=CDPSV

!     /* for nuetral deuterium */

      ACOEF(1)=-3.231141D+1
      ACOEF(2)=-1.386002D-1
      BCOEF(1)=-3.330843D+1
      BCOEF(2)=-5.738374D-1
      BCOEF(3)=-1.028610D-1
      BCOEF(4)=-3.920980D-3
      BCOEF(5)= 5.964135D-4
      DO NR=1,NRMAX
         SUMA=0.D0
         SUMB=0.D0
         EDCM=0.5D0*(1.5D0*RT(NR,2)*1.D3)
         DO NA=1,2
            SUMA=SUMA+ACOEF(NA)*(LOG(4.D0*EDCM))**(NA-1)
         ENDDO
         DO NB=1,5
            SUMB=SUMB+BCOEF(NB)*(LOG(4.D0*EDCM))**(NB-1)
         ENDDO
         SGMNI=2.D0*EXP(SUMA)*1.D-4
         SGMNN=2.D0*EXP(SUMB)*1.D-4

         VNI=SQRT(RT(NR,2)*RKEV/(PA(2)*AMM))
         VNC=SQRT(0.025D-3*RKEV/(PA(7)*AMM))
         VNH=SQRT(RT(NR,2)*RKEV/(PA(8)*AMM))
         CFNCI =RN(NR,2)*1.D20*SGMNI*VNI
         CFNCNC=RN(NR,7)*1.D20*SGMNN*VNC
         CFNCNH=RN(NR,8)*1.D20*SGMNN*VNH
         CFNHI =RN(NR,2)*1.D20*SGMNI*VNI
         CFNHNC=RN(NR,7)*1.D20*SGMNN*VNH
         CFNHNH=RN(NR,8)*1.D20*SGMNN*VNH
         AD(NR,7) = CNN*VNC**2/(CFNCI+CFNCNC+CFNCNH)
         AD(NR,8) = CNN*VNH**2/(CFNHI+CFNHNH+CFNHNC)

         AV(NR,7) = 0.D0
         AV(NR,8) = 0.D0
      ENDDO

!        ****** AVK : HEAT PINCH ******

!     --- NEOCLASSICAL PART ---

      IF(MDNCLS.EQ.0) THEN
!     NCLASS has already calculated neoclassical heat pinch(AVKNC)
!     beforehand if MDNCLS=1 so that MDLAVK becomes no longer valid.
      select case(MDLAVK)
      case(1)
         DO NS=1,NSM
            AVKNC(1:NRMAX,NS) =-RHOG(1:NRMAX)*CHP
            AVKDW(1:NRMAX,NS) = 0.D0
         END DO
      case(2)
         DO NS=1,NSM
            AVKNC(1:NRMAX,NS) =-RHOG(1:NRMAX)*(CHP*1.D6) /(ANE*1.D20*TE*RKEV)
            AVKDW(1:NRMAX,NS) = 0.D0
         END DO
      case(3)
!     *** Hinton & Hazeltine model ***
         DO NR=1,NRMAX
            IF(NR.EQ.NRMAX) THEN
               ANE = PNSS(1)
               ANI = PNSS(2)
               TE  = PTS(1)
               TD  = PTS(2)
            ELSE
               ANE = 0.5D0*(RN(NR+1,1)+RN(NR  ,1))
               ANI = 0.5D0*(RN(NR+1,2)+RN(NR  ,2))
               TE  = 0.5D0*(RT(NR+1,1)+RT(NR  ,1))
               TD  = 0.5D0*(RT(NR+1,2)+RT(NR  ,2))
            ENDIF
            ANED= ANE/ANI

            ZEFFL = ZEFF(NR)
            BPL   = BP(NR)
            QPL   = QP(NR)
            IF(QPL.GT.100.D0) QPL=100.D0
            EZOHL = EZOH(NR)
            EPS   = EPSRHO(NR)
            EPSS  = SQRT(EPS)**3
            VTE   = SQRT(TE*RKEV/AME)
            VTD   = SQRT(TD*RKEV/(PA(2)*AMM))
            TAUE  = FTAUE(ANE,ANI,TE,ZEFFL)
            TAUD  = FTAUI(ANE,ANI,TD,PZ(2),PA(2))
            RNUE  = ABS(QPL)*RR/(TAUE*VTE*EPSS)
            RNUD  = ABS(QPL)*RR/(TAUD*VTD*EPSS)

            RK13E = RK13/(1.D0+RA13*SQRT(RNUE)+RB13*RNUE)/(1.D0+RC13*RNUE*EPSS)
            RK23E = RK23/(1.D0+RA23*SQRT(RNUE)+RB23*RNUE)/(1.D0+RC23*RNUE*EPSS)
            RK3D  =((1.17D0-0.35D0*SQRT(RNUD))/(1.D0+0.7D0*SQRT(RNUD)) &
                 & -2.1D0*(RNUD*EPSS)**2)/(1.D0+(RNUD*EPSS)**2)

            H     = BB/SQRT(BB**2+BPL**2)
            AVKNC(NR,1) = (-RK23E+2.5D0*RK13E)*SQRT(EPS)*EZOHL/BPL/H
            AVK(NR,1)   = CNH*AVKNC(NR,1)
            AVKNC(NR,2:NSM) = RK3D/((1.D0+(RNUE*EPSS)**2)*PZ(2))*RK13E &
                 & *SQRT(EPS)*EZOHL/BPL/H*ANED
            AVKDW(NR,2:NSM) = 0.D0
         ENDDO
      case default
         IF(MDLAVK.NE.0) WRITE(6,*) 'XX INVALID MDLAVK : ',MDLAVK
         AVKNC(1:NRMAX,1:NSM)=0.D0
         AVKDW(1:NRMAX,1:NSM)=0.D0
         AVK  (1:NRMAX,1:NSM)=0.D0
      end select
      ENDIF

!     ***** NET HEAT PINCH *****

      AVKDW(1:NRMAX,1:NSLMAX)=CDH*AVKDW(1:NRMAX,1:NSLMAX)
      AVK(1:NRMAX,1:NSLMAX)=CDH*AVKDW(1:NRMAX,1:NSLMAX) &
           &               +CNH*AVKNC(1:NRMAX,1:NSLMAX)

      RETURN
      END SUBROUTINE TRCFAD

      END MODULE trcoef_adhoc
