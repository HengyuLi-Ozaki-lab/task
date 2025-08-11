! trpnf.f90

MODULE trpnf

  PRIVATE
  PUBLIC tr_pnf
  PRIVATE tr_nf_dd1
  PRIVATE tr_nf_dd2
  PRIVATE tr_nf_dt
  PRIVATE tr_nf_dhe3
  PRIVATE tr_nf_tt
  PRIVATE tr_nf_the3
  PUBLIC trnfdt
  PUBLIC trnfdd
  PUBLIC sigmam   ! DT Maxwellian
  PUBLIC sigmab   ! DD Slowing down dsitribution
  PUBLIC sigmbs   ! DD Slowing down dsitribution
  PUBLIC trnfdhe3
  PUBLIC sigmadhe3 ! DHe3 Maxwellian

CONTAINS

  SUBROUTINE tr_pnf

    USE trcomm
    USE libnf
    IMPLICIT NONE
    INTEGER:: ns,nnf,nr

    SNF_NSNNFNR(1:NSMAX,1:NNFMAX,1:NRMAX)=0.D0   ! particle source
    PNFCL_NSNNFNR(1:NSMAX,1:NNFMAX,1:NRMAX)=0.D0 ! collisional transfer in
    SNFNN_NNFNR(1:NNFMAX,1:NRMAX)=0.D0  ! neutron number
    PNFNN_NNFNR(1:NNFMAX,1:NRMAX)=0.D0  ! neutron power
    
    DO nnf=1,nnfmax
       SELECT CASE(model_nnf(nnf))
       CASE(id_nf_dd1)
          CALL tr_nf_dd1(nnf)
       CASE(id_nf_dd2)
          CALL tr_nf_dd2(nnf)
       CASE(id_nf_dt)
          CALL tr_nf_dt(nnf)
       END SELECT
    END DO

    ! --- following variables are used in trcalc at every step ---
    
    DO NR=1,NRMAX
       DO NS=1,NSMAX
          SNF_NSNR(NS,NR)=SUM(SNF_NSNNFNR(NS,1:NNFMAX,NR))
          PNFCL_NSNR(NS,NR)=SUM(PNFCL_NSNNFNR(NS,1:NNFMAX,NR))
       END DO
    END DO

    RETURN
  END SUBROUTINE tr_pnf

  ! *** DD1 reaction ***
  !        D + D -> T + p

  SUBROUTInE tr_nf_dd1(nnf)

    USE trcomm
    USE libnf
    IMPLICIT NONE
    INTEGER,INTENT(IN):: nnf
    REAL(rkind):: PND,PTD,RATE_NF,SNF
    INTEGER:: NR

    DO NR=1,NRMAX
       PND=RN(NR,NS_D)
       PTD=RT(NR,NS_D)
       RATE_NF=0.5D0*sigmav_nf(id_nf_dd1,PTD)  ! sigmav for dd1+dd2
       SNF=PND*PND*1.D20*RATE_NF               ! reaction rate
       SNF_NSNNFNR(ns_D,nnf,nr)=SNF_NSNNFNR(ns_D,nnf,nr)-2.D0*SNF      ! D
       SNF_NSNNFNR(ns_T,nnf,nr)=SNF_NSNNFNR(ns_T,nnf,nr)+SNF           ! T
       PNF_NSNNFNR(ns_T,nnf,nr)=PNF_NSNNFNR(ns_T,nnf,nr)+1.01D3*SNF    ! T
       SELECT CASE(model_nf_dd1)
       CASE(0) ! generate (1/2) He4
          SNF_NSNNFNR(ns_He4,nnf,nr)=SNF_NSNNFNR(ns_He4,nnf,nr)+0.5D0*SNF
          PNF_NSNNFNR(ns_He4,nnf,nr)=PNF_NSNNFNR(ns_He4,nnf,nr)+3.02D3*RKEV*SNF
       CASE(1) ! generate p
          SNF_NSNNFNR(ns_H,nnf,nr)=SNF_NSNNFNR(ns_H,nnf,nr)+SNF
          PNF_NSNNFNR(ns_H,nnf,nr)=PNF_NSNNFNR(ns_H,nnf,nr)+3.02D3*RKEV*SNF
       END SELECT
    END DO
    RETURN
  END SUBROUTInE tr_nf_dd1

  ! *** DD2 reaction ***
  !        D + D -> He3 + n

  SUBROUTInE tr_nf_dd2(nnf)

    USE trcomm
    USE libnf
    IMPLICIT NONE
    INTEGER,INTENT(IN):: nnf
    REAL(rkind):: PND,PTD,RATE_NF,SNF
    INTEGER:: NR

    DO NR=1,NRMAX
       PND=RN(NR,NS_D)
       PTD=RT(NR,NS_D)
       RATE_NF=0.5D0*sigmav_nf(id_nf_dd2,PTD)  ! sigmav for dd1+dd2
       SNF=PND*PND*1.D20*RATE_NF               ! reaction rate
       SNF_NSNNFNR(ns_D,nnf,nr)=SNF_NSNNFNR(ns_D,nnf,nr)-2.D0*SNF
       SELECT CASE(model_nf_dd2)
       CASE(0) ! generate He4
          SNF_NSNNFNR(ns_He4,nnf,nr)=SNF_NSNNFNR(ns_He4,nnf,nr)+SNF
          PNF_NSNNFNR(ns_He4,nnf,nr)=PNF_NSNNFNR(ns_He4,nnf,nr)+0.82D3*RKEV*SNF
       CASE(1) ! generate He3
          SNF_NSNNFNR(ns_He3,nnf,nr)=SNF_NSNNFNR(ns_He3,nnf,nr)+SNF
          PNF_NSNNFNR(ns_He3,nnf,nr)=PNF_NSNNFNR(ns_He3,nnf,nr)+0.82D3*RKEV*SNF
       END SELECT
       SNFNN_NNFNR(nnf,nr)=SNFNN_NNFNR(nnf,nr)+SNF
       PNFNN_NNFNR(nnf,nr)=PNFNN_NNFNR(nnf,nr)+2.45D3*RKEV*SNF
    END DO
    RETURN
  END SUBROUTInE tr_nf_dd2

  ! *** DT reaction ***
  !        D + T -> He4 + n

  SUBROUTInE tr_nf_dt(nnf)

    USE trcomm
    USE libnf
    IMPLICIT NONE
    INTEGER,INTENT(IN):: nnf
    REAL(rkind):: PND,PNT,PTD,RATE_NF,SNF
    INTEGER:: NR

    DO NR=1,NRMAX
       PND=RN(NR,NS_D)
       PNT=RN(NR,NS_T)
       PTD=RT(NR,NS_D)
       RATE_NF=sigmav_nf(id_nf_dt,PTD)  ! sigmav for dt
       SNF=PND*PNT*1.D20*RATE_NF
       SNF_NSNNFNR(ns_D,nnf,nr)=SNF_NSNNFNR(ns_D,nnf,nr)-SNF
       SNF_NSNNFNR(ns_T,nnf,nr)=SNF_NSNNFNR(ns_T,nnf,nr)-SNF
       SNF_NSNNFNR(ns_He4,nnf,nr)=SNF_NSNNFNR(ns_He4,nnf,nr)+SNF
       PNF_NSNNFNR(ns_He4,nnf,nr)=PNF_NSNNFNR(ns_He4,nnf,nr)+3.5D3*RKEV*SNF
       SNFNN_NNFNR(nnf,nr)=SNFNN_NNFNR(nnf,nr)+SNF
       PNFNN_NNFNR(nnf,nr)=PNFNN_NNFNR(nnf,nr)+14.1D3*RKEV*SNF
    END DO
    RETURN
  END SUBROUTInE tr_nf_dt

  ! *** DHe3 reaction ***
  !        D + He3 -> He4 + p

  SUBROUTInE tr_nf_dHe3(nnf)

    USE trcomm
    USE libnf
    IMPLICIT NONE
    INTEGER,INTENT(IN):: nnf
    REAL(rkind):: PND,PNHe3,PNT,PTD,RATE_NF,SNF
    INTEGER:: NR

    DO NR=1,NRMAX
       PND=RN(NR,NS_D)
       PNHe3=RN(NR,NS_He3)
       PTD=RT(NR,NS_D)
       RATE_NF=sigmav_nf(id_nf_dhe3,PTD)  ! sigmav for dt
       SNF=PND*PNHe3*1.D20*RATE_NF
       SNF_NSNNFNR(ns_D,  nnf,nr)=SNF_NSNNFNR(ns_D,  nnf,nr)-SNF
       SNF_NSNNFNR(ns_He3,nnf,nr)=SNF_NSNNFNR(ns_He3,nnf,nr)-SNF
       SNF_NSNNFNR(ns_He4,nnf,nr)=SNF_NSNNFNR(ns_He4,nnf,nr)+SNF
       SNF_NSNNFNR(ns_H,  nnf,nr)=SNF_NSNNFNR(ns_H,  nnf,nr)+SNF
       PNF_NSNNFNR(ns_He4,nnf,nr)=PNF_NSNNFNR(ns_He4,nnf,nr)+ 3.6D3*RKEV*SNF
       PNF_NSNNFNR(ns_H,  nnf,nr)=PNF_NSNNFNR(ns_H,  nnf,nr)+14.7D3*RKEV*SNF
    END DO
    RETURN
  END SUBROUTInE tr_nf_dHe3

  ! *** TT reaction ***
  !        T + T -> He4 + 2n

  SUBROUTInE tr_nf_tt(nnf)

    USE trcomm
    USE libnf
    IMPLICIT NONE
    INTEGER,INTENT(IN):: nnf
    REAL(rkind):: PNT,PTT,RATE_NF,SNF
    INTEGER:: NR

    DO NR=1,NRMAX
       PNT=RN(NR,NS_T)
       PTT=RT(NR,NS_T)
       RATE_NF=sigmav_nf(id_nf_tt,PTT)  ! sigmav for tt
       SNF=PNT*PNT*1.D20*RATE_NF
       SNF_NSNNFNR(ns_T,  nnf,nr)=SNF_NSNNFNR(ns_T,  nnf,nr)-2.D0*SNF
       SNF_NSNNFNR(ns_He4,nnf,nr)=SNF_NSNNFNR(ns_He4,nnf,nr)+SNF
       PNF_NSNNFNR(ns_He4,nnf,nr)=PNF_NSNNFNR(ns_He4,nnf,nr) &
            +(0.25D0/2.25D0)*11.3D3*RKEV*SNF
       SNFNN_NNFNR(nnf,nr)=SNFNN_NNFNR(nnf,nr)+2.D0*SNF
       PNFNN_NNFNR(nnf,nr)=PNFNN_NNFNR(nnf,nr) &
            +(2.00D0/2.25D0)*11.3D3*RKEV*SNF
            
    END DO
    RETURN
  END SUBROUTInE tr_nf_tt

  ! *** THe3 reaction ***
  !        T + He3 -> He4 + p + n; He4 + D; He5 + p

  SUBROUTInE tr_nf_tHe3(nnf)

    USE trcomm
    USE libnf
    IMPLICIT NONE
    INTEGER,INTENT(IN):: nnf
    REAL(rkind):: PNT,PNHe3,PTT,RATE_NF,SNF
    INTEGER:: NR

    DO NR=1,NRMAX
       PNT=RN(NR,NS_T)
       PNHe3=RN(NR,NS_He3)
       PTT=RT(NR,NS_T)
       RATE_NF=sigmav_nf(id_nf_the3,PTT)  ! sigmav for tt
       SNF=PNT*PNHe3*1.D20*RATE_NF
       SNF_NSNNFNR(ns_T,  nnf,nr)=SNF_NSNNFNR(ns_T,  nnf,nr)-SNF
       SNF_NSNNFNR(ns_He3,nnf,nr)=SNF_NSNNFNR(ns_He3,nnf,nr)-SNF
       SNF_NSNNFNR(ns_He4,nnf,nr)=SNF_NSNNFNR(ns_He4,nnf,nr)+0.94D0*SNF
       SNF_NSNNFNR(ns_H,  nnf,nr)=SNF_NSNNFNR(ns_H,  nnf,nr)+0.57D0*SNF
       SNF_NSNNFNR(ns_D,  nnf,nr)=SNF_NSNNFNR(ns_D,  nnf,nr)+0.43D0*SNF
       SELECT CASE(model_nf_the3)
       CASE(0)
          SNF_NSNNFNR(ns_He4,nnf,nr)=SNF_NSNNFNR(ns_He4,nnf,nr)+0.06D0*SNF
       CASE(1)
          SNF_NSNNFNR(ns_He5,nnf,nr)=SNF_NSNNFNR(ns_He5,nnf,nr)+0.06D0*SNF
       END SELECT
          
       PNF_NSNNFNR(ns_He4,nnf,nr)=PNF_NSNNFNR(ns_He4,nnf,nr) &
            +0.51D0*(0.25D0/2.25D0)*12.1D3*RKEV*SNF &
            +0.43D0                *4.80D3*RKEV*SNF
       PNF_NSNNFNR(ns_H,  nnf,nr)=PNF_NSNNFNR(ns_H,  nnf,nr) &
            +0.51D0*(1.00D0/2.25D0)*12.1D3*RKEV*SNF &
            +0.06D0                *9.46D3*RKEV*SNF
       PNF_NSNNFNR(ns_D,  nnf,nr)=PNF_NSNNFNR(ns_D,  nnf,nr) &
            +0.43D0                *9.50D3*RKEV*SNF
       SELECT CASE(model_nf_the3)
       CASE(0)
          SNF_NSNNFNR(ns_He4,nnf,nr)=SNF_NSNNFNR(ns_He4,nnf,nr)+0.06D0*SNF
          PNF_NSNNFNR(ns_He4,nnf,nr)=PNF_NSNNFNR(ns_He4,nnf,nr) &
               +0.06D0*1.89D3*RKEV*SNF
       CASE(1)
          SNF_NSNNFNR(ns_He5,nnf,nr)=SNF_NSNNFNR(ns_He5,nnf,nr)+0.06D0*SNF
          PNF_NSNNFNR(ns_He5,nnf,nr)=PNF_NSNNFNR(ns_He5,nnf,nr) &
               +0.06D0*1.89D3*RKEV*SNF
       END SELECT
       SNFNN_NNFNR(nnf,nr)=SNFNN_NNFNR(nnf,nr)+0.51D0*SNF
       PNFNN_NNFNR(nnf,nr)=PNFNN_NNFNR(nnf,nr) &
            +0.51D0*(1.D0/2.25D0)*12.1D3*RKEV*SNF
    END DO
    RETURN
  END SUBROUTInE tr_nf_tHe3

   

  

