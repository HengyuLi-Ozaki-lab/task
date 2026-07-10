!     ***********************************************************
!
!     Neoclassical transport coefficients (extracted from trcoef.f90, Phase 5 step 2)
!
!     ***********************************************************

      MODULE trcoef_neoclassical

      IMPLICIT NONE
      PRIVATE
      PUBLIC :: TRCFNC, TRCFDW_AKDW

      CONTAINS

      SUBROUTINE TRCFNC

      USE TRCOMM, ONLY : AEE, AK, AKDW, AKDWD, AKDWP, AKLD, AKLP,&
           & AKNC, AKNCP, AKNCT, AME, AMM, BB, BP, CDH, CNH, CSPRS,&
           & EPSRHO, MDDIAG, MDEDGE, MDLKNC, MDLUF, NREDGE, NRMAX,&
           & NSLMAX, NSM, PA, PNSS, PTS, PZ, QP, RA, RG, RKEV, RN, RR&
           &, RT, ZEFF, NSMAX, rkind
      USE trcoll, ONLY : FTAUE, FTAUI
      IMPLICIT NONE
      INTEGER:: NR, NS, NS1
      REAL(rkind)   :: AMA, AMD, AMT, ANA, ANDX, ANE, ANT, CHECK,&
           & DELDA, EPS, EPSS, F1, F2, QL, RALPHA,&
           & RHOA2, RHOD2, RHOE2, RHOT2, RK22E, RK2A, RK2D, RK2T,&
           & RMUSA, RMUSD, RMUST, RNUA, RNUD, RNUE, RNUT, TA, TAUA,&
           & TAUD, TAUE, TAUT, TD, TE, TERM1A, TERM1D, TERM1T, TERM2A&
           &, TERM2D, TERM2T, TT, VTA, VTD, VTE, VTT, ZEFFL
      REAL(rkind) :: RK22=2.55D0, RA22=0.45D0, RB22=0.43D0, RC22=0.43D0
      REAL(rkind) :: RK2=0.66D0 , RA2=1.03D0 , RB2=0.31D0 , RC2=0.74D0
      REAL(rkind),SAVE :: CDHSV

!      DATA RK11,RA11,RB11,RC11/1.04D0,2.01D0,1.53D0,0.89D0/
!      DATA RK12,RA12,RB12,RC12/1.20D0,0.76D0,0.67D0,0.56D0/
!!      DATA RK22,RA22,RB22,RC22/2.55D0,0.45D0,0.43D0,0.43D0/
!      DATA RK13,RA13,RB13,RC13/2.30D0,1.02D0,1.07D0,1.07D0/
!      DATA RK23,RA23,RB23,RC23/4.19D0,0.57D0,0.61D0,0.61D0/
!      DATA RK33,RA33,RB33,RC33/1.83D0,0.68D0,0.32D0,0.66D0/
!!      DATA RK2 ,RA2 ,RB2 ,RC2 /0.66D0,1.03D0,0.31D0,0.74D0/

      AMD=PA(2)*AMM
      AMT=AMD
      AMA=AMD
      IF(NSMAX.GE.3) AMT=PA(3)*AMM
      IF(NSMAX.GE.4) AMA=PA(4)*AMM

      DO NR=1,NRMAX
         IF(NR.EQ.NRMAX) THEN
            ANE =PNSS(1)
            ANDX=PNSS(2)
            ANT=0.D0
            ANA=0.D0
            IF(NSMAX.GE.3) ANT =PNSS(3)
            IF(NSMAX.GE.4) ANA =PNSS(4)
            TE=PTS(1)
            TD=PTS(2)
            TT=TD
            TA=TD
            IF(NSMAX.GE.3) TT=PTS(3)
            IF(NSMAX.GE.4) TA=PTS(4)
            ZEFFL=ZEFF(NR)
         ELSE
            ANE    = 0.5D0*(RN(NR+1,1)+RN(NR  ,1))
            ANDX   = 0.5D0*(RN(NR+1,2)+RN(NR  ,2))
            ANT=0.D0
            ANA=0.D0
            IF(NSMAX.GE.3) ANT    = 0.5D0*(RN(NR+1,3)+RN(NR  ,3))
            IF(NSMAX.GE.4) ANA    = 0.5D0*(RN(NR+1,4)+RN(NR  ,4))
            TE     = 0.5D0*(RT(NR+1,1)+RT(NR  ,1))
            TD     = 0.5D0*(RT(NR+1,2)+RT(NR  ,2))
            TT=TD
            TA=TD
            IF(NSMAX.GE.3) TT     = 0.5D0*(RT(NR+1,3)+RT(NR  ,3))
            IF(NSMAX.GE.4) TA     = 0.5D0*(RT(NR+1,4)+RT(NR  ,4))
            ZEFFL  = 0.5D0*(ZEFF(NR+1)+ZEFF(NR))
         ENDIF

         QL = QP(NR)
         EPS=EPSRHO(NR)
         EPSS=SQRT(EPS)**3

         VTE = SQRT(ABS(TE*RKEV/AME))
         VTD = SQRT(ABS(TD*RKEV/AMD))
         VTT = SQRT(ABS(TT*RKEV/AMT))
         VTA = SQRT(ABS(TA*RKEV/AMA))

         RHOE2=2.D0*AME*ABS(TE)*RKEV/(PZ(1)*AEE*BP(NR))**2
         RHOD2=2.D0*AMD*ABS(TD)*RKEV/(PZ(2)*AEE*BP(NR))**2
         RHOT2=RHOD2
         RHOA2=RHOD2
         IF(NSMAX.GE.3) RHOT2=2.D0*AMT*ABS(TT)*RKEV/(PZ(3)*AEE*BP(NR))**2
         IF(NSMAX.GE.4) RHOA2=2.D0*AMA*ABS(TA)*RKEV/(PZ(4)*AEE*BP(NR))**2

