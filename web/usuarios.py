# -*- coding: utf-8 -*-
"""Quem pode entrar na Auditoria Unimed (modo RESTRITO: só quem o admin adicionou).

Banco próprio (`dados/usuarios.sqlite`), separado do histórico das auditorias. A regra de quem
entra por onde é da camada da casa (`setrata-casa`); aqui só se guarda gente.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "dados" / "usuarios.sqlite"

PAPEIS = {
    "admin": "Administrador",
    "analista": "Analista do DP",
    "manutencao": "Manutenção (TI)",
}


@dataclass
class Usuario:
    id: int
    email: str
    nome: str
    papel: str
    ativo: bool
    senha_hash: str
    foto: str
    tema: str

    @property
    def tema_dict(self) -> dict:
        try:
            return json.loads(self.tema or "{}")
        except ValueError:
            return {}


def _conn() -> sqlite3.Connection:
    BANCO.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(BANCO)
    c.row_factory = sqlite3.Row
    return c


def garantir() -> None:
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            nome TEXT NOT NULL DEFAULT '',
            papel TEXT NOT NULL DEFAULT 'analista',
            ativo INTEGER NOT NULL DEFAULT 1,
            senha_hash TEXT NOT NULL DEFAULT '',
            foto TEXT NOT NULL DEFAULT '',
            tema TEXT NOT NULL DEFAULT '',
            criado_em TEXT NOT NULL DEFAULT ''
        )""")
        # auto-migração leve: colunas novas entram aqui com ADD COLUMN
        tem = {r["name"] for r in c.execute("PRAGMA table_info(usuarios)")}
        for col, ddl in (("foto", "TEXT NOT NULL DEFAULT ''"), ("tema", "TEXT NOT NULL DEFAULT ''")):
            if col not in tem:
                c.execute(f"ALTER TABLE usuarios ADD COLUMN {col} {ddl}")


def _de(row) -> Optional[Usuario]:
    if row is None:
        return None
    return Usuario(row["id"], row["email"], row["nome"], row["papel"], bool(row["ativo"]),
                   row["senha_hash"], row["foto"], row["tema"])


def por_email(email: str) -> Optional[Usuario]:
    with _conn() as c:
        return _de(c.execute("SELECT * FROM usuarios WHERE email = ?", ((email or "").strip().lower(),)).fetchone())


def por_id(uid) -> Optional[Usuario]:
    try:
        uid = int(uid)
    except (TypeError, ValueError):
        return None
    with _conn() as c:
        return _de(c.execute("SELECT * FROM usuarios WHERE id = ?", (uid,)).fetchone())


def todos() -> list[Usuario]:
    with _conn() as c:
        return [_de(r) for r in c.execute("SELECT * FROM usuarios ORDER BY lower(nome), email")]


def criar(email: str, nome: str, papel: str = "analista") -> Usuario:
    if papel not in PAPEIS:
        raise ValueError("Papel desconhecido.")
    with _conn() as c:
        c.execute("INSERT INTO usuarios (email, nome, papel, criado_em) VALUES (?, ?, ?, ?)",
                  ((email or "").strip().lower(), (nome or "").strip(), papel,
                   datetime.now(timezone.utc).isoformat(timespec="seconds")))
    return por_email(email)


def alterar(uid: int, **campos) -> None:
    permitidos = {"nome", "papel", "ativo", "senha_hash", "foto", "tema"}
    campos = {k: v for k, v in campos.items() if k in permitidos}
    if not campos:
        return
    if "papel" in campos and campos["papel"] not in PAPEIS:
        raise ValueError("Papel desconhecido.")
    if "ativo" in campos:
        campos["ativo"] = 1 if campos["ativo"] else 0
    sets = ", ".join(f"{k} = ?" for k in campos)
    with _conn() as c:
        c.execute(f"UPDATE usuarios SET {sets} WHERE id = ?", (*campos.values(), int(uid)))


def excluir(uid: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM usuarios WHERE id = ?", (int(uid),))


def hash_senha(senha: str) -> str:
    return generate_password_hash(senha, method="pbkdf2:sha256:600000")


def senha_confere(u: Usuario, senha: str) -> bool:
    return bool(u and u.senha_hash and senha) and check_password_hash(u.senha_hash, senha)
