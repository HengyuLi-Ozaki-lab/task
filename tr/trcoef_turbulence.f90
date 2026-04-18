!     ***********************************************************
!
!     Turbulent (anomalous) transport coefficients (extracted from trcoef.f90, Phase 5 step 1)
!
!     ***********************************************************

      MODULE trcoef_turbulence

      IMPLICIT NONE
      PRIVATE
      PUBLIC :: TRCFDW

      CONTAINS

      SUBROUTINE TRCFDW

      USE TRCOMM, ONLY : &
           AEE, ADDW, AGMP, AKDW, AME, AMM, AR1RHOG, AR2RHOG, BB, CALF, CDW, &
           CK0,CK1, CKALFA, CKBETA, CKGUMA, CWEB, DR, EPS0, EPSRHO, ER, EZOH, &
           KGR1, KGR2, KGR3, KGR4, MDCD05, MDLKAI, MDLUF, MDTC, NRMAX, NSM, &
           NSMAX, NSTM, PA, PADD, PBM, PI, PNSS, PTS, PZ, Q0, QP, RA, RDPS, &
           RG, RHOG, RHOM, RJCB, RKAP, RKEV, RKPRHO, RKPRHOG, RM, RMU0, RN, &
           RNF, RR, RT, RW, S, ALPHA, RKCV, SUMPBM, TAUK, VC, VEXB, VGR1, &
           VGR2, VGR3, VGR4, WEXB, ZEFF, VEXBP, WEXBP, BP, rkind
      USE trcdbm
      USE trmodels,ONLY: mbgb_driver,mmm95_driver,mmm71_driver
      USE libitp
      USE libgrf
      USE libplog, ONLY: plog
      IMPLICIT NONE
      INTEGER:: &
           NS, NR08, NR, I
      REAL(rkind)   :: &
           AEI, AGITG, AKDWEL, AKDWIL, AKDWL, ALPHAL, ALNI, ALTI, AMA, AMD, &
           AMI, AMT, ANA, ANDX, ANE, ANT, ANYUE, ARG, CHIB, CHIGB, CLN, CLPE, &
           CLS, CLT, CRTCL, CS, DEDW, DELTA2, DIDW, DKAI, DND, DNE, &
           DPE, DPERHO, DPP, DQ, DRL, DTD, DTE, DTERHO, DTI, DVE, EPS, ETAC, &
           ETAI, EZOHL, F, FBHM, FDREV, FEXB, FS, FTAUE, FTAUI, HETA, OMEGAD, &
           OMEGAS, OMEGASS, OMEGATT, PNI, PPK, PTI, QL, RBEEDG, RG1, &
           RGL, RGLC, RHOI, RHOS, RKPP2, RLAMBDA, RLAMDA, RNM, RNP, RNST2, &
           RNTM, RNTP, RNUZ, ROUS, RPEM, RPEP, RPM, RPP, RREFF, RRSTAR, &
           RRSTAX, SA, SL, SLAMDA, TA, TAUAP, TAUD, TAUE, TD, TE, TI, TRCOFS, &
           TRCOFSS, TRCOFSX, TRCOFT, TT, VA, VTE, VTI, WCI, WE1, WPE2, XCHI0, &
           XCHI1, XCHI2, XXA, XXH, ZEFFL, FSDFIX, BPA, PROFDL,ANI
      REAL(rkind):: &
           RS,RKAPL,SHEARL,PNEL,RHONI,DPDRL,DVEXBDRL,CEXB,CKAP,chi_cdbm, &
           PAL,PZL,ADFFI,ACHIE,ACHII,ACHIEB,ACHIIB,ACHIEGB,ACHIIGB, &
           VTIL, GAMMA0, EXBfactor, SHRfactor
      REAL(rkind):: CHIIW,DIFHW,CHIEW,DIMPW, &
                CHIIRB,DIFHRB,CHIERB,DIMPRB, &
                CHIIKB,DIFHKB,CHIEKB,DIMPKB, &
                ADDWHL,ADDWZL
      REAL(rkind):: CHII,DIFH,CHIE,DIFZ,VIST,VISP, &
                CHIIB,DIFHB,CHIEB,CHIEG 
      INTEGER:: MODEL,ierr
      REAL(rkind),DIMENSION(NRMAX):: S_HM


      AMD=PA(2)*AMM
      AMT=PA(3)*AMM
      AMA=PA(4)*AMM
      OMEGAD = PZ(2)*AEE*BB/AMD

      select case(MDLKAI)
      case(0:9)
         KGR1='/TI  vs r/'
         KGR2='/DTI  vs r/'
         KGR3='/CLN,CLT  vs r/'
         KGR4='/CLS  vs r/'
      case(10:19)
         KGR1='/LOG(DEDW),LOG(DIDW)  vs r/'
         KGR2='/ETAI,ETAC  vs r/'
         KGR3='/CLN,CLT  vs r/'
         KGR4='/CLS  vs r/'
      case(20:29)
         KGR1='/DTE,CRTCL  vs r/'
         KGR2='/ETAI,ETAC  vs r/'
         KGR3='/CLN,CLT  vs r/'
         KGR4='/CLS  vs r/'
      case(30:40,130:139)
         KGR1='/E$-r$=  vs r/'
         KGR2='/V$-ExB$=  vs r/'
         KGR3='@exp(-beta*WE1$+gamma$=)  vs r@'
         KGR4='@Lambda,1/(1+OmgST$+2$=)  vs r@'
      case(41:50)
         KGR1='/NST$+2$= vs r/'
         KGR2='/OmegaST vs r/'
         KGR3='@lambda vs r@'
         KGR4='@Lambda,1/(1+OmgST$+2$=),1/(1+G*WE1$+2$=)vs r@'
      case(51:59)
         KGR1='/NST$+2$= vs r/'
         KGR2='/OmegaST vs r/'
         KGR3='@lambda vs r@'
         KGR4='@Lambda,1/(1+OmgST$+2$=),1/(1+G*WE1$+2$=)vs r@'
      case(60:69)
         KGR1='/V$-ExB$=/'
         KGR2='/E$-r$=/'
         KGR3='/GROWTH RATE/'
         KGR4='/ExB SHEARING RATE/'
      case(140:149)
         KGR1='/ExB SHEARING RATE/'
         KGR2='/ExB Factor/'
         KGR3='/magnetic shear/'
         KGR4='/alpha/'
      case(150:159)
         KGR1='/chi-tb-e/'
         KGR2='/chi-tb-i/'
         KGR3='/dif-tb-h/'
         KGR4='/dif-tb-z/'
      case(160:169)
         KGR1='/chi-tb-e/'
         KGR2='/chi-tb-i/'
         KGR3='/Dif-tb-h/'
         KGR4='/Dif-tb-z/'
      case default
         KGR1='//'
         KGR2='//'
         KGR3='//'
         KGR4='//'
      end select

      DO I=1,3
         DO NR=1,NRMAX
            VGR1(NR,I)=0.D0
            VGR2(NR,I)=0.D0
            VGR3(NR,I)=0.D0
            VGR4(NR,I)=0.D0
         ENDDO
      ENDDO