!$$$         TAUE = FTAUE(ANE,ANDX,TE,1.D0)
!$$$         TAUD = FTAUI(ANE,ANDX,TD,1.D0,PA(2))
!$$$         TAUT = FTAUI(ANE,ANT ,TT,1.D0,PA(3))
!$$$         TAUA = FTAUI(ANE,ANA ,TA,2.D0,PA(4))
         TAUE = FTAUE(ANE,ANDX,TE,ZEFFL)
         TAUD = FTAUI(ANE,ANDX,TD,PZ(2),PA(2))
         TAUT=TAUD
         TAUA=TAUD
         IF(NSMAX.GE.3) TAUT = FTAUI(ANE,ANT ,TT,PZ(3),PA(3))
         IF(NSMAX.GE.4) TAUA = FTAUI(ANE,ANA ,TA,PZ(4),PA(4))

         RNUE=ABS(QL)*RR/(TAUE*VTE*EPSS)
         RNUD=ABS(QL)*RR/(TAUD*VTD*EPSS)
         RNUT=ABS(QL)*RR/(TAUT*VTT*EPSS)
         RNUA=ABS(QL)*RR/(TAUA*VTA*EPSS)

!     ***** NEOCLASSICAL TRANSPORT (HINTON, HAZELTINE) *****

      IF(MDLKNC.EQ.1) THEN

!         RK11E=RK11*(1.D0/(1.D0+RA11*SQRT(RNUE)+RB11*RNUE)+(EPSS*RC11)**2/RB11*RNUE/(1.D0+RC11*RNUE*EPSS))
!         RK12E=RK12*(1.D0/(1.D0+RA12*SQRT(RNUE)+RB12*RNUE)+(EPSS*RC12)**2/RB12*RNUE/(1.D0+RC12*RNUE*EPSS))
         RK22E=RK22*(1.D0/(1.D0+RA22*SQRT(RNUE)+RB22*RNUE)+(EPSS*RC22)**2/RB22*RNUE/(1.D0+RC22*RNUE*EPSS))
!         RK13E=RK13/(1.D0+RA13*SQRT(RNUE)+RB13*RNUE)/(1.D0+RC13*RNUE*EPSS)
!         RK23E=RK23/(1.D0+RA23*SQRT(RNUE)+RB23*RNUE)/(1.D0+RC23*RNUE*EPSS)
!         RK33E=RK33/(1.D0+RA33*SQRT(RNUE)+RB33*RNUE)/(1.D0+RC33*RNUE*EPSS)

         RK2D =RK2 *(1.D0/(1.D0+RA2 *SQRT(RNUD)+RB2 *RNUD)+(EPSS*RC2 )**2/RB2 *RNUD/(1.D0+RC2 *RNUD*EPSS))
         RK2T =RK2 *(1.D0/(1.D0+RA2 *SQRT(RNUT)+RB2 *RNUT)+(EPSS*RC2 )**2/RB2 *RNUT/(1.D0+RC2 *RNUT*EPSS))
         RK2A =RK2 *(1.D0/(1.D0+RA2 *SQRT(RNUA)+RB2 *RNUA)+(EPSS*RC2 )**2/RB2 *RNUA/(1.D0+RC2 *RNUA*EPSS))
