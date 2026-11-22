### Makefile

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

FFLAGS = $(OFLAGS)
#FFLAGS = $(DFLAGS) -Wuninitialized

OBJDIR=./obj

${OBJDIR}/%.o:%.f
	$(FCFIXED) $(FFLAGS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)
${OBJDIR}/%.o:%.f90
	$(FCFREE) $(FFLAGS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)

MODINCLUDE= -I./$(MOD) -I../pl/$(MOD) \
            -I../lib/$(MOD) -I../mtxp/$(MOD) \
            -I../../bpsd/$(MOD)


SRCC =  equcomm.f90
SRCS =  equ_status.f90 equtpxssl.f90 equpfds.f90 equsub.f90 equinit.f90 \
        equfct.f90 equinp.f90 equset.f90 \
        equpl.f90 equtrn.f90 equfile.f90 \
	equgout.f90 equunit.f90 \
	equtrpl.f90 equtrset.f90 equtradv.f90 equtrunit.f90 \
        equ_eqdsk.f90 equ_convert.f90 \
        equmenu.f90

OBJC=$(addprefix $(OBJDIR)/, $(SRCC:.f90=.o))
OBJS=$(addprefix $(OBJDIR)/, $(SRCS:.f90=.o))

LIBS = libequ.a ../pl/libpl.a ../eq/libeq.a ../lib/libtask.a ../lib/libgrf.a ../../bpsd/libbpsd.a

all: libs equ

libequ.a: $(OBJS)
	$(LD) $(LDFLAGS) libequ.a $(OBJS)

libs:
	(cd ../../bpsd; make libbpsd.a)
	(cd ../lib/; make libtask.a)
	(cd ../lib/; make libgrf.a)
	(cd ../mtxp/; make)
	(cd ../pl/; make libpl.a)

equ: $(OBJC) libs libequ.a $(OBJDIR)/equmain.o
	$(FLINKER) $(OBJDIR)/equmain.o $(OBJC) $(LIBS) -o $@ $(FFLAGS) $(FLIBS) $(LIBX_MTX)
clean:
	-rm -f ./#* ./*~ $(OBJDIR)/*.o $(MOD)/*.mod core *.a
veryclean: clean
	-rm -f equ
#
$(OBJDIR)/equmain.o : equmain.f90
$(OBJDIR)/equmenu.o : equmenu.f90
$(OBJDIR)/equunit.o : equunit.f90 equcomm.f90
$(OBJDIR)/equfct.o : equfct.f90 equcomm.f90
$(OBJDIR)/equinp.o : equinp.f90 equcomm.f90
$(OBJDIR)/equinit.o : equinit.f90 equcomm.f90
$(OBJDIR)/equset.o : equset.f90 equcomm.f90
$(OBJDIR)/equsub.o : equsub.f90 equcomm.f90
$(OBJDIR)/equpfds.o : equpfds.f90 equcomm.f90
$(OBJDIR)/equintf.o : equintf.f90 equcomm.f90
$(OBJDIR)/equgout.o : equgout.f90 equcomm.f90
$(OBJDIR)/equfile.o : equgout.f90 equcomm.f90
$(OBJDIR)/equtrunit.o : equtrunit.f90  
$(OBJDIR)/equtrpl.o : equtrpl.f90  
$(OBJDIR)/equtrset.o : equtrset.f90  
$(OBJDIR)/equtradv.o : equtradv.f90 equtrpl.f90
$(OBJDIR)/equtrsvq.o : equtrsvq.f90 equtrpl.f90
$(OBJDIR)/equtpxssl.o : equtpxssl.f90
$(OBJDIR)/equ_eqdsk.o : equ_eqdsk.f90 equcomm.f90
$(OBJDIR)/equ_convert.o : equ_convert.f90 equcomm.f90
# equ_status_mod (the failure record of the library interface) is used
# by the routines that used to STOP and by their callers.
$(OBJDIR)/equ_status.o : equ_status.f90
$(OBJDIR)/equsub.o $(OBJDIR)/equinit.o $(OBJDIR)/equset.o $(OBJDIR)/equfct.o : $(OBJDIR)/equ_status.o

# =====================================================================
# Library interface (libequapi.so) and the program without graphics
# (equ_nogr). Additions only: the targets above are unchanged.
# Design: docs/superpowers/specs/2026-11-22-equ-library-design.md.
#
# The PIC tree (obj/pic, mod_pic) mirrors eq/Makefile's; bpsd is
# rebuilt as PIC here, as eq and tr do (make -C equ bpsd_pic).
# =====================================================================
OBJDIR_PIC=obj/pic
MODDIR_PIC=mod_pic
PIC_FLAGS=-fPIC -J$(MODDIR_PIC) -I$(MODDIR_PIC)
MODINCLUDE_PIC=-I$(MODDIR_PIC) -I../../bpsd/$(MOD) -I../mtxp/mod_pic \
               -I../pl/mod_pic -I../lib/mod_pic

