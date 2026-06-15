from __future__ import annotations
import numpy as np
import pandas as pd
from datetime import date, timedelta
from pathlib import Path

RNG = np.random.default_rng(42)

INSTRUMENTS = {
    # Sub-lab 1: Masa y Volumen
    "BAL-001": {"name": "Balanza Analítica",    "sublab": "masa_volumen",   "magnitude": "masa",       "unit": "g",    "ref_value": 100.0000, "tolerance": 0.0002, "uncertainty_base": 0.00005, "drift": "linear"},
    "BAL-002": {"name": "Balanza de Precisión", "sublab": "masa_volumen",   "magnitude": "masa",       "unit": "g",    "ref_value": 500.000,  "tolerance": 0.005,  "uncertainty_base": 0.001,   "drift": "linear"},
    "PIP-001": {"name": "Pipeta Volumétrica",   "sublab": "masa_volumen",   "magnitude": "volumen",    "unit": "mL",   "ref_value": 10.000,   "tolerance": 0.020,  "uncertainty_base": 0.003,   "drift": "jump"},
    "BUR-001": {"name": "Bureta",               "sublab": "masa_volumen",   "magnitude": "volumen",    "unit": "mL",   "ref_value": 25.000,   "tolerance": 0.030,  "uncertainty_base": 0.005,   "drift": "linear"},
    # Sub-lab 2: Temperatura y Humedad
    "TER-REF": {"name": "Termómetro Referencia","sublab": "temp_humedad",   "magnitude": "temperatura","unit": "°C",   "ref_value": 20.00,    "tolerance": 0.05,   "uncertainty_base": 0.010,   "drift": "seasonal"},
    "TER-IND": {"name": "Termómetro Industrial","sublab": "temp_humedad",   "magnitude": "temperatura","unit": "°C",   "ref_value": 20.00,    "tolerance": 0.20,   "uncertainty_base": 0.050,   "drift": "seasonal_noisy"},
    "HIG-001": {"name": "Higrómetro",           "sublab": "temp_humedad",   "magnitude": "humedad",    "unit": "%HR",  "ref_value": 55.0,     "tolerance": 2.0,    "uncertainty_base": 0.5,     "drift": "seasonal"},
    "BAR-001": {"name": "Barómetro",            "sublab": "temp_humedad",   "magnitude": "presion",    "unit": "hPa",  "ref_value": 1013.25,  "tolerance": 1.0,    "uncertainty_base": 0.1,     "drift": "gaussian"},
    # Sub-lab 3: Química Analítica
    "XRF-001": {"name": "Espectrómetro XRF",    "sublab": "quimica",        "magnitude": "concentracion","unit": "%m", "ref_value": 10.000,   "tolerance": 0.100,  "uncertainty_base": 0.010,   "drift": "exponential"},
    "HPL-001": {"name": "Cromatógrafo HPLC",    "sublab": "quimica",        "magnitude": "concentracion","unit": "mg/L","ref_value": 50.000,  "tolerance": 0.500,  "uncertainty_base": 0.050,   "drift": "linear"},
    "PHM-001": {"name": "pH-metro",             "sublab": "quimica",        "magnitude": "pH",         "unit": "pH",   "ref_value": 7.000,    "tolerance": 0.020,  "uncertainty_base": 0.002,   "drift": "linear_jump"},
}

START_DATE = date(2025, 1, 1)
END_DATE   = date(2025, 12, 31)
REPS       = 150  # mediciones repetidas por día por instrumento

def generate_environmental_conditions(dates: list[date]) -> pd.DataFrame:
    n = len(dates)
    day_of_year = np.array([d.timetuple().tm_yday for d in dates])
    seasonal = np.sin(2 * np.pi * day_of_year / 365)

    temp     = 20.0 + 0.5 * seasonal + RNG.normal(0, 0.3, n)
    humidity = 55.0 + 3.0 * seasonal + RNG.normal(0, 1.0, n)
    pressure = 1013.25 + RNG.normal(0, 0.5, n)

    return pd.DataFrame({"date": dates, "temp_c": temp, "humidity_pct": humidity, "pressure_hpa": pressure})


