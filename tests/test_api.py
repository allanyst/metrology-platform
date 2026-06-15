from __future__ import annotations
import pytest
import duckdb
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from api.main import app


@pytest.fixture
def mock_db():
    conn = duckdb.connect(":memory:")

    conn.execute("CREATE SCHEMA gold")
    conn.execute("""
        CREATE TABLE gold.fact_calibration_status (
            instrument_id VARCHAR, instrument_name VARCHAR, sublab VARCHAR,
            magnitude VARCHAR, unit VARCHAR, last_calibration_date DATE,
            reference_value DOUBLE, mean_measured DOUBLE, mean_error DOUBLE,
            std_measured DOUBLE, n_replicates INTEGER, uncertainty_type_a DOUBLE,
            expanded_uncertainty_type_a DOUBLE, expanded_uncertainty_k2 DOUBLE,
            n_out_of_tolerance INTEGER, daily_status VARCHAR,
            lt_mean_error DOUBLE, lt_std_error DOUBLE,
            ucl_2s DOUBLE, lcl_2s DOUBLE, ucl_3s DOUBLE, lcl_3s DOUBLE,
            we_rule1_violation BOOLEAN, we_rule2_violation BOOLEAN,
            control_zone VARCHAR, overall_status VARCHAR
        )
    """)
    conn.execute("""
        INSERT INTO gold.fact_calibration_status VALUES
        ('BAL-001','Balanza Analítica','masa_volumen','masa','g',
         '2025-12-31',100.0,100.0001,0.0001,0.00005,20,0.00001,
         0.00002,0.00002,0,
         'OK',0.00005,0.00003,0.00011,-0.00001,0.00014,-0.00004,
         false,false,'WITHIN_1S','OK')
    """)
    conn.execute("""
        CREATE TABLE gold.fact_predictive_maintenance (
            instrument_id VARCHAR, slope DOUBLE, intercept DOUBLE,
            current_abs_error DOUBLE, tolerance DOUBLE,
            days_to_failure INTEGER, r_squared DOUBLE,
            trend VARCHAR, risk_level VARCHAR
        )
    """)
    conn.execute("""
        INSERT INTO gold.fact_predictive_maintenance VALUES
        ('BAL-001', 0.000001, 0.0, 0.0001, 0.0002, 100, 0.95, 'INCREASING', 'MEDIUM')
    """)
    conn.execute("""
        CREATE TABLE gold.fact_uncertainty (
            instrument_id VARCHAR, mean_measured DOUBLE,
            u_type_a DOUBLE, u_type_b DOUBLE,
            u_combined DOUBLE, u_expanded_k2 DOUBLE,
            ci_lower DOUBLE, ci_upper DOUBLE, n_simulations INTEGER
        )
    """)
    conn.execute("""
        INSERT INTO gold.fact_uncertainty VALUES
        ('BAL-001', 100.0001, 0.00001, 0.00003, 0.000032, 0.000063,
         99.99994, 100.00016, 100000)
    """)
    conn.execute("""
        CREATE TABLE gold.fact_control_charts (
            instrument_id VARCHAR, instrument_name VARCHAR, sublab VARCHAR,
            magnitude VARCHAR, unit VARCHAR, measurement_date DATE,
            reference_value DOUBLE, mean_measured DOUBLE, mean_error DOUBLE,
            std_measured DOUBLE, n_replicates INTEGER, daily_status VARCHAR,
            lt_mean_error DOUBLE, lt_std_error DOUBLE,
            ucl_1s DOUBLE, lcl_1s DOUBLE, ucl_2s DOUBLE, lcl_2s DOUBLE,
            ucl_3s DOUBLE, lcl_3s DOUBLE, we_rule1_violation BOOLEAN,
            we_rule2_violation BOOLEAN, control_zone VARCHAR
        )
    """)
    conn.execute("""
        INSERT INTO gold.fact_control_charts VALUES
        ('BAL-001','Balanza Analítica','masa_volumen','masa','g',
         '2025-12-31',100.0,100.0001,0.0001,0.00005,20,'OK',
         0.00005,0.00003,0.00008,0.00002,0.00011,-0.00001,0.00014,-0.00004,
         false,false,'WITHIN_1S')
    """)
    yield conn
    conn.close()


@pytest.fixture
def client(mock_db):
    app.state.db = mock_db
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_get_all_instruments(client):
    r = client.get("/instruments/")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["instrument_id"] == "BAL-001"


def test_get_instrument_found(client):
    r = client.get("/instruments/BAL-001")
    assert r.status_code == 200
    assert r.json()["instrument_id"] == "BAL-001"


def test_get_instrument_not_found(client):
    r = client.get("/instruments/FAKE-999")
    assert r.status_code == 404


def test_get_trends(client):
    r = client.get("/trends/BAL-001?days=30")
    assert r.status_code == 200
    assert r.json()["instrument_id"] == "BAL-001"
    assert "data" in r.json()


def test_calculate_uncertainty(client):
    r = client.post("/uncertainty/calculate", json={
        "instrument_id": "BAL-001",
        "measurements": [100.0001, 99.9999, 100.0002, 100.0000, 99.9998],
    })
    assert r.status_code == 200
    body = r.json()
    assert "u_expanded" in body
    assert body["n_measurements"] == 5
    assert body["u_expanded"] > 0


def test_uncertainty_requires_min_measurements(client):
    r = client.post("/uncertainty/calculate", json={
        "instrument_id": "BAL-001",
        "measurements": [100.0001],
    })
    assert r.status_code == 400