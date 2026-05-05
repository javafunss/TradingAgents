from langchain_core.tools import tool
from typing import Annotated


@tool
def get_smart_money_signals(
    chain_id: Annotated[str, "Chain ID: CT_501=Solana, 56=BSC"] = "CT_501",
    page: Annotated[int, "Page number, starting from 1"] = 1,
    page_size: Annotated[int, "Items per page (max 100)"] = 20,
) -> str:
    """Get on-chain Smart Money trading signals from Binance Web3.

    Tracks buying and selling activities of professional/smart money addresses.
    Returns signal type (buy/sell), trigger price, current price, max gain, and exit rate.
    """
    import requests
    import os

    PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    PROXIES = {"http": PROXY, "https": PROXY} if PROXY else None
    headers = {
        "Content-Type": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": "binance-web3/1.1 (Skill)",
    }
    payload = {"page": page, "pageSize": page_size, "chainId": chain_id}
    url = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/web/signal/smart-money/ai"
    try:
        resp = requests.post(url, json=payload, headers=headers, proxies=PROXIES, timeout=15)
        data = resp.json()
        if not data.get("success"):
            return "Error: {}".format(data.get("message", "API request failed"))
        signals = data.get("data", [])
        if not signals:
            return "No smart money signals available."
        lines = [
            "| # | Token | Signal | Trigger Price | Current Price | Max Gain | Exit Rate |",
            "|---|-------|--------|---------------|---------------|----------|-----------|",
        ]
        for i, s in enumerate(signals[:20], 1):
            ticker = s.get("ticker", "?")
            sig_type = s.get("operateType", "?")
            trigger = s.get("triggerPrice", "0")
            current = s.get("price", "0")
            max_gain = s.get("maxGain", "0")
            exit_rate = s.get("exitRate", "0")
            lines.append("| {} | {} | {} | ${} | ${} | {}% | {}% |".format(
                i, ticker, sig_type, trigger, current, max_gain, exit_rate,
            ))
        return "\n".join(lines)
    except Exception as e:
        return "Error fetching smart money signals: {}".format(e)
