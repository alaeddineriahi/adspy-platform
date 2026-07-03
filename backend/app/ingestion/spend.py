"""
Spend estimation — the honest version of what "spend spy" tools sell.

Meta discloses exact spend ONLY for political ads. For commercial ads the
best anyone can do is estimate, so we do it transparently, from the two
things advertisers can't hide:

  • variant_count — each collated variant is an ad-set/budget duplication;
    advertisers only duplicate what converts, and each duplicate carries
    its own daily budget.
  • days_running — how long that budget has been flowing.

  est = variants × market daily budget/variant × days, published as a WIDE
  band (×0.35 .. ×1.3) and labeled "estimated" in the UI. Basis: "heuristic".

When we have REAL data — eu_total_reach from the DSA-mandated official API
(EU-delivered ads, e.g. our France sweep) — the estimate tightens to
reach × market CPM band. Basis: "reach".
"""

# Typical daily budget per duplicated ad set, USD — deliberately conservative.
_DAILY_PER_VARIANT_USD = {
    "US": 25.0, "CA": 20.0, "GB": 20.0, "AU": 20.0, "FR": 15.0,
    "SA": 12.0, "AE": 12.0, "KW": 10.0, "QA": 10.0,
    "TN": 5.0, "MA": 5.0, "DZ": 4.0, "EG": 4.0,
}
_DEFAULT_DAILY = 8.0

# CPM bands (USD per 1000 impressions) for the reach-based estimate.
_CPM_BAND_USD = {
    "US": (7.0, 18.0), "CA": (6.0, 14.0), "GB": (6.0, 15.0), "AU": (6.0, 14.0),
    "FR": (4.0, 10.0),
    "SA": (3.0, 8.0), "AE": (3.5, 9.0), "KW": (3.0, 8.0), "QA": (3.0, 8.0),
    "TN": (1.0, 3.0), "MA": (1.0, 3.0), "DZ": (0.8, 2.5), "EG": (0.8, 2.5),
}
_DEFAULT_CPM = (2.0, 6.0)


def _round_band(v: float) -> int:
    """Round to a credible display figure (2 significant-ish digits)."""
    if v < 100:
        return int(round(v, -1)) or 10
    if v < 1_000:
        return int(round(v, -2))
    if v < 10_000:
        return int(round(v, -2))
    return int(round(v, -3))


def estimate_spend(
    country: str,
    days: int,
    variants: int,
    eu_total_reach: int | None = None,
) -> tuple[int, int, str]:
    """Returns (min_usd, max_usd, basis) — basis is "reach" or "heuristic"."""
    if eu_total_reach and eu_total_reach > 0:
        lo_cpm, hi_cpm = _CPM_BAND_USD.get(country, _DEFAULT_CPM)
        # reach ≈ unique users; impressions run ~1.5-3x reach for DR campaigns.
        lo = eu_total_reach * 1.5 / 1000 * lo_cpm
        hi = eu_total_reach * 3.0 / 1000 * hi_cpm
        return _round_band(lo), _round_band(hi), "reach"

    daily = _DAILY_PER_VARIANT_USD.get(country, _DEFAULT_DAILY)
    spend_days = min(max(days, 1), 365)
    mid = max(1, variants) * daily * spend_days
    return _round_band(mid * 0.35), _round_band(mid * 1.3), "heuristic"
