# -*- coding: utf-8 -*-
"""
Auditoria de exclusões indevidas — identifica beneficiários que permanecem
ativos ou faturados no plano de saúde sem direito.
"""
import calendar
import io
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

# ── Status ──────────────────────────────────────────────────────────────────
S_COBRANCA_INDEVIDA   = "COBRANÇA INDEVIDA"
S_EXCLUSAO_PENDENTE   = "EXCLUSÃO PENDENTE"
S_FORA_DO_PRAZO       = "EXCLUSÃO FORA DO PRAZO"
S_DUPLICIDADE         = "DUPLICIDADE DE MATRÍCULA"
S_DEPENDENTE_INDEVIDO = "DEPENDENTE ATIVO INDEVIDAMENTE"

CORES_STATUS = {
    S_COBRANCA_INDEVIDA:   "#f8d7da",
    S_FORA_DO_PRAZO:       "#ffd6a5",
    S_EXCLUSAO_PENDENTE:   "#fff3cd",
    S_DUPLICIDADE:         "#e1bee7",
    S_DEPENDENTE_INDEVIDO: "#b3e5fc",
}

ICONES_STATUS = {
    S_COBRANCA_INDEVIDA:   "🚨",
    S_FORA_DO_PRAZO:       "⚠️",
    S_EXCLUSAO_PENDENTE:   "🔶",
    S_DUPLICIDADE:         "🔁",
    S_DEPENDENTE_INDEVIDO: "👨‍👩‍👧",
}

_STATUS_PRIORIDADE = {
    S_COBRANCA_INDEVIDA:   1,
    S_FORA_DO_PRAZO:       2,
    S_EXCLUSAO_PENDENTE:   3,
    S_DUPLICIDADE:         4,
    S_DEPENDENTE_INDEVIDO: 5,
}


# ── Utilitários internos ─────────────────────────────────────────────────────

def _norm(s) -> str:
    txt = str(s or "").strip().upper()
    nfkd = unicodedata.normalize("NFKD", txt)
    return " ".join("".join(c for c in nfkd if not unicodedata.combining(c)).split())


def _parse_date(val) -> Optional[date]:
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


def _periodo_to_dates(periodo: str):
    try:
        partes = str(periodo or "").strip().split("/")
        mes, ano = int(partes[0]), int(partes[1])
        if ano < 100:
            ano += 2000
        inicio = date(ano, mes, 1)
        return inicio, _ultimo_dia_mes(inicio)
    except Exception:
        return None, None


def _encontrar_col(df: pd.DataFrame, *keywords) -> Optional[str]:
    for kw in keywords:
        kw_n = _norm(kw)
        for col in df.columns:
            if kw_n in _norm(col):
                return col
    return None


def _fmt(d: Optional[date]) -> str:
    return d.strftime("%d/%m/%Y") if d else ""


def _brl(v) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"


def _dias_indevidos(ultimo_coberto: Optional[date],
                    inicio_comp: Optional[date],
                    fim_comp: Optional[date]) -> int:
    if not ultimo_coberto or not inicio_comp or not fim_comp:
        return 0
    inicio_indevido = ultimo_coberto + timedelta(days=1)
    if inicio_indevido > fim_comp:
        return 0
    return max(0, (fim_comp - max(inicio_indevido, inicio_comp)).days + 1)


# ── Leitura da planilha de desligados ────────────────────────────────────────

