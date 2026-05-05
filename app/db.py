# -*- coding: utf-8 -*-
"""
Persistência em SQLite: histórico de auditorias + justificativas + mapeamentos.
"""
import io
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "dados" / "historico.db"


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def _garantir_tabelas():
    con = _conn()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS auditorias (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            periodo       TEXT    NOT NULL,
            cliente       TEXT    DEFAULT '',
            processado_em TEXT,
            df_json       TEXT,
            stats_json    TEXT,
            aprovado      INTEGER DEFAULT 0,
            aprovado_em   TEXT
        );
        CREATE TABLE IF NOT EXISTS justificativas (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            auditoria_id  INTEGER NOT NULL,
            funcionario   TEXT,
            descricao     TEXT,
            justificativa TEXT,
            criado_em     TEXT,
            FOREIGN KEY (auditoria_id) REFERENCES auditorias(id)
        );
        CREATE TABLE IF NOT EXISTS mapeamentos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente       TEXT    NOT NULL,
            tipo          TEXT    NOT NULL,
            mapa_json     TEXT,
            atualizado_em TEXT,
            UNIQUE (cliente, tipo) ON CONFLICT REPLACE
        );
    """)
    con.commit()
    con.close()


_garantir_tabelas()


# ---------------------------------------------------------------------------
# Auditorias
# ---------------------------------------------------------------------------

def salvar_auditoria(df: pd.DataFrame, stats: dict,
                     periodo: str, cliente: str = "") -> int:
    con = _conn()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO auditorias (periodo, cliente, processado_em, df_json, stats_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (periodo, cliente, datetime.now().isoformat(),
         df.to_json(orient="records", force_ascii=False),
         json.dumps(stats, ensure_ascii=False))
    )
    rowid = cur.lastrowid
    con.commit()
    con.close()
    return rowid


def carregar_auditoria(periodo: str, cliente: str = "") -> tuple:
    con = _conn()
    cur = con.cursor()
    cur.execute(
        "SELECT id, df_json, stats_json, aprovado, aprovado_em, processado_em "
        "FROM auditorias WHERE periodo=? AND (cliente=? OR ?='') "
        "ORDER BY processado_em DESC LIMIT 1",
        (periodo, cliente, cliente)
    )
    row = cur.fetchone()
    con.close()
    if not row:
        return None, None, None
    aid, df_json, stats_json, aprovado, aprovado_em, proc_em = row
    try:
        df = pd.read_json(io.StringIO(df_json), orient="records") if df_json else pd.DataFrame()
    except Exception:
        df = pd.DataFrame()
    stats = json.loads(stats_json) if stats_json else {}
    meta  = {"id": aid, "aprovado": bool(aprovado),
             "aprovado_em": aprovado_em, "processado_em": proc_em}
    return df, stats, meta


def listar_periodos(cliente: str = "") -> list:
    con = _conn()
    cur = con.cursor()
    cur.execute(
        "SELECT periodo, cliente, MAX(processado_em) AS ultimo, COUNT(*) AS versoes "
        "FROM auditorias WHERE (cliente=? OR ?='') "
        "GROUP BY periodo, cliente ORDER BY periodo DESC",
        (cliente, cliente)
    )
    rows = cur.fetchall()
    con.close()
    return [{"periodo": r[0], "cliente": r[1],
             "processado_em": (r[2] or "")[:16].replace("T", " "),
             "versoes": r[3]} for r in rows]


def aprovar_auditoria(auditoria_id: int):
    con = _conn()
    con.execute(
        "UPDATE auditorias SET aprovado=1, aprovado_em=? WHERE id=?",
        (datetime.now().isoformat(), auditoria_id)
    )
    con.commit()
    con.close()


# ---------------------------------------------------------------------------
# Justificativas
# ---------------------------------------------------------------------------

def salvar_justificativa(auditoria_id: int, funcionario: str,
                         descricao: str, justificativa: str):
    con = _conn()
    # Upsert manual — substitui se já existe para o mesmo funcionário/auditoria
    con.execute(
        "DELETE FROM justificativas WHERE auditoria_id=? AND funcionario=?",
        (auditoria_id, funcionario)
    )
    con.execute(
        "INSERT INTO justificativas (auditoria_id, funcionario, descricao, justificativa, criado_em) "
        "VALUES (?, ?, ?, ?, ?)",
        (auditoria_id, funcionario, descricao, justificativa, datetime.now().isoformat())
    )
    con.commit()
    con.close()


def carregar_justificativas(auditoria_id: int) -> dict:
    """Retorna {funcionario: justificativa}"""
    con = _conn()
    cur = con.cursor()
    cur.execute(
        "SELECT funcionario, justificativa FROM justificativas WHERE auditoria_id=?",
        (auditoria_id,)
    )
    rows = cur.fetchall()
    con.close()
    return {r[0]: r[1] for r in rows}


# ---------------------------------------------------------------------------
# Mapeamentos de colunas
# ---------------------------------------------------------------------------

def salvar_mapeamento(cliente: str, tipo: str, mapa: dict):
    if not cliente:
        return
    con = _conn()
    con.execute(
        "INSERT OR REPLACE INTO mapeamentos (cliente, tipo, mapa_json, atualizado_em) "
        "VALUES (?, ?, ?, ?)",
        (cliente, tipo, json.dumps(mapa, ensure_ascii=False), datetime.now().isoformat())
    )
    con.commit()
    con.close()


def carregar_mapeamento(cliente: str, tipo: str) -> dict:
    if not cliente:
        return {}
    con = _conn()
    cur = con.cursor()
    cur.execute(
        "SELECT mapa_json FROM mapeamentos WHERE cliente=? AND tipo=? "
        "ORDER BY atualizado_em DESC LIMIT 1",
        (cliente, tipo)
    )
    row = cur.fetchone()
    con.close()
    return json.loads(row[0]) if row else {}
