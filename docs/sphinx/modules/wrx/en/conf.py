"""Sphinx configuration for modules/wrx (English)."""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.abspath("../../.."))
from conf_common import *  # noqa: E402,F401,F403

language = "en"
project = "TASK/WRX — Wave Ray Extended"
html_title = "TASK/WRX — Wave Ray Extended"
html_short_title = "WRX (EN)"

intersphinx_mapping = {
    **intersphinx_mapping,
    "portal": (
        "https://task-docs.example.com/portal/en/",
        (os.path.abspath("../../../_build/portal/en/objects.inv"), None),
    ),
}
latex_documents = [("index", "task_wrx_manual.tex", project, author, "manual")]
