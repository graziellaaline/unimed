# -*- coding: utf-8 -*-
"""Tema (receita tema-vidro-e-relevo): pessoal -> padrão do sistema -> padrão da receita.
Lista fechada de valores, validada aqui no servidor: valor estranho vira o padrão."""
from __future__ import annotations

import json
from pathlib import Path

ARQ = Path(__file__).resolve().parent.parent / "dados" / "tema_padrao.json"
VALORES = {"estilo": ("vidro", "relevo"), "modo": ("claro", "escuro"), "destaque": ("azul", "marinho")}
RECEITA = {"estilo": "relevo", "modo": "claro", "destaque": "azul"}


def _limpo(t: dict | None) -> dict:
    t = t if isinstance(t, dict) else {}
    return {k: t[k] for k, ok in VALORES.items() if t.get(k) in ok}


def do_sistema() -> dict:
    try:
        salvo = json.loads(ARQ.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        salvo = {}
    return {**RECEITA, **_limpo(salvo)}


def gravar_do_sistema(t: dict) -> None:
    ARQ.parent.mkdir(parents=True, exist_ok=True)
    ARQ.write_text(json.dumps({**do_sistema(), **_limpo(t)}), encoding="utf-8")


def mesclar(atual: dict | None, parcial: dict | None) -> dict:
    return {**_limpo(atual), **_limpo(parcial)}


def efetivo(pessoal: dict | None) -> dict:
    return {**do_sistema(), **_limpo(pessoal)}
