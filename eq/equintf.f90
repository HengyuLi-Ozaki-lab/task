! equintf.f90
!
! Phase F-3 (MED tier): free-form F90 conversion of equintf.f.
! equread interface: setter routines that populate eqcom1/eqcom3 state
! (grid dimensions, PSI(R,Z), flux-function tables). Preserves exact
! numerical semantics of the original fixed-form source.
!
! NOTE: IMPLICIT NONE is NOT added here because the INCLUDEd shim
!       '../eq/eqcomq.inc' already supplies an IMPLICIT statement
!       (IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)) and USEs the
!       F-1 MODULEs (eqcom0/1/3_mod) for the COMMON symbols.
!
      SUBROUTINE equ_set_var1(nsr,nsz,nv,nsu,ilimt,btv,saxis,ell,trg)
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INTEGER, INTENT(IN) :: nsr,nsz,nv,nsu,ilimt
      REAL*8,  INTENT(IN) :: btv,saxis,ell,trg

      NRGMAX=nsr
      NZGMAX=nsz
      NPSMAX=nv
      Bctr=btv
      PSI0=saxis
      PSIA=0.D0
      RKAP=ell
      RDLT=trg
      NSUMAX=nsu
      limitr=ilimt
      RETURN
      END SUBROUTINE equ_set_var1

      SUBROUTINE equ_set_psi(rg_,zg_,psi_)

      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: rg_(NRGMAX),zg_(NZGMAX),psi_(NRGMAX*NZGMAX)
      INTEGER NZG,NRG

      DO NRG=1,NRGMAX
         RG(NRG)=rg_(NRG)
      END DO

      DO NZG=1,NZGMAX
         ZG(NZG)=zg_(NZG)
      END DO

      DO NZG=1,NZGMAX
         DO NRG=1,NRGMAX
            PSIRZ(NRG,NZG)=psi_((NZG-1)*NRGMAX+NRG)
         END DO
      END DO
      RETURN
      END SUBROUTINE equ_set_psi

      SUBROUTINE equ_set_fluxfn(pds,fds,vlv,qqv,prv,xxx)

      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      REAL*8, INTENT(IN) :: pds(NPSMAX),fds(NPSMAX),vlv(NPSMAX)
      REAL*8, INTENT(IN) :: qqv(NPSMAX),prv(NPSMAX),xxx(NPSMAX)
      INTEGER NPS

      DO NPS=1,NPSMAX
         PSIPS(NPS)=xxx(NPS)
         PPPS(NPS)=prv(NPS)
      END DO
      RETURN
      END SUBROUTINE equ_set_fluxfn
