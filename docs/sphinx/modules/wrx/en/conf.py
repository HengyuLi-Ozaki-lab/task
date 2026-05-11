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

# Cross-Sphinx-project Markdown links (modules → portal) trigger
# myst.xref_missing because the target lives outside this project's
# srcdir. Suppress only this specific warning so -W doesn't fail; the
# deployed unified site serves modules/ and portal/ under one tree, so
# the relative .md path resolves to .html at runtime.
# TODO: revert once intersphinx_mapping URL is real (placeholder today).
suppress_warnings = list(
    dict.fromkeys(globals().get("suppress_warnings", []) + ["myst.xref_missing"])
)
