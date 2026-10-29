# -*- coding: utf-8 -*-
"""As telas. Cada módulo expõe TELA (rota, título, layout, registrar)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class Tela:
    rota: str
    titulo: str
    layout: Callable
    registrar: Callable = lambda app, dep: None
    so_admin: bool = False


from web.telas import (aprovacao, analises, exclusoes, historico, importacao, inclusoes,  # noqa: E402
                       indevidas, meu_tema, usuarios)

TELAS = {t.rota: t for t in (aprovacao.TELA, importacao.TELA, inclusoes.TELA, exclusoes.TELA, indevidas.TELA,
                              historico.TELA, analises.TELA, usuarios.TELA, meu_tema.TELA)}