!     ***********************************************************

!           Nuclear reaction (DT)

!     ***********************************************************

  SUBROUTINE TRNFDT(nnf)

    USE TRCOMM
    USE libnf
    IMPLICIT NONE
    INteGER,INTENT(IN):: nnf
    REAL(rkind)   :: &
         ANE, EC, HYF, P1, PTNT, SS, SSB, TAUS, &
         TD, TE, TT, VC3, VCA3, VCD3, VCR, VCT3, VF, WF, ZEFFM, PB, SSF, RSB
    INTEGER:: NR,NNB,NS_beam
    REAL(rkind)   :: COULOG, HY   !FUNCTION

    VF =SQRT(2.D0*3.5D3 *RKEV/AMA) ! alpha velocity

      DO NR=1,NRMAX
         SNF_NSNNFNR(1:NSMAX,NNF,NR)=0.D0
         PNF_NSNNFNR(1:NSMAX,NNF,NR)=0.D0
         ANE= RN(NR,NS_e)
         TE = RT(NR,NS_e)
         TD = RT(NR,NS_D)
         TT = RT(NR,NS_T)
         SS = SIGMAM(TD,TT)
         IF(model_nnf(nnf).GE.3) THEN
            ZEFFM = (PZ(NS_D  )*PZ(NS_D  )*RN(NR,NS_D  )/PA(NS_D  ) &
                    +PZ(NS_T)  *PZ(NS_T  )*RN(NR,NS_T  )/PA(NS_T  ) &
                    +PZ(NS_He4)*PZ(NS_He4)*RN(NR,NS_He4)/PA(NS_He4) &
                    +PZC(NR)*PZC(NR) *ANC(NR) /12.D0 &
                    +PZFE(NR)*PZFE(NR)*ANFE(NR)/52.D0)/ANE
            SSB=0.D0
            PB=0.D0
            DO NNB=1,NNBMAX
               IF(pnbin(nnb).GT.0.D0) THEN
               NS_beam=ns_nnb(nnb)
               IF (NS_beam.EQ.NS_D) THEN
               ! Critiral energy: (5.43) Takamura     
               EC  = 14.8D0*TE*PA(NS_beam)*ZEFFM**(2.D0/3.D0)
               ! Ion-electron slowing time: (3.22) Takamura: 
               TAUS= 0.2D0*PA(NS_beam)*ABS(TE)**1.5D0 &
                    /(PZ(NS_beam)**2*ANE*COULOG(1,NS_beam,ANE,TE))
               ! weight factor in SIGMAB 
               PTNT= PNB_NNBNR(nnb,NR)*TAUS &
                    /(RN(NR,NS_beam)*1.D20*PNBENG(NNB)*RKEV)
               ! fusion reaction rate
               SSB = SSB+SIGMAB(PNBENG(NNB),EC,TT,PTNT)
               PB  = PB +PNB_NNBNR(NNB,NR)
