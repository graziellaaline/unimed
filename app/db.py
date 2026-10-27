# -*- coding: utf-8 -*-
"""
Persistência em SQLite: histórico de auditorias + justificativas + mapeamentos.
"""
import io
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
import shutil

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "dados" / "historico.db"
UPLOADS_DIR = BASE_DIR / "dados" / "uploads"


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
        CREATE TABLE IF NOT EXISTS justificativas_modelo (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente       TEXT    DEFAULT '',
            funcionario   TEXT,
            descricao     TEXT,
            justificativa TEXT,
            atualizado_em TEXT,
            UNIQUE (cliente, funcionario, descricao) ON CONFLICT REPLACE
        );
        CREATE TABLE IF NOT EXISTS mapeamentos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente       TEXT    NOT NULL,
            tipo          TEXT    NOT NULL,
            mapa_json     TEXT,
            atualizado_em TEXT,
            UNIQUE (cliente, tipo) ON CONFLICT REPLACE
        );
        CREATE TABLE IF NOT EXISTS arquivos_auditoria (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            auditoria_id  INTEGER NOT NULL,
            tipo          TEXT    NOT NULL,
            nome_original TEXT,
            caminho       TEXT    NOT NULL,
            criado_em     TEXT,
            FOREIGN KEY (auditoria_id) REFERENCES auditorias(id)
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


TIPOS_RENOMEADOS = {"Direito sem fatura": "Tem direito, fora da fatura"}


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
    # Nomes de tipo trocados depois (21/10/2026): auditorias antigas continuam
    # gravadas como estavam; só o nome mostrado na tela é o novo.
    if "Tipo Inconsistência" in df.columns:
        for antigo, novo in TIPOS_RENOMEADOS.items():
            df["Tipo Inconsistência"] = df["Tipo Inconsistência"].map(
                lambda v, a=antigo, n=novo: v.replace(a, n) if isinstance(v, str) else v)
    stats = json.loads(stats_json) if stats_json else {}
    meta  = {"id": aid, "aprovado": bool(aprovado),
             "aprovado_em": aprovado_em, "processado_em": proc_em}
    return df, stats, meta


def _chave_periodo(periodo: str) -> tuple:
    """(ano, mês) para ordenação cronológica. Períodos inválidos vão para o fim."""
    try:
        mes_txt, ano_txt = str(periodo or "").strip().split("/", 1)
        mes, ano = int(mes_txt), int(ano_txt)
        if ano < 100:
            ano += 2000
        return (ano, mes)
    except Exception:
        return (-1, -1)


def listar_periodos(cliente: str = "") -> list:
    con = _conn()
    cur = con.cursor()
    cur.execute(
        "SELECT MAX(id) AS id, periodo, cliente, MAX(processado_em) AS ultimo, COUNT(*) AS versoes "
        "FROM auditorias WHERE (cliente=? OR ?='') "
        "GROUP BY periodo, cliente",
        (cliente, cliente)
    )
    rows = cur.fetchall()
    con.close()
    itens = [{"id": r[0], "periodo": r[1], "cliente": r[2],
              "processado_em": (r[3] or "")[:16].replace("T", " "),
              "versoes": r[4]} for r in rows]
    # Ordenação cronológica feita em Python: 'periodo' é texto MM/AAAA, então
    # ORDER BY no SQL colocava 12/2025 na frente de 08/2026 (compara o mês
    # primeiro) — e as telas usam o primeiro item como "auditoria mais recente".
    itens.sort(key=lambda p: (_chave_periodo(p["periodo"]), p["processado_em"]),
               reverse=True)
    return itens


def aprovar_auditoria(auditoria_id: int):
    con = _conn()
    con.execute(
        "UPDATE auditorias SET aprovado=1, aprovado_em=? WHERE id=?",
        (datetime.now().isoformat(), auditoria_id)
    )
    con.commit()
    con.close()


def salvar_arquivos_auditoria(auditoria_id: int, arquivos: dict):
    """
    arquivos = {
      "contratos": [{"nome": "x.xlsx", "origem": "c:/tmp/x.xlsx"}],
      "fatura": [...],
      "compra": [...]
    }
    """
    base = UPLOADS_DIR / f"auditoria_{auditoria_id}"
    base.mkdir(parents=True, exist_ok=True)

    con = _conn()
    con.execute("DELETE FROM arquivos_auditoria WHERE auditoria_id=?", (auditoria_id,))

    for tipo, itens in (arquivos or {}).items():
        for i, item in enumerate(itens or [], start=1):
            origem = Path(item["origem"])
            nome_original = item["nome"]
            destino = base / f"{tipo}_{i}_{origem.name}"
            shutil.copy2(origem, destino)
            con.execute(
                "INSERT INTO arquivos_auditoria (auditoria_id, tipo, nome_original, caminho, criado_em) "
                "VALUES (?, ?, ?, ?, ?)",
                (auditoria_id, tipo, nome_original, str(destino), datetime.now().isoformat())
            )

    con.commit()
    con.close()


def carregar_arquivos_auditoria(auditoria_id: int) -> dict:
    con = _conn()
    cur = con.cursor()
    cur.execute(
        "SELECT tipo, nome_original, caminho FROM arquivos_auditoria WHERE auditoria_id=? ORDER BY id",
        (auditoria_id,)
    )
    rows = cur.fetchall()
    con.close()

    out = {"contratos": [], "fatura": [], "compra": [], "desligados": []}
    for tipo, nome_original, caminho in rows:
        if Path(caminho).exists():
            out.setdefault(tipo, []).append({
                "nome": nome_original,
                "caminho": caminho,
            })
    return out


# ---------------------------------------------------------------------------
# Justificativas
# ---------------------------------------------------------------------------

def chave_inconsistencia(descricao: str) -> str:
    """Mesma inconsistência de mês para mês: o texto sem os valores, que mudam
    todo mês ("Valor empresa (R$ 739.24) difere do contrato (R$ 450.00)")."""
    t = re.sub(r"\d+(?:[.,]\d+)*", "#", str(descricao or "").lower())
    return re.sub(r"\s+", " ", t).strip()


# Justificativa presa ao mês em que foi escrita ("Admissão na referência da
# fatura") não passa para o mês seguinte: lá o problema já é outro.
_SO_DO_MES = re.compile(r"refer[eê]ncia da fatura|m[eê]s de refer[eê]ncia", re.I)


def justificativa_herdavel(justificativa: str) -> bool:
    return bool(str(justificativa or "").strip()) and not _SO_DO_MES.search(justificativa)


# Cliente compara sem maiúscula/espaço: 10/2026 entrou como "SETRATA" e os
# modelos estavam como "Setrata" — a herança não achava nada (21/10/2026).
_MESMO_CLIENTE = "(UPPER(TRIM(cliente))=UPPER(TRIM(?)) OR cliente='')"


def migrar_justificativas(novo_id: int, periodo: str, cliente: str = ""):
    """
    Pré-popula justificativas do novo audit_id a partir de duas fontes, em ordem:

    1. Reprocessamento (mesmo período): copia do audit anterior do mesmo mês —
       garante que aprovações não se percam ao reprocessar.

    2. Mês novo (sem histórico do mesmo período): copia dos modelos salvos
       (justificativas_modelo), que acumulam aprovações de todos os meses anteriores.
       O usuário só precisa validar o que já foi pré-preenchido.

    Em ambos os casos, nunca sobrescreve registros já existentes no novo ID.
    """
    con = _conn()
    cur = con.cursor()

    # ── Fonte 1: mesmo período (reprocessamento) ──────────────────────────────
    cur.execute(
        "SELECT id FROM auditorias WHERE periodo=? "
        "AND (UPPER(TRIM(cliente))=UPPER(TRIM(?)) OR ?='') AND id != ? "
        "ORDER BY processado_em DESC LIMIT 1",
        (periodo, cliente or "", cliente or "", novo_id),
    )
    row = cur.fetchone()

    if row:
        id_anterior = row[0]
        cur.execute(
            "SELECT funcionario, descricao, justificativa FROM justificativas WHERE auditoria_id=?",
            (id_anterior,),
        )
        fontes = cur.fetchall()
    else:
        # ── Fonte 2: modelos persistidos de meses anteriores ─────────────────
        # Só herda quem tem a MESMA inconsistência neste mês (valores à parte):
        # justificativa de um problema não serve para outro.
        cur.execute(
            "SELECT funcionario, descricao, justificativa FROM justificativas_modelo "
            f"WHERE {_MESMO_CLIENTE} ORDER BY atualizado_em DESC",
            (cliente or "",),
        )
        modelos = cur.fetchall()
        cur.execute("SELECT df_json FROM auditorias WHERE id=?", (novo_id,))
        r = cur.fetchone()
        try:
            atual = pd.read_json(io.StringIO(r[0]), orient="records") if r and r[0] else pd.DataFrame()
        except Exception:
            atual = pd.DataFrame()
        pend = {}
        if {"Status", "Funcionário", "Inconsistência"} <= set(atual.columns):
            for _, lin in atual[atual["Status"] == "Inconsistente"].iterrows():
                pend[str(lin["Funcionário"])] = str(lin["Inconsistência"] or "")
        fontes = [(f, pend[f], j) for f, d, j in modelos
                  if f in pend and justificativa_herdavel(j)
                  and chave_inconsistencia(d) == chave_inconsistencia(pend[f])]

    vistos: set = set()
    for func, desc, just in fontes:
        if func in vistos:
            continue
        cur.execute(
            "SELECT COUNT(*) FROM justificativas WHERE auditoria_id=? AND funcionario=?",
            (novo_id, func),
        )
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO justificativas (auditoria_id, funcionario, descricao, justificativa, criado_em) "
                "VALUES (?, ?, ?, ?, ?)",
                (novo_id, func, desc, just, datetime.now().isoformat()),
            )
            vistos.add(func)

    con.commit()
    con.close()


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


