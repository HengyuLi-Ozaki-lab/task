! trpnf.f90

MODULE trpnf

  PRIVATE
  PUBLIC tr_prep_pnf
  PUBLIC tr_pnf
  PRIVATE tr_nf_dt
  PRIVATE tr_nf_dd1
  PRIVATE tr_nf_dd2
  PRIVATE tr_nf_dd3
  PRIVATE tr_nf_dhe31
  PRIVATE tr_nf_dhe32
  PRIVATE tr_nf_tt
  PRIVATE tr_nf_the31
  PRIVATE tr_nf_the32
  PRIVATE tr_nf_the33
  PRIVATE tr_nf_the34
  PRIVATE tr_nf_the35
  PRIVATE tr_nf_the36

CONTAINS

  SUBROUTINE tr_prep_pnf

    USE trcomm
    USE libnf
    IMPLICIT NONE
    INTEGER:: nnf,id_nf

    ! --- initialize fusion cross section and reaction rate ---
    
    DO nnf=1,nnfmax
       id_nf=id_nf_nnf(nnf)
       ns1_nnf(nnf)=ns1_idnf(id_nf)
       ns2_nnf(nnf)=ns2_idnf(id_nf)
       nsp_nnf(nnf)=nsp_idnf(id_nf)
       wgt_nnf(nnf)=wgt_idnf(id_nf)
       eng_nnf(nnf)=eng_idnf(id_nf)
       enn_nnf(nnf)=enn_idnf(id_nf)
    END DO
    
    WRITE(6,*) 'nnf: id_nf,ns1,ns2,nsp,wgt,eng,enn'
    DO nnf=1,nnfmax
       WRITE(6,'(5I4,3ES12.4)') &
            nnf,id_nf_nnf(nnf),ns1_nnf(nnf),ns2_nnf(nnf),nsp_nnf(nnf), &
            wgt_nnf(nnf),eng_nnf(nnf),enn_nnf(nnf)
    END DO

  END SUBROUTINE tr_prep_pnf

  ! *** calculate fusion power ***

  SUBROUTINE tr_pnf

    USE trcomm
    USE libnf
    USE trlib
    IMPLICIT NONE
    REAL(rkind):: ANE,TE,P1,VC3,VCR,WF,VF,TAUS,HYF
    REAL(rkind):: PN1,PN2,PT1,RATE_NF,SNF
    REAL(rkind):: wgt,eng,enn
    INTEGER:: nnf,nr,id_nf,ns1,ns2,nsp,ns

    SNF_NSNNFNR(1:NSMAX,1:NNFMAX,1:NRMAX)=0.D0   ! particle source
    PNFCL_NSNNFNR(1:NSMAX,1:NNFMAX,1:NRMAX)=0.D0 ! collisional transfer in
    SNFNN_NNFNR(1:NNFMAX,1:NRMAX)=0.D0  ! neutron number
    PNFNN_NNFNR(1:NNFMAX,1:NRMAX)=0.D0  ! neutron power
!   ref/trx-regress-capture ONLY (oracle correction #4): PNF_NSNNFNR is
!   accumulated with `+` at the bottom of this routine but was the one output
!   of the five not reset here, so the alpha birth power grew linearly in the
!   number of tr_pnf calls -- measured 1.0000x, 2.0019x, 3.0037x on successive
!   calls of the 10 keV DT deck, i.e. a factor of order the call count by the
!   end of a run.  The corrected build makes 46 calls over that deck's 5 steps.  Its four siblings are reset, which is what makes
!   the omission look unintended rather than a deliberate running total.
    PNF_NSNNFNR(1:NSMAX,1:NNFMAX,1:NRMAX)=0.D0 ! fusion power
    
    DO nnf=1,nnfmax
       id_nf=id_nf_nnf(nnf)
       ns1=ns1_nnf(nnf)
       ns2=ns2_nnf(nnf)
       wgt=wgt_nnf(nnf)
       nsp=nsp_nnf(nnf)
       eng=eng_nnf(nnf)
       enn=enn_nnf(nnf)
       DO NR=1,NRMAX
          PN1=RN(NR,ns1)
          PN2=RN(NR,ns2)
          PT1=RT(NR,ns1)
          RATE_NF=sigmav_nf(id_nf,PT1)
          SNF=wgt*PN1*PN2*1.D20*RATE_NF
          SNF_NSNNFNR(ns1,nnf,nr)=SNF_NSNNFNR(ns1,nnf,nr)-SNF
          SNF_NSNNFNR(ns2,nnf,nr)=SNF_NSNNFNR(ns2,nnf,nr)-SNF
          SNF_NSNNFNR(nsp,nnf,nr)=SNF_NSNNFNR(nsp,nnf,nr)+SNF
          PNF_NSNNFNR(nsp,nnf,nr)=PNF_NSNNFNR(nsp,nnf,nr)+eng*SNF*1.D20
          IF(enn.GT.0.D0) THEN
             SNFNN_NNFNR(nnf,nr)=SNFNN_NNFNR(nnf,nr)+SNF
             PNFNN_NNFNR(nnf,nr)=PNFNN_NNFNR(nnf,nr)+enn*SNF*1.D20
          END IF
       END DO
    END DO

    DO NR=1,NRMAX
       ANE= RN(NR,NS_e)
       TE = RT(NR,NS_e)
       P1   = 3.D0*SQRT(0.5D0*PI)*AME/ANE *(ABS(TE)*RKEV/AME)**1.5D0
       VC3=0.D0
       DO NS=1,NSMAX
          IF(PZ(NS).GT.0.D0) &    ! sum over ions
               VC3=VC3+P1*RN(NR,NS)*PZ(NS)**2/(PA(NS)*AMP)
       END DO
       VCR  = VC3**(1.D0/3.D0)
       DO nnf=1,nnfmax
          nsp=nsp_nnf(nnf)
          WF = RW(NR,NNBMAX+NNF)
!         ref/trx-regress-capture ONLY (oracle corrections #2 and #3).
!
!         #2  eng_nnf is ALREADY in joules -- libnf.f90 sets
!             eng_idnf(id_nf_dt)=3.5D3*RKEV -- so the RKEV that stood here
!             was applied twice.  Every other reader of eng honours the
!             joules convention (trpnf.f90's PNF_/PNFNN_ lines use eng and
!             enn bare), and both siblings apply exactly one RKEV to a
!             keV-valued energy: trx's own trpnb.f90 and kyoshimi's
!             tr/trpnf.f90.  Unfixed, VF came out 1.27e-8 of its true value
!             and TAUF was noise -- negative at Te=10 keV.
!
!         #3  ns is the terminated counter of the DO NS=1,NSMAX loop above,
!             so it held NSMAX+1, not a species.  For this deck that is 5,
!             and trinit.f90's `DO NS=5,NSM` fallback gives PA(5)=PZ(5)=1
!             instead of the alpha's PA(4)=4, PZ(4)=2.  nsp -- the reaction's
!             product species, assigned just above and otherwise unused --
!             is the intended index.  TAUS happens to be unaffected here
!             (PA/PZ**2 is 1 both ways), so the error reaches TAUF only
!             through VF, which was 2x too large.
          VF =SQRT(2.D0*eng_nnf(nnf)/(PA(nsp)*AMP))
          HYF=HY(VF/VCR)
          TAUS = 0.2D0*PA(nsp)*ABS(TE)**1.5D0 &
               /(PZ(nsp)**2*ANE*COULOG(1,nsp,ANE,TE))
          TAUF(NNF,NR)= 0.5D0*TAUS*(1.D0-HYF)
       END DO
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

END MODULE trpnf
