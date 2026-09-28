# -*- coding: utf-8 -*-
import calendar
import io
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.ui import ICONE, barra_lateral, tabela
from app.grade import grade
from st_aggrid import JsCode
from app import db
from app.exclusoes_indevidas import ler_desligados

st.set_page_config(page_title="Exclusões Indevidas — Unimed", page_icon=ICONE, layout="wide")
barra_lateral()
st.header("4 · Auditoria de Exclusões Indevidas")
st.caption(
    "Cruza a **planilha de desligados** com a **fatura** e a **compra** — "
    "identifica quem ainda está ativo indevidamente e calcula o prejuízo estimado."
)

# ── Helpers ───────────────────────────────────────────────────────────────────
def _norm(s) -> str:
    txt = str(s or "").strip().upper()
    nfkd = unicodedata.normalize("NFKD", txt)
    return " ".join("".join(c for c in nfkd if not unicodedata.combining(c)).split())

def _parse_date(val):
    if val is None:
        return None
    if isinstance(val, pd.Timestamp):
        return None if pd.isna(val) else val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()
    if not s or s.lower() in ("", "nan", "nat", "none"):
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return pd.to_datetime(s, format=fmt).date()
        except Exception:
            pass
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        return None if pd.isna(dt) else dt.date()
    except Exception:
        return None

def _ultimo_dia_mes(d: date) -> date:
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])

def _periodo_dates(periodo: str):
    try:
        p = str(periodo or "").strip().split("/")
        mes, ano = int(p[0]), int(p[1])
        if ano < 100:
            ano += 2000
        inicio = date(ano, mes, 1)
        return inicio, _ultimo_dia_mes(inicio)
    except Exception:
        return None, None

def _brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"

def _encontrar_col(df: pd.DataFrame, *keywords) -> str | None:
    for kw in keywords:
        kw_n = _norm(kw)
        for col in df.columns:
            if kw_n in _norm(col):
                return col
    return None

def _ler_planilha(conteudo: bytes, nome_arq: str) -> pd.DataFrame | None:
    melhor, melhor_score = None, -1
    def _score(df):
        return len([c for c in df.columns if not str(c).lower().startswith("unnamed")])
    if nome_arq.lower().endswith((".xlsx", ".xls")):
        for hr in range(10):
            try:
                df = pd.read_excel(io.BytesIO(conteudo), dtype=str, header=hr)
                df = df.dropna(how="all").dropna(how="all", axis=1)
                s = _score(df)
                if s > melhor_score:
                    melhor, melhor_score = df, s
            except Exception:
                continue
    else:
        for enc in ("latin-1", "cp1252", "utf-8-sig", "utf-8"):
            for sep in (";", ",", "\t", "|"):
                for hr in range(9):
                    try:
                        df = pd.read_csv(io.BytesIO(conteudo), sep=sep, dtype=str,
                                         encoding=enc, header=hr, skip_blank_lines=True,
                                         on_bad_lines="skip")
                        df = df.dropna(how="all").dropna(how="all", axis=1)
                        s = _score(df)
                        if s > melhor_score:
                            melhor, melhor_score = df, s
                    except Exception:
                        continue
    return melhor


# ── Auto-carregar auditoria ───────────────────────────────────────────────────
if "df_audit" not in st.session_state or st.session_state["df_audit"] is None:
    _ults = db.listar_periodos()
    if _ults:
        _ult = _ults[0]
        with st.spinner(f"Carregando auditoria {_ult['periodo']}…"):
            from app.regras import aplicar_regras, calcular_stats
            _df, _stats, _meta = db.carregar_auditoria(_ult["periodo"], _ult["cliente"])
        if _df is not None and not _df.empty:
            _df = aplicar_regras(_df)
            _aid = (_meta or {}).get("id") or _ult.get("id")
            _arqs = db.carregar_arquivos_auditoria(_aid) if _aid else {}
            st.session_state.update({
                "df_audit":     _df,
                "stats":        calcular_stats(_df),
                "periodo":      _ult["periodo"],
                "cliente":      _ult["cliente"],
                "auditoria_id": _aid,
                "arquivos_fontes": _arqs,
            })
            st.rerun()
        else:
            st.warning("Nenhuma auditoria carregada. Acesse **1 · Importação** primeiro.")
            st.stop()
    else:
        st.warning("Nenhuma auditoria carregada. Acesse **1 · Importação** primeiro.")
        st.stop()

