from types import SimpleNamespace

from rag_agro import vectorstore
from rag_agro.schemas import Chunk, RetrievedChunk


def test_indexacao_e_busca_usam_mesmo_embedding_e_upsert(monkeypatch):
    embedding_models = []
    upserts = []
    queries = []

    class FakeCollection:
        def upsert(self, **kwargs):
            upserts.append(kwargs)

        def query(self, **kwargs):
            queries.append(kwargs)
            return {
                "documents": [["trecho"]],
                "metadatas": [[{"source": "fonte.pdf", "page": 1}]],
                "distances": [[0.1]],
            }

    class FakeClient:
        def get_or_create_collection(self, **_kwargs):
            return FakeCollection()

    monkeypatch.setattr(
        vectorstore.chromadb,
        "PersistentClient",
        lambda path: FakeClient(),
    )
    monkeypatch.setattr(
        vectorstore.embedding_functions,
        "SentenceTransformerEmbeddingFunction",
        lambda model_name: embedding_models.append(model_name) or object(),
    )
    monkeypatch.setattr(
        vectorstore,
        "settings",
        SimpleNamespace(
            chroma_dir="fake-db",
            collection_name="test",
            embedding_model="multilingual-test-model",
            top_k=4,
        ),
    )

    vectorstore.add_chunks(
        [Chunk(id="stable-id", text="trecho", metadata={"source": "fonte.pdf", "page": 1})]
    )
    found = vectorstore.search("consulta", k=1)

    assert embedding_models == ["multilingual-test-model", "multilingual-test-model"]
    assert upserts[0]["ids"] == ["stable-id"]
    assert queries[0]["query_texts"] == ["consulta"]
    assert len(found) == 1
    assert isinstance(found[0], RetrievedChunk)
    assert found[0].source == "fonte.pdf"
    assert found[0].page == 1
