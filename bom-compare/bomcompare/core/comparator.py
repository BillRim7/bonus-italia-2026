"""Motore di confronto tra distinte (vettorizzato con pandas).

* ``compare_pair``  : confronto tra due distinte (vecchia -> nuova)
* ``compare_all``   : confronto di N distinte con allineamento per codice e
                      tutte le combinazioni a coppie.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd

from .models import (ADDED, COMPARE_FIELD_LABELS, MODIFIED, REMOVED, UNCHANGED,
                     BOMData, now_str)

log = logging.getLogger(__name__)

VALUE_FIELDS = ["code", "description", "quantity", "uom", "revision",
                "supplier", "price", "level", "parent"]


@dataclass
class CompareSettings:
    tolerance_pct: float = 10.0
    qty_epsilon: float = 1e-6
    ignore_description_case: bool = True
    ignore_whitespace: bool = True
    compare_fields: list[str] = field(
        default_factory=lambda: list(COMPARE_FIELD_LABELS.keys()))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompareSettings":
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        return cls(**known)

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


# --------------------------------------------------------------------------- #
# Confronto a coppie
# --------------------------------------------------------------------------- #
def _norm_text(series: pd.Series, settings: CompareSettings, is_desc: bool) -> pd.Series:
    s = series.fillna("").astype(str)
    if settings.ignore_whitespace:
        s = s.str.replace(r"\s+", " ", regex=True).str.strip()
    if is_desc and settings.ignore_description_case:
        s = s.str.lower()
    return s


def compare_pair(old: BOMData, new: BOMData, settings: CompareSettings) -> pd.DataFrame:
    """Confronta due distinte. Una riga per codice (unione dei codici).

    Colonne principali: key, code, description, <campo>_a / <campo>_b,
    delta_qty, delta_pct, status, chg_<campo>, changes, out_of_tol, impact, order.
    """
    a = old.df[["key", "row"] + VALUE_FIELDS].copy()
    b = new.df[["key", "row"] + VALUE_FIELDS].copy()
    a["_in_a"] = True
    b["_in_b"] = True
    m = a.merge(b, on="key", how="outer", suffixes=("_a", "_b"), sort=False)
    in_a = m["_in_a"].eq(True).to_numpy()
    in_b = m["_in_b"].eq(True).to_numpy()
    both = in_a & in_b

    res = pd.DataFrame({"key": m["key"]})
    res["code"] = m["code_b"].where(in_b, m["code_a"]).fillna("")
    res["description"] = m["description_b"].where(
        in_b & m["description_b"].fillna("").ne(""), m["description_a"]).fillna("")
    for f in VALUE_FIELDS:
        res[f"{f}_a"] = m[f"{f}_a"]
        res[f"{f}_b"] = m[f"{f}_b"]
    res["in_a"] = in_a
    res["in_b"] = in_b

    qa = m["quantity_a"].astype(float)
    qb = m["quantity_b"].astype(float)
    res["delta_qty"] = qb.fillna(0.0) - qa.fillna(0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        pct = np.where(qa.fillna(0).to_numpy() != 0,
                       (qb.fillna(0) - qa.fillna(0)) / qa.abs() * 100.0, np.nan)
    pct = np.where(~in_b & in_a, -100.0, pct)
    res["delta_pct"] = pct

    # ---- flag di modifica per campo -------------------------------------- #
    fields = set(settings.compare_fields)
    has = {f: old.has(f) and new.has(f) for f in VALUE_FIELDS}

    chg: dict[str, np.ndarray] = {}
    chg["quantity"] = both & (res["delta_qty"].abs() > settings.qty_epsilon).to_numpy()
    for f in ("description", "uom", "revision", "supplier"):
        if has[f]:
            ta = _norm_text(m[f"{f}_a"], settings, f == "description")
            tb = _norm_text(m[f"{f}_b"], settings, f == "description")
            if f == "uom":
                ta, tb = ta.str.upper(), tb.str.upper()
            chg[f] = both & (ta != tb).to_numpy()
        else:
            chg[f] = np.zeros(len(m), dtype=bool)
    if has["price"]:
        pa, pb = m["price_a"].astype(float), m["price_b"].astype(float)
        chg["price"] = both & (pa.notna() & pb.notna() & ((pa - pb).abs() > 1e-9)).to_numpy()
    else:
        chg["price"] = np.zeros(len(m), dtype=bool)
    if has["level"] or has["parent"]:
        la, lb = m["level_a"].astype(float), m["level_b"].astype(float)
        lvl_chg = (la.notna() & lb.notna() & (la != lb)).to_numpy()
        par_chg = (_norm_text(m["parent_a"], settings, False).str.upper()
                   != _norm_text(m["parent_b"], settings, False).str.upper()).to_numpy()
        chg["structure"] = both & (lvl_chg | par_chg)
    else:
        chg["structure"] = np.zeros(len(m), dtype=bool)

    modified = np.zeros(len(m), dtype=bool)
    for f, arr in chg.items():
        res[f"chg_{f}"] = arr
        if f in fields:
            modified |= arr

    status = np.full(len(m), UNCHANGED, dtype=object)
    status[modified] = MODIFIED
    status[in_b & ~in_a] = ADDED
    status[in_a & ~in_b] = REMOVED
    res["status"] = status
    res["changes"] = _changes_text(res, chg, fields)

    # ---- tolleranza e impatto economico ----------------------------------- #
    tol = float(settings.tolerance_pct or 0)
    res["out_of_tol"] = both & (np.abs(np.nan_to_num(res["delta_pct"].to_numpy(),
                                                     nan=0.0)) > tol) if tol > 0 else False
    pa = m["price_a"].astype(float)
    pb = m["price_b"].astype(float)
    if has["price"] or old.has("price") or new.has("price"):
        cost_a = (qa.fillna(0) * pa.fillna(pb).fillna(0)).where(in_a, 0.0)
        cost_b = (qb.fillna(0) * pb.fillna(pa).fillna(0)).where(in_b, 0.0)
        res["impact"] = cost_b - cost_a
    else:
        res["impact"] = np.nan

    # ---- ordine naturale (diff "interfogliato") ---------------------------- #
    res["order"] = _interleaved_order([old.df, new.df], res["key"])
    res = res.sort_values("order", kind="mergesort").reset_index(drop=True)
    return res


def _changes_text(res: pd.DataFrame, chg: dict[str, np.ndarray], fields: set[str]) -> list[str]:
    """Descrizione leggibile delle modifiche di ogni riga."""
    from .formatting import fmt_money, fmt_num
    parts: list[list[str]] = [[] for _ in range(len(res))]
    rev_a, rev_b = res["revision_a"].tolist(), res["revision_b"].tolist()
    sup_a, sup_b = res["supplier_a"].tolist(), res["supplier_b"].tolist()
    lvl_a, lvl_b = res["level_a"].tolist(), res["level_b"].tolist()
    par_a, par_b = res["parent_a"].tolist(), res["parent_b"].tolist()
    uom_a, uom_b = res["uom_a"].tolist(), res["uom_b"].tolist()
    prc_a, prc_b = res["price_a"].tolist(), res["price_b"].tolist()
    qty_a, qty_b = res["quantity_a"].tolist(), res["quantity_b"].tolist()
    for f in ("quantity", "description", "uom", "revision", "supplier", "price", "structure"):
        arr = chg[f]
        if f not in fields:
            continue
        for i in np.flatnonzero(arr):
            if f == "revision":
                parts[i].append(f"Rev. {rev_a[i] or '-'} → {rev_b[i] or '-'}")
            elif f == "supplier":
                parts[i].append(f"Fornitore {sup_a[i] or '-'} → {sup_b[i] or '-'}")
            elif f == "structure":
                txt = "Spostato"
                if lvl_a[i] == lvl_a[i] and lvl_b[i] == lvl_b[i] and lvl_a[i] != lvl_b[i]:
                    txt += f" liv. {int(lvl_a[i])} → {int(lvl_b[i])}"
                if (par_a[i] or "") != (par_b[i] or ""):
                    txt += f" (padre {par_a[i] or '-'} → {par_b[i] or '-'})"
                parts[i].append(txt)
            elif f == "quantity":
                parts[i].append(f"Qtà {fmt_num(qty_a[i])} → {fmt_num(qty_b[i])}")
            elif f == "uom":
                parts[i].append(f"U.M. {uom_a[i] or '-'} → {uom_b[i] or '-'}")
            elif f == "price":
                parts[i].append(f"Prezzo {fmt_money(prc_a[i])} → {fmt_money(prc_b[i])}")
            else:
                parts[i].append("Descrizione modificata")
    return ["; ".join(p) for p in parts]


def _interleaved_order(frames: list[pd.DataFrame], keys: pd.Series) -> np.ndarray:
    """Ordine "a la diff": segue la distinta più recente e inserisce gli
    articoli scomparsi subito dopo il loro predecessore nelle versioni
    precedenti. Restituisce il rango di ogni chiave in ``keys``.
    """
    n = len(frames)
    sort_key: dict[str, tuple] = {}
    newest = frames[-1]
    for pos, k in enumerate(newest.sort_values("row", kind="mergesort")["key"]):
        sort_key.setdefault(k, (pos,))
    for j in range(n - 2, -1, -1):
        prev: tuple | None = None
        for idx, k in enumerate(frames[j].sort_values("row", kind="mergesort")["key"]):
            if k in sort_key:
                prev = sort_key[k]
                continue
            base = prev if prev is not None else (-1,)
            sort_key[k] = base + (n - j, idx)
            prev = sort_key[k]
    ordered = sorted(sort_key, key=sort_key.__getitem__)
    rank = {k: i for i, k in enumerate(ordered)}
    return keys.map(rank).fillna(len(rank)).astype(int).to_numpy()


def summarize(pair: pd.DataFrame) -> dict[str, Any]:
    """Statistiche di un confronto a coppie."""
    counts = pair["status"].value_counts()
    impact = pair["impact"]
    has_impact = bool(impact.notna().any())
    return {
        "added": int(counts.get(ADDED, 0)),
        "removed": int(counts.get(REMOVED, 0)),
        "modified": int(counts.get(MODIFIED, 0)),
        "unchanged": int(counts.get(UNCHANGED, 0)),
        "total": int(len(pair)),
        "qty_changes": int(pair["chg_quantity"].sum()),
        "revision_changes": int(pair["chg_revision"].sum()),
        "supplier_changes": int(pair["chg_supplier"].sum()),
        "price_changes": int(pair["chg_price"].sum()),
        "structure_changes": int(pair["chg_structure"].sum()),
        "out_of_tolerance": int(pd.Series(pair["out_of_tol"]).sum()),
        "impact": float(impact.sum()) if has_impact else None,
        "cost_a": _total_cost(pair, "a") if has_impact else None,
        "cost_b": _total_cost(pair, "b") if has_impact else None,
    }


def _total_cost(pair: pd.DataFrame, side: str) -> float:
    q = pair[f"quantity_{side}"].astype(float).fillna(0)
    p = pair[f"price_{side}"].astype(float).fillna(0)
    return float((q * p).sum())


# --------------------------------------------------------------------------- #
# Confronto multiplo
# --------------------------------------------------------------------------- #
@dataclass
class ComparisonResult:
    """Risultato completo del confronto di N distinte."""

    names: list[str]
    boms: list[BOMData]
    pairs: dict[tuple[int, int], pd.DataFrame]
    aligned: pd.DataFrame
    settings: CompareSettings
    created_at: str = field(default_factory=now_str)

    @property
    def n(self) -> int:
        return len(self.names)

    def pair_label(self, pair: tuple[int, int]) -> str:
        i, j = pair
        return f"{self.names[i]} → {self.names[j]}"

    def pair_keys(self) -> list[tuple[int, int]]:
        """Coppie ordinate: prima la catena (1→2, 2→3…), poi le altre."""
        chain = [(i, i + 1) for i in range(self.n - 1)]
        others = [p for p in combinations(range(self.n), 2) if p not in chain]
        return chain + others

    def summary(self, pair: tuple[int, int]) -> dict[str, Any]:
        return summarize(self.pairs[pair])

    def any_field(self, fld: str) -> bool:
        return any(b.has(fld) for b in self.boms)


def compare_all(boms: list[BOMData], settings: CompareSettings) -> ComparisonResult:
    """Confronta tutte le distinte fornite (almeno 2) in ordine cronologico."""
    if len(boms) < 2:
        raise ValueError("Servono almeno due distinte per il confronto.")
    log.info("Confronto di %d distinte: %s", len(boms), [b.role for b in boms])
    pairs = {(i, j): compare_pair(boms[i], boms[j], settings)
             for i, j in combinations(range(len(boms)), 2)}
    aligned = _build_aligned(boms, pairs)
    return ComparisonResult(names=[b.role for b in boms], boms=boms, pairs=pairs,
                            aligned=aligned, settings=settings)


def _build_aligned(boms: list[BOMData], pairs: dict[tuple[int, int], pd.DataFrame]) -> pd.DataFrame:
    """Tabella allineata: una riga per codice, colonne ``<campo>_<i>`` per
    ogni distinta e ``status_<k>`` / ``delta_qty_<k>`` per ogni passo k-1→k.
    """
    n = len(boms)
    keys: list[str] = []
    seen: set[str] = set()
    for b in boms:
        for k in b.df["key"]:
            if k not in seen:
                seen.add(k)
                keys.append(k)
    al = pd.DataFrame({"key": keys})
    for i, b in enumerate(boms):
        part = b.df[["key"] + VALUE_FIELDS].copy()
        part.columns = ["key"] + [f"{f}_{i}" for f in VALUE_FIELDS]
        part[f"present_{i}"] = True
        al = al.merge(part, on="key", how="left")
        al[f"present_{i}"] = al[f"present_{i}"].eq(True)

    # Codice e descrizione di riferimento: la versione più recente disponibile.
    al["code"] = ""
    al["description"] = ""
    for i in range(n):
        has = al[f"present_{i}"]
        al.loc[has, "code"] = al.loc[has, f"code_{i}"]
        desc = al[f"description_{i}"].fillna("")
        al.loc[has & desc.ne(""), "description"] = desc[has & desc.ne("")]

    any_added = np.zeros(len(al), dtype=bool)
    any_removed = np.zeros(len(al), dtype=bool)
    any_modified = np.zeros(len(al), dtype=bool)
    any_tol = np.zeros(len(al), dtype=bool)
    cols = ["status", "delta_qty", "delta_pct", "changes", "out_of_tol", "impact",
            "chg_quantity", "chg_description", "chg_uom", "chg_revision",
            "chg_supplier", "chg_price", "chg_structure"]
    for k in range(1, n):
        p = pairs[(k - 1, k)].set_index("key")[cols]
        p.columns = [f"{c}_{k}" for c in cols]
        al = al.merge(p, left_on="key", right_index=True, how="left")
        st = al[f"status_{k}"].fillna("")
        al[f"status_{k}"] = st
        for c in cols[4:]:
            if c != "impact":
                al[f"{c}_{k}"] = al[f"{c}_{k}"].eq(True)
        al[f"changes_{k}"] = al[f"changes_{k}"].fillna("")
        any_added |= (st == ADDED).to_numpy()
        any_removed |= (st == REMOVED).to_numpy()
        any_modified |= (st == MODIFIED).to_numpy()
        any_tol |= al[f"out_of_tol_{k}"].to_numpy()

    al["any_added"] = any_added
    al["any_removed"] = any_removed
    al["any_modified"] = any_modified
    al["any_diff"] = any_added | any_removed | any_modified
    al["any_tol"] = any_tol
    al["order"] = _interleaved_order([b.df for b in boms], al["key"])
    al = al.sort_values("order", kind="mergesort").reset_index(drop=True)
    return al
