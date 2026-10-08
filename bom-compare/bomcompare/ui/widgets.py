"""Widget riutilizzabili: slot distinta (drag & drop), card statistiche, barra filtri."""
from __future__ import annotations

import os

from PyQt6.QtCore import QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from PyQt6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QSizePolicy, QToolButton, QVBoxLayout, QWidget)

from ..core.loader import SUPPORTED_EXTENSIONS
from ..core.models import ADDED, FIELD_LABELS, MODIFIED, REMOVED, UNCHANGED, BOMData
from .icons import icon
from .theme import Theme


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class BomSlotWidget(QFrame):
    """Riquadro per una distinta: accetta file trascinati o selezionati."""

    file_dropped = pyqtSignal(int, str)
    browse_requested = pyqtSignal(int)
    mapping_requested = pyqtSignal(int)
    history_requested = pyqtSignal(int)
    clear_requested = pyqtSignal(int)
    remove_requested = pyqtSignal(int)
    role_changed = pyqtSignal(int, str)

    def __init__(self, index: int, role: str, removable: bool, theme: Theme,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.index = index
        self.theme = theme
        self.bom: BOMData | None = None
        self.setObjectName("SlotCard")
        self.setAcceptDrops(True)
        self.setMinimumWidth(250)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)

        top = QHBoxLayout()
        self.badge = QLabel(str(index + 1))
        self.badge.setFixedSize(24, 24)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(self.badge)
        self.role_edit = QLineEdit(role)
        self.role_edit.setObjectName("RoleEdit")
        self.role_edit.setToolTip("Nome della distinta (clic per modificarlo)")
        self.role_edit.editingFinished.connect(
            lambda: self.role_changed.emit(self.index, self.role_edit.text().strip()))
        top.addWidget(self.role_edit, 1)
        if removable:
            rm = QToolButton()
            rm.setObjectName("Flat")
            rm.setIcon(icon("remove", theme.text_muted))
            rm.setToolTip("Rimuovi questo riquadro")
            rm.clicked.connect(lambda: self.remove_requested.emit(self.index))
            top.addWidget(rm)
        lay.addLayout(top)

        self.file_label = QLabel()
        self.file_label.setWordWrap(False)
        self.file_label.setTextFormat(Qt.TextFormat.PlainText)
        lay.addWidget(self.file_label)
        info_row = QHBoxLayout()
        self.info_label = QLabel()
        self.info_label.setObjectName("Muted")
        info_row.addWidget(self.info_label, 1)
        self.warn_label = QLabel()
        self.warn_label.setPixmap(icon("warning", "#D97706").pixmap(QSize(16, 16)))
        self.warn_label.hide()
        info_row.addWidget(self.warn_label)
        lay.addLayout(info_row)

        btns = QHBoxLayout()
        btns.setSpacing(6)
        self.browse_btn = QPushButton(icon("open"), "Sfoglia…")
        self.browse_btn.setToolTip("Seleziona il file Excel o CSV della distinta")
        self.browse_btn.clicked.connect(lambda: self.browse_requested.emit(self.index))
        self.map_btn = QPushButton(icon("columns"), "Colonne…")
        self.map_btn.setToolTip("Verifica o modifica quali colonne del file usare")
        self.map_btn.clicked.connect(lambda: self.mapping_requested.emit(self.index))
        self.hist_btn = QToolButton()
        self.hist_btn.setObjectName("Flat")
        self.hist_btn.setIcon(icon("history"))
        self.hist_btn.setToolTip("Carica una versione salvata nello storico")
        self.hist_btn.clicked.connect(lambda: self.history_requested.emit(self.index))
        self.clear_btn = QToolButton()
        self.clear_btn.setObjectName("Flat")
        self.clear_btn.setIcon(icon("clear"))
        self.clear_btn.setToolTip("Svuota questo riquadro")
        self.clear_btn.clicked.connect(lambda: self.clear_requested.emit(self.index))
        btns.addWidget(self.browse_btn)
        btns.addWidget(self.map_btn)
        btns.addStretch(1)
        btns.addWidget(self.hist_btn)
        btns.addWidget(self.clear_btn)
        lay.addLayout(btns)
        self.set_theme(theme)
        self.set_bom(None)

    # -- stato -------------------------------------------------------------- #
    @property
    def role(self) -> str:
        return self.role_edit.text().strip() or f"Distinta {self.index + 1}"

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        color = theme.slot_colors[self.index % len(theme.slot_colors)]
        self.badge.setStyleSheet(f"background:{color}; color:white; border-radius:12px;"
                                 "font-weight:700;")
        self.setStyleSheet(f"QFrame#SlotCard {{ border-top: 4px solid {color}; }}")

    def set_bom(self, bom: BOMData | None) -> None:
        self.bom = bom
        self.map_btn.setEnabled(bom is not None and bool(bom.source_path)
                                and os.path.exists(bom.source_path))
        self.clear_btn.setEnabled(bom is not None)
        self.setProperty("empty", bom is None)
        if bom is None:
            self.file_label.setText("⇩  Trascina qui un file Excel o CSV")
            self.info_label.setText("oppure usa il pulsante Sfoglia…")
            self.warn_label.hide()
        else:
            name = bom.file_name
            self.file_label.setText(("📄 " + name) if len(name) < 44 else "📄 …" + name[-42:])
            self.file_label.setToolTip(bom.source_path)
            parts = [f"{bom.row_count} codici"]
            if bom.sheet:
                parts.append(f"foglio «{bom.sheet}»")
            parts.append(f"{len(bom.mapping)} colonne riconosciute")
            self.info_label.setText(" · ".join(parts))
            self.info_label.setToolTip("Colonne usate:\n" + "\n".join(
                f"{FIELD_LABELS[k]} ← {v}" for k, v in bom.mapping.items()))
            self.warn_label.setVisible(bool(bom.warnings))
            self.warn_label.setToolTip("Avvisi di caricamento:\n• " + "\n• ".join(bom.warnings))
        _repolish(self)

    def set_loading(self, loading: bool) -> None:
        self.browse_btn.setEnabled(not loading)
        if loading:
            self.file_label.setText("⏳ Caricamento in corso…")

    # -- drag & drop -------------------------------------------------------- #
    @staticmethod
    def _accepted_path(event) -> str | None:
        md = event.mimeData()
        if md.hasUrls():
            for url in md.urls():
                path = url.toLocalFile()
                if os.path.splitext(path)[1].lower() in SUPPORTED_EXTENSIONS:
                    return path
        return None

    def dragEnterEvent(self, event):  # noqa: N802
        if self._accepted_path(event):
            event.acceptProposedAction()
            self.setProperty("dragOver", True)
            _repolish(self)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):  # noqa: N802
        self.setProperty("dragOver", False)
        _repolish(self)

    def dropEvent(self, event):  # noqa: N802
        self.setProperty("dragOver", False)
        _repolish(self)
        path = self._accepted_path(event)
        if path:
            event.acceptProposedAction()
            self.file_dropped.emit(self.index, path)


