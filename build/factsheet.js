/* ============================================================================
   Portfolio factsheet.

   Builds a printable analysis of the holdings in My Choice: valuation, measured
   risk, allocation, concentration and growth. Everything is computed in the
   browser from the sterling price series, so every figure traces back to a
   price history rather than a stored result.

   It deliberately reads like a factsheet and deliberately does not rate,
   score or recommend the portfolio. It reports what the mix did.
   ========================================================================== */

function fsWindowSeries(weights) {
  /* Weighted monthly series over the longest window in which every priced
     holding existed. Returns {axis, values, used, missing}. */
  var syms = Object.keys(weights).filter(function (s) { return SERIES && SERIES[s]; });
  var missing = Object.keys(weights).filter(function (s) { return !SERIES || !SERIES[s]; });
  if (!syms.length) return null;

  var start = -Infinity, end = Infinity;
  syms.forEach(function (s) {
    var t = SERIES[s].t;
    start = Math.max(start, t[0]);
    end = Math.min(end, t[t.length - 1]);
  });
  if (!(end > start)) return null;

  var axis = SERIES[syms[0]].t.filter(function (t) { return t >= start && t <= end; });
  if (axis.length < 6) return null;

  var px = {};
  syms.forEach(function (s) {
    var S = SERIES[s], j = 0, last = null, arr = [];
    for (var i = 0; i < axis.length; i++) {
      while (j < S.t.length && S.t[j] <= axis[i]) { last = S.c[j]; j++; }
      if (last == null) return;
      arr.push(last);
    }
    if (arr.length === axis.length) px[s] = arr;
  });
  var use = Object.keys(px);
  if (!use.length) return null;

  var wTot = use.reduce(function (a, s) { return a + weights[s]; }, 0);
  var vals = [1];
  for (var i = 1; i < axis.length; i++) {
    var r = 0;
    use.forEach(function (s) { r += (weights[s] / wTot) * (px[s][i] / px[s][i - 1] - 1); });
    vals.push(vals[vals.length - 1] * (1 + r));
  }
  return { axis: axis, values: vals, used: use, missing: missing };
}

function fsSparkline(axis, values, w, h) {
  var lo = Math.min.apply(null, values), hi = Math.max.apply(null, values);
  var pad = (hi - lo) * 0.08 || 0.01;
  lo -= pad; hi += pad;
  var pts = values.map(function (v, i) {
    var x = (i / (values.length - 1)) * (w - 44) + 38;
    var y = h - 18 - ((v - lo) / (hi - lo)) * (h - 34);
    return x.toFixed(1) + ',' + y.toFixed(1);
  });
  var d0 = new Date(axis[0] * 1000).toISOString().slice(0, 7);
  var d1 = new Date(axis[axis.length - 1] * 1000).toISOString().slice(0, 7);
  var base = (h - 18 - ((1 - lo) / (hi - lo)) * (h - 34)).toFixed(1);
  return '<svg viewBox="0 0 ' + w + ' ' + h + '" width="100%" height="' + h + '" role="img" ' +
    'aria-label="Growth of the portfolio">' +
    '<line x1="38" y1="' + base + '" x2="' + (w - 6) + '" y2="' + base +
      '" stroke="var(--line)" stroke-dasharray="3 3"/>' +
    '<polyline fill="none" stroke="var(--navy)" stroke-width="2" points="' + pts.join(' ') + '"/>' +
    '<text x="0" y="12" font-size="10" fill="var(--muted)">' + hi.toFixed(2) + '&times;</text>' +
    '<text x="0" y="' + (h - 4) + '" font-size="10" fill="var(--muted)">' + lo.toFixed(2) + '&times;</text>' +
    '<text x="38" y="' + (h - 4) + '" font-size="10" fill="var(--muted)">' + d0 + '</text>' +
    '<text x="' + (w - 6) + '" y="' + (h - 4) + '" font-size="10" text-anchor="end" ' +
      'fill="var(--muted)">' + d1 + '</text>' +
    '</svg>';
}

