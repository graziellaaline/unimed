# -*- coding: utf-8 -*-
"""
Leitura e cruzamento das 3 fontes: Contratos × Fatura CSV × Compra.
"""
import difflib
import unicodedata
from pathlib import Path
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _norm(s) -> str:
    txt = str(s or "").strip().strip("\"'")
    if any(ch in txt for ch in ("Ã", "Â", "¢", "€", "™")):
        try:
            txt = txt.encode("latin-1").decode("utf-8")
        except Exception:
            pass
    txt = txt.upper()
    nfkd = unicodedata.normalize("NFKD", txt)
    return " ".join("".join(c for c in nfkd if not unicodedata.combining(c)).split())


def _encontrar_col(df: pd.DataFrame, *keywords) -> Optional[str]:
    for kw in keywords:
        kw_n = _norm(kw).lower()
        for col in df.columns:
            if kw_n in _norm(col).lower():
                return col
    return None


def _col_por_indice(df: pd.DataFrame, idx: int) -> Optional[str]:
    """Retorna o nome da coluna pela posição (0-indexed). Ex: 3 = coluna D."""
    if 0 <= idx < len(df.columns):
        return df.columns[idx]
    return None


def _cabecalho_util(df: pd.DataFrame) -> bool:
    if df.empty or len(df.columns) < 2:
        return False
    named = sum(1 for c in df.columns if not str(c).lower().startswith("unnamed"))
    return named >= 2


def _score_cabecalho(df: pd.DataFrame, grupos_keywords: list[tuple[str, ...]] | None = None) -> int:
    if not _cabecalho_util(df):
        return -1
    if not grupos_keywords:
        return 0

    score = 0
    for grupo in grupos_keywords:
        if _encontrar_col(df, *grupo):
            score += 1
    return score


def _ler_planilha(path, grupos_keywords: list[tuple[str, ...]] | None = None) -> pd.DataFrame:
    """
    Lê CSV ou Excel com detecção automática de cabeçalho.
    Planilhas de RH frequentemente têm linhas de título antes dos dados —
    testa até a 8ª linha até encontrar colunas com nomes reais.
    """
    p = Path(path)
    melhor_df = None
    melhor_score = -1

    if p.suffix.lower() in (".xlsx", ".xls"):
        for header_row in range(9):
            try:
                df = pd.read_excel(p, dtype=str, header=header_row)
                df = df.dropna(how="all").dropna(how="all", axis=1)
                score = _score_cabecalho(df, grupos_keywords)
                if score > melhor_score:
                    melhor_df = df
                    melhor_score = score
            except Exception:
                continue
        if melhor_df is not None and (melhor_score > 0 or grupos_keywords is None):
            return melhor_df
        raise ValueError(f"Não foi possível encontrar o cabeçalho em '{p.name}'. "
                         "Verifique se o arquivo não está protegido ou corrompido.")

    # CSV — também tenta encontrar o cabeçalho correto, porque alguns exports
    # chegam com linhas introdutórias antes dos nomes das colunas.
    for enc in ("latin-1", "cp1252", "utf-8-sig", "utf-8"):
        for sep in (";", ",", "\t", "|"):
            for header_row in range(9):
                try:
                    df = pd.read_csv(
                        p,
                        encoding=enc,
                        sep=sep,
                        dtype=str,
                        header=header_row,
                        skip_blank_lines=True,
                        on_bad_lines="skip",
                    )
                    df = df.dropna(how="all").dropna(how="all", axis=1)
                    score = _score_cabecalho(df, grupos_keywords)
                    if score > melhor_score:
                        melhor_df = df
                        melhor_score = score
                except Exception:
                    continue
    if melhor_df is not None and (melhor_score > 0 or grupos_keywords is None):
        return melhor_df
    raise ValueError(f"Não foi possível ler '{p.name}'.")


