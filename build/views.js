/* ============================================================================
   Browse (A-Z) and Growth calculator.

   Both read the same `universe` object the match view already loads. Growth
   additionally loads series.json lazily -- monthly sterling closes -- so the
   page does not make everyone download several megabytes before anyone has
   asked a growth question.
   ========================================================================== */
let SERIES = null;
let gSel = [];

document.querySelectorAll('.nav a').forEach(function (a) {
  a.addEventListener('click', function (ev) {
    ev.preventDefault();
    document.querySelectorAll('.nav a').forEach(function (x) { x.classList.remove('on'); });
    a.classList.add('on');
    var v = a.dataset.view;
    document.querySelectorAll('.view').forEach(function (x) { x.classList.remove('on'); });
    $(v + 'View').classList.add('on');
    if (v === 'browse') initBrowse();
    if (v === 'growth') initGrowth();
  });
});

/* ---------------------------------------------------------------- browse */
let browseReady = false;

function initBrowse() {
  if (browseReady) return;
  browseReady = true;
  var houses = Array.from(new Set(universe.funds.map(function (f) { return f.house; })
    .filter(Boolean))).sort();
  var sectors = Array.from(new Set(universe.funds.map(function (f) { return f.sector; })
    .filter(Boolean))).sort();
  houses.forEach(function (h) { $('bqHouse').add(new Option(h, h)); });
  sectors.forEach(function (x) { $('bqSector').add(new Option(x, x)); });
  ['bqName', 'bqHouse', 'bqSector', 'bqSort', 'bqYears'].forEach(function (id) {
    $(id).addEventListener('input', renderBrowse);
  });
  renderBrowse();
}

function renderBrowse() {
  var q = $('bqName').value.trim().toLowerCase();
  var h = $('bqHouse').value;
  var sec = $('bqSector').value;
  var minY = parseFloat($('bqYears').value) || 0;
  var sort = $('bqSort').value;

  var rows = universe.funds.filter(function (f) {
    return (!q || (f.name || '').toLowerCase().indexOf(q) >= 0) &&
      (!h || f.house === h) && (!sec || f.sector === sec) && ((f.years || 0) >= minY);
  });

  var desc = sort.charAt(0) === '-';
  var key = desc ? sort.slice(1) : sort;
  rows.sort(function (a, b) {
    if (key === 'name') return (a.name || '').localeCompare(b.name || '');
    var av = a[key], bv = b[key];
    if (av == null) return 1;      // missing data sinks; it must never top a sorted list
    if (bv == null) return -1;
    return desc ? bv - av : av - bv;
  });

  $('bCount').textContent = rows.length + ' of ' + universe.funds.length + ' funds' +
    (minY ? ' with ' + minY + '+ years of history' : '');

  function num(v, d) { return v == null ? '<span class="meta">&mdash;</span>' : v.toFixed(d || 1); }

  var html = '', letter = '';
  rows.forEach(function (f) {
    if (key === 'name') {
      var L = (f.name || '?').charAt(0).toUpperCase();
      if (L !== letter) { letter = L; html += '<div class="azletter">' + esc(L) + '</div>'; }
    }
    html += '<div class="fundrow">' +
      '<div><div class="nm">' + esc(f.name || f.symbol) + '</div><div class="meta">' +
      esc(f.symbol) + (f.years ? ' &middot; ' + f.years + 'y' : '') +
      (f.gbpConverted ? ' &middot; converted to GBP' : '') + '</div></div>' +
      '<div class="meta">' + esc(f.house || '') + '</div>' +
      '<div class="meta">' + esc(f.sector || '') + '</div>' +
      '<div class="num">' + num(f.volDaily) + '</div>' +
      '<div class="num">' + num(f.r5) + '</div>' +
      '<div class="num">' + num(f.maxDD) + '</div></div>';
  });
  $('bList').innerHTML = html ||
    '<p class="sub" style="padding:14px">Nothing matches those filters.</p>';
}

/* ---------------------------------------------------------------- growth */
async function initGrowth() {
  if (SERIES) return;
  $('gTotals').innerHTML = '<div><span>Loading price history</span><b>&hellip;</b></div>';
  try {
    var r = await fetch('series.json', { cache: 'no-cache' });
    SERIES = (await r.json()).series || {};
  } catch (e) {
    SERIES = {};
  }
  $('gTotals').innerHTML = '';
  $('gSearch').addEventListener('input', gSuggest);
  $('gAmount').addEventListener('input', gRender);
  $('gYears').addEventListener('change', gRender);
}

function gSuggest() {
  var q = $('gSearch').value.trim().toLowerCase();
  var box = $('gPick');
  if (q.length < 2) { box.hidden = true; return; }
  var hits = universe.funds.filter(function (f) {
    return SERIES[f.symbol] && (f.name || '').toLowerCase().indexOf(q) >= 0;
  }).slice(0, 40);
  box.innerHTML = hits.map(function (f) {
    return '<div data-sym="' + esc(f.symbol) + '">' + esc(f.name || f.symbol) +
      ' <span class="meta">' + esc(f.symbol) + '</span></div>';
  }).join('') || '<div class="meta" style="padding:8px">No fund with price history matches.</div>';
  box.hidden = false;
  box.querySelectorAll('[data-sym]').forEach(function (el) {
    el.onclick = function () {
      if (gSel.indexOf(el.dataset.sym) < 0) gSel.push(el.dataset.sym);
      $('gSearch').value = '';
      box.hidden = true;
      gRender();
    };
  });
}

