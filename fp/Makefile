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
SRCS_CORE = fpcomm.f90 fpinit.f90 fpparm.f90 \
	fpmpi.f90 fpbroadcast.f90 fplib.f90 \
	fpexec.f90 fpreadeg.f90 fpsave.f90 fpwrite.f90 \
	fpcaltp.f90 fpcalte.f90 fpcaldeff.f90 fpcalchieff.f90 \
	fpwmin.f90 fpwrin.f90 fpcalwm.f90 fpcalwr.f90 fpcalw.f90 \
	fpcalcn.f90 fpcalcnr.f90 fpcalc.f90 fpnfrr.f90 fpnflg.f90  \
	cdbmfp.f90 \
	fpcalr.f90 fpreadsv.f90 fpoutdata.f90 fpcoef.f90 fpcale.f90 \
	fpbounce.f90 fpcalj.f90 fpdisrupt.f90 fpprep.f90 fploop.f90 \
	fpfile.f90 \
	fpregress.f90

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

veryclean: clean
	-rm -f fp

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
