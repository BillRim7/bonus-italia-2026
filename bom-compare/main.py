"""BOM Compare - punto di avvio dell'applicazione.

Uso:
    python main.py                       # avvio normale
    python main.py progetto.bomcompare   # apre direttamente un progetto
"""
from __future__ import annotations

import logging
import os
import sys
import traceback

os.environ.setdefault("QT_API", "pyqt6")  # qtawesome deve usare PyQt6

from PyQt6.QtCore import QLocale, Qt  # noqa: E402
from PyQt6.QtGui import QFont  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from bomcompare import APP_NAME, PROJECT_EXTENSION, __version__  # noqa: E402
from bomcompare.core.config import AppConfig, user_data_dir  # noqa: E402
from bomcompare.core.history import HistoryStore  # noqa: E402
from bomcompare.core.logger import setup_logging  # noqa: E402

log = logging.getLogger("bomcompare")


def install_exception_hook() -> None:
    """Mostra un messaggio comprensibile per gli errori non gestiti."""

    def hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        details = "".join(traceback.format_exception(exc_type, exc, tb))
        log.critical("Errore non gestito:\n%s", details)
        if QApplication.instance():
            box = QMessageBox(QMessageBox.Icon.Critical, "Errore imprevisto",
                              "Si è verificato un errore imprevisto.\n"
                              "Il lavoro in corso non è stato perso: puoi continuare o salvare "
                              "il progetto.\n\nSe il problema si ripete, invia al supporto il "
                              "file di log (menu Aiuto → Apri cartella log).")
            box.setDetailedText(details)
            box.exec()

    sys.excepthook = hook


def main() -> int:
    data_dir = user_data_dir()
    cfg = AppConfig()
    log_file = setup_logging(data_dir / "logs", cfg.get("app.log_level", "INFO"))
    log.info("Avvio %s %s (log: %s)", APP_NAME, __version__, log_file)
    install_exception_hook()

    QLocale.setDefault(QLocale(QLocale.Language.Italian, QLocale.Country.Italy))
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("BOMCompare")
    if sys.platform == "win32":
        app.setFont(QFont("Segoe UI", 9))
        try:  # icona corretta nella barra delle applicazioni di Windows
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BOMCompare.App")
        except Exception:  # noqa: BLE001
            pass

    # Import dopo QApplication: qtawesome richiede un'applicazione attiva.
    from bomcompare.ui.main_window import MainWindow
    from bomcompare.ui.theme import apply_theme, get_theme

    apply_theme(app, get_theme(cfg.theme))

    history = None
    if cfg.get("history.enabled", True):
        try:
            history = HistoryStore(data_dir / "storico.sqlite",
                                   int(cfg.get("history.max_snapshots", 1000)))
        except Exception:  # noqa: BLE001
            log.exception("Storico non disponibile")

    window = MainWindow(cfg, history)
    window.refresh_icons()
    window.show()

    project = next((a for a in sys.argv[1:] if a.lower().endswith(PROJECT_EXTENSION)), None)
    if project:
        window.open_project(project)
    else:
        window.maybe_show_tutorial()
    return app.exec()


if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    sys.exit(main())
