"""Genera i file Excel/CSV di esempio con 3 distinte fittizie.

Uso:  python sample_data/genera_esempi.py

Crea nella cartella ``sample_data``:
  * distinta_1_vecchia.xlsx
  * distinta_2_produzione.xlsx
  * distinta_3_progettazione.xlsx
  * distinte_esempio.xlsx        (le 3 distinte su 3 fogli)
  * distinta_2_produzione.csv    (stessa distinta in formato CSV italiano)
"""
from __future__ import annotations

import copy
import csv
import random
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

OUT = Path(__file__).resolve().parent
HEADERS = ["Livello", "Codice Articolo", "Descrizione", "Q.tà", "U.M.", "Rev.",
           "Fornitore", "Prezzo Unitario €"]
SUPPLIERS = ["Meccanica Rossi Srl", "Elettro Bianchi SpA", "Pneumax Italia",
             "Bulloneria Verdi", "Siemens Italia", "Festo Spa", "Lamiere Brambilla",
             "Plastiche Lombarde", "SKF Italia", "Omron Electronics"]

# (livello, codice, descrizione, qta, um, fornitore, prezzo)
ASSEMBLIES = [
    ("TEL", "TELAIO PRINCIPALE SALDATO", [
        ("LAM", "Lamiera piegata sp. 3 mm", "PZ", 6, 8, 45.0),
        ("PRF", "Profilato alluminio 45x45", "M", 4, 12, 18.5),
        ("PIE", "Piedino regolabile M16", "PZ", 4, 6, 7.9),
        ("VIT", "Vite TCEI M8x25 inox", "PZ", 3, 60, 0.18),
        ("DAD", "Dado autobloccante M8", "PZ", 3, 60, 0.07),
    ]),
    ("MOT", "GRUPPO MOTORIDUTTORE", [
        ("MTR", "Motore asincrono 1,5 kW", "PZ", 4, 1, 310.0),
        ("RID", "Riduttore a vite senza fine i=30", "PZ", 1, 1, 240.0),
        ("GIU", "Giunto elastico D28", "PZ", 4, 2, 32.0),
        ("CUS", "Cuscinetto 6205-2RS", "PZ", 8, 4, 6.4),
        ("ALB", "Albero trasmissione D25", "PZ", 0, 1, 58.0),
        ("CHI", "Chiavetta 8x7x30", "PZ", 3, 3, 0.9),
    ]),
    ("QEL", "QUADRO ELETTRICO", [
        ("PLC", "PLC compatto 24 I/O", "PZ", 4, 1, 520.0),
        ("INV", "Inverter 2,2 kW", "PZ", 4, 1, 385.0),
        ("ALI", "Alimentatore 24 Vdc 10 A", "PZ", 9, 1, 96.0),
        ("MAG", "Interruttore magnetotermico 16 A", "PZ", 1, 4, 22.5),
        ("REL", "Relè di sicurezza", "PZ", 9, 1, 140.0),
        ("MOR", "Morsetto a molla 2,5 mm²", "PZ", 1, 80, 0.85),
        ("CAV", "Cavo multipolare 7x1", "M", 1, 25, 2.3),
        ("PUL", "Pulsante emergenza a fungo", "PZ", 9, 2, 28.0),
    ]),
    ("PNE", "GRUPPO PNEUMATICO", [
        ("CIL", "Cilindro ISO 15552 D50 c.100", "PZ", 5, 2, 88.0),
        ("ELV", "Elettrovalvola 5/2 monostabile", "PZ", 5, 4, 54.0),
        ("FRL", "Gruppo FRL 1/2\"", "PZ", 2, 1, 120.0),
        ("TUB", "Tubo poliuretano D8", "M", 5, 15, 1.2),
        ("RAC", "Raccordo istantaneo D8 1/4\"", "PZ", 2, 16, 2.1),
    ]),
    ("NAS", "NASTRO TRASPORTATORE", [
        ("TAP", "Tappeto PVC alimentare L=3000", "PZ", 7, 1, 260.0),
        ("RUL", "Rullo motorizzato D50", "PZ", 0, 2, 145.0),
        ("RFO", "Rullo folle D50", "PZ", 0, 6, 38.0),
        ("SPO", "Sponda laterale inox", "PZ", 6, 2, 64.0),
        ("FOT", "Fotocellula a riflessione", "PZ", 9, 2, 75.0),
    ]),
    ("PRO", "PROTEZIONI E CARTER", [
        ("PAN", "Pannello policarbonato 1000x800", "PZ", 7, 4, 82.0),
        ("CER", "Cerniera in zama", "PZ", 0, 8, 6.5),
        ("MIC", "Microinterruttore di sicurezza", "PZ", 9, 2, 46.0),
        ("MAN", "Maniglia a ponte", "PZ", 7, 4, 4.8),
    ]),
]


