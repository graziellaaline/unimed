# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.ui import barra_lateral
from app.exportacao import exportar_excel
from app import db

st.set_page_config(page_title="Auditoria — Unimed", layout="wide")
barra_lateral()
st.header("2 · Resultado da Auditoria")

if "df_audit" not in st.session_state or st.session_state["df_audit"] is None:
    st.warning("Nenhuma auditoria carregada. Acesse **1 · Importação** ou **4 · Histórico**.")
    st.stop()

df      = st.session_state["df_audit"].copy()
stats   = st.session_state.get("stats", {})
periodo = st.session_state.get("periodo", "")
cliente = st.session_state.get("cliente", "")

st.subheader(f"Período: {periodo}" + (f" · {cliente}" if cliente else ""))

# ── KPIs ─────────────────────────────────────────────────────────────────────
def _brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    except Exception:
        return "—"

k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
k1.metric("Total",           stats.get("total", 0))
k2.metric("✅ OK",           stats.get("ok", 0))
k3.metric("⚠️ Inconsist.",   stats.get("inconsistente", 0))
k4.metric("Na Fatura",       stats.get("na_fatura", 0))
k5.metric("Na Compra",       stats.get("na_compra", 0))
k6.metric("Total Fatura",    _brl(stats.get("total_fatura", 0)))
k7.metric("Total Compra",    _brl(stats.get("total_compra", 0)))

st.divider()

# ── Filtros ───────────────────────────────────────────────────────────────────
with st.expander("🔍 Filtros", expanded=True):
    f1, f2, f3, f4, f5 = st.columns(5)

    status_vals = ["Todos"] + sorted(df["Status"].dropna().unique().tolist())
    f_status = f1.selectbox("Status", status_vals)

    if "Departamento" in df.columns:
        deps = ["Todos"] + sorted(df["Departamento"].dropna().unique().tolist())
        f_dep = f2.selectbox("Departamento", deps)
    else:
        f_dep = "Todos"

    f_nome = f3.text_input("Funcionário (parte do nome)")

    inc_opts = ["Todos", "Sim", "Não"]
    f_fatura = f4.selectbox("Está na Fatura", inc_opts)
    f_compra = f5.selectbox("Está na Compra", inc_opts)

df_f = df.copy()
if f_status != "Todos":
    df_f = df_f[df_f["Status"] == f_status]
if f_dep != "Todos" and "Departamento" in df_f.columns:
    df_f = df_f[df_f["Departamento"] == f_dep]
if f_nome:
    df_f = df_f[df_f["Funcionário"].str.contains(f_nome, case=False, na=False)]
if f_fatura != "Todos":
    df_f = df_f[df_f["Está na Fatura"] == f_fatura]
if f_compra != "Todos":
    df_f = df_f[df_f["Está na Compra"] == f_compra]

st.caption(f"**{len(df_f)}** registro(s) exibido(s)")

# ── Tabela ────────────────────────────────────────────────────────────────────
COLS_EX = [
    "Funcionário", "Departamento",
    "Tem Direito", "Está na Fatura", "Está na Compra",
    "Valor Contrato", "Valor Empresa (Compra)", "Valor Fatura", "Valor Compra Total",
    "Dif. Contrato x Compra", "Dif. Fatura x Compra",
    "Data Inclusão", "Dt. Admissão",
    "Status", "Inconsistência", "Ação Sugerida",
]
cols_ok = [c for c in COLS_EX if c in df_f.columns]

df_tab = df_f[cols_ok].copy()
for col in ["Valor Fatura", "Valor Empresa (Compra)", "Valor Compra Total",
            "Valor Contrato", "Dif. Contrato x Compra", "Dif. Fatura x Compra"]:
    if col in df_tab.columns:
        df_tab[col] = df_tab[col].apply(
            lambda v: _brl(v) if pd.notna(v) else "—"
        )

def _cor_linha(row):
    s = row.get("Status", "")
    if s == "Inconsistente":
        return ["background-color:#f8d7da"] * len(row)
    if s == "OK":
        return ["background-color:#d4edda"] * len(row)
    return [""] * len(row)

st.dataframe(
    df_tab.style.apply(_cor_linha, axis=1),
    use_container_width=True,
    height=520,
    hide_index=True,
)

# ── Exportação ────────────────────────────────────────────────────────────────
st.divider()
aid = st.session_state.get("auditoria_id")
df_inc  = st.session_state.get("df_inc",  pd.DataFrame())
df_just_raw = db.carregar_justificativas(aid) if aid else {}

# Monta df de justificativas para export
if df_just_raw:
    rows_just = []
    for func, just in df_just_raw.items():
        desc_row = df[df["Funcionário"] == func]
        desc = desc_row["Inconsistência"].iloc[0] if not desc_row.empty and "Inconsistência" in desc_row.columns else ""
        rows_just.append({"Funcionário": func, "Inconsistência": desc, "Justificativa": just})
    df_just = pd.DataFrame(rows_just)
else:
    df_just = pd.DataFrame()

excel_bytes = exportar_excel(df, df_inc, df_just, periodo)
st.download_button(
    "📥 Exportar Excel completo",
    data=excel_bytes,
    file_name=f"auditoria_unimed_{periodo.replace('/', '_')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="secondary",
)