def _parse_brl(v) -> float:
    s = str(v or "").strip().replace("R$", "").replace("\xa0", "").replace(" ", "")
    if not s or s.lower() in ("nan", "none", "-", ""):
        return 0.0
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.index(",") > s.index(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0


def _fmt_data(v) -> str:
    if v is None or str(v).strip() in ("", "nan", "None"):
        return ""
    try:
        ts = pd.to_datetime(v, dayfirst=True, errors="coerce")
        if pd.isna(ts):
            ts = pd.to_datetime(v, errors="coerce")
        return ts.strftime("%d/%m/%Y") if not pd.isna(ts) else str(v).strip()
    except Exception:
        return str(v).strip()


def _str(v) -> str:
    s = str(v or "").strip()
    return "" if s.lower() in ("nan", "none") else s


# ---------------------------------------------------------------------------
# Leitura das 3 fontes
# ---------------------------------------------------------------------------

_CONTRATOS_INELEGIVEIS = {
    "DETERMINADO", "TERCEIRIZACAO DETERMINADO", "TERCEIRIZAÇÃO DETERMINADO",
    "TEMPORARIO", "TEMPORÁRIO", "TERC DETERMINADO",
}


def ler_contratos(path, col_map: dict = None) -> pd.DataFrame:
    """
    Lê contratos usando apenas a nomenclatura das colunas.
    """
    df = _ler_planilha(path, [
        ("funcionario", "funcionária", "nome funcionario", "nome da funcionária"),
        ("departamento", "depto", "setor", "unidade", "lotação"),
        ("valor plano", "vlr plano", "mensalidade titular", "valor mensal titular"),
        ("admissao", "dt. admissao", "admissão", "dt adm"),
        ("contrato adm", "contrato administrativo", "tipo contrato"),
    ])
    col_map = col_map or {}

    def col(key, *defs):
        # 1. mapeamento explícito salvo
        if col_map.get(key):
            return col_map[key]
        # 2. detecção por keyword no nome da coluna
        return _encontrar_col(df, *defs)

    c = {
        "cod_func":     col("cod_func",
                            "cod. func", "cod func", "codigo", "código", "matricula",
                            "matrícula", "cód. funcionário", "num func", "cod. funcionario",
                            "chapa", "id funcionario", "id funcionário"),
        "funcionario":  col("funcionario",
                            "funcionario", "funcionária", "nome", "colaborador", "empregado",
                            "nome funcionario", "nome do funcionario", "nome da funcionaria",
                            "nome da funcionária", "nome colaborador", "nome empregado"),
        "departamento": col("departamento",
                            "departamento", "depto", "setor", "centro de custo",
                            "centro custo", "lotacao", "lotação", "unidade", "local"),
        "vlr_contrato": col("vlr_contrato",
                            "valor plano", "vlr plano", "plano saude", "plano de saude",
                            "vl. plano", "vl plano", "valor ps", "saude",
                            "mensalidade", "vlr. plano", "ps titular", "plano",
                            "valor mensal", "mensal titular", "mensalidade titular",
                            "valor titular", "valor mensal titular"),
        "admissao":     col("admissao",
                            "admissao", "dt. admissao", "data admissao", "data admissão",
                            "dt admissao", "dt. admissão", "admissão", "dt adm", "data adm"),
        "contrato_adm": col("contrato_adm",
                            "contrato adm", "contrato administrativo", "contrato adm.",
                            "contr. adm", "contrato adm/", "contrato adm ",
                            "tipo contrato", "contrato administrativo/adm"),
        "demissao":     col("demissao",
                            "demissao", "dt. demissao", "data demissao", "data demissão",
                            "dt demissao", "demissão", "rescisao", "rescisão", "desligamento",
                            "data desligamento"),
    }

    rows = []
    for _, row in df.iterrows():
        func = _str(row.get(c["funcionario"]) if c["funcionario"] else "")
        if not func:
            continue
        # Ignora linhas que parecem ser cabeçalho repetido
        if _norm(func) in ("FUNCIONARIO", "NOME", "COLABORADOR", "EMPREGADO",
                           "NOME FUNCIONARIO", "NOME DO FUNCIONARIO"):
            continue

        vlr = _parse_brl(row.get(c["vlr_contrato"]) if c["vlr_contrato"] else 0)
        tem_direito = vlr > 0

        admissao = _fmt_data(row.get(c["admissao"]) if c["admissao"] else "")
        demissao = _fmt_data(row.get(c["demissao"]) if c["demissao"] else "")

        rows.append({
            "cod_func":     _str(row.get(c["cod_func"]) if c["cod_func"] else ""),
            "funcionario":  func,
            "_norm_func":   _norm(func),
            "departamento": _str(row.get(c["departamento"]) if c["departamento"] else ""),
            "contrato_adm": _str(row.get(c["contrato_adm"]) if c["contrato_adm"] else ""),
            "tem_direito":  tem_direito,
            "vlr_contrato": vlr,
            "admissao":     admissao,
            "demissao":     demissao,
        })

    return pd.DataFrame(rows)


def ler_fatura_csv(path, col_map: dict = None) -> pd.DataFrame:
    df = _ler_planilha(path, [
        ("titular", "beneficiario", "nome"),
        ("categoria", "tipo"),
        ("descricao", "descrição", "item"),
        ("valor", "vl.", "preco"),
        ("data inclusao", "data de inclusao", "dt. inclusao"),
    ])
    col_map = col_map or {}

    def col(key, *defs):
        return col_map.get(key) or _encontrar_col(df, *defs)

    c = {
        "titular":       col("titular",       "titular", "beneficiario", "nome"),
        "categoria":     col("categoria",      "categoria", "tipo"),
        "descricao":     col("descricao",      "descricao", "descrição", "item", "produto", "servico"),
        "valor":         col("valor",          "valor", "vl.", "preco", "preco unit"),
        "data_inclusao": col("data_inclusao",  "data inclusao", "data de inclusao", "dt. inclusao",
                             "dt inclusao", "inclusao", "dt. inclusão", "data inclusão"),
        "nascimento":    col("nascimento",     "nascimento", "data nasc", "dt nasc", "data de nascimento"),
    }

    obrigatorias = {
        "titular": "Titular/Beneficiário",
        "descricao": "Descrição",
        "valor": "Valor",
    }
    faltando = [rotulo for key, rotulo in obrigatorias.items() if not c.get(key)]
    if faltando:
        raise ValueError(
            "Coluna(s) obrigatória(s) não encontrada(s) na fatura: "
            + ", ".join(faltando)
        )

    titulares: dict = {}
    linhas_validas = 0

    for _, row in df.iterrows():
        nome_raw = _str(row.get(c["titular"]) if c["titular"] else "")
        if not nome_raw:
            continue

        nome_norm = _norm(nome_raw)

        desc_raw  = _str(row.get(c["descricao"]) if c["descricao"] else "")
        desc_norm = _norm(desc_raw)

        # Regra EXATA: só aceita as duas descrições informadas pela Graziella.
        # Qualquer outra linha (duplicata, taxa, odonto, previdência, etc.) é ignorada.
        eh_conta_medica  = (desc_norm == "CONTA MEDICA")
        eh_mensalidade_s = ("MENSALIDADE" in desc_norm and "CONTRIBUICAO" in desc_norm)

        if not (eh_conta_medica or eh_mensalidade_s):
            continue

        linhas_validas += 1

        categ_raw = _str(row.get(c["categoria"]) if c["categoria"] else "")
        categ_n   = _norm(categ_raw).upper()
        eh_titular = (
            "TITULAR" in categ_n
            or (not categ_n)  # sem coluna categoria → trata como titular
        )

        # "Conta médica" = coparticipação; "Mensalidade/Contribuição Saúde" = mensalidade
        eh_mensalidade = eh_mensalidade_s

        valor = _parse_brl(row.get(c["valor"]) if c["valor"] else 0)

        data_inc = _fmt_data(row.get(c["data_inclusao"]) if c["data_inclusao"] else "")
        nasc     = _fmt_data(row.get(c["nascimento"])    if c["nascimento"]    else "")

        if nome_norm not in titulares:
            titulares[nome_norm] = {
                "nome":            nome_raw,
                "nascimento":      nasc,
                "vlr_mensalidade": 0.0,
                "vlr_dependente":  0.0,
                "vlr_copart":      0.0,
                # Inclusões do mês devem considerar apenas o titular.
                "data_inclusao":   data_inc if eh_titular else "",
            }
        else:
            # Preenche data_inclusao apenas a partir da linha do titular.
            if eh_titular and data_inc and not titulares[nome_norm]["data_inclusao"]:
                titulares[nome_norm]["data_inclusao"] = data_inc
            if nasc and not titulares[nome_norm]["nascimento"]:
                titulares[nome_norm]["nascimento"] = nasc

        if eh_titular and eh_mensalidade:
            titulares[nome_norm]["vlr_mensalidade"] += valor
        elif not eh_titular and eh_mensalidade:
            titulares[nome_norm]["vlr_dependente"] += valor
        else:
            titulares[nome_norm]["vlr_copart"] += valor

    if linhas_validas == 0:
        raise ValueError(
            "Nenhuma linha válida de fatura encontrada. "
            "Verifique se a coluna de descrição contém 'Mensalidade/Contribuição Saúde' "
            "ou 'Conta médica'."
        )

    rows = []
    for nome_norm, d in titulares.items():
        vlr_mens = round(d["vlr_mensalidade"], 2)
        vlr_dep  = round(d["vlr_dependente"],  2)
        vlr_cop  = round(d["vlr_copart"],      2)
        rows.append({
            "nome_fatura":        d["nome"],
            "_norm_fatura":       nome_norm,
            "nascimento_fat":     d["nascimento"],
            "vlr_mensalidade":    vlr_mens,
            "vlr_dependente":     vlr_dep,
            "vlr_copart":         vlr_cop,
            # Total fatura = mensalidade + dependentes + coparticipação (Conta médica)
            "vlr_fatura":         round(vlr_mens + vlr_dep + vlr_cop, 2),
            "data_inclusao":      d["data_inclusao"],
        })

    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["nome_fatura", "_norm_fatura", "nascimento_fat",
                 "vlr_fatura", "vlr_mensalidade", "vlr_dependente",
                 "vlr_copart", "data_inclusao"]
    )


