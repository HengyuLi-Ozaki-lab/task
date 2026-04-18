!     ***********************************************************
!
!       Phase 3 split of trrslt.f90 --- time-series / file output
!
!       Contains:
!         TRDATA              (interactive GVT/GVR browsing)
!         TRMXMN              (min/max of GVT(:,N))
!         TRSNAP              (status report)
!         TRXOUT              (save UFILE 1D/2D profiles)
!         TR_UFILE1D_CREATE   (1D UFILE writer helper)
!         TR_UFILE2D_CREATE   (2D UFILE writer helper)
!         TRXW1D              (raw 1D UFILE write)
!         TRXW2D              (raw 2D UFILE write)
!         GET_DATE            (UFILE date string)
!
!     ***********************************************************

MODULE trrslt_files
  IMPLICIT NONE
  PUBLIC

CONTAINS

!     ***********************************************************

!           PRINT LOCAL DATA

!     ***********************************************************

      SUBROUTINE TRDATA

      USE TRCOMM, ONLY : GRG, GRM, GT, GVR, GVT, NGR, NT
      IMPLICIT NONE
      INTEGER:: MGH, MGMAX, MGMIN, MGSTEP, MID, MRMAX, MRMIN, MRSTEP, MTMAX, MTMIN, MTSTEP, NG, NID, NR


    1 WRITE(6,*) '## INPUT MODE : 1:GVT(NT)  2:GVR(NR)  3:GVR(NG)'
      WRITE(6,*) '                NOW NGR=',NGR
      READ(5,*,END=9000,ERR=1) NID
      IF(NID.EQ.0) GOTO 9000

      IF(NID.EQ.1) THEN
   10    WRITE(6,*) '## INPUT NID,NTMIN,NTMAX,NTSTEP'
         READ(5,*,END=1,ERR=10) MID,MTMIN,MTMAX,MTSTEP
         IF(MID.EQ.0) GOTO 1
         DO NT=MTMIN,MTMAX,MTSTEP
            WRITE(6,601) NT,GT(NT),GVT(NT,MID)
         ENDDO
         GOTO 10
      ELSEIF(NID.EQ.2) THEN
   20    WRITE(6,*) '## INPUT NID,NG,NRMIN,NRMAX,NRSTEP,G or H(1 or 2)'
         READ(5,*,END=1,ERR=20) MID,NG,MRMIN,MRMAX,MRSTEP,MGH
         IF(MID.EQ.0) GOTO 1
         DO NR=MRMIN,MRMAX,MRSTEP
            IF(MGH.EQ.1) THEN
               WRITE(6,602) NG,NR,GRG(NR+1),GVR(NR,NG,MID)
            ELSEIF(MGH.EQ.2) THEN
               WRITE(6,602) NG,NR,GRM(NR),GVR(NR,NG,MID)
            ELSE
               GOTO 1
            ENDIF
         ENDDO
         GOTO 20
      ELSEIF(NID.EQ.3) THEN
   30    WRITE(6,*) '## INPUT NID,NR,NGMIN,NGMAX,NGSTEP,G or H(1 or 2)'
         READ(5,*,END=1,ERR=30) MID,NR,MGMIN,MGMAX,MGSTEP,MGH
         IF(MID.EQ.0) GOTO 1
         DO NG=MGMIN,MGMAX,MGSTEP
            IF(MGH.EQ.1) THEN
               WRITE(6,602) NG,NR,GRG(NR+1),GVR(NR,NG,MID)
            ELSEIF(MGH.EQ.2) THEN
               WRITE(6,602) NG,NR,GRM(NR),GVR(NR,NG,MID)
            ELSE
               GOTO 1
            ENDIF
         ENDDO
         GOTO 30
      ENDIF
      GOTO 1

 9000 RETURN
  601 FORMAT(' ','  NT=',I3,'  T=',1PE12.4,'  DATA=',1PE12.4)
  602 FORMAT(' ','  NG=',I3,'  NR=',I3,'  R=',1PE12.4,    '  DATA=',1PE12.4)
      END SUBROUTINE TRDATA

!     ***********************************************************

!          PEAK-VALUE WO SAGASE

