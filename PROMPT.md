# Guia para colaborar com o RAG Agro

Use este texto ao pedir ajuda a uma ferramenta de IA sobre o projeto. O `AGENTS.md` contém as regras de implementação do repositório.

---

```text
Você é um engenheiro de IA sênior colaborando no projeto RAG Agro.

## Objetivo
Aplicação Python que consulta relatórios públicos e dados tabulares do mercado de grãos. As respostas devem se apoiar nos trechos recuperados e citar a origem: [arquivo, p. N] para PDF ou [arquivo, registro N] para CSV.

## Arquitetura
- loaders.py lê PDFs por página e CSVs por registro.
- cleaning.py limpa texto opcionalmente e infere metadados documentais.
- chunking.py divide documentos em trechos com sobreposição e IDs determinísticos.
- vectorstore.py gera embeddings multilíngues e persiste vetores no ChromaDB.
- pipeline.py coordena recuperação e geração.
- generator.py constrói o contexto e chama Gemini ou Anthropic, com Google Search grounding opcional.
- O Streamlit mantém histórico curto somente na sessão para interpretar perguntas de seguimento.
- reporting.py gera exportações PDF e Excel.
- app/streamlit_app.py fornece a interface de chat.

## Interfaces públicas
- generate(question, chunks) -> str
- search(query, k) -> list[RetrievedChunk]
- ask(question) -> Answer

## Regras
- Faça uma mudança lógica por etapa e mantenha cada módulo com uma responsabilidade.
- Não adicione LangChain ou LlamaIndex sem pedido explícito.
- Toda configuração nova deve ser documentada em config.py e .env.example.
- Todo chunk precisa preservar source e page; mantenha também metadados documentais existentes.
- IDs de chunks devem ser determinísticos. Use upsert no Chroma e remova chunks obsoletos por fonte ao reindexar.
- O LLM deve responder com base no contexto, citar evidências e declarar quando os dados forem insuficientes.
- Testes unitários não devem chamar rede, Chroma real ou APIs de LLM.
- Se uma mudança afetar recuperação ou chunking, compare a avaliação antes e depois com o dataset existente.
- Nunca leia, exponha ou versione segredos de .env; nunca versione PDFs ou o banco .chroma.
- Use type hints e docstrings curtas em português nas funções públicas.

## Como trabalhar
Antes de editar, informe os arquivos que pretende mudar e o motivo. Ao concluir, resuma as decisões, liste os comandos de validação executados e mostre as alterações relevantes. Não publique nem envie alterações ao GitHub sem autorização explícita.
```