class StatCard(QFrame):
    """Card con un numero grande (es. 'Aggiunti 12')."""

    def __init__(self, title: str, color: str, tooltip: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setToolTip(tooltip)
        self.setMinimumWidth(120)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(0)
        self.title = QLabel(title)
        self.title.setObjectName("Muted")
        self.value = QLabel("–")
        self.value.setObjectName("BigNumber")
        lay.addWidget(self.title)
        lay.addWidget(self.value)
        self.set_color(color)

    def set_color(self, color: str) -> None:
        self.value.setStyleSheet(f"color: {color};")
        self.setStyleSheet(f"QFrame#StatCard {{ border-left: 4px solid {color}; }}")

    def set_value(self, text: str) -> None:
        self.value.setText(text)


class DistributionBar(QWidget):
    """Barra orizzontale con la proporzione aggiunti/eliminati/modificati/invariati."""

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.counts: dict[str, int] = {}
        self.setFixedHeight(14)

    def set_counts(self, counts: dict[str, int]) -> None:
        self.counts = counts
        self.update()

    def paintEvent(self, _event):  # noqa: N802
        total = sum(self.counts.values())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        clip = QPainterPath()
        clip.addRoundedRect(rect, 6, 6)
        p.setClipPath(clip)
        p.fillRect(rect, QColor(self.theme.border))
        if total:
            x = rect.left()
            for st in (ADDED, REMOVED, MODIFIED, UNCHANGED):
                w = rect.width() * self.counts.get(st, 0) / total
                color = self.theme.status_fg[st] if st != UNCHANGED else self.theme.border
                p.fillRect(QRectF(x, rect.top(), w, rect.height()), QColor(color))
                x += w
        p.end()


FILTERS = [
    ("all", "Tutti", "Mostra tutti i componenti"),
    ("diff", "Solo differenze", "Nasconde i componenti invariati"),
    ("added", "Aggiunti", "Solo componenti aggiunti (nuovi)"),
    ("removed", "Eliminati", "Solo componenti eliminati"),
    ("modified", "Modificati", "Solo componenti modificati"),
    ("tol", "⚠ Fuori tolleranza", "Solo variazioni di quantità oltre la tolleranza"),
]


class FilterBar(QWidget):
    """Ricerca rapida + filtri per stato."""

    changed = pyqtSignal(str, str)  # modalità, testo ricerca

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Cerca codice o descrizione…  (Ctrl+F)")
        self.search.setClearButtonEnabled(True)
        self.search_action = self.search.addAction(icon("search"),
                                                   QLineEdit.ActionPosition.LeadingPosition)
        self.search.setMinimumWidth(320)
        self.search.setToolTip("Ricerca rapida: più parole = tutte devono essere presenti")
        lay.addWidget(self.search)
        lay.addSpacing(8)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[str, QPushButton] = {}
        for mode, label, tip in FILTERS:
            btn = QPushButton(label)
            btn.setObjectName("Filter")
            btn.setCheckable(True)
            btn.setToolTip(tip)
            btn.setProperty("mode", mode)
            self.group.addButton(btn)
            self.buttons[mode] = btn
            lay.addWidget(btn)
        self.buttons["all"].setChecked(True)
        lay.addStretch(1)
        self.count_label = QLabel()
        self.count_label.setObjectName("Muted")
        lay.addWidget(self.count_label)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._emit)
        self.search.textChanged.connect(lambda _t: self._timer.start())
        self.group.buttonClicked.connect(lambda _b: self._emit())

    def refresh_icons(self) -> None:
        self.search_action.setIcon(icon("search"))

    @property
    def mode(self) -> str:
        btn = self.group.checkedButton()
        return btn.property("mode") if btn else "all"

    @property
    def text(self) -> str:
        return self.search.text()

    def set_mode(self, mode: str) -> None:
        if mode in self.buttons:
            self.buttons[mode].setChecked(True)
            self._emit()

    def _emit(self) -> None:
        self.changed.emit(self.mode, self.text)

    def set_counts(self, shown: int, total: int) -> None:
        self.count_label.setText(f"{shown} di {total} righe")
