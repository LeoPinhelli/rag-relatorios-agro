from rag_agro.cleaning import clean_pages


def test_remove_cabecalho_e_rodape_repetidos_nas_margens():
    pages = []
    for number, crop in enumerate(("soja", "milho", "trigo"), start=1):
        pages.append(
            {
                "source": "conab_boletim_2026.pdf",
                "page": number,
                "text": (
                    "Boletim Conab\nSafra 2026\nAcompanhamento mensal\n"
                    f"Dados específicos de {crop}\nÁrea e produção\nPreços de referência\n"
                    f"Página {number}\nConab - publicação oficial"
                ),
            }
        )

    cleaned = clean_pages(pages)

    assert all("Boletim Conab" not in page["text"] for page in cleaned)
    assert all("Conab - publicação oficial" not in page["text"] for page in cleaned)
    assert "Dados específicos de soja" in cleaned[0]["text"]
    assert "Dados específicos de milho" in cleaned[1]["text"]


def test_junta_palavra_hifenizada_e_normaliza_espacos():
    pages = [
        {
            "source": "conab_2026.pdf",
            "page": 1,
            "text": "A produ-\nção   de soja.\n\n\nÁrea   total.",
        }
    ]

    cleaned = clean_pages(pages)[0]["text"]

    assert cleaned == "A produção de soja.\n\nÁrea total."


def test_infere_tipo_e_ano_dos_nomes_conhecidos():
    pages = [
        {"text": "Conab", "source": "e-book_boletim-de-safras_2026.pdf", "page": 1},
        {"text": "WASDE", "source": "wasde1126.pdf", "page": 2},
        {"text": "CSV SIO", "source": "operaciones_informadas.csv", "page": 1},
        {"text": "Sem convenção", "source": "documento.pdf", "page": 5},
    ]

    cleaned = clean_pages(pages)

    assert cleaned[0]["doc_type"] == "conab"
    assert cleaned[0]["year"] == 2026
    assert cleaned[1]["doc_type"] == "usda"
    assert cleaned[1]["year"] == 2026
    assert cleaned[2]["doc_type"] == "sio_granos"
    assert "doc_type" not in cleaned[3]
    assert "year" not in cleaned[3]


def test_mantem_dados_originais_quando_limpeza_nao_e_ativada():
    original = [{
        "text": "A produ-\nção   de soja.",
        "source": "conab_2026.pdf",
        "page": 1,
    }]

    cleaned = clean_pages(original, enabled=False)

    assert cleaned[0]["text"] == original[0]["text"]
    assert cleaned[0]["doc_type"] == "conab"
