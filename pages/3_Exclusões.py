# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.ui import barra_lateral
from app import db
from app.processamento import _norm

st.set_page_config(page_title="Exclusões do Mês — Unimed", layout="wide")
barra_lateral()
st.header("3 · Exclusões do Mês de Referência")

# ── Verificar auditoria carregada ─────────────────────────────────────────────
if "df_audit" not in st.session_state or st.session_state["df_audit"] is None:
    st.warning("Nenhuma auditoria carregada. Acesse **1 · Importação**.")
    st.stop()

df_atual  = st.session_state["df_audit"]
periodo   = st.session_state.get("periodo", "")
cliente   = st.session_state.get("cliente", "")

st.subheader(f"Período atual: {periodo}")

# ── Selecionar período de referência anterior ─────────────────────────────────
todos_periodos = db.listar_periodos()
opcoes_ant = [p for p in todos_periodos if p["periodo"] != periodo]

if not opcoes_ant:
    st.info("Não há períodos anteriores salvos para comparar. Processe ao menos dois meses.")
    st.stop()

c1, _ = st.columns([2, 4])
with c1:
    periodo_ant_sel = st.selectbox(
        "Comparar titulares com o período",
        options=[p["periodo"] for p in opcoes_ant],
        index=0,
        help="Selecione o mês anterior — quem estava nele mas não está no atual será listado como exclusão.",
    )

# ── Carregar período anterior ─────────────────────────────────────────────────
info_ant = next((p for p in opcoes_ant if p["periodo"] == periodo_ant_sel), None)
df_ant_raw, _, _ = db.carregar_auditoria(
    periodo_ant_sel, info_ant["cliente"] if info_ant else ""
)

if df_ant_raw is None or df_ant_raw.empty:
    st.error(f"Não foi possível carregar os dados de {periodo_ant_sel}.")
    st.stop()

# ── Comparação de titulares ───────────────────────────────────────────────────
def _norm_nome(n) -> str:
    return _norm(str(n or ""))


def _na_fatura(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna apenas as linhas em que o funcionário consta na fatura."""
    if "Está na Fatura" in df.columns:
        return df[df["Está na Fatura"] == "Sim"].copy()
    if "_na_fatura" in df.columns:
        return df[df["_na_fatura"].astype(bool)].copy()
    return pd.DataFrame()


fat_atual = _na_fatura(df_atual)
fat_ant   = _na_fatura(df_ant_raw)

if fat_ant.empty:
    st.info(f"Não há titulares na fatura registrados para {periodo_ant_sel}.")
    st.stop()

nomes_atuais = {_norm_nome(f) for f in fat_atual["Funcionário"].dropna()}

mask     = fat_ant["Funcionário"].apply(lambda f: _norm_nome(f) not in nomes_atuais)
df_exc   = fat_ant[mask].copy()

# ── Resumo ────────────────────────────────────────────────────────────────────
st.divider()

m1, m2, m3 = st.columns(3)
m1.metric(f"Titulares em {periodo_ant_sel}",  len(fat_ant))
m2.metric(f"Titulares em {periodo}",          len(fat_atual))
m3.metric("Exclusões identificadas",           len(df_exc),
          delta=f"-{len(df_exc)}" if len(df_exc) else None,
          delta_color="inverse")

st.divider()

if df_exc.empty:
    st.success(f"Nenhuma exclusão identificada — todos os titulares de {periodo_ant_sel} continuam na fatura de {periodo}.")
    st.stop()

st.warning(
    f"**{len(df_exc)}** titular(es) que constavam na fatura de **{periodo_ant_sel}** "
    f"não aparecem mais na fatura de **{periodo}**."
)

# ── Filtros ───────────────────────────────────────────────────────────────────
with st.expander("🔍 Filtros", expanded=True):
    f1, f2, f3 = st.columns(3)

    empresas = ["Todos"]
    if "Empresa" in df_exc.columns:
        empresas += sorted([v for v in df_exc["Empresa"].dropna().unique() if str(v).strip()])
    f_empresa = f1.selectbox("Empresa", empresas)

    deps = ["Todos"]
    if "Departamento" in df_exc.columns:
        deps += sorted([v for v in df_exc["Departamento"].dropna().unique() if str(v).strip()])
    f_dep = f2.selectbox("Departamento", deps)

    contratos = ["Todos"]
    if "Contrato Adm." in df_exc.columns:
        contratos += sorted([v for v in df_exc["Contrato Adm."].dropna().unique() if str(v).strip()])
    f_contrato = f3.selectbox("Contrato Adm.", contratos)

df_exc_f = df_exc.copy()
if f_empresa != "Todos" and "Empresa" in df_exc_f.columns:
    df_exc_f = df_exc_f[df_exc_f["Empresa"] == f_empresa]
if f_dep != "Todos" and "Departamento" in df_exc_f.columns:
    df_exc_f = df_exc_f[df_exc_f["Departamento"] == f_dep]
if f_contrato != "Todos" and "Contrato Adm." in df_exc_f.columns:
    df_exc_f = df_exc_f[df_exc_f["Contrato Adm."] == f_contrato]

st.caption(f"**{len(df_exc_f)}** exclusão(ões) exibida(s)")

# ── Tabela ────────────────────────────────────────────────────────────────────
COLS = [
    "Funcionário", "Empresa", "Departamento", "Contrato Adm.",
    "Dt. Admissão", "Dt. Demissão", "Valor Fatura", "Tem Direito",
]
cols_ok = [c for c in COLS if c in df_exc_f.columns]
df_tab  = df_exc_f[cols_ok].copy().reset_index(drop=True)

def _brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"

if "Valor Fatura" in df_tab.columns:
    df_tab["Valor Fatura"] = df_tab["Valor Fatura"].apply(_brl)

st.dataframe(df_tab, use_container_width=True, hide_index=True)

# ── Observação ────────────────────────────────────────────────────────────────
st.divider()
st.info("""
**Observação para fechamento**

Titulares listados acima estavam na fatura do mês anterior e não aparecem mais na fatura atual.
Possíveis causas: desligamento, exclusão solicitada, ou ausência na fatura por erro da operadora.

Verifique se a exclusão foi solicitada formalmente e se há crédito ou acerto financeiro a realizar.
""")
