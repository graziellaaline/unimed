# -*- coding: utf-8 -*-
"""Gestão de usuários (só admin) — modo RESTRITO: só entra quem foi adicionado aqui.

A equipe do DP entra com a conta Google @setrata. Ao cadastrar, sai o e-mail com o endereço do
sistema e o login (regra dela, 27/10/2026); o botão "Enviar" reenvia. Quem pode o quê é decidido
pela camada da casa (pode_cadastrar / pode_alterar) — esconder botão não é a barreira."""
from __future__ import annotations

from dash import ALL, Input, Output, State, ctx, dcc, html, no_update

from web import comp
from web import usuarios as U
from web.telas import Tela

DESCRICAO = {"admin": "Vê tudo, fecha o mês, cadastra e tira pessoas, faz a triagem dos feedbacks.",
             "analista": "Importa, confere, justifica e fecha o mês. Não mexe em usuários."}


def _lista(dep):
    casa = dep["casa"]
    eu, _ = dep["eu"]()
    linhas = []
    for u in U.todos():
        if u.papel == "manutencao":
            continue
        supremo = u.email.lower() in casa.cfg.supremos
        info = [html.B(u.nome or u.email), html.Div(u.email, className="cap", style={"margin": 0}),
                html.Div(("👑 Administrador da casa (TI)" if supremo else U.PAPEIS.get(u.papel, u.papel))
                         + ("" if u.ativo else " · 🚫 suspenso"), className="cap", style={"margin": 0})]
        if supremo:
            acoes = html.Div("Intocável: é a conta de manutenção da casa.", className="cap")
        else:
            outro = "analista" if u.papel == "admin" else "admin"
            acoes = html.Div([
                html.Button("Tornar analista" if outro == "analista" else "Tornar administrador",
                            id={"t": "us-papel", "id": u.id, "p": outro}, className="btn peq", n_clicks=0),
                html.Button("Suspender" if u.ativo else "Reativar", id={"t": "us-ativo", "id": u.id},
                            className="btn peq" + (" perigo" if u.ativo else ""), n_clicks=0,
                            disabled=u.id == eu.id),
                html.Button("✉ Enviar acesso", id={"t": "us-enviar", "id": u.id}, className="btn peq ghost", n_clicks=0,
                            disabled=not u.ativo),
                html.Button("Excluir", id={"t": "us-excluir", "id": u.id}, className="btn peq ghost", n_clicks=0,
                            disabled=u.id == eu.id),
            ], className="acts")
        linhas.append(html.Div([html.Div(info), acoes], className="pn casa-fb-item cabeca", style={"alignItems": "center"}))
    return linhas


def layout(sel, quem):
    return html.Div([
        dcc.Store(id="us-ver", data=0), dcc.Store(id="us-pedido"), dcc.Store(id="us-excluindo"),
        html.Section([
            html.H2(id="us-excluir-titulo", className="t"),
            html.P(["Esta ação é irreversível. Digite ", html.Code("excluir"), " para confirmar."], className="sub"),
            dcc.Input(id="us-digite", className="inp", placeholder="excluir", autoComplete="off"),
            html.Div([html.Button("Cancelar", id="us-excluir-cancelar", className="btn ghost peq", n_clicks=0),
                      html.Button("Excluir de vez", id="us-excluir-de-vez", className="btn perigo peq", n_clicks=0, disabled=True)],
                     className="acts", style={"marginTop": "10px"}),
        ], id="us-excluir-painel", className="pn bloco", hidden=True),
        html.Section([
            html.H2("Adicionar pessoa", className="t"),
            html.P("Só entra quem estiver nesta lista. Informe o e-mail @setrata.com.br: a pessoa entra com a conta "
                   "Google e recebe um e-mail com o endereço do sistema e o login.", className="sub"),
            html.Div([
                html.Label(["Nome", dcc.Input(id="us-nome", className="inp", autoComplete="off")], className="campo"),
                html.Label(["E-mail @setrata.com.br", dcc.Input(id="us-email", type="email", className="inp",
                                                                 autoComplete="off")], className="campo"),
                html.Label(["Papel", dcc.RadioItems(id="us-papel-novo", value="analista", className="chips",
                                                    options=[{"label": f" {U.PAPEIS[k]}", "value": k} for k in ("analista", "admin")])],
                           className="campo"),
            ], className="linha-campos"),
            html.Div(id="us-papel-explica", className="cap"),
            html.Button("➕ Adicionar e enviar o e-mail de acesso", id="us-adicionar", className="btn azul", n_clicks=0,
                        style={"marginTop": "10px"}),
        ], className="pn bloco"),
        html.Section([html.H2("Quem tem acesso", className="t"),
                      html.P("Excluir é para sempre; para só impedir a entrada, prefira suspender.", className="sub"),
                      html.Div(id="us-lista")], className="pn bloco"),
    ])


