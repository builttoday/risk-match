# Risk Match

Type the risk score your attitude-to-risk questionnaire produced, and see every fund whose
**measured** volatility falls inside the band your firm associates with that level.

Live: https://builttoday.github.io/risk-match/

## What it does and does not do

The adviser supplies the framework; the tool supplies the measurement. It shows what a fund's
volatility, drawdown and returns actually were. It does not rate funds, rank them for
suitability, or recommend anything — suitability remains the adviser's judgement.

Set your own volatility bands in "Set what each risk level means for your firm". The defaults
are starting points, not anyone's house view.

## The numbers

Annualised volatility is the standard deviation of daily returns scaled by √252. Maximum
drawdown is the worst peak-to-trough fall. Both are computed from five years of public daily
closing prices, so any figure here can be reproduced from the price history.

This is **realised** risk, looking backwards. Risk-profiling services publish forward-looking
expected volatility from a capital markets model — a different measure that will not agree with
these figures. Past volatility is not a promise about future volatility.

Leveraged and inverse products are hidden by default. Their volatility is measured the same way
but describes a daily-rebalancing trading instrument rather than a holding.

## Provenance

Each fund is matched by name to the FCA Financial Services Register and links to the official
entry. A dash means no confident name match was found — not that the fund is unauthorised. A
status followed by "?" means the match was loose and may be the wrong fund. Click through before
putting a reference number in a client file.

## Coverage

190 sterling share classes, not the whole market. There is no free way to enumerate every UK
fund: the FCA Register API returns at most 20 rows per search with no working pagination, and
its bulk extract is a paid service. Full coverage needs a commercial data licence.

Price data is from public sources and is suitable for research, not as a licensed feed.
