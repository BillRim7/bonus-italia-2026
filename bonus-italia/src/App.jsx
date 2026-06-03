import { useState, useMemo } from "react";

const categories = [
  { id: "all", label: "Tutti", emoji: "🇮🇹" },
  { id: "famiglia", label: "Famiglia", emoji: "👨‍👩‍👧" },
  { id: "anziani", label: "Anziani", emoji: "👴" },
  { id: "disabili", label: "Disabilità", emoji: "♿" },
  { id: "studenti", label: "Studenti", emoji: "🎓" },
  { id: "casa", label: "Casa", emoji: "🏠" },
  { id: "mobilita", label: "Mobilità", emoji: "🚗" },
  { id: "lavoro", label: "Lavoro", emoji: "💼" },
  { id: "bollette", label: "Bollette", emoji: "⚡" },
  { id: "salute", label: "Salute", emoji: "🏥" },
];

const iseeColors = {
  "Senza ISEE": "#6366f1",
  "ISEE < 6.000€": "#ef4444",
  "ISEE < 8.000€": "#ef4444",
  "ISEE < 10.974€": "#f97316",
  "ISEE < 13.000€": "#f97316",
  "ISEE < 15.000€": "#eab308",
  "ISEE < 20.000€": "#eab308",
  "ISEE < 22.000€": "#84cc16",
  "ISEE < 25.000€": "#84cc16",
  "ISEE < 30.000€": "#22c55e",
  "ISEE < 35.000€": "#22c55e",
  "ISEE < 40.000€": "#10b981",
  "Qualsiasi ISEE": "#14b8a6",
};

