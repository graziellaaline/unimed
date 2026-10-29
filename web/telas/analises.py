# -*- coding: utf-8 -*-
"""7 · Análises — custos, desvios e inconsistências por grupo, e a evolução entre os meses."""
from __future__ import annotations

import pandas as pd
from dash import html

from web import comp, estado, servico
from web.telas import Tela

TOP = 15


def _bloco(titulo, conteudo, total=None):
    nota = html.P(f"Mostrando os {TOP} maiores de {total}.", className="cap") if total and total > TOP else None
    return html.Div([html.H2(titulo, className="t"), conteudo, nota], className="pn")


def _barras(d: pd.DataFrame, grupo: str, cols: list, fmt: str):
    if d is None or d.empty:
        return html.P("Sem dados para exibir.", className="cap")
    top = d.head(TOP)
    return comp.barras_h([[r[grupo], *[r[c] for c in cols]] for _, r in top.iterrows()], fmt,
                         series=cols if len(cols) > 1 else None)


def layout(sel, quem):
    df, stats, meta = estado.carregar(sel)
    if df is None:
        return comp.vazio_sem_auditoria()
    partes = [html.Div([comp.kpi("Total", stats.get("total", 0)), comp.kpi("✅ OK", stats.get("ok", 0)),
                        comp.kpi("⚠️ Inconsistentes", stats.get("inconsistente", 0)),
                        comp.kpi("Total fatura", comp.brl(stats.get("total_fatura", 0)), destaque=True),
                        comp.kpi("Total compra", comp.brl(stats.get("total_compra", 0)))], className="kpis")]

    # custos
    custos = []
    for grupo, titulo in (("Departamento", "Custo por departamento"), ("Empresa", "Custo por empresa"),
                          ("Contrato Adm.", "Custo por contrato adm.")):
        g, cols = servico.gastos_por(df, grupo)
        custos.append(_bloco(titulo, _barras(g, grupo, cols, "brl0"), len(g)))
    partes += [html.H2("Custos", className="t", style={"margin": "6px 0 12px"}), html.Div(custos, className="grid2")]

    # desvios
    dif_c = pd.to_numeric(df.get("Dif. Contrato x Compra", 0), errors="coerce").fillna(0)
    dif_f = pd.to_numeric(df.get("Dif. Fatura x Compra", 0), errors="coerce").fillna(0)
    partes += [html.H2("Desvios — contrato x compra e fatura x compra", className="t", style={"margin": "6px 0 12px"}),
               html.Div([comp.kpi("Desvio contrato x compra", comp.brl(dif_c.sum())),
                         comp.kpi("Desvio fatura x compra", comp.brl(dif_f.sum())),
                         comp.kpi("Registros com desvio", int(((dif_c.abs() > 0.01) | (dif_f.abs() > 0.01)).sum()))],
                        className="kpis")]
    desv = []
    for grupo in ("Departamento", "Contrato Adm."):
        d, cols = servico.desvios_por(df, grupo)
        desv.append(_bloco(f"Desvios por {grupo.lower()}", _barras(d, grupo, cols, "brl0"), len(d)))
    partes.append(html.Div(desv, className="grid2"))
    det, total = servico.maiores_desvios(df)
    partes.append(html.Section([
        html.H2("Registros com maior desvio", className="t"),
        comp.grade("an-desvios", det, "grade_desvios", moeda=servico.MOEDA, larguras={"Funcionário": 220}, altura=420)
        if not det.empty else html.P("Nenhum registro com desvio de valor neste período.", className="cap"),
        html.P(f"Os {len(det)} maiores de {total} registro(s) com divergência.", className="cap") if total else None,
    ], className="pn bloco"))

    # inconsistências
    inc = []
    for grupo in ("Departamento", "Empresa", "Contrato Adm."):
        i = servico.inconsistencias_por(df, grupo)
        inc.append(_bloco(f"Inconsistências por {grupo.lower()}", _barras(i, grupo, ["Qtd."], "num"), len(i)))
    t = servico.inconsistencias_por_tipo(df)
    inc.insert(1, _bloco("Inconsistências por tipo", _barras(t, "Tipo", ["Qtd."], "num")))
    partes += [html.H2("Inconsistências", className="t", style={"margin": "6px 0 12px"}), html.Div(inc, className="grid2")]

    # evolução
    ev = servico.evolucao(meta.get("cliente", ""))
    partes.append(html.H2("Evolução entre os meses", className="t", style={"margin": "6px 0 12px"}))
    if len(ev) <= 1:
        partes.append(comp.aviso("Ainda não há outros meses processados para comparar.", "info"))
    else:
        rot = lambda p: p[:3] + p[-2:] if len(p) == 7 else p  # 09/2026 -> 09/26
        partes.append(html.Div([
            _bloco("Total da fatura por mês", comp.colunas_tempo([(rot(r["Período"]), r["Total Fatura"]) for _, r in ev.iterrows()], "brl0")),
            _bloco("Total da compra por mês", comp.colunas_tempo([(rot(r["Período"]), r["Total Compra"]) for _, r in ev.iterrows()], "brl0")),
            _bloco("Inconsistências por mês", comp.colunas_tempo([(rot(r["Período"]), r["Inconsistentes"]) for _, r in ev.iterrows()], "num")),
        ], className="grid2"))
    return html.Div(partes)


TELA = Tela("/analises", "Análises", layout)
