/*
=============================================================================
QUERY 4 — Cold Start Signal Analysis
=============================================================================
Business Question:
    Can early-day viewer behaviour (Day 1 and Day 3 metrics) reliably predict
    a title's long-term success, and how should this inform greenlight and
    marketing activation decisions?

Methodology:
    1. Identify "Day 1" and "Day 3" as the first and third calendar day after
       a title's first observed play date.
    2. Compute completion rate, share rate, and rewatch rate for each window.
    3. Compute Day-30 engagement score using the same weighted formula as
       Query 1 (over the first 30 days of a title's life).
    4. Flag titles where Day-1 correctly predicted top/bottom quartile.

Interpretation:
    A high Day-1 completion rate but low Day-30 engagement may indicate a
    "hype bubble" — marketing-driven spike without sustained organic interest.
    A low Day-1 but high Day-30 signals "slow burn" content that benefits from
    word-of-mouth — ideal candidates for algorithmic recommendation boosts.
=============================================================================
*/

-- ── Step 1: Release anchor per title ─────────────────────────────────────
WITH release_anchors AS (
    SELECT
        content_id,
        MIN(watch_date) AS first_play_date
    FROM play_events
    GROUP BY content_id
),

-- ── Step 2: Day-1 Metrics (plays on the first calendar day of release) ───
day1_metrics AS (
    SELECT
        pe.content_id,
        COUNT(*)                                           AS d1_plays,
        COUNT(DISTINCT pe.user_id)                         AS d1_unique_viewers,
        ROUND(
            AVG(LEAST(
                pe.watch_duration_minutes::NUMERIC / NULLIF(pe.content_duration_minutes, 0),
                1.0
            )) * 100, 4
        )                                                  AS d1_completion_rate,
        ROUND(AVG(pe.rewatch_flag::NUMERIC) * 100, 4)     AS d1_rewatch_rate,
        ROUND(AVG(pe.shared_flag::NUMERIC)  * 100, 4)     AS d1_share_rate
    FROM play_events pe
    JOIN release_anchors ra ON ra.content_id = pe.content_id
    -- Day 1 definition: same calendar day as first play
    WHERE pe.watch_date = ra.first_play_date
    GROUP BY pe.content_id
),

-- ── Step 3: Day-3 Metrics (plays within first 3 days inclusive) ──────────
day3_metrics AS (
    SELECT
        pe.content_id,
        COUNT(*)                                           AS d3_plays,
        COUNT(DISTINCT pe.user_id)                         AS d3_unique_viewers,
        ROUND(
            AVG(LEAST(
                pe.watch_duration_minutes::NUMERIC / NULLIF(pe.content_duration_minutes, 0),
                1.0
            )) * 100, 4
        )                                                  AS d3_completion_rate,
        ROUND(AVG(pe.rewatch_flag::NUMERIC) * 100, 4)     AS d3_rewatch_rate,
        ROUND(AVG(pe.shared_flag::NUMERIC)  * 100, 4)     AS d3_share_rate
    FROM play_events pe
    JOIN release_anchors ra ON ra.content_id = pe.content_id
    WHERE (pe.watch_date - ra.first_play_date) BETWEEN 0 AND 2
    GROUP BY pe.content_id
),

-- ── Step 4: Day-30 Engagement Score (long-term benchmark) ─────────────────
day30_raw AS (
    SELECT
        pe.content_id,
        COUNT(*)                                                AS d30_plays,
        COUNT(DISTINCT pe.user_id)                              AS d30_unique_viewers,
        AVG(LEAST(
            pe.watch_duration_minutes::NUMERIC / NULLIF(pe.content_duration_minutes, 0),
            1.0
        ))                                                      AS d30_completion_rate,
        AVG(pe.rewatch_flag::NUMERIC)                           AS d30_rewatch_rate,
        AVG(pe.shared_flag::NUMERIC)                            AS d30_share_rate
    FROM play_events pe
    JOIN release_anchors ra ON ra.content_id = pe.content_id
    WHERE (pe.watch_date - ra.first_play_date) BETWEEN 0 AND 29
    GROUP BY pe.content_id
),

-- ── Step 5: Normalise Day-30 scores using min-max within the 30-day window ─
d30_bounds AS (
    SELECT
        MIN(d30_completion_rate)  AS min_cr, MAX(d30_completion_rate)  AS max_cr,
        MIN(d30_rewatch_rate)     AS min_rr, MAX(d30_rewatch_rate)     AS max_rr,
        MIN(d30_share_rate)       AS min_sr, MAX(d30_share_rate)       AS max_sr,
        MIN(d30_unique_viewers)   AS min_uv, MAX(d30_unique_viewers)   AS max_uv
    FROM day30_raw
),

