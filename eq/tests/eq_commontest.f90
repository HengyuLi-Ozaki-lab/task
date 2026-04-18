! eq_commontest.f90
!
! Phase F-1 Task F-1-3 bootstrap regression test.
!
! Uses each of the four new eqcom{0..3}_mod MODULEs, inspects the grid
! PARAMETERs, touches one SAVE variable from each non-parameter module,
! and prints the dims. The executable is standalone (not linked into
! libeq.a) and is run as a sanity check before any production change
! to the COMMON->MODULE migration.
!
! Build:    make -C eq eq_commontest
! Run:      ./eq/eq_commontest
!
! Exit 0 on success, non-zero if any grid dim fails its expected value.

PROGRAM eq_commontest
  USE eqcom0_mod
  USE eqcom1_mod
  USE eqcom2_mod
  USE eqcom3_mod
  IMPLICIT NONE

  INTEGER :: ierr

  ierr = 0

  WRITE(6, '(A)') '=== eq_commontest: eqcom{0..3}_mod bootstrap ==='

  ! --- eqcom0_mod PARAMETERs ---
  WRITE(6, '(A)') '-- eqcom0_mod grid PARAMETERs --'
  WRITE(6, '(A,I0)')  '  NRGM  = ', NRGM
  WRITE(6, '(A,I0)')  '  NZGM  = ', NZGM
  WRITE(6, '(A,I0)')  '  NPSM  = ', NPSM
  WRITE(6, '(A,I0)')  '  NRVM  = ', NRVM
  WRITE(6, '(A,I0)')  '  NTVM  = ', NTVM
  WRITE(6, '(A,I0)')  '  NSUM  = ', NSUM
  WRITE(6, '(A,I0)')  '  NSGM  = ', NSGM
  WRITE(6, '(A,I0)')  '  NTGM  = ', NTGM
  WRITE(6, '(A,I0)')  '  NUGM  = ', NUGM
  WRITE(6, '(A,I0)')  '  NRM   = ', NRM
  WRITE(6, '(A,I0)')  '  NTHM  = ', NTHM
  WRITE(6, '(A,I0)')  '  NPFCM = ', NPFCM

  ! --- eqcom3_mod re-exports NRMP / NTHMP ---
  WRITE(6, '(A)') '-- eqcom3_mod derived PARAMETERs --'
  WRITE(6, '(A,I0)')  '  NRMP  = ', NRMP
  WRITE(6, '(A,I0)')  '  NTHMP = ', NTHMP
  WRITE(6, '(A,I0)')  '  NRrpM = ', NRrpM
  WRITE(6, '(A,I0)')  '  NZrpM = ', NZrpM

  ! --- eqcom2_mod derived PARAMETERs ---
  WRITE(6, '(A)') '-- eqcom2_mod derived PARAMETERs --'
  WRITE(6, '(A,I0)')  '  MLM   = ', MLM
  WRITE(6, '(A,I0)')  '  MWM   = ', MWM
  WRITE(6, '(A,I0)')  '  NSGMP = ', NSGMP
  WRITE(6, '(A,I0)')  '  NTGMP = ', NTGMP
  WRITE(6, '(A,I0)')  '  NSGPM = ', NSGPM
  WRITE(6, '(A,I0)')  '  NTGPM = ', NTGPM
  WRITE(6, '(A,I0)')  '  NXM   = ', NXM
  WRITE(6, '(A,I0)')  '  NT    = ', NT

  ! --- Verify expected values (hard-coded to eqcom0.inc commitments) ---
  IF (NRGM  /= 513 ) CALL fail('NRGM',  NRGM,  513)
  IF (NZGM  /= 513 ) CALL fail('NZGM',  NZGM,  513)
  IF (NPSM  /= 513 ) CALL fail('NPSM',  NPSM,  513)
  IF (NRVM  /= 1001) CALL fail('NRVM',  NRVM,  1001)
  IF (NTVM  /= 1025) CALL fail('NTVM',  NTVM,  1025)
  IF (NSUM  /= 1343) CALL fail('NSUM',  NSUM,  1343)
  IF (NSGM  /= 128 ) CALL fail('NSGM',  NSGM,  128)
  IF (NTGM  /= 128 ) CALL fail('NTGM',  NTGM,  128)
  IF (NUGM  /= 128 ) CALL fail('NUGM',  NUGM,  128)
  IF (NRM   /= 1001) CALL fail('NRM',   NRM,   1001)
  IF (NTHM  /= 2049) CALL fail('NTHM',  NTHM,  2049)
  IF (NPFCM /= 10  ) CALL fail('NPFCM', NPFCM, 10)
  IF (NRMP  /= NRM + 1 ) CALL fail('NRMP',  NRMP,  NRM  + 1)
  IF (NTHMP /= NTHM + 1) CALL fail('NTHMP', NTHMP, NTHM + 1)

  ! --- Touch one SAVE variable from each non-parameter module to
  !     ensure it is addressable (default zero-initialisation expected). ---
  RAXIS   = 0.0D0   ! eqcom1_mod
  ZAXIS   = 0.0D0   ! eqcom1_mod
  DSG     = 0.0D0   ! eqcom2_mod
  DTG     = 0.0D0   ! eqcom2_mod
  PSITB   = 0.0D0   ! eqcom3_mod
  NRPMAX  = 0       ! eqcom3_mod

  IF (ierr /= 0) THEN
     WRITE(6, '(A,I0,A)') 'FAIL: ', ierr, ' mismatches'
     STOP 1
  ELSE
     WRITE(6, '(A)') 'PASS: all PARAMETERs match eqcom0.inc'
  END IF

CONTAINS

  SUBROUTINE fail(name, got, expected)
    CHARACTER(LEN=*), INTENT(IN) :: name
    INTEGER, INTENT(IN)          :: got, expected
    WRITE(6, '(A,A,A,I0,A,I0)') '  FAIL: ', name, &
         ' got=', got, ' expected=', expected
    ierr = ierr + 1
  END SUBROUTINE fail

END PROGRAM eq_commontest
