/*
 * Risk Match -- load the page in a DOM, click through every view, and report whether each
 * one actually rendered rows.
 *
 * WHY THIS EXISTS. pack.py copies a fixed list of fields, so any field the front end needs
 * that the pipeline stops producing simply vanishes -- and nothing fails, because
 * `undefined >= 8` is merely false. That is how the Match-by-risk band filter returned zero
 * funds for weeks after a rebuild while every other view looked perfect. "It built" is not
 * evidence that the site still works; this is.
 *
 * Run it after any rebuild, and after any edit to index.html:
 *     npm install jsdom          (once, anywhere on the path)
 *     node build/smoke.js
 *
 * It reads funds.json and series.json straight off disk, so it needs no server and no network.
 */
const fs = require('fs');
const path = require('path');
const { JSDOM, VirtualConsole } = require('jsdom');

const ROOT = path.resolve(__dirname, '..');
const errors = [];
const vc = new VirtualConsole();
vc.on('jsdomError', e => errors.push('jsdomError: ' + (e.message || e)));
vc.on('error', (...a) => errors.push('console.error: ' + a.join(' ')));

const dom = new JSDOM(fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8'), {
  runScripts: 'dangerously',
  pretendToBeVisual: true,
  url: 'http://localhost/',
  virtualConsole: vc,
  beforeParse(win) {
    win.fetch = (url) => Promise.resolve({
      ok: true,
      json: () => Promise.resolve(JSON.parse(
        fs.readFileSync(path.join(ROOT, String(url).split('?')[0]), 'utf8'))),
    });
    win.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
    win.open = (u) => { errors.push('opened a new tab: ' + u); return null; };
  },
});

const win = dom.window, doc = win.document;
const wait = ms => new Promise(r => setTimeout(r, ms));
const click = el => el.dispatchEvent(new win.MouseEvent('click', { bubbles: true, cancelable: true }));
const fire = (el, ev) => el.dispatchEvent(new win.Event(ev, { bubbles: true }));
const n = (sel, within) => (within || doc).querySelectorAll(sel).length;

let failures = 0;
function check(label, ok, detail) {
  if (!ok) failures++;
  console.log((ok ? '  ok   ' : '  FAIL ') + label + (detail == null ? '' : '  ' + detail));
}