def excluir_justificativa(auditoria_id: int, funcionario: str):
    con = _conn()
    con.execute(
        "DELETE FROM justificativas WHERE auditoria_id=? AND funcionario=?",
        (auditoria_id, funcionario)
    )
    con.commit()
    con.close()


def carregar_justificativas(auditoria_id: int) -> dict:
    """Retorna {funcionario: justificativa}"""
    if not auditoria_id:
        return {}
    con = _conn()
    cur = con.cursor()
    cur.execute(
        "SELECT funcionario, justificativa FROM justificativas WHERE auditoria_id=?",
        (auditoria_id,)
    )
    rows = cur.fetchall()
    con.close()
    return {r[0]: r[1] for r in rows}


def carregar_justificativas_por_periodo(periodo: str, cliente: str = "") -> tuple:
    """
    Busca as justificativas do audit mais recente do período que TENHA justificativas salvas.
    Retorna (auditoria_id, {funcionario: justificativa}).
    Fallback quando a sessão aponta para um audit_id sem justificativas.
    """
    con = _conn()
    cur = con.cursor()
    cur.execute(
        "SELECT j.auditoria_id, j.funcionario, j.justificativa "
        "FROM justificativas j "
        "JOIN auditorias a ON a.id = j.auditoria_id "
        "WHERE a.periodo=? AND (a.cliente=? OR ?='') "
        "ORDER BY a.processado_em DESC",
        (periodo, cliente or "", cliente or ""),
    )
    rows = cur.fetchall()
    con.close()
    if not rows:
        return None, {}
    aid_encontrado = rows[0][0]
    return aid_encontrado, {r[1]: r[2] for r in rows if r[0] == aid_encontrado}


def salvar_justificativa_modelo(cliente: str, funcionario: str,
                                descricao: str, justificativa: str):
    con = _conn()
    con.execute(
        "INSERT OR REPLACE INTO justificativas_modelo (cliente, funcionario, descricao, justificativa, atualizado_em) "
        "VALUES (?, ?, ?, ?, ?)",
        (cliente or "", funcionario, descricao, justificativa, datetime.now().isoformat())
    )
    con.commit()
    con.close()


def carregar_justificativa_modelo(cliente: str, funcionario: str, descricao: str) -> str:
    con = _conn()
    cur = con.cursor()
    cur.execute(
        "SELECT descricao, justificativa FROM justificativas_modelo "
        f"WHERE {_MESMO_CLIENTE} AND funcionario=? "
        "ORDER BY CASE WHEN cliente='' THEN 1 ELSE 0 END, atualizado_em DESC",
        (cliente or "", funcionario)
    )
    linhas = cur.fetchall()
    con.close()
    chave = chave_inconsistencia(descricao)
    return next((j for d, j in linhas
                 if chave_inconsistencia(d) == chave and justificativa_herdavel(j)), "")


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