!         RK3D=((1.17-0.35*SQRT(RNUD))/(1.D0+0.7*SQRT(RNUD))-2.1*(RNUD*EPSS)**2)/(1+(RNUD*EPSS)**2)
!         RK3T=((1.17-0.35*SQRT(RNUT))/(1.D0+0.7*SQRT(RNUT))-2.1*(RNUT*EPSS)**2)/(1+(RNUT*EPSS)**2)
!         RK3A=((1.17-0.35*SQRT(RNUA))/(1.D0+0.7*SQRT(RNUA))-2.1*(RNUA*EPSS)**2)/(1+(RNUA*EPSS)**2)

         AKNC(NR,1) = SQRT(EPS)*RHOE2/TAUE*RK22E
         AKNC(NR,2) = SQRT(EPS)*RHOD2/TAUD*RK2D
         AKNC(NR,3) = SQRT(EPS)*RHOT2/TAUT*RK2T
         AKNC(NR,4) = SQRT(EPS)*RHOA2/TAUA*RK2A

      ELSE

!     ***** CHANG HINTON *****

         DELDA=0.D0

         IF(MDLUF.EQ.0) THEN
            RALPHA=ZEFFL-1.D0
         ELSE
            RALPHA=PZ(3)**2*ANT/(PZ(2)**2*ANDX)
         ENDIF

         RMUSD=RNUD*(1.D0+1.54D0*RALPHA)
         RMUST=RNUT*(1.D0+1.54D0*RALPHA)
         RMUSA=RNUA*(1.D0+1.54D0*RALPHA)

         F1=(1.D0+1.5D0*(EPS**2+EPS*DELDA)+3.D0/8.D0*EPS**3*DELDA)/(1.D0+0.5D0*EPS*DELDA)
         F2=DSQRT(1.D0-EPS**2)*(1.D0+0.5D0*EPS*DELDA)/(1.D0+DELDA/EPS*(DSQRT(1.D0-EPS**2)-1.D0))

         TERM1D=(0.66D0*(1.D0+1.54D0*RALPHA) +(1.88D0*DSQRT(EPS)-1.54D0*EPS)*(1.D0+3.75D0*RALPHA))*F1 &
     &       /(1.D0+1.03D0*DSQRT(RMUSD)+0.31D0*RMUSD)
         TERM1T=(0.66D0*(1.D0+1.54D0*RALPHA) +(1.88D0*DSQRT(EPS)-1.54D0*EPS)*(1.D0+3.75D0*RALPHA))*F1 &
     &       /(1.D0+1.03D0*DSQRT(RMUST)+0.31D0*RMUST)
         TERM1A=(0.66D0*(1.D0+1.54D0*RALPHA) +(1.88D0*DSQRT(EPS)-1.54D0*EPS)*(1.D0+3.75D0*RALPHA))*F1 &
     &       /(1.D0+1.03D0*DSQRT(RMUSA)+0.31D0*RMUSA)

         TERM2D=0.583D0*RMUSD*EPS/(1.D0+0.74D0*RMUSD*EPSS)*(1.D0+(1.33D0*RALPHA*(1.D0+0.6D0*RALPHA)) &
     &       /(1.D0+1.79D0*RALPHA))*(F1-F2)
         TERM2T=0.583D0*RMUST*EPS/(1.D0+0.74D0*RMUST*EPSS)*(1.D0+(1.33D0*RALPHA*(1.D0+0.6D0*RALPHA)) &
     &       /(1.D0+1.79D0*RALPHA))*(F1-F2)
         TERM2A=0.583D0*RMUSA*EPS/(1.D0+0.74D0*RMUSA*EPSS)*(1.D0+(1.33D0*RALPHA*(1.D0+0.6D0*RALPHA)) &
     &       /(1.D0+1.79D0*RALPHA))*(F1-F2)

         AKNC(NR,1)=0.D0