!
!     ***** PP   is the total pressure (nT) *****
!     ***** DPP  is the derivative of total pressure (dnT/dr) *****
!     ***** TI   is the ion temperature (Ti) *****
!     ***** DTI  is the derivative of ion temperature (dTi/dr) *****
!     ***** TE   is the electron temperature (Te) *****
!     ***** DTE  is the derivative of electron temperature (dTe/dr) *****
!     ***** ANE  is the electron density (ne) *****
!     ***** DNE  is the derivative of electron density (dne/dr) *****
!     ***** CLN  is the density scale length ne/(dne/dr) *****
!     ***** CLT  is the ion temerature scale length Ti/(dTi/dr) *****
!     ***** DQ   is the derivative of safety factor (dq/dr) *****
!     ***** CLS  is the shear length R*q**2/(r*dq/dr) *****

      DO NR=1,NRMAX
         IF(SUMPBM.EQ.0.D0) THEN
            PADD(NR)=0.D0
         ELSE
            PADD(NR)=PBM(NR)*1.D-20/RKEV-RNF(NR,1)*RT(NR,2)
         ENDIF
!     Calculate ExB velocity in advance
!                            for ExB shearing rate calculation
         VEXB(NR)= -ER(NR)/BB
         VEXBP(NR)= -ER(NR)/(RR*BP(NR))
      ENDDO

      DO NR=1,NRMAX
!     characteristic time of temporal change of transport coefficients
         TAUK(NR)=QP(NR)*RR/SQRT(RT(NR,2)*RKEV/(PA(2)*AMM))*DBLE(MDTC)
!         DRL=RJCB(NR)/DR
         DRL=1.D0/(DR*RA)
         EPS=EPSRHO(NR)
         RNTP=0.D0
         RNP =0.D0
         RNTM=0.D0
         RNM =0.D0
         IF(NR.EQ.NRMAX) THEN
            ANE =PNSS(1)
            ANDX=PNSS(2)
            ANT =PNSS(3)
            ANA =PNSS(4)
            TE=PTS(1)
            TD=PTS(2)
            TT=PTS(3)
            TA=PTS(4)

!     In the following, we assume that
!        1. pressures of beam and fusion at rho=1 are negligible,
!        2. calibration of Pbeam (from UFILE) is not necessary at rho=1.

            DO NS=2,NSM
               RNTP=RNTP+PNSS(NS)*PTS(NS)
               RNP =RNP +PNSS(NS)
               RNTM=RNTM+RN(NR-1,NS)*RT(NR-1,NS)+RN(NR  ,NS)*RT(NR  ,NS)
               RNM =RNM +RN(NR-1,NS)+RN(NR  ,NS)
            ENDDO
            RNTM= RNTM+RW(NR-1,1)+RW(NR-1,2)+RW(NR  ,1)+RW(NR  ,2)
            RPP = RNTP+PNSS(1)   *PTS(1)
            RPM = RNTM+RN(NR-1,1)*RT(NR-1,1)+RN(NR  ,1)*RT(NR  ,1)+PADD(NR-1)+PADD(NR)
            RPEP= PNSS(1)   *PTS(1)
            RPEM= 0.5D0*(RN(NR-1,1)*RT(NR-1,1)+RN(NR  ,1)*RT(NR  ,1))
            RNTM= 0.5D0*RNTM
            RNM = 0.5D0*RNM
            RPM = 0.5D0*RPM

            DTE=DERIV3P(PTS(1),RT(NR,1),RT(NR-1,1),RHOG(NR),RHOM(NR),RHOM(NR-1))
            DNE=DERIV3P(PNSS(1),RN(NR,1),RN(NR-1,1),RHOG(NR),RHOM(NR),RHOM(NR-1))
            DPE=DERIV3P(PNSS(1)*PTS(1), RN(NR,1)*RT(NR,1),RN(NR-1,1)*RT(NR-1,1), RHOG(NR),RHOM(NR),RHOM(NR-1))
            DTD=DERIV3P(PTS(2),RT(NR,2),RT(NR-1,2),RHOG(NR),RHOM(NR),RHOM(NR-1))
            DND=DERIV3P(PNSS(2),RN(NR,2),RN(NR-1,2),RHOG(NR),RHOM(NR),RHOM(NR-1))
            ZEFFL=ZEFF(NR)
            EZOHL=EZOH(NR)

            DPP = (RPP-RPM)*DRL

            TI  = RNTP/RNP
            DTI = (RNTP/RNP-RNTM/RNM)*DRL
         ELSE
!     density and temperature for each species on grid
            ANE    = 0.5D0*(RN(NR+1,1)+RN(NR  ,1))
            ANDX   = 0.5D0*(RN(NR+1,2)+RN(NR  ,2))
            ANT    = 0.5D0*(RN(NR+1,3)+RN(NR  ,3))
            ANA    = 0.5D0*(RN(NR+1,4)+RN(NR  ,4))
            TE     = 0.5D0*(RT(NR+1,1)+RT(NR  ,1))
            TD     = 0.5D0*(RT(NR+1,2)+RT(NR  ,2))
            TT     = 0.5D0*(RT(NR+1,3)+RT(NR  ,3))
            TA     = 0.5D0*(RT(NR+1,4)+RT(NR  ,4))

!     incremental presssure and density for ion species
            DO NS=2,NSM
               RNTP=RNTP+RN(NR+1,NS)*RT(NR+1,NS)
               RNP =RNP +RN(NR+1,NS)
               RNTM=RNTM+RN(NR  ,NS)*RT(NR  ,NS)
               RNM =RNM +RN(NR  ,NS)
            ENDDO
!     incremental presssure and density for fast particles
            RNTP= RNTP+RW(NR+1,1)+RW(NR+1,2)
            RNTM= RNTM+RW(NR  ,1)+RW(NR  ,2)
!     incremental presssure and density for electron
            RPP = RNTP+RN(NR+1,1)*RT(NR+1,1)+PADD(NR+1)
            RPM = RNTM+RN(NR  ,1)*RT(NR  ,1)+PADD(NR  )
!     electron pressure
            RPEP= RN(NR+1,1)*RT(NR+1,1)
            RPEM= RN(NR  ,1)*RT(NR  ,1)

!     gradients of temperature, density and pressure for electron
            DTE = (RT(NR+1,1)-RT(NR  ,1))*DRL
            DNE = (RN(NR+1,1)-RN(NR  ,1))*DRL
            DPE = (RN(NR+1,1)*RT(NR+1,1)-RN(NR,1)*RT(NR,1))*DRL
!     gradients of temperature and density for ion
            DTD = (RT(NR+1,2)-RT(NR  ,2))*DRL
            DND = (RN(NR+1,2)-RN(NR  ,2))*DRL
