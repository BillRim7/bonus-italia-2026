# Presenze Doposcuola – Guida passo passo

Pagina unica, sempre allo stesso link, aggiornata in tempo reale per tutti i genitori.
Usa **Firebase Realtime Database** (gratuito, piano Spark, nessuna carta di credito) e **GitHub Pages** o **Netlify** per la pubblicazione (gratuiti).

File: `index.html`, `style.css`, `app.js`, `firebase-config.js` (qui vanno le tue chiavi), `database.rules.json` (regole di sicurezza).

## 1. Creare il progetto Firebase
1. Vai su https://console.firebase.google.com e accedi con un account Google.
2. Clicca **Crea un progetto** → nome (es. `doposcuola-presenze`) → disattiva Google Analytics → **Crea progetto**.

## 2. Creare il database
1. Menu a sinistra: **Build (Crea) → Realtime Database → Crea database**.
2. Scegli la posizione **Belgio (europe-west1)** (o la più vicina in Europa).
3. Seleziona **Modalità test** e conferma (le regole le sostituiamo subito al passo 3).

## 3. Impostare le regole
1. Nel Realtime Database apri la scheda **Regole**.
2. Cancella tutto, incolla il contenuto di `database.rules.json` e clicca **Pubblica**.

Le regole accettano solo: nome (max 30 caratteri) e stato "presente"/"assente", salvati sotto la data del giorno.

## 4. Prendere la configurazione
1. Clicca l'ingranaggio ⚙️ → **Impostazioni progetto**.
2. In **Le tue app** clicca l'icona web **`</>`** → dai un nome → **Registra app**.
3. Copia i valori di `firebaseConfig` (apiKey, authDomain, databaseURL, projectId, appId).
4. Incollali in `firebase-config.js` al posto di `INCOLLA_QUI_...`.
   - Se non vedi `databaseURL`, copialo dalla scheda **Dati** del Realtime Database (es. `https://xxx-default-rtdb.europe-west1.firebasedatabase.app`).

> L'apiKey di Firebase per le app web non è un segreto: la protezione è data dalle regole del passo 3.

## 5. Pubblicare la pagina (link permanente)
**Opzione A – Netlify Drop (la più semplice)**
1. Vai su https://app.netlify.com/drop (crea un account gratuito).
2. Trascina la cartella `doposcuola` nella pagina.
3. Ottieni un link tipo `https://nome-casuale.netlify.app`. In *Site settings → Change site name* puoi sceglierne uno più bello, es. `https://doposcuola-rossi.netlify.app`.

**Opzione B – GitHub Pages**
1. Carica i file in un repository GitHub.
2. **Settings → Pages → Deploy from a branch** → scegli il branch e la cartella (`/doposcuola` oppure root se sposti i file) → **Save**.
3. Dopo un minuto il link è `https://TUOUTENTE.github.io/NOMEREPO/`.

**Opzione C – Firebase Hosting** (`npm i -g firebase-tools`, `firebase login`, `firebase init hosting`, `firebase deploy`): link `https://NOME-PROGETTO.web.app`.

## 6. Mettere il link nel gruppo WhatsApp
1. Copia il link ottenuto.
2. Nel gruppo: **Info gruppo → Descrizione** e incolla il link, oppure invia il messaggio e **fissalo** (tieni premuto → Fissa).
3. Il link non cambia mai: la pagina mostra ogni giorno la data di oggi e parte da zero.

## 7. Come funziona (e cosa succede a mezzanotte)
- I dati sono salvati sotto la data del giorno (`presenze/2026-10-27/…`). Il giorno successivo la pagina legge un nuovo percorso vuoto: elenchi e contatori ripartono da zero **automaticamente, alle 00:00 ora italiana**, anche se la pagina è già aperta.
- Quando qualcuno apre la pagina, i dati dei giorni precedenti vengono **eliminati dal database**: nessuno storico.
- Stesso nome inserito due volte (anche "marco" / "Marco "): viene aggiornata la voce esistente, nessun duplicato. Le scritture usano transazioni, quindi più genitori contemporanei non creano conflitti.
- Un genitore può spostare un bambino tra Presenti/Assenti o rimuoverlo con i pulsanti accanto al nome.
- Nessun dato personale oltre al nome e allo stato.

**Nota:** chi ha il link può modificare l'elenco del giorno (scelta voluta, per non richiedere registrazione). Condividi il link solo nel gruppo.

## 8. Prova
Apri il link su due telefoni: inserisci un nome e tocca **Presente** – deve comparire subito su entrambi, con i contatori aggiornati.
