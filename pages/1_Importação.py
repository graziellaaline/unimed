# -*- coding: utf-8 -*-
import io
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ui import barra_lateral
from app.processamento import (ler_contratos, ler_compra,
                                 ler_faturas_csv, cruzar, mesclar_desligados,
                                 _encontrar_col, _encontrar_col_prioritaria,
                                 _score_cabecalho, CONTRATOS_HEADER_GROUPS,
                                 FATURA_HEADER_GROUPS, COMPRA_HEADER_GROUPS)
from app.exclusoes_indevidas import ler_desligados  # usado em page 6 e fallback
from app.regras import aplicar_regras, calcular_stats, identificar_incluidos_mes, _parse_periodo
from app import db

st.set_page_config(page_title="Importação — Auditoria Unimed", layout="wide")
barra_lateral()
st.header("1 · Importação de Arquivos")

# ── Recarregar última auditoria ───────────────────────────────────────────────
from app.regras import identificar_incluidos_mes

_ultimos = db.listar_periodos()


def _processar_auditoria(periodo, cliente, p_cont, p_fats, p_comp, p_desl=None):
    mc  = db.carregar_mapeamento(cliente, "contratos") if cliente else {}
    mf  = db.carregar_mapeamento(cliente, "fatura")    if cliente else {}
    mcp = db.carregar_mapeamento(cliente, "compra")    if cliente else {}

    df_cont   = ler_contratos(p_cont, mc)
    df_fat    = ler_faturas_csv(p_fats, mf) if p_fats else pd.DataFrame()
    df_compra = ler_compra(p_comp, mcp)     if p_comp else pd.DataFrame()

    if df_cont.empty:
        raise ValueError("Não foi possível ler a planilha de contratos. Verifique o arquivo.")

    df_cruzado = cruzar(df_cont, df_fat, df_compra, periodo)

    # ── Mesclagem com planilha de contratos inativos (desligados) ────────────
    # A planilha de inativos tem a mesma estrutura da de ativos — lida com ler_contratos.
    df_desl   = None
    relatorio = {}
    if p_desl:
        df_desl = ler_contratos(p_desl)   # mesma estrutura → usa mesma função
        df_cruzado, relatorio = mesclar_desligados(df_cruzado, df_desl, periodo)

    df_audit = aplicar_regras(df_cruzado)
    stats  = calcular_stats(df_audit)
    df_inc = identificar_incluidos_mes(df_audit, periodo)
    aid = db.salvar_auditoria(df_audit, stats, periodo, cliente)

    # Herdar justificativas da auditoria anterior — nunca perder aprovações ao reprocessar
    db.migrar_justificativas(aid, periodo, cliente)

    if cliente:
        db.salvar_mapeamento(cliente, "contratos", mc)
        if p_fats:
            db.salvar_mapeamento(cliente, "fatura", mf)
        if p_comp:
            db.salvar_mapeamento(cliente, "compra", mcp)

    return df_audit, stats, df_inc, aid, df_desl, relatorio


def _atualizar_sessao(df_audit, df_inc, stats, periodo, cliente, aid,
                      arquivos_fontes=None, df_desl=None, relatorio=None):
    st.session_state.update({
        "df_audit":           df_audit,
        "df_inc":             df_inc,
        "stats":              stats,
        "periodo":            periodo,
        "cliente":            cliente,
        "auditoria_id":       aid,
        "arquivos_fontes":    arquivos_fontes or st.session_state.get("arquivos_fontes", {}),
        "df_desligados":      df_desl,
        "relatorio_desligados": relatorio or {},
    })


def _mostrar_relatorio_desligados(relatorio: dict):
    """Exibe seção de inconsistências da importação de desligados."""
    if not relatorio:
        return

    sem_dt     = relatorio.get("sem_dt", [])
    pendencias = relatorio.get("pendencias", [])

    # "sem_match" (desligados sem correspondência na base ativa) não é exibido:
    # a planilha de inativos acumula desligados de qualquer época, então é normal
    # ter centenas que não pertencem ao período atual — não é uma inconsistência
    # acionável para a usuária.
    tem_algo = any([sem_dt, pendencias])
    if not tem_algo:
        st.success("✅ Todos os desligados foram vinculados por matrícula+nome sem inconsistências.")
        return

    with st.expander("⚠️ Inconsistências da planilha de desligados", expanded=True):
        if sem_dt:
            st.markdown(f"**📅 {len(sem_dt)} desligado(s) sem data de demissão na planilha**")
            st.caption("Encontrados na base mas a planilha não tem data — demissão não foi atualizada.")
            st.dataframe(pd.DataFrame({"Nome": sem_dt}), use_container_width=True, hide_index=True)

        if pendencias:
            st.markdown(f"**�?� {len(pendencias)} funcionário(s) com status desligado mas sem data de demissão**")
            st.caption(
                "Marcados como desligados (do contratos ou da planilha) sem data disponível — "
                "revise a planilha de desligados."
            )
            st.dataframe(pd.DataFrame({"Funcionário": pendencias}), use_container_width=True, hide_index=True)


