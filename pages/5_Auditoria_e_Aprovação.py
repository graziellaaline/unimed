# -*- coding: utf-8 -*-
"""
5 · Auditoria e Aprovação — resultado, justificativa e aprovação numa tela só.

Antes eram duas telas: a 5 mostrava o resultado e a 6 pedia as justificativas
e liberava a aprovação. Como o trabalho é o mesmo — olhar a pendência e
justificar ali — as duas viraram esta. A tabela é única: os filtros ficam no
cabeçalho de cada coluna (estilo Excel) e rodam no navegador, então dá para
alternar entre "só pendentes" e "tudo" sem recarregar a página.
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.ui import ICONE, barra_lateral
from app.grade import grade, cor_por_status, recarregar
from app.exportacao import exportar_excel
from app import db

st.set_page_config(page_title="Auditoria e Aprovação — Unimed", page_icon=ICONE, layout="wide")
barra_lateral()
st.header("5 · Auditoria e Aprovação")

# ── Auto-carregar do banco se sessão estiver vazia ────────────────────────────
if "df_audit" not in st.session_state or st.session_state["df_audit"] is None:
    _ultimos = db.listar_periodos()          # ordenado do mais recente para o mais antigo
    if _ultimos:
        _ult = _ultimos[0]
        with st.spinner(f"Carregando auditoria {_ult['periodo']}…"):
            from app.regras import aplicar_regras, calcular_stats, identificar_incluidos_mes
            _df, _stats, _meta = db.carregar_auditoria(_ult["periodo"], _ult["cliente"])
        if _df is not None and not _df.empty:
            _aid  = (_meta or {}).get("id") or _ult.get("id")
            _arqs = db.carregar_arquivos_auditoria(_aid) if _aid else {}
            # Correção dos inativos (desligados), se o arquivo estiver salvo
            _desl_item = (_arqs.get("desligados") or [None])[0]
            if _desl_item and _desl_item.get("caminho"):
                try:
                    from app.processamento import ler_contratos, mesclar_desligados
                    _df_inat = ler_contratos(_desl_item["caminho"])
                    _df, _   = mesclar_desligados(_df, _df_inat, _ult["periodo"])
                except Exception:
                    pass
            _df = aplicar_regras(_df)
            st.session_state.update({
                "df_audit":        _df,
                "df_inc":          identificar_incluidos_mes(_df, _ult["periodo"]),
                "stats":           calcular_stats(_df),
                "periodo":         _ult["periodo"],
                "cliente":         _ult["cliente"],
                "auditoria_id":    _aid,
                "arquivos_fontes": _arqs,
            })
            st.rerun()
        else:
            st.warning("Nenhuma auditoria encontrada. Acesse **1 · Importação**.")
            st.stop()
    else:
        st.warning("Nenhuma auditoria carregada. Acesse **1 · Importação**.")
        st.stop()

df      = st.session_state["df_audit"].copy()
stats   = st.session_state.get("stats", {})
periodo = st.session_state.get("periodo", "")
cliente = st.session_state.get("cliente", "")
aid     = st.session_state.get("auditoria_id")

# Garante colunas derivadas mesmo se o df em sessão veio de uma versão antiga.
if "Tipo Inconsistência" not in df.columns:
    from app.regras import aplicar_regras
    df = aplicar_regras(df)
    st.session_state["df_audit"] = df

# ── Fallback: garantir que aid aponta para o audit com justificativas ────────
if periodo:
    if not aid:
        for _p in db.listar_periodos():
            if _p["periodo"] == periodo:
                aid = _p["id"]
                st.session_state["auditoria_id"] = aid
                break
    if aid and not db.carregar_justificativas(aid):
        db.migrar_justificativas(aid, periodo, cliente)


def _carregar_justificativas_ativas() -> dict:
    """
    Carrega justificativas com dupla busca:
    1. Pelo auditoria_id da sessão
    2. Fallback por período com cliente='' (cobre variações de case no cliente)
    """
    resultado = db.carregar_justificativas(aid) if aid else {}
    if not resultado and periodo:
        _, resultado = db.carregar_justificativas_por_periodo(periodo, "")
    return resultado


pendentes = df[df["Status"] == "Inconsistente"].copy() if "Status" in df.columns else pd.DataFrame()


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

df["Justificado"]  = df["Funcionário"].map(lambda f: "Sim" if just_salvas.get(f, "").strip() else "Não")
df["Justificativa"] = df["Funcionário"].map(lambda f: just_salvas.get(f, "") or "")

st.subheader(f"Período: {periodo}" + (f" · {cliente}" if cliente else ""))


# ── KPIs ─────────────────────────────────────────────────────────────────────
def _brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"


_funcs_pend = pendentes["Funcionário"].tolist() if not pendentes.empty else []
_n_inc  = stats.get("inconsistente", len(_funcs_pend))
_n_just = sum(1 for f in _funcs_pend if just_salvas.get(f, "").strip())
_n_pend = _n_inc - _n_just

k1, k2, k3, k4, k5, k6, k7, k8 = st.columns(8)
k1.metric("Total",         stats.get("total", 0))
k2.metric("OK",            stats.get("ok", 0))
k3.metric("Inconsist.",    _n_inc)
k4.metric("Pendentes",     _n_pend, delta=f"-{_n_just} justificados" if _n_just else None,
          delta_color="inverse")
k5.metric("Na Fatura",     stats.get("na_fatura", 0))
k6.metric("Na Compra",     stats.get("na_compra", 0))
k7.metric("Total Fatura",  _brl(stats.get("total_fatura", 0)))
k8.metric("Total Compra",  _brl(stats.get("total_compra", 0)))

if _funcs_pend:
    st.progress(
        _n_just / len(_funcs_pend),
        text=f"{_n_just}/{len(_funcs_pend)} justificativas preenchidas",
    )

st.divider()

# ── Tabela única ─────────────────────────────────────────────────────────────
# Ordem FIXA da tabela — esta é a ordem arrumada pela Graziella, promovida
# para o código para não depender do arquivo de estado. Arrastar o cabeçalho
# continua funcionando e a nova posição fica gravada em disco; apagar
# `dados/ordem_colunas_grade_auditoria.json` volta exatamente para esta.
COLS = [
    "Empresa", "Justificado", "Status", "Funcionário", "Departamento",
    "Contrato Adm.", "Tipo Inconsistência", "Justificativa",
    "Dt. Admissão", "Dt. Demissão", "Dt. Elegibilidade",
    "Tem Direito", "Está na Fatura", "Está na Compra",
    "Valor Contrato", "Valor Empresa (Compra)", "Valor Fatura", "Valor Compra Total",
    "Dif. Fatura x Contrato", "Dif. Contrato x Compra", "Dif. Fatura x Compra",
    "Data Inclusão", "Inconsistência", "Ação Sugerida",
]
cols_ok = [c for c in COLS if c in df.columns]
df_tab = df[cols_ok].copy().reset_index(drop=True)

MOEDA = tuple(c for c in [
    "Valor Contrato", "Valor Empresa (Compra)", "Valor Fatura", "Valor Compra Total",
    "Dif. Fatura x Contrato", "Dif. Contrato x Compra", "Dif. Fatura x Compra",
] if c in df_tab.columns)
for c in MOEDA:
    df_tab[c] = pd.to_numeric(df_tab[c], errors="coerce")

# Datas como texto não ordenam cronologicamente — converter para data real.
DATAS = tuple(c for c in ["Dt. Admissão", "Dt. Demissão", "Dt. Elegibilidade", "Data Inclusão"]
              if c in df_tab.columns)
for c in DATAS:
    _limpo = (df_tab[c].astype(str).str.strip()
              .replace({"nan": "", "None": "", "NaT": "", "none": "", "NAT": ""}))
    df_tab[c] = pd.to_datetime(_limpo, dayfirst=True, errors="coerce")

st.caption(
    "Funil do cabeçalho filtra a coluna · arraste o cabeçalho para reordenar "
    "(a posição fica gravada) · duplo clique numa célula copia o conteúdo · "
    "**Justificativa** é editável · o tique do cabeçalho marca e desmarca todos."
)

resposta = grade(
    df_tab,
    key="grade_auditoria",
    height=520,
    colunas_moeda=MOEDA,
    colunas_data=DATAS,
    colunas_editaveis=("Justificativa",),
    larguras={"Funcionário": 220, "Inconsistência": 300, "Justificativa": 320},
    cor_linha=cor_por_status(),
    selecao=True,
)

df_visivel = pd.DataFrame(resposta["data"]) if resposta is not None else pd.DataFrame()
st.caption(f"**{len(df_visivel)}** registro(s) exibido(s) de {len(df_tab)}.")

# `selected_data` traz SÓ as linhas com o tiquezinho marcado (None quando não há
# nenhuma). Não confundir com `data`, que traz tudo o que o filtro deixou à
# vista — o lote nunca pode cair em cima do conjunto filtrado inteiro.
_sel = resposta.selected_data if resposta is not None else None
if isinstance(_sel, pd.DataFrame) and not _sel.empty and "Funcionário" in _sel.columns:
    selecionados = [str(f) for f in _sel["Funcionário"].tolist()]
else:
    selecionados = []


def _descricao(func: str) -> str:
    linha = pendentes[pendentes["Funcionário"] == func]
    return str(linha["Inconsistência"].iloc[0]) if not linha.empty else ""


# ── Salvar edições da coluna Justificativa ───────────────────────────────────
ed1, ed2 = st.columns([3, 1])
with ed1:
    gravar_modelo = st.checkbox(
        "Gravar justificativas para meses futuros ao salvar",
        key="modelo_individual",
        value=True,
    )
with ed2:
    if st.button("Salvar edições da tabela", use_container_width=True, type="primary"):
        salvos = revertidos = 0
        for _, row in df_visivel.iterrows():
            func = str(row.get("Funcionário", ""))
            just = str(row.get("Justificativa", "") or "").strip()
            antes = just_salvas.get(func, "").strip()
            if antes and not just:
                db.excluir_justificativa(aid, func)
                revertidos += 1
            elif just and just != antes:
                desc = _descricao(func)
                db.salvar_justificativa(aid, func, desc, just)
                if gravar_modelo:
                    db.salvar_justificativa_modelo(cliente, func, desc, just)
                salvos += 1
        if salvos or revertidos:
            partes = []
            if salvos:
                partes.append(f"{salvos} justificativa(s) salva(s)")
            if revertidos:
                partes.append(f"{revertidos} revertida(s) para pendente")
            st.success(" · ".join(partes) + ".")
            recarregar("grade_auditoria")
            st.rerun()
        else:
            st.info("Nenhuma alteração na tabela para salvar.")

st.divider()

# ── Justificativa em lote ────────────────────────────────────────────────────
st.markdown("#### Justificar em lote")
lt1, lt2 = st.columns([3, 1])
with lt1:
    just_lote = st.text_area(
        "Justificativa para os selecionados",
        placeholder=(
            f"{len(selecionados)} linha(s) selecionada(s) — escreva a justificativa e clique em Aplicar…"
            if selecionados
            else "Marque linhas na tabela acima para justificar várias de uma vez."
        ),
        height=90,
        disabled=not selecionados,
    )
    modelo_lote = st.checkbox(
        "Gravar para meses futuros (Funcionário + Inconsistência idênticos)",
        key="save_batch_template",
        value=True,
    )
    # Quem vai ser afetado fica à vista antes de clicar — filtrar a tabela não
    # seleciona ninguém; só o tiquezinho da linha seleciona.
    if selecionados:
        _amostra = ", ".join(selecionados[:5])
        if len(selecionados) > 5:
            _amostra += f" … (+{len(selecionados) - 5})"
        st.caption(f"Será aplicada a: **{_amostra}**")
with lt2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button(
        f"Aplicar aos {len(selecionados)} selecionado(s)" if selecionados else "Nenhum selecionado",
        disabled=not (selecionados and just_lote.strip()),
        use_container_width=True,
        type="primary",
    ):
        for func in selecionados:
            desc = _descricao(func)
            db.salvar_justificativa(aid, func, desc, just_lote.strip())
            if modelo_lote:
                db.salvar_justificativa_modelo(cliente, func, desc, just_lote.strip())
        st.success(f"Justificativa aplicada a {len(selecionados)} pendência(s).")
        recarregar("grade_auditoria")
        st.rerun()

st.divider()

# ── Aprovação e exportação ───────────────────────────────────────────────────
ap1, ap2 = st.columns([3, 1])

with ap1:
    if not _funcs_pend:
        st.success("Nenhuma pendência — todas as linhas estão OK. A auditoria pode ser aprovada.")
    elif _n_pend == 0:
        st.success("Todas as pendências têm justificativa. A auditoria pode ser aprovada.")
    else:
        st.info(f"Faltam **{_n_pend}** justificativa(s) para liberar a aprovação.")

    b1, b2 = st.columns(2)
    with b1:
        if st.button(
            "Aprovar auditoria do período",
            type="primary",
            disabled=_n_pend > 0,
            use_container_width=True,
        ):
            db.aprovar_auditoria(aid)
            st.success(f"Auditoria **{periodo}** aprovada com sucesso!")
            st.balloons()
    with b2:
        if st.button("Reaplicar modelos salvos", use_container_width=True):
            qtd, _ = _aplicar_modelos_exatos(salvar_no_banco=True)
            if qtd:
                st.success(f"{qtd} justificativa(s) reaplicada(s).")
                recarregar("grade_auditoria")
                st.rerun()
            else:
                st.info("Nenhuma justificativa reutilizável encontrada.")

with ap2:
    df_inc = st.session_state.get("df_inc", pd.DataFrame())
    if just_salvas:
        df_just = pd.DataFrame([
            {"Funcionário": f, "Inconsistência": _descricao(f), "Justificativa": j}
            for f, j in just_salvas.items()
        ])
    else:
        df_just = pd.DataFrame()

    st.download_button(
        "Exportar Excel completo",
        data=exportar_excel(df, df_inc, df_just, periodo),
        file_name=f"auditoria_unimed_{periodo.replace('/', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
