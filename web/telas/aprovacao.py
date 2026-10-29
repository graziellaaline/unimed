# -*- coding: utf-8 -*-
"""5 · Auditoria e Aprovação — resultado, justificativa e fechamento do mês numa tela só.

A justificativa é escrita direto na tabela e grava ao sair da célula (antes havia um botão
"Salvar edições"). Lote vale só para as linhas MARCADAS — filtrar não seleciona ninguém.
"""
from __future__ import annotations

import time

from dash import Input, Output, State, ctx, dcc, html, no_update

from app import db
from web import comp, servico
from web.telas import Tela

REGRAS_LINHA = {
    "lin-pend": "params.data && params.data['Status'] === 'Inconsistente' && params.data['Justificado'] !== 'Sim'",
    "lin-just": "params.data && params.data['Status'] === 'Inconsistente' && params.data['Justificado'] === 'Sim'",
}


def _resumo(d):
    s, n_inc, n_just, n_pend = d["stats"], d["n_inc"], d["n_just"], d["n_pend"]
    total_p = d["n_funcs_pend"]
    kpis = html.Div([
        comp.kpi("Total", s.get("total", 0)), comp.kpi("OK", s.get("ok", 0)),
        comp.kpi("Inconsistentes", n_inc),
        comp.kpi("Pendentes", n_pend, f"{n_just} justificadas" if n_just else None, destaque=True),
        comp.kpi("Na fatura", s.get("na_fatura", 0)), comp.kpi("Na compra", s.get("na_compra", 0)),
        comp.kpi("Total fatura", comp.brl(s.get("total_fatura", 0))),
        comp.kpi("Total compra", comp.brl(s.get("total_compra", 0))),
    ], className="kpis")
    if not total_p:
        barra = comp.aviso("Nenhuma pendência — todas as linhas estão OK. O mês pode ser fechado.", "ok")
    else:
        pct = n_just / total_p * 100
        barra = html.Div([
            html.Div([html.B("Justificativas do mês"),
                      html.Span(f"{n_just} de {total_p} preenchidas", className="tab-num", style={"color": "var(--txt2)"})],
                     className="cabeca", style={"marginBottom": 0}),
            html.Div(html.I(style={"width": f"{pct:.1f}%"}), className="prog", role="progressbar",
                     **{"aria-valuenow": n_just, "aria-valuemin": 0, "aria-valuemax": total_p}),
            html.Div("O mês só fecha com todas as inconsistências justificadas." if n_pend else
                     "Todas as pendências têm justificativa. O mês pode ser fechado.", className="cap"),
        ], className="pn bloco")
    return [kpis, barra]


def layout(sel, quem):
    d = servico.aprovacao(sel)
    if d is None:
        return comp.vazio_sem_auditoria()
    meta = d["meta"]
    fechado = meta.get("aprovado")
    return html.Div([
        dcc.Store(id="ap-ver", data=0),
        dcc.Store(id="ap-confirma"),
        dcc.Download(id="ap-excel"),
        html.Div(_resumo(d), id="ap-resumo"),
        html.Section([
            html.Div([
                html.Div([html.H2("Conferência linha a linha", className="t"),
                          html.P("Funil do cabeçalho filtra a coluna · arraste o cabeçalho para reordenar (a posição fica "
                                 "gravada) · duplo clique copia a célula · a Justificativa é editável e grava ao sair da célula.",
                                 className="sub", style={"margin": 0})]),
                html.Div([html.Button("⤓ Exportar Excel completo", id="ap-exportar", className="btn peq", n_clicks=0)],
                         className="acts"),
            ], className="cabeca"),
            comp.grade("ap-grade", d["tab"], "grade_auditoria", moeda=servico.MOEDA, datas=servico.DATAS,
                       editaveis=("Justificativa",), selecao=True, regras_linha=REGRAS_LINHA, id_linha="_id",
                       larguras={"Funcionário": 220, "Inconsistência": 300, "Justificativa": 320}),
            html.Label([dcc.Checklist(id="ap-modelo", options=[{"label": " Guardar as justificativas como modelo para os próximos meses",
                                                                  "value": "s"}], value=["s"])], className="marca"),
        ], className="pn bloco"),
        html.Section([
            html.Div([
                html.H2("Justificar em lote", className="t"),
                html.P("Vale só para as linhas marcadas na tabela (o tique da primeira coluna).", className="sub"),
                dcc.Textarea(id="ap-lote", className="inp", placeholder="Ex.: Desligamento comunicado após o fechamento da fatura"),
                html.Div(id="ap-lote-quem", className="cap"),
                dcc.Checklist(id="ap-lote-modelo", options=[{"label": " Guardar como modelo para os próximos meses", "value": "s"}],
                              value=["s"], className="marca"),
                html.Button("Aplicar às marcadas", id="ap-lote-aplicar", className="btn azul", n_clicks=0),
            ], className="pn"),
            html.Div([
                html.H2("Fechar o mês", className="t"),
                html.P(f"Grava a auditoria de {meta['periodo']} como aprovada no histórico, com as justificativas.",
                       className="sub"),
                comp.aviso(f"✅ Este mês já foi fechado em {str(meta.get('aprovado_em') or '')[:10]}.", "ok") if fechado else None,
                html.Div([
                    html.Button(f"✔ Aprovar e fechar {meta['periodo']}", id="ap-aprovar", className="btn pri",
                                n_clicks=0, disabled=d["n_pend"] > 0),
                    html.Button("Reaplicar modelos salvos", id="ap-modelos", className="btn ghost peq", n_clicks=0),
                ], className="acts"),
            ], className="pn"),
        ], className="grid2"),
    ])


