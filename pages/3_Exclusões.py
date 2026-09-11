# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.ui import barra_lateral, tabela
from app.grade import grade
from app import db
from app.processamento import _norm, indice_titulares, localizar_titular
from app.exportacao import exportar_descricoes_unimed, exportar_excel_exclusoes

st.set_page_config(page_title="Exclusões do Mês — Unimed", layout="wide")
barra_lateral()
st.header("3 · Exclusões do Mês de Referência")

# ── Auto-carregar auditoria (mesmo comportamento das demais abas) ─────────────
if "df_audit" not in st.session_state or st.session_state["df_audit"] is None:
    from app.regras import aplicar_regras, calcular_stats, identificar_incluidos_mes

    _ults = db.listar_periodos()
    _ult  = _ults[0] if _ults else None
    _df   = None
    if _ult:
        with st.spinner(f"Carregando auditoria {_ult['periodo']}…"):
            _df, _stats, _meta = db.carregar_auditoria(_ult["periodo"], _ult["cliente"])
    if _df is not None and not _df.empty:
        _df  = aplicar_regras(_df)
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

# Quem do mês anterior não foi localizado no mês atual = exclusão.
# A busca casa por matrícula (com nome ou admissão confirmando) antes do nome,
# senão quem muda de nome — casamento, p. ex. — viraria exclusão todo mês.
_idx_atual = indice_titulares(fat_atual)
_achados   = [localizar_titular(r, _idx_atual) for _, r in fat_ant.iterrows()]

mask   = pd.Series([not ok for ok, _ in _achados], index=fat_ant.index)
df_exc = fat_ant[mask].copy()

# Mesma matrícula com nome diferente: não é exclusão, é troca de nome
_renomeados = [
    (str(r.get("Funcionário", "")), reg["nome"])
    for (ok, reg), (_, r) in zip(_achados, fat_ant.iterrows())
    if ok and reg and _norm_nome(reg["nome"]) != _norm_nome(r.get("Funcionário", ""))
]

# Os valores desta lista são da fatura de `periodo_ant_sel` — último mês em que
# a pessoa foi cobrada. Ficam preservados (antes eram zerados, o que deixava a
# tabela inteira em R$ 0,00 e a coluna de composição sempre "—"): é justamente
# o que estava sendo cobrado que decide se cabe estorno. Os cabeçalhos abaixo
# levam o mês de referência para não parecer cobrança do mês atual.

# ── Enriquecer excluídos com dados dos inativos (para sem_contrato) ───────────
# Funcionários que aparecem só na fatura (_sem_contrato) têm empresa/dept vazios.
# Fonte 1: arquivo de inativos salvo no banco.
# Fonte 2: upload manual na própria página.

from app.processamento import ler_contratos as _ler_cont

_df_inat = pd.DataFrame()

# Fonte 1: arquivo salvo
_aid_atual  = st.session_state.get("auditoria_id")
_arqs_atual = db.carregar_arquivos_auditoria(_aid_atual) if _aid_atual else {}
_desl_item  = (_arqs_atual.get("desligados") or [None])[0]
if _desl_item and _desl_item.get("caminho"):
    try:
        _df_inat = _ler_cont(_desl_item["caminho"])
    except Exception:
        pass

# Fonte 2: upload manual (quando não há arquivo salvo ou para override)
_sem_dados = df_exc[
    df_exc["Empresa"].astype(str).str.strip().isin(["", "nan", "None"])
].shape[0] if not df_exc.empty else 0

if _df_inat.empty or _sem_dados > 0:
    with st.expander(
        "📂 Planilha de inativos não encontrada — faça upload para preencher os dados ausentes"
        if _df_inat.empty
        else f"📂 {_sem_dados} exclusão(ões) sem dados — carregue a planilha de inativos para enriquecer",
        expanded=_df_inat.empty,
    ):
        st.caption(
            "Funcionários que aparecem apenas na fatura (sem linha nos contratos ativos) "
            "precisam da planilha de inativos para mostrar empresa, departamento e contrato."
        )
        _arq_inat_up = st.file_uploader(
            "Planilha de funcionários inativos (mesma estrutura dos contratos ativos)",
            type=["xlsx", "xls", "csv"],
            key="up_inat_exc",
        )
        if _arq_inat_up:
            import tempfile, os
            _arq_inat_up.seek(0)
            _suf = Path(_arq_inat_up.name).suffix
            _tmp = tempfile.NamedTemporaryFile(delete=False, suffix=_suf)
            _tmp.write(_arq_inat_up.read())
            _tmp.close()
            try:
                _df_inat = _ler_cont(_tmp.name)
                st.success(f"✅ {len(_df_inat)} registro(s) carregado(s) da planilha de inativos.")
            except Exception as _e:
                st.error(f"Erro ao ler planilha: {_e}")
            finally:
                try:
                    os.unlink(_tmp.name)
                except Exception:
                    pass

