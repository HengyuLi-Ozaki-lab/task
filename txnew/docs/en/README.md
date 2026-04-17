# TXnew Documentation (English)

Sphinx documentation for the TASK/TXnew module.

## Requirements

- Python 3.6 or later
- Sphinx 4.0 or later
- sphinx-rtd-theme

## Installation

### Ubuntu/Debian

```bash
sudo apt-get install python3-sphinx python3-sphinx-rtd-theme
```

### pip

```bash
pip install sphinx sphinx-rtd-theme
```

## Build

### HTML

```bash
cd /home/k-yoshimi/program/task/txnew/docs/en
make html
```

Output will be in `_build/html/`.

Open in browser:
```bash
firefox _build/html/index.html
```

### PDF (via LaTeX)

```bash
make latexpdf
```

Requires LaTeX environment:
```bash
sudo apt-get install texlive-latex-recommended texlive-fonts-recommended texlive-latex-extra latexmk
```

## File Structure

```
docs/en/
├── conf.py              # Sphinx configuration
├── index.rst            # Main index
├── overview.rst         # Overview
├── installation.rst     # Installation guide
├── input_parameters.rst # Input parameters
├── output_variables.rst # Output variables
├── equations.rst        # Basic equations
├── examples.rst         # Usage examples
├── references.rst       # References
├── Makefile             # Build Makefile
└── README.md            # This file
```

## Development Mode

Live reload while editing:

```bash
pip install sphinx-autobuild
make livehtml
```

Preview at http://localhost:8000
