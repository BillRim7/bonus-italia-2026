"""Formattazione numeri in stile italiano (1.234,56)."""
from __future__ import annotations

import math
from typing import Any


def _is_missing(v: Any) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def _it(s: str) -> str:
    """Converte '1,234.56' (formato inglese) in '1.234,56'."""
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_num(v: Any, decimals: int = 3, signed: bool = False) -> str:
    if _is_missing(v):
        return ""
    v = float(v)
    if abs(v - round(v)) < 1e-9:
        s = f"{v:+,.0f}" if signed else f"{v:,.0f}"
    else:
        s = f"{v:+,.{decimals}f}" if signed else f"{v:,.{decimals}f}"
        s = s.rstrip("0").rstrip(".")
    if signed and float(v) == 0:
        s = "0"
    return _it(s)


def fmt_pct(v: Any) -> str:
    if _is_missing(v):
        return ""
    if abs(v) < 0.05:
        return "0 %"
    return _it(f"{float(v):+,.1f}") + " %"


def fmt_money(v: Any, signed: bool = False) -> str:
    if _is_missing(v):
        return ""
    s = f"{float(v):+,.2f}" if signed else f"{float(v):,.2f}"
    return _it(s) + " €"


def fmt_level(v: Any) -> str:
    if _is_missing(v):
        return ""
    return str(int(v))
