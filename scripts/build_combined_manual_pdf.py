"""
Build CompressorIQ_User_Manual.pdf = narrative (from USER_MANUAL.md) + screenshot PDF.

Requires: pip install -r scripts/requirements-manual-pdf.txt
Output:   project root + frontend/public/CompressorIQ_User_Manual.pdf
"""

from __future__ import annotations

import re
import sys
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
MANUAL_MD = ROOT / "USER_MANUAL.md"
SHOTS_PDF = ROOT / "CompressorIQ_User_Guide_Screenshots.pdf"
OUT_PDF = ROOT / "CompressorIQ_User_Manual.pdf"
PUBLIC_OUT = ROOT / "frontend" / "public" / "CompressorIQ_User_Manual.pdf"


def md_inline_to_xml(s: str) -> str:
    """Escape HTML and convert **bold** to <b>."""
    parts = re.split(r"(\*\*.+?\*\*)", s)
    out: list[str] = []
    for p in parts:
        if p.startswith("**") and p.endswith("**") and len(p) > 4:
            out.append("<b>" + escape(p[2:-2]) + "</b>")
        else:
            out.append(escape(p))
    return "".join(out)


def table_from_block(block: str):
    lines = [ln.rstrip() for ln in block.strip().splitlines() if ln.strip()]
    rows = []
    for ln in lines:
        if not ln.strip().startswith("|"):
            return None
        cells = [c.strip() for c in ln.split("|")]
        cells = [c for c in cells if c != ""]  # drop empty from split
        if not cells:
            return None
        rows.append(cells)
    if len(rows) < 2:
        return None
    # Drop GFM separator row (|---|---|)
    if len(rows) >= 2:
        sep = rows[1]
        if sep and all(re.match(r"^:?-+:?$", c.strip()) for c in sep):
            rows.pop(1)
    return rows


def build_narrative_pdf(path: Path) -> bytes:
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    raw = path.read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", raw)

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle(
        name="H1",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=8,
        spaceBefore=12,
    )
    h2 = ParagraphStyle(
        name="H2",
        parent=styles["Heading2"],
        fontSize=13,
        spaceAfter=6,
        spaceBefore=10,
    )
    h3 = ParagraphStyle(
        name="H3",
        parent=styles["Heading3"],
        fontSize=11,
        spaceAfter=4,
        spaceBefore=8,
    )
    body = ParagraphStyle(
        name="Body",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=13,
        spaceAfter=6,
    )
    bullet = ParagraphStyle(
        name="Bullet",
        parent=body,
        leftIndent=12,
        bulletIndent=6,
    )

    story = []
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="CompressorIQ User Manual",
    )

    for block in blocks:
        b = block.strip()
        if not b:
            continue
        if b.startswith("---"):
            story.append(Spacer(1, 6))
            continue

        tbl = table_from_block(b)
        if tbl:
            # Scale table to content width
            t = Table(tbl, hAlign="LEFT")
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.append(t)
            story.append(Spacer(1, 8))
            continue

        lines = b.splitlines()
        first = lines[0].strip()

        if first.startswith("### "):
            story.append(Paragraph(md_inline_to_xml(first[4:]), h3))
        elif first.startswith("## "):
            story.append(Paragraph(md_inline_to_xml(first[3:]), h2))
        elif first.startswith("# "):
            story.append(Paragraph(md_inline_to_xml(first[2:]), h1))
        elif first.startswith(("- ", "* ")):
            for line in lines:
                line = line.strip()
                if line.startswith(("- ", "* ")):
                    story.append(
                        Paragraph(
                            "• " + md_inline_to_xml(line[2:].strip()),
                            bullet,
                        )
                    )
        elif re.match(r"^\d+\.\s", first):
            for line in lines:
                line = line.strip()
                m = re.match(r"^(\d+)\.\s+(.*)", line)
                if m:
                    story.append(
                        Paragraph(
                            f"{m.group(1)}. {md_inline_to_xml(m.group(2))}",
                            body,
                        )
                    )
        else:
            merged = " ".join(ln.strip() for ln in lines)
            story.append(Paragraph(md_inline_to_xml(merged), body))

    doc.build(story)
    return buffer.getvalue()


def main() -> int:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("Install: pip install -r scripts/requirements-manual-pdf.txt", file=sys.stderr)
        return 1

    if not MANUAL_MD.is_file():
        print(f"Missing {MANUAL_MD}", file=sys.stderr)
        return 1

    print("Building narrative PDF from USER_MANUAL.md ...")
    narrative_bytes = build_narrative_pdf(MANUAL_MD)

    writer = PdfWriter()
    print("Appending narrative pages ...")
    for page in PdfReader(BytesIO(narrative_bytes)).pages:
        writer.add_page(page)

    if SHOTS_PDF.is_file():
        print(f"Appending {SHOTS_PDF.name} ...")
        for page in PdfReader(str(SHOTS_PDF)).pages:
            writer.add_page(page)
    else:
        print(f"Warning: {SHOTS_PDF} not found — narrative only.", file=sys.stderr)

    with open(OUT_PDF, "wb") as f:
        writer.write(f)
    print(f"Wrote {OUT_PDF}")

    try:
        import shutil

        shutil.copy2(OUT_PDF, PUBLIC_OUT)
        print(f"Copied to {PUBLIC_OUT}")
    except OSError as e:
        print(f"Note: could not copy to public: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
