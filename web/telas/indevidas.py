# -*- coding: utf-8 -*-
"""4 · Exclusões indevidas — desligados que ainda aparecem na fatura ou na compra, com prejuízo estimado."""
from __future__ import annotations

import base64
import io
import tempfile
from pathlib import Path

from dash import Input, Output, State, dcc, html, no_update

from web import comp, estado
from web import servico_indevidas as si
from web.telas import Tela

PASTA_TMP = Path(tempfile.gettempdir()) / "auditoria-unimed-desligados"
REGRAS_LINHA = {"lin-pend": "params.data && String(params.data['Status']).indexOf('INDEVIDA') >= 0",
                "lin-just": "params.data && String(params.data['Status']).indexOf('FORA DO PRAZO') >= 0"}


def _ler_upload(caminho: str):
    return si._ler_planilha(Path(caminho).read_bytes(), Path(caminho).name)


def _resultado(sel, upload, cols, prazo, cobertura):
    df, _s, meta = estado.carregar(sel)
    if df is None:
        return None, None
    periodo = meta["periodo"]
    banco = si.desligados_do_banco(meta)
    if upload:
        raw = _ler_upload(upload)
        if raw is None or raw.empty:
            return meta, comp.aviso("Não foi possível ler a planilha enviada. Confira o arquivo.", "crit")
        if not (cols or {}).get("nome"):
            return meta, comp.aviso("Escolha a coluna com o nome do funcionário.", "crit")
        linhas, origem, banco = si.linhas_do_upload(raw, cols), "planilha enviada nesta tela", None
    elif banco is not None:
        linhas, origem = si.linhas_do_banco(banco), "arquivo de desligados guardado nesta auditoria"
    else:
        return meta, comp.aviso("Nenhuma planilha de desligados disponível. Envie uma acima, ou importe a planilha "
                                "de desligados na Importação para ela valer em todas as telas.", "warn")
    if not linhas:
        return meta, comp.aviso("Nenhum registro válido na planilha de desligados.", "warn")
    df = si.mesclar_no_audit(df, linhas, banco, periodo)
    res = si.analisar(df, periodo, linhas, int(prazo or 10), cobertura == "mes")
    topo = comp.aviso(f"✅ {len(linhas)} desligado(s) disponíveis ({origem}).", "ok")
    if res.empty:
        return meta, html.Div([topo, comp.aviso(f"✅ Nenhum desligado consta na fatura ou na compra de {periodo}.", "ok")])
    k = si.kpis(res)
    partes = [topo, html.Div([
        comp.kpi("🚨 Vidas indevidas", k["vidas"]), comp.kpi("💸 Prejuízo estimado", comp.brl(k["prejuizo"]), destaque=True),
        comp.kpi("⚠️ Fora do prazo", k["fora_prazo"]), comp.kpi("Ativos na fatura", k["na_fat"]),
        comp.kpi("Ativos na compra", k["na_comp"]),
        comp.kpi("Atraso médio", f"{k['atraso']:.0f} dias" if k["atraso"] is not None else "—")], className="kpis")]
    if k["sem_data"]:
        partes.append(comp.aviso(f"⚠️ {k['sem_data']} funcionário(s) sem data de demissão na planilha — o prejuízo deles "
                                 "considera o valor total da fatura.", "warn"))
    graf = []
    for col, titulo in (("Contrato Adm.", "Contratos com mais casos"), ("Departamento", "Departamentos com mais casos")):
        rk = si.ranking(res, col)
        graf.append(html.Div([html.H2(titulo, className="t"),
                              comp.barras_h(list(zip(rk[col], rk["Casos"])), "casos") if not rk.empty
                              else html.P("Sem dados.", className="cap"),
                              comp.tabela_simples(rk, moeda=("Prejuízo",)) if not rk.empty else None], className="pn"))
    partes.append(html.Div(graf, className="grid2"))
    partes.append(html.Section([
        html.Div([html.Div([html.H2(f"Casos — {periodo}", className="t"),
                            html.P("Funil do cabeçalho filtra ou ordena · duplo clique copia a célula.", className="sub",
                                   style={"margin": 0})]),
                  html.Button("⤓ Exportar Excel", id="ind-exportar", className="btn peq", n_clicks=0)], className="cabeca"),
        comp.grade("ind-grade", res, "grade_exclusoes_indevidas", moeda=si.MOEDA, datas=si.DATAS,
                   larguras={"Funcionário": 220}, altura=500, regras_linha=REGRAS_LINHA),
    ], className="pn bloco"))
    return meta, html.Div(partes)


