# -*- coding: utf-8 -*-
"""6 · Histórico — as auditorias guardadas; abrir uma não exige importar de novo."""
from __future__ import annotations

from dash import ALL, Input, Output, ctx, html, no_update

from app import db
from web import comp
from web.telas import Tela


def layout(sel, quem):
    periodos = db.listar_periodos()
    if not periodos:
        return comp.aviso("Nenhuma auditoria guardada ainda. Processe a primeira na Importação.", "info")
    aberta = ((sel or {}).get("periodo"), (sel or {}).get("cliente", ""))
    linhas = []
    for p in periodos:
        linhas.append(html.Tr([
            html.Td(html.B(p["periodo"], className="tab-num")),
            html.Td(p["cliente"] or "—"),
            html.Td(p["processado_em"], className="tab-num"),
            html.Td(str(p["versoes"]), className="n"),
            html.Td(html.Span("● aberta na tela", className="tag ok") if (p["periodo"], p["cliente"]) == aberta else
                    html.Button("Abrir", id={"t": "hist-abrir", "p": p["periodo"], "c": p["cliente"]},
                                className="btn peq", n_clicks=0)),
        ]))
    return html.Section([
        html.H2("Auditorias guardadas", className="t"),
        html.P("Abra qualquer mês sem importar os arquivos de novo. Versões = quantas vezes o mês foi processado; "
               "vale sempre a mais recente.", className="sub"),
        html.Div(html.Table([html.Thead(html.Tr([html.Th("Período"), html.Th("Cliente"), html.Th("Processado em"),
                                                 html.Th("Versões", className="n"), html.Th("")])),
                             html.Tbody(linhas)]), className="tw"),
    ], className="pn")


def registrar(app, dep):
    @app.callback(Output("sel", "data", allow_duplicate=True), Output("url", "pathname", allow_duplicate=True),
                  Output("aviso", "data", allow_duplicate=True),
                  Input({"t": "hist-abrir", "p": ALL, "c": ALL}, "n_clicks"), prevent_initial_call=True)
    def _abrir(cliques):
        if not ctx.triggered_id or not any(cliques or []):
            return no_update, no_update, no_update
        p, c = ctx.triggered_id["p"], ctx.triggered_id["c"]
        return {"periodo": p, "cliente": c}, "/", {"msg": f"Auditoria {p} aberta.", "tipo": "ok"}


TELA = Tela("/historico", "Histórico", layout, registrar)
