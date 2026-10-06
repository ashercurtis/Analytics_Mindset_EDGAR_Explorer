"""
edgar.py
Lightweight teaching helper for SEC EDGAR data retrieval.

Designed for ACCTG teaching notebooks:
- students configure their SEC identity explicitly;
- public functions accept a ticker or CIK;
- HTTP/request details, CIK formatting, caching, and gentle rate limiting
  are handled here;
- raw JSON remains available so notebooks can slow down and inspect
  the structures before using convenience DataFrames.

This module uses public SEC data APIs. No API key is required.
"""

from __future__ import annotations

import time
from functools import lru_cache
from typing import Any

import pandas as pd
import requests

_SEC_DATA = "https://data.sec.gov"
_SEC_WWW = "https://www.sec.gov"
_USER_AGENT: str | None = None
_LAST_REQUEST_AT = 0.0

# Intentionally conservative for a classroom setting.
# SEC fair-access guidance currently permits up to 10 requests/second.
_MIN_REQUEST_INTERVAL = 0.15


class EdgarError(RuntimeError):
    """Base exception for this teaching module."""


class EdgarConfigurationError(EdgarError):
    """Raised when SEC identification has not been configured."""


class EdgarRequestError(EdgarError):
    """Raised when an SEC request fails."""


def configure(name: str, email: str) -> None:
    """
    Configure the identity sent with SEC requests.

    Run this near the beginning of each notebook/session:

        import edgar
        edgar.configure(
            name="Student Name",
            email="student@uw.edu"
        )

    The SEC asks automated users to declare a User-Agent identifying
    the requester. No API key is required for the public data APIs.
    """
    global _USER_AGENT

    name = str(name).strip()
    email = str(email).strip()

    if not name:
        raise EdgarConfigurationError("Please provide your name.")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise EdgarConfigurationError(
            "Please provide a valid contact email address."
        )

    _USER_AGENT = f"{name} {email}"


def is_configured() -> bool:
    """Return True after configure() has been called successfully."""
    return _USER_AGENT is not None


def _require_configuration() -> None:
    if not is_configured():
        raise EdgarConfigurationError(
            "EDGAR access is not configured. Run:\n\n"
            "    import edgar\n"
            "    edgar.configure(name='Your Name', email='you@example.edu')\n\n"
            "before requesting SEC data."
        )


def _headers() -> dict[str, str]:
    _require_configuration()
    return {
        "User-Agent": _USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
    }


def _get_json(url: str) -> Any:
    """Retrieve JSON from the SEC with basic validation and rate control."""
    global _LAST_REQUEST_AT

    _require_configuration()

    elapsed = time.monotonic() - _LAST_REQUEST_AT
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)

    try:
        response = requests.get(
            url,
            headers=_headers(),
            timeout=30,
        )
        _LAST_REQUEST_AT = time.monotonic()
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise EdgarRequestError(
            f"SEC request failed for {url}\n"
            f"Check your internet connection and SEC configuration.\n"
            f"Original error: {exc}"
        ) from exc
    except ValueError as exc:
        raise EdgarRequestError(
            f"The SEC response from {url} was not valid JSON."
        ) from exc


def _digits_only(value: str) -> bool:
    return value.isdigit()


def format_cik(cik: str | int) -> str:
    """Return a CIK as a 10-character zero-padded string."""
    value = str(cik).strip()
    if not _digits_only(value):
        raise ValueError(f"CIK must contain digits only: {cik!r}")
    if len(value) > 10:
        raise ValueError(f"CIK cannot exceed 10 digits: {cik!r}")
    return value.zfill(10)


@lru_cache(maxsize=1)
def ticker_lookup() -> pd.DataFrame:
    """
    Retrieve the SEC ticker/CIK/company-name mapping.

    Returns a DataFrame with:
        cik_str, ticker, title
    """
    data = _get_json(f"{_SEC_WWW}/files/company_tickers.json")
    df = pd.DataFrame.from_dict(data, orient="index")
    df["ticker"] = df["ticker"].astype(str).str.upper()
    df["cik_str"] = df["cik_str"].astype(str).str.zfill(10)
    return df.reset_index(drop=True)


def ticker_to_cik(ticker: str) -> str:
    """Translate a ticker symbol into a zero-padded 10-digit CIK."""
    ticker = str(ticker).strip().upper()
    matches = ticker_lookup().loc[
        ticker_lookup()["ticker"] == ticker,
        "cik_str",
    ]

    if matches.empty:
        raise EdgarError(f"Ticker {ticker!r} was not found in the SEC ticker file.")

    return str(matches.iloc[0])


