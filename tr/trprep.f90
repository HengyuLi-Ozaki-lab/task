! trprep.f90

MODULE trprep

  PRIVATE
  PUBLIC tr_prep

CONTAINS

  SUBROUTINE tr_prep(ierr)

    USE trcomm
    USE trcom0, ONLY : NSTM
    USE trcom1, ONLY : NTAMAX,KDIRX
    USE trprof
    USE trbpsd
    USE trmetric
    USE tr_dump_state_mod, ONLY : tr_dump_state_if_requested
    IMPLICIT NONE
    INTEGER,INTENT(OUT):: ierr

      CALL ALLOCATE_TRCOMM(IERR)
      IF(IERR.NE.0) RETURN

      IF(MDLUF.NE.0.AND.MDLXP.NE.0) CALL IPDB_OPEN(KUFDEV, KUFDCG)
      IF(MDLUF.NE.0) CALL UFILE_INTERFACE(KDIRX,KUFDIR,KUFDEV,KUFDCG,0)
      CALL TR_EQS_SELECT(0, ierr)
      IF(ierr.NE.0) RETURN   ! #142: TR_EQS_SELECT now returns ierr=1 on
                             ! MDLEQE/MDLEQN inconsistency instead of STOP

      NRAMAX=INT(RHOA*NRMAX)
      DR = 1.D0/DBLE(NRMAX)

      IF(MDLUF.EQ.1) THEN
!         IF(INIT.EQ.2.AND.NT.NE.0) THEN
         IF(NT.NE.0) THEN
            NT=0
            NTMAX=NTMAX_SAVE
         ENDIF
         CALL TR_UFILE_CONTROL(1)
      ELSEIF(MDLUF.EQ.2) THEN
         CALL TR_UFILE_CONTROL(2)
      ELSEIF(MDLUF.EQ.3) THEN
!         IF(INIT.EQ.2.AND.NT.NE.0) THEN
         IF(NT.NE.0) THEN
            NT=0
            NTMAX=NTMAX_SAVE
         ENDIF
         CALL TR_UFILE_CONTROL(3)
      ELSE
         CALL TR_UFILE_CONTROL(0)
      ENDIF

      NT    = 0
      T     = 0.D0
      TPRE  = 0.D0
      TST   = 0.D0
      VSEC  = 0.D0
      NGR   = 0
      NGT   = 0
      NGST  = 0
      RIP   = RIPS

      icount_of_pellet=0

      IF(MDLUF.EQ.1.OR.MDLUF.EQ.3) THEN
         IF(NTMAX.GT.NTAMAX) NTMAX=NTAMAX
      ENDIF

      CALL tr_prof

!     *** Initialize bpsd data ***

      CALL tr_bpsd_init
      CALL tr_bpsd_put(ierr)
      IF(ierr.NE.0) THEN
         write(6,'(A,I5)') 'XX tr_bpsd_put in tr_prof: ierr=',ierr
         RETURN   ! #142: was STOP — abort kills the libtrapi.so host process
      END IF

!     *** CALCULATE METRIC FACTOR ***

      CALL tr_set_metric(ierr)
      IF(ierr.NE.0) THEN
         write(6,'(A,I5)') 'XX tr_set_metric in tr_metric: ierr=',ierr
         RETURN   ! #142: was STOP
      END IF
      
!     *** CALCULATE ANEAVE and ANC, ANFE ***

      CALL tr_prof_impurity(ierr)
      IF(ierr.NE.0) THEN
         WRITE(6,'(A,I5)') 'XX tr_prof_impurity in tr_prep: ierr=',ierr
         RETURN   ! #142 followup: was unconditional STOP in tr_prof_impurity
      END IF

!     *** CALCULATE AJ, QP, BP, EZ ***

      IF(MODELG.EQ.2) CALL tr_prof_current

!     *** Initialize bpsd data ***

      CALL tr_bpsd_put(ierr)
      IF(ierr.NE.0) THEN
         write(6,'(A,I5)') 'XX tr_bpsd_put in tr_prof: ierr=',ierr
         RETURN   ! #142: was STOP
      END IF