!         AKNC(NR,2)=(QL**2*RHOD2)/(EPSS*TAUD)*(TERM1D+TERM2D)
!         AKNC(NR,3)=(QL**2*RHOT2)/(EPSS*TAUT)*(TERM1T+TERM2T)
!         AKNC(NR,4)=(QL**2*RHOA2)/(EPSS*TAUA)*(TERM1A+TERM2A)
         AKNC(NR,2)=(RHOD2*SQRT(EPS))/TAUD*(TERM1D+TERM2D)
         AKNC(NR,3)=(RHOT2*SQRT(EPS))/TAUT*(TERM1T+TERM2T)
         AKNC(NR,4)=(RHOA2*SQRT(EPS))/TAUA*(TERM1A+TERM2A)

      ENDIF

!     Limit of neoclassical diffusivity
         DO NS=1,NSMAX
            CHECK=ABS(RT(NR,NS)*RKEV/(2.D0*PZ(NS)*AEE*RR*BB))*RG(NR)*RA
            IF(AKNC(NR,NS).GT.CHECK) AKNC(NR,NS)=CHECK
         ENDDO
      ENDDO

      ENTRY TRCFDW_AKDW

      IF(MDEDGE.EQ.1) CDHSV=CDH
      DO NR=1,NRMAX
         IF(MDEDGE.EQ.1.AND.NR.GE.NREDGE) CDH=CSPRS
         DO NS=1,NSM
            AKDW(NR,NS) = CDH*AKDW(NR,NS)
            AK(NR,NS) = AKDW(NR,NS)+CNH*AKNC(NR,NS)
         ENDDO
      ENDDO
      IF(MDEDGE.EQ.1) CDH=CDHSV

!     ***** OFF-DIAGONAL TRANSPORT COEFFICIENTS *****

!     AKLP : heat flux coefficient for pressure gradient
!     AKLD : heat flux coefficient for density gradient

      select case(MDDIAG)
      case(1)
         DO NR=1,NRMAX
            DO NS=1,NSLMAX
               DO NS1=1,NSLMAX
                  IF(NS.EQ.NS1) THEN
                     AKLP(NR,NS,NS1)= AKDW(NR,NS)+CNH*( AKNCT(NR,NS,NS1)+AKNCP(NR,NS,NS1))
                     AKLD(NR,NS,NS1)=-AKDW(NR,NS)+CNH*(-AKNCT(NR,NS,NS1))
                  ELSE
                     AKLP(NR,NS,NS1)= CNH*( AKNCT(NR,NS,NS1)+AKNCP(NR,NS,NS1))
                     AKLD(NR,NS,NS1)= CNH*(-AKNCT(NR,NS,NS1))
                  ENDIF
               ENDDO
            ENDDO
         ENDDO
      case(2)
         DO NR=1,NRMAX
            IF(MDEDGE.EQ.1.AND.NR.GE.NREDGE) CDH=CSPRS
            DO NS=1,NSLMAX
               DO NS1=1,NSLMAX
                  IF(NS.EQ.NS1) THEN
                     AKLP(NR,NS,NS1)= CDH*AKDWP(NR,NS,NS1)+CNH*AKNC(NR,NS)
                     AKLD(NR,NS,NS1)= CDH*AKDWD(NR,NS,NS1)
                  ELSE
                     AKLP(NR,NS,NS1)= CDH*AKDWP(NR,NS,NS1)
                     AKLD(NR,NS,NS1)= CDH*AKDWD(NR,NS,NS1)
                  ENDIF
               ENDDO
            ENDDO
         ENDDO
      case(3)
         DO NR=1,NRMAX
            IF(MDEDGE.EQ.1.AND.NR.GE.NREDGE) CDH=CSPRS
            DO NS=1,NSLMAX
               DO NS1=1,NSLMAX
                  AKLP(NR,NS,NS1)= CDH*  AKDWP(NR,NS,NS1)+CNH*( AKNCT(NR,NS,NS1)+AKNCP(NR,NS,NS1))
                  AKLD(NR,NS,NS1)= CDH*  AKDWD(NR,NS,NS1)+CNH*(-AKNCT(NR,NS,NS1))
               ENDDO
            ENDDO
         ENDDO
      end select
      IF(MDEDGE.EQ.1) CDH=CDHSV
!
      RETURN
      END SUBROUTINE TRCFNC

      END MODULE trcoef_neoclassical
