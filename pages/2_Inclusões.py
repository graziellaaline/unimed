# -*- coding: utf-8 -*-
import unicodedata
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.ui import barra_lateral
from app.exportacao import exportar_excel
from app.regras import identificar_incluidos_mes, aplicar_regras, calcular_stats
from app import db

st.set_page_config(page_title="Inclusões do Mês — Unimed", layout="wide")
barra_lateral()
st.header("3 · Inclusões no Mês de Referência")


def _norm(s) -> str:
    txt = str(s or "").strip().upper()
    nfkd = unicodedata.normalize("NFKD", txt)
    return " ".join("".join(c for c in nfkd if not unicodedata.combining(c)).split())


def _periodo_anterior(periodo: str) -> str:
    """Retorna o período imediatamente anterior (ex: 05/2026 → 04/2026)."""
    try:
        partes = str(periodo).strip().split("/")
        mes, ano = int(partes[0]), int(partes[1])
        if ano < 100:
            ano += 2000
        if mes == 1:
            return f"12/{ano - 1}"
        return f"{mes - 1:02d}/{ano}"
    except Exception:
        return ""


# ── Auto-carregar auditoria ───────────────────────────────────────────────────
if "df_audit" not in st.session_state or st.session_state["df_audit"] is None:
    _ults = db.listar_periodos()
    if _ults:
        _ult = _ults[0]
        with st.spinner(f"Carregando auditoria {_ult['periodo']}…"):
            _df, _stats, _meta = db.carregar_auditoria(_ult["periodo"], _ult["cliente"])
        if _df is not None and not _df.empty:
            _df = aplicar_regras(_df)
            _aid = (_meta or {}).get("id") or _ult.get("id")
            st.session_state.update({
                "df_audit":     _df,
                "df_inc":       identificar_incluidos_mes(_df, _ult["periodo"]),
                "stats":        calcular_stats(_df),
                "periodo":      _ult["periodo"],
                "cliente":      _ult["cliente"],
                "auditoria_id": _aid,
                "arquivos_fontes": db.carregar_arquivos_auditoria(_aid) if _aid else {},
            })
            st.rerun()
        else:
            st.warning("Nenhuma auditoria encontrada. Acesse **1 · Importação**.")
            st.stop()
    else:
        st.warning("Nenhuma auditoria carregada. Acesse **1 · Importação**.")
        st.stop()

df      = st.session_state["df_audit"]
periodo = st.session_state.get("periodo", "")
cliente = st.session_state.get("cliente", "")

st.subheader(f"Período: {periodo}" + (f" · {cliente}" if cliente else ""))

# ── Critério 1: Data Inclusão da fatura coincide com o período ───────────────
# Sempre recalcula para não usar df_inc stale da sessão.
df_inc_fat = identificar_incluidos_mes(df, periodo)

# ── Critério 2: Titulares novos vs período anterior ──────────────────────────
periodo_ant = _periodo_anterior(periodo)
df_novos_vs_ant = pd.DataFrame()
info_periodo_ant = ""

if periodo_ant:
    _df_ant, _, _meta_ant = db.carregar_auditoria(periodo_ant, cliente)
    if _df_ant is not None and not _df_ant.empty:
        _df_ant = aplicar_regras(_df_ant)
        # Titulares ativos na fatura do período anterior
        nomes_ant = {
            _norm(str(n or ""))
            for n in _df_ant.loc[_df_ant["_na_fatura"].astype(bool), "Funcionário"]
        }
        # Titulares ativos na fatura do período atual
        df_fat_atual = df[df["_na_fatura"].astype(bool)].copy()
        # Novos: presentes agora mas ausentes no período anterior
        mascara_novo = df_fat_atual["Funcionário"].apply(
            lambda n: _norm(str(n or "")) not in nomes_ant
        )
        df_novos_vs_ant = df_fat_atual[mascara_novo].copy()
        info_periodo_ant = periodo_ant
    else:
        info_periodo_ant = None  # período anterior não encontrado no banco

# ── Combinar critérios ────────────────────────────────────────────────────────
# Critério 1 = inclusão com data no mês (pode ser retroativa)
# Critério 2 = qualquer novo titular vs mês anterior (incluindo sem Data Inclusão deste mês)
# Origem ajuda a entender de onde veio cada inclusão

func_norm_c1 = set(_norm(str(n)) for n in df_inc_fat["Funcionário"]) if not df_inc_fat.empty else set()

# Adicionar coluna de origem
if not df_inc_fat.empty:
    df_inc_fat = df_inc_fat.copy()
    df_inc_fat["Origem"] = "Inclusão no mês (Data Inclusão = " + periodo + ")"

