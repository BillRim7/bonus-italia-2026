"""Finestre di dialogo: mappatura colonne, storico, impostazioni, e-mail, tutorial."""
from __future__ import annotations

import logging
from urllib.parse import quote

from PyQt6.QtCore import QSize, Qt, QUrl
from PyQt6.QtGui import QBrush, QColor, QDesktopServices, QFont, QFontDatabase, QGuiApplication
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog,
                             QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout,
                             QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                             QMessageBox, QPlainTextEdit, QPushButton, QSpinBox,
                             QStackedWidget, QTableWidget, QTableWidgetItem, QTabWidget,
                             QVBoxLayout, QWidget)

from ..core.comparator import ComparisonResult
from ..core.config import AppConfig
from ..core.history import HistoryStore
from ..core.loader import (BOMLoadError, RawTable, cell_to_str, detect_columns,
                           inspect_file)
from ..core.models import COMPARE_FIELD_LABELS, FIELD_HINTS, FIELD_LABELS, FIELDS
from ..export.email_text import build_email_text
from .icons import icon

log = logging.getLogger(__name__)
NONE_LABEL = "— non presente —"


def wait_cursor():
    """Context manager per il cursore di attesa."""
    class _Ctx:
        def __enter__(self):
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        def __exit__(self, *exc):
            QApplication.restoreOverrideCursor()
    return _Ctx()


