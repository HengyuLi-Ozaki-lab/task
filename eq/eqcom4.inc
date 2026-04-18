!     $Id$
!
!     Phase F-3: comment syntax switched from "C" to "!" so this raw
!     COMMON bundle (not yet modernized to a MODULE) can be INCLUDEd
!     from both fixed-form (.f) and free-form (.f90) sources. The
!     COMMON and PARAMETER declarations are unchanged.
!
      PARAMETER (NTRM=200)
!
      COMMON /TREQL1/ PSIRHO(NTRM+2),UPSIRHO(4,NTRM+2)
      COMMON /TREQL2/ PSITR(NTRM),PSITRG(NTRM+1),PSITRX(NTRM+2)
      COMMON /TREQL3/ RHOTR(NTRM),RHOTRG(NTRM+1),RHOTRX(NTRM+2)
!
      COMMON /TREQG1/ UPPSI(4,NTRM+2),UQPSI(4,NTRM+2),UFPSI(4,NTRM+2)
      COMMON /TREQG2/ UJPSI(4,NTRM+2),UJPSI0(NTRM+2)
      COMMON /TREQG3/ UVTPSI(4,NTRM+2),UTPSI(4,NTRM+2)
      COMMON /TREQG4/ UQRHOEQ(4,NTRM+2)
!
      COMMON /TREQP1/ NTRMAX