if not df_novos_vs_ant.empty:
    df_novos_vs_ant = df_novos_vs_ant.copy()
    # Não duplicar com o critério 1
    df_extra = df_novos_vs_ant[
        df_novos_vs_ant["Funcionário"].apply(lambda n: _norm(str(n)) not in func_norm_c1)
    ].copy()
    df_extra["Origem"] = f"Novo titular (ausente em {info_periodo_ant})"
else:
    df_extra = pd.DataFrame()

df_inc_combined = pd.concat([df_inc_fat, df_extra], ignore_index=True)

# ── Exibição ─────────────────────────────────────────────────────────────────
total = len(df_inc_combined)
n_c1  = len(df_inc_fat)
n_c2  = len(df_extra)

if df_inc_combined.empty:
    msg = f"Nenhuma inclusão identificada em **{periodo}**"
    if info_periodo_ant:
        msg += f" (comparado com {info_periodo_ant})"
    st.info(msg)
    st.stop()

st.success(f"**{total}** inclusão(ões) identificada(s) em {periodo}")

c1, c2 = st.columns(2)
with c1:
    st.metric("📅 Data Inclusão = período", n_c1,
              help="Titulares cuja Data Inclusão na fatura coincide com o mês/ano da auditoria")
with c2:
    if info_periodo_ant:
        st.metric(f"🆕 Novos vs {info_periodo_ant}", n_c2,
                  help=f"Titulares presentes nesta fatura que não estavam em {info_periodo_ant}")
    elif info_periodo_ant is None:
        st.caption(f"⚠️ Período anterior ({periodo_ant}) não encontrado no banco — critério 2 não calculado")
    else:
        st.caption("Período anterior não disponível")

st.divider()

# ── Filtros ──────────────────────────────────────────────────────────────────
with st.expander("🔍 Filtros", expanded=True):
    f1, f2, f3, f4 = st.columns(4)

    opts_empresa = ["Todos"] + sorted([
        v for v in df_inc_combined.get("Empresa", pd.Series()).dropna().unique()
        if str(v).strip()
    ])
    opts_dep = ["Todos"] + sorted([
        v for v in df_inc_combined.get("Departamento", pd.Series()).dropna().unique()
        if str(v).strip()
    ])
    opts_cont = ["Todos"] + sorted([
        v for v in df_inc_combined.get("Contrato Adm.", pd.Series()).dropna().unique()
        if str(v).strip()
    ])
    opts_orig = ["Todos"] + sorted(df_inc_combined["Origem"].dropna().unique().tolist())

    f_empresa  = f1.selectbox("Empresa", opts_empresa)
    f_dep      = f2.selectbox("Departamento", opts_dep)
    f_contrato = f3.selectbox("Contrato Adm.", opts_cont)
    f_orig     = f4.selectbox("Origem", opts_orig)

df_f = df_inc_combined.copy()
if f_empresa  != "Todos": df_f = df_f[df_f.get("Empresa", pd.Series()) == f_empresa]
if f_dep      != "Todos": df_f = df_f[df_f.get("Departamento", pd.Series()) == f_dep]
if f_contrato != "Todos": df_f = df_f[df_f.get("Contrato Adm.", pd.Series()) == f_contrato]
if f_orig     != "Todos": df_f = df_f[df_f["Origem"] == f_orig]

st.caption(f"**{len(df_f)}** inclusão(ões) exibida(s)")

# ── Tabela ────────────────────────────────────────────────────────────────────
COLS = [
    "Funcionário", "Empresa", "Departamento", "Contrato Adm.",
    "Dt. Admissão", "Data Inclusão",
    "Valor Fatura", "Valor Contrato", "Tem Direito", "Origem",
]
cols_ok = [c for c in COLS if c in df_f.columns]
df_tab = df_f[cols_ok].copy()

def _brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"

for col in ["Valor Fatura", "Valor Contrato"]:
    if col in df_tab.columns:
        df_tab[col] = df_tab[col].apply(_brl)

st.dataframe(df_tab, use_container_width=True, hide_index=True, height=480)

# ── Observação ────────────────────────────────────────────────────────────────
st.divider()
st.info(
    "**Atenção — inclusões retroativas:** funcionários incluídos com data anterior ao "
    f"período {periodo} mas que não constavam em {info_periodo_ant or 'mês anterior'} "
    "podem gerar cobrança proporcional retroativa. Verifique se o valor faturado corresponde "
    "aos dias de cobertura efetiva."
)

# ── Export ────────────────────────────────────────────────────────────────────
aid = st.session_state.get("auditoria_id")
df_just_raw = db.carregar_justificativas(aid) if aid else {}
df_just = pd.DataFrame()
if df_just_raw:
    df_just = pd.DataFrame([{"Funcionário": f, "Justificativa": j} for f, j in df_just_raw.items()])

excel_bytes = exportar_excel(df, df_inc_combined, df_just, periodo)
st.download_button(
    "📥 Exportar Excel",
    data=excel_bytes,
    file_name=f"inclusoes_unimed_{periodo.replace('/', '_')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
