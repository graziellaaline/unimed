# -*- coding: utf-8 -*-
"""
Leitura e cruzamento das 3 fontes: Contratos × Fatura CSV × Compra.
"""
import difflib
import re
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


def _encontrar_col_prioritaria(df: pd.DataFrame, *keywords) -> Optional[str]:
    melhor_col = None
    melhor_score = -1

    for prioridade, kw in enumerate(keywords):
        kw_n = _norm(kw).lower()
        for col in df.columns:
            col_n = _norm(col).lower()
            if kw_n not in col_n:
                continue

            score = 0
            if col_n == kw_n:
                score += 100
            elif col_n.startswith(kw_n):
                score += 80
            else:
                score += 60

            score += max(0, 30 - prioridade)
            score += len(kw_n)

            if any(bloq in col_n for bloq in ("MATRIC", "COD", "CODIGO", "CHAPA", "ID ")) and "nome" in kw_n:
                score -= 100

            if score > melhor_score:
                melhor_col = col
                melhor_score = score

    return melhor_col


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
    s = str(v or "").strip().replace("R$", "").replace("\xa0", "")
    if not s or s.lower() in ("nan", "none", "-", ""):
        return 0.0
    # Extrai o primeiro bloco numérico — ignora texto junto ao valor (ex: "403,20 titular")
    m = re.search(r'\d+(?:[.,]\d+)*', s)
    if not m:
        return 0.0
    s = m.group(0)
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.index(",") > s.index(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0


def _classificar_plano(vlr_raw: str) -> tuple[bool, bool]:
    """
    Interpreta o campo 'Plano de Saúde' da planilha de contratos.
    Retorna (tem_direito, copart_apos_exp).

    Valores padronizados (ordem de prioridade):
      "Sim com coparticipação após experiência"  → (True, True)   elegível após 90 dias da admissão
      "Sim com coparticipação imediato"          → (True, False)  elegível desde a admissão
      Valor numérico > 0                         → (True, False)  elegível (valor definido)
      "Não" / vazio / zero                       → (False, False) sem direito
      Outros "Sim" / "S" / "X" genéricos        → (True, False)  elegível (indicador afirmativo)

    ATENÇÃO: o teste numérico vem ANTES do teste de "NAO" no texto, porque alguns campos
    descritivos contêm frases como "450,00 - Cargo X - Pesquisa NÃO tem plano" onde o
    valor 450 indica elegibilidade e "NÃO" faz parte do nome do cargo/categoria.
    """
    s = _norm(vlr_raw)

    if not s or s in ("NAO", "N", "0", "-", "NONE", "NAN"):
        return False, False

    # "Sim com coparticipação após experiência" → aguarda 90 dias
    if "EXPERIENCIA" in s:
        return True, True

    # "Sim com coparticipação imediato" → elegível desde a admissão
    if "IMEDIATO" in s:
        return True, False

    # Valor numérico — verificado ANTES de "NAO" para não ser enganado por descrições
    # do tipo "450,00 - Auxiliar Agrícola II - Pesquisa NÃO tem plano"
    if _parse_brl(vlr_raw) > 0:
        return True, False

    # Indicador negativo genérico (só chega aqui se não houver valor numérico)
    if "NAO" in s:
        return False, False

    # Indicadores afirmativos genéricos ("Sim", "S", "X", "Possui"…)
    if any(s == a or s.startswith(a + " ") for a in ("SIM", "S", "X", "POSSUI", "TEM", "ATIVO")):
        return True, False

    return False, False


# Formatos testados em ordem: DD/MM primeiro (padrão BR), depois ISO e variantes.
# NUNCA usar fallback sem dayfirst — o pandas sem dayfirst usa formato americano (MM/DD)
# e inverte dia e mês em datas ambíguas (ex: "07/05" → julho 5 em vez de maio 7).
_DATE_FMTS_BR = [
    "%d/%m/%Y", "%d/%m/%y",
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d",
    "%d-%m-%Y", "%d.%m.%Y",
    "%d/%m/%Y %H:%M:%S",
]

def _fmt_data(v) -> str:
    if v is None or str(v).strip() in ("", "nan", "None"):
        return ""
    s = str(v).strip()
    for fmt in _DATE_FMTS_BR:
        try:
            ts = pd.to_datetime(s, format=fmt, errors="coerce")
            if not pd.isna(ts):
                return ts.strftime("%d/%m/%Y")
        except Exception:
            continue
    # Último recurso: inferência com dayfirst=True APENAS (nunca sem dayfirst)
    try:
        ts = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if not pd.isna(ts):
            return ts.strftime("%d/%m/%Y")
    except Exception:
        pass
    return s


def _str(v) -> str:
    s = str(v or "").strip()
    return "" if s.lower() in ("nan", "none") else s


# ---------------------------------------------------------------------------
# Leitura das 3 fontes
# ---------------------------------------------------------------------------

# Regras de elegibilidade ao plano de saúde:
# • TERCEIRIZAÇÃO + depto PLANALTINA/298 → sempre elegível (exceção prioritária).
# • TERCEIRIZAÇÃO + INDETERMINADO + "Sim" na planilha → elegível desde a admissão (sem carência).
# • INDETERMINADO puro (sem TERCEIRIZAÇÃO) + tem direito na planilha → elegível após 90 dias da admissão.
# • TMG → sem direito, exceto MAURO ALVES DA SILVA.
# • Contratos especiais (134, 119…) + INDETERMINADO → tem direito; + DETERMINADO → sem direito.
# • Qualquer DETERMINADO → sem direito (regra geral).
# • Demais → segue planilha de contratos (vlr_contrato > 0).
_PALAVRA_DETERMINADO   = "DETERMINADO"
_PALAVRA_TERCEIRIZACAO = "TERCEIR"
_PALAVRA_TMG           = "TMG"
_CONTRATOS_ESPECIAIS   = {"134", "119"}   # contratos com direito por código, exceto se DETERMINADO
_DEPTOS_COM_EXCECAO    = ("PLANALTINA", "298")
_MAURO_EXCECAO_NORM    = "MAURO ALVES DA SILVA"   # exceção TMG — tem direito ao plano
_ANATACHA_NORM         = "ANATACHA CARDOSO ARAUJO" # regra especial: mensalidade=empresa, copart=funcionária

CONTRATOS_HEADER_GROUPS = [
    ("funcionario", "funcionária", "nome funcionario", "nome da funcionária"),
    ("empresa", "cod empresa", "cód empresa", "cód. empresa"),
    ("departamento", "depto", "setor", "unidade", "lotação"),
    ("valor plano", "valor plano de saude", "valor plano de saúde", "vlr plano", "mensalidade titular", "valor mensal titular"),
    ("admissao", "dt. admissao", "dt. admissão", "admissão", "dt adm"),
    ("contrato adm", "contrato administrativo", "tipo contrato"),
]

FATURA_HEADER_GROUPS = [
    ("titular", "beneficiario", "beneficiário", "nome"),
    ("categoria", "tipo"),
    ("descricao", "descrição", "descricao do item", "descrição do item", "item"),
    ("valor", "vl.", "preco"),
    ("data inclusao", "data de inclusao", "dt. inclusao"),
]

COMPRA_HEADER_GROUPS = [
    ("funcionario", "funcionária", "nome funcionario", "titular"),
    ("valor empresa", "valor. empresa", "valor mensal empresa", "mensalidade empresa", "patronal", "custo empresa"),
    ("valor beneficiario", "valor beneficário", "valor. beneficário", "valor funcionario", "mensalidade funcionario", "desconto funcionario"),
    ("cod. func", "cód. func.", "codigo", "matricula", "chapa"),
    ("tipo", "categoria", "vinculo", "vínculo", "grau", "tp beneficiario", "tipo beneficiario", "tipo de beneficiario", "titular dependente"),
]


def ler_contratos(path, col_map: dict = None) -> pd.DataFrame:
    """
    Lê contratos usando apenas a nomenclatura das colunas.
    """
    df = _ler_planilha(path, CONTRATOS_HEADER_GROUPS)
    col_map = col_map or {}

    def col(key, *defs):
        # 1. mapeamento explícito salvo
        if col_map.get(key):
            return col_map[key]
        # 2. detecção por keyword no nome da coluna
        return _encontrar_col(df, *defs)

    c = {
        "cod_func":     col("cod_func",
                            "cod. func", "cód. func.", "cod func", "codigo", "código", "matricula",
                            "matrícula", "cód. funcionário", "num func", "cod. funcionario",
                            "chapa", "id funcionario", "id funcionário"),
        "funcionario":  _encontrar_col_prioritaria(
                            df,
                            "nome do funcionario", "nome da funcionaria",
                            "nome funcionario", "nome da funcionária",
                            "funcionario", "funcionária", "nome colaborador",
                            "nome empregado", "colaborador", "empregado", "nome"
                         ),
        "empresa":      col("empresa",
                            "cod empresa", "cód empresa", "cód. empresa", "codigo empresa", "código empresa",
                            "empresa", "emp", "cod emp"),
        "departamento": col("departamento",
                            "departamento", "depto", "setor", "centro de custo",
                            "centro custo", "lotacao", "lotação", "unidade", "local"),
        "vlr_contrato": col("vlr_contrato",
                            "valor plano", "valor plano de saude", "valor plano de saúde", "vlr plano", "plano saude", "plano de saude",
                            "vl. plano", "vl plano", "valor ps", "saude",
                            "mensalidade", "vlr. plano", "ps titular", "plano",
                            "valor mensal", "mensal titular", "mensalidade titular",
                            "valor titular", "valor mensal titular"),
        "admissao":     col("admissao",
                            "admissao", "dt. admissao", "dt. admissão", "data admissao", "data admissão",
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

        vlr_raw = str(row.get(c["vlr_contrato"]) if c["vlr_contrato"] else "")
        vlr = _parse_brl(vlr_raw)
        tem_direito, copart_apos_exp = _classificar_plano(vlr_raw)

        departamento  = _str(row.get(c["departamento"]) if c["departamento"] else "")
        contrato_adm  = _str(row.get(c["contrato_adm"]) if c["contrato_adm"] else "")
        dept_norm     = _norm(departamento)
        contrato_norm = _norm(contrato_adm)

        # "DETERMINADO" é substring de "INDETERMINADO" — excluir explicitamente
        eh_determinado   = _PALAVRA_DETERMINADO in contrato_norm and "INDETERMINADO" not in contrato_norm
        eh_terceirizacao = _PALAVRA_TERCEIRIZACAO in contrato_norm
        eh_tmg           = _PALAVRA_TMG in contrato_norm
        eh_especial      = any(cod in contrato_norm for cod in _CONTRATOS_ESPECIAIS)
        eh_depto_excecao = any(kw in dept_norm for kw in _DEPTOS_COM_EXCECAO)
        func_norm_val    = _norm(func)
        eh_mauro_excecao = func_norm_val == _MAURO_EXCECAO_NORM

        if eh_terceirizacao and eh_depto_excecao:
            # Exceção prioritária: TERCEIRIZAÇÃO + depto PLANALTINA/298 → sempre elegível
            inelegivel_tipo = False
            tem_direito     = True
        elif eh_terceirizacao and "INDETERMINADO" in contrato_norm and tem_direito:
            # TERCEIRIZAÇÃO + INDETERMINADO com "Sim" na planilha → elegível desde a admissão
            inelegivel_tipo = False
            copart_apos_exp = False
        elif eh_tmg and not eh_mauro_excecao:
            # Contratos TMG → sem direito (exceto MAURO ALVES DA SILVA)
            inelegivel_tipo = True
            tem_direito     = False
        elif eh_especial and not eh_determinado:
            # Contratos especiais (134, 119…) + INDETERMINADO → tem direito imediato
            inelegivel_tipo = False
            tem_direito     = True
            copart_apos_exp = False   # direito imediato — ignora texto "após experiência"
        elif eh_determinado:
            # Regra geral: qualquer DETERMINADO → sem direito
            inelegivel_tipo = True
            tem_direito     = False
        elif "INDETERMINADO" in contrato_norm and tem_direito:
            # INDETERMINADO puro (sem TERCEIRIZAÇÃO) → elegível após 90 dias da admissão
            inelegivel_tipo = False
            copart_apos_exp = True
        else:
            # Demais modalidades → segue planilha de contratos
            inelegivel_tipo = False
            # tem_direito já definido por _classificar_plano

        admissao = _fmt_data(row.get(c["admissao"]) if c["admissao"] else "")
        demissao = _fmt_data(row.get(c["demissao"]) if c["demissao"] else "")

        rows.append({
            "cod_func":           _str(row.get(c["cod_func"]) if c["cod_func"] else ""),
            "funcionario":        func,
            "_norm_func":         _norm(func),
            "empresa":            _str(row.get(c["empresa"]) if c["empresa"] else ""),
            "departamento":       departamento,
            "contrato_adm":       contrato_adm,
            "tem_direito":        tem_direito,
            "vlr_contrato":           vlr,
            "admissao":               admissao,
            "demissao":               demissao,
            "inelegivel_contrato":    inelegivel_tipo,
            "copart_apos_exp":        copart_apos_exp,
        })

    return pd.DataFrame(rows)


def ler_fatura_csv(path, col_map: dict = None) -> pd.DataFrame:
    df = _ler_planilha(path, FATURA_HEADER_GROUPS)
    col_map = col_map or {}

    def col(key, *defs):
        return col_map.get(key) or _encontrar_col(df, *defs)

    c = {
        # Prioridade: coluna "Titular" (nome do funcionário, igual para titular e dependentes)
        # deve vencer sobre "Beneficiário" (nome individual do dependente).
        # Isso garante que todos os lançamentos de uma família sejam agrupados pelo titular.
        "titular":       _encontrar_col_prioritaria(
                            df,
                            "titular",                            # coluna "Titular" → sempre o funcionário
                            "nome do titular",
                            "nome beneficiario", "beneficiario titular",
                            "nome do beneficiario", "beneficiário titular",
                            "nome do beneficiário", "beneficiario", "beneficiária", "beneficiário",
                            "nome"
                         ),
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
    ultimo_titular_norm: str | None = None  # fallback: dependente sem coluna "Titular" separada

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

        eh_mensalidade = eh_mensalidade_s

        valor    = _parse_brl(row.get(c["valor"]) if c["valor"] else 0)
        data_inc = _fmt_data(row.get(c["data_inclusao"]) if c["data_inclusao"] else "")
        nasc     = _fmt_data(row.get(c["nascimento"])    if c["nascimento"]    else "")

        # Determina a chave de agrupamento.
        # Se a coluna detectada já contém o nome do titular (ex: coluna "Titular"),
        # nome_norm já é o funcionário em todas as linhas — dependentes acumulam naturalmente.
        # Se a coluna detectada é "Beneficiário" e o dependente tem nome diferente,
        # ele não estará em `titulares` → usar o último titular visto como fallback.
        if not eh_titular and nome_norm not in titulares and ultimo_titular_norm:
            nome_key = ultimo_titular_norm
        else:
            nome_key = nome_norm

        if eh_titular:
            ultimo_titular_norm = nome_norm

        if nome_key not in titulares:
            titulares[nome_key] = {
                "nome":            nome_raw,
                "nascimento":      nasc,
                "vlr_mensalidade": 0.0,
                "vlr_dependente":  0.0,
                "vlr_copart":      0.0,
                "data_inclusao":   data_inc if eh_titular else "",
            }
        else:
            if eh_titular and data_inc and not titulares[nome_key]["data_inclusao"]:
                titulares[nome_key]["data_inclusao"] = data_inc
            if nasc and not titulares[nome_key]["nascimento"]:
                titulares[nome_key]["nascimento"] = nasc

        if eh_titular and eh_mensalidade:
            titulares[nome_key]["vlr_mensalidade"] += valor
        elif not eh_titular and eh_mensalidade:
            titulares[nome_key]["vlr_dependente"] += valor
        else:
            titulares[nome_key]["vlr_copart"] += valor

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
    Lê planilha de compras e agrupa por TITULAR usando apenas a nomenclatura.
    Dependentes são acumulados no titular correspondente (por cod_func ou por ordem).
    Dependentes nunca viram linhas autônomas na auditoria.
    - vlr_empresa     : parcela da empresa (titular + dependentes) → comparada com fatura
    - vlr_func        : parcela do beneficiário (titular + dependentes)
    - vlr_compra_total: soma de TODAS as linhas → comparada com fatura
    """
    df = _ler_planilha(path, COMPRA_HEADER_GROUPS)
    col_map = col_map or {}

    def col(key, *defs):
        if col_map.get(key):
            return col_map[key]
        return _encontrar_col(df, *defs)

    c = {
        "cod_func":    col("cod_func",
                           "cod. func", "cód. func.", "cod func", "codigo", "código", "matricula",
                           "matrícula", "cód. funcionário", "num func", "chapa"),
        "funcionario": _encontrar_col_prioritaria(
                           df,
                           "nome do funcionario", "nome da funcionaria",
                           "nome funcionario", "nome da funcionária",
                           "beneficiario titular", "funcionario", "funcionária",
                           "titular", "colaborador", "empregado", "nome"
                        ),
        "vlr_empresa": col("vlr_empresa",
                           "valor empresa", "valor. empresa", "vlr empresa", "empresa", "valor emp",
                           "vl. empresa", "emp", "patronal", "empresa ps",
                           "val empresa", "val. empresa", "valor mensal empresa",
                           "valor titular empresa", "mensalidade empresa", "mensal empresa",
                           "custo empresa", "custo patronal"),
        "vlr_func":    col("vlr_func",
                           "valor beneficiario", "valor beneficário", "valor. beneficário", "vlr beneficiario", "beneficiario", "beneficiário",
                           "valor funcionario", "vlr funcionario",
                           "vl. beneficiario", "func ps", "val funcionario",
                           "val. funcionario", "valor mensal funcionario",
                           "mensalidade funcionario", "mensal funcionario",
                           "custo funcionario", "desconto funcionario", "desconto beneficiario"),
        "tipo":        col("tipo",
                           "tipo", "categoria", "vinculo", "vínculo", "grau",
                           "tp beneficiario", "tipo beneficiario", "tipo de beneficiario",
                           "titular dependente", "tp"),
    }

    tem_col_tipo = c["tipo"] is not None

    linhas: dict = {}       # _norm_titular → acumulador
    cod_to_norm: dict = {}  # cod_func → _norm_titular (para casar dependentes pelo código)
    ultimo_norm: str | None = None  # último titular visto (fallback quando não há cod_func)

    for _, row in df.iterrows():
        func = _str(row.get(c["funcionario"]) if c["funcionario"] else "")
        if not func or _norm(func) in ("FUNCIONARIO", "NOME", "COLABORADOR", "EMPREGADO", "TITULAR"):
            continue

        norm    = _norm(func)
        vlr_emp = _parse_brl(row.get(c["vlr_empresa"]) if c["vlr_empresa"] else 0)
        vlr_fun = _parse_brl(row.get(c["vlr_func"])    if c["vlr_func"]    else 0)
        cod     = _str(row.get(c["cod_func"]) if c["cod_func"] else "")

        # Detecta se a linha é de dependente
        eh_dependente = False
        if tem_col_tipo:
            tipo_raw = _norm(_str(row.get(c["tipo"]) or ""))
            eh_dependente = "DEPEND" in tipo_raw or tipo_raw in ("D", "DEP")

        if eh_dependente:
            # Acumula no titular: primeiro pelo cod_func, depois pelo último visto
            alvo = cod_to_norm.get(cod) if cod else None
            if alvo is None:
                alvo = ultimo_norm
            if alvo and alvo in linhas:
                linhas[alvo]["vlr_empresa"] += vlr_emp
                linhas[alvo]["vlr_func"]    += vlr_fun
            # Dependente nunca vira linha autônoma — ignorado se titular não encontrado
            continue

        # Linha de titular
        if norm not in linhas:
            linhas[norm] = {
                "cod_func_compra": cod,
                "nome_compra":     func,
                "_norm_compra":    norm,
                "vlr_empresa":     0.0,
                "vlr_func":        0.0,
            }
        linhas[norm]["vlr_empresa"] += vlr_emp
        linhas[norm]["vlr_func"]    += vlr_fun

        if cod:
            cod_to_norm[cod] = norm
        ultimo_norm = norm

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
            "vlr_empresa":      round(d["vlr_empresa"], 2),
            "vlr_func":         round(d["vlr_func"],    2),
            "vlr_compra_total": round(d["vlr_empresa"] + d["vlr_func"], 2),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _dt_ref_periodo(periodo: str):
    """Retorna o primeiro dia do mês de referência da auditoria (ex: '04/2026' → 2026-04-01)."""
    try:
        partes = str(periodo or "").strip().split("/")
        mes = int(partes[0])
        ano = int(partes[1])
        if ano < 100:
            ano += 2000
        return pd.Timestamp(year=ano, month=mes, day=1)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Matching por nome
# ---------------------------------------------------------------------------

def _match_nome(nome_a: str, nomes_b: list, threshold=0.72) -> Optional[int]:
    if not nome_a or not nomes_b:
        return None

    tokens_a = [t for t in str(nome_a).split() if t]
    primeiro_a = tokens_a[0] if tokens_a else ""
    best_i, best_s = None, 0.0
    for i, nb in enumerate(nomes_b):
        tokens_b = [t for t in str(nb).split() if t]
        primeiro_b = tokens_b[0] if tokens_b else ""
        s = difflib.SequenceMatcher(None, nome_a, nb).ratio()

        # Evita falso positivo entre pessoas com apenas o último sobrenome parecido.
        if primeiro_a and primeiro_b and primeiro_a != primeiro_b and s < 0.85:
            continue

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

    dt_ref = _dt_ref_periodo(periodo)   # primeiro dia do mês de referência (para regra dos 90 dias)

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

        # ── Regra dos 90 dias ──────────────────────────────────────────────
        copart_apos_exp = bool(cont.get("copart_apos_exp", False))
        aguarda_elegib  = False
        data_elegib_str = ""
        if copart_apos_exp and dt_ref:
            adm_str = str(cont.get("admissao", "")).strip()
            if adm_str and adm_str not in ("", "nan"):
                dt_adm = pd.to_datetime(adm_str, dayfirst=True, errors="coerce")
                if not pd.isna(dt_adm):
                    dt_elegib = dt_adm + pd.Timedelta(days=90)
                    data_elegib_str = dt_elegib.strftime("%d/%m/%Y")
                    aguarda_elegib = dt_elegib > dt_ref

        tem_dir_efetivo = cont["tem_direito"]
        if copart_apos_exp and aguarda_elegib:
            tem_dir_efetivo = False   # ainda em experiência → sem direito no período

        resultado.append({
            "Funcionário":        cont["funcionario"],
            "Empresa":            cont.get("empresa", ""),
            "Departamento":       cont["departamento"],
            "Contrato Adm.":      cont.get("contrato_adm", ""),
            "Cod. Funcionário":   cont["cod_func"],
            "Tem Direito":        "Sim" if tem_dir_efetivo else "Não",
            "Está na Fatura":     "Sim" if na_fatura else "Não",
            "Está na Compra":     "Sim" if na_compra else "Não",
            "Valor Fatura":       vlr_fat,
            "Valor Empresa (Compra)": vlr_emp,      # comparar com contrato
            "Valor Compra Total": vlr_comp_tot,     # comparar com fatura
            "Valor Contrato":     cont["vlr_contrato"],
            "Dif. Contrato x Compra": round(max(vlr_emp - cont["vlr_contrato"], 0.0), 2),
            "Dif. Fatura x Compra":   round(vlr_fat - vlr_comp_tot, 2),
            "Data Inclusão":      data_inc,
            "_vlr_mensalidade_fat": vlr_mens_fat,
            "_vlr_dependente_fat":  float(fat["vlr_dependente"]) if na_fatura else 0.0,
            "_vlr_copart_fat":      vlr_copart_fat,
            "Dt. Admissão":       cont.get("admissao", ""),
            "Dt. Demissão":       demissao,
            "Dt. Elegibilidade":  data_elegib_str,
            "Período":            periodo,
            "_na_fatura":             na_fatura,
            "_na_compra":             na_compra,
            "_desligado":             desligado,
            "_sem_contrato":          False,
            "_inelegivel_contrato":   bool(cont.get("inelegivel_contrato", False)),
            "_anatacha_especial":     nome_c == _ANATACHA_NORM,
            "_aguarda_elegibilidade": aguarda_elegib,
            "_copart_apos_exp":       copart_apos_exp,
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
            "Empresa":                "",
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
            "_vlr_mensalidade_fat":   float(fat["vlr_mensalidade"]),
            "_vlr_dependente_fat":    float(fat["vlr_dependente"]),
            "_vlr_copart_fat":        float(fat["vlr_copart"]),
            "Dt. Admissão":           "",
            "Dt. Demissão":           "",
            "Dt. Elegibilidade":      "",
            "Período":                periodo,
            "_na_fatura":             True,
            "_na_compra":             comp is not None,
            "_desligado":             False,
            "_sem_contrato":          True,
            "_anatacha_especial":     False,
            "_aguarda_elegibilidade": False,
            "_copart_apos_exp":       False,
        })

    # ── 3. Na compra mas sem contrato e sem fatura ──────────────────────────
    for i, comp in df_compra.iterrows():
        if i in compra_usadas:
            continue
        resultado.append({
            "Funcionário":            comp["nome_compra"],
            "Empresa":                "",
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
            "_vlr_mensalidade_fat":   0.0,
            "_vlr_dependente_fat":    0.0,
            "_vlr_copart_fat":        0.0,
            "Dt. Admissão":           "",
            "Dt. Demissão":           "",
            "Dt. Elegibilidade":      "",
            "Período":                periodo,
            "_na_fatura":             False,
            "_na_compra":             True,
            "_desligado":             False,
            "_sem_contrato":          True,
            "_anatacha_especial":     False,
            "_aguarda_elegibilidade": False,
            "_copart_apos_exp":       False,
        })

    return pd.DataFrame(resultado)
