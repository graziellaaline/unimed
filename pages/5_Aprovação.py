# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.ui import barra_lateral
from app import db

st.set_page_config(page_title="Aprovação — Auditoria Unimed", layout="wide")
barra_lateral()
st.header("5 · Aprovação de Pendências")

if "df_audit" not in st.session_state:
    st.warning("Nenhuma auditoria carregada. Acesse **1 · Importação** ou **4 · Histórico**.")
    st.stop()

df      = st.session_state["df_audit"]
aid     = st.session_state.get("auditoria_id")
periodo = st.session_state.get("periodo", "")

pendentes = df[df.get("Status", "").eq("Inconsistente")].copy() \
    if "Status" in df.columns else df[df["Status"] == "Inconsistente"].copy()

st.subheader(f"Período: {periodo}")

if pendentes.empty:
    st.success("✅ Nenhuma pendência — todas as linhas estão OK.")
    st.stop()

# ── Carrega justificativas já salvas ──────────────────────────────────────────
just_salvas = db.carregar_justificativas(aid) if aid else {}

st.warning(f"**{len(pendentes)}** pendência(s) aguardando justificativa obrigatória.")

# ── Barra de progresso ────────────────────────────────────────────────────────
funcionarios = pendentes["Funcionário"].tolist()
com_just = sum(1 for f in funcionarios if just_salvas.get(f, "").strip())
prog = com_just / len(funcionarios) if funcionarios else 0
st.progress(prog, text=f"{com_just}/{len(funcionarios)} justificativas preenchidas")

st.divider()

# ── Cards de pendência ────────────────────────────────────────────────────────
for i, (_, row) in enumerate(pendentes.iterrows()):
    func = str(row.get("Funcionário", ""))
    desc = str(row.get("Inconsistência", ""))
    acao = str(row.get("Ação Sugerida", ""))
    dept = str(row.get("Departamento", ""))

    titulo = f"⚠️  {func}"
    if dept:
        titulo += f" · {dept}"

    with st.expander(titulo, expanded=(i < 5 and com_just < len(funcionarios))):
        st.markdown(f"**Inconsistência:** {desc}")
        st.markdown(f"**Ação sugerida:** {acao}")

        val_existente = just_salvas.get(func, "")
        just_input = st.text_area(
            "Justificativa (obrigatória)",
            value=val_existente,
            key=f"just_{i}",
            placeholder="Descreva o motivo ou a ação tomada para resolver esta pendência…",
            height=100,
        )
        btn_col, _ = st.columns([1, 5])
        with btn_col:
            if st.button("Salvar", key=f"btn_salvar_{i}",
                         disabled=not just_input.strip()):
                db.salvar_justificativa(aid, func, desc, just_input.strip())
                just_salvas[func] = just_input.strip()
                st.success("Justificativa salva!")
                st.rerun()

st.divider()

# ── Aprovação final ───────────────────────────────────────────────────────────
todas_justificadas = com_just == len(funcionarios)
if todas_justificadas:
    st.success("✅ Todas as pendências têm justificativa. A auditoria pode ser aprovada.")
    if st.button("🎯 Aprovar Auditoria do Período", type="primary"):
        db.aprovar_auditoria(aid)
        st.success(f"Auditoria **{periodo}** aprovada com sucesso!")
        st.balloons()
else:
    faltam = len(funcionarios) - com_just
    st.info(f"Faltam **{faltam}** justificativa(s) para liberar a aprovação.")
