#!/usr/bin/env python3
"""Render task-library-manual.tex to a searchable multi-page PDF.

xelatex is not installed in this environment, so we extract the textual
content from the .tex source and lay it out with matplotlib's
PdfPages backend. Japanese is rendered via Noto Serif CJK JP (TTC).

This is a fallback path; when TeX Live is available, just run

    xelatex task-library-manual.tex
    xelatex task-library-manual.tex

and this script is unnecessary.
"""
from __future__ import annotations

import os
import re
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["text.usetex"] = False
matplotlib.rcParams["text.parse_math"] = False
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import font_manager as fm

HERE = Path(__file__).resolve().parent
TEX = HERE / "task-library-manual.tex"
PDF = HERE / "task-library-manual.pdf"

# ----------------------------------------------------------------------
# Font setup
# ----------------------------------------------------------------------
JP_SERIF = fm.FontProperties(fname="/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc")
JP_BOLD  = fm.FontProperties(fname="/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc")
JP_SANS  = fm.FontProperties(fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
# matplotlib cannot easily switch to a monospaced CJK font in the same line,
# so we use Sans CJK for code too (widely legible for JP + ASCII).
JP_MONO  = JP_SANS

# ----------------------------------------------------------------------
# Minimal TeX -> plain-text converter
# ----------------------------------------------------------------------
def strip_tex(src: str) -> str:
    """Very small TeX stripper: keep text, drop markup."""
    s = src

    # Drop preamble up to \begin{document}
    m = re.search(r"\\begin\{document\}", s)
    if m:
        s = s[m.end():]
    m = re.search(r"\\end\{document\}", s)
    if m:
        s = s[: m.start()]

    # Remove comments (% to end of line, but escape \% first)
    s = re.sub(r"(?<!\\)%.*", "", s)

    # Handle \verb-like bits first (cheap): nothing for now.

    # Replace common math/punct
    s = s.replace(r"\checkmark", "OK")
    s = s.replace(r"\triangle", "TRI")
    s = s.replace(r"\ldots", "...")
    s = s.replace(r"\\", "\n")
    s = s.replace(r"\textbf", "")
    s = s.replace(r"\emph", "")
    s = s.replace(r"\small", "")
    s = s.replace(r"\Large", "")
    s = s.replace(r"\Huge", "")
    s = s.replace(r"\bfseries", "")
    s = s.replace(r"\itshape", "")
    s = s.replace(r"\footnotesize", "")
    s = s.replace(r"\clearpage", "")
    s = s.replace(r"\vfill", "")
    s = s.replace(r"\noindent", "")
    s = s.replace(r"\newpage", "")

    # Drop titling etc
    for cmd in ("maketitle", "tableofcontents", "appendix"):
        s = s.replace(f"\\{cmd}", "")

    # Chapter/section/subsection markers -> keep name only
    def repl_hdr(match: re.Match) -> str:
        level, body = match.group(1), match.group(2)
        marker = {"chapter": "\n\n### CHAPTER ###\n",
                  "section": "\n\n## SECTION ##\n",
                  "subsection": "\n\n# SUBSECTION #\n",
                  "subsubsection": "\n# SUBSUB #\n",
                  "chapter*": "\n\n### CHAPTER ###\n",
                  "section*": "\n\n## SECTION ##\n"}.get(level, "\n")
        return f"{marker}{body}\n"

    s = re.sub(r"\\(chapter\*?|section\*?|subsection\*?|subsubsection\*?)\{([^}]*)\}",
               repl_hdr, s)

    # \texttt, \emph, \textit, \underline -> inline
    s = re.sub(r"\\textt?t\{([^}]*)\}", r"`\1`", s)
    s = re.sub(r"\\textit\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\underline\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\url\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\label\{[^}]*\}", "", s)
    s = re.sub(r"\\ref\{[^}]*\}", "(参照)", s)
    s = re.sub(r"\\cite\{[^}]*\}", "", s)
    s = re.sub(r"\\fbox\{([^}]*)\}", r"[\1]", s)
    s = re.sub(r"\\caption\{([^}]*)\}", r"キャプション: \1", s)

    # tcolorboxes: keep title + body
    def tcbox(match: re.Match) -> str:
        envname = match.group(1)
        opt = match.group(2) or ""
        body = match.group(3)
        title = opt.strip("[]")
        tag = {"faq": "FAQ", "learn": "学習目標",
               "note": "補足", "warn": "注意"}.get(envname, envname)
        hdr = f"[{tag}] {title}".strip()
        return f"\n\n==> {hdr}\n{body}\n<==\n"

    s = re.sub(
        r"\\begin\{(faq|learn|note|warn)\}(\[[^\]]*\])?(.*?)\\end\{\1\}",
        tcbox, s, flags=re.DOTALL)

    # abstract
    s = re.sub(r"\\begin\{abstract\}(.*?)\\end\{abstract\}",
               r"\n[要旨]\n\1\n[要旨終わり]\n", s, flags=re.DOTALL)

    # itemize / enumerate / description
    def list_repl(match: re.Match) -> str:
        kind = match.group(1)
        body = match.group(2)
        items = re.split(r"\\item(?:\[([^\]]*)\])?\s*", body)
        lines = []
        it = iter(items[1:])
        while True:
            try:
                tag = next(it)
                text = next(it, "")
            except StopIteration:
                break
            bullet = "- "
            if tag:
                bullet = f"[{tag}] "
            lines.append(bullet + text.strip())
        return "\n" + "\n".join(lines) + "\n"

    while re.search(r"\\begin\{(itemize|enumerate|description)\}", s):
        s = re.sub(
            r"\\begin\{(itemize|enumerate|description)\}(?:\[[^\]]*\])?(.*?)\\end\{\1\}",
            list_repl, s, flags=re.DOTALL)

    # listings
    def lst_repl(match: re.Match) -> str:
        body = match.group(1)
        return "\n<<code>>\n" + body.strip("\n") + "\n<<endcode>>\n"

    s = re.sub(r"\\begin\{lstlisting\}(?:\[[^\]]*\])?(.*?)\\end\{lstlisting\}",
               lst_repl, s, flags=re.DOTALL)

    # tabular / longtable: keep rows, drop column spec
    def tab_repl(match: re.Match) -> str:
        body = match.group(2)
        # Drop \toprule, \midrule, \bottomrule, \endhead, \endfirsthead
        for rm in (r"\toprule", r"\midrule", r"\bottomrule",
                   r"\endhead", r"\endfirsthead", r"\hline",
                   r"\\endhead"):
            body = body.replace(rm, "")
        # Drop caption inside table
        body = re.sub(r"\\caption\{[^}]*\}\\*", "", body)
        body = re.sub(r"\\label\{[^}]*\}", "", body)
        # Split rows on \\
        rows = [r.strip() for r in body.split("\\\\") if r.strip()]
        out = ["\n[表]"]
        for r in rows:
            cols = [c.strip() for c in r.split("&")]
            out.append("  | " + " | ".join(cols) + " |")
        out.append("[/表]\n")
        return "\n".join(out)

    s = re.sub(
        r"\\begin\{(tabular|longtable)\}\{[^}]*\}(.*?)\\end\{\1\}",
        tab_repl, s, flags=re.DOTALL)

    # tikzpicture / center: just drop for the text fallback but keep placeholder
    s = re.sub(
        r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}",
        "\n[図 (TikZ): PDF 版では LaTeX 層で描画]\n", s, flags=re.DOTALL)

    s = re.sub(r"\\begin\{center\}(.*?)\\end\{center\}", r"\1", s, flags=re.DOTALL)
    s = re.sub(r"\\begin\{tabbing\}(.*?)\\end\{tabbing\}", r"\1", s, flags=re.DOTALL)

    # Kill remaining unknown environments
    s = re.sub(r"\\begin\{[^}]*\}", "", s)
    s = re.sub(r"\\end\{[^}]*\}", "", s)

    # Remaining commands with args: \foo{bar} -> bar
    for _ in range(6):
        s2 = re.sub(r"\\[A-Za-z@]+(\[[^\]]*\])?\{([^{}]*)\}", r"\2", s)
        if s2 == s:
            break
        s = s2

    # Drop lone commands
    s = re.sub(r"\\[A-Za-z@]+\*?", "", s)

    # Escape sequences of ~ and $, collapse runs of whitespace
    s = s.replace("~", " ")
    s = s.replace("\\$", "$")
    s = s.replace("\\%", "%")
    s = s.replace("\\&", "&")
    s = s.replace("\\_", "_")
    s = s.replace("\\#", "#")
    s = s.replace("\\{", "{").replace("\\}", "}")
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s


