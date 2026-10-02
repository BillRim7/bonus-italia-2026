// Macchina a stati dell'avviso. Codice puro: build.js lo incorpora nel nodo Code di n8n,
// dove `state` è $getWorkflowStaticData('global').
//
// status: 'UNKNOWN' (mai letto un prezzo valido) | 'ABOVE' (>= soglia) | 'BELOW' (< soglia)
// Azioni restituite:
//   PRICE_ALERT  -> email di ribasso (solo transizione ABOVE -> BELOW)
//   TECH_ALERT   -> email tecnica (inizio di un errore o cambio del tipo di errore)
//   NONE         -> solo registrazione nel log

function toMicro(n) {
  return Math.round(n * 1e6);
}

function evaluate(state, result, threshold, checkedAt, opts) {
  const o = Object.assign({ alertOnFirstRunIfBelow: false, maxLog: 60 }, opts || {});
  const prev = {
    status: state.status || 'UNKNOWN',
    errorActive: !!state.errorActive,
    lastErrorCode: state.lastErrorCode || null,
  };
  const s = state;
  let action = 'NONE';
  let note;

  if (!result.ok) {
    // Errore: lo stato prezzo NON cambia, così un errore non può né generare né "consumare" un avviso.
    s.consecutiveErrors = (s.consecutiveErrors || 0) + 1;
    if (!prev.errorActive || prev.lastErrorCode !== result.errorCode) action = 'TECH_ALERT';
    s.errorActive = true;
    s.lastErrorCode = result.errorCode;
    s.lastErrorAt = checkedAt;
    note = 'Errore ' + result.errorCode + ' (consecutivi: ' + s.consecutiveErrors + ')';
  } else {
    const below = toMicro(result.price) < toMicro(threshold);
    if (prev.errorActive) note = 'Ripristinato dopo errore ' + prev.lastErrorCode;
    s.errorActive = false;
    s.lastErrorCode = null;
    s.consecutiveErrors = 0;
    s.lastPrice = result.price;
    s.lastPriceAt = checkedAt;

    if (below) {
      if (prev.status === 'ABOVE' || (prev.status === 'UNKNOWN' && o.alertOnFirstRunIfBelow)) {
        action = 'PRICE_ALERT';
        s.lastAlertAt = checkedAt;
        s.lastAlertPrice = result.price;
      } else if (prev.status === 'UNKNOWN') {
        note = (note ? note + '; ' : '') + 'Primo rilevamento già sotto soglia: nessun avviso (nessuna transizione osservata)';
      }
      s.status = 'BELOW';
    } else {
      if (prev.status === 'BELOW') note = (note ? note + '; ' : '') + 'Tornato sopra/uguale soglia: monitoraggio riarmato';
      s.status = 'ABOVE';
    }
  }

  s.lastCheckAt = checkedAt;
  s.log = (s.log || []).concat([{
    at: checkedAt,
    ok: result.ok,
    price: result.ok ? result.price : null,
    errorCode: result.ok ? null : result.errorCode,
    statusBefore: prev.status,
    statusAfter: s.status || 'UNKNOWN',
    action,
  }]).slice(-o.maxLog);

  return { action, statusBefore: prev.status, statusAfter: s.status || 'UNKNOWN', note: note || '' };
}

module.exports = { evaluate };