OBJC_PIC=$(addprefix $(OBJDIR_PIC)/, $(SRCC:.f90=.o))
OBJS_PIC=$(addprefix $(OBJDIR_PIC)/, $(SRCS:.f90=.o))

$(OBJDIR_PIC)/%.o: %.f90
	@mkdir -p $(OBJDIR_PIC) $(MODDIR_PIC)
	$(FCFREE) $(FFLAGS) $(PIC_FLAGS) -c $< -o $@ $(MODINCLUDE_PIC)

# --- bpsd in-tree PIC rebuild (as eq/Makefile and tr/Makefile) ---
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

# --- The sibling PIC libraries, built on demand (as eq/Makefile) ---
LIBS_PIC=../pl/libpl_pic.a ../lib/libtask_pic.a
LIBMTX_PIC=../mtxp/libmtxnompi_pic.o ../mtxp/libmtxbnd_pic.o

../pl/libpl_pic.a:
	(cd ../pl; $(MAKE) libpl_pic.a)
../lib/libtask_pic.a:
	(cd ../lib; $(MAKE) libtask_pic.a)
../lib/libgrf_pic.a:
	(cd ../lib; $(MAKE) libgrf_pic.a)
../mtxp/libmtxnompi_pic.o:
	(cd ../mtxp; $(MAKE) libmtxnompi_pic.o)
../mtxp/libmtxbnd_pic.o:
	(cd ../mtxp; $(MAKE) libmtxbnd_pic.o)
../../bpsd/libbpsd.a:
	(cd ../../bpsd; $(MAKE) libbpsd.a)

../lib/libgrf_pic.a: ../lib/libtask_pic.a
../mtxp/libmtxnompi_pic.o: ../lib/libtask_pic.a
../mtxp/libmtxbnd_pic.o: ../mtxp/libmtxnompi_pic.o

# Order-only, so `make -C equ libequapi.so` and `make -C equ equ_nogr`
# work from a clean tree (#230): bpsd's static build fills
# ../../bpsd/mod, which pl's PIC build reads; libgrf_pic.a is here for
# its .mod (equgout.f90 and equ_convert.f90 use libgrf).
.PHONY: libs_pic_prereq
libs_pic_prereq: ../../bpsd/libbpsd.a \
                 ../lib/libtask_pic.a ../lib/libgrf_pic.a \
                 ../mtxp/libmtxnompi_pic.o ../mtxp/libmtxbnd_pic.o \
                 $(OBJBPSD_PIC) ../pl/libpl_pic.a

$(OBJBPSD_PIC): | ../lib/libtask_pic.a
../pl/libpl_pic.a: | ../../bpsd/libbpsd.a ../lib/libtask_pic.a \
                     ../lib/libgrf_pic.a ../mtxp/libmtxbnd_pic.o
$(OBJC_PIC): | libs_pic_prereq
# Every PIC object of SRCS uses equcomm's modules, and those that
# used to STOP use equ_status_mod.
$(OBJDIR_PIC)/equsub.o $(OBJDIR_PIC)/equinit.o $(OBJDIR_PIC)/equset.o $(OBJDIR_PIC)/equfct.o: $(OBJDIR_PIC)/equ_status.o
# equcomm.o is a real prerequisite: an edit of equcomm.f90 rebuilds them.
$(OBJS_PIC) $(OBJDIR_PIC)/equmain.o $(OBJDIR_PIC)/equ_static_stubs.o: $(OBJC_PIC) | libs_pic_prereq

# --- equ_nogr: the program without graphics -------------------------
# The same main program, menu and solver as `equ`, linked from the PIC
# objects with equ_static_stubs.f90 in place of GSAF. Its only use is
# the comparison of the library's G-EQDSK with the program's
# (python/equlib/tests/test_program_parity.py). Its GSOPEN reads
# nothing, so its standard input starts with the menu commands.
equ_nogr: $(OBJC_PIC) $(OBJS_PIC) $(OBJDIR_PIC)/equmain.o \
          $(OBJDIR_PIC)/equ_static_stubs.o $(OBJBPSD_PIC) \
          ../lib/libgrf_pic.a $(LIBS_PIC) $(LIBMTX_PIC)
	$(FCFREE) $(FFLAGS) -o $@ $(OBJDIR_PIC)/equmain.o $(OBJC_PIC) \
	    $(OBJS_PIC) $(OBJDIR_PIC)/equ_static_stubs.o $(OBJBPSD_PIC) \
	    ../lib/libgrf_pic.a $(LIBS_PIC) $(LIBMTX_PIC)

clean_pic:
	-rm -rf $(OBJDIR_PIC) $(MODDIR_PIC) equ_nogr libequapi.so

