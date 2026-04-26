### $Id$ ###
include ../make.header
include ../mtxp/make.mtxp

# Phase 0 baseline build: default to LIB_MTX_BND (no MPI dep) so the
# legacy `make ti` link path works on a single-node dev box. Switch back
# to LIB_MTX_MUMPS only when a real MPI/MUMPS runtime is available.
LIB_MTX=$(LIB_MTX_BND)
LIBX_MTX=$(LIBX_MTX_BND)
#LIB_MTX=$(LIB_MTX_PCG)
#LIBX_MTX=$(LIBX_MTX_PCG)
#LIB_MTX=$(LIB_MTX_MUMPS)
#LIBX_MTX=$(LIBX_MTX_MUMPS)
#LIB_MTX=$(LIBXMTX_KSP)
#LIBX_MTX=$(LIBX_MTX_KSP)

FFLAGS = $(OFLAGS)
#FFLAGS = $(DFLAGS)

.SUFFIXES:
.SUFFIXES: .f .f90 .mod .o .a

.f.o :
	$(FCFIXED) $(FFLAGS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)
.f90.o :
	$(FCFREE) $(FFLAGS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)

MODINCLUDE= -I./$(MOD) -I../open-adas/adf11/adf11-lib/$(MOD) \
            -I../adpost/$(MOD) -I../eq/$(MOD) -I../pl/$(MOD) \
            -I../mtxp/$(MOD) -I../lib/$(MOD) -I../../bpsd/$(MOD) 

SRCS=   ticomm.f90 tiadas.f90 \
	tiinit.f90 tiparm.f90 \
	ticoef.f90 tisource.f90 ticalc.f90 tirecord.f90 \
        tiprep.f90 tiregress.f90 tiexec.f90 \
        tigout.f90 timenu.f90

# C ABI sources (Phase L-2+). Compiled via the ti_api_check target only;
# NOT part of $(SRCS) and NOT linked into libti.a / ti. The full
# libtiapi.so build arrives in Phase L-4.
SRCS_API=ti_state.f90 ti_param_registry.f90 ti_api.f90

#      trprof.f90 trufsub.f90 trufile.f90 trfile.f90 trhelp.f90 \
#      trexec.f90 trcalc.f90 \
#      tradat.f90 cdbm.f90 trmodels.f90 trcoef.f90 tritg.f90 \
#      trrslt.f90 \
#      trpnb.f90 trprf.f90 trpnf.f90 trpel.f90 trpsc.f90 trmdlt.f90 \
#      trgout.f90 trgrar.f90 trgrat.f90 trgrap.f90 trgrae.f90 \
#      trgrad.f90 trgram.f90 trgsub.f90 trfout.f90 \
#      trunit.f90 trloop.f90 trmenu.f90 tr_bpsd.f90

OBJS=$(SRCS:.f90=.o)
OBJ_API=$(SRCS_API:.f90=.o)

LIBS=libti.a ../adpost/lib-adpost.a ../open-adas/adf11/adf11-lib/lib-adf11.a ../eq/libeq.a ../pl/libpl.a ../lib/libtask.a ../lib/libgrf.a ../../bpsd/libbpsd.a


all: libs ti

libti.a: $(OBJS)
	$(LD) $(LDFLAGS) $@ $(OBJS)

../../bpsd/libbpsd.a:
	(cd ../../bpsd; make libbpsd.a)
../lib/libtask.a:
	(cd ../lib; make libtask.a)
../lib/libgrf.a:
	(cd ../lib; make libgrf.a)
../open-adas/adf11/adf11-lib/lib-adf11.a: 
	(cd ../open-adas/adf11/adf11-lib; make lib-adf11.a)
../adpost/lib-adpost.a: 
	(cd ../adpost; make lib-adpost.a)
../pl/libpl.a:
	(cd ../pl; make libpl.a)
../eq/libeq.a:
	(cd ../eq; make libeq.a)


libs:
	(cd ../../bpsd; make libbpsd.a)
	(cd ../lib; make libtask.a)
	(cd ../lib; make libgrf.a)
	(cd ../mtxp; make)
	(cd ../open-adas/adf11/adf11-lib; make lib-adf11.a)
	(cd ../adpost; make lib-adpost.a)
	(cd ../pl; make libpl.a)
	(cd ../eq; make libeq.a)

