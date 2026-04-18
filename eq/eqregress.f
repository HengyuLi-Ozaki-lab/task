C     $Id$
C
C   ***********************************************************
C   **       Phase L-0 regression dump for TASK/EQ           **
C   **                                                       **
C   **  Emits eq_regress.dat (1PE24.16 format) when env var  **
C   **  EQ_REGRESS_DUMP=1 is set; otherwise no-op so normal  **
C   **  runs are unaffected.                                 **
C   **                                                       **
C   **  Hooked from end of EQCALQ (called after every R/RUN  **
C   **  from EQMENU). F77 fixed-form to match eq/ convention **
C   **  and to compile with gfortran -std=legacy.            **
C   **                                                       **
C   **  Format v1 (line-oriented, parsed by                  **
C   **  test_run/scripts/extract_eq_metrics.py):             **
C   **    # comment lines start with #                       **
C   **    KEY=VALUE  for header dims and scalars             **
C   **    profile rows: NR PSIP PSIT PPS TTS QPS VPS RST     **
C   ***********************************************************
C
      SUBROUTINE EQ_REGRESS_DUMP_IF_ENABLED
C
      INCLUDE '../eq/eqcomq.inc'
C
      CHARACTER*16 ENV_VAL
      INTEGER STAT, IOERR, NR, UNIT_DUMP
      PARAMETER (UNIT_DUMP=78)
C
C     ----- check env var EQ_REGRESS_DUMP=1 -----
C
      CALL GET_ENVIRONMENT_VARIABLE('EQ_REGRESS_DUMP',ENV_VAL,
     &                              STATUS=STAT)
      IF(STAT.NE.0) RETURN
      IF(ENV_VAL(1:1).NE.'1') RETURN
C
C     ----- open eq_regress.dat in cwd; bail on failure -----
C
      OPEN(UNIT=UNIT_DUMP, FILE='eq_regress.dat',
     &     STATUS='REPLACE', ACTION='WRITE', IOSTAT=IOERR)
      IF(IOERR.NE.0) THEN
         WRITE(6,*) 'XX eqregress: cannot open eq_regress.dat, ',
     &              'IOSTAT=', IOERR
         RETURN
      ENDIF
C
C     ----- header / dimensions -----
C
      WRITE(UNIT_DUMP,'(A)')
     &     '# TASK/EQ regression dump (format v1)'
      WRITE(UNIT_DUMP,'(A,I0)')   'NRMAX=',  NRMAX
      WRITE(UNIT_DUMP,'(A,I0)')   'NTHMAX=', NTHMAX
      WRITE(UNIT_DUMP,'(A,I0)')   'NSUMAX=', NSUMAX
      WRITE(UNIT_DUMP,'(A,I0)')   'NSGMAX=', NSGMAX
      WRITE(UNIT_DUMP,'(A,I0)')   'NTGMAX=', NTGMAX
      WRITE(UNIT_DUMP,'(A,I0)')   'NPSMAX=', NPSMAX
      WRITE(UNIT_DUMP,'(A,I0)')   'NRVMAX=', NRVMAX
C
C     ----- global scalars (always defined after EQCALC) -----
C
      WRITE(UNIT_DUMP,'(A,1PE24.16)') 'RAXIS=',  RAXIS
      WRITE(UNIT_DUMP,'(A,1PE24.16)') 'ZAXIS=',  ZAXIS
      WRITE(UNIT_DUMP,'(A,1PE24.16)') 'PSI0=',   PSI0
      WRITE(UNIT_DUMP,'(A,1PE24.16)') 'PSIPA=',  PSIPA
      WRITE(UNIT_DUMP,'(A,1PE24.16)') 'PSITA=',  PSITA
      WRITE(UNIT_DUMP,'(A,1PE24.16)') 'RIPX=',   RIPX
C
C     ----- post-EQCALQV scalars (PVOL/BETAT/... defined when
C           EQCALQV ran; for default NSUMAX>0 case both tests hit). ----
C
      WRITE(UNIT_DUMP,'(A,1PE24.16)') 'PVOL=',   PVOL
      WRITE(UNIT_DUMP,'(A,1PE24.16)') 'RAAVE=',  RAAVE
      WRITE(UNIT_DUMP,'(A,1PE24.16)') 'BETAT=',  BETAT
      WRITE(UNIT_DUMP,'(A,1PE24.16)') 'BETAP=',  BETAP
      WRITE(UNIT_DUMP,'(A,1PE24.16)') 'QAXIS=',  QAXIS
      WRITE(UNIT_DUMP,'(A,1PE24.16)') 'QSURF=',  QSURF
C
C     ----- profile (NRMAX rows): flux-surface coordinates -----
C       NR  PSIP PSIT PPS TTS QPS VPS RST
C
      WRITE(UNIT_DUMP,'(A)')
     &     '# profile columns: NR PSIP PSIT PPS TTS QPS VPS RST'
      DO 100 NR=1,NRMAX
         WRITE(UNIT_DUMP,'(I5,7(1X,1PE24.16))')
     &        NR, PSIP(NR), PSIT(NR), PPS(NR), TTS(NR),
     &        QPS(NR), VPS(NR), RST(NR)
  100 CONTINUE
C
      CLOSE(UNIT_DUMP)
      RETURN
      END
