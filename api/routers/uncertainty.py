from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from main import get_db
import duckdb
import numpy as np

router = APIRouter(prefix="/uncertainty", tags=["uncertainty"])


class MeasurementInput(BaseModel):
    instrument_id: str
    measurements: list[float]
    u_type_b: float | None = None
    k: float = 2.0


@router.post("/calculate")
def calculate_uncertainty(
    body: MeasurementInput,
    conn: duckdb.DuckDBPyConnection = Depends(get_db),
):
    measurements = np.array(body.measurements)
    n = len(measurements)

    if n < 2:
        raise HTTPException(status_code=400, detail="At least 2 measurements required")

    mean_val = float(np.mean(measurements))
    std_val  = float(np.std(measurements, ddof=1))
    u_type_a = std_val / np.sqrt(n)

    if body.u_type_b is not None:
        u_type_b = body.u_type_b
    else:
        row = conn.execute(
            "SELECT u_type_b FROM gold.fact_uncertainty WHERE instrument_id = ?",
            [body.instrument_id]
        ).fetchone()
        u_type_b = float(row[0]) if row else 0.0

    u_combined = float(np.sqrt(u_type_a**2 + u_type_b**2))
    u_expanded = u_combined * body.k
    samples    = np.random.default_rng().normal(mean_val, u_combined, 100_000)

    return {
        "instrument_id":     body.instrument_id,
        "n_measurements":    n,
        "mean":              round(mean_val, 8),
        "std":               round(std_val, 8),
        "u_type_a":          round(u_type_a, 8),
        "u_type_b":          round(u_type_b, 8),
        "u_combined":        round(u_combined, 8),
        "u_expanded":        round(u_expanded, 8),
        "k":                 body.k,
        "coverage_interval": {
            "lower": round(float(np.percentile(samples, 2.5)), 8),
            "upper": round(float(np.percentile(samples, 97.5)), 8),
        },
    }
