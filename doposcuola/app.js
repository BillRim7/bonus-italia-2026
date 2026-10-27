(function () {
  const $ = (id) => document.getElementById(id);
  const TZ = "Europe/Rome";

  if (typeof firebaseConfig === "undefined" || firebaseConfig.databaseURL.indexOf("INCOLLA") === 0) {
    $("data").textContent = "Configurazione mancante: compila firebase-config.js";
    return;
  }
  firebase.initializeApp(firebaseConfig);
  const db = firebase.database();

  // Data odierna (fuso orario italiano) come chiave AAAA-MM-GG
  function chiaveOggi() {
    return new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
  }
  function dataEstesa() {
    return new Intl.DateTimeFormat("it-IT", { timeZone: TZ, weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(new Date());
  }
  // Chiave sicura per Firebase, uguale per "Marco", "marco " e "MARCO"
  function chiaveNome(nome) {
    return nome.trim().replace(/\s+/g, " ").toLowerCase().replace(/[.$#\[\]\/]/g, "_");
  }
  function pulisciNome(n) {
    n = n.trim().replace(/\s+/g, " ");
    return n.charAt(0).toUpperCase() + n.slice(1);
  }

  let giorno = null, rif = null;

  function iscriviOggi() {
    const oggi = chiaveOggi();
    if (oggi === giorno) return;
    if (rif) rif.off();
    giorno = oggi;
    $("data").textContent = dataEstesa();
    mostra({}); // azzera subito la vista
    rif = db.ref("presenze/" + giorno);
    rif.on("value", (snap) => mostra(snap.val() || {}));
    cancellaGiorniVecchi();
  }

  // Nessuno storico: chi apre la pagina elimina i giorni precedenti
  function cancellaGiorniVecchi() {
    db.ref("presenze").once("value").then((snap) => {
      snap.forEach((figlio) => { if (figlio.key !== giorno) db.ref("presenze/" + figlio.key).remove(); });
    }).catch(() => {});
  }

  function mostra(dati) {
    const liste = { presente: $("lista-presenti"), assente: $("lista-assenti") };
    liste.presente.textContent = ""; liste.assente.textContent = "";
    const conteggi = { presente: 0, assente: 0 };
    Object.keys(dati).map((k) => ({ k, v: dati[k] }))
      .sort((a, b) => (a.v.ts || 0) - (b.v.ts || 0))
      .forEach(({ k, v }) => {
        if (!liste[v.stato]) return;
        conteggi[v.stato]++;
        const li = document.createElement("li");
        const nome = document.createElement("span");
        nome.className = "nome"; nome.textContent = v.nome;
        const cambia = document.createElement("button");
        cambia.textContent = v.stato === "presente" ? "Sposta in Assenti" : "Sposta in Presenti";
        cambia.onclick = () => salva(v.nome, v.stato === "presente" ? "assente" : "presente", true);
        const rimuovi = document.createElement("button");
        rimuovi.className = "rimuovi"; rimuovi.textContent = "Rimuovi";
        rimuovi.setAttribute("aria-label", "Rimuovi " + v.nome);
        rimuovi.onclick = () => { if (confirm("Rimuovere " + v.nome + " dall'elenco?")) db.ref("presenze/" + giorno + "/" + k).remove(); };
        li.append(nome, cambia, rimuovi);
        liste[v.stato].appendChild(li);
      });
    $("n-presenti").textContent = conteggi.presente;
    $("n-assenti").textContent = conteggi.assente;
  }

  function messaggio(t) {
    $("messaggio").textContent = t;
    clearTimeout(messaggio.t);
    messaggio.t = setTimeout(() => ($("messaggio").textContent = ""), 4000);
  }

  function salva(nomeGrezzo, stato, daLista) {
    iscriviOggi();
    const nome = pulisciNome(nomeGrezzo);
    if (!nome) { messaggio("Inserisci il nome del bambino."); $("nome").focus(); return; }
    const k = chiaveNome(nome);
    // transazione: nessun duplicato anche con più genitori contemporanei
    db.ref("presenze/" + giorno + "/" + k).transaction((corrente) => {
      return { nome: corrente ? corrente.nome : nome, stato, ts: corrente && corrente.ts ? corrente.ts : firebase.database.ServerValue.TIMESTAMP };
    }).then((r) => {
      if (!r.committed) return;
      messaggio(nome + (stato === "presente" ? " è stato segnato come presente." : " è stato segnato come assente."));
      if (!daLista) { $("nome").value = ""; }
    }).catch(() => messaggio("Errore: riprova tra qualche istante."));
  }

  $("btn-presente").onclick = () => salva($("nome").value, "presente");
  $("btn-assente").onclick = () => salva($("nome").value, "assente");
  $("form").addEventListener("submit", (e) => e.preventDefault());

  db.ref(".info/connected").on("value", (s) => { $("stato-connessione").hidden = s.val() === true; });

  // Cambio giorno automatico (anche a pagina aperta a mezzanotte)
  iscriviOggi();
  setInterval(iscriviOggi, 15000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) iscriviOggi(); });
})();
