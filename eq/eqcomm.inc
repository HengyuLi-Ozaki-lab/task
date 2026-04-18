!     eqcomm (shim): transitional bundle header.
!     Kept for backwards-compatibility of INCLUDE '../eq/eqcomm.inc'.
!     Original composition: eqcom0 + eqcom1.
!     New code should USE eqcom0_mod/eqcom1_mod directly.
!     Phase F-5 will remove this shim.
!
!     Phase F-3: comment syntax switched from "C" to "!" so this shim
!     can be INCLUDEd from both fixed-form (.f) and free-form (.f90)
!     sources. No change to USE graph or IMPLICIT rule.
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
