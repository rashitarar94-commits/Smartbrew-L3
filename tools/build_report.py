"""Build the Word report for Tasks A and B from the Markdown sources in docs/.

The Markdown files stay the single source of truth; this script renders them
into one ``.docx`` for the Canvas submission. Diff blocks are coloured
red/green, tables become real Word tables, and headings feed a table of
contents.

Usage (python-docx is only needed for this tool, not for the app):
    .venv\\Scripts\\python -m pip install python-docx
    .venv\\Scripts\\python tools\\build_report.py
Output: docs/Lab3_G33_TaskA_TaskB_Report.docx
"""

import os
import re
from datetime import date

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "docs", "Lab3_G33_TaskA_TaskB_Report.docx")
REPO_URL = "https://github.com/rashitarar94-commits/Smartbrew-L3"

ACCENT = RGBColor(0x8A, 0x4B, 0x2A)
GREEN_BG, RED_BG, GREY_BG = "E6F4EA", "FCE8E6", "F3F1EE"
GREEN_FG, RED_FG = RGBColor(0x13, 0x73, 0x33), RGBColor(0xA5, 0x0E, 0x0E)
INLINE_RE = re.compile(r"(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\)|(?<!\*)\*[^*\s][^*]*\*(?!\*))")

# (heading shown in the report, markdown file, heading-level shift)
TASK_A = [
    ("docs/taskA/00_system_description.md", 1),
    ("docs/taskA/01_requirements.md", 1),
    ("docs/taskA/02_user_stories.md", 1),
    ("docs/taskA/03_product_backlog.md", 1),
    ("docs/taskA/04_comparison.md", 1),
    ("docs/taskA/05_prompt_log.md", 1),
]
TASK_B = [
    ("docs/taskB/feature_selection.md", 1),
    ("README.md", 1),
]


def shade(element, fill):
    """Give a paragraph or table cell a solid background colour.

    Inputs:  element – python-docx Paragraph or _Cell; fill – hex colour without '#'.
    Returns: None.
    """
    props = element._p.get_or_add_pPr() if hasattr(element, "_p") else element._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    props.append(shd)


def add_hyperlink(paragraph, text, url, size=None):
    """Append a clickable external hyperlink run to a paragraph.

    Inputs:  paragraph – target Paragraph; text – visible text; url – absolute URL;
             size – optional font size (Pt).
    Returns: None.
    """
    r_id = paragraph.part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), r_id)
    run = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "1155CC")
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    rpr.extend([color, underline])
    if size:
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), str(int(size.pt * 2)))
        rpr.append(sz)
    run.append(rpr)
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    run.append(t)
    link.append(run)
    paragraph._p.append(link)


def add_inline(paragraph, text, size=None, bold=False):
    """Render Markdown inline markup (bold, italic, code, links) into runs.

    Relative links (to repo files) become plain text; http(s) links become
    hyperlinks.

    Inputs:  paragraph – target Paragraph; text – Markdown text of one line/cell;
             size – optional font size; bold – make all runs bold (table headers).
    Returns: None.
    """
    text = text.replace("<br>", " ").replace("\\|", "|")
    for part in INLINE_RE.split(text):
        if not part:
            continue
        if part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
            run.font.color.rgb = ACCENT
        elif part.startswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("[") and "](" in part:
            label, url = re.match(r"\[([^\]]+)\]\(([^)]+)\)", part).groups()
            label = label.strip("`")
            if url.startswith("http"):
                add_hyperlink(paragraph, label, url, size)
                continue
            run = paragraph.add_run(label)
            run.italic = True
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            run = paragraph.add_run(part[1:-1])
            run.italic = True
        else:
            run = paragraph.add_run(part)
        if size:
            run.font.size = size
        if bold:
            run.bold = True


def split_row(line):
    """Split a Markdown table row into cell strings (honouring escaped pipes).

    Inputs:  line – a row such as ``| a | b |``.
    Returns: list of stripped cell texts.
    """
    inner = line.strip().strip("|")
    cells = re.split(r"(?<!\\)\|", inner)
    return [c.strip() for c in cells]