d30_scored AS (
    SELECT
        dr.content_id,
        dr.d30_plays,
        dr.d30_unique_viewers,
        ROUND(dr.d30_completion_rate * 100, 2)  AS d30_completion_pct,
        ROUND(dr.d30_rewatch_rate    * 100, 2)  AS d30_rewatch_pct,
        ROUND(dr.d30_share_rate      * 100, 2)  AS d30_share_pct,

        ROUND((
            ((dr.d30_completion_rate - b.min_cr) / NULLIF(b.max_cr - b.min_cr, 0) * 100 * 0.40)
          + ((dr.d30_rewatch_rate    - b.min_rr) / NULLIF(b.max_rr - b.min_rr, 0) * 100 * 0.25)
          + ((dr.d30_share_rate      - b.min_sr) / NULLIF(b.max_sr - b.min_sr, 0) * 100 * 0.20)
          + ((dr.d30_unique_viewers  - b.min_uv)::NUMERIC
              / NULLIF(b.max_uv - b.min_uv, 0) * 100 * 0.15)
        ), 2)                                    AS d30_engagement_score
    FROM day30_raw dr
    CROSS JOIN d30_bounds b
),

-- ── Step 6: Quartile classification on Day-30 score ──────────────────────
d30_ranked AS (
    SELECT
        ds.*,
        NTILE(4) OVER (ORDER BY ds.d30_engagement_score ASC) AS d30_quartile
        -- Quartile 1 = bottom 25%, Quartile 4 = top 25%
    FROM d30_scored ds
),

-- ── Step 7: Assemble cold-start vs. long-term view ───────────────────────
cold_start_full AS (
    SELECT
        dr.content_id,
        COALESCE(cc.title, 'Title_' || dr.content_id)  AS title,
        COALESCE(cc.genre, 'Unknown')                   AS genre,

        -- Day-1 signals
        COALESCE(d1.d1_plays,            0)             AS d1_plays,
        COALESCE(d1.d1_unique_viewers,   0)             AS d1_unique_viewers,
        COALESCE(d1.d1_completion_rate,  0)             AS d1_completion_rate,
        COALESCE(d1.d1_rewatch_rate,     0)             AS d1_rewatch_rate,
        COALESCE(d1.d1_share_rate,       0)             AS d1_share_rate,

        -- Day-3 signals
        COALESCE(d3.d3_plays,            0)             AS d3_plays,
        COALESCE(d3.d3_unique_viewers,   0)             AS d3_unique_viewers,
        COALESCE(d3.d3_completion_rate,  0)             AS d3_completion_rate,
        COALESCE(d3.d3_rewatch_rate,     0)             AS d3_rewatch_rate,
        COALESCE(d3.d3_share_rate,       0)             AS d3_share_rate,

        -- Day-30 benchmark
        dr.d30_plays,
        dr.d30_completion_pct,
        dr.d30_rewatch_pct,
        dr.d30_share_pct,
        dr.d30_engagement_score,
        dr.d30_quartile,

        -- Quartile label
        CASE dr.d30_quartile
            WHEN 4 THEN 'Top Quartile (Stars)'
            WHEN 3 THEN 'Upper Mid'
            WHEN 2 THEN 'Lower Mid'
            WHEN 1 THEN 'Bottom Quartile (Dogs)'
        END                                             AS d30_performance_tier

    FROM d30_ranked dr
    LEFT JOIN day1_metrics   d1 ON d1.content_id = dr.content_id
    LEFT JOIN day3_metrics   d3 ON d3.content_id = dr.content_id
    LEFT JOIN content_catalogue cc ON cc.content_id = dr.content_id
),

-- ── Step 8: Quartile bounds on Day-1 signal for prediction flag ───────────
d1_quartile_bounds AS (
    SELECT
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY d1_completion_rate) AS d1_cr_q1,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY d1_completion_rate) AS d1_cr_q3
    FROM cold_start_full
    WHERE d1_plays > 0
)

-- ── Final output with prediction accuracy flag ────────────────────────────
SELECT
    csf.*,

    -- Prediction: was Day-1 completion rate in top/bottom quartile?
    CASE
        WHEN csf.d1_completion_rate >= (SELECT d1_cr_q3 FROM d1_quartile_bounds)
             THEN 'Day-1 High Signal'
        WHEN csf.d1_completion_rate <= (SELECT d1_cr_q1 FROM d1_quartile_bounds)
             THEN 'Day-1 Low Signal'
        ELSE 'Day-1 Mid Signal'
    END                                                 AS d1_signal_tier,

    -- Was the Day-1 prediction correct for top/bottom quartile outcomes?
    CASE
        WHEN csf.d1_completion_rate >= (SELECT d1_cr_q3 FROM d1_quartile_bounds)
             AND csf.d30_quartile = 4  THEN 'TRUE POSITIVE  — D1 predicted Star'
        WHEN csf.d1_completion_rate <= (SELECT d1_cr_q1 FROM d1_quartile_bounds)
             AND csf.d30_quartile = 1  THEN 'TRUE NEGATIVE  — D1 predicted Dog'
        WHEN csf.d1_completion_rate >= (SELECT d1_cr_q3 FROM d1_quartile_bounds)
             AND csf.d30_quartile = 1  THEN 'FALSE POSITIVE — Hype Bubble'
        WHEN csf.d1_completion_rate <= (SELECT d1_cr_q1 FROM d1_quartile_bounds)
             AND csf.d30_quartile = 4  THEN 'FALSE NEGATIVE — Slow Burn'
        ELSE 'Non-Extreme — No Prediction'
    END                                                 AS prediction_outcome

FROM cold_start_full csf
ORDER BY csf.d30_engagement_score DESC;