!               WRITE(26,'(A,6ES12.4)') 'SSB:',SSB,PNB_NNBNR(NNB,NR), &
!                    SIGMAB(PNBENG(NNB),EC,TT,PTNT), &
!                    PNBENG(NNB),EC,TAUS
               ELSEIF(NS_beam.EQ.NS_T) THEN
                  RSB = 0
               ! TAUS= 0.2D0*PA(NS_beam)*ABS(TE)**1.5D0 /(PZ(NS_beam)**2*ANE*COULOG(1,NS_beam,ANE,TE))
               ! ! sf*nj*τsA
               ! ! SSB = SSB + ((((PNB_NNBNR(NNB,NR)))/(AEE*PNBENG(nnb)*RKEV))/(RN(NR,NS_beam))*1.D20) * TAUS*sigmaDbuTbm(TE) 
               ! !sigmaDbuTbm derived from NRL formlary, 1E-26 multiplied to adjust the unit from barn to m^2
               ! RSB = (((PNB_NNBNR(NNB,NR)))/(AEE*PNBENG(nnb)*RKEV))* TAUS * (sigmaDbuTbm(TE)*1.0D-28)
               ! WRITE(6,*) sigmaDbuTbm(TE)
               ENDIF
               END IF
            END DO
            
            ! ####### fast ion calculation #######
            ! ! Critiral energy: (5.43) Takamura     
            ! EC  = 14.8D0*TE*PA(NS_beam)*ZEFFM**(2.D0/3.D0)
            ! ! Ion-electron slowing time: (3.22) Takamura: 
            ! TAUS= 0.2D0*PA(NS_beam)*ABS(TE)**1.5D0 &
            !      /(PZ(NS_beam)**2*ANE*COULOG(1,NS_beam,ANE,TE))
            ! ! weight factor in SIGMAB 
            ! PTNT= PNB_NNBNR(nnb,NR)*TAUS &
            !      /(RN(NR,NS_beam)*1.D20*PNBENG(NNB)*RKEV)
            ! ! fusion reaction rate
            ! PBF  = PB +PNB_NNBNR(NNB,NR)

            ! ####### For fast ion calculation end ########
            ! if NS nnf= 12
            ! SSF = ((8.1725*1E9 &
            !      + (-9.1013*1E8)*TT &
            !      + (4.6685*1E7)*TT**2 &
            !      + (-1.1075*1E6)*TT**3 &
            !      + 9753.1*TT**4)) * 1E-31
           
         ! いるのか確認
         !    IF(PB.NE.0.D0) THEN
         !       SSB=SSB/PB
         !    ELSE
         !       SSB=0.D0
         !    END IF
         ELSE
            SSB=0.D0
         ENDIF
         
         !  高速成分は全て熱化したとみなし、断面積の足し合わせで
         !  総合反応数を与える
         !  DD反応からのfast TについてもDD reationのmoduleにてRNに統合し、
         !  SSFで断面積を与えている。
         
         SNF_NSNNFNR(NS_He4,NNF,NR) = (SS+SSB)*RN(NR,NS_D)*RN(NR,NS_T)*1.D20 !+ RSB*RN(NR,NS_D)
         ! SNF_NSNNFNR(NS_He4,NNF,NR) = (SS+SSB+SSF)*RN(NR,NS_D)*RN(NR,NS_T)*1.D20 + TAUS*RN(NR,NS_D)*sigmaDbuTbm(TE,ETNBI)
         PNF_NSNNFNR(NS_He4,NNF,NR) = SNF_NSNNFNR(NS_He4,NNF,NR)*3.5D3*RKEV*1.D20
         IF(MOD(model_nnf(nnf),2).EQ.1) &
              SNF_NSNNFNR(NS_He4,NNF,NR)=0.D0
         SNF_NSNNFNR(NS_D,NNF,NR) =-SNF_NSNNFNR(NS_He4,NNF,NR)
         SNF_NSNNFNR(NS_T,NNF,NR) =-SNF_NSNNFNR(NS_He4,NNF,NR)
         PNF_NSNNFNR(NS_D,NNF,NR) &
              =SNF_NSNNFNR(NS_He4,NNF,NR)*RT(NR,NS_D)*RKEV*1.D20
         PNF_NSNNFNR(NS_T,NNF,NR) &
              =SNF_NSNNFNR(NS_He4,NNF,NR)*RT(NR,NS_T)*RKEV*1.D20