!     ***********************************************************

      SUBROUTINE TRMXMN(N,STR)

      USE TRCOMM, ONLY : GVT, NGT, NT
      IMPLICIT NONE
      INTEGER:: N
      REAL   :: GVMAX, GVMIN

      CHARACTER STR*7

      GVMAX=GVT(1,N)
      GVMIN=GVT(1,N)

      DO NT=2,NGT
         GVMAX=MAX(GVMAX,GVT(NT,N))
         GVMIN=MIN(GVMIN,GVT(NT,N))
      ENDDO

      WRITE(6,600) STR,GVT(1,N),GVMAX,GVMIN,GVT(NGT,N)
  600 FORMAT(' ',A8,5X,1PD10.3,2X,1PD10.3,2X,1PD10.3,2X,1PD10.3)

      RETURN
      END SUBROUTINE TRMXMN

!     ***********************************************************

!           SIMPLE STATUS REPORT

!     ***********************************************************

      SUBROUTINE TRSNAP

      USE TRCOMM, ONLY : Q0, RT, T, TAUE1, WPT
      IMPLICIT NONE


      WRITE(6,601) T,WPT,TAUE1,Q0,RT(1,1),RT(1,2),RT(1,3),RT(1,4)
  601 FORMAT(' ','# T: ',F8.3,'(S)    WP:',F7.2,'(MJ)  ', &
     &           '  TAUE:',F7.3,'(S)   Q0:',F7.3,/ &
     &       ' ','  TE:',F7.3,'(KEV)   TD:',F7.3,'(KEV) ', &
     &           '  TT:',F7.3,'(KEV)   TA:',F7.3,'(KEV)')
      RETURN
      END SUBROUTINE TRSNAP


!     ***********************************************************

!           SAVE PROFILE DATA

!     ***********************************************************

      SUBROUTINE TRXOUT

        USE TRCOMM, ONLY : MDLUF,KXNDEV,KXNDCG,KXNID,KDIRW1,KDIRW2
        IMPLICIT NONE
        INTEGER:: IERR, IKDIRW, IKNDCG, IKNDEV, IKNID
        CHARACTER(LEN=80):: KDIRW, KFID


      KXNDEV='X'
      KXNDCG='test'
      KXNID ='in'

      IKNDEV=len_trim(KXNDEV)
      IKNDCG=len_trim(KXNDCG)
      IKNID =len_trim(KXNID )
      KDIRW='./profile_data/'//KXNDEV(1:IKNDEV)//'/' &
     &                          //KXNDCG(1:IKNDCG)//'/' &
     &                          //KXNID (1:IKNID )//'/'
!      KDIRW='../../tr.new/data/'//KXNDEV(1:IKNDEV)//'/' &
!     &                          //KXNDCG(1:IKNDCG)//'/' &
!     &                          //KXNID (1:IKNID )//'/'
!!      KDIRW='../../../profile/profile_data/'//KXNDEV(1:IKNDEV)//'/'
!!     &                          //KXNDCG(1:IKNDCG)//'/'
!!     &                          //KXNID (1:IKNID )//'/'
      IKDIRW=len_trim(KDIRW)
      KDIRW1=KDIRW(1:IKDIRW)//KXNDEV(1:IKNDEV) &
     &       //'1d'//KXNDCG(1:IKNDCG)//'.'
      KDIRW2=KDIRW(1:IKDIRW)//KXNDEV(1:IKNDEV) &
     &       //'2d'//KXNDCG(1:IKNDCG)//'.'