def ler_desligados(dados) -> pd.DataFrame:
    """
    Lê planilha de desligados a partir de path (str/Path) ou UploadedFile.
    Retorna (DataFrame, colunas_detectadas).
    """
    if isinstance(dados, (str, Path)):
        p = Path(dados)
        nome_arq = p.name.lower()
        conteudo = p.read_bytes()
    else:
        nome_arq = getattr(dados, "name", "").lower()
        dados.seek(0)
        conteudo = dados.read()

    raw = _melhor_df(conteudo, nome_arq)

    if raw is None or raw.empty:
        raise ValueError("Não foi possível ler a planilha de desligados.")

    cols_disponiveis = list(raw.columns)

    col_nome = _encontrar_col(raw,
        # variações explícitas frequentes
        "nome do funcionario", "nome da funcionaria", "nome funcionario",
        "nome do colaborador", "nome colaborador", "nome do empregado", "nome empregado",
        "nome do beneficiario", "nome beneficiario", "nome do titular", "nome titular",
        "nome do segurado", "nome segurado",
        # termos genéricos de nome
        "funcionario", "funcionária", "colaborador", "empregado",
        "beneficiario", "titular", "segurado", "associado",
        # último recurso: qualquer coluna com "nome"
        "nome",
    )

    # fallback: primeira coluna com maioria de valores alfabéticos longos
    if not col_nome:
        for c in cols_disponiveis:
            if str(c).lower().startswith("unnamed"):
                continue
            amostra = raw[c].dropna().astype(str).head(10)
            if amostra.empty:
                continue
            media_len = amostra.str.len().mean()
            pct_alpha = amostra.apply(lambda v: sum(ch.isalpha() or ch == " " for ch in v) / max(len(v), 1)).mean()
            if media_len >= 5 and pct_alpha >= 0.6:
                col_nome = c
                break

    if not col_nome:
        cols_str = " · ".join(f'"{c}"' for c in cols_disponiveis[:20])
        raise ValueError(
            f"Coluna de nome não encontrada na planilha de desligados.\n\n"
            f"Colunas detectadas no arquivo: {cols_str}\n\n"
            "Renomeie a coluna com os nomes para 'Nome Funcionário' ou 'Funcionário'."
        )

    col_dem = _encontrar_col(raw,
        "dt. demissao", "data demissao", "data de demissao", "dt demissao",
        "dt. desligamento", "data desligamento", "data de desligamento",
        "dt. rescisao", "data rescisao", "data de rescisao",
        "data saida", "dt saida", "dt. saida",
        "demissao", "desligamento", "rescisao", "saida",
    )
    col_cpf = _encontrar_col(raw, "cpf", "c.p.f", "cpf/cnpj", "documento", "doc.")
    col_mat = _encontrar_col(raw, "matricula", "matrícula", "chapa", "cod func", "cód. func",
                              "codigo", "código", "num func", "numero")

    colunas_detectadas = {
        "Nome":         col_nome,
        "Data Demissão": col_dem,
        "CPF":          col_cpf,
        "Matrícula":    col_mat,
    }

    nomes_bloqueados = {
        "NOME", "FUNCIONARIO", "FUNCIONARIA", "COLABORADOR", "EMPREGADO",
        "TITULAR", "BENEFICIARIO", "SEGURADO", "NOME FUNCIONARIO",
    }
    rows = []
    for _, row in raw.iterrows():
        nome_raw = str(row.get(col_nome) or "").strip()
        if not nome_raw or _norm(nome_raw) in nomes_bloqueados:
            continue
        rows.append({
            "nome":        nome_raw,
            "_norm_nome":  _norm(nome_raw),
            "dt_demissao": _parse_date(row.get(col_dem)) if col_dem else None,
            "cpf":         str(row.get(col_cpf) or "").strip() if col_cpf else "",
            "matricula":   str(row.get(col_mat) or "").strip() if col_mat else "",
        })

    df_out = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["nome", "_norm_nome", "dt_demissao", "cpf", "matricula"]
    )
    return df_out, colunas_detectadas


