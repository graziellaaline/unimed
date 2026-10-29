# -*- coding: utf-8 -*-
"""1 · Importação — recebe os arquivos do mês, mostra as colunas encontradas e processa a auditoria.

Os arquivos enviados ficam numa pasta temporária até o processamento; depois disso a auditoria
guarda a própria cópia (dados/uploads) e o temporário some. A barra de andamento é a do kit."""
from __future__ import annotations

import base64
import tempfile
import uuid
from pathlib import Path

import pandas as pd
from dash import Input, Output, State, dcc, html, no_update

from app import db
from app.regras import _parse_periodo
from web import comp, estado, progresso, servico
from web.telas import Tela

PASTA_TMP = Path(tempfile.gettempdir()) / "auditoria-unimed-importacao"
TIPOS = [  # chave, título, descrição, vários arquivos
    ("contratos", "Funcionários por contrato", "Obrigatório · Excel ou CSV", False),
    ("fatura", "Faturas Unimed", "Quantos arquivos forem · Excel ou CSV", True),
    ("compra", "Compra / lançamento", "Opcional · Excel ou CSV", False),
    ("desligados", "Funcionários desligados", "Opcional · nome e data de demissão", False),
]


def _guardar(conteudos, nomes) -> list:
    PASTA_TMP.mkdir(parents=True, exist_ok=True)
    saida = []
    for c, n in zip(conteudos, nomes):
        destino = PASTA_TMP / f"{uuid.uuid4().hex}{Path(n).suffix.lower()}"
        destino.write_bytes(base64.b64decode(c.split(",", 1)[1]))
        saida.append({"nome": n, "caminho": str(destino)})
    return saida


def _relatorio_desligados(rel: dict):
    if not rel:
        return None
    sem_dt, pend = rel.get("sem_dt", []), rel.get("pendencias", [])
    if not (sem_dt or pend):
        return comp.aviso("✅ Todos os desligados foram vinculados por matrícula e nome, sem inconsistências.", "ok")
    partes = [html.Summary("⚠️ Inconsistências da planilha de desligados")]
    if sem_dt:
        partes += [html.P(f"📅 {len(sem_dt)} desligado(s) sem data de demissão na planilha — a demissão não foi atualizada.",
                          className="sub"), comp.tabela_simples(pd.DataFrame({"Nome": sem_dt}))]
    if pend:
        partes += [html.P(f"⚠️ {len(pend)} funcionário(s) com status desligado e sem data de demissão — revise a planilha.",
                          className="sub"), comp.tabela_simples(pd.DataFrame({"Funcionário": pend}))]
    return html.Details(partes, className="pn bloco det", open=True)


def _bloco_reprocessar(sel):
    _df, stats, meta = estado.carregar(sel)
    alvo = meta if meta else None
    if not alvo:   # o botão existe sempre (a barra de andamento escuta o clique dele), só fica escondido
        return html.Button(id="imp-reprocessar", n_clicks=0, hidden=True)
    arqs = db.carregar_arquivos_auditoria(alvo["id"])
    nomes = []
    for k, t, _d, _v in TIPOS:
        arquivos = [html.Div(a["nome"], className="cap", style={"margin": 0}) for a in arqs.get(k, [])]
        nomes.append(html.Div([html.B(t, style={"display": "block"}), *(arquivos or [html.Div("—", className="cap")])]))
    tem = any(arqs.get(k) for k in ("contratos", "fatura", "compra"))
    return html.Section([
        html.Div([html.Div([html.H2(f"Auditoria aberta: {alvo['periodo']}" + (f" · {alvo['cliente']}" if alvo.get("cliente") else ""),
                                    className="t"),
                            html.P(f"{stats.get('ok', 0)} OK · {stats.get('inconsistente', 0)} inconsistências · "
                                   f"processada em {str(alvo.get('processado_em') or '')[:16].replace('T', ' ')}",
                                   className="sub", style={"margin": 0})]),
                  html.Button(f"↻ Reprocessar {alvo['periodo']} com as regras atuais" if tem else "Reprocessar (sem arquivos guardados)",
                              id="imp-reprocessar", className="btn azul", n_clicks=0, disabled=not tem)], className="cabeca"),
        html.Div(nomes, className="ups", style={"marginBottom": 0}),
    ], className="pn bloco")