def registrar(app, dep):
    # justificativa digitada na célula: grava na hora e atualiza a linha
    @app.callback(Output("ap-grade", "rowTransaction"), Output("aviso", "data", allow_duplicate=True),
                  Output("ap-ver", "data", allow_duplicate=True),
                  Input("ap-grade", "cellValueChanged"), State("sel", "data"), State("ap-modelo", "value"),
                  State("ap-ver", "data"), prevent_initial_call=True)
    def _celula(mudancas, sel, modelo, ver):
        if not mudancas:
            return no_update, no_update, no_update
        d = servico.aprovacao(sel)
        linhas, salvas, revertidas, ignoradas = [], 0, 0, 0
        for m in (mudancas if isinstance(mudancas, list) else [mudancas]):
            if m.get("colId") != "Justificativa":
                continue
            row = dict(m.get("data") or {})
            if row.get("Status") != "Inconsistente":
                ignoradas += 1
                continue
            r = servico.gravar_justificativa(d["meta"], d["pend"], str(row.get("Funcionário", "")),
                                             row.get("Justificativa", ""), bool(modelo))
            salvas += r == "salva"
            revertidas += r == "revertida"
            row["Justificado"] = "Sim" if (row.get("Justificativa") or "").strip() else "Não"
            linhas.append(row)
        partes = []
        if salvas:
            partes.append(f"{salvas} justificativa(s) salva(s)")
        if revertidas:
            partes.append(f"{revertidas} voltou(aram) para pendente")
        if ignoradas:
            partes.append("linha OK não precisa de justificativa")
        aviso = {"msg": " · ".join(partes) + ".", "tipo": "ok" if not ignoradas else "info"} if partes else no_update
        return ({"update": linhas} if linhas else no_update), aviso, (ver or 0) + 1

    @app.callback(Output("ap-lote-quem", "children"), Input("ap-grade", "selectedRows"))
    def _quem(sel_linhas):
        nomes = [str(r.get("Funcionário", "")) for r in (sel_linhas or []) if r.get("Status") == "Inconsistente"]
        if not nomes:
            return "Nenhuma linha inconsistente marcada."
        amostra = ", ".join(nomes[:5]) + (f" … (+{len(nomes) - 5})" if len(nomes) > 5 else "")
        return f"Será aplicada a {len(nomes)}: {amostra}"

    @app.callback(Output("ap-grade", "rowTransaction", allow_duplicate=True),
                  Output("aviso", "data", allow_duplicate=True), Output("ap-ver", "data", allow_duplicate=True),
                  Output("ap-lote", "value"), Output("ap-grade", "selectedRows"),
                  Input("ap-lote-aplicar", "n_clicks"), State("ap-grade", "selectedRows"), State("ap-lote", "value"),
                  State("ap-lote-modelo", "value"), State("sel", "data"), State("ap-ver", "data"),
                  prevent_initial_call=True)
    def _lote(_n, marcadas, texto, modelo, sel, ver):
        if not _n:
            return no_update, no_update, no_update, no_update, no_update
        alvo = [r for r in (marcadas or []) if r.get("Status") == "Inconsistente"]
        if not alvo:
            return no_update, {"msg": "Marque pelo menos uma linha inconsistente na tabela.", "tipo": "err"}, no_update, no_update, no_update
        if not (texto or "").strip():
            return no_update, {"msg": "Escreva a justificativa do lote.", "tipo": "err"}, no_update, no_update, no_update
        d = servico.aprovacao(sel)
        n = servico.justificar_lote(d["meta"], d["pend"], [str(r["Funcionário"]) for r in alvo], texto, bool(modelo))
        linhas = [{**r, "Justificativa": texto.strip(), "Justificado": "Sim"} for r in alvo]
        return {"update": linhas}, {"msg": f"Justificativa aplicada a {n} pendência(s).", "tipo": "ok"}, (ver or 0) + 1, "", []

    @app.callback(Output("ap-resumo", "children"), Output("ap-aprovar", "disabled"),
                  Input("ap-ver", "data"), State("sel", "data"), prevent_initial_call=True)
    def _recalcular(_v, sel):
        d = servico.aprovacao(sel)
        return _resumo(d), d["n_pend"] > 0

    @app.callback(Output("ap-grade", "rowData"), Output("aviso", "data", allow_duplicate=True),
                  Output("ap-ver", "data", allow_duplicate=True),
                  Input("ap-modelos", "n_clicks"), State("sel", "data"), State("ap-ver", "data"),
                  prevent_initial_call=True)
    def _modelos(_n, sel, ver):
        if not _n:
            return no_update, no_update, no_update
        d = servico.aprovacao(sel)
        n = servico.aplicar_modelos(d["meta"], d["pend"])
        if not n:
            return no_update, {"msg": "Nenhuma justificativa reutilizável encontrada.", "tipo": "info"}, no_update
        d = servico.aprovacao(sel)
        return comp._para_grade(d["tab"], servico.DATAS), {"msg": f"{n} justificativa(s) reaplicada(s).", "tipo": "ok"}, (ver or 0) + 1

    # fechar o mês: pergunta Sim/Não do kit (nunca o confirm() do navegador)
    app.clientside_callback(
        """async function (n, periodo) {
            if (!n) { return window.dash_clientside.no_update; }
            var ok = window.DP && DP.confirmar ? await DP.confirmar("Aprovar e fechar a auditoria de " + periodo + "?") : false;
            return ok ? Date.now() : window.dash_clientside.no_update;
        }""",
        Output("ap-confirma", "data"), Input("ap-aprovar", "n_clicks"), State("ap-aprovar", "children"),
        prevent_initial_call=True)

    @app.callback(Output("aviso", "data", allow_duplicate=True), Output("mudou", "data", allow_duplicate=True),
                  Input("ap-confirma", "data"), State("sel", "data"), State("mudou", "data"), prevent_initial_call=True)
    def _aprovar(confirmado, sel, mudou):
        if not confirmado:
            return no_update, no_update
        d = servico.aprovacao(sel)
        if d["n_pend"] > 0:          # o botão desabilitado não é a barreira: o servidor confere de novo
            return {"msg": f"Ainda faltam {d['n_pend']} justificativa(s).", "tipo": "err"}, no_update
        db.aprovar_auditoria(d["meta"]["id"])
        from web import estado
        estado.esquecer()
        return {"msg": f"Auditoria {d['meta']['periodo']} aprovada e guardada no histórico.", "tipo": "ok"}, (mudou or 0) + 1

    @app.callback(Output("ap-excel", "data"), Input("ap-exportar", "n_clicks"), State("sel", "data"),
                  prevent_initial_call=True)
    def _excel(_n, sel):
        if not _n:
            return no_update
        d = servico.aprovacao(sel)
        nome = f"auditoria_unimed_{d['meta']['periodo'].replace('/', '_')}.xlsx"
        return dcc.send_bytes(servico.excel_completo(d), nome)

    # a posição das colunas que a pessoa arrasta fica gravada
    @app.callback(Output("ap-grade", "id"), Input("ap-grade", "columnState"), prevent_initial_call=True)
    def _ordem(estado_cols):
        cols = [c.get("colId") for c in (estado_cols or []) if c.get("colId") and not c["colId"].startswith("_")]
        if cols:
            comp.gravar_ordem("grade_auditoria", [c for c in cols if c != "ag-Grid-SelectionColumn"])
        return no_update


TELA = Tela("/", "Auditoria e Aprovação", layout, registrar)