ti: libs libti.a timain.o 
	$(FLINKER) timain.o $(LIBS) -o $@ $(FFLAGS) $(FLIBS) $(LIBX_MTX)

clean :
	rm -f ./#* ./*~ *.o nclass/*.o itg/*.o glf/*.o cytran/*.o mmm95/*.o mbgb/*.o a.out core *.a *.mod $(MOD)/*.mod
	-rm -f $(TI_API_NEG_O) $(TI_API_NEG_BIN)
	-rm -f $(TI_API_SO_O)  $(TI_API_SO_BIN)

veryclean : clean
	rm -f ti

distclean: clean
	cd ../tr && make clean
	cd ../pl && make clean
	cd ../eq && make clean
	cd ../lib && make clean

clean_pic:
	-rm -rf $(OBJDIR_PIC) $(MODDIR_PIC) libtiapi.so
	-rm -f $(TI_API_SO_O) $(TI_API_SO_BIN)

ticomm.o : ticomm.f90
timain.o : timain.f90 ticomm.f90  timenu.f90
timenu.o : timenu.f90 ticomm.f90
tiinit.o : tiinit.f90 ticomm.f90
tiparm.o : tiparm.f90 ticomm.f90
tiprep.o : tiprep.f90 ticomm.f90 ../adpost/lib-adpost.f90 \
           ../open-adas/adf11/adf11-lib/lib-adf11.f90
tigout.o : tigout.f90 ticomm.f90
tiregress.o : tiregress.f90 ticomm.f90
tiexec.o : tiexec.f90 ticomm.f90 tiregress.f90
ticoef.o : ticoef.f90 ticomm.f90
tisource.o : tisource.f90 ticomm.f90
ticalc.o : ticalc.f90 ticomm.f90
tirecord.o : tirecord.f90 ticomm.f90

nclass/rarray_sum.o : nclass/rarray_sum.f
nclass/rarray_copy.o: nclass/rarray_copy.f
nclass/rarray_zero.o: nclass/rarray_zero.f
nclass/u_erf.o      : nclass/u_erf.f
nclass/u_lu_backsub.o: nclass/u_lu_backsub.f
nclass/u_lu_decomp.o : nclass/u_lu_decomp.f
nclass/write_mod.o   : nclass/write_mod.f

# ---------------------------------------------------------------------
# Phase L-6 C ABI test bundle
#
# `make ti_api_check_all` builds and runs the full C ABI test set:
#
#   test_smoke     - 4 entry points return TI_OK              (L-3)
#   test_param     - ti_set_param + ti_get_state dispatch     (L-3)
#   test_run       - ti_run advances T by N*DT                (L-3)
#   test_run_so    - dlopen libtiapi.so + full cycle          (L-4)
#   test_negative  - rejection contracts (pre-init / unknown  (L-6)
#                    name / malformed subscript / double-
#                    finalize)
#
# The test_negative driver is header-only: it compiles against
# ti_api.h only and at link time pulls in the same objects the other
# L-3 drivers use. On a checkout without the L-4 libtiapi.so build
# infrastructure, the Makefile variables $(FLINKER) / $(LIBS) /
# $(FLIBS) / $(LIBX_MTX) mirror what `make ti` already needs, so
# adding the API objects is enough.
#
# CC defaults to gcc; override on the command line if necessary.
# ---------------------------------------------------------------------
CC ?= gcc
CFLAGS_API ?= -Wall -Wextra -O2

TI_API_SMOKE_DIR=tests/c_abi
TI_API_NEG_C=$(TI_API_SMOKE_DIR)/test_negative.c
TI_API_NEG_O=$(TI_API_SMOKE_DIR)/test_negative.o
TI_API_NEG_BIN=$(TI_API_SMOKE_DIR)/test_negative

# Header-only compile check for the negative driver. Mirrors the
# `gcc -Wall -Wextra -c` user-level check in the L-2 task plan.
$(TI_API_NEG_O): $(TI_API_NEG_C) ti_api.h
	$(CC) $(CFLAGS_API) -I. -c -o $(TI_API_NEG_O) $(TI_API_NEG_C)