def layout(sel, quem):
    return html.Div([
        dcc.Store(id="imp-arquivos", data={k: [] for k, *_ in TIPOS}),
        dcc.Store(id="imp-iniciar"), dcc.Store(id="imp-reproc-iniciar"),
        html.Div(_bloco_reprocessar(sel), id="imp-reproc"),
        html.Section([
            html.H2("Mês e cliente", className="t"),
            html.P("O mês de referência amarra tudo: inclusões, exclusões e histórico. O cliente guarda o "
                   "mapeamento das colunas para os próximos meses.", className="sub"),
            html.Div([
                html.Label(["Mês/ano (obrigatório)",
                            dcc.Input(id="imp-periodo", placeholder="04/2026", className="inp tab-num", debounce=False,
                                      value=(sel or {}).get("periodo", ""))], className="campo"),
                html.Label(["Cliente / empresa (opcional)",
                            dcc.Input(id="imp-cliente", placeholder="Ex.: SETRATA", className="inp",
                                      value=(sel or {}).get("cliente", ""))], className="campo"),
            ], className="linha-campos", style={"marginBottom": 0}),
            html.Div(id="imp-periodo-erro"),
        ], className="pn bloco"),
        html.Section([
            html.H2("Arquivos do mês", className="t"),
            html.Div([dcc.Upload(html.Div([html.B(t), html.Span(d, className="mut"), html.Div(id=f"imp-nome-{k}", className="arq")]),
                                 id=f"imp-up-{k}", className="up", multiple=v, accept=".xlsx,.xls,.csv")
                      for k, t, d, v in TIPOS], className="ups"),
            html.Div(id="imp-previa"),
            html.Div(id="imp-pronto", className="cap"),
            html.Div(html.Button("▶ Processar auditoria", id="imp-processar", className="btn pri", n_clicks=0, disabled=True),
                     style={"marginTop": "12px"}),
        ], className="pn bloco"),
        html.Div(id="imp-resultado"),
    ])


def _resultado_ok(periodo, r):
    s = r["stats"]
    msg = (f"✅ Auditoria {periodo} concluída — {s.get('total', 0)} registros · {s.get('ok', 0)} OK · "
           f"{s.get('inconsistente', 0)} inconsistências"
           + (f" · {r['n_inc']} incluído(s) no mês" if r["n_inc"] else "")
           + (f" · {r['n_desl']} desligado(s) mesclados" if r["n_desl"] else "") + ".")
    return html.Div([comp.aviso(msg, "ok"), _relatorio_desligados(r["relatorio"]),
                     dcc.Link("Ver o resultado em Auditoria e Aprovação", href="/", className="btn azul")])


def _falha(e: Exception):
    return comp.aviso(f"Não deu para processar: {e}", "crit")


