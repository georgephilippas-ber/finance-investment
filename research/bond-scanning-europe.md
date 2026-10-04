# Scanning for European Bonds with the IBKR API

A practical guide to finding European government and corporate bonds through the IBKR market scanner. Every code
below comes from IBKR's scanner parameters XML, returned by `ib.reqScannerParametersAsync()`. A commented-out block in
`research/main.py` saves it as `interactive_brokers_scanner_reference.xml`; if IBKR changes its scanner, save a fresh
copy and check the codes against it.

The functions used here (`interactive_brokers_scan_bonds`, `quote_bonds`, `print_bonds_table`, …) are documented in
[Scanners](../documentation/scanners.md).

---

## 1. How a scan is built

An IBKR scan has four parts:

| Part             | What it means                                   | Example                    |
|------------------|-------------------------------------------------|----------------------------|
| `instrument`     | Which kind of security to scan                  | `BOND`, `BOND.GOVT.NON-US` |
| `locationCode`   | Which market or venue to scan                   | `BOND.GOVT.EU.EURONEXT`    |
| `scanCode`       | How results are **sorted** (and loosely chosen) | `HIGH_BOND_ASK_YIELD_ALL`  |
| filter tags      | Conditions every result must meet               | `currencyLike=EUR`         |

The scan code only decides the order. The filters do the real narrowing. A scan returns at most 50 rows, so tight
filters matter: otherwise you only see the top 50 of an arbitrary universe.

---

## 2. Where European bonds live

### Instruments

| `instrument`       | Covers                     |
|--------------------|----------------------------|
| `BOND`             | Corporate bonds (worldwide)|
| `BOND.GOVT.NON-US` | Non-US sovereign bonds     |

(`BOND.GOVT`, `BOND.AGNCY`, `BOND.MUNI` and `BOND.CD` are US-only.)

### Locations

| `locationCode`          | Name                       | Use with           |
|-------------------------|----------------------------|--------------------|
| `BOND.WW`               | Worldwide corporate bonds  | `BOND`             |
| `BOND.US`               | US corporate bonds         | `BOND`             |
| `BOND.EU.EURONEXT`      | Euronext corporate bonds   | `BOND`             |
| `BOND.EU.EBS`           | SIX Swiss corporate bonds  | `BOND`             |
| `BOND.GOVT.NON-US`      | All non-US sovereign bonds | `BOND.GOVT.NON-US` |
| `BOND.GOVT.US.NON-US`   | Non-US govt bonds          | `BOND.GOVT.NON-US` |
| `BOND.GOVT.EU.EURONEXT` | Euronext govt bonds        | `BOND.GOVT.NON-US` |
| `BOND.GOVT.EU.EBS`      | SIX Swiss govt bonds       | `BOND.GOVT.NON-US` |
| `BOND.GOVT.HK.SEHK`     | Hong Kong bonds            | `BOND.GOVT.NON-US` |

`BOND.WW` contains `BOND.US`, `BOND.EU.EURONEXT` and `BOND.EU.EBS`. `BOND.GOVT.NON-US` contains the four govt locations
below it.

**Which one to pick:**

- **Broadest search (recommended starting point):** use a parent location (`BOND.WW` or `BOND.GOVT.NON-US`), then narrow
  it with `currencyLike` and `issuerCountryIs`. Many European bonds are available outside Euronext and SIX, so a
  venue-specific location can miss them.
- **Only bonds on a particular exchange:** use `BOND.EU.EURONEXT`, `BOND.EU.EBS`, `BOND.GOVT.EU.EURONEXT` or
  `BOND.GOVT.EU.EBS`.

### Two restrictions on the exchange locations

The XML marks the Euronext and SIX locations with:

- **`access="restricted;s=..."`**: they need the matching market-data subscription on your account. Without it, the
  scan returns nothing or an error.
- **`rawPriceOnly="yes"`** (the two *corporate* exchange locations): only prices are available, so yield, spread and
  duration filters may not work there. Filter on price (`bondAsk...`, `bondBidOrAsk...`) instead.

---

## 3. Scan codes (sort order)