def _melhor_df(conteudo: bytes, nome_arq: str) -> Optional[pd.DataFrame]:
    """Tenta ler Excel ou CSV escolhendo o header com mais colunas nomeadas."""
    melhor: Optional[pd.DataFrame] = None
    melhor_score = -1

    def _score(df: pd.DataFrame) -> int:
        return len([c for c in df.columns if not str(c).lower().startswith("unnamed")])

    def _candidato(df: pd.DataFrame) -> bool:
        return not df.empty and _score(df) >= 1

    if nome_arq.endswith((".xlsx", ".xls")):
        for hr in range(10):
            try:
                df = pd.read_excel(io.BytesIO(conteudo), dtype=str, header=hr)
                df = df.dropna(how="all").dropna(how="all", axis=1)
                s = _score(df)
                if _candidato(df) and s > melhor_score:
                    melhor, melhor_score = df, s
            except Exception:
                continue
    else:
        for enc in ("latin-1", "cp1252", "utf-8-sig", "utf-8"):
            for sep in (";", ",", "\t", "|"):
                for hr in range(9):
                    try:
                        df = pd.read_csv(
                            io.BytesIO(conteudo), sep=sep, dtype=str,
                            encoding=enc, header=hr, skip_blank_lines=True,
                            on_bad_lines="skip",
                        )
                        df = df.dropna(how="all").dropna(how="all", axis=1)
                        s = _score(df)
                        if _candidato(df) and s > melhor_score:
                            melhor, melhor_score = df, s
                    except Exception:
                        continue
    return melhor


# ── Análise principal ────────────────────────────────────────────────────────

