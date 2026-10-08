"""Icone FontAwesome (qtawesome, font inclusi nel pacchetto: nessun download).

Se qtawesome non è disponibile si usano le icone standard di Qt.
"""
from __future__ import annotations

import logging
import os

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QStyle

os.environ.setdefault("QT_API", "pyqt6")
log = logging.getLogger(__name__)

try:
    import qtawesome as qta
    HAS_QTA = True
except Exception:  # noqa: BLE001 - qualunque problema -> fallback
    qta = None
    HAS_QTA = False
    log.warning("qtawesome non disponibile: uso icone standard")

# nome logico -> (icona FontAwesome 5, fallback QStyle)
ICONS = {
    "new": ("fa5s.file", "SP_FileIcon"),
    "open": ("fa5s.folder-open", "SP_DialogOpenButton"),
    "save": ("fa5s.save", "SP_DialogSaveButton"),
    "compare": ("fa5s.balance-scale", "SP_BrowserReload"),
    "excel": ("fa5s.file-excel", "SP_FileDialogDetailedView"),
    "pdf": ("fa5s.file-pdf", "SP_FileDialogContentsView"),
    "email": ("fa5s.envelope", "SP_MessageBoxInformation"),
    "history": ("fa5s.history", "SP_FileDialogBack"),
    "theme": ("fa5s.adjust", "SP_DesktopIcon"),
    "help": ("fa5s.question-circle", "SP_DialogHelpButton"),
    "settings": ("fa5s.cog", "SP_FileDialogListView"),
    "search": ("fa5s.search", "SP_FileDialogContentsView"),
    "columns": ("fa5s.columns", "SP_FileDialogListView"),
    "remove": ("fa5s.times", "SP_DialogCloseButton"),
    "upload": ("fa5s.file-upload", "SP_ArrowUp"),
    "add": ("fa5s.plus", "SP_FileDialogNewFolder"),
    "warning": ("fa5s.exclamation-triangle", "SP_MessageBoxWarning"),
    "info": ("fa5s.info-circle", "SP_MessageBoxInformation"),
    "log": ("fa5s.list-alt", "SP_FileDialogDetailedView"),
    "summary": ("fa5s.chart-bar", "SP_FileDialogInfoView"),
    "aligned": ("fa5s.th-list", "SP_FileDialogListView"),
    "pair": ("fa5s.exchange-alt", "SP_BrowserReload"),
    "template": ("fa5s.clone", "SP_FileDialogNewFolder"),
    "copy": ("fa5s.copy", "SP_DialogSaveButton"),
    "note": ("fa5s.sticky-note", "SP_FileDialogInfoView"),
    "check": ("fa5s.check-circle", "SP_DialogApplyButton"),
    "sample": ("fa5s.flask", "SP_DriveHDIcon"),
    "folder": ("fa5s.folder", "SP_DirIcon"),
    "trash": ("fa5s.trash-alt", "SP_TrashIcon"),
    "db": ("fa5s.database", "SP_DriveHDIcon"),
    "clear": ("fa5s.eraser", "SP_DialogResetButton"),
    "sun": ("fa5s.sun", "SP_DesktopIcon"),
    "moon": ("fa5s.moon", "SP_DesktopIcon"),
    "app": ("fa5s.layer-group", "SP_ComputerIcon"),
    "chevron-down": ("fa5s.chevron-down", "SP_ArrowDown"),
    "chevron-up": ("fa5s.chevron-up", "SP_ArrowUp"),
}


def arrow_images(color: str, cache_dir) -> dict[str, str]:
    """Salva le frecce per combo/spinbox come PNG (usate dal foglio di stile)."""
    out: dict[str, str] = {}
    if not HAS_QTA:
        return out
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        for name in ("chevron-down", "chevron-up"):
            path = cache_dir / f"{name}_{color.lstrip('#')}.png"
            if not path.exists():
                icon(name, color).pixmap(24, 24).save(str(path))
            out[name] = path.as_posix()
    except Exception:  # noqa: BLE001
        log.debug("Impossibile creare le immagini delle frecce", exc_info=True)
    return out


_default_color: str | None = None


def set_default_color(color: str | None) -> None:
    """Colore usato dalle icone senza colore esplicito (segue il tema)."""
    global _default_color
    _default_color = color


def icon(name: str, color: str | None = None) -> QIcon:
    fa_name, fallback = ICONS.get(name, ("fa5s.circle", "SP_FileIcon"))
    color = color or _default_color
    if HAS_QTA:
        try:
            return qta.icon(fa_name, color=color) if color else qta.icon(fa_name)
        except Exception:  # noqa: BLE001
            log.debug("Icona %s non trovata", fa_name)
    style = QApplication.style()
    sp = getattr(QStyle.StandardPixmap, fallback, QStyle.StandardPixmap.SP_FileIcon)
    return style.standardIcon(sp) if style else QIcon()