| `scanCode`                | Sorts by                     | Corp | Govt |
|---------------------------|------------------------------|:----:|:----:|
| `HIGH_BOND_ASK_YIELD_ALL` | Highest ask yield            | ✓    | ✓    |
| `LOW_BOND_BID_YIELD_ALL`  | Lowest bid yield             | ✓    | ✓    |
| `HIGH_BOND_SPREAD_ALL`    | Widest spread                | ✓    | ✓    |
| `LOW_BOND_SPREAD_ALL`     | Tightest spread              | ✓    | ✓    |
| `HIGH_COUPON_RATE`        | Highest coupon               | ✓    | ✓    |
| `LOW_COUPON_RATE`         | Lowest coupon                | ✓    | ✓    |
| `NEAR_MATURITY_DATE`      | Soonest maturity             | ✓    | ✓    |
| `FAR_MATURITY_DATE`       | Latest maturity              | ✓    | ✓    |
| `BOND_CUSIP_AZ` / `_ZA`   | Identifier, alphabetical     | ✓    | ✓    |
| `HIGH_MOODY_RATING_ALL`   | Best Moody's rating first    | ✓    |      |
| `LOW_MOODY_RATING_ALL`    | Worst Moody's rating first   | ✓    |      |
| `HIGH_SP_RATING_ALL`      | Best S&P rating first        | ✓    |      |
| `LOW_SP_RATING_ALL`       | Worst S&P rating first       | ✓    |      |
| `MOST_ACTIVE`             | Volume                       | ✓    |      |
| `TOP_TRADE_COUNT`         | Number of trades             | ✓    |      |
| `TOP_PERC_GAIN` / `_LOSE` | Price change today           | ✓    |      |
| `HIGH_/LOW_BOND_DEBT_2_EQUITY_RATIO` | Issuer leverage   | ✓    |      |
| `SCAN_esgScore_DESC` / `_ASC` | Issuer ESG score (Refinitiv) | ✓ |    |

The XML also has the other Refinitiv balance-sheet ratio scans and the individual ESG pillar scans, for corporates only.

---

## 4. Filters

Most numeric filters come in pairs, `...Above` and `...Below`. Pass them as strings.

### Available for both corporates and sovereigns

| Tag                                           | Meaning / units                                                |
|-----------------------------------------------|----------------------------------------------------------------|
| `currencyLike`                                | `EUR`, `GBP`, `CHF`, `USD`, `CAD`, `AUD`, `BRL`, `HKD`         |
| `issuerCountryIs`                             | ISO 2-letter code (see section 5)                              |
| `maturityDateAbove` / `Below`                 | `yyyymmdd` only (IBKR rejects `mm/yyyy` and years)             |
| `couponRateAbove` / `Below`                   | Coupon in %                                                    |
| `bondAskYieldAbove` / `Below`                 | Yield at the ask, in %                                         |
| `bondBidYieldAbove` / `Below`                 | Yield at the bid, in %                                         |
| `bondBidOrAskYieldAbove` / `Below`            | Yield at bid or ask, in %                                      |
| `bondAskAbove` / `Below`                      | Ask price (% of face value)                                    |
| `bondBidOrAskAbove` / `Below`                 | Bid or ask price                                               |
| `bondAskSizeValueAbove` / `Below`             | Size on the ask, **in thousands** of face value                |
| `bondSpreadAbove` / `Below`                   | Spread (unit not stated in the XML; likely basis points)       |
| `bondDurationAbove` / `Below`                 | Duration                                                       |
| `bondConvexityAbove` / `Below`                | Convexity                                                      |
| `bondAmtOutstandingAbove` / `Below`           | Issue size outstanding, **in millions** of face value          |
| `bondInitialSizeAbove` / `Below`              | Minimum order size (face value)                                |
| `bondIncrementSizeAbove` / `Below`            | Order size increment (face value)                              |
| `bondVarCouponRateIs`                         | `true` = only floaters, `false` = exclude floaters             |
| `excludeConvertible`                          | `true` to exclude convertibles                                 |
| `bondValidBidOrAskOnly`                       | `true` **includes** bonds with no quote (see the warning below)|

> **Warning: `bondValidBidOrAskOnly` does the opposite of what its name suggests.** The XML labels it "Include bonds
> without quotes" and says unquoted bonds are excluded by default. Leave it out to get only bonds you can trade now.
> Set it to `true` only to see the full universe, including bonds with no quote.

### Corporates only (`BOND`)

