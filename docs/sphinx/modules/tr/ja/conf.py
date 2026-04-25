"""Sphinx configuration for modules/tr (Japanese)."""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.abspath("../../.."))
from conf_common import *  # noqa: E402,F401,F403
from conf_common import apply_ja_latex

language = "ja"
project = "TASK/TR — 輸送計算"
html_title = "TASK/TR — 輸送計算"
html_short_title = "TR (JA)"

intersphinx_mapping = {
    **intersphinx_mapping,
    "portal": (
        "https://task-docs.example.com/portal/ja/",
        (os.path.abspath("../../../_build/portal/ja/objects.inv"), None),
    ),
}
latex_elements = apply_ja_latex(latex_elements)
latex_documents = [("index", "task_tr_manual.tex", project, author, "manual")]
