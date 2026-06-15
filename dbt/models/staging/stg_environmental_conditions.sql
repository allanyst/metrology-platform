WITH source AS (
    SELECT * FROM {{ source('bronze', 'environmental_conditions') }}
)

SELECT
    CAST(date AS DATE) AS condition_date,
    temp_c,
    humidity_pct,
    pressure_hpa,
    CASE
        WHEN temp_c BETWEEN 18.0 AND 22.0
         AND humidity_pct BETWEEN 45.0 AND 65.0
        THEN TRUE
        ELSE FALSE
    END AS within_lab_conditions,
    ingested_at
FROM source
WHERE date IS NOT NULL
