! equ_param_registry.f90
!
! Name -> variable dispatch of the EQU library interface (equ_api.f90):
! one CASE per variable of the &EQU namelist (eqnlin, equinit.f90), as
! eq/eq_param_registry.f90 does for EQ. A new namelist variable that a
! caller is to set gets a CASE here, its line in the MCP server's
! PARAMETER_REGISTRY (python/mcp-servers/equ_mcp/server.py) and, for an
! integer, its name in value_refused; python/equlib/tests/test_param_values.py
! holds the three to each other.
!
! Names: NAME, or NAME[i] for an array, with the index as Fortran declares
! it. Refused (ierr = 1): a malformed subscript, a subscript on a scalar,
! a bare array name, an index out of bounds, an unknown name, a value that
! is not finite, and for an integer a value with a fraction or beyond the
! default integer. Names the namelist accepts but nothing reads give
! ierr = 2 (equ_param_is_unused).

MODULE equ_param_registry
  USE, INTRINSIC :: ieee_arithmetic, ONLY: ieee_is_finite
  USE geo_mod, ONLY: nr, nz
  USE eqv_mod, ONLY: nv
  USE equ_mod, ONLY: nsumax, btv, isep, dsep, rloop, zloop, &
                     msetup, esetup, ieqmax, eeqmax, iodmax, eodmax, &
                     iadmax, eadmax, bavmax, bavmin
  USE aaa_mod, ONLY: iudsym, device, devnam, title
  USE par_mod, ONLY: rwmn, rwmx, zwmx, tcur, rmaj, rpla, &
                     zpla, elip, trig, elipup, trigup, yh, &
                     yd, qaxi, qsur, xxli, icp, cp
  USE vac_mod, ONLY: ivac, ncoil, cvac, cvacst, cvacwg, cvact, &
                     isvac, msfx, rvac, zvac, ilimt, ivbnd
  USE cnt_mod, ONLY: ieqout, ieqrd
  USE eqinit_mod, ONLY: knamcoil
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: equ_param_set, equ_param_set_str, equ_param_is_unused
  INTEGER, PARAMETER :: dp = KIND(1.0D0)