def ler_faturas_csv(paths: list, col_map: dict = None) -> pd.DataFrame:
    """
    Lê múltiplos arquivos de fatura e consolida em um único DataFrame.
    Titulares que aparecem em mais de uma fatura têm seus valores somados.
    """
    if not paths:
        return pd.DataFrame(
            columns=["nome_fatura", "_norm_fatura", "nascimento_fat",
                     "vlr_fatura", "vlr_mensalidade", "vlr_dependente",
                     "vlr_copart", "data_inclusao"]
        )

    partes = []
    falhas = []
    for p in paths:
        try:
            df_parte = ler_fatura_csv(p, col_map)
            if not df_parte.empty:
                partes.append(df_parte)
        except Exception as exc:
            falhas.append(f"{Path(p).name}: {exc}")

    if falhas:
        raise ValueError(
            "Erro ao ler a(s) fatura(s): " + " | ".join(falhas)
        )

    if not partes:
        return pd.DataFrame(
            columns=["nome_fatura", "_norm_fatura", "nascimento_fat",
                     "vlr_fatura", "vlr_mensalidade", "vlr_dependente",
                     "vlr_copart", "data_inclusao"]
        )

    df_all = pd.concat(partes, ignore_index=True)

    # Alguns uploads trazem o mesmo titular repetido de forma idêntica em mais de
    # um arquivo. Antes de consolidar por nome, removemos duplicatas exatas para
    # evitar dobrar a cobrança do mesmo conjunto de valores.
    df_all = df_all.drop_duplicates(
        subset=[
            "_norm_fatura",
            "nascimento_fat",
            "vlr_fatura",
            "vlr_mensalidade",
            "vlr_dependente",
            "vlr_copart",
            "data_inclusao",
        ]
    )

    # Consolida: mesma pessoa em arquivos diferentes → soma valores, mantém 1ª data de inclusão
    df_cons = (
        df_all.groupby("_norm_fatura", as_index=False)
        .agg(
            nome_fatura    =("nome_fatura",    "first"),
            nascimento_fat =("nascimento_fat", "first"),
            vlr_fatura     =("vlr_fatura",     "sum"),
            vlr_mensalidade=("vlr_mensalidade","sum"),
            vlr_dependente =("vlr_dependente", "sum"),
            vlr_copart     =("vlr_copart",     "sum"),
            data_inclusao  =("data_inclusao",  "first"),
        )
    )
    for col in ["vlr_fatura", "vlr_mensalidade", "vlr_dependente", "vlr_copart"]:
        df_cons[col] = df_cons[col].round(2)

    return df_cons