def company_info(ticker: str) -> dict[str, str]:
    """Return ticker, CIK, and SEC company name for a ticker."""
    ticker = str(ticker).strip().upper()
    matches = ticker_lookup().loc[ticker_lookup()["ticker"] == ticker]

    if matches.empty:
        raise EdgarError(f"Ticker {ticker!r} was not found in the SEC ticker file.")

    row = matches.iloc[0]
    return {
        "ticker": str(row["ticker"]),
        "cik": str(row["cik_str"]),
        "name": str(row["title"]),
    }


def resolve_cik(company: str | int) -> str:
    """
    Resolve either a ticker or CIK to a zero-padded 10-digit CIK.

    Examples:
        resolve_cik("AAPL")
        resolve_cik("320193")
        resolve_cik(320193)
    """
    value = str(company).strip()

    if _digits_only(value):
        return format_cik(value)

    return ticker_to_cik(value)


@lru_cache(maxsize=128)
def get_submissions(company: str | int) -> dict[str, Any]:
    """
    Return the raw SEC submissions JSON for a company.

    Keeping the raw dictionary visible is useful for notebook exercises
    that inspect keys, nested structures, and filing metadata.
    """
    cik = resolve_cik(company)
    return _get_json(f"{_SEC_DATA}/submissions/CIK{cik}.json")


def get_filings(company: str | int) -> pd.DataFrame:
    """
    Return the company's recent SEC filings as a pandas DataFrame.

    This corresponds to:
        submissions_json["filings"]["recent"]
    """
    data = get_submissions(company)
    recent = data.get("filings", {}).get("recent")

    if not isinstance(recent, dict):
        raise EdgarError("Could not find filings['recent'] in the SEC response.")

    return pd.DataFrame(recent)


def get_filings_by_form(
    company: str | int,
    form: str | list[str] | tuple[str, ...],
) -> pd.DataFrame:
    """
    Filter recent filings to one or more SEC form types.

    Examples:
        get_filings_by_form("AAPL", "10-K")
        get_filings_by_form("AAPL", ["10-K", "10-Q", "8-K"])
    """
    filings = get_filings(company)

    if "form" not in filings.columns:
        raise EdgarError("The filings response does not contain a 'form' column.")

    if isinstance(form, str):
        forms = [form]
    else:
        forms = list(form)

    wanted = {str(x).strip().upper() for x in forms}
    mask = filings["form"].astype(str).str.upper().isin(wanted)
    return filings.loc[mask].reset_index(drop=True)


@lru_cache(maxsize=128)
def get_company_facts(company: str | int) -> dict[str, Any]:
    """
    Return the raw SEC Company Facts/XBRL JSON for a company.

    The raw response is deliberately exposed so students can inspect:
        facts -> taxonomy -> concept -> units -> observations
    """
    cik = resolve_cik(company)
    return _get_json(
        f"{_SEC_DATA}/api/xbrl/companyfacts/CIK{cik}.json"
    )


def list_facts(
    company: str | int,
    taxonomy: str = "us-gaap",
) -> pd.DataFrame:
    """
    List concepts available under a taxonomy in Company Facts.

    Returns concept, label, and description where supplied by the SEC.
    """
    data = get_company_facts(company)
    concepts = data.get("facts", {}).get(taxonomy, {})

    rows = []
    for concept, details in concepts.items():
        rows.append({
            "concept": concept,
            "label": details.get("label"),
            "description": details.get("description"),
        })

    return pd.DataFrame(rows).sort_values(
        "concept",
        ignore_index=True,
    )


def get_fact(
    company: str | int,
    concept: str,
    taxonomy: str = "us-gaap",
) -> dict[str, Any]:
    """
    Return the raw Company Facts object for one XBRL concept.

    This intentionally does not map company concepts into standardized
    financial-statement line items. That mapping is a later analytical step.
    """
    data = get_company_facts(company)
    concepts = data.get("facts", {}).get(taxonomy, {})

    if concept not in concepts:
        raise EdgarError(
            f"Concept {concept!r} was not found under taxonomy {taxonomy!r}."
        )

    return concepts[concept]


def fact_observations(
    company: str | int,
    concept: str,
    taxonomy: str = "us-gaap",
) -> pd.DataFrame:
    """
    Convert the observations for one XBRL concept into a tidy DataFrame.

    If a concept is reported in multiple units, a 'unit' column identifies
    the source unit. No financial-statement standardization is performed.
    """
    fact = get_fact(company, concept, taxonomy)
    units = fact.get("units", {})

    rows = []
    for unit, observations in units.items():
        for observation in observations:
            row = dict(observation)
            row["unit"] = unit
            rows.append(row)

    return pd.DataFrame(rows)


def clear_cache() -> None:
    """Clear in-memory SEC responses; useful when demonstrating fresh retrieval."""
    ticker_lookup.cache_clear()
    get_submissions.cache_clear()
    get_company_facts.cache_clear()