!     effective charge number and parallel electric field on grid
            ZEFFL  = 0.5D0*(ZEFF(NR+1)+ZEFF(NR))
            EZOHL  = 0.5D0*(EZOH(NR+1)+EZOH(NR))

!     pressure gradient on grid
            DPP = (RPP-RPM)*DRL

!     effective ion temperature and its gradient on grid
            TI  = 0.5D0*(RNTP/RNP+RNTM/RNM)
            DTI = (RNTP/RNP-RNTM/RNM)*DRL
         ENDIF
!         WRITE(6,'(1PE12.4)') DPP

!$$$C     second derivative of effective pressure for old version WE1
!$$$         RPI4=0.D0
!$$$         RPI3=0.D0
!$$$         RPI2=0.D0
!$$$         RPI1=0.D0
!$$$         IF(NR.LE.1) THEN
!$$$            DO NS=2,NSM
!$$$               RPI4=RPI4+RN(NR,  NS)*RT(NR,  NS)
!$$$            ENDDO
!$$$            RPI4=RPI4+RW(NR,  1)+RW(NR,  2)+PADD(NR  )
!$$$         ELSE
!$$$            DO NS=2,NSM
!$$$               RPI4=RPI4+RN(NR-1,NS)*RT(NR-1,NS)
!$$$            ENDDO
!$$$            RPI4=RPI4+RW(NR-1,1)+RW(NR-1,2)+PADD(NR-1)
!$$$         ENDIF
!$$$            DO NS=2,NSM
!$$$               RPI3=RPI3+RN(NR  ,NS)*RT(NR  ,NS)
!$$$            ENDDO
!$$$            RPI3=RPI3+RW(NR  ,1)+RW(NR  ,2)+PADD(NR  )
!$$$         IF(NR.GE.NRMAX-1) THEN
!$$$            DO NS=2,NSM
!$$$               RPI2=RPI2+RN(NR  ,NS)*RT(NR  ,NS)
!$$$            ENDDO
!$$$            RPI2=RPI2+RW(NR  ,1)+RW(NR  ,2)+PADD(NR  )
!$$$         ELSE
!$$$            DO NS=2,NSM
!$$$               RPI2=RPI2+RN(NR+1,NS)*RT(NR+1,NS)
!$$$            ENDDO
!$$$            RPI2=RPI2+RW(NR+1,1)+RW(NR+1,2)+PADD(NR+1)
!$$$         ENDIF
!$$$         IF(NR.GE.NRMAX-2) THEN
!$$$            DO NS=2,NSM
!$$$               RPI1=RPI1+RN(NR  ,NS)*RT(NR  ,NS)
!$$$            ENDDO
!$$$            RPI1=RPI1+RW(NR  ,1)+RW(NR  ,2)+PADD(NR  )
!$$$         ELSE
!$$$            DO NS=2,NSM
!$$$               RPI1=RPI1+RN(NR+1,NS)*RT(NR+1,NS)
!$$$            ENDDO
!$$$            RPI1=RPI1+RW(NR+1,1)+RW(NR+1,2)+PADD(NR+1)
!$$$         ENDIF
!$$$         RPIM=0.5D0*(RPI1+RPI2)
!$$$         RPI0=0.5D0*(RPI2+RPI3)
!$$$         RPIP=0.5D0*(RPI3+RPI4)
!$$$         DPPP=(RPIP-2*RPI0+RPIM)*DRL*DRL

!     safety factor and its gradient on grid
!         DQ = DERIV3(NR,RHOG,QP,NRMAX,1)
         IF(NR.EQ.1) THEN
            DQ=(4.D0*QP(2)-3.D0*QP(1)-QP(3))/(2.D0*DR)
         ELSE IF(NR.EQ.NRMAX) THEN
            DQ=(3.D0*QP(NRMAX)-4.D0*QP(NRMAX-1)+QP(NRMAX-2))/(2.D0*DR)
         ELSE
            DQ=(QP(NR+1)-QP(NR-1))/(2.D0*DR)
         ENDIF
         
         QL = QP(NR)

!     sound speed for electron
         VTE = SQRT(ABS(TE*RKEV/AME))

!     characteristic length of ion temperature
         IF(ABS(DTI).GT.1.D-32) THEN
            CLT=TI/DTI
         ELSE
            IF(DTI.GE.0.D0) THEN
               CLT = 1.D32
            ELSE
               CLT =-1.D32
            ENDIF
         ENDIF

!     characteristic length of electron density
         IF(ABS(DNE).GT.1.D-32) THEN
            CLN=ANE/DNE
         ELSE
            IF(DNE.GE.0.D0) THEN
               CLN = 1.D32
            ELSE
               CLN =-1.D32
            ENDIF
         ENDIF

!     characteristic length of electron pressure
         IF(ABS(RPEP-RPEM).GT.1.D-32) THEN
            CLPE=0.5D0*(RPEP+RPEM)/(RPEP-RPEM)/DRL
         ELSE
            IF(RPEP-RPEM.GE.0.D0) THEN
               CLPE = 1.D32
            ELSE
               CLPE =-1.D32
            ENDIF
         ENDIF

!     ???
         IF(ABS(DQ).GT.1.D-32) THEN
            CLS=QL*QL/(DQ*EPS)
         ELSE
            IF(DQ.GE.0.D0) THEN
               CLS = 1.D32
            ELSE
               CLS =-1.D32
            ENDIF
         ENDIF

!     collision time between electrons and ions
         TAUE = FTAUE(ANE,ANDX,TE,ZEFFL)
         ANYUE = 0.5D0*(1.D0+ZEFFL)/TAUE

         ROUS = DSQRT(ABS(TE)*RKEV/AMD)/OMEGAD
         PPK  = 0.3D0/ROUS
         OMEGAS  = PPK*TE*RKEV/(AEE*BB*ABS(CLN))
         OMEGATT = DSQRT(2.D0)*VTE/(RR*QL)

!     Alfven wave velocity
         PNI=ANDX+ANT+ANA
         AMI=(AMD*ANDX+AMT*ANT+AMA*ANA)/PNI
         VA=SQRT(BB**2/(RMU0*ANE*1.D20*AMI))
!     magnetic shear
         S(NR)=RHOG(NR)/QL*DQ
!     pressure gradient for MHD instability
         ALPHA(NR)=-2.D0*RMU0*QL**2*RR/BB**2*(DPP*1.D20*RKEV)
!     magnetic curvature
         RKCV(NR)=-EPS*(1.D0-1.D0/(QL*QL))

!     rotational shear
!        omega(or gamma)_e=(r/q) d(q v_exb/r)/dr
         DVE = DERIV3(NR,RHOG,VEXB,NRMAX,1)
         WEXB(NR) = (S(NR)-1.D0)*VEXB(NR)/RHOG(NR)+DVE
         DVE = DERIV3(NR,RHOG,VEXBP,NRMAX,1)
         WEXBP(NR) = RR*BP(NR)*DVE/BB
!     Doppler shear
         AGMP(NR) = QP(NR)/EPS*WEXB(NR)

