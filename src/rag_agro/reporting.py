"""Gera relatórios para download a partir da resposta e das fontes recuperadas."""

from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from rag_agro.schemas import Answer


def _timestamp() -> str:
    """Retorna a data e hora local para identificar a geração do relatório."""
    return datetime.now().astimezone().strftime("%d/%m/%Y %H:%M %Z")


def _safe_cell(value: str) -> str:
    """Evita que conteúdo exportado seja interpretado como fórmula no Excel."""
    clean = value[:32_000]
    if clean.startswith(("=", "+", "-", "@")):
        return "'" + clean
    return clean


def build_excel_report(answer: Answer, question: str) -> bytes:
    """Cria um Excel com a resposta e os trechos usados como evidência."""
    workbook = Workbook()
    summary = workbook.active
    summary.title = "Resposta"
    summary.append(["Relatório RAG Agro"])
    summary.append(["Gerado em", _timestamp()])
    summary.append(["Pergunta", _safe_cell(question)])
    summary.append(["Resposta", _safe_cell(answer.text)])
    summary.column_dimensions["A"].width = 24
    summary.column_dimensions["B"].width = 100
    for row in summary.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    summary["A1"].font = Font(bold=True, size=16, color="FFFFFF")
    summary["A1"].fill = PatternFill("solid", fgColor="356859")
    summary.row_dimensions[4].height = 110

    evidence = workbook.create_sheet("Trechos usados")
    evidence.append(["Arquivo", "Página/registro", "Similaridade", "Trecho"])
    for cell in evidence[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="356859")
    for chunk in answer.sources:
        evidence.append(
            [chunk.source, chunk.page, chunk.score, _safe_cell(chunk.text)]
        )
    for row in evidence.iter_rows(min_row=2):
        row[3].alignment = Alignment(vertical="top", wrap_text=True)
    for column, width in {"A": 42, "B": 12, "C": 16, "D": 100}.items():
        evidence.column_dimensions[column].width = width
    if answer.web_sources:
        web_sources = workbook.create_sheet("Fontes online")
        web_sources.append(["Fonte", "URL", "Consultado em"])
        for cell in web_sources[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="356859")
        for source in answer.web_sources:
            web_sources.append(
                [_safe_cell(source.title), _safe_cell(source.url), source.accessed_at]
            )
            web_sources.cell(web_sources.max_row, 2).hyperlink = source.url
        web_sources.column_dimensions["A"].width = 48
        web_sources.column_dimensions["B"].width = 100
        web_sources.column_dimensions["C"].width = 24
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def build_pdf_report(answer: Answer, question: str) -> bytes:
    """Cria um PDF com a resposta e as passagens que a fundamentam."""
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Relatório RAG Agro",
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle("BodyPt", parent=styles["BodyText"], leading=15, alignment=TA_LEFT)
    story = [
        Paragraph("Relatório RAG Agro", styles["Title"]),
        Paragraph(f"Gerado em {_timestamp()}", styles["Italic"]),
        Spacer(1, 8 * mm),
        Paragraph("Pergunta", styles["Heading2"]),
        Paragraph(escape(question).replace("\n", "<br/>"), body),
        Spacer(1, 4 * mm),
        Paragraph("Resposta", styles["Heading2"]),
        Paragraph(escape(answer.text).replace("\n", "<br/>"), body),
        Spacer(1, 4 * mm),
        Paragraph("Trechos usados", styles["Heading2"]),
    ]
    for chunk in answer.sources:
        reference = "registro" if chunk.source.lower().endswith(".csv") else "p."
        story.extend(
            [
                Paragraph(
                    f"<b>{escape(chunk.source)}, {reference} {chunk.page}</b> "
                    f"— similaridade {chunk.score:.3f}",
                    body,
                ),
                Paragraph(escape(chunk.text).replace("\n", "<br/>"), body),
                Spacer(1, 3 * mm),
            ]
        )
    if answer.web_sources:
        story.extend(
            [Spacer(1, 4 * mm), Paragraph("Fontes online", styles["Heading2"])]
        )
        for source in answer.web_sources:
            safe_url = escape(source.url, {'"': "&quot;"})
            story.append(
                Paragraph(
                    f'<link href="{safe_url}">{escape(source.title)}</link> — '
                    f"{escape(source.url)} (consultado em {escape(source.accessed_at)})",
                    body,
                )
            )
    document.build(story)
    return output.getvalue()
