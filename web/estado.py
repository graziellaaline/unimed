# -*- coding: utf-8 -*-
"""A auditoria aberta na tela. No Streamlit ela morava no `st.session_state`; aqui cada tela
recebe {periodo, cliente} da Store do navegador e lê do histórico (com cache por versão gravada).
"""
from __future__ import annotations

import threading

import pandas as pd

from app import db
from app.regras import aplicar_regras, calcular_stats, identificar_incluidos_mes

_cache: dict = {}
_trava = threading.Lock()


def periodos() -> list:
    return db.listar_periodos()


def padrao() -> dict:
    """A auditoria mais recente do histórico (o que a tela abre quando não há escolha)."""
    ps = periodos()
    return {"periodo": ps[0]["periodo"], "cliente": ps[0]["cliente"]} if ps else {}


def carregar(sel: dict | None):
    """(df, stats, meta) da auditoria escolhida, já com as regras atuais — ou (None, {}, {})."""
    sel = sel or padrao()
    if not sel.get("periodo"):
        return None, {}, {}
    periodo, cliente = sel["periodo"], sel.get("cliente", "")
    df, stats, meta = db.carregar_auditoria(periodo, cliente)
    if df is None or df.empty:
        return None, {}, {}
    chave = (meta["id"], meta.get("processado_em"))
    with _trava:
        if chave in _cache:
            d, s = _cache[chave]
            return d.copy(), dict(s), {**meta, "periodo": periodo, "cliente": cliente}
    # correção dos inativos (desligados), quando o arquivo ficou guardado — como a tela 5 fazia
    item = (db.carregar_arquivos_auditoria(meta["id"]).get("desligados") or [None])[0]
    if item and item.get("caminho"):
        try:
            from app.processamento import ler_contratos, mesclar_desligados
            df, _ = mesclar_desligados(df, ler_contratos(item["caminho"]), periodo)
        except Exception:      # noqa: BLE001 — arquivo sumiu ou mudou: segue sem a correção
            pass
    df = aplicar_regras(df)
    stats = calcular_stats(df) or stats or {}
    with _trava:
        if len(_cache) > 12:
            _cache.clear()
        _cache[chave] = (df, stats)
    return df.copy(), dict(stats), {**meta, "periodo": periodo, "cliente": cliente}


def incluidos(df: pd.DataFrame, periodo: str) -> pd.DataFrame:
    return identificar_incluidos_mes(df, periodo)


def esquecer() -> None:
    with _trava:
        _cache.clear()
