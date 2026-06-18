# -*- coding: utf-8 -*-
"""
Regras de auditoria Unimed.
"""
import pandas as pd


def _parse_periodo(periodo: str) -> tuple[int, int] | tuple[None, None]:
    s = str(periodo or "").strip()
    if "/" not in s:
        return None, None

    try:
        mes_txt, ano_txt = [p.strip() for p in s.split("/", 1)]
        mes = int(mes_txt)
        ano = int(ano_txt)
    except ValueError:
        return None, None

    if not 1 <= mes <= 12:
        return None, None

    if ano < 100:
        ano += 2000

    return mes, ano


def aplicar_regras(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()

    if {"Valor Empresa (Compra)", "Valor Contrato"}.issubset(df.columns):
        df["Dif. Contrato x Compra"] = df.apply(
            lambda row: round(
                max(
                    float(row.get("Valor Empresa (Compra)", 0) or 0)
                    - float(row.get("Valor Contrato", 0) or 0),
                    0.0,
                ),
                2,
            ),
            axis=1,
        )

    if {"Valor Fatura", "Valor Compra Total", "_na_fatura", "_na_compra"}.issubset(df.columns):
        df["Dif. Fatura x Compra"] = df.apply(
            lambda row: round(
                abs(
                    float(row.get("Valor Fatura", 0) or 0)
                    - float(row.get("Valor Compra Total", 0) or 0)
                ),
                2,
            ) if bool(row.get("_na_fatura", False)) and bool(row.get("_na_compra", False)) else 0.0,
            axis=1,
        )

    status_list, desc_list, acao_list, tipo_list = [], [], [], []

    for _, row in df.iterrows():
        # Inelegível = sem direito por regra contratual/departamental.
        # Se não tem cobrança → OK.  Se tem cobrança → divergência obrigatória.
        if bool(row.get("_inelegivel_contrato", False)):
            _na_fat = bool(row.get("_na_fatura", False))
            _na_cmp = bool(row.get("_na_compra", False))
            if _na_fat or _na_cmp:
                _partes = []
                if _na_fat:
                    _partes.append("cobrança na fatura Unimed")
                if _na_cmp:
                    _partes.append("lançamento no sistema de compra")
                status_list.append("Inconsistente")
                desc_list.append(
                    "Sem elegibilidade ao plano de saúde conforme regras contratuais/departamento"
                    f" — {' e '.join(_partes)} indevido(s)"
                )
                acao_list.append(
                    "Verificar e solicitar exclusão do plano conforme modalidade contratual"
                )
                tipo_list.append("Sem elegibilidade (contrato/departamento)")
            else:
                status_list.append("OK")
                desc_list.append("")
                acao_list.append("")
                tipo_list.append("")
            continue

        # Funcionário em período de experiência (< 90 dias da admissão)
        if bool(row.get("_aguarda_elegibilidade", False)):
            _na_fat = bool(row.get("_na_fatura", False))
            _na_cmp = bool(row.get("_na_compra", False))
            dt_eleg = str(row.get("Dt. Elegibilidade", "") or "")
            eleg_txt = f", elegível em {dt_eleg}" if dt_eleg else ""
            if _na_fat or _na_cmp:
                _partes = []
                if _na_fat:
                    _partes.append("cobrança na fatura Unimed")
                if _na_cmp:
                    _partes.append("lançamento no sistema de compra")
                status_list.append("Inconsistente")
                desc_list.append(
                    f"Em período de experiência{eleg_txt}"
                    f" — {' e '.join(_partes)} indevido(s)"
                )
                acao_list.append("Remover do plano até completar 90 dias da admissão")
                tipo_list.append("Período de experiência")
            else:
                status_list.append("OK")
                desc_list.append("")
                acao_list.append("")
                tipo_list.append("")
            continue

        tem_direito  = str(row.get("Tem Direito", "Não"))
        na_fatura    = bool(row.get("_na_fatura", False))
        na_compra    = bool(row.get("_na_compra", False))
        desligado    = bool(row.get("_desligado", False))
        sem_contrato = bool(row.get("_sem_contrato", False))
        vlr_fat      = float(row.get("Valor Fatura", 0) or 0)
        vlr_emp      = float(row.get("Valor Empresa (Compra)", 0) or 0)   # empresa vs contrato
        vlr_comp_tot = float(row.get("Valor Compra Total", 0) or 0)       # total vs fatura
        vlr_cont     = float(row.get("Valor Contrato", 0) or 0)

        inc = []
        acoes = []
        tipos = []

        # R1 — Tem direito e não está na fatura
        if tem_direito == "Sim" and not na_fatura and not desligado:
            inc.append("Tem direito ao plano mas não consta na fatura Unimed")
            acoes.append("Verificar inclusão junto à Unimed")
            tipos.append("Direito sem fatura")

        # R2 — Tem direito, está na fatura, mas não está na compra
        if tem_direito == "Sim" and na_fatura and not na_compra:
            inc.append("Consta na fatura mas não há lançamento de compra")
            acoes.append("Lançar a compra no sistema")
            tipos.append("Fatura sem compra")

        # R3 — Não tem direito e está na fatura
        if tem_direito == "Não" and na_fatura:
            inc.append("Sem valor previsto no contrato mas consta na fatura")
            acoes.append("Verificar se valor do plano está preenchido no contrato")
            tipos.append("Sem direito mas na fatura")

        # R4 — Na compra mas não na fatura
        if na_compra and not na_fatura:
            inc.append("Lançado na compra mas não consta na fatura Unimed")
            acoes.append("Verificar se lançamento é indevido ou se fatura está incompleta")
            tipos.append("Compra sem fatura")

        # R5 — Valor empresa (compra) vs contrato
        # Para ANATACHA: empresa cobre mensalidade titular + dependentes (não só o contrato titular).
        # Usamos comparação especial; para os demais, comparação padrão empresa vs contrato.
        anatacha = bool(row.get("_anatacha_especial", False))
        if anatacha and na_fatura and na_compra:
            vlr_mens_fat = float(row.get("_vlr_mensalidade_fat", 0) or 0)
            vlr_dep_fat  = float(row.get("_vlr_dependente_fat",  0) or 0)
            vlr_cop_fat  = float(row.get("_vlr_copart_fat",      0) or 0)
            esperado_emp = round(vlr_mens_fat + vlr_dep_fat, 2)
            vlr_func_cmp = round(vlr_comp_tot - vlr_emp, 2)
            if abs(vlr_emp - esperado_emp) > 0.10:
                inc.append(
                    f"ANATACHA — compra empresa (R$ {vlr_emp:.2f}) difere das mensalidades "
                    f"titular+dependentes na fatura (R$ {esperado_emp:.2f})"
                )
                acoes.append("Ajustar compra empresa para cobrir mensalidade titular + dependentes")
                tipos.append("ANATACHA — mensalidade")
            if vlr_cop_fat > 0 and abs(vlr_func_cmp - vlr_cop_fat) > 0.10:
                inc.append(
                    f"ANATACHA — compra funcionária (R$ {vlr_func_cmp:.2f}) difere da "
                    f"coparticipação na fatura (R$ {vlr_cop_fat:.2f})"
                )
                acoes.append("Ajustar compra funcionária para cobrir apenas coparticipações")
                tipos.append("ANATACHA — coparticipação")
        elif not anatacha and na_compra and vlr_cont > 0 and vlr_emp > 0:
            dif_cont = vlr_emp - vlr_cont
            if dif_cont > 0.10:
                inc.append(
                    f"Valor empresa na compra (R$ {vlr_emp:.2f}) difere do contrato "
                    f"(R$ {vlr_cont:.2f}) — diferença R$ {dif_cont:.2f}"
                )
                acoes.append("Ajustar valor da compra empresa para coincidir com o contrato")
                tipos.append("Valor empresa ≠ contrato")

        # R6 — Total compra (titular + dependentes) difere da fatura
        if na_fatura and na_compra and vlr_fat > 0 and vlr_comp_tot > 0:
            dif_fat = abs(vlr_fat - vlr_comp_tot)
            if dif_fat > 0.10:
                inc.append(
                    f"Total da compra (R$ {vlr_comp_tot:.2f}) difere da fatura "
                    f"(R$ {vlr_fat:.2f}) — diferença R$ {dif_fat:.2f}"
                )
                acoes.append("Verificar lançamentos de titular e dependentes na compra")
                tipos.append("Total compra ≠ fatura")

        # R7 — Funcionário desligado sendo cobrado
        if desligado and na_fatura:
            inc.append("Funcionário desligado consta na fatura")
            acoes.append("Solicitar exclusão retroativa à Unimed")
            tipos.append("Desligado na fatura")

        # R8 — Sem correspondência no contrato
        if sem_contrato and na_fatura:
            inc.append("Consta na fatura sem correspondência na planilha de contratos")
            acoes.append("Verificar vínculo empregatício")
            tipos.append("Sem correspondência no contrato")

        if inc:
            status_list.append("Inconsistente")
            desc_list.append(" | ".join(inc))
            acao_list.append(" | ".join(acoes))
            tipo_list.append(" | ".join(tipos))
        else:
            status_list.append("OK")
            desc_list.append("")
            acao_list.append("")
            tipo_list.append("")

    df["Status"]            = status_list
    df["Inconsistência"]    = desc_list
    df["Ação Sugerida"]     = acao_list
    df["Tipo Inconsistência"] = tipo_list
    return df


def identificar_duplicatas_fatura(df_fat: pd.DataFrame) -> pd.DataFrame:
    if df_fat.empty or "_norm_fatura" not in df_fat.columns:
        return pd.DataFrame()
    return df_fat[df_fat["_norm_fatura"].duplicated(keep=False)].copy()


def identificar_incluidos_mes(df: pd.DataFrame, periodo: str) -> pd.DataFrame:
    if df.empty or "Data Inclusão" not in df.columns or not periodo:
        return pd.DataFrame()

    mes, ano = _parse_periodo(periodo)
    if mes is None or ano is None:
        return pd.DataFrame()

    def eh_do_mes(dt_str):
        s = str(dt_str or "").strip()
        if not s:
            return False
        dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if pd.isna(dt):
            dt = pd.to_datetime(s, errors="coerce")
        return not pd.isna(dt) and dt.month == mes and dt.year == ano

    return df[df["Data Inclusão"].apply(eh_do_mes)].copy()


def calcular_stats(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    return {
        "total":          len(df),
        "ok":             int((df["Status"] == "OK").sum()),
        "inconsistente":  int((df["Status"] == "Inconsistente").sum()),
        "na_fatura":      int(df["_na_fatura"].sum()) if "_na_fatura" in df else 0,
        "na_compra":      int(df["_na_compra"].sum()) if "_na_compra" in df else 0,
        "total_fatura":   float(df["Valor Fatura"].sum()) if "Valor Fatura" in df else 0.0,
        "total_compra":   float(df["Valor Compra Total"].sum()) if "Valor Compra Total" in df else 0.0,
        "total_contrato": float(df["Valor Contrato"].sum()) if "Valor Contrato" in df else 0.0,
    }
