/*
=============================================================================
QUERY 2 — Content Decay Curve (Weekly Viewership Retention Post-Release)
=============================================================================
Business Question:
    How quickly does a title lose its audience after release, and which
    titles are "evergreen" performers versus "one-week wonders"?

Methodology:
    1. For each (content_id, week_number), count plays where week_number is
       measured relative to the title's first observed play date.
    2. Calculate viewership in weeks 1, 2, 3, 4, 8, and 12.
    3. Express each week as a percentage of Week 1 baseline.
    4. Classify titles into top/bottom 10 % decayers using percentile windows.

Note on "release date":
    We use the first observed watch_date in play_events as a proxy for
    release date (since synthetic data may predate actual release).
=============================================================================
*/

-- ── Step 1: Determine each title's observed first play date ──────────────────
WITH release_anchors AS (
    SELECT
        content_id,
        MIN(watch_date)                                AS first_play_date
    FROM play_events
    GROUP BY content_id
),

-- ── Step 2: Label every play event with a week number relative to release ──
weekly_events AS (
    SELECT
        pe.content_id,
        -- Week number: integer division of days since first play, 1-indexed
        FLOOR(
            (pe.watch_date - ra.first_play_date)::NUMERIC / 7
        ) + 1                                          AS week_number,
        pe.user_id
    FROM play_events        pe
    JOIN release_anchors    ra  ON ra.content_id = pe.content_id
    -- Only analyse first 12 weeks to keep the decay curve tractable
    WHERE (pe.watch_date - ra.first_play_date) BETWEEN 0 AND 83
),

-- ── Step 3: Count plays per content per week ─────────────────────────────
weekly_plays AS (
    SELECT
        content_id,
        week_number,
        COUNT(*)                    AS plays_that_week,
        COUNT(DISTINCT user_id)     AS unique_viewers_that_week
    FROM weekly_events
    GROUP BY content_id, week_number
),

-- ── Step 4: Pivot week 1 plays as anchor baseline ────────────────────────
week1_baseline AS (
    SELECT
        content_id,
        plays_that_week             AS week1_plays
    FROM weekly_plays
    WHERE week_number = 1
),

-- ── Step 5: Create the pivoted decay table for milestone weeks ────────────
decay_curve AS (
    SELECT
        wp.content_id,
        wb.week1_plays,

        MAX(CASE WHEN wp.week_number =  1 THEN wp.plays_that_week END) AS w1_plays,
        MAX(CASE WHEN wp.week_number =  2 THEN wp.plays_that_week END) AS w2_plays,
        MAX(CASE WHEN wp.week_number =  3 THEN wp.plays_that_week END) AS w3_plays,
        MAX(CASE WHEN wp.week_number =  4 THEN wp.plays_that_week END) AS w4_plays,
        MAX(CASE WHEN wp.week_number =  8 THEN wp.plays_that_week END) AS w8_plays,
        MAX(CASE WHEN wp.week_number = 12 THEN wp.plays_that_week END) AS w12_plays

    FROM weekly_plays   wp
    JOIN week1_baseline wb ON wb.content_id = wp.content_id
    GROUP BY wp.content_id, wb.week1_plays
),

-- ── Step 6: Express plays as % of Week 1 baseline ────────────────────────
decay_pct AS (
    SELECT
        dc.content_id,
        dc.week1_plays,

        100.0                                                              AS w1_retention_pct,

        ROUND(COALESCE(dc.w2_plays,  0)::NUMERIC / dc.week1_plays * 100, 2) AS w2_retention_pct,
        ROUND(COALESCE(dc.w3_plays,  0)::NUMERIC / dc.week1_plays * 100, 2) AS w3_retention_pct,
        ROUND(COALESCE(dc.w4_plays,  0)::NUMERIC / dc.week1_plays * 100, 2) AS w4_retention_pct,
        ROUND(COALESCE(dc.w8_plays,  0)::NUMERIC / dc.week1_plays * 100, 2) AS w8_retention_pct,
        ROUND(COALESCE(dc.w12_plays, 0)::NUMERIC / dc.week1_plays * 100, 2) AS w12_retention_pct,

        -- Speed of decay: week-4 retention is the primary decay signal
        COALESCE(dc.w4_plays, 0)::NUMERIC / dc.week1_plays                AS w4_retention_ratio

    FROM decay_curve dc
    WHERE dc.week1_plays > 0
),

-- ── Step 7: Percentile classification of decay speed ─────────────────────
decay_classified AS (
    SELECT
        dp.*,

        -- PERCENT_RANK: 0 = fastest decay, 1 = slowest decay (most retained)
        PERCENT_RANK() OVER (ORDER BY dp.w4_retention_ratio ASC) AS decay_percentile,

        CASE
            WHEN PERCENT_RANK() OVER (ORDER BY dp.w4_retention_ratio ASC) <= 0.10
                THEN 'Fastest Decay (Bottom 10%)'
            WHEN PERCENT_RANK() OVER (ORDER BY dp.w4_retention_ratio ASC) >= 0.90
                THEN 'Slowest Decay (Top 10% — Evergreen)'
            ELSE 'Average Decay'
        END                                                       AS decay_category

    FROM decay_pct dp
)

-- ── Final output ─────────────────────────────────────────────────────────
SELECT
    dc.content_id,
    COALESCE(cc.title, 'Title_' || dc.content_id)  AS title,
    COALESCE(cc.genre, 'Unknown')                  AS genre,
    dc.week1_plays,
    dc.w1_retention_pct,
    dc.w2_retention_pct,
    dc.w3_retention_pct,
    dc.w4_retention_pct,
    dc.w8_retention_pct,
    dc.w12_retention_pct,
    ROUND(dc.decay_percentile * 100, 1)            AS decay_percentile_rank,
    dc.decay_category
FROM decay_classified dc
LEFT JOIN content_catalogue cc ON cc.content_id = dc.content_id
ORDER BY dc.w4_retention_ratio ASC;   -- Fastest decayers first
