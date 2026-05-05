"""ccxt-based cryptocurrency perpetual swap data fetcher.

Provides functions for fetching OHLCV data, funding rates, open interest,
and market ticker data for cryptocurrency perpetual swap markets via ccxt.

All functions return CSV-format strings, consistent with the A v0.2.4
y_finance.py style, so that agents can read them as structured text.

Symbol format follows ccxt conventions:
  - Perpetual swap: "SOL/USDT:USDT" (base/quote:settle)
  - Spot: "BTC/USDT" (base/quote)
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Annotated, Optional

import pandas as pd
import ccxt


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _get_exchange(exchange_id: str = "binance") -> ccxt.Exchange:
    """Create a ccxt exchange instance.

    Args:
        exchange_id: Exchange identifier (default: "binance").

    Returns:
        Configured ccxt Exchange instance.
    """
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({
        "enableRateLimit": True,
        "options": {"defaultType": "swap"},  # Prefer perpetual swaps
    })
    return exchange


def _to_ccxt_symbol(symbol: str) -> str:
    """Normalise a raw symbol to ccxt format.

    Tries to be flexible:
      - "SOL/USDT:USDT" → passed through
      - "SOLUSDT" → "SOL/USDT:USDT"
      - "SOL" → "SOL/USDT:USDT"

    Args:
        symbol: Raw symbol string.

    Returns:
        ccxt-compatible symbol string.
    """
    s = symbol.upper().strip()
    if "/" in s:
        return s  # Already in ccxt format

    # Strip any "USDT" suffix and rebuild
    base = s
    for suffix in ["USDT", "USD", "BUSD"]:
        if s.endswith(suffix) and len(s) > len(suffix):
            base = s[: -len(suffix)]
            break
    return f"{base}/USDT:USDT"


# ---------------------------------------------------------------------------
# Public API — all return CSV strings (agent-readable)
# ---------------------------------------------------------------------------


def get_crypto_perpetual_data(
    symbol: Annotated[str, "Trading pair symbol, e.g. SOL/USDT:USDT for SOL perpetual swap"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """Fetch OHLCV data for a cryptocurrency perpetual swap market.

    Uses ccxt to fetch Binance perpetual swap candles, returning CSV format
    compatible with the existing y_finance.py data functions.

    Date-aware: end_date is capped to today to prevent future-data leakage
    in backtesting mode.

    Args:
        symbol: Trading pair symbol in ccxt format, e.g. "SOL/USDT:USDT".
        start_date: Start date in yyyy-mm-dd format.
        end_date: End date in yyyy-mm-dd format.

    Returns:
        CSV-formatted string with columns: Timestamp, Open, High, Low,
        Close, Volume.
    """
    # Curb future dates to prevent data leakage
    today = datetime.now().strftime("%Y-%m-%d")
    if end_date > today:
        end_date = today

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    ccxt_symbol = _to_ccxt_symbol(symbol)
    exchange = _get_exchange()

    try:
        # Convert to millisecond timestamps for ccxt
        since = int(start_dt.timestamp() * 1000)
        until = int(end_dt.timestamp() * 1000)

        # Fetch in batches of 1000 candles (max per request)
        all_candles = []
        current_since = since
        while current_since < until:
            candles = exchange.fetch_ohlcv(
                ccxt_symbol,
                timeframe="1h",
                since=current_since,
                limit=1000,
            )
            if not candles:
                break
            all_candles.extend(candles)
            current_since = candles[-1][0] + 3600_000  # Next batch = last ts + 1h
            if current_since >= until:
                break

        if not all_candles:
            return (
                f"# No data found for symbol '{ccxt_symbol}' "
                f"between {start_date} and {end_date}\n"
            )

        # Build DataFrame
        df = pd.DataFrame(
            all_candles,
            columns=["Timestamp", "Open", "High", "Low", "Close", "Volume"],
        )
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], unit="ms")
        df.set_index("Timestamp", inplace=True)

        # Filter to exact date range
        df = df.loc[start_date:end_date]

        # Round for readability
        numeric_cols = ["Open", "High", "Low", "Close"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].round(2)
        if "Volume" in df.columns:
            df["Volume"] = df["Volume"].round(4)

        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer)

        header = (
            f"# Perpetual swap data for {ccxt_symbol} from {start_date} to {end_date}\n"
            f"# Total records: {len(df)}\n"
            f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"# Timeframe: 1h\n\n"
        )

        return header + csv_buffer.getvalue()

    except Exception as exc:
        return (
            f"# Error fetching perpetual data for {ccxt_symbol}: {exc}\n"
        )


def get_crypto_funding_rate(
    symbol: Annotated[str, "Trading pair symbol, e.g. SOL/USDT:USDT"],
    lookback_hours: Annotated[int, "Number of hours to look back for funding history"] = 24,
) -> str:
    """Fetch funding rate history for a perpetual swap market.

    Args:
        symbol: Trading pair symbol in ccxt format.
        lookback_hours: Lookback period in hours (default: 24).

    Returns:
        CSV-formatted string with funding rate history.
    """
    ccxt_symbol = _to_ccxt_symbol(symbol)
    exchange = _get_exchange()

    try:
        since = int((datetime.now().timestamp() - lookback_hours * 3600) * 1000)
        funding_rates = exchange.fetch_funding_rate_history(
            ccxt_symbol,
            since=since,
            limit=100,
        )

        if not funding_rates:
            return f"# No funding rate data available for {ccxt_symbol}\n"

        records = []
        for entry in funding_rates:
            records.append({
                "Timestamp": datetime.fromtimestamp(entry["timestamp"] / 1000).strftime("%Y-%m-%d %H:%M:%S"),
                "FundingRate": entry.get("fundingRate", 0),
                "Symbol": entry.get("symbol", ccxt_symbol),
            })

        df = pd.DataFrame(records)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)

        current_rate = records[-1]["FundingRate"] if records else 0
        header = (
            f"# Funding rate history for {ccxt_symbol}\n"
            f"# Lookback period: {lookback_hours}h\n"
            f"# Records: {len(records)}\n"
            f"# Latest funding rate: {current_rate * 100:.4f}%\n"
            f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        )

        return header + csv_buffer.getvalue()

    except Exception as exc:
        return f"# Error fetching funding rate for {ccxt_symbol}: {exc}\n"


def get_crypto_open_interest(
    symbol: Annotated[str, "Trading pair symbol, e.g. SOL/USDT:USDT"],
) -> str:
    """Fetch current open interest for a perpetual swap market.

    Args:
        symbol: Trading pair symbol in ccxt format.

    Returns:
        CSV-formatted string with open interest data.
    """
    ccxt_symbol = _to_ccxt_symbol(symbol)
    exchange = _get_exchange()

    try:
        oi = exchange.fetch_open_interest(ccxt_symbol)

        if not oi:
            return f"# No open interest data available for {ccxt_symbol}\n"

        records = [{
            "Symbol": oi.get("symbol", ccxt_symbol),
            "OpenInterest": oi.get("openInterest", 0),
            "BaseValue": oi.get("baseValue", 0),
            "QuoteValue": oi.get("quoteValue", 0),
            "Timestamp": datetime.fromtimestamp(oi.get("timestamp", 0) / 1000).strftime("%Y-%m-%d %H:%M:%S"),
        }]

        df = pd.DataFrame(records)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)

        header = (
            f"# Open interest for {ccxt_symbol}\n"
            f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        )

        return header + csv_buffer.getvalue()

    except Exception as exc:
        return f"# Error fetching open interest for {ccxt_symbol}: {exc}\n"


def get_crypto_market_ticker(
    symbol: Annotated[str, "Trading pair symbol, e.g. SOL/USDT:USDT"],
) -> str:
    """Fetch current market ticker data for a crypto perpetual swap market.

    Includes: last price, 24h change, 24h volume, bid/ask, high/low.

    Args:
        symbol: Trading pair symbol in ccxt format.

    Returns:
        CSV-formatted string with market ticker data.
    """
    ccxt_symbol = _to_ccxt_symbol(symbol)
    exchange = _get_exchange()

    try:
        ticker = exchange.fetch_ticker(ccxt_symbol)

        if not ticker:
            return f"# No ticker data available for {ccxt_symbol}\n"

        records = [{
            "Symbol": ticker.get("symbol", ccxt_symbol),
            "Last": ticker.get("last", 0),
            "Bid": ticker.get("bid", 0),
            "Ask": ticker.get("ask", 0),
            "High24h": ticker.get("high", 0),
            "Low24h": ticker.get("low", 0),
            "BaseVolume24h": ticker.get("baseVolume", 0),
            "QuoteVolume24h": ticker.get("quoteVolume", 0),
            "PercentageChange24h": ticker.get("percentage", 0),
            "Timestamp": datetime.fromtimestamp(ticker.get("timestamp", 0) / 1000).strftime("%Y-%m-%d %H:%M:%S"),
        }]

        df = pd.DataFrame(records)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)

        header = (
            f"# Market ticker for {ccxt_symbol}\n"
            f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        )

        return header + csv_buffer.getvalue()

    except Exception as exc:
        return f"# Error fetching ticker for {ccxt_symbol}: {exc}\n"
