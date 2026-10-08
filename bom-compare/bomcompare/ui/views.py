"""Viste principali: allineata a pannelli, a coppie, riepilogo e log."""
from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QItemSelectionModel, Qt, pyqtSignal
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QFrame, QGridLayout, QHBoxLayout,
                             QHeaderView, QLabel, QMenu, QPushButton, QScrollArea, QSplitter,
                             QTableView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..core.comparator import ComparisonResult
from ..core.formatting import fmt_money
from ..core.models import ADDED, MODIFIED, REMOVED, UNCHANGED
from .icons import icon
from .table_models import BomTableModel, Col, TableController
from .theme import Theme
from .widgets import DistributionBar, StatCard

OPTIONAL_GROUPS = [
    ("level", "Livello"), ("uom", "Unità di misura"), ("rev", "Revisione"),
    ("sup", "Fornitore"), ("price", "Prezzo"), ("dqty", "Δ Qtà"), ("dpct", "Δ %"),
    ("chg", "Modifiche"),
]


def make_table_view(row_height: int) -> QTableView:
    view = QTableView()
    view.setAlternatingRowColors(False)
    view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    view.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked
                         | QAbstractItemView.EditTrigger.EditKeyPressed)
    view.setWordWrap(False)
    view.setShowGrid(True)
    view.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerItem)
    vh = view.verticalHeader()
    vh.setDefaultSectionSize(row_height)
    vh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
    hh = view.horizontalHeader()
    hh.setHighlightSections(False)
    hh.setSectionsClickable(True)
    hh.setStretchLastSection(True)
    hh.setFixedHeight(30)
    hh.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
    return view


class _SortableMixin:
    """Gestione click intestazione -> ordinamento tramite il controller."""

    ctrl: TableController

    def _handle_sort(self, view: QTableView, cols: list[Col], section: int,
                     all_views: list[QTableView]) -> None:
        col = cols[section]
        state = self.ctrl.sort_state
        if state and state[0].id == col.id:
            if state[1]:
                ascending = False
            else:   # terzo clic: torna all'ordine originale della distinta
                self.ctrl.sort_by(None)
                for v in all_views:
                    v.horizontalHeader().setSortIndicatorShown(False)
                return
        else:
            ascending = True
        self.ctrl.sort_by(col, ascending)
        for v in all_views:
            v.horizontalHeader().setSortIndicatorShown(v is view)
        view.horizontalHeader().setSortIndicator(
            section, Qt.SortOrder.AscendingOrder if ascending else Qt.SortOrder.DescendingOrder)