# ── Auto-carregar arquivos_fontes quando sessão reinicia ─────────────────────
if "df_audit" in st.session_state and st.session_state["df_audit"] is not None:
    if not st.session_state.get("arquivos_fontes"):
        _aid_sess = st.session_state.get("auditoria_id")
        if _aid_sess:
            _arqs_sess = db.carregar_arquivos_auditoria(_aid_sess)
            if any(_arqs_sess.get(k) for k in ("contratos", "fatura", "compra")):
                st.session_state["arquivos_fontes"] = _arqs_sess

# Auditoria já na sessão
if "df_audit" in st.session_state and st.session_state["df_audit"] is not None:
    _periodo_atual = st.session_state.get("periodo", "")
    st.success(
        f"✅ Auditoria **{_periodo_atual}** carregada — "
        f"{st.session_state.get('stats', {}).get('ok', 0)} OK · "
        f"{st.session_state.get('stats', {}).get('inconsistente', 0)} inconsistências. "
        "Acesse **5 · Auditoria** no menu."
    )
    # Mostrar relatório de desligados da sessão, se houver
    _rel_sessao = st.session_state.get("relatorio_desligados", {})
    if _rel_sessao:
        _mostrar_relatorio_desligados(_rel_sessao)

elif _ultimos:
    # Há auditorias salvas no banco mas nenhuma na sessão
    _ultimo = _ultimos[0]
    _aid_ult = _ultimo.get("id")
    _arqs_ult = db.carregar_arquivos_auditoria(_aid_ult) if _aid_ult else {}
    _tem_arqs = any(_arqs_ult.get(k) for k in ("contratos", "fatura", "compra"))

    st.info(
        f"📂 Última auditoria salva: **{_ultimo['periodo']}** "
        f"· processada em {_ultimo['processado_em']}"
    )
    _bc1, _bc2 = st.columns(2)

    with _bc1:
        if st.button(
            f"⬇  Carregar resultado de {_ultimo['periodo']} (sem reimportar)",
            use_container_width=True,
        ):
            with st.spinner("Carregando…"):
                _df, _stats, _meta = db.carregar_auditoria(
                    _ultimo["periodo"], _ultimo["cliente"]
                )
            if _df is not None and not _df.empty:
                _df = aplicar_regras(_df)
                _stats = calcular_stats(_df)
                _aid = (_meta or {}).get("id")
                # Auto-carregar desligados salvos
                _df_desl = None
                if _arqs_ult.get("desligados"):
                    try:
                        _p_desl_saved = _arqs_ult["desligados"][0]["caminho"]
                        _df_desl, _ = ler_desligados(_p_desl_saved)
                    except Exception:
                        pass
                _atualizar_sessao(
                    _df,
                    identificar_incluidos_mes(_df, _ultimo["periodo"]),
                    _stats or {},
                    _ultimo["periodo"],
                    _ultimo["cliente"],
                    _aid,
                    _arqs_ult,
                    df_desl=_df_desl,
                )
                st.success(
                    f"✅ Auditoria **{_ultimo['periodo']}** carregada! "
                    "Acesse **5 · Auditoria** no menu à esquerda."
                )
                st.rerun()
            else:
                st.error(
                    "Não foi possível carregar a auditoria do banco. "
                    "Tente reprocessar os arquivos."
                )

    with _bc2:
        if st.button(
            f"🔄 Reprocessar {_ultimo['periodo']} com regras atuais"
            if _tem_arqs else "🔄 Reprocessar (sem arquivos salvos)",
            type="primary",
            disabled=not _tem_arqs,
            use_container_width=True,
        ):
            try:
                with st.spinner(f"Reprocessando {_ultimo['periodo']}…"):
                    _p_cont = (_arqs_ult.get("contratos") or [{}])[0].get("caminho")
                    _p_fats = [x["caminho"] for x in _arqs_ult.get("fatura", [])]
                    _p_comp_item = (_arqs_ult.get("compra") or [None])[0]
                    _p_comp = _p_comp_item.get("caminho") if isinstance(_p_comp_item, dict) else None
                    _p_desl_item = (_arqs_ult.get("desligados") or [None])[0]
                    _p_desl = _p_desl_item.get("caminho") if isinstance(_p_desl_item, dict) else None
                    df_r, stats_r, df_inc_r, aid_r, df_desl_r, rel_r = _processar_auditoria(
                        _ultimo["periodo"], _ultimo["cliente"],
                        _p_cont, _p_fats, _p_comp, _p_desl,
                    )
                    db.salvar_arquivos_auditoria(aid_r, {
                        "contratos":  [{"nome": Path(x["caminho"]).name, "origem": x["caminho"]} for x in _arqs_ult.get("contratos", [])],
                        "fatura":     [{"nome": Path(x["caminho"]).name, "origem": x["caminho"]} for x in _arqs_ult.get("fatura", [])],
                        "compra":     [{"nome": Path(x["caminho"]).name, "origem": x["caminho"]} for x in _arqs_ult.get("compra", [])],
                        "desligados": [{"nome": Path(x["caminho"]).name, "origem": x["caminho"]} for x in _arqs_ult.get("desligados", [])],
                    })
                    _arqs_r = db.carregar_arquivos_auditoria(aid_r)
                    _atualizar_sessao(df_r, df_inc_r, stats_r,
                                      _ultimo["periodo"], _ultimo["cliente"], aid_r, _arqs_r,
                                      df_desl=df_desl_r, relatorio=rel_r)
                st.success(f"✅ Auditoria **{_ultimo['periodo']}** reprocessada com as regras atuais.")
                if rel_r:
                    _mostrar_relatorio_desligados(rel_r)
                st.rerun()
            except Exception as _exc:
                st.error(f"Erro ao reprocessar: {_exc}")
                import traceback as _tb
                with st.expander("Detalhes técnicos"):
                    st.code(_tb.format_exc())

