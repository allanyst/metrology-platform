from __future__ import annotations
import numpy as np
import duckdb
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "metrology.duckdb"
N_SIMULATIONS = 100_000

UNCERTAINTY_TYPE_B = {
    "BAL-001": 0.00003,
    "BAL-002": 0.0008,
    "PIP-001": 0.002,
    "BUR-001": 0.003,
    "TER-REF": 0.008,
    "TER-IND": 0.03,
    "HIG-001": 0.3,
    "BAR-001": 0.08,
    "XRF-001": 0.008,
    "HPL-001": 0.03,
    "PHM-001": 0.001,
}

RNG = np.random.default_rng(42)


def run_monte_carlo(instrument_id: str, u_a: float, u_b: float, mean_val: float) -> dict:
    samples_a = RNG.normal(0, u_a, N_SIMULATIONS)
    samples_b = RNG.normal(0, u_b, N_SIMULATIONS)
    combined  = samples_a + samples_b

    u_combined  = float(np.std(combined))
    u_expanded  = u_combined * 2
    percentile_2_5  = float(np.percentile(combined, 2.5))
    percentile_97_5 = float(np.percentile(combined, 97.5))

    return {
        "instrument_id":      instrument_id,
        "mean_measured":      mean_val,
        "u_type_a":           round(u_a, 8),
        "u_type_b":           round(u_b, 8),
        "u_combined":         round(u_combined, 8),
        "u_expanded_k2":      round(u_expanded, 8),
        "ci_lower":           round(mean_val + percentile_2_5, 8),
        "ci_upper":           round(mean_val + percentile_97_5, 8),
        "n_simulations":      N_SIMULATIONS,
    }


def compute_and_store() -> None:
    conn = duckdb.connect(str(DB_PATH))

    rows = conn.execute("""
        SELECT instrument_id, mean_measured, uncertainty_type_a
        FROM gold.fact_calibration_status
        ORDER BY instrument_id
    """).fetchall()

    results = []
    for instrument_id, mean_measured, u_a in rows:
        u_b = UNCERTAINTY_TYPE_B.get(instrument_id, 0.001)
        result = run_monte_carlo(instrument_id, float(u_a), float(u_b), float(mean_measured))
        results.append(result)
        print(f"{instrument_id}: u_combined={result['u_combined']:.6f}, U(k=2)={result['u_expanded_k2']:.6f}")

    conn.execute("CREATE SCHEMA IF NOT EXISTS gold")
    conn.execute("DROP TABLE IF EXISTS gold.fact_uncertainty")
    conn.execute("""
        CREATE TABLE gold.fact_uncertainty AS
        SELECT * FROM (VALUES
    """ + ",\n".join([
        f"('{r['instrument_id']}', {r['mean_measured']}, {r['u_type_a']}, "
        f"{r['u_type_b']}, {r['u_combined']}, {r['u_expanded_k2']}, "
        f"{r['ci_lower']}, {r['ci_upper']}, {r['n_simulations']})"
        for r in results
    ]) + """
        ) t(instrument_id, mean_measured, u_type_a, u_type_b,
            u_combined, u_expanded_k2, ci_lower, ci_upper, n_simulations)
    """)

    conn.close()
    print(f"\nStored {len(results)} uncertainty records in gold.fact_uncertainty")


if __name__ == "__main__":
    compute_and_store()