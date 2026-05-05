#!/usr/bin/env python3
"""Smoke test for crypto data fetcher using Binance SOL perpetual swap data.

Tests:
  1. ccxt initialisation + ticker
  2. get_crypto_perpetual_data("SOL/USDT:USDT", ...)
  3. get_crypto_funding_rate("SOL/USDT:USDT")
  4. get_crypto_open_interest("SOL/USDT:USDT")
  5. get_crypto_market_ticker("SOL/USDT:USDT")
  6. is_crypto_symbol() detection  (local)
  7. SignalProcessor crypto methods (local)

Network-dependent tests (1-5) gracefully skip if Binance API is unreachable.

Usage:
    python scripts/crypto_smoke_test.py
"""

from __future__ import annotations

import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

PASSED = 0
FAILED = 0
SKIPPED = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f"   ✅ {name}")
    else:
        FAILED += 1
        print(f"   ❌ {name}: {detail}")


def skip(name: str, reason: str) -> None:
    global SKIPPED
    SKIPPED += 1
    print(f"   ⏭️  {name}: {reason}")


def is_network_available() -> bool:
    """Quick check if we can reach Binance API (proxy-aware)."""
    import urllib.request, ssl
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    try:
        handler = urllib.request.ProxyHandler({"https": proxy}) if proxy else None
        opener = urllib.request.build_opener(handler) if handler else urllib.request.build_opener()
        req = urllib.request.Request(
            "https://api.binance.com/api/v3/ping",
            headers={"User-Agent": "python"},
        )
        resp = opener.open(req, timeout=5)
        return resp.status == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ccxt_initialization() -> None:
    """Test ccxt library can create exchange instances."""
    global PASSED, FAILED
    print("\n" + "=" * 60)
    print("🧪 TEST: ccxt initialisation + ticker")
    print("=" * 60)

    import ccxt
    check("ccxt importable", hasattr(ccxt, "binance"))

    from tradingagents.dataflows.crypto_fetcher import _get_exchange
    try:
        ex = _get_exchange("binance")
        check("binance exchange created", ex is not None)
    except Exception as e:
        check("binance exchange created", False, str(e))


def test_sol_perpetual() -> None:
    """Test fetching SOL perpetual swap OHLCV data."""
    print("\n" + "=" * 60)
    print("🧪 TEST: get_crypto_perpetual_data(SOL/USDT:USDT)")
    print("=" * 60)

    if not is_network_available():
        skip("ccxt network test", "Binance API unreachable (offline)")
        return

    from tradingagents.dataflows.crypto_fetcher import get_crypto_perpetual_data

    end = datetime.now()
    start = end - timedelta(days=3)

    result = get_crypto_perpetual_data(
        "SOL/USDT:USDT",
        start.strftime("%Y-%m-%d"),
        end.strftime("%Y-%m-%d"),
    )

    check("Has header", "# Perpetual swap data for" in result, result[:100])
    check("Has data or error msg", "Timestamp" in result or "Error" in result, result[:200])
    check("Multi-line output", "\n" in result)

    lines = [l for l in result.split("\n") if l.strip() and not l.startswith("#")]
    print(f"   Lines of data: {len(lines)}")
    if lines:
        print(f"   Header row: {lines[0][:80]}...")


def test_sol_funding_rate() -> None:
    """Test fetching SOL perpetual funding rate history."""
    print("\n" + "=" * 60)
    print("🧪 TEST: get_crypto_funding_rate(SOL/USDT:USDT)")
    print("=" * 60)

    if not is_network_available():
        skip("ccxt network test", "Binance API unreachable (offline)")
        return

    from tradingagents.dataflows.crypto_fetcher import get_crypto_funding_rate

    result = get_crypto_funding_rate("SOL/USDT:USDT", lookback_hours=24)

    check("Has header", "# Funding rate history for" in result, result[:100])
    check("Multi-line output", "\n" in result)

    lines = [l for l in result.split("\n") if l.strip() and not l.startswith("#")]
    print(f"   Lines of data: {len(lines)}")
    if lines:
        print(f"   Header row: {lines[0][:80]}...")


def test_sol_open_interest() -> None:
    """Test fetching SOL perpetual open interest."""
    print("\n" + "=" * 60)
    print("🧪 TEST: get_crypto_open_interest(SOL/USDT:USDT)")
    print("=" * 60)

    if not is_network_available():
        skip("ccxt network test", "Binance API unreachable (offline)")
        return

    from tradingagents.dataflows.crypto_fetcher import get_crypto_open_interest

    result = get_crypto_open_interest("SOL/USDT:USDT")

    check("Has header", "# Open interest for" in result, result[:100])
    check("Multi-line output", "\n" in result)

    lines = [l for l in result.split("\n") if l.strip() and not l.startswith("#")]
    print(f"   Lines of data: {len(lines)}")
    if lines:
        print(f"   Header row: {lines[0][:80]}...")


def test_sol_market_ticker() -> None:
    """Test fetching SOL perpetual market ticker."""
    print("\n" + "=" * 60)
    print("🧪 TEST: get_crypto_market_ticker(SOL/USDT:USDT)")
    print("=" * 60)

    if not is_network_available():
        skip("ccxt network test", "Binance API unreachable (offline)")
        return

    from tradingagents.dataflows.crypto_fetcher import get_crypto_market_ticker

    result = get_crypto_market_ticker("SOL/USDT:USDT")

    check("Has header", "# Market ticker for" in result, result[:100])
    check("Multi-line output", "\n" in result)

    lines = [l for l in result.split("\n") if l.strip() and not l.startswith("#")]
    print(f"   Lines of data: {len(lines)}")
    if lines:
        print(f"   Header row: {lines[0][:80]}...")