# ── Período e cliente ────────────────────────────────────────────────────────
st.markdown("### Período de referência")
c1, c2 = st.columns([1, 2])
with c1:
    periodo = st.text_input(
        "Mês/Ano  *(obrigatório)*",
        value=st.session_state.get("periodo", ""),
        placeholder="04/2026",
        help="Digite o mês e ano no formato MM/AA ou MM/AAAA, ex: 04/26 ou 04/2026",
    )
    if periodo and _parse_periodo(periodo) == (None, None):
        st.error("Formato inválido — use MM/AA ou MM/AAAA, ex: 04/26 ou 04/2026")
        periodo = ""
with c2:
    cliente = st.text_input(
        "Cliente / Empresa  *(opcional — salva mapeamentos)*",
        value=st.session_state.get("cliente", ""),
        placeholder="Ex: Setrata",
    )

st.divider()

arquivos_fontes = st.session_state.get("arquivos_fontes", {})
if any(arquivos_fontes.get(k) for k in ("contratos", "fatura", "compra")):
    st.markdown("### Arquivos carregados")
    a1, a2, a3, a4 = st.columns(4)
    with a1:
        st.caption("**Contratos**")
        for item in arquivos_fontes.get("contratos", []):
            st.write(item["nome"])
    with a2:
        st.caption("**Faturas**")
        for item in arquivos_fontes.get("fatura", []):
            st.write(item["nome"])
    with a3:
        st.caption("**Compra**")
        for item in arquivos_fontes.get("compra", []):
            st.write(item["nome"])
    with a4:
        st.caption("**Desligados**")
        for item in arquivos_fontes.get("desligados", []):
            st.write(item["nome"])
        if not arquivos_fontes.get("desligados"):
            st.caption("_Nenhum arquivo_")

    if st.button("🔄 Reprocessar com arquivos salvos", use_container_width=True, type="primary"):
        _periodo_reprocess = periodo or st.session_state.get("periodo", "")
        _cliente_reprocess = cliente or st.session_state.get("cliente", "")
        try:
            with st.spinner("Reprocessando…"):
                _p_cont = (arquivos_fontes.get("contratos") or [{}])[0].get("caminho")
                _p_fats = [x["caminho"] for x in arquivos_fontes.get("fatura", [])]
                _p_comp = (arquivos_fontes.get("compra") or [None])[0]
                if isinstance(_p_comp, dict):
                    _p_comp = _p_comp.get("caminho")
                _p_desl_item = (arquivos_fontes.get("desligados") or [None])[0]
                _p_desl = _p_desl_item.get("caminho") if isinstance(_p_desl_item, dict) else None
                df_audit_r, stats_r, df_inc_r, aid_r, df_desl_r, rel_r = _processar_auditoria(
                    _periodo_reprocess, _cliente_reprocess,
                    _p_cont, _p_fats, _p_comp, _p_desl,
                )
                db.salvar_arquivos_auditoria(aid_r, {
                    "contratos":  [{"nome": Path(x["caminho"]).name, "origem": x["caminho"]} for x in arquivos_fontes.get("contratos", [])],
                    "fatura":     [{"nome": Path(x["caminho"]).name, "origem": x["caminho"]} for x in arquivos_fontes.get("fatura", [])],
                    "compra":     [{"nome": Path(x["caminho"]).name, "origem": x["caminho"]} for x in arquivos_fontes.get("compra", [])],
                    "desligados": [{"nome": Path(x["caminho"]).name, "origem": x["caminho"]} for x in arquivos_fontes.get("desligados", [])],
                })
                _arqs_r = db.carregar_arquivos_auditoria(aid_r)
                _atualizar_sessao(df_audit_r, df_inc_r, stats_r,
                                  _periodo_reprocess, _cliente_reprocess, aid_r, _arqs_r,
                                  df_desl=df_desl_r, relatorio=rel_r)
            st.success(f"✅ Auditoria **{_periodo_reprocess}** reprocessada.")
            if rel_r:
                _mostrar_relatorio_desligados(rel_r)
            st.rerun()
        except Exception as exc:
            st.error(f"Erro ao reprocessar: {exc}")
            import traceback as _tb
            with st.expander("Detalhes técnicos"):
                st.code(_tb.format_exc())

    st.divider()