df_audit = st.session_state["df_audit"]
periodo  = st.session_state.get("periodo", "")
st.info(f"**Auditoria carregada:** {periodo} · {len(df_audit)} registros")

st.divider()

# ── Carregar planilha de desligados ──────────────────────────────────────────
# Prioridade: 1) sessão (importada em 1 · Importação)  2) arquivos salvos no DB  3) upload manual
st.markdown("### 📋 Planilha de Desligados")

_df_desl_sessao = st.session_state.get("df_desligados")
_origem_desl    = None

if _df_desl_sessao is not None and not _df_desl_sessao.empty:
    _origem_desl = "importação"
else:
    # Tenta carregar do arquivo salvo na auditoria
    _aid_atual   = st.session_state.get("auditoria_id")
    _arqs_atual  = db.carregar_arquivos_auditoria(_aid_atual) if _aid_atual else {}
    _desl_salvos = _arqs_atual.get("desligados", [])
    if _desl_salvos:
        try:
            # Planilha de inativos tem mesma estrutura de contratos → usa ler_contratos
            from app.processamento import ler_contratos as _ler_cont
            _df_desl_sessao = _ler_cont(_desl_salvos[0]["caminho"])
            if not _df_desl_sessao.empty:
                st.session_state["df_desligados"] = _df_desl_sessao
                _origem_desl = "banco"
        except Exception:
            _df_desl_sessao = None

if _origem_desl == "importação":
    n_desl = len(_df_desl_sessao)
    st.success(
        f"✅ **{n_desl}** desligado(s) carregado(s) automaticamente "
        "da **1 · Importação** — nenhum upload necessário aqui."
    )
elif _origem_desl == "banco":
    n_desl = len(_df_desl_sessao)
    st.success(
        f"✅ **{n_desl}** desligado(s) recuperado(s) do arquivo salvo nesta auditoria."
    )
else:
    st.info(
        "💡 **Dica:** Para não precisar fazer upload aqui, importe a planilha de desligados "
        "diretamente em **1 · Importação** — o sistema usará automaticamente em todas as abas."
    )

st.caption("Faça upload abaixo para usar uma planilha diferente ou se nenhuma foi importada.")

arq_desl = st.file_uploader(
    "Planilha de desligados (opcional — substitui o importado em 1 · Importação)",
    type=["xlsx", "xls", "csv"],
    key="up_desligados",
    label_visibility="collapsed",
)

# Upload manual sobrescreve a da sessão
if arq_desl:
    arq_desl.seek(0)
    conteudo = arq_desl.read()
    st.session_state["_desl_bytes"]   = conteudo
    st.session_state["_desl_nome"]    = arq_desl.name
    st.session_state["_desl_col_map"] = {}

desl_bytes = st.session_state.get("_desl_bytes")
desl_nome  = st.session_state.get("_desl_nome", "")

# Decide qual fonte usar: upload manual > sessão/DB
if desl_bytes:
    raw_desl = _ler_planilha(desl_bytes, desl_nome)
    _usando_upload_manual = True
elif _df_desl_sessao is not None and not _df_desl_sessao.empty:
    raw_desl = None
    _usando_upload_manual = False
else:
    st.warning("⬆️ Nenhuma planilha de desligados disponível. Carregue um arquivo ou importe em **1 · Importação**.")
    st.stop()

