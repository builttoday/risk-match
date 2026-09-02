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

**Match by risk** — funds whose measured volatility sits inside your band for a risk level.
Leveraged and inverse products are excluded unless you ask for them: their volatility is a
real figure, but it describes a daily-rebalancing trading instrument rather than a holding.

**Browse funds** — all 974, A–Z, filtered by fund manager, sector, minimum history, and
sorted by clicking any column header. Volatility, five-year return, drawdown, Sharpe, Sortino,
beta and worst twelve months are shown by default; **Show all figures** adds weekly volatility,
one- and three-year returns, correlation and CAGR. Select rows to send them straight to the
growth calculator or My Choice, and each row links to a factsheet search and its price
history.

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

**Analysis** — top tens by any measure, the universe broken down by sector and by region, and
the correlation study below. Every figure is computed in the browser from the same data the
rest of the tool uses, so no ranking can go stale against the numbers beside it.

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

974 share classes and instruments, up to 25 years of history — median 8.7 years, with 456 funds
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

Price data is from public sources and is suitable for research, not as a licensed feed. Some
of it is simply wrong: fourteen instruments arrived with volatilities between 126% and
1,958,187% a year, which is not a risky fund but a broken history. `build/repair.py` finds
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

**Only 50 of the 974 are currently matched.** The matches live in `build/fca_cache.json`, keyed
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
build/portfolio.py  walk-forward portfolio test
```
