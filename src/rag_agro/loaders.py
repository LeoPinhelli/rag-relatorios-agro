"""Etapa 1: carregar PDFs, página por página, guardando a origem."""

import csv
import io
from pathlib import Path

from pypdf import PdfReader


def load_pdf(path: Path) -> list[dict]:
    """Retorna uma lista de páginas: texto + metadados (arquivo e página)."""
    reader = PdfReader(path)
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append({"text": text, "source": path.name, "page": number})
    return pages


def load_csv(path: Path) -> list[dict]:
    """Carrega operações CSV como registros citáveis, preservando a linha de origem."""
    raw = path.read_bytes()
    encodings = ("utf-16-le", "utf-8-sig", "utf-16", "cp1252", "latin-1")
    if b"\x00" not in raw[:200]:
        encodings = ("utf-8-sig", "utf-16", "utf-16-le", "cp1252", "latin-1")
    text = None
    for encoding in encodings:
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError(f"Não foi possível decodificar {path.name}")

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t,")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ";"
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    records: list[dict] = []
    labels = {
        "FECHA OPERACION": "Data da operação",
        "FECHA CONCERTACION": "Data de concertação",
        "NRO. OPERACION": "Número da operação",
        "OPERACION": "Operação",
        "TIPO": "Modalidade",
        "PRECIO": "Tipo de preço",
        "PRODUCTO": "Produto",
        "CANT. (TN)": "Quantidade (toneladas)",
        "CALIDAD": "Qualidade",
        "PROCEDENCIA PCIA": "Província de origem",
        "PROCEDENCIA LOCALID.": "Localidade de origem",
        "PRECIO/TN MONEDA": "Moeda do preço por tonelada",
        "PRECIO/TN MONTO": "Preço por tonelada",
        "LUGAR ENTREGA": "Local de entrega",
        "CONDICION PAGO": "Condição de pagamento",
        "COSECHA": "Safra",
    }
    for number, row in enumerate(reader, start=1):
        fields = []
        for key, value in row.items():
            if not key or value is None or not value.strip():
                continue
            label = labels.get(key.strip(), key.strip().rstrip("?"))
            fields.append(f"{label}: {value.strip()}")
        if fields:
            records.append({"text": "; ".join(fields), "source": path.name, "page": number})
    return records


def load_folder(folder: Path) -> list[dict]:
    pages: list[dict] = []
    for pdf in sorted(folder.glob("*.pdf")):
        pages.extend(load_pdf(pdf))
    for csv_file in sorted(folder.glob("*.csv")):
        pages.extend(load_csv(csv_file))
    return pages
