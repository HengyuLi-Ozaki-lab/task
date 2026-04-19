### $Id: Makefile,v 1.69 2012/07/25 07:53:52 nuga Exp $ ###
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

FFLAGS=$(OFLAGS)
#FFLAGS=$(DFLAGS)

.SUFFIXES:
.SUFFIXES: .f90 .mod .o .a

OBJDIR=./obj

MODINCLUDE= -I./$(MOD)  -I../ob/$(MOD) \
            -I../dp/$(MOD) -I../pl/$(MOD) -I../eq/$(MOD) \
            -I../lib/$(MOD) -I../mtxp/$(MOD) \
            -I../../bpsd/$(MOD)

${OBJDIR}/%.o:%.f
	$(FCFIXED) $(FFLAGS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)
${OBJDIR}/%.o:%.f90
	$(FCFREE) $(FFLAGS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)

# --- core (Fokker-Planck physics + I/O, no graphics, no menu) ---
# Ordering: fpregress is placed BEFORE fploop because fploop USEs the
# fpregress module. The OBJDIR (non-PIC) intra-fp dep declarations at
# the bottom of this Makefile fix this for `fploop.o : fpregress.o`,
# but the OBJDIR_PIC pattern rule does not pick up those declarations.
# Building in source-order is the simplest portable fix.
SRCS_CORE = fpcomm.f90 fpinit.f90 fpparm.f90 \
	fpmpi.f90 fpbroadcast.f90 fplib.f90 \
	fpexec.f90 fpreadeg.f90 fpsave.f90 fpwrite.f90 \
	fpcaltp.f90 fpcalte.f90 fpcaldeff.f90 fpcalchieff.f90 \
	fpwmin.f90 fpwrin.f90 fpcalwm.f90 fpcalwr.f90 fpcalw.f90 \
	fpcalcn.f90 fpcalcnr.f90 fpcalc.f90 fpnfrr.f90 fpnflg.f90  \
	cdbmfp.f90 \
	fpcalr.f90 fpreadsv.f90 fpoutdata.f90 fpcoef.f90 fpcale.f90 \
	fpbounce.f90 fpcalj.f90 fpdisrupt.f90 \
	fpregress.f90 \
	fpprep.f90 fploop.f90 \
	fpfile.f90

# --- graphics (plotting, contour, plot-oriented file output) ---
SRCS_GRAPHICS = fpcont.f90 fpfout.f90 fpgsub.f90 fpgout.f90

# --- interactive menu driver (depends on graphics) ---
SRCS_MENU = fpmenu.f90

# --- final SRCS for the existing `fp` binary (unchanged behaviour) ---
SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)

# --- C ABI sources (Phase L-2+). Compiled via the fp_api_check target only;
#     NOT part of $(SRCS) and NOT linked into libfp.a / fp. The full
#     libfpapi.so build arrives in Phase L-4.
SRCS_API = fp_state.f90 fp_param_registry.f90 fp_api.f90

OBJS=$(addprefix $(OBJDIR)/, $(SRCS:.f90=.o))
OBJ_API=$(addprefix $(OBJDIR)/, $(SRCS_API:.f90=.o))

LIBS = libfp.a ../ob/libob.a ../pl/libpl.a ../eq/libeq.a ../dp/libdp.a \
       ../lib/libgrf.a ../lib/libtask.a ../../bpsd/libbpsd.a

all: libs fp


../../bpsd/libbpsd.a:
	(cd ../../bpsd; make libbpsd.a)
../lib/libtask.a:
	(cd ../lib; make libtask.a)
../lib/libgrf.a:
	(cd ../lib; make libgrf.a)
../pl/libpl.a:
	(cd ../pl; make libpl.a)
../eq/libeq.a:
	(cd ../eq; make libeq.a)
../dp/libdp.a:
	(cd ../dp; make libdp.a)
../ob/libob.a:
	(cd ../ob; make libob.a)

