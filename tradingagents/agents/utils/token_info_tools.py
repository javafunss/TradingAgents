from langchain_core.tools import tool
from typing import Annotated


@tool
def search_token(
    keyword: Annotated[str, "Search keyword: token name, symbol, or contract address"],
    chain_ids: Annotated[str, "Comma-separated chain IDs, e.g. '56,8453,CT_501'"] = "56,8453,CT_501",
) -> str:
    """Search for tokens by name, symbol, or contract address on Binance Web3.

    Searches across multiple chains (BSC, Base, Solana) and returns token
    metadata including price, volume, market cap, and holder data.
    """
    import requests
    import os

    PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    PROXIES = {"http": PROXY, "https": PROXY} if PROXY else None
    headers = {
        "Accept-Encoding": "identity",
        "User-Agent": "binance-web3/1.1 (Skill)",
    }
    params = {"keyword": keyword, "chainIds": chain_ids, "orderBy": "volume24h"}
    url = "https://web3.binance.com/bapi/defi/v5/public/wallet-direct/buw/wallet/market/token/search/ai"
    try:
        resp = requests.get(url, params=params, headers=headers, proxies=PROXIES, timeout=15)
        data = resp.json()
        if not data.get("success"):
            return "Error: {}".format(data.get("message", "API request failed"))
        tokens = data.get("data", [])
        if not tokens:
            return "No tokens found for '{}'.".format(keyword)
        lines = [
            "| Chain | Symbol | Name | Price | 24h Change | Volume | Market Cap | Holders |",
            "|-------|--------|------|-------|------------|--------|------------|---------|",
        ]
        for t in tokens[:10]:
            chain = t.get("chainId", "?")
            sym = t.get("symbol", "?")
            name = t.get("name", "?")
            price = t.get("price", "0")
            chg = t.get("percentChange24h", "0")
            vol = t.get("volume24h", "0")
            mc = t.get("marketCap", "0")
            holders = t.get("holders", "0")
            lines.append("| {} | {} | {} | ${} | {}% | ${} | ${} | {} |".format(chain, sym, name, price, chg, vol, mc, holders))
        return "\n".join(lines)
    except Exception as e:
        return "Error searching tokens: {}".format(e)


@tool
def get_token_market_data(
    chain_id: Annotated[str, "Chain ID: 56=BSC, 8453=Base, CT_501=Solana"],
    contract_address: Annotated[str, "Token contract address"],
) -> str:
    """Get real-time market data for a specific token on Binance Web3.

    Returns price, 24h change, volume, liquidity, market cap, holder count,
    and top 10% holder concentration.
    """
    import requests
    import os

    PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    PROXIES = {"http": PROXY, "https": PROXY} if PROXY else None
    headers = {
        "Accept-Encoding": "identity",
        "User-Agent": "binance-web3/1.1 (Skill)",
    }
    params = {"chainId": chain_id, "contractAddress": contract_address}
    url = "https://web3.binance.com/bapi/defi/v5/public/wallet-direct/buw/wallet/market/token/detail/ai"
    try:
        resp = requests.get(url, params=params, headers=headers, proxies=PROXIES, timeout=15)
        data = resp.json()
        if not data.get("success"):
            return "Error: {}".format(data.get("message", "API request failed"))
        detail = data.get("data", {})
        lines = [
            "**Token Market Data**",
            "",
            "- **Symbol**: {}".format(detail.get("symbol", "?")),
            "- **Name**: {}".format(detail.get("name", "?")),
            "- **Price**: ${}".format(detail.get("price", "0")),
            "- **24h Change**: {}%".format(detail.get("percentChange24h", "0")),
            "- **Volume 24h**: ${}".format(detail.get("volume24h", "0")),
            "- **Liquidity**: ${}".format(detail.get("liquidity", "0")),
            "- **Market Cap**: ${}".format(detail.get("marketCap", "0")),
            "- **Holders**: {}".format(detail.get("holders", "0")),
            "- **Top 10% Holders**: {}%".format(detail.get("holdersTop10Percent", "0")),
            "- **Chain**: {}".format(chain_id),
            "- **Contract**: {}...{}".format(contract_address[:20], contract_address[-6:]),
        ]
        return "\n".join(lines)
    except Exception as e:
        return "Error fetching token market data: {}".format(e)


