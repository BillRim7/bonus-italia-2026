"""Lettura di file Excel/CSV, rilevamento colonne e normalizzazione distinte."""
from __future__ import annotations

import csv
import io
import logging
import math
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable

import pandas as pd

from .models import BOMData, FIELDS, FIELD_LABELS, coerce_normalized

log = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".xlsx", ".xlsm", ".xls", ".csv", ".txt"}
FILE_DIALOG_FILTER = ("Distinte (*.xlsx *.xlsm *.xls *.csv *.txt);;"
                      "Excel (*.xlsx *.xlsm *.xls);;CSV (*.csv *.txt);;Tutti i file (*)")

ProgressFn = Callable[[int, str], None]


class BOMLoadError(Exception):
    """Errore di caricamento con messaggio comprensibile per l'utente."""


# --------------------------------------------------------------------------- #
# Utilità di normalizzazione
# --------------------------------------------------------------------------- #
def normalize_header(text: Any) -> str:
    """'Q.tà Unitaria' -> 'qta unitaria' (minuscolo, senza accenti/simboli)."""
    if text is None or (isinstance(text, float) and math.isnan(text)):
        return ""
    s = unicodedata.normalize("NFKD", str(text))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def cell_to_str(value: Any) -> str:
    """Converte una cella in testo pulito (1001.0 -> '1001')."""
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        if value.is_integer():
            return str(int(value))
        return repr(value)
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    return "" if s.lower() in ("nan", "none", "nat") else s


_NUM_CLEAN = re.compile(r"[^\d,.\-+eE]")


def parse_number(value: Any) -> float:
    """Interpreta numeri in formato italiano o inglese.

    '1.234,5' -> 1234.5 ; '1,5' -> 1.5 ; '1,234.5' -> 1234.5 ; '€ 12' -> 12
    Restituisce NaN se il valore non è numerico.
    """
    if value is None:
        return math.nan
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    s = _NUM_CLEAN.sub("", str(value).strip())
    if not s or s in "+-.,":
        return math.nan
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        # Una sola virgola = separatore decimale; più virgole = migliaia.
        s = s.replace(",", ".") if s.count(",") == 1 else s.replace(",", "")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return math.nan


def parse_level(value: Any) -> float:
    """Livello distinta: '2', 2.0, '..2' (stile SAP) o '...' (conteggio punti)."""
    if value is None:
        return math.nan
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return math.nan
    digits = re.sub(r"[^\d]", "", s)
    if digits:
        return float(digits)
    dots = s.count(".")
    return float(dots) if dots else math.nan


# --------------------------------------------------------------------------- #
# Lettura grezza
# --------------------------------------------------------------------------- #
def _check_file(path: str) -> str:
    if not path or not os.path.exists(path):
        raise BOMLoadError(f"Il file non esiste:\n{path}")
    if os.path.isdir(path):
        raise BOMLoadError("È stata selezionata una cartella, non un file.")
    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise BOMLoadError(
            f"Formato '{ext or 'sconosciuto'}' non supportato.\n"
            "Usa file Excel (.xlsx, .xls) oppure CSV.")
    if os.path.getsize(path) == 0:
        raise BOMLoadError("Il file è vuoto.")
    return ext


def list_sheets(path: str) -> list[str]:
    """Elenco dei fogli di un file Excel (lista vuota per i CSV)."""
    ext = _check_file(path)
    if ext in (".csv", ".txt"):
        return []
    try:
        with pd.ExcelFile(path) as xls:
            return [str(s) for s in xls.sheet_names]
    except Exception as exc:  # noqa: BLE001 - convertito in messaggio utente
        raise _friendly_error(exc, path) from exc