function gChips() {
  $('gChips').innerHTML = gSel.map(function (sym) {
    var f = universe.funds.find(function (x) { return x.symbol === sym; }) || { name: sym };
    return '<span class="chip">' + esc(f.name || sym) +
      '<button data-x="' + esc(sym) + '">&times;</button></span>';
  }).join('');
  $('gChips').querySelectorAll('[data-x]').forEach(function (b) {
    b.onclick = function () {
      gSel = gSel.filter(function (s) { return s !== b.dataset.x; });
      gRender();
    };
  });
}

function gRender() {
  gChips();
  var amt = parseFloat($('gAmount').value) || 0;
  var yrs = parseFloat($('gYears').value);
  if (!gSel.length || !amt) {
    $('gTotals').innerHTML = ''; $('gTable').innerHTML = ''; $('gWarn').innerHTML = '';
    return;
  }

  var each = amt / gSel.length;
  var now = Math.floor(Date.now() / 1000);
  var wantFrom = yrs ? now - yrs * 365.25 * 86400 : 0;
  var endTotal = 0, warn = [], rows = '';

  gSel.forEach(function (sym) {
    var s = SERIES[sym];
    var f = universe.funds.find(function (x) { return x.symbol === sym; }) || { name: sym };
    if (!s) return;
    var i = 0;
    while (i < s.t.length - 1 && s.t[i] < wantFrom) i++;
    var startPx = s.c[i], endPx = s.c[s.c.length - 1], startTs = s.t[i];
    var realYears = (s.t[s.t.length - 1] - startTs) / (365.25 * 86400);

    // A fund cannot show a return for years before it existed. Say so rather than
    // quietly reporting a short period as though it answered the question asked.
    if (yrs && realYears < yrs - 0.25) {
      warn.push(esc(f.name || sym) + ' has only ' + realYears.toFixed(1) + ' years');
    }

    var end = each * (endPx / startPx);
    endTotal += end;
    var grow = (endPx / startPx - 1) * 100;
    var cagr = realYears > 0.3 ? (Math.pow(endPx / startPx, 1 / realYears) - 1) * 100 : null;
    var d = new Date(startTs * 1000);

    rows += '<div class="fundrow" style="grid-template-columns:1fr 100px 100px 84px 84px 72px">' +
      '<div><div class="nm">' + esc(f.name || sym) + '</div><div class="meta">from ' +
      d.toISOString().slice(0, 7) + ' &middot; ' + realYears.toFixed(1) + 'y</div></div>' +
      '<div class="num">&pound;' + each.toFixed(2) + '</div>' +
      '<div class="num">&pound;' + end.toFixed(2) + '</div>' +
      '<div class="num">' + grow.toFixed(1) + '%</div>' +
      '<div class="num">' + (cagr == null ? '&mdash;' : cagr.toFixed(1) + '%') + '</div>' +
      '<div class="num">' + (f.volDaily == null ? '&mdash;' : f.volDaily.toFixed(1)) +
      '</div></div>';
  });

  var gain = endTotal - amt;
  var money = function (v) {
    return v.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };
  var col = gain >= 0 ? 'var(--good)' : 'var(--bad)';
  $('gTotals').innerHTML =
    '<div><span>Invested</span><b>&pound;' + money(amt) + '</b></div>' +
    '<div><span>Would be worth</span><b>&pound;' + money(endTotal) + '</b></div>' +
    '<div><span>Gain</span><b style="color:' + col + '">' + (gain >= 0 ? '+' : '') +
    '&pound;' + money(gain) + '</b></div>' +
    '<div><span>Return</span><b style="color:' + col + '">' + (gain >= 0 ? '+' : '') +
    (gain / amt * 100).toFixed(1) + '%</b></div>';

  $('gWarn').innerHTML = warn.length
    ? '<div class="warnline"><strong>Shorter history than you asked for.</strong> ' +
      warn.join('; ') + '. The total mixes periods of different lengths, so it is not a ' +
      'like-for-like comparison.</div>'
    : '';

  $('gTable').innerHTML =
    '<div class="fhead" style="grid-template-columns:1fr 100px 100px 84px 84px 72px">' +
    '<div>Fund</div><div class="num">In</div><div class="num">Out</div>' +
    '<div class="num">Total</div><div class="num">A year</div><div class="num">Vol %</div></div>' +
    rows +
    '<p class="sub" style="margin-top:12px">Split equally across the funds chosen and held ' +
    'throughout, in sterling. Survivorship bias applies: only funds that still exist can be ' +
    'shown, so any long-run figure here is flattering to the industry. Past performance is not ' +
    'a guide to future returns, and nothing here is advice.</p>';
}