# ----------------------------------------------------------------------
# Page layout
# ----------------------------------------------------------------------
PAGE_W_IN = 8.27   # A4 width in inches
PAGE_H_IN = 11.69  # A4 height in inches
MARGIN_IN = 0.95
LINE_H_IN = 0.23    # line height in inches (~16pt), roomier
TOP_TEXT  = PAGE_H_IN - MARGIN_IN
BOTTOM_MARGIN = MARGIN_IN + 0.15
LEFT_TEXT = MARGIN_IN
RIGHT_TEXT = PAGE_W_IN - MARGIN_IN
MAX_CHARS_PER_LINE = 40    # for JP text (shorter line -> more lines)
MAX_CHARS_PER_LINE_MONO = 60  # for code blocks

def tokenise_lines(text: str) -> list[tuple[str, str]]:
    """Split the body into (kind, line) tuples ready for rendering.

    kinds: heading1, heading2, heading3, body, code, blank, box.
    """
    out: list[tuple[str, str]] = []
    in_code = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.strip() == "<<code>>":
            in_code = True
            out.append(("codestart", ""))
            continue
        if line.strip() == "<<endcode>>":
            in_code = False
            out.append(("codeend", ""))
            continue
        if in_code:
            out.append(("code", line))
            continue
        if line.strip() == "":
            out.append(("blank", ""))
            continue
        if line.strip() == "### CHAPTER ###":
            out.append(("pagebreak", ""))
            out.append(("chapter_next", ""))
            continue
        if line.strip() == "## SECTION ##":
            out.append(("section_next", ""))
            continue
        if line.strip() == "# SUBSECTION #":
            out.append(("subsection_next", ""))
            continue
        if line.strip() == "# SUBSUB #":
            out.append(("subsub_next", ""))
            continue

        # Consume "_next" markers
        if out and out[-1][0].endswith("_next"):
            kind = out.pop()[0].replace("_next", "")
            out.append((kind, line))
            continue

        # Box markers
        if line.startswith("==>"):
            out.append(("boxstart", line[3:].strip()))
            continue
        if line.startswith("<=="):
            out.append(("boxend", ""))
            continue

        out.append(("body", line))
    return out


