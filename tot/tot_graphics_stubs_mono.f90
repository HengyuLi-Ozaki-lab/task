! tot_graphics_stubs_mono.f90
!
! Unified graphics stubs for the L-7b-ii monolithic libtotapi_mono.so
! build. Consolidates the symbol union across the five per-module
! <mod>_graphics_stubs.f90 files (eq + tr + fp + ti + wrx) so the
! mono build can include exactly ONE stubs object, avoiding the
! duplicate-symbol link errors that arise when more than one
! per-module stubs .o is in the same .so.
!
! NOT used by the default per-module libtotapi.so build path — that
! path links each module's own stubs through that module's
! libXapi.so. This file is referenced only by tot/Makefile's
! libtotapi_mono.so target.
!
! Pattern: hand-authored union, each symbol defined ONCE. Grouped
! below by *primary* provenance so future readers can trace back to
! the originating per-module stubs file.
!
! ABI choices for symbols where the per-module stubs diverge:
!
! * GUTIME — eq/tr/ti/tot declare `SUBROUTINE GUTIME(KK)` with
!   `CHARACTER(LEN=*), INTENT(OUT) :: KK`; fp/wrx declare
!   `SUBROUTINE GUTIME(T)` with `REAL, INTENT(OUT) :: T` (CPU_TIME
!   wrapper). Same ELF symbol `_gutime_`, different caller-side
!   type — at first glance an ABI mismatch.
!
!   In-tree audit (in-house code review 2026-05-18) of all live
!   `CALL GUTIME` sites resolved the apparent conflict:
!   - **fp** (e.g. fploop.f90): passes a REAL local — matches our
!     stub.
!   - **tr** (trmain.f90, trrslt_print.f90): passes `GTCPU1` /
!     `GTCPU2`, both declared `REAL` — matches our stub.
!   - **eq / ti / tot**: zero live `CALL GUTIME` sites. The
!     CHARACTER declarations in their stubs are dead code carried
!     for the per-module .so's "every stub exported" hygiene; no
!     mono-build caller reaches them.
!
!   The REAL ABI is therefore unconditionally correct on the
!   reachable surface — no "bounded UB" actually occurs at runtime.
!
! * EQGOUT — eq/tr/fp/ti declare `SUBROUTINE EQGOUT(MODE)` with
!   `INTEGER, INTENT(IN) :: MODE`; wrx declares `SUBROUTINE EQGOUT`
!   (no args). In-tree audit confirms the 1-arg form is correct:
!   - tr passes `0`, eq passes `MSTAT` / `1`, fp/ti pass an integer.
!   - **wrx has zero live `CALL EQGOUT` sites** — its no-arg stub
!     is dead code, same hygiene rationale as the eq/ti/tot GUTIME
!     case above.
!
! * GRD1D — fp/ti expose it as `MODULE grd1d_mod` (symbol
!   `___grd1d_mod_MOD_grd1d`); wrx exposes it as a standalone
!   `SUBROUTINE GRD1D` (symbol `_grd1d_`). These are TWO DIFFERENT
!   ELF symbols (module-qualified vs flat), so no ABI conflict.
!   Both are provided below.

! ======================================================================
! Section 1: symbols common across most/all modules
! ======================================================================
! (eq + tr + fp + ti + tot + wrx all declare these — first 7
!  matchable across all 6 stub files)

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

SUBROUTINE GUFLSH
  IMPLICIT NONE
END SUBROUTINE GUFLSH

! GUTIME — REAL ABI. All live CALL GUTIME sites (fp + tr) pass a
! REAL local; eq/ti/tot have no live callers. See header note.
SUBROUTINE GUTIME(T)
  IMPLICIT NONE
  REAL, INTENT(OUT) :: T
  CALL CPU_TIME(T)
END SUBROUTINE GUTIME

! ======================================================================
! Section 2: 2D plotting stubs (common to eq + tr + fp + ti + wrx)
! ======================================================================

SUBROUTINE MOVE2D(X, Y)
  IMPLICIT NONE
  REAL, INTENT(IN) :: X, Y
END SUBROUTINE MOVE2D

SUBROUTINE DRAW2D(X, Y)
  IMPLICIT NONE
  REAL, INTENT(IN) :: X, Y
END SUBROUTINE DRAW2D

! EQGOUT — 1-arg form. eq/tr/fp/ti pass an integer; wrx has no
! live CALL EQGOUT sites. See header note.
SUBROUTINE EQGOUT(MODE)
  IMPLICIT NONE
  INTEGER, INTENT(IN) :: MODE