const bonuses = [
  // FAMIGLIA
  {
    id: 1,
    categoria: "famiglia",
    nome: "Assegno Unico e Universale (AUU)",
    importo: "Fino a ~200€/mese per figlio",
    isee: "Qualsiasi ISEE",
    descrizione: "Contributo mensile per ogni figlio a carico fino a 21 anni (senza limiti di età se disabile). L'importo massimo spetta con ISEE < 15.000€, quello minimo (~57€) senza ISEE.",
    come: "Domanda online INPS o tramite CAF/patronato",
    scadenza: "Permanente (rinnovo annuale con nuovo ISEE)",
    tipo: "stabile",
    link: "https://www.inps.it/it/it/dettaglio-scheda.it.schede-servizio-strumento.schede-servizi.assegno-unico-e-universale-per-i-figli-a-carico.html",
    novita: false,
  },
  {
    id: 2,
    categoria: "famiglia",
    nome: "Bonus Asilo Nido",
    importo: "Da 1.500€ a 3.600€/anno",
    isee: "ISEE < 40.000€",
    descrizione: "Rimborso per rette di asili nido pubblici e privati. Con ISEE < 25.000€: 3.600€; < 40.000€: 3.000€; oltre: 1.500€. Maggiorazione per 2° figlio sotto i 10 anni.",
    come: "Domanda INPS entro il 31/12 dell'anno di frequenza",
    scadenza: "Permanente (domanda annuale)",
    tipo: "stabile",
    link: "https://www.inps.it",
    novita: false,
  },
  {
    id: 3,
    categoria: "famiglia",
    nome: "Bonus Mamme Lavoratrici",
    importo: "Esonero contributivo fino a 3.000€/anno",
    isee: "Qualsiasi ISEE",
    descrizione: "Sgravio dei contributi previdenziali per lavoratrici dipendenti (pubbliche e private) con almeno 2 figli. Quota più alta per 3+ figli. Si applica sul cedolino automaticamente.",
    come: "Automatico tramite datore di lavoro",
    scadenza: "Confermato 2026",
    tipo: "stabile",
    link: "https://www.inps.it",
    novita: false,
  },
  {
    id: 4,
    categoria: "famiglia",
    nome: "Carta \"Dedicata a Te\"",
    importo: "500€ una tantum",
    isee: "ISEE < 15.000€",
    descrizione: "Carta prepagata per acquistare generi alimentari di prima necessità, carburante, abbonamenti trasporti pubblici e alcuni elettrodomestici ad alta efficienza. Erogazione automatica tramite INPS/Comuni.",
    come: "Erogazione automatica, ritiro in Posta",
    scadenza: "Bando annuale (verifica aggiornamenti 2026)",
    tipo: "bando",
    link: "https://www.inps.it",
    novita: false,
  },
  {
    id: 5,
    categoria: "famiglia",
    nome: "Assegno di Inclusione (ADI)",
    importo: "Fino a ~750€/mese",
    isee: "ISEE < 9.360€",
    descrizione: "Sostituisce il Reddito di Cittadinanza. Per nuclei familiari con disabili, minori, over 60 o persone in svantaggio certificato. Richiede percorso di inclusione sociale/lavorativa.",
    come: "Domanda INPS, poi patto di inclusione al Centro per l'Impiego",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.inps.it",
    novita: false,
  },
  {
    id: 6,
    categoria: "famiglia",
    nome: "Centri Estivi (Fondo Comuni)",
    importo: "Fondo 60M€/anno",
    isee: "Qualsiasi ISEE",
    descrizione: "Nuovo fondo permanente istituito dalla Legge di Bilancio 2026 destinato ai Comuni per potenziare centri estivi, servizi socioeducativi e strutture ricreative.",
    come: "Tramite Comune di residenza",
    scadenza: "Permanente dal 2026",
    tipo: "nuovo",
    link: "https://www.governo.it",
    novita: true,
  },

  // ANZIANI
  {
    id: 7,
    categoria: "anziani",
    nome: "Assegno Universale Anziani",
    importo: "Fino a 850€/mese",
    isee: "ISEE < 6.000€",
    descrizione: "Misura sperimentale per ultraottantenni non autosufficienti con bisogno assistenziale gravissimo. Comprende l'indennità di accompagnamento (542€) + quota aggiuntiva per assistenti familiari.",
    come: "Domanda INPS con valutazione multi-dimensionale",
    scadenza: "Sperimentale fino al 31/12/2026",
    tipo: "bando",
    link: "https://www.inps.it",
    novita: true,
  },
  {
    id: 8,
    categoria: "anziani",
    nome: "Carta Acquisti (over 65)",
    importo: "480€/anno (80€ ogni 2 mesi)",
    isee: "ISEE < 8.000€",
    descrizione: "Carta prepagata per spese alimentari, farmaci e bollette luce/gas. Soglia ISEE: < 8.052,75€ dai 65 anni; < 10.974,42€ dai 70 anni in su.",
    come: "Domanda agli sportelli Poste Italiane con ISEE",
    scadenza: "Permanente (rinnovo ISEE annuale)",
    tipo: "stabile",
    link: "https://www.postepay.it",
    novita: false,
  },
  {
    id: 9,
    categoria: "anziani",
    nome: "Assegno Sociale INPS (over 67)",
    importo: "~548€/mese (13 mensilità)",
    isee: "Reddito molto basso",
    descrizione: "Per chi ha compiuto 67 anni e si trova in difficoltà economica, senza una pensione sufficiente. Importo rivalutato nel 2026.",
    come: "Domanda INPS",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.inps.it",
    novita: false,
  },
  {
    id: 10,
    categoria: "anziani",
    nome: "Esenzione Canone RAI (over 75)",
    importo: "90€/anno",
    isee: "Reddito familiare < 8.000€",
    descrizione: "Esenzione totale dal canone RAI per chi ha superato i 75 anni con reddito del nucleo familiare (richiedente + coniuge) inferiore a 8.000€.",
    come: "Domanda all'Agenzia delle Entrate",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.agenziaentrate.gov.it",
    novita: false,
  },
  {
    id: 11,
    categoria: "anziani",
    nome: "Esenzione Ticket Sanitario (over 65)",
    importo: "Esenzione totale ticket",
    isee: "Reddito < 36.151,98€",
    descrizione: "Esenzione dal ticket per visite specialistiche ed esami diagnostici per chi ha almeno 65 anni e appartiene a nucleo con reddito complessivo < 36.151,98€. Codice esenzione E01.",
    come: "Richiesta al medico di base o ASL con documenti reddituali",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.salute.gov.it",
    novita: false,
  },
  {
    id: 12,
    categoria: "anziani",
    nome: "Bonus Bollette Anziani (clienti vulnerabili)",
    importo: "Varia (sconto automatico)",
    isee: "ISEE < 9.530€ o over 75",
    descrizione: "Gli over 75 rientrano automaticamente tra i 'clienti vulnerabili' con diritto a bonus bollette su luce e gas, indipendentemente dall'ISEE.",
    come: "Automatico se ISEE aggiornato o over 75",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.arera.it",
    novita: false,
  },

  // DISABILI
  {
    id: 13,
    categoria: "disabili",
    nome: "Indennità di Accompagnamento",
    importo: "542,02€/mese",
    isee: "Qualsiasi ISEE",
    descrizione: "Per persone non autosufficienti che necessitano di assistenza continua. Non dipende dall'ISEE né dall'età.",
    come: "Richiesta all'INPS tramite medico di base (visita commissione medica)",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.inps.it",
    novita: false,
  },
  {
    id: 14,
    categoria: "disabili",
    nome: "Pensione di Invalidità (100%)",
    importo: "~336€/mese (fino a 747€ con maggiorazione)",
    isee: "ISEE < soglie specifiche",
    descrizione: "Per invalidi civili al 100%. Importo base ~336€ mensili con possibilità di maggiorazione fino a 747€ per chi rispetta specifiche soglie di reddito.",
    come: "Richiesta all'INPS con verbale di invalidità",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.inps.it",
    novita: false,
  },
  {
    id: 15,
    categoria: "disabili",
    nome: "Assegno Mensile Invalidità (74-99%)",
    importo: "~336€/mese",
    isee: "Qualsiasi ISEE",
    descrizione: "Per chi ha un'invalidità civile riconosciuta tra il 74% e il 99%.",
    come: "Richiesta all'INPS con verbale di invalidità",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.inps.it",
    novita: false,
  },
  {
    id: 16,
    categoria: "disabili",
    nome: "Agevolazioni Auto Disabili",
    importo: "IVA 4% + detrazione 19% + bollo gratuito",
    isee: "Qualsiasi ISEE",
    descrizione: "IVA agevolata al 4% sull'acquisto dell'auto, detrazione IRPEF del 19% fino a 18.075,99€, esenzione bollo auto e imposta di trascrizione. Valido per veicolo usato prevalentemente dal disabile.",
    come: "Fattura con riferimenti di legge; dichiarazione dei redditi per detrazione",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.agenziaentrate.gov.it",
    novita: false,
  },
  {
    id: 17,
    categoria: "disabili",
    nome: "Permessi Legge 104 (lavoratori)",
    importo: "3 giorni/mese retribuiti",
    isee: "Qualsiasi ISEE",
    descrizione: "3 giorni di permesso mensile retribuiti per il lavoratore disabile (art. 3 c. 3 L.104) o per il familiare che assiste una persona con disabilità grave. Anche frazionabili in ore.",
    come: "Domanda INPS tramite datore di lavoro",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.inps.it",
    novita: false,
  },
  {
    id: 18,
    categoria: "disabili",
    nome: "Bonus Caregiver",
    importo: "Variabile (Comuni/Regioni)",
    isee: "Qualsiasi ISEE",
    descrizione: "Sostegno economico per chi assiste familiari con disabilità grave (Legge 104). Importo variabile erogato da Comuni e Regioni.",
    come: "Domanda al Comune di residenza o Regione",
    scadenza: "Bando locale",
    tipo: "bando",
    link: "https://www.governo.it",
    novita: false,
  },
  {
    id: 19,
    categoria: "disabili",
    nome: "Detrazioni Ausili Tecnici e Informatici",
    importo: "IVA 4% + detrazione 19%",
    isee: "Qualsiasi ISEE",
    descrizione: "Computer, tablet, dispositivi domotici per disabili: IVA agevolata al 4% e detrazione IRPEF del 19%. Anche protesi e ausili medici.",
    come: "Fattura con codice fiscale; dichiarazione dei redditi",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.agenziaentrate.gov.it",
    novita: false,
  },
  {
    id: 20,
    categoria: "disabili",
    nome: "Disability Card",
    importo: "Accesso gratuito/agevolato",
    isee: "Qualsiasi ISEE",
    descrizione: "Carta INPS che permette l'accesso agevolato o gratuito a trasporti, musei e servizi culturali in Italia e nell'UE.",
    come: "Richiesta all'INPS",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.inps.it",
    novita: false,
  },
  {
    id: 21,
    categoria: "disabili",
    nome: "Incentivi Assunzione Disabili",
    importo: "35%-70% della retribuzione lorda per 36-60 mesi",
    isee: "Qualsiasi ISEE",
    descrizione: "Per i datori di lavoro: 35% per invalidi 67-79%, 70% per invalidi >79% (36 mesi), 70% per disabili intellettivi/psichici almeno 45% (60 mesi).",
    come: "Domanda tramite SIISL e INPS",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.inps.it",
    novita: false,
  },

  // STUDENTI
  {
    id: 22,
    categoria: "studenti",
    nome: "Carta della Cultura Giovani",
    importo: "500€",
    isee: "ISEE < 35.000€",
    descrizione: "Voucher per i nati nel 2007 (18 anni nel 2025) per libri, cinema, teatro, concerti, corsi, streaming culturale. Ultima edizione cumulabile con Carta del Merito.",
    come: "Registrazione su cartegiovani.cultura.gov.it con SPID o CIE",
    scadenza: "Domanda entro 30/06/2026, spesa entro 31/12/2026",
    tipo: "bando",
    link: "https://cartegiovani.cultura.gov.it",
    novita: false,
  },
  {
    id: 23,
    categoria: "studenti",
    nome: "Carta del Merito",
    importo: "500€",
    isee: "Qualsiasi ISEE",
    descrizione: "Per chi ha conseguito la maturità con 100/100 (indipendentemente dal reddito). Cumulabile con Carta della Cultura per un totale di 1.000€.",
    come: "Registrazione su cartegiovani.cultura.gov.it con SPID o CIE",
    scadenza: "Domanda entro 30/06/2026, spesa entro 31/12/2026",
    tipo: "bando",
    link: "https://cartegiovani.cultura.gov.it",
    novita: false,
  },
  {
    id: 24,
    categoria: "studenti",
    nome: "No Tax Area Universitaria",
    importo: "Esenzione totale tasse universitarie",
    isee: "ISEE < 22.000€",
    descrizione: "Esonero totale dalla contribuzione universitaria per ISEE < 22.000€. Molti atenei alzano la soglia fino a 28.000-30.000€. Riduzioni progressive fino a 30.000€.",
    come: "Autocertificazione ISEE all'università al momento dell'iscrizione",
    scadenza: "Permanente (per anno accademico)",
    tipo: "stabile",
    link: "https://www.mur.gov.it",
    novita: false,
  },
  {
    id: 25,
    categoria: "studenti",
    nome: "Borse di Studio DSU Regionali",
    importo: "Varia (solitamente 2.000-5.000€/anno)",
    isee: "ISEE < 25.000€",
    descrizione: "Borse di studio per studenti universitari basate su merito e reddito, gestite dalle agenzie regionali per il diritto allo studio (DSU). Includono anche alloggio.",
    come: "Bando annuale DSU regionale (es. ER.GO in Emilia-Romagna)",
    scadenza: "Bando annuale (tipicamente estate)",
    tipo: "bando",
    link: "https://www.er-go.it",
    novita: false,
  },
  {
    id: 26,
    categoria: "studenti",
    nome: "Borse di Studio INPS (figli dipendenti pubblici)",
    importo: "2.000€ ciascuna (13.228 borse)",
    isee: "Qualsiasi ISEE",
    descrizione: "Borse di studio per figli e orfani di dipendenti e pensionati pubblici. Numero e importo stabiliti annualmente dall'INPS.",
    come: "Bando INPS, domanda online",
    scadenza: "Bando annuale",
    tipo: "bando",
    link: "https://www.inps.it",
    novita: false,
  },
  {
    id: 27,
    categoria: "studenti",
    nome: "Fondo Libri di Testo (scuola secondaria)",
    importo: "Fondo 20M€/anno",
    isee: "ISEE basso",
    descrizione: "Nuovo fondo permanente 2026 destinato ai Comuni per sostenere l'acquisto di libri di testo per la scuola secondaria di II grado.",
    come: "Tramite Comune di residenza",
    scadenza: "Permanente dal 2026",
    tipo: "nuovo",
    link: "https://www.governo.it",
    novita: true,
  },
  {
    id: 28,
    categoria: "studenti",
    nome: "Esenzione Tasse Scolastiche (IV-V superiore)",
    importo: "Esenzione completa",
    isee: "ISEE < 20.000€",
    descrizione: "Esenzione totale dalle tasse scolastiche (iscrizione, frequenza, esame) per gli studenti del 4° e 5° anno della scuola secondaria.",
    come: "Presentazione ISEE alla segreteria scolastica",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.miur.gov.it",
    novita: false,
  },
  {
    id: 29,
    categoria: "studenti",
    nome: "Erasmus Italiano",
    importo: "Borsa per mobilità interna",
    isee: "Qualsiasi ISEE",
    descrizione: "Programma di mobilità interna tra università italiane. Rifinanziato dalla Legge di Bilancio 2026 con 3 milioni di euro.",
    come: "Bando universitario",
    scadenza: "Bando annuale",
    tipo: "bando",
    link: "https://www.mur.gov.it",
    novita: false,
  },
  {
    id: 30,
    categoria: "studenti",
    nome: "Fondo Borse di Studio Universitarie (+250M€)",
    importo: "Incremento fondo esistente",
    isee: "ISEE basso + merito",
    descrizione: "La Legge di Bilancio 2026 ha aumentato di 250 milioni di euro il fondo per le borse di studio universitarie, ampliando la platea di beneficiari meritevoli a basso reddito.",
    come: "Tramite DSU regionale",
    scadenza: "Permanente",
    tipo: "nuovo",
    link: "https://www.mur.gov.it",
    novita: true,
  },

  // CASA
  {
    id: 31,
    categoria: "casa",
    nome: "Bonus Ristrutturazioni (Bonus Casa)",
    importo: "Detrazione 50% (prima casa) / 36% (altre)",
    isee: "Qualsiasi ISEE",
    descrizione: "Detrazione IRPEF per lavori di ristrutturazione edilizia. 50% per prima casa (max 96.000€), 36% per seconde case. Ripartita in 10 anni. Attenzione: tetto annuo se reddito > 75.000€.",
    come: "Bonifico dedicato, trasmissione dati ENEA, dichiarazione redditi",
    scadenza: "Confermato 2026",
    tipo: "stabile",
    link: "https://www.agenziaentrate.gov.it",
    novita: false,
  },
  {
    id: 32,
    categoria: "casa",
    nome: "Ecobonus (Riqualificazione Energetica)",
    importo: "Detrazione 50% (prima casa) / 36% (altre)",
    isee: "Qualsiasi ISEE",
    descrizione: "Detrazione per miglioramento efficienza energetica: pompe di calore, infissi, isolamento termico. Allineato al Bonus Casa nelle aliquote. Limite annuo: 14.000€ per redditi 75-100k€; 8.000€ oltre 100k€.",
    come: "Bonifico dedicato + scheda tecnica + trasmissione ENEA entro 90 giorni",
    scadenza: "Confermato 2026",
    tipo: "stabile",
    link: "https://www.agenziaentrate.gov.it",
    novita: false,
  },
  {
    id: 33,
    categoria: "casa",
    nome: "Conto Termico 3.0",
    importo: "Contributo diretto fino al 65%",
    isee: "Qualsiasi ISEE",
    descrizione: "Contributo in conto capitale (non detrazione) per pompe di calore, solare termico, biomassa, sistemi di ventilazione. Fino al 65% delle spese ammissibili. Erogato in 1-5 anni da GSE.",
    come: "Domanda sul portale GSE prima dei lavori",
    scadenza: "Permanente (fondi rinnovabili annualmente)",
    tipo: "stabile",
    link: "https://www.gse.it",
    novita: false,
  },
  {
    id: 34,
    categoria: "casa",
    nome: "Bonus Mobili",
    importo: "Detrazione 50% su max 5.000€",
    isee: "Qualsiasi ISEE",
    descrizione: "Detrazione IRPEF del 50% per acquisto mobili e grandi elettrodomestici di classe energetica elevata, legata a interventi di ristrutturazione avviati nel 2025-2026.",
    come: "Bonifico o carta dedicata; dichiarazione dei redditi",
    scadenza: "Confermato 2026",
    tipo: "stabile",
    link: "https://www.agenziaentrate.gov.it",
    novita: false,
  },
  {
    id: 35,
    categoria: "casa",
    nome: "Bonus Barriere Architettoniche",
    importo: "Detrazione 50% (dal 2026, era 75%)",
    isee: "Qualsiasi ISEE",
    descrizione: "Per eliminare barriere architettoniche: scale, corridoi, bagni, ascensori, rampe. Dal 2026 l'aliquota torna al 50% (prima casa). La detrazione al 75% era solo fino al 31/12/2025.",
    come: "Bonifico dedicato, dichiarazione dei redditi",
    scadenza: "Confermato 2026 (aliquota ridotta)",
    tipo: "stabile",
    link: "https://www.agenziaentrate.gov.it",
    novita: false,
  },
  {
    id: 36,
    categoria: "casa",
    nome: "Bonus Case Green (IVA al 50%)",
    importo: "Detrazione 50% dell'IVA pagata",
    isee: "Qualsiasi ISEE",
    descrizione: "Detrazione IRPEF pari al 50% dell'IVA versata per l'acquisto di abitazioni ad alta efficienza energetica. Non è uno sconto immediato ma un rimborso fiscale spalmato nel tempo.",
    come: "Dichiarazione dei redditi con fattura d'acquisto",
    scadenza: "Novità 2026",
    tipo: "nuovo",
    link: "https://www.agenziaentrate.gov.it",
    novita: true,
  },
  {
    id: 37,
    categoria: "casa",
    nome: "Superbonus (solo sisma 2016)",
    importo: "110% - solo casi residuali",
    isee: "Qualsiasi ISEE",
    descrizione: "Non più disponibile in via generale. Rimane solo per interventi di ricostruzione/riduzione rischio sismico in Abruzzo, Lazio, Marche e Umbria (sisma 2016) con istanze già presentate.",
    come: "Solo per pratiche già avviate",
    scadenza: "Solo casi pregressi",
    tipo: "stabile",
    link: "https://www.agenziaentrate.gov.it",
    novita: false,
  },

  // MOBILITÀ
  {
    id: 38,
    categoria: "mobilita",
    nome: "Ecobonus Auto Elettrica (PNRR)",
    importo: "Fino a 13.750€ con rottamazione",
    isee: "Qualsiasi ISEE (ISEE < 30.000€: +25%)",
    descrizione: "Incentivo per acquisto auto elettrica gestito dal MASE con fondi PNRR (600M€). Base: 11.000€ con rottamazione Euro 0-4; +25% per ISEE < 30.000€. Sconto applicato in fattura dal concessionario.",
    come: "Tramite concessionario autorizzato (sconto in fattura automatico)",
    scadenza: "Fino a esaurimento fondi (entro giugno 2026)",
    tipo: "bando",
    link: "https://www.mase.gov.it",
    novita: false,
  },
  {
    id: 39,
    categoria: "mobilita",
    nome: "Ecobonus Moto/Ciclomotori Elettrici",
    importo: "Fino a 4.000€",
    isee: "Qualsiasi ISEE",
    descrizione: "Per acquisto moto, scooter, ciclomotori, tricicli e quadricicli elettrici/ibridi (categorie L1e-L7e). 30% del prezzo senza rottamazione (max 3.000€); 40% con rottamazione (max 4.000€). Budget 30M€.",
    come: "Tramite concessionario autorizzato sulla piattaforma MIMIT/Invitalia",
    scadenza: "Attivo dal 18/03/2026, fino a esaurimento fondi",
    tipo: "bando",
    link: "https://ecobonus.mise.gov.it",
    novita: false,
  },
  {
    id: 40,
    categoria: "mobilita",
    nome: "Agevolazioni Auto Disabili",
    importo: "IVA 4% + detrazione 19% + esenzione bollo",
    isee: "Qualsiasi ISEE",
    descrizione: "Per persone con disabilità: IVA al 4%, detrazione IRPEF 19% (max spesa 18.075,99€), esenzione bollo auto e imposta di trascrizione al PRA.",
    come: "Fattura con riferimento normativo; dichiarazione dei redditi",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.agenziaentrate.gov.it",
    novita: false,
  },
  {
    id: 41,
    categoria: "mobilita",
    nome: "Bonus Bici/Monopattini (bandi regionali)",
    importo: "Variabile (50-500€)",
    isee: "Varia per bando",
    descrizione: "Non esiste più un bonus nazionale per bici e monopattini dal 2024. Esistono bandi locali regionali e comunali a macchia di leopardo. Verifica il sito della tua Regione/Comune.",
    come: "Portale Regione o Comune di residenza",
    scadenza: "Bando locale (verifica disponibilità)",
    tipo: "bando",
    link: "https://incentivi.gov.it",
    novita: false,
  },
  {
    id: 42,
    categoria: "mobilita",
    nome: "Bonus Trasporti Pubblici",
    importo: "Fino a 60€ (abbonamento)",
    isee: "ISEE < 20.000€",
    descrizione: "Contributo per l'acquisto di abbonamenti a trasporto pubblico locale, regionale o nazionale (treni, metro, bus). Valido anche per Trenitalia.",
    come: "Piattaforma bonustrasporti.lavoro.gov.it con SPID",
    scadenza: "Bando periodico (verifica disponibilità 2026)",
    tipo: "bando",
    link: "https://bonustrasporti.lavoro.gov.it",
    novita: false,
  },

  // LAVORO
  {
    id: 43,
    categoria: "lavoro",
    nome: "NASpI (Indennità Disoccupazione)",
    importo: "75% dello stipendio medio (primi 30 gg) poi riduzione",
    isee: "Qualsiasi ISEE",
    descrizione: "Indennità di disoccupazione per lavoratori dipendenti con almeno 13 settimane contributive negli ultimi 4 anni. Dura metà delle settimane contributive (max 24 mesi). Dal 6° mese si riduce del 3%/mese.",
    come: "Domanda INPS entro 68 giorni dalla cessazione del rapporto",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.inps.it",
    novita: false,
  },
  {
    id: 44,
    categoria: "lavoro",
    nome: "Super Deduzione Nuove Assunzioni (130%)",
    importo: "Deduzione 130% del costo del lavoro",
    isee: "Qualsiasi ISEE",
    descrizione: "Per le imprese che assumono a tempo indeterminato: deduzione del 130% del costo del lavoratore. Percentuale più alta per assunzioni di categorie svantaggiate.",
    come: "Dichiarazione dei redditi aziendale",
    scadenza: "Confermato 2026",
    tipo: "stabile",
    link: "https://www.mef.gov.it",
    novita: false,
  },
  {
    id: 45,
    categoria: "lavoro",
    nome: "Esonero Contributivo Giovani under 35",
    importo: "100% contributi (max 3.000€/anno) per 36 mesi",
    isee: "Qualsiasi ISEE",
    descrizione: "Esonero totale dei contributi previdenziali (no INAIL) per le aziende che assumono giovani under 35 alla prima occupazione stabile. Durata 36 mesi.",
    come: "Domanda INPS tramite datore di lavoro",
    scadenza: "Confermato 2026",
    tipo: "stabile",
    link: "https://www.inps.it",
    novita: false,
  },
  {
    id: 46,
    categoria: "lavoro",
    nome: "Supporto Formazione e Lavoro (SFL)",
    importo: "500€/mese per 12 mesi",
    isee: "ISEE < 6.000€",
    descrizione: "Per persone tra 18 e 59 anni in difficoltà economica, in grado di lavorare. Condizionato alla partecipazione a programmi di formazione/tirocinio tramite GOL.",
    come: "Domanda INPS + iscrizione SIISL + percorso formativo",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.inps.it",
    novita: false,
  },
  {
    id: 47,
    categoria: "lavoro",
    nome: "Incentivo Assunzione percettori NASpI",
    importo: "20% dell'indennità residua mensile",
    isee: "Qualsiasi ISEE",
    descrizione: "Contributo mensile al datore di lavoro che assume un lavoratore percettore di NASpI a tempo indeterminato. Max 24 mesi. Cumulabile con altri sgravi.",
    come: "Offerta pubblicata su SIISL + domanda INPS",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.inps.it",
    novita: false,
  },

  // BOLLETTE
  {
    id: 48,
    categoria: "bollette",
    nome: "Bonus Bolletta Luce (disagio economico)",
    importo: "~190€/anno (automatico)",
    isee: "ISEE < 9.530€",
    descrizione: "Sconto automatico in bolletta dell'energia elettrica. Anche per famiglie numerose (4+ figli) con ISEE < 20.000€. Non serve fare domanda se si ha l'ISEE aggiornato.",
    come: "Automatico con ISEE aggiornato (tramite 730 o DSU al CAF)",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.arera.it",
    novita: false,
  },
  {
    id: 49,
    categoria: "bollette",
    nome: "Bonus Bolletta Gas (disagio economico)",
    importo: "~30-110€/anno (varia per zona climatica)",
    isee: "ISEE < 9.530€",
    descrizione: "Sconto automatico in bolletta del gas naturale. L'importo varia in base alla zona climatica del comune di residenza.",
    come: "Automatico con ISEE aggiornato",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.arera.it",
    novita: false,
  },
  {
    id: 50,
    categoria: "bollette",
    nome: "Bonus Bolletta Acqua (disagio economico)",
    importo: "~50 litri/giorno/persona gratuiti",
    isee: "ISEE < 9.530€",
    descrizione: "Bonus idrico integrativo per le famiglie in disagio economico: 50 litri al giorno per persona a costo zero.",
    come: "Automatico con ISEE aggiornato",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.arera.it",
    novita: false,
  },
  {
    id: 51,
    categoria: "bollette",
    nome: "Bonus Bolletta Elettrica (disagio fisico)",
    importo: "Sconto fisso su tariffa",
    isee: "Qualsiasi ISEE",
    descrizione: "Per chi utilizza apparecchiature elettromedicali salvavita in casa (respiratori, dialisi, ecc.). Non dipende dall'ISEE, richiede certificazione ASL.",
    come: "Domanda al distributore di zona con certificazione ASL",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.arera.it",
    novita: false,
  },
  {
    id: 52,
    categoria: "bollette",
    nome: "Conto Corrente Base Gratuito",
    importo: "Azzera canone (~34,20€/anno)",
    isee: "ISEE < 11.600€",
    descrizione: "Conto corrente a operatività limitata (carta debito, bonifici, prelievi) obbligatoriamente gratuito per famiglie con ISEE < 11.600€ e pensionati con reddito < 18.000€.",
    come: "Richiesta alla propria banca con ISEE",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.bancaditalia.it",
    novita: false,
  },

  // SALUTE
  {
    id: 53,
    categoria: "salute",
    nome: "Bonus Psicologo",
    importo: "Da 500€ a 1.500€",
    isee: "ISEE < 50.000€",
    descrizione: "Contributo per sessioni di psicoterapia con psicoterapeuti iscritti all'albo. ISEE < 15.000€: 1.500€; < 30.000€: 1.000€; < 50.000€: 500€.",
    come: "Domanda INPS online, poi scelta del professionista dalla lista INPS",
    scadenza: "Bando annuale (verifica 2026)",
    tipo: "bando",
    link: "https://www.inps.it",
    novita: false,
  },
  {
    id: 54,
    categoria: "salute",
    nome: "Detrazioni Spese Sanitarie",
    importo: "Detrazione 19% senza franchigia per disabili",
    isee: "Qualsiasi ISEE",
    descrizione: "Detrazione IRPEF del 19% su spese mediche documentabili (con franchigia di 129,11€ per le persone senza disabilità). Per disabili la franchigia non si applica.",
    come: "Dichiarazione dei redditi con fatture/ricevute",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.agenziaentrate.gov.it",
    novita: false,
  },
  {
    id: 55,
    categoria: "salute",
    nome: "Esenzione Ticket Sanitario per reddito",
    importo: "Esenzione totale ticket",
    isee: "Reddito < 36.151,98€ (per over 65) o altri codici",
    descrizione: "Diverse fasce di esenzione: E01 (over 65 basso reddito), E02 (titolari pensione minima < 60.000€ con coniuge), E03 (disoccupati), E04 (invalidi parziali). Verificare il proprio codice.",
    come: "Richiesta al medico di base con documenti reddituali",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.salute.gov.it",
    novita: false,
  },
  {
    id: 56,
    categoria: "salute",
    nome: "Bonus Spese Veterinarie",
    importo: "Detrazione 19% su max 550€",
    isee: "Qualsiasi ISEE",
    descrizione: "Detrazione IRPEF del 19% sulle spese veterinarie per animali domestici legalmente detenuti, su importo eccedente 129,11€ fino a 550€ (max detrazione ~80€).",
    come: "Dichiarazione dei redditi con fatture veterinarie",
    scadenza: "Permanente",
    tipo: "stabile",
    link: "https://www.agenziaentrate.gov.it",
    novita: false,
  },
];

