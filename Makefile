.PHONY: install ingest app eval test lint

install:
	pip install -e ".[dev]"

ingest:
	python -m rag_agro.ingest data/raw

app:
	streamlit run app/streamlit_app.py

eval:
	python evals/run_eval.py

test:
	pytest -q

lint:
	ruff check .