!   *************************************************************
!   ***  0.GE.MDLKAI.LT.10 : CONSTANT COEFFICIENT MODEL       ***
!   *** 10.GE.MDLKAI.LT.20 : DRIFT WAVE (+ITG +ETG) MODEL     ***
!   *** 20.GE.MDLKAI.LT.30 : REBU-LALLA MODEL                 ***
!   *** 30.GE.MDLKAI.LT.40 : CURRENT-DIFFUSIVITY DRIVEN MODEL ***
!   *** 40.GE.MDLKAI.LT.60 : DRIFT WAVE BALLOONING MODEL      ***
!   ***       MDLKAI.GE.60 : ITG(/TEM, ETG) MODEL ETC         ***
!   *************************************************************
!
         SELECT CASE(MDLKAI)
            CASE(0:9)
!   *********************************************************
!   ***  MDLKAI.EQ. 0   : CONSTANT*(1+A*r**2)             ***
!   ***  MDLKAI.EQ. 1   : CONSTANT/(1-A*r**2)             ***
!   ***  MDLKAI.EQ. 2   : CONSTANT*(dTi/dr)**B/(1-A*r**2) ***
!   ***  MDLKAI.EQ. 3   : CONSTANT*(dTi/dr)**B*Ti**C      ***
!   ***  MDLKAI.EQ. 4   : PROP. TO CUBIC FUNC. with Bohm  ***
!   ***  MDLKAI.EQ. 5   : PROP. TO CUBIC FUNC.            ***
!   *********************************************************

            select case(MDLKAI)
            case(0)
               AKDWL=1.D0+CKALFA*RG(NR)**2
            case(1)
               AKDWL=1.D0/(1.D0-CKALFA*RG(NR)**2)
            case(2)
               AKDWL=1.D0/(1.D0-CKALFA*RG(NR)**2)*(ABS(DTI)*RA)**CKBETA
            case(3)
               AKDWL=1.D0*(ABS(DTI)*RA)**CKBETA*ABS(TI)**CKGUMA
            case(4)
               FSDFIX=0.1D0
               BPA=AR1RHOG(NRMAX)*RDPS/RR
               PROFDL=(PTS(1)*RKEV/(16.D0*AEE*SQRT(BB**2+BPA**2)))/FSDFIX
               AKDWL=FSDFIX*(1.D0+(PROFDL-1.D0)*(RHOG(NR)/ RA)**2)
            case(5)
               FSDFIX=1.D0
               PROFDL=20.D0
               AKDWL=FSDFIX*(1.D0+(PROFDL-1.D0)*(RHOG(NR)/ RA)**2)
            case default
               WRITE(6,*) 'XX INVALID MDLKAI : ',MDLKAI
               AKDWL=0.D0
            end select
            AKDW(NR,1)=CK0*AKDWL
            AKDW(NR,2)=CK1*AKDWL
            AKDW(NR,3)=CK1*AKDWL
            AKDW(NR,4)=CK1*AKDWL

            VGR1(NR,1)=TI
            VGR1(NR,2)=0.D0
            VGR2(NR,1)=DTI
            VGR2(NR,2)=0.D0
            VGR3(NR,1)=CLN
            VGR3(NR,2)=CLT
            VGR4(NR,1)=CLS
            VGR4(NR,2)=CLS

          CASE(10:19)

            ETAI=CLN/CLT
            select case(MDLKAI)
            case(10)
               ETAC   = 1.D0
               RRSTAR = RR
               FDREV  = 1.D0
               HETA   = 1.D0
            case(11:13)
               ETAC   = 1.D0
               RRSTAR = RR
               FDREV  = 1.D0
