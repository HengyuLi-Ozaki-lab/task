! libnf.f90

MODULE libnf_local
  USE bpsd_kinds
  INTEGER:: id_nf_local
  ! pm_local receives PA(nsp_idnf(id_nf))*AMP (~6.7e-27 kg) and is then a
  ! DIVISOR in sigmav_nf_local.  Declared INTEGER upstream, which truncates it
  ! to 0 and divides by zero the moment that path is reached.
  REAL(rkind):: pm_local
  REAL(rkind):: temperature_local
END MODULE libnf_local

MODULE libnf
  USE bpsd_kinds
  ! WAIVER, deliberate and load-bearing for Task 7.  The port plan said to
  ! drop this import and take AMM from TRCOMM instead, because bpsd's AMP is
  ! CODATA-2018 (1.67262192369D-27) while tr's AMM is CODATA-2006
  ! (1.672621637D-27) -- a relative difference of 1.714e-7, about 1700x the
  ! 1e-10 gate Task 7 will apply.
  !
  ! It is kept because dropping it now would edit more of the upstream file
  ! than the port otherwise touches, and because the only AMP consumer
  ! (sigmav_nf_local) is PRIVATE and unreachable today: RKEV inside
  ! set_usigmav_nf resolves to TRCOMM's CODATA-2006 value, so nothing shipped
  ! here is affected.  Verified: eng_idnf(DT) = 5.6076177045D-13, bit-equal to
  ! 3.5D3 * 1.602176487D-19 * 1D3.
  !
  ! Nothing here may rely on that.  A new routine naming AEE or AMP without an
  ! explicit `USE trcomm,ONLY:` silently picks up CODATA-2018 and lands ~1.7e-7
  ! off, ~1700x the 1e-10 gate, with no obvious cause.  RKEV is different: it
  ! is not in bpsd_constants at all, so naming it bare is a compile error
  ! rather than a silent wrong value.  Consumers should import from this
  ! module with an explicit ONLY list, as trpnf_multi does.
  USE bpsd_constants

  ! Fusion model
  !   model_pnf=0 : no fusion reaction
  !   model_pnf=1 : D + T -> He4 + n              nnfmax=1  nsmax=4 DT
  !   model_pnf=2 : D + D -> T + p                nnfmax=4  nsmax=6 DD1 DD2
  !                 D + D -> He3 + n                                DD3
  !                 D + T -> He4 + n                                DT
  !   model_pnf=3 : D + D -> T + p                nnfmax=6  nsmax=6 DD1 DD2
  !                 D + D -> He3 + n                                DD3
  !                 D + T -> He4 + n                                DT
  !                 D + He3 -> He4 + p                              DHe31 DHe32
  !   model_pnf=4 : D + D -> T + p                nnfmax=13 nsmax=7 DD1 DD2
  !                 D + D -> He3 + n                                DD3
  !                 D + T -> He4 + n                                DT
  !                 D + He3 -> He4 + p                              DH31 DHe32
  !                 T + T -> He4 + 2n                               TT
  !                 T + He3 -> He4 + p + n                          THe31 THe32
  !                 T + He3 -> He4 + D                              THe33 THe34
  !                 T + He3 -> He5 + p                              THe35 THe36
  
  !   model_pnf=12: D + D -> T + p   | T + He4/2  nnfmax=4  nsmax=4 DD1 DD2
  !                 D + D -> He3 + n ! He4 + n                      DD3
  !                 D + T -> He4 + n                                DT
  !   model_pnf=14: D + D -> T + p   ! T +He4/2   nnfmax=13 nsmax=4 DD1 DD2
  !                 D + D -> He3 + n ! He4 + n                      DD3
  !                 D + T -> He4 + n                                DT
  !                 D + He3 -> He4 + p                              DHe31 DHe32
  !                 T + T -> He4 + 2n                               TT
  !                 T + He3 -> He4 + p + n                          THe31 THe32
  !                 T + He3 -> He4 + D                              THe33 THe34
  !                 T + He3 -> He5 + p ! He4 + p                    THe35 THe36
  ! Fusion reaction id
  
  INTEGER,PARAMETER,PUBLIC:: id_nf_DT=    1 ! D + T   -> <He4> +  n
  INTEGER,PARAMETER,PUBLIC:: id_nf_DD1=   2 ! D + D   -> <T>   +  p
  INTEGER,PARAMETER,PUBLIC:: id_nf_DD2=   3 ! D + D   ->  T    + <p> 
  INTEGER,PARAMETER,PUBLIC:: id_nf_DD3=   4 ! D + D   -> <He3> +  n
  INTEGER,PARAMETER,PUBLIC:: id_nf_DHe31= 5 ! D + He3 -> <He4> +  p
  INTEGER,PARAMETER,PUBLIC:: id_nf_DHe32= 6 ! D + He3 ->  He4  + <p>
  INTEGER,PARAMETER,PUBLIC:: id_nf_TT=    7 ! T + T   -> <He4> + 2n
  INTEGER,PARAMETER,PUBLIC:: id_nf_THe31= 8 ! T + He3 -> <He4> +  p  + n
  INTEGER,PARAMETER,PUBLIC:: id_nf_THe32= 9 ! T + He3 ->  He4  + <p> + n
  INTEGER,PARAMETER,PUBLIC:: id_nf_THe33=10 ! T + He3 -> <He4> +  D
  INTEGER,PARAMETER,PUBLIC:: id_nf_THe34=11 ! T + He3 ->  He4  + <D>
  INTEGER,PARAMETER,PUBLIC:: id_nf_THe35=12 ! T + He3 -> <He5> +  p
  INTEGER,PARAMETER,PUBLIC:: id_nf_THe36=13 ! T + He3 ->  He5  + <p>

  INTEGER,DIMENSION(:),ALLOCATABLE:: id_nf_nnf
  
  Integer,DIMENSION(13),PUBLIC:: &
       ns1_idnf,ns2_idnf,nsp_idnf
  REAL(rkind),DIMENSION(13),PUBLIC::  &
       wgt_idnf,eng_idnf,enn_idnf

       ! Duane coef (NEL Formulary 2019)

  REAL(rkind),DIMENSION(5,6):: &
       Duane=reshape((/46.097D0, 372.D0, 4.36D-4,  1.220D0, 0.D0, &
                       47.88D0,  482.D0, 3.08D-4,  1.177D0, 0.D0, &
                       45.95D0,  5.02D4, 1.368D-2, 1.076D0, 409.D0, &
                       89.27D0,  2.59D4, 3.98D-3,  1.297D0, 647.D0, &
                       38.39D0,  448.D0, 1.02D-3,  2.09D0,  0.D0, &
                       123.1D0, 1.125D4, 0.D0,     0.D0,    0.D0/), &
                       (/5,6/))

  ! temperature range for reaction rate sigmav
    
  REAL(rkind),DIMENSION(10):: &
       tempa=(/ 1.D0, 2.D0, 5.D0, 10.D0, 20.D0, &
       50.D0, 100.D0, 200.D0, 500.D0, 1000.D0 /)
  
  ! reaction rate sigmav for DD
  REAL(rkind),DIMENSION(10):: &
       svnf_dd=(/ 1.5D-21, 5.4D-21, 1.8D-19, 1.2D-18, 5.2D-18, &
                  2.1D-17, 4.5D-17, 8.8D-17, 1.8D-16, 2.2D-16 /)
  ! reaction rate sigmav for DT
  REAL(rkind),DIMENSION(10):: &
       svnf_dt=(/ 5.5D-21, 2.6D-19, 1.3D-17, 1.1D-16, 4.2D-16, &
                  8.7D-16, 8.5D-16, 6.3D-16, 3.7D-16, 2.7D-16 /)
  ! reaction rate sigmav for DHe3
  REAL(rkind),DIMENSION(10):: &
       svnf_dhe3=(/ 1.0D-26, 1.4D-23, 6.7D-21, 2.3D-19, 3.8D-18, &
                    5.4D-17, 1.6D-16, 2.4D-16, 2.3D-16, 1.8D-16 /)
  ! reaction rate sigmav for TT
  REAL(rkind),DIMENSION(10):: &
       svnf_tt=(/ 3.3D-22, 7.1D-21, 1.4D-19, 7.2D-19, 2.5D-18, &
                  8.7D-18, 1.9D-17, 4.2D-17, 8.4D-17, 8.0D-17 /)
  ! reaction rate sigmav for THe3
  REAL(rkind),DIMENSION(10):: &
       svnf_the3=(/ 1.0D-28, 1.0D-25, 2.1D-22, 1.2D-20, 2.6D-19, &
                    5.3D-18, 2.7D-17, 9.2D-17, 2.9D-16, 5.2D-16 /)

  ! Mass of incident particle

  REAL(rkind),DIMENSION(4,10):: &
       usvnf_dd,usvnf_dt,usvnf_dhe3,usvnf_tt,usvnf_the3
  REAL(rkind),DIMENSION(10):: &
       dsvnf,tempa_log

  ! *** library subroutines ***

  PUBLIC set_usigmav_nf  ! set_usigmav_nf
  PUBLIC sigmav_nf       ! sigmav_nf(id_nf,temperature) Maxwellian fitting
  PUBLIC nf_finalize     ! release per-session state at teardown
  PUBLIC nf_reset_log    ! re-arm the once-per-site logging latches

  ! sigmav_nf is a FUNCTION whose signature is pinned by test_libnf.py's
  ! ctypes binding, so it reports failure out-of-band here instead of by
  ! STOP.  These are the codes it reports; the two observables that carry
  ! them are declared below.
  INTEGER,PARAMETER,PUBLIC:: NF_ERR_ID   = 1  ! id_nf outside 1..13
  INTEGER,PARAMETER,PUBLIC:: NF_ERR_TEMP = 2  ! temperature NaN or > 1000 keV
  INTEGER,PARAMETER,PUBLIC:: NF_ERR_SPL  = 3  ! SPL1DF evaluation failed
  ! Two observables, because one cannot serve both jobs.
  !
  ! nf_last_error is a PER-CALL code: tr_pnf clears it at entry and reads it
  ! after its loop, so it describes that call only.  It cannot be the record
  ! of whether a run failed -- tr_pnf runs ~L+2 times per timestep, so a
  ! failure during the converge loop is erased by the next clean call.
  !
  ! nf_error_count saturates rather than wrapping, because signed overflow
  ! is UB and -fcheck=all does not catch it.  It gets large fast: one count
  ! per failing (reaction, radius) per tr_pnf call, measured 14300 over 5
  ! steps at nnfmax=13/NRMAX=50 with every point failing.
  !
  ! nf_error_count is the DURABLE one: incremented at every failure and never
  ! cleared by tr_pnf, so it survives the whole run.  It is what a caller or
  ! a test should assert on.  It is reset by nf_finalize (teardown) and by
  ! tr_init.  It does NOT gate the logging -- nf_logged below does; the
  ! counter keeps counting after the messages stop.
  INTEGER,PUBLIC:: nf_last_error  = 0
  INTEGER,PUBLIC:: nf_error_count = 0
  ! One latch per REPORTING SITE, not per returned code.  Gating every site
  ! on one flag means that after the first fault of a run a fault of a
  ! different kind prints nothing -- and NaN and over-range both return
  ! NF_ERR_TEMP, so keying the latch on the code would silence the NaN
  ! message after any over-range one.  NaN is the more alarming of the two:
  ! it exists because NaN fails every ordered comparison and would otherwise
  ! reach LOG10.  The SPL1DF site is likewise the only place the offending
  ! id_nf and temperature are ever printed TOGETHER (id_nf alone appears at
  ! the bad-id and NaN sites).
  INTEGER,PARAMETER,PRIVATE:: NF_LOG_ID   = 1
  INTEGER,PARAMETER,PRIVATE:: NF_LOG_NAN  = 2
  INTEGER,PARAMETER,PRIVATE:: NF_LOG_HIGH = 3
  INTEGER,PARAMETER,PRIVATE:: NF_LOG_SPL  = 4
  INTEGER,PARAMETER,PRIVATE:: NF_LOG_MAX  = 4
  LOGICAL,DIMENSION(NF_LOG_MAX),PRIVATE:: nf_logged = .FALSE.
  ! The caller-side summary latch lives here too, so it is reset by the same
  ! tr_init sweep.  A SAVEd local in trcalc would survive finalize and go
  ! quiet for the rest of the process after one run's first fault.
  LOGICAL,PUBLIC:: nf_summary_logged = .FALSE.

  ! sigma_nf and sigmav_nf_int are NOT exported, on measured grounds:
  !
  !   sigma_nf indexes Duane(5,6) -- an NRL-ordered table whose columns are
  !   (DD,DD,DT,DHe3,TT,THe3), confirmed by the D-T resonance amplitude
  !   A2=5.02D4 sitting in column 3 -- with id_nf, whose enumeration is
  !   (DT,DD1,DD2,DD3,DHe31,DHe32,...).  So sigma_nf(id_nf_DT) reads a D-D
  !   coefficient set.  Its guard also admits only 1..6 while id_nf runs to 13.
  !
  !   sigmav_nf_int did not return within 45 s for (DT, 10 keV).
  !
  ! Both also STOP on bad input, which kills the host process from inside a
  ! dlopened .so (CLAUDE.md).  Left PRIVATE rather than deleted so the upstream
  ! file stays diffable.  Fixing them is not Task 5 -- reported upstream.
  PRIVATE:: sigma_nf, sigmav_nf_int, sigmav_nf_local
  ! sigmav_nfb_int was PUBLIC upstream but is defined nowhere in the tree
  ! (grep over all of trx/ finds only that one declaration).  With no
  ! module-level IMPLICIT NONE it silently became a public REAL module
  ! VARIABLE.  Dropped rather than carried.

