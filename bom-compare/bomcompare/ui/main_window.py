"""Finestra principale dell'applicazione."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QByteArray, QSize, Qt, QThreadPool, QTimer, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence
from PyQt6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QFileDialog, QHBoxLayout,
                             QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox,
                             QProgressBar, QSizePolicy, QTabWidget, QToolBar, QToolButton,
                             QVBoxLayout, QWidget)

from .. import APP_NAME, PROJECT_EXTENSION, __version__
from ..core.comparator import ComparisonResult, CompareSettings, compare_all
from ..core.config import AppConfig, resource_path, user_data_dir
from ..core.history import HistoryStore
from ..core.loader import FILE_DIALOG_FILTER, SUPPORTED_EXTENSIONS, BOMLoadError, build_bom, \
    inspect_file
from ..core.models import BOMData
from ..core.project import ProjectError, ProjectState, load_project, save_project
from ..export.excel_report import export_excel
from ..export.pdf_report import PDF_AVAILABLE, export_pdf
from .dialogs import (EmailDialog, HistoryDialog, MappingDialog, SettingsDialog, TutorialDialog,
                      wait_cursor)
from .icons import icon
from .theme import apply_theme, get_theme
from .views import AlignedView, LogView, PairView, SummaryView
from .widgets import BomSlotWidget, FilterBar
from .workers import FuncTask, LoadTask

log = logging.getLogger(__name__)
PROJECT_FILTER = f"Progetto BOM Compare (*{PROJECT_EXTENSION})"


class MainWindow(QMainWindow):
    def __init__(self, cfg: AppConfig, history: HistoryStore | None):
        super().__init__()
        self.cfg = cfg
        self.history = history
        self.theme = get_theme(cfg.theme)
        self.state = ProjectState(roles=cfg.roles(), boms=[None] * 3,
                                  template=cfg.user.get("template", "Standard"))
        self.result: ComparisonResult | None = None
        self.project_path: str | None = None
        self.dirty = False
        self.raw_tables: dict[int, object] = {}
        self.pool = QThreadPool.globalInstance()
        self._loading: dict[int, int] = {}
        self._tasks: list[LoadTask] = []
        self._themed_actions: list[tuple[QAction, str]] = []
        self.slots: list[BomSlotWidget] = []

        self.setWindowTitle(APP_NAME)
        ico = resource_path("assets", "app.ico")
        self.setWindowIcon(QIcon(str(ico)) if ico.exists() else icon("app", "#2563EB"))
        self.setAcceptDrops(True)
        self.resize(1500, 900)
        self.setMinimumSize(1000, 640)

        self._compare_timer = QTimer(self)
        self._compare_timer.setSingleShot(True)
        self._compare_timer.setInterval(250)
        self._compare_timer.timeout.connect(self.run_compare)

        self._build_actions()
        self._build_menu()
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._rebuild_slots()
        self._restore_geometry()
        self._update_actions()
        self._update_title()

    # ===================================================================== #
    # Costruzione interfaccia
    # ===================================================================== #
    def _act(self, text: str, icon_name: str | None, slot, shortcut=None, tip: str = "") -> QAction:
        act = QAction(text, self)
        if icon_name:
            self._themed_actions.append((act, icon_name))
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        act.setToolTip(tip or text)
        act.setStatusTip(tip or text)
        act.triggered.connect(slot)
        return act

    def _build_actions(self) -> None:
        S = QKeySequence.StandardKey
        self.a_new = self._act("Nuovo", "new", self.new_project, S.New, "Nuovo confronto (Ctrl+N)")
        self.a_open = self._act("Apri…", "open", self.open_project, S.Open,
                                "Apri un progetto salvato (Ctrl+O)")
        self.a_save = self._act("Salva", "save", self.save_project, S.Save,
                                "Salva il progetto (Ctrl+S)")
        self.a_save_as = self._act("Salva con nome…", None, self.save_project_as, S.SaveAs)
        self.a_compare = self._act("Confronta", "compare", self.run_compare, "F5",
                                   "Esegui di nuovo il confronto (F5)")
        self.a_excel = self._act("Esporta Excel", "excel", self.export_excel, "Ctrl+E",
                                 "Crea il report Excel con colori e riepilogo (Ctrl+E)")
        self.a_pdf = self._act("Esporta PDF", "pdf", self.export_pdf, "Ctrl+P",
                               "Crea un report PDF da condividere (Ctrl+P)")
        self.a_email = self._act("Testo e-mail", "email", self.show_email, "Ctrl+M",
                                 "Elenco modifiche pronto da incollare in una e-mail")
        self.a_history = self._act("Storico", "history", lambda: self.show_history(None), "Ctrl+H",
                                   "Versioni salvate delle distinte e confronti precedenti")
        self.a_store = self._act("Salva confronto nello storico", "db", self.store_comparison, None,
                                 "Archivia il confronto corrente nello storico locale")
        self.a_settings = self._act("Impostazioni…", "settings", self.show_settings, "Ctrl+,",
                                    "Tolleranza, campi da confrontare, tema")
        self.a_theme = self._act("Tema chiaro/scuro", "theme", self.toggle_theme, "Ctrl+T",
                                 "Passa dal tema chiaro a quello scuro (Ctrl+T)")
        self.a_help = self._act("Guida rapida", "help", self.show_tutorial, "F1",
                                "Mostra la guida introduttiva (F1)")
        self.a_sample = self._act("Carica dati di esempio", "sample", self.load_samples, None,
                                  "Carica tre distinte fittizie per provare l'applicazione")
        self.a_add_slot = self._act("Aggiungi distinta", "add", self.add_slot, None,
                                    "Aggiungi un riquadro per un'altra distinta")
        self.a_save_tpl = self._act("Salva impostazioni come template…", "template",
                                    self.save_template)
        self.a_logs = self._act("Apri cartella log", "folder", self.open_log_folder)
        self.a_about = self._act("Informazioni", "info", self.show_about)
        self.a_quit = self._act("Esci", None, self.close, S.Quit)
        self.a_search = self._act("Cerca", None, self._focus_search, S.Find)
        self.addAction(self.a_search)
        if not PDF_AVAILABLE:
            self.a_pdf.setToolTip("Esportazione PDF non disponibile (manca reportlab)")

    def _build_menu(self) -> None:
        mb = self.menuBar()
        m = mb.addMenu("&File")
        for a in (self.a_new, self.a_open, None, self.a_save, self.a_save_as, None):
            m.addSeparator() if a is None else m.addAction(a)
        self.recent_menu = m.addMenu("Progetti recenti")
        self.recent_menu.aboutToShow.connect(self._fill_recent)
        m.addSeparator()
        for a in (self.a_excel, self.a_pdf, self.a_email, None, self.a_quit):
            m.addSeparator() if a is None else m.addAction(a)
        m = mb.addMenu("&Confronto")
        for a in (self.a_compare, self.a_add_slot, None, self.a_history, self.a_store, None,
                  self.a_save_tpl, self.a_settings):
            m.addSeparator() if a is None else m.addAction(a)
        m = mb.addMenu("&Visualizza")
        m.addAction(self.a_theme)
        m.addAction(self.a_search)
        m = mb.addMenu("&Aiuto")
        for a in (self.a_help, self.a_sample, None, self.a_logs, self.a_about):
            m.addSeparator() if a is None else m.addAction(a)

    def _build_toolbar(self) -> None:
        tb = QToolBar("Principale")
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(tb)
        for a in (self.a_new, self.a_open, self.a_save, None, self.a_compare, None,
                  self.a_excel, self.a_pdf, self.a_email, None, self.a_history):
            tb.addSeparator() if a is None else tb.addAction(a)
        tb.addSeparator()

        tb.addWidget(self._tb_label("Macchina:"))
        self.machine_edit = QLineEdit()
        self.machine_edit.setPlaceholderText("Modello / matricola")
        self.machine_edit.setToolTip("Nome della macchina: compare nei report e nello storico")
        self.machine_edit.setFixedWidth(150)
        self.machine_edit.textEdited.connect(self._on_machine)
        tb.addWidget(self.machine_edit)
        tb.addWidget(self._tb_label("  Template:"))
        self.template_combo = QComboBox()
        self.template_combo.setToolTip("Impostazioni predefinite per tipo di macchina")
        self.template_combo.setMinimumWidth(170)
        self._fill_templates()
        self.template_combo.currentTextChanged.connect(self._on_template)
        tb.addWidget(self.template_combo)
        tb.addWidget(self._tb_label("  Tolleranza:"))
        self.tol_spin = QDoubleSpinBox()
        self.tol_spin.setRange(0, 1000)
        self.tol_spin.setDecimals(1)
        self.tol_spin.setSuffix(" %")
        self.tol_spin.setToolTip("Evidenzia in giallo le variazioni di quantità oltre questa "
                                 "percentuale (0 = disattivato)")
        self.tol_spin.setValue(float(self.cfg.comparison_settings().get("tolerance_pct", 10)))
        self.tol_spin.valueChanged.connect(self._on_tolerance)
        tb.addWidget(self.tol_spin)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)
        tb.addAction(self.a_theme)
        tb.addAction(self.a_help)

    @staticmethod
    def _tb_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("Muted")
        return lbl

    def _build_central(self) -> None:
        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(10, 10, 10, 6)
        lay.setSpacing(8)

        self.slots_row = QHBoxLayout()
        self.slots_row.setSpacing(10)
        self.slots_container = QHBoxLayout()
        self.slots_container.setSpacing(10)
        self.slots_row.addLayout(self.slots_container, 1)
        self.add_slot_btn = QToolButton()
        self.add_slot_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.add_slot_btn.setText("Aggiungi\ndistinta")
        self.add_slot_btn.setToolTip(self.a_add_slot.toolTip())
        self.add_slot_btn.setIconSize(QSize(20, 20))
        self.add_slot_btn.clicked.connect(self.add_slot)
        self.add_slot_btn.setFixedWidth(84)
        self.add_slot_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.slots_row.addWidget(self.add_slot_btn)
        lay.addLayout(self.slots_row)

        self.filter_bar = FilterBar()
        self.filter_bar.changed.connect(self._apply_filters)
        lay.addWidget(self.filter_bar)

        row_h = int(self.cfg.get("ui.row_height", 26))
        self.tabs = QTabWidget()
        self.aligned_view = AlignedView(self.theme, row_h)
        self.pair_view = PairView(self.theme, row_h)
        self.summary_view = SummaryView(self.theme)
        self.log_view = LogView()
        self.tabs.addTab(self.aligned_view, "Vista allineata")
        self.tabs.addTab(self.pair_view, "Confronto a coppie")
        self.tabs.addTab(self.summary_view, "Riepilogo")
        self.tabs.addTab(self.log_view, "Log modifiche")
        self.tabs.setTabToolTip(0, "Le distinte affiancate, allineate per codice articolo")
        self.tabs.setTabToolTip(1, "Dettaglio completo tra due distinte a scelta")
        self.tabs.setTabToolTip(2, "Statistiche e impatto economico")
        self.tabs.setTabToolTip(3, "Cronologia delle operazioni con data e ora")
        self.tabs.currentChanged.connect(lambda _i: self._update_counts())
        lay.addWidget(self.tabs, 1)

        self.aligned_view.counts_changed.connect(lambda *_: self._update_counts())
        self.pair_view.counts_changed.connect(lambda *_: self._update_counts())
        self.aligned_view.ctrl.note_changed.connect(self._on_note)
        self.pair_view.ctrl.note_changed.connect(self._on_note)
        self.summary_view.open_pair.connect(self._open_pair)
        self.setCentralWidget(central)

    def _build_statusbar(self) -> None:
        sb = self.statusBar()
        self.status_label = QLabel("Pronto. Trascina le distinte nei riquadri in alto.")
        sb.addWidget(self.status_label, 1)
        self.progress = QProgressBar()
        self.progress.setFixedWidth(220)
        self.progress.setRange(0, 100)
        self.progress.hide()
        sb.addPermanentWidget(self.progress)
        offline = QLabel("● Offline – i dati restano su questo computer")
        offline.setObjectName("Muted")
        sb.addPermanentWidget(offline)

    # ===================================================================== #
    # Riquadri distinte
    # ===================================================================== #
    def _rebuild_slots(self) -> None:
        while self.slots_container.count():
            item = self.slots_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.slots = []
        n = max(3, len(self.state.boms))
        while len(self.state.boms) < n:
            self.state.boms.append(None)
        defaults = self.cfg.roles()
        while len(self.state.roles) < n:
            idx = len(self.state.roles)
            self.state.roles.append(defaults[idx] if idx < len(defaults) else f"Distinta {idx + 1}")
        for i in range(n):
            slot = BomSlotWidget(i, self.state.roles[i], removable=i >= 3, theme=self.theme)
            slot.file_dropped.connect(self.load_file)
            slot.browse_requested.connect(self.browse_file)
            slot.mapping_requested.connect(self.edit_mapping)
            slot.history_requested.connect(self.show_history)
            slot.clear_requested.connect(self.clear_slot)
            slot.remove_requested.connect(self.remove_slot)
            slot.role_changed.connect(self._on_role)
            slot.set_bom(self.state.boms[i])
            self.slots_container.addWidget(slot)
            self.slots.append(slot)
        can_add = n < int(self.cfg.get("max_boms", 6))
        self.a_add_slot.setEnabled(can_add)
        self.add_slot_btn.setEnabled(can_add)

    def add_slot(self) -> None:
        if len(self.state.boms) >= int(self.cfg.get("max_boms", 6)):
            return
        self.state.boms.append(None)
        self._rebuild_slots()

    def remove_slot(self, index: int) -> None:
        if index < 3 or index >= len(self.state.boms):
            return
        del self.state.boms[index]
        del self.state.roles[index]
        self.raw_tables = {(k if k < index else k - 1): v for k, v in self.raw_tables.items()
                           if k != index}
        self._rebuild_slots()
        self._mark_dirty()
        self.schedule_compare()

    def clear_slot(self, index: int) -> None:
        bom = self.state.boms[index]
        self.state.boms[index] = None
        self.raw_tables.pop(index, None)
        self.slots[index].set_bom(None)
        if bom:
            self._log("Distinta rimossa", f"{self.slots[index].role}: {bom.file_name}")
        self._mark_dirty()
        self.schedule_compare()

    def _on_role(self, index: int, name: str) -> None:
        name = name or f"Distinta {index + 1}"
        if self.state.roles[index] == name:
            return
        self.state.roles[index] = name
        if self.state.boms[index]:
            self.state.boms[index].role = name
        self._mark_dirty()
        self.schedule_compare()

    # ===================================================================== #
    # Caricamento file
    # ===================================================================== #
    def browse_file(self, index: int) -> None:
        start = self.cfg.user.get("last_dir") or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, f"Seleziona la distinta – {self.slots[index].role}", start, FILE_DIALOG_FILTER)
        if path:
            self.load_file(index, path)

    def load_file(self, index: int, path: str) -> None:
        if index in self._loading:
            return
        self.cfg.user["last_dir"] = os.path.dirname(path)
        self.cfg.save_user()
        slot = self.slots[index]
        slot.set_loading(True)
        self._loading[index] = 0
        self._show_progress(0, f"{slot.role}: apertura file…")
        task = LoadTask(index, path, slot.role, self.cfg.column_aliases(),
                        self.cfg.comparison_settings())
        task.signals.progress.connect(self._on_load_progress)
        task.signals.loaded.connect(self._on_loaded)
        task.signals.needs_mapping.connect(self._on_needs_mapping)
        task.signals.failed.connect(self._on_load_failed)
        self._tasks.append(task)
        self.pool.start(task)

    def _on_load_progress(self, index: int, pct: int, msg: str) -> None:
        self._loading[index] = pct
        role = self.slots[index].role if index < len(self.slots) else ""
        self._show_progress(min(self._loading.values()), f"{role}: {msg}")

    def _finish_loading(self, index: int) -> None:
        self._loading.pop(index, None)
        self._tasks = [t for t in self._tasks
                       if not isinstance(t, LoadTask) or t.slot in self._loading]
        if index < len(self.slots):
            self.slots[index].set_loading(False)
            self.slots[index].set_bom(self.state.boms[index])
        if not self._loading:
            self.progress.hide()

    def _on_loaded(self, index: int, bom: BOMData, rt) -> None:
        self._finish_loading(index)
        self._set_bom(index, bom, rt)

    def _on_load_failed(self, index: int, message: str) -> None:
        self._finish_loading(index)
        self._set_status("Caricamento non riuscito.")
        log.warning("Caricamento fallito (slot %d): %s", index, message)
        QMessageBox.warning(self, "Impossibile caricare la distinta", message)

    def _on_needs_mapping(self, index: int, rt) -> None:
        self._finish_loading(index)
        QMessageBox.information(
            self, "Verifica colonne",
            "Non è stato possibile riconoscere automaticamente la colonna del Codice "
            "articolo.\nNella finestra successiva indica quali colonne usare.")
        self._open_mapping(index, rt)

    def _open_mapping(self, index: int, rt) -> None:
        dlg = MappingDialog(rt, self.cfg.column_aliases(), self.slots[index].role,
                            int(self.cfg.get("ui.preview_rows", 100)), self)
        if dlg.exec() != MappingDialog.DialogCode.Accepted:
            return
        try:
            with wait_cursor():
                bom = build_bom(dlg.rt, self.slots[index].role, self.cfg.comparison_settings())
        except BOMLoadError as exc:
            QMessageBox.warning(self, "Distinta non valida", str(exc))
            return
        self._set_bom(index, bom, dlg.rt)

    def edit_mapping(self, index: int) -> None:
        rt = self.raw_tables.get(index)
        bom = self.state.boms[index]
        if rt is None and bom and bom.source_path and os.path.exists(bom.source_path):
            try:
                with wait_cursor():
                    rt = inspect_file(bom.source_path, self.cfg.column_aliases(),
                                      sheet=bom.sheet, header_row=bom.header_row)
                    rt.mapping = dict(bom.mapping)
            except BOMLoadError as exc:
                QMessageBox.warning(self, "File non disponibile", str(exc))
                return
        if rt is None:
            QMessageBox.information(self, "Colonne", "Il file originale non è disponibile: "
                                    "ricarica la distinta per modificare le colonne.")
            return
        self._open_mapping(index, rt)

    def _set_bom(self, index: int, bom: BOMData, rt=None) -> None:
        bom.role = self.slots[index].role
        self.state.boms[index] = bom
        if rt is not None:
            self.raw_tables[index] = rt
        self.slots[index].set_bom(bom)
        detail = f"{bom.role}: {bom.file_name} ({bom.row_count} codici)"
        if bom.warnings:
            detail += " – " + " ".join(bom.warnings)
        self._log("Distinta caricata", detail)
        self._set_status(f"Caricata «{bom.file_name}»: {bom.row_count} codici.")
        if self.history and self.cfg.user.get(
                "auto_snapshot", self.cfg.get("history.auto_snapshot_on_load", True)):
            try:
                self.history.add_snapshot(bom, self.machine_edit.text().strip())
            except Exception:  # noqa: BLE001 - lo storico non deve bloccare il lavoro
                log.exception("Salvataggio snapshot non riuscito")
        self._mark_dirty()
        self.schedule_compare()

    def dragEnterEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        projects = [p for p in paths if p.lower().endswith(PROJECT_EXTENSION)]
        if projects:
            self.open_project(projects[0])
            return
        files = [p for p in paths if os.path.splitext(p)[1].lower() in SUPPORTED_EXTENSIONS]
        if not files:
            QMessageBox.information(self, "Formato non supportato",
                                    "Trascina file Excel (.xlsx, .xls) o CSV.")
            return
        max_boms = int(self.cfg.get("max_boms", 6))
        files = files[:max_boms]
        while len(self.state.boms) < len(files):
            self.state.boms.append(None)
            self._rebuild_slots()
        empty = [i for i, b in enumerate(self.state.boms) if b is None]
        targets = empty if len(empty) >= len(files) else list(range(len(files)))
        for idx, path in zip(targets, sorted(files)):
            self.load_file(idx, path)

    def load_samples(self) -> None:
        folder = resource_path("sample_data")
        names = ["distinta_1_vecchia.xlsx", "distinta_2_produzione.xlsx",
                 "distinta_3_progettazione.xlsx"]
        missing = [n for n in names if not (folder / n).exists()]
        if missing:
            QMessageBox.warning(self, "Dati di esempio",
                                f"File di esempio non trovati in:\n{folder}")
            return
        if not self.machine_edit.text():
            self.machine_edit.setText("ABC-200")
            self.state.machine = "ABC-200"
        for i, n in enumerate(names):
            self.load_file(i, str(folder / n))

    # ===================================================================== #
    # Confronto
    # ===================================================================== #
    def schedule_compare(self) -> None:
        self._compare_timer.start()

    def run_compare(self) -> None:
        boms = []
        for i, b in enumerate(self.state.boms):
            if b is not None:
                b.role = self.state.roles[i]
                boms.append(b)
        if len(boms) < 2:
            self._set_result(None)
            self._set_status("Carica almeno due distinte per avviare il confronto."
                             if boms else "Pronto. Trascina le distinte nei riquadri in alto.")
            return
        settings = CompareSettings.from_dict(self.cfg.comparison_settings())
        try:
            with wait_cursor():
                result = compare_all(boms, settings)
        except Exception as exc:  # noqa: BLE001
            log.exception("Errore durante il confronto")
            QMessageBox.critical(self, "Errore nel confronto",
                                 f"Si è verificato un errore durante il confronto:\n{exc}")
            return
        self._set_result(result)
        parts = []
        for pair in result.pair_keys()[: result.n - 1]:
            s = result.summary(pair)
            parts.append(f"{result.pair_label(pair)}: +{s['added']} −{s['removed']} "
                         f"✎{s['modified']}")
        self._log("Confronto eseguito", " | ".join(parts))
        self._set_status("Confronto completato. " + "   ".join(parts))

    def _set_result(self, result: ComparisonResult | None) -> None:
        self.result = result
        self.aligned_view.set_result(result, self.state.notes)
        self.pair_view.set_result(result, self.state.notes)
        self.summary_view.set_result(result)
        self._apply_filters(self.filter_bar.mode, self.filter_bar.text)
        self._update_actions()

    def _apply_filters(self, mode: str, text: str) -> None:
        self.aligned_view.apply_filter(mode, text)
        self.pair_view.apply_filter(mode, text)
        self._update_counts()

    def _update_counts(self) -> None:
        view = self.tabs.currentWidget()
        if self.result is None:
            self.filter_bar.count_label.setText("")
        elif view in (self.aligned_view, self.pair_view):
            ctrl = view.ctrl
            self.filter_bar.set_counts(len(ctrl.positions), len(ctrl.df))
        else:
            self.filter_bar.count_label.setText("")

    def _open_pair(self, pair) -> None:
        self.pair_view.select_pair(pair)
        self.tabs.setCurrentWidget(self.pair_view)

    def _on_note(self, key: str, text: str) -> None:
        self._log("Nota modificata", f"{key}: {text or '(rimossa)'}")
        self.aligned_view.refresh()
        self.pair_view.refresh()
        self._mark_dirty()

    def _on_tolerance(self, value: float) -> None:
        overrides = self.cfg.user.setdefault("comparison_overrides", {})
        overrides["tolerance_pct"] = value
        self.cfg.save_user()
        self._mark_dirty()
        self.schedule_compare()

    def _on_machine(self, text: str) -> None:
        self.state.machine = text.strip()
        self._mark_dirty()

    # ===================================================================== #
    # Template
    # ===================================================================== #
    def _fill_templates(self) -> None:
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        for name, tpl in self.cfg.templates.items():
            self.template_combo.addItem(name)
            self.template_combo.setItemData(self.template_combo.count() - 1,
                                            tpl.get("description", ""),
                                            Qt.ItemDataRole.ToolTipRole)
        current = self.cfg.user.get("template", "Standard")
        if self.template_combo.findText(current) >= 0:
            self.template_combo.setCurrentText(current)
        self.template_combo.blockSignals(False)

    def _on_template(self, name: str) -> None:
        if not name:
            return
        self.cfg.user["template"] = name
        overrides = self.cfg.user.setdefault("comparison_overrides", {})
        overrides.pop("tolerance_pct", None)
        overrides.pop("compare_fields", None)
        self.cfg.save_user()
        self.state.template = name
        tpl = self.cfg.templates.get(name, {})
        self.tol_spin.blockSignals(True)
        self.tol_spin.setValue(float(self.cfg.comparison_settings().get("tolerance_pct", 10)))
        self.tol_spin.blockSignals(False)
        if tpl.get("roles"):
            for i, role in enumerate(tpl["roles"][: len(self.slots)]):
                self.slots[i].role_edit.setText(role)
                self.state.roles[i] = role
                if self.state.boms[i]:
                    self.state.boms[i].role = role
        self._log("Template applicato", name)
        self._mark_dirty()
        self.schedule_compare()

    def save_template(self) -> None:
        name, ok = QInputDialog.getText(self, "Salva template",
                                        "Nome del template (es. tipo di macchina):")
        name = name.strip()
        if not ok or not name:
            return
        aliases: dict[str, list[str]] = {}
        for b in self.state.loaded_boms():
            for fld, col in b.mapping.items():
                aliases.setdefault(fld, [])
                if col.lower() not in aliases[fld]:
                    aliases[fld].append(col.lower())
        settings = self.cfg.comparison_settings()
        self.cfg.user.setdefault("user_templates", {})[name] = {
            "description": f"Template utente creato il {datetime.now():%d/%m/%Y}",
            "tolerance_pct": settings.get("tolerance_pct", 10),
            "compare_fields": settings.get("compare_fields", []),
            "roles": list(self.state.roles),
            "extra_aliases": aliases,
        }
        self.cfg.user["template"] = name
        self.cfg.save_user()
        self._fill_templates()
        self._log("Template salvato", name)
        self._set_status(f"Template «{name}» salvato.")

    # ===================================================================== #
    # Progetto
    # ===================================================================== #
    def _confirm_discard(self) -> bool:
        if not self.dirty or not self.state.loaded_boms():
            return True
        box = QMessageBox(QMessageBox.Icon.Question, "Modifiche non salvate",
                          "Il confronto corrente contiene modifiche non salvate.\n"
                          "Vuoi salvarle prima di continuare?", parent=self)
        save = box.addButton("Salva", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("Non salvare", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Annulla", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is save:
            return self.save_project()
        return box.clickedButton() is discard

    def new_project(self) -> None:
        if not self._confirm_discard():
            return
        self._apply_state(ProjectState(roles=self.cfg.roles(), boms=[None] * 3,
                                       template=self.cfg.user.get("template", "Standard")))
        self.project_path = None
        self.dirty = False
        self._update_title()

    def open_project(self, path: str | None = None) -> None:
        if not self._confirm_discard():
            return
        if not path:
            start = self.cfg.user.get("last_dir") or str(Path.home())
            path, _ = QFileDialog.getOpenFileName(self, "Apri progetto", start, PROJECT_FILTER)
            if not path:
                return
        try:
            with wait_cursor():
                state = load_project(path)
        except ProjectError as exc:
            QMessageBox.warning(self, "Impossibile aprire il progetto", str(exc))
            return
        self._apply_state(state)
        self.project_path = path
        self.cfg.add_recent_project(path)
        self._log("Progetto aperto", path)
        self.dirty = False
        self._update_title()

    def _apply_state(self, state: ProjectState) -> None:
        self.state = state
        self.raw_tables.clear()
        if len(state.boms) < 3:
            state.boms += [None] * (3 - len(state.boms))
        self._rebuild_slots()
        self.machine_edit.setText(state.machine)
        if state.template and self.template_combo.findText(state.template) >= 0:
            self.template_combo.blockSignals(True)
            self.template_combo.setCurrentText(state.template)
            self.template_combo.blockSignals(False)
            self.cfg.user["template"] = state.template
        tol = state.settings.get("tolerance_pct")
        if tol is not None:
            self.tol_spin.setValue(float(tol))
        self.log_view.set_entries(state.change_log)
        self.run_compare()

    def save_project(self) -> bool:
        if not self.project_path:
            return self.save_project_as()
        return self._save_to(self.project_path)

    def save_project_as(self) -> bool:
        default = self._default_name("Confronto") + PROJECT_EXTENSION
        start = os.path.join(self.cfg.user.get("last_dir") or str(Path.home()), default)
        path, _ = QFileDialog.getSaveFileName(self, "Salva progetto", start, PROJECT_FILTER)
        if not path:
            return False
        if not path.lower().endswith(PROJECT_EXTENSION):
            path += PROJECT_EXTENSION
        return self._save_to(path)

    def _save_to(self, path: str) -> bool:
        self.state.machine = self.machine_edit.text().strip()
        self.state.settings = {"tolerance_pct": self.tol_spin.value()}
        self._log("Progetto salvato", path)
        try:
            with wait_cursor():
                save_project(path, self.state)
        except ProjectError as exc:
            QMessageBox.critical(self, "Salvataggio non riuscito", str(exc))
            return False
        self.project_path = path
        self.cfg.add_recent_project(path)
        self.dirty = False
        self._update_title()
        self._set_status(f"Progetto salvato: {path}")
        return True

    def _fill_recent(self) -> None:
        self.recent_menu.clear()
        recent = [p for p in self.cfg.user.get("recent_projects", []) if os.path.exists(p)]
        if not recent:
            act = self.recent_menu.addAction("(nessun progetto recente)")
            act.setEnabled(False)
        for p in recent:
            self.recent_menu.addAction(os.path.basename(p),
                                       lambda checked=False, path=p: self.open_project(path))

    # ===================================================================== #
    # Esportazioni
    # ===================================================================== #
    def _default_name(self, prefix: str) -> str:
        machine = "".join(ch for ch in self.machine_edit.text().strip()
                          if ch.isalnum() or ch in "-_") or "BOM"
        return f"{prefix}_{machine}_{datetime.now():%Y%m%d_%H%M}"

    def _ask_save_path(self, title: str, ext: str, flt: str) -> str | None:
        start = os.path.join(self.cfg.user.get("last_dir") or str(Path.home()),
                             self._default_name("Confronto") + ext)
        path, _ = QFileDialog.getSaveFileName(self, title, start, flt)
        if not path:
            return None
        return path if path.lower().endswith(ext) else path + ext

    def _offer_open(self, path: str, kind: str) -> None:
        box = QMessageBox(QMessageBox.Icon.Information, "Esportazione completata",
                          f"Report {kind} creato:\n{path}", parent=self)
        open_btn = box.addButton("Apri il file", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Chiudi", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is open_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _run_export(self, kind: str, path: str, fn, *args) -> None:
        """Esegue l'export in background mostrando la barra di avanzamento."""
        for a in (self.a_excel, self.a_pdf):
            a.setEnabled(False)
        self.progress.setRange(0, 0)  # indeterminata
        self.progress.show()
        self._set_status(f"Creazione report {kind} in corso…")
        task = FuncTask(fn, path, *args)

        def done(_result) -> None:
            self._end_export(task)
            self._log(f"Report {kind} esportato", path)
            if kind == "Excel":
                self._store_comparison_silent()
            self._set_status(f"Report {kind} creato: {path}")
            self._offer_open(path, kind)

        def failed(exc) -> None:
            self._end_export(task)
            self._set_status("Esportazione non riuscita.")
            if isinstance(exc, PermissionError):
                msg = ("Il file è aperto in un altro programma (es. Excel) o la cartella non è "
                       "scrivibile.\nChiudi il file e riprova.")
            else:
                msg = f"Impossibile creare il report {kind}.\nDettaglio tecnico: {exc}"
            QMessageBox.critical(self, "Esportazione non riuscita", msg)

        task.signals.finished.connect(done)
        task.signals.failed.connect(failed)
        self._tasks.append(task)
        self.pool.start(task)

    def _end_export(self, task) -> None:
        if task in self._tasks:
            self._tasks.remove(task)
        self.progress.setRange(0, 100)
        self.progress.hide()
        self._update_actions()

    def export_excel(self) -> None:
        if not self.result:
            return
        path = self._ask_save_path("Esporta report Excel", ".xlsx", "Excel (*.xlsx)")
        if path:
            self._run_export("Excel", path, export_excel, self.result, dict(self.state.notes),
                             list(self.state.change_log), self.machine_edit.text().strip())

    def export_pdf(self) -> None:
        if not self.result:
            return
        if not PDF_AVAILABLE:
            QMessageBox.information(self, "PDF non disponibile",
                                    "Il componente per la creazione dei PDF non è installato.\n"
                                    "Usa l'esportazione Excel.")
            return
        path = self._ask_save_path("Esporta report PDF", ".pdf", "PDF (*.pdf)")
        if path:
            self._run_export("PDF", path, export_pdf, self.result, dict(self.state.notes),
                             self.machine_edit.text().strip())

    def show_email(self) -> None:
        if not self.result:
            return
        pair = self.pair_view.current_pair or self.result.pair_keys()[0]
        EmailDialog(self.result, pair, self.machine_edit.text().strip(),
                    self.state.notes, self).exec()

    # ===================================================================== #
    # Storico
    # ===================================================================== #
    def show_history(self, slot_index: int | None = None) -> None:
        if not self.history:
            QMessageBox.information(self, "Storico", "Lo storico non è disponibile.")
            return
        dlg = HistoryDialog(self.history, [s.role for s in self.slots], slot_index, self)
        if dlg.exec() != HistoryDialog.DialogCode.Accepted or not dlg.action:
            return
        try:
            if dlg.action[0] == "snapshot":
                _kind, sid, slot = dlg.action
                bom = self.history.get_snapshot(sid)
                bom.warnings = list(bom.warnings) + [f"Versione storica del {bom.loaded_at}"]
                self._set_bom(slot, bom)
            else:
                if not self._confirm_discard():
                    return
                state = ProjectState.from_dict(self.history.get_comparison_project(dlg.action[1]))
                self._apply_state(state)
                self.project_path = None
                self.dirty = False
                self._update_title()
        except Exception as exc:  # noqa: BLE001
            log.exception("Errore apertura storico")
            QMessageBox.warning(self, "Storico", f"Impossibile aprire l'elemento:\n{exc}")

    def _comparison_summary(self) -> dict:
        return {self.result.pair_label(p): self.result.summary(p)
                for p in self.result.pair_keys()} if self.result else {}

    def store_comparison(self) -> None:
        if not self.result or not self.history:
            return
        default = f"{self.machine_edit.text().strip() or 'Confronto'} {datetime.now():%d/%m/%Y %H:%M}"
        title, ok = QInputDialog.getText(self, "Salva nello storico", "Titolo del confronto:",
                                         text=default)
        if not ok:
            return
        self.history.add_comparison(title or default, self.state.machine, self.result.names,
                                    self._comparison_summary(), self.state.to_dict())
        self._log("Confronto archiviato nello storico", title)
        self._set_status("Confronto salvato nello storico.")

    def _store_comparison_silent(self) -> None:
        if not self.result or not self.history:
            return
        try:
            title = f"{self.state.machine or 'Confronto'} (export {datetime.now():%d/%m/%Y %H:%M})"
            self.history.add_comparison(title, self.state.machine, self.result.names,
                                        self._comparison_summary(), self.state.to_dict())
        except Exception:  # noqa: BLE001
            log.exception("Archiviazione automatica del confronto non riuscita")

    # ===================================================================== #
    # Varie
    # ===================================================================== #
    def show_settings(self) -> None:
        old_theme = self.cfg.theme
        if SettingsDialog(self.cfg, self).exec():
            self.tol_spin.blockSignals(True)
            self.tol_spin.setValue(float(self.cfg.comparison_settings().get("tolerance_pct", 10)))
            self.tol_spin.blockSignals(False)
            if self.cfg.theme != old_theme:
                self._apply_theme()
            self._log("Impostazioni modificate")
            self.run_compare()

    def toggle_theme(self) -> None:
        self.cfg.user["theme"] = "dark" if self.cfg.theme == "light" else "light"
        self.cfg.save_user()
        self._apply_theme()

    def _apply_theme(self) -> None:
        self.theme = get_theme(self.cfg.theme)
        apply_theme(QApplication.instance(), self.theme)
        self.refresh_icons()
        self._rebuild_slots()  # ricrea i riquadri con le icone del nuovo tema
        self.aligned_view.set_theme(self.theme)
        self.pair_view.set_theme(self.theme)
        self.summary_view.set_theme(self.theme)

    def refresh_icons(self) -> None:
        for act, name in self._themed_actions:
            act.setIcon(icon(name, self.theme.text))
        for idx, name in enumerate(("aligned", "pair", "summary", "log")):
            self.tabs.setTabIcon(idx, icon(name))
        self.add_slot_btn.setIcon(icon("add", self.theme.accent))
        self.filter_bar.refresh_icons()
        self.a_theme.setIcon(icon("sun" if self.theme.name == "dark" else "moon", self.theme.text))

    def show_tutorial(self) -> None:
        dlg = TutorialDialog(self)
        dlg.dont_show.setChecked(True)
        code = dlg.exec()
        self.cfg.user["first_run"] = not dlg.dont_show.isChecked()
        self.cfg.save_user()
        if code == TutorialDialog.LOAD_SAMPLE:
            self.load_samples()

    def maybe_show_tutorial(self) -> None:
        if self.cfg.user.get("first_run", True):
            QTimer.singleShot(400, self.show_tutorial)

    def open_log_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(user_data_dir() / "logs")))

    def show_about(self) -> None:
        QMessageBox.about(
            self, f"Informazioni su {APP_NAME}",
            f"<h3>{APP_NAME} {__version__}</h3>"
            "<p>Confronto offline di distinte base (BOM) per produzione, "
            "ufficio tecnico e acquisti.</p>"
            "<p>Nessuna connessione internet utilizzata: i dati restano sul computer.</p>"
            f"<p style='color:gray'>Dati utente, storico e log:<br>{user_data_dir()}</p>")

    def _focus_search(self) -> None:
        self.filter_bar.search.setFocus()
        self.filter_bar.search.selectAll()

    def _log(self, event: str, detail: str = "") -> None:
        entry = self.state.log_event(event, detail)
        self.log_view.add_entry(entry)

    def _mark_dirty(self) -> None:
        if not self.dirty:
            self.dirty = True
            self._update_title()

    def _update_title(self) -> None:
        name = os.path.basename(self.project_path) if self.project_path else "Nuovo confronto"
        self.setWindowTitle(f"{name}{' *' if self.dirty else ''} – {APP_NAME}")

    def _update_actions(self) -> None:
        has = self.result is not None
        for a in (self.a_excel, self.a_pdf, self.a_email, self.a_store):
            a.setEnabled(has)
        self.a_pdf.setEnabled(has and PDF_AVAILABLE)

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def _show_progress(self, value: int, text: str) -> None:
        self.progress.show()
        self.progress.setValue(value)
        self._set_status(text)

    def _restore_geometry(self) -> None:
        geo = self.cfg.user.get("window_geometry")
        if geo:
            try:
                self.restoreGeometry(QByteArray.fromHex(geo.encode()))
            except Exception:  # noqa: BLE001
                pass

    def closeEvent(self, event):  # noqa: N802
        if not self._confirm_discard():
            event.ignore()
            return
        self.cfg.user["window_geometry"] = bytes(self.saveGeometry().toHex()).decode()
        self.cfg.save_user()
        log.info("Applicazione chiusa")
        event.accept()
