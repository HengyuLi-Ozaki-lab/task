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
SRCS =  equtpxssl.f90 equpfds.f90 equsub.f90 equinit.f90 \
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
# Every PIC object of SRCS uses equcomm's modules.
$(OBJS_PIC) $(OBJDIR_PIC)/equmain.o $(OBJDIR_PIC)/equ_static_stubs.o: | libs_pic_prereq $(OBJC_PIC)

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
