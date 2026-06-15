from __future__ import annotations
import numpy as np
import duckdb
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "metrology.duckdb"

TOLERANCE = {
    "BAL-001": 0.0002,
    "BAL-002": 0.005,
    "PIP-001": 0.020,
    "BUR-001": 0.030,
    "TER-REF": 0.05,
    "TER-IND": 0.20,
    "HIG-001": 2.0,
    "BAR-001": 1.0,
    "XRF-001": 0.100,
    "HPL-001": 0.500,
    "PHM-001": 0.020,
}


def predict_days_to_failure(errors: np.ndarray, tolerance: float) -> dict:
    n = len(errors)
    x = np.arange(n)

    coeffs = np.polyfit(x, errors, 1)
    slope, intercept = coeffs

    abs_errors = np.abs(errors)
    abs_coeffs = np.polyfit(x, abs_errors, 1)
    abs_slope, abs_intercept = abs_coeffs

    current_abs_error = abs(float(np.polyval(coeffs, n - 1)))

    if abs_slope <= 0:
        days_to_failure = None
        predicted_failure_date = None
    else:
        remaining = tolerance - current_abs_error
        if remaining <= 0:
            days_to_failure = 0
        else:
            days_to_failure = int(remaining / abs_slope)

    r_squared = float(1 - np.var(errors - np.polyval(coeffs, x)) / np.var(errors)) if np.var(errors) > 0 else 0.0

    return {
        "slope":               round(float(slope), 10),
        "intercept":           round(float(intercept), 8),
        "current_abs_error":   round(current_abs_error, 8),
        "tolerance":           tolerance,
        "days_to_failure":     days_to_failure,
        "r_squared":           round(r_squared, 4),
        "trend":               "INCREASING" if slope > 0 else "DECREASING" if slope < 0 else "STABLE",
        "risk_level":          (
            "CRITICAL" if days_to_failure is not None and days_to_failure <= 30
            else "HIGH"    if days_to_failure is not None and days_to_failure <= 90
            else "MEDIUM"  if days_to_failure is not None and days_to_failure <= 180
            else "LOW"
        ),
    }


def compute_and_store() -> None:
    conn = duckdb.connect(str(DB_PATH))

    rows = conn.execute("""
        SELECT instrument_id, measurement_date, mean_error
        FROM gold.fact_instrument_stats
        ORDER BY instrument_id, measurement_date
    """).fetchall()

    from collections import defaultdict
    series = defaultdict(list)
    for instrument_id, measurement_date, mean_error in rows:
        series[instrument_id].append(float(mean_error))

    results = []
    for instrument_id, errors in series.items():
        tol = TOLERANCE.get(instrument_id, 0.01)
        pred = predict_days_to_failure(np.array(errors), tol)
        pred["instrument_id"] = instrument_id
        results.append(pred)
        print(f"{instrument_id}: trend={pred['trend']}, days_to_failure={pred['days_to_failure']}, risk={pred['risk_level']}")

    conn.execute("DROP TABLE IF EXISTS gold.fact_predictive_maintenance")
    conn.execute("""
        CREATE TABLE gold.fact_predictive_maintenance AS
        SELECT * FROM (VALUES
    """ + ",\n".join([
        f"('{r['instrument_id']}', {r['slope']}, {r['intercept']}, "
        f"{r['current_abs_error']}, {r['tolerance']}, "
        f"{'NULL' if r['days_to_failure'] is None else r['days_to_failure']}, "
        f"{r['r_squared']}, '{r['trend']}', '{r['risk_level']}')"
        for r in results
    ]) + """
        ) t(instrument_id, slope, intercept, current_abs_error, tolerance,
            days_to_failure, r_squared, trend, risk_level)
    """)

    conn.close()
    print(f"\nStored {len(results)} predictive maintenance records.")


if __name__ == "__main__":
    compute_and_store()