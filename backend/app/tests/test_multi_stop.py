import json
import sqlite3

import pytest
from pydantic import ValidationError

from app.modules.multi_stop import calc_multi_stop
from app.modules.multi_stop.schemas import MultiStopRequest
from app.services import taxi_service

T = {"start_price": 11, "start_include_km": 3, "per_km": 2.5, "per_slow_min": 0.8, "night_factor": 1.2}
LEGS = [{"distance_km": 5, "slow_min": 2}, {"distance_km": 4, "slow_min": 1}]


def test_segments_summed_base_charged_once():
    r = calc_multi_stop(LEGS, False, T)
    assert r["segment_count"] == 2
    assert [s["seq"] for s in r["segments"]] == [1, 2]
    assert r["segments"][0] == {"seq": 1, "distance_km": 5.0, "slow_min": 2.0}
    assert r["distance_km"] == 9.0
    assert r["slow_min"] == 3.0
    assert r["start"] == 11.0  # 起步价全程只计一次
    assert r["mileage"] == 15.0  # (9 - 3) * 2.5
    assert r["slow_fee"] == 2.4
    assert r["total"] == 28.4


def test_night_factor_applies_to_summed_total():
    r = calc_multi_stop(LEGS, True, T)
    assert r["night"] is True
    assert r["total"] == 34.08  # 28.4 * 1.2


def test_negative_leg_rejected():
    with pytest.raises(ValueError):
        calc_multi_stop([{"distance_km": 5, "slow_min": 2}, {"distance_km": -1, "slow_min": 0}], False, T)
    with pytest.raises(ValueError):
        calc_multi_stop([{"distance_km": 5, "slow_min": 2}, {"distance_km": 1, "slow_min": -0.5}], False, T)


def test_single_segment_rejected():
    with pytest.raises(ValueError):
        calc_multi_stop([{"distance_km": 5, "slow_min": 2}], False, T)


def test_request_schema_enforces_order_rules():
    with pytest.raises(ValidationError):
        MultiStopRequest(segments=[{"distance_km": 1, "slow_min": 0}])
    with pytest.raises(ValidationError):
        MultiStopRequest(segments=[{"distance_km": 1, "slow_min": 0}, {"distance_km": 0, "slow_min": -2}])
    ok = MultiStopRequest(segments=LEGS, night=True, persist=False)
    assert len(ok.segments) == 2 and ok.persist is False


def _service(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
    CREATE TABLE tariff(id INTEGER PRIMARY KEY, start_price REAL, start_include_km REAL, per_km REAL, per_slow_min REAL, night_factor REAL);
    CREATE TABLE calc_runs(id INTEGER PRIMARY KEY, kind TEXT, trip_id INTEGER, input_json TEXT, result_json TEXT, created_at TEXT);
    """)
    conn.execute("INSERT INTO tariff VALUES (1,11,3,2.5,0.8,1.2)")
    monkeypatch.setattr(taxi_service, "connect", lambda: conn)
    return taxi_service.TaxiService(), conn


def _run_count(conn):
    return conn.execute("SELECT COUNT(*) c FROM calc_runs").fetchone()["c"]


def test_persist_writes_snapshot_with_segments(monkeypatch):
    s, conn = _service(monkeypatch)
    r = s.multi_fare(LEGS, False, True)
    assert r["run_id"]
    row = conn.execute("SELECT * FROM calc_runs WHERE id=?", (r["run_id"],)).fetchone()
    assert row["kind"] == "multi_stop"
    saved_in = json.loads(row["input_json"])
    assert [seg["distance_km"] for seg in saved_in["segments"]] == [5, 4]
    saved_out = json.loads(row["result_json"])
    assert saved_out["segment_count"] == 2
    assert [seg["seq"] for seg in saved_out["segments"]] == [1, 2]
    assert saved_out["total"] == 28.4


def test_readonly_trial_writes_nothing(monkeypatch):
    s, conn = _service(monkeypatch)
    r = s.multi_fare(LEGS, True, False)
    assert r["run_id"] is None
    assert r["total"] == 34.08
    assert _run_count(conn) == 0


def test_rejected_order_writes_nothing(monkeypatch):
    s, conn = _service(monkeypatch)
    with pytest.raises(ValueError):
        s.multi_fare([{"distance_km": 3, "slow_min": 1}], False, True)
    with pytest.raises(ValueError):
        s.multi_fare([{"distance_km": 3, "slow_min": 1}, {"distance_km": -2, "slow_min": 0}], False, True)
    assert _run_count(conn) == 0


def test_tariff_change_does_not_rewrite_stored_run(monkeypatch):
    s, conn = _service(monkeypatch)
    r = s.multi_fare(LEGS, False, True)
    conn.execute("UPDATE tariff SET per_km=99")
    row = conn.execute("SELECT * FROM calc_runs WHERE id=?", (r["run_id"],)).fetchone()
    saved = json.loads(row["result_json"])
    assert saved["total"] == 28.4
    assert [seg["distance_km"] for seg in saved["segments"]] == [5.0, 4.0]
    assert s.multi_fare(LEGS, False, False)["total"] == 607.4  # 新价只影响新单