!              WRITE(26,'(A1,I3,I3,6E12.4)') ':', &
!              NT,NR,SS,SSB,SSF,RN(NR,2),RN(NR,3), &
!              SNF_NSNNFNR(NS_He4,NNF,NR)
      ENDDO

      DO NR=1,NRMAX
         ANE= RN(NR,NS_e)
         TE = RT(NR,NS_e)
         WF = RW(NR,NNBMAX+NNF)
         P1   = 3.D0*SQRT(0.5D0*PI)*AME/ANE *(ABS(TE)*RKEV/AME)**1.5D0
         VCD3 = P1*RN(NR,NS_D)*PZ(NS_D)**2/AMD
         VCT3 = P1*RN(NR,NS_T)*PZ(NS_T)**2/AMT
         VCA3 = P1*RN(NR,NS_He4)*PZ(NS_He4)**2/AMA
         VC3  = VCD3+VCT3+VCA3
         VCR  = VC3**(1.D0/3.D0)
         HYF=HY(VF/VCR)
         TAUS = 0.2D0*PA(NS_He4)*ABS(TE)**1.5D0 &
              /(PZ(NS_He4)**2*ANE*COULOG(1,2,ANE,TE))
         TAUF(NNF,NR)= 0.5D0*TAUS*(1.D0-HYF)
         RNF(NR,NNBMAX+NNF) &
              = 2.D0*LOG(1.D0+(VF/VCR)**3)*WF /(3.D0*(1.D0-HYF)*3.5D3)
         IF(RNF(NR,NNBMAX+NNF).GT.0.D0) THEN
            RTF(NR,NNBMAX+NNF)= WF/RNF(NR,NNBMAX+NNF)
         ELSE
            RTF(NR,NNBMAX+NNF)= 0.D0
         ENDIF
         PNFIN_NNFNR(NNF,NR) = WF*RKEV*1.D20/TAUF(nnf,NR)
         PNFCL_NSNNFNR(NS_e,  NNF,NR)=    (1.D0-HYF)*PNFIN_NNFNR(NNF,NR)
         PNFCL_NSNNFNR(NS_D,  NNF,NR)=(VCD3/VC3)*HYF*PNFIN_NNFNR(NNF,NR)
         PNFCL_NSNNFNR(NS_T,  NNF,NR)=(VCT3/VC3)*HYF*PNFIN_NNFNR(NNF,NR)
         PNFCL_NSNNFNR(NS_He4,NNF,NR)=(VCA3/VC3)*HYF*PNFIN_NNFNR(NNF,NR)
      ENDDO

      RETURN
      END SUBROUTINE TRNFDT