!     *** initilize graphic data ***

      GRG(1)=0.0
      GRM(1:NRMAX)  =SNGL(RM(1:NRMAX))
      GRG(2:NRMAX+1)=SNGL(RG(1:NRMAX))

      ! Optional state dump for binary-vs-library divergence diagnosis.
      ! No-op unless TR_DUMP_STATE env var is set to a writable file path.
      CALL tr_dump_state_if_requested('after_tr_prep')

      RETURN

    END SUBROUTINE tr_prep
  END MODULE trprep


!     ***********************************************************

!           MODEL SELECTOR

!     ***********************************************************

  SUBROUTINE TR_EQS_SELECT(INIT, IERR)

    USE TRCOMM, ONLY : &
         AMM, AMZ, MDDIAG, MDLEOI, MDLEQ0, MDLEQB, MDLEQE, MDLEQN, &
         MDLEQT, MDLEQU, MDLEQZ, MDLKAI, MDLUF, &
         MDLWLD, MDNCLS, NEA, NEQM, NEQMAX, NEQMAXM, NNS, NREDGE, &
         NRMAX, NSCMAX, NSLMAX, NSM, NSMAX,      &
         NSNMAX, NSS, NST, NSTM, NSTMAX, NSV, NSZMAX, PA, PZ, RGFLS, RQFLS
    USE TRCOM1, ONLY : INS
    IMPLICIT NONE
    INTEGER,INTENT(IN) :: INIT
    INTEGER,INTENT(OUT) :: IERR  ! #142. Not OPTIONAL: TR_EQS_SELECT is an
                                ! external procedure, so an OPTIONAL dummy
                                ! would need an explicit interface at its
                                ! caller, which tr_prep (its only caller in
                                ! tr/) does not have; tr_prep passes IERR.
    INTEGER:: IND, INDH, INDHD, MDANOM, MDSLCT, NEQ, NEQ1, NEQI
    INTEGER:: NEQRMAX, NEQS, NEQT, NNSC, NNSMAX, NNSN, NS, NSSN, NSVN
    INTEGER:: NBAD
    INTEGER, SAVE :: NSSMAX


!     If INS is zero, all particles designated by NSMAX are fully
!     calculated. If INS=1, we handle only electrons and bulk ions
!     IF INS=2, three species are employed in the simulation but
!     just one of them is calculated.

      NSCMAX=NSMAX+NSZMAX          ! the number of charged particles
      NSTMAX=NSMAX+NSZMAX+NSNMAX   ! the number of all particles

      IF(NSMAX.EQ.1.AND.MDLEOI.EQ.0) MDLEOI=1
      IF(INIT.EQ.0) THEN
         INS=0
      ELSE
         IF(NSSMAX.NE.NSMAX) THEN
            INS=0
         ENDIF
      ENDIF
      NSSMAX=NSMAX
      IF(MDLUF.NE.0) THEN
         CALL CHECK_IMPURITY(MDSLCT)
         IF(MDSLCT.EQ.0) THEN
            IF(NSMAX.EQ.1) THEN
               INS=1
               NSMAX=2
            ENDIF
         ELSE
            IF(NSMAX.EQ.1) INS=2
            NSMAX=3
!            PA(3)=12.D0
!            PZ(3)=6.D0
         ENDIF
      ENDIF
!     *** for NCLASS ***
      IF(NSMAX.EQ.1) THEN
         NSLMAX=2
      ELSE
         NSLMAX=NSMAX
      ENDIF
!     ***

