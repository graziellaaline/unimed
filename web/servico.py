# -*- coding: utf-8 -*-
"""O trabalho das telas, sem tela: o que estava espalhado nas páginas do Streamlit e não era
desenho. As regras e o cálculo continuam em app/ (processamento, regras, db), sem mudança."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from app import db
from app.exportacao import exportar_excel
from app.processamento import cruzar, ler_compra, ler_contratos, ler_faturas_csv, mesclar_desligados
from app.regras import aplicar_regras, calcular_stats, identificar_incluidos_mes
from web import estado

# ── Importação (antes: pages/1_Importação.py) ────────────────────────────────
ETAPAS = ["Lendo contratos", "Lendo faturas", "Lendo compra", "Cruzando contrato, fatura e compra",
          "Mesclando desligados", "Aplicando regras", "Salvando no histórico",
          "Trazendo justificativas da auditoria anterior"]


def processar(periodo, cliente, p_cont, p_fats, p_comp, p_desl=None, etapa=lambda _f: None):
    mc = db.carregar_mapeamento(cliente, "contratos") if cliente else {}
    mf = db.carregar_mapeamento(cliente, "fatura") if cliente else {}
    mcp = db.carregar_mapeamento(cliente, "compra") if cliente else {}

    etapa(ETAPAS[0])
    df_cont = ler_contratos(p_cont, mc)
    etapa(ETAPAS[1])
    df_fat = ler_faturas_csv(p_fats, mf) if p_fats else pd.DataFrame()
    etapa(ETAPAS[2])
    df_compra = ler_compra(p_comp, mcp) if p_comp else pd.DataFrame()
    if df_cont.empty:
        raise ValueError("Não foi possível ler a planilha de contratos. Verifique o arquivo.")

    etapa(ETAPAS[3])
    df_cruzado = cruzar(df_cont, df_fat, df_compra, periodo)

    # a planilha de inativos tem a mesma estrutura da de ativos — lida com ler_contratos
    df_desl, relatorio = None, {}
    etapa(ETAPAS[4])
    if p_desl:
        df_desl = ler_contratos(p_desl)
        df_cruzado, relatorio = mesclar_desligados(df_cruzado, df_desl, periodo)

    etapa(ETAPAS[5])
    df_audit = aplicar_regras(df_cruzado)
    stats = calcular_stats(df_audit)
    etapa(ETAPAS[6])
    aid = db.salvar_auditoria(df_audit, stats, periodo, cliente)
    # herdar justificativas da auditoria anterior — nunca perder aprovações ao reprocessar
    etapa(ETAPAS[7])
    db.migrar_justificativas(aid, periodo, cliente)

    if cliente:
        db.salvar_mapeamento(cliente, "contratos", mc)
        if p_fats:
            db.salvar_mapeamento(cliente, "fatura", mf)
        if p_comp:
            db.salvar_mapeamento(cliente, "compra", mcp)
    estado.esquecer()
    return {"aid": aid, "stats": stats, "relatorio": relatorio,
            "n_inc": len(identificar_incluidos_mes(df_audit, periodo)),
            "n_desl": 0 if df_desl is None or df_desl.empty else len(df_desl)}


def caminhos_salvos(arqs: dict):
    """(contratos, [faturas], compra, desligados) dos arquivos guardados de uma auditoria."""
    def um(k):
        item = (arqs.get(k) or [None])[0]
        return item.get("caminho") if isinstance(item, dict) else None
    return um("contratos"), [x["caminho"] for x in arqs.get("fatura", [])], um("compra"), um("desligados")


def regravar_arquivos(aid, arqs: dict) -> None:
    db.salvar_arquivos_auditoria(aid, {
        k: [{"nome": Path(x["caminho"]).name, "origem": x["caminho"]} for x in arqs.get(k, [])]
        for k in ("contratos", "fatura", "compra", "desligados")})


def reprocessar(periodo, cliente, arqs: dict, etapa=lambda _f: None) -> dict:
    p_cont, p_fats, p_comp, p_desl = caminhos_salvos(arqs)
    if not p_cont:
        raise ValueError("Esta auditoria não tem a planilha de contratos guardada. Importe os arquivos de novo.")
    r = processar(periodo, cliente, p_cont, p_fats, p_comp, p_desl, etapa)
    regravar_arquivos(r["aid"], arqs)
    return r


def limpar_temporarios(caminhos) -> None:
    for p in caminhos:
        try:
            if p:
                os.unlink(p)
        except OSError:
            pass


# ── Auditoria e Aprovação (antes: pages/5_Auditoria_e_Aprovação.py) ──────────
# Ordem FIXA da tabela — a que a Graziella arrumou; arrastar o cabeçalho grava outra em disco.
COLS = [
    "Empresa", "Justificado", "Status", "Funcionário", "Departamento",
    "Contrato Adm.", "Tipo Inconsistência", "Justificativa",
    "Dt. Admissão", "Dt. Demissão", "Dt. Elegibilidade",
    "Tem Direito", "Está na Fatura", "Está na Compra",
    "Valor Contrato", "Valor Empresa (Compra)", "Valor Fatura", "Valor Compra Total",
    "Dif. Fatura x Contrato", "Dif. Contrato x Compra", "Dif. Fatura x Compra",
    "Data Inclusão", "Inconsistência", "Ação Sugerida",
]
MOEDA = ("Valor Contrato", "Valor Empresa (Compra)", "Valor Fatura", "Valor Compra Total",
         "Dif. Fatura x Contrato", "Dif. Contrato x Compra", "Dif. Fatura x Compra")
DATAS = ("Dt. Admissão", "Dt. Demissão", "Dt. Elegibilidade", "Data Inclusão")


def _aid(meta) -> int | None:
    aid = (meta or {}).get("id")
    if aid and not db.carregar_justificativas(aid):
        db.migrar_justificativas(aid, meta["periodo"], meta.get("cliente", ""))
    return aid


def justificativas(meta) -> dict:
    """Com dupla busca: pelo id da auditoria e, sem nada, pelo período (cliente em branco)."""
    aid = (meta or {}).get("id")
    r = db.carregar_justificativas(aid) if aid else {}
    if not r and meta and meta.get("periodo"):
        _, r = db.carregar_justificativas_por_periodo(meta["periodo"], "")
    return r


def aplicar_modelos(meta, pendentes: pd.DataFrame) -> int:
    """Justificativa-modelo de meses anteriores (mesmo funcionário + mesma inconsistência)."""
    aid, cliente = _aid(meta), meta.get("cliente", "")
    atuais = justificativas(meta)
    n = 0
    for _, row in pendentes.iterrows():
        func, desc = str(row.get("Funcionário", "")), str(row.get("Inconsistência", ""))
        if atuais.get(func, "").strip():
            continue
        modelo = db.carregar_justificativa_modelo(cliente, func, desc)
        if modelo and aid:
            db.salvar_justificativa(aid, func, desc, modelo)
            n += 1
    return n


def aprovacao(sel):
    """O que a tela 5 mostra: df com Justificado/Justificativa, números e pendências."""
    df, stats, meta = estado.carregar(sel)
    if df is None:
        return None
    _aid(meta)
    pend = df[df["Status"] == "Inconsistente"].copy() if "Status" in df.columns else pd.DataFrame()
    aplicar_modelos(meta, pend)
    just = justificativas(meta)
    df["Justificado"] = df["Funcionário"].map(lambda f: "Sim" if just.get(f, "").strip() else "Não")
    df["Justificativa"] = df["Funcionário"].map(lambda f: just.get(f, "") or "")
    funcs_pend = pend["Funcionário"].astype(str).tolist() if not pend.empty else []
    n_inc = stats.get("inconsistente", len(funcs_pend))
    n_just = sum(1 for f in funcs_pend if just.get(f, "").strip())
    tab = df[[c for c in COLS if c in df.columns]].copy().reset_index(drop=True)
    for c in MOEDA:
        if c in tab.columns:
            tab[c] = pd.to_numeric(tab[c], errors="coerce")
    for c in DATAS:
        if c in tab.columns:
            limpo = tab[c].astype(str).str.strip().replace({"nan": "", "None": "", "NaT": "", "none": "", "NAT": ""})
            tab[c] = pd.to_datetime(limpo, dayfirst=True, errors="coerce")
    tab["_id"] = tab.index.astype(str)
    return {"df": df, "tab": tab, "stats": stats, "meta": meta, "pend": pend, "just": just,
            "n_inc": n_inc, "n_just": n_just, "n_pend": n_inc - n_just, "n_funcs_pend": len(funcs_pend)}


def descricao(pend: pd.DataFrame, func: str) -> str:
    linha = pend[pend["Funcionário"].astype(str) == func]
    return str(linha["Inconsistência"].iloc[0]) if not linha.empty else ""


def gravar_justificativa(meta, pend, func: str, texto: str, modelo: bool) -> str:
    """'salva' | 'revertida' | '' (nada mudou)."""
    aid = _aid(meta)
    texto = (texto or "").strip()
    antes = justificativas(meta).get(func, "").strip()
    if antes and not texto:
        db.excluir_justificativa(aid, func)
        return "revertida"
    if texto and texto != antes:
        desc = descricao(pend, func)
        db.salvar_justificativa(aid, func, desc, texto)
        if modelo:
            db.salvar_justificativa_modelo(meta.get("cliente", ""), func, desc, texto)
        return "salva"
    return ""


def justificar_lote(meta, pend, funcs: list, texto: str, modelo: bool) -> int:
    aid = _aid(meta)
    for func in funcs:
        desc = descricao(pend, func)
        db.salvar_justificativa(aid, func, desc, texto.strip())
        if modelo:
            db.salvar_justificativa_modelo(meta.get("cliente", ""), func, desc, texto.strip())
    return len(funcs)


def excel_completo(dados) -> bytes:
    df, meta, just, pend = dados["df"], dados["meta"], dados["just"], dados["pend"]
    df_inc = identificar_incluidos_mes(df, meta["periodo"])
    df_just = pd.DataFrame([{"Funcionário": f, "Inconsistência": descricao(pend, f), "Justificativa": j}
                            for f, j in just.items()]) if just else pd.DataFrame()
    return exportar_excel(df, df_inc, df_just, meta["periodo"])


# ── Inclusões (antes: pages/2_Inclusões.py) ──────────────────────────────────
def _norm(s) -> str:
    import unicodedata
    txt = str(s or "").strip().upper()
    nfkd = unicodedata.normalize("NFKD", txt)
    return " ".join("".join(c for c in nfkd if not unicodedata.combining(c)).split())


def periodo_anterior(periodo: str) -> str:
    """O período imediatamente anterior (05/2026 → 04/2026)."""
    try:
        mes, ano = (int(x) for x in str(periodo).strip().split("/")[:2])
        if ano < 100:
            ano += 2000
        return f"12/{ano - 1}" if mes == 1 else f"{mes - 1:02d}/{ano}"
    except Exception:       # noqa: BLE001
        return ""


COLS_INC = ["Funcionário", "Empresa", "Departamento", "Contrato Adm.", "Dt. Admissão", "Data Inclusão",
            "Valor Fatura", "Valor Contrato", "Tem Direito", "Origem"]


def inclusoes(sel):
    from app.processamento import indice_titulares, localizar_titular
    df, _stats, meta = estado.carregar(sel)
    if df is None:
        return None
    periodo, cliente = meta["periodo"], meta.get("cliente", "")
    # critério 1: Data Inclusão da fatura coincide com o período
    df_inc_fat = identificar_incluidos_mes(df, periodo)
    # critério 2: titulares novos vs período anterior (casa por matrícula antes do nome —
    # sem isso, quem muda de nome entra como "novo titular" todo mês)
    ant = periodo_anterior(periodo)
    df_novos, info_ant = pd.DataFrame(), ""
    if ant:
        df_ant, _, _ = db.carregar_auditoria(ant, cliente)
        if df_ant is not None and not df_ant.empty:
            df_ant = aplicar_regras(df_ant)
            idx_ant = indice_titulares(df_ant[df_ant["_na_fatura"].astype(bool)])
            atual = df[df["_na_fatura"].astype(bool)].copy()
            novo = pd.Series([not localizar_titular(r, idx_ant)[0] for _, r in atual.iterrows()], index=atual.index)
            df_novos, info_ant = atual[novo].copy(), ant
        else:
            info_ant = None
    ja = set(_norm(n) for n in df_inc_fat["Funcionário"]) if not df_inc_fat.empty else set()
    if not df_inc_fat.empty:
        df_inc_fat = df_inc_fat.copy()
        df_inc_fat["Origem"] = "Inclusão no mês (Data Inclusão = " + periodo + ")"
    if not df_novos.empty:
        extra = df_novos[df_novos["Funcionário"].apply(lambda n: _norm(n) not in ja)].copy()
        extra["Origem"] = f"Novo titular (ausente em {info_ant})"
    else:
        extra = pd.DataFrame()
    todos = pd.concat([df_inc_fat, extra], ignore_index=True)
    # quem já está desligado não é inclusão — é cobrança de quem saiu (tela 4)
    desl = pd.DataFrame()
    if not todos.empty and "_desligado" in todos.columns:
        m = todos["_desligado"].astype(bool)
        desl, todos = todos[m].copy(), todos[~m].copy()
    tab = todos[[c for c in COLS_INC if c in todos.columns]].copy().reset_index(drop=True)
    for c in ("Valor Fatura", "Valor Contrato"):
        if c in tab.columns:
            tab[c] = pd.to_numeric(tab[c], errors="coerce")
    for c in ("Dt. Admissão", "Data Inclusão"):
        if c in tab.columns:
            limpo = tab[c].astype(str).str.strip().replace({"nan": "", "None": "", "NaT": "", "none": "", "NAT": ""})
            tab[c] = pd.to_datetime(limpo, dayfirst=True, errors="coerce")
    return {"df": df, "meta": meta, "todos": todos.reset_index(drop=True), "tab": tab, "desl": desl,
            "n_c1": len(df_inc_fat), "n_c2": len(extra), "ant": ant, "info_ant": info_ant}


def texto_descricao(todos: pd.DataFrame, nomes_visiveis, tipo: str, col_data: str) -> str:
    """O texto para colar acompanha o que está filtrado na tela."""
    from app.exportacao import exportar_descricoes_unimed
    df_f = todos
    if nomes_visiveis is not None and "Funcionário" in todos.columns and len(nomes_visiveis) < len(todos):
        df_f = todos[todos["Funcionário"].isin(nomes_visiveis)]
    return exportar_descricoes_unimed(df_f, tipo, col_data) or ""


def excel_inclusoes(d) -> bytes:
    aid = d["meta"].get("id")
    j = db.carregar_justificativas(aid) if aid else {}
    df_just = pd.DataFrame([{"Funcionário": f, "Justificativa": t} for f, t in j.items()]) if j else pd.DataFrame()
    return exportar_excel(d["df"], d["todos"], df_just, d["meta"]["periodo"])


# ── Exclusões (antes: pages/3_Exclusões.py) ──────────────────────────────────
def _na_fatura(df: pd.DataFrame) -> pd.DataFrame:
    if "Está na Fatura" in df.columns:
        return df[df["Está na Fatura"] == "Sim"].copy()
    if "_na_fatura" in df.columns:
        return df[df["_na_fatura"].astype(bool)].copy()
    return pd.DataFrame()


def _so_conta_medica(row) -> bool:
    """Só coparticipação na fatura anterior: resíduo de atendimento, não exclusão de plano."""
    return (float(row.get("_vlr_mensalidade_fat", 0) or 0) <= 0
            and float(row.get("_vlr_dependente_fat", 0) or 0) <= 0
            and float(row.get("_vlr_copart_fat", 0) or 0) > 0)


def _composicao(row) -> str:
    partes = []
    if float(row.get("_vlr_mensalidade_fat", 0) or 0) > 0:
        partes.append("Mensalidade")
    if float(row.get("_vlr_dependente_fat", 0) or 0) > 0:
        partes.append("Dependentes")
    if float(row.get("_vlr_copart_fat", 0) or 0) > 0:
        partes.append("Coparticipação")
    return " + ".join(partes) if partes else "—"


def _enriquecer_com_inativos(df_exc: pd.DataFrame, df_inat: pd.DataFrame) -> pd.DataFrame:
    """Quem só aparece na fatura (sem contrato ativo) ganha empresa/departamento dos inativos."""
    from app.processamento import _norm as norm_proc
    if df_inat.empty or df_exc.empty:
        return df_exc
    por_mat, por_nome = {}, {}
    for _, ir in df_inat.iterrows():
        cod, nn = str(ir.get("cod_func", "") or "").strip(), str(ir.get("_norm_func", "") or "").strip()
        if cod and nn:
            por_mat[(cod, nn)] = ir
        if nn:
            por_nome[nn] = ir
    campos = [("Empresa", "empresa"), ("Departamento", "departamento"), ("Contrato Adm.", "contrato_adm"),
              ("Dt. Admissão", "admissao"), ("Dt. Demissão", "demissao")]
    for idx, row in df_exc.iterrows():
        cod, nn = str(row.get("Cod. Funcionário", "") or "").strip(), norm_proc(str(row.get("Funcionário", "") or ""))
        ir = por_mat.get((cod, nn))
        if ir is None:
            ir = por_nome.get(nn)
        if ir is None:
            continue
        for ca, ci in campos:
            if ca in df_exc.columns:
                val, cur = str(ir.get(ci, "") or "").strip(), str(row.get(ca, "") or "").strip()
                if val and val.lower() not in ("nan", "none") and not cur:
                    df_exc.at[idx, ca] = val
    return df_exc


def periodos_para_comparar(sel) -> list:
    _df, _s, meta = estado.carregar(sel)
    return [p for p in db.listar_periodos() if p["periodo"] != (meta or {}).get("periodo")]


def exclusoes(sel, periodo_ant: str | None = None, inativos_extra: str | None = None):
    from app.processamento import _norm as norm_proc, indice_titulares, ler_contratos, localizar_titular
    df, _stats, meta = estado.carregar(sel)
    if df is None:
        return None
    periodo = meta["periodo"]
    opcoes = periodos_para_comparar(sel)
    base = {"meta": meta, "opcoes": opcoes, "ant": None}
    if not opcoes:
        return {**base, "erro": "Não há períodos anteriores salvos para comparar. Processe ao menos dois meses."}
    info = next((p for p in opcoes if p["periodo"] == periodo_ant), opcoes[0])
    ant = info["periodo"]
    df_ant, _, _ = db.carregar_auditoria(ant, info["cliente"])
    if df_ant is None or df_ant.empty:
        return {**base, "ant": ant, "erro": f"Não foi possível carregar os dados de {ant}."}
    fat_atual, fat_ant = _na_fatura(df), _na_fatura(df_ant)
    if fat_ant.empty:
        return {**base, "ant": ant, "erro": f"Não há titulares na fatura registrados para {ant}."}
    # quem do mês anterior não foi localizado agora = exclusão (matrícula antes do nome)
    idx = indice_titulares(fat_atual)
    achados = [localizar_titular(r, idx) for _, r in fat_ant.iterrows()]
    df_exc = fat_ant[pd.Series([not ok for ok, _ in achados], index=fat_ant.index)].copy()
    renomeados = [(str(r.get("Funcionário", "")), reg["nome"])
                  for (ok, reg), (_, r) in zip(achados, fat_ant.iterrows())
                  if ok and reg and norm_proc(str(reg["nome"] or "")) != norm_proc(str(r.get("Funcionário", "") or ""))]
    # inativos: arquivo guardado da auditoria atual ou o que foi enviado nesta tela
    df_inat = pd.DataFrame()
    item = (db.carregar_arquivos_auditoria(meta["id"]).get("desligados") or [None])[0]
    for caminho in (inativos_extra, item.get("caminho") if item else None):
        if caminho and df_inat.empty:
            try:
                df_inat = ler_contratos(caminho)
            except Exception:      # noqa: BLE001
                pass
    df_exc = _enriquecer_com_inativos(df_exc, df_inat)
    sem_dados = int(df_exc["Empresa"].astype(str).str.strip().isin(["", "nan", "None"]).sum()) if not df_exc.empty else 0
    df_copart = pd.DataFrame()
    if not df_exc.empty:
        m = df_exc.apply(_so_conta_medica, axis=1)
        df_copart, df_exc = df_exc[m].copy(), df_exc[~m].copy()
    if not df_exc.empty:
        df_exc["Composição da Cobrança"] = df_exc.apply(_composicao, axis=1)
    cols = ["Funcionário", "Empresa", "Departamento", "Contrato Adm.", "Dt. Admissão", "Dt. Demissão",
            "_vlr_mensalidade_fat", "_vlr_dependente_fat", "_vlr_copart_fat",
            "Composição da Cobrança", "Valor Fatura", "Tem Direito"]
    tab = df_exc[[c for c in cols if c in df_exc.columns]].copy().reset_index(drop=True).rename(columns={
        "_vlr_mensalidade_fat": "Mensalidade", "_vlr_dependente_fat": "Dependentes", "_vlr_copart_fat": "Coparticipação"})
    tab_excel = tab.copy()
    moeda = [c for c in ("Mensalidade", "Dependentes", "Coparticipação", "Valor Fatura") if c in tab.columns]
    for c in moeda:
        tab[c] = pd.to_numeric(tab[c], errors="coerce")
    for c in ("Dt. Admissão", "Dt. Demissão"):
        if c in tab.columns:
            limpo = tab[c].astype(str).str.strip().replace({"nan": "", "None": "", "NaT": "", "none": "", "NAT": ""})
            tab[c] = pd.to_datetime(limpo, dayfirst=True, errors="coerce")
    # o cabeçalho diz que os valores são da fatura do mês anterior
    tab = tab.rename(columns={c: f"{c} ({ant})" for c in moeda})
    copart = pd.DataFrame()
    if not df_copart.empty:
        cc = [c for c in ["Funcionário", "Empresa", "Departamento", "Contrato Adm.", "Dt. Admissão", "Dt. Demissão",
                          "_vlr_copart_fat"] if c in df_copart.columns]
        copart = df_copart[cc].rename(columns={"_vlr_copart_fat": f"Conta médica ({ant})"}).reset_index(drop=True)
    return {**base, "ant": ant, "erro": "", "n_ant": len(fat_ant), "n_atual": len(fat_atual),
            "exc": df_exc.reset_index(drop=True), "tab": tab, "tab_excel": tab_excel,
            "moeda": tuple(f"{c} ({ant})" for c in moeda), "renomeados": renomeados, "copart": copart,
            "sem_inativos": df_inat.empty, "sem_dados": sem_dados}


# ── Análises (antes: pages/7_Análises.py) ────────────────────────────────────
def _col(df, grupo):
    return df[grupo].fillna("").astype(str).str.strip()


def gastos_por(df, grupo):
    cols = [c for c in ["Valor Fatura", "Valor Compra Total", "Valor Contrato"] if c in df.columns]
    if grupo not in df.columns or not cols:
        return pd.DataFrame(), []
    d = df.copy()
    d[grupo] = _col(d, grupo)
    d = d[d[grupo] != ""]
    if d.empty:
        return pd.DataFrame(), cols
    for c in cols:
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0)
    return d.groupby(grupo, as_index=False)[cols].sum().sort_values(cols[0], ascending=False), cols


def desvios_por(df, grupo):
    cols = [c for c in ["Dif. Contrato x Compra", "Dif. Fatura x Compra"] if c in df.columns]
    if grupo not in df.columns or not cols:
        return pd.DataFrame(), []
    d = df.copy()
    d[grupo] = _col(d, grupo)
    d = d[d[grupo] != ""]
    for c in cols:
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0).abs()
    d = d[d[cols].sum(axis=1) > 0]
    if d.empty:
        return pd.DataFrame(), cols
    return d.groupby(grupo, as_index=False)[cols].sum().sort_values(cols[0], ascending=False), cols


def inconsistencias_por(df, grupo):
    if grupo not in df.columns:
        return pd.DataFrame()
    d = df[df.get("Status", pd.Series(dtype=str)).fillna("").astype(str).str.strip() == "Inconsistente"].copy()
    if d.empty:
        return pd.DataFrame()
    d[grupo] = _col(d, grupo)
    d = d[d[grupo] != ""]
    if d.empty:
        return pd.DataFrame()
    return (d.groupby(grupo, as_index=False).size().rename(columns={"size": "Qtd."})
            .sort_values("Qtd.", ascending=False))


def inconsistencias_por_tipo(df):
    if "Tipo Inconsistência" not in df.columns:
        return pd.DataFrame()
    tipos = [t.strip() for cell in df["Tipo Inconsistência"].dropna() for t in str(cell).split("|") if t.strip()]
    if not tipos:
        return pd.DataFrame()
    return pd.Series(tipos).value_counts().rename_axis("Tipo").reset_index(name="Qtd.").sort_values("Qtd.", ascending=False)


def maiores_desvios(df):
    cols = [c for c in ["Funcionário", "Empresa", "Departamento", "Contrato Adm.", "Valor Contrato",
                        "Valor Empresa (Compra)", "Valor Fatura", "Valor Compra Total", "Dif. Contrato x Compra",
                        "Dif. Fatura x Compra", "Inconsistência"] if c in df.columns]
    if not cols:
        return pd.DataFrame(), 0
    d = df[cols].copy()
    d["_total"] = (pd.to_numeric(d.get("Dif. Contrato x Compra", 0), errors="coerce").fillna(0).abs()
                   + pd.to_numeric(d.get("Dif. Fatura x Compra", 0), errors="coerce").fillna(0).abs())
    d = d[d["_total"] > 0.01].sort_values("_total", ascending=False)
    total = len(d)
    d = d.drop(columns=["_total"]).head(20).reset_index(drop=True)
    for c in MOEDA:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    return d, total


_EVOLUCAO: dict = {}


def evolucao(cliente: str = "") -> pd.DataFrame:
    """Totais por período. Guarda o resultado enquanto o histórico não muda (é a conta mais pesada)."""
    periodos = db.listar_periodos(cliente) if cliente else db.listar_periodos()
    chave = (cliente, tuple((p["id"], p["processado_em"]) for p in periodos))
    if chave not in _EVOLUCAO:
        _EVOLUCAO.clear()
        _EVOLUCAO[chave] = _evolucao(periodos)
    return _EVOLUCAO[chave].copy()


def _evolucao(periodos) -> pd.DataFrame:
    linhas = []
    for p in periodos:
        d, _s, _m = db.carregar_auditoria(p["periodo"], p["cliente"])
        if d is None or d.empty:
            continue
        d = aplicar_regras(d)
        linhas.append({"Período": p["periodo"],
                       "Total Fatura": pd.to_numeric(d.get("Valor Fatura", 0), errors="coerce").fillna(0).sum(),
                       "Total Compra": pd.to_numeric(d.get("Valor Compra Total", 0), errors="coerce").fillna(0).sum(),
                       "Inconsistentes": int((d.get("Status", "").astype(str).str.strip() == "Inconsistente").sum())})
    if not linhas:
        return pd.DataFrame()
    return (pd.DataFrame(linhas).groupby("Período", as_index=False).last()
            .assign(_ord=lambda x: pd.to_datetime("01/" + x["Período"], format="%d/%m/%Y", errors="coerce"))
            .sort_values("_ord").drop(columns="_ord").reset_index(drop=True))


# ── Prévia das colunas encontradas (antes: _ler_colunas_arq na tela 1) ───────
def colunas_do_arquivo(caminho: str, grupos=None) -> list:
    import io
    from app.processamento import _score_cabecalho
    try:
        dados = Path(caminho).read_bytes()
    except OSError:
        return []

    def validas(df):
        return not df.empty and len(df.columns) >= 2 and sum(
            1 for c in df.columns if not str(c).lower().startswith("unnamed")) >= 2

    melhor, nota = [], -1
    if str(caminho).lower().endswith((".xlsx", ".xls")):
        tentativas = ((lambda h=h: pd.read_excel(io.BytesIO(dados), dtype=str, header=h)) for h in range(9))
    else:
        tentativas = ((lambda e=e, s=s, h=h: pd.read_csv(io.BytesIO(dados), sep=s, dtype=str, encoding=e, header=h,
                                                         skip_blank_lines=True, on_bad_lines="skip"))
                      for e in ("latin-1", "cp1252", "utf-8-sig", "utf-8") for s in (";", ",", "\t", "|") for h in range(9))
    for ler in tentativas:
        try:
            df = ler().dropna(how="all").dropna(how="all", axis=1)
            n = _score_cabecalho(df, grupos)
            if validas(df) and n > nota:
                melhor, nota = list(df.columns), n
        except Exception:      # noqa: BLE001
            continue
    return melhor


def previa_colunas(arquivos: dict) -> list:
    """[(título, colunas do arquivo, {campo: coluna encontrada})] para a prévia da Importação."""
    from app.processamento import (COMPRA_HEADER_GROUPS, CONTRATOS_HEADER_GROUPS, FATURA_HEADER_GROUPS,
                                   _encontrar_col as ec, _encontrar_col_prioritaria as ecp)
    saida = []
    if arquivos.get("contratos"):
        cols = colunas_do_arquivo(arquivos["contratos"][0]["caminho"], CONTRATOS_HEADER_GROUPS)
        d = pd.DataFrame(columns=cols)
        saida.append(("Contratos", cols, {
            "Funcionário": ecp(d, "nome do funcionario", "nome da funcionaria", "nome funcionario", "nome da funcionária",
                               "funcionario", "funcionária", "nome colaborador", "nome empregado", "nome"),
            "Empresa": ec(d, "cód. empresa", "cod empresa", "empresa"),
            "Departamento": ec(d, "departamento", "depto", "setor", "unidade", "lotação"),
            "Contrato Adm.": ec(d, "contrato adm", "contrato administrativo", "contrato adm.", "contr. adm", "tipo contrato"),
            "Valor Plano": ec(d, "valor plano de saúde", "valor plano de saude", "valor plano", "vlr plano",
                              "mensalidade titular", "valor mensal titular", "plano", "saude", "mensalidade"),
            "Admissão": ec(d, "dt. admissão", "dt. admissao", "admissão", "dt adm", "data adm")}))
    if arquivos.get("fatura"):
        cols = colunas_do_arquivo(arquivos["fatura"][0]["caminho"], FATURA_HEADER_GROUPS)
        d = pd.DataFrame(columns=cols)
        saida.append(("Fatura", cols, {
            "Titular": ecp(d, "nome do titular", "beneficiário titular", "beneficiario titular", "titular",
                           "beneficiário", "beneficiario", "nome"),
            "Descrição": ec(d, "descrição do item", "descricao do item", "descrição", "descricao"),
            "Valor": ec(d, "valor", "vl."),
            "Data Inclusão": ec(d, "data inclusao", "data de inclusao", "inclusao", "dt. inclusao"),
            "Nascimento": ec(d, "nascimento", "data nasc")}))
    if arquivos.get("compra"):
        cols = colunas_do_arquivo(arquivos["compra"][0]["caminho"], COMPRA_HEADER_GROUPS)
        d = pd.DataFrame(columns=cols)
        saida.append(("Compra", cols, {
            "Funcionário": ecp(d, "nome do funcionario", "nome da funcionaria", "nome funcionario", "nome da funcionária",
                               "beneficiario titular", "funcionario", "funcionária", "titular", "nome"),
            "Valor Empresa": ec(d, "valor. empresa", "valor empresa", "valor mensal empresa", "mensalidade empresa",
                                "patronal", "custo empresa", "empresa"),
            "Valor Func.": ec(d, "valor. beneficário", "valor beneficário", "valor beneficiario", "valor funcionario",
                              "mensalidade funcionario", "desconto funcionario", "beneficiario")}))
    if arquivos.get("desligados"):
        from app.exclusoes_indevidas import _encontrar_col as ecd, _melhor_df
        caminho = arquivos["desligados"][0]["caminho"]
        try:
            raw = _melhor_df(Path(caminho).read_bytes(), caminho.lower())
            cols = list(raw.columns) if raw is not None else []
        except Exception:      # noqa: BLE001
            cols = []
        d = pd.DataFrame(columns=cols)
        saida.append(("Desligados", cols, {
            "Nome": ecd(d, "nome funcionario", "nome colaborador", "funcionario", "nome"),
            "Data Demissão": ecd(d, "demissao", "desligamento", "rescisao", "data demissao", "saida"),
            "CPF": ecd(d, "cpf", "documento"),
            "Matrícula": ecd(d, "matricula", "chapa", "cod func", "codigo")}))
    return saida
