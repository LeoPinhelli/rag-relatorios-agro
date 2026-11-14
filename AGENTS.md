# AGENTS.md

Instruções para agentes de IA (Claude Code, Codex, Cursor) que trabalham neste repositório.

## Visão geral

RAG em Python que responde perguntas sobre relatórios públicos do mercado de grãos
(Conab, USDA), citando arquivo e página. Duas fases:

1. **Indexação** (`make ingest`): PDF → páginas → chunks → embeddings → ChromaDB.
2. **Consulta** (`make app`): pergunta → busca top-k → prompt com contexto → Claude responde.

## Mapa do código

| Arquivo | Responsabilidade | Depende de |
|---|---|---|
| `src/rag_agro/config.py` | Lê `.env` em `Settings` imutável | dotenv |
| `src/rag_agro/schemas.py` | `Chunk`, `RetrievedChunk`, `Answer` | — |
| `src/rag_agro/loaders.py` | PDF → `[{text, source, page}]` | pypdf |
| `src/rag_agro/chunking.py` | Divide texto com overlap; IDs determinísticos | schemas |
| `src/rag_agro/vectorstore.py` | Coleção Chroma, `add_chunks`, `search` | chromadb, sentence-transformers |
| `src/rag_agro/generator.py` | `SYSTEM_PROMPT`, `build_context`, `generate` | anthropic |
| `src/rag_agro/pipeline.py` | `ask(question)` → `Answer` | vectorstore, generator |
| `src/rag_agro/ingest.py` | CLI: `python -m rag_agro.ingest <pasta>` | loaders, chunking, vectorstore |
| `app/streamlit_app.py` | Interface de chat | pipeline |
| `evals/run_eval.py` | Hit rate@k, MRR e JSON de resultados | vectorstore |

Fluxo de dados: `loaders → chunking → vectorstore` (indexação) e `pipeline → vectorstore → generator` (consulta).

## Comandos

```bash
make install   # pip install -e ".[dev]"
make ingest    # indexa data/raw/*.pdf
make app       # abre o chat em localhost:8501
make eval      # hit rate@k + MRR; salva JSON em evals/results/
make test      # pytest
make lint      # ruff
```

## Configuração

Tudo em `.env` (modelo em `.env.example`). Nunca coloque valores fixos no código.
Variáveis: `ANTHROPIC_API_KEY`, `LLM_MODEL`, `EMBEDDING_MODEL`, `CHROMA_DIR`,
`COLLECTION_NAME`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K`.

## Regras obrigatórias

- **Um módulo, uma etapa.** Não misture leitura, chunking, busca e geração no mesmo arquivo.
- **Toda configuração nova vai em `config.py` e `.env.example`.**
- **Todo chunk carrega `source` e `page`.** Sem isso, a citação quebra.
- **IDs de chunk são determinísticos.** Use hash de `source-page-índice`. Nunca `uuid4`.
- **Use `upsert`, não `add`,** no Chroma. Reindexar não pode duplicar.
- **O prompt proíbe inventar.** Qualquer mudança em `SYSTEM_PROMPT` mantém: responder só com o contexto, citar `[arquivo, p. N]`, dizer "Não encontrei" quando faltar dado.
- **Nunca faça commit de `.env`, `.chroma/` ou PDFs.**
- **Type hints em toda função pública.** Docstring curta em português.

## Testes

- Testes unitários não chamam rede, Chroma nem API. Use stubs (ver `tests/test_prompt.py`).
- Toda função nova em `chunking.py` ou `generator.py` ganha teste.
- Antes de concluir uma tarefa: `make lint && make test`.

## Como fazer mudanças comuns

**Trocar o LLM:** edite só `generator.py`. Mantenha a assinatura
`generate(question, chunks) -> str`.

**Trocar o banco vetorial:** edite só `vectorstore.py`. Mantenha
`add_chunks(chunks)` e `search(query, k) -> list[RetrievedChunk]`.

**Novo formato de documento (DOCX, HTML):** crie função em `loaders.py` que
retorne `[{text, source, page}]`. Registre em `load_folder`.

**Mudar chunk_size/overlap:** altere o `.env`, apague `.chroma/`, rode
`make ingest` e `make eval`. Registre o resultado na tabela do README.

**Busca híbrida ou reranking:** implemente em `vectorstore.py` (ou novo
`retrieval.py`), mantendo o retorno `list[RetrievedChunk]`. Compare com `make eval`.

**Avaliação:** `evals/run_eval.py` calcula hit rate@k e MRR sem chamar o LLM. Cada execução
salva métricas e fontes recuperadas em `evals/results/AAAA-MM-DD.json`. Mantenha `expected_source`
em `evals/dataset.jsonl` igual aos nomes dos arquivos do corpus; fontes esperadas ausentes tornam
a linha de base inválida.

## Convenções de commit

Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.
Um commit por mudança lógica.

## Não faça

- Não adicione LangChain/LlamaIndex sem pedido explícito. O projeto é didático e sem framework.
- Não altere a interface pública dos módulos sem atualizar quem a usa e os testes.
- Não reduza a cobertura de testes.
