// Esecuzione: node --test test/   (Node >= 18, nessuna dipendenza)
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { extractLucePrice, parseItalianNumber } = require('../src/extract');
const { evaluate } = require('../src/state');

const fx = (f) => fs.readFileSync(path.join(__dirname, 'fixtures', f), 'utf8');
const OFFER = 'Octopus Fissa 12M';
const OPTS = { boundaryNames: ['Octopus Fissa 12M Plus', 'Octopus Flex'] };
const THRESHOLD = 0.10;
const page = (body) => '<html><body>' + body + '</body></html>' + ' '.repeat(300);

test('virgola decimale italiana', () => {
  assert.equal(parseItalianNumber('0,1683'), 0.1683);
  assert.equal(parseItalianNumber('0,10'), 0.1);
  assert.equal(parseItalianNumber('1.234,5'), 1234.5);
  assert.equal(parseItalianNumber('0.1683'), 0.1683);
  assert.ok(Number.isNaN(parseItalianNumber('n.d.')));
  assert.ok(Number.isNaN(parseItalianNumber('0,1,2')));
});

test('caso 1 - prezzo sopra soglia: estrae solo la materia prima luce dell\'offerta scelta', () => {
  const r = extractLucePrice(fx('sopra-soglia.html'), OFFER, OPTS);
  assert.equal(r.ok, true, JSON.stringify(r));
  assert.equal(r.price, 0.1683); // non 0,45 €/Smc (gas), non 6 €/mese, non 0,05 (Plus), non 0,25 (spesa media), non 0,0001 (script)
  const e = evaluate({ status: 'ABOVE' }, r, THRESHOLD, 't1');
  assert.equal(e.action, 'NONE');
  assert.equal(e.statusAfter, 'ABOVE');
});

test('caso 2 - prezzo sotto soglia: un solo avviso sulla transizione', () => {
  const r = extractLucePrice(fx('sotto-soglia.html'), OFFER, OPTS);
  assert.equal(r.ok, true, JSON.stringify(r));
  assert.equal(r.price, 0.095);
  const state = { status: 'ABOVE' };
  assert.equal(evaluate(state, r, THRESHOLD, 't1').action, 'PRICE_ALERT');
  assert.equal(evaluate(state, r, THRESHOLD, 't2').action, 'NONE'); // giorno dopo, ancora sotto: niente email
  assert.equal(state.status, 'BELOW');
});

test('caso 3 - dato non leggibile (contenuto dinamico): nessun avviso di ribasso, avviso tecnico', () => {
  const r = extractLucePrice(fx('non-leggibile.html'), OFFER, OPTS);
  assert.equal(r.ok, false);
  assert.equal(r.errorCode, 'DYNAMIC_CONTENT');
  const state = { status: 'ABOVE' };
  assert.equal(evaluate(state, r, THRESHOLD, 't1').action, 'TECH_ALERT');
  assert.equal(evaluate(state, r, THRESHOLD, 't2').action, 'NONE'); // stesso errore: nessuno spam
  assert.equal(state.status, 'ABOVE'); // lo stato prezzo non cambia
});

test('ciclo completo: sopra -> sotto (avviso) -> sotto -> errore -> sotto -> sopra (riarmo) -> sotto (nuovo avviso)', () => {
  const state = {};
  const ok = (price) => ({ ok: true, price });
  const err = { ok: false, errorCode: 'HTTP_ERROR' };
  const seq = [ok(0.12), ok(0.09), ok(0.09), err, ok(0.09), ok(0.10), ok(0.099)];
  const actions = seq.map((r, i) => evaluate(state, r, THRESHOLD, 't' + i).action);
  assert.deepEqual(actions, ['NONE', 'PRICE_ALERT', 'NONE', 'TECH_ALERT', 'NONE', 'NONE', 'PRICE_ALERT']);
  assert.equal(state.log.length, 7);
});

test('prezzo uguale alla soglia non è "inferiore"', () => {
  const state = { status: 'ABOVE' };
  assert.equal(evaluate(state, { ok: true, price: 0.1 }, 0.1, 't').action, 'NONE');
  assert.equal(state.status, 'ABOVE');
});

test('primo avvio già sotto soglia: nessun avviso (nessuna transizione osservata) salvo opzione', () => {
  assert.equal(evaluate({}, { ok: true, price: 0.05 }, 0.1, 't').action, 'NONE');
  assert.equal(evaluate({}, { ok: true, price: 0.05 }, 0.1, 't', { alertOnFirstRunIfBelow: true }).action, 'PRICE_ALERT');
});

test('errori di struttura e ambiguità non producono prezzi', () => {
  assert.equal(extractLucePrice('', OFFER).errorCode, 'EMPTY_BODY');
  assert.equal(extractLucePrice(page('<h2>Octopus Fissa 24M</h2><p>0,12 €/kWh</p>'), OFFER).errorCode, 'OFFER_NOT_FOUND');
  assert.equal(extractLucePrice(page('<h2>Octopus Fissa 12M</h2><p>Prezzo in arrivo</p>'), OFFER).errorCode, 'PRICE_NOT_FOUND');
  assert.equal(extractLucePrice(page('<h2>Octopus Fissa 12M</h2><p>F1 0,15 €/kWh F2 0,12 €/kWh</p>'), OFFER).errorCode, 'AMBIGUOUS');
  assert.equal(extractLucePrice(page('<h2>Octopus Fissa 12M</h2><p>PUN + 0,01 €/kWh</p>'), OFFER).errorCode, 'INDEXED_PRICE');
  assert.equal(extractLucePrice(page('<h2>Octopus Fissa 12M</h2><p>16,83 €/kWh</p>'), OFFER).errorCode, 'OUT_OF_RANGE');
  assert.equal(extractLucePrice(page('<h2>Octopus Fissa 12M</h2><p>0,16/kWh</p>'), OFFER).errorCode, 'PRICE_NOT_FOUND');
});

test('formati alternativi dello stesso prezzo', () => {
  for (const body of ['€ 0,1683/kWh', '0,1683 euro/kWh', '16,83 c€/kWh', '0,1683&nbsp;&euro;/kWh']) {
    const r = extractLucePrice(page('<h2>Octopus Fissa 12M</h2><p>' + body + '</p>'), OFFER);
    assert.equal(r.ok, true, body + ' -> ' + JSON.stringify(r));
    assert.equal(Math.round(r.price * 1e4), 1683, body);
  }
});