| Tag                                     | Meaning / values                                                                 |
|-----------------------------------------|----------------------------------------------------------------------------------|
| `bondCreditRating`                      | `highGrade` (investment grade) or `highYield`                                    |
| `moodyRatingAbove` / `Below`            | `AAA AA1 AA2 AA3 A1 A2 A3 BAA1 BAA2 BAA3 BA1 … B3 CAA1 … C NR`                   |
| `spRatingAbove` / `Below`               | `AAA AA+ AA AA- A+ A A- BBB+ BBB BBB- BB+ … D NR`                                |
| `ratingsRelation`                       | How Moody's and S&P filters combine: `or`, `and`, `xand`                         |
| `bondIssuerLike`                        | Issuer name, partial match (e.g. `Siemens`)                                      |
| `bondStkSymbolIs`                       | Ticker of the issuer's stock (e.g. `SAP`)                                        |
| `bondCallableIs`                        | `true` only / `false` exclude                                                    |
| `bondNextCallDateAbove` / `Below`       | Call protection: a date, presumably `yyyymmdd` like maturity (untested)          |
| `bondPaymentFreqIs`                     | `1` annual, `2` semi-annual, `4` quarterly, `12` monthly, `0` at maturity        |
| `bondDefaultedIs`                       | `false` to exclude defaulted bonds                                               |
| `bondTradingFlatIs`                     | `false` to exclude bonds trading without accrued interest (often distressed)     |
| `bondExchListedIs`                      | `true` only exchange-listed                                                      |
| `bondStkMarketCapAbove` / `Below`       | Issuer equity market cap, in millions                                            |
| `bondDebtOutstandingAbove` / `Below`    | Issuer total debt, in millions                                                   |
| `bondDebt2BookRatioAbove` / `Below`     | Issuer debt/book (Refinitiv)                                                     |
| `esgScoreAbove` / `Below`               | Issuer ESG score (Refinitiv); pillar scores also available                       |
| `priceAbove`/`Below`, `volumeAbove`, `changePercAbove`/`Below`, `tradeCountAbove`/`Below` | Trading activity |

**Sovereigns have no rating filters or rating scans.** To restrict by credit quality, filter by `issuerCountryIs`
instead (e.g. scan only `DE`, `NL`, `AT`, `FI` for AAA/AA euro sovereigns).

---

## 5. European country codes

The `issuerCountryIs` values for Europe, taken from the XML:

| Code | Country      | Code | Country     | Code | Country        |
|------|--------------|------|-------------|------|----------------|
| `AT` | Austria      | `FR` | France      | `NL` | Netherlands    |
| `BE` | Belgium      | `DE` | Germany     | `NO` | Norway         |
| `BG` | Bulgaria     | `GR` | Greece      | `PL` | Poland         |
| `HR` | Croatia      | `HU` | Hungary     | `PT` | Portugal       |
| `CY` | Cyprus       | `IE` | Ireland     | `RO` | Romania        |
| `CZ` | Czech Rep.   | `IT` | Italy       | `SK` | Slovakia       |
| `DK` | Denmark      | `LV` | Latvia      | `SI` | Slovenia       |
| `EE` | Estonia      | `LT` | Lithuania   | `ES` | Spain          |
| `FI` | Finland      | `LU` | Luxembourg  | `SE` | Sweden         |
| `GB` | United Kingdom | `MT` | Malta     | `CH` | Switzerland    |

`issuerCountryIs` takes one country per scan. To cover several countries, run one scan per country (section 7).

---

## 6. Running a scan

`interactive_brokers_scan_bonds` lives in `clients/interactive_brokers/scanners/fixed_income.py`:

```python
from clients.interactive_brokers.client import connect, disconnect
from clients.interactive_brokers.scanners.fixed_income import interactive_brokers_scan_bonds

ib = await connect()
try:
  bonds = await interactive_brokers_scan_bonds(ib, instrument="BOND.GOVT.NON-US", location="BOND.GOVT.NON-US",
                                               scan_code="HIGH_BOND_ASK_YIELD_ALL", issuerCountryIs="DE",
                                               currencyLike="EUR")
finally:
  disconnect(ib)
```

Pass any filter from section 4 as a keyword argument; values are converted to strings for you. Tags that are not in
`BondFilters` still work but are flagged by type checkers.

