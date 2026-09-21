import json
import sqlite3

import pytest

from app.modules.multi_stop import MultiStopError, calc_multi_stop
from app.services.taxi_service import TaxiService

T = {"start_price": 11, "start_include_km": 3, "per_km": 2.5, "per_slow_min": 0.8, "night_factor": 1.2}
TWO = [{"distance_km": 2, "slow_min": 1}, {"distance_km": 3, "slow_min": 2}]


def test_segments_summed_then_priced():
    r = calc_multi_stop(TWO, False, T)
    assert r["segment_count"] == 2
    assert [s["seq"] for s in r["segments"]] == [1, 2]
    assert r["distance_km"] == 5.0
    assert r["slow_min"] == 3.0
    assert r["start"] == 11.0
    assert r["mileage"] == 5.0
    assert r["slow_fee"] == 2.4
    assert r["total"] == 18.4


def test_start_price_charged_once():
    r = calc_multi_stop([{"distance_km": 1, "slow_min": 0}, {"distance_km": 1, "slow_min": 0}], False, T)
    assert r["total"] == 11.0


def test_night_factor_applies_to_summed_totals():
    r = calc_multi_stop([{"distance_km": 10, "slow_min": 5}, {"distance_km": 8, "slow_min": 7}], True, T)
    assert r["total"] == 69.72


def test_single_segment_rejected():
    with pytest.raises(MultiStopError):
        calc_multi_stop([{"distance_km": 5, "slow_min": 2}], False, T)


def test_negative_segment_rejected():
    with pytest.raises(MultiStopError):
        calc_multi_stop([{"distance_km": 5, "slow_min": 2}, {"distance_km": -1, "slow_min": 0}], False, T)
    with pytest.raises(MultiStopError):
        calc_multi_stop([{"distance_km": 5, "slow_min": 2}, {"distance_km": 1, "slow_min": -0.5}], False, T)


def _mem_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
    CREATE TABLE tariff(id INTEGER PRIMARY KEY, start_price REAL, start_include_km REAL, per_km REAL, per_slow_min REAL, night_factor REAL);
    CREATE TABLE calc_runs(id INTEGER PRIMARY KEY, kind TEXT, trip_id INTEGER, input_json TEXT, result_json TEXT, created_at TEXT);
    INSERT INTO tariff(start_price,start_include_km,per_km,per_slow_min,night_factor) VALUES (11,3,2.5,0.8,1.2);
    """)
    return conn


def _service(monkeypatch, conn):
    monkeypatch.setattr("app.services.taxi_service.connect", lambda: conn)
    return TaxiService()


def test_persist_writes_run_with_frozen_segments(monkeypatch):
    conn = _mem_conn()
    with _service(monkeypatch, conn) as s:
        r = s.multi_fare(TWO, False, True)
        assert r["run_id"]
        row = conn.execute("SELECT * FROM calc_runs WHERE id=?", (r["run_id"],)).fetchone()
        assert row["kind"] == "multi_stop"
        saved = json.loads(row["result_json"])
        assert [x["distance_km"] for x in saved["segments"]] == [2.0, 3.0]
        assert saved["total"] == 18.4
        # later tariff change must not rewrite the stored breakdown
        conn.execute("UPDATE tariff SET per_km=99")
        conn.commit()
        again = json.loads(conn.execute("SELECT result_json FROM calc_runs WHERE id=?", (r["run_id"],)).fetchone()["result_json"])
        assert again["mileage"] == 5.0
        assert again["total"] == 18.4
        assert [x["distance_km"] for x in again["segments"]] == [2.0, 3.0]


def test_trial_run_persists_nothing(monkeypatch):
    conn = _mem_conn()
    with _service(monkeypatch, conn) as s:
        r = s.multi_fare(TWO, False, False)
        assert r["run_id"] is None
        assert r["total"] == 18.4
        assert conn.execute("SELECT COUNT(*) c FROM calc_runs").fetchone()["c"] == 0


def test_rejected_order_persists_nothing(monkeypatch):
    conn = _mem_conn()
    with _service(monkeypatch, conn) as s:
        with pytest.raises(MultiStopError):
            s.multi_fare([{"distance_km": 5, "slow_min": 2}], False, True)
        with pytest.raises(MultiStopError):
            s.multi_fare([{"distance_km": 5, "slow_min": 2}, {"distance_km": -1, "slow_min": 0}], False, True)
        assert conn.execute("SELECT COUNT(*) c FROM calc_runs").fetchone()["c"] == 0
