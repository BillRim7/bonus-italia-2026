"""Caricamento file in background (l'interfaccia resta reattiva)."""
from __future__ import annotations

import logging
from typing import Any

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from ..core.loader import BOMLoadError, build_bom, inspect_file

log = logging.getLogger(__name__)


class LoadSignals(QObject):
    progress = pyqtSignal(int, int, str)     # slot, percentuale, messaggio
    needs_mapping = pyqtSignal(int, object)  # slot, RawTable
    loaded = pyqtSignal(int, object, object)  # slot, BOMData, RawTable
    failed = pyqtSignal(int, str)            # slot, messaggio per l'utente


class LoadTask(QRunnable):
    """Legge un file, rileva le colonne e (se possibile) normalizza la distinta."""

    def __init__(self, slot: int, path: str, role: str, aliases: dict[str, list[str]],
                 settings: dict[str, Any]):
        super().__init__()
        self.slot = slot
        self.path = path
        self.role = role
        self.aliases = aliases
        self.settings = settings
        self.signals = LoadSignals()
        self.setAutoDelete(False)  # il riferimento è tenuto dalla finestra

    def run(self) -> None:
        def progress(pct: int, msg: str) -> None:
            self.signals.progress.emit(self.slot, pct, msg)
        try:
            rt = inspect_file(self.path, self.aliases, progress=progress)
            if not rt.is_mapping_complete:
                self.signals.needs_mapping.emit(self.slot, rt)
                return
            bom = build_bom(rt, self.role, self.settings, progress=progress)
            self.signals.loaded.emit(self.slot, bom, rt)
        except BOMLoadError as exc:
            self.signals.failed.emit(self.slot, str(exc))
        except MemoryError:
            self.signals.failed.emit(self.slot, "Memoria insufficiente per aprire il file.")
        except Exception as exc:  # noqa: BLE001
            log.exception("Errore imprevisto nel caricamento di %s", self.path)
            self.signals.failed.emit(self.slot, f"Errore imprevisto durante la lettura del "
                                                f"file.\nDettaglio tecnico: {exc}")


class FuncSignals(QObject):
    finished = pyqtSignal(object)   # valore restituito
    failed = pyqtSignal(object)     # eccezione


class FuncTask(QRunnable):
    """Esegue una funzione lunga (es. export) fuori dal thread dell'interfaccia."""

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn, self.args, self.kwargs = fn, args, kwargs
        self.signals = FuncSignals()
        self.setAutoDelete(False)

    def run(self) -> None:
        try:
            self.signals.finished.emit(self.fn(*self.args, **self.kwargs))
        except Exception as exc:  # noqa: BLE001 - gestita dal chiamante
            log.exception("Operazione in background non riuscita")
            self.signals.failed.emit(exc)
