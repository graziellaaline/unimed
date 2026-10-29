# -*- coding: utf-8 -*-
"""A moldura de todas as telas: pílula de ícones (receita menu-micro-pilula), cabeçalho com a
auditoria aberta, botão claro/escuro e o cartão da conta."""
from __future__ import annotations

from dash import ALL, Input, Output, State, ctx, dcc, html, no_update

from version import __version__
from web import estado

ICONES = {
    "importar": '<path d="M12 3v12m0 0-4-4m4 4 4-4"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>',
    "inclusoes": '<circle cx="10" cy="8" r="4"/><path d="M3 20a7 7 0 0 1 14 0"/><path d="M19 8v6m-3-3h6"/>',
    "exclusoes": '<circle cx="10" cy="8" r="4"/><path d="M3 20a7 7 0 0 1 14 0"/><path d="M16 11h6"/>',
    "indevidas": '<path d="M12 3 2 20h20L12 3z"/><path d="M12 10v4m0 3v.01"/>',
    "aprovacao": '<path d="M9 12l2 2 4-4"/><rect x="4" y="3" width="16" height="18" rx="3"/>',
    "historico": '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/>',
    "analises": '<path d="M4 20V10m6 10V4m6 16v-7m4 7H2"/>',
    "usuarios": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><circle cx="17.5" cy="9" r="2.5"/><path d="M16 14.2a5 5 0 0 1 6 4.8"/>',
}

MENU = [  # rota, ícone, nome, número da tela de antes (quem já usa reconhece)
    ("/importacao", "importar", "Importação", "1"),
    ("/inclusoes", "inclusoes", "Inclusões", "2"),
    ("/exclusoes", "exclusoes", "Exclusões", "3"),
    ("/exclusoes-indevidas", "indevidas", "Exclusões indevidas", "4"),
    ("/", "aprovacao", "Auditoria e Aprovação", "5"),
    ("/historico", "historico", "Histórico", "6"),
    ("/analises", "analises", "Análises", "7"),
]


def _svg(nome: str):
    # o Dash não desenha <svg> (nem pelo Markdown): o ícone vai como máscara CSS pintada com
    # currentColor, então segue o tema e o estado ativo sem cor fixa
    from urllib.parse import quote
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" '
           'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' + ICONES[nome] + "</svg>")
    return html.Span(className="ic", style={"--ic": f'url("data:image/svg+xml,{quote(svg)}")'}, **{"aria-hidden": "true"})


def _iniciais(u) -> str:
    partes = [p for p in (u.nome or u.email.split("@")[0]).replace(".", " ").split() if p]
    return "".join(p[0] for p in partes[:2]).upper() or "?"


def pilula(rota_atual: str, u, admin: bool):
    filhos = []
    for rota, ic, nome, num in MENU:
        filhos.append(dcc.Link([_svg(ic), html.Span(num, className="num")], href=rota, title=f"{num} · {nome}",
                               className="on" if rota == rota_atual else ""))
    filhos.append(html.Span(className="sep"))
    if admin:
        filhos.append(dcc.Link(_svg("usuarios"), href="/usuarios", title="Gestão de usuários",
                               className="on" if rota_atual == "/usuarios" else ""))
    filhos.append(html.Span("∴", className="tri", **{"aria-hidden": "true"}))
    return filhos


def _opcoes_auditoria():
    return [{"label": f"{p['periodo']}" + (f" · {p['cliente']}" if p["cliente"] else ""),
             "value": f"{p['periodo']}|{p['cliente']}"} for p in estado.periodos()]