function fsBars(rows, total) {
  return rows.map(function (r) {
    var pc = total ? (r[1] / total * 100) : 0;
    return '<div class="fsbar"><div class="fsbar-l">' + esc(r[0]) + '</div>' +
      '<div class="fsbar-t"><i style="width:' + pc.toFixed(1) + '%"></i></div>' +
      '<div class="fsbar-v">' + pc.toFixed(1) + '%</div></div>';
  }).join('');
}

function renderFactsheet() {
  var box = $('fsBody');
  var held = myChoice.filter(function (s) { return myUnits[s] > 0; });
  if (!held.length) {
    box.innerHTML = '<p class="sub">No holdings yet. Star funds in <strong>Browse funds</strong>, ' +
      'then enter the units you hold in <strong>My Choice</strong>.</p>';
    return;
  }

  var weights = {}, total = 0, rows = [];
  held.forEach(function (s) {
    var f = fundBy(s);
    var v = (f && f.last != null) ? myUnits[s] * f.last : null;
    if (v != null) { weights[s] = v; total += v; }
    rows.push({ f: f, sym: s, units: myUnits[s], value: v });
  });
  rows.sort(function (a, b) { return (b.value || 0) - (a.value || 0); });

  var ser = fsWindowSeries(weights);
  var stats = null;
  if (ser) {
    var vals = ser.values;
    var rets = [];
    for (var i = 1; i < vals.length; i++) rets.push(vals[i] / vals[i - 1] - 1);
    var n = rets.length;
    var mean = rets.reduce(function (a, b) { return a + b; }, 0) / n;
    var sd = Math.sqrt(rets.reduce(function (a, b) { return a + (b - mean) * (b - mean); }, 0) / (n - 1));
    var peak = 1, mdd = 0;
    vals.forEach(function (v) { peak = Math.max(peak, v); mdd = Math.min(mdd, v / peak - 1); });
    var yrs = n / 12;
    stats = {
      vol: sd * Math.sqrt(12) * 100,
      maxDD: mdd * 100,
      growth: (vals[vals.length - 1] - 1) * 100,
      cagr: yrs >= 1 ? (Math.pow(vals[vals.length - 1], 1 / yrs) - 1) * 100 : null,
      years: yrs
    };
    // The comparison that matters: what a weighted average would have claimed.
    var naive = 0;
    Object.keys(weights).forEach(function (s) {
      var f = fundBy(s);
      if (f && f.volDaily != null) naive += (weights[s] / total) * f.volDaily;
    });
    stats.naive = naive;
  }

  var bySector = {}, byHouse = {};
  rows.forEach(function (r) {
    if (r.value == null || !r.f) return;
    var sec = r.f.sector || 'Unclassified', h = r.f.house || 'Unknown';
    bySector[sec] = (bySector[sec] || 0) + r.value;
    byHouse[h] = (byHouse[h] || 0) + r.value;
  });
  var secRows = Object.keys(bySector).map(function (k) { return [k, bySector[k]]; })
    .sort(function (a, b) { return b[1] - a[1]; });
  var houseRows = Object.keys(byHouse).map(function (k) { return [k, byHouse[k]]; })
    .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 8);

  var biggest = rows[0];
  var conc = (biggest && biggest.value != null && total) ? biggest.value / total * 100 : 0;

  var money = function (v) {
    return v.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  box.innerHTML =
    '<div class="fshead">' +
      '<div><span>Total value</span><b>&pound;' + money(total) + '</b></div>' +
      '<div><span>Holdings</span><b>' + rows.length + '</b></div>' +
      (stats ? '<div><span>Volatility</span><b>' + stats.vol.toFixed(1) + '%</b></div>' +
               '<div><span>Worst fall</span><b>' + stats.maxDD.toFixed(1) + '%</b></div>' +
               (stats.cagr != null ? '<div><span>Return a year</span><b>' +
                  stats.cagr.toFixed(1) + '%</b></div>' : '') : '') +
    '</div>' +

    (conc > 25 ? '<div class="warnline"><strong>Concentrated.</strong> ' +
      esc(biggest.f ? (biggest.f.name || biggest.sym) : biggest.sym) + ' is ' +
      conc.toFixed(0) + '% of the portfolio. The measured risk below is largely that ' +
      'one holding&rsquo;s risk.</div>' : '') +

    (ser ? '<h3 class="fsh">Growth of the mix</h3>' +
      '<p class="sub">Rebased to 1.00 at the start of the longest window in which every ' +
      'priced holding existed (' + stats.years.toFixed(1) + ' years). Total ' +
      (stats.growth >= 0 ? '+' : '') + stats.growth.toFixed(1) + '%.</p>' +
      fsSparkline(ser.axis, ser.values, 760, 150) : '') +

    '<h3 class="fsh">Holdings</h3>' +
    '<div class="fhead" style="grid-template-columns:1fr 90px 90px 100px 70px 64px 66px">' +
    '<div>Holding</div><div class="num">Units</div><div class="num">Price</div>' +
    '<div class="num">Value</div><div class="num">Weight</div><div class="num">Vol %</div>' +
    '<div class="num">Max DD</div></div>' +
    rows.map(function (r) {
      var f = r.f || {};
      return '<div class="fundrow" style="grid-template-columns:1fr 90px 90px 100px 70px 64px 66px">' +
        '<div><div class="nm">' + esc(f.name || r.sym) + '</div><div class="meta">' +
        esc(r.sym) + (f.sector ? ' &middot; ' + esc(f.sector) : '') + '</div></div>' +
        '<div class="num">' + r.units.toLocaleString('en-GB') + '</div>' +
        '<div class="num">' + (f.last != null ? '&pound;' + f.last.toFixed(4) : '&mdash;') + '</div>' +
        '<div class="num">' + (r.value == null ? '&mdash;' : '&pound;' + money(r.value)) + '</div>' +
        '<div class="num">' + (r.value != null && total ? (r.value / total * 100).toFixed(1) + '%' : '&mdash;') + '</div>' +
        '<div class="num">' + (f.volDaily != null ? f.volDaily.toFixed(1) : '&mdash;') + '</div>' +
        '<div class="num">' + (f.maxDD != null ? f.maxDD.toFixed(1) : '&mdash;') + '</div></div>';
    }).join('') +

    '<div class="fscols">' +
      '<div><h3 class="fsh">By sector</h3>' + fsBars(secRows, total) + '</div>' +
      '<div><h3 class="fsh">By manager</h3>' + fsBars(houseRows, total) + '</div>' +
    '</div>' +

    (stats ? '<h3 class="fsh">What the diversification was worth</h3>' +
      '<p class="sub">A weighted average of the holdings&rsquo; own volatilities would put this ' +
      'portfolio at <strong>' + stats.naive.toFixed(1) + '%</strong>. Measured from the ' +
      'combined series it is <strong>' + stats.vol.toFixed(1) + '%</strong>. ' +
      (stats.naive > stats.vol
        ? 'The difference is the diversification the mix actually delivered &mdash; the holdings ' +
          'did not all move together.'
        : 'There is no benefit visible here, which happens when one holding dominates or the ' +
          'holdings move closely together.') + '</p>' : '') +

    '<h3 class="fsh">How these figures were produced</h3>' +
    '<ul class="fsnote">' +
      '<li>Every price series is converted to sterling before measurement, so currency ' +
      'movement is included where a holding is priced abroad.</li>' +
      '<li>Volatility and drawdown are computed from the combined monthly series over the ' +
      'window shown, not averaged across holdings.</li>' +
      '<li>Values use the latest available price and the units entered. Nothing is verified ' +
      'against a custodian or platform statement.</li>' +
      (ser && ser.missing.length ? '<li><strong>Excluded for want of price history: ' +
        ser.missing.map(esc).join(', ') + '.</strong> The figures above are not the whole ' +
        'portfolio.</li>' : '') +
      '<li>Past performance is not a guide to future returns.</li>' +
      '<li>This is a measurement of a portfolio you entered. It is not advice, not a ' +
      'recommendation, and not a suitability assessment.</li>' +
    '</ul>';
}
