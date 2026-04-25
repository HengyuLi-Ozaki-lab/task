"""Sphinx configuration for the Portal (English) — landing page."""
from __future__ import annotations

import os
import sys

# Import shared config.
sys.path.insert(0, os.path.abspath("../.."))
from conf_common import *  # noqa: E402,F401,F403

language = "en"
project = "TASK Plasma Library"
html_title = "TASK Plasma Library — Portal"
html_short_title = "TASK Portal (EN)"

# Intersphinx: add module docs so portal cards can link into them.
# All 7 modules are listed; the local .inv path gates resolution at
# build time. Modules whose HTML hasn't been built yet will simply
# skip (a soft warning).
intersphinx_mapping = {  # noqa: F405
    **intersphinx_mapping,  # noqa: F405
    **{
        mod: (
            f"https://task-docs.example.com/{mod}/en/",
            (os.path.abspath(f"../../_build/{mod}/en/objects.inv"), None),
        )
        for mod in ("tr", "eq", "ti", "fp", "wr", "wrx", "tot")
    },
}

latex_documents = [("index", "task_portal.tex", project, author, "manual")]  # noqa: F405