!!!!!!            ARG = 6.D0*(ETAI(NR)-ETAC(NR))*RA/CLN(NR)
               ARG = 6.D0*(ETAI-ETAC)
               IF(ARG.LE.-150.D0) THEN
                  HETA = 0.D0
               ELSEIF(ARG.GT.150.D0) THEN
                  HETA = 1.D0
               ELSE
                  HETA = 1.D0/(1.D0+EXP(-ARG))
               ENDIF
            case(14)
               IF(ABS(CLN)/RR.GE.0.2D0) THEN
                  ETAC = 1.D0+2.5D0*(ABS(CLN)/RR-0.2D0)
               ELSE
                  ETAC = 1.D0
               ENDIF
               RRSTAR = RR
               FDREV  = 1.D0
               ARG = 6.D0*(ETAI-ETAC)*RA/CLN
               IF(ARG.LE.-150.D0) THEN
                  HETA = 0.D0
               ELSEIF(ARG.GT.150.D0) THEN
                  HETA = 1.D0
               ELSE
                  HETA = 1.D0/(1.D0+EXP(-ARG))
               ENDIF
            case(15:16)
               ETAC    = 1.D0
               RRSTAX  = ABS(RR*(1.D0-(2.D0+1.D0   /QL**2)*EPS) &
                             /(1.D0-(2.D0+RKAP**2/QL**2)*EPS))
               RREFF = RRSTAX/(1.2D0*ABS(CLN))
               FDREV = SQRT(2.D0*PI)*RREFF**1.5D0*(RREFF-1.5D0) *EXP(-RREFF)
               RRSTAR= MIN(RRSTAX,CLS)
               FDREV = MAX(FDREV,ANYUE/(EPS*OMEGAS))
               ARG = 6.D0*(ETAI-ETAC)
               IF(ARG.LE.-150.D0) THEN
                  HETA = 0.D0
               ELSEIF(ARG.GT.150.D0) THEN
                  HETA = 1.D0
               ELSE
                  HETA = 1.D0/(1.D0+EXP(-ARG))
               ENDIF
            case default
               WRITE(6,*) 'XX INVALID MDLKAI : ',MDLKAI
               RRSTAR = RR
               FDREV  = 1.D0
               HETA   = 1.D0
            end select
            IF(MDLKAI.EQ.16) THEN
               DEDW = CK0*2.5D0*OMEGAS/PPK**2 &
     &               *(SQRT(EPS)*MIN(FDREV,EPS*OMEGAS/ANYUE)+OMEGAS/OMEGATT*MAX(1.D0,ANYUE/OMEGATT))
               RGL   = 2.5D0*OMEGAS*HETA*SQRT(2.D0*ABS(TI)*ABS(ETAI)*ABS(CLN)/(TE*RRSTAR))
               AMD=PA(2)*AMM
               TAUD = FTAUI(ANE,ANDX,TD,PZ(2),PA(2))
               RNUZ= 1.D0/(TAUD*SQRT(EPS))
               XCHI1=SQRT(RNUZ)/(SQRT(RNUZ)+SQRT(RGL))
               XXH=2.D0/(1.D0+PPK**2)
               RGLC=OMEGAS/(2*SQRT(2.D0)*XXH)
               XXA=XXH*PPK**2/4.D0
               IF(RGL.GT.RGLC) THEN
                  XCHI2=XXA*(SQRT(1.D0+(2.D0/XXA)*(RGL-RGLC)/RGL)-1.D0)
               ELSE
                  XCHI2=0.D0
               ENDIF
               XCHI0=SQRT(XCHI1**2+XCHI2**2)
               DIDW = CK1*XCHI0*RGL/PPK**2
            ELSE
               DEDW = CK0*2.5D0*OMEGAS/PPK**2 &
     &            *(SQRT(EPS)*MIN(FDREV,EPS*OMEGAS/ANYUE)+OMEGAS/OMEGATT*MAX(1.D0,ANYUE/OMEGATT))

               DIDW = CK1*2.5D0*OMEGAS/PPK**2*HETA*SQRT(2.D0*ABS(TI)*ABS(ETAI)*ABS(CLN)/(TE*RRSTAR))
            ENDIF

            AKDW(NR,1) = CDW(1)*DEDW+CDW(2)*DIDW
            AKDW(NR,2) = CDW(3)*DEDW+CDW(4)*DIDW
            AKDW(NR,3) = CDW(5)*DEDW+CDW(6)*DIDW
            AKDW(NR,4) = CDW(7)*DEDW+CDW(8)*DIDW
            IF(MDLKAI.EQ.12) THEN
               AKDW(NR,1) = AKDW(NR,1)*QL
               AKDW(NR,2) = AKDW(NR,2)*QL
               AKDW(NR,3) = AKDW(NR,3)*QL
               AKDW(NR,4) = AKDW(NR,4)*QL
            ELSEIF(MDLKAI.EQ.13) THEN
               AKDW(NR,1) = AKDW(NR,1)*(1+QL**2)
               AKDW(NR,2) = AKDW(NR,2)*(1+QL**2)
               AKDW(NR,3) = AKDW(NR,3)*(1+QL**2)
               AKDW(NR,4) = AKDW(NR,4)*(1+QL**2)
            ENDIF
            VGR1(NR,1)=PLOG(DEDW,1.D-2,1.D2)
            VGR1(NR,2)=PLOG(DIDW,1.D-2,1.D2)
            VGR2(NR,1)=ETAI
            VGR2(NR,2)=ETAC
            VGR3(NR,1)=CLN
            VGR3(NR,2)=CLT
            VGR4(NR,1)=CLS
            VGR4(NR,2)=CLS

          CASE(20:29)

            select case(MDLKAI)
            case(20)
               CRTCL=6.D-2*SQRT(EZOHL*BB**3/(ANE*1.D20*SQRT(TE*RKEV))) &
                          *SQRT(AEE**2/(RMU0*SQRT(AME)))/(QL*RKEV)
               IF(ABS(DTE).LE.CRTCL .OR. DQ.LE.0.D0 .OR. NR.EQ.1) THEN
                  DKAI=0.D0
               ELSE
                  DKAI=1.5D-1*(ABS(DTE)/TE +2.D0*ABS(DNE)/ANE) &
                       *SQRT(TE/TI)*(1.D0/EPS)*(QL**2/(DQ*BB*SQRT(RR)))*VC**2 &
                       *SQRT(RMU0*1.5D0*AMM)*(1.D0-CRTCL/ABS(DTE))
               ENDIF
               AKDW(NR,1)=                  DKAI
               AKDW(NR,2)=ZEFFL*SQRT(TE/TD)*DKAI
               AKDW(NR,3)=ZEFFL*SQRT(TE/TT)*DKAI
               AKDW(NR,4)=ZEFFL*SQRT(TE/TA)*DKAI
            case default
               WRITE(6,*) 'XX INVALID MDLKAI : ',MDLKAI
               AKDW(NR,1)=0.D0
               AKDW(NR,2)=0.D0
               AKDW(NR,3)=0.D0
               AKDW(NR,4)=0.D0
            end select
            VGR1(NR,1)=DTE
            VGR1(NR,2)=CRTCL
            VGR2(NR,1)=ETAI
            VGR2(NR,2)=ETAC
            VGR3(NR,1)=CLN
            VGR3(NR,2)=CLT
            VGR4(NR,1)=CLS
            VGR4(NR,2)=CLS

          CASE(30:39)

            WPE2=ANE*1.D20*AEE*AEE/(AME*EPS0)
            DELTA2=VC**2/WPE2

            RNST2=0.D0
            OMEGASS=0.D0
            SLAMDA=0.D0
            RLAMDA=0.D0
            RG1=1.D0
            WE1=0.D0

            IF(MOD(MDLKAI,2).EQ.0) THEN
               SL=(S(NR)**2+0.1D0**2)
               WE1=-QL*RR/(SL*VA)*DVE
               RG1=CWEB*FEXB(ABS(WE1),S(NR),ALPHA(NR))
!               DBDRR=DPPP*1.D20*RKEV*RA*RA/(BB**2/(2*RMU0))
!               DELTAE=SQRT(DELTA2)
!               WE1=SQRT(PA(2)/PA(1))*(QL*RR*DELTAE)/(2*SL*RA*RA)*DBDRR
!               RG1=1.D0/(1.D0+RG1*WE1*WE1)
            ENDIF

            select case(MDLKAI)
            case(30)
               FS=1.D0/(1.7D0+SQRT(6.D0)*S(NR))
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
            case(31)
               ALPHAL=ALPHA(NR)*CALF
               FS=TRCOFS(S(NR),ALPHAL,RKCV(NR))
               IF(MDCD05.NE.0) &
                    FS=FS*(2.D0*SQRT(RKPRHO(NR))/(1.D0+RKPRHO(NR)**2))**1.5D0
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
            case(32)
               ALPHAL=ALPHA(NR)*CALF
               FS=TRCOFS(S(NR),ALPHAL,RKCV(NR))
               FS=FS*RG1
               IF(MDCD05.NE.0) &
                    FS=FS*(2.D0*SQRT(RKPRHO(NR))/(1.D0+RKPRHO(NR)**2))**1.5D0
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
            case(33)
               FS=TRCOFS(S(NR),0.D0,RKCV(NR))
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
            case(34)
               FS=TRCOFS(S(NR),0.D0,RKCV(NR))
               FS=FS*RG1
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
            case(35)
               ALPHAL=ALPHA(NR)*CALF
               FS=TRCOFSS(S(NR),ALPHAL)
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
            case(36)
               ALPHAL=ALPHA(NR)*CALF
               FS=TRCOFSS(S(NR),ALPHAL)
!               FS=FS/(1.D0+RG1*WE1*WE1)
               FS=FS*RG1
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
            case(37)
               FS=TRCOFSS(S(NR),0.D0)
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
            case(38)
               FS=TRCOFSS(S(NR),0.D0)
