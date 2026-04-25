"""Sphinx configuration for modules/tot (Japanese)."""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.abspath("../../.."))
from conf_common import *  # noqa: E402,F401,F403
from conf_common import apply_ja_latex

language = "ja"
project = "TASK/TOT — オーケストレータ"
html_title = "TASK/TOT — オーケストレータ"
html_short_title = "TOT (JA)"

intersphinx_mapping = {
    **intersphinx_mapping,
    "portal": (
        "https://task-docs.example.com/portal/ja/",
        (os.path.abspath("../../../_build/portal/ja/objects.inv"), None),
    ),
}
latex_elements = apply_ja_latex(latex_elements)
latex_documents = [("index", "task_tot_manual.tex", project, author, "manual")]