libfp.a: $(OBJS)
	$(LD) $(LDFLAGS) libfp.a $(OBJS)

libs:
	(cd ../../bpsd; make libbpsd.a)
	(cd ../lib; make libtask.a)
	(cd ../lib; make libgrf.a)
	(cd ../mtxp; make)
	(cd ../pl; make libpl.a)
	(cd ../eq; make libeq.a)
	(cd ../dp; make libdp.a)
	(cd ../ob; make libob.a)

fp : $(LIB_MTX) $(LIBS) $(OBJDIR)/fpmain.o
	$(FLINKER) $(OBJDIR)/fpmain.o $(LIBS) -o $@ $(FFLAGS) $(FLIBS) $(LIBX_MTX)

# ---------------------------------------------------------------------
# Phase L-3: C ABI check
#
# `make fp_api_check` builds the API objects (fp_state.o,
# fp_param_registry.o, fp_api.o) and three C drivers under tests/c_abi/:
#
#   test_smoke.c  -> sanity: every entry point returns FP_OK after
#                    fp_init -> fp_run(0) -> ... -> fp_finalize.
#   test_param.c  -> fp_set_param("NRMAX", 20) and friends, then
#                    verify state.nrmax == 20 via fp_get_state.
#   test_run.c    -> fp_run(1) on a tiny grid, verify TIMEFP > 0.
#
# At L-3 the API objects need the full FPCOMM stack (fp_loop, fp_prep,
# fp_init in fpinit, plus pl/eq/ob/dp/lib/mtxp/bpsd) to link, so we
# pull in $(LIBS) and $(LIB_MTX) just like the fp binary itself. The
# fp binary remains byte-for-byte identical (libfp.a does not include
# the SRCS_API objects).
#
# CC defaults to gcc; override on the command line if necessary
# (e.g. `make fp_api_check CC=clang`).
# ---------------------------------------------------------------------
CC ?= gcc
CFLAGS_API ?= -Wall -Wextra -O2

FP_API_SMOKE_DIR=tests/c_abi
FP_API_SMOKE_C=$(FP_API_SMOKE_DIR)/test_smoke.c
FP_API_SMOKE_O=$(FP_API_SMOKE_DIR)/test_smoke.o
FP_API_SMOKE_BIN=$(FP_API_SMOKE_DIR)/test_smoke

FP_API_PARAM_C=$(FP_API_SMOKE_DIR)/test_param.c
FP_API_PARAM_O=$(FP_API_SMOKE_DIR)/test_param.o
FP_API_PARAM_BIN=$(FP_API_SMOKE_DIR)/test_param

FP_API_RUN_C=$(FP_API_SMOKE_DIR)/test_run.c
FP_API_RUN_O=$(FP_API_SMOKE_DIR)/test_run.o
FP_API_RUN_BIN=$(FP_API_SMOKE_DIR)/test_run

# Header-only C compiles.
$(FP_API_SMOKE_O): $(FP_API_SMOKE_C) fp_api.h
	$(CC) $(CFLAGS_API) -I. -c -o $(FP_API_SMOKE_O) $(FP_API_SMOKE_C)
$(FP_API_PARAM_O): $(FP_API_PARAM_C) fp_api.h
	$(CC) $(CFLAGS_API) -I. -c -o $(FP_API_PARAM_O) $(FP_API_PARAM_C)
$(FP_API_RUN_O): $(FP_API_RUN_C) fp_api.h
	$(CC) $(CFLAGS_API) -I. -c -o $(FP_API_RUN_O) $(FP_API_RUN_C)

# Link the C drivers against the API objects + libfp + libpl/libeq/...
# (full FPCOMM stack). This proves the BIND(C) names emitted by
# fp_api.f90 match the prototypes in fp_api.h and exercises fp_prep /
# fp_loop end-to-end.
$(FP_API_SMOKE_BIN): $(FP_API_SMOKE_O) $(OBJ_API) $(LIB_MTX) $(LIBS)
	$(FLINKER) -o $(FP_API_SMOKE_BIN) $(FP_API_SMOKE_O) $(OBJ_API) \
	    $(LIBS) $(FFLAGS) $(FLIBS) $(LIBX_MTX)
