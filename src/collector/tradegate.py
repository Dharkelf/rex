"""Tradegate live quote scraper — no historical storage, live-only."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from src.utils.config import load_config

logger = logging.getLogger(__name__)

_TIMEOUT_S = 10
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; rex-signal/1.0)"}


@dataclass
class TradegatQuote:
    bid: float | None
    ask: float | None
    last: float | None
    currency: str = "EUR"


def fetch_tradegate_quote() -> TradegatQuote:
    """Scrape current bid/ask/last from Tradegate for ASWM (IE0008BA4TY1)."""
    cfg = load_config()
    url: str = cfg["etf"]["tradegate_url"]

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT_S)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Tradegate fetch failed: %s", exc)
        return TradegatQuote(bid=None, ask=None, last=None)

    try:
        soup = BeautifulSoup(resp.text, "lxml")
        quote = _parse_quote(soup)
        logger.info("Tradegate quote: bid=%.4f ask=%.4f last=%.4f", quote.bid or 0, quote.ask or 0, quote.last or 0)
        return quote
    except Exception as exc:
        logger.warning("Tradegate parse error: %s", exc)
        return TradegatQuote(bid=None, ask=None, last=None)


def _parse_quote(soup: BeautifulSoup) -> TradegatQuote:
    """Extract bid/ask/last from Tradegate order book page."""
    bid: float | None = None
    ask: float | None = None
    last: float | None = None

    # Tradegate renders prices in <span> or <td> with specific class/id patterns.
    # The page structure: table rows with label "Geld" (bid), "Brief" (ask), "Kurs" (last).
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True).lower()
            value_text = cells[1].get_text(strip=True).replace(",", ".").replace("\xa0", "")
            try:
                value = float("".join(c for c in value_text if c in "0123456789."))
            except ValueError:
                continue
            if "geld" in label:
                bid = value
            elif "brief" in label:
                ask = value
            elif "kurs" in label and last is None:
                last = value

    # Fallback: look for data in script tags or other containers
    if bid is None and ask is None:
        spans = soup.find_all("span", class_=True)
        for span in spans:
            text = span.get_text(strip=True).replace(",", ".").replace("\xa0", "")
            cls = " ".join(span.get("class", []))
            try:
                val = float("".join(c for c in text if c in "0123456789."))
            except ValueError:
                continue
            if "bid" in cls.lower() and bid is None:
                bid = val
            elif "ask" in cls.lower() and ask is None:
                ask = val

    return TradegatQuote(bid=bid, ask=ask, last=last)


def tradegate_deviation(tradegate_last: float, xetra_close: float) -> float:
    """Return relative deviation of Tradegate last vs XETRA close."""
    if xetra_close == 0:
        return 0.0
    return (tradegate_last - xetra_close) / xetra_close