!     ***********************************************************

!           REACTION CROSS SECTION (MAXELLIAN) DT

!     ***********************************************************

      FUNCTION SIGMAM(TD,TT)
         USE bpsd_kinds
         USE libnf
         IMPLICIT NONE
         REAL(rkind),INTENT(IN)::  TD,TT
         REAL(rkind):: TI,SIGMAM

         TI = (3.D0*ABS(TD)+2.D0*ABS(TT))/5.D0

         SIGMAM=sigmav_nf(id_nf_dt,TI)*(1E-6)
         
         RETURN
         END FUNCTION SIGMAM

!     ***********************************************************

!           Nuclear reaction (DD)

!     ***********************************************************

      SUBROUTINE TRNFDD(nnf)

        USE TRCOMM
        USE libnf
         IMPLICIT NONE
         INteGER,INTENT(IN):: nnf
         REAL(rkind)   :: &
              ANE, EC, HYF, P1, PTNT, SS, SSB, TAUS, &
              TD, TE, TT, VC3, VCA3, VCD3, VCR, VCT3, VF, WF, ZEFFM, PB
         INTEGER:: NR,NNB,NS_beam
         REAL(rkind)   :: COULOG, HY   !FUNCTION
     
         VF =SQRT(2.D0*3.5D3 *RKEV/AMA) ! alpha velocity
   
         DO NR=1,NRMAX
             SNF_NSNR(1:NSMAX,NR)=0.D0
             PNF_NSNR(1:NSMAX,NR)=0.D0
             ANE= RN(NR,NS_e)
             TE = RT(NR,NS_e)
             TD = RT(NR,NS_D)
             TT = RT(NR,NS_T)
             SS = sigmav_nf(id_nf_dt,TD)
             IF(model_nnf(nnf).GE.13) THEN
               !  ZEFFM = (PZ(NS_D)*PZ(NS_D)*RN(NR,NS_D)/PA(NS_D) &
               !          +PZ(NS_T)*PZ(NS_T)*RN(NR,NS_T)/PA(NS_T) &
               !          +PZ(NS_He4)*PZ(NS_He4)*RN(NR,NS_He4)/PA(NS_He4) &
               !          +PZC(NR)*PZC(NR) *ANC(NR) /12.D0 &
               !          +PZFE(NR)*PZFE(NR)*ANFE(NR)/52.D0)/ANE
               ZEFFM = (PZ(NS_D  )*PZ(NS_D  )*RN(NR,NS_D  )/PA(NS_D  ) &
                       +PZ(NS_T  )*PZ(NS_T  )*RN(NR,NS_T  )/PA(NS_T  ) &
                       +PZ(NS_He4)*PZ(NS_He4)*RN(NR,NS_He4)/PA(NS_He4) &
                       +PZC(NR) *PZC(NR) *ANC(NR) /12.D0 &
                       +PZFE(NR)*PZFE(NR)*ANFE(NR)/52.D0)/ANE
                SSB=0.D0
                PB=0.D0
                DO NNB=1,NNBMAX
                   NS_beam=ns_nnb(nnb)
                   ! Critiral energy: (5.43) Takamura     
                   EC  = 14.8D0*TE*PA(NS_beam)*ZEFFM**(2.D0/3.D0)
                   ! Ion-electron slowing time: (3.22) Takamura: 
                   TAUS= 0.2D0*PA(NS_beam)*ABS(TE)**1.5D0 &
                        /(PZ(NS_beam)**2*ANE*COULOG(1,NS_beam,ANE,TE))
                   ! weight factor in SIGMAB 
                   PTNT= PNB_NNBNR(nnb,NR)*TAUS &
                        /(RN(NR,NS_beam)*1.D20*PNBENG(NNB)*RKEV)
                   ! fusion reaction rate 要確認！
                   SSB = SSB+PNB_NNBNR(NNB,NR)*SIGMAB(PNBENG(NNB),EC,TD,PTNT)
                   PB  = PB +PNB_NNBNR(NNB,NR)
                END DO
                IF(PB.NE.0.D0) THEN
                   SSB=SSB/PB
                ELSE
                   SSB=0.D0
                END IF
             ELSE
                SSB=0.D0
             ENDIF
             !    粒子数計算　T生成はDD反応の半分であるとして計算。 DHe3の粒子ソースとしての計算は行っていない。
             SNF_NSNNFNR(NS_T,NNF,NR) = 0.5*0.5*(SS+SSB)*RN(NR,2)*RN(NR,2)*1.D20
             !パワーバランスではHe3生成、p生成との足し合わせとするため、反応数はSNFの2倍
             PNF_NSNNFNR(NS_T,NNF,NR) = 2*SNF_NSNNFNR(NS_T,NNF,NR)*((1.01D3+3.03D3+0.82D3)/2)*RKEV*1.D20
             IF(MOD(model_nnf(nnf),2).EQ.1) SNF_NSNNFNR(NS_He4,NNF,NR)=0.D0
            !  本来はDは二つ消失。Hを考慮しない場合はSNFD=-SNFT
             SNF_NSNNFNR(NS_D,NNF,NR) =-SNF_NSNNFNR(NS_T,NNF,NR)
          ENDDO
 
   
         DO NR=1,NRMAX
            ANE= RN(NR,1)
            TE = RT(NR,1)
            WF = RW(NR,2)
            P1   = 3.D0*SQRT(0.5D0*PI)*AME/ANE *(ABS(TE)*RKEV/AME)**1.5D0
            VCD3 = P1*RN(NR,2)*PZ(NS_D)**2/AMD
            VCT3 = P1*RN(NR,3)*PZ(NS_T)**2/AMT
            VCA3 = P1*RN(NR,4)*PZ(NS_He4)**2/AMA
            VC3  = VCD3+VCT3+VCA3
            VCR  = VC3**(1.D0/3.D0)
            HYF=HY(VF/VCR)
            TAUS = 0.2D0*PA(NS_He4)*ABS(TE)**1.5D0 /(PZ(NS_He4)**2*ANE*COULOG(1,2,ANE,TE))
            ! TAUF(NR)= 0.5D0*TAUS*(1.D0-HYF)
            TAUF(nnf,NR) = 0.5D0*TAUS*(1.D0-HYF)
            RNF(NR,2)= 2.D0*LOG(1.D0+(VF/VCR)**3)*WF /(3.D0*(1.D0-HYF)*3.5D3)
            IF(RNF(NR,2).GT.0.D0) THEN
               RTF(NR,2)= WF/RNF(NR,2)
            ELSE
               RTF(NR,2)= 0.D0
            ENDIF
            PNFIN_NNFNR(NNF,NR) = WF*RKEV*1.D20/TAUF(nnf,NR)
            PNFCL_NSNNFNR(NS_e,  NNF,NR)=    (1.D0-HYF)*PNFIN_NNFNR(NNF,NR)
            PNFCL_NSNNFNR(NS_D,  NNF,NR)=(VCD3/VC3)*HYF*PNFIN_NNFNR(NNF,NR)
            PNFCL_NSNNFNR(NS_T,  NNF,NR)=(VCT3/VC3)*HYF*PNFIN_NNFNR(NNF,NR)
            PNFCL_NSNNFNR(NS_He4,NNF,NR)=(VCA3/VC3)*HYF*PNFIN_NNFNR(NNF,NR)

         ENDDO
   
         RETURN
         END SUBROUTINE TRNFDD
 