(async () => {
  await wait(1500);
  console.log('\nDATA');
  const funds = JSON.parse(fs.readFileSync(path.join(ROOT, 'funds.json'), 'utf8'));
  check('funds.json loaded', funds.funds.length > 0, funds.funds.length + ' funds');

  console.log('\nEVERY VIEW RENDERS');
  for (const t of ['match', 'browse', 'shares', 'analysis', 'choice', 'growth', 'factsheet']) {
    click(doc.querySelector('.nav a[data-view="' + t + '"]'));
    await wait(700);
    const v = doc.getElementById(t + 'View');
    check(t + ' opens', v.classList.contains('on'));
  }

  console.log('\nMATCH BY RISK RETURNS ROWS AT EVERY LEVEL');
  click(doc.querySelector('.nav a[data-view="match"]'));
  for (const lvl of ['1', '3', '5', '8', '10']) {
    doc.getElementById('riskInput').value = lvl;
    fire(doc.getElementById('riskInput'), 'input');
    click(doc.getElementById('matchBtn'));
    await wait(200);
    const rows = n('tbody tr', doc.getElementById('results'));
    check('risk ' + lvl, rows > 0, rows + ' funds');
  }

  console.log('\nBROWSE');
  click(doc.querySelector('.nav a[data-view="browse"]'));
  await wait(600);
  check('list renders', n('#bList .fundrow') > 0, n('#bList .fundrow') + ' rows');
  const boxes = () => Array.from(doc.querySelectorAll('#bList [data-pick]'));
  const modal = doc.getElementById('fundModal');
  check('dialog starts hidden', modal.hidden === true);

  const b0 = boxes()[0];
  b0.checked = true; fire(b0, 'change');
  await wait(200);
  check('ticking a fund opens the dialog', !modal.hidden,
        '"' + (doc.getElementById('fmTitle').textContent || '').slice(0, 34) + '"');
  check('dialog shows the measurements', n('#fmFigs div') === 6);
  check('dialog offers actions', n('#fmActs button') >= 4);
  check('dialog names the risk bands', /risk \d/.test(doc.getElementById('fmBand').textContent));
  check('focus moves into the dialog',
        modal.contains(doc.activeElement) && doc.activeElement.tagName === 'BUTTON');

  click(modal.querySelector('[data-act="keep"]'));
  await wait(150);
  check('Keep closes it and leaves the tick', modal.hidden && boxes()[0].checked);

  const all = doc.getElementById('bAll');
  all.checked = true; fire(all, 'change');
  await wait(300);
  check('select-all does NOT open it', modal.hidden);
  all.checked = false; fire(all, 'change');
  await wait(200);

  const b1 = boxes()[1];
  b1.checked = true; fire(b1, 'change');
  await wait(200);
  click(modal.querySelector('[data-act="untick"]'));
  await wait(200);
  check('Untick closes it and clears the tick', modal.hidden && !boxes()[1].checked);

  const b2 = boxes()[2];
  b2.checked = true; fire(b2, 'change');
  await wait(200);
  doc.dispatchEvent(new win.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  await wait(150);
  check('Escape closes it and leaves the tick', modal.hidden && boxes()[2].checked);

  console.log('\nBROWSE COLUMN ORDER');
  // The sort arrow is an empty <i> inside the heading, so textContent picks up a stray "i".
  const heads = Array.from(doc.querySelectorAll('#bTable .fhead .num'))
                     .map(h => ({ t: h.firstChild.textContent.trim(),
                                  xf: h.classList.contains('xf') }));
  const visible = heads.filter(h => !h.xf).map(h => h.t);
  check('return comes before volatility',
        visible[0] === '5yr return' && visible[1] === 'Volatility', visible.join(' | '));
  check('Sortino is not in the default view', heads.some(h => h.t === 'Sortino' && h.xf));
  check('Max fall is not in the default view', heads.some(h => h.t === 'Max fall' && h.xf));
  const firstRow = doc.querySelector('#bList .fundrow');
  const cells = Array.from(firstRow.querySelectorAll('.num'))
                     .filter(c => !c.classList.contains('xf'));
  check('cells line up with headings', cells.length === visible.length,
        cells.length + ' cells, ' + visible.length + ' headings');

  console.log('\nCLIENT');
  click(doc.querySelector('.nav a[data-view="client"]'));
  await wait(600);
  check('questionnaire renders', n('#cQuestions .q') === 13, n('#cQuestions .q') + ' questions');
  check('every question has its options', n('#cQuestions input[type=radio]') === 45,
        n('#cQuestions input[type=radio]') + ' options');
  // Answer every item at its most cautious, then its boldest. 13 and 47 are the arithmetic
  // limits of the published scale, so any other total means the scoring is wrong.
  // Item 1 scores in REVERSE -- "a real gambler" is the first option and scores 4 -- so the
  // cautious answer there is the last option, not the first. Assuming otherwise makes a
  // correct implementation look broken by exactly 3 points at each end.
  const REVERSED = new Set([0]);
  for (const bold of [false, true]) {
    for (let i = 0; i < 13; i++) {
      const rs = Array.from(doc.querySelectorAll('input[name="gl' + i + '"]'));
      const last = REVERSED.has(i) ? !bold : bold;
      const r = last ? rs[rs.length - 1] : rs[0];
      r.checked = true; fire(r, 'change');
    }
    await wait(250);
    const score = doc.getElementById('cScore').textContent;
    const band = doc.getElementById('cBand').textContent;
    check((bold ? 'boldest' : 'most cautious') + ' answers total ' + (bold ? 47 : 13),
          score === (bold ? '47' : '13'), score + ' - ' + band);
  }
  for (const [id, v] of [['cLevel', '5'], ['cCapacity', '10'], ['cTerm', '2']]) {
    const el = doc.getElementById(id);
    el.value = v; fire(el, 'input');
  }
  await wait(300);
  check('checks fire against the fund data', n('#cFlags .flagline') >= 2,
        n('#cFlags .flagline') + ' flags');
  check('a check quotes measured drawdown',
        /median maximum drawdown/.test(doc.getElementById('cFlags').textContent));
  click(doc.getElementById('cToMatch'));
  await wait(400);
  check('the risk level carries into Match by risk',
        doc.getElementById('matchView').classList.contains('on') &&
        doc.getElementById('riskInput').value === '5');

  console.log('\nANALYSIS -- every panel, then every control');
  click(doc.querySelector('.nav a[data-view="analysis"]'));
  await wait(1500);
  check('rankings', n('#anTop .fundrow') > 0, n('#anTop .fundrow') + ' rows');
  check('breakdown', n('#anGroups .fundrow') > 0, n('#anGroups .fundrow') + ' groups');
  check('risk-band census', n('#anBands .fundrow') === 10);
  check('scatter', n('#anScatter circle') > 0, n('#anScatter circle') + ' points');
  check('stress table', n('#anStress .fundrow') > 0, n('#anStress .fundrow') + ' groups');

  async function sweep(id, values) {
    const el = doc.getElementById(id);
    const before = el.value;
    for (const v of values) {
      el.value = v; fire(el, 'input');
      await wait(160);
      check(id + ' = ' + (v === '' ? '(any)' : v),
            n('#anTop .fundrow') + n('#anGroups .fundrow') + n('#anBands .fundrow') > 0);
    }
    el.value = before; fire(el, 'input');
    await wait(160);
  }
  await sweep('anMetric', ['r5', 'r3', 'r1', 'cagr', 'sharpe', 'sortino', 'volDaily',
                           'volWeekly', 'maxDD', 'worst12m', 'beta', 'corr', 'years']);
  await sweep('anDir', ['lo', 'hi']);
  await sweep('anCount', ['25', '50', '10']);
  await sweep('anGroup', ['sector', 'region', 'house', 'type', 'vol', 'hist', 'cur']);
  await sweep('anGroupSort', ['n', 'volDaily', 'r5', 'maxDD', 'sharpe', 'name']);
  await sweep('anGroupMin', ['1', '3', '10']);
  await sweep('anWhat', ['funds', 'shares', '']);
  await sweep('anMinYears', ['0', '3', '10', '5']);
  await sweep('anLev', ['1', '0']);
  await sweep('anCur', ['gbp', 'conv', '']);
  await sweep('anBandBasis', ['volWeekly', 'volDaily']);
  await sweep('anX', ['volDaily', 'maxDD', 'beta']);
  await sweep('anY', ['r5', 'cagr', 'sharpe']);
  await sweep('anStressBy', ['sector', 'region', 'house', 'type', 'vol']);

  console.log('\nSCRIPT ERRORS');
  if (errors.length) { errors.slice(0, 12).forEach(e => console.log('  ' + e)); failures += errors.length; }
  else console.log('  none');

  console.log('\n' + (failures ? failures + ' PROBLEM(S)' : 'all checks passed'));
  process.exit(failures ? 1 : 0);
})();