!     *** 1D DATA ***

      KFID='IP'
      CALL TR_UFILE1D_CREATE(KFID,34,1.D6 ,IERR)

      KFID='DIRECT'
      CALL TR_UFILE1D_CREATE(KFID, 2,1.D0 ,IERR)

      KFID='DIRECT'
      CALL TR_UFILE1D_CREATE(KFID, 3,1.D0 ,IERR)

      KFID='DIRECT'
      CALL TR_UFILE1D_CREATE(KFID, 4,1.D0 ,IERR)

      KFID='DIRECT'
      CALL TR_UFILE1D_CREATE(KFID, 5,1.D0 ,IERR)

      KFID='DIRECT'
      CALL TR_UFILE1D_CREATE(KFID, 6,1.D0 ,IERR)

      IF(MDLUF.NE.0) THEN
      KFID='DIRECT'
      CALL TR_UFILE1D_CREATE(KFID, 8,1.D0 ,IERR)
      ELSE
      KFID='PNBI'
      CALL TR_UFILE1D_CREATE(KFID,41,1.D0 ,IERR)
      ENDIF

      KFID='DIRECT'
      CALL TR_UFILE1D_CREATE(KFID, 9,1.D0 ,IERR)

      KFID='DIRECT'
      CALL TR_UFILE1D_CREATE(KFID,10,1.D0 ,IERR)

      KFID='DIRECT'
      CALL TR_UFILE1D_CREATE(KFID,11,1.D0 ,IERR)

      KFID='PRAD'
      CALL TR_UFILE1D_CREATE(KFID,60,1.D0 ,IERR)

      KFID='ZEFF'
      CALL TR_UFILE1D_CREATE(KFID,86,1.D0 ,IERR)

      KFID='VSURF'
      CALL TR_UFILE1D_CREATE(KFID,74,1.D0 ,IERR)

      KFID='LI'
      CALL TR_UFILE1D_CREATE(KFID,75,1.D0 ,IERR)

      KFID='WTH'
      CALL TR_UFILE1D_CREATE(KFID,31,1.D6 ,IERR)

      KFID='WTOT'
      CALL TR_UFILE1D_CREATE(KFID,33,1.D6 ,IERR)

      KFID='TE0'
      CALL TR_UFILE1D_CREATE(KFID, 9,1.D3 ,IERR)

      KFID='TI0'
      CALL TR_UFILE1D_CREATE(KFID,10,1.D3 ,IERR)

      KFID='DIRECT'
      CALL TR_UFILE1D_CREATE(KFID,26,1.D0 ,IERR)

      KFID='POHM'
      CALL TR_UFILE1D_CREATE(KFID,40,1.D0 ,IERR)

      KFID='IBOOT'
      CALL TR_UFILE1D_CREATE(KFID,38,1.D6 ,IERR)

      KFID='DIRECT'
      CALL TR_UFILE1D_CREATE(KFID,29,1.D0 ,IERR)

      KFID='PFUSION'
      CALL TR_UFILE1D_CREATE(KFID,46,1.D0 ,IERR)