$(FP_API_PARAM_BIN): $(FP_API_PARAM_O) $(OBJ_API) $(LIB_MTX) $(LIBS)
	$(FLINKER) -o $(FP_API_PARAM_BIN) $(FP_API_PARAM_O) $(OBJ_API) \
	    $(LIBS) $(FFLAGS) $(FLIBS) $(LIBX_MTX)
$(FP_API_RUN_BIN): $(FP_API_RUN_O) $(OBJ_API) $(LIB_MTX) $(LIBS)
	$(FLINKER) -o $(FP_API_RUN_BIN) $(FP_API_RUN_O) $(OBJ_API) \
	    $(LIBS) $(FFLAGS) $(FLIBS) $(LIBX_MTX)

.PHONY: fp_api_check
fp_api_check: $(OBJ_API) $(FP_API_SMOKE_BIN) $(FP_API_PARAM_BIN) $(FP_API_RUN_BIN)
	@echo "Phase L-3 fp_api_check: running smoke ..."
	@$(FP_API_SMOKE_BIN)
	@echo "Phase L-3 fp_api_check: running test_param ..."
	@$(FP_API_PARAM_BIN)
	@echo "Phase L-3 fp_api_check: running test_run ..."
	@$(FP_API_RUN_BIN)
	@echo "Phase L-3 fp_api_check OK:"
	@echo "  - Fortran API objects compiled: $(OBJ_API)"
	@echo "  - C drivers built + run        : $(FP_API_SMOKE_BIN) $(FP_API_PARAM_BIN) $(FP_API_RUN_BIN)"

