"""
warm_cache.py — run this once a day (separately from the main scan)
to pre-fetch eBay sold prices for all PRICE_DB keywords.

Usage:
    python warm_cache.py          # only fetches missing/stale
    python warm_cache.py --force  # refreshes everything
"""

import sys
from scanner import PRICE_DB
from ebay_pricer import warm_cache, get_cache_stats

force = "--force" in sys.argv

stats_before = get_cache_stats(PRICE_DB)
print(f"Cache before: {stats_before['cached_fresh']}/{stats_before['total_keywords']} ({stats_before['coverage_pct']}%)")

warm_cache(PRICE_DB, force=force)

stats_after = get_cache_stats(PRICE_DB)
print(f"Cache after:  {stats_after['cached_fresh']}/{stats_after['total_keywords']} ({stats_after['coverage_pct']}%)")
