WITH stats AS (
    SELECT * FROM {{ ref('fact_instrument_stats') }}
),

-- Parámetros de largo plazo por instrumento (media del año completo)
long_term AS (
    SELECT
        instrument_id,
        AVG(mean_error)     AS lt_mean_error,
        STDDEV_SAMP(mean_error) AS lt_std_error
    FROM stats
    GROUP BY instrument_id
),

-- Unimos con los límites de control
control AS (
    SELECT
        s.instrument_id,
        s.instrument_name,
        s.sublab,
        s.magnitude,
        s.unit,
        s.measurement_date,
        s.reference_value,
        s.mean_measured,
        s.mean_error,
        s.std_measured,
        s.n_replicates,
        s.daily_status,
        l.lt_mean_error,
        l.lt_std_error,

        -- Límites Levey-Jennings
        l.lt_mean_error + l.lt_std_error        AS ucl_1s,
        l.lt_mean_error - l.lt_std_error        AS lcl_1s,
        l.lt_mean_error + 2 * l.lt_std_error    AS ucl_2s,
        l.lt_mean_error - 2 * l.lt_std_error    AS lcl_2s,
        l.lt_mean_error + 3 * l.lt_std_error    AS ucl_3s,
        l.lt_mean_error - 3 * l.lt_std_error    AS lcl_3s,

        -- Flags Western Electric Rule 1: punto fuera de ±3s
        CASE WHEN ABS(s.mean_error - l.lt_mean_error) > 3 * l.lt_std_error
             THEN TRUE ELSE FALSE END AS we_rule1_violation,

        -- Flags Western Electric Rule 2: punto fuera de ±2s
        CASE WHEN ABS(s.mean_error - l.lt_mean_error) > 2 * l.lt_std_error
             THEN TRUE ELSE FALSE END AS we_rule2_violation,

        -- Zona: dentro de qué banda cae el punto
        CASE
            WHEN ABS(s.mean_error - l.lt_mean_error) > 3 * l.lt_std_error THEN 'BEYOND_3S'
            WHEN ABS(s.mean_error - l.lt_mean_error) > 2 * l.lt_std_error THEN 'BEYOND_2S'
            WHEN ABS(s.mean_error - l.lt_mean_error) > l.lt_std_error     THEN 'BEYOND_1S'
            ELSE 'WITHIN_1S'
        END AS control_zone

    FROM stats s
    JOIN long_term l USING (instrument_id)
)

SELECT * FROM control
ORDER BY instrument_id, measurement_date
