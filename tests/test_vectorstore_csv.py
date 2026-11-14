from rag_agro import vectorstore


class FakeCollection:
    def get(self, include):
        assert include == ["documents", "metadatas"]
        return {
            "documents": [
                "Data da operação: 14/11/2026; Produto: SOJA; Quantidade: 14,42",
                "Data da operação: 14/11/2026; Produto: MAIZ; Quantidade: 80,11",
                "Data da operação: 14/10/2026; Produto: SOJA; Quantidade: 10,00",
            ],
            "metadatas": [
                {"source": "operaciones.csv", "page": 1},
                {"source": "operaciones.csv", "page": 2},
                {"source": "operaciones.csv", "page": 3},
            ],
        }


def test_search_csv_retorna_todas_as_linhas_do_produto_e_periodo(monkeypatch):
    monkeypatch.setattr(vectorstore, "get_collection", FakeCollection)
    found = vectorstore.search_csv("relatório de soja para novembro de 2026")
    assert len(found) == 1
    assert found[0].page == 1
    assert "SOJA" in found[0].text


def test_search_csv_reconhece_milho_e_nao_filtra_sem_periodo(monkeypatch):
    monkeypatch.setattr(vectorstore, "get_collection", FakeCollection)
    found = vectorstore.search_csv("dados de milho")
    assert len(found) == 1
    assert found[0].page == 2
