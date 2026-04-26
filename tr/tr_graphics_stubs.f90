! tr_graphics_stubs.f90
!
! Phase L-4: minimal stand-ins for the few GSAF / graphics entry points
! that TRCORE references at run-time even though libtrapi.so excludes
! all real graphics output.
!
! Background: SRCS_CORE includes trrslt_globals.f90 (TRGLOB) which is
! invoked every NTSTEP from tr_eval (trexec.f90 ~line 410). TRGLOB calls
! GUCLIP to truncate REAL(8) -> REAL(4) for time-series storage. The real
! GUCLIP lives in libgsp/libgsaf which are non-PIC and cannot be linked
! into a shared object; we therefore provide an in-tree replacement that
! does just the cast.
!
! The remaining stubs (PAGES, PAGEE, GUDATE, GUTIME, GUFLSH) are no-ops
! that prevent dlopen from failing if any code path eventually reaches a
! plotting hook. None of them are exercised by tr_init -> tr_run ->
! tr_finalize so the no-op behaviour is safe; if a future caller needs
! real output the right answer is to add a libtrgrf_pic.a (see design
! doc Section A.4) rather than to extend these stubs.

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
! Additional stubs needed for the macOS shared-library build.
!
! On Linux, ld's -Wl,--start-group resolves cycles across the linked
! archives so calls like trfout.f90's CALL VIEWRTLIST(...) are pulled
! in from trgrad.f90 (graphics) even though SRCS_GRAPHICS is excluded
! from libtrapi.so — the resulting unresolved symbol is recorded as a
! "lazy" import and dlopen succeeds. Apple's ld doesn't re-scan
! archives, and Apple's dlopen does eager symbol resolution, so any
! unresolved import causes dlopen to fail. Defining them here as
! no-ops makes libtrapi.so loadable on macOS as well; the .so init /
! run / finalize path never reaches them, so no-op behaviour is safe.
! ----------------------------------------------------------------------

SUBROUTINE VIEWRTLIST(NMAX)
  IMPLICIT NONE
  INTEGER, INTENT(IN) :: NMAX
END SUBROUTINE VIEWRTLIST

SUBROUTINE VIEWGTLIST(NMAX)
  IMPLICIT NONE
  INTEGER, INTENT(IN) :: NMAX
END SUBROUTINE VIEWGTLIST

SUBROUTINE GETKRT(NP, KRT)
  IMPLICIT NONE
  INTEGER, INTENT(IN) :: NP
  CHARACTER(LEN=*), INTENT(OUT) :: KRT
  KRT = ' '
END SUBROUTINE GETKRT

SUBROUTINE GETKGT(NP, KGT)
  IMPLICIT NONE
  INTEGER, INTENT(IN) :: NP
  CHARACTER(LEN=*), INTENT(OUT) :: KGT
  KGT = ' '
END SUBROUTINE GETKGT

! draw_cross / eqfile graphics paths in eq's plotting code call these.
! eq has its own eq_graphics_stubs.f90 that defines them, but those are
! only included in libeqapi.so; libtrapi.so links libeq_pic.a which
! lacks the stubs. Provide local fallbacks here.
SUBROUTINE MOVE2D(X, Y)
  IMPLICIT NONE
  REAL, INTENT(IN) :: X, Y
END SUBROUTINE MOVE2D

SUBROUTINE DRAW2D(X, Y)
  IMPLICIT NONE
  REAL, INTENT(IN) :: X, Y
END SUBROUTINE DRAW2D

! eqgout writes equilibrium plot files; not on the libtrapi.so happy path.
SUBROUTINE EQGOUT(MODE)
  IMPLICIT NONE
  INTEGER, INTENT(IN) :: MODE
END SUBROUTINE EQGOUT

! grd2d is a libgrf module procedure used by trgrar/trgrap (graphics
! plotting). The full implementation lives in lib/libgrf/grd2d.f90 but
! libtrapi.so deliberately excludes libgrf to avoid X11 dependency. The
! interface is variadic with many optional args; provide a minimal
! interface that satisfies the non-graphics call sites (none on the
! libtrapi.so happy path).
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
