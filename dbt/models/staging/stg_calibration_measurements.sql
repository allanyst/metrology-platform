WITH source AS (
    SELECT * FROM {{ source('bronze', 'calibration_measurements') }}
)

SELECT
    instrument_id,
    instrument_name,
    sublab,
    magnitude,
    unit,
    CAST(measurement_date AS DATE)  AS measurement_date,
    replicate,
    reference_value,
    measured_value,
    error,
    uncertainty,
    uncertainty * 2                 AS expanded_uncertainty_k2,
    in_tolerance,
    temp_c,
    humidity_pct,
    pressure_hpa,
    ingested_at
FROM source
WHERE measured_value IS NOT NULL
  AND reference_value IS NOT NULL
  AND instrument_id IS NOT NULL
