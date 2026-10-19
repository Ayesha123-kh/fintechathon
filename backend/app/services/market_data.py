"""Free / open market data sources used by the shared agent teams (via MCP)."""

import asyncio
import ipaddress
import json
import logging
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.core.cache import redis

log = logging.getLogger(__name__)
UA = {"User-Agent": "Mozilla/5.0 (compatible; BachatResearchBot/1.0)"}
TOLA_GRAMS = 11.6638
TROY_OUNCE_GRAMS = 31.1035

COINGECKO_IDS = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin", "XRP": "ripple",
    "ADA": "cardano", "DOGE": "dogecoin", "USDT": "tether", "TON": "the-open-network", "AVAX": "avalanche-2",
}


async def _cached(key: str, ttl: int, fn) -> Any:
    hit = await redis.get(key)
    if hit:
        return json.loads(hit)
    value = await fn()
    await redis.set(key, json.dumps(value, default=str), ex=ttl)
    return value


async def _get_json(url: str, **kw) -> Any:
    async with httpx.AsyncClient(timeout=20, headers=UA, follow_redirects=True) as c:
        r = await c.get(url, **kw)
        r.raise_for_status()
        return r.json()


async def fx_rates(base: str = "USD") -> dict:
    async def fetch():
        data = await _get_json(f"https://open.er-api.com/v6/latest/{base.upper()}")
        return {"base": base.upper(), "rates": {k: data["rates"][k] for k in ("PKR", "USD", "EUR", "GBP", "AED", "SAR")
                                                 if k in data["rates"]}, "as_of": data.get("time_last_update_utc")}
    return await _cached(f"fx:{base}", 3600, fetch)


async def metal_price(symbol: str) -> dict:
    """XAU / XAG spot in USD/oz plus the Pakistani per-tola equivalent (spot, before local premium)."""
    symbol = symbol.upper().replace("GOLD_TOLA_PK", "XAU").replace("SILVER_TOLA_PK", "XAG")

    async def fetch():
        data = await _get_json(f"https://api.gold-api.com/price/{symbol}")
        usd_oz = float(data["price"])
        pkr = (await fx_rates("USD"))["rates"].get("PKR")
        out = {"symbol": symbol, "usd_per_oz": usd_oz, "updated": data.get("updatedAt")}
        if pkr:
            out["pkr_per_tola_spot"] = round(usd_oz * pkr / TROY_OUNCE_GRAMS * TOLA_GRAMS, 0)
            out["note"] = "Spot conversion; local sarafa rates include premiums. Verify with sarafa association."
        return out
    return await _cached(f"metal:{symbol}", 600, fetch)


async def crypto_prices(symbols: list[str]) -> dict:
    ids = [COINGECKO_IDS.get(s.upper(), s.lower()) for s in symbols]

    async def fetch():
        data = await _get_json(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": ",".join(ids), "vs_currencies": "usd,pkr", "include_24hr_change": "true",
                    "include_market_cap": "true"},
        )
        rev = {v: k for k, v in COINGECKO_IDS.items()}
        return {rev.get(k, k.upper()): v for k, v in data.items()}
    return await _cached(f"crypto:{','.join(sorted(ids))}", 120, fetch)


async def psx_quote(symbol: str) -> dict:
    """Latest quote from the PSX data portal company page."""
    symbol = symbol.upper()

    async def fetch():
        async with httpx.AsyncClient(timeout=20, headers=UA, follow_redirects=True) as c:
            r = await c.get(f"https://dps.psx.com.pk/company/{symbol}")
        if r.status_code != 200:
            return {"symbol": symbol, "error": f"PSX returned {r.status_code} (unknown symbol?)"}
        soup = BeautifulSoup(r.text, "lxml")
        close = soup.select_one(".quote__close")
        change = soup.select_one(".quote__change")
        stats = {}
        for item in soup.select(".stats_item"):
            parts = [p.get_text(" ", strip=True) for p in item.find_all(recursive=False)]
            if len(parts) >= 2 and parts[0]:
                key = parts[0].replace(" ^", "").lower()
                # The page repeats the block per market (REG/FUT/ODL); keep the first non-zero value.
                if key not in stats or stats[key] in ("0", "0.00"):
                    stats[key] = parts[1]
        if not close:
            return {"symbol": symbol, "error": "quote not found on page"}
        return {"symbol": symbol, "price": close.get_text(strip=True).replace("Rs.", "").strip(),
                "change": change.get_text(" ", strip=True) if change else None,
                "open": stats.get("open"), "high": stats.get("high"), "low": stats.get("low"),
                "volume": stats.get("volume"), "previous_close": stats.get("ldcp"),
                "52_week_range": stats.get("52-week range"), "circuit_breaker": stats.get("circuit breaker"),
                "source": f"https://dps.psx.com.pk/company/{symbol}"}
    return await _cached(f"psx:{symbol}", 120, fetch)