def wrap_jp(line: str, width: int) -> list[str]:
    """Character-based wrapping (works for both JP and ASCII)."""
    if not line:
        return [""]
    out: list[str] = []
    cur = ""
    # Simple char-count; in JP each kanji counts as 1 for our purposes.
    # For code, keep leading indent.
    for ch in line:
        cur += ch
        if len(cur) >= width:
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out


def measure_advance(kind: str) -> float:
    """How tall is this element in inches."""
    if kind == "chapter":
        return LINE_H_IN * 2.6
    if kind == "section":
        return LINE_H_IN * 1.9
    if kind == "subsection":
        return LINE_H_IN * 1.5
    if kind == "subsub":
        return LINE_H_IN * 1.3
    if kind in ("body", "code", "boxstart", "boxend"):
        return LINE_H_IN
    if kind == "blank":
        return LINE_H_IN * 0.5
    return LINE_H_IN


def plot_page(lines_to_draw: list[tuple[str, str]], pdf: PdfPages,
              page_num: int, total_heading: str) -> None:
    fig, ax = plt.subplots(figsize=(PAGE_W_IN, PAGE_H_IN))
    ax.set_xlim(0, PAGE_W_IN)
    ax.set_ylim(0, PAGE_H_IN)
    ax.set_axis_off()
    # Header/footer
    ax.text(LEFT_TEXT, PAGE_H_IN - 0.35,
            "TASK プラズマ輸送ライブラリ化 — 日本語マニュアル",
            fontproperties=JP_SANS, fontsize=8, color="gray")
    ax.text(RIGHT_TEXT, PAGE_H_IN - 0.35, total_heading,
            fontproperties=JP_SANS, fontsize=8, color="gray", ha="right")
    ax.plot([LEFT_TEXT, RIGHT_TEXT], [PAGE_H_IN - 0.45, PAGE_H_IN - 0.45],
            color="gray", linewidth=0.4)
    ax.text(PAGE_W_IN / 2, 0.35, str(page_num),
            fontproperties=JP_SANS, fontsize=9, ha="center")

    y = TOP_TEXT - 0.3
    in_box = False
    box_start_y = None
    code_bg_start = None
    for kind, text in lines_to_draw:
        if kind == "chapter":
            y -= 0.3
            ax.text(LEFT_TEXT, y, f"第 {text} 章", fontproperties=JP_BOLD,
                    fontsize=18, color="#003366")
            y -= 0.35
            ax.plot([LEFT_TEXT, RIGHT_TEXT], [y, y], color="#003366", lw=1.0)
            y -= 0.25
        elif kind == "section":
            y -= 0.1
            ax.text(LEFT_TEXT, y, text, fontproperties=JP_BOLD,
                    fontsize=14, color="#333366")
            y -= 0.35
        elif kind == "subsection":
            ax.text(LEFT_TEXT, y, text, fontproperties=JP_BOLD,
                    fontsize=12, color="#333366")
            y -= 0.30
        elif kind == "subsub":
            ax.text(LEFT_TEXT, y, text, fontproperties=JP_BOLD,
                    fontsize=11, color="#333366")
            y -= 0.26
        elif kind == "boxstart":
            ax.text(LEFT_TEXT, y, f"■ {text}", fontproperties=JP_BOLD,
                    fontsize=10, color="#8c4400")
            y -= LINE_H_IN
            in_box = True
            box_start_y = y + 0.05
        elif kind == "boxend":
            if in_box and box_start_y is not None:
                # Draw a light border from the saved box start down to y
                ax.add_patch(plt.Rectangle(
                    (LEFT_TEXT - 0.05, y - 0.05),
                    RIGHT_TEXT - LEFT_TEXT + 0.1,
                    box_start_y - y + 0.1,
                    fill=False, edgecolor="#c08040", linewidth=0.6))
                in_box = False
                box_start_y = None
            y -= 0.1
        elif kind == "codestart":
            code_bg_start = y + 0.05
        elif kind == "codeend":
            if code_bg_start is not None:
                ax.add_patch(plt.Rectangle(
                    (LEFT_TEXT - 0.05, y - 0.02),
                    RIGHT_TEXT - LEFT_TEXT + 0.1,
                    code_bg_start - y,
                    fill=True, facecolor="#f5f5f5", edgecolor="#dddddd",
                    linewidth=0.4, zorder=0))
                code_bg_start = None
            y -= 0.05
        elif kind == "code":
            ax.text(LEFT_TEXT + 0.1, y, text, fontproperties=JP_MONO,
                    fontsize=8.5, color="#1a1a1a")
            y -= LINE_H_IN * 0.95
        elif kind == "body":
            ax.text(LEFT_TEXT, y, text, fontproperties=JP_SERIF,
                    fontsize=10.5, color="#111111")
            y -= LINE_H_IN
        elif kind == "blank":
            y -= LINE_H_IN * 0.6

    fig.savefig(pdf, format="pdf")
    plt.close(fig)