# --------------------------------------------------------------------------- #
# Vista allineata (un pannello per distinta, scroll sincronizzato)
# --------------------------------------------------------------------------- #
class AlignedView(QWidget, _SortableMixin):
    counts_changed = pyqtSignal(int, int)

    def __init__(self, theme: Theme, row_height: int = 26, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.row_height = row_height
        self.ctrl = TableController(self)
        self.result: ComparisonResult | None = None
        self.views: list[QTableView] = []
        self.models: list[BomTableModel] = []
        self.panel_cols: list[list[Col]] = []
        self.headers: list[QLabel] = []
        self.hidden_groups: set[str] = set()
        self._syncing = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        lay.addWidget(self.splitter)
        self.placeholder = QLabel("Carica almeno due distinte per vedere il confronto.\n"
                                  "Trascina i file nei riquadri in alto oppure usa “Sfoglia…”.")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setObjectName("Muted")
        lay.addWidget(self.placeholder)
        self.splitter.hide()

    # -- costruzione -------------------------------------------------------- #
    def _cols_for_panel(self, i: int, n: int, has_level: bool, has_price: bool) -> list[Col]:
        k = i if i > 0 else 1
        pres = f"present_{i}"
        st = f"status_{k}"
        cols = [
            Col(f"code_{i}", "Codice", f"code_{i}", "text", pres, st, width=118,
                tooltip="Codice articolo"),
            Col(f"desc_{i}", "Descrizione", f"description_{i}", "text", pres, st,
                f"chg_description_{k}", width=210),
        ]
        if has_level:
            cols.append(Col(f"level_{i}", "Liv.", f"level_{i}", "level", pres, st,
                            f"chg_structure_{k}", width=40, optional=True,
                            tooltip="Livello nella distinta multi-livello"))
        cols += [
            Col(f"qty_{i}", "Qtà", f"quantity_{i}", "num", pres, st, f"chg_quantity_{k}",
                width=60, tooltip="Quantità"),
            Col(f"uom_{i}", "U.M.", f"uom_{i}", "text", pres, st, f"chg_uom_{k}",
                width=44, optional=True, tooltip="Unità di misura"),
            Col(f"rev_{i}", "Rev.", f"revision_{i}", "text", pres, st, f"chg_revision_{k}",
                width=44, optional=True, tooltip="Revisione componente"),
            Col(f"sup_{i}", "Fornitore", f"supplier_{i}", "text", pres, st,
                f"chg_supplier_{k}", width=130, optional=True),
        ]
        if has_price:
            cols.append(Col(f"price_{i}", "Prezzo", f"price_{i}", "money", pres, st,
                            f"chg_price_{k}", width=80, optional=True,
                            tooltip="Prezzo unitario"))
        if i > 0:
            cols += [
                Col(f"dqty_{i}", "Δ Qtà", f"delta_qty_{i}", "delta", None, st, width=58,
                    optional=True, tooltip="Differenza quantità rispetto alla distinta precedente"),
                Col(f"dpct_{i}", "Δ %", f"delta_pct_{i}", "pct", None, st, None,
                    f"out_of_tol_{i}", width=64, optional=True,
                    tooltip="Variazione percentuale della quantità (⚠ giallo = fuori tolleranza)"),
                Col(f"status_{i}", "Stato", st, "status", None, st, width=96,
                    tooltip="Stato rispetto alla distinta precedente"),
            ]
        else:
            cols.append(Col(f"status_{i}", "Stato →", st, "status", None, st, width=96,
                            tooltip="Stato del componente nella distinta successiva"))
        if i == n - 1:
            cols.append(Col("note", "Note", None, "note", width=160,
                            tooltip="Annotazioni libere (doppio clic per modificare)"))
        return cols

    def set_result(self, result: ComparisonResult | None, notes: dict[str, str]) -> None:
        self.result = result
        for idx in reversed(range(self.splitter.count())):
            w = self.splitter.widget(idx)
            w.hide()
            w.setParent(None)
            w.deleteLater()
        self.views, self.models, self.panel_cols, self.headers = [], [], [], []
        if result is None:
            self.ctrl.set_data(self.ctrl.df.iloc[0:0], notes, [])
            self.splitter.hide()
            self.placeholder.show()
            return
        self.placeholder.hide()
        self.splitter.show()
        n = result.n
        has_level = result.any_field("level")
        has_price = result.any_field("price")
        search_cols = ["code", "description"] + [f"description_{i}" for i in range(n)]
        self.ctrl.set_data(result.aligned, notes, search_cols)

        for i in range(n):
            cols = self._cols_for_panel(i, n, has_level, has_price)
            panel = QFrame()
            panel.setObjectName("Card")
            pl = QVBoxLayout(panel)
            pl.setContentsMargins(0, 0, 0, 0)
            pl.setSpacing(0)
            header = QLabel()
            header.setTextFormat(Qt.TextFormat.RichText)
            header.setContentsMargins(10, 6, 10, 6)
            self.headers.append(header)
            pl.addWidget(header)
            view = make_table_view(self.row_height)
            model = BomTableModel(self.ctrl, cols, self.theme, view)
            view.setModel(model)
            for c, col in enumerate(cols):
                view.setColumnWidth(c, col.width)
            if i > 0:
                view.verticalHeader().hide()
            pl.addWidget(view)
            self.splitter.addWidget(panel)
            self.views.append(view)
            self.models.append(model)
            self.panel_cols.append(cols)

        for view, cols in zip(self.views, self.panel_cols):
            view.verticalScrollBar().valueChanged.connect(self._sync_scroll)
            view.selectionModel().currentRowChanged.connect(
                lambda cur, _prev, v=view: self._sync_selection(v, cur.row()))
            view.horizontalHeader().sectionClicked.connect(
                lambda s, v=view, c=cols: self._handle_sort(v, c, s, self.views))
            view.horizontalHeader().customContextMenuRequested.connect(
                lambda pos, v=view: self._columns_menu(v, pos))
        self._update_headers()
        self._apply_hidden()
        self.splitter.setSizes([1000] * n)

    def _update_headers(self) -> None:
        if not self.result:
            return
        t = self.theme
        for i, header in enumerate(self.headers):
            color = t.slot_colors[i % len(t.slot_colors)]
            bom = self.result.boms[i]
            header.setText(
                f"<span style='background:{color}; color:white; border-radius:4px;'>"
                f"&nbsp;{i + 1}&nbsp;</span>&nbsp; <b>{self.result.names[i]}</b>"
                f"&nbsp;&nbsp;<span style='color:{t.text_muted}'>{bom.file_name} · "
                f"{bom.row_count} codici</span>")

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        for m in self.models:
            m.set_theme(theme)
        self._update_headers()

    # -- sincronizzazione --------------------------------------------------- #
    def _sync_scroll(self, value: int) -> None:
        if self._syncing:
            return
        self._syncing = True
        for v in self.views:
            v.verticalScrollBar().setValue(value)
        self._syncing = False

    def _sync_selection(self, source: QTableView, row: int) -> None:
        if self._syncing or row < 0:
            return
        self._syncing = True
        for v in self.views:
            if v is not source:
                idx = v.model().index(row, 0)
                v.selectionModel().setCurrentIndex(
                    idx, QItemSelectionModel.SelectionFlag.ClearAndSelect
                    | QItemSelectionModel.SelectionFlag.Rows)
        self._syncing = False

    # -- colonne visibili --------------------------------------------------- #
    def _columns_menu(self, view: QTableView, pos) -> None:
        menu = QMenu(self)
        menu.addSection("Colonne visibili (tutti i pannelli)")
        present = {c.id.rsplit("_", 1)[0] for cols in self.panel_cols for c in cols}
        for key, label in OPTIONAL_GROUPS:
            if key not in present:
                continue
            act = menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(key not in self.hidden_groups)
            act.toggled.connect(lambda on, k=key: self.set_group_visible(k, on))
        menu.exec(view.horizontalHeader().mapToGlobal(pos))

    def set_group_visible(self, key: str, visible: bool) -> None:
        if visible:
            self.hidden_groups.discard(key)
        else:
            self.hidden_groups.add(key)
        self._apply_hidden()

    def _apply_hidden(self) -> None:
        for view, cols in zip(self.views, self.panel_cols):
            for c, col in enumerate(cols):
                view.setColumnHidden(c, col.optional and
                                     col.id.rsplit("_", 1)[0] in self.hidden_groups)

    # -- filtri ------------------------------------------------------------- #
    def apply_filter(self, mode: str, text: str) -> None:
        if self.result is None:
            return
        al = self.ctrl.df
        column = {"diff": "any_diff", "added": "any_added", "removed": "any_removed",
                  "modified": "any_modified", "tol": "any_tol"}.get(mode)
        mask = al[column].to_numpy(dtype=bool) if column else None
        self.ctrl.apply_filter(mask, text)
        self.counts_changed.emit(len(self.ctrl.positions), len(al))

    def refresh(self) -> None:
        for v in self.views:
            v.viewport().update()

    def selected_keys(self) -> list[str]:
        if not self.views:
            return []
        rows = {i.row() for i in self.views[0].selectionModel().selectedRows()}
        keys = self.ctrl.column("key")
        return [keys[int(self.ctrl.positions[r])] for r in sorted(rows)]


# --------------------------------------------------------------------------- #
# Vista a coppie (dettaglio A -> B)
# --------------------------------------------------------------------------- #
class PairView(QWidget, _SortableMixin):
    counts_changed = pyqtSignal(int, int)
    pair_changed = pyqtSignal(object)

    def __init__(self, theme: Theme, row_height: int = 26, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.ctrl = TableController(self)
        self.result: ComparisonResult | None = None
        self.notes: dict[str, str] = {}
        self.cols: list[Col] = []
        self._filter = ("all", "")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 0)
        top = QHBoxLayout()
        top.addWidget(QLabel("Confronto:"))
        self.combo = QComboBox()
        self.combo.setMinimumWidth(380)
        self.combo.setToolTip("Scegli quali due distinte confrontare")
        self.combo.currentIndexChanged.connect(self._on_pair_selected)
        top.addWidget(self.combo)
        self.legend = QLabel()
        self.legend.setObjectName("Muted")
        top.addSpacing(12)
        top.addWidget(self.legend, 1)
        lay.addLayout(top)
        self.view = make_table_view(row_height)
        self.model = BomTableModel(self.ctrl, [], theme, self.view)
        self.view.setModel(self.model)
        self.view.horizontalHeader().sectionClicked.connect(
            lambda s: self._handle_sort(self.view, self.cols, s, [self.view]))
        lay.addWidget(self.view)

    @property
    def current_pair(self) -> tuple[int, int] | None:
        data = self.combo.currentData()
        return tuple(data) if data else None

    def set_result(self, result: ComparisonResult | None, notes: dict[str, str]) -> None:
        self.result = result
        self.notes = notes
        prev = self.current_pair
        self.combo.blockSignals(True)
        self.combo.clear()
        if result:
            for pair in result.pair_keys():
                self.combo.addItem(result.pair_label(pair), list(pair))
            if prev and prev in result.pairs:
                self.combo.setCurrentIndex(result.pair_keys().index(prev))
        self.combo.blockSignals(False)
        self._on_pair_selected()

    def select_pair(self, pair: tuple[int, int]) -> None:
        if self.result and pair in self.result.pairs:
            self.combo.setCurrentIndex(self.result.pair_keys().index(pair))

    def _on_pair_selected(self) -> None:
        pair = self.current_pair
        if not self.result or not pair:
            self.model.cols = []
            self.ctrl.set_data(self.ctrl.df.iloc[0:0], self.notes, [])
            self.legend.setText("")
            return
        i, j = pair
        a, b = self.result.names[i], self.result.names[j]
        self.legend.setText(f"A = {a}   ·   B = {b}")
        bi, bj = self.result.boms[i], self.result.boms[j]
        has_level = bi.has("level") or bj.has("level")
        has_price = bi.has("price") or bj.has("price")
        st = "status"
        A, B = "in_a", "in_b"
        cols = [
            Col("status", "Stato", "status", "status", None, st, width=100),
            Col("code", "Codice", "code", "text", None, st, width=120),
            Col("desc", "Descrizione", "description", "text", None, st, "chg_description",
                width=230),
        ]
        if has_level:
            cols += [Col("level_a", "Liv. A", "level_a", "level", A, st, "chg_structure",
                         width=48, optional=True),
                     Col("level_b", "Liv. B", "level_b", "level", B, st, "chg_structure",
                         width=48, optional=True),
                     Col("parent_b", "Padre B", "parent_b", "text", B, st, "chg_structure",
                         width=110, optional=True, tooltip="Assieme padre nella distinta B")]
        cols += [
            Col("qty_a", "Qtà A", "quantity_a", "num", A, st, width=64, tooltip=f"Quantità in {a}"),
            Col("qty_b", "Qtà B", "quantity_b", "num", B, st, "chg_quantity", width=64,
                tooltip=f"Quantità in {b}"),
            Col("dqty", "Δ Qtà", "delta_qty", "delta", None, st, width=64),
            Col("dpct", "Δ %", "delta_pct", "pct", None, st, None, "out_of_tol", width=70),
            Col("uom_a", "U.M. A", "uom_a", "text", A, st, width=52, optional=True),
            Col("uom_b", "U.M. B", "uom_b", "text", B, st, "chg_uom", width=52, optional=True),
            Col("rev_a", "Rev. A", "revision_a", "text", A, st, width=52, optional=True),
            Col("rev_b", "Rev. B", "revision_b", "text", B, st, "chg_revision", width=52,
                optional=True),
            Col("sup_a", "Fornitore A", "supplier_a", "text", A, st, width=140, optional=True),
            Col("sup_b", "Fornitore B", "supplier_b", "text", B, st, "chg_supplier", width=140,
                optional=True),
        ]
        if has_price:
            cols += [
                Col("price_a", "Prezzo A", "price_a", "money", A, st, width=84, optional=True),
                Col("price_b", "Prezzo B", "price_b", "money", B, st, "chg_price", width=84,
                    optional=True),
                Col("impact", "Impatto €", "impact", "money", None, st, width=90,
                    tooltip="Variazione di costo: Qtà B × Prezzo B − Qtà A × Prezzo A"),
            ]
        cols += [
            Col("tol", "⚠", "out_of_tol", "tol", None, st, None, "out_of_tol", width=30,
                tooltip="Fuori tolleranza"),
            Col("chg", "Modifiche", "changes", "text", None, st, width=260),
            Col("note", "Note", None, "note", width=180,
                tooltip="Annotazioni libere (doppio clic per modificare)"),
        ]
        df = self.result.pairs[pair]
        self.model.beginResetModel()
        self.model.cols = cols
        self.cols = cols
        self.model.endResetModel()
        self.ctrl.set_data(df, self.notes, ["code", "description", "description_a"])
        for c, col in enumerate(cols):
            self.view.setColumnWidth(c, col.width)
        self.view.horizontalHeader().setSortIndicatorShown(False)
        self.apply_filter(*self._filter)
        self.pair_changed.emit(pair)

    def apply_filter(self, mode: str, text: str) -> None:
        self._filter = (mode, text)
        if not self.result or not self.current_pair:
            return
        df = self.ctrl.df
        status = df["status"].to_numpy()
        masks = {
            "diff": status != UNCHANGED,
            "added": status == ADDED,
            "removed": status == REMOVED,
            "modified": status == MODIFIED,
            "tol": df["out_of_tol"].to_numpy(dtype=bool) if len(df) else np.array([], bool),
        }
        self.ctrl.apply_filter(masks.get(mode), text)
        self.counts_changed.emit(len(self.ctrl.positions), len(df))

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.model.set_theme(theme)

    def refresh(self) -> None:
        self.view.viewport().update()


# --------------------------------------------------------------------------- #
# Riepilogo
# --------------------------------------------------------------------------- #
class SummaryView(QScrollArea):
    open_pair = pyqtSignal(object)

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.result: ComparisonResult | None = None
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._build_empty()

    def _build_empty(self) -> None:
        w = QLabel("Il riepilogo apparirà dopo il confronto.")
        w.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w.setObjectName("Muted")
        self.setWidget(w)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.set_result(self.result)

    def set_result(self, result: ComparisonResult | None) -> None:
        self.result = result
        if result is None:
            self._build_empty()
            return
        t = self.theme
        root = QWidget()
        lay = QVBoxLayout(root)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(14)
        title = QLabel(f"Riepilogo confronto · tolleranza quantità ±"
                       f"{result.settings.tolerance_pct:g}% · generato il {result.created_at}")
        title.setObjectName("Muted")
        lay.addWidget(title)
        for pair in result.pair_keys():
            s = result.summary(pair)
            card = QFrame()
            card.setObjectName("Card")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 12, 14, 12)
            head = QHBoxLayout()
            lbl = QLabel(result.pair_label(pair))
            lbl.setObjectName("Title")
            head.addWidget(lbl)
            head.addStretch(1)
            btn = QPushButton(icon("pair"), "Apri dettaglio")
            btn.clicked.connect(lambda _c=False, p=pair: self.open_pair.emit(p))
            head.addWidget(btn)
            cl.addLayout(head)
            bar = DistributionBar(t)
            bar.set_counts({ADDED: s["added"], REMOVED: s["removed"],
                            MODIFIED: s["modified"], UNCHANGED: s["unchanged"]})
            cl.addWidget(bar)
            stats = QHBoxLayout()
            for label, key, st, tip in (
                    ("Aggiunti", "added", ADDED, "Componenti nuovi"),
                    ("Eliminati", "removed", REMOVED, "Componenti non più presenti"),
                    ("Modificati", "modified", MODIFIED, "Stesso codice, dati diversi"),
                    ("Invariati", "unchanged", UNCHANGED, "Nessuna differenza")):
                sc = StatCard(label, t.status_fg[st], tip)
                sc.set_value(str(s[key]))
                stats.addWidget(sc)
            stats.addStretch(1)
            cl.addLayout(stats)
            grid = QGridLayout()
            grid.setHorizontalSpacing(30)
            details = [
                ("Cambi quantità", s["qty_changes"]),
                ("Cambi revisione", s["revision_changes"]),
                ("Cambi fornitore", s["supplier_changes"]),
                ("Cambi prezzo", s["price_changes"]),
                ("Spostamenti di struttura", s["structure_changes"]),
                ("⚠ Fuori tolleranza", s["out_of_tolerance"]),
            ]
            if s["impact"] is not None:
                details += [("Costo distinta A", fmt_money(s["cost_a"])),
                            ("Costo distinta B", fmt_money(s["cost_b"])),
                            ("Impatto economico", fmt_money(s["impact"], signed=True))]
            for idx, (name, value) in enumerate(details):
                r, c = divmod(idx, 3)
                n_lbl = QLabel(name)
                n_lbl.setObjectName("Muted")
                v_lbl = QLabel(f"<b>{value}</b>")
                if name == "Impatto economico":
                    color = t.status_fg[REMOVED] if s["impact"] > 0 else t.status_fg[ADDED]
                    v_lbl.setStyleSheet(f"color:{color}; font-size:12pt;")
                grid.addWidget(n_lbl, r, c * 2)
                grid.addWidget(v_lbl, r, c * 2 + 1)
            cl.addLayout(grid)
            lay.addWidget(card)
        lay.addStretch(1)
        self.setWidget(root)


class LogView(QTableWidget):
    """Log delle operazioni con data e ora."""

    def __init__(self, parent=None):
        super().__init__(0, 3, parent)
        self.setHorizontalHeaderLabels(["Data e ora", "Evento", "Dettaglio"])
        self.verticalHeader().hide()
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        hh = self.horizontalHeader()
        hh.setStretchLastSection(True)
        self.setColumnWidth(0, 150)
        self.setColumnWidth(1, 220)

    def set_entries(self, entries: list[dict[str, str]]) -> None:
        self.setRowCount(0)
        for e in entries:
            self.add_entry(e)

    def add_entry(self, entry: dict[str, str]) -> None:
        self.insertRow(0)
        for c, key in enumerate(("timestamp", "event", "detail")):
            item = QTableWidgetItem(entry.get(key, ""))
            item.setToolTip(entry.get(key, ""))
            self.setItem(0, c, item)