!     *** 2D DATA ***

      KFID='TE'
      CALL TR_UFILE2D_CREATE(KFID, 1,1.D3 ,0,IERR)

      KFID='TI'
      CALL TR_UFILE2D_CREATE(KFID, 2,1.D3 ,0,IERR)

      KFID='NE'
      CALL TR_UFILE2D_CREATE(KFID, 5,1.D20,0,IERR)

      IF(MDLUF.NE.0) THEN
      KFID='QNBIE'
      CALL TR_UFILE2D_CREATE(KFID,89,1.D0 ,0,IERR)
      ENDIF

      KFID='QICRHE'
      CALL TR_UFILE2D_CREATE(KFID,38,1.D0 ,0,IERR)

      KFID='QECHE'
      CALL TR_UFILE2D_CREATE(KFID,36,1.D0 ,0,IERR)

      KFID='QLHE'
      CALL TR_UFILE2D_CREATE(KFID,37,1.D0 ,0,IERR)

      IF(MDLUF.NE.0) THEN
      KFID='QNBII'
      CALL TR_UFILE2D_CREATE(KFID,90,1.D0 ,0,IERR)
      ENDIF

      KFID='QICRHI'
      CALL TR_UFILE2D_CREATE(KFID,41,1.D0 ,0,IERR)

      KFID='QECHI'
      CALL TR_UFILE2D_CREATE(KFID,39,1.D0 ,0,IERR)

      KFID='QLHI'
      CALL TR_UFILE2D_CREATE(KFID,40,1.D0 ,0,IERR)

      KFID='CURNBI'
      CALL TR_UFILE2D_CREATE(KFID,11,1.D0 ,0,IERR)

      KFID='CURICRH'
      CALL TR_UFILE2D_CREATE(KFID,44,1.D0 ,0,IERR)

      KFID='CURECH'
      CALL TR_UFILE2D_CREATE(KFID,42,1.D0 ,0,IERR)

      KFID='CURLH'
      CALL TR_UFILE2D_CREATE(KFID,43,1.D0 ,0,IERR)

      KFID='NFAST'
      CALL TR_UFILE2D_CREATE(KFID,45,1.D20,0,IERR)

      KFID='QRAD'
      CALL TR_UFILE2D_CREATE(KFID,22,1.D0 ,0,IERR)

      KFID='ZEFFR'
      CALL TR_UFILE2D_CREATE(KFID,33,1.D0 ,0,IERR)

      KFID='Q'
      CALL TR_UFILE2D_CREATE(KFID,27,1.D0 ,1,IERR)

      KFID='CHIE'
      CALL TR_UFILE2D_CREATE(KFID,34,1.D0 ,1,IERR)

      KFID='CHII'
      CALL TR_UFILE2D_CREATE(KFID,35,1.D0 ,1,IERR)

      KFID='NM1'
      CALL TR_UFILE2D_CREATE(KFID, 6,1.D20,0,IERR)

      KFID='CURTOT'
      CALL TR_UFILE2D_CREATE(KFID, 9,1.D0 ,0,IERR)

      KFID='NIMP'
      CALL TR_UFILE2D_CREATE(KFID,46,1.D20,0,IERR)

      KFID='QOHM'
      CALL TR_UFILE2D_CREATE(KFID,15,1.D0 ,0,IERR)

      KFID='BPOL'
      CALL TR_UFILE2D_CREATE(KFID,47,1.D0 ,1,IERR)

      KFID='RMAJOR'
      CALL TR_UFILE2D_CREATE(KFID,49,1.D0 ,0,IERR)

      KFID='RMINOR'
      CALL TR_UFILE2D_CREATE(KFID,50,1.D0 ,0,IERR)

      KFID='VOLUME'
      CALL TR_UFILE2D_CREATE(KFID,51,1.D0 ,0,IERR)

      KFID='KAPPAR'
      CALL TR_UFILE2D_CREATE(KFID,52,1.D0 ,0,IERR)

      KFID='DELTAR'
      CALL TR_UFILE2D_CREATE(KFID,53,1.D0 ,0,IERR)

      KFID='GRHO1'
      CALL TR_UFILE2D_CREATE(KFID,54,1.D0 ,0,IERR)

      KFID='GRHO2'
      CALL TR_UFILE2D_CREATE(KFID,55,1.D0 ,0,IERR)

      KFID='CURBS'
      CALL TR_UFILE2D_CREATE(KFID,13,1.D0 ,0,IERR)

      KFID='CHITBE'
      CALL TR_UFILE2D_CREATE(KFID,56,1.D0 ,1,IERR)

      KFID='CHITBI'
      CALL TR_UFILE2D_CREATE(KFID,57,1.D0 ,1,IERR)

      KFID='ETAR'
      CALL TR_UFILE2D_CREATE(KFID,32,1.D0 ,0,IERR)

      RETURN
      END SUBROUTINE TRXOUT

