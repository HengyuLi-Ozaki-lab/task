! ti_graphics_stubs.f90
!
! Phase L-4: minimal stand-ins for the few GSAF / graphics entry points
! that TICORE may reference at run-time even though libtiapi.so excludes
! all real graphics output.
!
! Background: the non-graphics ti core (SRCS_CORE in ti/Makefile) does
! not call GUCLIP/PAGES/PAGEE/GUDATE/GUTIME/GUFLSH directly, but
! transitive dependencies pulled in from libpl_pic / libeq_pic or from
! the bpsd / adpost / adf11 libraries may reference them. The real
! GUCLIP lives in libgsp/libgsaf which are non-PIC and cannot be linked
! into a shared object; we therefore provide in-library replacements so
! dlopen() succeeds without dragging libg3d/libgsp into the .so.
!
! The stubs are no-ops (or, for GUCLIP, a simple REAL(X) cast). None of
! them are exercised by ti_init -> ti_run -> ti_finalize so the no-op
! behaviour is safe; if a future caller needs real output the right
! answer is to add a libtigrf_pic.a rather than to extend these stubs.
! Mirrors tr_graphics_stubs.f90 (PR #35).

REAL FUNCTION GUCLIP(X)
  IMPLICIT NONE
  DOUBLE PRECISION, INTENT(IN) :: X
  GUCLIP = REAL(X)
END FUNCTION GUCLIP

SUBROUTINE PAGES
  IMPLICIT NONE
END SUBROUTINE PAGES

SUBROUTINE PAGEE
  IMPLICIT NONE
END SUBROUTINE PAGEE

SUBROUTINE GUDATE(KK)
  IMPLICIT NONE
  CHARACTER(LEN=*), INTENT(OUT) :: KK
  KK = ' '
END SUBROUTINE GUDATE

SUBROUTINE GUTIME(KK)
  IMPLICIT NONE
  CHARACTER(LEN=*), INTENT(OUT) :: KK
  KK = ' '
END SUBROUTINE GUTIME

SUBROUTINE GUFLSH
  IMPLICIT NONE
END SUBROUTINE GUFLSH

! ----------------------------------------------------------------------
! Additional stubs for the macOS shared-library build. Apple's dlopen
! does eager symbol resolution; any unresolved import causes dlopen to
! fail. These no-op stubs satisfy the eager check; the .so init / run /
! finalize path never reaches them.
! ----------------------------------------------------------------------

SUBROUTINE MOVE2D(X, Y)
  IMPLICIT NONE
  REAL, INTENT(IN) :: X, Y
END SUBROUTINE MOVE2D

SUBROUTINE DRAW2D(X, Y)
  IMPLICIT NONE
  REAL, INTENT(IN) :: X, Y
END SUBROUTINE DRAW2D

SUBROUTINE EQGOUT(MODE)
  IMPLICIT NONE
  INTEGER, INTENT(IN) :: MODE
END SUBROUTINE EQGOUT

! GSAF text-mode graphics primitives (MOVE/TEXT/NUMBD). Stubs only.
SUBROUTINE MOVE(X, Y)
  IMPLICIT NONE
  REAL, INTENT(IN) :: X, Y
END SUBROUTINE MOVE

SUBROUTINE TEXT(STR, NW)
  IMPLICIT NONE
  CHARACTER(LEN=*), INTENT(IN) :: STR
  INTEGER, INTENT(IN) :: NW
END SUBROUTINE TEXT

SUBROUTINE NUMBD(VAL, FMT, NW)
  IMPLICIT NONE
  REAL, INTENT(IN) :: VAL
  CHARACTER(LEN=*), INTENT(IN) :: FMT
  INTEGER, INTENT(IN) :: NW
END SUBROUTINE NUMBD

! libgrf module procedures used by graphics output paths excluded from
! the .so. These don't need to do anything; the symbols just need to
! exist for dyld.
MODULE grd1d_mod
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: grd1d
CONTAINS
  SUBROUTINE GRD1D(NGP, FX, FY, NXM, NXMAX, NLMAX)
    INTEGER, INTENT(IN) :: NGP, NXM, NXMAX, NLMAX
    REAL, INTENT(IN) :: FX(*), FY(*)
  END SUBROUTINE GRD1D
END MODULE grd1d_mod

MODULE grd2d_mod
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: grd2d
CONTAINS
  SUBROUTINE GRD2D(NGP, FX, FY, FF, NXM, NXMAX, NYMAX)
    INTEGER, INTENT(IN) :: NGP, NXM, NXMAX, NYMAX
    REAL, INTENT(IN) :: FX(*), FY(*), FF(*)
  END SUBROUTINE GRD2D
END MODULE grd2d_mod
