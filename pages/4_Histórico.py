# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.ui import barra_lateral
from app import db
from app.regras import identificar_incluidos_mes

st.set_page_config(page_title="Histórico — Auditoria Unimed", layout="wide")
barra_lateral()
st.header("4 · Histórico de Auditorias")

periodos = db.listar_periodos()

if not periodos:
    st.info("Nenhuma auditoria salva ainda. Processe em **1 · Importação**.")
    st.stop()

# ── Lista de histórico ────────────────────────────────────────────────────────
df_hist = pd.DataFrame(periodos)
df_hist.columns = ["Período", "Cliente", "Processado em", "Versões"]
st.dataframe(df_hist, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Recarregar auditoria anterior")

c1, c2, c3 = st.columns(3)
with c1:
    periodo_sel = c1.selectbox("Período", [p["periodo"] for p in periodos])
with c2:
    cliente_sel = c2.text_input("Cliente (deixe em branco para qualquer)")
with c3:
    st.write("")
    st.write("")
    btn = c3.button("⬇ Carregar", type="primary")

if btn:
    df_loaded, stats, meta = db.carregar_auditoria(periodo_sel, cliente_sel)
    if df_loaded is None or df_loaded.empty:
        st.error("Não foi possível carregar a auditoria selecionada.")
    else:
        df_inc = identificar_incluidos_mes(df_loaded, periodo_sel)
        st.session_state.update({
            "df_audit":     df_loaded,
            "df_inc":       df_inc,
            "stats":        stats,
            "periodo":      periodo_sel,
            "cliente":      cliente_sel,
            "auditoria_id": meta.get("id"),
        })
        proc = (meta.get("processado_em") or "")[:16].replace("T", " às ")
        aprv = "✅ Aprovada" if meta.get("aprovado") else "⏳ Pendente"
        st.success(
            f"Auditoria **{periodo_sel}** carregada · "
            f"processado em {proc} · status: {aprv}"
        )
        st.info("Navegue para **2 · Auditoria** para ver o resultado.")
