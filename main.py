# -*- coding: utf-8 -*-
import streamlit as st
from version import __version__
from app.ui import barra_lateral

st.set_page_config(
    page_title=f"Auditoria Unimed {__version__}",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

barra_lateral()
st.title("🏥 Auditoria Unimed")
st.markdown("""
Use o menu lateral para navegar:

| Página | Função |
|--------|--------|
| **1 · Importação** | Carregue os arquivos e processe a auditoria |
| **2 · Inclusões** | Novos beneficiários incluídos no período |
| **3 · Exclusões** | Quem saiu da fatura vs mês anterior |
| **4 · Auditoria Exclusões Indevidas** | Desligados ainda cobrados — prejuízo estimado |
| **5 · Auditoria** | Tabela completa com filtros, KPIs e exportação |
| **6 · Aprovação** | Justifique pendências e aprove o fechamento |
| **7 · Histórico** | Consulte e recarregue auditorias anteriores |
""")

if "df_audit" in st.session_state and st.session_state["df_audit"] is not None:
    periodo = st.session_state.get("periodo", "")
    stats   = st.session_state.get("stats", {})
    st.info(
        f"**Auditoria carregada:** {periodo} · "
        f"{stats.get('ok', 0)} OK · "
        f"{stats.get('inconsistente', 0)} inconsistências"
    )