def analisar_exclusoes(
    df_audit: pd.DataFrame,
    periodo: str,
    df_desligados: Optional[pd.DataFrame] = None,
    prazo_exclusao_dias: int = 10,
    cobrir_mes_inteiro: bool = True,
) -> pd.DataFrame:
    """
    Retorna DataFrame com trilha completa de auditoria de exclusões indevidas.
    Fontes: df_audit da sessão + planilha de desligados (opcional).
    """
    if df_audit is None or df_audit.empty:
        return pd.DataFrame()

    inicio_comp, fim_comp = _periodo_to_dates(periodo)
    hoje = date.today()
    data_ref = fim_comp or hoje

    registros: list[dict] = []
    processados: set = set()

    # ── Fonte 1: df_audit (contratos × fatura × compra) ──────────────────────
    for _, row in df_audit.iterrows():
        nome         = str(row.get("Funcionário", "") or "")
        nome_n       = _norm(nome)
        if not nome_n:
            continue

        empresa      = str(row.get("Empresa", "") or "")
        dept         = str(row.get("Departamento", "") or "")
        contrato_adm = str(row.get("Contrato Adm.", "") or "")
        na_fatura    = bool(row.get("_na_fatura", False))
        na_compra    = bool(row.get("_na_compra", False))
        desligado    = bool(row.get("_desligado", False))
        inelegivel   = bool(row.get("_inelegivel_contrato", False))
        vlr_fatura   = float(row.get("Valor Fatura", 0) or 0)
        dt_dem       = _parse_date(row.get("Dt. Demissão"))
        dt_adm       = _parse_date(row.get("Dt. Admissão"))

        # R1 — Desligado ainda ativo (fatura ou compra)
        if desligado and (na_fatura or na_compra) and dt_dem:
            ultimo_coberto = _ultimo_dia_mes(dt_dem) if cobrir_mes_inteiro else dt_dem
            prazo_limite   = dt_dem + timedelta(days=prazo_exclusao_dias)
            dias_indev     = _dias_indevidos(ultimo_coberto, inicio_comp, fim_comp)
            vlr_prej       = round(vlr_fatura * dias_indev / 30, 2) if dias_indev else vlr_fatura
            dias_atraso    = max(0, (data_ref - prazo_limite).days)

            fontes = [f for f, b in [("fatura Unimed", na_fatura), ("compra", na_compra)] if b]
            if dias_atraso > 0:
                status = S_FORA_DO_PRAZO
                regra  = (f"Prazo de {prazo_exclusao_dias} dias p/ exclusão expirou — "
                          f"em atraso há {dias_atraso} dia(s)")
            else:
                status = S_COBRANCA_INDEVIDA
                regra  = (f"Desligado em {_fmt(dt_dem)} — "
                          f"ainda ativo em: {' e '.join(fontes)}")

            registros.append(_rec(
                nome=nome, empresa=empresa, dept=dept, contrato_adm=contrato_adm,
                status=status, dt_dem=dt_dem, data_perda=dt_dem,
                ultimo_coberto=ultimo_coberto, prazo_limite=prazo_limite,
                dias_atraso=dias_atraso, na_fatura=na_fatura, na_compra=na_compra,
                periodo=periodo, dias_indev=dias_indev,
                vlr_fatura=vlr_fatura, vlr_prej=vlr_prej, regra=regra,
            ))
            processados.add(nome_n)
            continue

        # R2 — Sem elegibilidade contratual mas ativo
        if inelegivel and (na_fatura or na_compra):
            fontes = [f for f, b in [("fatura Unimed", na_fatura), ("compra", na_compra)] if b]
            registros.append(_rec(
                nome=nome, empresa=empresa, dept=dept, contrato_adm=contrato_adm,
                status=S_EXCLUSAO_PENDENTE, dt_dem=None, data_perda=dt_adm,
                ultimo_coberto=None, prazo_limite=None, dias_atraso=0,
                na_fatura=na_fatura, na_compra=na_compra,
                periodo=periodo, dias_indev=31,
                vlr_fatura=vlr_fatura, vlr_prej=vlr_fatura,
                regra=f"Sem elegibilidade ao plano — ativo em: {' e '.join(fontes)}",
            ))
            processados.add(nome_n)

    # ── Fonte 2: planilha de desligados × fatura ─────────────────────────────
    if df_desligados is not None and not df_desligados.empty and "_na_fatura" in df_audit.columns:
        nomes_na_fat = {
            _norm(str(n or ""))
            for n in df_audit.loc[df_audit["_na_fatura"].astype(bool), "Funcionário"]
        }
        fat_lookup = {
            _norm(str(r.get("Funcionário", "") or "")): float(r.get("Valor Fatura", 0) or 0)
            for _, r in df_audit.iterrows()
        }

        for _, drow in df_desligados.iterrows():
            nome_d  = str(drow.get("nome", "") or "")
            nome_n  = _norm(nome_d)
            if not nome_n or nome_n in processados:
                continue
            if nome_n not in nomes_na_fat:
                continue

            dt_dem = drow.get("dt_demissao")
            if not isinstance(dt_dem, date):
                dt_dem = _parse_date(dt_dem)

            ultimo_coberto = (_ultimo_dia_mes(dt_dem) if cobrir_mes_inteiro else dt_dem) if dt_dem else None
            prazo_limite   = (dt_dem + timedelta(days=prazo_exclusao_dias)) if dt_dem else None
            dias_indev     = _dias_indevidos(ultimo_coberto, inicio_comp, fim_comp) if ultimo_coberto else 0
            dias_atraso    = max(0, (data_ref - prazo_limite).days) if prazo_limite else 0
            vlr_fat        = fat_lookup.get(nome_n, 0.0)
            vlr_prej       = round(vlr_fat * dias_indev / 30, 2) if dias_indev else vlr_fat

            status = S_FORA_DO_PRAZO if dias_atraso > 0 else S_COBRANCA_INDEVIDA
            regra  = (
                f"Prazo de {prazo_exclusao_dias} dias expirou — em atraso há {dias_atraso} dia(s) "
                f"[planilha de desligados]"
                if dias_atraso > 0
                else "Consta na planilha de desligados — ainda ativo na fatura Unimed"
            )

            registros.append(_rec(
                nome=nome_d, empresa="", dept="", contrato_adm="",
                status=status, dt_dem=dt_dem, data_perda=dt_dem,
                ultimo_coberto=ultimo_coberto, prazo_limite=prazo_limite,
                dias_atraso=dias_atraso, na_fatura=True, na_compra=False,
                periodo=periodo, dias_indev=dias_indev,
                vlr_fatura=vlr_fat, vlr_prej=vlr_prej, regra=regra,
            ))
            processados.add(nome_n)

    # ── R3: CPF duplicado na fatura ──────────────────────────────────────────
    col_cpf = _encontrar_col(df_audit, "cpf", "c.p.f", "documento")
    if col_cpf and "_na_fatura" in df_audit.columns:
        df_fat = df_audit[df_audit["_na_fatura"].astype(bool)].copy()
        cpf_s  = df_fat[col_cpf].astype(str).str.strip()
        cpf_s  = cpf_s[cpf_s.ne("") & cpf_s.str.lower().ne("nan")]
        dup    = set(cpf_s[cpf_s.duplicated(keep=False)])
        for _, drow in df_fat[df_fat[col_cpf].astype(str).str.strip().isin(dup)].iterrows():
            nome_d = str(drow.get("Funcionário", "") or "")
            if _norm(nome_d) in processados:
                continue
            cpf_v = str(drow.get(col_cpf, "") or "")
            registros.append(_rec(
                nome=nome_d, empresa=str(drow.get("Empresa", "") or ""),
                dept=str(drow.get("Departamento", "") or ""),
                contrato_adm=str(drow.get("Contrato Adm.", "") or ""),
                status=S_DUPLICIDADE, dt_dem=None, data_perda=None,
                ultimo_coberto=None, prazo_limite=None, dias_atraso=0,
                na_fatura=True, na_compra=bool(drow.get("_na_compra", False)),
                periodo=periodo, dias_indev=0,
                vlr_fatura=float(drow.get("Valor Fatura", 0) or 0),
                vlr_prej=float(drow.get("Valor Fatura", 0) or 0),
                regra=f"CPF {cpf_v} — múltiplas matrículas ativas na fatura",
            ))
            processados.add(_norm(nome_d))

    if not registros:
        return pd.DataFrame()

    df_out = pd.DataFrame(registros)
    df_out["_ord"] = df_out["Status"].map(_STATUS_PRIORIDADE).fillna(9).astype(int)
    df_out = (df_out.sort_values(["_ord", "Valor Estimado Prejuízo"], ascending=[True, False])
              .drop(columns=["_ord"])
              .reset_index(drop=True))
    return df_out


