### $Id$ ###
include ../make.header
include ../mtxp/make.mtxp
#LIB_MTX=$(LIB_MTX_BND)
#LIBX_MTX=$(LIBX_MTX_BND)
#LIB_MTX=$(LIB_MTX_PCG)
#LIBX_MTX=$(LIBX_MTX_PCG)
#LIB_MTX=$(LIB_MTX_MUMPS)
#LIBX_MTX=$(LIBX_MTX_MUMPS)
#LIB_MTX=$(LIBXMTX_KSP)
#LIBX_MTX=$(LIBX_MTX_KSP)

FFLAGS=-g $(OFLAGS)
#FFLAGS=$(DFLAGS)

MODINCLUDE=-I$(MOD) -I../../bpsd/$(MOD) -I../mtxp/$(MOD) -I../pl/$(MOD) -I../lib/$(MOD)

# SRCS_CORE: Phase F-1 (eq F90 modernization) -- new F90 MODULEs
# mirroring the eqcom{0..3}.inc COMMON bundles. These must compile
# before any file that USEs them (directly or via the shim headers
# eqcom{c,m,q,x}.inc). Keep them at the head of $(OBJS) so the make
# dependency walker emits their .mod files early.
SRCS_CORE = eqcom0_mod.f90 eqcom1_mod.f90 eqcom2_mod.f90 eqcom3_mod.f90

SRCX = equcom.f90 equread.f90 eqlib.f90
SRCS = eqbpsd.f eqinit.f eqmenu.f eqcalc.f eqcalq.f eqcalv.f \
       eqsub.f eqfunc.f eqintf.f eqsplf.f equintf.f \
       eq-eqdsk.f eq-qst.f eqfile.f \
       eqgout.f eqgsub.f eqgetp.f eqregress.f \
       newton.f invematrix.f equnit.f eqrppl.f

SRCT = trtest.f treqin.f
SRCP = pltest.f
SRCA = aktest.f akeqin.f
SRC2D= eqg2d.f
SRC3D= eqg3d.f

OBJS = $(SRCS_CORE:.f90=.o) $(SRCX:.f90=.o) $(SRCS:.f=.o)
OBJT = $(SRCT:.f=.o)
OBJP = $(SRCP:.f=.o)
OBJA = $(SRCA:.f=.o)
OBJ2D=$(SRC2D:.f=.o)
OBJ3D=$(SRC3D:.f=.o)

LIBS2 = libeq.a ../pl/libpl.a ../lib/libgrf.a ../lib/libtask.a ../../bpsd/libbpsd.a
LIBS3 = ../pl/libpl.a libeq3.a ../lib/libgrf.a ../lib/libtask.a ../../bpsd/libbpsd.a

.SUFFIXES: .f90

.f.o :
	$(FCFIXED) $(FFLAGS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)
.f90.o :
	$(FCFREE) $(FFLAGS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)

all : libs eq


../../bpsd/libbpsd.a:
	(cd ../../bpsd; make libbpsd.a)
../lib/libtask.a:
	(cd ../lib; make libtask.a)
../lib/libgrf.a:
	(cd ../lib; make libgr.a)
../pl/libpl.a:
	(cd ../mtxp; make)
	(cd ../pl; make libpl.a)

libeq.a: $(OBJS) $(OBJ2D)
	$(LD) $(LDFLAGS) libeq.a $(OBJS) $(OBJ2D) ../pl/libpl.a
libeq3.a: $(OBJS) $(OBJ3D)
	$(LD) $(LDFLAGS) libeq3.a $(OBJS) $(OBJ3D)

libs:
	(cd ../../bpsd; make libbpsd.a)
	(cd ../lib; make libtask.a)
	(cd ../lib; make libgrf.a)
	(cd ../mtxp; make)
	(cd ../pl; make libpl.a)

eq: libs libeq.a eqmain.o
	$(FLINKER) eqmain.o $(LIBS2) -o $@ $(FFLAGS) $(FLIBS) $(LIBX_MTX)

eq3: libs libeq3.a eqmain.o
	$(FLINKER) eqmain.o $(LIBS3) -o $@ $(FFLAGS) $(FLIBS) $(LIBX_MTX)

tr : libs libeq.a $(OBJT)
	$(FLINKER) $(OBJT) $(LIBS2) -o $@ $(FFLAGS) $(FLIBS) $(LIBX_MTX)

pl : libs libeq.a $(OGJP)
	$(FLINKER) $(OBJP) $(LIBS2) -o $@ $(FFLAGS) $(FLIBS) $(LIBX_MTX)

