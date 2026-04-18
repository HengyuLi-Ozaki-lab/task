! fp_graphics_stubs.f90
!
! Phase L-4: minimal stand-ins for the few GSAF / graphics entry points
! that FP core code references at run-time even though libfpapi.so excludes
! all real graphics output.
!
! Background: SRCS_CORE includes fploop.f90, fpprep.f90, fpcale.f90, fpcoef.f90,
! fpnfrr.f90, etc. which contain CALL GUTIME(t) for timing measurements.
! GUTIME lives in libgsp/libgsaf which are non-PIC and cannot be linked into
! a shared object. We therefore provide an in-tree replacement that returns
! the elapsed CPU time via the Fortran intrinsic CPU_TIME.
!
! Other stubs (PAGES, PAGEE, GRD1D, FPGRFA, etc.) are no-ops / returns that
! cover graphics paths gated by IDBGFP debug flags. They are not exercised
! during normal fp_init -> fp_run -> fp_finalize but the linker still needs
! the symbols to resolve. RTLD_LAZY at dlopen time would also work for any
! we miss, but providing them here gives an `ldd`-clean .so.

REAL FUNCTION GUCLIP(X)
  IMPLICIT NONE
  DOUBLE PRECISION, INTENT(IN) :: X
  GUCLIP = REAL(X)
END FUNCTION GUCLIP

SUBROUTINE GUTIME(T)
  IMPLICIT NONE
  REAL, INTENT(OUT) :: T
  CALL CPU_TIME(T)
END SUBROUTINE GUTIME

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

SUBROUTINE GUFLSH
  IMPLICIT NONE
END SUBROUTINE GUFLSH
