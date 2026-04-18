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

# Phase L-1: SRCS split into CORE / GRAPHICS / MENU groups so later phases
# (libeq_pic.a / libeqapi.so) can link the core physics without pulling in
# GSAF plotting or the interactive menu. The eq / pl / ak binaries still
# build from the full union ($(SRCS_CORE) + $(SRCS_GRAPHICS) + $(SRCS_MENU)),
# so behavior is unchanged.

# --- core (equilibrium physics + file I/O + regression hook, no graphics, no menu) ---
SRCS_CORE = equcom.f90 equread.f90 eqlib.f90 \
            eqbpsd.f eqinit.f eqcalc.f eqcalq.f eqcalv.f \
            eqsub.f eqfunc.f eqintf.f eqsplf.f equintf.f \
            eq-eqdsk.f eq-qst.f eqgetp.f eqregress.f \
            newton.f invematrix.f equnit.f eqrppl.f

# --- graphics (GSAF plotting, contour; eqfile uses GUCLIP) ---
# Note: eqg2d.f / eqg3d.f remain in SRC2D / SRC3D below (selected per
# libeq.a vs libeq3.a target), so they are NOT listed here.
SRCS_GRAPHICS = eqgout.f eqgsub.f eqfile.f

# --- interactive menu driver (depends on graphics) ---
SRCS_MENU = eqmenu.f

# --- final SRCS for the existing eq / pl / ak binaries (unchanged behaviour) ---
SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)

# Legacy alias for the module group (kept for any ad-hoc references).
SRCX = equcom.f90 equread.f90 eqlib.f90

# Phase L-2: C ABI sources. Compiled via the eq_api_compile_check /
# eq_api_check targets only; NOT part of $(SRCS) and NOT linked into
# libeq.a or the eq / pl / ak binaries so their behavior is unchanged.
# The full libeqapi.so build arrives in Phase L-4.
SRCS_API = eq_state.f90 eq_param_registry.f90 eq_api.f90
OBJ_API  = $(SRCS_API:.f90=.o) eq_api_common.o

SRCT = trtest.f treqin.f
SRCP = pltest.f
SRCA = aktest.f akeqin.f
SRC2D= eqg2d.f
SRC3D= eqg3d.f

OBJS = $(patsubst %.f,%.o,$(patsubst %.f90,%.o,$(SRCS)))
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

# libtrapi.so / libeqapi.so exclude all graphics and the interactive menu,
# so libeq_pic.a is built from $(SRCS_CORE) only. The L-1 split (above)
# made this explicit: SRCS_GRAPHICS (eqgout/eqgsub/eqg2d/eqg3d/eqfile) and
# SRCS_MENU (eqmenu) are omitted. Any symbols still referenced from CORE
# that resolve into GRAPHICS (e.g. equread::eqdsk via eq-eqdsk/eq-qst)
# remain undefined in the resulting .so and must be linked with
# -Wl,--unresolved-symbols=ignore-in-shared-libs, failing loudly if a
# graphics path is ever reached at run-time.
SRCS_EQ_NOGR = $(SRCS_CORE)
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

