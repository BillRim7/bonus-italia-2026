# BOM Compare – Confronto distinte base

Applicazione desktop **offline** per confrontare distinte base (BOM – *Bill of Materials*) di
versioni diverse della stessa macchina: **vecchia**, **in produzione** e **in progettazione/lancio**.

Pensata per reparto produzione, ufficio tecnico e acquisti: si trascinano i file Excel,
le differenze compaiono subito colorate e si esporta un report da condividere.

> 🔒 **Funziona senza internet.** Nessun dato esce dal computer: niente cloud, niente
> servizi esterni, niente aggiornamenti automatici. Icone e caratteri sono inclusi nel programma.

---

## Indice

1. [Funzionalità](#funzionalità)
2. [Installazione](#installazione)
3. [Guida all'uso](#guida-alluso)
4. [Formato dei file Excel/CSV](#formato-dei-file-excelcsv)
5. [Configurazione (config.json)](#configurazione-configjson)
6. [Creare l'eseguibile .exe](#creare-leseguibile-exe)
7. [Risoluzione problemi](#risoluzione-problemi)
8. [Struttura del codice](#struttura-del-codice)

---

## Funzionalità

| Area | Cosa fa |
|---|---|
| **Caricamento** | Excel `.xlsx` / `.xls` e CSV (`;` o `,`, decimali con virgola). Drag & drop o *Sfoglia…*. 3 distinte di base, fino a 6. |
| **Colonne** | Riconoscimento automatico di *Codice, Descrizione, Quantità, U.M., Revisione, Fornitore, Prezzo, Livello, Padre* – anche con righe di titolo sopra la tabella. Mappatura manuale con anteprima. |
| **Confronto** | Tutte le coppie (Vecchia→Produzione, Produzione→Progettazione, Vecchia→Progettazione). Δ quantità, Δ %, cambi di revisione, fornitore, U.M., prezzo. |
| **Multi-livello** | Gestione sotto-assiemi (colonna *Livello* e/o *Codice padre*), rilevamento dei componenti **spostati di livello/assieme**, somma automatica dei codici ripetuti. |
| **Visualizzazione** | Pannelli affiancati con **scroll sincronizzato** e righe allineate per codice; vista di dettaglio a coppie; riepilogo con statistiche. |
| **Strumenti** | Ricerca rapida, filtri (solo differenze / aggiunti / eliminati / modificati / fuori tolleranza), ordinamento per colonna, note editabili. |
| **Tolleranze** | Evidenzia in giallo le variazioni di quantità oltre la soglia impostata (es. ±10%). |
| **Costi** | Se c'è il prezzo: costo totale di ogni distinta e **impatto economico** delle modifiche. |
| **Export** | Report **Excel** colorato (riepilogo, vista allineata, un foglio per coppia, log), **PDF**, **testo per e-mail**. |
| **Progetti** | Salvataggio `.bomcompare` (contiene anche i dati: si riapre anche senza i file originali). |
| **Storico** | Database locale SQLite con tutte le versioni caricate e i confronti archiviati: si possono riconfrontare versioni storiche. |
| **Template** | Impostazioni predefinite per tipo di macchina (tolleranza, campi da confrontare, nomi colonne aziendali). |
| **Interfaccia** | Tutta in italiano, tema chiaro/scuro, tooltip, barra di avanzamento, guida al primo avvio, log delle operazioni con data e ora. |

### Codice colori

| Colore | Significato |
|---|---|
| 🟢 **Verde** | Componente **aggiunto** (presente solo nella versione più recente) |
| 🔴 **Rosso** | Componente **eliminato** (non più presente nella versione più recente) |
| 🔵 **Blu** | Componente **modificato** (stesso codice, dati diversi). Le celle cambiate sono in **grassetto** con blu più intenso |
| ⚪ **Grigio** | Componente **invariato** |
| 🟡 **Giallo** | Variazione di quantità **fuori tolleranza** |

---

## Installazione

### A) Utenti finali – eseguibile pronto

1. Copiare la cartella `BOMCompare` (prodotta da `build.bat`) sul PC, ad esempio in
   `C:\Programmi\BOMCompare` o sul desktop.
2. Avviare **`BOMCompare.exe`**. Non serve installare Python né altro.
3. Facoltativo: creare un collegamento sul desktop (tasto destro → *Invia a* → *Desktop*).

Compatibile con **Windows 10 e 11** (64 bit).

### B) Da sorgente (sviluppatori / IT)

Requisiti: **Python 3.10 o superiore** (da [python.org](https://www.python.org), spuntare
*“Add Python to PATH”*).

```bat
cd bom-compare
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

In seguito basta un doppio clic su **`avvia.bat`**.

### PC aziendali senza internet

1. Su un PC con internet eseguire **`scarica_dipendenze.bat`**: crea la cartella `wheels`
   con tutti i pacchetti.
2. Copiare l'intera cartella del progetto (inclusa `wheels`) sul PC isolato.
3. Eseguire `build.bat`: installerà i pacchetti dalla cartella `wheels`, senza connessione.

---

## Guida all'uso

Al primo avvio compare una **guida rapida** (sempre disponibile con **F1**). Dall'ultima
pagina, o dal menu *Aiuto → Carica dati di esempio*, si caricano tre distinte di prova.

### 1. Caricare le distinte

- In alto ci sono tre riquadri: **1 – Macchina VECCHIA**, **2 – Macchina in PRODUZIONE**,
  **3 – Macchina in PROGETTAZIONE**.
- **Trascinare** il file Excel/CSV dentro il riquadro, oppure premere **Sfoglia…**.
- Si possono trascinare **più file insieme** sulla finestra: vengono distribuiti nei riquadri
  vuoti in ordine alfabetico.
- Il nome del riquadro si modifica con un clic (es. “ABC-200 rev. 2023”).
- **Aggiungi distinta** (a destra) aggiunge altri riquadri, fino a 6 versioni.
- Il riquadro mostra numero di codici, foglio letto e colonne riconosciute; l'icona ⚠ indica
  eventuali avvisi (righe senza codice, quantità non numeriche, codici ripetuti sommati…).

### 2. Verificare le colonne (se necessario)

Il programma riconosce le colonne da solo. Se il risultato non convince premere
**Colonne…**: si possono scegliere il **foglio**, la **riga di intestazione** (anche
cliccando nell'anteprima) e quale colonna usare per ogni campo. È obbligatorio solo il
**Codice articolo**; senza quantità si assume 1 per riga.

### 3. Leggere il confronto

Il confronto parte **automaticamente** appena ci sono almeno due distinte (oppure **F5**).

- **Vista allineata** – un pannello per distinta, affiancati. Le righe sono allineate per
  codice articolo e lo scorrimento è sincronizzato. Ogni pannello è colorato rispetto alla
  distinta precedente; il primo mostra cosa succede nella distinta successiva
  (colonna *Stato →*). Le righe assenti mostrano *— non presente —* o *— eliminato —*.
  Colonne aggiuntive: **Δ Qtà**, **Δ %**, **Stato**, **Note**.
- **Confronto a coppie** – scegliere due distinte qualsiasi (anche Vecchia → Progettazione)
  per vedere tutti i dati affiancati (A/B), la colonna **Modifiche** in chiaro
  (es. *“Rev. A → B; Fornitore X → Y”*) e l'**impatto €**.
- **Riepilogo** – per ogni coppia: aggiunti, eliminati, modificati, invariati, cambi di
  revisione/fornitore/prezzo, spostamenti di struttura, fuori tolleranza, costi e impatto.
- **Log modifiche** – cronologia delle operazioni con data e ora (salvata nel progetto e
  nel report Excel).

### 4. Filtrare, cercare, ordinare, annotare

- **Cerca** (Ctrl+F): codice o parte della descrizione; più parole = tutte presenti.
- Filtri: **Tutti · Solo differenze · Aggiunti · Eliminati · Modificati · ⚠ Fuori tolleranza**.
- **Clic sull'intestazione** di una colonna per ordinare (crescente → decrescente → ordine
  originale). Nella vista allineata l'ordinamento si applica a tutti i pannelli.
- **Tasto destro sull'intestazione** per mostrare/nascondere colonne (U.M., Revisione,
  Fornitore, Prezzo…).
- **Doppio clic nella colonna Note** per annotare un componente (es. “verificare con
  acquisti”). Le note finiscono nei report e nel testo per e-mail.
- Passando il mouse su una cella si vede il dettaglio delle modifiche.

### 5. Tolleranza e template

- Nella barra in alto, **Tolleranza** imposta la soglia di variazione quantità (0 = disattivata).
- **Template** applica impostazioni pronte per tipo di macchina (tolleranza, campi da
  confrontare, nomi dei riquadri, nomi di colonna aziendali). Con
  *Confronto → Salva impostazioni come template…* si crea un template personale.
- *Confronto → Impostazioni…* permette di scegliere quali differenze contano come
  “modifica” (ad es. ignorare la descrizione) e altre opzioni.

### 6. Esportare e condividere

| Pulsante | Risultato |
|---|---|
| **Esporta Excel** (Ctrl+E) | Report `.xlsx`: *Riepilogo*, *Vista allineata*, un foglio per ogni coppia, *Log modifiche*. Colori, filtri automatici e intestazioni bloccate. |
| **Esporta PDF** (Ctrl+P) | Riepilogo + elenco differenze di ogni coppia, A4 orizzontale. |
| **Testo e-mail** (Ctrl+M) | Elenco modifiche già formattato: *Copia negli appunti*, *Salva .txt* o *Apri nel programma di posta*. |

### 7. Salvare il lavoro e usare lo storico

- **Salva** (Ctrl+S) crea un file **`.bomcompare`** con distinte, mappature, note e log.
  Si riapre con **Apri** (Ctrl+O) o trascinandolo sulla finestra.
- Ogni distinta caricata viene archiviata automaticamente nello **Storico** (Ctrl+H).
  Da lì si può ricaricare una versione storica in un qualsiasi riquadro (anche con il
  pulsante 🕘 del riquadro) e confrontarla con le versioni attuali.
- *Confronto → Salva confronto nello storico* archivia il confronto corrente; anche ogni
  export Excel viene archiviato.

### Scorciatoie da tastiera

| Tasto | Azione | Tasto | Azione |
|---|---|---|---|
| Ctrl+N | Nuovo confronto | F5 | Rifai il confronto |
| Ctrl+O | Apri progetto | Ctrl+F | Cerca |
| Ctrl+S | Salva progetto | Ctrl+T | Tema chiaro/scuro |
| Ctrl+E | Esporta Excel | Ctrl+H | Storico |
| Ctrl+P | Esporta PDF | F1 | Guida rapida |

---

## Formato dei file Excel/CSV

Basta una tabella con **una riga per componente** e una riga di intestazione. L'ordine
delle colonne non conta e possono esserci righe di titolo sopra la tabella.

### Esempio di file (dummy)

| Livello | Codice Articolo | Descrizione | Q.tà | U.M. | Rev. | Fornitore | Prezzo Unitario € |
|---|---|---|---|---|---|---|---|
| 0 | MAC-ABC200 | CONFEZIONATRICE ABC-200 | 1 | PZ | B | | |
| 1 | ASS-MOT-102 | GRUPPO MOTORIDUTTORE | 1 | PZ | A | Produzione interna | |
| 2 | MTR-2140 | Motore asincrono 1,5 kW IE3 | 1 | PZ | B | Siemens Italia | 310,00 |
| 2 | CUS-2440 | Cuscinetto 6205-2RS | 4 | PZ | A | NSK Italia Srl | 6,40 |
| 1 | ASS-QEL-103 | QUADRO ELETTRICO | 1 | PZ | A | Produzione interna | |
| 2 | MOR-3640 | Morsetto a molla 2,5 mm² | 96 | PZ | A | Elettro Bianchi SpA | 0,79 |
| 2 | CAV-3740 | Cavo multipolare 7x1 | 25 | M | A | Elettro Bianchi SpA | 2,30 |

### Nomi di colonna riconosciuti (esempi)

| Campo | Intestazioni riconosciute automaticamente |
|---|---|
| Codice articolo *(obbligatorio)* | Codice, Codice articolo, Cod. Art., Articolo, Part Number, P/N, Item, Materiale |
| Descrizione | Descrizione, Desc, Denominazione, Testo breve, Description |
| Quantità | Quantità, Q.tà, Qta, Qty, Pezzi, N. pezzi, Quantity |
| Unità di misura | U.M., UM, UdM, Unità di misura, UoM |
| Revisione | Revisione, Rev, Rev., Indice revisione |
| Fornitore | Fornitore, Supplier, Vendor, Produttore, Costruttore |
| Prezzo | Prezzo, Prezzo unitario, Costo, Costo unitario, Price, € |
| Livello | Livello, Liv., Level (valori `1, 2, 3` oppure stile SAP `.1`, `..2`) |
| Codice padre | Codice padre, Padre, Assieme padre, Parent |

Altri nomi si aggiungono in `config.json` (sezione `column_aliases`) o nei template.

**Regole di lettura**

- Numeri in formato italiano (`1.234,5`) o inglese (`1,234.5`); simboli come `€` ignorati.
- Codici numerici restano testo (`001` non diventa `1`); maiuscole/minuscole ignorate (configurabile).
- Righe senza codice (totali, righe vuote, note) vengono ignorate con un avviso.
- Lo stesso codice su più righe (es. viteria in più sotto-assiemi) viene **sommato**.
- Distinte multi-livello: se c'è solo il *Livello*, il *padre* viene dedotto dall'ordine delle righe.

### File di esempio inclusi (`sample_data/`)

| File | Contenuto |
|---|---|
| `distinta_1_vecchia.xlsx` | Confezionatrice ABC-200, versione obsoleta (101 righe) |
| `distinta_2_produzione.xlsx` | Versione in produzione (100 righe) |
| `distinta_3_progettazione.xlsx` | Nuova versione in lancio (102 righe) |
| `distinte_esempio.xlsx` | Le tre distinte in un unico file, su tre fogli |
| `distinta_2_produzione.csv` | La distinta di produzione in CSV italiano (`;` e virgola decimale) |

Le distinte contengono volutamente: componenti aggiunti/eliminati, variazioni di quantità
dentro e fuori tolleranza, cambi di revisione, fornitore, U.M. e prezzo, un componente
spostato in un altro assieme e un nuovo sotto-assieme a 3 livelli. Si rigenerano con
`python sample_data/genera_esempi.py`.

---

## Configurazione (config.json)

`config.json` si trova accanto a `BOMCompare.exe` e contiene le impostazioni **aziendali**
condivise; l'IT può modificarlo e distribuirlo con l'applicazione.

| Sezione | Descrizione |
|---|---|
| `comparison.tolerance_pct` | Tolleranza predefinita sulle quantità (%) |
| `comparison.compare_fields` | Quali campi generano lo stato “Modificato”: `quantity`, `description`, `uom`, `revision`, `supplier`, `price`, `structure` |
| `comparison.ignore_description_case` / `ignore_whitespace` | Confronto descrizioni tollerante |
| `comparison.code_case_insensitive` | `abc-1` e `ABC-1` sono lo stesso codice |
| `comparison.aggregate_duplicates` | Somma le quantità dei codici ripetuti |
| `default_roles` | Nomi predefiniti dei riquadri |
| `max_boms` | Numero massimo di distinte confrontabili |
| `column_aliases` | Nomi di colonna riconosciuti per ogni campo |
| `history` | Storico attivo, salvataggio automatico, numero massimo di versioni |
| `ui` | Tema predefinito, altezza righe, righe di anteprima |
| `templates` | Template per tipo di macchina (`tolerance_pct`, `compare_fields`, `roles`, `extra_aliases`) |

Le **preferenze personali** (tema, template scelto, file recenti, template utente) e i dati
locali sono salvati in:

| Cosa | Percorso |
|---|---|
| Preferenze utente | `%APPDATA%\BOMCompare\user_settings.json` |
| Storico (SQLite) | `%APPDATA%\BOMCompare\storico.sqlite` |
| Log di diagnostica | `%APPDATA%\BOMCompare\logs\bomcompare.log` (menu *Aiuto → Apri cartella log*) |

---

## Creare l'eseguibile .exe

Su un PC Windows con Python 3.10+:

```bat
build.bat            :: crea dist\BOMCompare\BOMCompare.exe  (consigliato: avvio rapido)
build.bat onefile    :: crea un unico file dist\BOMCompare.exe (più lento ad aprirsi)
```

Lo script crea un ambiente virtuale `.venv`, installa le dipendenze (dalla cartella
`wheels` se presente), **esegue i test** e lancia PyInstaller con `bomcompare.spec`.
Al termine copia accanto all'eseguibile `config.json`, i file di esempio e questo README.
Per distribuire l'app basta copiare la cartella `dist\BOMCompare`.

---

## Risoluzione problemi

| Problema | Soluzione |
|---|---|
| *“Il file è in uso da un altro programma”* | Chiudere il file in Excel e riprovare. |
| *“Non è stato possibile riconoscere la colonna del Codice”* | Nella finestra che si apre indicare la riga di intestazione e la colonna del codice. Per evitarlo in futuro aggiungere il nome della colonna in `config.json` o salvare un template. |
| Molte righe “aggiunte” ed “eliminate” con codici simili | I codici sono diversi per spazi o zeri iniziali (`0123` vs `123`). Verificare l'origine dei dati. |
| Quantità tutte a 0 | La colonna quantità scelta non è numerica: controllare con *Colonne…*. |
| File `.xls` non leggibile | Aprirlo in Excel e salvarlo come `.xlsx`. |
| File protetto da password | Rimuovere la protezione in Excel. |
| Windows SmartScreen blocca l'avvio | *Ulteriori informazioni → Esegui comunque* (l'eseguibile non è firmato digitalmente; l'IT può firmarlo). |
| Errore imprevisto | Il messaggio mostra i dettagli; inviare al supporto il file di log (*Aiuto → Apri cartella log*). |

---

## Struttura del codice

```
bom-compare/
├── main.py                    # avvio, logging, gestione errori globale
├── config.json                # configurazione aziendale
├── requirements.txt           # dipendenze runtime
├── requirements-dev.txt       # + PyInstaller e pytest
├── build.bat                  # creazione eseguibile Windows
├── avvia.bat                  # avvio da sorgente
├── scarica_dipendenze.bat     # pacchetti per installazione offline
├── bomcompare.spec            # configurazione PyInstaller
├── assets/app.ico             # icona applicazione
├── sample_data/               # distinte di esempio + generatore
├── tests/test_core.py         # test automatici (python -m pytest)
└── bomcompare/
    ├── core/                  # LOGICA (nessuna dipendenza dall'interfaccia)
    │   ├── config.py          #   config.json + preferenze utente + percorsi
    │   ├── logger.py          #   log su file con rotazione
    │   ├── models.py          #   campi, stati, classe BOMData
    │   ├── loader.py          #   lettura Excel/CSV, rilevamento colonne, normalizzazione
    │   ├── comparator.py      #   motore di confronto (pandas, vettorizzato)
    │   ├── formatting.py      #   numeri in formato italiano
    │   ├── project.py         #   file .bomcompare
    │   └── history.py         #   storico SQLite
    ├── export/                # REPORT
    │   ├── excel_report.py    #   report Excel colorato (openpyxl)
    │   ├── pdf_report.py      #   report PDF (reportlab)
    │   └── email_text.py      #   testo per e-mail
    └── ui/                    # INTERFACCIA (PyQt6)
        ├── main_window.py     #   finestra principale, azioni, menu
        ├── views.py           #   vista allineata, a coppie, riepilogo, log
        ├── table_models.py    #   modelli tabellari virtuali (migliaia di righe)
        ├── widgets.py         #   riquadri drag & drop, card, barra filtri
        ├── dialogs.py         #   mappatura colonne, storico, impostazioni, e-mail, guida
        ├── workers.py         #   caricamento file in background
        ├── theme.py           #   temi chiaro/scuro
        └── icons.py           #   icone FontAwesome (qtawesome)
```

**Prestazioni.** Il confronto è vettorizzato con pandas e le tabelle sono “virtuali”
(vengono disegnate solo le righe visibili): distinte da 5.000 righe si confrontano in
meno di un secondo. I file vengono letti in un thread separato con barra di avanzamento,
così l'interfaccia non si blocca.

**Test.** `python -m pytest` esegue i test su lettura file, rilevamento colonne,
confronto, multi-livello, tolleranze, impatto economico, progetti, storico ed export.