END SUBROUTINE EQGOUT

! ======================================================================
! Section 3: tr-unique stubs
! ======================================================================
! tr/trview.f90 + trrslt_*.f90 reference these on the view-menu /
! result-list paths. The C ABI happy path does not reach them.

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
  INTEGER, INTENT(OUT) :: NP
  CHARACTER(LEN=*), INTENT(OUT) :: KRT(*)
  NP = 0
END SUBROUTINE GETKRT

SUBROUTINE GETKGT(NP, KGT)
  IMPLICIT NONE
  INTEGER, INTENT(OUT) :: NP
  CHARACTER(LEN=*), INTENT(OUT) :: KGT(*)
  NP = 0
END SUBROUTINE GETKGT

! ======================================================================
! Section 4: ti-unique stubs (MOVE / TEXT / NUMBD)
! ======================================================================
! ti/tigout.f90 references these on the print-page path. NUMBD also
! appears in tot/tot_graphics_stubs.f90 with the same signature; we
! keep this single definition.

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

! ======================================================================
! Section 5: wrx-unique stubs (GSAF subroutine surface)
! ======================================================================
! wrx/wrview.f90 + wrx_dump_state.f90 + wrcalpwr.f90 reference these
! on the wave-plot diagnostic paths. None reached on the .so happy
! path (wrx_init -> wrx_set_param -> wrx_run -> wrx_get_state ->
! wrx_finalize). Arguments are intentionally typed as REAL / INTEGER
! with no INTENT(OUT) writes so call sites passing arbitrary types
! don't trip a write through a wrong-typed pointer.

SUBROUTINE GSOPEN
  IMPLICIT NONE
END SUBROUTINE GSOPEN

SUBROUTINE GSCLOS
  IMPLICIT NONE
END SUBROUTINE GSCLOS

! Standalone GRD1D (wrx-only; distinct ELF symbol from
! grd1d_mod%GRD1D in §7 below)
SUBROUTINE GRD1D(IPAT, X, Y, NXM, NXMAX, NGMAX, TITLE, MODE_XY)
  IMPLICIT NONE
  INTEGER, INTENT(IN) :: IPAT, NXM, NXMAX, NGMAX, MODE_XY
  REAL,    INTENT(IN) :: X(*), Y(*)
  CHARACTER(LEN=*), INTENT(IN) :: TITLE
END SUBROUTINE GRD1D

SUBROUTINE R2W2B(FACTOR, RGB)
  IMPLICIT NONE
  REAL, INTENT(IN)  :: FACTOR
  REAL, INTENT(OUT) :: RGB(3)
  RGB = 0.0
END SUBROUTINE R2W2B

SUBROUTINE W2G2B(FACTOR, RGB)
  IMPLICIT NONE
  REAL, INTENT(IN)  :: FACTOR
  REAL, INTENT(OUT) :: RGB(3)
  RGB = 0.0
END SUBROUTINE W2G2B

SUBROUTINE R2Y2W(FACTOR, RGB)
  IMPLICIT NONE
  REAL, INTENT(IN)  :: FACTOR
  REAL, INTENT(OUT) :: RGB(3)
  RGB = 0.0
END SUBROUTINE R2Y2W

SUBROUTINE GMNMX1(A, N, M, XMIN, XMAX)
  IMPLICIT NONE
  REAL,    INTENT(IN)  :: A(*)
  INTEGER, INTENT(IN)  :: N, M
  REAL,    INTENT(OUT) :: XMIN, XMAX
  XMIN = 0.0; XMAX = 0.0
END SUBROUTINE GMNMX1

SUBROUTINE GMNMX2(A, NX, NY, NXM, M1, M2, XMIN, XMAX)
  IMPLICIT NONE
  REAL,    INTENT(IN)  :: A(*)
  INTEGER, INTENT(IN)  :: NX, NY, NXM, M1, M2
  REAL,    INTENT(OUT) :: XMIN, XMAX
  XMIN = 0.0; XMAX = 0.0
END SUBROUTINE GMNMX2

SUBROUTINE GQSCAL(XMIN, XMAX, GXMIN, GXMAX, GXSTEP)
  IMPLICIT NONE
  REAL, INTENT(IN)  :: XMIN, XMAX
  REAL, INTENT(OUT) :: GXMIN, GXMAX, GXSTEP
  GXMIN = 0.0; GXMAX = 0.0; GXSTEP = 0.0
