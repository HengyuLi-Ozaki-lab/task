# Configuration file for the Sphinx documentation builder.

# -- Project information -----------------------------------------------------
project = 'TASK/TXnew'
copyright = '2024, BPSI Research Group, Kyoto University'
author = 'A. Fukuyama et al.'
version = '5.5'
release = '5.5'

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
     'BPSI Research Group', 'manual'),
]

# -- Extension configuration -------------------------------------------------
mathjax3_config = {
    'tex': {
        'macros': {
            'RR': r'\mathbb{R}',
        }
    }
}

# Language
language = 'en'