!     *****

      SUBROUTINE TR_UFILE1D_CREATE(KFID,NUM,AMP,IERR)

      USE TRCOMM, ONLY : BB, GVRT, GT, GVT, MDLUF, NGT, NRAMAX, NRMAX, NROMAX, NTM, RA, RG, RHOA, RKAP, RR, rkind
      USE libspl1d
      IMPLICIT NONE
      CHARACTER(LEN=80),INTENT(INOUT):: KFID
      INTEGER,INTENT(IN) :: NUM
      REAL(rkind),   INTENT(IN) :: AMP
      INTEGER,INTENT(OUT):: IERR
      INTEGER:: ID, NTL, NTLMAX
      REAL(rkind)   :: DATOUT, DTL, FQ95, TIN
      REAL,DIMENSION(NTM)  :: GTL, GF1
      REAL(rkind),DIMENSION(NTM)  :: TF, DGT, DIN, DERIV
      REAL(rkind),DIMENSION(NRMAX)  :: F1, DERIVQ
      REAL(rkind),DIMENSION(4,NTM):: UOUT
      REAL(rkind),DIMENSION(4,NRMAX):: UQ95
      CHARACTER(LEN=80)::KERRF
      REAL :: GUCLIP

      IF(KFID.EQ.'DIRECT') THEN
         IF(NUM.EQ.2) THEN
            KFID='BT'
            TF(1:NGT)=BB
         ELSEIF(NUM.EQ.3) THEN
            KFID='AMIN'
            TF(1:NGT)=RA
         ELSEIF(NUM.EQ.4) THEN
            KFID='RGEO'
            TF(1:NGT)=RR
         ELSEIF(NUM.EQ.5) THEN
            KFID='KAPPA'
            TF(1:NGT)=RKAP
         ELSEIF(NUM.EQ.6) THEN
            KFID='DELTA'
            TF(1:NGT)=0.D0
         ELSEIF(NUM.EQ.8) THEN
            KFID='PNBI'
            TF(1:NGT)=DBLE(GVT(1:NGT,89)+GVT(1:NGT,90))
         ELSEIF(NUM.EQ.9) THEN
            KFID='PECH'
            TF(1:NGT)=DBLE(GVT(1:NGT,91)+GVT(1:NGT,92))
         ELSEIF(NUM.EQ.10) THEN
            KFID='PICRH'
            TF(1:NGT)=DBLE(GVT(1:NGT,95)+GVT(1:NGT,96))
         ELSEIF(NUM.EQ.11) THEN
            KFID='PLH'
            TF(1:NGT)=DBLE(GVT(1:NGT,93)+GVT(1:NGT,94))
         ELSEIF(NUM.EQ.26) THEN
            KFID='Q95'
            ID=0
            IF(MDLUF.NE.0.AND.NRMAX.NE.NROMAX) THEN
               ID=1
               NRMAX=NROMAX
            ENDIF
            DO NTL=1,NGT
               F1(1:NRMAX)=DBLE(GVRT(1:NRMAX,NTL,27))
               CALL SPL1D (RG,F1,DERIVQ,UQ95,NRMAX,0,IERR)
               CALL SPL1DF(0.95D0,FQ95,RG,UQ95,NRMAX,IERR)
               TF(NTL)=FQ95
            ENDDO
            IF(ID.NE.0) NRMAX=NRAMAX
         ELSEIF(NUM.EQ.29) THEN
            KFID='RHOA'
            TF(1:NGT)=RHOA
         ENDIF

         DGT(1:NGT)=DBLE(GT(1:NGT))
         DIN(1:NGT)=DBLE(TF(1:NGT))
         DERIV(1:NGT)=0.D0
      ELSE
         DGT(1:NGT)=DBLE(GT(1:NGT))
         DIN(1:NGT)=DBLE(GVT(1:NGT,NUM))
         DERIV(1:NGT)=0.D0
      ENDIF

      CALL SPL1D(DGT,DIN,DERIV,UOUT,NGT,0,IERR)
      IF(IERR.NE.0) THEN
         IF(KFID.EQ.'DIRECT') THEN
            WRITE(6,'(A,I2,A,I2)') 'XX TRXOUT: SPL1D DIRECT(',NUM,'): IERR=',IERR
         ELSE
            WRITE(6,'(A,I2,A,I2)') 'XX TRXOUT: SPL1D GVT(',NUM,'): IERR=',IERR
         ENDIF
      ENDIF

      DTL=0.05D0
      NTLMAX=INT((GT(NGT)-GT(1))/SNGL(DTL))+1

      DO NTL=1,NTLMAX
         TIN=DBLE(GT(1))+DTL*DBLE(NTL-1)
         CALL SPL1DF(TIN,DATOUT,DGT,UOUT,NGT,IERR)
         WRITE(KERRF,'(A,I2,A,I2)') 'XX TRXOUT: SPL1DF GVT(',NUM,'): IERR=',IERR
         IF(IERR.NE.0) WRITE(6,*) KERRF
         GTL(NTL)=GUCLIP(TIN)
         GF1(NTL)=GUCLIP(DATOUT*AMP)
      ENDDO

      CALL TRXW1D(KFID,GTL,GF1,NTM,NTLMAX)

      RETURN
      END SUBROUTINE TR_UFILE1D_CREATE

