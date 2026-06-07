/*
=============================================================================
QUERY 3 — Audience Segment Affinity
=============================================================================
Business Question:
    Which genre–age group–device type combinations generate the highest
    engagement quality, and how should the platform personalise its homepage
    recommendations and marketing spend accordingly?

Methodology:
    1. Compute per-event completion rate, rewatch, and share signals.
    2. Aggregate into a cross-tab keyed on genre × age_group × device_type.
    3. Re-use the engagement scoring logic (simplified, pre-normalised version)
       so the affinity score is comparable to the content-level score.
    4. Rank the top 3 genre-audience combinations.

Note:
    Using a simplified engagement score here (non-normalised, relative scale)
    because we are comparing across segments rather than across content IDs.
    For an apples-to-apples comparison with Query 1, run Query 1 first and
    JOIN the scores here.
=============================================================================
*/

-- ── Step 1: Compute per-event-level signals ───────────────────────────────
WITH event_signals AS (
    SELECT
        pe.content_id,
        pe.user_id,
        pe.genre,
        pe.user_age_group,
        pe.device_type,

        -- Completion fraction (capped at 1.0)
        LEAST(
            pe.watch_duration_minutes::NUMERIC / NULLIF(pe.content_duration_minutes, 0),
            1.0
        )                                              AS completion_fraction,

        pe.rewatch_flag,
        pe.shared_flag
    FROM play_events pe
),

-- ── Step 2: Segment-level aggregation ────────────────────────────────────
segment_metrics AS (
    SELECT
        es.genre,
        es.user_age_group,
        es.device_type,

        COUNT(*)                                       AS total_plays,
        COUNT(DISTINCT es.user_id)                     AS unique_viewers,
        COUNT(DISTINCT es.content_id)                  AS titles_watched,

        ROUND(AVG(es.completion_fraction) * 100, 2)    AS avg_completion_pct,
        ROUND(AVG(es.rewatch_flag::NUMERIC) * 100, 2)  AS rewatch_rate_pct,
        ROUND(AVG(es.shared_flag::NUMERIC) * 100, 2)   AS share_rate_pct,

        -- Simplified engagement score (weighted average of raw rates)
        -- This mirrors Query 1 weights but without cross-segment normalisation
        ROUND(
            (AVG(es.completion_fraction) * 100 * 0.40)
          + (AVG(es.rewatch_flag::NUMERIC) * 100 * 0.25)
          + (AVG(es.shared_flag::NUMERIC) * 100 * 0.20)
          -- Reach component: log-normalised viewer count scaled to 0-100
          + (LN(COUNT(DISTINCT es.user_id) + 1) / LN(2001) * 100 * 0.15),
            2
        )                                              AS segment_engagement_score

    FROM event_signals es
    GROUP BY es.genre, es.user_age_group, es.device_type
),

-- ── Step 3: Identify top 3 genre-audience combinations ───────────────────
-- (genre × age_group only — device collapsed for higher-level insight)
genre_age_summary AS (
    SELECT
        sm.genre,
        sm.user_age_group,
        SUM(sm.total_plays)                            AS total_plays,
        SUM(sm.unique_viewers)                         AS unique_viewers,
        ROUND(AVG(sm.avg_completion_pct), 2)           AS avg_completion_pct,
        ROUND(AVG(sm.segment_engagement_score), 2)     AS avg_engagement_score,
        DENSE_RANK() OVER (
            ORDER BY AVG(sm.segment_engagement_score) DESC
        )                                              AS affinity_rank
    FROM segment_metrics sm
    GROUP BY sm.genre, sm.user_age_group
),

-- ── Step 4: CASE-based audience tier labelling ────────────────────────────
segment_with_labels AS (
    SELECT
        sm.*,

        -- Age tier using CASE
        CASE
            WHEN sm.user_age_group IN ('13-17', '18-24') THEN 'Gen Z'
            WHEN sm.user_age_group IN ('25-34', '35-44') THEN 'Millennial'
            WHEN sm.user_age_group IN ('45-54', '55+')   THEN 'Gen X / Boomer'
            ELSE 'Unknown'
        END                                            AS audience_tier,

        -- Device category simplification
        CASE
            WHEN sm.device_type IN ('smart_tv', 'console') THEN 'Living Room'
            WHEN sm.device_type IN ('mobile', 'tablet')    THEN 'Mobile'
            WHEN sm.device_type = 'desktop'                THEN 'Desktop'
            ELSE 'Other'
        END                                            AS device_category,

        -- Engagement tier
        CASE
            WHEN sm.segment_engagement_score >= 65 THEN 'High Affinity'
            WHEN sm.segment_engagement_score >= 45 THEN 'Medium Affinity'
            ELSE 'Low Affinity'
        END                                            AS affinity_tier,

        DENSE_RANK() OVER (
            ORDER BY sm.segment_engagement_score DESC
        )                                              AS overall_rank

    FROM segment_metrics sm
)

-- ── Final cross-tab output ────────────────────────────────────────────────
SELECT
    swl.genre,
    swl.user_age_group,
    swl.audience_tier,
    swl.device_type,
    swl.device_category,
    swl.total_plays,
    swl.unique_viewers,
    swl.titles_watched,
    swl.avg_completion_pct,
    swl.rewatch_rate_pct,
    swl.share_rate_pct,
    swl.segment_engagement_score,
    swl.affinity_tier,
    swl.overall_rank
FROM segment_with_labels swl
ORDER BY swl.segment_engagement_score DESC;

-- ── BONUS: Top 3 Genre × Age Group combinations ──────────────────────────
-- Uncomment to surface the three highest-affinity macro segments:
/*
SELECT genre, user_age_group, total_plays, unique_viewers,
       avg_completion_pct, avg_engagement_score, affinity_rank
FROM   genre_age_summary
WHERE  affinity_rank <= 3
ORDER  BY affinity_rank;
*/
