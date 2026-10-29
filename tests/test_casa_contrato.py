# -*- coding: utf-8 -*-
"""Suíte de contrato da camada da casa (setrata-casa) contra este app.

Os mesmos testes que passam em todos os apps da casa. Reprovou = o defeito está no que mudou
AQUI (adaptador, sessão, trava), não no pacote. Roda com dados em pasta temporária: a suíte liga
e desliga a porta de manutenção e grava feedback."""
import secrets
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

pytest.importorskip("setrata_casa")


def test_contrato_da_casa(tmp_path, monkeypatch):
    from flask import Flask
    from setrata_casa import contrato
    from setrata_casa.flask import instalar

    from casa import instalar as ligacao
    from casa.adaptador import AdaptadorUnimed
    from web import usuarios as U

    monkeypatch.setattr(U, "BANCO", tmp_path / "usuarios.sqlite")
    U.garantir()
    segredos = tmp_path / "secrets"
    segredos.mkdir()
    (segredos / "admin-local.txt").write_text(secrets.token_urlsafe(18), encoding="utf-8")

    cfg = ligacao.configuracao()
    cfg.pasta_dados, cfg.pasta_segredos = tmp_path / "casa", segredos
    cfg.google_client_id = cfg.google_client_secret = ""        # o teste não fala com o Google de verdade
    cfg.pasta_dados.mkdir()

    app = Flask(__name__)
    app.secret_key = secrets.token_hex(16)
    casa = instalar(app, cfg, AdaptadorUnimed())
    casa.no_boot()

    resultado = contrato.rodar(casa, app.test_client)
    print(resultado.relatorio())
    assert resultado.ok > 0 and resultado.falhas == 0, resultado.relatorio()
