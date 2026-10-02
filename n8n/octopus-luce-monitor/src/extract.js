// Estrazione del prezzo materia prima luce (€/kWh) di UNA offerta dall'HTML della pagina tariffe.
// Codice puro, senza dipendenze: viene incorporato così com'è nel nodo Code di n8n da build.js.
// Regola generale: in caso di dubbio NON restituire un prezzo, ma un errore con codice.

const ENTITIES = {
  nbsp: ' ', amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", euro: '€',
  egrave: 'è', eacute: 'é', agrave: 'à', ograve: 'ò', ugrave: 'ù', igrave: 'ì',
};

function decodeEntities(s) {
  return s
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(parseInt(d, 10)))
    .replace(/&([a-z]+);/gi, (m, n) => (ENTITIES[n.toLowerCase()] !== undefined ? ENTITIES[n.toLowerCase()] : m));
}

// Testo visibile: via script/style/noscript/template/commenti, tag -> spazio, spazi normalizzati.
function visibleText(html) {
  const noHidden = html
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/<(script|style|noscript|template|svg)\b[\s\S]*?<\/\1\s*>/gi, ' ');
  return decodeEntities(noHidden.replace(/<[^>]+>/g, ' '))
    .replace(/[   ]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

// "0,1683" -> 0.1683 ; "1.234,5" -> 1234.5 ; "0.1683" -> 0.1683. Restituisce NaN se non numerico.
function parseItalianNumber(raw) {
  if (typeof raw === 'number') return raw;
  if (raw === null || raw === undefined) return NaN;
  let s = String(raw).trim().replace(/\s/g, '').replace(/^€/, '');
  if (!/^\d{1,3}(\.\d{3})*(,\d+)?$|^\d+(,\d+)?$|^\d+(\.\d+)?$/.test(s)) return NaN;
  if (s.includes(',')) s = s.replace(/\./g, '').replace(',', '.');
  return Number(s);
}

function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Nome offerta -> regex tollerante a spazi/maiuscole ma con confini di parola:
// "Octopus Fissa 12M" NON deve combaciare con "Octopus Fissa 12Mesi". Le varianti più lunghe
// (es. "Octopus Fissa 12M Plus") si escludono elencandole in boundaryNames.
function offerNameRegex(name) {
  const body = name.trim().split(/\s+/).map(escapeRegExp).join('\\s+');
  return new RegExp('(?<![\\p{L}\\p{N}])' + body + '(?![\\p{L}\\p{N}])', 'giu');
}

// Prezzo in €/kWh: "0,1683 €/kWh", "€ 0,1683/kWh", "0,1683 euro/kWh", "16,83 c€/kWh".
const KWH_PRICE = /(€\s*)?(\d+(?:[.,]\d+)?)\s*(c€|cent(?:esimi)?(?:\s+di\s+euro)?|€|euro|eur)?\s*\/\s*kwh\b/gi;

// Parole che, subito prima del valore, indicano che NON è il prezzo materia prima.
const EXCLUDE_BEFORE = /(totale|complessiv|medio|media|stimat|stima|bolletta|spesa|risparmi|iva\s+inclusa|tasse\s+incluse|sconto|bonus)\W*[^€\d]{0,40}$/i;
// Indizi di prezzo indicizzato (PUN + spread): la soglia non sarebbe confrontabile.
const INDEXED_BEFORE = /(pun|psv|indicizzat|variabile|\+)\s*[^\d]{0,25}$/i;

function extractLucePrice(html, offerName, opts) {
  const o = Object.assign({ windowChars: 400, boundaryNames: [], minPrice: 0.01, maxPrice: 2 }, opts || {});
  const fail = (code, detail, extra) => Object.assign({ ok: false, errorCode: code, errorDetail: detail, offerName }, extra || {});

  if (typeof html !== 'string' || html.length < 200) return fail('EMPTY_BODY', 'Risposta vuota o troppo corta');
  if (!offerName || !offerName.trim()) return fail('CONFIG', 'Nome offerta non configurato');

  const text = visibleText(html);
  const nameRe = offerNameRegex(offerName);
  const matches = [...text.matchAll(nameRe)];

  if (matches.length === 0) {
    // Il nome esiste solo dentro <script> (es. JSON di Next.js) => contenuto renderizzato lato client.
    if (offerNameRegex(offerName).test(decodeEntities(html))) {
      return fail('DYNAMIC_CONTENT', "Nome offerta presente solo negli script: la pagina carica i prezzi dinamicamente. Usare una fonte alternativa.");
    }
    return fail('OFFER_NOT_FOUND', 'Offerta "' + offerName + '" non trovata nella pagina (nome cambiato o offerta ritirata?)');
  }

  const boundaryRes = o.boundaryNames
    .filter((b) => b && b.trim() && b.trim().toLowerCase() !== offerName.trim().toLowerCase())
    .map(offerNameRegex);

  const found = [];
  let indexedHits = 0;
  for (const m of matches) {
    // Occorrenza che in realtà è l'inizio di un'offerta più lunga elencata nei confini: saltala.
    const isVariant = boundaryRes.some((re) => { re.lastIndex = 0; const v = re.exec(text.slice(m.index, m.index + 200)); return v && v.index === 0 && v[0].length > m[0].length; });
    if (isVariant) continue;
    const start = m.index + m[0].length;
    let section = text.slice(start, start + o.windowChars);
    // Tronca alla prossima occorrenza dell'offerta stessa o di un'altra offerta nota.
    for (const re of [offerNameRegex(offerName), ...boundaryRes]) {
      re.lastIndex = 0;
      const b = re.exec(section);
      if (b) section = section.slice(0, b.index);
    }
    for (const p of section.matchAll(KWH_PRICE)) {
      const unit = (p[3] || p[1] || '').toLowerCase().trim();
      if (!unit) continue; // "0,16/kWh" senza valuta: non verificabile
      const before = section.slice(Math.max(0, p.index - 60), p.index);
      if (INDEXED_BEFORE.test(before)) { indexedHits++; continue; }
      if (EXCLUDE_BEFORE.test(before)) continue;
      let value = parseItalianNumber(p[2]);
      if (Number.isNaN(value)) continue;
      if (unit.startsWith('c')) value = value / 100;
      found.push({ value, raw: p[0].trim(), context: (before + p[0]).trim().slice(-120) });
    }
  }

  if (found.length === 0) {
    if (indexedHits > 0) return fail('INDEXED_PRICE', "L'offerta mostra un prezzo indicizzato (PUN/spread): non è un prezzo fisso confrontabile con la soglia.");
    return fail('PRICE_NOT_FOUND', 'Offerta trovata ma nessun prezzo luce in €/kWh vicino al nome (struttura cambiata o caricamento dinamico).');
  }

  const distinct = [...new Set(found.map((f) => Math.round(f.value * 1e6)))];
  if (distinct.length > 1) {
    return fail('AMBIGUOUS', 'Più prezzi €/kWh diversi associati all\'offerta: ' + found.map((f) => f.raw).join(' | '), { candidates: found });
  }

  const price = found[0].value;
  if (!Number.isFinite(price) || price < o.minPrice || price > o.maxPrice) {
    return fail('OUT_OF_RANGE', 'Valore ' + found[0].raw + ' fuori dall\'intervallo plausibile ' + o.minPrice + '–' + o.maxPrice + ' €/kWh');
  }

  return { ok: true, offerName, price, priceRaw: found[0].raw, context: found[0].context, occurrences: found.length };
}

module.exports = { extractLucePrice, parseItalianNumber, visibleText };
