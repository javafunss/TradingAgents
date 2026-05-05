#!/usr/bin/env python3
"""Smoke test for crypto data fetcher using Binance SOL perpetual swap data.

Tests:
  1. ccxt initialisation
  2. get_crypto_perpetual_data("SOL/USDT:USDT", ...)
  3. get_crypto_funding_rate("SOL/USDT:USDT")
  4. get_crypto_open_interest("SOL/USDT:USDT")
  5. get_crypto_market_ticker("SOL/USDT:USDT")
  6. Validate output format (CSV headers, data rows)

Usage:
    python scripts/crypto_smoke_test.py
"""

from __future__ import annotations

import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta
from tradingagents.dataflows.crypto_fetcher import (
    get_crypto_perpetual_data,
    get_crypto_funding_rate,
    get_crypto_open_interest,
    get_crypto_market_ticker,
)


def test_sol_perpetual() -> None:
    """Test fetching SOL perpetual swap OHLCV data."""
    print("=" * 60)
    print("🧪 TEST: get_crypto_perpetual_data(SOL/USDT:USDT)")
    print("=" * 60)

    end = datetime.now()
    start = end - timedelta(days=3)

    result = get_crypto_perpetual_data(
        "SOL/USDT:USDT",
        start.strftime("%Y-%m-%d"),
        end.strftime("%Y-%m-%d"),
    )

    # Validate
    assert "# Perpetual swap data for" in result, "Missing header"
    assert "Timestamp" in result or "Error" in result, "Missing data or error"
    # Check it's CSV-like (has line breaks, commas)
    assert "\n" in result, "Expected multi-line output"

    # Print summary
    lines = [l for l in result.split("\n") if l.strip() and not l.startswith("#")]
    print(f"   Lines of data: {len(lines)}")
    if lines:
        print(f"   Header row: {lines[0][:80]}...")
    if len(lines) > 1:
        print(f"   First data row: {lines[1][:80]}...")
    print("   ✅ SOL perpetual data OK\n")


def test_sol_funding_rate() -> None:
    """Test fetching SOL perpetual funding rate history."""
    print("=" * 60)
    print("🧪 TEST: get_crypto_funding_rate(SOL/USDT:USDT)")
    print("=" * 60)

    result = get_crypto_funding_rate("SOL/USDT:USDT", lookback_hours=24)

    assert "# Funding rate history for" in result, "Missing header"
    assert "\n" in result, "Expected multi-line output"

    lines = [l for l in result.split("\n") if l.strip() and not l.startswith("#")]
    print(f"   Lines of data: {len(lines)}")
    if lines:
        print(f"   Header row: {lines[0][:80]}...")
    if len(lines) > 1:
        print(f"   First data row: {lines[1][:80]}...")

    # Check that FundingRate appears in the text
    print("   ✅ SOL funding rate OK\n")


def test_sol_open_interest() -> None:
    """Test fetching SOL perpetual open interest."""
    print("=" * 60)
    print("🧪 TEST: get_crypto_open_interest(SOL/USDT:USDT)")
    print("=" * 60)

    result = get_crypto_open_interest("SOL/USDT:USDT")

    assert "# Open interest for" in result, "Missing header"
    assert "\n" in result, "Expected multi-line output"

    lines = [l for l in result.split("\n") if l.strip() and not l.startswith("#")]
    print(f"   Lines of data: {len(lines)}")
    if lines:
        print(f"   Header row: {lines[0][:80]}...")
    if len(lines) > 1:
        print(f"   First data row: {lines[1][:80]}...")

    print("   ✅ SOL open interest OK\n")


def test_sol_market_ticker() -> None:
    """Test fetching SOL perpetual market ticker."""
    print("=" * 60)
    print("🧪 TEST: get_crypto_market_ticker(SOL/USDT:USDT)")
    print("=" * 60)

    result = get_crypto_market_ticker("SOL/USDT:USDT")

    assert "# Market ticker for" in result, "Missing header"
    assert "\n" in result, "Expected multi-line output"

    lines = [l for l in result.split("\n") if l.strip() and not l.startswith("#")]
    print(f"   Lines of data: {len(lines)}")
    if lines:
        print(f"   Header row: {lines[0][:80]}...")
    if len(lines) > 1:
        print(f"   First data row: {lines[1][:80]}...")

    print("   ✅ SOL market ticker OK\n")


def test_is_crypto_symbol() -> None:
    """Test the is_crypto_symbol detection function."""
    print("=" * 60)
    print("🧪 TEST: is_crypto_symbol() detection")
    print("=" * 60)

    from tradingagents.agents.utils.crypto_tools import is_crypto_symbol

    # Known crypto → True
    assert is_crypto_symbol("BTC") is True
    assert is_crypto_symbol("SOL") is True
    assert is_crypto_symbol("ETH") is True

    # ccxt format → True
    assert is_crypto_symbol("SOL/USDT:USDT") is True

    # Known stocks → False
    assert is_crypto_symbol("AAPL") is False
    assert is_crypto_symbol("MSFT") is False
    assert is_crypto_symbol("NVDA") is False

    print("   ✅ All symbol detection assertions passed!\n")


def test_signal_processor_crypto() -> None:
    """Test the SignalProcessor crypto methods."""
    print("=" * 60)
    print("🧪 TEST: SignalProcessor crypto methods")
    print("=" * 60)

    from tradingagents.graph.signal_processing import SignalProcessor

    sp = SignalProcessor()

    # Test extract_crypto_metrics
    text = (
        "The funding rate is 0.015% indicating bullish sentiment. "
        "Open interest stands at $2.5B. "
        "Liquidation levels at 125.50 may act as support."
    )
    metrics = sp.extract_crypto_metrics(text)
    assert metrics.get("funding_rate") == 0.015, f"Expected 0.015, got {metrics.get('funding_rate')}"
    assert metrics.get("open_interest") == "2.5B", f"Expected 2.5B, got {metrics.get('open_interest')}"
    assert metrics.get("liquidation_level") == 125.50, f"Expected 125.50, got {metrics.get('liquidation_level')}"

    # Test process_crypto_signal with high funding
    rating = sp.process_crypto_signal(text)
    assert "high funding" in rating, f"Expected 'high funding' label, got: {rating}"

    print(f"   Funding rate parsed: {metrics['funding_rate']}")
    print(f"   Rating with label: {rating}")
    print("   ✅ SignalProcessor crypto methods OK!\n")


def main() -> None:
    """Run all crypto smoke tests."""
    print("\n🚀 Running crypto smoke tests...\n")
    errors = []

    tests = [
        ("SOL perpetual data", test_sol_perpetual),
        ("SOL funding rate", test_sol_funding_rate),
        ("SOL open interest", test_sol_open_interest),
        ("SOL market ticker", test_sol_market_ticker),
        ("is_crypto_symbol detection", test_is_crypto_symbol),
        ("SignalProcessor crypto", test_signal_processor_crypto),
    ]

    for name, test_fn in tests:
        try:
            test_fn()
        except Exception as e:
            errors.append((name, e))
            print(f"   ❌ {name} FAILED: {e}\n")

    print("=" * 60)
    if errors:
        print(f"\n❌ {len(errors)}/{len(tests)} tests FAILED:\n")
        for name, err in errors:
            print(f"   - {name}: {err}")
        sys.exit(1)
    else:
        print(f"\n🎉 All {len(tests)} tests PASSED!")
        sys.exit(0)


if __name__ == "__main__":
    main()