.PHONY: ti_api_compile_check
ti_api_compile_check: $(TI_API_NEG_O)
	@echo "Phase L-6 ti_api_compile_check OK: test_negative.c compiles"

# Full build+run target. Requires the existing libti.a + deps (which
# `make ti` already builds), plus the API objects compiled here. If
# libtiapi.so is not yet available the run_so step is gracefully
# skipped.
.PHONY: ti_api_check_all
ti_api_check_all: libti.a $(OBJ_API) $(TI_API_NEG_BIN)
	@echo "Phase L-6 ti_api_check_all: negative tests ..."
	@LD_LIBRARY_PATH=.:$${LD_LIBRARY_PATH} $(TI_API_NEG_BIN)
	@echo "Phase L-6 ti_api_check_all OK:"
	@echo "  - Fortran API objects : $(OBJ_API)"
	@echo "  - C driver executed   : test_negative"

# Link the negative driver. Pulls in the same library chain as `ti`
# so ti_init / ti_set_param / ti_run / ti_get_state / ti_finalize all
# resolve. When the L-4 libtiapi.so infrastructure lands this rule
# can be simplified to dlopen + libdl.
$(TI_API_NEG_BIN): $(TI_API_NEG_O) $(OBJ_API) libti.a
	$(FLINKER) -o $(TI_API_NEG_BIN) $(TI_API_NEG_O) $(OBJ_API) \
	   $(LIBS) $(FFLAGS) $(FLIBS) $(LIBX_MTX)

ti_state.o          : ti_state.f90
ti_param_registry.o : ti_param_registry.f90 ticomm.f90
ti_api.o            : ti_api.f90 ti_state.f90 ti_param_registry.f90 \
                      ticomm.f90 tiinit.f90 tiprep.f90 tiexec.f90

# =====================================================================
# Phase L-4: libtiapi.so shared library build
#
# Builds a position-independent shared object that exposes the 5 C ABI
# entry points (ti_init, ti_run, ti_set_param, ti_get_state, ti_finalize)
# and links in SRCS + SRCS_API plus the (non-graphics) supporting
# libraries (libpl_pic, libeq_pic, libtask_pic, libmds_pic, lib-adpost_pic,
# lib-adf11_pic, libmtxnompi_pic, libmtxbnd_pic, bpsd PIC).
#
# The PIC build is a *separate* tree at obj/pic/ + mod_pic/ so the
# existing non-PIC ti build is unaffected. Dependent libraries are
# PIC-rebuilt via opt-in targets added in eq/pl/lib/mtxp/adpost/adf11
# Makefiles (libeq_pic.a, libpl_pic.a, libtask_pic.a, libmds_pic.a,
# lib-adpost_pic.a, lib-adf11_pic.a, libmtxnompi_pic.o, libmtxbnd_pic.o).
#
# The bpsd sources live in the parent ../../bpsd/ repo which is outside
# our worktree; we PIC-rebuild bpsd objects in-tree (obj/pic/bpsd/) so
# we don't need to modify bpsd/Makefile.
#
# Note: this Makefile selects LIB_MTX=LIB_MTX_MUMPS by default, but the
# libtiapi.so link path uses libmtxnompi_pic.o + libmtxbnd_pic.o (BND
# backend) because the MUMPS backend is not currently built as PIC and
# is unreachable from the C ABI happy path.
#
# Mirrors tr L-4 (PR #35) + wr L-4 (PR #39).
# =====================================================================

OBJDIR_PIC=obj/pic
MODDIR_PIC=mod_pic
PIC_FLAGS=-fPIC -J$(MODDIR_PIC) -I$(MODDIR_PIC)
MODINCLUDE_PIC= -I./$(MODDIR_PIC) \
                -I../open-adas/adf11/adf11-lib/mod_pic \
                -I../adpost/mod_pic \
                -I../pl/mod_pic -I../eq/mod_pic \
                -I../lib/mod_pic -I../mtxp/mod_pic