# Aplicar enriquecimento
if not _df_inat.empty and not df_exc.empty:
    _inat_mat  = {}
    _inat_nome = {}
    for _, _ir in _df_inat.iterrows():
        _cod_i = str(_ir.get("cod_func", "") or "").strip()
        _nn_i  = str(_ir.get("_norm_func", "") or "").strip()
        if _cod_i and _nn_i:
            _inat_mat[(_cod_i, _nn_i)] = _ir
        if _nn_i:
            _inat_nome[_nn_i] = _ir

    _campos = [
        ("Empresa",        "empresa"),
        ("Departamento",   "departamento"),
        ("Contrato Adm.",  "contrato_adm"),
        ("Dt. Admissão",   "admissao"),
        ("Dt. Demissão",   "demissao"),
    ]
    for _idx, _row in df_exc.iterrows():
        _cod = str(_row.get("Cod. Funcionário", "") or "").strip()
        _nn  = _norm_nome(_row.get("Funcionário", ""))
        # Usar get com chave composta; se não achar, tentar só por nome
        _irow = _inat_mat.get((_cod, _nn))
        if _irow is None:
            _irow = _inat_nome.get(_nn)
        if _irow is None:
            continue
        for _ca, _ci in _campos:
            if _ca in df_exc.columns:
                _val = str(_irow.get(_ci, "") or "").strip()
                _cur = str(_row.get(_ca, "") or "").strip()
                if _val and _val.lower() not in ("nan", "none") and not _cur:
                    df_exc.at[_idx, _ca] = _val

# ── Separar o residual de conta médica ───────────────────────────────────────
# Quem constava na fatura anterior só com coparticipação não era titular ativo
# do plano naquele mês: é cobrança de atendimento já ocorrido, comum em quem já
# estava desligado. Sumir no mês seguinte é o esperado, não é exclusão.
def _so_conta_medica(row) -> bool:
    return (float(row.get("_vlr_mensalidade_fat", 0) or 0) <= 0
            and float(row.get("_vlr_dependente_fat", 0) or 0) <= 0
            and float(row.get("_vlr_copart_fat", 0) or 0) > 0)


df_copart = pd.DataFrame()
if not df_exc.empty:
    _mask_cm  = df_exc.apply(_so_conta_medica, axis=1)
    df_copart = df_exc[_mask_cm].copy()
    df_exc    = df_exc[~_mask_cm].copy()

# ── Resumo ────────────────────────────────────────────────────────────────────
st.divider()

m1, m2, m3 = st.columns(3)
m1.metric(f"Titulares em {periodo_ant_sel}",  len(fat_ant))
m2.metric(f"Titulares em {periodo}",          len(fat_atual))
m3.metric("Exclusões identificadas",           len(df_exc),
          delta=f"-{len(df_exc)}" if len(df_exc) else None,
          delta_color="inverse")

if _renomeados:
    with st.expander(
        f"✍️ {len(_renomeados)} titular(es) mudaram de nome entre {periodo_ant_sel} e {periodo} "
        "— não são exclusões",
        expanded=False,
    ):
        st.caption(
            "Mesma matrícula e mesma data de admissão, nome diferente na fatura "
            "(casamento, correção de cadastro). Continuam ativos."
        )
        tabela(
            pd.DataFrame(_renomeados, columns=[f"Nome em {periodo_ant_sel}", f"Nome em {periodo}"]),
            use_container_width=True, hide_index=True,
        )

