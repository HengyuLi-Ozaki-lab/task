! eq_graphics_stubs.f90
!
! Phase L-4: minimal no-op stand-ins for the GSAF / grafix entry points
! that eq's SRCS_CORE references at run-time even though libeqapi.so
! excludes all real graphics output.
!
! Background: libgsp / libg3d (the real GSAF implementations) are
! distributed as non-PIC static archives and cannot be linked into a
! PIC shared object. libeqapi.so therefore provides these symbols as
! no-ops so that dlopen() succeeds and any code path that happens to
! reach a plotting hook returns silently. None of them are exercised
! by eq_init -> eq_run -> eq_get_state -> eq_finalize on the happy
! path, so the no-op behaviour is safe. If a future caller needs real
! plots the right answer is to add a libeqgrf_pic.a (see design doc
! Section A.4) rather than to extend these stubs.
!
! GUCLIP is the one exception: it is called from equread / eqfile to
! cast REAL(8) -> REAL(4) for time-series storage, so we implement the
! actual cast, matching tr_graphics_stubs.f90.
!
! grd2d / grd1d are libgrf module procedures rather than plain GSAF
! symbols; they are satisfied at link time by libgrf_pic.a and do NOT
! need a stub here.

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

! draw_cross in eqfile.f90 calls these; only reached on plotting paths
! that the C ABI does not exercise (eq_save / eqdsk diagnostics).
SUBROUTINE MOVE2D(X, Y)
  IMPLICIT NONE
  REAL, INTENT(IN) :: X, Y
END SUBROUTINE MOVE2D

SUBROUTINE DRAW2D(X, Y)
  IMPLICIT NONE
  REAL, INTENT(IN) :: X, Y
END SUBROUTINE DRAW2D

! ----------------------------------------------------------------------
! Additional stubs for the macOS shared-library build. Apple's dlopen
! does eager symbol resolution; any unresolved import causes dlopen to
! fail. These no-op stubs satisfy the eager check; the .so init / run /
! finalize path never reaches them.
! ----------------------------------------------------------------------

SUBROUTINE EQGOUT(MODE)
  IMPLICIT NONE
  INTEGER, INTENT(IN) :: MODE
END SUBROUTINE EQGOUT

! libgrf module procedures for graphics output paths excluded from .so.
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
