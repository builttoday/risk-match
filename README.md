# Risk Match

Type the risk score your attitude-to-risk questionnaire produced, and see every fund whose
**measured** volatility falls inside the band your firm associates with that level. Browse the
whole universe A–Z, or work out what a sum invested in chosen funds would have grown to.

Live: https://builttoday.github.io/risk-match/

## What it does and does not do

The adviser supplies the framework; the tool supplies the measurement. It shows what a fund's
volatility, drawdown and returns actually were. It does not rate funds, rank them for
suitability, or recommend anything — suitability remains the adviser's judgement.

Set your own volatility bands in "Set what each risk level means for your firm". The defaults
are starting points, not anyone's house view.

## The views

**Client** — the fact find, and a risk-tolerance questionnaire. Term, objective, withdrawals,
capacity for loss, knowledge, emergency fund, and the risk level your firm assessed. The
questionnaire is **Grable & Lytton's 13-item Financial Risk Tolerance Scale**, published in
*Financial Services Review* in 1999 and used in hundreds of studies since — reproduced
verbatim, dollar amounts and all, because its score bands were calibrated on those exact
questions and a reworded scale is no longer the scale that was validated. The licensed
questionnaires advisers actually use (Defaqto's, Dynamic Planner's, FinaMetrica's) cannot be
reproduced here, and inventing thirteen plausible-sounding questions instead would be worse
than either: an unvalidated scale wearing a validated one's clothes.

The score measures **willingness** to take risk. It says nothing about capacity, term, or what
your firm's level 5 means, so the tool will not map it onto a 1–10 scale for you — the fact
find asks for that level instead. What it does do is check what you recorded against what the
fund data measures: how far funds in your band for that level have actually fallen, against the
capacity for loss on file. Everything stays in `localStorage` on that device; nothing is
transmitted, and nothing reaches this repository, which is public.

**Match by risk** — funds whose measured volatility sits inside your band for a risk level.
Leveraged and inverse products are excluded unless you ask for them: their volatility is a
real figure, but it describes a daily-rebalancing trading instrument rather than a holding.

**Browse funds** — all 980, A–Z, filtered by fund manager, sector, minimum history, and
sorted by clicking any column header. **Five-year return comes first, then volatility**, with
Sharpe, beta and the worst twelve months beside them; **Show all figures** adds weekly
volatility, the one- and three-year returns, maximum fall, Sortino, correlation and growth a
year. Six numbers read; twelve are a spreadsheet. Select rows to send them straight to the
growth calculator or My Choice, and each row links to a factsheet search and its price
history.

Ticking a fund opens a dialog in the middle of the screen and asks what it is for, rather than
guessing. A tick on its own is ambiguous — compare this, keep this, or just look at this
— so the dialog names the fund, shows its measurements, says which of your own risk bands
its volatility falls in, and offers the growth calculator, My Choice, its factsheet and its
price history. The tick survives Escape and a click outside, so a mis-click never quietly
empties a selection someone has been building up. Select-all does not open it.

**Growth calculator** — pick funds, set an amount, choose a rolling period or a specific start
date, and see what it would have become. **Amount and start date are editable per fund**, so a
holding bought last spring is not measured over the same five years as one held since 2015; the
date box shows the date actually used, which is the first price on or after the one asked for,
so a start before the fund existed is visible rather than silent. The mix can be sent straight
to the factsheet. Computed in the browser from the price series, so any
figure can be traced back to a price history. A scenario is linkable:
`?g=SYM,SYM&amt=1000&from=2026-01-01#growth`.

**Shares** — the 92 FTSE 100 constituents the tool holds, measured exactly as the funds are,
with an ICB industry from a dated hand-written map rather than guessed from the company name.
Kept apart from the funds on purpose: a single company carries the risk of one business, not
of a market, and one combined list invites a comparison that should not be made. The S&P 500
appears instead as a **sector** in Browse funds, holding its tracker share classes — the form
a UK investor can actually own it in.

**Analysis** — five panels over one shared pool of funds, described at the top of the page
and reported back as a count, so no two tables here can quietly be measured over different
universes. Narrow that pool by what it is, minimum history, manager, sector, currency risk and
whether leveraged products are included.

- **Rankings** — thirteen measures, either end first, ten to fifty rows. The order box says
  "highest" and "lowest" rather than "best" and "worst", because beta and correlation have no
  good end.
- **Break the universe down** — by sector, region, manager, what it is, volatility range,
  length of history or currency, ordered by any of the medians, with small groups filtered out.
- **Your risk levels** — how many funds each of *your* bands actually contains, measured
  against daily or weekly volatility. A level with two funds in it is a band worth re-reading
  before a client is placed in it.
- **Does one measure move with another?** — any two measures plotted against each other with
  Pearson and Spearman recomputed live over whatever pool is set. Where the two disagree the
  relationship is a curve, which is the whole point of showing both.
- **The episodes that mattered** — median total return through the Covid crash and recovery,
  the 2022 sell-off, the gilt crisis, the rally to end-2024 and 2025 so far, from month-end
  prices. Each cell carries the number of funds that have prices covering the whole window:
  a group whose funds mostly launched after 2020 shows a small count for the Covid columns, and
  the median of four survivors is not what that sector went through at the time.

Every figure is computed in the browser from the same data the rest of the tool uses, so no
ranking can go stale against the numbers beside it. The controlled 60-month correlation study
stays at the foot of the page, unchanged: the live scatter answers the same question over any
subset, but a subset the reader chose is not a controlled window.

**My Choice** — star any fund to build a personal shortlist, and enter the units you hold to
value it. **Each fund carries its own measurement period** — six months for one bought in the
spring, two years for another — and its return, volatility and drawdown are recomputed over
that period from the price series rather than read off a stored five-year figure. Stored in `localStorage` on your own device: nothing is sent anywhere and nothing is
committed to this repository, because the site is public and what someone holds is not.

**Factsheet** — a printable analysis of the holdings you entered: valuation, measured
volatility and drawdown, growth of the mix, allocation by sector and by manager, and an
automatic warning when one holding dominates.

Portfolio volatility is **computed from the combined weighted series, not averaged across
holdings**. A weighted average always overstates risk because it assumes everything moves
together; the factsheet shows both figures so the diversification actually delivered is
visible.

## Every column explains itself

Each column heading carries an (i). A heading is a two-word abbreviation of a statistical
decision, and an adviser reading "Sortino 0.42" cannot act on it without knowing what went in
— above all the risk-free rate, without which neither Sharpe nor Sortino means anything. A
`title` attribute will not do this job: it never appears on a phone, and it cannot be reached
by keyboard. The definitions answer hover, focus and tap alike.

Two columns were also **mislabelled**: the three- and five-year returns are cumulative, and
were headed "p.a.". A fund that grew 39% in total across three years was being shown as having
grown 39% a year. They now read "3yr total" and "5yr total".

## The numbers

Two volatility figures are shown, deliberately:

- **Daily** — standard deviation of daily returns × √252.
- **Weekly** — standard deviation of weekly returns × √52. This is the SRRI convention used on
  every UCITS KIID, and therefore the number a firm's risk bands were most likely calibrated
  against. Showing both stops a fund looking like a 5 here and a 4 on its own factsheet with no
  explanation.

Also computed: maximum drawdown, CAGR, Sharpe and Sortino (against a stated 4% risk-free rate,
because neither means anything without one), beta and correlation to a global GBP benchmark,
worst rolling twelve months, and 1/3/5-year returns.

**Beta and correlation use the same 60 monthly returns for every fund**, against VWRP.L. That
is the factsheet convention, and a single shared window is what makes two funds' betas
comparable — a fund measured over its own longest history is not being measured against the
same market. A fund without 36 months inside that window shows a dash rather than a figure
nobody else's is comparable to. The benchmark's own beta and correlation come out at exactly
1.00, which is the check that the calculation is wired up correctly.

Pairing a fund with the benchmark by *exact timestamp* does not work: Yahoo stamps an
LSE-listed ETF and an OEIC share class at different times of day, so the intersection is
usually empty. That silently left 63% of the universe with no beta at all — and a missing beta
looks exactly like a fund with too little history. Match on calendar month instead.

This is **realised** risk, looking backwards. Risk-profiling services publish forward-looking
expected volatility from a capital markets model — a different measure that will not agree with
these figures. Past volatility is not a promise about future volatility.

## Everything is in sterling

A global manager's share class may be priced in USD, EUR or CHF. Each price series is converted
to GBP with a matching daily FX series **before** any statistic is computed, because for a UK
investor the volatility that matters includes the currency move, not the local-currency figure
on the factsheet. Funds that required conversion are marked, since their sterling volatility
carries currency risk a hedged share class would not.

London quotes most instruments in **pence**, which Yahoo reports as currency `GBp`. Note that
`"GBp".upper() == "GBP"`, so any code that uppercases before testing will silently price 108
LSE instruments a hundred times too high — and because volatility and returns are ratios, the
error stays invisible until a holding is valued.

## Coverage

980 share classes and instruments, up to 25 years of history — median 8.7 years, with 456 funds
having ten years or more and 219 having twenty. Not the whole market: there is no free way to
enumerate every UK fund. The FCA Register API returns at most 20 rows per search with no working
pagination, and its bulk extract is a paid service.

Some funds are simply absent from the public price source — BlackRock Consensus 100, for one,
under any of three ISINs and five name forms. Full coverage needs a commercial data licence
(FE fundinfo, Morningstar, or a cheaper feed such as EODHD).

**Trustnet is FE fundinfo's own retail site**, so the factsheets this tool links to and the
paid feed that would fix the coverage gap come from the same company. Registering with
Trustnet is free and gives a person full factsheet access in a browser — it does not provide
an API, a bulk export, or a licence, and scraping the site to get one would breach its terms.
The two are worth keeping distinct: a login solves *looking a fund up*, and only a data
licence solves *holding the data*.

Trustnet has no public search URL to link to — its search is built client-side, and
`/search?q=`, `/fund/search?keywords=` and `/factsheets/search?q=` all return 404 or 500. So
the factsheet link is a site-scoped web search instead, which lands on the right share class
in one hop.

**Searching by ISIN works far better than by name.** A fund that returns nothing for nine name
variations resolves immediately from its ISIN.

### Adding a fund that the sweep missed

`build/discover.py` finds funds by sweeping a list of fund-house names, so a smaller manager
whose name is not on that list is simply absent. `build/add.py` prices one named share class
and merges it in — `python add.py GB00BNM3D752` — without refetching the other thousand. It
imports fetch.py's own `chart`/`to_gbp`/`stats` rather than reimplementing them, so an added
fund is measured by exactly the same calculation as the rest of the universe; a second
implementation that drifted by a rounding rule would put a fund in the wrong band, which is
the one thing this tool must not do. Follow it with `classify.py`, `fca.py`, `pack.py`,
`beta.py`, all of which are whole-file and cheap.

Note that `fetch.py` matches the benchmark by exact timestamp when it computes beta, and Yahoo
stamps an OEIC and an LSE ETF at different times of day, so the beta on a newly added OEIC is
wrong until `beta.py` recomputes it on a shared monthly window. Added this way, the two IFSL
Rockhold funds first showed betas of 0.35 and 0.02; the real figures are 0.75 and 0.19.

### Model portfolios are not funds, and cannot be measured here

A discretionary manager's MPS ranges are published as factsheets but are not priced
instruments: no ISIN, no daily price, nothing for this tool to measure. Their factsheets carry
the manager's own risk figures, computed by a licensed data provider, and typically say the
document is for the recipient it was delivered to and should not be reproduced — so those
numbers cannot be copied in here either.

What can be done instead is to hold the **underlying funds** and let the tool measure the
blend from public prices. Rockhold's Fund Blend range, for example, is stated on its own
factsheet as a mix of two OEICs, both of which are now in the universe:

| | vol (weekly) | vol (daily basis) | max drawdown | history |
|---|---|---|---|---|
| IFSL Rockhold Global Equity A GBP Acc | 10.83% | 8.89% | −15.9% | from Oct 2021 |
| IFSL Rockhold Fixed Interest A GBP Acc | 3.79% | 2.94% | −11.6% | from Oct 2021 |

A 65/35 mix of the two measures **7.60%** weekly volatility over the whole common history,
against the 7.30 standard deviation the Balanced factsheet quotes for its own five-year window
to 30 September 2025. The two figures agreeing to within a third of a percentage point is the
useful result: the risk of a published blend can be reproduced from public prices, so the
tool never needs to restate anyone else's licensed number.

Price data is from public sources and is suitable for research, not as a licensed feed. Some
of it is simply wrong: fourteen instruments arrived with volatilities between 126% and
1,958,187% a year, which is not a risky fund but a broken history.

**Volatility is the wrong trigger on its own, and that cost real accuracy.** `repair.py`
originally looked only at funds above 100% volatility. That misses an entire fault: a unit-price
restatement, pence to pounds, spliced onto the old series without adjustment. One ÷100 step in
1,935 daily observations lifts annualised volatility to about 39% — an adventurous fund, not an
obviously broken file — while the five-year return reads **−99%**. Twenty-six instruments
carried one, and WS Lindsell Train UK Equity was live on the site at −99.08% over five years for
exactly this reason. The trigger is now the *fault* rather than its effect: any single-step break
in the price series, or any figure no fund produces. A break within 10% of a round unit factor is
a redenomination and the earlier segment is **rescaled**, keeping the whole history; anything
else is still truncated.

**A hole in the data reads as a break, and that is how three "repairs" went wrong.** Three
BlackRock and L&G share classes looked like clean 1/100 redenominations. They were not: a
December 2019 price sat next to a June 2026 price with six and a half years of history simply
missing, and the ratio between the two meant nothing at all. Rescaling on that "factor" stitches
two disconnected segments into a history that never happened — worse than the −99% it replaces,
because it looks right. A unit change now has to happen **between adjacent observations**, and
holes are cut before any other test runs: nineteen series carried one, eleven of them longer than
six months, and a fund claiming 12.6 years of history across a 2,814-day gap was reporting
arithmetic on two different periods pretending to be one. Six months is the threshold, which is
generous on purpose — a suspended property fund stops pricing for weeks, not years.

**What counts as "still broken" after a repair is mechanical, and deliberately so.** An earlier
version of that guard dropped anything with a drawdown worse than −90% and threw away twenty
real shares — Lloyds and NatWest really did fall that far through 2008–09 — plus Liontrust Russia
meeting a real 2022. Judging plausibility is how a tool starts quietly discarding the history it
does not like. The guard now drops a series only if a break survives the repair, the volatility
is still impossible, or too little history is left to measure. `build/repair.py` finds
them and separates the two causes — a *denomination flip*, where a stretch of the history is
reported in a different unit and the two breaks invert each other (GR8.L fell 99.0% in one
month and rose 10,057% the next: a divide by 103 then a multiply by 101), and an *unreversed
level break*, where the early history belongs to a different instrument and can only be cut
away (FRAS.L steps 43× in February 2007 and never returns). Six were recovered, eight were
dropped. A wrong number on a risk tool is worse than a missing one.

## Fund manager and sector are derived

There is no free feed of UK fund sector classifications, so both are inferred from the fund
name and flagged `derived`. Good enough to filter and browse by; **not** the IA sector of record
or the manager of record. Treat them as navigation, not as fact.

## Provenance

Each fund is matched by name to the FCA Financial Services Register and links to the official
entry. A dash means no confident name match was found — not that the fund is unauthorised. A
status followed by "?" means the match was loose and may be the wrong fund. Click through before
putting a reference number in a client file.

**Only 50 of the 980 are currently matched.** The matches live in `build/fca_cache.json`, keyed
by symbol, precisely so a rebuild of the universe carries them forward — when they were held
only on the fund record, growing the universe from 190 funds to 982 wiped the entire FCA column
and nothing failed loudly enough to notice. Filling in the rest means running `build/fca.py`
with a register API key (free, from https://register.fca.org.uk/Developer/s/) in `FCA_EMAIL`
and `FCA_KEY`; without them the script carries the cache forward and matches nothing new.

## Does anything predict growth?

`build/correlate.py`, across 634 funds over the **same 60 months** (Sept 2021 – Aug 2026).
The common window is the whole point: each fund's own history covers a different stretch of
market, so comparing funds over their own periods measures the years rather than the funds.

| Against growth | Pearson | Spearman | Reading |
|---|---|---|---|
| Worst 12 months | +0.70 | +0.29 | The strongest single link |
| Maximum drawdown | +0.63 | +0.11 | Shallower falls, more growth |
| Correlation to market | +0.23 | +0.29 | Weak but real |
| Beta | +0.12 | +0.36 | Barely clears zero |
| Volatility | −0.25 | +0.35 | Sign flips — not a straight line |

**Risk paid, but only up to a point.** Sorted into ten volatility bands, average growth climbs
from 2.2% a year in the calmest tenth to 9.7% around the sixth, then falls away — and the most
volatile tenth averaged 1.0%. That sign flip between Pearson and Spearman is the relationship
being a hill rather than a slope, and no single correlation can describe a hill.

**But the spread in that top tenth is the real story.** Its *average* was 1.0% a year while its
*median* was 14.1%. Most of the most volatile funds did well; a handful did so badly they pulled
the average down thirteen points. That is the honest description of high volatility — not lower
returns, but a far wider range of outcomes with a bad end long enough to swamp the mean.

**Drawdown separates funds that volatility does not.** Holding volatility constant, the link
between a shallower worst fall and higher growth strengthens from +0.63 to **+0.84**. That is
why this tool shows drawdown and worst-12-months beside volatility instead of letting
volatility speak alone.

Three cautions. Drawdown, worst-12-months and growth are all summaries of one price path, so
part of the association is arithmetic rather than a discovery. This is a single five-year
window containing the 2022 sell-off; it describes what happened, not what will. And **Sharpe
and Sortino are excluded entirely** — each is growth divided by a risk measure, so correlating
either with growth is correlating growth with itself, and yields a meaningless +0.84.

## The portfolio backtest

`build/portfolio.py` tests mechanical fund-of-funds construction rules walk-forward: each
portfolio is built using only data before its fold and scored on the fold itself, with the
covariance shrunk toward a constant-correlation target and the shrinkage strength chosen by
cross-validation inside the build window.

**The result, stated plainly: none of the rules reliably beat a cheap global tracker.** The best
of them returned 15.8% a year against the tracker's 12.6%, but the 90% confidence interval on
that excess crosses zero and it won in only two of four folds — a coin flip. Two biases flatter
every number besides: survivorship, since funds that closed after doing badly are not in the
universe, and unmodelled rebalancing costs.

It is a backtest, not advice, and not a recommendation.

## Building the data

```
build/discover.py   find candidate funds (Yahoo search, fund houses + FTSE 100 + benchmarks)
build/add.py        price one named share class by ISIN or symbol and merge it in, no rebuild
build/fetch.py      price them, convert to GBP, compute statistics and weekly series
build/names.py      backfill full names from chart metadata
build/classify.py   derive manager, sector and the leveraged/inverse flag
                    (run AFTER repair.py: pack.py reads classify's output, so a repair
                     made after classifying never reaches the site)
build/fca.py        match to the FCA register, cached across rebuilds
build/indices.py    add FTSE 100 and S&P 500 constituents, with their industries
build/repair.py     re-measure instruments whose price series is visibly broken
build/pack.py       write funds.json and series.json for the site
build/beta.py       recompute beta and correlation on a shared monthly window
build/correlate.py  does anything predict growth? (needs numpy)
build/smoke.js      click through every view in a DOM and check each one renders rows
                    (npm install jsdom; node build/smoke.js). Run it after every rebuild --
                    a dropped field breaks a view without anything failing loudly.
build/portfolio.py  walk-forward portfolio test
```
