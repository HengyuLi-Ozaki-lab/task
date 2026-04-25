# TASK library manual — Sphinx sources

This directory hosts the Sphinx sources for the TASK library user manual.
It supersedes the standalone LaTeX document at
`docs/manual/task-library-manual.tex`, which is now frozen at its 2026-04
snapshot.

## Layout (hybrid portal + per-module)

```
docs/sphinx/
├── README.md                 (this file)
├── requirements.txt          pip install target
├── Makefile                  builds portal + per-module docs
├── conf_common.py            shared Sphinx config (extensions, autodoc, MyST)
│
├── portal/                   landing page — links to all modules
│   ├── en/
│   │   ├── conf.py
│   │   ├── index.md          card-based module directory
│   │   └── common/architecture.md
│   └── ja/ (same shape)
│
├── modules/                  per-module independent Sphinx projects
│   ├── tr/{en,ja}/           (full chapter)
│   ├── eq/{en,ja}/           (full chapter)
│   ├── ti/{en,ja}/           (placeholder)
│   ├── fp/{en,ja}/           (placeholder)
│   ├── wr/{en,ja}/           (placeholder)
│   ├── wrx/{en,ja}/          (placeholder)
│   └── tot/{en,ja}/          (placeholder)
│
├── shared/notebooks/         executable notebooks included from both trees
└── _build/                   build output (portal/{en,ja}, tr/{en,ja}, …)
```

Each module directory (`modules/<mod>/{en,ja}/`) is a self-contained
Sphinx project with its own `conf.py` that imports `conf_common.py`.
The portal links to modules via `sphinx-design` cards and `intersphinx`.

## i18n strategy

We use the **parallel-tree** strategy: each `en/` and `ja/` directory is
an independent Sphinx project. Source prose is edited in both languages
directly — no `.po` files involved. The trade-off is that we rely on
reviewer discipline to keep the trees in sync; PRs that modify one tree
should state whether the other tree needs a matching update.

`sphinx-intl` is present in `requirements.txt` so we can migrate to a
gettext-driven flow later without re-architecting the project.

## Building

### HTML

```bash
pip install -r docs/sphinx/requirements.txt     # one-time
cd docs/sphinx
make              # builds portal + all modules (en + ja)
make portal       # portal only
make tr           # tr module (en + ja)
make tr-en        # tr English only
make modules      # all 7 modules
make clean
```

### PDF (xelatex)

```bash
cd docs/sphinx
make pdf-portal-en    # -> _build/latex-portal-en/
make pdf-tr-en        # -> _build/latex-tr-en/
make pdf              # all PDFs
```

The PDF path needs xelatex plus Japanese CJK fonts. On Debian / Ubuntu:

```bash
sudo apt-get install texlive-xetex texlive-lang-japanese \
    texlive-latex-extra fonts-noto-cjk fonts-dejavu-core
```

On TinyTeX (the minimal distribution some users have):

```bash
tlmgr install cmap fontspec polyglossia collection-latexrecommended \
              fncychap tabulary titlesec varwidth wrapfig \
              capt-of eqparbox needspace
```

`fontspec` is **not** bundled with `collection-latexrecommended`, even
though Sphinx's xelatex output requires it via our
`latex_elements["fontpkg"]` block — list it explicitly here.

The default `SPHINXOPTS = -W --keep-going` treats warnings as errors
(CI-strict). Override for local dev:

```bash
make SPHINXOPTS="" tr-en
```

## Build order

The portal is built first because per-module Sphinx projects reference
the portal's `objects.inv` via `intersphinx` for cross-references to
`common/architecture`. The Makefile encodes this dependency:

```
make tr-en  →  depends on portal-en  →  then builds modules/tr/en
```

## Notebooks

Jupyter notebooks live under `docs/sphinx/shared/notebooks/` and are
symlinked into both language trees of each module. They are included via
`myst-nb` with `nb_execution_mode = "off"` — we commit pre-executed
output cells for determinism. To re-execute before committing:

```bash
jupyter nbconvert --to notebook --execute --inplace <notebook>.ipynb
```

## Contribution contract

1. A code change that adds/removes a public Python-wrapper symbol
   should include a matching documentation update in at least `en/`
   (JA counterpart can trail by one PR if time-constrained, but must be
   linked via an issue).
2. A change to a Fortran API signature must update the relevant chapter
   in both trees (or leave a TODO pointing at the issue).
3. `make` must pass cleanly (`-W`) before merge. CI enforces this.
