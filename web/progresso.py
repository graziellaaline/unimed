# -*- coding: utf-8 -*-
"""Andamento do processamento para a barra do kit (DP.acompanhar lê /api/progresso a cada 0,7 s).
Um processamento por vez: a auditoria grava no mesmo histórico, dois ao mesmo tempo se atropelam."""
from __future__ import annotations

import threading
import time

_trava = threading.Lock()
_estado = {"rodando": False, "fase": "", "feitos": 0, "total": 0, "porcentagem": 0, "erro": "", "inicio": 0.0, "fim": 0.0}


def ocupado() -> bool:
    return _estado["rodando"]


def comecar(total: int) -> bool:
    with _trava:
        if _estado["rodando"]:
            return False
        _estado.update(rodando=True, fase="Começando…", feitos=0, total=total, porcentagem=0, erro="",
                       inicio=time.time(), fim=0.0)
        return True


def etapa(fase: str) -> None:
    with _trava:
        _estado["feitos"] = min(_estado["feitos"] + 1, _estado["total"] or 1)
        _estado["fase"] = fase
        _estado["porcentagem"] = int(100 * (_estado["feitos"] - 1) / max(_estado["total"], 1))


def terminar(erro: str = "") -> None:
    with _trava:
        _estado.update(rodando=False, erro=erro, porcentagem=100, fim=time.time())


def ler() -> dict:
    with _trava:
        d = dict(_estado)
    d["decorrido_s"] = round(((d["fim"] or time.time()) - d["inicio"]) if d["inicio"] else 0, 1)
    return {k: d[k] for k in ("rodando", "fase", "feitos", "total", "porcentagem", "erro", "decorrido_s")}
