"""Gestione della configurazione.

Due livelli:
  * ``config.json`` accanto all'eseguibile (o alla radice del progetto):
    impostazioni aziendali condivise (alias colonne, template, tolleranze).
  * ``user_settings.json`` nella cartella dati utente: preferenze personali
    (tema, primo avvio, file recenti, template creati dall'utente).
"""
from __future__ import annotations

import copy
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Valori di riserva usati se config.json manca o è danneggiato.
_BUILTIN_DEFAULTS: dict[str, Any] = {
    "app": {"name": "BOM Compare", "log_level": "INFO"},
    "comparison": {
        "tolerance_pct": 10.0,
        "qty_epsilon": 1e-6,
        "ignore_description_case": True,
        "ignore_whitespace": True,
        "code_case_insensitive": True,
        "aggregate_duplicates": True,
        "compare_fields": ["quantity", "description", "uom", "revision",
                           "supplier", "price", "structure"],
    },
    "default_roles": ["Macchina VECCHIA", "Macchina in PRODUZIONE",
                      "Macchina in PROGETTAZIONE"],
    "max_boms": 6,
    "column_aliases": {
        "code": ["codice articolo", "codice", "articolo", "part number", "item"],
        "description": ["descrizione", "description"],
        "quantity": ["quantita", "qta", "qty", "quantity"],
        "uom": ["unita di misura", "um", "uom"],
        "revision": ["revisione", "rev", "revision"],
        "supplier": ["fornitore", "supplier", "vendor"],
        "price": ["prezzo", "costo", "price", "cost"],
        "level": ["livello", "level"],
        "parent": ["codice padre", "padre", "parent"],
    },
    "history": {"enabled": True, "auto_snapshot_on_load": True, "max_snapshots": 1000},
    "ui": {"default_theme": "light", "row_height": 26, "preview_rows": 100},
    "templates": {"Standard": {"description": "Impostazioni generiche.",
                               "tolerance_pct": 10.0, "extra_aliases": {}}},
}

_USER_DEFAULTS: dict[str, Any] = {
    "theme": None,              # None -> usa ui.default_theme
    "first_run": True,
    "recent_projects": [],
    "last_dir": "",
    "template": "Standard",
    "user_templates": {},
    "comparison_overrides": {},  # sovrascritture personali di "comparison"
    "window_geometry": None,
}


# --------------------------------------------------------------------------- #
# Percorsi
# --------------------------------------------------------------------------- #
def is_frozen() -> bool:
    """True se l'app gira come eseguibile PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """Cartella dell'applicazione (accanto all'.exe o radice del progetto)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def resource_dir() -> Path:
    """Cartella delle risorse incluse nel pacchetto (PyInstaller _MEIPASS)."""
    return Path(getattr(sys, "_MEIPASS", app_dir()))


def resource_path(*parts: str) -> Path:
    """Cerca una risorsa prima accanto all'eseguibile, poi nel pacchetto."""
    local = app_dir().joinpath(*parts)
    if local.exists():
        return local
    return resource_dir().joinpath(*parts)


def user_data_dir() -> Path:
    """Cartella dati utente (impostazioni, storico SQLite, log)."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        path = base / "BOMCompare"
    else:
        path = Path.home() / ".bomcompare"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _deep_merge(base: dict, override: dict) -> dict:
    """Unisce ricorsivamente ``override`` in una copia di ``base``."""
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


# --------------------------------------------------------------------------- #
# Configurazione
# --------------------------------------------------------------------------- #
class AppConfig:
    """Accesso unico a configurazione aziendale + preferenze utente."""

    def __init__(self, config_path: Path | None = None, user_dir: Path | None = None):
        self.config_path = config_path or resource_path("config.json")
        self.user_dir = user_dir or user_data_dir()
        self.user_settings_path = self.user_dir / "user_settings.json"
        self.data: dict[str, Any] = self._load_config()
        self.user: dict[str, Any] = self._load_user()

    # -- caricamento -------------------------------------------------------- #
    def _load_config(self) -> dict[str, Any]:
        try:
            with open(self.config_path, encoding="utf-8") as fh:
                loaded = json.load(fh)
            log.info("Configurazione caricata da %s", self.config_path)
            return _deep_merge(_BUILTIN_DEFAULTS, loaded)
        except FileNotFoundError:
            log.warning("config.json non trovato (%s): uso valori predefiniti",
                        self.config_path)
        except (OSError, json.JSONDecodeError) as exc:
            log.error("config.json non valido: %s. Uso valori predefiniti", exc)
        return copy.deepcopy(_BUILTIN_DEFAULTS)

    def _load_user(self) -> dict[str, Any]:
        try:
            with open(self.user_settings_path, encoding="utf-8") as fh:
                return _deep_merge(_USER_DEFAULTS, json.load(fh))
        except FileNotFoundError:
            pass
        except (OSError, json.JSONDecodeError) as exc:
            log.error("Impostazioni utente non leggibili: %s", exc)
        return copy.deepcopy(_USER_DEFAULTS)

    def save_user(self) -> None:
        try:
            tmp = self.user_settings_path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.user, fh, indent=2, ensure_ascii=False)
            tmp.replace(self.user_settings_path)
        except OSError as exc:
            log.error("Impossibile salvare le impostazioni utente: %s", exc)

    # -- accesso ------------------------------------------------------------ #
    def get(self, dotted: str, default: Any = None) -> Any:
        """Legge una chiave annidata, es. ``get("ui.row_height")``."""
        node: Any = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    @property
    def theme(self) -> str:
        return self.user.get("theme") or self.get("ui.default_theme", "light")

    @property
    def templates(self) -> dict[str, dict]:
        """Template aziendali + template creati dall'utente."""
        merged = dict(self.get("templates", {}))
        merged.update(self.user.get("user_templates", {}))
        return merged

    def comparison_settings(self) -> dict[str, Any]:
        """Impostazioni di confronto effettive (config + template + utente)."""
        base = dict(self.get("comparison", {}))
        template = self.templates.get(self.user.get("template", ""), {})
        for key in ("tolerance_pct", "compare_fields"):
            if key in template:
                base[key] = template[key]
        base.update(self.user.get("comparison_overrides", {}))
        return base

    def column_aliases(self) -> dict[str, list[str]]:
        """Alias colonne, inclusi quelli aggiuntivi del template attivo."""
        aliases = {k: list(v) for k, v in self.get("column_aliases", {}).items()}
        template = self.templates.get(self.user.get("template", ""), {})
        for field, extra in template.get("extra_aliases", {}).items():
            aliases.setdefault(field, [])
            # Gli alias del template hanno priorità: vanno in testa.
            aliases[field] = list(extra) + [a for a in aliases[field] if a not in extra]
        return aliases

    def roles(self) -> list[str]:
        template = self.templates.get(self.user.get("template", ""), {})
        return list(template.get("roles") or self.get("default_roles", []))

    def add_recent_project(self, path: str) -> None:
        recent = [p for p in self.user.get("recent_projects", []) if p != path]
        self.user["recent_projects"] = [path] + recent[:9]
        self.save_user()