def base_bom() -> list[dict]:
    rows = [dict(level=0, code="MAC-ABC200", desc="CONFEZIONATRICE ABC-200",
                 qty=1, um="PZ", rev="A", sup="", price=None)]
    for a_idx, (prefix, desc, comps) in enumerate(ASSEMBLIES, start=1):
        rows.append(dict(level=1, code=f"ASS-{prefix}-{100 + a_idx}", desc=desc,
                         qty=1, um="PZ", rev="A", sup="Produzione interna", price=None))
        for c_idx, (cp, cdesc, um, sup_idx, qty, price) in enumerate(comps, start=1):
            rows.append(dict(level=2, code=f"{cp}-{a_idx}{c_idx}40",
                             desc=cdesc, qty=qty, um=um, rev="A",
                             sup=SUPPLIERS[sup_idx], price=price))
    # Minuteria comune per rendere la distinta più "realistica" (righe extra)
    rng = random.Random(7)
    rows.append(dict(level=1, code="ASS-MIN-900", desc="KIT MINUTERIA E CONSUMABILI",
                     qty=1, um="PZ", rev="A", sup="Produzione interna", price=None))
    for i in range(1, 61):
        d = rng.choice(["Rondella piana", "Vite TE", "Grano M6", "Fascetta",
                        "Etichetta", "Guaina", "Spina cilindrica", "Distanziale"])
        rows.append(dict(level=2, code=f"MIN-{5000 + i}", desc=f"{d} tipo {i}",
                         qty=rng.choice([2, 4, 6, 8, 10, 12]), um="PZ", rev="A",
                         sup=SUPPLIERS[3], price=round(rng.uniform(0.05, 2.5), 2)))
    return rows


def find(rows, code):
    for r in rows:
        if r["code"] == code:
            return r
    raise KeyError(code)


def make_versions() -> tuple[list[dict], list[dict], list[dict]]:
    old = base_bom()

    # ---- Produzione: evoluzione della vecchia ----------------------------- #
    prod = copy.deepcopy(old)
    find(prod, "MAC-ABC200")["rev"] = "B"
    find(prod, "MTR-2140")["rev"] = "B"                     # cambio revisione
    find(prod, "MTR-2140")["desc"] = "Motore asincrono 1,5 kW IE3"
    find(prod, "VIT-1440")["qty"] = 72                       # +20%
    find(prod, "CUS-2440")["sup"] = "NSK Italia Srl"             # cambio fornitore
    find(prod, "MOR-3640")["qty"] = 96
    find(prod, "MOR-3640")["price"] = 0.79                   # prezzo
    prod = [r for r in prod if r["code"] not in ("CHI-2640", "MIN-5007", "MIN-5021")]
    idx = prod.index(find(prod, "PUL-3840")) + 1
    prod.insert(idx, dict(level=2, code="SEL-3940", desc="Selettore a chiave 2 posizioni",
                          qty=1, um="PZ", rev="A", sup=SUPPLIERS[9], price=31.0))
    idx = prod.index(find(prod, "RAC-4540")) + 1
    prod.insert(idx, dict(level=2, code="SIL-4640", desc="Silenziatore sinterizzato 1/4\"",
                          qty=4, um="PZ", rev="A", sup=SUPPLIERS[5], price=3.2))

    # ---- Progettazione: nuova versione ------------------------------------ #
    new = copy.deepcopy(prod)
    find(new, "MAC-ABC200")["rev"] = "C"
    find(new, "PLC-3140")["desc"] = "PLC compatto 32 I/O con Ethernet"
    find(new, "PLC-3140")["rev"] = "C"
    find(new, "PLC-3140")["price"] = 610.0
    find(new, "INV-3240")["sup"] = SUPPLIERS[1]
    find(new, "TUB-4440")["qty"] = 9                         # -40% (fuori toll.)
    find(new, "LAM-1140")["qty"] = 8                         # +33%
    find(new, "CAV-3740")["um"] = "MT"                       # cambio U.M.
    # Fotocellula spostata dal nastro alle protezioni (cambio struttura)
    fot = find(new, "FOT-5540")
    new.remove(fot)
    idx = new.index(find(new, "MIC-6340")) + 1
    new.insert(idx, fot)
    # Componenti eliminati e nuovo sotto-assieme a 3 livelli
    new = [r for r in new if r["code"] not in ("RFO-5340", "ELV-4240", "MIN-5033")]
    idx = new.index(find(new, "FRL-4340"))
    new[idx:idx] = [
        dict(level=2, code="ASS-ISL-4050", desc="ISOLA VALVOLE 8 POSTI", qty=1, um="PZ",
             rev="A", sup="Produzione interna", price=None),
        dict(level=3, code="ISL-4051", desc="Isola valvole base 8 posti", qty=1, um="PZ",
             rev="A", sup=SUPPLIERS[5], price=420.0),
        dict(level=3, code="ISL-4052", desc="Modulo valvola 5/2", qty=6, um="PZ",
             rev="A", sup=SUPPLIERS[5], price=61.0),
        dict(level=3, code="ISL-4053", desc="Cavo connessione M12 5 m", qty=1, um="PZ",
             rev="A", sup=SUPPLIERS[5], price=24.0),
    ]
    idx = new.index(find(new, "MAN-6440")) + 1
    new.insert(idx, dict(level=2, code="LED-6550", desc="Barra LED illuminazione 24 V",
                         qty=2, um="PZ", rev="A", sup=SUPPLIERS[9], price=58.0))
    for r in new:
        if r["code"].startswith("MIN-") and int(r["code"][4:]) % 9 == 0:
            r["qty"] += 2
    return old, prod, new