!      IF(MDLEQT.EQ.0) THEN
!         NEQMAX=MDLEQB+(MDLEQN+MDLEQT+MDLEQU)*2+MDLEQ0*NSNMAX+MDLEQZ*NSZMAX
!      ELSEIF(MDLEQT.EQ.1) THEN
!         NEQMAX=MDLEQB+2+(MDLEQT+MDLEQU)*2+MDLEQ0*NSNMAX+MDLEQZ*NSZMAX
!      ENDIF
      IF(MDLEQT.EQ.0) THEN
         NEQMAX=MDLEQB+(MDLEQN+MDLEQT+MDLEQU)*NSMAX+MDLEQ0*NSNMAX+MDLEQZ*NSZMAX
      ELSEIF(MDLEQT.EQ.1) THEN
         NEQMAX=MDLEQB+NSMAX+(MDLEQT+MDLEQU)*NSMAX+MDLEQ0*NSNMAX+MDLEQZ*NSZMAX
      ENDIF

      IERR = 0
      IF(MDLEQN.EQ.0.AND.(MDLEQE.EQ.1.OR.MDLEQE.EQ.2)) THEN
         WRITE(6,*)  'XX TR_EQS_SELECT : MDLEQE can be 1 or 2 when MDLEQN is 1.'
         IERR = 1
         RETURN
      ENDIF

      NSS(1:NEQMAXM)=-1  ! 0: EM, particle species
      NSV(1:NEQMAXM)=-1  ! 1: density, 2: temperature 3: toroidal flow
      NNS(1:NEQMAXM)=0   ! 
      NST(1:NEQMAXM)=0
      NEQ=0
      IF(MDLEQB.EQ.1) THEN
         NEQ=NEQ+1
         NSS(NEQ)=0
         NSV(NEQ)=0
      ENDIF
      IND=0
      INDH=0
      INDHD=0
      DO NS=1,NSM
         IF(MDLEQN.EQ.1.OR.MDLEQT.EQ.1) THEN
            IF(MDLEQN.EQ.1) IND=1
            CALL TR_TABLE(NS,NEQ,1,IND,INDH,INDHD)
            IF(IND.EQ.-1) CONTINUE
         ENDIF
         IF(MDLEQT.EQ.1) THEN
            CALL TR_TABLE(NS,NEQ,2,IND,INDH,INDHD)
            IF(IND.EQ.-1) CONTINUE
         ENDIF
         IF(MDLEQU.EQ.1) THEN
            CALL TR_TABLE(NS,NEQ,3,IND,INDH,INDHD)
            IF(IND.EQ.-1) CONTINUE
         ENDIF
      ENDDO
      IF(MDLEQZ.EQ.1) THEN
         IF(NSZMAX.EQ.1) THEN
            NEQ=NEQ+1
            NSS(NEQ  )=5
            NSV(NEQ  )=1
         ELSEIF(NSZMAX.EQ.2) THEN
            NEQ=NEQ+2
            NSS(NEQ-1)=5
            NSV(NEQ-1)=1
            NSS(NEQ  )=6
            NSV(NEQ  )=1
         ENDIF
      ENDIF
      IF(MDLEQ0.EQ.1) THEN
         NEQ=NEQ+2
         NSS(NEQ-1)=7
         NSV(NEQ-1)=1
         NSS(NEQ  )=8
         NSV(NEQ  )=1
      ENDIF

      IF(INS.NE.0) THEN
         NEQI=0
         DO NEQ=1,NEQMAX
            NSSN=NSS(NEQ)
            NSVN=NSV(NEQ)
            IF(NSSN.NE.MDLEOI.OR.NSVN.NE.2) THEN
               NEQI=NEQI+1
               NNS(NEQI)=NEQ
            ENDIF
         ENDDO
      ENDIF

      NNSC=0
      DO NEQ=1,NEQMAX
         NNSN=NNS(NEQ)
         IF(NNSN.NE.0) THEN
            NNSC=NNSC+1
         ELSE
            GOTO 1000
         ENDIF
      ENDDO
 1000 CONTINUE
      NNSMAX=NNSC
      NEQRMAX=NEQMAX-NNSMAX

      NEQS=1
      NEQT=1
      DO NEQ=1,NEQMAX
         NNSN=NNS(NEQ)
         DO NEQ1=1,NEQMAX
            IF(NEQ1.GE.NEQS) THEN
               IF(NEQ1.LT.NNSN.OR.NNSN.EQ.0) THEN
                  NST(NEQ1)=NEQT
                  NEQT=NEQT+1
                  IF(NEQT.GT.NEQRMAX) GOTO 1200
               ELSEIF(NNSN.EQ.NEQ1) THEN
                  NST(NEQ1)=0
                  NEQS=NNSN+1
                  GOTO 1100
               ENDIF
            ENDIF
         ENDDO
 1100    CONTINUE
      ENDDO
 1200 CONTINUE

      DO NS=1,NSMAX
         IF(PZ(NS).NE.0.D0) THEN
            AMZ(NS)=PA(NS)*AMM/PZ(NS)**2
         ELSE
            AMZ(NS)=0.D0
         ENDIF
      ENDDO

      WRITE(6,600) 'NEQ','NSS','NSV','NNS','NST'
      DO NEQ=1,NEQMAX
         WRITE(6,610) NEQ,NSS(NEQ),NSV(NEQ),NNS(NEQ),NST(NEQ)
      ENDDO
 600  FORMAT(' ',5(' ',A))
 610  FORMAT(' ',5I4)