# --------------------------------------------------------------------------- #
# Mappatura colonne
# --------------------------------------------------------------------------- #
class MappingDialog(QDialog):
    """Permette di scegliere foglio, riga di intestazione e colonne da usare."""

    def __init__(self, rt: RawTable, aliases: dict[str, list[str]], role: str,
                 preview_rows: int = 100, parent=None):
        super().__init__(parent)
        self.rt = rt
        self.aliases = aliases
        self.preview_rows = preview_rows
        self.setWindowTitle(f"Mappatura colonne – {role}")
        self.resize(1100, 680)

        lay = QVBoxLayout(self)
        intro = QLabel("Indica quali colonne del file contengono i dati della distinta. "
                       "Le colonne sono state <b>rilevate automaticamente</b>: verifica e "
                       "correggi se necessario. Solo il <b>Codice articolo</b> è obbligatorio.")
        intro.setWordWrap(True)
        lay.addWidget(intro)

        top = QHBoxLayout()
        if rt.sheets:
            top.addWidget(QLabel("Foglio:"))
            self.sheet_combo = QComboBox()
            self.sheet_combo.addItems(rt.sheets)
            if rt.sheet in rt.sheets:
                self.sheet_combo.setCurrentText(rt.sheet)
            self.sheet_combo.currentTextChanged.connect(self._on_sheet)
            top.addWidget(self.sheet_combo)
            top.addSpacing(20)
        else:
            self.sheet_combo = None
        top.addWidget(QLabel("Riga intestazione:"))
        self.header_spin = QSpinBox()
        self.header_spin.setRange(1, max(1, min(len(rt.raw), 200)))
        self.header_spin.setValue(rt.header_row + 1)
        self.header_spin.setToolTip("Riga che contiene i nomi delle colonne "
                                    "(puoi anche cliccare una riga dell'anteprima)")
        self.header_spin.valueChanged.connect(self._on_header)
        top.addWidget(self.header_spin)
        auto = QPushButton(icon("check"), "Rileva automaticamente")
        auto.clicked.connect(self._auto_detect)
        top.addWidget(auto)
        top.addStretch(1)
        lay.addLayout(top)

        body = QHBoxLayout()
        form_box = QGroupBox("Campi della distinta")
        form = QGridLayout(form_box)
        self.combos: dict[str, QComboBox] = {}
        for r, fld in enumerate(FIELDS):
            label = QLabel(FIELD_LABELS[fld] + (" *" if fld == "code" else ""))
            if fld == "code":
                label.setStyleSheet("font-weight:600;")
            combo = QComboBox()
            combo.setMinimumWidth(200)
            combo.setToolTip(FIELD_HINTS[fld])
            combo.currentIndexChanged.connect(self._refresh_preview_colors)
            self.combos[fld] = combo
            label.setToolTip(FIELD_HINTS[fld])
            form.addWidget(label, r, 0)
            form.addWidget(combo, r, 1)
        hint = QLabel("* obbligatorio. Passa il mouse su un campo per sapere a cosa serve.")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        form.addWidget(hint, len(FIELDS), 0, 1, 2)
        form.setRowStretch(len(FIELDS) + 1, 1)
        body.addWidget(form_box, 0)

        prev_box = QGroupBox("Anteprima del file (la riga evidenziata è l'intestazione)")
        pl = QVBoxLayout(prev_box)
        self.preview = QTableWidget()
        self.preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.preview.cellClicked.connect(lambda r, _c: self.header_spin.setValue(r + 1))
        pl.addWidget(self.preview)
        body.addWidget(prev_box, 1)
        lay.addLayout(body, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Conferma")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annulla")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)
        self._fill_preview()
        self._fill_combos()

    # -- aggiornamenti ------------------------------------------------------ #
    def _on_sheet(self, name: str) -> None:
        try:
            with wait_cursor():
                self.rt = inspect_file(self.rt.path, self.aliases, sheet=name)
        except BOMLoadError as exc:
            QMessageBox.warning(self, "Foglio non leggibile", str(exc))
            return
        self.header_spin.blockSignals(True)
        self.header_spin.setRange(1, max(1, min(len(self.rt.raw), 200)))
        self.header_spin.setValue(self.rt.header_row + 1)
        self.header_spin.blockSignals(False)
        self._fill_preview()
        self._fill_combos()

    def _on_header(self, value: int) -> None:
        self.rt.header_row = value - 1
        self.rt.mapping = detect_columns(list(self.rt.table.columns), self.aliases)
        self._fill_combos()
        self._refresh_preview_colors()

    def _auto_detect(self) -> None:
        from ..core.loader import detect_header_row
        self.header_spin.setValue(detect_header_row(self.rt.raw, self.aliases) + 1)
        self._on_header(self.header_spin.value())

    def _fill_combos(self) -> None:
        columns = list(self.rt.table.columns)
        for fld, combo in self.combos.items():
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(NONE_LABEL, "")
            for c in columns:
                combo.addItem(c, c)
            current = self.rt.mapping.get(fld, "")
            idx = combo.findData(current) if current else 0
            combo.setCurrentIndex(max(0, idx))
            combo.blockSignals(False)
        self._refresh_preview_colors()

    def _fill_preview(self) -> None:
        raw = self.rt.raw.head(self.preview_rows)
        self.preview.clear()
        self.preview.setRowCount(len(raw))
        self.preview.setColumnCount(len(raw.columns))
        self.preview.setHorizontalHeaderLabels([f"Col. {i + 1}" for i in range(len(raw.columns))])
        for r, row in enumerate(raw.itertuples(index=False)):
            for c, v in enumerate(row):
                self.preview.setItem(r, c, QTableWidgetItem(cell_to_str(v)))
        self.preview.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents)
        self._refresh_preview_colors()

    def _refresh_preview_colors(self) -> None:
        hdr = self.header_spin.value() - 1
        used = {combo.currentData() for combo in self.combos.values() if combo.currentData()}
        names = list(self.rt.table.columns) if len(self.rt.raw) else []
        accent = QBrush(QColor("#2563EB"))
        white = QBrush(QColor("#FFFFFF"))
        mapped = QBrush(QColor(37, 99, 235, 40))
        bold = QFont()
        bold.setBold(True)
        for r in range(self.preview.rowCount()):
            for c in range(self.preview.columnCount()):
                item = self.preview.item(r, c)
                if item is None:
                    continue
                if r == hdr:
                    item.setBackground(accent)
                    item.setForeground(white)
                    item.setFont(bold)
                elif r < hdr:
                    item.setBackground(QBrush())
                    item.setForeground(QBrush(QColor("#9CA3AF")))
                    item.setFont(QFont())
                else:
                    in_use = c < len(names) and names[c] in used
                    item.setBackground(mapped if in_use else QBrush())
                    item.setForeground(QBrush())
                    item.setFont(QFont())

    def _accept(self) -> None:
        mapping = {f: c.currentData() for f, c in self.combos.items() if c.currentData()}
        if not mapping.get("code"):
            QMessageBox.warning(self, "Codice mancante",
                                "Seleziona la colonna che contiene il Codice articolo.")
            return
        values = list(mapping.values())
        dup = {v for v in values if values.count(v) > 1}
        if dup:
            QMessageBox.warning(self, "Colonna usata più volte",
                                "La stessa colonna è stata assegnata a più campi:\n"
                                + ", ".join(dup))
            return
        self.rt.mapping = mapping
        self.accept()