def _friendly_error(exc: Exception, path: str) -> BOMLoadError:
    name = os.path.basename(path)
    if isinstance(exc, BOMLoadError):
        return exc
    if isinstance(exc, PermissionError):
        return BOMLoadError(
            f"Impossibile aprire '{name}': il file è in uso da un altro programma "
            "(ad esempio Excel).\nChiudi il file e riprova.")
    if isinstance(exc, ImportError) and "xlrd" in str(exc):
        return BOMLoadError(
            "Per leggere i vecchi file .xls serve il componente 'xlrd'.\n"
            "In alternativa salva il file come .xlsx da Excel e riprova.")
    msg = str(exc).lower()
    if "encrypted" in msg or "password" in msg:
        return BOMLoadError(f"Il file '{name}' è protetto da password. "
                            "Rimuovi la protezione e riprova.")
    if "zip" in msg or "not a zip" in msg or "unsupported format" in msg or "corrupt" in msg:
        return BOMLoadError(f"Il file '{name}' sembra danneggiato o non è un file Excel valido.")
    log.exception("Errore lettura file %s", path)
    return BOMLoadError(f"Impossibile leggere il file '{name}'.\nDettaglio tecnico: {exc}")


def _read_text(path: str) -> str:
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _sniff_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t|").delimiter
    except csv.Error:
        counts = {d: sample.count(d) for d in (";", ",", "\t", "|")}
        return max(counts, key=counts.get)


def read_raw(path: str, sheet: str | None = None) -> pd.DataFrame:
    """Legge il file senza intestazione: tutte le celle come oggetti/testo."""
    ext = _check_file(path)
    try:
        if ext in (".csv", ".txt"):
            text = _read_text(path)
            delimiter = _sniff_delimiter(text[:8192])
            df = pd.read_csv(io.StringIO(text), sep=delimiter, header=None,
                             dtype=str, keep_default_na=False,
                             skip_blank_lines=False, engine="python",
                             on_bad_lines="warn")
        else:
            df = pd.read_excel(path, sheet_name=sheet if sheet is not None else 0,
                               header=None, dtype=object)
    except Exception as exc:  # noqa: BLE001
        raise _friendly_error(exc, path) from exc
    # Rimuove righe e colonne completamente vuote ai bordi.
    df = df.replace({"": None})
    df = df.dropna(how="all").dropna(axis=1, how="all")
    if df.empty:
        raise BOMLoadError("Il file (o il foglio selezionato) non contiene dati.")
    return df.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Rilevamento intestazione e colonne
# --------------------------------------------------------------------------- #
def _alias_score(header: str, alias: str) -> int:
    if not header or not alias:
        return 0
    if header == alias:
        return 100 + len(alias)
    h_tokens = header.split()
    a_tokens = alias.split()
    if h_tokens[: len(a_tokens)] == a_tokens:
        return 60 + len(alias)
    if len(alias) >= 3 and f" {alias} " in f" {header} ":
        return 30 + len(alias)
    return 0


def detect_columns(columns: list[str], aliases: dict[str, list[str]]) -> dict[str, str]:
    """Associa automaticamente i campi standard alle colonne del file.

    Assegnazione "greedy" per punteggio: ogni colonna e ogni campo vengono
    usati al massimo una volta.
    """
    normalized = {col: normalize_header(col) for col in columns}
    candidates: list[tuple[int, int, str, str]] = []
    for fld in FIELDS:
        for priority, alias in enumerate(aliases.get(fld, [])):
            alias_n = normalize_header(alias)
            for col, col_n in normalized.items():
                score = _alias_score(col_n, alias_n)
                if score:
                    candidates.append((score, -priority, fld, col))
    candidates.sort(reverse=True)
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for _score, _prio, fld, col in candidates:
        if fld in mapping or col in used:
            continue
        mapping[fld] = col
        used.add(col)
    return mapping


def detect_header_row(raw: pd.DataFrame, aliases: dict[str, list[str]],
                      max_scan: int = 30) -> int:
    """Trova la riga d'intestazione (salta titoli/loghi sopra la tabella)."""
    best_row, best_score = 0, -1
    for idx in range(min(max_scan, len(raw))):
        values = [cell_to_str(v) for v in raw.iloc[idx].tolist()]
        mapping = detect_columns([v for v in values if v], aliases)
        score = len(mapping) * 10 + (15 if "code" in mapping else 0)
        if score > best_score:
            best_row, best_score = idx, score
    return best_row


