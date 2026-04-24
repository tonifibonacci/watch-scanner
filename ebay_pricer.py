"""
ebay_pricer.py — scrapes eBay completed/sold listings to get real market prices.
No API key needed. Results are cached to disk to avoid repeated requests.

Usage:
    from ebay_pricer import get_market_price

    sell_target, source = get_market_price("seiko 6139")
    # sell_target → float or None
    # source      → "ebay" | "cache" | "fallback"
"""

import json
import time
import random
import re
import statistics
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# ── Config ─────────────────────────────────────────────────────────────────────

CACHE_FILE  = Path("ebay_price_cache.json")
CACHE_TTL_H = 24          # hours before a cached price is considered stale
MIN_SALES   = 3           # minimum sold listings needed to trust the price
MAX_PAGES   = 2           # pages of results to scrape per keyword (20 items/page)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── Cache helpers ──────────────────────────────────────────────────────────────

def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_cache(cache: dict):
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _cache_get(cache: dict, keyword: str):
    """Return cached price if fresh, else None."""
    entry = cache.get(keyword.lower())
    if not entry:
        return None
    try:
        ts = datetime.fromisoformat(entry["ts"])
        if datetime.utcnow() - ts < timedelta(hours=CACHE_TTL_H):
            return entry["price"]
    except Exception:
        pass
    return None


def _cache_set(cache: dict, keyword: str, price: float):
    cache[keyword.lower()] = {"price": round(price, 2), "ts": datetime.utcnow().isoformat()}

# ── eBay scraper ───────────────────────────────────────────────────────────────

def _build_url(keyword: str, page: int = 1) -> str:
    """
    eBay completed + sold listings search URL.
    LH_Complete=1  → completed listings
    LH_Sold=1      → sold only
    LH_ItemCondition=3000|4000|5000 → used/good/acceptable
    _sop=15        → sort by date (most recent first)
    """
    q = keyword.replace(" ", "+")
    offset = (page - 1) * 48
    return (
        f"https://www.ebay.com/sch/i.html"
        f"?_nkw={q}"
        f"&_sacat=0"
        f"&LH_Complete=1"
        f"&LH_Sold=1"
        f"&LH_ItemCondition=3000%7C4000%7C5000"
        f"&_sop=15"
        f"&_ipg=48"
        f"&_pgn={page}"
    )


def _parse_prices(html: str) -> list[float]:
    """Extract sold prices (EUR or USD) from eBay search results page."""
    soup = BeautifulSoup(html, "html.parser")
    prices = []

    for item in soup.select(".s-item"):
        # Skip the ghost "Shop on eBay" first item
        title_el = item.select_one(".s-item__title")
        if not title_el or "Shop on eBay" in title_el.text:
            continue

        price_el = item.select_one(".s-item__price")
        if not price_el:
            continue

        raw = price_el.get_text(" ", strip=True)

        # Handle ranges like "EUR 45.00 to EUR 80.00" → take midpoint
        range_match = re.findall(r"[\d,]+\.?\d*", raw.replace(",", ""))
        if not range_match:
            continue

        nums = [float(x) for x in range_match if float(x) > 1]
        if not nums:
            continue

        price = sum(nums) / len(nums)  # midpoint for ranges, single value otherwise

        # Convert USD to EUR (rough factor — good enough for deal scoring)
        if "US $" in raw or "USD" in raw:
            price *= 0.92

        prices.append(price)

    return prices


def _scrape_ebay(keyword: str) -> float | None:
    """
    Scrape eBay sold listings for `keyword`.
    Returns median sold price in EUR, or None if not enough data.
    """
    if not REQUESTS_AVAILABLE:
        return None

    all_prices = []

    for page in range(1, MAX_PAGES + 1):
        url = _build_url(keyword, page)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                break
            prices = _parse_prices(resp.text)
            all_prices.extend(prices)
        except Exception as e:
            print(f"    [ebay_pricer] request error ({keyword}, p{page}): {e}")
            break

        time.sleep(random.uniform(1.5, 3.0))

    if len(all_prices) < MIN_SALES:
        return None

    # Remove outliers: keep prices within 1.5× IQR
    all_prices.sort()
    q1 = all_prices[len(all_prices) // 4]
    q3 = all_prices[(len(all_prices) * 3) // 4]
    iqr = q3 - q1
    filtered = [p for p in all_prices if (q1 - 1.5 * iqr) <= p <= (q3 + 1.5 * iqr)]

    if len(filtered) < MIN_SALES:
        filtered = all_prices  # fallback: use all if filtering removes too much

    median = statistics.median(filtered)
    print(f"    [ebay_pricer] {keyword}: {len(filtered)} sales, median €{median:.0f}")
    return round(median, 2)

# ── Public API ─────────────────────────────────────────────────────────────────

_cache: dict = {}
_cache_loaded = False


def _ensure_cache():
    global _cache, _cache_loaded
    if not _cache_loaded:
        _cache = _load_cache()
        _cache_loaded = True


def get_market_price(keyword: str, fallback: float | None = None) -> tuple[float | None, str]:
    """
    Returns (price, source) where source is "cache", "ebay", or "fallback".
    `fallback` is the static PRICE_DB sell_target — returned if eBay data unavailable.
    """
    _ensure_cache()
    kw = keyword.lower()

    cached = _cache_get(_cache, kw)
    if cached is not None:
        return cached, "cache"

    price = _scrape_ebay(kw)
    if price is not None:
        _cache_set(_cache, kw, price)
        _save_cache(_cache)
        return price, "ebay"

    return fallback, "fallback"


def warm_cache(price_db: dict, force: bool = False):
    """
    Pre-fetches eBay prices for all keywords in PRICE_DB.
    Call this separately (e.g. once a day) rather than during every scan.
    Set force=True to refresh even if cache is fresh.
    """
    _ensure_cache()
    total = len(price_db)
    print(f"[ebay_pricer] Warming cache for {total} keywords...")

    for i, (keyword, (brand, min_buy, max_buy, sell_target)) in enumerate(price_db.items(), 1):
        kw = keyword.lower()
        if not force and _cache_get(_cache, kw) is not None:
            print(f"  [{i}/{total}] {keyword}: cached, skip")
            continue

        print(f"  [{i}/{total}] {keyword}...")
        price = _scrape_ebay(kw)
        if price:
            _cache_set(_cache, kw, price)
            _save_cache(_cache)

        # Polite delay between keywords
        time.sleep(random.uniform(3, 6))

    print("[ebay_pricer] Cache warm complete.")


def get_cache_stats(price_db: dict) -> dict:
    """Returns a summary of cache coverage."""
    _ensure_cache()
    total = len(price_db)
    fresh = sum(1 for kw in price_db if _cache_get(_cache, kw.lower()) is not None)
    stale_or_missing = total - fresh
    return {
        "total_keywords": total,
        "cached_fresh": fresh,
        "missing_or_stale": stale_or_missing,
        "coverage_pct": round(fresh / total * 100, 1) if total else 0,
    }
