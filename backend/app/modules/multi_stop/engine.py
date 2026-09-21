"""Multi-stop fare engine: ordered legs, one base fare, summed pricing."""

from app.engines.tariff_breakdown import calc_fare

MIN_SEGMENTS = 2


def calc_multi_stop(segments: list[dict], night: bool, tariff: dict) -> dict:
    """Price an ordered multi-stop trip against the current tariff.

    Legs are numbered consecutively from 1 in submission order. The base
    fare applies once for the whole trip: all leg kilometres and low-speed
    minutes are summed first, then priced with the night flag.

    Raises ValueError if any leg's km/low-speed is negative or fewer than
    two legs are given — the whole order is rejected and nothing may be
    persisted for it.
    """
    if len(segments) < MIN_SEGMENTS:
        raise ValueError(f"need at least {MIN_SEGMENTS} segments, got {len(segments)}")
    legs = []
    for seq, seg in enumerate(segments, start=1):
        km = float(seg["distance_km"])
        slow = float(seg["slow_min"])
        if km < 0 or slow < 0:
            raise ValueError(f"segment {seq} has negative distance_km/slow_min")
        legs.append({"seq": seq, "distance_km": round(km, 2), "slow_min": round(slow, 1)})
    total_km = sum(leg["distance_km"] for leg in legs)
    total_slow = sum(leg["slow_min"] for leg in legs)
    fare = calc_fare(total_km, total_slow, night, tariff)
    return {"segment_count": len(legs), "segments": legs, **fare}