if _usando_upload_manual:
    if raw_desl is None or raw_desl.empty:
        st.error("Não foi possível ler a planilha. Verifique o arquivo.")
        st.stop()

    cols_arquivo = list(raw_desl.columns)

    col_nome_auto = _encontrar_col(raw_desl,
        "nome do funcionario", "nome da funcionaria", "nome funcionario",
        "nome do colaborador", "nome colaborador", "nome do empregado", "nome empregado",
        "nome do beneficiario", "nome beneficiario", "nome do titular",
        "nome segurado", "funcionario", "funcionária",
        "colaborador", "empregado", "beneficiario", "titular", "segurado", "nome",
    )
    if not col_nome_auto:
        for c in cols_arquivo:
            if str(c).lower().startswith("unnamed"):
                continue
            amostra = raw_desl[c].dropna().astype(str).head(15)
            if amostra.empty:
                continue
            if amostra.str.len().mean() >= 5 and amostra.apply(
                lambda v: sum(ch.isalpha() or ch == " " for ch in v) / max(len(v), 1)
            ).mean() >= 0.6:
                col_nome_auto = c
                break

    col_dem_auto = _encontrar_col(raw_desl,
        "dt. demissao", "data demissao", "data de demissao", "dt demissao",
        "dt. desligamento", "data desligamento", "data de desligamento",
        "dt. rescisao", "data rescisao", "data de rescisao", "dt. rescisão",
        "data saida", "dt saida", "dt. saida", "data de saida",
        "demissao", "desligamento", "rescisao", "saida", "rescisão",
    )
    col_cpf_auto = _encontrar_col(raw_desl, "cpf", "c.p.f", "cpf/cnpj", "documento")
    col_mat_auto = _encontrar_col(raw_desl, "matricula", "matrícula", "chapa", "cod func",
                                   "cód. func", "codigo", "número")

    with st.expander("🔍 Colunas detectadas — verifique ou corrija", expanded=not col_dem_auto):
        opcoes = ["(não usar)"] + cols_arquivo
        mc1, mc2, mc3, mc4 = st.columns(4)

        def _sel(label, col_auto, key, col_widget):
            idx = opcoes.index(col_auto) if col_auto and col_auto in opcoes else 0
            escolha = col_widget.selectbox(label, opcoes, index=idx, key=key)
            return escolha if escolha != "(não usar)" else None

        col_nome = _sel("Nome do Funcionário *", col_nome_auto, "sel_nome", mc1)
        col_dem  = _sel("Data de Demissão *",    col_dem_auto,  "sel_dem",  mc2)
        col_cpf  = _sel("CPF (opcional)",         col_cpf_auto,  "sel_cpf",  mc3)
        col_mat  = _sel("Matrícula (opcional)",   col_mat_auto,  "sel_mat",  mc4)

        if col_nome:
            st.caption(f"✅ Nome: `{col_nome}`")
        else:
            st.error("Selecione a coluna com o nome do funcionário.")
        if col_dem:
            st.caption(f"✅ Data demissão: `{col_dem}`")
        else:
            st.warning("⚠️ Coluna de data de demissão não selecionada — cálculos de prazo serão ignorados.")

    if not col_nome:
        st.stop()

    BLOQUEADOS = {"NOME", "FUNCIONARIO", "FUNCIONARIA", "COLABORADOR", "EMPREGADO",
                  "TITULAR", "BENEFICIARIO", "SEGURADO", "NOME FUNCIONARIO"}

    desl_rows = []
    for _, row in raw_desl.iterrows():
        nome_raw = str(row.get(col_nome) or "").strip()
        if not nome_raw or _norm(nome_raw) in BLOQUEADOS:
            continue
        desl_rows.append({
            "_norm": _norm(nome_raw),
            "nome":  nome_raw,
            "dt_dem": _parse_date(row.get(col_dem)) if col_dem else None,
            "cpf":   str(row.get(col_cpf) or "").strip() if col_cpf else "",
            "mat":   str(row.get(col_mat) or "").strip() if col_mat else "",
        })

    if not desl_rows:
        st.warning("Nenhum registro válido encontrado na planilha de desligados.")
        st.stop()
    st.success(f"✅ **{len(desl_rows)}** desligado(s) carregado(s) da planilha.")

