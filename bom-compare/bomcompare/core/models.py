"""Strutture dati condivise: campi della distinta, stati e classe BOMData."""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd

# --------------------------------------------------------------------------- #
# Campi normalizzati di una distinta
# --------------------------------------------------------------------------- #
FIELDS: list[str] = ["code", "description", "quantity", "uom", "revision",
                     "supplier", "price", "level", "parent"]

FIELD_LABELS: dict[str, str] = {
    "code": "Codice articolo",
    "description": "Descrizione",
    "quantity": "Quantità",
    "uom": "Unità di misura",
    "revision": "Revisione",
    "supplier": "Fornitore",
    "price": "Prezzo unitario",
    "level": "Livello",
    "parent": "Codice padre",
}

FIELD_HINTS: dict[str, str] = {
    "code": "Obbligatorio. Identifica univocamente il componente.",
    "description": "Consigliato. Usato anche per la ricerca rapida.",
    "quantity": "Consigliato. Se assente si assume 1 per ogni riga.",
    "uom": "Facoltativo. Es. PZ, KG, M.",
    "revision": "Facoltativo. Abilita il rilevamento dei cambi di revisione.",
    "supplier": "Facoltativo. Abilita il rilevamento dei cambi fornitore.",
    "price": "Facoltativo. Abilita il calcolo dell'impatto economico.",
    "level": "Facoltativo. Per distinte multi-livello (1, 2, 3… oppure .1, ..2).",
    "parent": "Facoltativo. Codice dell'assieme padre (dedotto dal livello se assente).",
}

REQUIRED_FIELDS = ["code"]
NUMERIC_FIELDS = {"quantity", "price", "level"}
TEXT_FIELDS = [f for f in FIELDS if f not in NUMERIC_FIELDS]

# Campi che possono generare lo stato "Modificato".
COMPARE_FIELD_LABELS: dict[str, str] = {
    "quantity": "Quantità",
    "description": "Descrizione",
    "uom": "Unità di misura",
    "revision": "Revisione",
    "supplier": "Fornitore",
    "price": "Prezzo",
    "structure": "Struttura (livello/padre)",
}

# --------------------------------------------------------------------------- #
# Stati del confronto
# --------------------------------------------------------------------------- #
ADDED = "Aggiunto"
REMOVED = "Eliminato"
MODIFIED = "Modificato"
UNCHANGED = "Invariato"
STATUSES = [ADDED, REMOVED, MODIFIED, UNCHANGED]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# --------------------------------------------------------------------------- #
# Serializzazione DataFrame <-> JSON (senza inferenze di tipo indesiderate)
# --------------------------------------------------------------------------- #
def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):  # numpy scalar
        value = value.item()
        if isinstance(value, float) and math.isnan(value):
            return None
    return value


def df_to_payload(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "columns": list(df.columns),
        "data": [[_clean(v) for v in row] for row in df.itertuples(index=False, name=None)],
    }


def normalized_from_payload(payload: dict[str, Any]) -> pd.DataFrame:
    """Ricostruisce una distinta normalizzata forzando i tipi corretti."""
    df = pd.DataFrame(payload.get("data", []), columns=payload.get("columns", []))
    return coerce_normalized(df)


def coerce_normalized(df: pd.DataFrame) -> pd.DataFrame:
    """Garantisce colonne e tipi standard di una distinta normalizzata."""
    df = df.copy()
    for col in FIELDS + ["key", "occurrences", "row"]:
        if col not in df.columns:
            df[col] = None
    for col in ("quantity", "price", "level"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
    for col in TEXT_FIELDS + ["key"]:
        df[col] = df[col].where(df[col].notna(), "").astype(str)
    df["occurrences"] = pd.to_numeric(df["occurrences"], errors="coerce").fillna(1).astype(int)
    df["row"] = pd.to_numeric(df["row"], errors="coerce").fillna(0).astype(int)
    return df[["key"] + FIELDS + ["occurrences", "row"]].reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Distinta caricata
# --------------------------------------------------------------------------- #
@dataclass
class BOMData:
    """Una distinta base caricata e normalizzata.

    ``df`` contiene una riga per codice articolo (righe duplicate aggregate)
    con le colonne: key, code, description, quantity, uom, revision,
    supplier, price, level, parent, occurrences, row.
    """

    role: str
    source_path: str
    df: pd.DataFrame
    sheet: str | None = None
    header_row: int = 0
    mapping: dict[str, str] = field(default_factory=dict)
    raw_rows: int = 0
    warnings: list[str] = field(default_factory=list)
    loaded_at: str = field(default_factory=now_str)

    @property
    def file_name(self) -> str:
        import os
        return os.path.basename(self.source_path) if self.source_path else "(storico)"

    @property
    def row_count(self) -> int:
        return len(self.df)

    def has(self, fld: str) -> bool:
        """True se il campo è presente nella sorgente (mappato o dedotto)."""
        if fld == "parent" and self.has("level"):
            return True
        return fld in self.mapping and bool(self.mapping[fld])

    def content_hash(self) -> str:
        cols = ["key", "quantity", "description", "uom", "revision", "supplier",
                "price", "level", "parent"]
        payload = self.df[cols].to_csv(index=False).encode("utf-8")
        return hashlib.sha1(payload).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "source_path": self.source_path,
            "sheet": self.sheet,
            "header_row": self.header_row,
            "mapping": self.mapping,
            "raw_rows": self.raw_rows,
            "warnings": self.warnings,
            "loaded_at": self.loaded_at,
            "data": df_to_payload(self.df),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BOMData":
        return cls(
            role=payload.get("role", ""),
            source_path=payload.get("source_path", ""),
            df=normalized_from_payload(payload.get("data", {})),
            sheet=payload.get("sheet"),
            header_row=int(payload.get("header_row", 0) or 0),
            mapping=dict(payload.get("mapping", {})),
            raw_rows=int(payload.get("raw_rows", 0) or 0),
            warnings=list(payload.get("warnings", [])),
            loaded_at=payload.get("loaded_at", now_str()),
        )
