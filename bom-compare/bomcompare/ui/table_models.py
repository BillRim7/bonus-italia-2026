"""Modelli tabellari "virtuali" per visualizzare migliaia di righe senza rallentamenti.

Un ``TableController`` possiede il DataFrame, l'ordine delle righe visibili
(filtri + ordinamento) e le note. Più ``BomTableModel`` possono condividere
lo stesso controller: è così che i 3 pannelli della vista allineata restano
sempre sulla stessa riga (stesso codice articolo).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QObject, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont

from ..core.formatting import fmt_level, fmt_money, fmt_num, fmt_pct
from ..core.models import ADDED, MODIFIED, REMOVED, UNCHANGED
from .theme import Theme

STATUS_RANK = {ADDED: 0, REMOVED: 1, MODIFIED: 2, UNCHANGED: 3, "": 4}
STATUS_ICON = {ADDED: "＋ ", REMOVED: "－ ", MODIFIED: "✎ ", UNCHANGED: "", "": ""}


@dataclass
class Col:
    """Definizione di una colonna visualizzata."""

    id: str
    header: str
    src: str | None = None          # colonna del DataFrame
    kind: str = "text"              # text|num|delta|pct|money|level|status|note|tol
    present: str | None = None      # colonna bool: riga presente in questa distinta
    status: str | None = None       # colonna con lo stato che colora la cella
    changed: str | None = None      # colonna bool: valore modificato -> evidenziato
    tol: str | None = None          # colonna bool: fuori tolleranza
    tooltip: str = ""
    width: int = 90
    optional: bool = False          # può essere nascosta dal menu colonne


class TableController(QObject):
    """Dati + filtro + ordinamento condivisi tra uno o più modelli."""

    about_to_reset = pyqtSignal()
    reset_done = pyqtSignal()
    note_changed = pyqtSignal(str, str)   # key, testo

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.df = pd.DataFrame()
        self.notes: dict[str, str] = {}
        self.positions = np.array([], dtype=int)
        self._mask: np.ndarray | None = None
        self._sort: tuple[Col, bool] | None = None
        self._lists: dict[str, list] = {}
        self._text: dict[str, list[str]] = {}
        self.search_blob: pd.Series = pd.Series(dtype=str)

    # -- dati --------------------------------------------------------------- #
    def set_data(self, df: pd.DataFrame, notes: dict[str, str], search_cols: list[str]) -> None:
        self.about_to_reset.emit()
        self.df = df.reset_index(drop=True)
        self.notes = notes
        self._lists.clear()
        self._text.clear()
        self._sort = None
        self._mask = None
        blob = pd.Series([""] * len(self.df), dtype=object)
        for c in search_cols:
            if c in self.df.columns:
                blob = blob + " " + self.df[c].fillna("").astype(str)
        self.search_blob = blob.str.lower()
        self.positions = np.arange(len(self.df))
        self.reset_done.emit()

    def column(self, name: str) -> list:
        if name not in self._lists:
            self._lists[name] = (self.df[name].tolist() if name in self.df.columns
                                 else [None] * len(self.df))
        return self._lists[name]

    def text(self, col: Col, pos: int) -> str:
        """Testo visualizzato (cache per colonna)."""
        if col.kind == "note":
            return self.notes.get(self.column("key")[pos], "")
        cache = self._text.get(col.id)
        if cache is None:
            cache = self._build_text(col)
            self._text[col.id] = cache
        return cache[pos]

    def _build_text(self, col: Col) -> list[str]:
        values = self.column(col.src) if col.src else [None] * len(self.df)
        fmt = {
            "num": fmt_num,
            "delta": lambda v: fmt_num(v, signed=True),
            "pct": fmt_pct,
            "money": fmt_money,
            "level": fmt_level,
            "tol": lambda v: "⚠" if v else "",
        }.get(col.kind)
        if fmt is None:
            out = ["" if v is None or (isinstance(v, float) and np.isnan(v)) else str(v)
                   for v in values]
        else:
            out = [fmt(v) for v in values]
        if col.kind == "status":
            out = [STATUS_ICON.get(s, "") + s for s in out]
        if col.present:
            present = self.column(col.present)
            out = [t if p else "" for t, p in zip(out, present)]
        return out

    # -- filtro e ordinamento ---------------------------------------------- #
    def apply_filter(self, mask: np.ndarray | None, search: str = "") -> None:
        if mask is None:
            mask = np.ones(len(self.df), dtype=bool)
        search = search.strip().lower()
        if search:
            for term in search.split():
                mask = mask & self.search_blob.str.contains(term, regex=False).to_numpy()
        self._mask = mask
        self._recompute()

    def sort_by(self, col: Col | None, ascending: bool = True) -> None:
        self._sort = (col, ascending) if col else None
        self._recompute()

    def _recompute(self) -> None:
        self.about_to_reset.emit()
        mask = self._mask if self._mask is not None else np.ones(len(self.df), dtype=bool)
        pos = np.flatnonzero(mask)
        if self._sort and len(pos):
            col, asc = self._sort
            values = self._sort_values(col).iloc[pos]
            ordered = values.sort_values(ascending=asc, na_position="last", kind="mergesort")
            pos = ordered.index.to_numpy()
        self.positions = pos
        self.reset_done.emit()

    def _sort_values(self, col: Col) -> pd.Series:
        n = len(self.df)
        if col.kind == "note":
            s = pd.Series([self.notes.get(k, "") or None for k in self.column("key")])
            return s.str.lower()
        if col.src is None or col.src not in self.df.columns:
            return pd.Series([None] * n)
        s = self.df[col.src]
        if col.kind == "status":
            s = s.map(STATUS_RANK).astype(float)
        elif col.kind == "tol":
            s = (~s.astype(bool)).astype(float)
        elif col.kind in ("num", "delta", "pct", "money", "level"):
            s = pd.to_numeric(s, errors="coerce")
        else:
            s = s.fillna("").astype(str).str.lower().replace("", np.nan)
        if col.present:
            s = s.where(self.df[col.present].astype(bool))
        return s.reset_index(drop=True)

    @property
    def sort_state(self) -> tuple[Col, bool] | None:
        return self._sort

    def set_note(self, pos: int, text: str) -> None:
        key = self.column("key")[pos]
        text = text.strip()
        if self.notes.get(key, "") == text:
            return
        if text:
            self.notes[key] = text
        else:
            self.notes.pop(key, None)
        self.note_changed.emit(key, text)


class BomTableModel(QAbstractTableModel):
    """Modello Qt che legge dal controller condiviso."""

    def __init__(self, controller: TableController, cols: list[Col], theme: Theme,
                 parent: QObject | None = None):
        super().__init__(parent)
        self.ctrl = controller
        self.cols = cols
        self.set_theme(theme)
        controller.about_to_reset.connect(self.beginResetModel)
        controller.reset_done.connect(self.endResetModel)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self._bg = {k: QBrush(QColor(v)) for k, v in theme.status_bg.items()}
        self._fg = {k: QBrush(QColor(v)) for k, v in theme.status_fg.items()}
        self._absent = QBrush(QColor(theme.absent_bg))
        self._changed = QBrush(QColor(theme.changed_bg))
        self._warn = QBrush(QColor(theme.warn_bg))
        self._warn_fg = QBrush(QColor(theme.warn_fg))
        self._text = QBrush(QColor(theme.text))
        self._muted = QBrush(QColor(theme.text_muted))
        self._bold = QFont()
        self._bold.setBold(True)
        self._italic = QFont()
        self._italic.setItalic(True)
        if self.rowCount():
            self.dataChanged.emit(self.index(0, 0),
                                  self.index(self.rowCount() - 1, self.columnCount() - 1))

    # -- struttura ---------------------------------------------------------- #
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.ctrl.positions)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.cols)

    def headerData(self, section: int, orientation: Qt.Orientation,  # noqa: N802
                   role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and 0 <= section < len(self.cols):
            col = self.cols[section]
            if role == Qt.ItemDataRole.DisplayRole:
                return col.header
            if role == Qt.ItemDataRole.ToolTipRole:
                return (col.tooltip or col.header) + "\n(clic per ordinare)"
        elif orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole:
            return str(section + 1)
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.isValid() and self.cols[index.column()].kind == "note":
            base |= Qt.ItemFlag.ItemIsEditable
        return base

    def pos_of(self, row: int) -> int:
        return int(self.ctrl.positions[row])

    # -- dati --------------------------------------------------------------- #
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        col = self.cols[index.column()]
        pos = int(self.ctrl.positions[index.row()])
        R = Qt.ItemDataRole

        if role in (R.DisplayRole, R.EditRole):
            text = self.ctrl.text(col, pos)
            if role == R.DisplayRole and col.id.startswith("code") and not text and col.present:
                st = self._status(col, pos)
                return "— eliminato —" if st == REMOVED else "— non presente —"
            return text

        present = self._present(col, pos)
        status = self._status(col, pos)
        if role == R.BackgroundRole:
            if not present:
                return self._absent
            if col.tol and self.ctrl.column(col.tol)[pos]:
                return self._warn
            if col.changed and status == MODIFIED and self.ctrl.column(col.changed)[pos]:
                return self._changed
            return self._bg.get(status)
        if role == R.ForegroundRole:
            if not present:
                return self._muted
            if col.tol and self.ctrl.column(col.tol)[pos]:
                return self._warn_fg
            if col.kind == "status" or col.id.startswith("code"):
                return self._fg.get(status, self._text)
            if status == UNCHANGED:
                return self._muted
            return self._text
        if role == R.FontRole:
            if not present:
                return self._italic
            if col.kind == "status" and status in (ADDED, REMOVED, MODIFIED):
                return self._bold
            if col.changed and status == MODIFIED and self.ctrl.column(col.changed)[pos]:
                return self._bold
            return None
        if role == R.TextAlignmentRole:
            if col.kind in ("num", "delta", "pct", "money"):
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if col.kind in ("level", "tol"):
                return int(Qt.AlignmentFlag.AlignCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if role == R.ToolTipRole:
            return self._tooltip(col, pos, status)
        return None

    def _present(self, col: Col, pos: int) -> bool:
        return bool(self.ctrl.column(col.present)[pos]) if col.present else True

    def _status(self, col: Col, pos: int) -> str:
        return (self.ctrl.column(col.status)[pos] or "") if col.status else ""

    def _tooltip(self, col: Col, pos: int, status: str) -> str | None:
        if col.kind == "note":
            return "Doppio clic per scrivere una nota su questo componente"
        changes_col = col.status.replace("status", "changes") if col.status else None
        parts = []
        if status:
            parts.append(f"Stato: {status}")
        if changes_col and changes_col in self.ctrl.df.columns:
            ch = self.ctrl.column(changes_col)[pos]
            if ch:
                parts.append("Modifiche:" + "".join(f"\n  • {p}" for p in str(ch).split("; ")))
        if col.tol and self.ctrl.column(col.tol)[pos]:
            parts.append("⚠ Variazione quantità oltre la tolleranza impostata")
        note = self.ctrl.notes.get(self.ctrl.column("key")[pos])
        if note:
            parts.append(f"Nota: {note}")
        text = self.ctrl.text(col, pos)
        if text and len(text) > 25:
            parts.insert(0, text)
        return "\n".join(parts) if parts else None

    def setData(self, index: QModelIndex, value: Any,  # noqa: N802
                role: int = Qt.ItemDataRole.EditRole) -> bool:
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        col = self.cols[index.column()]
        if col.kind != "note":
            return False
        self.ctrl.set_note(self.pos_of(index.row()), str(value or ""))
        self.dataChanged.emit(index, index)
        return True
