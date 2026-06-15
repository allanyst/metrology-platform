WITH measurements AS (
    SELECT * FROM {{ ref('stg_calibration_measurements') }}
),

daily_stats AS (
    SELECT
        instrument_id,
        instrument_name,
        sublab,
        magnitude,
        unit,
        measurement_date,
        reference_value,
        COUNT(*)                                    AS n_replicates,
        AVG(measured_value)                         AS mean_measured,
        STDDEV_SAMP(measured_value)                 AS std_measured,
        AVG(error)                                  AS mean_error,
        MAX(ABS(error))                             AS max_abs_error,
        AVG(uncertainty)                            AS uncertainty_base,
        AVG(expanded_uncertainty_k2)                AS expanded_uncertainty_k2,
        STDDEV_SAMP(measured_value) / SQRT(COUNT(*)) AS uncertainty_type_a,
        STDDEV_SAMP(measured_value) / SQRT(COUNT(*)) * 2 AS expanded_uncertainty_type_a,
        AVG(temp_c)                                 AS mean_temp_c,
        AVG(humidity_pct)                           AS mean_humidity_pct,
        BOOL_AND(in_tolerance)                      AS all_in_tolerance,
        COUNT(*) FILTER (WHERE NOT in_tolerance)    AS n_out_of_tolerance
    FROM measurements
    GROUP BY
        instrument_id, instrument_name, sublab,
        magnitude, unit, measurement_date, reference_value
)

SELECT
    *,
    CASE
        WHEN n_out_of_tolerance = 0             THEN 'OK'
        WHEN n_out_of_tolerance <= n_replicates * 0.1 THEN 'WARNING'
        ELSE                                         'OUT_OF_TOLERANCE'
    END AS daily_status
FROM daily_stats
