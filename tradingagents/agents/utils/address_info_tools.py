from langchain_core.tools import tool
from typing import Annotated


@tool
def get_wallet_positions(
    address: Annotated[str, "Wallet address to query (e.g., 0x... for EVM, ... for Solana)"],
    chain_id: Annotated[str, "Chain ID: 56=BSC, 8453=Base"] = "56",
    offset: Annotated[int, "Pagination offset"] = 0,
) -> str:
    """Query all token holdings and positions for a wallet address.

    Returns token name, symbol, current price, 24h price change,
    and holding quantity for every token in the wallet.
    """
    import requests
    import os

    PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    PROXIES = {"http": PROXY, "https": PROXY} if PROXY else None
    headers = {
        "clienttype": "web",
        "clientversion": "1.2.0",
        "Accept-Encoding": "identity",
        "User-Agent": "binance-web3/1.1 (Skill)",
    }
    params = {"address": address, "chainId": chain_id, "offset": offset}
    url = "https://web3.binance.com/bapi/defi/v3/public/wallet-direct/buw/wallet/address/pnl/active-position-list/ai"
    try:
        resp = requests.get(url, params=params, headers=headers, proxies=PROXIES, timeout=15)
        data = resp.json()
        if not data.get("success"):
            return "Error: {}".format(data.get("message", "API request failed"))
        positions = data.get("data", {}).get("list", [])
        if not positions:
            return "No positions found for address {}...".format(address[:20])
        lines = [
            "| Token | Symbol | Price | 24h Change | Balance | Value (USD) |",
            "|-------|--------|-------|------------|---------|-------------|",
        ]
        for p in positions:
            name = p.get("name", "?")
            sym = p.get("symbol", "?")
            price = float(p.get("price", 0))
            chg = p.get("percentChange24h", "0")
            balance = float(p.get("remainQty", 0))
            value = price * balance
            lines.append("| {} | {} | ${:.6f} | {}% | {:.4f} | ${:.2f} |".format(name, sym, price, chg, balance, value))
        return "\n".join(lines)
    except Exception as e:
        return "Error fetching wallet positions: {}".format(e)