# ── Upload dos arquivos ───────────────────────────────────────────────────────
st.markdown("### Arquivos")
uc1, uc2, uc3, uc4 = st.columns(4)

with uc1:
    st.markdown("**📋 Funcionários por Contrato**")
    st.caption("Obrigatório · Excel ou CSV")
    arq_cont = st.file_uploader("Contratos", type=["xlsx", "xls", "csv"],
                                 key="up_cont", label_visibility="collapsed")

with uc2:
    st.markdown("**📄 Faturas Unimed**")
    st.caption("Selecione quantas quiser · Excel ou CSV")
    arq_fats = st.file_uploader("Faturas", type=["xlsx", "xls", "csv"],
                                 key="up_fat", label_visibility="collapsed",
                                 accept_multiple_files=True)
    if arq_fats:
        st.caption(f"✅ {len(arq_fats)} arquivo(s) carregado(s)")

with uc3:
    st.markdown("**💳 Compra / Lançamento**")
    st.caption("Opcional · Excel ou CSV")
    arq_comp = st.file_uploader("Compra", type=["xlsx", "xls", "csv"],
                                 key="up_comp", label_visibility="collapsed")

with uc4:
    st.markdown("**🚫 Funcionários Desligados**")
    st.caption("Opcional · Excel ou CSV com nome e data de demissão")
    arq_desl = st.file_uploader("Desligados", type=["xlsx", "xls", "csv"],
                                 key="up_desl", label_visibility="collapsed")
    if arq_desl:
        st.caption("✅ Arquivo carregado")

st.divider()

# ── Preview de colunas detectadas (informativo, sem interação) ───────────────
def _ler_colunas_arq(arq, grupos_keywords=None):
    """Lê colunas de um arquivo (UploadedFile). Retorna lista ou []."""
    if not arq:
        return []
    try:
        arq.seek(0)
        dados = arq.read()
        nome = arq.name.lower()
        melhor_cols = []
        melhor_score = -1

        def _cols_validas(df):
            if df.empty or len(df.columns) < 2:
                return False
            named = sum(1 for c in df.columns if not str(c).lower().startswith("unnamed"))
            return named >= 2

        if nome.endswith((".xlsx", ".xls")):
            for header_row in range(9):
                try:
                    df = pd.read_excel(io.BytesIO(dados), dtype=str, header=header_row)
                    df = df.dropna(how="all").dropna(how="all", axis=1)
                    score = _score_cabecalho(df, grupos_keywords)
                    if _cols_validas(df) and score > melhor_score:
                        melhor_cols = list(df.columns)
                        melhor_score = score
                except Exception:
                    continue
        else:
            for enc in ("latin-1", "cp1252", "utf-8-sig", "utf-8"):
                for sep in (";", ",", "\t", "|"):
                    for header_row in range(9):
                        try:
                            df = pd.read_csv(
                                io.BytesIO(dados),
                                sep=sep,
                                dtype=str,
                                encoding=enc,
                                header=header_row,
                                skip_blank_lines=True,
                                on_bad_lines="skip",
                            )
                            df = df.dropna(how="all").dropna(how="all", axis=1)
                            score = _score_cabecalho(df, grupos_keywords)
                            if _cols_validas(df) and score > melhor_score:
                                melhor_cols = list(df.columns)
                                melhor_score = score
                        except Exception:
                            continue
        return melhor_cols
    except Exception:
        return []


