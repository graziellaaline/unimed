# -*- coding: utf-8 -*-
"""A ligação do app com a camada da casa (setrata-casa). Segredo vem do secrets/config.env."""
from __future__ import annotations

from pathlib import Path

from setrata_casa import Config, carregar_env
from setrata_casa.flask import instalar as _instalar

from casa.adaptador import AdaptadorUnimed

RAIZ = Path(__file__).resolve().parent.parent
APP_ID = "auditoria-unimed"


def configuracao() -> Config:
    carregar_env(RAIZ / "secrets" / "config.env")
    import os
    conta = RAIZ / "config" / "serviceaccount.json"
    return Config.do_ambiente(
        "UNIMED",
        app_id=APP_ID,
        nome="Auditoria Unimed",
        url_publica=os.environ.get("UNIMED_PUBLIC_URL", "http://127.0.0.1:8055"),
        pasta_dados=RAIZ / "dados" / "casa",
        pasta_segredos=RAIZ / "secrets",
        pagina_login="/login",
        pagina_inicial="/",
        caminho_da_fila="/",
        nome_curto="Unimed",
        cor="#005584",
        icones="/brand",
        conta_servico=conta if conta.exists() else None,
    )


def ligar(server):
    """Pendura as rotas /_casa/... no Flask do Dash e garante os supremos."""
    cfg = configuracao()
    Path(cfg.pasta_dados).mkdir(parents=True, exist_ok=True)
    casa = _instalar(server, cfg, AdaptadorUnimed())
    casa.no_boot()
    return casa
