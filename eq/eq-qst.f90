! Phase F-4 (HIGH tier): free-form F90 conversion of eq-qst.f.
! QST/JAEA equilibrium file reader (subroutines EQJAEAR, RBB) with
! axis / X-point detection and separatrix tracing. Preserves exact
! numerical semantics of the original fixed-form source.
!
! NOTE: IMPLICIT NONE is NOT added at file level because the INCLUDEd
!       shim '../eq/eqcomq.inc' already supplies an IMPLICIT statement
!       (IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)) and USEs the
!       F-1 MODULEs (eqcom0/1/3_mod) for the COMMON symbols.
!
!     ***** READ QST (A>K>A> JAREA) EQ FORMAT FILE *****
!
      SUBROUTINE EQJAEAR(IERR)

      USE, INTRINSIC :: IEEE_ARITHMETIC, ONLY: IEEE_IS_FINITE
      USE libfio
      USE libbrent
      USE libspl1d
      USE libgrf
      USE plcomm
      USE eqcom0_mod
      USE eqcom1_mod
      USE eqcom3_mod
      IMPLICIT COMPLEX*16(C),REAL*8(A,B,D-F,H,O-Z)
      INTEGER, INTENT(OUT) :: IERR

      integer:: ir,iz
      INTEGER:: IOS,NRGF,NZGF
      LOGICAL:: LEX2
      CHARACTER(LEN=16):: KPART,KR(4)
      REAL(rkind),DIMENSION(:,:),ALLOCATABLE:: psi_temp
      DIMENSION PSIRG(NRGM,NZGM),PSIZG(NRGM,NZGM),PSIRZG(NRGM,NZGM)
      DIMENSION PSIx1(NRGM,NZGM),psix2(NRGM,NZGM),PSIx3(NRGM,NZGM)
      REAL(rkind):: DERIV(NPSM)
      REAL(rkind),DIMENSION(1)::  THIN=(/0.035/)
      REAL(rkind),DIMENSION(:),ALLOCATABLE:: rc_xp,zc_xp,psic_xp
      REAL(rkind),DIMENSION(NSUM):: XA
      INTEGER:: icount,icountmax
      INTEGER,PARAMETER:: icountm=10
      INTEGER:: ic_min1,ic_min2,ic_min3
      REAL(rkind):: psic_max,psic_min
      EXTERNAL RBB,PSIGZ0

      neqdsk=21
      CALL FROPEN(neqdsk,KNAMEQ,0,MODEFR,'EQ',IERR)
      IF(IERR.NE.0) RETURN