def apply_header(raw: pd.DataFrame, header_row: int) -> pd.DataFrame:
    """Usa la riga ``header_row`` come intestazione (nomi resi univoci)."""
    header_row = max(0, min(header_row, len(raw) - 1))
    names: list[str] = []
    seen: dict[str, int] = {}
    for i, value in enumerate(raw.iloc[header_row].tolist()):
        name = cell_to_str(value) or f"Colonna {i + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name} ({seen[name]})"
        else:
            seen[name] = 1
        names.append(name)
    body = raw.iloc[header_row + 1:].copy()
    body.columns = names
    return body.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Normalizzazione
# --------------------------------------------------------------------------- #
def _derive_parents(codes: list[str], levels: list[float]) -> list[str]:
    """Deduce il codice padre da una distinta indentata per livelli."""
    parents: list[str] = []
    stack: list[tuple[float, str]] = []  # (livello, codice)
    for code, lvl in zip(codes, levels):
        if lvl is None or math.isnan(lvl):
            parents.append("")
            continue
        while stack and stack[-1][0] >= lvl:
            stack.pop()
        parents.append(stack[-1][1] if stack else "")
        stack.append((lvl, code))
    return parents


def _join_unique(values: pd.Series) -> str:
    uniq: list[str] = []
    for v in values:
        if v and v not in uniq:
            uniq.append(v)
    return " | ".join(uniq)


def normalize_bom(table: pd.DataFrame, mapping: dict[str, str],
                  settings: dict[str, Any] | None = None) -> tuple[pd.DataFrame, list[str], int]:
    """Converte la tabella con intestazione in una distinta normalizzata.

    Restituisce (dataframe normalizzato, avvisi, righe valide lette).
    """
    settings = settings or {}
    if not mapping.get("code"):
        raise BOMLoadError("Non è stata indicata la colonna del Codice articolo.\n"
                           "Apri 'Colonne…' e seleziona la colonna corretta.")
    missing = [c for c in mapping.values() if c and c not in table.columns]
    if missing:
        raise BOMLoadError("Colonne non trovate nel file: " + ", ".join(missing))

    warnings: list[str] = []
    out = pd.DataFrame(index=table.index)
    out["row"] = range(len(table))
    for fld in FIELDS:
        col = mapping.get(fld)
        if fld in ("quantity", "price"):
            out[fld] = table[col].map(parse_number) if col else math.nan
        elif fld == "level":
            out[fld] = table[col].map(parse_level) if col else math.nan
        else:
            out[fld] = table[col].map(cell_to_str) if col else ""

    # Righe senza codice: totali, righe vuote, note -> scartate.
    empty_code = out["code"] == ""
    if empty_code.any():
        warnings.append(f"{int(empty_code.sum())} righe senza codice articolo ignorate.")
    out = out[~empty_code].copy()
    if out.empty:
        raise BOMLoadError("Nessuna riga con codice articolo trovata.\n"
                           "Verifica la mappatura delle colonne e la riga di intestazione.")

    if mapping.get("quantity"):
        bad_qty = out["quantity"].isna()
        if bad_qty.any():
            warnings.append(f"{int(bad_qty.sum())} righe con quantità non numerica "
                            "considerate pari a 0.")
        out["quantity"] = out["quantity"].fillna(0.0)
    else:
        out["quantity"] = 1.0
        warnings.append("Colonna quantità assente: assunta quantità 1 per ogni riga.")

    # Multi-livello: deduce il padre se è presente solo il livello.
    if mapping.get("level") and not mapping.get("parent"):
        out["parent"] = _derive_parents(out["code"].tolist(), out["level"].tolist())

    ws = settings.get("ignore_whitespace", True)
    if ws:
        out["description"] = out["description"].str.replace(r"\s+", " ", regex=True).str.strip()
    out["key"] = out["code"].str.strip()
    if settings.get("code_case_insensitive", True):
        out["key"] = out["key"].str.upper()

    raw_valid = len(out)
    dup_mask = out["key"].duplicated(keep=False)
    if dup_mask.any():
        n_codes = out.loc[dup_mask, "key"].nunique()
        if settings.get("aggregate_duplicates", True):
            warnings.append(f"{n_codes} codici presenti su più righe: quantità sommate "
                            "(es. stesso componente in più sotto-assiemi).")
            out = _aggregate(out)
        else:
            warnings.append(f"{n_codes} codici duplicati: mantenuta solo la prima riga.")
            out = out.drop_duplicates("key", keep="first")
    out["occurrences"] = out.get("occurrences", 1)
    return coerce_normalized(out), warnings, raw_valid