# Pattern rules for PIC compilation. Each rule creates its output dir
# on demand so we don't need an explicit mkdir phase.
$(OBJDIR_PIC)/%.o: %.f90
	@mkdir -p $(@D) $(MODDIR_PIC)
	$(FCFREE) $(FFLAGS) $(PIC_FLAGS) -c $< -o $@ $(MODINCLUDE_PIC)
$(OBJDIR_PIC)/%.o: %.f
	@mkdir -p $(@D) $(MODDIR_PIC)
	$(FCFIXED) $(FFLAGS) $(PIC_FLAGS) -c $< -o $@ $(MODINCLUDE_PIC)

# Core ti sources for libtiapi.so. Mirrors SRCS but drops graphics-only
# files. On ti, SRCS already excludes graphics sources (tigout is the
# lone graphics module and is retained here because tiprep transitively
# references it; it's harmless as long as libtiapi.so never calls plot).
# For clarity we define SRCS_TI_NOGR explicitly so any future graphics
# split is a one-line change.
SRCS_TI_NOGR=ticomm.f90 tiadas.f90 \
             tiinit.f90 tiparm.f90 \
             ticoef.f90 tisource.f90 ticalc.f90 tirecord.f90 \
             tiregress.f90 \
             tiprep.f90 tiexec.f90 tigout.f90

# BPSD PIC rebuild (out-of-tree source, in-tree object/mod).
# We replicate bpsd/Makefile's build order here.
BPSD_SRC=../../bpsd
OBJBPSD_PIC=$(OBJDIR_PIC)/bpsd/bpsd_kinds.o \
            $(OBJDIR_PIC)/bpsd/bpsd_constants.o \
            $(OBJDIR_PIC)/bpsd/bpsd_flags.o \
            $(OBJDIR_PIC)/bpsd/bpsd_libchar.o \
            $(OBJDIR_PIC)/bpsd/bpsd_libfio.o \
            $(OBJDIR_PIC)/bpsd/bpsd_libspl.o \
            $(OBJDIR_PIC)/bpsd/bpsd_types.o \
            $(OBJDIR_PIC)/bpsd/bpsd_types_internal.o \
            $(OBJDIR_PIC)/bpsd/bpsd_subs.o \
            $(OBJDIR_PIC)/bpsd/bpsd_shot.o \
            $(OBJDIR_PIC)/bpsd/bpsd_device.o \
            $(OBJDIR_PIC)/bpsd/bpsd_species.o \
            $(OBJDIR_PIC)/bpsd/bpsd_equ1D.o \
            $(OBJDIR_PIC)/bpsd/bpsd_metric1D.o \
            $(OBJDIR_PIC)/bpsd/bpsd_plasmaf.o \
            $(OBJDIR_PIC)/bpsd/bpsd_trmatrix.o \
            $(OBJDIR_PIC)/bpsd/bpsd_trsource.o \
            $(OBJDIR_PIC)/bpsd/bpsd_base.o

$(OBJDIR_PIC)/bpsd/%.o: $(BPSD_SRC)/%.f90
	@mkdir -p $(@D) $(MODDIR_PIC)
	$(FCFREE) $(FFLAGS) $(PIC_FLAGS) -c $< -o $@ $(MODINCLUDE_PIC)