# --------------------------------------------------------------------------- #
# Storico
# --------------------------------------------------------------------------- #
class HistoryDialog(QDialog):
    """Distinte e confronti salvati nel database locale."""

    def __init__(self, store: HistoryStore, slot_names: list[str], target_slot: int | None = None,
                 parent=None):
        super().__init__(parent)
        self.store = store
        self.slot_names = slot_names
        self.action: tuple | None = None
        self.setWindowTitle("Storico versioni")
        self.resize(980, 560)
        lay = QVBoxLayout(self)
        info = QLabel("Le distinte caricate vengono salvate automaticamente nello storico "
                      "locale. Puoi ricaricare una versione storica in un riquadro per "
                      "confrontarla con le versioni attuali.")
        info.setWordWrap(True)
        info.setObjectName("Muted")
        lay.addWidget(info)
        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)

        # Distinte
        w1 = QWidget()
        l1 = QVBoxLayout(w1)
        self.snap_table = self._table(["Data", "Macchina", "Ruolo", "File", "Codici"])
        self.snap_table.doubleClicked.connect(lambda _i: self._load_snapshot())
        l1.addWidget(self.snap_table)
        row = QHBoxLayout()
        row.addWidget(QLabel("Carica nel riquadro:"))
        self.slot_combo = QComboBox()
        for i, name in enumerate(slot_names):
            self.slot_combo.addItem(f"{i + 1} – {name}", i)
        if target_slot is not None:
            self.slot_combo.setCurrentIndex(target_slot)
        row.addWidget(self.slot_combo)
        load_btn = QPushButton(icon("upload"), "Carica versione")
        load_btn.setObjectName("Primary")
        load_btn.clicked.connect(self._load_snapshot)
        row.addWidget(load_btn)
        row.addStretch(1)
        del_btn = QPushButton(icon("trash"), "Elimina")
        del_btn.clicked.connect(self._delete_snapshot)
        row.addWidget(del_btn)
        l1.addLayout(row)
        self.tabs.addTab(w1, icon("db"), "Versioni distinte")

        # Confronti
        w2 = QWidget()
        l2 = QVBoxLayout(w2)
        self.comp_table = self._table(["Data", "Titolo", "Macchina", "Distinte", "Differenze"])
        self.comp_table.doubleClicked.connect(lambda _i: self._open_comparison())
        l2.addWidget(self.comp_table)
        row2 = QHBoxLayout()
        open_btn = QPushButton(icon("open"), "Apri confronto")
        open_btn.setObjectName("Primary")
        open_btn.clicked.connect(self._open_comparison)
        row2.addWidget(open_btn)
        row2.addStretch(1)
        del2 = QPushButton(icon("trash"), "Elimina")
        del2.clicked.connect(self._delete_comparison)
        row2.addWidget(del2)
        l2.addLayout(row2)
        self.tabs.addTab(w2, icon("history"), "Confronti salvati")

        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.button(QDialogButtonBox.StandardButton.Close).setText("Chiudi")
        close.rejected.connect(self.reject)
        lay.addWidget(close)
        self._reload()

    @staticmethod
    def _table(headers: list[str]) -> QTableWidget:
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.verticalHeader().hide()
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        t.horizontalHeader().setStretchLastSection(True)
        t.setSortingEnabled(True)
        return t

    def _reload(self) -> None:
        snaps = self.store.list_snapshots()
        self.snap_table.setSortingEnabled(False)
        self.snap_table.setRowCount(len(snaps))
        for r, s in enumerate(snaps):
            vals = [s["created_at"], s["machine"] or "", s["role"] or "", s["label"] or "",
                    str(s["rows"])]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setData(Qt.ItemDataRole.UserRole, s["id"])
                item.setToolTip(s["source_path"] or "")
                self.snap_table.setItem(r, c, item)
        self.snap_table.setSortingEnabled(True)
        self.snap_table.resizeColumnsToContents()

        comps = self.store.list_comparisons()
        self.comp_table.setSortingEnabled(False)
        self.comp_table.setRowCount(len(comps))
        for r, cmp in enumerate(comps):
            summ = cmp["summary"]
            diff = ", ".join(f"{k}: +{v.get('added', 0)} −{v.get('removed', 0)} "
                             f"✎{v.get('modified', 0)}" for k, v in summ.items())
            vals = [cmp["created_at"], cmp["title"] or "", cmp["machine"] or "",
                    " / ".join(cmp["names"]), diff]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setData(Qt.ItemDataRole.UserRole, cmp["id"])
                item.setToolTip(v)
                self.comp_table.setItem(r, c, item)
        self.comp_table.setSortingEnabled(True)
        self.comp_table.resizeColumnsToContents()

    @staticmethod
    def _selected_id(table: QTableWidget) -> int | None:
        items = table.selectedItems()
        return items[0].data(Qt.ItemDataRole.UserRole) if items else None

    def _load_snapshot(self) -> None:
        sid = self._selected_id(self.snap_table)
        if sid is None:
            QMessageBox.information(self, "Storico", "Seleziona una versione dall'elenco.")
            return
        self.action = ("snapshot", sid, self.slot_combo.currentData())
        self.accept()

    def _delete_snapshot(self) -> None:
        sid = self._selected_id(self.snap_table)
        if sid is not None and _confirm(self, "Eliminare la versione selezionata dallo storico?"):
            self.store.delete_snapshot(sid)
            self._reload()

    def _open_comparison(self) -> None:
        cid = self._selected_id(self.comp_table)
        if cid is None:
            QMessageBox.information(self, "Storico", "Seleziona un confronto dall'elenco.")
            return
        self.action = ("comparison", cid)
        self.accept()

    def _delete_comparison(self) -> None:
        cid = self._selected_id(self.comp_table)
        if cid is not None and _confirm(self, "Eliminare il confronto selezionato dallo storico?"):
            self.store.delete_comparison(cid)
            self._reload()


