! trpnf.f90

MODULE trpnf

  PRIVATE
  PUBLIC tr_prep_pnf
  PUBLIC tr_pnf
  PRIVATE tr_nf_dd1
  PRIVATE tr_nf_dd2
  PRIVATE tr_nf_dt
  PRIVATE tr_nf_dhe3
  PRIVATE tr_nf_tt
  PRIVATE tr_nf_the3

CONTAINS

  SUBROUTINE tr_prep_pnf

    USE trcomm
    USE libnf
    IMPLICIT NONE
    INTEGER:: nnf,id_nf

    ! --- initialize fusion cross section and reaction rate ---
    
    CALL set_usigmav_nf

    DO nnf=1,nnfmax
       id_nf=model_nnf(nnf)
       nspmax_nnf(nnf)=nspmax_idnf(id_nf)
       nss1_nnf(nnf)=nss1_idnf(id_nf)
       nss2_nnf(nnf)=nss2_idnf(id_nf)
       nsp1_nnf(nnf)=nsp1_idnf(id_nf)
       nsp2_nnf(nnf)=nsp2_idnf(id_nf)
       nsp3_nnf(nnf)=nsp3_idnf(id_nf)
       eng1_nnf(nnf)=eng1_idnf(id_nf)
       eng2_nnf(nnf)=eng2_idnf(id_nf)
       eng3_nnf(nnf)=eng3_idnf(id_nf)
    END DO
    
  END SUBROUTINE tr_prep_pnf

  ! *** calculate fusion power ***

  SUBROUTINE tr_pnf

    USE trcomm
    USE libnf
    USE trlib
    IMPLICIT NONE
    REAL(rkind):: ANE,TE,P1,VC3,VCR,WF,VF,TAUS,HYF
    INTEGER:: ns,nnf,nr

    WRITE(6,*) '@@@ point 21181'
    
    SNF_NSNNFNR(1:NSMAX,1:NNFMAX,1:NRMAX)=0.D0   ! particle source
    PNFCL_NSNNFNR(1:NSMAX,1:NNFMAX,1:NRMAX)=0.D0 ! collisional transfer in
    SNFNN_NNFNR(1:NNFMAX,1:NRMAX)=0.D0  ! neutron number
    PNFNN_NNFNR(1:NNFMAX,1:NRMAX)=0.D0  ! neutron power
    
    DO nnf=1,nnfmax
       WRITE(6,*) '@@@ point 21182'
       SELECT CASE(model_nnf(nnf))
       CASE(id_nf_dd1)
          CALL tr_nf_dd1(nnf)
       CASE(id_nf_dd2)
          CALL tr_nf_dd2(nnf)
       CASE(id_nf_dt)
          CALL tr_nf_dt(nnf)
       CASE(id_nf_dhe3)
          CALL tr_nf_dhe3(nnf)
       CASE(id_nf_tt)
          CALL tr_nf_tt(nnf)
       CASE(id_nf_the3)
          CALL tr_nf_the3(nnf)
       END SELECT
    END DO

    WRITE(6,*) '@@@ point 21183'
    DO NR=1,NRMAX
       ANE= RN(NR,NS_e)
       TE = RT(NR,NS_e)
       P1   = 3.D0*SQRT(0.5D0*PI)*AME/ANE *(ABS(TE)*RKEV/AME)**1.5D0
       VC3=0.D0
    WRITE(6,*) '@@@ point 21184'
       DO NS=1,NSMAX
          IF(PZ(NS).GT.0.D0) &    ! sum over ions
               VC3=VC3+P1*RN(NR,NS)*PZ(NS)**2/(PA(NS)*AMP)
       END DO
    WRITE(6,*) '@@@ point 21185'
       VCR  = VC3**(1.D0/3.D0)
       DO nnf=1,nnfmax
          WRITE(6,*) '@@@ point 21186: nnf,ns=',nnf,ns
          ns=nsp1_nnf(nnf)
          WF = RW(NR,NNBMAX+NNF)
          WRITE(6,*) '@@@ point 21187: nnf,ns,pA=',nnf,ns,PA(ns)
          VF =SQRT(2.D0*eng1_nnf(nnf)*RKEV/(PA(ns)*AMP))
          WRITE(6,*) '@@@ point 21188: ns,nnf,ANE,TE=',ns,nnf,ANE,TE
          WRITE(6,*) '@@@ point 21188: VF,VCR=',VF,VCR
          HYF=HY(VF/VCR)
          WRITE(6,*) '@@@ point 21189: ns,nnf,ANE,TE=',ns,nnf,ANE,TE
          TAUS = 0.2D0*PA(ns)*ABS(TE)**1.5D0 &
               /(PZ(ns)**2*ANE*COULOG(1,ns,ANE,TE))
          TAUF(NNF,NR)= 0.5D0*TAUS*(1.D0-HYF)
       END DO
    END DO
    WRITE(6,*) '@@@ point 21189'
          
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
       RATE_NF=0.5D0*sigmav_nf(id_nf_DD1,PTD)  ! sigmav for dd1+dd2
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
       RATE_NF=0.5D0*sigmav_nf(id_nf_DD2,PTD)  ! sigmav for dd1+dd2
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
       RATE_NF=sigmav_nf(id_nf_DT,PTD)  ! sigmav for dt
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
       RATE_NF=sigmav_nf(id_nf_DHe3,PTD)  ! sigmav for dt
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
       RATE_NF=sigmav_nf(id_nf_TT,PTT)  ! sigmav for tt
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
       RATE_NF=sigmav_nf(id_nf_THe3,PTT)  ! sigmav for tt
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

END MODULE trpnf
