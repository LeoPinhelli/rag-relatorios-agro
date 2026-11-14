import csv

from rag_agro.loaders import load_csv


def test_load_csv_utf16_semicolon_preserves_record_reference(tmp_path):
    path = tmp_path / "operaciones.csv"
    with path.open("w", encoding="utf-16-le", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["PRODUCTO", "CANT. (TN)", "PRECIO/TN MONTO"])
        writer.writerow(["SOJA", "14,42", "485103,00"])
    records = load_csv(path)
    assert len(records) == 1
    assert records[0]["source"] == "operaciones.csv"
    assert records[0]["page"] == 1
    assert "Produto: SOJA" in records[0]["text"]
    assert "Quantidade (toneladas): 14,42" in records[0]["text"]
