from langchain_core.tools import tool
from typing import Annotated


@tool
def get_trending_tokens(
    chain_id: Annotated[str, "Chain ID: 56=BSC, 8453=Base, CT_501=Solana"] = "56",
    period: Annotated[int, "Time period: 10=1m, 20=5m, 30=1h, 40=4h, 50=24h"] = 50,
    page: Annotated[int, "Page number"] = 1,
    size: Annotated[int, "Page size (max 200)"] = 20,
) -> str:
    """Get trending/popular token rankings from Binance Web3 market data.

    Uses Binance's unified token rank API to find hot trending tokens across multiple chains.
    """
    import requests
    import os

    PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    PROXIES = {"http": PROXY, "https": PROXY} if PROXY else None
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "binance-web3/2.1 (Skill)",
        "Accept-Encoding": "identity",
    }
    payload = {
        "rankType": 10,
        "chainId": chain_id,
        "period": period,
        "sortBy": 70,
        "orderAsc": False,
        "page": page,
        "size": size,
    }
    url = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/unified/rank/list/ai"
    try:
        resp = requests.post(url, json=payload, headers=headers, proxies=PROXIES, timeout=15)
        data = resp.json()
        if not data.get("success"):
            return "Error: {}".format(data.get("message", "API request failed"))
        tokens = data.get("data", {}).get("tokens", [])
        if not tokens:
            return "No trending tokens found."
        lines = [
            "| Rank | Symbol | Price | 24h Change | Volume | Market Cap | Holders |",
            "|------|--------|-------|------------|--------|------------|---------|",
        ]
        for i, t in enumerate(tokens[:20], 1):
            sym = t.get("symbol", "?")
            price = t.get("price", "0")
            chg = t.get("percentChange24h", "0")
            vol = t.get("volume24h", "0")
            mc = t.get("marketCap", "0")
            holders = t.get("holders", "0")
            lines.append("| {} | {} | ${} | {}% | ${} | ${} | {} |".format(i, sym, price, chg, vol, mc, holders))
        return "\n".join(lines)
    except Exception as e:
        return "Error fetching trending tokens: {}".format(e)


@tool
def get_social_hype_rank(
    chain_id: Annotated[str, "Chain ID: 56=BSC, 8453=Base, CT_501=Solana"] = "56",
    sentiment: Annotated[str, "Sentiment filter: All, Positive, Negative, Neutral"] = "All",
    target_language: Annotated[str, "Translation target language: en, zh"] = "en",
) -> str:
    """Get social media hype and sentiment rankings for tokens from Binance Web3.

    Shows which tokens have the highest social buzz, sentiment analysis,
    and AI-generated social summaries.
    """
    import requests
    import os

    PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    PROXIES = {"http": PROXY, "https": PROXY} if PROXY else None
    headers = {
        "Accept-Encoding": "identity",
        "User-Agent": "binance-web3/2.1 (Skill)",
    }
    params = {
        "chainId": chain_id,
        "sentiment": sentiment,
        "targetLanguage": target_language,
        "timeRange": 1,
        "socialLanguage": "ALL",
    }
    url = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/social/hype/rank/leaderboard/ai"
    try:
        resp = requests.get(url, params=params, headers=headers, proxies=PROXIES, timeout=15)
        data = resp.json()
        if not data.get("success"):
            return "Error: {}".format(data.get("message", "API request failed"))
        items = data.get("data", {}).get("leaderBoardList", [])
        if not items:
            return "No social hype data found."
        lines = [
            "| Rank | Symbol | Sentiment | Hype Score | Price Change | Market Cap | Summary |",
            "|------|--------|-----------|------------|--------------|------------|---------|",
        ]
        for i, item in enumerate(items[:15], 1):
            meta = item.get("metaInfo", {})
            market = item.get("marketInfo", {})
            social = item.get("socialHypeInfo", {})
            sym = meta.get("symbol", "?")
            sent = social.get("sentiment", "?")
            hype = social.get("socialHype", 0)
            chg = market.get("priceChange", 0)
            mc = market.get("marketCap", 0)
            summary = social.get("socialSummaryBriefTranslated") or social.get("socialSummaryBrief", "")
            lines.append("| {} | {} | {} | {} | {}% | ${} | {} |".format(i, sym, sent, hype, chg, mc, summary[:60]))
        return "\n".join(lines)
    except Exception as e:
        return "Error fetching social hype data: {}".format(e)
