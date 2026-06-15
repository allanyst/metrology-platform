from fastapi import APIRouter, HTTPException, Query, Depends
from main import get_db
import duckdb

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("/{instrument_id}")
def get_trends(
    instrument_id: str,
    days: int = Query(default=90, ge=7, le=365),
    conn: duckdb.DuckDBPyConnection = Depends(get_db),
):
    exists = conn.execute(
        "SELECT COUNT(*) FROM gold.fact_calibration_status WHERE instrument_id = ?",
        [instrument_id]
    ).fetchone()[0]

    if not exists:
        raise HTTPException(status_code=404, detail=f"Instrument {instrument_id} not found")

    rows = conn.execute("""
        SELECT
            measurement_date::VARCHAR AS measurement_date,
            mean_error,
            std_measured,
            lt_mean_error,
            ucl_1s, lcl_1s,
            ucl_2s, lcl_2s,
            ucl_3s, lcl_3s,
            control_zone,
            we_rule1_violation,
            we_rule2_violation,
            daily_status
        FROM gold.fact_control_charts
        WHERE instrument_id = ?
          AND measurement_date >= (
              SELECT MAX(measurement_date) - INTERVAL (?) DAY
              FROM gold.fact_control_charts
              WHERE instrument_id = ?
          )
        ORDER BY measurement_date
    """, [instrument_id, days, instrument_id]).fetchdf()

    return {
        "instrument_id": instrument_id,
        "days_requested": days,
        "n_records": len(rows),
        "data": rows.to_dict(orient="records"),
    }