@tool
def get_token_kline(
    chain_id: Annotated[str, "Chain ID: 56=BSC, 8453=Base, CT_501=Solana"],
    contract_address: Annotated[str, "Token contract address"],
    interval: Annotated[str, "Kline interval: 1m, 5m, 15m, 30m, 1h, 4h, 1d"] = "1h",
    limit: Annotated[int, "Number of candles to return (max 500)"] = 100,
) -> str:
    """Get K-Line candlestick chart data for a token from Binance Web3.

    Returns OHLCV data for technical analysis.
    """
    import requests
    import os
    from datetime import datetime

    PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    PROXIES = {"http": PROXY, "https": PROXY} if PROXY else None
    headers = {
        "Accept-Encoding": "identity",
        "User-Agent": "binance-web3/1.1 (Skill)",
    }
    params = {
        "chainId": chain_id,
        "contractAddress": contract_address,
        "interval": interval,
        "limit": limit,
    }
    url = "https://web3.binance.com/bapi/defi/v5/public/wallet-direct/buw/wallet/market/token/kline/ai"
    try:
        resp = requests.get(url, params=params, headers=headers, proxies=PROXIES, timeout=15)
        data = resp.json()
        if not data.get("success"):
            return "Error: {}".format(data.get("message", "API request failed"))
        candles = data.get("data", [])
        if not candles:
            return "No K-Line data for contract {}".format(contract_address)
        lines = [
            "## K-Line Data ({}) - Token {}...".format(interval, contract_address[:10]),
            "Timestamp,Open,High,Low,Close,Volume",
        ]
        for c in candles[-limit:]:
            if c.get("openTime"):
                ts = datetime.fromtimestamp(c["openTime"] / 1000).strftime("%Y-%m-%d %H:%M")
            else:
                ts = "?"
            lines.append("{},{},{},{},{},{}".format(
                ts,
                c.get("open", 0),
                c.get("high", 0),
                c.get("low", 0),
                c.get("close", 0),
                c.get("volume", 0),
            ))
        return "\n".join(lines)
    except Exception as e:
        return "Error fetching K-Line data: {}".format(e)


@tool
def audit_token_security(
    binance_chain_id: Annotated[str, "Binance chain ID: CT_501=Solana, 56=BSC, 8453=Base, 1=Ethereum"],
    contract_address: Annotated[str, "Token contract address to audit"],
) -> str:
    """Run a comprehensive security audit on a token contract.

    Detects honeypots, rug pulls, malicious functions, ownership risks,
    and unusual buy/sell taxes before trading.
    """
    import requests
    import os
    import uuid

    PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    PROXIES = {"http": PROXY, "https": PROXY} if PROXY else None
    headers = {
        "Content-Type": "application/json",
        "source": "agent",
        "Accept-Encoding": "identity",
        "User-Agent": "binance-web3/1.4 (Skill)",
    }
    payload = {
        "binanceChainId": binance_chain_id,
        "contractAddress": contract_address,
        "requestId": str(uuid.uuid4()),
    }
    url = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/security/token/audit"
    try:
        resp = requests.post(url, json=payload, headers=headers, proxies=PROXIES, timeout=15)
        data = resp.json()
        if not data.get("success"):
            return "Error: {}".format(data.get("message", "Audit API request failed"))
        audit = data.get("data", {})
        risk = audit.get("riskLevel", "unknown")
        lines = [
            "## Token Security Audit - {}...".format(contract_address[:20]),
            "",
            "**Risk Level**: {}".format(risk),
            "**Safe**: {}".format("\u2705" if audit.get("isSafe") else "\u274c"),
            "**Honeypot**: {}".format("\u26a0\ufe0f Detected" if audit.get("isHoneypot") else "\u2705 Clean"),
            "**Can Sell**: {}".format("\u2705 Yes" if audit.get("canSell") else "\u274c No"),
            "**Is Token**: {}".format("\u2705 Yes" if audit.get("isToken") else "\u274c No"),
            "**Is In-DEX**: {}".format("\u2705 Yes" if audit.get("isInDex") else "\u274c No"),
            "**Buy Tax**: {}%".format(audit.get("buyTax", "?")),
            "**Sell Tax**: {}%".format(audit.get("sellTax", "?")),
            "**Owner Balance**: {}".format(audit.get("ownerBalance", "?")),
            "**Owner Change Balance**: {}".format(audit.get("ownerChangeBalance", "?")),
            "**Total Supply**: {}".format(audit.get("totalSupply", "?")),
        ]
        if audit.get("scamCategory"):
            lines.append("**Scam Category**: {}".format(audit.get("scamCategory")))
        if audit.get("cautionInfo"):
            caution = audit.get("cautionInfo", [])
            if isinstance(caution, list):
                for c in caution[:5]:
                    if isinstance(c, dict):
                        name = c.get("name", "Risk")
                        desc = c.get("desc", "")
                        lines.append("**\u26a0\ufe0f {}**: {}".format(name, desc))
        return "\n".join(lines)
    except Exception as e:
        return "Error auditing token security: {}".format(e)
