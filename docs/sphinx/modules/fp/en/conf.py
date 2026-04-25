"""Sphinx configuration for modules/fp (English)."""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.abspath("../../.."))
from conf_common import *  # noqa: E402,F401,F403

language = "en"
project = "TASK/FP — Fokker-Planck"
html_title = "TASK/FP — Fokker-Planck"
html_short_title = "FP (EN)"

intersphinx_mapping = {
    **intersphinx_mapping,
    "portal": (
        "https://task-docs.example.com/portal/en/",
        (os.path.abspath("../../../_build/portal/en/objects.inv"), None),
    ),
}
latex_documents = [("index", "task_fp_manual.tex", project, author, "manual")]