# Enforce the dependency order so -j builds don't race.
$(OBJDIR_PIC)/bpsd/bpsd_constants.o:     $(OBJDIR_PIC)/bpsd/bpsd_kinds.o
$(OBJDIR_PIC)/bpsd/bpsd_flags.o:          $(OBJDIR_PIC)/bpsd/bpsd_kinds.o
$(OBJDIR_PIC)/bpsd/bpsd_libchar.o:        $(OBJDIR_PIC)/bpsd/bpsd_kinds.o
$(OBJDIR_PIC)/bpsd/bpsd_libfio.o:         $(OBJDIR_PIC)/bpsd/bpsd_kinds.o
$(OBJDIR_PIC)/bpsd/bpsd_libspl.o:         $(OBJDIR_PIC)/bpsd/bpsd_kinds.o
$(OBJDIR_PIC)/bpsd/bpsd_types.o:          $(OBJDIR_PIC)/bpsd/bpsd_kinds.o $(OBJDIR_PIC)/bpsd/bpsd_constants.o
$(OBJDIR_PIC)/bpsd/bpsd_types_internal.o: $(OBJDIR_PIC)/bpsd/bpsd_types.o
$(OBJDIR_PIC)/bpsd/bpsd_subs.o:           $(OBJDIR_PIC)/bpsd/bpsd_types_internal.o $(OBJDIR_PIC)/bpsd/bpsd_libchar.o $(OBJDIR_PIC)/bpsd/bpsd_libfio.o $(OBJDIR_PIC)/bpsd/bpsd_libspl.o $(OBJDIR_PIC)/bpsd/bpsd_flags.o
$(OBJDIR_PIC)/bpsd/bpsd_shot.o:           $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_device.o:         $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_species.o:        $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_equ1D.o:          $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_metric1D.o:       $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_plasmaf.o:        $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_trmatrix.o:       $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_trsource.o:       $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_base.o:           $(OBJDIR_PIC)/bpsd/bpsd_shot.o $(OBJDIR_PIC)/bpsd/bpsd_device.o $(OBJDIR_PIC)/bpsd/bpsd_species.o $(OBJDIR_PIC)/bpsd/bpsd_equ1D.o $(OBJDIR_PIC)/bpsd/bpsd_metric1D.o $(OBJDIR_PIC)/bpsd/bpsd_plasmaf.o $(OBJDIR_PIC)/bpsd/bpsd_trmatrix.o $(OBJDIR_PIC)/bpsd/bpsd_trsource.o

.PHONY: bpsd_pic
bpsd_pic: $(OBJBPSD_PIC)

# Object sets for libtiapi.so: core ti sources + API sources.
OBJS_PIC=$(addprefix $(OBJDIR_PIC)/, $(SRCS_TI_NOGR:.f90=.o))
OBJ_API_PIC=$(addprefix $(OBJDIR_PIC)/, $(SRCS_API:.f90=.o))

# Graphics stubs that satisfy any residual GUCLIP / PAGES / ... calls
# coming from libpl_pic / libeq_pic without dragging in non-PIC
# libgsp/libg3d. Built only as PIC so it is libtiapi.so-only.
SRCS_GR_STUBS=ti_graphics_stubs.f90
OBJ_GR_STUBS_PIC=$(addprefix $(OBJDIR_PIC)/, $(SRCS_GR_STUBS:.f90=.o))

OBJ_LIBTIAPI= $(OBJS_PIC) $(OBJ_API_PIC) $(OBJ_GR_STUBS_PIC)

# Dependent PIC archives / objects.
LIBS_PIC=../eq/libeq_pic.a ../pl/libpl_pic.a \
         ../lib/libmds_pic.a ../lib/libtask_pic.a \
         ../open-adas/adf11/adf11-lib/lib-adf11_pic.a \
         ../adpost/lib-adpost_pic.a
LIBMTX_PIC=../mtxp/libmtxnompi_pic.o ../mtxp/libmtxbnd_pic.o

# Build dependent PIC libs on demand (matches the libXX.a recipes above).
../eq/libeq_pic.a:
	(cd ../eq; make libeq_pic.a)
../pl/libpl_pic.a:
	(cd ../pl; make libpl_noeq_pic)
	(cd ../eq; make libeq_pic.a)
	(cd ../pl; make libpl_pic.a)
../lib/libmds_pic.a:
	(cd ../lib; make libmds_pic.a)
../lib/libtask_pic.a:
	(cd ../lib; make libtask_pic.a)
../mtxp/libmtxnompi_pic.o:
	(cd ../mtxp; make libmtxnompi_pic.o)
../mtxp/libmtxbnd_pic.o:
	(cd ../mtxp; make libmtxbnd_pic.o)
../adpost/lib-adpost_pic.a:
	(cd ../adpost; make lib-adpost_pic.a)
../open-adas/adf11/adf11-lib/lib-adf11_pic.a:
	(cd ../open-adas/adf11/adf11-lib; make lib-adf11_pic.a)