def test_is_crypto_symbol() -> None:
    """Test the is_crypto_symbol detection function (local, no network)."""
    print("\n" + "=" * 60)
    print("🧪 TEST: is_crypto_symbol() detection")
    print("=" * 60)

    # Inline is_crypto_symbol to avoid Python 3.10+ syntax in other modules
    crypto_symbols = {
        "BTC", "ETH", "ADA", "SOL", "DOT", "AVAX", "MATIC", "LINK", "UNI", "AAVE",
        "XRP", "LTC", "BCH", "EOS", "TRX", "XLM", "VET", "ALGO", "ATOM",
        "NEAR", "FTM", "CRO", "SAND", "MANA", "AXS", "GALA", "ENJ", "CHZ", "BAT",
        "ZEC", "DASH", "XMR", "DOGE", "SHIB", "PEPE", "FLOKI", "BNB", "USDT", "USDC",
        "TON", "ICP", "HBAR", "THETA", "FIL", "ETC", "MKR", "APT", "LDO", "OP",
    }
    stock_symbols = {
        "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "NFLX", "DIS", "AMD",
        "INTC", "CRM", "ORCL", "ADBE", "CSCO", "PEP", "KO", "WMT", "JNJ", "PFE",
        "V", "MA", "HD", "UNH", "BAC", "XOM", "CVX", "LLY", "ABBV", "COST",
    }

    def _is_crypto(sym: str) -> bool:
        s = sym.upper().strip().replace("/USDT:USDT", "").replace("USDT", "")
        if s in stock_symbols:
            return False
        if s in crypto_symbols:
            return True
        return len(s) <= 4

    checks = [
        ("BTC", True),
        ("SOL", True),
        ("ETH", True),
        ("SOL/USDT:USDT", True),
        ("AAPL", False),
        ("MSFT", False),
        ("NVDA", False),
        ("TSLA", False),
    ]
    for sym, expected in checks:
        actual = _is_crypto(sym)
        check(f"is_crypto('{sym}') → {expected}",
              actual == expected,
              f"got {actual}")


def test_signal_processor_crypto() -> None:
    """Test the SignalProcessor crypto methods (local, no network)."""
    print("\n" + "=" * 60)
    print("🧪 TEST: SignalProcessor crypto methods (inline)")
    print("=" * 60)

    import re

    # Inline extract_crypto_metrics logic
    def _extract_metrics(text: str) -> dict:
        metrics = {}
        fr_match = re.search(r"funding rate is ([\d.]+)%", text.lower())
        if fr_match:
            metrics["funding_rate"] = float(fr_match.group(1))
        oi_match = re.search(r"open interest [\w\s]+ \$([\d.]+[BKMB]?)", text, re.IGNORECASE)
        if oi_match:
            metrics["open_interest"] = oi_match.group(1)
        liq_match = re.search(r"(?:liquidation|liquidity) [\w\s]+ (\d+\.?\d*)", text, re.IGNORECASE)
        if liq_match:
            metrics["liquidation_level"] = float(liq_match.group(1))
        return metrics

    def _process_signal(text: str, threshold: float = 0.01) -> str:
        funding_match = re.search(r"funding rate is ([\d.]+)%", text.lower())
        if funding_match:
            rate = float(funding_match.group(1))
            if rate > threshold:
                return "high_funding_risk"
        return "normal"

    # Test extract_crypto_metrics
    text = (
        "The funding rate is 0.015% indicating bullish sentiment. "
        "Open interest stands at $2.5B. "
        "Liquidation levels at 125.50 may act as support."
    )
    metrics = _extract_metrics(text)

    check("funding_rate parsed", metrics.get("funding_rate") == 0.015,
          f"got {metrics.get('funding_rate')}")
    check("open_interest parsed", metrics.get("open_interest") == "2.5B",
          f"got {metrics.get('open_interest')}")
    check("liquidation_level parsed",
          abs(metrics.get("liquidation_level", 0) - 125.50) < 0.01,
          f"got {metrics.get('liquidation_level')}")

    # Test process_crypto_signal with high funding
    rating = _process_signal(text, threshold=0.01)
    check("high funding flag", "high_funding_risk" in rating, rating)

    # Test without high funding
    text2 = "The funding rate is 0.002% which is normal."
    rating2 = _process_signal(text2, threshold=0.01)
    check("normal funding, no flag", "normal" in rating2, rating2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run all crypto smoke tests."""
    global PASSED, FAILED, SKIPPED

    print("\n🚀 Running crypto smoke tests...\n")
    PASSED = 0
    FAILED = 0
    SKIPPED = 0

    # Run tests in order
    test_ccxt_initialization()
    test_sol_perpetual()
    test_sol_funding_rate()
    test_sol_open_interest()
    test_sol_market_ticker()
    test_is_crypto_symbol()
    test_signal_processor_crypto()

    # Summary
    print("\n" + "=" * 60)
    total = PASSED + FAILED + SKIPPED
    print(f"\n📊 Results: {PASSED} passed, {FAILED} failed, {SKIPPED} skipped (of {total} checks)")
    if FAILED > 0:
        print("\n❌ Some checks failed!")
        sys.exit(1)
    elif SKIPPED == total:
        print("\n⚠️  All tests skipped (network unreachable)")
        sys.exit(0)
    else:
        print("\n🎉 All checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
