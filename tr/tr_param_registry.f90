! tr_param_registry.f90
!
! Phase L-3: setter table for namelist (trparm.f90) parameters.
!
! Implements a hand-written SELECT CASE dispatch that maps a parameter
! name (optionally with a 1-origin subscript in square brackets, e.g.
! "PN[1]") to an assignment into the matching TRCOMM variable.
!
! The initial set follows design doc §5.3:
!   - geometry/device scalars (RR, RA, RKAP, RDLT, BB, PHIA, RIPS, RIPE)
!   - plasma scalars/arrays  (NSMAX, PA[i], PZ[i], PN[i], PNS[i], PT[i], PTS[i])
!   - time evolution         (DT, NTMAX, NTSTEP, EPSLTR, LMAXTR)
!   - transport switches     (MDLKAI, MDLETA, MDLAD, MDLAVK, CDW[i], CHP,
!                             CK0, CK1)
!   - module switches        (MDLNB, MDLEC, MDLLH, MDLIC, MDLPEL,
!                             MDLJBS, MDLST, MDLNF, MDLUF)
!
! Approximately 34 unique names covering ~50 settable variables once
! array subscripts are counted. Additional namelist vars may be added
! in a later PR by extending the SELECT CASE list; the parser handles
! any "NAME" or "NAME[idx]" input unchanged.
!
! See docs/superpowers/specs/2026-04-17-tr-library-design.md §5 and
! docs/superpowers/plans/2026-04-18-tr-library-L3-param-registry.md.

MODULE tr_param_registry
  USE trcomm, ONLY: rkind, &
       RR, RA, RKAP, RDLT, BB, PHIA, &
       NSMAX, PA, PZ, PN, PNS, PT, PTS, &
       RIPS, RIPE, &
       DT, NTMAX, NTSTEP, EPSLTR, LMAXTR, &
       MDLKAI, MDLETA, MDLAD, MDLAVK, CDW, CHP, CK0, CK1, &
       MDLNB, MDLEC, MDLLH, MDLIC, MDLPEL, MDLJBS, MDLST, MDLNF, MDLUF
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: tr_param_set
  PUBLIC :: parse_array_subscript_pub   ! exported for unit-test only

