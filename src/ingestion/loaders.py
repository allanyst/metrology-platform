from __future__ import annotations
import duckdb
import pandas as pd
from pathlib import Path

import os

_db_env  = os.environ.get("METROLOGY_DB_PATH")
DB_PATH  = Path(_db_env) if _db_env else Path(__file__).parent.parent.parent / "data" / "db" / "metrology.duckdb"
RAW_PATH = DB_PATH.parent.parent / "raw"


def get_connection() -> duckdb.DuckDBPyConnection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))


def init_bronze(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("CREATE SCHEMA IF NOT EXISTS bronze")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS bronze.calibration_measurements (
            instrument_id    VARCHAR,
            instrument_name  VARCHAR,
            sublab           VARCHAR,
            magnitude        VARCHAR,
            unit             VARCHAR,
            measurement_date DATE,
            replicate        INTEGER,
            reference_value  DOUBLE,
            measured_value   DOUBLE,
            error            DOUBLE,
            uncertainty      DOUBLE,
            in_tolerance     BOOLEAN,
            temp_c           DOUBLE,
            humidity_pct     DOUBLE,
            pressure_hpa     DOUBLE,
            ingested_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS bronze.environmental_conditions (
            date         DATE,
            temp_c       DOUBLE,
            humidity_pct DOUBLE,
            pressure_hpa DOUBLE,
            ingested_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def load_measurements(conn: duckdb.DuckDBPyConnection) -> int:
    df = pd.read_csv(RAW_PATH / "calibration_measurements.csv", parse_dates=["measurement_date"])
    df = df.reset_index(drop=True)
    conn.execute("DELETE FROM bronze.calibration_measurements")
    conn.register("df", df)
    conn.execute("""
        INSERT INTO bronze.calibration_measurements
        SELECT
            instrument_id, instrument_name, sublab, magnitude, unit,
            measurement_date, replicate, reference_value, measured_value,
            error, uncertainty, in_tolerance, temp_c, humidity_pct,
            pressure_hpa, CURRENT_TIMESTAMP
        FROM df
    """)
    conn.unregister("df")
    return len(df)


def load_environmental(conn: duckdb.DuckDBPyConnection) -> int:
    df = pd.read_csv(RAW_PATH / "environmental_conditions.csv", parse_dates=["date"])
    df = df.reset_index(drop=True)
    conn.execute("DELETE FROM bronze.environmental_conditions")
    conn.register("df", df)
    conn.execute("""
        INSERT INTO bronze.environmental_conditions
        SELECT date, temp_c, humidity_pct, pressure_hpa, CURRENT_TIMESTAMP
        FROM df
    """)
    conn.unregister("df")
    return len(df)


if __name__ == "__main__":
    conn = get_connection()
    init_bronze(conn)

    n1 = load_measurements(conn)
    print(f"Loaded {n1:,} measurement records into bronze.calibration_measurements")

    n2 = load_environmental(conn)
    print(f"Loaded {n2:,} environmental records into bronze.environmental_conditions")

    conn.close()
    print("Bronze layer ready.")