"""Storico locale (SQLite): versioni di distinte e confronti salvati."""
from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .models import BOMData, now_str

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    machine     TEXT,
    role        TEXT,
    label       TEXT,
    source_path TEXT,
    rows        INTEGER,
    data_hash   TEXT,
    payload     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_snap_hash ON snapshots(data_hash);
CREATE TABLE IF NOT EXISTS comparisons (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    title       TEXT,
    machine     TEXT,
    names       TEXT,
    summary     TEXT,
    project     TEXT NOT NULL
);
"""


class HistoryStore:
    """Accesso al database dello storico (thread principale)."""

    def __init__(self, db_path: Path, max_snapshots: int = 1000):
        self.db_path = Path(db_path)
        self.max_snapshots = max_snapshots
        with closing(self._connect()) as con, con:
            con.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    # -- distinte ----------------------------------------------------------- #
    def add_snapshot(self, bom: BOMData, machine: str = "", label: str = "") -> int | None:
        """Salva una versione della distinta. Evita duplicati identici."""
        digest = bom.content_hash()
        with closing(self._connect()) as con, con:
            row = con.execute(
                "SELECT id FROM snapshots WHERE data_hash=? AND machine=? AND role=?",
                (digest, machine, bom.role)).fetchone()
            if row:
                return None
            cur = con.execute(
                "INSERT INTO snapshots(created_at, machine, role, label, source_path,"
                " rows, data_hash, payload) VALUES (?,?,?,?,?,?,?,?)",
                (now_str(), machine, bom.role, label or bom.file_name, bom.source_path,
                 bom.row_count, digest, json.dumps(bom.to_dict(), ensure_ascii=False)))
            self._prune(con)
            log.info("Snapshot storico salvato (id=%s, %s)", cur.lastrowid, bom.role)
            return cur.lastrowid

    def _prune(self, con: sqlite3.Connection) -> None:
        con.execute("DELETE FROM snapshots WHERE id NOT IN "
                    "(SELECT id FROM snapshots ORDER BY id DESC LIMIT ?)",
                    (self.max_snapshots,))

    def list_snapshots(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as con:
            rows = con.execute("SELECT id, created_at, machine, role, label, source_path, rows"
                               " FROM snapshots ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

    def get_snapshot(self, snap_id: int) -> BOMData:
        with closing(self._connect()) as con:
            row = con.execute("SELECT payload FROM snapshots WHERE id=?", (snap_id,)).fetchone()
        if not row:
            raise KeyError(snap_id)
        return BOMData.from_dict(json.loads(row["payload"]))

    def delete_snapshot(self, snap_id: int) -> None:
        with closing(self._connect()) as con, con:
            con.execute("DELETE FROM snapshots WHERE id=?", (snap_id,))

    # -- confronti ---------------------------------------------------------- #
    def add_comparison(self, title: str, machine: str, names: list[str],
                       summary: dict[str, Any], project: dict[str, Any]) -> int:
        with closing(self._connect()) as con, con:
            cur = con.execute(
                "INSERT INTO comparisons(created_at, title, machine, names, summary, project)"
                " VALUES (?,?,?,?,?,?)",
                (now_str(), title, machine, json.dumps(names, ensure_ascii=False),
                 json.dumps(summary, ensure_ascii=False),
                 json.dumps(project, ensure_ascii=False)))
            return int(cur.lastrowid)

    def list_comparisons(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as con:
            rows = con.execute("SELECT id, created_at, title, machine, names, summary"
                               " FROM comparisons ORDER BY id DESC").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["names"] = json.loads(d["names"] or "[]")
            d["summary"] = json.loads(d["summary"] or "{}")
            out.append(d)
        return out

    def get_comparison_project(self, comp_id: int) -> dict[str, Any]:
        with closing(self._connect()) as con:
            row = con.execute("SELECT project FROM comparisons WHERE id=?",
                              (comp_id,)).fetchone()
        if not row:
            raise KeyError(comp_id)
        return json.loads(row["project"])

    def delete_comparison(self, comp_id: int) -> None:
        with closing(self._connect()) as con, con:
            con.execute("DELETE FROM comparisons WHERE id=?", (comp_id,))
