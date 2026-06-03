#!/usr/bin/env python3
"""docx_extract.py — first-pass .docx -> Markdown for vault migration.

Walks the document body IN ORDER (paragraphs + tables interleaved), maps Word
heading styles to #/##/###, preserves bold runs as **...**, turns List Bullet/
Number styles into - / 1., and renders tables as GitHub Markdown tables.

This is a BASE conversion — an agent then refines it into house style
(frontmatter, callouts, mermaid for diagrams, wikilinks). It deliberately does
NOT hand-number headings.

Run with the dac venv python:
    $SKILL_PYTHON docx_extract.py <in.docx> [> out.md]   # a python with python-docx
"""
import sys
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


def runs_to_md(p):
    out = []
    for r in p.runs:
        t = r.text
        if not t:
            continue
        if r.bold and t.strip():
            # keep surrounding spaces outside the ** markers
            lead = t[: len(t) - len(t.lstrip())]
            trail = t[len(t.rstrip()):]
            out.append(f"{lead}**{t.strip()}**{trail}")
        else:
            out.append(t)
    return "".join(out) if out else p.text


def para_to_md(p):
    style = (p.style.name or "").lower()
    text = runs_to_md(p).rstrip()
    if not text.strip():
        return ""
    if style.startswith("heading") or style.startswith("title"):
        # Heading 1/2/3... -> #/##/###; Title -> #
        if style.startswith("title"):
            level = 1
        else:
            digits = "".join(c for c in style if c.isdigit())
            level = int(digits) if digits else 2
        level = max(1, min(level, 6))
        return "#" * level + " " + text.strip()
    if "list bullet" in style or style.startswith("list paragraph") and text.lstrip().startswith(("•", "-")):
        return "- " + text.strip().lstrip("•-").strip()
    if "list number" in style:
        return "1. " + text.strip()
    return text


def table_to_md(tbl):
    rows = []
    for row in tbl.rows:
        cells = [" ".join(c.text.split()).replace("|", r"\|") for c in row.cells]
        rows.append(cells)
    if not rows:
        return ""
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    md = ["| " + " | ".join(rows[0]) + " |",
          "| " + " | ".join(["---"] * ncol) + " |"]
    for r in rows[1:]:
        md.append("| " + " | ".join(r) + " |")
    return "\n".join(md)


def main(path):
    doc = Document(path)
    body = doc.element.body
    out = []
    for child in body.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "p":
            md = para_to_md(Paragraph(child, doc))
            if md:
                out.append(md)
        elif tag == "tbl":
            md = table_to_md(Table(child, doc))
            if md:
                out.append("")
                out.append(md)
                out.append("")
    print("\n\n".join(out))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: docx_extract.py <in.docx>")
    main(sys.argv[1])
