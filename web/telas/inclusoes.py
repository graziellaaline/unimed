# -*- coding: utf-8 -*-
"""2 · Inclusões no mês de referência (data de inclusão no período + titulares novos vs o mês anterior)."""
from __future__ import annotations

from dash import Input, Output, State, dcc, html, no_update

from web import comp, servico
from web.telas import Tela


def bloco_texto(prefixo: str, titulo: str, texto: str):
    """O texto para copiar e colar (Descrição): acompanha o filtro da tabela."""
    return html.Section([
        html.H2(titulo, className="t"),
        html.P("Um bloco por funcionário. Acompanha o que está filtrado na tabela.", className="sub"),
        dcc.Textarea(id=f"{prefixo}-texto", value=texto, className="inp", readOnly=True, style={"minHeight": "220px"}),
        html.Div([html.Button("Copiar texto", id=f"{prefixo}-copiar", className="btn azul peq", n_clicks=0),
                  html.Button("⤓ Baixar .txt", id=f"{prefixo}-txt", className="btn peq", n_clicks=0)],
                 className="acts", style={"marginTop": "10px"}),
        dcc.Download(id=f"{prefixo}-baixar-txt"),
    ], className="pn bloco")


def registrar_texto(app, prefixo: str, grade_id: str, calcular, nome_txt, extras=()):
    """Liga copiar/baixar e o recálculo do texto quando o filtro da tabela muda."""
    app.clientside_callback(
        """function (n, txt) {
            if (!n) { return window.dash_clientside.no_update; }
            var fim = function (ok) { if (window.DP) DP.toast(ok ? "Texto copiado." : "Selecione o texto e use Ctrl+C.", ok ? "ok" : "info"); };
            if (navigator.clipboard) { navigator.clipboard.writeText(txt || "").then(function () { fim(true); }, function () { fim(false); }); }
            else { fim(false); }
            return "";
        }""",
        Output(f"{prefixo}-copiar", "title"), Input(f"{prefixo}-copiar", "n_clicks"), State(f"{prefixo}-texto", "value"),
        prevent_initial_call=True)

    @app.callback(Output(f"{prefixo}-texto", "value"), Input(grade_id, "virtualRowData"), State("sel", "data"),
                  *[State(i, p) for i, p in extras], prevent_initial_call=True)
    def _texto(visiveis, sel, *mais):
        if visiveis is None:
            return no_update
        return calcular(sel, [r.get("Funcionário") for r in visiveis], *mais)

    @app.callback(Output(f"{prefixo}-baixar-txt", "data"), Input(f"{prefixo}-txt", "n_clicks"),
                  State(f"{prefixo}-texto", "value"), State("sel", "data"), prevent_initial_call=True)
    def _txt(_n, txt, sel):
        if not _n:
            return no_update
        return dcc.send_string(txt or "", nome_txt(sel))


def _txt_calc(sel, nomes):
    d = servico.inclusoes(sel)
    return servico.texto_descricao(d["todos"], nomes, "INCLUSÃO", "Data Inclusão")


def _nome_txt(sel):
    return f"inclusoes_unimed_{(sel or {}).get('periodo', '').replace('/', '_')}_descricao.txt"


def layout(sel, quem):
    d = servico.inclusoes(sel)
    if d is None:
        return comp.vazio_sem_auditoria()
    periodo, info_ant = d["meta"]["periodo"], d["info_ant"]
    if d["todos"].empty:
        msg = f"Nenhuma inclusão identificada em {periodo}" + (f" (comparado com {info_ant})." if info_ant else ".")
        return comp.aviso(msg, "info")
    alertas = []
    if not d["desl"].empty:
        nomes = ", ".join(d["desl"]["Funcionário"].head(6).astype(str))
        if len(d["desl"]) > 6:
            nomes += f" e mais {len(d['desl']) - 6}"
        alertas.append(comp.aviso(f"⚠️ {len(d['desl'])} pessoa(s) fora desta lista por já estarem desligadas — não são "
                                  f"inclusões, são cobranças de quem saiu: {nomes}. Confira em Exclusões indevidas.", "warn"))
    if info_ant:
        k2 = comp.kpi(f"Novos em relação a {info_ant}", d["n_c2"], "titulares que não estavam no mês anterior", destaque=True)
    elif info_ant is None:
        k2 = comp.kpi(f"Novos em relação a {d['ant']}", "—", "o mês anterior não está no histórico")
    else:
        k2 = comp.kpi("Novos em relação ao mês anterior", "—", "mês anterior indisponível")
    return html.Div([
        *alertas,
        html.Div([comp.kpi("Inclusão com data no período", d["n_c1"]), k2,
                  comp.kpi("Total de inclusões", len(d["todos"]))], className="kpis"),
        html.Section([
            html.Div([html.Div([html.H2(f"Incluídos em {periodo}", className="t"),
                                html.P("Funil do cabeçalho filtra ou ordena · duplo clique copia a célula.",
                                       className="sub", style={"margin": 0})]),
                      html.Button("⤓ Exportar Excel", id="inc-exportar", className="btn peq", n_clicks=0)],
                     className="cabeca"),
            comp.grade("inc-grade", d["tab"], "grade_inclusoes", moeda=("Valor Fatura", "Valor Contrato"),
                       datas=("Dt. Admissão", "Data Inclusão"), larguras={"Funcionário": 220}, altura=480),
            dcc.Download(id="inc-excel"),
        ], className="pn bloco"),
        comp.aviso(f"Inclusões retroativas: quem foi incluído com data anterior a {periodo} e não constava em "
                   f"{info_ant or 'mês anterior'} pode gerar cobrança proporcional retroativa. Confira se o valor "
                   "faturado corresponde aos dias de cobertura.", "info"),
        bloco_texto("inc", "Texto para copiar e colar (Descrição)", _txt_calc(sel, None)),
    ])


def registrar(app, dep):
    registrar_texto(app, "inc", "inc-grade", _txt_calc, _nome_txt)

    @app.callback(Output("inc-excel", "data"), Input("inc-exportar", "n_clicks"), State("sel", "data"),
                  prevent_initial_call=True)
    def _excel(_n, sel):
        if not _n:
            return no_update
        d = servico.inclusoes(sel)
        return dcc.send_bytes(servico.excel_inclusoes(d), f"inclusoes_unimed_{d['meta']['periodo'].replace('/', '_')}.xlsx")


TELA = Tela("/inclusoes", "Inclusões", layout, registrar)
