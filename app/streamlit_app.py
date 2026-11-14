"""Interface de chat. Rode com: streamlit run app/streamlit_app.py"""

from datetime import datetime

import streamlit as st

from rag_agro.pipeline import ask
from rag_agro.reporting import build_excel_report, build_pdf_report

st.set_page_config(page_title="RAG Agro", page_icon="🌾")
st.title("🌾 Pergunte aos relatórios de grãos")
st.caption("Respostas baseadas em relatórios públicos, com fonte citada.")

if "history" not in st.session_state:
    st.session_state.history = []

for role, content in st.session_state.history:
    st.chat_message(role).markdown(content)

if question := st.chat_input("Ex.: Qual a estimativa de safra de soja?"):
    st.chat_message("user").markdown(question)
    with st.spinner("Buscando nos relatórios..."):
        answer = ask(question)
    with st.chat_message("assistant"):
        st.markdown(answer.text)
        if answer.report_requested:
            file_name = f"rag_agro_{datetime.now():%Y%m%d_%H%M%S}"
            pdf_col, excel_col = st.columns(2)
            with pdf_col:
                st.download_button(
                    "Baixar relatório PDF",
                    data=build_pdf_report(answer, question),
                    file_name=f"{file_name}.pdf",
                    mime="application/pdf",
                    key=f"pdf_{file_name}",
                )
            with excel_col:
                st.download_button(
                    "Baixar dados Excel",
                    data=build_excel_report(answer, question),
                    file_name=f"{file_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"xlsx_{file_name}",
                )
        with st.expander("Trechos usados"):
            for c in answer.sources:
                reference = (
                    f"registro {c.page}"
                    if c.source.lower().endswith(".csv")
                    else f"p. {c.page}"
                )
                st.markdown(f"**{c.source}, {reference}** · similaridade {c.score}")
                st.caption(c.text[:400] + "...")
    st.session_state.history += [("user", question), ("assistant", answer.text)]