def _rec(nome, empresa, dept, contrato_adm,
         status, dt_dem, data_perda, ultimo_coberto, prazo_limite,
         dias_atraso, na_fatura, na_compra,
         periodo, dias_indev, vlr_fatura, vlr_prej, regra) -> dict:
    return {
        "Funcionário":                  nome,
        "Empresa":                      empresa,
        "Departamento":                 dept,
        "Contrato Adm.":                contrato_adm,
        "Status":                       status,
        "Dt. Demissão":                 _fmt(dt_dem),
        "Data Perda do Direito":        _fmt(data_perda),
        "Último Dia de Cobertura":      _fmt(ultimo_coberto),
        "Prazo Limite de Exclusão":     _fmt(prazo_limite),
        "Dias em Atraso (Exclusão)":    int(dias_atraso),
        "Ativo na Fatura":              "Sim" if na_fatura else "Não",
        "Ativo na Compra":              "Sim" if na_compra else "Não",
        "Competência Indevida Inicial": periodo,
        "Dias de Cobrança Indevida":    int(dias_indev),
        "Valor Fatura Mensal":          round(float(vlr_fatura), 2),
        "Valor Estimado Prejuízo":      round(float(vlr_prej), 2),
        "Regra Violada":                regra,
    }


# ── KPIs ─────────────────────────────────────────────────────────────────────

def calcular_kpis(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {}
    atrasos = df.loc[df["Dias em Atraso (Exclusão)"] > 0, "Dias em Atraso (Exclusão)"]
    return {
        "vidas_indevidas":    len(df),
        "valor_total":        float(df["Valor Estimado Prejuízo"].sum()),
        "cobranca_indevida":  int((df["Status"] == S_COBRANCA_INDEVIDA).sum()),
        "fora_do_prazo":      int((df["Status"] == S_FORA_DO_PRAZO).sum()),
        "excl_pendente":      int((df["Status"] == S_EXCLUSAO_PENDENTE).sum()),
        "duplicidade":        int((df["Status"] == S_DUPLICIDADE).sum()),
        "dependente_indevido": int((df["Status"] == S_DEPENDENTE_INDEVIDO).sum()),
        "tempo_medio_atraso": round(float(atrasos.mean()), 1) if not atrasos.empty else 0.0,
    }