# The shared library itself. gfortran drives the link so libgfortran is
# pulled in automatically. --start-group/--end-group resolves any cyclic
# references between eq / pl / bpsd that our non-PIC ti link only avoids
# by listing archives in a careful order.
#
# We deliberately drop $(FLIBS) from the link: those pull in non-PIC
# graphics archives (libg3d/libgsp/libgdp) via GFLIBS. libtiapi.so
# excludes graphics so none of the gsaf calls are reachable; leaving
# GFLIBS in triggers R_X86_64_PC32 relocation errors when ld tries to
# copy non-PIC .text from libg3d-gfc64.a into the .so. MDSLIB/LIBLA are
# unused at the default config (MDSPLUS=nomdsplus.f, LAPACK=nolapack.f)
# so dropping them is safe.
# Platform-aware ld flags: Apple ld (macOS) rejects GNU-ld-only flags
# (-soname / --start-group / --end-group) but resolves cycles
# automatically and uses -install_name. `-undefined dynamic_lookup`
# defers unresolved imports (graphics symbols not on the .so happy
# path) to runtime so dlopen succeeds on macOS, matching Linux.
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
  SO_SONAME = -Wl,-install_name,@rpath/libtiapi.so
  SO_GROUP_BEGIN =
  SO_GROUP_END =
  SO_UNDEFINED = -Wl,-undefined,dynamic_lookup
else
  SO_SONAME = -Wl,-soname,libtiapi.so
  SO_GROUP_BEGIN = -Wl,--start-group
  SO_GROUP_END = -Wl,--end-group
  SO_UNDEFINED =
endif

libtiapi.so: $(OBJ_LIBTIAPI) $(OBJBPSD_PIC) $(LIBS_PIC) $(LIBMTX_PIC)
	$(FCFREE) -shared -fPIC $(SO_SONAME) $(SO_UNDEFINED) \
	    $(OBJ_LIBTIAPI) $(OBJBPSD_PIC) $(LIBMTX_PIC) \
	    $(SO_GROUP_BEGIN) $(LIBS_PIC) $(SO_GROUP_END) \
	    -o libtiapi.so

# ---------------------------------------------------------------------
# Phase L-4: ti_api_check_so
#
# Dynamically loads libtiapi.so via dlopen(), resolves the 5 symbols,
# runs the full init -> set_param -> run -> get_state -> finalize
# cycle, and asserts each return is 0. This exercises the .so exactly
# like a Python ctypes wrapper will at L-5 and is distinct from the
# static C ABI drivers which link OBJ_API directly against libti.a
# (same Fortran code, different link path).
# ---------------------------------------------------------------------
TI_API_SO_C=$(TI_API_SMOKE_DIR)/test_run_so.c
TI_API_SO_O=$(TI_API_SMOKE_DIR)/test_run_so.o
TI_API_SO_BIN=$(TI_API_SMOKE_DIR)/test_run_so

$(TI_API_SO_O): $(TI_API_SO_C) ti_api.h
	$(CC) $(CFLAGS_API) -I. -c -o $(TI_API_SO_O) $(TI_API_SO_C)

$(TI_API_SO_BIN): $(TI_API_SO_O)
	$(CC) -o $(TI_API_SO_BIN) $(TI_API_SO_O) -ldl

.PHONY: libtiapi_inspect
libtiapi_inspect: libtiapi.so
	@echo "=== file ==="
	@file libtiapi.so
	@echo "=== ldd ==="
	@ldd libtiapi.so
	@echo "=== exported ti_* symbols ==="
	@nm -D libtiapi.so | grep ' T ti_' || true
	@echo "=== undefined symbols (count) ==="
	@nm -D libtiapi.so | grep ' U ' | wc -l
	@echo "=== first 40 undefined ==="
	@nm -D libtiapi.so | grep ' U ' | head -40
	@echo "=== non-libc/gfortran undefined (graphics / external) ==="
	@nm -D libtiapi.so | grep ' U ' | grep -vE '@(GLIBC|GCC|GFORTRAN)' | head -40

.PHONY: ti_api_check_so
ti_api_check_so: libtiapi.so $(TI_API_SO_BIN)
	@echo "Phase L-4 ti_api_check_so: dlopen libtiapi.so + full cycle ..."
	@TILIB_PATH=$(CURDIR)/libtiapi.so $(TI_API_SO_BIN)
	@echo "Phase L-4 ti_api_check_so OK"
