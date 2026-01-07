# Configuration file for the Sphinx documentation builder.
#
# TASK/TXnew Documentation

# -- Project information -----------------------------------------------------
project = 'TASK/TXnew'
copyright = '2024, BPSI - Kyoto University'
author = 'BPSI Development Team'
version = '5.5'
release = '5.5.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.mathjax',
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Fallback theme if sphinx_rtd_theme is not installed
try:
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
except ImportError:
    html_theme = 'alabaster'

# -- Options for LaTeX output ------------------------------------------------
latex_elements = {
    'papersize': 'a4paper',
    'pointsize': '11pt',
    'preamble': r'''
\usepackage{amsmath}
\usepackage{amssymb}
''',
}

latex_documents = [
    ('index', 'txnew.tex', 'TASK/TXnew Documentation',
     'BPSI Development Team', 'manual'),
]

# -- Options for manual page output ------------------------------------------
man_pages = [
    ('index', 'txnew', 'TASK/TXnew Documentation',
     [author], 1)
]

# -- Math configuration ------------------------------------------------------
mathjax3_config = {
    'tex': {
        'macros': {
            'RR': r'\mathbb{R}',
            'pd': [r'\frac{\partial #1}{\partial #2}', 2],
        }
    }
}

# -- Language ----------------------------------------------------------------
language = 'ja'