CONTAINS

  FUNCTION tr_param_set(name, value) RESULT(ierr)
    CHARACTER(LEN=*), INTENT(IN) :: name
    REAL(rkind),      INTENT(IN) :: value
    INTEGER :: ierr
    INTEGER :: idx
    CHARACTER(LEN=32) :: b

    ierr = 0
    CALL parse_array_subscript(name, b, idx)

    SELECT CASE (TRIM(b))
    ! --- geometry / device scalars ---------------------------------
    CASE ("RR");    RR    = value
    CASE ("RA");    RA    = value
    CASE ("RKAP");  RKAP  = value
    CASE ("RDLT");  RDLT  = value
    CASE ("BB");    BB    = value
    CASE ("PHIA");  PHIA  = value
    ! --- plasma scalars --------------------------------------------
    CASE ("NSMAX"); NSMAX = INT(value)
    ! --- plasma arrays (1..NSMM, 1-origin; NSMM=100 per tr/trcom0.f90)
    !     SIZE(arr) keeps the bound check correct if the declared
    !     dimension constant is renamed.
    CASE ("PA");    IF (idx < 1 .OR. idx > SIZE(PA))  THEN; ierr = 1; ELSE; PA(idx)  = value; END IF
    CASE ("PZ");    IF (idx < 1 .OR. idx > SIZE(PZ))  THEN; ierr = 1; ELSE; PZ(idx)  = value; END IF
    CASE ("PN");    IF (idx < 1 .OR. idx > SIZE(PN))  THEN; ierr = 1; ELSE; PN(idx)  = value; END IF
    CASE ("PNS");   IF (idx < 1 .OR. idx > SIZE(PNS)) THEN; ierr = 1; ELSE; PNS(idx) = value; END IF
    CASE ("PT");    IF (idx < 1 .OR. idx > SIZE(PT))  THEN; ierr = 1; ELSE; PT(idx)  = value; END IF
    CASE ("PTS");   IF (idx < 1 .OR. idx > SIZE(PTS)) THEN; ierr = 1; ELSE; PTS(idx) = value; END IF
    ! --- current ---------------------------------------------------
    CASE ("RIPS");  RIPS  = value
    CASE ("RIPE");  RIPE  = value
    ! --- time evolution --------------------------------------------
    CASE ("DT");     DT     = value
    CASE ("NTMAX");  NTMAX  = INT(value)
    CASE ("NTSTEP"); NTSTEP = INT(value)
    CASE ("EPSLTR"); EPSLTR = value
    CASE ("LMAXTR"); LMAXTR = INT(value)
    ! --- transport model switches & coefficients -------------------
    CASE ("MDLKAI"); MDLKAI = INT(value)
    CASE ("MDLETA"); MDLETA = INT(value)
    CASE ("MDLAD");  MDLAD  = INT(value)
    CASE ("MDLAVK"); MDLAVK = INT(value)
    CASE ("CDW");    IF (idx < 1 .OR. idx > SIZE(CDW)) THEN; ierr = 1; ELSE; CDW(idx) = value; END IF
    CASE ("CHP");    CHP   = value
    CASE ("CK0");    CK0   = value
    CASE ("CK1");    CK1   = value
    ! --- module switches -------------------------------------------
    CASE ("MDLNB");  MDLNB  = INT(value)
    CASE ("MDLEC");  MDLEC  = INT(value)
    CASE ("MDLLH");  MDLLH  = INT(value)
    CASE ("MDLIC");  MDLIC  = INT(value)
    CASE ("MDLPEL"); MDLPEL = INT(value)
    CASE ("MDLJBS"); MDLJBS = INT(value)
    CASE ("MDLST");  MDLST  = INT(value)
    CASE ("MDLNF");  MDLNF  = INT(value)
    CASE ("MDLUF");  MDLUF  = INT(value)
    CASE DEFAULT
       ierr = 1   ! unknown name
    END SELECT
  END FUNCTION tr_param_set

  !-------------------------------------------------------------------
  ! Split "NAME" or "NAME[N]" into (base, idx).
  !
  !   "RR"      -> base="RR",  idx=0       (scalar form)
  !   "PN[1]"   -> base="PN",  idx=1       (1-origin subscript)
  !   "CDW[12]" -> base="CDW", idx=12
  !   malformed -> base=<full>, idx=-1     (caller returns ierr=1)
  !-------------------------------------------------------------------
  SUBROUTINE parse_array_subscript(full_name, base, idx)
    CHARACTER(LEN=*), INTENT(IN)  :: full_name
    CHARACTER(LEN=*), INTENT(OUT) :: base
    INTEGER,          INTENT(OUT) :: idx
    INTEGER :: lb, rb, ios
    base = ' '
    idx  = 0
    lb = INDEX(full_name, '[')
    rb = INDEX(full_name, ']')
    IF (lb == 0 .AND. rb == 0) THEN
       base = TRIM(ADJUSTL(full_name))
       RETURN
    END IF
    IF (lb == 0 .OR. rb == 0 .OR. rb <= lb + 1) THEN
       base = TRIM(ADJUSTL(full_name))   ! malformed; caller returns ierr=1
       idx  = -1
       RETURN
    END IF
    base = full_name(1:lb-1)
    READ(full_name(lb+1:rb-1), *, IOSTAT=ios) idx
    IF (ios /= 0) idx = -1
  END SUBROUTINE parse_array_subscript

  ! Public alias for unit testing only.
  SUBROUTINE parse_array_subscript_pub(full_name, base, idx)
    CHARACTER(LEN=*), INTENT(IN)  :: full_name
    CHARACTER(LEN=*), INTENT(OUT) :: base
    INTEGER,          INTENT(OUT) :: idx
    CALL parse_array_subscript(full_name, base, idx)
  END SUBROUTINE parse_array_subscript_pub

END MODULE tr_param_registry
