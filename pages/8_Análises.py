# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.ui import barra_lateral
from app import db
from app.regras import aplicar_regras, calcular_stats

st.set_page_config(page_title="Análises — Unimed", layout="wide")
barra_lateral()
st.header("8 · Painel de Análises")

# ── Auto-carregar do banco se sessão estiver vazia ────────────────────────────
if "df_audit" not in st.session_state or st.session_state["df_audit"] is None:
    _ultimos = db.listar_periodos()
    if _ultimos:
        _ult = _ultimos[0]
        with st.spinner(f"Carregando auditoria {_ult['periodo']}…"):
            _df, _stats, _meta = db.carregar_auditoria(_ult["periodo"], _ult["cliente"])
        if _df is not None and not _df.empty:
            _df = aplicar_regras(_df)
            st.session_state.update({
                "df_audit":     _df,
                "stats":        calcular_stats(_df),
                "periodo":      _ult["periodo"],
                "cliente":      _ult["cliente"],
                "auditoria_id": (_meta or {}).get("id") or _ult.get("id"),
            })
            st.rerun()
        else:
            st.warning("Nenhuma auditoria encontrada. Acesse **1 · Importação**.")
            st.stop()
    else:
        st.warning("Nenhuma auditoria carregada. Acesse **1 · Importação**.")
        st.stop()

df      = st.session_state["df_audit"].copy()
periodo = st.session_state.get("periodo", "")
cliente = st.session_state.get("cliente", "")

# Garante colunas derivadas (Status, Inconsistência, Tipo Inconsistência, Dif. …)
# mesmo que o df em sessão tenha sido carregado por uma versão antiga do código.
if "Tipo Inconsistência" not in df.columns or "Dif. Fatura x Compra" not in df.columns:
    df = aplicar_regras(df)
    st.session_state["df_audit"] = df

stats = calcular_stats(df)

st.subheader(f"Período: {periodo}" + (f" · {cliente}" if cliente else ""))


def _brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"


# ── KPIs ─────────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total", stats.get("total", 0))
k2.metric("✅ OK", stats.get("ok", 0))
k3.metric("⚠️ Inconsistentes", stats.get("inconsistente", 0))
k4.metric("Total Fatura", _brl(stats.get("total_fatura", 0)))
k5.metric("Total Compra", _brl(stats.get("total_compra", 0)))

st.divider()


# ── Helpers de agregação ──────────────────────────────────────────────────────
def _col_normalizada(grupo: str) -> pd.Series:
    return df[grupo].fillna("").astype(str).str.strip()


def _gastos_por(grupo: str) -> pd.DataFrame:
    if grupo not in df.columns:
        return pd.DataFrame()
    cols_valor = [c for c in ["Valor Fatura", "Valor Compra Total", "Valor Contrato"] if c in df.columns]
    if not cols_valor:
        return pd.DataFrame()
    d = df.copy()
    d[grupo] = _col_normalizada(grupo)
    d = d[d[grupo] != ""]
    if d.empty:
        return pd.DataFrame()
    for col in cols_valor:
        d[col] = pd.to_numeric(d[col], errors="coerce").fillna(0)
    return (
        d.groupby(grupo, as_index=False)[cols_valor].sum()
        .sort_values(cols_valor[0], ascending=False)
    )


def _desvios_por(grupo: str) -> pd.DataFrame:
    if grupo not in df.columns:
        return pd.DataFrame()
    cols_desvio = [c for c in ["Dif. Contrato x Compra", "Dif. Fatura x Compra"] if c in df.columns]
    if not cols_desvio:
        return pd.DataFrame()
    d = df.copy()
    d[grupo] = _col_normalizada(grupo)
    d = d[d[grupo] != ""]
    if d.empty:
        return pd.DataFrame()
    for col in cols_desvio:
        d[col] = pd.to_numeric(d[col], errors="coerce").fillna(0).abs()
    d = d[(d[cols_desvio].sum(axis=1)) > 0]
    if d.empty:
        return pd.DataFrame()
    return (
        d.groupby(grupo, as_index=False)[cols_desvio].sum()
        .sort_values(cols_desvio[0], ascending=False)
    )


