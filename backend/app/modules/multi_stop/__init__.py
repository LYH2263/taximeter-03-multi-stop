"""multi_stop: one meter run over ordered stops.

Segments are validated and numbered from 1, then all km and slow minutes
are summed before pricing, so the start price is charged exactly once.
"""
from app.engines.tariff_breakdown import calc_fare

MIN_SEGMENTS = 2


class MultiStopError(ValueError):
    """Whole order rejected; nothing may be persisted."""


def normalize_segments(segments) -> list[dict]:
    if not segments or len(segments) < MIN_SEGMENTS:
        raise MultiStopError(f"至少需要{MIN_SEGMENTS}段行程")
    out = []
    for i, seg in enumerate(segments, start=1):
        km = float(seg["distance_km"])
        slow = float(seg["slow_min"])
        if km < 0 or slow < 0:
            raise MultiStopError(f"第{i}段公里或低速不能为负")
        out.append({"seq": i, "distance_km": round(km, 2), "slow_min": round(slow, 1)})
    return out


def calc_multi_stop(segments, night: bool, tariff: dict) -> dict:
    segs = normalize_segments(segments)
    total_km = round(sum(s["distance_km"] for s in segs), 2)
    total_slow = round(sum(s["slow_min"] for s in segs), 1)
    fare = calc_fare(total_km, total_slow, night, tariff)
    return {
        "segment_count": len(segs),
        "segments": segs,
        "distance_km": total_km,
        "slow_min": total_slow,
        "night": night,
        "night_factor": fare["night_factor"],
        "start": fare["start"],
        "mileage": fare["mileage"],
        "slow_fee": fare["slow_fee"],
        "total": fare["total"],
    }
