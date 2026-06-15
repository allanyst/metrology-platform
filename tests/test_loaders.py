from __future__ import annotations
import pytest
import duckdb
import pandas as pd
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.ingestion.loaders import init_bronze, load_measurements, load_environmental


@pytest.fixture
def in_memory_db():
    conn = duckdb.connect(":memory:")
    init_bronze(conn)
    yield conn
    conn.close()


def test_init_bronze_creates_schemas(in_memory_db):
    schemas = in_memory_db.execute(
        "SELECT schema_name FROM information_schema.schemata"
    ).fetchdf()["schema_name"].tolist()
    assert "bronze" in schemas


def test_init_bronze_creates_tables(in_memory_db):
    tables = in_memory_db.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'bronze'"
    ).fetchdf()["table_name"].tolist()
    assert "calibration_measurements" in tables
    assert "environmental_conditions" in tables


def test_load_measurements_inserts_rows(in_memory_db, tmp_path):
    df = pd.DataFrame([{
        "instrument_id": "BAL-001", "instrument_name": "Balanza",
        "sublab": "masa_volumen", "magnitude": "masa", "unit": "g",
        "measurement_date": "2025-01-01", "replicate": 1,
        "reference_value": 100.0, "measured_value": 100.0001,
        "error": 0.0001, "uncertainty": 0.00005, "in_tolerance": True,
        "temp_c": 20.0, "humidity_pct": 55.0, "pressure_hpa": 1013.0,
    }])
    csv_path = tmp_path / "calibration_measurements.csv"
    df.to_csv(csv_path, index=False)

    with patch("src.ingestion.loaders.RAW_PATH", tmp_path):
        n = load_measurements(in_memory_db)

    assert n == 1
    count = in_memory_db.execute(
        "SELECT COUNT(*) FROM bronze.calibration_measurements"
    ).fetchone()[0]
    assert count == 1


def test_load_environmental_inserts_rows(in_memory_db, tmp_path):
    df = pd.DataFrame([{
        "date": "2025-01-01",
        "temp_c": 20.1, "humidity_pct": 55.0, "pressure_hpa": 1013.0,
    }])
    csv_path = tmp_path / "environmental_conditions.csv"
    df.to_csv(csv_path, index=False)

    with patch("src.ingestion.loaders.RAW_PATH", tmp_path):
        n = load_environmental(in_memory_db)

    assert n == 1