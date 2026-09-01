/* ============================================================================
   My Choice, with quantities -- a real holdings valuation.

   Each entry may carry a number of units (shares for a listed instrument, units
   for a fund). Value = units x the last sterling price, which is why every
   series is converted to GBP at build time.

   WHY THE PORTFOLIO VOLATILITY IS COMPUTED, NOT AVERAGED
   A weighted average of each fund's volatility is always too high, because it
   assumes every holding moves together. The real figure comes from building the
   weighted return series and measuring that, which captures the diversification
   the holdings actually gave you. The gap between the two is worth seeing, so
   both are shown.
   ========================================================================== */

const LS_UNITS = 'riskmatch.units';

function unitsLoad() {
  try {
    var v = JSON.parse(localStorage.getItem(LS_UNITS) || '{}');
    return (v && typeof v === 'object') ? v : {};
  } catch (e) { return {}; }
}
function unitsSave(u) {
  try { localStorage.setItem(LS_UNITS, JSON.stringify(u)); } catch (e) {}
}
let myUnits = unitsLoad();

function setUnits(sym, n) {
  if (!n || n <= 0) delete myUnits[sym]; else myUnits[sym] = n;
  unitsSave(myUnits);
  renderChoice();
}

function fundBy(sym) {
  return universe.funds.find(function (f) { return f.symbol === sym; }) || null;
}

function holdingValue(sym) {
  var f = fundBy(sym);
  if (!f || f.last == null || !myUnits[sym]) return null;
  return myUnits[sym] * f.last;
}

/* Portfolio statistics from the actual weighted series, over a chosen window. */
function portfolioStats(symsWithWeights, years) {
  if (!SERIES) return null;
  var syms = Object.keys(symsWithWeights).filter(function (s) { return SERIES[s]; });
  if (!syms.length) return null;

  // Common monthly axis: latest start, earliest end, so every holding is present throughout.
  var start = -Infinity, end = Infinity;
  syms.forEach(function (s) {
    var t = SERIES[s].t;
    start = Math.max(start, t[0]);
    end = Math.min(end, t[t.length - 1]);
  });
  if (years) start = Math.max(start, end - years * 365.25 * 86400);
  if (!(end > start)) return null;

  var axis = SERIES[syms[0]].t.filter(function (t) { return t >= start && t <= end; });
  if (axis.length < 8) return null;

  var series = {};
  syms.forEach(function (s) {
    var S = SERIES[s], j = 0, last = null, px = [];
    for (var i = 0; i < axis.length; i++) {
      while (j < S.t.length && S.t[j] <= axis[i]) { last = S.c[j]; j++; }
      if (last == null) return;
      px.push(last);
    }
    if (px.length === axis.length) series[s] = px;
  });
  var use = Object.keys(series);
  if (!use.length) return null;

  var wTot = use.reduce(function (a, s) { return a + symsWithWeights[s]; }, 0);
  if (!wTot) return null;

  var rets = [], growth = 1, peak = 1, mdd = 0;
  for (var i = 1; i < axis.length; i++) {
    var r = 0;
    use.forEach(function (s) {
      r += (symsWithWeights[s] / wTot) * (series[s][i] / series[s][i - 1] - 1);
    });
    rets.push(r);
    growth *= (1 + r);
    peak = Math.max(peak, growth);
    mdd = Math.min(mdd, growth / peak - 1);
  }
  var n = rets.length;
  var mean = rets.reduce(function (a, b) { return a + b; }, 0) / n;
  var sd = Math.sqrt(rets.reduce(function (a, b) { return a + (b - mean) * (b - mean); }, 0) / (n - 1));
  var yrs = n / 12;

  // The naive figure, shown alongside so the diversification benefit is visible.
  var naive = 0;
  use.forEach(function (s) {
    var f = fundBy(s);
    if (f && f.volDaily != null) naive += (symsWithWeights[s] / wTot) * f.volDaily;
  });

  return {
    vol: sd * Math.sqrt(12) * 100,
    naiveVol: naive,
    maxDD: mdd * 100,
    growth: (growth - 1) * 100,
    cagr: yrs >= 1 ? (Math.pow(growth, 1 / yrs) - 1) * 100 : null,
    years: yrs,
    used: use.length,
    from: axis[0]
  };
}

function renderHoldings() {
  var box = $('choiceHoldings');
  if (!box) return;
  var held = myChoice.filter(function (s) { return myUnits[s] > 0; });
  if (!held.length) {
    box.innerHTML = '<p class="sub">Enter a number of units or shares against any fund above ' +
      'to value the holding and measure the portfolio properly.</p>';
    return;
  }
  var weights = {}, total = 0;
  held.forEach(function (s) {
    var v = holdingValue(s);
    if (v != null) { weights[s] = v; total += v; }
  });
  var st = portfolioStats(weights, null);

  var rows = held.map(function (s) {
    var f = fundBy(s), v = holdingValue(s);
    return '<div class="fundrow" style="grid-template-columns:1fr 110px 110px 90px 70px">' +
      '<div><div class="nm">' + esc(f ? (f.name || s) : s) + '</div>' +
      '<div class="meta">' + esc(s) + '</div></div>' +
      '<div class="num">' + (myUnits[s]).toLocaleString('en-GB') + '</div>' +
      '<div class="num">' + (f && f.last != null ? '&pound;' + f.last.toFixed(4) : '&mdash;') + '</div>' +
      '<div class="num">' + (v == null ? '&mdash;' : '&pound;' + v.toFixed(2)) + '</div>' +
      '<div class="num">' + (total && v != null ? (v / total * 100).toFixed(1) + '%' : '&mdash;') +
      '</div></div>';
  }).join('');

  box.innerHTML =
    '<h3 style="margin:22px 0 8px;font-size:1.05rem">Holdings</h3>' +
    '<div class="gtot">' +
      '<div><span>Total value</span><b>&pound;' + total.toLocaleString('en-GB',
        { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '</b></div>' +
      (st ? '<div><span>Portfolio volatility</span><b>' + st.vol.toFixed(1) + '%</b></div>' +
            '<div><span>If they moved together</span><b>' + st.naiveVol.toFixed(1) + '%</b></div>' +
            '<div><span>Worst fall</span><b>' + st.maxDD.toFixed(1) + '%</b></div>' : '') +
    '</div>' +
    '<div class="fhead" style="grid-template-columns:1fr 110px 110px 90px 70px">' +
    '<div>Holding</div><div class="num">Units</div><div class="num">Price</div>' +
    '<div class="num">Value</div><div class="num">Weight</div></div>' + rows +
    (st ? '<p class="sub" style="margin-top:12px">Measured over ' + st.years.toFixed(1) +
      ' years, the longest window in which all ' + st.used + ' priced holdings existed. ' +
      'Portfolio volatility is computed from the combined series, not averaged &mdash; the ' +
      'gap between it and the "moved together" figure is the diversification your mix ' +
      'actually delivered. Not advice.</p>' : '');
}