!     ***********************************************************

!           REACTION CROSS SECTION (MAXELLIAN) DD

!     ***********************************************************

         FUNCTION SIGMAM_DD(TD)

            ! not completed
    
          USE trcomm,ONLY: rkind
          IMPLICIT NONE
          REAL(rkind) TD,SIGMAM_DD
          REAL(rkind) TI,H,ARG
    
          TI=TD
         !  H  = TI/37.D0 + 5.45D0/(3.D0+TI*(1.D0+(TI/37.5D0)**2.8D0))
         !  ARG= -20.D0/TI**(1.D0/3.D0)
          !selection of fusion reaction cross section approximation
         !  IF(MDLSS=0) THEN
            ! IF(ARG.GE.-100.D0)  THEN
         !        SIGMAM_DD = 3.7D-18*TI**(-2.D0/3.D0)*EXP(ARG)/H
         !    ELSE
         !        SIGMAM_DD = 0.D0
         !    ENDIF
          !  ELSE
          
            IF(TI.GE.4) THEN 
               SIGMAM_DD = ((2.1069E-20)+ (-3.7748E-20)*TI + (1.1242E-20)*TI**2 + (-1.9831E-22)*TI**3 + (1.3421E-24)*TI**4)*1E-6
            ELSE
               SIGMAM_DD = (4.428*1E-20)*1E-6
            ENDIF    
         !  ENDIF  
    
          RETURN
        END FUNCTION SIGMAM_DD