def _aggregate(df: pd.DataFrame) -> pd.DataFrame:
    """Aggrega le righe con lo stesso codice (somma quantità)."""
    df = df.copy()
    df["occurrences"] = 1
    agg = {
        "code": "first", "description": "first", "quantity": "sum", "uom": "first",
        "revision": _join_unique, "supplier": _join_unique, "price": "first",
        "level": "min", "parent": _join_unique, "occurrences": "sum", "row": "min",
    }
    grouped = df.groupby("key", sort=False).agg(agg).reset_index()
    return grouped.sort_values("row", kind="mergesort")


# --------------------------------------------------------------------------- #
# Caricamento completo
# --------------------------------------------------------------------------- #
@dataclass
class RawTable:
    """Risultato intermedio: file letto, intestazione e colonne rilevate."""

    path: str
    raw: pd.DataFrame
    sheets: list[str] = field(default_factory=list)
    sheet: str | None = None
    header_row: int = 0
    mapping: dict[str, str] = field(default_factory=dict)

    @property
    def table(self) -> pd.DataFrame:
        return apply_header(self.raw, self.header_row)

    @property
    def is_mapping_complete(self) -> bool:
        return bool(self.mapping.get("code"))


def inspect_file(path: str, aliases: dict[str, list[str]], sheet: str | None = None,
                 header_row: int | None = None, progress: ProgressFn | None = None) -> RawTable:
    """Legge il file e propone foglio, riga d'intestazione e mappatura."""
    progress = progress or (lambda *_: None)
    progress(5, "Apertura file…")
    sheets = list_sheets(path)
    if sheets and sheet is None:
        # Sceglie il foglio con l'intestazione più riconoscibile.
        best = (-1, sheets[0])
        for idx, name in enumerate(sheets[:10]):
            progress(10 + idx * 3, f"Analisi foglio '{name}'…")
            try:
                raw = read_raw(path, name)
            except BOMLoadError:
                continue
            hdr = detect_header_row(raw, aliases)
            score = len(detect_columns([cell_to_str(v) for v in raw.iloc[hdr]], aliases))
            if score > best[0]:
                best = (score, name)
        sheet = best[1]
    progress(45, "Lettura dati…")
    raw = read_raw(path, sheet)
    progress(65, "Rilevamento colonne…")
    if header_row is None:
        header_row = detect_header_row(raw, aliases)
    rt = RawTable(path=path, raw=raw, sheets=sheets, sheet=sheet, header_row=header_row)
    rt.mapping = detect_columns(list(rt.table.columns), aliases)
    log.info("File %s: foglio=%s intestazione=%d mappatura=%s",
             path, sheet, header_row, rt.mapping)
    return rt


def build_bom(rt: RawTable, role: str, settings: dict[str, Any] | None = None,
              progress: ProgressFn | None = None) -> BOMData:
    """Normalizza un RawTable con la mappatura scelta e crea la BOMData."""
    progress = progress or (lambda *_: None)
    progress(75, "Normalizzazione distinta…")
    table = rt.table
    df, warnings, raw_valid = normalize_bom(table, rt.mapping, settings)
    progress(100, "Completato")
    mapping = {k: v for k, v in rt.mapping.items() if v}
    return BOMData(role=role, source_path=rt.path, df=df, sheet=rt.sheet,
                   header_row=rt.header_row, mapping=mapping,
                   raw_rows=raw_valid, warnings=warnings)


def describe_mapping(mapping: dict[str, str]) -> str:
    return "\n".join(f"{FIELD_LABELS[f]}: {mapping[f]}" for f in FIELDS if mapping.get(f))