def _status_norm() -> pd.Series:
    return df.get("Status", pd.Series(dtype=str)).fillna("").astype(str).str.strip()


def _inconsistencias_por(grupo: str) -> pd.DataFrame:
    if grupo not in df.columns:
        return pd.DataFrame()
    d = df[_status_norm() == "Inconsistente"].copy()
    if d.empty:
        return pd.DataFrame()
    d[grupo] = d[grupo].fillna("").astype(str).str.strip()
    d = d[d[grupo] != ""]
    if d.empty:
        return pd.DataFrame()
    return (
        d.groupby(grupo, as_index=False).size()
        .rename(columns={"size": "Qtd. Inconsistências"})
        .sort_values("Qtd. Inconsistências", ascending=False)
    )


def _inconsistencias_por_tipo() -> pd.DataFrame:
    if "Tipo Inconsistência" not in df.columns:
        return pd.DataFrame()
    tipos = [
        t.strip()
        for cell in df["Tipo Inconsistência"].dropna()
        for t in str(cell).split("|")
        if t.strip()
    ]
    if not tipos:
        return pd.DataFrame()
    return (
        pd.Series(tipos).value_counts()
        .rename_axis("Tipo")
        .reset_index(name="Qtd.")
        .sort_values("Qtd.", ascending=False)
    )


# ── Custos ───────────────────────────────────────────────────────────────────
st.markdown("### 💰 Custos")
c1, c2, c3 = st.columns(3)
for col, grupo, titulo in [
    (c1, "Departamento", "Por Departamento"),
    (c2, "Empresa", "Por Empresa"),
    (c3, "Contrato Adm.", "Por Contrato Adm."),
]:
    with col:
        st.markdown(f"**{titulo}**")
        g = _gastos_por(grupo)
        if g.empty:
            st.caption(f"Sem dados de {grupo.lower()} para exibir.")
        else:
            st.bar_chart(g.set_index(grupo), use_container_width=True)

st.divider()

# ── Desvios ──────────────────────────────────────────────────────────────────
st.markdown("### 📉 Desvios (Contrato x Compra / Fatura x Compra)")

_dif_cont = pd.to_numeric(df.get("Dif. Contrato x Compra", 0), errors="coerce").fillna(0)
_dif_fat  = pd.to_numeric(df.get("Dif. Fatura x Compra", 0), errors="coerce").fillna(0)
m1, m2, m3 = st.columns(3)
m1.metric("Desvio Contrato x Compra", _brl(_dif_cont.sum()))
m2.metric("Desvio Fatura x Compra", _brl(_dif_fat.sum()))
m3.metric("Registros com desvio", int(((_dif_cont.abs() > 0.01) | (_dif_fat.abs() > 0.01)).sum()))

d1, d2 = st.columns(2)
with d1:
    st.markdown("**Por Departamento**")
    d = _desvios_por("Departamento")
    if d.empty:
        st.caption("Sem desvios por departamento para exibir.")
    else:
        st.bar_chart(d.set_index("Departamento"), use_container_width=True)
with d2:
    st.markdown("**Por Contrato Adm.**")
    d = _desvios_por("Contrato Adm.")
    if d.empty:
        st.caption("Sem desvios por Contrato Adm. para exibir.")
    else:
        st.bar_chart(d.set_index("Contrato Adm."), use_container_width=True)

st.markdown("**🔎 Detalhe — registros com maior desvio**")
_cols_det = [c for c in [
    "Funcionário", "Empresa", "Departamento", "Contrato Adm.",
    "Valor Contrato", "Valor Empresa (Compra)", "Valor Fatura", "Valor Compra Total",
    "Dif. Contrato x Compra", "Dif. Fatura x Compra", "Inconsistência",
] if c in df.columns]
df_det = df[_cols_det].copy() if _cols_det else pd.DataFrame()
if not df_det.empty:
    df_det["_total_desvio"] = (
        pd.to_numeric(df_det.get("Dif. Contrato x Compra", 0), errors="coerce").fillna(0).abs()
        + pd.to_numeric(df_det.get("Dif. Fatura x Compra", 0), errors="coerce").fillna(0).abs()
    )
    df_det = df_det[df_det["_total_desvio"] > 0.01].sort_values("_total_desvio", ascending=False)