!               FS=FS/(1.D0+RG1*WE1*WE1)
               FS=FS*RG1
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
            case(39)
               ALPHAL=ALPHA(NR)*CALF
               FS=TRCOFSX(S(NR),ALPHAL,RKCV(NR),RA/RR)
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
            case default
               WRITE(6,*) 'XX INVALID MDLKAI : ',MDLKAI
               FS=1.D0
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**3*DELTA2*VA/(QL*RR)
            end select
            AKDW(NR,1)=AKDWEL
            AKDW(NR,2)=AKDWIL
            AKDW(NR,3)=AKDWIL
            AKDW(NR,4)=AKDWIL

            VGR1(NR,1)=FS
            VGR1(NR,2)=S(NR)
            VGR1(NR,3)=ALPHA(NR)
            VGR2(NR,1)=ER(NR)
            VGR2(NR,2)=VEXB(NR)
            VGR2(NR,3)=0.D0
            VGR3(NR,1)=RG1
            VGR3(NR,2)=ABS(WE1)
            VGR3(NR,3)=0.D0
            VGR4(NR,1)=RLAMDA
            VGR4(NR,2)=1.D0/(1.D0+OMEGASS**2)
            VGR4(NR,3)=0.D0

          CASE(40:50)

            WPE2=ANE*1.D20*AEE*AEE/(AME*EPS0)
            DELTA2=VC**2/WPE2

            RNST2=0.D0
            OMEGASS=0.D0
            SLAMDA=0.D0
            RLAMDA=0.D0

            IF(MOD(MDLKAI,2).EQ.0) THEN
               RG1=CWEB*FEXB(ABS(WE1),S(NR),ALPHA(NR))
               SL=SQRT(S(NR)**2+0.1D0**2)
               WE1=-QL*RR/(SL*VA)*DVE
!               DBDRR=DPPP*1.D20*RKEV*RA*RA/(BB**2/(2*RMU0))
!               DELTAE=SQRT(DELTA2)
!               WE1=SQRT(PA(2)/PA(1))*(QL*RR*DELTAE)/(2*SL*RA*RA)*DBDRR
            ENDIF

            F=VTE/VA
!
            select case(MDLKAI)
            case(40)
               FS=1.D0/(1.7D0+SQRT(6.D0)*S(NR))
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
            case(41)
               ALPHAL=ALPHA(NR)*CALF
               FS=TRCOFS(S(NR),ALPHAL,RKCV(NR))
!               IF (NR.LE.2) write(6,'(I5,4F15.10)') NR,S(NR),ALPHA(NR),RKCV(NR),FS
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
            case(42)
               ALPHAL=ALPHA(NR)*CALF
               FS=TRCOFS(S(NR),ALPHAL,RKCV(NR))
!               FS=FS/(1.D0+RG1*WE1*WE1)
               FS=FS*RG1
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
            case(43)
               FS=TRCOFS(S(NR),0.D0,RKCV(NR))
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
            case(44)
               FS=TRCOFS(S(NR),0.D0,RKCV(NR))
!               FS=FS/(1.D0+RG1*WE1*WE1)
               FS=FS*RG1
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
            case(45)
               ALPHAL=ALPHA(NR)*CALF
               FS=TRCOFSS(S(NR),ALPHAL)
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
            case(46)
               ALPHAL=ALPHA(NR)*CALF
               FS=TRCOFSS(S(NR),ALPHAL)
!               FS=FS/(1.D0+RG1*WE1*WE1)
               FS=FS*RG1
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
            case(47)
               FS=TRCOFSS(S(NR),0.D0)
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
            case(48)
               FS=TRCOFSS(S(NR),0.D0)
!               FS=FS/(1.D0+RG1*WE1*WE1)
               FS=FS*RG1
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
            case(49)
               ALPHAL=ALPHA(NR)*CALF
               FS=TRCOFSX(S(NR),ALPHAL,RKCV(NR),RA/RR)
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)*F
            case(50)
               AEI=(PZ(2)*ANDX+PZ(3)*ANT+PZ(4)*ANA)*AEE/PNI
               WCI=AEI*BB/AMI
               PTI=(TD*ANDX+TT*ANT+TA*ANA)/PNI
               VTI=SQRT(ABS(PTI*RKEV/AMI))
               RHOI=VTI/WCI

               ALPHAL=ALPHA(NR)*CALF
               FS=TRCOFT(S(NR),ALPHAL,RKCV(NR),RA/RR)
               SA=S(NR)-ALPHA(NR)
               RNST2=0.5D0/((1.D0-2.D0*SA+3.D0*SA*SA)*FS)
               RKPP2=RNST2/(FS*ABS(ALPHA(NR))*DELTA2)

               SLAMDA=RKPP2*RHOI**2
               RLAMDA=RLAMBDA(SLAMDA)
               OMEGAS= SQRT(RKPP2)*TE*RKEV/(AEE*BB*ABS(CLPE))
               TAUAP=(QL*RR)/VA
               OMEGASS=(OMEGAS*TAUAP)/(RNST2*SQRT(ALPHA(NR)))
               AKDWEL=CK0*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)/(RLAMDA*(1.D0+OMEGASS**2))
               AKDWIL=CK1*FS*SQRT(ABS(ALPHA(NR)))**2*DELTA2*VA/(QL*RR)/(1.D0+OMEGASS**2)
            end select

            AKDW(NR,1)=AKDWEL
            AKDW(NR,2)=AKDWIL
            AKDW(NR,3)=AKDWIL
            AKDW(NR,4)=AKDWIL

            VGR1(NR,1)=FS
            VGR1(NR,2)=S(NR)
            VGR1(NR,3)=ALPHA(NR)
            VGR2(NR,1)=RNST2
            VGR2(NR,2)=OMEGASS
            VGR2(NR,3)=0.D0
            VGR3(NR,1)=SLAMDA
            VGR3(NR,2)=0.D0
            VGR3(NR,3)=0.D0
            VGR4(NR,1)=RLAMDA
            VGR4(NR,2)=1.D0/(1.D0+OMEGASS**2)
!            VGR4(NR,3)=1.D0/(1.D0+RG1*WE1*WE1)
            VGR4(NR,3)=RG1

          CASE(60:65)

            WPE2=ANE*1.D20*AEE*AEE/(AME*EPS0)
            DELTA2=VC**2/WPE2

            RNST2=0.D0
            OMEGASS=0.D0
            SLAMDA=0.D0
            RLAMDA=0.D0

            IF(NR.EQ.1) THEN
               DRL=RJCB(NR)/DR
               S_HM(NR) = RM(NR)*RA/(0.5D0*(QP(NR)+Q0))*(QP(NR)-Q0)*DRL
            ELSE
               DRL=RJCB(NR)/DR
               S_HM(NR) = RM(NR)/(0.5D0*(QP(NR)+QP(NR-1))) *(QP(NR)-QP(NR-1))/DR
            ENDIF

            VGR1(NR,2)=S(NR)
            VGR1(NR,3)=ALPHA(NR)
            VGR2(NR,1)=VEXB(NR)
            VGR2(NR,2)=ER(NR)
            VGR2(NR,3)=0.D0
            VGR3(NR,1)=AGMP(NR)
            VGR3(NR,2)=0.D0
            VGR3(NR,3)=0.D0
            VGR4(NR,1)=WEXB(NR)
            VGR4(NR,2)=WEXBP(NR)
            VGR4(NR,3)=0.D0
            IF(MDLKAI.EQ.65) THEN
               DPERHO=DPE/RJCB(NR)
               DTERHO=DTE/RJCB(NR)
               NR08=INT(0.8D0*NRMAX)
               CHIB  = (ABS(DPERHO*1.D3)/(ANE*BB))*QL*QL*((RT(NR08,1)-RT(NRMAX,1))/RT(NRMAX,1))
               RHOS  = 1.02D-4*SQRT(PA(2)*TE*1.D3/PZ(2))/(RA*BB)