def _confirm(parent, text: str) -> bool:
    box = QMessageBox(QMessageBox.Icon.Question, "Conferma", text, parent=parent)
    yes = box.addButton("Sì", QMessageBox.ButtonRole.YesRole)
    box.addButton("No", QMessageBox.ButtonRole.NoRole)
    box.exec()
    return box.clickedButton() is yes


# --------------------------------------------------------------------------- #
# Impostazioni
# --------------------------------------------------------------------------- #
class SettingsDialog(QDialog):
    def __init__(self, cfg: AppConfig, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("Impostazioni")
        self.setMinimumWidth(520)
        current = cfg.comparison_settings()
        lay = QVBoxLayout(self)

        box = QGroupBox("Confronto")
        form = QFormLayout(box)
        self.tol = QDoubleSpinBox()
        self.tol.setRange(0, 1000)
        self.tol.setSuffix(" %")
        self.tol.setDecimals(1)
        self.tol.setValue(float(current.get("tolerance_pct", 10)))
        self.tol.setToolTip("Avvisa quando la quantità varia più di questa percentuale "
                            "(0 = disattivato)")
        form.addRow("Tolleranza quantità:", self.tol)
        self.fields: dict[str, QCheckBox] = {}
        fields_w = QWidget()
        fl = QGridLayout(fields_w)
        fl.setContentsMargins(0, 0, 0, 0)
        for k, (f, label) in enumerate(COMPARE_FIELD_LABELS.items()):
            cb = QCheckBox(label)
            cb.setChecked(f in current.get("compare_fields", []))
            self.fields[f] = cb
            fl.addWidget(cb, k // 2, k % 2)
        form.addRow("Considera modifica se cambia:", fields_w)
        self.ignore_case = QCheckBox("Ignora maiuscole/minuscole nella descrizione")
        self.ignore_case.setChecked(bool(current.get("ignore_description_case", True)))
        self.code_case = QCheckBox("Codici articolo: ignora maiuscole/minuscole")
        self.code_case.setChecked(bool(current.get("code_case_insensitive", True)))
        self.aggregate = QCheckBox("Somma le quantità dei codici ripetuti su più righe")
        self.aggregate.setChecked(bool(current.get("aggregate_duplicates", True)))
        for cb in (self.ignore_case, self.code_case, self.aggregate):
            form.addRow("", cb)
        lay.addWidget(box)

        box2 = QGroupBox("Aspetto e storico")
        f2 = QFormLayout(box2)
        self.theme = QComboBox()
        self.theme.addItem("Chiaro", "light")
        self.theme.addItem("Scuro", "dark")
        self.theme.setCurrentIndex(0 if cfg.theme == "light" else 1)
        f2.addRow("Tema:", self.theme)
        self.history = QCheckBox("Salva automaticamente nello storico le distinte caricate")
        self.history.setChecked(bool(cfg.user.get("auto_snapshot",
                                                  cfg.get("history.auto_snapshot_on_load", True))))
        f2.addRow("", self.history)
        lay.addWidget(box2)
        note = QLabel("Le opzioni su codici e righe ripetute si applicano alle distinte "
                      "caricate successivamente.")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        lay.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Salva")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annulla")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _save(self) -> None:
        self.cfg.user["comparison_overrides"] = {
            "tolerance_pct": self.tol.value(),
            "compare_fields": [f for f, cb in self.fields.items() if cb.isChecked()],
            "ignore_description_case": self.ignore_case.isChecked(),
            "code_case_insensitive": self.code_case.isChecked(),
            "aggregate_duplicates": self.aggregate.isChecked(),
        }
        self.cfg.user["theme"] = self.theme.currentData()
        self.cfg.user["auto_snapshot"] = self.history.isChecked()
        self.cfg.save_user()
        self.accept()


# --------------------------------------------------------------------------- #
# Testo per e-mail
# --------------------------------------------------------------------------- #
class EmailDialog(QDialog):
    def __init__(self, result: ComparisonResult, pair: tuple[int, int] | None, machine: str,
                 notes: dict[str, str], parent=None):
        super().__init__(parent)
        self.result = result
        self.machine = machine
        self.notes = notes
        self.setWindowTitle("Elenco modifiche per e-mail")
        self.resize(860, 640)
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Confronto:"))
        self.combo = QComboBox()
        for p in result.pair_keys():
            self.combo.addItem(result.pair_label(p), list(p))
        if pair in result.pairs:
            self.combo.setCurrentIndex(result.pair_keys().index(pair))
        self.combo.currentIndexChanged.connect(self._refresh)
        top.addWidget(self.combo, 1)
        self.only_sig = QCheckBox("Escludi variazioni di quantità entro tolleranza")
        self.only_sig.toggled.connect(self._refresh)
        top.addWidget(self.only_sig)
        lay.addLayout(top)
        self.text = QPlainTextEdit()
        mono = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        mono.setPointSize(10)
        self.text.setFont(mono)
        lay.addWidget(self.text, 1)
        row = QHBoxLayout()
        copy_btn = QPushButton(icon("copy"), "Copia negli appunti")
        copy_btn.setObjectName("Primary")
        copy_btn.clicked.connect(self._copy)
        save_btn = QPushButton(icon("save"), "Salva come .txt…")
        save_btn.clicked.connect(self._save)
        mail_btn = QPushButton(icon("email"), "Apri nel programma di posta")
        mail_btn.setToolTip("Apre Outlook (o il client predefinito) con il testo già inserito")
        mail_btn.clicked.connect(self._mailto)
        row.addWidget(copy_btn)
        row.addWidget(save_btn)
        row.addWidget(mail_btn)
        row.addStretch(1)
        close = QPushButton("Chiudi")
        close.clicked.connect(self.accept)
        row.addWidget(close)
        lay.addLayout(row)
        self._refresh()

    def _refresh(self) -> None:
        pair = tuple(self.combo.currentData())
        self.text.setPlainText(build_email_text(self.result, pair, self.machine, self.notes,
                                                only_tol=self.only_sig.isChecked()))

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self.text.toPlainText())
        QMessageBox.information(self, "Copiato", "Testo copiato negli appunti.\n"
                                "Ora puoi incollarlo (Ctrl+V) nella tua e-mail.")

    def _save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Salva testo", "modifiche_distinta.txt",
                                              "Testo (*.txt)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(self.text.toPlainText())
            except OSError as exc:
                QMessageBox.critical(self, "Errore", f"Impossibile salvare il file:\n{exc}")

    def _mailto(self) -> None:
        text = self.text.toPlainText()
        lines = text.splitlines()
        subject = lines[0].replace("Oggetto: ", "") if lines else "Modifiche distinta"
        body = "\n".join(lines[2:])
        if len(body) > 1800:  # limite pratico degli URL mailto
            QGuiApplication.clipboard().setText(body)
            body = ("[Il testo completo è stato copiato negli appunti: incollalo qui con "
                    "Ctrl+V]\n")
        url = QUrl(f"mailto:?subject={quote(subject)}&body={quote(body)}")
        if not QDesktopServices.openUrl(url):
            QMessageBox.warning(self, "Posta", "Nessun programma di posta configurato. "
                                "Usa 'Copia negli appunti'.")


