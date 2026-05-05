"""Cryptocurrency-specific tool functions for agent use.

All functions are wrapped as LangChain ``@tool`` decorators so they can be
bound to LLM agents, consistent with the pattern in ``core_stock_tools.py``,
``fundamental_data_tools.py``, etc.

Symbol detection is also provided for routing between crypto and stock
analysis paths.
"""

from __future__ import annotations

from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor


# ---------------------------------------------------------------------------
# Known symbol lookups
# ---------------------------------------------------------------------------

# Known crypto symbols (primary list used for routing)
CRYPTO_SYMBOLS = {
    "BTC", "ETH", "ADA", "SOL", "DOT", "AVAX", "MATIC", "LINK", "UNI", "AAVE",
    "XRP", "LTC", "BCH", "EOS", "TRX", "XLM", "VET", "ALGO", "ATOM", "LUNA",
    "NEAR", "FTM", "CRO", "SAND", "MANA", "AXS", "GALA", "ENJ", "CHZ", "BAT",
    "ZEC", "DASH", "XMR", "DOGE", "SHIB", "PEPE", "FLOKI", "BNB", "USDT", "USDC",
    "TON", "ICP", "HBAR", "THETA", "FIL", "ETC", "MKR", "APT", "LDO", "OP",
    "IMX", "GRT", "RUNE", "FLOW", "EGLD", "XTZ", "MINA", "ROSE", "KAVA",
    "SUI", "SEI", "ARB", "STRK", "TIA", "WIF", "ENA", "PENDLE", "INJ", "FET",
    "AGIX", "OCEAN", "RNDR", "TAO", "KAS", "CFX", "VANA", "VVV", "VVUSDT",
}

# Known stock symbols (to avoid false-positive crypto routing)
STOCK_SYMBOLS = {
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "NFLX", "DIS", "AMD",
    "INTC", "CRM", "ORCL", "ADBE", "CSCO", "PEP", "KO", "WMT", "JNJ", "PFE",
    "V", "MA", "HD", "UNH", "BAC", "XOM", "CVX", "LLY", "ABBV", "COST",
    "AVGO", "TMO", "ACN", "DHR", "TXN", "LOW", "QCOM", "HON", "UPS", "MDT",
    "GS", "JPM", "WFC", "C", "MS", "BLK", "SPY", "QQQ", "IWM", "DIA",
}


def is_crypto_symbol(symbol: str) -> bool:
    """Detect if a symbol is a cryptocurrency rather than a stock.

    Uses a whitelist approach: known crypto symbols are classified as crypto,
    known stock symbols as stocks. Unknown short symbols are conservatively
    classified as stocks.

    Args:
        symbol: Ticker symbol (e.g., "BTC", "AAPL", "SOL/USDT:USDT").

    Returns:
        True if the symbol appears to be a cryptocurrency.
    """
    # Normalise: strip exchange suffixes and path notation
    raw = symbol.upper().strip()

    # ccxt perpetual swap notation: split on "/" and take the base
    if "/" in raw:
        raw = raw.split("/")[0]

    # Remove common quote currency suffixes
    for suffix in ["USDT", "USD", "BUSD", "USDC"]:
        if raw.endswith(suffix) and len(raw) > len(suffix):
            raw = raw[: -len(suffix)]
            break

    # Known stock → not crypto
    if raw in STOCK_SYMBOLS:
        return False

    # Known crypto
    if raw in CRYPTO_SYMBOLS:
        return True

    # Conservative default: short alphanumeric (2-4 chars) that's not a
    # known stock could be crypto
    if len(raw) <= 4 and raw.isalnum() and raw.isupper():
        return True

    return False


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------


@tool
def get_crypto_price_data(
    symbol: Annotated[str, "Crypto trading pair symbol, e.g. SOL/USDT:USDT for SOL perpetual"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """Fetch perpetual swap OHLCV price data for a cryptocurrency.

    Uses the configured crypto_data vendor (default: crypto_fetcher/ccxt).
    Returns CSV-formatted OHLCV data.

    Args:
        symbol: Trading pair symbol, e.g. "SOL/USDT:USDT" or "SOLUSDT".
        start_date: Start date in yyyy-mm-dd format.
        end_date: End date in yyyy-mm-dd format.

    Returns:
        CSV-formatted string with OHLCV price data.
    """
    return route_to_vendor("get_crypto_perpetual_data", symbol, start_date, end_date)


@tool
def get_crypto_market_data(
    symbol: Annotated[str, "Crypto trading pair symbol, e.g. SOL/USDT:USDT"],
) -> str:
    """Fetch current market ticker data for a crypto perpetual swap.

    Uses the configured crypto_data vendor (default: crypto_fetcher/ccxt).
    Returns CSV-formatted ticker with last price, 24h change, volume, etc.

    Args:
        symbol: Trading pair symbol, e.g. "SOL/USDT:USDT".

    Returns:
        CSV-formatted string with market ticker data.
    """
    return route_to_vendor("get_crypto_market_ticker", symbol)


@tool
def get_funding_rate_analysis(
    symbol: Annotated[str, "Crypto trading pair symbol, e.g. SOL/USDT:USDT"],
) -> str:
    """Fetch funding rate history for a crypto perpetual swap.

    Uses the configured crypto_data vendor (default: crypto_fetcher/ccxt).
    Returns CSV-formatted funding rate history for the last 24 hours.

    High funding rates (>0.01%) suggest the market is heavily long-biased;
    negative rates suggest short-bias.

    Args:
        symbol: Trading pair symbol.

    Returns:
        CSV-formatted string with funding rate history.
    """
    return route_to_vendor("get_crypto_funding_rate", symbol, 24)


@tool
def get_liquidation_levels(
    symbol: Annotated[str, "Crypto trading pair symbol, e.g. SOL/USDT:USDT"],
) -> str:
    """Fetch aggregate open interest for a crypto perpetual swap.

    Uses the configured crypto_data vendor (default: crypto_fetcher/ccxt).
    Open interest levels can indicate where liquidation cascades may cluster.

    Args:
        symbol: Trading pair symbol.

    Returns:
        CSV-formatted string with open interest data.
    """
    return route_to_vendor("get_crypto_open_interest", symbol)