!     *****

      SUBROUTINE TR_UFILE2D_CREATE(KFID,NUM,AMP,ID,IERR)

      USE TRCOMM, ONLY : GVRT, GRG, GRM, GT, NGT, NRMAX, NRMP, NTM, rkind
      USE libitp  
      USE libspl1d
      IMPLICIT NONE
      CHARACTER(LEN=80),INTENT(IN) :: KFID
      INTEGER       ,INTENT(IN) :: NUM, ID
      REAL(rkind)          ,INTENT(IN) :: AMP
      INTEGER       ,INTENT(OUT):: IERR
      INTEGER::NTL, NRLMAX, NTLMAX, NRL
      REAL(rkind)   ::DTL, TIN, F0, R1, R2, F1, F2
      REAL,DIMENSION(NRMP)    :: GRL
      REAL,DIMENSION(NTM)     :: GTL
      REAL,DIMENSION(NRMP,NTM):: GF2
      REAL(rkind),DIMENSION(NTM)     :: DGT,DIN,DERIV
      REAL(rkind),DIMENSION(4,NTM)   :: U
      REAL   :: GUCLIP


      DGT(1:NGT)=DBLE(GT(1:NGT))

      NRLMAX=NRMAX
      DTL=0.05D0
      NTLMAX=INT((GT(NGT)-GT(1))/SNGL(DTL))+1
      IF(ID.EQ.0) THEN
         DO NRL=1,NRLMAX
            GRL(NRL)=GRM(NRL)
            DIN(1:NGT)=DBLE(GVRT(NRL,1:NGT,NUM))
            CALL SPL1D(DGT,DIN,DERIV,U,NGT,0,IERR)
            IF(IERR.NE.0) WRITE(6,'(A,I2,A,I2)') 'XX TRXOUT: SPL1D GVRT(',NUM,'): IERR=',IERR
!
            DO NTL=1,NTLMAX
               TIN=DBLE(GT(1))+DTL*DBLE(NTL-1)
               CALL SPL1DF(TIN,F0,DGT,U,NGT,IERR)
               IF(IERR.NE.0) WRITE(*,'(A,I2,A,I2)') 'XX TRXOUT: SPL1DF GVRT(',NUM,'): IERR=',IERR
               GTL(NTL)    =GUCLIP(TIN)
               GF2(NRL,NTL)=GUCLIP(F0*AMP)
            ENDDO
         ENDDO
      ELSEIF(ID.EQ.1) THEN
         NRLMAX=NRMAX+1
         NRL=1
            GRL(NRL)=GRG(NRL)
            IF(KFID.EQ.'Q') THEN
               DIN(1:NGT)=(4.D0*DBLE(GVRT(NRL,1:NGT,NUM))-DBLE(GVRT(NRL+1,1:NGT,NUM)))/3.D0
            ELSEIF(KFID.EQ.'BPOL') THEN
               DIN(1:NGT)=0.D0
            ELSE
               DO NTL=1,NGT
                  R1=DBLE(GRL(NRL))
                  R2=DBLE(GRL(NRL+1))
                  F1=DBLE(GVRT(NRL  ,NTL,NUM))
                  F2=DBLE(GVRT(NRL+1,NTL,NUM))
                  DIN(NTL)=FCTR(R1,R2,F1,F2)
               ENDDO
            ENDIF
            CALL SPL1D(DGT,DIN,DERIV,U,NGT,0,IERR)
            IF(IERR.NE.0) WRITE(6,'(A,I2,A,I2)') 'XX TRXOUT: SPL1D GVRT(',NUM,'): IERR=',IERR
            DO NTL=1,NTLMAX
               TIN=DBLE(GT(1))+DTL*DBLE(NTL-1)
               CALL SPL1DF(TIN,F0,DGT,U,NGT,IERR)
               IF(IERR.NE.0) WRITE(*,'(A,I2,A,I2)') 'XX TRXOUT: SPL1DF GVRT(',NUM,'): IERR=',IERR
               GTL(NTL)    =GUCLIP(TIN)
               GF2(NRL,NTL)=GUCLIP(F0*AMP)
            ENDDO

         DO NRL=2,NRLMAX
            GRL(NRL)=GRG(NRL)
            DIN(1:NGT)=DBLE(GVRT(NRL-1,1:NGT,NUM))
            CALL SPL1D(DGT,DIN,DERIV,U,NGT,0,IERR)
            IF(IERR.NE.0) WRITE(6,'(A,I2,A,I2)') 'XX TRXOUT: SPL1D GVRT(',NUM,'): IERR=',IERR
            DO NTL=1,NTLMAX
               TIN=DBLE(GT(1))+DTL*DBLE(NTL-1)
               CALL SPL1DF(TIN,F0,DGT,U,NGT,IERR)
               IF(IERR.NE.0) WRITE(*,'(A,I2,A,I2)') 'XX TRXOUT: SPL1DF GVRT(',NUM,'): IERR=',IERR
               GTL(NTL)    =GUCLIP(TIN)
               GF2(NRL,NTL)=GUCLIP(F0*AMP)
            ENDDO
         ENDDO
      ENDIF
      CALL TRXW2D(KFID,GTL,GRL,GF2,NRMP,NTM,NRLMAX,NTLMAX)

      RETURN
      END SUBROUTINE TR_UFILE2D_CREATE