def registrar(app, dep):
    casa = dep["casa"]

    def _so_admin():
        if not dep["e_admin"]():
            raise PermissionError("Só administradores mexem em usuários.")
        return dep["eu"]()[0]

    @app.callback(Output("us-papel-explica", "children"), Input("us-papel-novo", "value"))
    def _explica(p):
        txt = DESCRICAO.get(p, "")
        return txt + (" Administrador alcança os dados de todas as pessoas." if p == "admin" else "")

    @app.callback(Output("us-lista", "children"), Input("us-ver", "data"))
    def _listar(_v):
        _so_admin()
        return _lista(dep)

    def _enviar_acesso(eu, email) -> str:
        try:
            casa.enviar_acesso(eu, email)
            return f"E-mail de acesso enviado para {email}."
        except Exception as e:        # noqa: BLE001 — falha suave: o cadastro vale mesmo sem o e-mail
            return f"Cadastro feito, mas o e-mail não saiu: {getattr(e, 'mensagem', e)}"

    @app.callback(Output("us-ver", "data", allow_duplicate=True), Output("aviso", "data", allow_duplicate=True),
                  Output("us-nome", "value"), Output("us-email", "value"),
                  Input("us-adicionar", "n_clicks"), State("us-nome", "value"), State("us-email", "value"),
                  State("us-papel-novo", "value"), State("us-ver", "data"), prevent_initial_call=True)
    def _adicionar(_n, nome, email, papel, ver):
        if not _n:
            return no_update, no_update, no_update, no_update
        eu = _so_admin()
        email = (email or "").strip().lower()
        if not (nome or "").strip() or "@" not in email:
            return no_update, {"msg": "Preencha o nome e o e-mail.", "tipo": "err"}, no_update, no_update
        motivo = casa.pode_cadastrar(email, admin=papel == "admin")
        if motivo:
            return no_update, {"msg": motivo, "tipo": "err"}, no_update, no_update
        if U.por_email(email):
            return no_update, {"msg": "Esta pessoa já está na lista.", "tipo": "err"}, no_update, no_update
        U.criar(email, nome.strip(), papel)
        return (ver or 0) + 1, {"msg": f"{nome.strip()} adicionada. " + _enviar_acesso(eu, email), "tipo": "ok"}, "", ""

    # Sim/Não do kit antes das ações que tiram acesso; o pedido volta pelo us-pedido
    app.clientside_callback(
        """async function (papel, ativo, excluir) {
            var t = window.dash_clientside.callback_context.triggered_id;
            if (!t || !window.DP) { return window.dash_clientside.no_update; }
            var cliques = [].concat(papel, ativo, excluir).some(function (n) { return n; });
            if (!cliques) { return window.dash_clientside.no_update; }
            if (t.t === "us-excluir") {
                var ok = await DP.confirmar("Excluir esta pessoa de vez? Para só impedir a entrada, use Suspender.");
                if (!ok) { return window.dash_clientside.no_update; }
                return {acao: "excluir", id: t.id, em: Date.now()};
            }
            if (t.t === "us-ativo" || (t.t === "us-papel" && t.p === "admin")) {
                var pergunta = t.t === "us-ativo" ? "Confirmar a mudança de acesso desta pessoa?" :
                    "Tornar administrador? Administrador alcança os dados de todas as pessoas.";
                if (!(await DP.confirmar(pergunta))) { return window.dash_clientside.no_update; }
            }
            return {acao: t.t, id: t.id, p: t.p || "", em: Date.now()};
        }""",
        Output("us-pedido", "data"),
        Input({"t": "us-papel", "id": ALL, "p": ALL}, "n_clicks"), Input({"t": "us-ativo", "id": ALL}, "n_clicks"),
        Input({"t": "us-excluir", "id": ALL}, "n_clicks"), prevent_initial_call=True)

    @app.callback(Output("us-ver", "data", allow_duplicate=True), Output("aviso", "data", allow_duplicate=True),
                  Input("us-pedido", "data"), Input({"t": "us-enviar", "id": ALL}, "n_clicks"), State("us-ver", "data"),
                  prevent_initial_call=True)
    def _agir(pedido, enviar, ver):
        eu = _so_admin()
        if isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get("t") == "us-enviar":
            if not any(enviar or []):
                return no_update, no_update
            alvo = U.por_id(ctx.triggered_id["id"])
            return no_update, {"msg": _enviar_acesso(eu, alvo.email).replace("Cadastro feito, mas o", "O"), "tipo": "info"}
        if not pedido:
            return no_update, no_update
        alvo = U.por_id(pedido["id"])
        if alvo is None:
            return (ver or 0) + 1, {"msg": "Usuário não encontrado.", "tipo": "err"}
        acao = pedido["acao"]
        if acao == "us-papel":
            motivo = casa.pode_alterar(eu, alvo.email, rebaixar=pedido["p"] != "admin", promover=pedido["p"] == "admin")
            if not motivo:
                U.alterar(alvo.id, papel=pedido["p"])
        elif acao == "us-ativo":
            motivo = casa.pode_alterar(eu, alvo.email, desativar=alvo.ativo)
            if not motivo:
                U.alterar(alvo.id, ativo=not alvo.ativo)
        else:
            return no_update, no_update          # o painel de digitar "excluir" cuida (callback abaixo)
        if motivo:
            return (ver or 0) + 1, {"msg": motivo, "tipo": "err"}
        return (ver or 0) + 1, {"msg": "Feito.", "tipo": "ok"}


