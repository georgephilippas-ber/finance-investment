# Scanners

`clients/interactive_brokers/scanners/` — finds bonds and ETFs with IBKR's market scanner, prices them and prints
them; for bonds it also computes yields. Scan codes, filter tags and ready-made queries are in the tutorials:
[bonds](../research/bond-scanning-europe.md) and [ETFs](../research/etf-scanning-europe.md).

| Module | Contents |
|---|---|
| `__init__.py` | Hides IBKR's harmless "API scanner subscription cancelled" message (error 162), which ib_async logs as an error after every one-shot scan. Other 162 errors still show. Applied on import of any scanner module. |
| `fixed_income.py` | [`interactive_brokers_scan_bonds`](#interactive_brokers_scan_bonds), [`quote_bonds`](#quote_bonds) |
| `exchange_traded_fund.py` | [`interactive_brokers_scan_etfs`](#interactive_brokers_scan_etfs), [`quote_etfs`](#quote_etfs) |
| `domain.py` | [`BondFilters`](#bondfilters), [`BondQuote`](#bondquote), [`Bond`](#bond), [`EtfFilters`](#etffilters), [`EtfQuote`](#etfquote), [`Etf`](#etf), `SCANNER_ROW_LIMIT` |
| `printing.py` | [`print_bond`](#print_bond), [`print_bonds`](#print_bonds), [`print_bonds_table`](#print_bonds_table), [`print_etf`](#print_etf), [`print_etfs`](#print_etfs), [`print_etfs_table`](#print_etfs_table) |
| `_shared.py` | Internal: running a scan and fetching contract details, reading the ISIN, resolving issuers, fetching prices. |

- Nothing here places orders. Requests are IBKR scanner, contract-details and market-data requests, plus one
  [LEI resolver](lei_resolver.md) lookup (ESMA FIRDS and GLEIF) per scanned instrument.
- **Prices are requested as delayed-frozen market data** (IBKR market-data type 4): real-time where you subscribe,
  otherwise 15-minute delayed, and the last available price when the market is closed. Calling `quote_bonds` or
  `quote_etfs` switches the whole `IB` session to this mode.
- Bond prices are **clean** and **per 100 of face value**, as IBKR quotes them. They are not amounts of money. ETF
  prices are per share, in the ETF's trading currency.
- Bond yields and calculations default to [`latest_weekday()`](helpers.md#latest_weekday) as the valuation date, so a
  weekend run lines up with Friday's closing prices.

# Bonds

## Fetching

### `interactive_brokers_scan_bonds`
```python
async def interactive_brokers_scan_bonds(ib: IB, *, instrument: str, location: str, scan_code: str, rows: int = SCANNER_ROW_LIMIT, **filters: Unpack[BondFilters]) -> List[Bond]
```
Runs one IBKR scan and returns the matching bonds as [`Bond`](#bond)s, without quotes.
- `instrument`, `location`, `scan_code` — IBKR scanner codes, e.g. `"BOND.GOVT.NON-US"`, `"BOND.GOVT.NON-US"`,
  `"HIGH_BOND_ASK_YIELD_ALL"`. The scan code sets the order; the filters do the narrowing.
- `rows` — at most `SCANNER_ROW_LIMIT` (50), IBKR's cap per scan. A full 50 usually means more bonds matched.
- `filters` — IBKR filter tags as keyword arguments, sent as strings (`issuerCountryIs="DE"`, `bondCallableIs="false"`).
  Tags missing from [`BondFilters`](#bondfilters) still work at runtime but are flagged by type checkers.

One contract-details request is made per result, concurrently. IBKR leaves most bond fields empty, so each
`Bond` is filled as follows:

| Field | Source |
|---|---|
| `contract_id`, `isin`, `description`, `bond_type`, `callable`, `minimum_size`, `size_increment` | IBKR contract details (`conId`, `secIdList`, `descAppend`, `tradingClass`, …) |
| `annual_coupon`, `maturity` | IBKR's coupon and maturity when present; otherwise read from `descAppend` (`OBL 2 1/2 04/16/31` → 0.025, 2031-04-16) |
| `currency` | IBKR's contract currency when present; otherwise the `currencyLike` filter; otherwise `None` |
| `inflation_linked` | `True` when IBKR flags an index-ratio factor (`evRule` starting with `factor`), e.g. `DBRI` |
| `legal_entity` | The issuer from the [LEI resolver](lei_resolver.md#get_legal_entity_by_isin): issuer LEI from ESMA FIRDS (or GLEIF), details from GLEIF; at most 4 bonds resolved at a time. `None` when neither register knows the ISIN or the lookup fails (logged as a warning). A 50-bond EUR corporate scan resolved all 50, adding about 15 seconds |

**Skipped bonds.** A bond whose description cannot be read (e.g. a floating-rate note) is left out with a logged
warning, so one bad result does not fail the whole scan.

**Errors.** `LookupError` if a conId matches no or several contracts. Request failures propagate.

### `quote_bonds`
```python
async def quote_bonds(ib: IB, bonds: List[Bond]) -> List[Bond]
```
Returns the same bonds, in the same order, with `quote` filled in as a [`BondQuote`](#bondquote). `Bond` is frozen,
so these are new objects; the input list is unchanged.
- Price: IBKR's market price (last trade inside the spread, otherwise the midpoint); when there is none, the
  previous close; when there is neither, `quote` is `None`. `live` is `True` only for real-time data.
- `as_of` is when the quote arrived, not when the price was set. On a weekend a close is stamped with the weekend time.

## Data structures

### `BondFilters`
```python
class BondFilters(TypedDict, total=False):
    maturityDateAbove: str
    maturityDateBelow: str
    bondVarCouponRateIs: Any
    issuerCountryIs: str
    currencyLike: str
    bondCreditRating: str
    bondCallableIs: Any
    bondDefaultedIs: Any
    excludeConvertible: Any
    bondAmtOutstandingAbove: Any
    bondInitialSizeAbove: Any
    bondInitialSizeBelow: Any
```
The typed subset of IBKR filter tags accepted by `interactive_brokers_scan_bonds`. Maturity dates must be `yyyymmdd`:
IBKR rejects `mm/yyyy` and numbers of years with "Invalid Maturity Date Filter", although its parameters XML lists
them; `bondAmtOutstanding…` is in millions of face value; `bondCreditRating` is `"highGrade"` or `"highYield"`.
The full list of tags, with units, is in the [tutorial](../research/bond-scanning-europe.md#4-filters).

### `BondQuote`
```python
@dataclass(frozen=True)
class BondQuote:
    price: Decimal
    as_of: datetime
    live: bool
```
A read-only price snapshot with no behaviour of its own; `Bond` methods read it.
- `price` — clean price per 100 face.
- `as_of` — when IBKR delivered the quote (UTC).
- `live` — `True` only for real-time data; `False` for delayed, frozen or previous-close prices.

### `Bond`
```python
@dataclass(frozen=True)
class Bond:
    contract_id: int
    isin: Optional[str]
    description: str
    bond_type: str
    currency: Optional[str]
    annual_coupon: Decimal
    maturity: date
    inflation_linked: bool = False
    callable: bool = False
    minimum_size: Decimal = Decimal(1)
    size_increment: Decimal = Decimal(1)
    legal_entity: Optional[LegalEntity] = None
    quote: Optional[BondQuote] = None
```
One bond and, optionally, its latest quote. Frozen and hashable; the hash includes the quote, so the same bond at two
prices counts as two keys. Match bonds by `contract_id`.
- `description` — IBKR's `descAppend`, Bloomberg style: issuer code, coupon, maturity (`OBL 2 1/2 04/16/31`).
- `bond_type` — IBKR's trading class: the issuer or programme code (`DBR`, `OBL`, `DBRI`, `VW`, `PBBGR`).
- `annual_coupon` — a fraction of face value: `0.025` for 2.5 %.
- `legal_entity` — the issuing [`LegalEntity`](lei_resolver.md#legalentity): LEI, legal name, country, status. It is
  the legal issuer, which can be a subsidiary (an `ACAFP` bond can belong to Crédit Agricole Assurances).
- `minimum_size`, `size_increment` — in IBKR **quantity units**, which are not necessarily currency. A what-if order
  on a Bund showed one unit = €1,000 of face value, so `minimum_size = 100` would be €100,000. Check a bond's unit
  in TWS before trading.

**Coupons are treated as annual.** IBKR does not report the payment frequency, so every bond is assumed to pay once
a year on the anniversary of its maturity. That is right for German and most euro government bonds; yields for
semi-annual payers (Italian BTPs, UK gilts, most USD bonds) are slightly off.

#### Methods

Each method that needs a price reads `quote` and returns `None` without one. `settlement` / `on` default to
[`latest_weekday()`](helpers.md#latest_weekday).

| Method | Returns |
|---|---|
| `is_zero_coupon` (property) | `annual_coupon == 0` |
| `years_to_maturity(on=None)` | days to maturity / 365.25, as `Decimal` |
| `coupon_dates(after)` | remaining coupon dates after `after`, ending at maturity |
| `dirty_price(settlement=None)` | clean price plus coupon accrued since the last coupon date (actual days), per 100 face |
| `yield_to_maturity(settlement=None)` | annual yield in %: the IRR of paying the dirty price for the remaining cash flows, timed in actual/365.25 years and solved with SciPy's `brentq`. Real yield for inflation-linked bonds |
| `yield_without_reinvestment(settlement=None)` | annual return in % if coupons are kept as cash: `((100 + remaining coupons) / dirty price) ** (1 / years) - 1`. A conservative floor under `yield_to_maturity`; equal to it for zero-coupon bonds |

`dirty_price` and the yields raise `ValueError` for a matured bond.

**Limits.** No holiday calendar or settlement lag (T+2): the valuation date is a plain weekday. Day counts are
actual/actual, which suits Bunds but not 30/360 markets. Duration and convexity are not computed.

## Printing

Prices are formatted with Babel (`97.035`, `1,109.462`) without a currency symbol, since they are per 100 face.
Coupons and yields are percentages to three decimals. Missing values are shown as `-`.

### `print_bond`
```python
def print_bond(bond: Bond, valuation_date: Optional[date] = None) -> None
```
Titled with the bond's description. A two-column sheet in groups:
1. Description, ISIN, IBKR contract ID, bond type, currency.
2. Issuer (legal name), LEI, issuer country, LEI status, from `legal_entity`.
3. Coupon, years to maturity, yield to maturity, yield without reinvestment, maturity.
4. Payment frequency (always "Annual (assumed)"), inflation-linked, callable.
5. Minimum size, size increment.
6. Price source (Live / Close), quote received, valuation date.
7. Clean price, accrued interest, dirty price.

Every calculation uses the one `valuation_date` (default `latest_weekday()`), which the sheet shows. Yield labels end
in "(real)" for inflation-linked bonds.

### `print_bonds`
```python
def print_bonds(bonds: List[Bond], valuation_date: Optional[date] = None) -> None
```
A [`print_bond`](#print_bond) sheet for each bond, separated by a blank line. All sheets use the same valuation date
(default `latest_weekday()`).

### `print_bonds_table`
```python
def print_bonds_table(bonds: List[Bond], valuation_date: Optional[date] = None, *, title: str = "BONDS", has_lei: bool = False) -> None
```
With `has_lei=True`, only bonds with a `legal_entity` are printed and the title shows how many were kept, e.g.
**BONDS (16 of > 50 instruments)**.
Titled `title` followed by the number of bonds, e.g. **BONDS (21 instruments)**. At exactly 50, IBKR's scanner cap, it
reads **(> 50 instruments)**, since more bonds probably matched. One row per bond and a row count. Columns: Contract ID, Name (`description`), Issuer (the legal name from `legal_entity`), ISIN, Clean price, Coupon, Years to
maturity, Yield to maturity, Yield, no reinvestment.

# ETFs

## Fetching ETFs

### `interactive_brokers_scan_etfs`
```python
async def interactive_brokers_scan_etfs(client_: IB, *, instrument: str, location: str, scan_code: str, rows: int = SCANNER_ROW_LIMIT, **filters: Unpack[EtfFilters]) -> List[Etf]
```
Runs one IBKR scan and returns the matching ETFs as [`Etf`](#etf)s, without quotes.
- `instrument`, `location`, `scan_code` — e.g. `"STOCK.EU"`, `"STK.EU.IBIS-ETF"` (Xetra's ETF segment),
  `"MOST_ACTIVE_AVG_USD"`. European ETFs are scanned as European stocks; US ETFs have their own instruments
  (`ETF.EQ.US`, `ETF.FI.US`).
- For `STOCK.*` instruments the ETF stock-type filter `stkTypes="inc:ETF"` is added unless you pass your own.
- Results whose IBKR stock type is not `ETF` (ETNs, ETCs, ordinary shares) are dropped.

| Field | Source |
|---|---|
| `contract_id`, `symbol`, `currency`, `minimum_size`, `size_increment` | IBKR contract details. European ETFs trade in fractions (minimum 0.0001 shares) |
| `isin` | IBKR's `secIdList` |
| `name` | IBKR's long name, abbreviated (`VANG FTSE AW USDA`) |
| `exchange` | IBKR's primary exchange (`IBIS`, `IBIS2`, `AEB`, `SBF`, …) |
| `legal_entity` | The fund from the [LEI resolver](lei_resolver.md#get_legal_entity_by_isin). An ETF's LEI belongs to the fund itself, so this gives its full registered name (`Vanguard FTSE All-World UCITS ETF`) |

A 50-ETF scan with fund lookups took about 45 seconds.

### `quote_etfs`
```python
async def quote_etfs(client_: IB, etfs: List[Etf]) -> List[Etf]
```
Returns the same ETFs with `quote` filled in as an [`EtfQuote`](#etfquote), by the same rules as
[`quote_bonds`](#quote_bonds).

## ETF data structures

### `EtfFilters`
```python
class EtfFilters(TypedDict, total=False):
    stkTypes: str
    avgUsdVolumeAbove: Any
    avgUsdVolumeBelow: Any
    usdPriceAbove: Any
    usdPriceBelow: Any
    histPerfRatioYTDAbove: Any
    histPerfRatio1yAbove: Any
    histPerfRatio3yAbove: Any
    histPerfRatio5yAbove: Any
    dividendYieldFrdAbove: Any
    dividendYieldFrdBelow: Any
    firstTradeDateBelow: str
    issuerCountryIs: str
    peaEligibleStkIs: Any
```
The typed subset of filter tags that work for European ETFs. The full list is in the
[ETF tutorial](../research/etf-scanning-europe.md#4-filters).

### `EtfQuote`
```python
@dataclass(frozen=True)
class EtfQuote:
    price: Decimal
    as_of: datetime
    live: bool
```
Like [`BondQuote`](#bondquote), but `price` is per share in the ETF's trading currency.

### `Etf`
```python
@dataclass(frozen=True)
class Etf:
    contract_id: int
    symbol: str
    isin: Optional[str]
    name: str
    currency: str
    exchange: str
    minimum_size: Decimal = Decimal(1)
    size_increment: Decimal = Decimal(1)
    legal_entity: Optional[LegalEntity] = None
    quote: Optional[EtfQuote] = None
```
One ETF listing and, optionally, its latest quote. The same fund can be listed on several exchanges and in several
currencies; each listing has its own `contract_id` but the same `isin`. IBKR's scanner returns no expense ratio, fund
size or distribution policy for European ETFs; see the [tutorial](../research/etf-scanning-europe.md).

## Printing ETFs

ETF prices are money, so unlike bond prices they are formatted with a currency symbol (`€171.18`).

### `print_etf`
```python
def print_etf(etf: Etf) -> None
```
Titled with the symbol and exchange (`VWCE (IBIS2)`). A two-column sheet in groups:
1. Name, symbol, ISIN, IBKR contract ID, exchange, currency.
2. Fund (legal name), LEI, fund country, LEI status, from `legal_entity`.
3. Minimum size, size increment.
4. Price source (Live / Close), quote received.
5. Price.

### `print_etfs`
```python
def print_etfs(etfs: List[Etf]) -> None
```
A [`print_etf`](#print_etf) sheet for each ETF, separated by a blank line.

### `print_etfs_table`
```python
def print_etfs_table(etfs: List[Etf], *, title: str = "ETFS") -> None
```
One row per ETF, titled with the instrument count like [`print_bonds_table`](#print_bonds_table). Columns: Contract ID,
Symbol, Name, Fund (legal name from `legal_entity`), ISIN, Exchange, Price (with currency symbol, via Babel), Source
(Live / Close).

# Examples

```python
from clients.interactive_brokers.client import connect, disconnect
from clients.interactive_brokers.scanners.fixed_income import quote_bonds, interactive_brokers_scan_bonds
from clients.interactive_brokers.scanners.printing import print_bond, print_bonds_table

ib = await connect()
try:
  bonds = await interactive_brokers_scan_bonds(ib, instrument="BOND.GOVT.NON-US", location="BOND.GOVT.NON-US",
                                               scan_code="HIGH_BOND_ASK_YIELD_ALL", issuerCountryIs="DE",
                                               currencyLike="EUR",
                                               maturityDateAbove="20281002", maturityDateBelow="20311002")
  quoted = await quote_bonds(ib, bonds)
  print_bonds_table(quoted, title="GERMAN GOVERNMENT BONDS")
  print_bond(quoted[0])
finally:
  disconnect(ib)
```

```python
from clients.interactive_brokers.scanners.exchange_traded_fund import interactive_brokers_scan_etfs, quote_etfs
from clients.interactive_brokers.scanners.printing import print_etfs_table

etfs = await interactive_brokers_scan_etfs(ib, instrument="STOCK.EU", location="STK.EU.IBIS-ETF",
                                           scan_code="MOST_ACTIVE_AVG_USD")
print_etfs_table(await quote_etfs(ib, etfs), title="MOST TRADED ETFS ON XETRA")
```
