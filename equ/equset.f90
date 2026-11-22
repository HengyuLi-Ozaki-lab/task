! equset.f90

      module eqset_mod
      use tpxssl_mod
      use eqsub_mod
      use eqfct_mod
      public
      contains
!=======================================================================
      subroutine eqset
      use equ_status_mod, only: equ_fail, equ_failed
!=======================================================================
!     set up free bondary equilibriium
!             for fiven functional forms of dp/ds and TdT/ds
!=======================================================================
      use aaa_mod
      use geo_mod
      use par_mod
      use equ_mod
      use eqv_mod
      use cnt_mod
      use com_mod
      implicit none
! local variables
      real*8   bav0
      integer keqmax,i
!=======================================================================
!<<restart>>
      if(iread.gt.0)then
      do i=1,nsr*nsz
      rbp(i)=psi(i)
      enddo
      bav0=bav
      bav=1.
      call eqvac
      do i=1,nsr*nsz
      psi(i)=rbp(i)
      enddo
      call eqrcu
      if(equ_failed()) return
      bav=bav0
!--confirm equilibrium accuracy for metrics
      write(6,*)
      write(6,*)'== check of equilibrium accuracy through ode =='
      call eqeqv
      if(equ_failed()) return
      keqmax=ieqmax
      ieqmax=10
      call eqfct
      ieqmax=keqmax
      if(equ_failed()) return
      return
      endif
!=======================================================================
      call cpusec(cputim)
!-----------------------------------------------------------------------
!     load Solovev equilibrium as initial guess
!-----------------------------------------------------------------------
      call eqvac
      call eqsol
      call eqrbp
      call eqlin
      if(equ_failed()) return
      call eqequ
      if(equ_failed()) return
      call eqeqv
      if(equ_failed()) return
      call eqout
      if(equ_failed()) return
!--confirm equilibrium accuracy for metrics
      write(6,*)
      write(6,*)'== check of equilibrium accuracy through ode =='
      keqmax=ieqmax
      ieqmax=10
      call eqfct
      ieqmax=keqmax
      if(equ_failed()) return
      call cpusec(cpuequ)
!=======================================================================
      return
      end subroutine eqset
!
      end module eqset_mod
