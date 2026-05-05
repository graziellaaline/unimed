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
                                ler_faturas_csv, cruzar, _encontrar_col)
from app.regras import aplicar_regras, calcular_stats, identificar_incluidos_mes
from app import db

st.set_page_config(page_title="Importação — Auditoria Unimed", layout="wide")
barra_lateral()
st.header("1 · Importação de Arquivos")

# ── Recarregar última auditoria ───────────────────────────────────────────────
from app.regras import identificar_incluidos_mes

_ultimos = db.listar_periodos()

# Auditoria já na sessão
if "df_audit" in st.session_state and st.session_state["df_audit"] is not None:
    _periodo_atual = st.session_state.get("periodo", "")
    st.success(
        f"✅ Auditoria **{_periodo_atual}** carregada — "
        f"{st.session_state.get('stats', {}).get('ok', 0)} OK · "
        f"{st.session_state.get('stats', {}).get('inconsistente', 0)} inconsistências. "
        "Acesse **2 · Auditoria** no menu."
    )

elif _ultimos:
    # Há auditorias salvas no banco mas nenhuma na sessão
    _ultimo = _ultimos[0]
    st.info(
        f"📂 Última auditoria salva: **{_ultimo['periodo']}** "
        f"· processada em {_ultimo['processado_em']}"
    )
    if st.button(
        f"⬇  Carregar auditoria de {_ultimo['periodo']} (sem importar arquivos)",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner("Carregando…"):
            _df, _stats, _meta = db.carregar_auditoria(
                _ultimo["periodo"], _ultimo["cliente"]
            )
        if _df is not None and not _df.empty:
            st.session_state["df_audit"]     = _df
            st.session_state["df_inc"]       = identificar_incluidos_mes(_df, _ultimo["periodo"])
            st.session_state["stats"]        = _stats or {}
            st.session_state["periodo"]      = _ultimo["periodo"]
            st.session_state["cliente"]      = _ultimo["cliente"]
            st.session_state["auditoria_id"] = (_meta or {}).get("id")
            st.success(
                f"✅ Auditoria **{_ultimo['periodo']}** carregada com sucesso! "
                "Acesse **2 · Auditoria** no menu à esquerda."
            )
        else:
            st.error(
                "Não foi possível carregar a auditoria do banco de dados. "
                "Tente processar os arquivos novamente."
            )

st.divider()

# ── Período e cliente ────────────────────────────────────────────────────────
st.markdown("### Período de referência")
c1, c2 = st.columns([1, 2])
with c1:
    periodo = st.text_input(
        "Mês/Ano  *(obrigatório)*",
        value=st.session_state.get("periodo", ""),
        placeholder="04/2026",
        help="Digite o mês e ano no formato MM/AAAA, ex: 04/2026",
    )
    if periodo and "/" not in periodo:
        st.error("Formato inválido — use MM/AAAA, ex: 04/2026")
        periodo = ""
with c2:
    cliente = st.text_input(
        "Cliente / Empresa  *(opcional — salva mapeamentos)*",
        value=st.session_state.get("cliente", ""),
        placeholder="Ex: Setrata",
    )

st.divider()

# ── Upload dos arquivos ───────────────────────────────────────────────────────
st.markdown("### Arquivos")
uc1, uc2, uc3 = st.columns(3)

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

st.divider()

# ── Preview de colunas detectadas (informativo, sem interação) ───────────────
def _ler_colunas_arq(arq):
    """Lê colunas de um arquivo (UploadedFile). Retorna lista ou []."""
    if not arq:
        return []
    try:
        arq.seek(0)
        dados = arq.read()
        nome = arq.name.lower()
        if nome.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(dados), dtype=str, nrows=3)
        else:
            # Tenta com separadores comuns; nrows=3 para o sniffer funcionar
            for sep in (";", ",", "\t", "|"):
                try:
                    df = pd.read_csv(io.BytesIO(dados), sep=sep, dtype=str,
                                      nrows=3, encoding="latin-1")
                    if len(df.columns) >= 2:
                        return list(df.columns)
                except Exception:
                    continue
            # Fallback: sep=None com engine python
            df = pd.read_csv(io.BytesIO(dados), sep=None, engine="python",
                               dtype=str, nrows=3, encoding="latin-1")
        return list(df.columns)
    except Exception:
        return []


def _icone(col):
    return "✅" if col else "⚠️"


