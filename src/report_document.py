"""Render the submitted report Markdown and local figures as a paginated PDF."""

import argparse
import re
from io import BytesIO
from pathlib import Path
from statistics import mean
from xml.sax.saxutils import escape, quoteattr

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.doctemplate import LayoutError
from reportlab.platypus.flowables import Flowable

from .paths import PROJECT_ROOT

INK = colors.HexColor("#1B2C42")
ACCENT = colors.HexColor("#0C615D")
MUTED = colors.HexColor("#4D6378")
MARGIN = 46
TEXT_WIDTH = A4[0] - 2 * MARGIN
TABLE_RULE = re.compile(r":?-{3,}:?")
INLINE = re.compile(r"`([^`]+)`|\*\*([^*]+)\*\*|\[([^\]]+)\]\(([^)]+)\)")
FIGURE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

BODY = ParagraphStyle(
    "Body", fontName="Helvetica", fontSize=10.5, leading=15, textColor=INK, spaceAfter=9,
)
TITLE = ParagraphStyle(
    "Title", parent=BODY, fontName="Helvetica-Bold", fontSize=31, leading=34, spaceAfter=17,
)
HEADING = ParagraphStyle(
    "Heading", parent=BODY, fontName="Helvetica-Bold", fontSize=22, leading=25,
    spaceBefore=2, spaceAfter=16, keepWithNext=True,
)
SUBHEADING = ParagraphStyle(
    "Subheading", parent=BODY, fontName="Helvetica-Bold", fontSize=12, leading=15,
    textColor=ACCENT, spaceBefore=7, spaceAfter=6, keepWithNext=True,
)
CELL = ParagraphStyle("Cell", parent=BODY, fontSize=9, leading=11, spaceAfter=0)
TABLE_HEAD = ParagraphStyle(
    "Table heading", parent=CELL, fontName="Helvetica-Bold", textColor=colors.white,
)
BULLET = ParagraphStyle("Bullet", parent=BODY, leftIndent=13, bulletIndent=2, spaceAfter=5)
MONOSPACE = ParagraphStyle(
    "Code", fontName="Courier", fontSize=9, leading=12, textColor=INK,
    leftIndent=8, spaceBefore=5, spaceAfter=9,
)
CAPTION = ParagraphStyle(
    "Caption", parent=BODY, textColor=MUTED, fontSize=9.5, leading=13,
    spaceAfter=12,
)


def _inline_markup(value: str) -> str:
    """Convert the report's inline Markdown to escaped Paragraph markup."""
    parts: list[str] = []
    end = 0
    for match in INLINE.finditer(value):
        parts.append(escape(value[end:match.start()]))
        code, bold, label, destination = match.groups()
        if code is not None:
            parts.append(f'<font name="Courier" size="9">{escape(code)}</font>')
        elif bold is not None:
            parts.append(f"<b>{escape(bold)}</b>")
        elif destination.startswith(("https://", "http://")):
            parts.append(f'<link href={quoteattr(destination)} color="#0C615D">{escape(label)}</link>')
        else:
            parts.append(escape(label))
        end = match.end()
    parts.append(escape(value[end:]))
    return "".join(parts)


def _table_rows(lines: list[str]) -> list[list[str]]:
    """Split this report's pipe-delimited table dialect into cells."""
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    if len(rows) < 2 or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("Report contains a table with unequal column counts.")
    if not all(TABLE_RULE.fullmatch(cell) for cell in rows[1]):
        raise ValueError("Report contains a table without a heading separator.")
    return rows[:1] + rows[2:]


def _table(lines: list[str]) -> Table:
    """Build a table with alternating row fills and proportional columns."""
    rows = _table_rows(lines)
    weights = [max(3, mean(len(value) for value in column)) ** 0.5 for column in zip(*rows)]
    widths = [TEXT_WIDTH * weight / sum(weights) for weight in weights]
    cells = [
        [Paragraph(_inline_markup(cell), TABLE_HEAD if index == 0 else CELL) for cell in row]
        for index, row in enumerate(rows)
    ]
    table = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#EEF3F7"), colors.white]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#B8C9D6")),
    ]))
    return table