def paginate(tokens: list[tuple[str, str]]) -> list[list[tuple[str, str]]]:
    """Break the stream into pages.

    - Wrap body / code lines to their character width first.
    - Push lines onto the current page until they'd cross the bottom margin.
    - Honour explicit `pagebreak` tokens.
    """
    pages: list[list[tuple[str, str]]] = [[]]
    y_budget = TOP_TEXT - BOTTOM_MARGIN - 0.5

    def new_page() -> None:
        pages.append([])

    def wrap_tokens() -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for kind, text in tokens:
            if kind in ("body",):
                for w in wrap_jp(text, MAX_CHARS_PER_LINE):
                    out.append((kind, w))
            elif kind == "code":
                for w in wrap_jp(text, MAX_CHARS_PER_LINE_MONO):
                    out.append((kind, w))
            elif kind in ("chapter", "section", "subsection", "subsub"):
                for w in wrap_jp(text, MAX_CHARS_PER_LINE):
                    out.append((kind, w))
            else:
                out.append((kind, text))
        return out

    wrapped = wrap_tokens()
    y_used = 0.0
    for kind, text in wrapped:
        if kind == "pagebreak":
            new_page()
            y_used = 0.0
            continue
        if kind == "chapter":
            # chapters start a new page
            if pages[-1]:
                new_page()
                y_used = 0.0
        if kind == "codestart" or kind == "codeend":
            adv = 0.06
        elif kind == "boxstart" or kind == "boxend":
            adv = LINE_H_IN
        elif kind == "code":
            adv = LINE_H_IN * 0.85
        else:
            adv = measure_advance(kind)
        if y_used + adv > y_budget:
            new_page()
            y_used = 0.0
        pages[-1].append((kind, text))
        y_used += adv
    # Drop empty trailing page
    if pages and not pages[-1]:
        pages.pop()
    return pages


def main() -> None:
    src = TEX.read_text(encoding="utf-8")
    text = strip_tex(src)

    # Front matter TOC-ish: add a cover page manually.
    tokens = tokenise_lines(text)

    # Insert cover + TOC marker at the beginning
    cover = [
        ("section", "TASK プラズマ輸送ライブラリ化プロジェクト"),
        ("body", ""),
        ("body", "日本語マニュアル・報告書"),
        ("body", "tr / ti / wr / wrx / fp モジュール (Phase L-0 〜 L-7)"),
        ("blank", ""),
        ("body", "著者: k-yoshimi (東京大学)"),
        ("body", "日付: 2026 年 4 月 18 日"),
        ("blank", ""),
        ("body", "本書は TeX Live 不在の環境向けに matplotlib で組版した"),
        ("body", "搭乗便フォールバック版 PDF です. LaTeX ソースは"),
        ("body", "docs/manual/task-library-manual.tex を参照してください."),
        ("body", "TeX Live があれば xelatex でより整った PDF が得られます."),
        ("pagebreak", ""),
    ]
    tokens = cover + tokens

    pages = paginate(tokens)

    print(f"Rendering {len(pages)} pages to {PDF}")
    with PdfPages(PDF) as pdf:
        for i, page in enumerate(pages, 1):
            plot_page(page, pdf, i, f"第 {i} / {len(pages)} 頁")

    print("done.")


if __name__ == "__main__":
    main()