ak : libs libeq.a $(OBJA)
	$(FLINKER) $(OBJA) $(LIBS2) -o $@ $(FFLAGS) $(FLIBS) $(LIBX_MTX)

clean:
	-rm -f core a.out *.o *.mod ./*~ *.a $(MOD)/*.mod
	-rm -f doc/*~

veryclean: clean
	rm -f eq pl ak

# ---------------------------------------------------------------------
# PIC build (Phase L-4) - opt-in target for libtrapi.so.
#
# `libeq_pic.a` mirrors libeq.a but uses -fPIC and a separate
# obj/pic + mod_pic tree so the existing libeq.a/eq build is untouched.
# Per Bugbot review, this uses `$(AR) rcs` instead of `$(LD)` (which is
# `ld -r -o` and would emit a non-archive object file).
# ---------------------------------------------------------------------
OBJDIR_PIC=obj/pic
MODDIR_PIC=mod_pic
PIC_FLAGS=-fPIC -J$(MODDIR_PIC) -I$(MODDIR_PIC)
MODINCLUDE_PIC=-I$(MODDIR_PIC) -I../../bpsd/$(MOD) -I../mtxp/mod_pic -I../pl/mod_pic -I../lib/mod_pic

# libtrapi.so excludes all graphics, so libeq_pic.a drops:
#   - eqgout / eqgsub / eqg2d : direct GSAF (PAGES/PAGEE/GRD1D/etc.)
#   - equread                 : module with embedded gsaf calls (pagee)
#
# We KEEP eqfile/equnit/eq-eqdsk/eq-qst etc. even though they reference
# equread::eqdsk; the resulting .so has those symbols undefined but they
# are unreachable from the tr_init -> tr_run happy path (only invoked on
# explicit EQDSK file load, which the C ABI does not expose). Linking the
# shared object with -Wl,--unresolved-symbols=ignore-in-shared-libs lets
# the .so load while still failing loudly if a graphics path is ever
# reached at run-time.
SRCS_EQ_NOGR = eqcom0_mod.f90 eqcom1_mod.f90 eqcom2_mod.f90 eqcom3_mod.f90
SRCS_EQ_NOGR += equcom.f90 equread.f90 eqlib.f90
SRCS_EQ_NOGR += eqbpsd.f eqinit.f eqmenu.f eqcalc.f eqcalq.f eqcalv.f \
                eqsub.f eqfunc.f eqintf.f eqsplf.f equintf.f \
                eq-eqdsk.f eq-qst.f eqfile.f eqgetp.f eqregress.f \
                newton.f invematrix.f equnit.f eqrppl.f
OBJS_PIC = $(addprefix $(OBJDIR_PIC)/, $(patsubst %.f90,%.o,$(patsubst %.f,%.o,$(SRCS_EQ_NOGR))))

$(OBJDIR_PIC)/%.o: %.f
	@mkdir -p $(OBJDIR_PIC) $(MODDIR_PIC)
	$(FCFIXED) $(FFLAGS) $(PIC_FLAGS) -c $< -o $@ $(MODINCLUDE_PIC)
$(OBJDIR_PIC)/%.o: %.f90
	@mkdir -p $(OBJDIR_PIC) $(MODDIR_PIC)
	$(FCFREE) $(FFLAGS) $(PIC_FLAGS) -c $< -o $@ $(MODINCLUDE_PIC)

libeq_pic.a: $(OBJS_PIC)
	$(AR) rcs libeq_pic.a $(OBJS_PIC)

clean_pic:
	-rm -rf $(OBJDIR_PIC) $(MODDIR_PIC) libeq_pic.a

EQCOMM = eqcom0.inc eqcom1.inc

# Phase F-1: dependencies for new F90 COMMON-replacement MODULEs.
# - eqcom0_mod is the root (PARAMETER-only).
# - eqcom1/2/3_mod USE eqcom0_mod, so their .mod must be available.
# - Every .f that INCLUDEs a shim (eqcom{c,m,q,x}.inc) now transitively
#   requires the corresponding .mod file. We list them here so that a
#   parallel `make -jN` cannot race past module compilation.
EQCOM_MODS = eqcom0_mod.o eqcom1_mod.o eqcom2_mod.o eqcom3_mod.o

eqcom0_mod.o: eqcom0_mod.f90
eqcom1_mod.o: eqcom1_mod.f90 eqcom0_mod.o
eqcom2_mod.o: eqcom2_mod.f90 eqcom0_mod.o
eqcom3_mod.o: eqcom3_mod.f90 eqcom0_mod.o

# Shim .inc files now USE the new MODULEs; every consumer of a shim
# therefore depends on those .mod files in addition to the raw .inc.
eqmain.o: eqmain.f $(EQCOMM) $(EQCOM_MODS)
eqinit.o: eqinit.f $(EQCOMM) $(EQCOM_MODS)
eqcalc.o: eqcalc.f $(EQCOMM) $(EQCOM_MODS)
eqcalx.o: eqcalx.f $(EQCOMM) eqcom5.inc $(EQCOM_MODS)
eqcalq.o: eqcalq.f $(EQCOMM) eqcom3.inc $(EQCOM_MODS)
eqcalv.o: eqcalv.f $(EQCOMM) eqcom2.inc $(EQCOM_MODS)
eqsub.o : eqsub.f  $(EQCOMM) eqcom2.inc $(EQCOM_MODS)
eqfunc.o: eqfunc.f $(EQCOMM) eqcom2.inc eqcom4.inc $(EQCOM_MODS)
eqsplf.o: eqsplf.f $(EQCOMM) eqcom3.inc $(EQCOM_MODS)
eqfile.o: eqfile.f $(EQCOMM) eqcom2.inc $(EQCOM_MODS)
eq-eqdsk.o: eq-eqdsk.f $(EQCOMM) eqcom2.inc $(EQCOM_MODS)
eq-qst.o: eq-qst.f $(EQCOMM) eqcom2.inc $(EQCOM_MODS)
eqintf.o: eqintf.f $(EQCOMM) eqcom2.inc $(EQCOM_MODS)
eqgout.o: eqgout.f $(EQCOMM) eqcom2.inc eqcom3.inc $(EQCOM_MODS)
eqbpsd.o: eqbpsd.f $(EQCOMM) eqcom3.inc $(EQCOM_MODS)
#eqtrbpsd.o: eqtrbpsd.f $(EQCOMM)
#eqtrbpsdlib.o: eqtrbpsdlib.f90
eqjft2m.o: eqjft2m.f $(EQCOMM) eqcom3.inc $(EQCOM_MODS)
eqlib.o : eqlib.f90
equnit.o: equnit.f eqbpsd.f $(EQCOM_MODS)
eqgsub.o: eqgsub.f
eqg2d.o: eqg2d.f $(EQCOMM) eqcom3.inc $(EQCOM_MODS)
eqg3d.o: eqg3d.f $(EQCOMM) eqcom3.inc $(EQCOM_MODS)
equcom.o: equcom.f90
equread.o: equread.f90 equcom.f90
equintf.o: equintf.f $(EQCOMM) eqcom3.inc $(EQCOM_MODS)
eqrppl.o: eqrppl.f $(EQCOMM) eqcom3.inc $(EQCOM_MODS)
eqgetp.o: eqgetp.f $(EQCOMM) eqcom3.inc $(EQCOM_MODS)
eqregress.o: eqregress.f $(EQCOMM) eqcom3.inc eqcomq.inc $(EQCOM_MODS)
trtest.o: trtest.f
treqin.o: treqin.f $(EQCOMM) eqcom3.inc eqcom4.inc $(EQCOM_MODS)
pltest.o: pltest.f
aktest.o: aktest.f
akeqin.o: akeqin.f $(EQCOMM) eqcom3.inc $(EQCOM_MODS)
newton.o: newton.f
invematrix.o: invematrix.f

# ---------------------------------------------------------------------
# Phase F-1 Task F-1-3: eq_commontest bootstrap program.
# Standalone test that USEs all four new MODULEs and prints the grid
# dimensions, so regressions on PARAMETER values fail loudly. Not linked
# into libeq.a / eq. Build with `make eq_commontest`.
# ---------------------------------------------------------------------
EQCOMMONTEST_OBJS = eqcom0_mod.o eqcom1_mod.o eqcom2_mod.o eqcom3_mod.o \
                   tests/eq_commontest.o

tests/eq_commontest.o: tests/eq_commontest.f90 $(EQCOM_MODS)
	$(FCFREE) $(FFLAGS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)

eq_commontest: $(EQCOMMONTEST_OBJS)
	$(FLINKER) $(EQCOMMONTEST_OBJS) -o $@ $(FFLAGS)

run_commontest: eq_commontest
	./eq_commontest

clean_commontest:
	-rm -f tests/eq_commontest.o eq_commontest