!     *****

      SUBROUTINE TRXW1D(KFID,GT,GF,NTM,NTXMAX)

      USE TRCOMM, ONLY : KDIRW1, KXNDCG, KXNDEV
      IMPLICIT NONE
      CHARACTER(LEN=80)     ,INTENT(IN):: KFID
      INTEGER            ,INTENT(IN):: NTM, NTXMAX
      REAL,DIMENSION(NTM),INTENT(IN):: GT, GF
      INTEGER:: KL1, IST, NTX
      CHARACTER(LEN=9) :: CDATE
      CHARACTER(LEN=80):: KFILE


      CALL GET_DATE(CDATE)

      KL1=len_trim(KDIRW1)
      KFILE=KDIRW1(1:KL1)//KFID
      WRITE(6,*) '- OPEN FILE:',KFILE(1:55)

      OPEN(16,FILE=KFILE,IOSTAT=IST,FORM='FORMATTED',ERR=10)

      WRITE(16,'(1X,A8,A8,A14,A29,A9)') KXNDCG(1:8),KXNDEV(1:8), &
     &     '               ', &
     &     ';-SHOT #- F(X) DATA -UF1DWR- ',CDATE
      WRITE(16,'(1X,A10,A20,A38)') 'TR:/tasktr','                    ', &
     &     ';-SHOT DATE-  UFILES ASCII FILE SYSTEM'
      WRITE(16,'(1X,A30,A29)') &
     &     'TIME          SECONDS         ', &
     &     ';-INDEPENDENT VARIABLE LABEL-'
      WRITE(16,'(1X,A30,A27)') KFID, &
     &     ';-DEPENDENT VARIABLE LABEL-'
      WRITE(16,'(1X,I1,A29,A39)') 2,'                             ', &
     &     ';-PROC CODE- 0:RAW 1:AVG 2:SM. 3:AVG+SM'
      WRITE(16,'(1X,I11,A19,A33)') NTXMAX,'                   ', &
     &     ';-# OF PTS-  X, F(X) DATA FOLLOW:'

      WRITE(16,'(1X,1P6E13.6)') (GT(NTX),NTX=1,NTXMAX)
      WRITE(16,'(1X,1P6E13.6)') (GF(NTX),NTX=1,NTXMAX)

      WRITE(16,'(A52)') &
     &     ';----END-OF-DATA-----------------COMMENTS:-----------'

      CLOSE(16)
      RETURN

   10 WRITE(6,*) 'XX NEW FILE OPEN ERROR : IOSTAT = ',IST
      RETURN
      END SUBROUTINE TRXW1D

