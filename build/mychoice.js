/* ============================================================================
   My Choice -- a personal shortlist of funds.

   Stored in localStorage, on this device only. Nothing is sent anywhere and
   nothing is committed to the repository: the site is public, and what someone
   holds or is considering is not.
   ========================================================================== */
const LS_CHOICE = 'riskmatch.mychoice';

function choiceLoad() {
  try {
    var v = JSON.parse(localStorage.getItem(LS_CHOICE) || '[]');
    return Array.isArray(v) ? v : [];
  } catch (e) { return []; }
}

function choiceSave(list) {
  try { localStorage.setItem(LS_CHOICE, JSON.stringify(list)); } catch (e) {}
}

let myChoice = choiceLoad();

function inChoice(sym) { return myChoice.indexOf(sym) >= 0; }

function toggleChoice(sym) {
  if (inChoice(sym)) myChoice = myChoice.filter(function (s) { return s !== sym; });
  else myChoice = myChoice.concat([sym]);
  choiceSave(myChoice);
  updateChoiceCount();
  if (typeof renderBrowse === 'function' && $('browseView').classList.contains('on')) renderBrowse();
  if ($('choiceView') && $('choiceView').classList.contains('on')) renderChoice();
}

function updateChoiceCount() {
  var el = document.querySelector('.nav a[data-view="choice"]');
  if (el) el.textContent = myChoice.length ? 'My Choice (' + myChoice.length + ')' : 'My Choice';
}

function choiceStar(sym) {
  return '<button class="star' + (inChoice(sym) ? ' on' : '') + '" data-star="' + esc(sym) +
    '" title="' + (inChoice(sym) ? 'Remove from My Choice' : 'Add to My Choice') + '">' +
    (inChoice(sym) ? '&#9733;' : '&#9734;') + '</button>';
}

function wireStars(root) {
  (root || document).querySelectorAll('[data-star]').forEach(function (b) {
    b.onclick = function (ev) { ev.stopPropagation(); toggleChoice(b.dataset.star); };
  });
}

/* ------------------------------------------------------------------ view */
function renderChoice() {
  var wrap = $('choiceList');
  var funds = myChoice.map(function (s) {
    return universe.funds.find(function (f) { return f.symbol === s; });
  }).filter(Boolean);

  if (!funds.length) {
    wrap.innerHTML = '<p class="sub" style="padding:18px 0">Nothing saved yet. Open ' +
      '<strong>Browse funds</strong> and use the star beside any fund to add it here. ' +
      'The list is kept in this browser only.</p>';
    $('choiceActions').hidden = true;
    $('choiceStats').innerHTML = '';
    return;
  }
  $('choiceActions').hidden = false;

  // A shortlist is worth summarising: the spread of volatility across it says more about
  // what has been assembled than any single fund's number does.
  var vols = funds.map(function (f) { return f.volDaily; }).filter(function (v) { return v != null; });
  var avg = vols.length ? vols.reduce(function (a, b) { return a + b; }, 0) / vols.length : null;
  var lo = vols.length ? Math.min.apply(null, vols) : null;
  var hi = vols.length ? Math.max.apply(null, vols) : null;
  var dds = funds.map(function (f) { return f.maxDD; }).filter(function (v) { return v != null; });
  var worst = dds.length ? Math.min.apply(null, dds) : null;

  $('choiceStats').innerHTML =
    '<div><span>Funds</span><b>' + funds.length + '</b></div>' +
    (avg == null ? '' :
      '<div><span>Average volatility</span><b>' + avg.toFixed(1) + '%</b></div>' +
      '<div><span>Range</span><b>' + lo.toFixed(1) + '&ndash;' + hi.toFixed(1) + '%</b></div>') +
    (worst == null ? '' :
      '<div><span>Worst drawdown held</span><b>' + worst.toFixed(1) + '%</b></div>');

  function num(v, d) { return v == null ? '<span class="meta">&mdash;</span>' : v.toFixed(d || 1); }
  wrap.innerHTML =
    '<div class="fhead" style="grid-template-columns:1fr 120px 68px 68px 62px 96px 40px">' +
    '<div>Fund</div><div>Manager</div>' +
    '<div class="num">Vol %</div><div class="num">5yr %</div><div class="num">Max DD</div>' +
    '<div class="num">Units held</div><div></div></div>' +
    funds.map(function (f) {
      return '<div class="fundrow" style="grid-template-columns:1fr 120px 68px 68px 62px 96px 40px">' +
        '<div><div class="nm">' + esc(f.name || f.symbol) + '</div><div class="meta">' +
        esc(f.symbol) + (f.years ? ' &middot; ' + f.years + 'y' : '') + '</div></div>' +
        '<div class="meta">' + esc(f.house || '') + '</div>' +
        '<div class="num">' + num(f.volDaily) + '</div>' +
        '<div class="num">' + num(f.r5) + '</div>' +
        '<div class="num">' + num(f.maxDD) + '</div>' +
        '<div><input class="uin" type="number" min="0" step="any" data-units="' +
          esc(f.symbol) + '" value="' + (myUnits[f.symbol] || '') + '" placeholder="0"></div>' +
        '<div>' + choiceStar(f.symbol) + '</div></div>';
    }).join('');
  wireStars(wrap);
  wrap.querySelectorAll('[data-units]').forEach(function (i) {
    i.onchange = function () { setUnits(i.dataset.units, parseFloat(i.value)); };
  });
  if (typeof renderHoldings === 'function') renderHoldings();
}

function choiceToGrowth() {
  var withSeries = myChoice.filter(function (s) { return !SERIES || SERIES[s]; });
  document.querySelector('.nav a[data-view="growth"]').click();
  initGrowth().then(function () {
    var missing = myChoice.filter(function (s) { return !SERIES[s]; });
    gSel = myChoice.filter(function (s) { return SERIES[s]; });
    gRender();
    if (missing.length) {
      $('gWarn').innerHTML = '<div class="warnline"><strong>Not shown: ' +
        missing.map(esc).join(', ') + '.</strong> Too little price history to chart. ' +
        'They are excluded from the totals, so this is not your whole shortlist.</div>' +
        $('gWarn').innerHTML;
    }
  });
}

function choiceClear() {
  if (!myChoice.length) return;
  if (!confirm('Remove all ' + myChoice.length + ' funds from My Choice?')) return;
  myChoice = [];
  choiceSave(myChoice);
  updateChoiceCount();
  renderChoice();
}

function choiceCopy() {
  var txt = myChoice.map(function (s) {
    var f = universe.funds.find(function (x) { return x.symbol === s; }) || {};
    return (f.name || s) + '\t' + s;
  }).join('\n');
  navigator.clipboard.writeText(txt).then(function () {
    var b = $('choiceCopy');
    var t = b.textContent; b.textContent = 'Copied';
    setTimeout(function () { b.textContent = t; }, 1400);
  }, function () {});
}