eqmain.o: eqmain.f $(EQCOMM)
eqinit.o: eqinit.f $(EQCOMM)
eqcalc.o: eqcalc.f $(EQCOMM)
eqcalx.o: eqcalx.f $(EQCOMM) eqcom5.inc
eqcalq.o: eqcalq.f $(EQCOMM) eqcom3.inc
eqcalv.o: eqcalv.f $(EQCOMM) eqcom2.inc
eqsub.o : eqsub.f  $(EQCOMM) eqcom2.inc
eqfunc.o: eqfunc.f $(EQCOMM) eqcom2.inc eqcom4.inc
eqsplf.o: eqsplf.f $(EQCOMM) eqcom3.inc
eqfile.o: eqfile.f $(EQCOMM) eqcom2.inc
eq-eqdsk.o: eq-eqdsk.f $(EQCOMM) eqcom2.inc
eq-qst.o: eq-qst.f $(EQCOMM) eqcom2.inc
eqintf.o: eqintf.f $(EQCOMM) eqcom2.inc
eqgout.o: eqgout.f $(EQCOMM) eqcom2.inc eqcom3.inc
eqbpsd.o: eqbpsd.f $(EQCOMM) eqcom3.inc
#eqtrbpsd.o: eqtrbpsd.f $(EQCOMM)
#eqtrbpsdlib.o: eqtrbpsdlib.f90
eqjft2m.o: eqjft2m.f $(EQCOMM) eqcom3.inc
eqlib.o : eqlib.f90
equnit.o: equnit.f eqbpsd.f
eqgsub.o: eqgsub.f
eqg2d.o: eqg2d.f $(EQCOMM) eqcom3.inc
eqg3d.o: eqg3d.f $(EQCOMM) eqcom3.inc
equcom.o: equcom.f90
equread.o: equread.f90 equcom.f90
equintf.o: equintf.f $(EQCOMM) eqcom3.inc
eqrppl.o: eqrppl.f $(EQCOMM) eqcom3.inc
eqgetp.o: eqgetp.f $(EQCOMM) eqcom3.inc
eqregress.o: eqregress.f $(EQCOMM) eqcom3.inc eqcomq.inc
trtest.o: trtest.f
treqin.o: treqin.f $(EQCOMM) eqcom3.inc eqcom4.inc
pltest.o: pltest.f
aktest.o: aktest.f
akeqin.o: akeqin.f $(EQCOMM) eqcom3.inc
newton.o: newton.f
invematrix.o: invematrix.f

# ---------------------------------------------------------------------
# Phase L-2 C ABI scaffold
#
# `make eq_api_compile_check` compiles the new API objects
# (eq_state.o / eq_param_registry.o / eq_api.o / eq_api_common.o)
# without linking. It does NOT touch libeq.a, the eq / pl / ak
# binaries, or any existing objects, so the L-0/L-1 behavior is
# bit-identical.
#
# `make eq_api_check` additionally builds a minimal C driver
# (tests/c_abi/test_smoke.c) that links libeq.a + OBJ_API and
# calls eq_init -> eq_get_state -> eq_finalize. The driver prints
# the grid dimensions returned by eq_get_state.
#
# Both targets require libeq.a to be up-to-date because eq_api_common.f
# uses INCLUDE 'eqcomm.inc' which pulls in USE plcomm from pl/ (same
# dependency chain as libeq.a itself).
# ---------------------------------------------------------------------
CC ?= gcc
CFLAGS_API ?= -Wall -Wextra -O2

EQ_API_SMOKE_DIR = tests/c_abi
EQ_API_SMOKE_C   = $(EQ_API_SMOKE_DIR)/test_smoke.c
EQ_API_SMOKE_O   = $(EQ_API_SMOKE_DIR)/test_smoke.o
EQ_API_SMOKE_BIN = $(EQ_API_SMOKE_DIR)/test_smoke

eq_state.o          : eq_state.f90
eq_param_registry.o : eq_param_registry.f90
eq_api.o            : eq_api.f90 eq_state.f90 eq_param_registry.f90 equnit.f
eq_api_common.o     : eq_api_common.f $(EQCOMM)

.PHONY: eq_api_compile_check
eq_api_compile_check: libs libeq.a $(OBJ_API)
	@echo "Phase L-2 eq_api_compile_check OK: $(OBJ_API)"

$(EQ_API_SMOKE_O): $(EQ_API_SMOKE_C) eq_api.h
	$(CC) $(CFLAGS_API) -I. -c -o $(EQ_API_SMOKE_O) $(EQ_API_SMOKE_C)

$(EQ_API_SMOKE_BIN): $(EQ_API_SMOKE_O) $(OBJ_API) libeq.a
	$(FLINKER) -o $(EQ_API_SMOKE_BIN) $(EQ_API_SMOKE_O) $(OBJ_API) \
	    $(LIBS2) $(FFLAGS) $(FLIBS) $(LIBX_MTX)

.PHONY: eq_api_check
eq_api_check: libs libeq.a $(EQ_API_SMOKE_BIN)
	@echo "Phase L-2 eq_api_check: running $(EQ_API_SMOKE_BIN) ..."
	@LD_LIBRARY_PATH=.:$${LD_LIBRARY_PATH} $(EQ_API_SMOKE_BIN)
	@echo "Phase L-2 eq_api_check OK"