`interactive_brokers_scan_bonds` returns a list of `Bond` objects with ISIN, coupon, maturity and the other details. Section 8 shows how to
add prices and yields; [Scanners](../documentation/scanners.md#interactive_brokers_scan_bonds) explains where each field comes from.

---

## 7. Recipes

### 7.1 German Bunds, 2 to 10 years, highest yield first

```python
await interactive_brokers_scan_bonds(
    ib, instrument="BOND.GOVT.NON-US", location="BOND.GOVT.NON-US", scan_code="HIGH_BOND_ASK_YIELD_ALL",
    issuerCountryIs="DE",
    currencyLike="EUR",
    maturityDateAbove="20281002",   # 2 years from 2 Oct 2026
    maturityDateBelow="20361002",   # 10 years
    bondVarCouponRateIs="false",
)
```

### 7.2 Euro-area periphery sovereigns paying over 3%

```python
results = {}
for country in ["IT", "ES", "PT", "GR"]:
    results[country] = await interactive_brokers_scan_bonds(
        ib, instrument="BOND.GOVT.NON-US", location="BOND.GOVT.NON-US", scan_code="HIGH_BOND_ASK_YIELD_ALL",
        issuerCountryIs=country,
        currencyLike="EUR",
        bondAskYieldAbove=3,
        maturityDateBelow="20331002",   # 7 years
    )
```

### 7.3 Short-dated core-euro govts (cash-like ladder)

```python
await interactive_brokers_scan_bonds(
    ib, instrument="BOND.GOVT.NON-US", location="BOND.GOVT.NON-US", scan_code="NEAR_MATURITY_DATE",
    issuerCountryIs="NL",
    currencyLike="EUR",
    maturityDateBelow="20271231",
    bondAmtOutstandingAbove=5_000,   # >= EUR 5bn outstanding, i.e. liquid lines
)
```

### 7.4 Investment-grade EUR corporates, plain vanilla, 3 to 7 years

```python
await interactive_brokers_scan_bonds(
    ib, instrument="BOND", location="BOND.WW", scan_code="HIGH_BOND_ASK_YIELD_ALL",
    currencyLike="EUR",
    bondCreditRating="highGrade",
    maturityDateAbove="20291002",   # 3 years
    maturityDateBelow="20331002",   # 7 years
    bondCallableIs="false",
    excludeConvertible="true",
    bondVarCouponRateIs="false",
    bondDefaultedIs="false",
    bondAmtOutstandingAbove=500,     # >= EUR 500m issue size
)
```

### 7.5 A-rated or better from both agencies, French issuers

```python
await interactive_brokers_scan_bonds(
    ib, instrument="BOND", location="BOND.WW", scan_code="HIGH_SP_RATING_ALL",
    issuerCountryIs="FR",
    currencyLike="EUR",
    spRatingAbove="A-",
    moodyRatingAbove="A3",
    ratingsRelation="and",
)
```

Check the direction with a bond you know before relying on it. "Above" should mean "this rating or better", but the XML
does not say.

### 7.6 EUR high yield with guard rails

```python
await interactive_brokers_scan_bonds(
    ib, instrument="BOND", location="BOND.WW", scan_code="HIGH_BOND_ASK_YIELD_ALL",
    currencyLike="EUR",
    bondCreditRating="highYield",
    spRatingAbove="BB-",             # stay in the upper part of high yield
    bondAskYieldAbove=5,
    bondAskYieldBelow=10,            # very high yields usually mean distress
    bondDurationBelow=4,
    bondDefaultedIs="false",
    bondTradingFlatIs="false",
    bondCallableIs="false",
)
```

### 7.7 Bonds you can buy in small amounts

Many European corporate bonds have a EUR 100,000 minimum denomination. To leave those out:

```python
await interactive_brokers_scan_bonds(
    ib, instrument="BOND", location="BOND.WW", scan_code="HIGH_BOND_ASK_YIELD_ALL",
    currencyLike="EUR",
    bondCreditRating="highGrade",
    bondInitialSizeBelow=100,        # minimum order below 100 units
)
```

The XML does not state the unit of `bondInitialSize`. It appears to match IBKR's order quantity, the same unit as
`Bond.minimum_size`, and that unit is not currency: a what-if order on a Bund showed one unit = €1,000 of face value.
So `minimum_size = 1` means about €1,000 and `100` about €100,000. Check a bond's unit in TWS before trading.

### 7.8 One issuer's whole curve

```python
await interactive_brokers_scan_bonds(
    ib, instrument="BOND", location="BOND.WW", scan_code="FAR_MATURITY_DATE",
    bondIssuerLike="Volkswagen",
    currencyLike="EUR",
)
```

### 7.9 Swiss franc bonds on SIX

```python
# Sovereigns: yield filters are available here
await interactive_brokers_scan_bonds(ib, instrument="BOND.GOVT.NON-US", location="BOND.GOVT.EU.EBS", scan_code="HIGH_BOND_ASK_YIELD_ALL", currencyLike="CHF")

# Corporates: SIX corporate data is price-only, so filter and sort on price
await interactive_brokers_scan_bonds(
    ib, instrument="BOND", location="BOND.EU.EBS", scan_code="HIGH_COUPON_RATE",
    currencyLike="CHF",
    bondAskBelow=100,                # trading below par
    maturityDateBelow="20311002",   # 5 years
)
```

### 7.10 Low-carbon EUR corporates

```python
await interactive_brokers_scan_bonds(
    ib, instrument="BOND", location="BOND.WW", scan_code="SCAN_esgEmissionsScore_DESC",
    currencyLike="EUR",
    bondCreditRating="highGrade",
    esgEmissionsScoreAbove=70,
)
```

---

## 8. Prices and yields

`quote_bonds` returns the same bonds with a `quote` (clean price, time, live flag); `print_bonds_table` and `print_bond`
show them with their yields:

```python
from clients.interactive_brokers.scanners.fixed_income import quote_bonds
from clients.interactive_brokers.scanners.printing import print_bond, print_bonds_table

quoted = await quote_bonds(ib, bonds)
print_bonds_table(quoted, title="GERMAN GOVERNMENT BONDS")
print_bond(quoted[0])

bond = quoted[0]
bond.dirty_price()  # 98.193 for OBL 2 1/2 04/16/31 at 97.035 clean
bond.yield_to_maturity()  # 3.21 (%)
bond.yield_without_reinvestment()  # 3.04 (%), coupons kept as cash
```

Prices are requested as delayed-frozen data: real-time where you subscribe, otherwise delayed or the last close
(`quote.live` is `False`). Without any price, `quote` and every yield are `None`.

Coupons are treated as annual, because IBKR does not report the payment frequency. That is right for German and most
other euro government bonds; for semi-annual payers (Italian BTPs, UK gilts, most USD bonds) the computed yield is
slightly off. The full calculation rules are in [Scanners](../documentation/scanners.md#methods).

---

## 9. Pitfalls

- **Empty results.** Remove filters one at a time. The usual causes are a missing market-data subscription for the
  location, a yield filter on a price-only location, or filters that don't match each other.
- **Unsupported filters are dropped without warning.** A filter that doesn't apply to the instrument, such as a rating
  filter on sovereigns, is usually ignored rather than rejected, so the results can look filtered when they aren't. Each
  instrument's supported filters are in its `<filters>` list in the scanner parameters XML.
- **50-row cap.** If a scan returns exactly 50 rows, you are probably missing bonds. Tighten the filters or split the
  scan by country or maturity range.
- **Scanner yields are snapshots.** For the bonds you shortlist, check yields against live market data.
- **Units differ by filter.** Issue size is in millions and quoted size is in thousands. Yields and coupons are in
  percent.
- **Order quantities are not currency.** IBKR's quantity unit for bonds can be €1,000 of face value per unit (Bunds),
  so minimum sizes and order quantities must be converted before reading them as money.
- **IBKR returns few bond details.** Ratings, issuer names, payment frequency and often currency, coupon and maturity
  come back empty. The scanner can filter on ratings but does not return them.
- **Refinitiv data covers issuers, not bonds.** The balance-sheet ratio and ESG filters describe the issuing company,
  so every bond from the same issuer gets the same value.

---

## 10. Looking up other codes

```python
import xml.etree.ElementTree as ET

root = ET.parse("interactive_brokers_scanner_reference.xml").getroot()

# Filters available for an instrument
for instrument in root.iter("Instrument"):
    if instrument.findtext("type") == "BOND.GOVT.NON-US":
        print(instrument.findtext("filters"))
        break

# Tag codes and allowed values for one filter id
for filter_list in root.findall("FilterList"):
    for f in filter_list:
        if f.findtext("id") == "BOND_PAYMENT_FREQ":
            for field in f.iter("AbstractField"):
                print(field.findtext("code"), [v.findtext("code") for v in field.iter("ComboValue")])
```
