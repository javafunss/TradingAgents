from langchain_core.tools import tool
from typing import Annotated


@tool
def get_rwa_stock_list(
    token_type: Annotated[int, "Filter by type: 1=Ondo Finance (omit for all)"] = 1,
) -> str:
    """List all tokenized US stocks available on Binance Web3 (Ondo Finance RWA tokens).

    Returns ticker, chain info, contract address, token symbol, and shares multiplier.
    Each token represents 'multiplier' shares of the underlying stock.
    """
    import requests
    import os

    PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    PROXIES = {"http": PROXY, "https": PROXY} if PROXY else None
    headers = {
        "Accept-Encoding": "identity",
        "User-Agent": "binance-web3/1.1 (Skill)",
    }
    params = {"type": token_type} if token_type else {}
    url = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/rwa/stock/detail/list/ai"
    try:
        resp = requests.get(url, params=params, headers=headers, proxies=PROXIES, timeout=15)
        data = resp.json()
        if not data.get("success"):
            return "Error: {}".format(data.get("message", "API request failed"))
        stocks = data.get("data", [])
        if not stocks:
            return "No tokenized stocks found."
        lines = [
            "| Stock Ticker | Token Symbol | Chain | Contract Address | Multiplier |",
            "|-------------|--------------|-------|------------------|------------|",
        ]
        for s in stocks:
            ticker = s.get("ticker", "?")
            sym = s.get("symbol", "?")
            chain = "ETH" if s.get("chainId") == "1" else "BSC" if s.get("chainId") == "56" else s.get("chainId", "?")
            addr = s.get("contractAddress", "?")
            mult = s.get("multiplier", "1.0")
            lines.append("| {} | {} | {} | {}... | {} |".format(ticker, sym, chain, addr[:20], mult))
        return "\n".join(lines)
    except Exception as e:
        return "Error fetching RWA stock list: {}".format(e)


@tool
def get_rwa_stock_data(
    chain_id: Annotated[str, "Chain ID: 1=Ethereum, 56=BSC"],
    contract_address: Annotated[str, "Token contract address"],
) -> str:
    """Get real-time on-chain data for a tokenized US stock.

    Returns on-chain price, holder count, circulating supply, US stock market
    fundamentals (P/E ratio, dividend yield, 52-week range), and order limits.
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
    url = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/rwa/dynamic/v2/ai"
    try:
        resp = requests.get(url, params=params, headers=headers, proxies=PROXIES, timeout=15)
        data = resp.json()
        if not data.get("success"):
            return "Error: {}".format(data.get("message", "API request failed"))
        info = data.get("data", {})
        lines = [
            "**Tokenized Stock Data**",
            "",
            "- **Ticker**: {}".format(info.get("ticker", "?")),
            "- **Token Symbol**: {}".format(info.get("symbol", "?")),
            "- **On-Chain Price**: ${}".format(info.get("price", "0")),
            "- **Reference Price**: ${} (adjusted by multiplier)".format(info.get("referencePrice", "0")),
            "- **Shares Multiplier**: {}x".format(info.get("sharesMultiplier", "1")),
            "- **Holder Count**: {}".format(info.get("holderCount", "0")),
            "- **Circulating Supply**: {}".format(info.get("circulatingSupply", "0")),
            "- **Total Supply**: {}".format(info.get("totalSupply", "0")),
            "- **Market Cap**: ${}".format(info.get("marketCap", "0")),
            "- **24h Change**: {}%".format(info.get("percentChange24h", "0")),
            "- **Price/Earnings (P/E)**: {}".format(info.get("pe", "N/A")),
            "- **Dividend Yield**: {}%".format(info.get("dividendYield", "N/A")),
            "- **52-Week High**: ${}".format(info.get("high52w", "N/A")),
            "- **52-Week Low**: ${}".format(info.get("low52w", "N/A")),
            "- **Min Order**: {} tokens".format(info.get("minOrderQty", "?")),
            "- **Max Order**: {} tokens".format(info.get("maxOrderQty", "?")),
        ]
        return "\n".join(lines)
    except Exception as e:
        return "Error fetching RWA stock data: {}".format(e)