!     A species that matched no class, two that took one place, one placed above NSMAX, or a species 1
!     that is not the electron would leave an equation without a species (NEA below is then written
!     with index -1) or a species without its equations (the solve stops on it), or the electrons
!     out of place: refuse the run, naming the species.
      CALL tr_species_equations_check(NBAD)
      IF(NBAD.NE.0) THEN
         IERR = 1
         RETURN
      END IF
!     *** EQUATION SELECTOR ***

!     Format : NEA(species,equation) for all equations
      NEA(0:NSTM,0:3)=0
      DO NEQ=1,NEQMAX
         NEA(NSS(NEQ),NSV(NEQ))=NEQ
      ENDDO

!     CHECK WHETHER TURBULENT TRANSPORT MODEL HAS OFF-DIAGONAL PARTS

      IF(MDLKAI.EQ.61.OR.(MDLKAI.EQ.63.AND.MDLWLD.EQ.1)) THEN
         MDANOM=1
      ELSE
         MDANOM=0
      ENDIF

!     |-----------------------|
!     |MDDIAG |NCLASS |MDANOM |
!     |-------|-------|-------|
!     |   0   |   *   |   *   |
!     |   1   |   o   |   *   |
!     |   2   |   *   |   o   |
!     |   3   |   o   |   o   |
!     |-----------------------|

      IF(MDNCLS.EQ.0) THEN
         IF(MDANOM.EQ.1) THEN
            MDDIAG=2
         ELSE
            MDDIAG=0
         ENDIF
         RGFLS(1:NRMAX,1:5,1:NSMAX)=0.D0
         RQFLS(1:NRMAX,1:5,1:NSMAX)=0.D0
      ELSE
         IF(MDANOM.EQ.1) THEN
            MDDIAG=3
         ELSE
            MDDIAG=1
         ENDIF
      ENDIF

!     *** GRID POINT OF EDGE REGION ***

      NREDGE=NINT(0.93*NRMAX)

      RETURN
      END SUBROUTINE TR_EQS_SELECT

!     ***********************************************************

!           SORTER AS MAIN PART OF MODEL SELECTOR

!     ***********************************************************

      SUBROUTINE TR_TABLE(NS,NEQ,NSW,IND,INDH,INDHD)

      USE TRCOMM, ONLY : AME, AMM, MDLEQE, NEQMAX, NNS, NSMAX, NSS, NSV, PA, rkind
      IMPLICIT NONE
      INTEGER,INTENT(IN)   :: NS, NSW
      INTEGER,INTENT(INOUT):: NEQ, IND, INDH, INDHD
      INTEGER :: NEQI, NEQII, NNSN, NSVN
      REAL(rkind)    :: REM

      REM=AME/AMM
      IF(NS.LE.NSMAX) THEN
         IF(ABS(PA(NS)-REM).LE.1.D-10) THEN
!     electron
            NEQ=NEQ+1
            NSS(NEQ)=1
            NSV(NEQ)=NSW
            IF(NSW.EQ.2.AND.IND.EQ.0) THEN
               DO NEQI=NEQ-1,NEQMAX
                  NSVN=NSV(NEQI)
                  IF(NSVN.EQ.1.AND.MDLEQE.EQ.0) THEN
                     DO NEQII=1,NEQMAX
                        NNSN=NNS(NEQII)
                        IF(NNSN.EQ.0) THEN
                           NNS(NEQII)=NEQI
                           GOTO 100
                        ENDIF
                     ENDDO
                  ENDIF
               ENDDO
 100           CONTINUE
            ELSEIF(NSW.EQ.2.AND.IND.EQ.1) THEN
               IF(MDLEQE.EQ.0) THEN
                  IF(NSS(1).EQ.0) THEN
                     NNS(1)=2
                  ELSEIF(NSS(1).EQ.1) THEN
                     NNS(1)=1
                  ENDIF
               ELSEIF(MDLEQE.EQ.2) THEN
                  NNS(1)=3
               ENDIF
            ENDIF
         ELSEIF(PA(NS).EQ.1.D0.OR.ABS(PA(NS)-2.D0).LT.0.5D0) THEN