clean :
	-rm -f core a.out $(OBJDIR)/*.o *.a ./#* ./*~ ./mod/*.mod
	-rm -f $(FP_API_SMOKE_O) $(FP_API_SMOKE_BIN)
	-rm -f $(FP_API_PARAM_O) $(FP_API_PARAM_BIN)
	-rm -f $(FP_API_RUN_O) $(FP_API_RUN_BIN)
	-rm -f $(FP_API_SO_O) $(FP_API_SO_BIN)
	-rm -f $(FP_API_NEG_O) $(FP_API_NEG_BIN)

veryclean: clean
	-rm -f fp

clean_pic:
	-rm -rf $(OBJDIR_PIC) $(MODDIR_PIC) libfpapi.so
	-rm -f $(FP_API_SO_O) $(FP_API_SO_BIN)
	-rm -f $(FP_API_NEG_O) $(FP_API_NEG_BIN)

# =====================================================================
# Phase L-4: libfpapi.so shared library build
#
# Builds a position-independent shared object that exposes the 5 C ABI
# entry points (fp_init, fp_run, fp_set_param, fp_get_state, fp_finalize)
# and links in SRCS_CORE + SRCS_API. The PIC build is a *separate* tree
# at obj/pic/ + mod_pic/ so the existing non-PIC fp build is unaffected.
#
# Dependent libraries are PIC-rebuilt via opt-in targets added in
# eq/pl/lib/mtxp/dp/ob Makefiles (libeq_pic.a, libpl_pic.a,
# libtask_pic.a, libdp_pic.a, libob_pic.a, libmtxnompi_pic.o,
# libmtxbnd_pic.o).
#
# The bpsd sources live in the parent ../../bpsd/ repo which is outside
# our worktree; we PIC-rebuild bpsd objects in-tree (obj/pic/bpsd/) so
# we don't need to modify bpsd/Makefile.
# =====================================================================

OBJDIR_PIC=obj/pic
MODDIR_PIC=mod_pic
PIC_FLAGS=-fPIC -J$(MODDIR_PIC) -I$(MODDIR_PIC)
MODINCLUDE_PIC= -I./$(MODDIR_PIC) -I../ob/mod_pic -I../dp/mod_pic \
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

# BPSD PIC rebuild (out-of-tree source, in-tree object/mod).
# We replicate bpsd/Makefile's build order here. The order matches the
# non-PIC libbpsd.a layout (see bpsd/Makefile's SRCS).
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
$(OBJDIR_PIC)/bpsd/bpsd_constants.o:       $(OBJDIR_PIC)/bpsd/bpsd_kinds.o
$(OBJDIR_PIC)/bpsd/bpsd_flags.o:            $(OBJDIR_PIC)/bpsd/bpsd_kinds.o
$(OBJDIR_PIC)/bpsd/bpsd_libchar.o:          $(OBJDIR_PIC)/bpsd/bpsd_kinds.o
$(OBJDIR_PIC)/bpsd/bpsd_libfio.o:           $(OBJDIR_PIC)/bpsd/bpsd_kinds.o
$(OBJDIR_PIC)/bpsd/bpsd_libspl.o:           $(OBJDIR_PIC)/bpsd/bpsd_kinds.o
$(OBJDIR_PIC)/bpsd/bpsd_types.o:            $(OBJDIR_PIC)/bpsd/bpsd_kinds.o $(OBJDIR_PIC)/bpsd/bpsd_constants.o
$(OBJDIR_PIC)/bpsd/bpsd_types_internal.o:   $(OBJDIR_PIC)/bpsd/bpsd_types.o
$(OBJDIR_PIC)/bpsd/bpsd_subs.o:             $(OBJDIR_PIC)/bpsd/bpsd_types_internal.o $(OBJDIR_PIC)/bpsd/bpsd_libchar.o $(OBJDIR_PIC)/bpsd/bpsd_libfio.o $(OBJDIR_PIC)/bpsd/bpsd_libspl.o $(OBJDIR_PIC)/bpsd/bpsd_flags.o
$(OBJDIR_PIC)/bpsd/bpsd_shot.o:             $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_device.o:           $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_species.o:          $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_equ1D.o:            $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_metric1D.o:         $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_plasmaf.o:          $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_trmatrix.o:         $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_trsource.o:         $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_base.o:             $(OBJDIR_PIC)/bpsd/bpsd_shot.o $(OBJDIR_PIC)/bpsd/bpsd_device.o $(OBJDIR_PIC)/bpsd/bpsd_species.o $(OBJDIR_PIC)/bpsd/bpsd_equ1D.o $(OBJDIR_PIC)/bpsd/bpsd_metric1D.o $(OBJDIR_PIC)/bpsd/bpsd_plasmaf.o $(OBJDIR_PIC)/bpsd/bpsd_trmatrix.o $(OBJDIR_PIC)/bpsd/bpsd_trsource.o

.PHONY: bpsd_pic
bpsd_pic: $(OBJBPSD_PIC)

# Object sets for libfpapi.so. Mirror SRCS_CORE + SRCS_API; SRCS_GRAPHICS
# and SRCS_MENU are NOT included.
OBJ_CORE_PIC = $(addprefix $(OBJDIR_PIC)/, $(SRCS_CORE:.f90=.o))
OBJ_API_PIC  = $(addprefix $(OBJDIR_PIC)/, $(SRCS_API:.f90=.o))

# Graphics stubs that satisfy GUTIME / PAGES / GRD1D / etc. without
# dragging in non-PIC libgsp/libg3d. Built only as PIC so it is
# libfpapi.so-only.
SRCS_GR_STUBS    = fp_graphics_stubs.f90
OBJ_GR_STUBS_PIC = $(addprefix $(OBJDIR_PIC)/, $(SRCS_GR_STUBS:.f90=.o))

OBJ_LIBFPAPI = $(OBJ_CORE_PIC) $(OBJ_API_PIC) $(OBJ_GR_STUBS_PIC)

# Dependent PIC archives / objects (order: bpsd -> lib (mds/task) ->
# mtxp -> pl -> eq -> dp -> ob, same as the non-PIC fp link order).
LIBS_PIC = ../ob/libob_pic.a ../dp/libdp_pic.a \
           ../eq/libeq_pic.a ../pl/libpl_pic.a \
           ../lib/libtask_pic.a
LIBMTX_PIC = ../mtxp/libmtxnompi_pic.o ../mtxp/libmtxbnd_pic.o

# Build dependent PIC libs on demand. Note pl/Makefile splits PIC build
# into two phony targets so we can interleave the eq build to break the
# pl <-> eq circular dependency (mirrors the non-PIC libpl.a recipe).
../eq/libeq_pic.a:
	(cd ../pl; make libpl_noeq_pic)
	(cd ../eq; make libeq_pic.a)
../pl/libpl_pic.a: ../eq/libeq_pic.a
	(cd ../pl; make libpl_pic.a)
../lib/libtask_pic.a:
	(cd ../lib; make libtask_pic.a)
../dp/libdp_pic.a: ../pl/libpl_pic.a ../eq/libeq_pic.a
	(cd ../dp; make libdp_pic.a)
../ob/libob_pic.a: ../pl/libpl_pic.a ../eq/libeq_pic.a
	(cd ../ob; make libob_pic.a)
../mtxp/libmtxnompi_pic.o:
	(cd ../mtxp; make libmtxnompi_pic.o)
../mtxp/libmtxbnd_pic.o:
	(cd ../mtxp; make libmtxbnd_pic.o)

.PHONY: libs_pic
libs_pic: ../lib/libtask_pic.a ../mtxp/libmtxnompi_pic.o \
          ../mtxp/libmtxbnd_pic.o $(OBJBPSD_PIC) \
          ../eq/libeq_pic.a ../pl/libpl_pic.a \
          ../dp/libdp_pic.a ../ob/libob_pic.a

# The shared library itself. gfortran drives the link so libgfortran is
# pulled in automatically. --start-group/--end-group resolves the cyclic
# references between eq / pl / bpsd / dp / ob.
#
# We deliberately drop $(FLIBS) from the link: those resolve to
# `-lg3d-gfc64 -lgsp-gfc64 -lgdp-gfc64 -lX11`, none of which are PIC,
# so keeping them would trigger R_X86_64_PC32 relocation errors when ld
# tries to copy non-PIC .text into the .so. libfpapi.so excludes
# SRCS_GRAPHICS / SRCS_MENU so none of the gsaf calls are reachable;
# the small set of GUTIME/PAGES/GRD1D refs left in core code are
# satisfied by fp_graphics_stubs.f90.
libfpapi.so: $(OBJ_LIBFPAPI) $(OBJBPSD_PIC) $(LIBS_PIC) $(LIBMTX_PIC)
	$(FCFREE) -shared -fPIC -Wl,-soname,libfpapi.so \
	    $(OBJ_LIBFPAPI) $(OBJBPSD_PIC) $(LIBMTX_PIC) \
	    -Wl,--start-group $(LIBS_PIC) -Wl,--end-group \
	    -o libfpapi.so

# ---------------------------------------------------------------------
# Phase L-4: fp_api_check_so
#
# Dynamically loads libfpapi.so via dlopen(), resolves the 5 symbols,
# runs the full init -> set_param -> run -> get_state -> finalize
# cycle, and asserts each return is FP_OK. This exercises the .so
# exactly like a Python ctypes wrapper will at L-5.
# ---------------------------------------------------------------------
FP_API_SO_C=$(FP_API_SMOKE_DIR)/test_run_so.c
FP_API_SO_O=$(FP_API_SMOKE_DIR)/test_run_so.o
FP_API_SO_BIN=$(FP_API_SMOKE_DIR)/test_run_so

$(FP_API_SO_O): $(FP_API_SO_C) fp_api.h
	$(CC) $(CFLAGS_API) -I. -c -o $(FP_API_SO_O) $(FP_API_SO_C)

$(FP_API_SO_BIN): $(FP_API_SO_O)
	$(CC) -o $(FP_API_SO_BIN) $(FP_API_SO_O) -ldl

.PHONY: libfpapi_inspect
libfpapi_inspect: libfpapi.so
	@echo "=== file ==="
	@file libfpapi.so
	@echo "=== ldd ==="
	@ldd libfpapi.so
	@echo "=== exported fp_* symbols ==="
	@nm -D libfpapi.so | grep ' T fp_' || true
	@echo "=== undefined symbols (count) ==="
	@nm -D libfpapi.so | grep ' U ' | wc -l
	@echo "=== first 40 undefined ==="
	@nm -D libfpapi.so | grep ' U ' | head -40

.PHONY: fp_api_check_so
fp_api_check_so: libfpapi.so $(FP_API_SO_BIN)
	@echo "Phase L-4 fp_api_check_so: dlopen libfpapi.so + full cycle ..."
	@FPLIB_PATH=$(CURDIR)/libfpapi.so $(FP_API_SO_BIN)
	@echo "Phase L-4 fp_api_check_so OK"

# ---------------------------------------------------------------------
# Phase L-6: Layer 2 (C ABI) test suite
#
# Builds + runs the full C ABI test set in one shot so CI (via
# test_run/run_tests.sh) can invoke a single target. Consists of:
#
#   test_smoke     - 5 entry points return FP_OK          (L-3)
#   test_param     - set_param + get_state dispatch       (L-3)
#   test_run       - fp_run advances TIMEFP               (L-3)
#   test_run_so    - dlopen libfpapi.so + full cycle      (L-4)
#   test_negative  - rejection contracts (L-6, new)
#
# The L-3 trio links against OBJ_API + libfp.a; the dlopen driver uses
# libdl and loads libfpapi.so at runtime. The negative driver shares
# the L-3 link path.
# ---------------------------------------------------------------------
FP_API_NEG_C=$(FP_API_SMOKE_DIR)/test_negative.c
FP_API_NEG_O=$(FP_API_SMOKE_DIR)/test_negative.o
FP_API_NEG_BIN=$(FP_API_SMOKE_DIR)/test_negative

$(FP_API_NEG_O): $(FP_API_NEG_C) fp_api.h
	$(CC) $(CFLAGS_API) -I. -c -o $(FP_API_NEG_O) $(FP_API_NEG_C)

$(FP_API_NEG_BIN): $(FP_API_NEG_O) $(OBJ_API) $(LIB_MTX) $(LIBS)
	$(FLINKER) -o $(FP_API_NEG_BIN) $(FP_API_NEG_O) $(OBJ_API) \
	    $(LIBS) $(FFLAGS) $(FLIBS) $(LIBX_MTX)

.PHONY: fp_api_check_all
fp_api_check_all: fp_api_check fp_api_check_so $(FP_API_NEG_BIN)
	@echo "Phase L-6 fp_api_check_all: running negative tests ..."
	@$(FP_API_NEG_BIN)
	@echo "Phase L-6 fp_api_check_all OK: smoke/param/run/run_so/negative"

# Phase L-3 C ABI sources. fp_param_registry depends on fpcomm; fp_api
# depends on fpcomm + fpinit + fpprep + fploop + plinit + equnit +
# obinit + libmtx in addition to fp_state and fp_param_registry.
$(OBJDIR)/fp_state.o           : fp_state.f90
$(OBJDIR)/fp_param_registry.o  : fp_param_registry.f90 fpcomm.f90 \
                                 $(OBJDIR)/fpcomm.o
$(OBJDIR)/fp_api.o             : fp_api.f90 fp_state.f90 fp_param_registry.f90 \
                                 fpcomm.f90 fpinit.f90 fpprep.f90 fploop.f90 \
                                 $(OBJDIR)/fp_state.o $(OBJDIR)/fp_param_registry.o \
                                 $(OBJDIR)/fpcomm.o $(OBJDIR)/fpinit.o \
                                 $(OBJDIR)/fpprep.o $(OBJDIR)/fploop.o

$(OBJDIR)/fpcomm.o : fpcomm.f90 ../pl/plcomm.f90 ../dp/dpcomm.f90
$(OBJDIR)/fpmain.o : fpinit.f90 fpparm.f90 fpmain.f90 fpcomm.f90
$(OBJDIR)/fpmenu.o : fpwrin.f90 fpgout.f90 fpfout.f90 fploop.f90 \
                     fpprep.f90 fpparm.f90 fpfile.f90 fpmenu.f90 fpcomm.f90
$(OBJDIR)/fpinit.o : fpinit.f90 fpcomm.f90
$(OBJDIR)/fpparm.o : fpparm.f90 fpcomm.f90
$(OBJDIR)/fpprep.o : fpoutdata.f90 fpcale.f90 fpbounce.f90 fpnfrr.f90 \
                     fpwmin.f90 fpwrin.f90 fpsave.f90 fpcalw.f90 \
                     fpbroadcast.f90 fpparm.f90 fpcoef.f90 fpdisrupt.f90 \
                     fpreadeg.f90 fpprep.f90 fpcomm.f90
$(OBJDIR)/fploop.o : fpoutdata.f90 fpnfrr.f90 fpsave.f90 fpexec.f90 \
                     fpprep.f90 fpcoef.f90 fpdisrupt.f90 fpreadeg.f90 \
                     fploop.f90 fpcomm.f90 fpoutdata.f90 fplib.f90 \
                     fpregress.f90 $(OBJDIR)/fpregress.o
$(OBJDIR)/fpregress.o : fpregress.f90 fpcomm.f90
$(OBJDIR)/fpexec.o : fpexec.f90 fpcomm.f90
$(OBJDIR)/fpdrexec.o : fpdrexec.f90 fpcomm.f90
$(OBJDIR)/fpbroadcast.o : fpbroadcast.f90 fpcomm.f90
$(OBJDIR)/fpcoef.o : fpreadsv.f90 fpreadeg.f90 fpcalr.f90 fpnfrr.f90 \
                     fpcalwm.f90 fpcalwr.f90 fpcalw.f90 fpcalc.f90 \
                     fpcoef.f90 fplib.f90 fpcomm.f90
$(OBJDIR)/fpcalc.o : fpcalcnr.f90 fpcalcn.f90 fpcalc.f90 fpcomm.f90
$(OBJDIR)/fpcalcn.o : fpcalcn.f90 fpcomm.f90
$(OBJDIR)/fpcalcnr.o : fpcoef.f90 fpcalcnr.f90 fpcomm.f90
$(OBJDIR)/fpcalj.o : fpcalj.f90 fpcomm.f90
$(OBJDIR)/fpcalw.o : fpcalw.f90 fpcalwr.f90 fpcalwm.f90 fpcomm.f90
$(OBJDIR)/fpcalwr.o : fpwrin.f90 fpcalwr.f90 fpcomm.f90
$(OBJDIR)/fpcalwm.o : fpwmin.f90 fpcalwm.f90 fpcomm.f90
$(OBJDIR)/fpcont.o : fpcont.f90 fpcomm.f90
$(OBJDIR)/fpfout.o : fpfout.f90 fpcomm.f90
$(OBJDIR)/fpgout.o : fpfout.f90 fpcont.f90 fpgsub.f90 fpgout.f90 fpcomm.f90
$(OBJDIR)/fpfile.o : fplib.f90 fpprep.f90 fpreadeg.f90 fpreadsv.f90 \
                     fpfile.f90 fpnfrr.f90 fpcomm.f90
$(OBJDIR)/fpsave.o : fpexec.f90 fpreadeg.f90 fpsave.f90 fpcomm.f90
$(OBJDIR)/fpwrin.o : fpwrin.f90 fpcomm.f90
$(OBJDIR)/fpwmin.o : fpwrin.f90 fpcomm.f90
$(OBJDIR)/fpnfrr.o : fpparm.f90 fpinit.f90 fpnfrr.f90 fplib.f90 fpcomm.f90
$(OBJDIR)/fpbounce.o : fpparm.f90 fpinit.f90 fpbounce.f90 fpcomm.f90
$(OBJDIR)/fpcale.o: fpcale.f90 fpmpi.f90
$(OBJDIR)/fpdisrupt.o: fpcale.f90 fpcoef.f90 fpdisrupt.f90 fpcomm.f90
$(OBJDIR)/fpcalr.o: fpcalr.f90 fpcomm.f90
$(OBJDIR)/fpreadeg.o: fpreadeg.f90 fpcomm.f90
$(OBJDIR)/fpreadsv.o: fpreadsv.f90 fpcomm.f90
$(OBJDIR)/fpoutdata.o: fpoutdata.f90 fpreadeg.f90 fplib.f90 fpnfrr.f90 \
                       fpcomm.f90
$(OBJDIR)/fpcaltp.o: fpcaltp.f90 fpcomm.f90
$(OBJDIR)/fpcaldeff.o: fpcaldeff.f90 fpcomm.f90
$(OBJDIR)/fplib.o: fplib.f90 fpcomm.f90
$(OBJDIR)/fpmpi.o: fpmpi.f90 fpcomm.f90
$(OBJDIR)/fpcdbbm.o : fpcdbm.f90 fpcomm.f90
$(OBJDIR)/fpwrite.o : fpwrite.f90 fpcomm.f90

$(OBJDIR)/fowmain.o : fowmain.f90 fowmenu.f90 fowcomm.f90 fpinit.f90 \
                      fpcomm.f90 fpwrite.f90
$(OBJDIR)/fowmenu.o : fowmain.f90 fowcomm.f90 fowprep.f90 foworbit.f90 \
                      fpprep.f90 fpcomm.f90 fpwrite.f90
$(OBJDIR)/fowcomm.o : fowcomm.f90
$(OBJDIR)/fowlib.o  : fowlib.f90 fowcomm.f90
$(OBJDIR)/fowexec.o : fowexec.f90 fowcomm.f90 fpcomm.f90
$(OBJDIR)/fowprep.o : fowprep.f90 fowcomm.f90 fowdistribution.f90 \
                      foworbit.f90 fowdistribution.f90 fowobclassify.f90
$(OBJDIR)/foworbit.o: foworbit.f90 fowcomm.f90 fpcomm.f90 \
                      ../ob/obcomm.f90 ../ob/obcalc.f90 ../ob/obprep.f90 \
                      ../ob/obinit.f90 ../ob/obparm.f90
$(OBJDIR)/fowdistribution.o : fowdistribution.f90 foworbit.f90 fowcomm.f90 \
                              fpcomm.f90
$(OBJDIR)/fowcoef.o : fowdistribution.f90 fowcoef.f90 fowcomm.f90 \
                      fpcomm.f90 fowobclassify.f90
$(OBJDIR)/fowsource.o : fowsource.f90 fowcomm.f90 fpcomm.f90 fowprep.f90 \
                        foworbit.f90 fowdistribution.f90
$(OBJDIR)/fowloop.o : fowexec.f90 fowdistribution.f90 fowcoef.f90 \
                      fowsource.f90 fowcomm.f90 fpcomm.f90 fowprep.f90 \
                      fpwrite.f90 fowevalNC.f90 fowobclassify.f90
$(OBJDIR)/fowevalNC.o : fowevalNC.f90 fowcomm.f90 fpcomm.f90 fpwrite.f90 \
                        fowcoef.f90 fowexec.f90 foworbit.f90
$(OBJDIR)/fowobclassify.o : fowobclassify.f90 fowcomm.f90 fpcomm.f90 \
                            fpwrite.f90