!     ***********************************************************

!      REACTION RATE : TAIL

!     ***********************************************************

      FUNCTION SIGMAB(EB,EC,TI,PTNT)

!      APPROXIMATE FORMULA OF FUSION REACTION RATE
!         FOR SLOWING DOWN ION DISTRIBUTION
!      REF. TAKIZUKA AND YAMAGIWA, JAERI-M 87-066

!      EB   : BEAM ENERGY (KEV)
!      EC   : CRITICAL ENERGY (KEV)
!      TI   : TRITIUM TEMPERATURE (KEV)
!      PTNT : PB * TAUS / (ND * EB)

      USE trcomm,ONLY: rkind
      IMPLICIT NONE
      REAL(rkind) EB,EC,TI,PTNT,SIGMAB
      REAL(rkind) XB,XC,AG1,AG2,AG3,AL1,AL2,AL3,X1,X2,X3,X4,SA

      XB=SQRT(EB/127.D0)
      XC=SQRT(EC/127.D0)

      AG1= 1.06D0-0.058D0*SQRT(ABS(TI))
      AG2= 1.06D0-0.058D0*SQRT(ABS(TI))
      AG3= 0.33D0
      AL1= 1.D0/(0.40D0+0.032D0*TI)
      AL2=-1.D0/(0.91D0+0.016D0*SQRT(ABS(TI)))
      AL3=-0.11D0
      X1=0.97D0-AG1/AL1
      X2=0.97D0
      X3=0.97D0+(AG2-AG3)/(AL3-AL2)
      X4=0.97D0+3.D0

      IF(XB.LT.X1) THEN
         SA=0.D0
      ELSE
         SA=-SIGMBS(X1,AG1,AL1,XC)
         IF(XB.LT.X2) THEN
            SA=SA+SIGMBS(XB,AG1,AL1,XC)
         ELSE
            SA=SA+SIGMBS(X2,AG1,AL1,XC)-SIGMBS(X2,AG2,AL2,XC)
            IF(XB.LT.X3) THEN
               SA=SA+SIGMBS(XB,AG2,AL2,XC)
            ELSE
               SA=SA+SIGMBS(X3,AG2,AL2,XC)-SIGMBS(X3,AG3,AL3,XC)
               IF(XB.LT.X4) THEN
                  SA=SA+SIGMBS(XB,AG3,AL3,XC)
               ELSE
                  SA=SA+SIGMBS(X4,AG3,AL3,XC)
               ENDIF
            ENDIF
         ENDIF
      ENDIF
      SIGMAB=PTNT*1.67D-21*SA
      RETURN
      END FUNCTION SIGMAB

      FUNCTION SIGMBS(XX,RGG,RGL,XC)

      USE trcomm,ONLY: rkind
      IMPLICIT NONE
      REAL(rkind) :: XX,RGG,RGL,XC,SIGMBS
      REAL(rkind) :: X

      X=XX/XC
      SIGMBS=((RGG-0.97D0*RGL)/3.D0+XC*RGL/6.D0)*LOG(X*X*X+1.D0) &
           +XC*RGL*(X-LOG(X+1.D0)/2.D0 &
                   -ATAN((2.D0*X-1.D0)/SQRT(3.D0))/SQRT(3.D0))
      RETURN
    END FUNCTION SIGMBS

!     ***********************************************************

!           Nuclear reaction (D-He3)