END SUBROUTINE GQSCAL

SUBROUTINE SETLIN(A, B, C)
  IMPLICIT NONE
  INTEGER, INTENT(IN) :: A, B, C
END SUBROUTINE SETLIN

SUBROUTINE SETCHS(A, B)
  IMPLICIT NONE
  REAL, INTENT(IN) :: A, B
END SUBROUTINE SETCHS

SUBROUTINE SETFNT(A)
  IMPLICIT NONE
  INTEGER, INTENT(IN) :: A
END SUBROUTINE SETFNT

SUBROUTINE SETRGB(R, G, B)
  IMPLICIT NONE
  REAL, INTENT(IN) :: R, G, B
END SUBROUTINE SETRGB

SUBROUTINE SETCLP(A, B, C, D)
  IMPLICIT NONE
  REAL, INTENT(IN) :: A, B, C, D
END SUBROUTINE SETCLP

SUBROUTINE SETLNW(A)
  IMPLICIT NONE
  REAL, INTENT(IN) :: A
END SUBROUTINE SETLNW

SUBROUTINE SETMKS(A, B)
  IMPLICIT NONE
  INTEGER, INTENT(IN) :: A
  REAL,    INTENT(IN) :: B
END SUBROUTINE SETMKS

SUBROUTINE GDEFIN(A, B, C, D, E, F, G, H)
  IMPLICIT NONE
  REAL, INTENT(IN) :: A, B, C, D, E, F, G, H
END SUBROUTINE GDEFIN

SUBROUTINE GFRAME
  IMPLICIT NONE
END SUBROUTINE GFRAME

SUBROUTINE GSCALE(A, B, C, D, E, F)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A, B, C, D, E
  INTEGER, INTENT(IN) :: F
END SUBROUTINE GSCALE

SUBROUTINE GSCALL(A, B, C, D, E, F)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A, B, C, D, E
  INTEGER, INTENT(IN) :: F
END SUBROUTINE GSCALL

SUBROUTINE GVALUE(A, B, C, D, E)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A, B, C, D
  INTEGER, INTENT(IN) :: E
END SUBROUTINE GVALUE

SUBROUTINE GVALUL(A, B, C, D, E)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A, B, C, D
  INTEGER, INTENT(IN) :: E
END SUBROUTINE GVALUL

SUBROUTINE GPLOTP(X, Y, N, A, B, C, D, E)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: X(*), Y(*)
  INTEGER, INTENT(IN) :: N, A, B, C, D, E
END SUBROUTINE GPLOTP

SUBROUTINE OFFCLP(A)
  IMPLICIT NONE
  INTEGER, INTENT(IN) :: A
END SUBROUTINE OFFCLP

SUBROUTINE INQLNW(A)
  IMPLICIT NONE
  REAL, INTENT(OUT) :: A
  A = 0.0
END SUBROUTINE INQLNW

SUBROUTINE INQTSZ(A)
  IMPLICIT NONE
  REAL, INTENT(OUT) :: A
  A = 0.0
END SUBROUTINE INQTSZ

INTEGER FUNCTION NGULEN(X)
  IMPLICIT NONE
  REAL, INTENT(IN) :: X
  NGULEN = 0
END FUNCTION NGULEN

! 3D plot stubs (wrx-only)
SUBROUTINE GDEFIN3D(A, B, C, D, E, F, G)
  IMPLICIT NONE
  REAL, INTENT(IN) :: A, B, C, D, E, F, G
END SUBROUTINE GDEFIN3D

SUBROUTINE GAXIS3D(A, B)
  IMPLICIT NONE
  REAL, INTENT(IN) :: A, B
END SUBROUTINE GAXIS3D

SUBROUTINE GSCALE3DX(A, B, C, D, E)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A, B, C, D
  INTEGER, INTENT(IN) :: E
END SUBROUTINE GSCALE3DX

SUBROUTINE GSCALE3DY(A, B, C, D, E)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A, B, C, D
  INTEGER, INTENT(IN) :: E
END SUBROUTINE GSCALE3DY

SUBROUTINE GSCALE3DZ(A, B, C, D, E)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A, B, C, D
  INTEGER, INTENT(IN) :: E
END SUBROUTINE GSCALE3DZ

SUBROUTINE GVALUE3DX(A, B, C, D, E)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A, B, C, D
  INTEGER, INTENT(IN) :: E
END SUBROUTINE GVALUE3DX