# --- libequapi.so: the library interface ----------------------------
# The library's objects are SRCS without the graphics and the menu:
# equgout.f90 and equ_convert.f90 draw, equmenu.f90 is the menu, and
# equunit.f90 uses eqgout_mod; equ_api.f90 calls the solver's routines
# itself. No GSAF symbol is referenced by what remains, so no graphics
# stubs are linked (equ_static_stubs.f90 is for equ_nogr only).
SRCS_CORE=$(filter-out equgout.f90 equmenu.f90 equ_convert.f90 equunit.f90,$(SRCS))
OBJS_PIC_CORE=$(addprefix $(OBJDIR_PIC)/, $(SRCS_CORE:.f90=.o))
SRCS_API=equ_state.f90 equ_param_registry.f90 equ_image.f90 equ_api.f90
OBJ_API_PIC=$(addprefix $(OBJDIR_PIC)/, $(SRCS_API:.f90=.o))
OBJ_LIBEQUAPI=$(OBJC_PIC) $(OBJS_PIC_CORE) $(OBJ_API_PIC)

$(OBJ_API_PIC): $(OBJC_PIC) $(OBJS_PIC_CORE) | libs_pic_prereq
$(OBJDIR_PIC)/equ_param_registry.o: $(OBJDIR_PIC)/equ_state.o
$(OBJDIR_PIC)/equ_image.o: $(OBJDIR_PIC)/equ_param_registry.o
$(OBJDIR_PIC)/equ_api.o: $(OBJDIR_PIC)/equ_state.o $(OBJDIR_PIC)/equ_param_registry.o \
                         $(OBJDIR_PIC)/equ_image.o

# eq/Makefile's link line: gfortran drives it (libgfortran comes along),
# FLIBS is left out (no graphics), Apple ld resolves the cycles itself.
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
  SO_SONAME = -Wl,-install_name,@rpath/libequapi.so
  SO_GROUP_BEGIN =
  SO_GROUP_END =
  SO_UNDEFINED = -Wl,-undefined,dynamic_lookup
else
  SO_SONAME = -Wl,-soname,libequapi.so
  SO_GROUP_BEGIN = -Wl,--start-group
  SO_GROUP_END = -Wl,--end-group
  SO_UNDEFINED = -Wl,--unresolved-symbols=ignore-all
endif

libequapi.so: $(OBJ_LIBEQUAPI) $(OBJBPSD_PIC) $(LIBS_PIC) $(LIBMTX_PIC)
	$(FCFREE) -shared -fPIC $(SO_SONAME) $(SO_UNDEFINED) \
	    $(OBJ_LIBEQUAPI) $(OBJBPSD_PIC) $(LIBMTX_PIC) \
	    $(SO_GROUP_BEGIN) $(LIBS_PIC) $(SO_GROUP_END) \
	    -o libequapi.so

.PHONY: libequapi_inspect
libequapi_inspect: libequapi.so
	@echo "=== exported equ_* symbols ==="
	@nm -g libequapi.so | grep ' T _*equ_[a-z_]*$$' || true
	@echo "=== undefined, other than libc and libgfortran ==="
	@nm -u libequapi.so | grep -vE '@|^_*_gfortran|^_*(str|mem|f|mal|cal|fre|abort|exit|printf|sprintf|snprintf)' | head -40 || true

# --- C-level checks through dlopen (as eq_api_check_so) -------------
CC ?= gcc
CFLAGS_API ?= -Wall -Wextra -O2
EQU_API_DIR = tests/c_abi

$(EQU_API_DIR)/test_run_so: $(EQU_API_DIR)/test_run_so.c equ_api.h
	$(CC) $(CFLAGS_API) -I. -o $@ $(EQU_API_DIR)/test_run_so.c -ldl
$(EQU_API_DIR)/test_negative: $(EQU_API_DIR)/test_negative.c equ_api.h
	$(CC) $(CFLAGS_API) -I. -o $@ $(EQU_API_DIR)/test_negative.c -ldl

# test_run_so copies the QUEST example into its own working directory.
.PHONY: equ_api_check_so equ_api_check_all
equ_api_check_so: libequapi.so $(EQU_API_DIR)/test_run_so
	@rm -rf $(EQU_API_DIR)/run && mkdir -p $(EQU_API_DIR)/run
	@cd $(EQU_API_DIR)/run && EQULIB_PATH=$(CURDIR)/libequapi.so \
	    EQU_EXAMPLE_DIR=$(CURDIR)/example ../test_run_so > run.log 2>&1 \
	    || { tail -40 run.log; exit 1; }
	@grep '^OK:' $(EQU_API_DIR)/run/run.log
	@echo "equ_api_check_so OK"

equ_api_check_all: equ_api_check_so $(EQU_API_DIR)/test_negative
	@cd $(EQU_API_DIR)/run && EQULIB_PATH=$(CURDIR)/libequapi.so \
	    ../test_negative > negative.log 2>&1 || { tail -20 negative.log; exit 1; }
	@grep '^OK:' $(EQU_API_DIR)/run/negative.log
	@echo "equ_api_check_all OK"