async def psx_history(symbol: str) -> dict:
    """Recent daily closes for a PSX ticker (Yahoo Finance .KA listing)."""
    data = await global_quote(f"{symbol.upper()}.KA", "3mo")
    # Yahoo's "price" for .KA listings can be stale; the daily closes are what we use.
    return {"symbol": symbol.upper(), "currency": "PKR", "range": "3mo",
            "range_change_pct": data.get("range_change_pct"), "closes": data.get("closes")}


async def global_quote(symbol: str, range_: str = "1mo") -> dict:
    """US/global equities and ETFs via Yahoo Finance's public chart endpoint."""
    symbol = symbol.upper()

    async def fetch():
        data = await _get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                               params={"range": range_, "interval": "1d"})
        res = data["chart"]["result"][0]
        meta = res["meta"]
        closes = [c for c in res["indicators"]["quote"][0].get("close", []) if c is not None]
        change = (closes[-1] / closes[0] - 1) * 100 if len(closes) > 1 else None
        return {"symbol": symbol, "currency": meta.get("currency"), "price": meta.get("regularMarketPrice"),
                "previous_close": meta.get("chartPreviousClose"), "range": range_,
                "range_change_pct": round(change, 2) if change is not None else None,
                "closes": [round(c, 2) for c in closes[-30:]]}
    return await _cached(f"yq:{symbol}:{range_}", 600, fetch)


async def web_search(query: str, max_results: int = 8, news: bool = False) -> list[dict]:
    from ddgs import DDGS

    def run():
        with DDGS() as d:
            if news:
                return list(d.news(query, max_results=max_results, region="pk-en"))
            return list(d.text(query, max_results=max_results, region="pk-en"))
    try:
        results = await asyncio.to_thread(run)
    except Exception as exc:
        log.warning("search failed: %s", exc)
        return [{"error": str(exc)}]
    return [{"title": r.get("title"), "url": r.get("href") or r.get("url"), "snippet": r.get("body"),
             "date": r.get("date"), "source": r.get("source")} for r in results]


FETCH_MAX_BYTES = 3 * 1024 * 1024
FETCH_MAX_REDIRECTS = 5


async def _public_address(host: str) -> bool:
    """True only when every address the name resolves to is on the public internet."""
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, None)
    except OSError:
        return False
    if not infos:
        return False
    for *_, sockaddr in infos:
        ip = ipaddress.ip_address(str(sockaddr[0]).split("%")[0])
        if ip.version == 6 and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if not ip.is_global or ip.is_multicast:
            return False
    return True


async def _refusal(url: httpx.URL) -> str | None:
    """Why the bots may not fetch this URL, or None when they may."""
    if url.scheme not in ("http", "https"):
        return "only http(s) URLs"
    if url.port not in (None, 80, 443):
        return "only the standard web ports"
    if not url.host or not await _public_address(url.host):
        return "that address is on a private or internal network"
    return None


async def fetch_url(url: str, max_chars: int = 12000) -> dict:
    """Read a public web page for the deal and research bots. They read untrusted pages that could try to steer them
    at internal services, so only public addresses on the standard web ports are fetched, every redirect is checked
    again, and at most FETCH_MAX_BYTES are read. (A name that resolves differently between the check and the
    request could still slip through; that needs control of a domain's DNS.)"""
    try:
        target = httpx.URL(url)
    except httpx.InvalidURL:
        return {"error": "invalid URL"}
    try:
        async with httpx.AsyncClient(timeout=25, headers=UA, follow_redirects=False) as c:
            for _ in range(FETCH_MAX_REDIRECTS + 1):
                if reason := await _refusal(target):
                    return {"url": str(target), "error": reason}
                async with c.stream("GET", target) as r:
                    if r.is_redirect and "location" in r.headers:
                        target = target.join(r.headers["location"])
                        continue
                    body = bytearray()
                    async for chunk in r.aiter_bytes():
                        body += chunk
                        if len(body) > FETCH_MAX_BYTES:
                            break
                    status, ctype, final, encoding = r.status_code, r.headers.get("content-type", ""), r.url, r.encoding
                break
            else:
                return {"url": str(target), "error": "too many redirects"}
    except httpx.HTTPError as exc:
        return {"url": url, "error": str(exc)}
    html = bytes(body[:FETCH_MAX_BYTES]).decode(encoding or "utf-8", errors="replace")
    if "json" in ctype:
        return {"url": str(final), "status": status, "text": html[:max_chars]}
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "form"]):
        tag.decompose()
    title = soup.title.get_text(strip=True) if soup.title else ""
    text = re.sub(r"\n{3,}", "\n\n", soup.get_text("\n", strip=True))
    links = []
    for a in soup.find_all("a", href=True)[:300]:
        label = a.get_text(" ", strip=True)
        href = a["href"]
        if label and re.search(r"deal|discount|offer|promo|sale|card|instagram|facebook|tiktok", label + href, re.IGNORECASE):
            links.append({"text": label[:80], "href": str(final.join(href))})
    return {"url": str(final), "status": status, "title": title, "text": text[:max_chars],
            "relevant_links": links[:40]}
