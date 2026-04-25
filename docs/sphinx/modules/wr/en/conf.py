"""Sphinx configuration for modules/wr (English)."""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.abspath("../../.."))
from conf_common import *  # noqa: E402,F401,F403

language = "en"
project = "TASK/WR — Wave Ray"
html_title = "TASK/WR — Wave Ray"
html_short_title = "WR (EN)"

intersphinx_mapping = {
    **intersphinx_mapping,
    "portal": (
        "https://task-docs.example.com/portal/en/",
        (os.path.abspath("../../../_build/portal/en/objects.inv"), None),
    ),
}
latex_documents = [("index", "task_wr_manual.tex", project, author, "manual")]