def ler_compra(path, col_map: dict = None) -> pd.DataFrame:
    """
    Lê planilha de compras e agrupa por funcionário usando apenas a nomenclatura.
    Cada funcionário pode ter múltiplas linhas (titular + dependentes).
    - vlr_empresa: parcela da empresa → comparada com valor do contrato
    - vlr_func   : parcela do beneficiário
    - vlr_compra_total   : soma de TODAS as linhas (empresa + func) → comparada com fatura
    """
    df = _ler_planilha(path, [
        ("funcionario", "funcionária", "nome funcionario", "titular"),
        ("valor empresa", "valor mensal empresa", "mensalidade empresa", "patronal", "custo empresa"),
        ("valor beneficiario", "valor funcionario", "mensalidade funcionario", "desconto funcionario"),
        ("cod. func", "codigo", "matricula", "chapa"),
    ])
    col_map = col_map or {}

    def col(key, *defs):
        if col_map.get(key):
            return col_map[key]
        return _encontrar_col(df, *defs)

    c = {
        "cod_func":    col("cod_func",
                           "cod. func", "cod func", "codigo", "código", "matricula",
                           "matrícula", "cód. funcionário", "num func", "chapa"),
        "funcionario": col("funcionario",
                           "funcionario", "funcionária", "nome", "colaborador", "empregado",
                           "nome do funcionario", "nome funcionario", "nome da funcionaria",
                           "nome da funcionária", "titular", "beneficiario titular"),
        "vlr_empresa": col("vlr_empresa",
                           "valor empresa", "vlr empresa", "empresa", "valor emp",
                            "vl. empresa", "emp", "patronal", "empresa ps",
                           "val empresa", "val. empresa", "valor mensal empresa",
                           "valor titular empresa", "mensalidade empresa", "mensal empresa",
                           "custo empresa", "custo patronal"),
        "vlr_func":    col("vlr_func",
                           "valor beneficiario", "vlr beneficiario", "beneficiario",
                            "valor funcionario", "vlr funcionario",
                            "vl. beneficiario", "func ps", "val funcionario",
                           "val. funcionario", "valor mensal funcionario",
                           "mensalidade funcionario", "mensal funcionario",
                           "custo funcionario", "desconto funcionario", "desconto beneficiario"),
    }

    # Lê todas as linhas brutas
    linhas: dict = {}   # _norm_func → acumulador
    for _, row in df.iterrows():
        func = _str(row.get(c["funcionario"]) if c["funcionario"] else "")
        if not func or func.lower() in ("funcionario", "nome", "colaborador"):
            continue

        norm = _norm(func)
        vlr_emp = _parse_brl(row.get(c["vlr_empresa"]) if c["vlr_empresa"] else 0)
        vlr_fun = _parse_brl(row.get(c["vlr_func"])    if c["vlr_func"]    else 0)
        cod     = _str(row.get(c["cod_func"]) if c["cod_func"] else "")

        if norm not in linhas:
            linhas[norm] = {
                "cod_func_compra": cod,
                "nome_compra":     func,
                "_norm_compra":    norm,
                "vlr_empresa":     0.0,
                "vlr_func":        0.0,
            }
        # Acumula todas as linhas (titular + dependentes)
        linhas[norm]["vlr_empresa"] += vlr_emp
        linhas[norm]["vlr_func"]    += vlr_fun

    if not linhas:
        return pd.DataFrame(
            columns=["cod_func_compra", "nome_compra", "_norm_compra",
                     "vlr_empresa", "vlr_func", "vlr_compra_total"]
        )

    rows = []
    for d in linhas.values():
        rows.append({
            "cod_func_compra":  d["cod_func_compra"],
            "nome_compra":      d["nome_compra"],
            "_norm_compra":     d["_norm_compra"],
            "vlr_empresa":      round(d["vlr_empresa"], 2),  # comparar com contrato
            "vlr_func":         round(d["vlr_func"],    2),
            "vlr_compra_total": round(d["vlr_empresa"] + d["vlr_func"], 2),  # comparar c/ fatura
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Matching por nome
# ---------------------------------------------------------------------------

def _match_nome(nome_a: str, nomes_b: list, threshold=0.72) -> Optional[int]:
    if not nome_a or not nomes_b:
        return None
    best_i, best_s = None, 0.0
    for i, nb in enumerate(nomes_b):
        s = difflib.SequenceMatcher(None, nome_a, nb).ratio()
        if s > best_s and s >= threshold:
            best_s, best_i = s, i
    return best_i


# ---------------------------------------------------------------------------
# Cruzamento principal
# ---------------------------------------------------------------------------

def cruzar(df_cont: pd.DataFrame,
           df_fat: pd.DataFrame,
           df_compra: pd.DataFrame,
           periodo: str) -> pd.DataFrame:

    if df_cont.empty:
        return pd.DataFrame()

    fat_nomes    = df_fat["_norm_fatura"].tolist()    if not df_fat.empty    else []
    compra_nomes = df_compra["_norm_compra"].tolist() if not df_compra.empty else []

    fat_usadas    = set()
    compra_usadas = set()
    resultado     = []

    # ── 1. Funcionários do contrato ─────────────────────────────────────────
    for _, cont in df_cont.iterrows():
        nome_c = cont["_norm_func"]

        fat_idx = None
        if fat_nomes:
            idx = _match_nome(nome_c, fat_nomes)
            if idx is not None and idx not in fat_usadas:
                fat_idx = idx
                fat_usadas.add(idx)

        compra_idx = None
        if compra_nomes:
            idx = _match_nome(nome_c, compra_nomes)
            if idx is not None and idx not in compra_usadas:
                compra_idx = idx
                compra_usadas.add(idx)

        fat   = df_fat.iloc[fat_idx]     if fat_idx    is not None else None
        comp  = df_compra.iloc[compra_idx] if compra_idx is not None else None

        na_fatura = fat  is not None
        na_compra = comp is not None

        vlr_fat       = float(fat["vlr_fatura"])      if na_fatura else 0.0
        vlr_mens_fat  = float(fat["vlr_mensalidade"]) if na_fatura else 0.0
        vlr_copart_fat= float(fat["vlr_copart"])      if na_fatura else 0.0
        vlr_emp       = float(comp["vlr_empresa"])     if na_compra else 0.0
        vlr_comp_tot  = float(comp["vlr_compra_total"])if na_compra else 0.0
        data_inc = str(fat["data_inclusao"]) if na_fatura else ""

        demissao  = cont.get("demissao", "")
        desligado = bool(demissao and str(demissao).strip() not in ("", "nan"))

        resultado.append({
            "Funcionário":        cont["funcionario"],
            "Departamento":       cont["departamento"],
            "Contrato Adm.":      cont.get("contrato_adm", ""),
            "Cod. Funcionário":   cont["cod_func"],
            "Tem Direito":        "Sim" if cont["tem_direito"] else "Não",
            "Está na Fatura":     "Sim" if na_fatura else "Não",
            "Está na Compra":     "Sim" if na_compra else "Não",
            "Valor Fatura":       vlr_fat,
            "Valor Empresa (Compra)": vlr_emp,      # comparar com contrato
            "Valor Compra Total": vlr_comp_tot,     # comparar com fatura
            "Valor Contrato":     cont["vlr_contrato"],
            "Dif. Contrato x Compra": round(max(vlr_emp - cont["vlr_contrato"], 0.0), 2),
            "Dif. Fatura x Compra":   round(vlr_fat - vlr_comp_tot, 2),
            "Data Inclusão":      data_inc,
            "Dt. Admissão":       cont.get("admissao", ""),
            "Dt. Demissão":       demissao,
            "Período":            periodo,
            "_na_fatura":         na_fatura,
            "_na_compra":         na_compra,
            "_desligado":         desligado,
            "_sem_contrato":      False,
        })

    # ── 2. Na fatura mas sem contrato ───────────────────────────────────────
    for i, fat in df_fat.iterrows():
        if i in fat_usadas:
            continue

        comp_idx = _match_nome(fat["_norm_fatura"], compra_nomes)
        comp = None
        if comp_idx is not None and comp_idx not in compra_usadas:
            comp = df_compra.iloc[comp_idx]
            compra_usadas.add(comp_idx)

        vlr_comp_tot = float(comp["vlr_compra_total"]) if comp is not None else 0.0
        vlr_emp      = float(comp["vlr_empresa"])     if comp is not None else 0.0
        vlr_fat_f    = float(fat["vlr_fatura"])

        resultado.append({
            "Funcionário":            fat["nome_fatura"],
            "Departamento":           "",
            "Contrato Adm.":          "",
            "Cod. Funcionário":       "",
            "Tem Direito":            "—",
            "Está na Fatura":         "Sim",
            "Está na Compra":         "Sim" if comp is not None else "Não",
            "Valor Fatura":           vlr_fat_f,
            "Valor Empresa (Compra)": vlr_emp,
            "Valor Compra Total":     vlr_comp_tot,
            "Valor Contrato":         0.0,
            "Dif. Contrato x Compra": 0.0,
            "Dif. Fatura x Compra":   round(vlr_fat_f - vlr_comp_tot, 2),
            "Data Inclusão":          str(fat["data_inclusao"]),
            "Dt. Admissão":           "",
            "Dt. Demissão":           "",
            "Período":                periodo,
            "_na_fatura":             True,
            "_na_compra":             comp is not None,
            "_desligado":             False,
            "_sem_contrato":          True,
        })

    # ── 3. Na compra mas sem contrato e sem fatura ──────────────────────────
    for i, comp in df_compra.iterrows():
        if i in compra_usadas:
            continue
        resultado.append({
            "Funcionário":            comp["nome_compra"],
            "Departamento":           "",
            "Contrato Adm.":          "",
            "Cod. Funcionário":       comp.get("cod_func_compra", ""),
            "Tem Direito":            "—",
            "Está na Fatura":         "Não",
            "Está na Compra":         "Sim",
            "Valor Fatura":           0.0,
            "Valor Empresa (Compra)": float(comp["vlr_empresa"]),
            "Valor Compra Total":     float(comp["vlr_compra_total"]),
            "Valor Contrato":         0.0,
            "Dif. Contrato x Compra": 0.0,
            "Dif. Fatura x Compra":   round(-float(comp["vlr_compra_total"]), 2),
            "Data Inclusão":          "",
            "Dt. Admissão":           "",
            "Dt. Demissão":           "",
            "Período":                periodo,
            "_na_fatura":             False,
            "_na_compra":             True,
            "_desligado":             False,
            "_sem_contrato":          True,
        })

    return pd.DataFrame(resultado)