if arq_cont or arq_fats or arq_comp:
    with st.expander("🔍 Colunas detectadas automaticamente", expanded=True):
        dc1, dc2, dc3 = st.columns(3)

        def _mostrar_cols(titulo, cols, mapa_campos):
            st.markdown(f"**{titulo}**")
            if cols:
                # Lista TODAS as colunas encontradas no arquivo
                st.caption(f"📋 Colunas no arquivo: `{'` · `'.join(cols)}`")
                st.markdown("---")
                for label, col_detectada in mapa_campos.items():
                    st.caption(f"{_icone(col_detectada)} {label}: `{col_detectada or 'não encontrado'}`")
            else:
                st.caption("Nenhum arquivo carregado.")

        # Contratos
        cols_cont = _ler_colunas_arq(arq_cont) if arq_cont else []
        df_cont_preview = pd.DataFrame(columns=cols_cont)
        with dc1:
            _mostrar_cols("Contratos", cols_cont, {
                "Funcionário (col D)":  _encontrar_col(df_cont_preview, "funcionario","nome","colaborador") or (cols_cont[3]  if len(cols_cont) > 3  else None),
                "Departamento (col G)": _encontrar_col(df_cont_preview, "departamento","depto","setor")     or (cols_cont[6]  if len(cols_cont) > 6  else None),
                "Valor Plano (col L)":  _encontrar_col(df_cont_preview, "valor plano","vlr plano","plano","saude","mensalidade") or (cols_cont[11] if len(cols_cont) > 11 else None),
                "Admissão (col H)":     _encontrar_col(df_cont_preview, "admissao","dt. admissao","admissão") or (cols_cont[7]  if len(cols_cont) > 7  else None),
            })

        # Fatura
        arq_fat_preview = arq_fats[0] if arq_fats else None
        cols_fat = _ler_colunas_arq(arq_fat_preview) if arq_fat_preview else []
        df_fat_preview = pd.DataFrame(columns=cols_fat)
        with dc2:
            _mostrar_cols("Fatura CSV", cols_fat, {
                "Titular":       _encontrar_col(df_fat_preview, "titular","beneficiario","nome"),
                "Valor":         _encontrar_col(df_fat_preview, "valor","vl."),
                "Data Inclusão": _encontrar_col(df_fat_preview, "data inclusao","data de inclusao","inclusao","dt. inclusao"),
                "Nascimento":    _encontrar_col(df_fat_preview, "nascimento","data nasc"),
            })

        # Compra
        cols_comp = _ler_colunas_arq(arq_comp) if arq_comp else []
        df_comp_preview = pd.DataFrame(columns=cols_comp)
        with dc3:
            _mostrar_cols("Compra", cols_comp, {
                "Funcionário (col F)":    _encontrar_col(df_comp_preview, "funcionario","nome","colaborador") or (cols_comp[5]  if len(cols_comp) > 5  else None),
                "Valor Empresa (col K)":  _encontrar_col(df_comp_preview, "valor empresa","empresa","emp","patronal")           or (cols_comp[10] if len(cols_comp) > 10 else None),
                "Valor Func. (col L)":    _encontrar_col(df_comp_preview, "valor beneficiario","beneficiario","funcionario")    or (cols_comp[11] if len(cols_comp) > 11 else None),
            })

# ── Botão processar ──────────────────────────────────────────────────────────
pode_processar = bool(arq_cont and periodo and "/" in periodo)

if not arq_cont:
    st.info("📋 Carregue a **planilha de contratos** para habilitar o processamento.")
elif not periodo:
    st.warning("📅 Preencha o **período de referência** (ex: 04/2026) para habilitar o processamento.")

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

    try:
        with st.spinner(f"Processando auditoria de {periodo}…"):
            p_cont = _tmp(arq_cont)
            p_fats = [_tmp(a) for a in (arq_fats or [])]
            p_comp = _tmp(arq_comp) if arq_comp else None

            # Mapeamento automático — sem interação do usuário
            mc  = db.carregar_mapeamento(cliente, "contratos") if cliente else {}
            mf  = db.carregar_mapeamento(cliente, "fatura")    if cliente else {}
            mcp = db.carregar_mapeamento(cliente, "compra")    if cliente else {}

            df_cont   = ler_contratos(p_cont, mc)
            df_fat    = ler_faturas_csv(p_fats, mf) if p_fats else pd.DataFrame()
            df_compra = ler_compra(p_comp, mcp)     if p_comp else pd.DataFrame()

            if df_cont.empty:
                st.error("Não foi possível ler a planilha de contratos. Verifique o arquivo.")
                st.stop()

            df_audit = cruzar(df_cont, df_fat, df_compra, periodo)
            df_audit = aplicar_regras(df_audit)

        stats  = calcular_stats(df_audit)
        df_inc = identificar_incluidos_mes(df_audit, periodo)

        aid = db.salvar_auditoria(df_audit, stats, periodo, cliente)
        if cliente:
            db.salvar_mapeamento(cliente, "contratos", mc)
            if p_fats:
                db.salvar_mapeamento(cliente, "fatura", mf)
            if p_comp:
                db.salvar_mapeamento(cliente, "compra", mcp)

        st.session_state.update({
            "df_audit":     df_audit,
            "df_inc":       df_inc,
            "stats":        stats,
            "periodo":      periodo,
            "cliente":      cliente,
            "auditoria_id": aid,
        })

        n_inc = len(df_inc)
        st.success(
            f"✅ Auditoria **{periodo}** concluída — "
            f"**{stats['total']}** registros · "
            f"**{stats['ok']}** OK · "
            f"**{stats['inconsistente']}** inconsistências"
            + (f" · **{n_inc}** incluído(s) no mês" if n_inc else "")
        )
        st.info("👉 Acesse **2 · Auditoria** no menu à esquerda para ver o resultado.")

    except Exception as exc:
        st.error(f"Erro ao processar: {exc}")
        import traceback
        with st.expander("Detalhes técnicos do erro"):
            st.code(traceback.format_exc())

    finally:
        for p in ([p_cont] if p_cont else []) + p_fats + ([p_comp] if p_comp else []):
            try:
                os.unlink(p)
            except Exception:
                pass