else:
    # Usa dados da sessão.
    # Detecta formato: df_cont (ler_contratos) tem '_norm_func'; formato legado tem '_norm_nome'.
    desl_rows = []
    _eh_formato_cont = "_norm_func" in _df_desl_sessao.columns

    for _, drow in _df_desl_sessao.iterrows():
        if _eh_formato_cont:
            nome_raw = str(drow.get("funcionario", "") or "").strip()
            nn       = str(drow.get("_norm_func", "") or "")
            dem_str  = str(drow.get("demissao", "") or "").strip()
            dt_d     = _parse_date(dem_str) if dem_str else None
            mat      = str(drow.get("cod_func", "") or "")
            cpf      = str(drow.get("cpf", "") or "")
        else:
            nome_raw = str(drow.get("nome", "") or "").strip()
            nn       = str(drow.get("_norm_nome", "") or _norm(nome_raw))
            dt_raw   = drow.get("dt_demissao")
            dt_d     = dt_raw if isinstance(dt_raw, date) else _parse_date(dt_raw)
            mat      = str(drow.get("matricula", "") or "")
            cpf      = str(drow.get("cpf", "") or "")

        if not nome_raw:
            continue
        desl_rows.append({
            "_norm": nn,
            "nome":  nome_raw,
            "dt_dem": dt_d,
            "cpf":   cpf,
            "mat":   mat,
        })
    st.success(f"✅ **{len(desl_rows)}** desligado(s) disponíveis.")

# ── Mesclar dados dos inativos na auditoria da sessão ────────────────────────
# Atualiza df_audit em memória (Dt. Demissão + campos ausentes) para que todas
# as abas reflitam os dados dos inativos sem reprocessamento completo.
# Fonte da mesclagem = a mesma que gerou `desl_rows`: o upload manual quando há
# um, senão o df da sessão/banco (que já vem no formato de ler_contratos).
_usar_df_sessao = (
    not _usando_upload_manual
    and _df_desl_sessao is not None
    and not _df_desl_sessao.empty
    and "_norm_func" in _df_desl_sessao.columns
)

if desl_rows:
    from app.processamento import mesclar_desligados

    if _usar_df_sessao:
        _df_para_merge_cont = _df_desl_sessao
    else:
        # Upload manual / formato legado → converte para o formato de contratos
        _df_para_merge_cont = pd.DataFrame([{
            "cod_func":    d.get("mat", ""),
            "_norm_func":  d["_norm"],
            "funcionario": d["nome"],
            "demissao":    d["dt_dem"].strftime("%d/%m/%Y") if d.get("dt_dem") else "",
            "empresa": "", "departamento": "", "contrato_adm": "", "admissao": "",
        } for d in desl_rows])

    _df_merged, _ = mesclar_desligados(
        st.session_state["df_audit"], _df_para_merge_cont, periodo
    )
    _dt_antes  = st.session_state["df_audit"]["Dt. Demissão"].fillna("").tolist()
    _dt_depois = _df_merged["Dt. Demissão"].fillna("").tolist()
    if _dt_antes != _dt_depois:
        from app.regras import aplicar_regras
        _df_merged = aplicar_regras(_df_merged)
        st.session_state["df_audit"] = _df_merged
        df_audit = _df_merged

st.divider()

# ── Configurações ─────────────────────────────────────────────────────────────
with st.expander("⚙️ Configurações", expanded=False):
    cc1, cc2 = st.columns(2)
    prazo_dias = cc1.number_input(
        "Prazo para exclusão após demissão (dias)",
        min_value=1, max_value=90, value=10, step=1,
    )
    cobertura_mes = cc2.radio(
        "Cobertura após demissão",
        options=["Até o último dia do mês da demissão", "Somente até a data da demissão"],
        index=0,
    ) == "Até o último dia do mês da demissão"

st.divider()

# ── Cruzar com fatura / compra ────────────────────────────────────────────────
inicio_comp, fim_comp = _periodo_dates(periodo)
# Auditar um mês ainda em curso não pode fabricar atraso: se a competência
# termina no futuro, a referência é hoje. Sem isso, quem foi demitido no mês
# corrente já nascia "fora do prazo" contra uma data que nem chegou.
data_ref = min(fim_comp, date.today()) if fim_comp else date.today()

def _tipo_cobranca(vlr_mens: float, vlr_dep: float, vlr_copart: float) -> str:
    partes = []
    if vlr_mens > 0:
        partes.append("Mensalidade/Contribuição Saúde")
    if vlr_dep > 0:
        partes.append("Dependente")
    if vlr_copart > 0:
        partes.append("Conta médica")
    return " + ".join(partes) if partes else "—"

