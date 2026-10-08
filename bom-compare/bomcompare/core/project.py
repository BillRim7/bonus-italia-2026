"""Salvataggio/apertura dei progetti ``.bomcompare``.

Il progetto è un file JSON (UTF-8) che contiene anche i dati delle distinte:
si può riaprire anche se i file Excel originali sono stati spostati.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from .. import __version__
from .models import BOMData, now_str

log = logging.getLogger(__name__)

FORMAT_ID = "bomcompare-project"
FORMAT_VERSION = 1


class ProjectError(Exception):
    """Errore di apertura/salvataggio progetto (messaggio per l'utente)."""


@dataclass
class ProjectState:
    """Stato del lavoro corrente dell'utente."""

    machine: str = ""
    template: str = "Standard"
    roles: list[str] = field(default_factory=list)
    boms: list[BOMData | None] = field(default_factory=list)
    notes: dict[str, str] = field(default_factory=dict)
    change_log: list[dict[str, str]] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_str)

    def log_event(self, event: str, detail: str = "") -> dict[str, str]:
        entry = {"timestamp": now_str(), "event": event, "detail": detail}
        self.change_log.append(entry)
        log.info("[log progetto] %s %s", event, detail)
        return entry

    def loaded_boms(self) -> list[BOMData]:
        return [b for b in self.boms if b is not None]

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": FORMAT_ID,
            "format_version": FORMAT_VERSION,
            "app_version": __version__,
            "saved_at": now_str(),
            "created_at": self.created_at,
            "machine": self.machine,
            "template": self.template,
            "roles": self.roles,
            "boms": [b.to_dict() if b is not None else None for b in self.boms],
            "notes": self.notes,
            "change_log": self.change_log,
            "settings": self.settings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectState":
        if data.get("format") != FORMAT_ID:
            raise ProjectError("Il file selezionato non è un progetto BOM Compare.")
        if int(data.get("format_version", 0)) > FORMAT_VERSION:
            raise ProjectError("Il progetto è stato creato con una versione più recente "
                               "di BOM Compare. Aggiorna l'applicazione.")
        return cls(
            machine=data.get("machine", ""),
            template=data.get("template", "Standard"),
            roles=list(data.get("roles", [])),
            boms=[BOMData.from_dict(b) if b else None for b in data.get("boms", [])],
            notes=dict(data.get("notes", {})),
            change_log=list(data.get("change_log", [])),
            settings=dict(data.get("settings", {})),
            created_at=data.get("created_at", now_str()),
        )


def save_project(path: str, state: ProjectState) -> None:
    try:
        payload = json.dumps(state.to_dict(), ensure_ascii=False)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(payload)
        import os
        os.replace(tmp, path)
        log.info("Progetto salvato: %s", path)
    except PermissionError as exc:
        raise ProjectError("Impossibile salvare: il file è in uso o la cartella "
                           "non è scrivibile.") from exc
    except OSError as exc:
        raise ProjectError(f"Impossibile salvare il progetto:\n{exc}") from exc


def load_project(path: str) -> ProjectState:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError as exc:
        raise ProjectError(f"Progetto non trovato:\n{path}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ProjectError("Il file di progetto è danneggiato o non valido.") from exc
    except OSError as exc:
        raise ProjectError(f"Impossibile aprire il progetto:\n{exc}") from exc
    state = ProjectState.from_dict(data)
    log.info("Progetto aperto: %s", path)
    return state