def _icone(col):
    return "✅" if col else "⚠�?"


if arq_cont or arq_fats or arq_comp or arq_desl:
    with st.expander("�? Colunas detectadas automaticamente", expanded=True):
        dc1, dc2, dc3, dc4 = st.columns(4)

        def _mostrar_cols(titulo, cols, mapa_campos):
            st.markdown(f"**{titulo}**")
            if cols:
                st.caption(f"📋 Colunas no arquivo: `{'` · `'.join(cols)}`")
                st.markdown("---")
                for label, col_detectada in mapa_campos.items():
                    st.caption(f"{_icone(col_detectada)} {label}: `{col_detectada or 'não encontrado'}`")
            else:
                st.caption("Nenhum arquivo carregado.")

        # Contratos
        cols_cont = _ler_colunas_arq(arq_cont, CONTRATOS_HEADER_GROUPS) if arq_cont else []
        df_cont_preview = pd.DataFrame(columns=cols_cont)
        with dc1:
            _mostrar_cols("Contratos", cols_cont, {
                "Funcionário":         _encontrar_col_prioritaria(df_cont_preview, "nome do funcionario","nome da funcionaria","nome funcionario","nome da funcionária","funcionario","funcionária","nome colaborador","nome empregado","nome"),
                "Empresa":             _encontrar_col(df_cont_preview, "cód. empresa","cod empresa","empresa"),
                "Departamento":        _encontrar_col(df_cont_preview, "departamento","depto","setor","unidade","lotação"),
                "Contrato Adm.":       _encontrar_col(df_cont_preview, "contrato adm","contrato administrativo","contrato adm.","contr. adm","tipo contrato"),
                "Valor Plano":         _encontrar_col(df_cont_preview, "valor plano de saúde","valor plano de saude","valor plano","vlr plano","mensalidade titular","valor mensal titular","plano","saude","mensalidade"),
                "Admissão":            _encontrar_col(df_cont_preview, "dt. admissão","dt. admissao","admissão","dt adm","data adm"),
            })

        # Fatura
        arq_fat_preview = arq_fats[0] if arq_fats else None
        cols_fat = _ler_colunas_arq(arq_fat_preview, FATURA_HEADER_GROUPS) if arq_fat_preview else []
        df_fat_preview = pd.DataFrame(columns=cols_fat)
        with dc2:
            _mostrar_cols("Fatura CSV", cols_fat, {
                "Titular":       _encontrar_col_prioritaria(df_fat_preview, "nome do titular","beneficiário titular","beneficiario titular","titular","beneficiário","beneficiario","nome"),
                "Descrição":     _encontrar_col(df_fat_preview, "descrição do item","descricao do item","descrição","descricao"),
                "Valor":         _encontrar_col(df_fat_preview, "valor","vl."),
                "Data Inclusão": _encontrar_col(df_fat_preview, "data inclusao","data de inclusao","inclusao","dt. inclusao"),
                "Nascimento":    _encontrar_col(df_fat_preview, "nascimento","data nasc"),
            })

        # Compra
        cols_comp = _ler_colunas_arq(arq_comp, COMPRA_HEADER_GROUPS) if arq_comp else []
        df_comp_preview = pd.DataFrame(columns=cols_comp)
        with dc3:
            _mostrar_cols("Compra", cols_comp, {
                "Funcionário":            _encontrar_col_prioritaria(df_comp_preview, "nome do funcionario","nome da funcionaria","nome funcionario","nome da funcionária","beneficiario titular","funcionario","funcionária","titular","nome"),
                "Valor Empresa":          _encontrar_col(df_comp_preview, "valor. empresa","valor empresa","valor mensal empresa","mensalidade empresa","patronal","custo empresa","empresa"),
                "Valor Func.":            _encontrar_col(df_comp_preview, "valor. beneficário","valor beneficário","valor beneficiario","valor funcionario","mensalidade funcionario","desconto funcionario","beneficiario"),
            })

        # Desligados
        if arq_desl:
            arq_desl.seek(0)
            _desl_bytes = arq_desl.read()
            _desl_nome  = arq_desl.name.lower()
            try:
                from app.exclusoes_indevidas import _melhor_df, _encontrar_col as _ec_d
                _raw_desl = _melhor_df(_desl_bytes, _desl_nome)
                cols_desl = list(_raw_desl.columns) if _raw_desl is not None else []
            except Exception:
                cols_desl = []
            df_desl_preview = pd.DataFrame(columns=cols_desl)
            with dc4:
                _mostrar_cols("Desligados", cols_desl, {
                    "Nome":            _ec_d(df_desl_preview, "nome funcionario","nome colaborador","funcionario","nome"),
                    "Data Demissão":   _ec_d(df_desl_preview, "demissao","desligamento","rescisao","data demissao","saida"),
                    "CPF":             _ec_d(df_desl_preview, "cpf","documento"),
                    "Matrícula":       _ec_d(df_desl_preview, "matricula","chapa","cod func","codigo"),
                })
        else:
            with dc4:
                st.markdown("**Desligados**")
                st.caption("Nenhum arquivo carregado.")

