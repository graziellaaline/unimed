# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.ui import barra_lateral
from app import db

st.set_page_config(page_title="Aprovação — Auditoria Unimed", layout="wide")
barra_lateral()
st.header("5 · Aprovação de Pendências")

# ── Auto-carregar do banco se sessão estiver vazia ────────────────────────────
if "df_audit" not in st.session_state or st.session_state["df_audit"] is None:
    _ultimos = db.listar_periodos()          # já ordenado por processado_em DESC
    if _ultimos:
        _ult = _ultimos[0]                   # mais recente em absoluto
        with st.spinner(f"Carregando auditoria {_ult['periodo']}…"):
            from app.regras import aplicar_regras, calcular_stats, identificar_incluidos_mes
            _df, _stats, _meta = db.carregar_auditoria(_ult["periodo"], _ult["cliente"])
        if _df is not None and not _df.empty:
            _df = aplicar_regras(_df)
            _aid = (_meta or {}).get("id") or _ult.get("id")
            _arqs = db.carregar_arquivos_auditoria(_aid) if _aid else {}
            st.session_state.update({
                "df_audit":      _df,
                "df_inc":        identificar_incluidos_mes(_df, _ult["periodo"]),
                "stats":         calcular_stats(_df),
                "periodo":       _ult["periodo"],
                "cliente":       _ult["cliente"],
                "auditoria_id":  _aid,
                "arquivos_fontes": _arqs,
            })
            st.rerun()
        else:
            st.warning("Nenhuma auditoria encontrada no banco. Acesse **1 · Importação**.")
            st.stop()
    else:
        st.warning("Nenhuma auditoria carregada. Acesse **1 · Importação**.")
        st.stop()

df      = st.session_state["df_audit"]
aid     = st.session_state.get("auditoria_id")
periodo = st.session_state.get("periodo", "")
cliente = st.session_state.get("cliente", "")

# ── Fallback: garantir que aid aponta para o audit com justificativas ────────
if periodo:
    if not aid:
        # Sessão sem auditoria_id — buscar o mais recente do período
        _ultimos_per = db.listar_periodos()
        for _p in _ultimos_per:
            if _p["periodo"] == periodo:
                aid = _p["id"]
                st.session_state["auditoria_id"] = aid
                break

    if aid and not db.carregar_justificativas(aid):
        # audit_id existe mas sem justificativas — migrar do período
        db.migrar_justificativas(aid, periodo, cliente)

pendentes = df[df["Status"] == "Inconsistente"].copy() if "Status" in df.columns else pd.DataFrame()

st.subheader(f"Período: {periodo}" + (f" · {cliente}" if cliente else ""))

if pendentes.empty:
    st.success("✅ Nenhuma pendência — todas as linhas estão OK.")
    st.stop()


# ── Justificativas salvas ─────────────────────────────────────────────────────
def _carregar_justificativas_ativas() -> dict:
    """
    Carrega justificativas com dupla busca:
    1. Pelo auditoria_id da sessão
    2. Fallback por período com cliente='' (cobre variações de case no nome do cliente)
    """
    resultado = db.carregar_justificativas(aid) if aid else {}
    if not resultado and periodo:
        _, resultado = db.carregar_justificativas_por_periodo(periodo, "")
    return resultado


def _aplicar_modelos_exatos(salvar_no_banco=True):
    atuais = _carregar_justificativas_ativas()
    aplicadas = 0
    for _, row in pendentes.iterrows():
        func = str(row.get("Funcionário", ""))
        desc = str(row.get("Inconsistência", ""))
        if atuais.get(func, "").strip():
            continue
        modelo = db.carregar_justificativa_modelo(cliente, func, desc)
        if modelo and aid:
            if salvar_no_banco:
                db.salvar_justificativa(aid, func, desc, modelo)
            atuais[func] = modelo
            aplicadas += 1
    return aplicadas, atuais


_, just_salvas = _aplicar_modelos_exatos(salvar_no_banco=True)

funcionarios  = pendentes["Funcionário"].tolist()
com_just      = sum(1 for f in funcionarios if just_salvas.get(f, "").strip())
prog          = com_just / len(funcionarios) if funcionarios else 0

st.warning(f"**{len(pendentes)}** pendência(s) aguardando justificativa.")
st.progress(prog, text=f"{com_just}/{len(funcionarios)} justificativas preenchidas")

st.divider()

# ── Filtros ───────────────────────────────────────────────────────────────────
filtro_causas = ["Todas"] + sorted(
    [v for v in pendentes["Inconsistência"].dropna().unique().tolist() if str(v).strip()]
)

fc1, fc2, fc3 = st.columns([3, 3, 2])
with fc1:
    causa_sel = st.selectbox("Inconsistência", filtro_causas)
with fc2:
    f_nome = st.text_input("Funcionário (parte do nome)")
with fc3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("♻ Reaplicar modelos salvos", use_container_width=True):
        qtd, _ = _aplicar_modelos_exatos(salvar_no_banco=True)
        if qtd:
            st.success(f"{qtd} justificativa(s) reaplicada(s).")
            st.rerun()
        else:
            st.info("Nenhuma justificativa reutilizável encontrada.")

