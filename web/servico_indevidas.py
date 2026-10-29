# -*- coding: utf-8 -*-
"""4 · Exclusões indevidas, sem tela: cruza a planilha de desligados com a fatura e a compra e
calcula o prejuízo estimado. Cálculo trazido sem mudança de pages/4_Auditoria_Exclusões_Indevidas.py."""
from __future__ import annotations

import calendar
import io
import unicodedata
from datetime import date, timedelta

import pandas as pd

from app import db

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



BLOQUEADOS = {"NOME", "FUNCIONARIO", "FUNCIONARIA", "COLABORADOR", "EMPREGADO",
              "TITULAR", "BENEFICIARIO", "SEGURADO", "NOME FUNCIONARIO"}
PRIORIDADE = {"🚨 COBRANÇA INDEVIDA": 1, "⚠️ EXCLUSÃO FORA DO PRAZO": 2, "🔶 EXCLUÍDO — COM COBRANÇA MÉDICA": 3}
MOEDA = ("Valor Fatura Mensal", "Valor Estimado Prejuízo")
DATAS = ("Dt. Demissão", "Último Dia de Cobertura", "Prazo Limite Exclusão")


def desligados_do_banco(meta) -> pd.DataFrame | None:
    """A planilha de inativos guardada na auditoria (mesma estrutura dos contratos)."""
    from app.processamento import ler_contratos
    salvos = db.carregar_arquivos_auditoria(meta["id"]).get("desligados", []) if meta else []
    if not salvos:
        return None
    try:
        df = ler_contratos(salvos[0]["caminho"])
        return df if not df.empty else None
    except Exception:      # noqa: BLE001
        return None


def colunas_automaticas(raw: pd.DataFrame) -> dict:
    col_nome = _encontrar_col(
        raw, "nome do funcionario", "nome da funcionaria", "nome funcionario",
        "nome do colaborador", "nome colaborador", "nome do empregado", "nome empregado",
        "nome do beneficiario", "nome beneficiario", "nome do titular",
        "nome segurado", "funcionario", "funcionária",
        "colaborador", "empregado", "beneficiario", "titular", "segurado", "nome")
    if not col_nome:
        for c in raw.columns:
            if str(c).lower().startswith("unnamed"):
                continue
            amostra = raw[c].dropna().astype(str).head(15)
            if amostra.empty:
                continue
            if amostra.str.len().mean() >= 5 and amostra.apply(
                    lambda v: sum(ch.isalpha() or ch == " " for ch in v) / max(len(v), 1)).mean() >= 0.6:
                col_nome = c
                break
    return {
        "nome": col_nome,
        "dem": _encontrar_col(
            raw, "dt. demissao", "data demissao", "data de demissao", "dt demissao",
            "dt. desligamento", "data desligamento", "data de desligamento",
            "dt. rescisao", "data rescisao", "data de rescisao", "dt. rescisão",
            "data saida", "dt saida", "dt. saida", "data de saida",
            "demissao", "desligamento", "rescisao", "saida", "rescisão"),
        "cpf": _encontrar_col(raw, "cpf", "c.p.f", "cpf/cnpj", "documento"),
        "mat": _encontrar_col(raw, "matricula", "matrícula", "chapa", "cod func", "cód. func", "codigo", "número"),
    }


def linhas_do_upload(raw: pd.DataFrame, cols: dict) -> list:
    linhas = []
    for _, row in raw.iterrows():
        nome_raw = str(row.get(cols["nome"]) or "").strip()
        if not nome_raw or _norm(nome_raw) in BLOQUEADOS:
            continue
        linhas.append({"_norm": _norm(nome_raw), "nome": nome_raw,
                       "dt_dem": _parse_date(row.get(cols["dem"])) if cols.get("dem") else None,
                       "cpf": str(row.get(cols["cpf"]) or "").strip() if cols.get("cpf") else "",
                       "mat": str(row.get(cols["mat"]) or "").strip() if cols.get("mat") else ""})
    return linhas