const tipoBadge = {
  stabile: { label: "Permanente", color: "#10b981", bg: "#10b98120" },
  bando: { label: "A bando", color: "#f59e0b", bg: "#f59e0b20" },
  nuovo: { label: "Novità 2026", color: "#6366f1", bg: "#6366f120" },
};

export default function BonusItalia() {
  const [activeCategory, setActiveCategory] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedId, setExpandedId] = useState(null);
  const [filterType, setFilterType] = useState("all");

  const filtered = useMemo(() => {
    return bonuses.filter((b) => {
      const catMatch = activeCategory === "all" || b.categoria === activeCategory;
      const typeMatch = filterType === "all" || b.tipo === filterType;
      const searchMatch =
        searchQuery === "" ||
        b.nome.toLowerCase().includes(searchQuery.toLowerCase()) ||
        b.descrizione.toLowerCase().includes(searchQuery.toLowerCase());
      return catMatch && typeMatch && searchMatch;
    });
  }, [activeCategory, searchQuery, filterType]);

  const counts = useMemo(() => {
    const c = {};
    categories.forEach((cat) => {
      c[cat.id] = cat.id === "all" ? bonuses.length : bonuses.filter((b) => b.categoria === cat.id).length;
    });
    return c;
  }, []);

  return (
    <div style={{
      fontFamily: "'Georgia', 'Times New Roman', serif",
      background: "#0e0e14",
      minHeight: "100vh",
      color: "#e8e0d0",
      padding: "0",
    }}>
      {/* Header */}
      <div style={{
        background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
        padding: "40px 24px 32px",
        borderBottom: "1px solid #ffffff15",
        position: "relative",
        overflow: "hidden",
      }}>
        <div style={{
          position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
          background: "radial-gradient(ellipse at 20% 50%, #e8173015 0%, transparent 60%), radial-gradient(ellipse at 80% 20%, #009fe315 0%, transparent 50%)",
          pointerEvents: "none",
        }} />
        <div style={{ maxWidth: 960, margin: "0 auto", position: "relative" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
            <span style={{ fontSize: 40 }}>🇮🇹</span>
            <div>
              <h1 style={{
                margin: 0, fontSize: 28, fontWeight: 700, letterSpacing: -0.5,
                color: "#fff", fontFamily: "'Georgia', serif",
              }}>
                Guida Completa ai Bonus Italia
              </h1>
              <p style={{ margin: 0, color: "#94a3b8", fontSize: 14, marginTop: 2, fontFamily: "system-ui, sans-serif" }}>
                Tutte le agevolazioni attive • Aggiornato a Giugno 2026 • {bonuses.length} bonus catalogati
              </p>
            </div>
          </div>
          <div style={{
            background: "#ffffff10", border: "1px solid #ffffff20",
            borderRadius: 8, padding: "10px 14px", marginTop: 16,
            fontSize: 13, color: "#fbbf24", fontFamily: "system-ui, sans-serif",
            display: "flex", gap: 8, alignItems: "flex-start",
          }}>
            <span>⚠️</span>
            <span><strong>Nota fondamentale:</strong> L'ISEE è il "passaporto" per quasi tutti i bonus. Presentare la DSU al CAF ogni gennaio è essenziale per non perdere alcun beneficio. Verifica sempre su <strong>incentivi.gov.it</strong> e tramite l'App IO.</span>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 960, margin: "0 auto", padding: "24px 16px" }}>
        {/* Search + Filter */}
        <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
          <input
            type="text"
            placeholder="🔍  Cerca un bonus..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              flex: 1, minWidth: 200,
              background: "#ffffff0d", border: "1px solid #ffffff20",
              borderRadius: 8, padding: "10px 14px", color: "#e8e0d0",
              fontSize: 14, fontFamily: "system-ui, sans-serif",
              outline: "none",
            }}
          />
          <div style={{ display: "flex", gap: 8 }}>
            {[
              { id: "all", label: "Tutti" },
              { id: "stabile", label: "🟢 Permanenti" },
              { id: "bando", label: "🟡 A bando" },
              { id: "nuovo", label: "🟣 Novità 2026" },
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setFilterType(t.id)}
                style={{
                  padding: "8px 14px", borderRadius: 8, cursor: "pointer", fontSize: 13,
                  fontFamily: "system-ui, sans-serif", border: "1px solid",
                  borderColor: filterType === t.id ? "#6366f1" : "#ffffff20",
                  background: filterType === t.id ? "#6366f130" : "transparent",
                  color: filterType === t.id ? "#a5b4fc" : "#94a3b8",
                  transition: "all 0.2s",
                }}
              >{t.label}</button>
            ))}
          </div>
        </div>

        {/* Category Tabs */}
        <div style={{
          display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 24,
        }}>
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              style={{
                padding: "8px 16px", borderRadius: 100, cursor: "pointer",
                fontSize: 13, fontFamily: "system-ui, sans-serif",
                border: "1px solid",
                borderColor: activeCategory === cat.id ? "#e8173080" : "#ffffff20",
                background: activeCategory === cat.id ? "#e8173020" : "#ffffff08",
                color: activeCategory === cat.id ? "#fca5a5" : "#94a3b8",
                transition: "all 0.2s",
                display: "flex", alignItems: "center", gap: 6,
              }}
            >
              <span>{cat.emoji}</span>
              <span>{cat.label}</span>
              <span style={{
                background: "#ffffff15", borderRadius: 100,
                padding: "1px 7px", fontSize: 11,
                color: activeCategory === cat.id ? "#fca5a5" : "#64748b",
              }}>
                {counts[cat.id]}
              </span>
            </button>
          ))}
        </div>

        {/* Results count */}
        <div style={{
          color: "#64748b", fontSize: 13, marginBottom: 16,
          fontFamily: "system-ui, sans-serif",
        }}>
          {filtered.length} bonus trovati
        </div>

        {/* Bonus List */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {filtered.map((bonus) => {
            const isOpen = expandedId === bonus.id;
            const iseeColor = iseeColors[bonus.isee] || "#64748b";
            const tipo = tipoBadge[bonus.tipo];

            return (
              <div
                key={bonus.id}
                style={{
                  background: isOpen ? "#ffffff0f" : "#ffffff08",
                  border: `1px solid ${isOpen ? "#ffffff25" : "#ffffff12"}`,
                  borderRadius: 12,
                  overflow: "hidden",
                  transition: "all 0.2s",
                }}
              >
                <button
                  onClick={() => setExpandedId(isOpen ? null : bonus.id)}
                  style={{
                    width: "100%", textAlign: "left", background: "none",
                    border: "none", cursor: "pointer", padding: "14px 18px",
                    display: "flex", alignItems: "flex-start", gap: 12,
                  }}
                >
                  {/* Category emoji */}
                  <span style={{ fontSize: 22, flexShrink: 0, marginTop: 1 }}>
                    {categories.find((c) => c.id === bonus.categoria)?.emoji}
                  </span>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <span style={{
                        color: "#e8e0d0", fontSize: 15, fontWeight: 600,
                        fontFamily: "system-ui, sans-serif",
                      }}>
                        {bonus.novita && <span style={{ color: "#a78bfa", marginRight: 4 }}>★</span>}
                        {bonus.nome}
                      </span>
                    </div>
                    <div style={{
                      display: "flex", gap: 8, marginTop: 6, flexWrap: "wrap",
                      alignItems: "center",
                    }}>
                      <span style={{
                        background: "#22c55e20", border: "1px solid #22c55e30",
                        color: "#4ade80", borderRadius: 6, padding: "2px 10px",
                        fontSize: 12, fontFamily: "system-ui, sans-serif", fontWeight: 600,
                      }}>
                        💰 {bonus.importo}
                      </span>
                      <span style={{
                        background: `${iseeColor}20`, border: `1px solid ${iseeColor}30`,
                        color: iseeColor, borderRadius: 6, padding: "2px 10px",
                        fontSize: 12, fontFamily: "system-ui, sans-serif",
                      }}>
                        {bonus.isee}
                      </span>
                      <span style={{
                        background: tipo.bg, border: `1px solid ${tipo.color}30`,
                        color: tipo.color, borderRadius: 6, padding: "2px 10px",
                        fontSize: 12, fontFamily: "system-ui, sans-serif",
                      }}>
                        {tipo.label}
                      </span>
                    </div>
                  </div>
                  <span style={{
                    color: "#64748b", fontSize: 18, flexShrink: 0, marginTop: 4,
                    transition: "transform 0.2s",
                    transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
                  }}>▾</span>
                </button>

                {isOpen && (
                  <div style={{
                    padding: "0 18px 18px 18px",
                    borderTop: "1px solid #ffffff10",
                    marginTop: -4,
                    paddingTop: 16,
                  }}>
                    <p style={{
                      margin: "0 0 14px", color: "#94a3b8", fontSize: 14,
                      lineHeight: 1.6, fontFamily: "system-ui, sans-serif",
                    }}>
                      {bonus.descrizione}
                    </p>

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 10 }}>
                      <div style={{
                        background: "#ffffff08", borderRadius: 8, padding: "10px 14px",
                      }}>
                        <div style={{ fontSize: 11, color: "#64748b", fontFamily: "system-ui, sans-serif", marginBottom: 4, textTransform: "uppercase", letterSpacing: 0.5 }}>Come richiederlo</div>
                        <div style={{ fontSize: 13, color: "#cbd5e1", fontFamily: "system-ui, sans-serif" }}>{bonus.come}</div>
                      </div>
                      <div style={{
                        background: "#ffffff08", borderRadius: 8, padding: "10px 14px",
                      }}>
                        <div style={{ fontSize: 11, color: "#64748b", fontFamily: "system-ui, sans-serif", marginBottom: 4, textTransform: "uppercase", letterSpacing: 0.5 }}>Scadenza</div>
                        <div style={{ fontSize: 13, color: "#cbd5e1", fontFamily: "system-ui, sans-serif" }}>{bonus.scadenza}</div>
                      </div>
                    </div>

                    <div style={{ marginTop: 12 }}>
                      <a
                        href={bonus.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          display: "inline-flex", alignItems: "center", gap: 6,
                          color: "#93c5fd", fontSize: 13, textDecoration: "none",
                          fontFamily: "system-ui, sans-serif",
                          borderBottom: "1px solid #93c5fd40",
                          paddingBottom: 1,
                        }}
                      >
                        🔗 Vai al sito ufficiale →
                      </a>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {filtered.length === 0 && (
          <div style={{
            textAlign: "center", color: "#64748b", padding: "60px 0",
            fontFamily: "system-ui, sans-serif",
          }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>🔍</div>
            <p>Nessun bonus trovato con i criteri selezionati.</p>
          </div>
        )}

        {/* Footer */}
        <div style={{
          marginTop: 40, padding: "20px", background: "#ffffff08",
          borderRadius: 12, border: "1px solid #ffffff12",
          fontFamily: "system-ui, sans-serif",
        }}>
          <h3 style={{ margin: "0 0 12px", color: "#e8e0d0", fontSize: 15 }}>📌 Fonti Ufficiali da Monitorare</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 8 }}>
            {[
              { label: "incentivi.gov.it", desc: "Portale unico incentivi", url: "https://incentivi.gov.it" },
              { label: "App IO", desc: "Notifiche bonus automatiche", url: "https://io.italia.it" },
              { label: "INPS.it", desc: "Domande e prestazioni", url: "https://www.inps.it" },
              { label: "Agenzie Entrate", desc: "Detrazioni fiscali", url: "https://www.agenziaentrate.gov.it" },
              { label: "CAF di zona", desc: "Consulenza gratuita ISEE", url: "#" },
              { label: "GSE.it", desc: "Conto Termico 3.0", url: "https://www.gse.it" },
            ].map((s) => (
              <a
                key={s.label}
                href={s.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  background: "#ffffff08", borderRadius: 8, padding: "10px 12px",
                  textDecoration: "none", display: "block",
                  border: "1px solid #ffffff15",
                  transition: "background 0.2s",
                }}
              >
                <div style={{ color: "#60a5fa", fontSize: 13, fontWeight: 600 }}>{s.label}</div>
                <div style={{ color: "#64748b", fontSize: 12, marginTop: 2 }}>{s.desc}</div>
              </a>
            ))}
          </div>
          <p style={{ color: "#475569", fontSize: 12, marginTop: 16, margin: "16px 0 0" }}>
            ⚠️ Questa guida ha scopo informativo. Gli importi e le condizioni possono variare. Verifica sempre sui siti ufficiali o rivolgiti a un CAF/patronato prima di presentare domanda.
          </p>
        </div>
      </div>
    </div>
  );
}