!               RHOS  = SQRT(2.D0*AMM/AEE)*SQRT(PA(2)*TE*1.D3)/(PZ(2)*RA*BB)
               CHIGB = RHOS*ABS(DTERHO*1.D3)/BB
               CS    = SQRT(ABS(TE*RKEV/(PA(2)*AMM)))
               ALNI  = ABS(DND/ANDX)
               ALTI  = ABS(DTD/TD)
               AGITG = 0.1D0*CS/RA*SQRT(RA*ALNI+RA*ALTI)*SQRT(TD/TE)
               WEXB(NR)=0.D0
               AKDW(NR,1) = 8.D-5  *CHIB*FBHM(WEXB(NR),AGITG,S(NR))+7.D-2  *CHIGB
               AKDW(NR,2) = 1.6D-4 *CHIB*FBHM(WEXB(NR),AGITG,S(NR))+1.75D-2*CHIGB
               AKDW(NR,3) = AKDW(NR,2)
               AKDW(NR,4) = AKDW(NR,2)
               VGR1(NR,1) = FBHM(WEXB(NR),AGITG,S(NR))
            ENDIF

          CASE(130:139)  ! CDBM defined in trcdbm.f90

            RS=RA*RG(NR)
            RKAPL=RKPRHO(NR)
            SHEARL=S(NR)
            PNEL=ANE*1.D20

            RHONI=(AMD*ANDX+AMT*ANT+AMA*ANA)*1.D20
            
            DPDRl=DPP*1.D20*RKEV
            DVEXBDRL=DVE/RA
            SL=(S(NR)**2+0.1D0**2)
            WE1=-QL*RR/(SL*VA)*DVE
            RG1=CWEB*FEXB(ABS(WE1),S(NR),ALPHA(NR))
            cexb=RG1
            ckap=1.d0
            MODEL=MDLKAI-130

            CALL tr_cdbm(BB,RR,RS,RKAPL,QL,SHEARL,PNEL,rhoni,dpdrl, &
                 &    dvexbdrl,calf,ckap,cexb,MODEL,chi_cdbm)

            AKDWEL=(CK0/12.D0)*chi_cdbm
            AKDWIL=(CK1/12.D0)*chi_cdbm

            AKDW(NR,1)=AKDWEL
            AKDW(NR,2)=AKDWIL
            AKDW(NR,3)=AKDWIL
            AKDW(NR,4)=AKDWIL

            VGR1(NR,1)=0.d0
            VGR1(NR,2)=S(NR)
            VGR1(NR,3)=ALPHA(NR)
            VGR2(NR,1)=ER(NR)!RNST2
            VGR2(NR,2)=VEXB(NR)!OMEGASS
            VGR2(NR,3)=WEXB(NR)
            VGR3(NR,1)=0.D0
            VGR3(NR,2)=0.D0
            VGR3(NR,3)=0.D0
            VGR4(NR,1)=0.D0
            VGR4(NR,2)=0.D0
            VGR4(NR,3)=0.D0

         CASE(140:149)
            PAL=0.D0
            PZL=0.D0
            DO NS=2,NSMAX
               PAL=PAL+PA(NS)*RN(NR,NS)
               PZL=PZL+PZ(NS)*RN(NR,NS)
            ENDDO
            PAL=PAL/RN(NR,1)
            PZL=PZL/RN(NR,1)
           
            CALL mbgb_driver(RA*RG(NR),RR,ANE*1.D20,TE,TI,DTE,DNE,PAL,PZL, &
                             QP(NR),BB,WEXBP(NR),S(NR), &
                             ADFFI,ACHIE,ACHII,ACHIEB,ACHIIB,ACHIEGB,ACHIIGB, &
                             ierr)