def column_widths(rows, total_cm):
    """Choose column widths proportional to the text length of each column.

    Inputs:  rows – list of rows (list of cell strings); total_cm – table width.
    Returns: list of Cm widths that sum to ``total_cm``.
    """
    n = max(len(r) for r in rows)
    mins, weights = [], []
    for i in range(n):
        texts = [re.sub(r"[`*]|\]\([^)]*\)|\[", "", r[i]) if i < len(r) else "" for r in rows]
        longest_word = max((len(w) for t in texts for w in t.split()), default=1)
        mins.append(min(3.2, 0.17 * longest_word + 0.4))  # keep IDs like "FR-01" on one line
        weights.append(sum(len(t) for t in texts) / len(texts) + 1)
    spare = total_cm - sum(mins)
    if spare <= 0:
        scale = total_cm / sum(mins)
        return [Cm(m * scale) for m in mins]
    return [Cm(m + spare * w / sum(weights)) for m, w in zip(mins, weights)]


def add_table(doc, rows, total_cm):
    """Insert a Markdown table as a formatted Word table.

    Inputs:  doc – Document; rows – header row followed by body rows;
             total_cm – usable page width.
    Returns: None.
    """
    n = max(len(r) for r in rows)
    rows = [r + [""] * (n - len(r)) for r in rows]
    size = Pt(8) if n >= 5 else Pt(9)
    table = doc.add_table(rows=len(rows), cols=n)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    widths = column_widths(rows, total_cm)
    for r_idx, row in enumerate(rows):
        for c_idx, text in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.width = widths[c_idx]
            para = cell.paragraphs[0]
            para.paragraph_format.space_after = Pt(0)
            add_inline(para, text, size=size, bold=(r_idx == 0))
            if r_idx == 0:
                shade(cell, "EFE3D6")
    header = table.rows[0]._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    header.append(repeat)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_code(doc, lines, lang):
    """Insert a fenced code block; diff blocks get red/green line backgrounds.

    Inputs:  doc – Document; lines – code lines; lang – fence language tag.
    Returns: None.
    """
    for line in lines:
        para = doc.add_paragraph()
        fmt = para.paragraph_format
        fmt.space_after = Pt(0)
        fmt.space_before = Pt(0)
        fmt.left_indent = Cm(0.2)
        run = para.add_run(line if line else " ")
        run.font.name = "Consolas"
        run.font.size = Pt(7.5)
        if lang == "diff" and line.startswith("+"):
            shade(para, GREEN_BG)
            run.font.color.rgb = GREEN_FG
        elif lang == "diff" and line.startswith("-"):
            shade(para, RED_BG)
            run.font.color.rgb = RED_FG
        else:
            shade(para, GREY_BG)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


BLOCK_START = re.compile(r"^\s*([-*] |\d+\. |#{1,6} |\||>|```|---)")


def join_continuation(lines, i, text, list_item):
    """Merge hard-wrapped Markdown lines into one paragraph of text.

    Inputs:  lines – all lines of the file; i – index of the paragraph's first line;
             text – text of that first line; list_item – True when the paragraph is a
             list item (continuation lines are then indented).
    Returns: tuple (index of the last consumed line, joined text).
    """
    while i + 1 < len(lines):
        nxt = lines[i + 1]
        if not nxt.strip() or BLOCK_START.match(nxt):
            break
        if list_item and not nxt.startswith(" "):
            break
        text += " " + nxt.strip()
        i += 1
    return i, text


def render_markdown(doc, path, shift, total_cm):
    """Render one Markdown file into the document.

    Inputs:  doc – Document; path – repo-relative Markdown path;
             shift – number of levels to push headings down; total_cm – text width.
    Returns: None.
    """
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            block = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            add_code(doc, block, lang)
        elif stripped.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not re.match(r"^\|[\s:|-]+\|$", lines[i].strip()):
                    rows.append(split_row(lines[i]))
                i += 1
            add_table(doc, rows, total_cm)
            continue
        elif re.match(r"^#{1,6} ", stripped):
            level = min(len(stripped.split(" ")[0]) + shift, 4)
            heading = doc.add_heading(level=level)
            add_inline(heading, stripped.split(" ", 1)[1])
        elif stripped == "---":
            pass
        elif stripped.startswith(">"):
            text = stripped.lstrip("> ").strip()
            while i + 1 < len(lines) and lines[i + 1].strip().startswith(">"):
                i += 1
                text += " " + lines[i].strip().lstrip(">").strip()
            para = doc.add_paragraph()
            para.paragraph_format.left_indent = Cm(0.6)
            shade(para, "FFF4D6")
            add_inline(para, text)
        elif re.match(r"^\s*[-*] ", line) or re.match(r"^\s*\d+\. ", line):
            number = re.match(r"^\s*(\d+)\. ", line)
            indent = (len(line) - len(line.lstrip())) // 2
            text = re.sub(r"^\s*([-*]|\d+\.) ", "", line)
            i, text = join_continuation(lines, i, text, list_item=True)
            if number:
                # Keep the Markdown's own numbers, so every list restarts at 1.
                para = doc.add_paragraph()
                para.paragraph_format.left_indent = Cm(0.7)
                para.paragraph_format.first_line_indent = Cm(-0.5)
                para.add_run(f"{number.group(1)}.\t")
                add_inline(para, text)
            else:
                add_inline(doc.add_paragraph(style="List Bullet 2" if indent else "List Bullet"), text)
        elif stripped:
            i, text = join_continuation(lines, i, stripped, list_item=False)
            add_inline(doc.add_paragraph(), text)
        i += 1


