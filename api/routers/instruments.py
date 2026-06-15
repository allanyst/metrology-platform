from fastapi import APIRouter, HTTPException, Depends
from main import get_db
import duckdb

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("/")
def get_all_instruments(conn: duckdb.DuckDBPyConnection = Depends(get_db)):
    rows = conn.execute("""
        SELECT
            cs.instrument_id,
            cs.instrument_name,
            cs.sublab,
            cs.magnitude,
            cs.unit,
            cs.last_calibration_date::VARCHAR AS last_calibration_date,
            cs.mean_measured,
            cs.mean_error,
            cs.expanded_uncertainty_type_a,
            cs.overall_status,
            cs.control_zone,
            cs.we_rule1_violation,
            cs.we_rule2_violation,
            pm.days_to_failure,
            pm.risk_level,
            pm.trend,
            u.u_combined,
            u.u_expanded_k2
        FROM gold.fact_calibration_status cs
        LEFT JOIN gold.fact_predictive_maintenance pm USING (instrument_id)
        LEFT JOIN gold.fact_uncertainty u USING (instrument_id)
        ORDER BY cs.instrument_id
    """).fetchdf()
    return rows.to_dict(orient="records")


@router.get("/{instrument_id}")
def get_instrument(instrument_id: str, conn: duckdb.DuckDBPyConnection = Depends(get_db)):
    row = conn.execute("""
        SELECT
            cs.*,
            pm.days_to_failure,
            pm.risk_level,
            pm.trend,
            pm.r_squared,
            u.u_combined,
            u.u_expanded_k2,
            u.ci_lower,
            u.ci_upper
        FROM gold.fact_calibration_status cs
        LEFT JOIN gold.fact_predictive_maintenance pm USING (instrument_id)
        LEFT JOIN gold.fact_uncertainty u USING (instrument_id)
        WHERE cs.instrument_id = ?
    """, [instrument_id]).fetchdf()

    if row.empty:
        raise HTTPException(status_code=404, detail=f"Instrument {instrument_id} not found")
    return row.to_dict(orient="records")[0]