TITLE_FILL = PatternFill("solid", start_color="1F3864")
HEAD_FILL = PatternFill("solid", start_color="D9E2F3")


def write_sheet(ws, rows: list[dict], title: str) -> None:
    ws["A1"] = title
    ws["A1"].font = Font(bold=True, size=14, color="FFFFFF")
    ws["A1"].fill = TITLE_FILL
    ws.merge_cells("A1:H1")
    ws["A2"] = "Distinta base fittizia generata per test - dati non reali"
    ws["A2"].font = Font(italic=True, color="666666")
    for col, h in enumerate(HEADERS, start=1):
        c = ws.cell(row=4, column=col, value=h)
        c.font = Font(bold=True)
        c.fill = HEAD_FILL
        c.alignment = Alignment(horizontal="center")
    for r_idx, r in enumerate(rows, start=5):
        values = [r["level"], r["code"], ("    " * r["level"]) + r["desc"], r["qty"],
                  r["um"], r["rev"], r["sup"], r["price"]]
        for col, v in enumerate(values, start=1):
            ws.cell(row=r_idx, column=col, value=v)
        if r["level"] <= 1:
            for col in range(1, 9):
                ws.cell(row=r_idx, column=col).font = Font(bold=True)
    for col, width in enumerate([8, 18, 46, 8, 7, 6, 26, 18], start=1):
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.freeze_panes = "A5"


def main() -> None:
    old, prod, new = make_versions()
    versions = [
        ("distinta_1_vecchia.xlsx", "Vecchia", old, "ABC-200 - versione 2022 (obsoleta)"),
        ("distinta_2_produzione.xlsx", "Produzione", prod, "ABC-200 - versione in produzione"),
        ("distinta_3_progettazione.xlsx", "Progettazione", new, "ABC-200 - nuova versione (lancio)"),
    ]
    combined = Workbook()
    combined.remove(combined.active)
    for fname, sheet, rows, title in versions:
        wb = Workbook()
        write_sheet(wb.active, rows, title)
        wb.active.title = "Distinta"
        wb.save(OUT / fname)
        write_sheet(combined.create_sheet(sheet), rows, title)
        print(f"Creato {fname} ({len(rows)} righe)")
    combined.save(OUT / "distinte_esempio.xlsx")
    print("Creato distinte_esempio.xlsx (3 fogli)")

    # CSV in formato italiano: separatore ';' e virgola decimale
    with open(OUT / "distinta_2_produzione.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(HEADERS)
        for r in prod:
            price = "" if r["price"] is None else f"{r['price']:.2f}".replace(".", ",")
            w.writerow([r["level"], r["code"], r["desc"], r["qty"], r["um"], r["rev"],
                        r["sup"], price])
    print("Creato distinta_2_produzione.csv")


if __name__ == "__main__":
    main()
