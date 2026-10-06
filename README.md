# EDGAR Teaching Module

A lightweight helper module for teaching SEC EDGAR API retrieval in Python/Jupyter notebooks.

## Teaching design

The module is deliberately **not** a complete EDGAR abstraction library. It hides repetitive request mechanics while leaving the important data structures visible for teaching.

The intended sequence is:

1. **Manual EDGAR/XBRL review** — students use the SEC website and inspect filings manually.
2. **Filings API** — students learn ticker → CIK, HTTP requests, JSON, nested structures, filing forms, and pandas.
3. **Company Facts** — students inspect XBRL Company Facts and then use helpers to work with concepts and observations.
4. **Later extension** — map company/XBRL concepts to common financial-statement line items for analysis and valuation.

The module intentionally does **not** perform that final financial-statement mapping.

## Installation

From a VS Code terminal:

```bash
python -m pip install -r requirements.txt
```

## Required first step in every notebook

Students should configure their identity before extracting SEC data:

```python
import edgar

edgar.configure(
    name="Your Name",
    email="your_email@uw.edu"
)
```

This is intentionally explicit. The SEC asks automated users to declare a User-Agent identifying the requester. The public data APIs do not require an API key.

## First retrieval

```python
cik = edgar.ticker_to_cik("AAPL")
print(cik)
```

Then:

```python
submissions = edgar.get_submissions("AAPL")
print(type(submissions))
print(submissions.keys())
```

Once students have explored the raw structure:

```python
filings = edgar.get_filings("AAPL")
filings.head()
```

Filter forms:

```python
annual_reports = edgar.get_filings_by_form("AAPL", "10-K")
```

or:

```python
selected = edgar.get_filings_by_form(
    "AAPL",
    ["10-K", "10-Q", "8-K"]
)
```

## Company Facts

Retrieve the raw XBRL Company Facts response:

```python
facts = edgar.get_company_facts("AAPL")
facts.keys()
```

List available US-GAAP concepts:

```python
concepts = edgar.list_facts("AAPL")
concepts.head()
```

Retrieve one concept:

```python
fact = edgar.get_fact(
    "AAPL",
    "Assets"
)
```

Convert that concept's observations to a DataFrame:

```python
assets = edgar.fact_observations(
    "AAPL",
    "Assets"
)
```

## Public functions

- `configure(name, email)`
- `is_configured()`
- `format_cik(cik)`
- `ticker_lookup()`
- `ticker_to_cik(ticker)`
- `company_info(ticker)`
- `resolve_cik(company)`
- `get_submissions(company)`
- `get_filings(company)`
- `get_filings_by_form(company, form)`
- `get_company_facts(company)`
- `list_facts(company, taxonomy="us-gaap")`
- `get_fact(company, concept, taxonomy="us-gaap")`
- `fact_observations(company, concept, taxonomy="us-gaap")`
- `clear_cache()`

All functions that retrieve SEC data require `configure()` first.

## Notes for instructors

- `get_submissions()` and `get_company_facts()` deliberately return raw dictionaries. This supports iterative notebook exploration.
- Convenience DataFrame functions are available after students understand the raw response.
- Ticker lookup and company responses are cached in memory to avoid unnecessary repeated requests during a notebook session.
- The module uses a conservative pause between network requests.
- Public helper functions accept either a ticker or CIK where appropriate.
