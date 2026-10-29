# -*- coding: utf-8 -*-
"""A única peça da camada da casa escrita neste app: como a Auditoria Unimed guarda gente e
abre sessão. A regra (quem entra, por onde, supremos, porta, triagem) é do `setrata-casa`.
"""
from __future__ import annotations

from typing import Optional

from flask import session

from setrata_casa import Adaptador

from web import usuarios as U
from version import __version__


class AdaptadorUnimed(Adaptador):
    # ── gente ──
    def buscar(self, email: str) -> Optional[U.Usuario]:
        return U.por_email(email)

    def criar(self, email: str, nome: str, *, admin: bool, manutencao: bool = False) -> U.Usuario:
        papel = "manutencao" if manutencao else ("admin" if admin else "analista")
        return U.por_email(email) or U.criar(email, nome, papel)

    def email(self, u) -> str:
        return u.email

    def nome(self, u) -> str:
        return u.nome or u.email

    def ativo(self, u) -> bool:
        return bool(u.ativo)

    def e_admin(self, u) -> bool:
        return u.papel == "admin"

    def tornar_admin(self, u) -> None:
        U.alterar(u.id, papel="admin", ativo=True)

    def conferir_senha(self, u, senha: str) -> bool:
        atual = U.por_id(u.id)
        return U.senha_confere(atual, senha)

    def definir_senha(self, u, senha: Optional[str]) -> None:
        U.alterar(u.id, senha_hash=U.hash_senha(senha) if senha else "")

    def tem_senha(self, u) -> bool:
        atual = U.por_id(u.id)
        return bool(atual and atual.senha_hash)

    def admins(self) -> list:
        return [u.email for u in U.todos() if u.papel == "admin" and u.ativo]

    def definir_foto(self, u, url: str) -> None:
        U.alterar(u.id, foto=url or "")

    # ── sessão: cookie assinado do Flask ──
    def usuario_da_requisicao(self, req):
        uid = session.get("uid")
        if not uid:
            return None, False
        return U.por_id(uid), bool(session.get("manut"))

    def abrir_sessao(self, u, *, manutencao: bool, resposta):
        session.clear()
        session["uid"] = u.id
        session["manut"] = bool(manutencao)
        session.permanent = True
        return resposta

    def versao(self) -> str:
        return __version__

    seletores = {"login_email": "#email", "login_senha": "#senha", "login_entrar": "#entrar",
                 "feedback_chip": "#casaFbChip"}
