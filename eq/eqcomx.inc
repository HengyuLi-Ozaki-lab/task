C     eqcomx (shim): transitional bundle header.
C     Kept for backwards-compatibility of INCLUDE '../eq/eqcomx.inc'.
C     Original composition: eqcom0 + eqcom1 + eqcom5.
C     eqcom5 (matrix solver) is NOT F90-modernized in Phase F-1,
C     so the original eqcom5.inc is still INCLUDEd here verbatim.
C     New core code should USE eqcom0_mod/eqcom1_mod directly;
C     eqcom5 will be modernized in a follow-up phase.
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INCLUDE '../eq/eqcom5.inc'
