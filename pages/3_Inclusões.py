# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.ui import barra_lateral
from app.exportacao import exportar_excel
from app import db

st.set_page_config(page_title="Inclusões do Mês — Unimed", layout="wide")
barra_lateral()
st.header("3 · Inclusões no Mês de Referência")

if "df_inc" not in st.session_state:
    st.warning("Nenhuma auditoria carregada. Acesse **1 · Importação**.")
    st.stop()

df_inc  = st.session_state.get("df_inc",  pd.DataFrame())
periodo = st.session_state.get("periodo", "")
df      = st.session_state.get("df_audit", pd.DataFrame())

st.subheader(f"Período: {periodo}")

if df_inc is None or df_inc.empty:
    st.info(f"Nenhum funcionário incluído no plano em **{periodo}** (sem data de inclusão coincidindo com o período).")
    st.stop()

st.success(f"**{len(df_inc)}** funcionário(s) incluído(s) no plano em {periodo}")

# ── Tabela ─────────────────────────────────────────────────────────────────
COLS = [
    "Funcionário", "Departamento", "Dt. Admissão", "Data Inclusão",
    "Período", "Valor Fatura", "Valor Contrato", "Tem Direito", "Contrato",
]
cols_ok = [c for c in COLS if c in df_inc.columns]

df_tab = df_inc[cols_ok].copy()

def _brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    except Exception:
        return "—"

for col in ["Valor Fatura", "Valor Contrato"]:
    if col in df_tab.columns:
        df_tab[col] = df_tab[col].apply(_brl)

st.dataframe(df_tab, use_container_width=True, hide_index=True)

# ── Observação financeira ───────────────────────────────────────────────────
st.divider()
st.info("""
**Observação para ocorrência financeira**

Funcionários incluídos no mês de referência podem gerar cobrança **proporcional ou retroativa**
dependendo da data de inclusão. Verifique se o valor cobrado pela Unimed corresponde aos dias
de cobertura e ao valor previsto no contrato antes de aprovar o lançamento.
""")

# ── Export ──────────────────────────────────────────────────────────────────
aid = st.session_state.get("auditoria_id")
df_just_raw = db.carregar_justificativas(aid) if aid else {}
df_just = pd.DataFrame()
if df_just_raw:
    rows_just = [{"Funcionário": f, "Justificativa": j} for f, j in df_just_raw.items()]
    df_just = pd.DataFrame(rows_just)

excel_bytes = exportar_excel(df, df_inc, df_just, periodo)
st.download_button(
    "📥 Exportar Excel (Inclusões + Auditoria)",
    data=excel_bytes,
    file_name=f"inclusoes_unimed_{periodo.replace('/', '_')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