!     ***********************************************************

    SUBROUTINE TRNFDHe3(NNF)

      USE TRCOMM
      IMPLICIT NONE
      INTEGER,INTENT(IN):: NNF
      REAL(rkind)   :: &
           ANE, HYF, P1, SS, TAUS, &
           TD, TE, THe3, VC3, VCA3, VCD3, VCR, VCHe3, VF, WF
      INTEGER:: NR
      REAL(rkind)   :: COULOG, HY   !FUNCTION

      VF =SQRT(2.D0*3.6D3 *RKEV/AMA)

      DO NR=1,NRMAX
         SNF_NSNR(1:NSMAX,NR)=0.D0
         PNF_NSNR(1:NSMAX,NR)=0.D0
         ANE  = RN(NR,NS_e)
         TE   = RT(NR,NS_e)
         TD   = RT(NR,NS_D)
         THe3 = RT(NR,NS_He3)
         SS = SIGMADHe3(TD,THe3)
         SNF_NSNR(NS_He4,NR) = SS*RN(NR,NS_D)*RN(NR,NS_T)*1.D20
         PNF_NSNR(NS_He4,NR) = SNF_NSNR(NS_He4,NR)*(3.5D3+14.7D3)*RKEV*1.D20
             ! proton energy added
             ! for simplicity
         IF(MOD(model_nnf(nnf),2).EQ.1) SNF_NSNR(NS_He4,NR) = 0.D0
         SNF_NSNR(NS_D,NR)   =-SNF_NSNR(NS_He4,NR)
         SNF_NSNR(NS_He3,NR) =-SNF_NSNR(NS_He4,NR)
      ENDDO

      DO NR=1,NRMAX
         ANE= RN(NR,NS_e)
         TE = RT(NR,NS_e)
         WF = RW(NR,NNBMAX+NNF)
         P1   = 3.D0*SQRT(0.5D0*PI)*AME/ANE *(ABS(TE)*RKEV/AME)**1.5D0
         VCD3  = P1*RN(NR,NS_D)*PZ(NS_D)**2/AMD
         VCHe3 = P1*RN(NR,NS_He3)*PZ(NS_He3)**2/AMHe3
         VCA3  = P1*RN(NR,NS_He4)*PZ(NS_He4)**2/AMA
         VC3  = VCD3+VCHe3+VCA3
         VCR  = VC3**(1.D0/3.D0)
         HYF=HY(VF/VCR)
         TAUS = 0.2D0*PA(NS_He4)*ABS(TE)**1.5D0 /(PZ(NS_He4)**2*ANE*COULOG(1,2,ANE,TE))
         TAUF(nnf,NR)= 0.5D0*TAUS*(1.D0-HYF)
         RNF(NR,NNBMAX+NNF) &
              = 2.D0*LOG(1.D0+(VF/VCR)**3)*WF /(3.D0*(1.D0-HYF)*3.6D3)
         IF(RNF(NR,NNBMAX+NNF).GT.0.D0) THEN
            RTF(NR,NNBMAX+NNF)= WF/RNF(NR,NNBMAX+NNF)
         ELSE
            RTF(NR,NNBMAX+NNF)= 0.D0
         ENDIF
         PNFIN_NNFNR(NNF,NR) = WF*RKEV*1.D20/TAUF(nnf,NR)
         PNFCL_NSNNFNR(NS_e,  NNF,NR)  =     (1.D0-HYF)*PNFIN_NNFNR(NNF,NR)
         PNFCL_NSNNFNR(NS_D,  NNF,NR)  =(VCD3 /VC3)*HYF*PNFIN_NNFNR(NNF,NR)
         PNFCL_NSNNFNR(NS_He3,NNF,NR)  =(VCHe3/VC3)*HYF*PNFIN_NNFNR(NNF,NR)
         PNFCL_NSNNFNR(NS_He4,NNF,NR)  =(VCA3 /VC3)*HYF*PNFIN_NNFNR(NNF,NR)
      ENDDO

      RETURN
      END SUBROUTINE TRNFDHe3

!     ***********************************************************

!           REACTION CROSS SECTION (MAXELLIAN)

!     ***********************************************************

      FUNCTION SIGMADHe3(TD,THe3)

      USE trcomm,ONLY: rkind
      USE libspl1d
      IMPLICIT NONE
      REAL(rkind) TD,THe3,TI,TIL,XRATEL,SIGMADHe3
      REAL(rkind),DIMENSION(10),save:: RENG,RRATE
      REAL(rkind),DIMENSION(10),save:: RENGL,RRATEL,DIFF
      REAL(rkind),DIMENSION(4,10),save:: URRATE
      INTEGER:: NX,IERR
      INTEGER,save:: INIT=0
      DATA RENG/1.D0, 2.D0, 5.D0, 10.D0, 20.D0, &
                50.D0,100.D0,200.D0,500.D0,1000.D0/
      DATA RRATE/1.0D-32, 1.4D-29, 6.7D-27, 2.3D-25, 3.8D-24, &
                 5.4D-23, 1.6D-22, 2.4D-22, 2.3D-22, 1.8D-22/

      IF(INIT.EQ.0) THEN
         
         DO NX=1,10
            RENGL(NX)=LOG(RENG(NX))
            RRATE(NX)=LOG(RRATEL(NX))
         ENDDO
         CALL SPL1D(RENGL,RRATEL,DIFF,URRATE,10,0,IERR)
         IF(IERR.NE.0) WRITE(6,*) 'XX SIGMADHe3: SPL1D: IERR=',IERR
         INIT=1
      ENDIF

      TI = (3.D0*ABS(TD)+2.D0*ABS(THe3))/5.D0
      IF(TI.GT.0.D0) THEN
         TIL=LOG(MAX(TI,1.D0))
         CALL SPL1DF(TIL,XRATEL,RENGL,URRATE,10,IERR)
         IF(IERR.NE.0) WRITE(6,*) 'XX SIGMADHe3: SPL1DF: IERR=',IERR
         IF(IERR.NE.0) WRITE(6,*) TIL,RENGL(1),RENGL(10)
         IF(IERR.NE.0) WRITE(6,*) TI,TD,THe3
         SIGMADHe3=EXP(XRATEL)
      ELSE
         SIGMADHe3=0.D0
      ENDIF
      RETURN
      END FUNCTION SIGMADHe3
END MODULE trpnf