fat_lookup = {}
# fat_lookup com chave dupla: (cod_func, _norm) quando há matrícula; _norm para sem_contrato
fat_lookup_mat  = {}  # (cod_func, _norm) → entry
fat_lookup_nome = {}  # _norm → entry (sem_contrato / sem matrícula)

for _, row in df_audit.iterrows():
    n   = _norm(str(row.get("Funcionário", "") or ""))
    cod = str(row.get("Cod. Funcionário", "") or "").strip()
    if not n:
        continue
    entry = {
        "na_fatura":    bool(row.get("_na_fatura", False)),
        "na_compra":    bool(row.get("_na_compra", False)),
        "vlr_fatura":   float(row.get("Valor Fatura", 0) or 0),
        "vlr_mens":     float(row.get("_vlr_mensalidade_fat", 0) or 0),
        "vlr_dep":      float(row.get("_vlr_dependente_fat", 0) or 0),
        "vlr_copart":   float(row.get("_vlr_copart_fat", 0) or 0),
        "empresa":      str(row.get("Empresa", "") or ""),
        "dept":         str(row.get("Departamento", "") or ""),
        "contrato_adm": str(row.get("Contrato Adm.", "") or ""),
        "adm_str":      str(row.get("Dt. Admissão", "") or ""),
    }
    if cod:
        fat_lookup_mat[(cod, n)] = entry
    else:
        fat_lookup_nome[n] = entry

registros = []
for d in desl_rows:
    desl_mat = str(d.get("mat", "") or "").strip()
    desl_nn  = d["_norm"]

    # Regra: matrícula+nome idênticos (estrito) quando matrícula disponível nos dois lados
    fat = None
    if desl_mat:
        fat = fat_lookup_mat.get((desl_mat, desl_nn))
    if fat is None:
        fat = fat_lookup_nome.get(desl_nn)

    if not fat:
        continue
    if not fat["na_fatura"] and not fat["na_compra"]:
        continue

    # Validar: demissão deve ser posterior à admissão do contrato atual
    # (mesma regra de mesclar_desligados — evita falsos positivos de recontratos)
    dt_dem = d["dt_dem"]
    if dt_dem and fat.get("adm_str"):
        try:
            dt_adm_val = _parse_date(fat["adm_str"])
            if dt_adm_val and dt_dem < dt_adm_val:
                continue  # contrato anterior — ignorar
        except Exception:
            pass

    # dt_dem já definido na validação acima
    vlr_fatura   = fat["vlr_fatura"]
    ultimo_coberto = (_ultimo_dia_mes(dt_dem) if cobertura_mes else dt_dem) if dt_dem else None
    prazo_limite   = (dt_dem + timedelta(days=prazo_dias)) if dt_dem else None
    dias_atraso    = max(0, (data_ref - prazo_limite).days) if prazo_limite else 0

    dias_indev = 0
    if ultimo_coberto and inicio_comp and fim_comp:
        inicio_indev = ultimo_coberto + timedelta(days=1)
        if inicio_indev <= fim_comp:
            dias_indev = max(0, (fim_comp - max(inicio_indev, inicio_comp)).days + 1)

    # Sem data de demissão não dá para ratear — assume a fatura cheia (é o que o
    # aviso de "sem data" explica). Com data e zero dia indevido no período, a
    # cobrança do mês é legítima: prejuízo 0 (antes somava a fatura cheia e
    # inflava o KPI de prejuízo estimado).
    if dias_indev:
        vlr_prej = round(vlr_fatura * dias_indev / 30, 2)
    elif dt_dem is None:
        vlr_prej = vlr_fatura
    else:
        vlr_prej = 0.0

    # Status: se apenas Conta médica está sendo cobrada → "Excluído - com cobrança"
    _so_copart = fat["vlr_copart"] > 0 and fat["vlr_mens"] == 0 and fat["vlr_dep"] == 0
    if _so_copart:
        status = "🔶 EXCLUÍDO — COM COBRANÇA MÉDICA"
    elif dias_atraso > 0:
        status = "⚠️ EXCLUSÃO FORA DO PRAZO"
    else:
        status = "🚨 COBRANÇA INDEVIDA"

    def _ts(d):
        return pd.Timestamp(d) if d else pd.NaT

    registros.append({
        "Funcionário":             d["nome"],
        "Empresa":                 fat["empresa"],
        "Departamento":            fat["dept"],
        "Contrato Adm.":           fat["contrato_adm"],
        "Status":                  status,
        "O que está sendo cobrado": _tipo_cobranca(fat["vlr_mens"], fat["vlr_dep"], fat["vlr_copart"]),
        "Dt. Demissão":            _ts(dt_dem),
        "Último Dia de Cobertura": _ts(ultimo_coberto),
        "Prazo Limite Exclusão":   _ts(prazo_limite),
        "Dias em Atraso":          dias_atraso,
        "Ativo na Fatura":         "Sim" if fat["na_fatura"] else "Não",
        "Ativo na Compra":         "Sim" if fat["na_compra"] else "Não",
        "Competência":             periodo,
        "Dias Cobrança Indevida":  dias_indev,
        "Valor Fatura Mensal":     vlr_fatura,
        "Valor Estimado Prejuízo": vlr_prej,
    })