SUBROUTINE GVALUE3DY(A, B, C, D, E)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A, B, C, D
  INTEGER, INTENT(IN) :: E
END SUBROUTINE GVALUE3DY

SUBROUTINE GVALUE3DZ(A, B, C, D, E)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A, B, C, D
  INTEGER, INTENT(IN) :: E
END SUBROUTINE GVALUE3DZ

SUBROUTINE GVIEW3D(A, B, C, D, E, F, G)
  IMPLICIT NONE
  REAL, INTENT(IN) :: A, B, C, D, E, F, G
END SUBROUTINE GVIEW3D

! Contour stubs (wrx-only)
SUBROUTINE CONTF2(A, B, C, D, E, F, G, H)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A(*), B(*), C(*), D, E
  INTEGER, INTENT(IN) :: F, G, H
END SUBROUTINE CONTF2

SUBROUTINE CONTF3(A, B, C, D, E, F, G, H, I)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A(*), B(*), C(*), D, E, F
  INTEGER, INTENT(IN) :: G, H, I
END SUBROUTINE CONTF3

SUBROUTINE CONTF4(A, B, C, D, E, F, G, H, I, J)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A(*), B(*), C(*), D, E, F, G
  INTEGER, INTENT(IN) :: H, I, J
END SUBROUTINE CONTF4

SUBROUTINE CONTG2(A, B, C, D, E, F, G, H)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A(*), B(*), C(*), D, E
  INTEGER, INTENT(IN) :: F, G, H
END SUBROUTINE CONTG2

SUBROUTINE CONTG3(A, B, C, D, E, F, G, H, I)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A(*), B(*), C(*), D, E, F
  INTEGER, INTENT(IN) :: G, H, I
END SUBROUTINE CONTG3

SUBROUTINE CONTG4(A, B, C, D, E, F, G, H, I, J)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A(*), B(*), C(*), D, E, F, G
  INTEGER, INTENT(IN) :: H, I, J
END SUBROUTINE CONTG4

SUBROUTINE CONTQ2(A, B, C, D, E, F, G, H)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A(*), B(*), C(*), D, E
  INTEGER, INTENT(IN) :: F, G, H
END SUBROUTINE CONTQ2

SUBROUTINE CONTQ3(A, B, C, D, E, F, G, H, I)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A(*), B(*), C(*), D, E, F
  INTEGER, INTENT(IN) :: G, H, I
END SUBROUTINE CONTQ3

SUBROUTINE CONTQ3D1(A, B, C, D, E, F, G, H, I, J)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A(*), B(*), C(*), D, E, F, G
  INTEGER, INTENT(IN) :: H, I, J
END SUBROUTINE CONTQ3D1

SUBROUTINE CONTQ4(A, B, C, D, E, F, G, H, I, J)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A(*), B(*), C(*), D, E, F, G
  INTEGER, INTENT(IN) :: H, I, J
END SUBROUTINE CONTQ4

SUBROUTINE CPLOT3D1(A, B, C, D, E, F, G, H, I)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A(*), B(*), C(*), D, E, F
  INTEGER, INTENT(IN) :: G, H, I
END SUBROUTINE CPLOT3D1

SUBROUTINE GDATA3D1(A, B, C, D, E, F, G, H, I)
  IMPLICIT NONE
  REAL,    INTENT(IN) :: A(*), B(*), C(*), D, E, F
  INTEGER, INTENT(IN) :: G, H, I
END SUBROUTINE GDATA3D1

! ======================================================================
! Section 6: grd1d_mod (fp + ti)
! ======================================================================

MODULE grd1d_mod
CONTAINS
  SUBROUTINE GRD1D(NGP, FX, FY, NXM, NXMAX, NLMAX)
    IMPLICIT NONE
    INTEGER, INTENT(IN) :: NGP, NXM, NXMAX, NLMAX
    REAL,    INTENT(IN) :: FX(*), FY(*)
  END SUBROUTINE GRD1D
END MODULE grd1d_mod

! ======================================================================
! Section 7: grd2d_mod (eq + tr + fp + ti)
! ======================================================================

MODULE grd2d_mod
CONTAINS
  SUBROUTINE GRD2D(NGP, FX, FY, FF, NXM, NXMAX, NYMAX)
    IMPLICIT NONE
    INTEGER, INTENT(IN) :: NGP, NXM, NXMAX, NYMAX
    REAL,    INTENT(IN) :: FX(*), FY(*), FF(*)
  END SUBROUTINE GRD2D
END MODULE grd2d_mod