CONTAINS
  
  ! Re-arm the one-line-per-site logging without touching the tables.
  ! Called by tr_prep, so the unit of silence is one PREPARE, not one
  ! process: trmenu's R handler re-preps every interactive run, and
  ! set_param invalidates g_prepared on the library side.  Two paths
  ! deliberately do NOT re-arm, being continuations of the same prepared
  ! run: trmenu's C/CONT handler, and successive tr_run calls on one
  ! handle.  tr_init and nf_finalize also call this.
  SUBROUTINE nf_reset_log
    IMPLICIT NONE
    nf_logged(:)      = .FALSE.
    nf_summary_logged = .FALSE.
    RETURN
  END SUBROUTINE nf_reset_log

  ! Release the per-session reaction table.  Called from the same teardown
  ! points as DEALLOCATE_TRCOMM (tr_api_finalize, trmain), not from
  ! set_usigmav_nf: freeing on the model_pnf=0 path would add a free() to
  ! the default sequence in any process that had run model_pnf>0, which is
  ! the heap perturbation the bit-exactness note in trcomm_nf is about.
  ! trcomm/trcomm_nf cannot do this themselves -- libnf's subroutine-scoped
  ! USE trcomm makes trcomm.mod a build prerequisite of libnf.o, so a
  ! USE libnf from either would be a module cycle.
  !
  ! Does NOT reset the _idnf tables (ns1/ns2/nsp/wgt/eng/enn), which are also
  ! model_pnf-dependent and keep the dead session's values.  Harmless on both
  ! routes into tr_prep_pnf: after a teardown its .NOT.ALLOCATED(id_nf_nnf)
  ! guard fires first, because this routine freed the table; within one
  ! session the nnfmax<=0 check does.  And set_usigmav_nf rewrites ids 1-4
  ! unconditionally and 5-13 under model_pnf>=3, covering every slot any
  ! nnfmax reaches.  Noted so the omission reads as a decision.
  SUBROUTINE nf_finalize
    IMPLICIT NONE
    IF(ALLOCATED(id_nf_nnf)) DEALLOCATE(id_nf_nnf)
    nf_last_error  = 0
    nf_error_count = 0
    CALL nf_reset_log
    RETURN
  END SUBROUTINE nf_finalize

  ! ierr_nf reports failure instead of the bare STOPs upstream uses: every
  ! one of them is reachable through libtrapi.so and would take down the
  ! host process -- pytest, or the MCP server -- rather than returning
  ! (CLAUDE.md, Fortran library discipline; issue #142).  tr_prep is the
  ! only caller, so widening the signature costs nothing.
  !   1 = spline setup failed        2 = undefined model_pnf
  !   3 = a required ion species is absent from the composition
  !
  ! --- set spline coefficients for reaction rate sigmav
  SUBROUTINE set_usigmav_nf(ierr_nf)
    USE trcomm
    ! NS_* reach trx's libnf only via trx/trcomm.f90:5's USE plcomm; nothing in
    ! tr/ does that.  ONLY: is deliberate -- tr's trcomm and plcomm export
    ! colliding names, so a bare USE plcomm here would compile today and break
    ! on the first Task-6 edit near NSMAX/PA/PZ.
    USE plcomm,ONLY: NS_D,NS_T,NS_He4,NS_He3,NS_H,NS_He5
    USE libspl1d
    IMPLICIT NONE
    INTEGER,INTENT(OUT):: ierr_nf
    REAL(rkind),DIMENSION(10):: dsvnf
    INTEGER:: ntemp,id,ierr

    ierr_nf = 0

    ! Spline setup moved AHEAD of the model_pnf dispatch.  Upstream it sits
    ! after CASE(0)'s RETURN, so at model_pnf=0 tempa_log stays all-zero and any
    ! later sigmav_nf call hits SPL1DF's degenerate-grid guard and STOPs the
    ! host process.  Order-independent: this block reads only tempa/svnf_* and
    ! writes only tempa_log/usvnf_*, none of which the model_pnf code touches.
    DO ntemp=1,10
       tempa_log(ntemp)=LOG10(tempa(ntemp))
    END DO
    
    CALL SPL1D(tempa_log,svnf_dt,  dsvnf,usvnf_dt,  10,0,ierr)
    id=1
    IF(ierr.EQ.0) THEN
       CALL SPL1D(tempa_log,svnf_dd,  dsvnf,usvnf_dd,  10,0,ierr)
       id=2
    ENDIF
    IF(ierr.EQ.0) THEN
       CALL SPL1D(tempa_log,svnf_dhe3,dsvnf,usvnf_dhe3,10,0,ierr)
       id=3
    END IF
    IF(ierr.EQ.0) THEN
       CALL SPL1D(tempa_log,svnf_tt,  dsvnf,usvnf_tt,  10,0,ierr)
       id=4
    END IF
    IF(ierr.EQ.0) THEN
       CALL SPL1D(tempa_log,svnf_the3,dsvnf,usvnf_the3,10,0,ierr)
       id=5
    END IF
    IF(ierr.NE.0) THEN
       WRITE(6,'(A,I4)') 'XX SPL1D error in set_usvnf: id=',id
       ierr_nf = 1
       RETURN
    END IF

    SELECT CASE(model_pnf)
    CASE(0) ! no fusion reaction
       nnfmax=0
       ! Deliberately does NOT free id_nf_nnf.  Freeing here would put a
       ! new free() on the model_pnf=0 path, between tr_api_init's
       ! ALLOCATE_TRCOMM and tr_prep's own allocations, in any process that
       ! previously ran model_pnf>0 -- exactly the mid-sequence heap
       ! perturbation trcomm_nf's note says has to be measured on Linux.
       ! nf_finalize does it at teardown instead, so a second session's
       ! default path has the same allocation history as a first one's.
       !
       ! Consequence, recorded because it is a real coupling: within ONE
       ! session, going model_pnf>0 -> 0 leaves the table allocated, so
       ! tr_prep_pnf's ALLOCATED(id_nf_nnf) guard cannot prove
       ! set_usigmav_nf ran in this configuration.  The nnfmax<=0 check
       ! immediately after it is what actually refuses that case.
       RETURN
    CASE(1) ! DT
       nnfmax=1
    CASE(2,12) ! DT+DD 
       nnfmax=4
    CASE(3)    ! DT+DD+DHe3
       nnfmax=6
    CASE(4,14) ! DT+DD+DHe3+TT+THe3
       nnfmax=13
    CASE DEFAULT
       WRITE(6,*) 'XX Error libnf: undefined model_pnf: model_pnf=',model_pnf
       ierr_nf = 2
       RETURN
    END SELECT

    IF(ALLOCATED(id_nf_nnf)) DEALLOCATE(id_nf_nnf)
    ALLOCATE(id_nf_nnf(nnfmax))

    SELECT CASE(model_pnf)
    CASE(1)
       id_nf_nnf(1)=id_nf_dt
    CASE(2,12)
       id_nf_nnf(1)=id_nf_dt
       id_nf_nnf(2)=id_nf_dd1
       id_nf_nnf(3)=id_nf_dd2
       id_nf_nnf(4)=id_nf_dd3
    CASE(3)
       id_nf_nnf(1)=id_nf_dt
       id_nf_nnf(2)=id_nf_dd1
       id_nf_nnf(3)=id_nf_dd2
       id_nf_nnf(4)=id_nf_dd3
       id_nf_nnf(5)=id_nf_dhe31
       id_nf_nnf(6)=id_nf_dhe32
    CASE(4,14)
       id_nf_nnf(1)=id_nf_dt
       id_nf_nnf(2)=id_nf_dd1
       id_nf_nnf(3)=id_nf_dd2
       id_nf_nnf(4)=id_nf_dd3
       id_nf_nnf(5)=id_nf_dhe31
       id_nf_nnf(6)=id_nf_dhe32
       id_nf_nnf(7)=id_nf_tt
       id_nf_nnf(8)=id_nf_the31
       id_nf_nnf(9)=id_nf_the32
       id_nf_nnf(10)=id_nf_the33
       id_nf_nnf(11)=id_nf_the34
       id_nf_nnf(12)=id_nf_the35
       id_nf_nnf(13)=id_nf_the36
    CASE DEFAULT
       WRITE(6,*) 'XX Error libnf: undefined model_pnf: model_pnf=',model_pnf
       ierr_nf = 2
       RETURN
    END SELECT

    ! DEVIATION FROM trx (upstream defect): 13 -> 14, moved to CASE(4,14).
    !
    ! Upstream reads CASE(1,12,13). 13 is accepted by neither SELECT above
    ! and is rejected outright by the first, so that label is dead, while 14
    ! -- which CASE(4,14) above accepts and the header table documents --
    ! matched nothing here and fell through to CASE DEFAULT, which upstream
    ! is a STOP -- so on the unported original model_pnf=14 killed the
    ! process on a value the routine calls valid.  In this tree that branch
    ! had already become ierr_nf=2, so the symptom here was a refused run.
    !
    ! 14 belongs with 4, not with 1/12, even though the header table calls
    ! it an nsmax=4 variant. What matters is which species the nsp_idnf /
    ! ns1_idnf / ns2_idnf fill below actually indexes, and at model_pnf=14
    ! that is the same six as at model_pnf=4: the only .EQ.14 remap in this
    ! file is the32 (below), so H survives on dd2, dhe32 and the36, He5 on
    ! the35, and He3 is ns2 for all seven DHe3/THe3 reactions. Reading the
    ! header table's intent instead of the code costs a real abort here.
    !
    ! CAVEAT for model_pnf=12, left as upstream: nsp_idnf(id_nf_dd3) is
    ! inverted relative to every sibling remap -- it hands He3 to the
    ! reduced variant and He4 to the full one, the opposite of dd2 and
    ! the32 -- so 12 does index He3, which this branch does not check.
    ! Correcting it changes which species receives the D-D neutron branch,
    ! i.e. it is a numerical change, and belongs with the Task 7 validation
    ! alongside the incomplete .EQ.14 remap set.
    SELECT CASE(model_pnf)
    CASE(1,12)
       IF(NS_D*NS_T*NS_He4.EQ.0) THEN
          IF(NS_D.EQ.0) WRITE(6,*)   'XX Error: libnf: NS_D=0'
          IF(NS_T.EQ.0) WRITE(6,*)   'XX Error: libnf: NS_T=0'
          IF(NS_He4.EQ.0) WRITE(6,*) 'XX Error: libnf: NS_He4=0'
          ierr_nf = 3
          RETURN
       END IF
    CASE(2,3)
       IF(NS_D*NS_T*NS_He4*NS_H*NS_He3.EQ.0) THEN
          IF(NS_D.EQ.0)   WRITE(6,*) 'XX Error: libnf: NS_D=0'
          IF(NS_T.EQ.0)   WRITE(6,*) 'XX Error: libnf: NS_T=0'
          IF(NS_H.EQ.0)   WRITE(6,*) 'XX Error: libnf: NS_H=0'
          IF(NS_He4.EQ.0) WRITE(6,*) 'XX Error: libnf: NS_He4=0'
          IF(NS_He3.EQ.0) WRITE(6,*) 'XX Error: libnf: NS_He3=0'
          ierr_nf = 3
          RETURN
       END IF
    CASE(4,14)
       IF(NS_D*NS_T*NS_He4*NS_H*NS_He3*NS_He5.EQ.0) THEN
          IF(NS_D.EQ.0)   WRITE(6,*) 'XX Error: libnf: NS_D=0'
          IF(NS_T.EQ.0)   WRITE(6,*) 'XX Error: libnf: NS_T=0'
          IF(NS_H.EQ.0)   WRITE(6,*) 'XX Error: libnf: NS_H=0'
          IF(NS_He4.EQ.0) WRITE(6,*) 'XX Error: libnf: NS_He4=0'
          IF(NS_He3.EQ.0) WRITE(6,*) 'XX Error: libnf: NS_He3=0'
          IF(NS_He5.EQ.0) WRITE(6,*) 'XX Error: libnf: NS_He5=0'
          ierr_nf = 3
          RETURN
       END IF
    CASE DEFAULT
       ! 'libnb' upstream -- this is libnf; the message named the wrong module.
       WRITE(6,*) 'XX Error libnf: undefined model_pnf: model_pnf=',model_pnf
       ierr_nf = 2
       RETURN
    END SELECT

    
    
    ns1_idnf(id_nf_dt)=NS_D
    ns2_idnf(id_nf_dt)=NS_T
    wgt_idnf(id_nf_dt)=1.0D0
    nsp_idnf(id_nf_dt)=NS_He4
    eng_idnf(id_nf_dt)=3.5D3*RKEV
    enn_idnf(id_nf_dt)=14.1D3*RKEV

    ns1_idnf(id_nf_dd1)=NS_D
    ns2_idnf(id_nf_dd1)=NS_D
    wgt_idnf(id_nf_dd1)=0.5D0
    nsp_idnf(id_nf_dd1)=NS_T
    eng_idnf(id_nf_dd1)=1.01D3*RKEV
    enn_idnf(id_nf_dd1)=0.D0
    
    ns1_idnf(id_nf_dd2)=NS_D
    ns2_idnf(id_nf_dd2)=NS_D
    wgt_idnf(id_nf_dd2)=0.5D0
    IF(model_pnf.EQ.12) THEN
       nsp_idnf(id_nf_dd2)=NS_He4
    ELSE
       nsp_idnf(id_nf_dd2)=NS_H
    END IF
    eng_idnf(id_nf_dd2)=3.02D3*RKEV
    ! Upstream names dd3 here, inside the dd2 block, and assigns dd3's real
    ! value further down -- so enn_idnf(id_nf_dd2) was the one slot of the
    ! thirteen never written, and tr_pnf branches on it (IF(enn > 0)).
    ! 0 is also the physically right value: dd2 is D + D -> T + <p>, a
    ! charged-particle branch that releases no neutron.
    enn_idnf(id_nf_dd2)=0.D0

    ns1_idnf(id_nf_dd3)=NS_D
    ns2_idnf(id_nf_dd3)=NS_D
    wgt_idnf(id_nf_dd3)=0.5D0
    IF(model_pnf.EQ.12) THEN
       nsp_idnf(id_nf_dd3)=NS_He3
    ELSE
       nsp_idnf(id_nf_dd3)=NS_He4
    END IF
    eng_idnf(id_nf_dd3)=0.82D3*RKEV
    enn_idnf(id_nf_dd3)=2.45D3*RKEV

    IF(model_pnf.GE.3) THEN
       ns1_idnf(id_nf_dhe31)=NS_D
       ns2_idnf(id_nf_dhe31)=NS_He3
       wgt_idnf(id_nf_dhe31)=1.D0
       nsp_idnf(id_nf_dhe31)=NS_He4
       eng_idnf(id_nf_dhe31)=3.6D3*RKEV
       enn_idnf(id_nf_dhe31)=0.D0

       ns1_idnf(id_nf_dhe32)=NS_D
       ns2_idnf(id_nf_dhe32)=NS_He3
       wgt_idnf(id_nf_dhe32)=1.D0
       nsp_idnf(id_nf_dhe32)=NS_H
       eng_idnf(id_nf_dhe32)=14.7D3*RKEV
       enn_idnf(id_nf_dhe32)=0.D0

       ns1_idnf(id_nf_tt)=NS_T
       ns2_idnf(id_nf_tt)=NS_T
       wgt_idnf(id_nf_tt)=1.D0
       nsp_idnf(id_nf_tt)=NS_He4
       eng_idnf(id_nf_tt)=1.25D3*RKEV  ! 11.3MeV*0.25/2.25
       enn_idnf(id_nf_tt)=10.05D3*RKEV ! 11.3Mev*2.00/2.25

       ns1_idnf(id_nf_the31)=NS_T
       ns2_idnf(id_nf_the31)=NS_He3
       wgt_idnf(id_nf_the31)=0.51D0
       nsp_idnf(id_nf_the31)=NS_He4
       eng_idnf(id_nf_the31)=1.34D3*RKEV ! 12.1MeV*0.25/2.25
       enn_idnf(id_nf_the31)=5.38D3*RKEV ! 12.1Mev*1.00/2.25

       ns1_idnf(id_nf_the32)=NS_T
       ns2_idnf(id_nf_the32)=NS_He3
       wgt_idnf(id_nf_the32)=0.51D0
       IF(model_pnf.EQ.14) THEN
          nsp_idnf(id_nf_the32)=NS_He4
       ELSE
          nsp_idnf(id_nf_the32)=NS_H
       END IF
       eng_idnf(id_nf_the32)=5.38D3*RKEV ! 12.1MeV*1.0/2.25
       enn_idnf(id_nf_the32)=0.D0

       ns1_idnf(id_nf_the33)=NS_T
       ns2_idnf(id_nf_the33)=NS_He3
       wgt_idnf(id_nf_the33)=0.43D0
       nsp_idnf(id_nf_the33)=NS_He4
       eng_idnf(id_nf_the33)=4.8D3*RKEV
       enn_idnf(id_nf_the33)=0.D0

       ns1_idnf(id_nf_the34)=NS_T
       ns2_idnf(id_nf_the34)=NS_He3
       wgt_idnf(id_nf_the34)=0.43D0
       nsp_idnf(id_nf_the34)=NS_D
       eng_idnf(id_nf_the34)=9.58D3*RKEV
       enn_idnf(id_nf_the34)=0.D0

       ns1_idnf(id_nf_the35)=NS_T
       ns2_idnf(id_nf_the35)=NS_He3
       wgt_idnf(id_nf_the35)=0.06D0
       nsp_idnf(id_nf_the35)=NS_He5
       eng_idnf(id_nf_the35)=1.89D3*RKEV
       enn_idnf(id_nf_the35)=0.D0

       ns1_idnf(id_nf_the36)=NS_T
       ns2_idnf(id_nf_the36)=NS_He3
       wgt_idnf(id_nf_the36)=0.06D0
       nsp_idnf(id_nf_the36)=NS_H
       eng_idnf(id_nf_the36)=9.46D3*RKEV
       enn_idnf(id_nf_the36)=0.D0
    END IF


    RETURN
  END SUBROUTINE set_usigmav_nf

  ! --- cross section of nuclear fusion reaction ---
  ! ---     in barn (10^{-28}m^{-2})
  ! ---     as a function of energy in keV

  FUNCTION sigma_nf(id_nf,energy)

    IMPLICIT NONE
    INTEGER,INTENT(IN):: id_nf
    REAL(rkind),INTENT(IN):: energy
    REAL(rkind):: sigma_nf
    
    IF(id_nf.LT.1.OR.id_nf.GT.6) THEN
       WRITE(6,'(A,I4)') &
            'XX sigma_nf: input error: undefined id_nf: ',id_nf
       STOP
    ENDIF
    
    IF(energy.LE.0.D0) THEN
       WRITE(6,*) 'XX sigma_duane: input error: non-positive energy: ',energy
       STOP
    ENDIF
    
    sigma_nf=(Duane(5,id_nf) &
         +Duane(2,id_nf) &
         /((Duane(4,id_nf)-Duane(3,id_nf)*energy)**2+1.D0)) &
         /(energy*(EXP(Duane(1,id_nf)/SQRT(energy))-1.D0))
    RETURN
  END FUNCTION sigma_nf
  
  ! --- reaction rate of nuclear fusion: sigmav  ---
  ! ---     as a function of temperature in keV

  ! Failures are reported out-of-band rather than by STOP.  P1 Task 6 put this
  ! function on a live path -- tr_pnf calls it once per (reaction, radius) on
  ! every TRCALC, and TRCALC runs several times per timestep -- so a STOP here
  ! aborts the host process, pytest or the MCP server, mid-solve (CLAUDE.md,
  ! Fortran library discipline; issue #142).  The signature is deliberately
  ! unchanged: test_libnf.py binds this symbol through ctypes with a fixed
  ! argtypes.
  !
  ! Read nf_error_count, not nf_last_error, to answer "did this run fail".
  ! tr_pnf clears nf_last_error at entry, so a failure inside the converge loop
  ! is erased by the next clean call.  nf_last_error is for a caller that
  ! clears it, runs one loop and checks immediately -- what tr_pnf does.
  FUNCTION sigmav_nf(id_nf,temperature)

    USE libspl1d
    IMPLICIT NONE
    INTEGER,INTENT(IN):: id_nf
    REAL(rkind),INTENT(IN):: temperature
    REAL(rkind):: sigmav_nf,temperature_log
    INTEGER:: ierr

    ierr=0
    sigmav_nf=0.D0

    IF(id_nf.LT.1.OR.id_nf.GT.13) THEN
       IF(.NOT.nf_logged(NF_LOG_ID)) &   ! first of this site -- see the declaration
            WRITE(6,'(A,I4)') 'XX sigmav_nf: undefined id_nf: ',id_nf
       nf_last_error=NF_ERR_ID
       nf_logged(NF_LOG_ID)=.TRUE.
       IF(nf_error_count < HUGE(nf_error_count)) &
            nf_error_count=nf_error_count+1
       RETURN
    END IF

    ! NaN fails every ordered comparison, so it would slip past both the
    ! low and high guards below and reach LOG10.  Test it explicitly.
    IF(temperature.NE.temperature) THEN
       IF(.NOT.nf_logged(NF_LOG_NAN)) &
            WRITE(6,'(A,I4)') 'XX sigmav_nf: NaN temperature: id_nf=',id_nf
       nf_last_error=NF_ERR_TEMP
       nf_logged(NF_LOG_NAN)=.TRUE.
       IF(nf_error_count < HUGE(nf_error_count)) &
            nf_error_count=nf_error_count+1
       RETURN
    END IF

    IF(temperature.LT.1.D0) THEN
       ! Below the table floor; 0 is the intended answer, not an error.
       sigmav_nf=0.D0
       RETURN
    END IF

    IF(temperature.GT.1000.D0) THEN
       IF(.NOT.nf_logged(NF_LOG_HIGH)) &
            WRITE(6,'(A,ES12.4)') &
            'XX sigmav_nf: above the 1000 keV table top: ',temperature
       nf_last_error=NF_ERR_TEMP
       nf_logged(NF_LOG_HIGH)=.TRUE.
       IF(nf_error_count < HUGE(nf_error_count)) &
            nf_error_count=nf_error_count+1
       RETURN
    END IF

    temperature_log=LOG10(temperature)
    SELECT CASE(id_nf)
    CASE(id_nf_dt)
       CALL SPL1DF(temperature_log,sigmav_nf,tempa_log,usvnf_dt,10,ierr)
    CASE(id_nf_dd1,id_nf_dd2,id_nf_dd3)
       CALL SPL1DF(temperature_log,sigmav_nf,tempa_log,usvnf_dd,10,ierr)
    CASE(id_nf_dhe31,id_nf_dhe32)
       CALL SPL1DF(temperature_log,sigmav_nf,tempa_log,usvnf_dhe3,10,ierr)
    CASE(id_nf_tt)
       CALL SPL1DF(temperature_log,sigmav_nf,tempa_log,usvnf_tt,10,ierr)
    CASE(id_nf_the31,id_nf_the32,id_nf_the33, &
         id_nf_the34,id_nf_the35,id_nf_the36)
       CALL SPL1DF(temperature_log,sigmav_nf,tempa_log,usvnf_the3,10,ierr)
    END SELECT
    IF(ierr.NE.0) THEN
       IF(.NOT.nf_logged(NF_LOG_SPL)) THEN
          WRITE(6,'(A,I4)')     'XX SPL1DF error in sigmav_nf: id_nf=',id_nf
          WRITE(6,'(A,ES12.4)') '       temperature=',temperature
       END IF
       sigmav_nf=0.D0
       nf_last_error=NF_ERR_SPL
       nf_logged(NF_LOG_SPL)=.TRUE.
       IF(nf_error_count < HUGE(nf_error_count)) &
            nf_error_count=nf_error_count+1
       RETURN
    END IF

!     UPSTREAM DEFECT, corrected here and in the reference oracle.
!
!     The svnf_* tables above are in cm^3/s, but every consumer needs m^3/s:
!     tr_pnf's SNF = wgt*PN1*PN2*1.D20*RATE_NF has RN in 1e20 m^-3.  The same
!     table exists upstream as trm/libsigma.f90's sigmavma_dt, and BOTH of its
!     consumers there convert -- trm/trpnf.f90 and trx/trsigmavnf.f90 each
!     write `*(1E-6)`.  The libnf rewrite copied the table forward and dropped
!     the conversion, so every fusion rate came out 1e6 too large.
!
!     Checked against Bosch-Hale (Nucl. Fusion 32 (1992) 611): read as cm^3/s
!     the table reproduces the published D-T reactivity to within 0.80-1.01
!     over 1-100 keV and peaks at 8.7e-16 cm^3/s; read as m^3/s it would sit
!     1e6 above the physical D-T maximum.
!
!     Applied at the one computed exit, so it covers all five tables and every
!     caller exactly once; the below-floor branch RETURNs 0 earlier and needs
!     no scale.  The matching correction in the oracle is task-trx-ref
!     trx/libnf.f90 on branch ref/trx-regress-capture.
      sigmav_nf=sigmav_nf*1.D-6

  END FUNCTION sigmav_nf

  ! --- sigmav_nf by integeral over energy ---
  !         <sigmav>=\int_0^\infty 4\pi v^2 dv sigma v f(v)
  !                  f(v)=(m/2\pi T)^{3/2} exp(-mv^2/2T)   normalized to 1
  !                  E=mv^2/2
  !                  v=SQRT{2E/m}
  !                  dv=(1/2) SQRT{2/mE} dE
  !                  4\pi v^2 dv=4\pi (2E/m) (1/2) SQRT{2/mE} dE
  !                             =4\pi SQRT{E^2/m^2 2/mE} dE
  !                             =4\pi SQRT{2E/m^3} dE
  !                  f(E)=(m/2\pi T)^{3/2} exp(-E/T)
  !                <f(E)>=\int_0^\infty 4\pi v^2 dv f(v) 
  !                      =\int_0^\infty 4\pi SQRT{2E/m^3} dE
  !                               (m/2\pi T)^{3/2} exp(-E/T)
  !                      =\int_0^\infty SQRT{16 \pi^2 2E/m^3 m^3/8 \pi^3 T^3}
  !                               dE exp(-E/T)
  !                      =\int_0^\infty SQRT{4E/\pi T} exp(-E/T) dE/T
  !                      =\int_0^\infty SQRT{4X/\pi} exp(-X) dX
  !                      = (2/SQRT{\pi}) \int_0^\infty SQRT{X} exp(-X) dX
  !                      = 1
  !          <sigmav>=\int_0^\infty 4\pi SQRT{2E/m^3} dE sigma SQRT{2E/m} f(E)
  !                  =\int_0^\infty 4\pi 2E/m^2 dE sigma
  !                                   (m/2\pi T)^{3/2} exp(-E/T)
  !                  =\int_0^\infty SQRT{8 E^2/m\pi T} sigma exp(-E/T) dE/T
  !                  =\int_0^\infty SQRT{8T/m\pi} (E/T) sigma exp(-E/T) dE/T
  !                  =\int_0^\infty SQRT{8T/m\pi} X sigma exp(-X) dX

  ! --- sigmav for energy --- X=energy/temperature

  FUNCTION sigmav_nf_local(X)
    USE trcomm,ONLY: RKEV
    USE libnf_local
    IMPLICIT NONE
    REAL(rkind),INTENT(IN):: X
    REAL(rkind):: sigmav_nf_local
    REAL(rkind):: energy,velocity

    energy=temperature_local*X
    velocity=SQRT(2.D0*energy*RKEV/pm_local)
    sigmav_nf_local=sigma_nf(id_nf_local,energy)*velocity
    RETURN
  END FUNCTION sigmav_nf_local


  FUNCTION sigmav_nf_int(id_nf,temperature)

    USE plcomm
    USE libnf_local
    USE libde
    IMPLICIT NONE
    INTEGER,INTENT(IN):: id_nf
    REAL(rkind),INTENT(IN):: temperature
    REAL(rkind):: sigmav_nf_int
    REAL(rkind):: error_int,H0,EPS
    INTEGER:: ILST

    IF(id_nf.LT.1.OR.id_nf.GT.6) THEN
       WRITE(6,'(A,I4)') 'XX sigmav_nf: input error: undefined id_nf: ',id_nf
       STOP
    END IF

    IF(temperature.LT.1.D0) THEN
       sigmav_nf_int=0.D0
       RETURN
    END IF

    IF(temperature.GT.1000.D0) THEN
       WRITE(6,'(A,ES12.4)') &
            'XX sigmav_nf: input error: Too high temperature: temperature=', &
            temperature
       STOP
    END IF

    id_nf_local=id_nf
    temperature_local=temperature
    pm_local=PA(nsp_idnf(id_nf))*AMP

    H0=1.D-4
    EPS=1.D-6
    
    CALL DEHIFE(sigmav_nf_int,error_int,H0,eps,ilst,sigmav_nf_local, &
         'sigmav_nf_int')

    RETURN
  END FUNCTION sigmav_nf_int



  
  ! --- p-B reaction ---
  !        Ref. A. Tantori and F Belloni, Nucl. Fusion 63 (2023) 086001 (9pp)
  !     cross section --- sigma
  !     astrophysics factor --- S

  FUNCTION sigma_nf_PB_NS(E_Mev)

    USE plcomm
    IMPLICIT NONE
    REAL(rkind),INTENT(IN):: E_MeV ! Energy in MeV
    REAL(rkind):: sigma_nf_PB_NS

    sigma_nf_PB_NS=S_nf_PB_NS(E_MeV*1.D3)/E_MeV*EXP(-SQRT(22.589D0/E_MeV))
    RETURN
  END FUNCTION sigma_nf_PB_NS
    
  FUNCTION sigma_nf_PB_SW(E_Mev)

    USE plcomm
    IMPLICIT NONE
    REAL(rkind),INTENT(IN):: E_MeV ! Energy in MeV
    REAL(rkind):: sigma_nf_PB_SW

    sigma_nf_PB_SW=S_nf_PB_SW(E_MeV*1.D3)/E_MeV*EXP(-SQRT(22.589D0/E_MeV))
    RETURN
  END FUNCTION sigma_nf_PB_SW
    
  FUNCTION S_nf_PB_NS(E_keV)

    USE plcomm
    IMPLICIT NONE
    REAL(rkind),INTENT(IN):: E_keV ! Energy in keV
    REAL(rkind):: S_nf_PB_NS
    ! constants all in MeV
    REAL(rkind),PARAMETER:: C_0=197.D0
    REAL(rkind),PARAMETER:: C_1=0.240D0
    REAL(rkind),PARAMETER:: C_2=2.31D-4
    REAL(rkind),PARAMETER:: A_L=1.82D4
    REAL(rkind),PARAMETER:: E_L=148.0D-3
    REAL(rkind),PARAMETER:: delE_L=2.35D-3
    REAL(rkind),PARAMETER:: D_0=330.D0
    REAL(rkind),PARAMETER:: D_1=66.1D0
    REAL(rkind),PARAMETER:: D_2=-20.3D0
    REAL(rkind),PARAMETER:: D_5=-1.58D0
    REAL(rkind),PARAMETER:: A_0=2.57D6
    REAL(rkind),PARAMETER:: A_1=5.67D5
    REAL(rkind),PARAMETER:: A_2=1.34D5
    REAL(rkind),PARAMETER:: A_3=5.68D5
    REAL(rkind),PARAMETER:: E_0=581.3D-3
    REAL(rkind),PARAMETER:: E_1=1083.D-3
    REAL(rkind),PARAMETER:: E_2=2405.D-3
    REAL(rkind),PARAMETER:: E_3=3344.D-3
    REAL(rkind),PARAMETER:: delE_0=85.7D-3
    REAL(rkind),PARAMETER:: delE_1=234.D-3
    REAL(rkind),PARAMETER:: delE_2=138.D-3
    REAL(rkind),PARAMETER:: delE_3=309.D-3
    REAL(rkind),PARAMETER:: B=4.38D0
  
    REAL(rkind):: E_MeV, E_n, S

    E_MeV=E_kev*0.001D0 ! Energy in  MeV

    IF(E_MeV.LE.0.4D0) THEN ! S_1
       S=C_0+C_1*E_keV+C_2*E_keV**2+A_L*1.D-6/((E_MeV-E_L)**2+delE_L**2)
    ELSE IF(E_MeV.LE.0.642D0) THEN ! S_2
       E_n=1.D1*(E_MeV-0.400D0)
       S=D_0+D_1*E_n+D_2*E_n**2+D_5*E_n**5
    ELSE IF(E_MeV.LE.3.5D0) THEN ! S_3
       S=B+A_0*1.D-6/((E_MeV-E_0)**2+delE_0**2) &
          +A_1*1.D-6/((E_MeV-E_1)**2+delE_1**2) &
          +A_2*1.D-6/((E_MeV-E_2)**2+delE_2**2) &
          +A_3*1.D-6/((E_MeV-E_3)**2+delE_3**2)
    ELSE ! out of range
       S=B+A_0*1.D-6/((3.5D0-E_0)**2+delE_0**2) &
          +A_1*1.D-6/((3.5D0-E_1)**2+delE_1**2) &
          +A_2*1.D-6/((3.5D0-E_2)**2+delE_2**2) &
          +A_3*1.D-6/((3.5D0-E_3)**2+delE_3**2)
    END IF
    S_nf_PB_NS=S
    RETURN
  END FUNCTION S_nf_PB_NS

  FUNCTION S_nf_PB_SW(E_keV)

    USE plcomm
    IMPLICIT NONE
    REAL(rkind),INTENT(IN):: E_keV ! Energy in keV
    REAL(rkind):: S_nf_PB_SW
    ! constants all in MeV
    REAL(rkind),PARAMETER:: C_0=197.D0
    REAL(rkind),PARAMETER:: C_1=0.269D0
    REAL(rkind),PARAMETER:: C_2=2.54D-4
    REAL(rkind),PARAMETER:: D_0=346.D0
    REAL(rkind),PARAMETER:: D_1=150.D0
    REAL(rkind),PARAMETER:: D_2=-59.9D0
    REAL(rkind),PARAMETER:: D_5=-0.460D0
    REAL(rkind),PARAMETER:: A_0=1.98D6
    REAL(rkind),PARAMETER:: A_1=3.89D6
    REAL(rkind),PARAMETER:: A_2=1.36D6
    REAL(rkind),PARAMETER:: A_3=3.71D6
    REAL(rkind),PARAMETER:: E_0=640.9D-3
    REAL(rkind),PARAMETER:: E_1=1211.D-3
    REAL(rkind),PARAMETER:: E_2=2340.D-3
    REAL(rkind),PARAMETER:: E_3=3294.D-3
    REAL(rkind),PARAMETER:: delE_0=85.5D-3
    REAL(rkind),PARAMETER:: delE_1=414.D-3
    REAL(rkind),PARAMETER:: delE_2=221.D-3
    REAL(rkind),PARAMETER:: delE_3=351.D-3
    REAL(rkind),PARAMETER:: B=0.381D0
  
    REAL(rkind):: E_MeV, E_n, S

    E_MeV=E_kev*0.001D0 ! Energy in  MeV

    IF(E_MeV.LE.0.4D0) THEN ! S_1
       S=C_0+C_1*E_keV+C_2*E_keV**2
    ELSE IF(E_MeV.LE.0.668D0) THEN ! S_2
       E_n=1.D1*(E_MeV-0.400D0)
       S=D_0+D_1*E_n+D_2*E_n**2+D_5*E_n**5
    ELSE IF(E_MeV.LE.9.76D0) THEN ! S_3
       S=B+A_0*1.D-6/((E_MeV-E_0)**2+delE_0**2) &
          +A_1*1.D-6/((E_MeV-E_1)**2+delE_1**2) &
          +A_2*1.D-6/((E_MeV-E_2)**2+delE_2**2) &
          +A_3*1.D-6/((E_MeV-E_3)**2+delE_3**2)
    ELSE ! out of range
       S=B+A_0*1.D-6/((9.76D0-E_0)**2+delE_0**2) &
          +A_1*1.D-6/((9.76D0-E_1)**2+delE_1**2) &
          +A_2*1.D-6/((9.76D0-E_2)**2+delE_2**2) &
          +A_3*1.D-6/((9.76D0-E_3)**2+delE_3**2)
    END IF
    S_nf_PB_SW=S
    RETURN
  END FUNCTION S_nf_PB_SW

END MODULE libnf
      