def add_toc(doc):
    """Insert a Word table-of-contents field (filled when Word updates fields).

    Inputs:  doc – Document.
    Returns: None.
    """
    para = doc.add_paragraph()
    run = para.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = 'TOC \\o "1-2" \\h \\z \\u'
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "Right-click and choose “Update Field” to build the table of contents."
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for el in (begin, instr, sep, placeholder, end):
        run._r.append(el)
    settings = doc.settings.element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    settings.append(update)


def setup_styles(doc):
    """Set fonts, heading colours and spacing for the whole document.

    Inputs:  doc – Document.
    Returns: None.
    """
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(4)
    for lvl, size in ((1, 18), (2, 14), (3, 12), (4, 11)):
        style = doc.styles[f"Heading {lvl}"]
        style.font.name = "Calibri"
        style.font.size = Pt(size)
        style.font.color.rgb = ACCENT
        style.paragraph_format.space_before = Pt(12 if lvl > 1 else 0)
        style.paragraph_format.space_after = Pt(4)


def title_page(doc):
    """Write the cover page with course, group, repository and LLM information.

    Inputs:  doc – Document.
    Returns: None.
    """
    for _ in range(5):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Lab Assignment 3 – Software Engineering with LLMs")
    r.font.size, r.bold, r.font.color.rgb = Pt(24), True, ACCENT
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("SmartBrew AI – Task A (Requirements Elicitation) & Task B (Code Generation)")
    r.font.size = Pt(14)
    doc.add_paragraph()
    info = [
        ("Group", "G33"),
        ("Date", date(2026, 10, 25).strftime("%d %B %Y")),
        ("LLM used", "Claude Opus 5.5 (claude-opus-5-5, Anthropic) via Claude Code – all tasks"),
        ("Repository", REPO_URL),
    ]
    for label, value in info:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(f"{label}: ")
        r.bold = True
        if value.startswith("http"):
            add_hyperlink(p, value, value)
        else:
            p.add_run(value)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def part_title(doc, title, subtitle):
    """Start a new part (Task A / Task B) on a fresh page.

    Inputs:  doc – Document; title – Heading 1 text; subtitle – one-line description.
    Returns: None.
    """
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    doc.add_heading(title, level=1)
    p = doc.add_paragraph()
    r = p.add_run(subtitle)
    r.italic = True


def build():
    """Assemble the full report and save it to ``docs/``.

    Inputs:  none (reads the Markdown files listed in TASK_A and TASK_B).
    Returns: str path of the written .docx file.
    """
    doc = Document()
    section = doc.sections[0]
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    for side in ("left_margin", "right_margin"):
        setattr(section, side, Cm(1.8))
    section.top_margin = section.bottom_margin = Cm(1.8)
    total_cm = 21 - 2 * 1.8
    setup_styles(doc)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run(f"SmartBrew AI · Lab 3 · Group G33 · {REPO_URL}").font.size = Pt(8)

    title_page(doc)
    doc.add_heading("Contents", level=1)
    add_toc(doc)

    part_title(doc, "Task A – LLM-Assisted Requirements Elicitation",
               "System description, LLM-generated requirements, user stories and backlog, "
               "comparison with Assignment 2, and the prompt log.")
    for path, shift in TASK_A:
        render_markdown(doc, path, shift, total_cm)

    part_title(doc, "Task B – Code Generation & Executable Prototype",
               f"Selected functionalities and the prototype documentation. Source code: {REPO_URL}")
    for path, shift in TASK_B:
        render_markdown(doc, path, shift, total_cm)

    doc.save(OUT)
    return OUT


if __name__ == "__main__":
    print("Written", build())
