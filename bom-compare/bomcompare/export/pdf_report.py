"""Report PDF (facoltativo, richiede reportlab - funziona offline)."""
from __future__ import annotations

import logging

from ..core.comparator import ComparisonResult
from ..core.formatting import fmt_money, fmt_num, fmt_pct
from ..core.models import ADDED, MODIFIED, REMOVED, UNCHANGED, now_str

log = logging.getLogger(__name__)

try:  # reportlab è opzionale
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                    Table, TableStyle)
    PDF_AVAILABLE = True
except ImportError:  # pragma: no cover
    PDF_AVAILABLE = False

STATUS_BG = {ADDED: "#DCFCE7", REMOVED: "#FEE2E2", MODIFIED: "#DBEAFE", UNCHANGED: "#F3F4F6"}
STATUS_FG = {ADDED: "#166534", REMOVED: "#991B1B", MODIFIED: "#1E40AF", UNCHANGED: "#6B7280"}


def export_pdf(path: str, result: ComparisonResult, notes: dict[str, str],
               machine: str = "", include_unchanged: bool = False) -> None:
    if not PDF_AVAILABLE:
        raise RuntimeError("Esportazione PDF non disponibile: componente 'reportlab' mancante.")
    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=7, leading=8.5)
    title = styles["Title"]
    h2 = styles["Heading2"]

    doc = SimpleDocTemplate(path, pagesize=landscape(A4), leftMargin=10 * mm,
                            rightMargin=10 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
                            title="Report confronto distinte", author="BOM Compare")
    story = [Paragraph("Report confronto distinte base", title),
             Paragraph(f"Macchina: <b>{machine or '-'}</b> &nbsp;&nbsp; "
                       f"Generato il {now_str()} &nbsp;&nbsp; "
                       f"Tolleranza quantità ±{result.settings.tolerance_pct:g}%",
                       styles["Normal"]),
             Spacer(1, 6 * mm)]

    # Distinte
    data = [["#", "Ruolo", "File", "Codici"]]
    for i, b in enumerate(result.boms):
        data.append([str(i + 1), b.role, b.file_name, str(b.row_count)])
    story += [_table(data, [10 * mm, 70 * mm, 120 * mm, 25 * mm]), Spacer(1, 6 * mm)]

    # Statistiche
    data = [["Confronto", "Aggiunti", "Eliminati", "Modificati", "Invariati",
             "Cambi rev.", "Cambi forn.", "Fuori toll.", "Impatto €"]]
    for pair in result.pair_keys():
        s = result.summary(pair)
        data.append([result.pair_label(pair), s["added"], s["removed"], s["modified"],
                     s["unchanged"], s["revision_changes"], s["supplier_changes"],
                     s["out_of_tolerance"], fmt_money(s["impact"], signed=True)])
    t = _table(data, [90 * mm] + [21 * mm] * 7 + [30 * mm])
    extra = []
    for r in range(1, len(data)):
        for c, st in ((1, ADDED), (2, REMOVED), (3, MODIFIED), (4, UNCHANGED)):
            extra += [("BACKGROUND", (c, r), (c, r), colors.HexColor(STATUS_BG[st])),
                      ("TEXTCOLOR", (c, r), (c, r), colors.HexColor(STATUS_FG[st]))]
    t.setStyle(TableStyle(extra))
    story += [Paragraph("Riepilogo", h2), t]

    for pair in result.pair_keys():
        df = result.pairs[pair]
        if not include_unchanged:
            df = df[df["status"] != UNCHANGED]
        story += [PageBreak(), Paragraph(f"Dettaglio: {result.pair_label(pair)}", h2)]
        if df.empty:
            story.append(Paragraph("Nessuna differenza.", styles["Normal"]))
            continue
        rows = [["Stato", "Codice", "Descrizione", "Qtà A", "Qtà B", "Diff. Qtà", "Var. %",
                 "Modifiche", "Note"]]
        for r in df.itertuples(index=False):
            rows.append([r.status, r.code, Paragraph(_esc(r.description), small),
                         fmt_num(r.quantity_a), fmt_num(r.quantity_b),
                         fmt_num(r.delta_qty, signed=True) if r.status == MODIFIED else "",
                         fmt_pct(r.delta_pct) if r.status == MODIFIED else "",
                         Paragraph(_esc(r.changes), small),
                         Paragraph(_esc(notes.get(r.key, "")), small)])
        t = _table(rows, [20 * mm, 28 * mm, 70 * mm, 16 * mm, 16 * mm, 16 * mm, 16 * mm,
                          55 * mm, 40 * mm])
        style = []
        for k, r in enumerate(df.itertuples(index=False), start=1):
            style += [("BACKGROUND", (0, k), (-1, k), colors.HexColor(STATUS_BG[r.status])),
                      ("TEXTCOLOR", (0, k), (1, k), colors.HexColor(STATUS_FG[r.status]))]
            if r.out_of_tol:
                style.append(("BACKGROUND", (6, k), (6, k), colors.HexColor("#FDE68A")))
        t.setStyle(TableStyle(style))
        story.append(t)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    log.info("Report PDF salvato: %s", path)


def _esc(text: str) -> str:
    return (str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _table(data, widths):
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawString(10 * mm, 6 * mm, "BOM Compare - report generato offline")
    canvas.drawRightString(doc.pagesize[0] - 10 * mm, 6 * mm, f"Pagina {doc.page}")
    canvas.restoreState()
