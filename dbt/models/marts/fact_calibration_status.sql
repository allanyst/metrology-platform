WITH latest_stats AS (
    SELECT *
    FROM {{ ref('fact_instrument_stats') }}
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY instrument_id
        ORDER BY measurement_date DESC
    ) = 1
),

control AS (
    SELECT *
    FROM {{ ref('fact_control_charts') }}
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY instrument_id
        ORDER BY measurement_date DESC
    ) = 1
)

SELECT
    s.instrument_id,
    s.instrument_name,
    s.sublab,
    s.magnitude,
    s.unit,
    s.measurement_date        AS last_calibration_date,
    s.reference_value,
    s.mean_measured,
    s.mean_error,
    s.std_measured,
    s.n_replicates,
    s.uncertainty_type_a,
    s.expanded_uncertainty_type_a,
    s.expanded_uncertainty_k2,
    s.n_out_of_tolerance,
    s.daily_status,
    c.lt_mean_error,
    c.lt_std_error,
    c.ucl_2s,
    c.lcl_2s,
    c.ucl_3s,
    c.lcl_3s,
    c.we_rule1_violation,
    c.we_rule2_violation,
    c.control_zone,
    CASE
        WHEN c.we_rule1_violation              THEN 'CRITICAL'
        WHEN c.we_rule2_violation              THEN 'WARNING'
        WHEN s.daily_status = 'OUT_OF_TOLERANCE' THEN 'OUT_OF_TOLERANCE'
        WHEN s.daily_status = 'WARNING'        THEN 'WARNING'
        ELSE                                        'OK'
    END AS overall_status
FROM latest_stats s
JOIN control c USING (instrument_id)
