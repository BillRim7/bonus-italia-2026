"""Testo preformattato dei cambiamenti, pronto da incollare in una e-mail."""
from __future__ import annotations

import pandas as pd

from ..core.comparator import ComparisonResult
from ..core.formatting import fmt_money, fmt_num, fmt_pct
from ..core.models import ADDED, MODIFIED, REMOVED, now_str


def _line(code: str, desc: str, width_code: int = 16, width_desc: int = 42) -> str:
    desc = desc if len(desc) <= width_desc else desc[: width_desc - 1] + "…"
    return f"{code:<{width_code}} {desc:<{width_desc}}"


def build_email_text(result: ComparisonResult, pair: tuple[int, int], machine: str = "",
                     notes: dict[str, str] | None = None, only_tol: bool = False) -> str:
    notes = notes or {}
    i, j = pair
    df: pd.DataFrame = result.pairs[pair]
    s = result.summary(pair)
    a, b = result.names[i], result.names[j]
    out: list[str] = []
    out.append(f"Oggetto: Modifiche distinta base{(' ' + machine) if machine else ''}"
               f" - {a} → {b}")
    out.append("")
    out.append("Buongiorno,")
    out.append(f"di seguito le differenze tra la distinta \"{a}\" e la distinta \"{b}\"")
    out.append(f"(confronto generato il {now_str()} con BOM Compare).")
    out.append("")
    out.append("RIEPILOGO")
    out.append("-" * 60)
    out.append(f"  Componenti aggiunti ......... {s['added']}")
    out.append(f"  Componenti eliminati ........ {s['removed']}")
    out.append(f"  Componenti modificati ....... {s['modified']}")
    out.append(f"  Cambi di revisione .......... {s['revision_changes']}")
    out.append(f"  Cambi di fornitore .......... {s['supplier_changes']}")
    out.append(f"  Fuori tolleranza (±{result.settings.tolerance_pct:g}%) ... "
               f"{s['out_of_tolerance']}")
    if s["impact"] is not None:
        out.append(f"  Impatto economico ........... {fmt_money(s['impact'], signed=True)}")
    out.append("")

    def note_of(key: str) -> str:
        n = notes.get(key, "").strip()
        return f"\n      Nota: {n}" if n else ""

    sections = [(ADDED, "COMPONENTI AGGIUNTI", "+"), (REMOVED, "COMPONENTI ELIMINATI", "-"),
                (MODIFIED, "COMPONENTI MODIFICATI", "*")]
    for status, title, sign in sections:
        part = df[df["status"] == status]
        if only_tol and status == MODIFIED:
            part = part[part["out_of_tol"] | ~part["changes"].str.match(r"^Qtà [^;]*$")]
        if part.empty:
            continue
        out.append(f"{title} ({len(part)})")
        out.append("-" * 60)
        for r in part.itertuples(index=False):
            head = f"  {sign} " + _line(r.code, r.description)
            if status == ADDED:
                out.append(f"{head}  Qtà {fmt_num(r.quantity_b)} {r.uom_b or ''}".rstrip()
                           + note_of(r.key))
            elif status == REMOVED:
                out.append(f"{head}  Qtà {fmt_num(r.quantity_a)} {r.uom_a or ''}".rstrip()
                           + note_of(r.key))
            else:
                details = []
                if r.chg_quantity:
                    details.append(f"Qtà {fmt_num(r.quantity_a)} → {fmt_num(r.quantity_b)} "
                                   f"({fmt_num(r.delta_qty, signed=True)}; {fmt_pct(r.delta_pct)})"
                                   + (" ⚠ FUORI TOLLERANZA" if r.out_of_tol else ""))
                for part_txt in str(r.changes).split("; "):
                    if not part_txt or part_txt.startswith("Qtà "):
                        continue
                    if part_txt == "Descrizione modificata":
                        part_txt = f'Descrizione: "{r.description_a}" → "{r.description_b}"'
                    details.append(part_txt)
                out.append(head.rstrip())
                for d in details:
                    out.append(f"      {d}")
                if note_of(r.key):
                    out.append(note_of(r.key).lstrip("\n"))
        out.append("")
    if s["added"] + s["removed"] + s["modified"] == 0:
        out.append("Nessuna differenza rilevata tra le due distinte.")
        out.append("")
    out.append("Cordiali saluti")
    return "\n".join(out)