!     regard the particle whose mass is 1.0 as HYDROGEN
!     regard the particle whose mass is between 1.5 and 2.5 as DEUTERIUM
!     If bulk particle is hydrogen, INDH=1
            IF(PA(NS).EQ.1.D0) INDH=1
            NEQ=NEQ+1
!     If plasma is composed of hydrogen and deuterium, INDHD=1
            IF(INDH.EQ.1.AND.ABS(PA(NS)-2.D0).LT.0.5D0) THEN
               NSS(NEQ)=3
               INDHD=1
            ELSE
               NSS(NEQ)=2
            ENDIF
            NSV(NEQ)=NSW
            IF(NSW.EQ.2.AND.IND.EQ.0) THEN
               DO NEQI=NEQ-1,NEQMAX
                  NSVN=NSV(NEQI)
                  IF(NSVN.EQ.1) THEN
                     DO NEQII=1,NEQMAX
                        NNSN=NNS(NEQII)
                        IF(NNSN.EQ.0) THEN
                           NNS(NEQII)=NEQI
                           GOTO 200
                        ENDIF
                     ENDDO
                  ENDIF
               ENDDO
 200           CONTINUE
            ENDIF
         ELSEIF(ABS(PA(NS)-3.D0).LT.0.5D0) THEN
!     regard the particle whose mass is between 2.5 and 3.5 as TRITIUM
            NEQ=NEQ+1
            IF(INDHD.EQ.1) THEN
               NSS(NEQ)=4
            ELSE
               NSS(NEQ)=3
            ENDIF
            NSV(NEQ)=NSW
            IF(NSW.EQ.2.AND.IND.EQ.0) THEN
               DO NEQI=NEQ-1,NEQMAX
                  NSVN=NSV(NEQI)
                  IF(NSVN.EQ.1) THEN
                     DO NEQII=1,NEQMAX
                        NNSN=NNS(NEQII)
                        IF(NNSN.EQ.0) THEN
                           NNS(NEQII)=NEQI
                           GOTO 300
                        ENDIF
                     ENDDO
                  ENDIF
               ENDDO
 300           CONTINUE
            ENDIF
         ELSEIF(ABS(PA(NS)-4.D0).LT.0.5D0) THEN
!     regard the particle whose mass is between 3.5 and 4.5 as HELIUM
            NEQ=NEQ+1
            NSS(NEQ)=4
            NSV(NEQ)=NSW
            IF(NSW.EQ.2.AND.IND.EQ.0) THEN
               DO NEQI=NEQ-1,NEQMAX
                  NSVN=NSV(NEQI)
                  IF(NSVN.EQ.1) THEN
                     DO NEQII=1,NEQMAX
                        NNSN=NNS(NEQII)
                        IF(NNSN.EQ.0) THEN
                           NNS(NEQII)=NEQI
                           GOTO 400
                        ENDIF
                     ENDDO
                  ENDIF
               ENDDO
 400           CONTINUE
            ENDIF
         ELSEIF(ABS(PA(NS)-12.D0).LT.3.D0.AND.NSMAX.EQ.3) THEN
!     regard the particle whose mass is between 9.0 and 15.0 as CARBON
            NEQ=NEQ+1
            NSS(NEQ)=3
            NSV(NEQ)=NSW
            IF(NSW.EQ.2.AND.IND.EQ.0) THEN
               DO NEQI=NEQ-1,NEQMAX
                  NSVN=NSV(NEQI)
                  IF(NSVN.EQ.1) THEN
                     DO NEQII=1,NEQMAX
                        NNSN=NNS(NEQII)
                        IF(NNSN.EQ.0) THEN
                           NNS(NEQII)=NEQI
                           GOTO 500
                        ENDIF
                     ENDDO
                  ENDIF
               ENDDO
 500           CONTINUE
            ENDIF
         ELSEIF(PA(NS).EQ.0.D0) THEN
            IND=-1
         ENDIF
      ENDIF

      RETURN
      END SUBROUTINE TR_TABLE