def registrar(app, dep):
    for k, _t, _d, varios in TIPOS:
        @app.callback(Output("imp-arquivos", "data", allow_duplicate=True), Output(f"imp-nome-{k}", "children"),
                      Input(f"imp-up-{k}", "contents"), State(f"imp-up-{k}", "filename"), State("imp-arquivos", "data"),
                      prevent_initial_call=True)
        def _receber(conteudo, nome, atuais, _k=k, _v=varios):
            if not conteudo:
                return no_update, no_update
            conteudos, nomes = (conteudo, nome) if _v else ([conteudo], [nome])
            atuais = dict(atuais or {})
            servico.limpar_temporarios(a["caminho"] for a in atuais.get(_k, []))
            atuais[_k] = _guardar(conteudos, nomes)
            rotulo = f"✅ {len(nomes)} arquivo(s)" if _v and len(nomes) > 1 else f"✅ {nomes[0]}"
            return atuais, rotulo

    @app.callback(Output("imp-previa", "children"), Output("imp-processar", "disabled"), Output("imp-pronto", "children"),
                  Output("imp-periodo-erro", "children"),
                  Input("imp-arquivos", "data"), Input("imp-periodo", "value"))
    def _previa(arqs, periodo):
        arqs = arqs or {}
        periodo_ok = bool(periodo) and _parse_periodo(periodo) != (None, None)
        erro = comp.aviso("Formato inválido — use MM/AA ou MM/AAAA, ex.: 04/26 ou 04/2026.", "crit") if periodo and not periodo_ok else None
        if not arqs.get("contratos"):
            pronto = "📋 Envie a planilha de contratos para liberar o processamento."
        elif not periodo_ok:
            pronto = "📅 Preencha o mês de referência (ex.: 04/2026) para liberar o processamento."
        else:
            pronto = ""
        blocos = []
        for titulo, cols, campos in servico.previa_colunas(arqs):
            blocos.append(html.Div([html.B(titulo), html.Div([html.Div(f"{'✅' if c else '⚠️'} {rot}: {c or 'não encontrado'}",
                                                                      className="cap", style={"margin": 0})
                                                             for rot, c in campos.items()]),
                                    html.Details([html.Summary(f"{len(cols)} colunas no arquivo"),
                                                  html.P(" · ".join(map(str, cols)), className="cap")], className="det")],
                                   className="pn kpi"))
        previa = html.Details([html.Summary("🔍 Colunas encontradas automaticamente"), html.Div(blocos, className="ups")],
                              className="det", open=True) if blocos else None
        return previa, not (arqs.get("contratos") and periodo_ok), pronto, erro

    # a barra do kit começa a ler o andamento assim que o botão é clicado
    for botao in ("imp-processar", "imp-reprocessar"):
        app.clientside_callback(
            """function (n) { if (n && window.DP) { DP.toast("Processando…", "progress", true); DP.acompanhar("/api/progresso", true); }
                              return window.dash_clientside.no_update; }""",
            Output(botao, "title"), Input(botao, "n_clicks"), prevent_initial_call=True)

    @app.callback(Output("imp-resultado", "children"), Output("mudou", "data", allow_duplicate=True),
                  Output("sel", "data", allow_duplicate=True), Output("imp-arquivos", "data", allow_duplicate=True),
                  Input("imp-processar", "n_clicks"), State("imp-periodo", "value"), State("imp-cliente", "value"),
                  State("imp-arquivos", "data"), State("mudou", "data"), prevent_initial_call=True)
    def _processar(_n, periodo, cliente, arqs, mudou):
        if not _n:
            return no_update, no_update, no_update, no_update
        arqs, cliente = arqs or {}, (cliente or "").strip()
        if not arqs.get("contratos") or _parse_periodo(periodo or "") == (None, None):
            return comp.aviso("Falta a planilha de contratos ou o mês de referência.", "crit"), no_update, no_update, no_update
        if not progresso.comecar(len(servico.ETAPAS)):
            return comp.aviso("Já tem um processamento em andamento. Espere ele terminar.", "warn"), no_update, no_update, no_update
        caminhos = [a["caminho"] for lista in arqs.values() for a in lista]
        try:
            p_cont = arqs["contratos"][0]["caminho"]
            p_fats = [a["caminho"] for a in arqs.get("fatura", [])]
            p_comp = (arqs.get("compra") or [{}])[0].get("caminho")
            p_desl = (arqs.get("desligados") or [{}])[0].get("caminho")
            r = servico.processar(periodo, cliente, p_cont, p_fats, p_comp, p_desl, progresso.etapa)
            db.salvar_arquivos_auditoria(r["aid"], {k: [{"nome": a["nome"], "origem": a["caminho"]} for a in arqs.get(k, [])]
                                                    for k in ("contratos", "fatura", "compra", "desligados")})
            progresso.terminar()
        except Exception as e:        # noqa: BLE001 — a tela explica; o detalhe vai para o log
            progresso.terminar(str(e))
            server_log(e)
            return _falha(e), no_update, no_update, no_update
        finally:
            servico.limpar_temporarios(caminhos)
        return (_resultado_ok(periodo, r), (mudou or 0) + 1, {"periodo": periodo, "cliente": cliente},
                {k: [] for k, *_ in TIPOS})

    @app.callback(Output("imp-resultado", "children", allow_duplicate=True), Output("mudou", "data", allow_duplicate=True),
                  Input("imp-reprocessar", "n_clicks"), State("sel", "data"), State("mudou", "data"),
                  prevent_initial_call=True)
    def _reprocessar(_n, sel, mudou):
        if not _n:
            return no_update, no_update
        _df, _s, meta = estado.carregar(sel)
        if not meta:
            return comp.aviso("Nenhuma auditoria aberta para reprocessar.", "warn"), no_update
        if not progresso.comecar(len(servico.ETAPAS)):
            return comp.aviso("Já tem um processamento em andamento. Espere ele terminar.", "warn"), no_update
        try:
            r = servico.reprocessar(meta["periodo"], meta.get("cliente", ""), db.carregar_arquivos_auditoria(meta["id"]),
                                    progresso.etapa)
            progresso.terminar()
        except Exception as e:        # noqa: BLE001
            progresso.terminar(str(e))
            server_log(e)
            return _falha(e), no_update
        return _resultado_ok(meta["periodo"], r), (mudou or 0) + 1


def server_log(e: Exception) -> None:
    import logging
    logging.getLogger("auditoria-unimed").exception("processamento falhou: %s", e)


TELA = Tela("/importacao", "Importação", layout, registrar)