if not df_copart.empty:
    with st.expander(
        f"🩺 {len(df_copart)} pessoa(s) tinham só conta médica em {periodo_ant_sel} "
        "— não são exclusões de plano",
        expanded=False,
    ):
        st.caption(
            "Não havia mensalidade na fatura, só coparticipação (atendimento já realizado) "
            "— normalmente resíduo de quem já estava desligado. Não sair no mês seguinte "
            "é o esperado; a cobrança de uso não é estornável."
        )
        _cols_cm = [c for c in ["Funcionário", "Empresa", "Departamento", "Contrato Adm.",
                                "Dt. Admissão", "Dt. Demissão", "_vlr_copart_fat"]
                    if c in df_copart.columns]
        _tab_cm = df_copart[_cols_cm].copy().reset_index(drop=True)
        _tab_cm = _tab_cm.rename(columns={"_vlr_copart_fat": f"Conta médica ({periodo_ant_sel})"})
        _col_cm = f"Conta médica ({periodo_ant_sel})"
        if _col_cm in _tab_cm.columns:
            _tab_cm[_col_cm] = _tab_cm[_col_cm].apply(
                lambda v: f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
        tabela(_tab_cm, use_container_width=True, hide_index=True)

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
# Quebra do valor cobrado: mensalidade titular, dependentes e/ou coparticipação.
# Importante para decidir se cabe exclusão retroativa (mensalidade é recorrente;
# coparticipação é cobrança por uso já ocorrido — normalmente não é estornável).
def _composicao(row) -> str:
    partes = []
    if float(row.get("_vlr_mensalidade_fat", 0) or 0) > 0:
        partes.append("Mensalidade")
    if float(row.get("_vlr_dependente_fat", 0) or 0) > 0:
        partes.append("Dependentes")
    if float(row.get("_vlr_copart_fat", 0) or 0) > 0:
        partes.append("Coparticipação")
    return " + ".join(partes) if partes else "—"

if not df_exc_f.empty:
    df_exc_f = df_exc_f.copy()
    df_exc_f["Composição da Cobrança"] = df_exc_f.apply(_composicao, axis=1)

COLS = [
    "Funcionário", "Empresa", "Departamento", "Contrato Adm.",
    "Dt. Admissão", "Dt. Demissão",
    "_vlr_mensalidade_fat", "_vlr_dependente_fat", "_vlr_copart_fat",
    "Composição da Cobrança", "Valor Fatura", "Tem Direito",
]
cols_ok = [c for c in COLS if c in df_exc_f.columns]
df_tab  = df_exc_f[cols_ok].copy().reset_index(drop=True)
df_tab  = df_tab.rename(columns={
    "_vlr_mensalidade_fat": "Mensalidade",
    "_vlr_dependente_fat":  "Dependentes",
    "_vlr_copart_fat":      "Coparticipação",
})

df_tab_excel = df_tab.copy()  # valores numéricos, antes de formatar como R$ texto

def _brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"

_MOEDA_EXC = tuple(c for c in ["Mensalidade", "Dependentes", "Coparticipação", "Valor Fatura"]
                   if c in df_tab.columns)
for _col_moeda in _MOEDA_EXC:
    df_tab[_col_moeda] = pd.to_numeric(df_tab[_col_moeda], errors="coerce")

# Converter colunas de data (texto dd/mm/aaaa → data real) para a ordenação por
# cabeçalho funcionar cronologicamente — como texto, "31/07/2025" vinha antes de
# "02/07/2026" (ordena pelo dia). df_tab_excel acima fica com o texto original.
_DATE_COLS_EXC = tuple(c for c in ["Dt. Admissão", "Dt. Demissão"] if c in df_tab.columns)
for _dc in _DATE_COLS_EXC:
    _clean = (df_tab[_dc].astype(str).str.strip()
              .replace({"nan": "", "None": "", "NaT": "", "none": "", "NAT": ""}))
    df_tab[_dc] = pd.to_datetime(_clean, dayfirst=True, errors="coerce")

# Deixa explícito no cabeçalho que os valores são da fatura do mês anterior
df_tab = df_tab.rename(columns={c: f"{c} ({periodo_ant_sel})" for c in _MOEDA_EXC})
_MOEDA_EXC = tuple(f"{c} ({periodo_ant_sel})" for c in _MOEDA_EXC)

st.caption(
    f"Os valores abaixo são os da fatura de **{periodo_ant_sel}** — último mês em que "
    f"estas pessoas foram cobradas. Em **{periodo}** não há cobrança para elas. "
    "Clique no funil do cabeçalho para filtrar ou ordenar a coluna."
)
_resp_exc = grade(
    df_tab.reset_index(drop=True),
    key="grade_exclusoes",
    height=480,
    colunas_moeda=_MOEDA_EXC,
    colunas_data=_DATE_COLS_EXC,
    larguras={"Funcionário": 220},
)

excel_bytes_exc = exportar_excel_exclusoes(df_tab_excel, periodo)
st.download_button(
    "📥 Exportar Excel (Exclusões)",
    data=excel_bytes_exc,
    file_name=f"exclusoes_unimed_{periodo.replace('/', '_')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# ── Observação ────────────────────────────────────────────────────────────────
st.divider()
st.info("""
**Observação para fechamento**

Titulares listados acima estavam na fatura do mês anterior e não aparecem mais na fatura atual.
Possíveis causas: desligamento, exclusão solicitada, ou ausência na fatura por erro da operadora.

Verifique se a exclusão foi solicitada formalmente e se há crédito ou acerto financeiro a realizar.
""")

# ── Export — blocos para colar em outro sistema ───────────────────────────────
st.divider()
st.subheader("📋 Texto para copiar e colar (Descrição)")

_col_data_exc = "Dt. Demissão" if "Dt. Demissão" in df_exc_f.columns else None
texto_desc_exc = exportar_descricoes_unimed(df_exc_f, "EXCLUSÃO", _col_data_exc or "")
if texto_desc_exc:
    st.text_area(
        "Um bloco por funcionário — copie o trecho desejado ou baixe o arquivo completo abaixo",
        value=texto_desc_exc,
        height=240,
    )
    st.download_button(
        "📥 Baixar .txt (Exclusões)",
        data=texto_desc_exc.encode("utf-8"),
        file_name=f"exclusoes_unimed_{periodo.replace('/', '_')}_descricao.txt",
        mime="text/plain",
    )
else:
    st.caption("Nenhuma exclusão para gerar texto.")