# ── Botão processar ──────────────────────────────────────────────────────────
pode_processar = bool(arq_cont and periodo and _parse_periodo(periodo) != (None, None))

if not arq_cont:
    st.info("📋 Carregue a **planilha de contratos** para habilitar o processamento.")
elif not periodo:
    st.warning("📅 Preencha o **período de referência** (ex: 04/26 ou 04/2026) para habilitar o processamento.")

st.markdown("---")
btn = st.button(
    "▶  Processar Auditoria",
    type="primary",
    disabled=not pode_processar,
    use_container_width=True,
)

if btn:
    def _tmp(arq):
        arq.seek(0)
        suf = Path(arq.name).suffix
        f = tempfile.NamedTemporaryFile(delete=False, suffix=suf)
        f.write(arq.read())
        f.close()
        return f.name

    p_cont = None
    p_fats = []
    p_comp = None
    p_desl = None

    try:
        with st.spinner(f"Processando auditoria de {periodo}…"):
            p_cont = _tmp(arq_cont)
            p_fats = [_tmp(a) for a in (arq_fats or [])]
            p_comp = _tmp(arq_comp) if arq_comp else None
            p_desl = _tmp(arq_desl) if arq_desl else None
            df_audit, stats, df_inc, aid, df_desl, relatorio = _processar_auditoria(
                periodo, cliente, p_cont, p_fats, p_comp, p_desl
            )

        arquivos_salvos = {
            "contratos":  [{"nome": arq_cont.name, "origem": p_cont}],
            "fatura":     [{"nome": a.name, "origem": p} for a, p in zip((arq_fats or []), p_fats)],
            "compra":     [{"nome": arq_comp.name, "origem": p_comp}] if p_comp and arq_comp else [],
            "desligados": [{"nome": arq_desl.name, "origem": p_desl}] if p_desl and arq_desl else [],
        }
        db.salvar_arquivos_auditoria(aid, arquivos_salvos)
        arquivos_fontes = db.carregar_arquivos_auditoria(aid)
        _atualizar_sessao(df_audit, df_inc, stats, periodo, cliente, aid, arquivos_fontes,
                          df_desl=df_desl, relatorio=relatorio)

        n_inc = len(df_inc)
        n_desl = len(df_desl) if df_desl is not None and not df_desl.empty else 0
        st.success(
            f"✅ Auditoria **{periodo}** concluída — "
            f"**{stats['total']}** registros · "
            f"**{stats['ok']}** OK · "
            f"**{stats['inconsistente']}** inconsistências"
            + (f" · **{n_inc}** incluído(s) no mês" if n_inc else "")
            + (f" · **{n_desl}** desligado(s) mesclados" if n_desl else "")
        )

        if relatorio:
            _mostrar_relatorio_desligados(relatorio)

        st.info("👉 Acesse **5 · Auditoria** no menu à esquerda para ver o resultado.")

    except Exception as exc:
        st.error(f"Erro ao processar: {exc}")
        import traceback
        with st.expander("Detalhes técnicos do erro"):
            st.code(traceback.format_exc())

    finally:
        for p in ([p_cont] if p_cont else []) + p_fats + ([p_comp] if p_comp else []) + ([p_desl] if p_desl else []):
            try:
                os.unlink(p)
            except Exception:
                pass