def linhas_do_banco(df: pd.DataFrame) -> list:
    """Formato de ler_contratos ('_norm_func') ou o legado ('_norm_nome')."""
    linhas, formato_cont = [], "_norm_func" in df.columns
    for _, d in df.iterrows():
        if formato_cont:
            nome_raw = str(d.get("funcionario", "") or "").strip()
            nn = str(d.get("_norm_func", "") or "")
            dem = str(d.get("demissao", "") or "").strip()
            dt_d = _parse_date(dem) if dem else None
            mat, cpf = str(d.get("cod_func", "") or ""), str(d.get("cpf", "") or "")
        else:
            nome_raw = str(d.get("nome", "") or "").strip()
            nn = str(d.get("_norm_nome", "") or _norm(nome_raw))
            bruto = d.get("dt_demissao")
            dt_d = bruto if isinstance(bruto, date) else _parse_date(bruto)
            mat, cpf = str(d.get("matricula", "") or ""), str(d.get("cpf", "") or "")
        if nome_raw:
            linhas.append({"_norm": nn, "nome": nome_raw, "dt_dem": dt_d, "cpf": cpf, "mat": mat})
    return linhas


def mesclar_no_audit(df_audit: pd.DataFrame, linhas: list, df_banco, periodo: str) -> pd.DataFrame:
    """Dt. Demissão e campos ausentes vindos dos desligados, sem reprocessar tudo."""
    from app.processamento import mesclar_desligados
    from app.regras import aplicar_regras
    if not linhas:
        return df_audit
    if df_banco is not None and "_norm_func" in df_banco.columns:
        base = df_banco
    else:
        base = pd.DataFrame([{"cod_func": d.get("mat", ""), "_norm_func": d["_norm"], "funcionario": d["nome"],
                              "demissao": d["dt_dem"].strftime("%d/%m/%Y") if d.get("dt_dem") else "",
                              "empresa": "", "departamento": "", "contrato_adm": "", "admissao": ""} for d in linhas])
    merged, _ = mesclar_desligados(df_audit, base, periodo)
    if df_audit["Dt. Demissão"].fillna("").tolist() != merged["Dt. Demissão"].fillna("").tolist():
        merged = aplicar_regras(merged)
    return merged


def _tipo_cobranca(vlr_mens: float, vlr_dep: float, vlr_copart: float) -> str:
    partes = []
    if vlr_mens > 0:
        partes.append("Mensalidade/Contribuição Saúde")
    if vlr_dep > 0:
        partes.append("Dependente")
    if vlr_copart > 0:
        partes.append("Conta médica")
    return " + ".join(partes) if partes else "—"



def analisar(df_audit: pd.DataFrame, periodo: str, desl_rows: list, prazo_dias: int = 10,
             cobertura_mes: bool = True) -> pd.DataFrame:
    inicio_comp, fim_comp = _periodo_dates(periodo)
    # Auditar um mês ainda em curso não pode fabricar atraso: se a competência
    # termina no futuro, a referência é hoje. Sem isso, quem foi demitido no mês
    # corrente já nascia "fora do prazo" contra uma data que nem chegou.
    data_ref = min(fim_comp, date.today()) if fim_comp else date.today()

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
        return pd.DataFrame()
    df_res = pd.DataFrame(registros)
    df_res["_ord"] = df_res["Status"].map(PRIORIDADE).fillna(9).astype(int)
    return (df_res.sort_values(["_ord", "Valor Estimado Prejuízo"], ascending=[True, False])
            .drop(columns=["_ord"]).reset_index(drop=True))


def kpis(df_res: pd.DataFrame) -> dict:
    med = df_res.loc[df_res["Dias em Atraso"] > 0, "Dias em Atraso"].mean()
    return {"vidas": len(df_res), "prejuizo": float(df_res["Valor Estimado Prejuízo"].sum()),
            "fora_prazo": int(df_res["Status"].str.contains("FORA DO PRAZO").sum()),
            "na_fat": int((df_res["Ativo na Fatura"] == "Sim").sum()),
            "na_comp": int((df_res["Ativo na Compra"] == "Sim").sum()),
            "atraso": None if pd.isna(med) else float(med), "sem_data": int(df_res["Dt. Demissão"].isna().sum())}


def ranking(df_res: pd.DataFrame, coluna: str) -> pd.DataFrame:
    if not df_res[coluna].astype(str).str.strip().ne("").any():
        return pd.DataFrame()
    return (df_res[df_res[coluna].astype(str).str.strip().ne("")].groupby(coluna)
            .agg(Casos=("Funcionário", "count"), Prejuízo=("Valor Estimado Prejuízo", "sum"))
            .reset_index().sort_values("Casos", ascending=False).head(10))


def excel(df_res: pd.DataFrame) -> bytes:
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