def apply_drift(ref: float, tolerance: float, drift_type: str, day_idx: int, n_days: int) -> float:
    t = day_idx / n_days  # 0 → 1 a lo largo del año

    if drift_type == "linear":
        drift = tolerance * 0.8 * t

    elif drift_type == "jump":
        jump_day = int(n_days * 0.45)
        drift = tolerance * 0.6 if day_idx >= jump_day else 0.0

    elif drift_type == "seasonal":
        day_of_year = day_idx % 365
        drift = tolerance * 0.3 * np.sin(2 * np.pi * day_of_year / 365)

    elif drift_type == "seasonal_noisy":
        day_of_year = day_idx % 365
        drift = tolerance * 0.5 * np.sin(2 * np.pi * day_of_year / 365)

    elif drift_type == "gaussian":
        drift = 0.0

    elif drift_type == "exponential":
        drift = -ref * 0.05 * (1 - np.exp(-3 * t))

    elif drift_type == "linear_jump":
        drift = tolerance * 0.4 * t
        jump_day = int(n_days * 0.70)
        if day_idx >= jump_day:
            drift += tolerance * 0.5

    else:
        drift = 0.0

    return ref + drift

def generate_measurements(env: pd.DataFrame) -> pd.DataFrame:
    dates = env["date"].tolist()
    n_days = len(dates)
    records = []

    for day_idx, day in enumerate(dates):
        env_row = env[env["date"] == day].iloc[0]

        for inst_id, cfg in INSTRUMENTS.items():
            drifted_ref = apply_drift(
                cfg["ref_value"],
                cfg["tolerance"],
                cfg["drift"],
                day_idx,
                n_days,
            )

            for rep in range(1, REPS + 1):
                noise = RNG.normal(0, cfg["uncertainty_base"])

                if cfg["drift"] == "exponential":
                    detector_noise = RNG.normal(0, cfg["uncertainty_base"] * (1 + 2 * day_idx / n_days))
                    measured = drifted_ref + detector_noise
                else:
                    measured = drifted_ref + noise

                error = measured - cfg["ref_value"]
                in_tolerance = abs(error) <= cfg["tolerance"]

                records.append({
                    "instrument_id":   inst_id,
                    "instrument_name": cfg["name"],
                    "sublab":          cfg["sublab"],
                    "magnitude":       cfg["magnitude"],
                    "unit":            cfg["unit"],
                    "measurement_date": str(day),
                    "replicate":       rep,
                    "reference_value": cfg["ref_value"],
                    "measured_value":  round(measured, 6),
                    "error":           round(error, 6),
                    "uncertainty":     cfg["uncertainty_base"],
                    "in_tolerance":    in_tolerance,
                    "temp_c":          round(float(env_row["temp_c"]), 2),
                    "humidity_pct":    round(float(env_row["humidity_pct"]), 2),
                    "pressure_hpa":    round(float(env_row["pressure_hpa"]), 2),
                })

    return pd.DataFrame(records)


if __name__ == "__main__":
    print("Generating environmental conditions...")
    dates = [START_DATE + timedelta(days=i) for i in range((END_DATE - START_DATE).days + 1)]
    env = generate_environmental_conditions(dates)

    print("Generating measurements...")
    df = generate_measurements(env)

    out_path = Path(__file__).parent.parent.parent / "data" / "raw"
    out_path.mkdir(parents=True, exist_ok=True)

    env.to_csv(out_path / "environmental_conditions.csv", index=False)
    df.to_csv(out_path / "calibration_measurements.csv", index=False)

    print(f"Done! {len(df):,} measurement records generated.")
    print(f"  Instruments : {df['instrument_id'].nunique()}")
    print(f"  Date range  : {df['measurement_date'].min()} → {df['measurement_date'].max()}")
    print(f"  In tolerance: {df['in_tolerance'].mean()*100:.1f}%")