CONTAINS

  !-------------------------------------------------------------------
  ! equ_param_set : a numeric parameter. ierr 0 set, 1 refused, 2 unused.
  !-------------------------------------------------------------------
  SUBROUTINE equ_param_set(name, value, ierr)
    CHARACTER(LEN=*), INTENT(IN)  :: name
    REAL(dp),         INTENT(IN)  :: value
    INTEGER,          INTENT(OUT) :: ierr
    CHARACTER(LEN=32) :: b
    INTEGER :: idx

    ierr = 0
    CALL parse_array_subscript(name, b, idx)
    IF (LEN_TRIM(b) == 0) THEN
       ierr = 1
       RETURN
    END IF
    IF (equ_param_is_unused(b) .AND. idx == -1) THEN
       ierr = 2
       RETURN
    END IF
    IF (value_refused(b, value)) THEN
       ierr = 1
       RETURN
    END IF

    SELECT CASE (TRIM(b))
    CASE ("NR")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          nr = INT(value)
       END IF
    CASE ("NZ")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          nz = INT(value)
       END IF
    CASE ("NV")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          nv = INT(value)
       END IF
    CASE ("NSUMAX")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          nsumax = INT(value)
       END IF
    CASE ("IUDSYM")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          iudsym = INT(value)
       END IF
    CASE ("RWMN")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          rwmn = value
       END IF
    CASE ("RWMX")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          rwmx = value
       END IF
    CASE ("ZWMX")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          zwmx = value
       END IF
    CASE ("BTV")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          btv = value
       END IF
    CASE ("TCUR")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          tcur = value
       END IF
    CASE ("RMAJ")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          rmaj = value
       END IF
    CASE ("RPLA")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          rpla = value
       END IF
    CASE ("ZPLA")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          zpla = value
       END IF
    CASE ("ELIP")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          elip = value
       END IF
    CASE ("TRIG")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          trig = value
       END IF
    CASE ("ELIPUP")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          elipup = value
       END IF
    CASE ("TRIGUP")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          trigup = value
       END IF
    CASE ("YH")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          yh = value
       END IF
    CASE ("YD")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          yd = value
       END IF
    CASE ("QAXI")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          qaxi = value
       END IF
    CASE ("QSUR")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          qsur = value
       END IF
    CASE ("XXLI")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          xxli = value
       END IF
    CASE ("ICP")   ! (1:10)
       IF (idx < LBOUND(icp, 1) .OR. idx > UBOUND(icp, 1)) THEN
          ierr = 1
       ELSE
          icp(idx) = INT(value)
       END IF
    CASE ("CP")   ! (1:10)
       IF (idx < LBOUND(cp, 1) .OR. idx > UBOUND(cp, 1)) THEN
          ierr = 1
       ELSE
          cp(idx) = value
       END IF
    CASE ("IVAC")   ! (0:18)
       IF (idx < LBOUND(ivac, 1) .OR. idx > UBOUND(ivac, 1)) THEN
          ierr = 1
       ELSE
          ivac(idx) = INT(value)
       END IF
    CASE ("NCOIL")   ! (0:18)
       IF (idx < LBOUND(ncoil, 1) .OR. idx > UBOUND(ncoil, 1)) THEN
          ierr = 1
       ELSE
          ncoil(idx) = INT(value)
       END IF
    CASE ("CVAC")   ! (0:18)
       IF (idx < LBOUND(cvac, 1) .OR. idx > UBOUND(cvac, 1)) THEN
          ierr = 1
       ELSE
          cvac(idx) = value
       END IF
    CASE ("CVACST")   ! (0:18)
       IF (idx < LBOUND(cvacst, 1) .OR. idx > UBOUND(cvacst, 1)) THEN
          ierr = 1
       ELSE
          cvacst(idx) = value
       END IF
    CASE ("CVACWG")   ! (0:18)
       IF (idx < LBOUND(cvacwg, 1) .OR. idx > UBOUND(cvacwg, 1)) THEN
          ierr = 1
       ELSE
          cvacwg(idx) = value
       END IF
    CASE ("CVACT")   ! (0:18)
       IF (idx < LBOUND(cvact, 1) .OR. idx > UBOUND(cvact, 1)) THEN
          ierr = 1
       ELSE
          cvact(idx) = value
       END IF
    CASE ("ISVAC")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          isvac = INT(value)
       END IF
    CASE ("MSFX")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          msfx = INT(value)
       END IF
    CASE ("RVAC")   ! (0:30)
       IF (idx < LBOUND(rvac, 1) .OR. idx > UBOUND(rvac, 1)) THEN
          ierr = 1
       ELSE
          rvac(idx) = value
       END IF
    CASE ("ZVAC")   ! (0:30)
       IF (idx < LBOUND(zvac, 1) .OR. idx > UBOUND(zvac, 1)) THEN
          ierr = 1
       ELSE
          zvac(idx) = value
       END IF
    CASE ("ISEP")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          isep = INT(value)
       END IF
    CASE ("DSEP")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          dsep = value
       END IF
    CASE ("ILIMT")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          ilimt = INT(value)
       END IF
    CASE ("IVBND")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          ivbnd = INT(value)
       END IF
    CASE ("RLOOP")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          rloop = value
       END IF
    CASE ("ZLOOP")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          zloop = value
       END IF
    CASE ("MSETUP")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          msetup = INT(value)
       END IF
    CASE ("ESETUP")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          esetup = value
       END IF
    CASE ("IEQMAX")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          ieqmax = INT(value)
       END IF
    CASE ("EEQMAX")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          eeqmax = value
       END IF
    CASE ("IODMAX")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          iodmax = INT(value)
       END IF
    CASE ("EODMAX")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          eodmax = value
       END IF
    CASE ("IADMAX")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          iadmax = INT(value)
       END IF
    CASE ("EADMAX")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          eadmax = value
       END IF
    CASE ("BAVMAX")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          bavmax = value
       END IF
    CASE ("BAVMIN")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          bavmin = value
       END IF
    CASE ("IEQOUT")   ! (1:10)
       IF (idx < LBOUND(ieqout, 1) .OR. idx > UBOUND(ieqout, 1)) THEN
          ierr = 1
       ELSE
          ieqout(idx) = INT(value)
       END IF
    CASE ("IEQRD")
       IF (idx /= -1) THEN
          ierr = 1
       ELSE
          ieqrd = INT(value)
       END IF
    CASE DEFAULT
       ierr = 1
    END SELECT
  END SUBROUTINE equ_param_set

  !-------------------------------------------------------------------
  ! equ_param_set_str : a CHARACTER parameter. ierr 0 set, 1 refused
  ! (unknown name, or a value longer than the variable: it is not cut).
  !-------------------------------------------------------------------
  SUBROUTINE equ_param_set_str(name, value, ierr)
    CHARACTER(LEN=*), INTENT(IN)  :: name
    CHARACTER(LEN=*), INTENT(IN)  :: value
    INTEGER,          INTENT(OUT) :: ierr

    ierr = 0
    SELECT CASE (TRIM(ADJUSTL(name)))
    CASE ("DEVICE")   ! CHARACTER(LEN=8)
       IF (LEN_TRIM(value) > LEN(device)) THEN
          ierr = 1
       ELSE
          device = TRIM(value)
       END IF
    CASE ("DEVNAM")   ! CHARACTER(LEN=8)
       IF (LEN_TRIM(value) > LEN(devnam)) THEN
          ierr = 1
       ELSE
          devnam = TRIM(value)
       END IF
    CASE ("TITLE")   ! CHARACTER(LEN=70)
       IF (LEN_TRIM(value) > LEN(title)) THEN
          ierr = 1
       ELSE
          title = TRIM(value)
       END IF
    CASE ("KNAMCOIL")   ! CHARACTER(LEN=80)
       IF (LEN_TRIM(value) > LEN(knamcoil)) THEN
          ierr = 1
       ELSE
          knamcoil = TRIM(value)
       END IF
    CASE DEFAULT
       ierr = 1
    END SELECT
  END SUBROUTINE equ_param_set_str

  !-------------------------------------------------------------------
  ! equ_param_is_unused : names the &EQU namelist accepts that EQU does
  ! not read (IVP, IVTAB, IVGRP, JEQRD, IEQWT, JEQWT) and the three
  ! dummies of eqnlin (EQFILE, RWAL, ZWAL).
  !-------------------------------------------------------------------
  LOGICAL FUNCTION equ_param_is_unused(b)
    CHARACTER(LEN=*), INTENT(IN) :: b
    SELECT CASE (TRIM(b))
    CASE ("IVP", "IVTAB", "IVGRP", "JEQRD", "IEQWT", "JEQWT", "EQFILE", "RWAL", "ZWAL")
       equ_param_is_unused = .TRUE.
    CASE DEFAULT
       equ_param_is_unused = .FALSE.
    END SELECT
  END FUNCTION equ_param_is_unused

  !-------------------------------------------------------------------
  ! value_refused : not finite, for every name; for an integer name a
  ! fraction or a value beyond the default integer (INT would be the
  ! compiler's choice there). The names are the integer CASEs above.
  !-------------------------------------------------------------------
  LOGICAL FUNCTION value_refused(b, value)
    CHARACTER(LEN=*), INTENT(IN) :: b
    REAL(dp),         INTENT(IN) :: value

    value_refused = .NOT. ieee_is_finite(value)
    IF (value_refused) RETURN
    SELECT CASE (TRIM(b))
    CASE ("NR", "NZ", "NV", "NSUMAX", "IUDSYM", "ICP", &
          "IVAC", "NCOIL", "ISVAC", "MSFX", "ISEP", "ILIMT", &
          "IVBND", "MSETUP", "IEQMAX", "IODMAX", "IADMAX", "IEQOUT", &
          "IEQRD")
       value_refused = ABS(value) > REAL(HUGE(0), dp) .OR. &
                       value /= AINT(value)
    END SELECT
  END FUNCTION value_refused

  !-------------------------------------------------------------------
  ! parse_array_subscript : "NAME" -> (NAME, -1); "NAME[N]" -> (NAME, N)
  ! for N an unsigned whole number of at most nine digits; anything else
  ! (one bracket, an empty or non-digit subscript, text after "]", a name
  ! longer than BASE) -> (blank, -1). From eq/eq_param_registry.f90.
  !-------------------------------------------------------------------
  SUBROUTINE parse_array_subscript(full_name, base, idx)
    CHARACTER(LEN=*), INTENT(IN)  :: full_name
    CHARACTER(LEN=*), INTENT(OUT) :: base
    INTEGER,          INTENT(OUT) :: idx
    INTEGER :: lb, rb, n, i, k
    CHARACTER(LEN=LEN(full_name)) :: sub
    base = ' '
    idx  = -1
    lb = INDEX(full_name, '[')
    rb = INDEX(full_name, ']')
    IF (lb == 0 .AND. rb == 0) THEN
       IF (LEN_TRIM(ADJUSTL(full_name)) > LEN(base)) RETURN
       base = TRIM(ADJUSTL(full_name))
       RETURN
    END IF
    IF (lb == 0 .OR. rb == 0 .OR. rb <= lb + 1) RETURN
    IF (rb /= LEN_TRIM(full_name) .OR. lb - 1 > LEN(base)) RETURN
    sub = ADJUSTL(full_name(lb+1:rb-1))
    n = LEN_TRIM(sub)
    IF (n == 0 .OR. n > 9) RETURN
    IF (VERIFY(sub(1:n), '0123456789') /= 0) RETURN
    k = 0
    DO i = 1, n
       k = 10 * k + (IACHAR(sub(i:i)) - IACHAR('0'))
    END DO
    idx  = k
    base = full_name(1:lb-1)
  END SUBROUTINE parse_array_subscript

END MODULE equ_param_registry