if df_det.empty:
    st.caption("Nenhum registro com desvio de valor neste período. 🎉")
else:
    df_det_show = df_det.drop(columns=["_total_desvio"]).head(20).copy()
    for col in ["Valor Contrato", "Valor Empresa (Compra)", "Valor Fatura", "Valor Compra Total",
                "Dif. Contrato x Compra", "Dif. Fatura x Compra"]:
        if col in df_det_show.columns:
            df_det_show[col] = df_det_show[col].apply(lambda v: _brl(v) if pd.notna(v) else "—")
    st.dataframe(df_det_show, use_container_width=True, hide_index=True, height=420)
    st.caption(f"Mostrando os {len(df_det_show)} maiores desvios de {len(df_det)} registro(s) divergente(s) no total.")

st.divider()

# ── Inconsistências ────────────────────────────────────────────────────────────
st.markdown("### ⚠️ Inconsistências")
i1, i2 = st.columns(2)
with i1:
    st.markdown("**Por Departamento**")
    i = _inconsistencias_por("Departamento")
    if i.empty:
        st.caption("Sem inconsistências por departamento para exibir.")
    else:
        st.bar_chart(i.set_index("Departamento"), use_container_width=True)
with i2:
    st.markdown("**Por Tipo**")
    i = _inconsistencias_por_tipo()
    if i.empty:
        st.caption("Sem inconsistências para exibir.")
    else:
        st.bar_chart(i.set_index("Tipo"), use_container_width=True)

i3, i4 = st.columns(2)
with i3:
    st.markdown("**Por Empresa**")
    i = _inconsistencias_por("Empresa")
    if i.empty:
        st.caption("Sem inconsistências por empresa para exibir.")
    else:
        st.bar_chart(i.set_index("Empresa"), use_container_width=True)
with i4:
    st.markdown("**Por Contrato Adm.**")
    i = _inconsistencias_por("Contrato Adm.")
    if i.empty:
        st.caption("Sem inconsistências por Contrato Adm. para exibir.")
    else:
        st.bar_chart(i.set_index("Contrato Adm."), use_container_width=True)

st.divider()

# ── Evolução histórica entre períodos ─────────────────────────────────────────
st.markdown("### 📈 Evolução entre períodos")
_periodos_hist = db.listar_periodos(cliente) if cliente else db.listar_periodos()
if len(_periodos_hist) <= 1:
    st.caption(
        f"Ainda não há outros períodos processados para comparar "
        f"(encontrado apenas: {', '.join(p['periodo'] for p in _periodos_hist)})."
        if _periodos_hist else "Nenhum período encontrado."
    )
else:
    linhas = []
    for p in _periodos_hist:
        _df_p, _stats_p, _ = db.carregar_auditoria(p["periodo"], p["cliente"])
        if _df_p is None or _df_p.empty:
            continue
        _df_p = aplicar_regras(_df_p)
        linhas.append({
            "Período":        p["periodo"],
            "Total Fatura":   pd.to_numeric(_df_p.get("Valor Fatura", 0), errors="coerce").fillna(0).sum(),
            "Total Compra":   pd.to_numeric(_df_p.get("Valor Compra Total", 0), errors="coerce").fillna(0).sum(),
            "Inconsistentes": int((_df_p.get("Status", "").astype(str).str.strip() == "Inconsistente").sum()),
        })
    if linhas:
        df_hist = (
            pd.DataFrame(linhas)
            .groupby("Período", as_index=False).last()  # uma linha por período (já é o mais recente de cada)
            .assign(_ord=lambda d: pd.to_datetime("01/" + d["Período"], format="%d/%m/%Y", errors="coerce"))
            .sort_values("_ord")
            .drop(columns="_ord")
        )
        e1, e2 = st.columns(2)
        with e1:
            st.markdown("**Total Fatura x Total Compra**")
            st.line_chart(df_hist.set_index("Período")[["Total Fatura", "Total Compra"]], use_container_width=True)
        with e2:
            st.markdown("**Qtd. de Inconsistências**")
            st.line_chart(df_hist.set_index("Período")[["Inconsistentes"]], use_container_width=True)
    else:
        st.caption("Não foi possível montar o histórico.")