def _registrar_exclusao(app, dep):
    casa = dep["casa"]

    @app.callback(Output("us-excluindo", "data"), Output("us-excluir-painel", "hidden"), Output("us-excluir-titulo", "children"),
                  Output("us-digite", "value"),
                  Input("us-pedido", "data"), Input("us-excluir-cancelar", "n_clicks"), prevent_initial_call=True)
    def _abrir(pedido, _c):
        if ctx.triggered_id == "us-excluir-cancelar" or not pedido or pedido.get("acao") != "excluir":
            return None, True, no_update, ""
        alvo = U.por_id(pedido["id"])
        return ({"id": alvo.id}, False, f"Excluir {alvo.nome or alvo.email}?", "") if alvo else (None, True, no_update, "")

    @app.callback(Output("us-excluir-de-vez", "disabled"), Input("us-digite", "value"))
    def _trava(txt):
        return (txt or "").strip().lower() != "excluir"

    @app.callback(Output("us-ver", "data", allow_duplicate=True), Output("aviso", "data", allow_duplicate=True),
                  Output("us-excluir-painel", "hidden", allow_duplicate=True),
                  Input("us-excluir-de-vez", "n_clicks"), State("us-excluindo", "data"), State("us-digite", "value"),
                  State("us-ver", "data"), prevent_initial_call=True)
    def _excluir(_n, alvo_id, txt, ver):
        if not _n:
            return no_update, no_update, no_update
        if not dep["e_admin"]():
            return no_update, {"msg": "Só administradores mexem em usuários.", "tipo": "err"}, True
        if (txt or "").strip().lower() != "excluir" or not alvo_id:   # o servidor confere de novo
            return no_update, {"msg": "Digite excluir para confirmar.", "tipo": "err"}, no_update
        eu = dep["eu"]()[0]
        alvo = U.por_id(alvo_id["id"])
        motivo = casa.pode_alterar(eu, alvo.email, excluir=True) if alvo else "Usuário não encontrado."
        if motivo:
            return (ver or 0) + 1, {"msg": motivo, "tipo": "err"}, True
        U.excluir(alvo.id)
        return (ver or 0) + 1, {"msg": f"{alvo.nome or alvo.email} excluída.", "tipo": "ok"}, True


def _registrar_tudo(app, dep):
    registrar(app, dep)
    _registrar_exclusao(app, dep)


TELA = Tela("/usuarios", "Gestão de usuários", layout, _registrar_tudo, so_admin=True)
