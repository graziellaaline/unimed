# -*- coding: utf-8 -*-
"""Auditoria Unimed em Dash — arranque.

Flask por baixo, com a camada da casa (setrata-casa) pendurada em /_casa/...; o Dash monta as
telas. Sem sessão válida nada passa da tela de entrada: a trava fica no `before_request`, porque
callback do Dash é rota HTTP como outra qualquer.
"""
from __future__ import annotations

import json
import secrets
import sys
from pathlib import Path

import dash
from dash import Input, Output, State, dcc, html
from flask import Flask, abort, jsonify, redirect, request, send_from_directory, session

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from version import __version__  # noqa: E402
from web import usuarios as U  # noqa: E402
from web import tema  # noqa: E402

# ── Flask + segredo da sessão ────────────────────────────────────────────────
server = Flask(__name__, static_folder=str(RAIZ / "static"), static_url_path="/static")


def _chave_sessao() -> str:
    import os
    from setrata_casa import carregar_env
    carregar_env(RAIZ / "secrets" / "config.env")
    if os.environ.get("UNIMED_SECRET_KEY"):
        return os.environ["UNIMED_SECRET_KEY"]
    arq = RAIZ / "secrets" / "chave_sessao.txt"          # máquina de desenvolvimento: gera uma vez
    if not arq.exists():
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(secrets.token_urlsafe(48), encoding="utf-8")
    return arq.read_text(encoding="utf-8").strip()


server.secret_key = _chave_sessao()
server.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                     PERMANENT_SESSION_LIFETIME=60 * 60 * 12, MAX_CONTENT_LENGTH=200 * 1024 * 1024)

U.garantir()
from casa.instalar import ligar  # noqa: E402
from setrata_casa.flask import pedido as _pedido  # noqa: E402

CASA = ligar(server)


def eu():
    """O usuário logado (já conferido pela casa) e se é a sessão da porta de manutenção."""
    return CASA.quem(request, _pedido())


def e_admin() -> bool:
    u, manut = eu()
    return CASA.e_admin(u, manut)


# ── a trava ──────────────────────────────────────────────────────────────────
LIVRES = ("/login", "/_casa/", "/sw.js", "/manifest.json", "/healthz", "/brand/", "/static/", "/assets/",
          "/_versao-app", "/favicon.ico")


@server.before_request
def _trava():
    p = request.path
    if p.startswith(LIVRES) or p == "/api/tema" and request.method == "GET":
        return None
    u, _ = eu()
    if u is not None:
        return None
    if p.startswith(("/_dash-", "/api/", "/_reload-hash")):
        return jsonify({"erro": "Sua sessão expirou. Entre novamente."}), 401
    return redirect("/login?volta=" + p if p != "/" else "/login")


@server.after_request
def _cabecalhos(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    return resp


@server.get("/login")
def _login():
    u, _ = eu()
    if u is not None:
        return redirect("/")
    html_ = (RAIZ / "web" / "paginas" / "login.html").read_text(encoding="utf-8")
    return html_.replace("{{VERSAO}}", __version__)


@server.get("/sair")
def _sair():
    session.clear()
    return redirect("/login")


@server.get("/brand/<path:nome>")
def _brand(nome):
    return send_from_directory(RAIZ / "web" / "brand", nome, max_age=3600)


@server.get("/api/eu")
def _api_eu():
    u, manut = eu()
    return jsonify({"nome": u.nome or u.email, "email": u.email, "papel": u.papel,
                    "papel_rotulo": U.PAPEIS.get(u.papel, u.papel), "foto": u.foto,
                    "admin": CASA.e_admin(u, manut), "manutencao": manut,
                    "supremo": (u.email or "").lower() in CASA.cfg.supremos, "versao": __version__})


@server.route("/api/tema", methods=["GET", "PUT"])
def _api_tema():
    u, _ = eu()
    if request.method == "GET":
        return jsonify({"tema": tema.efetivo(u.tema_dict if u else None), "padrao": tema.do_sistema()})
    corpo = request.get_json(silent=True) or {}
    if corpo.pop("como_padrao", False):
        if not e_admin():
            return jsonify({"erro": "Só administradores mudam o tema padrão."}), 403
        tema.gravar_do_sistema(corpo)
        return jsonify({"tema": tema.efetivo(u.tema_dict), "padrao": tema.do_sistema()})
    if corpo.get("voltar_ao_padrao"):
        U.alterar(u.id, tema="")
        return jsonify({"tema": tema.efetivo(None)})
    novo = tema.mesclar(u.tema_dict, corpo)
    U.alterar(u.id, tema=json.dumps(novo))
    return jsonify({"tema": tema.efetivo(novo)})


@server.get("/api/progresso")
def _api_progresso():
    from web import progresso
    return jsonify(progresso.ler())


# ── aviso de versão do kit (/_versao-app) ────────────────────────────────────
try:
    sys.path.insert(0, r"C:\Projetos\_identidade")
    import versao_web
    versao_web.registrar(server, __version__, changelog=str(RAIZ / "CHANGELOG.md"))
except Exception:                  # no servidor do TI o kit não existe: o aviso fica só com a versão
    @server.get("/_versao-app")
    def _versao_app():
        return jsonify({"versao": __version__, "boot": CASA.cfg.app_id + "-" + str(id(server)), "novidades": []})

# ── Dash ─────────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    server=server,
    assets_folder=str(RAIZ / "web" / "assets"),
    title="Auditoria Unimed",
    update_title=None,
    suppress_callback_exceptions=True,
    external_stylesheets=[f"/static/dp-componentes.css?v={__version__}"],
    external_scripts=[f"/static/dp-componentes.js?v={__version__}"],
)
app.index_string = """<!doctype html>
<html lang="pt-BR" data-estilo="relevo" data-modo="claro" data-destaque="azul">
<head>{%metas%}<title>{%title%}</title>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<link rel="manifest" href="/manifest.json?v=""" + __version__ + """">
<link rel="icon" href="/brand/icon-192.png?v=""" + __version__ + """">
{%favicon%}{%css%}</head>
<body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body></html>"""

from web import moldura  # noqa: E402
from web.telas import TELAS  # noqa: E402

app.layout = moldura.layout


@app.callback(Output("tela", "children"), Output("titulo", "children"), Output("pilula", "children"),
              Input("url", "pathname"), Input("sel", "data"))
def _rotear(caminho, sel):
    u, manut = eu()
    admin = CASA.e_admin(u, manut)
    caminho = caminho or "/"
    tela = TELAS.get(caminho) or TELAS["/"]
    if tela.so_admin and not admin:
        tela = TELAS["/"]
    return tela.layout(sel, {"usuario": u, "admin": admin}), tela.titulo, moldura.pilula(tela.rota, u, admin)


DEP = {"casa": CASA, "eu": eu, "e_admin": e_admin}
moldura.registrar(app, DEP)
for _t in {id(t): t for t in TELAS.values()}.values():
    _t.registrar(app, DEP)


def principal():
    import os
    porta = int(os.environ.get("UNIMED_PORTA", "8055"))
    host = os.environ.get("UNIMED_HOST", "127.0.0.1")
    try:
        from waitress import serve
        serve(server, host=host, port=porta, threads=8)
    except ImportError:
        server.run(host=host, port=porta, debug=False)


if __name__ == "__main__":
    principal()