if not registros:
    st.success(
        f"✅ Nenhum funcionário da planilha de desligados consta na "
        f"fatura ou compra do período **{periodo}**."
    )
    st.stop()

# Ordem de gravidade explícita (não depende do emoji do Status):
# 1º Cobrança Indevida  →  2º Fora do Prazo  →  3º Excluído c/ cobrança médica
_PRIORIDADE_STATUS = {
    "🚨 COBRANÇA INDEVIDA":            1,
    "⚠️ EXCLUSÃO FORA DO PRAZO":       2,
    "🔶 EXCLUÍDO — COM COBRANÇA MÉDICA": 3,
}
df_res = pd.DataFrame(registros)
df_res["_ord"] = df_res["Status"].map(_PRIORIDADE_STATUS).fillna(9).astype(int)
df_res = (df_res
          .sort_values(["_ord", "Valor Estimado Prejuízo"], ascending=[True, False])
          .drop(columns=["_ord"])
          .reset_index(drop=True))

# ── KPIs ──────────────────────────────────────────────────────────────────────
st.subheader(f"Resultado — {periodo}")

total_prej = df_res["Valor Estimado Prejuízo"].sum()
fora_prazo = (df_res["Status"].str.contains("FORA DO PRAZO")).sum()
na_fat     = (df_res["Ativo na Fatura"] == "Sim").sum()
na_comp    = (df_res["Ativo na Compra"] == "Sim").sum()
med_atraso = df_res.loc[df_res["Dias em Atraso"] > 0, "Dias em Atraso"].mean()
sem_data   = df_res["Dt. Demissão"].isna().sum()

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("🚨 Vidas Indevidas",   len(df_res))
k2.metric("💸 Prejuízo Estimado", _brl(total_prej))
k3.metric("⚠️ Fora do Prazo",     fora_prazo)
k4.metric("📄 Ativos na Fatura",  na_fat)
k5.metric("💳 Ativos na Compra",  na_comp)
k6.metric("⏱️ Atraso Médio",
          f"{med_atraso:.0f} dias" if not pd.isna(med_atraso) else "—")

if sem_data > 0:
    st.warning(
        f"⚠️ **{sem_data}** funcionário(s) sem data de demissão na planilha — "
        "os cálculos de dias e prazo foram feitos usando o valor total da fatura como prejuízo."
    )

st.divider()

# ── Gráficos ──────────────────────────────────────────────────────────────────
g1, g2 = st.columns(2)