pendentes_exibidas = pendentes.copy()
if causa_sel != "Todas":
    pendentes_exibidas = pendentes_exibidas[pendentes_exibidas["Inconsistência"] == causa_sel]
if f_nome:
    pendentes_exibidas = pendentes_exibidas[
        pendentes_exibidas["Funcionário"].str.contains(f_nome, case=False, na=False)
    ]

st.caption(f"**{len(pendentes_exibidas)}** pendência(s) exibida(s)")

# ── Tabela editável ───────────────────────────────────────────────────────────
COLS_INFO = [c for c in [
    "Funcionário", "Empresa", "Departamento", "Contrato Adm.",
    "Dt. Admissão", "Dt. Demissão", "Dt. Elegibilidade",
    "Inconsistência", "Ação Sugerida",
] if c in pendentes_exibidas.columns]

df_tab = pendentes_exibidas[COLS_INFO].copy().reset_index(drop=True)
df_tab.insert(0, "☑", False)
df_tab["Justificativa"] = df_tab["Funcionário"].map(lambda f: just_salvas.get(f, "") or "")
df_tab["Sit."]          = df_tab["Funcionário"].map(lambda f: "✅" if just_salvas.get(f, "").strip() else "⏳")

col_cfg = {
    "☑":             st.column_config.CheckboxColumn("☑", width="small"),
    "Funcionário":   st.column_config.TextColumn("Funcionário",   width="medium"),
    "Departamento":  st.column_config.TextColumn("Departamento",  width="medium"),
    "Contrato Adm.": st.column_config.TextColumn("Contrato Adm.", width="small"),
    "Dt. Admissão":  st.column_config.TextColumn("Dt. Admissão",  width="small"),
    "Dt. Demissão":  st.column_config.TextColumn("Dt. Demissão",  width="small"),
    "Inconsistência":st.column_config.TextColumn("Inconsistência",width="large"),
    "Ação Sugerida": st.column_config.TextColumn("Ação Sugerida", width="medium"),
    "Justificativa": st.column_config.TextColumn("Justificativa", width="large"),
    "Sit.":          st.column_config.TextColumn("Sit.",          width="small"),
}
cols_bloqueadas = [c for c in df_tab.columns if c not in ("☑", "Justificativa")]

edited = st.data_editor(
    df_tab,
    column_config=col_cfg,
    disabled=cols_bloqueadas,
    use_container_width=True,
    hide_index=True,
    height=430,
    key="tabela_aprovacao",
)

# ── Salvar edições inline da tabela ──────────────────────────────────────────
sv1, sv2 = st.columns([3, 1])
with sv1:
    salvar_modelo_individual = st.checkbox(
        "Gravar justificativas para meses futuros ao salvar",
        key="modelo_individual",
    )
with sv2:
    if st.button("💾 Salvar edições da tabela", use_container_width=True, type="primary"):
        saved = 0
        for _, row in edited.iterrows():
            func = str(row.get("Funcionário", ""))
            just = str(row.get("Justificativa", "")).strip()
            if not just:
                continue
            inc_row = pendentes[pendentes["Funcionário"] == func]
            desc = str(inc_row["Inconsistência"].iloc[0]) if not inc_row.empty else ""
            db.salvar_justificativa(aid, func, desc, just)
            if salvar_modelo_individual:
                db.salvar_justificativa_modelo(cliente, func, desc, just)
            saved += 1
        if saved:
            st.success(f"{saved} justificativa(s) salva(s).")
            st.rerun()
        else:
            st.info("Nenhuma justificativa preenchida na tabela para salvar.")

st.divider()

# ── Justificativa em lote para selecionados ───────────────────────────────────
selecionados = edited[edited["☑"] == True]["Funcionário"].tolist() if not edited.empty else []

st.markdown("#### Justificar em lote")
la1, la2 = st.columns([3, 1])
with la1:
    placeholder_lote = (
        f"{len(selecionados)} linha(s) selecionada(s) — escreva a justificativa e clique em Aplicar…"
        if selecionados
        else "Selecione linhas na tabela acima (coluna ☑) para justificar em lote."
    )
    just_lote = st.text_area(
        "Justificativa para os selecionados",
        placeholder=placeholder_lote,
        height=90,
        disabled=not selecionados,
    )
    salvar_modelo_lote = st.checkbox(
        "Gravar para meses futuros (Funcionário + Inconsistência idênticos)",
        key="save_batch_template",
    )
with la2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    label_btn = (
        f"✅ Aplicar aos {len(selecionados)} selecionado(s)"
        if selecionados
        else "Nenhum selecionado"
    )
    if st.button(
        label_btn,
        disabled=not (selecionados and just_lote.strip()),
        use_container_width=True,
        type="primary",
    ):
        for func in selecionados:
            inc_row = pendentes[pendentes["Funcionário"] == func]
            desc = str(inc_row["Inconsistência"].iloc[0]) if not inc_row.empty else ""
            db.salvar_justificativa(aid, func, desc, just_lote.strip())
            if salvar_modelo_lote:
                db.salvar_justificativa_modelo(cliente, func, desc, just_lote.strip())
        st.success(f"Justificativa aplicada a {len(selecionados)} pendência(s).")
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
