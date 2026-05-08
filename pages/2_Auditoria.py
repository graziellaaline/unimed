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

graficos_container = st.container()

# ── Filtros ───────────────────────────────────────────────────────────────────
with st.expander("🔍 Filtros", expanded=True):
    f1, f2, f3, f4 = st.columns(4)
    f5, f6, f7 = st.columns(3)

    status_vals = ["Todos"] + sorted(df["Status"].dropna().unique().tolist())
    f_status = f1.selectbox("Status", status_vals)

    empresas = ["Todos"]
    if "Empresa" in df.columns:
        empresas += sorted([v for v in df["Empresa"].dropna().unique().tolist() if str(v).strip()])
    f_empresa = f2.selectbox("Empresa", empresas)

    deps = ["Todos"]
    if "Departamento" in df.columns:
        deps += sorted([v for v in df["Departamento"].dropna().unique().tolist() if str(v).strip()])
    f_dep = f3.selectbox("Departamento", deps)

    contratos_adm = ["Todos"]
    if "Contrato Adm." in df.columns:
        contratos_adm += sorted([v for v in df["Contrato Adm."].dropna().unique().tolist() if str(v).strip()])
    f_contrato_adm = f4.selectbox("Contrato Adm.", contratos_adm)

    f_nome = f5.text_input("Funcionário (parte do nome)")

    inc_opts = ["Todos", "Sim", "Não"]
    f_fatura = f6.selectbox("Está na Fatura", inc_opts)
    f_compra = f7.selectbox("Está na Compra", inc_opts)

df_f = df.copy()
if f_status != "Todos":
    df_f = df_f[df_f["Status"] == f_status]
if f_empresa != "Todos" and "Empresa" in df_f.columns:
    df_f = df_f[df_f["Empresa"] == f_empresa]
if f_dep != "Todos" and "Departamento" in df_f.columns:
    df_f = df_f[df_f["Departamento"] == f_dep]
if f_contrato_adm != "Todos" and "Contrato Adm." in df_f.columns:
    df_f = df_f[df_f["Contrato Adm."] == f_contrato_adm]
if f_nome:
    df_f = df_f[df_f["Funcionário"].str.contains(f_nome, case=False, na=False)]
if f_fatura != "Todos":
    df_f = df_f[df_f["Está na Fatura"] == f_fatura]
if f_compra != "Todos":
    df_f = df_f[df_f["Está na Compra"] == f_compra]

st.caption(f"**{len(df_f)}** registro(s) exibido(s)")

# ── Gráficos ────────────────────────────────────────────────────────────────
def _base_gastos(df_base, grupo):
    if grupo not in df_base.columns:
        return pd.DataFrame()

    cols_valor = [c for c in ["Valor Fatura", "Valor Compra Total", "Valor Contrato"] if c in df_base.columns]
    if not cols_valor:
        return pd.DataFrame()

    df_grp = df_base.copy()
    df_grp[grupo] = df_grp[grupo].fillna("").astype(str).str.strip()
    df_grp = df_grp[df_grp[grupo] != ""]
    if df_grp.empty:
        return pd.DataFrame()

    return (
        df_grp.groupby(grupo, as_index=False)[cols_valor]
        .sum()
        .sort_values("Valor Fatura" if "Valor Fatura" in cols_valor else cols_valor[0], ascending=False)
    )


def _base_desvios(df_base, grupo):
    if grupo not in df_base.columns:
        return pd.DataFrame()

    cols_desvio = [c for c in ["Dif. Contrato x Compra", "Dif. Fatura x Compra"] if c in df_base.columns]
    if not cols_desvio:
        return pd.DataFrame()

    df_grp = df_base.copy()
    df_grp[grupo] = df_grp[grupo].fillna("").astype(str).str.strip()
    df_grp = df_grp[df_grp[grupo] != ""]
    if df_grp.empty:
        return pd.DataFrame()

    for col in cols_desvio:
        if col in df_grp.columns:
            df_grp[col] = pd.to_numeric(df_grp[col], errors="coerce").fillna(0).abs()

    return (
        df_grp.groupby(grupo, as_index=False)[cols_desvio]
        .sum()
        .sort_values(cols_desvio[0], ascending=False)
    )


with graficos_container:
    st.markdown("### Gráficos de Gastos")
    g1, g2 = st.columns(2)

    with g1:
        st.markdown("**Por Departamento**")
        gastos_dep = _base_gastos(df_f, "Departamento")
        if gastos_dep.empty:
            st.caption("Sem dados de departamento para exibir.")
        else:
            st.bar_chart(gastos_dep.set_index("Departamento"), use_container_width=True)

    with g2:
        st.markdown("**Por Contrato Adm.**")
        gastos_contrato = _base_gastos(df_f, "Contrato Adm.")
        if gastos_contrato.empty:
            st.caption("Sem dados de Contrato Adm. para exibir.")
        else:
            st.bar_chart(gastos_contrato.set_index("Contrato Adm."), use_container_width=True)

    st.divider()
    st.markdown("### Gráficos de Desvio")
    d1, d2 = st.columns(2)

    with d1:
        st.markdown("**Desvio por Departamento**")
        desvios_dep = _base_desvios(df_f, "Departamento")
        if desvios_dep.empty:
            st.caption("Sem desvios por departamento para exibir.")
        else:
            st.bar_chart(desvios_dep.set_index("Departamento"), use_container_width=True)

    with d2:
        st.markdown("**Desvio por Contrato Adm.**")
        desvios_contrato = _base_desvios(df_f, "Contrato Adm.")
        if desvios_contrato.empty:
            st.caption("Sem desvios por Contrato Adm. para exibir.")
        else:
            st.bar_chart(desvios_contrato.set_index("Contrato Adm."), use_container_width=True)

    st.divider()

# ── Tabela ────────────────────────────────────────────────────────────────────
COLS_EX = [
    "Funcionário", "Empresa", "Departamento", "Contrato Adm.",
    "Dt. Admissão", "Dt. Demissão", "Dt. Elegibilidade",
    "Tem Direito", "Está na Fatura", "Está na Compra",
    "Valor Contrato", "Valor Empresa (Compra)", "Valor Fatura", "Valor Compra Total",
    "Dif. Contrato x Compra", "Dif. Fatura x Compra",
    "Data Inclusão",
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
