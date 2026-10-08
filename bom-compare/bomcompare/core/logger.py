"""Configurazione del logging su file (rotazione) e console."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"


def setup_logging(log_dir: Path, level: str = "INFO") -> Path:
    """Attiva il log su ``log_dir/bomcompare.log`` (max 5 file da 1 MB)."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "bomcompare.log"

    root = logging.getLogger()
    root.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = logging.Formatter(LOG_FORMAT)
    try:
        file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000,
                                           backupCount=5, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        # Cartella non scrivibile: si prosegue solo con la console.
        pass

    if sys.stderr is not None:  # con PyInstaller --windowed stderr è None
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(formatter)
        root.addHandler(console)

    logging.getLogger("PyQt6").setLevel(logging.WARNING)
    return log_file