def _mapa(upload, cols):
    if not upload:
        return None
    raw = _ler_upload(upload)
    if raw is None or raw.empty:
        return None
    opcoes = [{"label": "(não usar)", "value": ""}] + [{"label": str(c), "value": str(c)} for c in raw.columns]
    campos = [("nome", "Nome do funcionário *"), ("dem", "Data de demissão *"), ("cpf", "CPF (opcional)"),
              ("mat", "Matrícula (opcional)")]
    return html.Details([
        html.Summary("Colunas encontradas — confira ou corrija"),
        html.Div([html.Label([rot, dcc.Dropdown(id={"t": "ind-col", "k": k}, options=opcoes, value=cols.get(k) or "",
                                                 clearable=False, className="escolha-auditoria")], className="campo")
                  for k, rot in campos], className="linha-campos"),
        comp.aviso("⚠️ Sem a coluna de data de demissão os cálculos de prazo ficam de fora.", "warn") if not cols.get("dem") else None,
    ], className="det", open=not cols.get("dem"))


def layout(sel, quem):
    meta, corpo = _resultado(sel, None, {}, 10, "mes")
    if meta is None:
        return comp.vazio_sem_auditoria()
    return html.Div([
        dcc.Store(id="ind-upload"), dcc.Store(id="ind-cols", data={}), dcc.Download(id="ind-excel"),
        html.P("Cruza a planilha de desligados com a fatura e a compra: aponta quem ainda está ativo indevidamente e "
               "estima o prejuízo.", className="sub"),
        html.Section([
            html.Div([
                dcc.Upload(html.Div([html.B("Outra planilha de desligados"),
                                     html.Span("Opcional — substitui a da Importação · xlsx, xls ou csv", className="mut")]),
                           id="ind-arquivo", className="up", accept=".xlsx,.xls,.csv", multiple=False),
                html.Div([
                    html.Label(["Prazo para exclusão após a demissão (dias)",
                                dcc.Input(id="ind-prazo", type="number", min=1, max=90, step=1, value=10, className="inp")],
                               className="campo"),
                    html.Label(["Cobertura depois da demissão",
                                dcc.RadioItems(id="ind-cobertura", value="mes", className="chips", options=[
                                    {"label": " Até o último dia do mês da demissão", "value": "mes"},
                                    {"label": " Só até a data da demissão", "value": "data"}])], className="campo"),
                ], style={"display": "grid", "gap": "12px"}),
            ], className="grid2", style={"marginBottom": 0}),
            html.Div(id="ind-mapa"),
        ], className="pn bloco"),
        html.Div(corpo, id="ind-corpo"),
    ])


def registrar(app, dep):
    from dash import ALL

    @app.callback(Output("ind-upload", "data"), Output("ind-cols", "data"), Output("ind-mapa", "children"),
                  Input("ind-arquivo", "contents"), State("ind-arquivo", "filename"), prevent_initial_call=True)
    def _arquivo(conteudo, nome):
        if not conteudo:
            return no_update, no_update, no_update
        PASTA_TMP.mkdir(parents=True, exist_ok=True)
        destino = PASTA_TMP / f"desligados_{abs(hash(conteudo)) % 10**10}{Path(nome or 'x.xlsx').suffix}"
        destino.write_bytes(base64.b64decode(conteudo.split(",", 1)[1]))
        raw = _ler_upload(str(destino))
        cols = si.colunas_automaticas(raw) if raw is not None and not raw.empty else {}
        return str(destino), cols, _mapa(str(destino), cols)

    @app.callback(Output("ind-cols", "data", allow_duplicate=True), Input({"t": "ind-col", "k": ALL}, "value"),
                  State({"t": "ind-col", "k": ALL}, "id"), prevent_initial_call=True)
    def _colunas(valores, ids):
        if not ids:
            return no_update
        return {i["k"]: (v or None) for i, v in zip(ids, valores)}

    @app.callback(Output("ind-corpo", "children"), Input("ind-upload", "data"), Input("ind-cols", "data"),
                  Input("ind-prazo", "value"), Input("ind-cobertura", "value"), State("sel", "data"),
                  prevent_initial_call=True)
    def _recalcular(upload, cols, prazo, cobertura, sel):
        return _resultado(sel, upload, cols or {}, prazo, cobertura)[1]

    @app.callback(Output("ind-excel", "data"), Input("ind-exportar", "n_clicks"), State("ind-upload", "data"),
                  State("ind-cols", "data"), State("ind-prazo", "value"), State("ind-cobertura", "value"),
                  State("sel", "data"), prevent_initial_call=True)
    def _excel(_n, upload, cols, prazo, cobertura, sel):
        if not _n:
            return no_update
        df, _s, meta = estado.carregar(sel)
        banco = None if upload else si.desligados_do_banco(meta)
        linhas = si.linhas_do_upload(_ler_upload(upload), cols or {}) if upload else si.linhas_do_banco(banco)
        res = si.analisar(si.mesclar_no_audit(df, linhas, banco, meta["periodo"]), meta["periodo"], linhas,
                          int(prazo or 10), cobertura == "mes")
        return dcc.send_bytes(si.excel(res), f"exclusoes_indevidas_{meta['periodo'].replace('/', '_')}.xlsx")


TELA = Tela("/exclusoes-indevidas", "Exclusões indevidas", layout, registrar)