def layout():
    pad = estado.padrao()
    return html.Div([
        dcc.Location(id="url"),
        dcc.Store(id="sel", storage_type="session", data=pad),
        dcc.Store(id="mudou", data=0),          # as telas que gravam algo avisam a moldura por aqui
        dcc.Store(id="aviso"),                  # {msg, tipo}: vira DP.toast do kit (nenhum aviso próprio)
        html.Div(id="aviso-eco", hidden=True),
        html.Nav([html.Button("·", id="bt-eu", className="eu", n_clicks=0,
                              **{"aria-label": "Sua conta", "aria-haspopup": "dialog"}),
                  html.Span(className="sep"),
                  html.Div(id="pilula", style={"display": "contents"})], className="pill", **{"aria-label": "Menu"}),
        html.Div(id="cartao-eu", className="pn cartao-eu", hidden=True, role="dialog", **{"aria-label": "Sua conta"}),
        html.Div([
            html.Header([
                html.Div([html.H1(id="titulo"),
                          html.Div(id="ctx", className="ctx")]),
                html.Div([
                    dcc.Dropdown(id="escolha-auditoria", options=_opcoes_auditoria(),
                                 value=f"{pad.get('periodo', '')}|{pad.get('cliente', '')}" if pad else None,
                                 clearable=False, searchable=False, placeholder="Nenhuma auditoria ainda",
                                 className="escolha-auditoria", style={"minWidth": "210px"}),
                    html.Span(__version__, className="cap", style={"margin": 0}),
                    html.Button("☾ Modo escuro", className="btn ghost peq", **{"data-tema-modo": "1"}),
                ], className="acts"),
            ], className="top"),
            html.Main(id="tela"),
        ], className="casca"),
    ])


def conta(u):
    """O botão da conta no topo da pílula: a foto do Google ou as iniciais."""
    if u.foto:
        return html.Img(src=u.foto, alt="", referrerPolicy="no-referrer"), f"Você: {u.nome or u.email}"
    return _iniciais(u), f"Você: {u.nome or u.email}"


def registrar(app, dep):
    @app.callback(Output("bt-eu", "children"), Output("bt-eu", "title"), Input("url", "pathname"))
    def _conta(_p):
        u, _ = dep["eu"]()
        return conta(u)

    app.clientside_callback(
        """function (a) { if (a && a.msg && window.DP) { DP.toast(a.msg, a.tipo || "ok"); } return ""; }""",
        Output("aviso-eco", "children"), Input("aviso", "data"), prevent_initial_call=True)

    @app.callback(Output("sel", "data"), Input("escolha-auditoria", "value"), State("sel", "data"),
                  prevent_initial_call=True)
    def _escolher(v, atual):
        if not v:
            return no_update
        periodo, _, cliente = v.partition("|")
        novo = {"periodo": periodo, "cliente": cliente}
        return no_update if novo == atual else novo

    @app.callback(Output("escolha-auditoria", "options"), Output("escolha-auditoria", "value"),
                  Input("mudou", "data"), Input("sel", "data"))
    def _lista(_m, sel):
        sel = sel or estado.padrao()
        return _opcoes_auditoria(), (f"{sel.get('periodo', '')}|{sel.get('cliente', '')}" if sel else None)

    @app.callback(Output("ctx", "children"), Input("sel", "data"), Input("mudou", "data"))
    def _contexto(sel, _m):
        df, stats, meta = estado.carregar(sel)
        if df is None:
            return "Nenhuma auditoria carregada. Comece pela Importação."
        partes = [html.Span("Período "), html.B(meta["periodo"], className="tab-num")]
        if meta.get("cliente"):
            partes.append(f" · {meta['cliente']}")
        partes.append(f" · {stats.get('total', 0)} vidas")
        partes.append(html.Span(" · ✅ mês fechado" if meta.get("aprovado") else " · ⚠️ em aberto"))
        return partes

    @app.callback(Output("cartao-eu", "children"), Output("cartao-eu", "hidden"),
                  Input("bt-eu", "n_clicks"), Input("url", "pathname"), State("cartao-eu", "hidden"),
                  prevent_initial_call=True)
    def _cartao(n, _p, escondido):
        eu, CASA = dep["eu"], dep["casa"]
        if ctx.triggered_id != "bt-eu" or not n:
            return no_update, True
        u, manut = eu()
        papel = "👑 Administrador da casa" if (u.email or "").lower() in CASA.cfg.supremos else (
            "⚙️ Administrador" if CASA.e_admin(u, manut) else "Analista do DP")
        corpo = [html.Span("Você", className="mut"),
                 html.Div([html.Div([html.B(u.nome or u.email), html.Div(u.email, className="mut"),
                                     html.Div(papel, className="mut")])], className="linha"),
                 html.Div([dcc.Link("🎨 Meu tema", href="/meu-tema", className="btn peq"),
                           html.A("⏻ Sair", href="/sair", className="btn peq")], className="acts")]
        return corpo, not escondido
