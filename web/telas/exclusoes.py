# -*- coding: utf-8 -*-
"""3 · Exclusões do mês — quem estava na fatura do mês anterior e não está mais."""
from __future__ import annotations

import base64
import tempfile
from pathlib import Path

import pandas as pd
from dash import Input, Output, State, dcc, html, no_update

from app.exportacao import exportar_excel_exclusoes
from web import comp, servico
from web.telas import Tela
from web.telas.inclusoes import bloco_texto, registrar_texto

PASTA_TMP = Path(tempfile.gettempdir()) / "auditoria-unimed-inativos"


def _calc(sel, ant=None, inat=None):
    return servico.exclusoes(sel, ant, inat)


def _texto(d, nomes=None):
    col = "Dt. Demissão" if "Dt. Demissão" in d["exc"].columns else ""
    return servico.texto_descricao(d["exc"], nomes, "EXCLUSÃO", col)


def _corpo(d):
    periodo, ant = d["meta"]["periodo"], d["ant"]
    if d.get("erro"):
        return comp.aviso(d["erro"], "info")
    partes = [html.Div([comp.kpi(f"Titulares em {ant}", d["n_ant"]), comp.kpi(f"Titulares em {periodo}", d["n_atual"]),
                        comp.kpi("Exclusões encontradas", len(d["exc"]), destaque=True)], className="kpis")]
    if d["renomeados"]:
        partes.append(html.Details([
            html.Summary(f"✍️ {len(d['renomeados'])} titular(es) mudaram de nome entre {ant} e {periodo} — não são exclusões"),
            html.P("Mesma matrícula e mesma admissão, nome diferente na fatura (casamento, correção de cadastro). Continuam ativos.",
                   className="cap"),
            comp.tabela_simples(pd.DataFrame(d["renomeados"], columns=[f"Nome em {ant}", f"Nome em {periodo}"])),
        ], className="pn bloco det"))
    if not d["copart"].empty:
        partes.append(html.Details([
            html.Summary(f"🩺 {len(d['copart'])} pessoa(s) tinham só conta médica em {ant} — não são exclusões de plano"),
            html.P("Não havia mensalidade, só coparticipação (atendimento já realizado) — normalmente resíduo de quem já "
                   "estava desligado. A cobrança de uso não é estornável.", className="cap"),
            comp.tabela_simples(d["copart"], moeda=(f"Conta médica ({ant})",)),
        ], className="pn bloco det"))
    if d["exc"].empty:
        partes.append(comp.aviso(f"✅ Nenhuma exclusão — todos os titulares de {ant} continuam na fatura de {periodo}.", "ok"))
        return html.Div(partes)
    partes += [
        comp.aviso(f"⚠️ {len(d['exc'])} titular(es) que constavam na fatura de {ant} não aparecem mais na fatura de {periodo}.",
                   "warn"),
        html.Section([
            html.Div([html.Div([html.H2("Exclusões", className="t"),
                                html.P(f"Os valores são os da fatura de {ant} — último mês em que estas pessoas foram "
                                       f"cobradas. Em {periodo} não há cobrança para elas.", className="sub", style={"margin": 0})]),
                      html.Button("⤓ Exportar Excel", id="exc-exportar", className="btn peq", n_clicks=0)], className="cabeca"),
            comp.grade("exc-grade", d["tab"], "grade_exclusoes", moeda=d["moeda"], datas=("Dt. Admissão", "Dt. Demissão"),
                       larguras={"Funcionário": 220}, altura=480),
            dcc.Download(id="exc-excel"),
        ], className="pn bloco"),
        comp.aviso("Observação para o fechamento: possíveis causas são desligamento, exclusão solicitada ou ausência na "
                   "fatura por erro da operadora. Confira se a exclusão foi pedida formalmente e se há crédito ou acerto a fazer.",
                   "info"),
        bloco_texto("exc", "Texto para copiar e colar (Descrição)", _texto(d)),
    ]
    return html.Div(partes)


def layout(sel, quem):
    d = _calc(sel)
    if d is None:
        return comp.vazio_sem_auditoria()
    opcoes = [{"label": p["periodo"] + (f" · {p['cliente']}" if p["cliente"] else ""), "value": p["periodo"]}
              for p in d["opcoes"]]
    inativos = None
    if not d.get("erro") and (d["sem_inativos"] or d["sem_dados"]):
        inativos = html.Details([
            html.Summary("📂 Planilha de inativos não encontrada — envie para preencher os dados que faltam" if d["sem_inativos"]
                         else f"📂 {d['sem_dados']} exclusão(ões) sem empresa — envie a planilha de inativos"),
            html.P("Quem aparece só na fatura (sem linha nos contratos ativos) precisa dela para mostrar empresa, "
                   "departamento e contrato. Mesma estrutura dos contratos ativos.", className="cap"),
            dcc.Upload(html.Div([html.B("Planilha de inativos"), html.Span("xlsx, xls ou csv · clique ou arraste", className="mut")]),
                       id="exc-inat", className="up", accept=".xlsx,.xls,.csv", multiple=False),
        ], className="pn bloco det", open=d["sem_inativos"])
    return html.Div([
        dcc.Store(id="exc-inat-caminho"),
        html.Section(html.Div([html.Label(["Comparar titulares com o período",
                                           dcc.Dropdown(id="exc-ant", options=opcoes, value=d["ant"], clearable=False,
                                                        className="escolha-auditoria")], className="campo")],
                              className="linha-campos", style={"margin": 0}), className="pn bloco") if opcoes else None,
        inativos,
        html.Div(_corpo(d), id="exc-corpo"),
    ])


def registrar(app, dep):
    @app.callback(Output("exc-inat-caminho", "data"), Output("aviso", "data", allow_duplicate=True),
                  Input("exc-inat", "contents"), State("exc-inat", "filename"), prevent_initial_call=True)
    def _inat(conteudo, nome):
        if not conteudo:
            return no_update, no_update
        PASTA_TMP.mkdir(parents=True, exist_ok=True)
        destino = PASTA_TMP / f"inativos_{abs(hash(conteudo)) % 10**10}{Path(nome or 'x.xlsx').suffix}"
        destino.write_bytes(base64.b64decode(conteudo.split(",", 1)[1]))
        return str(destino), {"msg": f"Planilha de inativos recebida: {nome}.", "tipo": "ok"}

    @app.callback(Output("exc-corpo", "children"), Input("exc-ant", "value"), Input("exc-inat-caminho", "data"),
                  State("sel", "data"), prevent_initial_call=True)
    def _comparar(ant, inat, sel):
        return _corpo(_calc(sel, ant, inat))

    registrar_texto(app, "exc", "exc-grade",
                    lambda sel, nomes, ant, inat: _texto(_calc(sel, ant, inat), nomes),
                    lambda sel: f"exclusoes_unimed_{(sel or {}).get('periodo', '').replace('/', '_')}_descricao.txt",
                    extras=(("exc-ant", "value"), ("exc-inat-caminho", "data")))

    @app.callback(Output("exc-excel", "data"), Input("exc-exportar", "n_clicks"), State("sel", "data"),
                  State("exc-ant", "value"), State("exc-inat-caminho", "data"), prevent_initial_call=True)
    def _excel(_n, sel, ant, inat):
        if not _n:
            return no_update
        d = _calc(sel, ant, inat)
        p = d["meta"]["periodo"]
        return dcc.send_bytes(exportar_excel_exclusoes(d["tab_excel"], p), f"exclusoes_unimed_{p.replace('/', '_')}.xlsx")


TELA = Tela("/exclusoes", "Exclusões", layout, registrar)
