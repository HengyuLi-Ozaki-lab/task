# Build the TASK library manual — hybrid portal + per-module layout.
#
# Usage:
#   make              # builds portal + all modules (en + ja)
#   make portal       # portal only (en + ja)
#   make portal-en    # portal English only
#   make tr           # tr module (en + ja)
#   make tr-en        # tr English only
#   make modules      # all 7 modules (en + ja)
#   make clean

SPHINXBUILD   ?= sphinx-build
BUILDDIR      ?= _build

# `-W --keep-going` is enforced by CI; for local dev, override with
#   make SPHINXOPTS=""
# to tolerate warnings.
SPHINXOPTS    ?= -W --keep-going

MODULES := tr eq ti fp wr wrx tot
LANGS   := en ja

# ── Top-level targets ────────────────────────────────────────────────
.PHONY: all html portal modules clean help \
        $(MODULES) \
        portal-en portal-ja \
        $(foreach m,$(MODULES),$(m)-en $(m)-ja) \
        pdf pdf-portal-en pdf-portal-ja \
        $(foreach m,$(MODULES),pdf-$(m)-en pdf-$(m)-ja) \
        linkcheck-portal-en linkcheck-portal-ja \
        $(foreach m,$(MODULES),linkcheck-$(m)-en linkcheck-$(m)-ja) \
        livehtml-portal-en livehtml-portal-ja

all: html
html: portal modules

# ── Portal (must be built first — modules depend on its objects.inv) ─
portal: portal-en portal-ja

portal-en:
	$(SPHINXBUILD) -b html $(SPHINXOPTS) portal/en $(BUILDDIR)/portal/en

portal-ja:
	$(SPHINXBUILD) -b html $(SPHINXOPTS) portal/ja $(BUILDDIR)/portal/ja

# ── Modules ──────────────────────────────────────────────────────────
modules: $(MODULES)

# Per-module convenience targets (both languages).
$(MODULES): %: %-en %-ja

# Generic rules for module-en / module-ja.
$(foreach m,$(MODULES),$(m)-en): %-en: portal-en
	$(SPHINXBUILD) -b html $(SPHINXOPTS) modules/$*/en $(BUILDDIR)/$*/en

$(foreach m,$(MODULES),$(m)-ja): %-ja: portal-ja
	$(SPHINXBUILD) -b html $(SPHINXOPTS) modules/$*/ja $(BUILDDIR)/$*/ja

# ── PDF via xelatex ─────────────────────────────────────────────────
# Three xelatex passes: (1) aux, (2) toc & longtable widths, (3) settle
# TOC page numbers.  See conf_common.py:latex_elements for the preamble.
pdf: pdf-portal-en pdf-portal-ja $(foreach m,$(MODULES),pdf-$(m)-en pdf-$(m)-ja)

# PDF builds tolerate warnings: --keep-going continues past warnings,
# and we drop -W (warnings-as-errors) for LaTeX output specifically
# because notebook output and autodoc routinely trigger benign warnings.
PDFOPTS = --keep-going

define PDF_RULE
pdf-$(1)-$(2):
	$$(SPHINXBUILD) -b latex $$(PDFOPTS) $(3) $$(BUILDDIR)/latex-$(1)-$(2)
	# Three xelatex passes (TOC + cross-refs + settle). The leading `-`
	# tells Make to ignore xelatex's exit code, because xelatex returns
	# non-zero on benign warnings (undefined refs in pass 1, font glyph
	# misses, etc.). We do NOT pipe to /dev/null so real errors stay
	# visible. The final .xdv-existence check below distinguishes real
	# failures from benign warnings: if xelatex couldn't write a .xdv,
	# we fail fast with a clear error instead of letting xdvipdfmx emit
	# a confusing "no such file" message.
	-cd $$(BUILDDIR)/latex-$(1)-$(2) && xelatex -no-pdf -interaction=nonstopmode *.tex > xelatex-pass1.log 2>&1
	-cd $$(BUILDDIR)/latex-$(1)-$(2) && xelatex -no-pdf -interaction=nonstopmode *.tex > xelatex-pass2.log 2>&1
	-cd $$(BUILDDIR)/latex-$(1)-$(2) && xelatex -no-pdf -interaction=nonstopmode *.tex > xelatex-pass3.log 2>&1
	@ls $$(BUILDDIR)/latex-$(1)-$(2)/*.xdv >/dev/null 2>&1 || (echo "ERROR: xelatex produced no .xdv for $(1)-$(2). Check $$(BUILDDIR)/latex-$(1)-$(2)/xelatex-pass3.log" && exit 1)
	cd $$(BUILDDIR)/latex-$(1)-$(2) && xdvipdfmx *.xdv
	@echo "PDF ready: $$(BUILDDIR)/latex-$(1)-$(2)/"
endef

$(eval $(call PDF_RULE,portal,en,portal/en))
$(eval $(call PDF_RULE,portal,ja,portal/ja))
$(foreach m,$(MODULES),$(eval $(call PDF_RULE,$(m),en,modules/$(m)/en)))
$(foreach m,$(MODULES),$(eval $(call PDF_RULE,$(m),ja,modules/$(m)/ja)))

# ── Linkcheck ────────────────────────────────────────────────────────
linkcheck-portal-en:
	$(SPHINXBUILD) -b linkcheck $(SPHINXOPTS) portal/en $(BUILDDIR)/linkcheck-portal-en

linkcheck-portal-ja:
	$(SPHINXBUILD) -b linkcheck $(SPHINXOPTS) portal/ja $(BUILDDIR)/linkcheck-portal-ja

$(foreach m,$(MODULES),linkcheck-$(m)-en): linkcheck-%-en:
	$(SPHINXBUILD) -b linkcheck $(SPHINXOPTS) modules/$*/en $(BUILDDIR)/linkcheck-$*-en

$(foreach m,$(MODULES),linkcheck-$(m)-ja): linkcheck-%-ja:
	$(SPHINXBUILD) -b linkcheck $(SPHINXOPTS) modules/$*/ja $(BUILDDIR)/linkcheck-$*-ja

# ── Live development ─────────────────────────────────────────────────
livehtml-portal-en:
	sphinx-autobuild -b html $(SPHINXOPTS) portal/en $(BUILDDIR)/portal/en

livehtml-portal-ja:
	sphinx-autobuild -b html $(SPHINXOPTS) portal/ja $(BUILDDIR)/portal/ja

# ── Clean ────────────────────────────────────────────────────────────
clean:
	rm -rf $(BUILDDIR)

# ── Help ─────────────────────────────────────────────────────────────
help:
	@echo "Targets:"
	@echo "  all (default)     build portal + all modules (HTML, en+ja)"
	@echo "  portal            portal only (en+ja)"
	@echo "  portal-en/ja      portal single language"
	@echo "  modules           all 7 modules (en+ja)"
	@echo "  tr / eq / ...     single module (en+ja)"
	@echo "  tr-en / tr-ja     single module, single language"
	@echo "  pdf               all PDFs (portal + modules, en+ja)"
	@echo "  pdf-tr-en         single module PDF"
	@echo "  linkcheck-*       link validation"
	@echo "  livehtml-portal-en/ja  live dev server (requires sphinx-autobuild)"
	@echo "  clean             remove _build/"
	@echo ""
	@echo "Override SPHINXOPTS='' to tolerate warnings during local dev."
