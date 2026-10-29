# -*- coding: utf-8 -*-
"""Peças repetidas das telas: indicador, aviso, etiqueta, gráfico em SVG e a grade (dash-ag-grid)."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

import dash_ag_grid as dag
import pandas as pd
from dash import dcc, html

DADOS = Path(__file__).resolve().parent.parent / "dados"


def brl(v) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "—"


def brl_curto(v) -> str:
    return brl(v)[:-3]


def kpi(rotulo, valor, detalhe=None, destaque=False):
    return html.Div([html.Div(rotulo, className="r"),
                     html.Div(valor, className="v" + (" ac" if destaque else "")),
                     html.Div(detalhe, className="d") if detalhe else None], className="pn kpi")


def aviso(texto, tipo="info"):
    return html.Div(texto, className=f"aviso {tipo}", role="status")


def vazio_sem_auditoria():
    return html.Div([html.H2("Nenhuma auditoria aberta", className="t"),
                     html.P("Importe os arquivos do mês para começar, ou escolha uma auditoria no topo.", className="sub"),
                     dcc.Link("Ir para a Importação", href="/importacao", className="btn azul")], className="pn")


def svg(conteudo: str):
    """HTML cru (tabela do kit). SVG não passa pelo Markdown do Dash — gráfico é `grafico(...)`."""
    return dcc.Markdown(conteudo, dangerously_allow_html=True, style={"display": "contents"})


def grafico(tipo: str, dados: list, fmt: str = "num", series=None):
    """Gráfico desenhado no navegador por assets/50-graficos.js com as cores do tema.
    tipo: 'barras' (horizontais) ou 'tempo' (colunas: último em azul, contexto em azul-claro).
    fmt: 'num' | 'brl' | 'brl0' | 'casos'."""
    if not dados:
        return html.P("Sem dados para exibir.", className="cap")
    pares = [[str(linha[0]), *[float(v or 0) for v in linha[1:]]] for linha in dados]
    return html.Div(className="grafico", role="img", **{"data-tipo": tipo, "data-fmt": fmt,
                                                        "data-g": json.dumps(pares, ensure_ascii=False),
                                                        "data-series": json.dumps(list(series or []), ensure_ascii=False)})


def barras_h(dados: list, fmt: str = "num", series=None):
    return grafico("barras", dados, fmt, series)


def colunas_tempo(dados: list, fmt: str = "num"):
    return grafico("tempo", dados, fmt)


def tabela_simples(df: pd.DataFrame, moeda=(), max_linhas=500):
    """Tabela HTML com o filtro A→Z do kit (class dp-filtravel)."""
    if df is None or df.empty:
        return html.P("Nenhum registro.", className="cap")
    df = df.head(max_linhas)
    cab = "".join(f'<th class="{"n" if c in moeda else ""}">{escape(str(c))}</th>' for c in df.columns)
    linhas = []
    for _, r in df.iterrows():
        cel = []
        for c in df.columns:
            v = r[c]
            if c in moeda:
                cel.append(f'<td class="n">{escape(brl(v))}</td>')
            else:
                cel.append(f"<td>{escape('' if pd.isna(v) else str(v))}</td>")
        linhas.append("<tr>" + "".join(cel) + "</tr>")
    return svg(f'<div class="tw"><table class="dp-filtravel"><thead><tr>{cab}</tr></thead>'
               f'<tbody>{"".join(linhas)}</tbody></table></div>')


# ── grade (dash-ag-grid) ─────────────────────────────────────────────────────
def _arquivo_ordem(chave: str) -> Path:
    return DADOS / f"ordem_colunas_{chave}.json"


def ordem_salva(chave: str) -> list:
    try:
        return list(json.loads(_arquivo_ordem(chave).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return []


def gravar_ordem(chave: str, colunas: list) -> None:
    try:
        DADOS.mkdir(parents=True, exist_ok=True)
        _arquivo_ordem(chave).write_text(json.dumps(colunas, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass                                     # não pode derrubar a tela


def _para_grade(df: pd.DataFrame, datas=()) -> list:
    d = df.copy()
    for c in datas:
        if c in d.columns:
            d[c] = pd.to_datetime(d[c], errors="coerce").dt.strftime("%Y-%m-%d")   # ISO: ordena no tempo
    return json.loads(d.to_json(orient="records", force_ascii=False, date_format="iso"))


def grade(id_, df: pd.DataFrame, chave: str, *, moeda=(), datas=(), editaveis=(), larguras=None,
          selecao=False, altura=520, regras_linha=None, id_linha=None):
    """A tabela com filtro estilo Excel em cada coluna. A ordem das colunas que a pessoa arrasta
    fica gravada em disco (mesmos arquivos da versão Streamlit)."""
    ordem = ordem_salva(chave)
    cols = list(df.columns)
    if ordem:
        arrumadas = [c for c in ordem if c in cols]
        cols = arrumadas + [c for c in cols if c not in arrumadas]
    larguras = larguras or {}
    defs = []
    for i, c in enumerate(cols):
        d = {"field": c, "headerName": c, "filter": "UniFiltro", "sortable": True, "resizable": True,
             "minWidth": 110, "valueFormatter": {"function": "uniVazio(params)"}}
        if c in moeda:
            d.update(valueFormatter={"function": "uniBRL(params)"}, type="numericColumn", minWidth=140)
        elif c in datas:
            d.update(valueFormatter={"function": "uniData(params)"}, minWidth=125)
        if c in editaveis:
            d.update(editable=True, singleClickEdit=True, cellClass="cel-edit",
                     cellEditor="agLargeTextCellEditor", cellEditorPopup=True,
                     cellEditorParams={"maxLength": 2000, "rows": 4, "cols": 50})
        if c in larguras:
            d["width"] = larguras[c]
        if c.startswith("_"):
            d.update(hide=True, suppressColumnsToolPanel=True)
        if selecao and i == 0:
            d.update(checkboxSelection=True, headerCheckboxSelection=True,
                     headerCheckboxSelectionFilteredOnly=True)
        defs.append(d)
    opcoes = {"animateRows": True, "enableCellTextSelection": True, "ensureDomOrder": True,
              "suppressDragLeaveHidesColumns": True, "maintainColumnOrder": True, "suppressMenuHide": True,
              "stopEditingWhenCellsLoseFocus": True, "onCellDoubleClicked": {"function": "uniCopiar(params)"},
              "localeText": {"noRowsToShow": "Nenhum registro para exibir."}}
    if selecao:
        opcoes.update(rowSelection="multiple", suppressRowClickSelection=True)
    return dag.AgGrid(
        id=id_, rowData=_para_grade(df, datas), columnDefs=defs, columnSize="autoSize" if not larguras else None,
        defaultColDef={"flex": 0}, dashGridOptions=opcoes, rowClassRules=regras_linha or {},
        className="ag-theme-alpine", style={"height": f"{altura}px", "width": "100%"},
        persistence=True, persisted_props=["filterModel"], getRowId=(f"params.data[{json.dumps(id_linha)}]" if id_linha else None),
    )