def _figure(source: Path, match: re.Match[str]) -> Image:
    """Size a relative PNG figure without distorting its axes or labels."""
    image_path = source.parent / match.group(2)
    width, height = ImageReader(image_path).getSize()
    scale = min(TEXT_WIDTH / width, 335 / height)
    return Image(str(image_path), width=width * scale, height=height * scale, hAlign="CENTER")


def _flowables(source: Path) -> list[Flowable]:
    """Read the small Markdown subset used by the canonical report source."""
    story: list[Flowable] = []
    lines = iter(source.read_text(encoding="utf-8").splitlines())
    pending_table: list[str] = []
    for line in lines:
        if line.startswith("|"):
            pending_table.append(line)
            continue
        if pending_table:
            story.extend((_table(pending_table), Spacer(1, 11)))
            pending_table.clear()
        if not line:
            continue
        if line == "<!-- pagebreak -->":
            story.append(PageBreak())
        elif line.startswith("```"):
            code_lines = []
            for code_line in lines:
                if code_line == "```":
                    break
                code_lines.append(code_line)
            else:
                raise ValueError("Report contains an unclosed code block.")
            story.append(Preformatted("\n".join(code_lines), MONOSPACE))
        elif figure := FIGURE.fullmatch(line):
            story.extend((_figure(source, figure), Spacer(1, 6)))
        elif line.startswith("# "):
            story.append(Paragraph(_inline_markup(line[2:]), TITLE))
        elif line.startswith("## "):
            story.append(Paragraph(_inline_markup(line[3:]), HEADING))
        elif line.startswith("### "):
            story.append(Paragraph(_inline_markup(line[4:]), SUBHEADING))
        elif line.startswith("- "):
            story.append(Paragraph(_inline_markup(line[2:]), BULLET, bulletText="-"))
        elif line.startswith("Figure "):
            story.append(Paragraph(_inline_markup(line), CAPTION))
        else:
            story.append(Paragraph(_inline_markup(line), BODY))
    if pending_table:
        story.append(_table(pending_table))
    return story


def _page(canvas: Canvas, document: SimpleDocTemplate) -> None:
    """Draw a small course identifier and page number in the margins."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, A4[1] - 29, "FAST-NUCES KARACHI")
    canvas.drawRightString(A4[0] - MARGIN, A4[1] - 29, "AL-2002  /  FALL 2026")
    canvas.setStrokeColor(colors.HexColor("#CCD8E1"))
    canvas.line(MARGIN, 38, A4[0] - MARGIN, 38)
    canvas.drawString(MARGIN, 25, "Attack-Path Analyzer and Remediation Planner")
    canvas.drawRightString(A4[0] - MARGIN, 25, f"{document.page:02d}")
    canvas.restoreState()


def render_report(source: Path, output: Path) -> int:
    """Write the report only after confirming the academic page count."""
    pdf = BytesIO()
    document = SimpleDocTemplate(
        pdf, pagesize=A4, leftMargin=MARGIN - 6, rightMargin=MARGIN - 6,
        topMargin=55, bottomMargin=55,
        title="Attack-Path Analyzer and Remediation Planner",
        author="OpenAI Codex (AI-assisted build)",
        subject="AL-2002 Artificial Intelligence Laboratory, Fall 2026",
    )
    document.build(_flowables(source), onFirstPage=_page, onLaterPages=_page)
    if not 8 <= document.page <= 10:
        raise ValueError(f"Report rendered to {document.page} pages. Expected 8 to 10.")
    output.write_bytes(pdf.getvalue())
    return document.page


def main(argv: list[str] | None = None) -> int:
    """Render the academic report from the delivered Markdown source."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    source = PROJECT_ROOT / "docs" / "report.md"
    output = source.with_suffix(".pdf")
    try:
        page_count = render_report(source, output)
    except (OSError, ValueError, LayoutError) as exc:
        parser.exit(1, f"Report error: {exc}\n")
    print(f"Rendered {page_count} pages to {output.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