!            WRITE(6,'(1P6E12.4)') &
!                 RA*RG(NR),RR,ANE*1.D20,TE,TI,DTE, &
!                 DNE,PAL,PZL,QP(NR),BB,WEXBP(NR), &
!                 S(NR),ADFFI, &
!                 ACHIE,ACHII,ACHIEB,ACHIIB,ACHIEGB,ACHIIGB

            AKDWEL=ACHIE
            AKDWIL=ACHII

            AKDW(NR,1)=AKDWEL
            AKDW(NR,2)=AKDWIL
            AKDW(NR,3)=AKDWIL
            AKDW(NR,4)=AKDWIL

            VGR1(NR,1)=ER(NR)
            VTIL=SQRT(2.D0*TI*RKEV/(PAL*AMM))
            GAMMA0=VTIL/(QP(NR)*RR)
            EXBfactor=1.D0/(1.D0+(WEXBP(NR)/GAMMA0)**2)
            SHRfactor=1.D0/MAX(1.D0,(S(NR)-0.5d0)**2)
            VGR2(NR,1)=EXBfactor
            VGR2(NR,2)=SHRfactor
            VGR3(NR,1)=S(NR)
            VGR3(NR,2)=0.D0
            VGR3(NR,3)=0.D0
            VGR4(NR,1)=ALPHA(NR)
            VGR4(NR,2)=0.D0
            VGR4(NR,3)=0.D0

         CASE(150:159) ! MMM95 transport model
            CALL mmm95_driver(NR,CHIIW,DIFHW,CHIEW,DIMPW, &
                                 CHIIRB,DIFHRB,CHIERB,DIMPRB, &
                                 CHIIKB,DIFHKB,CHIEKB,DIMPKB,IERR)

            AKDWEL=CHIEW+CHIERB+CHIEKB
            AKDWIL=CHIIW+CHIIRB+CHIIKB
            ADDWHL=DIFHW+DIFHRB+DIFHKB
            ADDWZL=DIMPW+DIMPRB+DIMPKB

            AKDW(NR,1)=AKDWEL         ! electron thermal diffusivity
            AKDW(NR,2:NSMAX)=AKDWIL   ! ion thermal diffusivity
            ADDW(NR,1)=ADDWHL         ! electron partilcle diffusivity (adhoc)
            DO NS=2,NSMAX
               IF(PA(NS).LE.3.D0.AND.PZ(NS).EQ.1.D0) THEN  
                  ADDW(NR,2:NSMAX)=ADDWHL   ! hydrogen ion particle diffusivity
               ELSE
                  ADDW(NR,2:NSMAX)=ADDWZL   ! impurity ion particle diffusivity
               END IF
            END DO
            
            VGR1(NR,1)=CHIEW
            VGR1(NR,2)=CHIEW+CHIERB
            VGR1(NR,3)=CHIEW+CHIERB+CHIEKB
            VGR2(NR,1)=CHIIW
            VGR2(NR,2)=CHIIW+CHIIRB
            VGR2(NR,3)=CHIIW+CHIIRB+CHIIKB
            VGR3(NR,1)=DIFHW
            VGR3(NR,2)=DIFHW+DIFHRB
            VGR3(NR,3)=DIFHW+DIFHRB+DIFHKB
            VGR4(NR,1)=DIMPW
            VGR4(NR,2)=DIMPW+DIMPRB
            VGR4(NR,3)=DIMPW+DIMPRB+DIMPKB

         CASE(160:169) ! mmm7_1 transport model
            CALL mmm71_driver(NR,CHII,DIFH,CHIE,DIFZ,VIST,VISP, &
                                 CHIIW,DIFHW,CHIEW,CHIIB,DIFHB,CHIEB,CHIEG, &
                                 IERR)

            AKDWEL=CHIE
            AKDWIL=CHII
            ADDWHL=DIFH
            ADDWZL=DIFZ

            AKDW(NR,1)=CHIE           ! electron thermal diffusivity
            AKDW(NR,2:NSMAX)=CHII     ! ion thermal diffusivity
            ADDW(NR,1)=DIFH           ! electron partilcle diffusivity (adhoc)
            DO NS=2,NSMAX
               IF(PA(NS).LE.3.D0.AND.PZ(NS).EQ.1.D0) THEN  
                  ADDW(NR,2:NSMAX)=DIFH   ! hydrogen ion particle diffusivity
               ELSE
                  ADDW(NR,2:NSMAX)=DIFZ   ! impurity ion particle diffusivity
               END IF
            END DO
            
            VGR1(NR,1)=CHIEW
            VGR1(NR,2)=CHIEW+CHIEB
            VGR1(NR,3)=CHIEW+CHIEB+CHIEG
            VGR2(NR,1)=CHIIW
            VGR2(NR,2)=CHIIW+CHIIB
            VGR2(NR,3)=CHII
            VGR3(NR,1)=DIFHW
            VGR3(NR,2)=DIFHW+DIFHB
            VGR3(NR,3)=DIFH
            VGR4(NR,1)=VIST
            VGR4(NR,2)=VISP
            VGR4(NR,3)=0.D0


          CASE(230:239)

            RS=RA*RG(NR)
            RKAPL=RKPRHO(NR)
            SHEARL=S(NR)
            PNEL=ANE*1.D20

            DPDRl=DPP*1.D20*RKEV
            DVEXBDRL=DVE/RA
            SL=(S(NR)**2+0.1D0**2)
            WE1=-QL*RR/(SL*VA)*DVE
            RG1=CWEB*FEXB(ABS(WE1),S(NR),ALPHA(NR))
            cexb=RG1
            ckap=1.d0
            MODEL=MDLKAI-230

            PNI=ANDX+ANT+ANA
            DO NS=2,NSMAX
               AMI=PA(NS)*AMM
               VA=SQRT(BB**2/(RMU0*ANE*1.D20*AMI))
               WE1=-QL*RR/(SL*VA)*DVE
               RG1=CWEB*FEXB(ABS(WE1),S(NR),ALPHA(NR))
               RHONI=AMI*PNI*1.D20
               CALL tr_cdbm(BB,RR,RS,RKAPL,QL,SHEARL,PNEL,rhoni,dpdrl, &
                    dvexbdrl,calf,ckap,cexb,MODEL,chi_cdbm)
               AKDW(NR,NS)=chi_cdbm
            END DO
            ANE=0.D0
            AKDW(NR,1)=0.D0
            DO NS=2,NSMAX
               IF(NR.EQ.NRMAX) THEN
                  ANI=PNSS(NS)
               ELSE
                  ANI=0.5D0*(RN(NR+1,NS)+RN(NR  ,NS))
               END IF
               ANE=ANE+PZ(NS)*ANI
               AKDW(NR,1)=AKDW(NR,1)+AKDW(NR,NS)*PZ(NS)*ANI
            END DO
            AKDW(NR,1)=AKDW(NR,1)/ANE

            VGR1(NR,1)=0.d0
            VGR1(NR,2)=S(NR)
            VGR1(NR,3)=ALPHA(NR)
            VGR2(NR,1)=ER(NR)!RNST2
            VGR2(NR,2)=VEXB(NR)!OMEGASS
            VGR2(NR,3)=WEXB(NR)
            VGR3(NR,1)=0.D0
            VGR3(NR,2)=0.D0
            VGR3(NR,3)=0.D0
            VGR4(NR,1)=0.D0
            VGR4(NR,2)=0.D0
            VGR4(NR,3)=0.D0

         END SELECT
      ENDDO

!      DO NR=1,NRMAX
!         WRITE(6,'(I5,1P6E12.4)') NR,VGR1(NR,1),VGR1(NR,2),VGR1(NR,3), &
!                                     VGR2(NR,1),VGR2(NR,2),VGR2(NR,3)
!      END DO
!      DO NR=1,NRMAX
!         WRITE(6,'(I5,1P6E12.4)') NR,VGR3(NR,1),VGR3(NR,2),VGR3(NR,3), &
!                                     VGR4(NR,1),VGR4(NR,2),VGR4(NR,3)
!      END DO
         
!            CALL PAGES
!            CALL GRD1D(1,RG,VGR1,NRMAX,NRMAX,3,'CHIE vs RS')
!            CALL GRD1D(2,RG,VGR2,NRMAX,NRMAX,3,'CHII vs RS')
!            CALL GRD1D(3,RG,VGR3,NRMAX,NRMAX,3,'ADIH vs RS')
!            CALL GRD1D(4,RG,VGR4,NRMAX,NRMAX,3,'ADIZ vs RS')
!            CALL PAGEE

      IF(MDLKAI.EQ.60.OR.MDLKAI.EQ.61) THEN
         CALL GLF23_DRIVER(S_HM)
      ELSEIF(MDLKAI.EQ.62) THEN
         CALL AITKEN(1.D0,RBEEDG,RM,RNF(:,1),2,NRMAX)
         RBEEDG=RBEEDG/PNSS(1)
         CALL IFSPPPL_DRIVER(NSTM,NRMAX,RN,RR,DR,RJCB,RHOG,RHOM, &
              QP,S,EPSRHO,RKPRHOG,RT,BB,AMM,AME,PNSS,PTS,RNF(1:NRMAX,1), &
              RBEEDG,MDLUF,NSMAX,AR1RHOG,AR2RHOG,AKDW)
      ELSEIF(MDLKAI.EQ.63.OR.MDLKAI.EQ.64) THEN
         CALL WEILAND_DRIVER
      ENDIF

      RETURN
      END SUBROUTINE TRCFDW

      END MODULE trcoef_turbulence
