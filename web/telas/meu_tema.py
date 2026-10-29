# -*- coding: utf-8 -*-
"""Meu tema (receita tema-vidro-e-relevo): cada pessoa escolhe estilo, modo e cor de destaque.
Os cliques são tratados no navegador (assets/20-tema.js): a prévia aplica na hora, Salvar grava."""
from __future__ import annotations

from dash import html

from web.telas import Tela


def _cartao(estilo: str, nome: str, texto: str):
    return html.Button([html.Div([html.Div(className="previa-painel"), html.Div(className="previa-painel curto")],
                                 className="previa", **{"data-previa": estilo}),
                        html.B(nome), html.Span(texto, className="cap", style={"margin": 0}),
                        html.Span("Em uso", className="tag ok selo-em-uso")],
                       className="pn cartao-tema", **{"data-escolha-estilo": estilo})


def layout(sel, quem):
    admin = quem.get("admin")
    return html.Div([
        html.Section([
            html.H2("Estilo", className="t"),
            html.P("Vale só para você. Clique para ver na hora; Salvar guarda a escolha.", className="sub"),
            html.Div([_cartao("relevo", "Relevo", "Superfícies da cor do fundo, relevo por sombra (neumorphism)."),
                      _cartao("vidro", "Vidro", "Painéis de vidro translúcido sobre fundo com profundidade (glassmorphism).")],
                     className="grid2", style={"marginBottom": 0}),
        ], className="pn bloco"),
        html.Section([
            html.H2("Modo e cor de destaque", className="t"),
            html.Div([html.Button("☀ Claro", className="chip", **{"data-escolha-modo": "claro"}),
                      html.Button("☾ Escuro", className="chip", **{"data-escolha-modo": "escuro"})], className="chips"),
            html.Div([html.Button("Azul Setrata", className="chip", **{"data-escolha-destaque": "azul"}),
                      html.Button("Azul-noite", className="chip", **{"data-escolha-destaque": "marinho"})], className="chips"),
            html.P("A paleta é a do kit DP Setrata; o destaque azul-noite vale no modo claro.", className="cap"),
        ], className="pn bloco"),
        html.Div([
            html.Button("Salvar meu tema", className="btn pri", **{"data-tema-acao": "salvar"}),
            html.Button("Descartar alterações", className="btn ghost", **{"data-tema-acao": "descartar"}),
            html.Button("Voltar ao tema padrão", className="btn ghost", **{"data-tema-acao": "padrao"}),
            html.Button("Salvar como padrão do sistema", className="btn azul", **{"data-tema-acao": "sistema"}) if admin else None,
        ], className="acts"),
    ])


TELA = Tela("/meu-tema", "Meu tema", layout)
