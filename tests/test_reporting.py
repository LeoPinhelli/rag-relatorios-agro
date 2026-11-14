from io import BytesIO

from openpyxl import load_workbook

from rag_agro.reporting import build_excel_report, build_pdf_report
from rag_agro.schemas import Answer, RetrievedChunk, WebSource


def _answer() -> Answer:
    return Answer(
        text="A produção estimada foi elevada.",
        sources=[
            RetrievedChunk(
                text="A produção foi revisada para 49 milhões de toneladas.",
                source="boletim.pdf",
                page=12,
                score=0.92,
            )
        ],
    )


def test_pdf_exporta_resposta_e_citacao():
    pdf = build_pdf_report(_answer(), "Qual foi a revisão da estimativa?")

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500


def test_excel_exporta_resposta_e_trechos():
    xlsx = build_excel_report(_answer(), "Qual foi a revisão da estimativa?")
    workbook = load_workbook(BytesIO(xlsx), read_only=True)

    assert workbook.sheetnames == ["Resposta", "Trechos usados"]
    assert workbook["Resposta"]["B4"].value == "A produção estimada foi elevada."
    assert workbook["Trechos usados"]["A2"].value == "boletim.pdf"
    assert workbook["Trechos usados"]["B2"].value == 12


def test_relatorios_incluem_referencias_online():
    answer = _answer()
    answer.web_sources = [WebSource("Relatório Conab", "https://www.conab.gov.br/relatorio.pdf")]

    workbook = load_workbook(
        BytesIO(build_excel_report(answer, "Pergunta")), read_only=False
    )
    pdf = build_pdf_report(answer, "Pergunta")

    assert workbook.sheetnames == ["Resposta", "Trechos usados", "Fontes online"]
    assert workbook["Fontes online"]["B2"].hyperlink.target == (
        "https://www.conab.gov.br/relatorio.pdf"
    )
    assert pdf.startswith(b"%PDF")