!
!     Every READ of the two files has an IOSTAT, and a map without an
!     axis returns: a short or malformed file, or a map with no axis, is
!     an error return with its reason for the C API's eq_last_error,
!     where it ended the process (a Fortran runtime error, a STOP:
!     task-web-client #204).
      REWIND(neqdsk)
      READ (neqdsk,IOSTAT=IOS) NRGF,NZGF
      IF(IOS.NE.0) THEN
         CALL READ_FAILED('KNAMEQ',KNAMEQ,'grid counts')
         RETURN
      ENDIF
!     The grid's arrays hold NRGM x NZGM points and the spacing divides
!     by NRGMAX-1: counts outside 2..NRGM are no grid of this format.
      IF(NRGF.LT.2.OR.NRGF.GT.NRGM.OR.NZGF.LT.2.OR.NZGF.GT.NZGM) THEN
         CLOSE(neqdsk)
         WRITE(EQ_ERRMSG,'(3A,I0,A,I0,A,I0,A,I0)',IOSTAT=IOS) &
              'EQ_READ: MODELG=8 load failed: KNAMEQ=''',TRIM(KNAMEQ), &
              ''' gives a grid of ',NRGF,' x ',NZGF, &
              ' points, outside 2..',NRGM,' x 2..',NZGM
         IF(IOS.NE.0) EQ_ERRMSG='EQ_READ: MODELG=8 load failed:'// &
              ' KNAMEQ gives grid counts outside the arrays'
         WRITE(6,'(2A)') 'XX ',TRIM(EQ_ERRMSG)
         IERR=3
         RETURN
      ENDIF
      write(6,*) 'nrgmax,nzgmax=',NRGF,NZGF
      READ (neqdsk,IOSTAT=IOS) rmin,rmax,zmin,zmax
      IF(IOS.NE.0) THEN
         CALL READ_FAILED('KNAMEQ',KNAMEQ,'R and Z ranges')
         RETURN
      ENDIF
!     A range that is empty (its spacing 0) or not finite is no grid,
!     and a falling one loads but is no grid for the field lookups:
!     GETRZ (eq/eqintf.f90) takes every point with R <= RG(1) or
!     Z <= ZG(1) as outside, where it returns no poloidal field and no
!     error, and PL looks the field up through it for MODELG 3, 5, 8.
      IF(.NOT.(IEEE_IS_FINITE(rmin).AND.IEEE_IS_FINITE(rmax).AND. &
               IEEE_IS_FINITE(zmin).AND.IEEE_IS_FINITE(zmax).AND. &
               rmax.GT.rmin.AND.zmax.GT.zmin)) THEN
         CLOSE(neqdsk)
         WRITE(KR,'(ES11.4)',IOSTAT=IOS) rmin,rmax,zmin,zmax
         WRITE(EQ_ERRMSG,'(11A)',IOSTAT=IOS) &
              'EQ_READ: MODELG=8 load failed: KNAMEQ=''',TRIM(KNAMEQ), &
              ''' gives R and Z ranges that are no grid: R from ', &
              TRIM(ADJUSTL(KR(1))),' to ',TRIM(ADJUSTL(KR(2))), &
              ', Z from ',TRIM(ADJUSTL(KR(3))),' to ',TRIM(ADJUSTL(KR(4)))
         IF(IOS.NE.0) EQ_ERRMSG='EQ_READ: MODELG=8 load failed:'// &
              ' KNAMEQ gives R and Z ranges that are no grid'
         WRITE(6,'(2A)') 'XX ',TRIM(EQ_ERRMSG)
         IERR=3
         RETURN
      ENDIF
      NRGMAX=NRGF
      NZGMAX=NZGF
      write(6,*) 'rmin,rmax=',rmin,rmax
      write(6,*) 'zmin,zmax=',zmin,zmax
      DR=(rmax-rmin)/(NRGMAX-1)
      DZ=(zmax-zmin)/(NZGMAX-1)
      DO NRG=1,NRGMAX
         RG(NRG)=rmin+DR*(NRG-1)
      ENDDO
      DO NZG=1,NZGMAX
         ZG(NZG)=zmin+DZ*(NZG-1)
      ENDDO

      ALLOCATE(psi_temp(NRGMAX,NZGMAX))
      ! Defensive zero-init (see PR #123 pattern): libeqapi.so finalize+reinit
      ! cycle can reuse heap chunks with stale values.
      psi_temp = 0.D0
      READ(neqdsk,IOSTAT=IOS) psi_temp
      IF(IOS.NE.0) THEN
         DEALLOCATE(psi_temp)
         CALL READ_FAILED('KNAMEQ',KNAMEQ,'psi map')
         RETURN
      ENDIF
      psirz(1:nrgmax,1:nzgmax)=psi_temp(1:nrgmax,1:nzgmax)
      DEALLOCATE(psi_temp)

      read (neqdsk,IOSTAT=IOS) BtR
      IF(IOS.NE.0) THEN
         CALL READ_FAILED('KNAMEQ',KNAMEQ,'BtR record')
         RETURN
      ENDIF
      write(6,*) 'read BtR=',BtR
      CLOSE(neqdsk)

      neqdsk=22
      CALL FROPEN(neqdsk,KNAMEQ2,1,MODEFR,'EQ',IERR)
      IF(IERR.NE.0) THEN
!        Name the second file for eq_last_error: EQ_READ's fallback
!        names KNAMEQ, which was read (task-web-client #191).
         INQUIRE(FILE=KNAMEQ2,EXIST=LEX2,IOSTAT=IOS)
         IF(IOS.NE.0) LEX2=.FALSE.
         IF(LEN_TRIM(KNAMEQ2).EQ.0) THEN
            EQ_ERRMSG='EQ_READ: MODELG=8 load failed: its second file'// &
                 ' KNAMEQ2 is blank'
         ELSEIF(.NOT.LEX2) THEN
            WRITE(EQ_ERRMSG,'(3A)',IOSTAT=IOS) &
                 'EQ_READ: MODELG=8 load failed: its second file KNAMEQ2=''', &
                 TRIM(KNAMEQ2),''' not found'
         ELSE
            WRITE(EQ_ERRMSG,'(3A,I0,A)',IOSTAT=IOS) &
                 'EQ_READ: MODELG=8 load failed: its second file KNAMEQ2=''', &
                 TRIM(KNAMEQ2),''' could not be opened (IERR=',IERR,')'
         ENDIF
         RETURN
      ENDIF
      write(6,*) 'open 2'
      npsmax=41
      REWIND(neqdsk)
      READ(neqdsk,*,IOSTAT=IOS)
      IF(IOS.NE.0) THEN
         CALL READ_FAILED('KNAMEQ2',KNAMEQ2,'header line')
         RETURN
      ENDIF
      DO nps=1,npsmax
         READ(neqdsk,*,IOSTAT=IOS) i,ttps(nps),ppps(nps)
         IF(IOS.NE.0) THEN
            WRITE(KPART,'(A,I0,A)') 'row ',nps,' of 41'
            CALL READ_FAILED('KNAMEQ2',KNAMEQ2,TRIM(KPART))
            RETURN
         ENDIF
      ENDDO
      CLOSE(neqdsk)


! ----- calculate dpsirz/dr)**2+(dpsirz/dz)**2 -----

      psix1(1:nrgmax,1:nzgmax)=0.0
      DO nz=2,nzgmax-1
         DO nr=2,nrgmax-1
            psix1(nr,nz)=(psirz(nr+1,nz)-psirz(nr-1,nz))**2 &
                        /(rg(nr+1)-rg(nr-1))**2 &
                        +(psirz(nr,nz+1)-psirz(nr,nz-1))**2 &
                        /(zg(nz+1)-zg(nz-1))**2
         END DO
      END DO

! ----- find local minimum -----
      ALLOCATE(rc_xp(icountm),zc_xp(icountm),psic_xp(icountm))
      ! Defensive zero-init (see PR #123 pattern): libeqapi.so finalize+reinit
      ! cycle can reuse heap chunks with stale values.
      rc_xp   = 0.D0
      zc_xp   = 0.D0
      psic_xp = 0.D0
      icount=0
      DO nz=3,nzgmax-2
         DO nr=3,nrgmax-2
            IF((psix1(nr,nz) < psix1(nr-1,nz)) .AND. &
               (psix1(nr,nz) < psix1(nr+1,nz)) .AND. &
               (psix1(nr,nz) < psix1(nr,nz-1)) .AND. &
               (psix1(nr,nz) < psix1(nr,nz+1))) THEN
               icount=icount+1
               rc_xp(icount)=rg(nr)
               zc_xp(icount)=zg(nz)
               psic_xp(icount)=psirz(nr,nz)
               IF(icount == icountm) GOTO 1000
            END IF
         END DO
      END DO
 1000 CONTINUE
      icountmax=icount

      SELECT CASE(icountmax)
      CASE(0)
         WRITE(6,*) 'XX NO MAG AXIS FOUND'
         WRITE(EQ_ERRMSG,'(3A)',IOSTAT=IOS) &
              'EQ_READ: MODELG=8 load failed: the psi map in KNAMEQ=''', &
              TRIM(KNAMEQ),''' has no magnetic axis: no interior point'// &
              ' where |grad psi| is below its four neighbours (ierr=102)'
         IF(IOS.NE.0) EQ_ERRMSG='EQ_READ: MODELG=8 load failed:'// &
              ' the psi map in KNAMEQ has no magnetic axis (ierr=102)'
         IERR=102
         RETURN
      CASE(1)
         RAXIS=rc_xp(1)
         ZAXIS=zc_xp(1)
         PSIAXIS=psic_xp(1)
         NXPOINT=0
         WRITE(6,'(A,1P3E12.4)') 'Axis:',RAXIS,ZAXIS,PSIAXIS
      CASE(2:icountm)
         ic_min1=0
         ic_min2=0
         ic_min3=0
         psic_max=psic_xp(1)
         DO icount=2,icountmax
            psic_max=MAX(psic_xp(icount),psic_max)
         END DO
         psic_min=psic_max
         ic_min1=0
         DO icount=1,icountmax
            IF(psic_xp(icount) < psic_min) THEN
               ic_min1=icount
               psic_min=psic_xp(icount)
            END IF
         END DO
         psic_min=psic_max
         ic_min2=0
         DO icount=1,icountmax
            IF((icount /= ic_min1).AND. &
               (psic_xp(icount) < psic_min)) THEN
               ic_min2=icount
               psic_min=psic_xp(icount)
            END IF
         END DO
         psic_min=psic_max
         ic_min3=0
         DO icount=1,icountmax
            IF((icount /= ic_min1).AND. &
               (icount /= ic_min2).AND. &
               (psic_xp(icount) < psic_min)) THEN
               ic_min3=icount
               psic_min=psic_xp(icount)
            END IF
         END DO

         IF(ic_min1 /= 0) THEN
            RAXIS=rc_xp(ic_min1)
            ZAXIS=zc_xp(ic_min1)
            PSIAXIS=psic_xp(ic_min1)
            NXPOINT=0
            WRITE(6,'(A,1P3E12.4)') 'Axis:',RAXIS,ZAXIS,PSIAXIS
         ENDIF
         IF(ic_min2 /= 0) THEN
            RXPNT1=rc_xp(ic_min2)
            ZXPNT1=zc_xp(ic_min2)
            PSIXPNT1=psic_xp(ic_min2)
            NXPOINT=1
            WRITE(6,'(A,1P3E12.4)') 'Xp1: ',RXPNT1,ZXPNT1,PSIXPNT1
         ENDIF
         IF(ic_min3 /= 0) THEN
            RXPNT2=rc_xp(ic_min3)
            ZXPNT2=zc_xp(ic_min3)
            PSIXPNT2=psic_xp(ic_min3)
            NXPOINT=2
            WRITE(6,'(A,1P3E12.4)') 'Xp2: ',RXPNT2,ZXPNT2,PSIXPNT2
         ENDIF
      END SELECT

! -----
      CALL setup_psig
      CALL find_axis(IERR)
      IF(IERR.NE.0) THEN
!        find_axis's reason starts "EQAXIS: "; name the load instead, as
!        this reader's other reasons do.
         IF(EQ_ERRMSG(1:8).EQ.'EQAXIS: ') EQ_ERRMSG= &
              'EQ_READ: MODELG=8 load failed: '//EQ_ERRMSG(9:)
         RETURN
      ENDIF
      WRITE(6,'(A,1P3E12.4)') 'RAXIS,ZAXIS,PSI_AXIS=', &
                               RAXIS,ZAXIS,PSIG(RAXIS,ZAXIS)
      IF(NXPOINT >= 1) THEN
         CALL find_xpoint1
         WRITE(6,'(A,1P3E12.4)') 'RXPNT1,ZXPNT1,PSI_XPNT1=', &
                                  RXPNT1,ZXPNT1,PSIG(RXPNT1,ZXPNT1)
      END IF
      IF(NXPOINT >= 2) THEN
         CALL find_xpoint2
         WRITE(6,'(A,1P3E12.4)') 'RXPNT2,ZXPNT2,PSI_XPNT2=', &
                                  RXPNT2,ZXPNT2,PSIG(RXPNT2,ZXPNT2)
      END IF

      REDGE=FBRENT(PSIGZ0,RAXIS+0.1D0,2*RAXIS,1.D-8)
      WRITE(6,'(A,1P3E12.4)') 'REDGE,ZAXIS,PSI_EDGE=', &
                               REDGE,ZAXIS,PSIG(REDGE,ZAXIS)

      NMAX=NTVM
      H=16.D0*(REDGE-RAXIS)/NMAX
      CALL calc_separtrix(REDGE,ZAXIS,RXPNT1,ZXPNT1,H,NMAX, &
                          XA,RSU,ZSU,NSUMAX,IERR)

!      CALL PAGES
!      CALL GRD2D(0,rg,zg,psirz,nrgm,nrgmax,nzgmax,'@psirz@',0,0,1,
!     &           NLMAX=31,ASPECT=0.D0,
!     &           LINE_thickness=THIN)
!      CALL SETRGB(1.0,0.0,0.0)
!      CALL SETLNW(0.035)
!      CALL draw_cross(RAXIS,ZAXIS,0.2D0)
!      IF(nxpoint >= 1) CALL draw_cross(RXPNT1,ZXPNT1,0.2D0)
!      IF(nxpoint >= 2) CALL draw_cross(RXPNT2,ZXPNT2,0.2D0)
!      IF(nxpoint >= 1) THEN
!         CALL SETRGB(0.0,0.0,0.0)
!         DO NSU=1,NSUMAX
!            CALL draw_cross(RSU(NSU),ZSU(NSU),0.1D0)
!C            WRITE(6,'(A,I5,1P3E12.4)') 'SU:',NSU,RSU(NSU),ZSU(NSU),
!C     &                                 PSIG(RSU(NSU),ZSU(NSU))
!         END DO
!      END IF
!      CALL PAGEE

      RSUMAX = RAXIS
      RSUMIN = RAXIS
      ZSUMAX = ZAXIS
      ZSUMIN = ZAXIS
      R_ZSUMAX = 0.d0
      R_ZSUMIN = 0.d0
      DO i = 1, nsumax
         IF(RSU(i) > RSUMAX) RSUMAX = RSU(i)
         IF(RSU(i) < RSUMIN) RSUMIN = RSU(i)
         IF(ZSU(i) > ZSUMAX) THEN
            ZSUMAX   = ZSU(i)
            R_ZSUMAX = RSU(i)
         END IF
         IF(ZSU(i) < ZSUMIN) THEN
            ZSUMIN   = ZSU(i)
            R_ZSUMIN = RSU(i)
         END IF
      END DO

! *** The following variable defined in Tokamaks 3rd, Sec. 14.14 ***
      RR = RAXIS
      RA = REDGE - RAXIS
      !==  RB: wall minor radius  ======================
      !    Multiplication factor 1.1 is tentatively set.
      RB   = 1.1d0 * RA
!      RB   = 1.2d0 * RA
      !=================================================
      RKAP = (ZSUMAX - ZSUMIN) / (RSUMAX - RSUMIN)

!  ---- corrected on 2010/01/18 for negative triangularity ----
!      RDLT = 0.5d0 * (ABS(RR-R_ZSUMIN) + ABS(RR-R_ZSUMAX)) / RA

      RDLT = 0.5d0 * ((RR-R_ZSUMIN) + (RR-R_ZSUMAX)) / RA
      BB   = BtR / RR

      write(6,'(A,1PE12.4)') 'RR    =',RR
      write(6,'(A,1PE12.4)') 'RA    =',RA
      write(6,'(A,1PE12.4)') 'RB    =',RB
      write(6,'(A,1PE12.4)') 'RKAP  =',RKAP
      write(6,'(A,1PE12.4)') 'RDLT  =',RDLT
      write(6,'(A,1PE12.4)') 'BB    =',BB

      PSI0 = 2.D0*PI*PSIG(RAXIS,ZAXIS)
      PSIA = 0.D0
      PSIPA=-PSI0
      DO NZG=1,NZGMAX
         DO NRG=1,NRGMAX
            PSIRZ(NRG,NZG)=2.D0*PI*PSIRZ(NRG,NZG)
         ENDDO
      ENDDO
      call setup_psig

      DPS=PSIPA/(NPSMAX-1)
      DO NPS=1,NPSMAX
         PSIPS(NPS)=DPS*(NPS-1)
         TTPS(NPS)=2.D0*PI*TTPS(NPS)
      ENDDO

      TTDTTPS(1:npsmax)=0.D0
      DPPPS(1:npsmax)=0.D0

      CALL SPL1D(PSIPS,PPPS,  DERIV,UPPPS, NPSMAX,0,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX SPL1D for PPPS: IERR=',IERR
      CALL SPL1D(PSIPS,TTPS,  DERIV,UTTPS, NPSMAX,0,IERR)
      IF(IERR.NE.0) WRITE(6,*) 'XX SPL1D for TTPS: IERR=',IERR
!
!      DO NPS=1,NPSMAX
!         X=PPFUNC(PSIPS(NPS))
!         WRITE(6,'(A,I5,1P5E12.4)')
!     &        'NPS:',NPS,PSIPS(NPS),PPPS(NPS),TTPS(NPS),
!     &        PPFUNC(PSIPS(NPS)),TTFUNC(PSIPS(NPS))
!      END DO
!
      CALL EQCALQP(IERR)
      IF(IERR.NE.0) RETURN
!
      IF(NSUMAX.GT.0) THEN
         CALL EQCALQV(IERR)
         IF(IERR.NE.0) RETURN
      ENDIF
!
      CALL EQSETS_RHO(IERR)
      CALL EQSETS(IERR)

      DO NZG=1,NZGMAX
      DO NRG=1,NRGMAX
         HJTRZ(NRG,NZG)=0.D0
      ENDDO
      ENDDO
      RETURN

      CONTAINS

!     A READ of KNAMEQ or KNAMEQ2 failed (IOS): close the file and give
!     IERR 4 when it ends early, 3 when it cannot be read, and a reason
!     naming the file and the part, for eq_last_error.
      SUBROUTINE READ_FAILED(KVAR,KFILE,KWHAT)
        CHARACTER(LEN=*),INTENT(IN):: KVAR,KFILE,KWHAT
        INTEGER:: IOS_W
        CLOSE(neqdsk)
        IF(IOS.LT.0) THEN
           IERR=4
           WRITE(EQ_ERRMSG,'(7A)',IOSTAT=IOS_W) &
                'EQ_READ: MODELG=8 load failed: ',KVAR,'=''', &
                TRIM(KFILE),''' ends before its ',KWHAT
        ELSE
           IERR=3
           WRITE(EQ_ERRMSG,'(7A)',IOSTAT=IOS_W) &
                'EQ_READ: MODELG=8 load failed: ',KVAR,'=''', &
                TRIM(KFILE),''' could not be read: its ',KWHAT
        ENDIF
        IF(IOS_W.NE.0) EQ_ERRMSG= &
             'EQ_READ: MODELG=8 load failed: a file could not be read'
        WRITE(6,'(2A)') 'XX ',TRIM(EQ_ERRMSG)
      END SUBROUTINE READ_FAILED

      END

      SUBROUTINE RBB(X,RGB)
      REAL,INTENT(IN):: X
      REAL,INTENT(OUT):: RGB(3)

      RGB(1)=0.0
      RGB(2)=0.0
      RGB(3)=0.0

      IF(X > 0.5) THEN
         RGB(1)=SQRT(2*(X-0.5))
      ELSE IF(X < 0.5) THEN
         RGB(3)=SQRT(2*(0.5-X))
      ENDIF
      RETURN
      END
