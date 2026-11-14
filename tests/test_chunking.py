import pytest

from rag_agro.chunking import make_chunks, split_text


def test_respeita_tamanho_maximo():
    text = "Frase de teste sobre soja. " * 200
    chunks = split_text(text, chunk_size=300, overlap=50)
    assert all(len(c) <= 300 for c in chunks)


def test_texto_curto_vira_um_chunk():
    assert split_text("Milho em alta.", 300, 50) == ["Milho em alta."]


def test_overlap_invalido():
    with pytest.raises(ValueError):
        split_text("abc", chunk_size=100, overlap=100)


def test_ids_deterministicos():
    pages = [{"text": "Soja. " * 100, "source": "a.pdf", "page": 1}]
    first = [c.id for c in make_chunks(pages, 200, 20)]
    second = [c.id for c in make_chunks(pages, 200, 20)]
    assert first == second
    assert len(set(first)) == len(first)


def test_metadados_preservados():
    pages = [
        {"text": "Soja. " * 50, "source": "b.pdf", "page": 7},
        {"text": "Milho. " * 50, "source": "c.pdf", "page": 2},
    ]
    chunks = make_chunks(pages, 80, 10)
    assert chunks
    assert all(chunk.metadata["source"] for chunk in chunks)
    assert all(isinstance(chunk.metadata["page"], int) for chunk in chunks)


def test_preserva_metadados_documentais_derivados():
    pages = [
        {
            "text": "Estimativa de soja.",
            "source": "conab_2026.pdf",
            "page": 1,
            "doc_type": "conab",
            "year": 2026,
        }
    ]
    chunk = make_chunks(pages, 200, 20)[0]
    assert chunk.metadata == {
        "source": "conab_2026.pdf",
        "page": 1,
        "doc_type": "conab",
        "year": 2026,
    }


def test_overlap_preserva_o_fim_do_trecho_anterior():
    chunks = split_text("0123456789ABCDEFGHIJ", chunk_size=10, overlap=3)
    assert chunks[1].startswith(chunks[0][-3:])


def test_prefere_corte_em_fim_de_paragrafo():
    text = "Primeiro parágrafo com uma frase.\n\nSegundo parágrafo com outra frase."
    chunks = split_text(text, chunk_size=42, overlap=0)
    assert chunks[0] == "Primeiro parágrafo com uma frase."
    assert chunks[1] == "Segundo parágrafo com outra frase."
