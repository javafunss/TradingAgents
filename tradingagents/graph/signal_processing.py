"""Extract the 5-tier portfolio rating from the Portfolio Manager's decision.

The Portfolio Manager produces a typed ``PortfolioDecision`` via structured
output and renders it to markdown that always carries a ``**Rating**: X``
header (see :func:`tradingagents.agents.schemas.render_pm_decision`).  The
deterministic heuristic in :mod:`tradingagents.agents.utils.rating` is more
than sufficient to extract that rating; no extra LLM call is needed.

This module exists for backwards compatibility with callers that expect a
``SignalProcessor.process_signal(text)`` interface.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from tradingagents.agents.utils.rating import parse_rating

# Regex to extract crypto-specific metrics from a full signal / report text
_FUNDING_RATE_RE = re.compile(
    r"funding\s*rate[\s:]*(-?[\d.]+%?)", re.IGNORECASE
)
_OPEN_INTEREST_RE = re.compile(
    r"open\s*interest[\s:]*[$]?([\d,]+(?:\.[\d]+)?[KMBT]?)", re.IGNORECASE
)
_LIQUIDATION_RE = re.compile(
    r"liquidation\s*(?:level|price|zone)[\s:]*[$]?([\d,]+(?:\.[\d]+)?)",
    re.IGNORECASE,
)


class SignalProcessor:
    """Read the 5-tier rating out of a Portfolio Manager decision.

    Also provides crypto-specific methods for Funding Rate, Liquidation
    levels, and Open Interest metric extraction.
    """

    def __init__(self, quick_thinking_llm: Any = None):
        # The LLM argument is accepted for backwards compatibility but no
        # longer used: the PM's structured output guarantees the rating is
        # parseable from the rendered markdown without a second LLM call.
        self.quick_thinking_llm = quick_thinking_llm

    def process_signal(self, full_signal: str) -> str:
        """Return one of Buy / Overweight / Hold / Underweight / Sell."""
        return parse_rating(full_signal)

    # ------------------------------------------------------------------
    # Crypto-specific methods
    # ------------------------------------------------------------------

    def process_crypto_signal(self, full_signal: str) -> str:
        """Process a crypto trading signal, incorporating funding rate and
        liquidation-level context if present.

        Returns the base rating enriched with an edge label when crypto
        metrics push the decision (e.g. "Sell (high funding)").

        Args:
            full_signal: Complete trading signal or PM decision text.

        Returns:
            Rating string with optional crypto-context note.
        """
        rating = self.process_signal(full_signal)

        metrics = self.extract_crypto_metrics(full_signal)
        edge_label = self._crypto_edge_label(metrics)

        if edge_label:
            return f"{rating} ({edge_label})"
        return rating

    def extract_crypto_metrics(self, text: str) -> dict:
        """Extract crypto-specific metrics from a signal or report text.

        Args:
            text: Full report or signal text to search.

        Returns:
            Dict with keys:
              - ``funding_rate`` (float | None): the last matched funding rate
              - ``open_interest`` (str | None): raw OI value string
              - ``liquidation_level`` (float | None): parsed liquidation level
        """
        metrics: dict = {}

        # Funding rate
        fr_match = _FUNDING_RATE_RE.search(text)
        if fr_match:
            raw = fr_match.group(1).replace("%", "")
            try:
                metrics["funding_rate"] = float(raw)
            except ValueError:
                metrics["funding_rate"] = None

        # Open interest
        oi_match = _OPEN_INTEREST_RE.search(text)
        if oi_match:
            metrics["open_interest"] = oi_match.group(1)

        # Liquidation level
        liq_match = _LIQUIDATION_RE.search(text)
        if liq_match:
            raw = liq_match.group(1).replace(",", "")
            try:
                metrics["liquidation_level"] = float(raw)
            except ValueError:
                metrics["liquidation_level"] = None

        return metrics

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _crypto_edge_label(metrics: dict) -> Optional[str]:
        """Return an edge-label string when crypto metrics justify one.

        Signals:
          - ``funding_rate > 0.01%`` → "high funding" (overheated longs)
          - ``funding_rate < -0.01%`` → "neg funding" (short squeeze risk)

        Args:
            metrics: Output of :meth:`extract_crypto_metrics`.

        Returns:
            Short label or None.
        """
        fr = metrics.get("funding_rate")
        if fr is None:
            return None
        if fr > 0.01:
            return "high funding"
        if fr < -0.01:
            return "neg funding"
        return None