# --------------------------------------------------------------------------- #
# Tutorial primo avvio
# --------------------------------------------------------------------------- #
TUTORIAL_PAGES = [
    ("app", "Benvenuto in BOM Compare",
     "<p>Questa applicazione confronta <b>distinte base</b> (BOM) e mostra in modo chiaro "
     "cosa è cambiato tra una versione e l'altra della macchina.</p>"
     "<p>Funziona <b>completamente offline</b>: i tuoi file non lasciano mai il computer.</p>"
     "<p>In pochi passaggi vedrai come:</p><ol><li>caricare le distinte</li>"
     "<li>leggere i colori del confronto</li><li>filtrare e cercare</li>"
     "<li>esportare e condividere i risultati</li></ol>"),
    ("upload", "1. Carica le distinte",
     "<p>In alto trovi tre riquadri:</p><ul>"
     "<li><b>1 – Macchina VECCHIA</b> (versione precedente)</li>"
     "<li><b>2 – Macchina in PRODUZIONE</b> (versione corrente)</li>"
     "<li><b>3 – Macchina in PROGETTAZIONE</b> (nuova versione)</li></ul>"
     "<p><b>Trascina</b> un file Excel (.xlsx, .xls) o CSV dentro un riquadro, oppure "
     "premi <b>Sfoglia…</b>. Puoi anche trascinare tre file insieme sulla finestra.</p>"
     "<p>Il nome di ogni riquadro si può modificare con un clic. Con <b>+ Distinta</b> "
     "puoi aggiungere altre versioni.</p>"),
    ("columns", "2. Colonne riconosciute automaticamente",
     "<p>L'app riconosce da sola le colonne <i>Codice, Descrizione, Quantità, U.M., "
     "Revisione, Fornitore, Prezzo, Livello</i>, anche se il file ha righe di titolo in "
     "alto.</p><p>Se qualcosa non torna premi <b>Colonne…</b> nel riquadro: potrai scegliere "
     "il foglio, la riga di intestazione e quale colonna usare per ogni campo.</p>"),
    ("compare", "3. Leggi i colori",
     "<p>Il confronto parte da solo appena ci sono almeno due distinte.</p>"
     "<table cellpadding='6'>"
     "<tr><td style='background:#DCFCE7;color:#166534'><b>VERDE</b></td>"
     "<td>componente <b>aggiunto</b> nella versione più recente</td></tr>"
     "<tr><td style='background:#FEE2E2;color:#991B1B'><b>ROSSO</b></td>"
     "<td>componente <b>eliminato</b></td></tr>"
     "<tr><td style='background:#DBEAFE;color:#1E40AF'><b>BLU</b></td>"
     "<td>componente <b>modificato</b> (le celle cambiate sono in grassetto)</td></tr>"
     "<tr><td style='color:#6B7280'><b>GRIGIO</b></td><td>componente <b>invariato</b></td></tr>"
     "<tr><td style='background:#FDE68A;color:#92400E'><b>GIALLO</b></td>"
     "<td>variazione quantità <b>fuori tolleranza</b></td></tr></table>"
     "<p>Nella <b>Vista allineata</b> le distinte sono affiancate e scorrono insieme, "
     "riga per riga sullo stesso codice.</p>"),
    ("search", "4. Filtra, cerca, annota",
     "<ul><li>Scrivi nella casella <b>Cerca</b> un codice o parte della descrizione.</li>"
     "<li>Usa i pulsanti <b>Solo differenze, Aggiunti, Eliminati…</b> per filtrare.</li>"
     "<li>Clicca l'intestazione di una colonna per <b>ordinare</b>.</li>"
     "<li>Fai doppio clic nella colonna <b>Note</b> per scrivere un'annotazione.</li>"
     "<li>Tasto destro sull'intestazione per mostrare/nascondere colonne.</li></ul>"),
    ("excel", "5. Esporta e salva",
     "<ul><li><b>Esporta Excel</b>: report completo con riepilogo e colori.</li>"
     "<li><b>Esporta PDF</b>: per condividere o stampare.</li>"
     "<li><b>Testo e-mail</b>: elenco modifiche pronto da incollare.</li>"
     "<li><b>Salva progetto</b> (.bomcompare): riapri il lavoro in seguito, note comprese.</li>"
     "<li><b>Storico</b>: ogni distinta caricata viene archiviata per confronti futuri.</li>"
     "</ul><p>Vuoi provare subito? Premi <b>Carica dati di esempio</b>.</p>"),
]