!     *****

      SUBROUTINE TRXW2D(KFID,GT,GR,GF,NRM,NTM,NRXMAX,NTXMAX)

      USE TRCOMM, ONLY :KDIRW2, KXNDCG, KXNDEV
      IMPLICIT NONE
      CHARACTER(LEN=80)         ,INTENT(IN):: KFID
      INTEGER                ,INTENT(IN):: NRM, NTM, NRXMAX, NTXMAX
      REAL,DIMENSION(NTM)    ,INTENT(IN):: GT
      REAL,DIMENSION(NRM)    ,INTENT(IN):: GR
      REAL,DIMENSION(NRM,NTM),INTENT(IN):: GF
      INTEGER:: KL2,IST,NRX,NTX
      CHARACTER(LEN=9) :: CDATE
      CHARACTER(LEN=80):: KFILE


      CALL GET_DATE(CDATE)

      KL2=len_trim(KDIRW2)
      KFILE=KDIRW2(1:KL2)//KFID
      WRITE(6,*) '- OPEN FILE:',KFILE(1:55)

      OPEN(16,FILE=KFILE,IOSTAT=IST,FORM='FORMATTED',ERR=10)

      WRITE(16,'(1X,A8,A8,A14,A29,A9)') KXNDCG(1:8),KXNDEV(1:8), &
     &     '               ', &
     &     ';-SHOT #- F(X) DATA -UF1DWR- ',CDATE
      WRITE(16,'(1X,A10,A20,A38)') 'TR:/tasktr','                    ', &
     &     ';-SHOT DATE-  UFILES ASCII FILE SYSTEM'
      WRITE(16,'(1X,A30,A32)') &
     &     'RHO                           ', &
     &     ';-INDEPENDENT VARIABLE LABEL: X-'
      WRITE(16,'(1X,A30,A32)') &
     &     'TIME          SECONDS         ', &
     &     ';-INDEPENDENT VARIABLE LABEL: Y-'
      WRITE(16,'(1X,A30,A27)') KFID, &
     &     ';-DEPENDENT VARIABLE LABEL-'
      WRITE(16,'(1X,I1,A29,A39)') 2,'                             ', &
     &     ';-PROC CODE- 0:RAW 1:AVG 2:SM. 3:AVG+SM'
      WRITE(16,'(1X,I11,A19,A12)') NRXMAX,'                   ', &
     &     ';-# OF X PTS-:'
      WRITE(16,'(1X,I11,A19,A35)') NTXMAX,'                   ', &
     &     ';-# OF Y PTS-  X, F(X) DATA FOLLOW:'

      WRITE(16,'(1X,1P6E13.6)') (GR(NRX),NRX=1,NRXMAX)
      WRITE(16,'(1X,1P6E13.6)') (GT(NTX),NTX=1,NTXMAX)
      WRITE(16,'(1X,1P6E13.6)') ((GF(NRX,NTX),NRX=1,NRXMAX),NTX=1,NTXMAX)

      WRITE(16,'(A52)')  ';----END-OF-DATA-----------------COMMENTS:-----------'

      CLOSE(16)
      RETURN

   10 WRITE(6,*) 'XX NEW FILE OPEN ERROR : IOSTAT = ',IST
      RETURN
      END SUBROUTINE TRXW2D

!     *****

      SUBROUTINE GET_DATE(CDATE)

      IMPLICIT NONE
      CHARACTER(LEN=9),INTENT(OUT):: CDATE
      INTEGER      :: NDD, NDM, NDY, NTIH, NTIM, NTIS
      CHARACTER(LEN=2):: CDD, CDY
      CHARACTER(LEN=3):: CDM
      CHARACTER(LEN=3),DIMENSION(12):: CDATA = &
     &     (/'Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'/)


      CALL GUDATE(NDY,NDM,NDD,NTIH,NTIM,NTIS)
      CDM=CDATA(NDM)
      IF(NDD.LT.10) THEN
         WRITE(CDD,'(A1,I1)') ' ',NDD
      ELSE
         WRITE(CDD,'(I2)') NDD
      ENDIF
      NDY=NDY-100
      IF(NDY.LT.10) THEN
         WRITE(CDY,'(I1,I1)') 0,NDY
      ELSE
         WRITE(CDY,'(I2)') NDY
      ENDIF
      WRITE(CDATE,'(A2,A1,A3,A1,A2)') CDD,'-',CDM,'-',CDY

      RETURN
      END SUBROUTINE GET_DATE

END MODULE trrslt_files