with g1:
    st.markdown("**Ranking — Contratos com mais casos**")
    if df_res["Contrato Adm."].str.strip().ne("").any():
        rk = (df_res[df_res["Contrato Adm."].str.strip().ne("")]
              .groupby("Contrato Adm.")
              .agg(Casos=("Funcionário", "count"),
                   Prejuízo=("Valor Estimado Prejuízo", "sum"))
              .reset_index().sort_values("Casos", ascending=False).head(10))
        rk["Prejuízo"] = rk["Prejuízo"].apply(_brl)
        tabela(rk, use_container_width=True, hide_index=True)
    else:
        st.caption("Sem dados de contrato.")

with g2:
    st.markdown("**Ranking — Departamentos com mais casos**")
    if df_res["Departamento"].str.strip().ne("").any():
        rk2 = (df_res[df_res["Departamento"].str.strip().ne("")]
               .groupby("Departamento")
               .agg(Casos=("Funcionário", "count"),
                    Prejuízo=("Valor Estimado Prejuízo", "sum"))
               .reset_index().sort_values("Casos", ascending=False).head(10))
        rk2["Prejuízo"] = rk2["Prejuízo"].apply(_brl)
        tabela(rk2, use_container_width=True, hide_index=True)
    else:
        st.caption("Sem dados de departamento.")

st.divider()

# ── Tabela ────────────────────────────────────────────────────────────────────
# Filtros ficam no funil do cabeçalho de cada coluna e rodam no navegador.
df_tab = df_res.copy().reset_index(drop=True)

MOEDA = tuple(c for c in ["Valor Fatura Mensal", "Valor Estimado Prejuízo"] if c in df_tab.columns)
for col in MOEDA:
    df_tab[col] = pd.to_numeric(df_tab[col], errors="coerce")

DATAS = tuple(c for c in ["Dt. Demissão", "Último Dia de Cobertura", "Prazo Limite Exclusão"]
              if c in df_tab.columns)

_COR_STATUS = JsCode("""
function (p) {
    if (!p.data) { return null; }
    if (p.data['Status'] && p.data['Status'].indexOf('INDEVIDA') >= 0) { return { background: '#FBEDED' }; }
    if (p.data['Status'] && p.data['Status'].indexOf('FORA DO PRAZO') >= 0) { return { background: '#FDF3E7' }; }
    return null;
}
""")

st.caption("Clique no funil do cabeçalho para filtrar ou ordenar a coluna · duplo clique numa célula copia o conteúdo.")

_resp = grade(
    df_tab,
    key="grade_exclusoes_indevidas",
    height=500,
    colunas_moeda=MOEDA,
    colunas_data=DATAS,
    larguras={"Funcionário": 220},
    cor_linha=_COR_STATUS,
)
df_f = pd.DataFrame(_resp["data"]) if _resp is not None else df_tab
st.caption(f"**{len(df_f)}** caso(s) exibido(s) de {len(df_tab)}.")

# ── Exportação ────────────────────────────────────────────────────────────────
st.divider()

def _excel() -> bytes:
    out = io.BytesIO()
    _COLS_DATA = ["Dt. Demissão", "Último Dia de Cobertura", "Prazo Limite Exclusão"]
    df_exp = df_res.copy()
    for c in _COLS_DATA:
        if c in df_exp.columns:
            df_exp[c] = df_exp[c].apply(
                lambda v: v.strftime("%d/%m/%Y") if pd.notna(v) else ""
            )
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df_exp.to_excel(writer, sheet_name="Exclusões Indevidas", index=False)
        (df_res.groupby("Status")
         .agg(Casos=("Funcionário", "count"),
              Valor_Total=("Valor Estimado Prejuízo", "sum"))
         .reset_index()
         .rename(columns={"Valor_Total": "Valor Estimado Total"})
         .to_excel(writer, sheet_name="Resumo", index=False))
        if df_res["Contrato Adm."].str.strip().ne("").any():
            (df_res.groupby("Contrato Adm.")
             .agg(Casos=("Funcionário", "count"),
                  Prejuizo=("Valor Estimado Prejuízo", "sum"))
             .reset_index().sort_values("Casos", ascending=False)
             .to_excel(writer, sheet_name="Ranking Contratos", index=False))
    return out.getvalue()

st.download_button(
    "📥 Exportar Excel",
    data=_excel(),
    file_name=f"exclusoes_indevidas_{periodo.replace('/', '_')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="secondary",
)