class TutorialDialog(QDialog):
    LOAD_SAMPLE = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Guida rapida")
        self.setFixedSize(QSize(640, 470))
        lay = QVBoxLayout(self)
        self.stack = QStackedWidget()
        for ico, title, html in TUTORIAL_PAGES:
            page = QWidget()
            pl = QVBoxLayout(page)
            head = QHBoxLayout()
            lbl_icon = QLabel()
            lbl_icon.setPixmap(icon(ico, "#2563EB").pixmap(QSize(40, 40)))
            head.addWidget(lbl_icon)
            t = QLabel(title)
            t.setObjectName("Title")
            t.setStyleSheet("font-size:16pt;")
            head.addWidget(t, 1)
            pl.addLayout(head)
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            pl.addWidget(line)
            body = QLabel(html)
            body.setWordWrap(True)
            body.setTextFormat(Qt.TextFormat.RichText)
            body.setAlignment(Qt.AlignmentFlag.AlignTop)
            pl.addWidget(body, 1)
            self.stack.addWidget(page)
        lay.addWidget(self.stack, 1)
        self.page_label = QLabel()
        self.page_label.setObjectName("Muted")
        row = QHBoxLayout()
        self.dont_show = QCheckBox("Non mostrare più all'avvio")
        row.addWidget(self.dont_show)
        row.addStretch(1)
        row.addWidget(self.page_label)
        self.back = QPushButton("◀ Indietro")
        self.back.clicked.connect(lambda: self._go(-1))
        self.next = QPushButton("Avanti ▶")
        self.next.setObjectName("Primary")
        self.next.clicked.connect(lambda: self._go(1))
        self.sample = QPushButton(icon("sample"), "Carica dati di esempio")
        self.sample.clicked.connect(lambda: self.done(self.LOAD_SAMPLE))
        row.addWidget(self.back)
        row.addWidget(self.sample)
        row.addWidget(self.next)
        lay.addLayout(row)
        self._go(0)

    def _go(self, delta: int) -> None:
        idx = self.stack.currentIndex() + delta
        if idx >= self.stack.count():
            self.accept()
            return
        self.stack.setCurrentIndex(max(0, idx))
        last = self.stack.currentIndex() == self.stack.count() - 1
        self.back.setEnabled(self.stack.currentIndex() > 0)
        self.next.setText("Fine" if last else "Avanti ▶")
        self.sample.setVisible(last)
        self.page_label.setText(f"{self.stack.currentIndex() + 1} / {self.stack.count()}")