!     ***********************************************************

!     TR_TABLE places a species by its mass alone: the electron is PA = AME/AMM to 1e-10 (place 1),
!     hydrogen PA = 1 or deuterium 1.5 < PA < 2.5 (2; deuterium beside hydrogen 3), tritium
!     2.5 < PA < 3.5 (3; beside hydrogen and deuterium 4), helium 3.5 < PA < 4.5 (4), carbon
!     9 < PA < 15 with NSMAX = 3 (3). Species 1..NSMAX must take these places once each, and the
!     electron must be species 1 (the solve takes species 1 for the electrons, trcalc.f90's PNSS(1) for
!     one). The places are given in the order of the species, so deuterium takes 3 only after a
!     hydrogen and tritium 4 only after both (e/D/H gives two species place 2; e/T/H is fine). NBAD
!     counts, each said on unit 6: a species 1 that is not the electron; a species
!     1..NSMAX that gets no equation for a variable the run evolves (density with MDLEQN or MDLEQT,
!     temperature with MDLEQT, toroidal flow with MDLEQU) -- a variable has at most NSMAX equations of
!     species 1..NSMAX, one per species that matched a class, so a place taken twice or above NSMAX
!     comes to this; and an equation left without a species (NSS = -1), which an impurity or neutral
!     count above what the table fills (NSZMAX > 2, or NSNMAX > 2 with MDLEQ0) also leaves.

      SUBROUTINE tr_species_equations_check(NBAD)

      USE TRCOMM, ONLY : AME, AMM, MDLEQN, MDLEQT, MDLEQU, NEQMAX, NSMAX, NSS, NSV, PA
      IMPLICIT NONE
      INTEGER, INTENT(OUT) :: NBAD
      CHARACTER(LEN=13), PARAMETER :: VARIABLE(3) = [CHARACTER(LEN=13) :: 'density', 'temperature', 'toroidal flow']
      LOGICAL :: EVOLVED(3)
      INTEGER :: NEQ, NS, NV, NFOUND

      NBAD = 0
      IF(NSMAX.GE.1 .AND. ABS(PA(1)-AME/AMM).GT.1.D-10) THEN
         NBAD = NBAD + 1
         WRITE(6,'(A,1PE13.6,A,1PE13.6,A)') 'XX TR_EQS_SELECT: species 1 (PA =', PA(1), &
              ') is not the electron (AME/AMM =', AME/AMM, '), which the solve takes it for'
      END IF
      EVOLVED = [MDLEQN.EQ.1 .OR. MDLEQT.EQ.1, MDLEQT.EQ.1, MDLEQU.EQ.1]
      DO NS = 1, NSMAX
         DO NV = 1, 3
            IF(.NOT.EVOLVED(NV)) CYCLE
            NFOUND = 0
            DO NEQ = 1, NEQMAX
               IF(NSS(NEQ).EQ.NS .AND. NSV(NEQ).EQ.NV) NFOUND = NFOUND + 1
            END DO
            IF(NFOUND.EQ.0) THEN
               NBAD = NBAD + 1
               WRITE(6,'(A,I0,A,1PE13.6,3A)') 'XX TR_EQS_SELECT: species ', NS, ' (PA =', PA(NS), &
                    ') gets no ', TRIM(VARIABLE(NV)), ' equation'
            END IF
         END DO
      END DO
      DO NEQ = 1, NEQMAX
         IF(NSS(NEQ).LT.0 .OR. NSV(NEQ).LT.0) THEN
            NBAD = NBAD + 1
            WRITE(6,'(A,I0,A)') 'XX TR_EQS_SELECT: equation ', NEQ, ' has no species'
         END IF
      END DO
      IF(NBAD.NE.0) WRITE(6,'(A)') &
           'XX TR_EQS_SELECT: TR places a species by its mass PA: electron AME/AMM to 1e-10 (1), ' // &
           'hydrogen 1 or deuterium 1.5-2.5 (2; 3 after a hydrogen), tritium 2.5-3.5 (3; 4 after H and D), ' // &
           'helium 3.5-4.5 (4), carbon 9-15 with NSMAX = 3 (3); species 1..NSMAX take these places once each, ' // &
           'the electron first'
      RETURN
      END SUBROUTINE tr_species_equations_check
