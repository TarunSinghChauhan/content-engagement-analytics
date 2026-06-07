/*
=============================================================================
QUERY 5 — Content Portfolio Health Report (BCG-Style Quadrant Analysis)
=============================================================================
Business Question:
    Which titles should we continue investing in, which should be allowed to
    coast on existing audiences, which require an awareness push, and which
    should be deprioritised or removed from the catalogue?

Methodology:
    Adapted BCG growth-share matrix applied to streaming content:

        ┌──────────────────┬─────────────────────┬──────────────────────────┐
        │ Quadrant         │ Engagement Score     │ Audience Reach           │
        ├──────────────────┼─────────────────────┼──────────────────────────┤
        │ Stars            │ High (≥ median)      │ High (≥ median)          │
        │ Cash Cows        │ Low  (< median)      │ High (≥ median)          │
        │ Question Marks   │ High (≥ median)      │ Low  (< median)          │
        │ Dogs             │ Low  (< median)      │ Low  (< median)          │
        └──────────────────┴─────────────────────┴──────────────────────────┘

    Engagement score is taken from Query 1 logic (recalculated inline here
    for self-containment). Reach is unique viewer count.
=============================================================================
*/

-- ── Step 1: Recalculate engagement score inline (mirrors Query 1) ─────────
WITH raw_metrics AS (
    SELECT
        pe.content_id,
        AVG(LEAST(
            pe.watch_duration_minutes::NUMERIC / NULLIF(pe.content_duration_minutes, 0), 1.0
        ))                                             AS completion_rate,
        AVG(pe.rewatch_flag::NUMERIC)                  AS rewatch_rate,
        AVG(pe.shared_flag::NUMERIC)                   AS share_rate,
        COUNT(DISTINCT pe.user_id)                     AS unique_viewers,
        COUNT(*)                                       AS total_plays
    FROM play_events pe
    GROUP BY pe.content_id
),

bounds AS (
    SELECT
        MIN(completion_rate) AS min_cr, MAX(completion_rate) AS max_cr,
        MIN(rewatch_rate)    AS min_rr, MAX(rewatch_rate)    AS max_rr,
        MIN(share_rate)      AS min_sr, MAX(share_rate)      AS max_sr,
        MIN(unique_viewers)  AS min_uv, MAX(unique_viewers)  AS max_uv
    FROM raw_metrics
),

scored AS (
    SELECT
        rm.content_id,
        rm.completion_rate,
        rm.rewatch_rate,
        rm.share_rate,
        rm.unique_viewers,
        rm.total_plays,
        ROUND((
            ((rm.completion_rate - b.min_cr) / NULLIF(b.max_cr - b.min_cr, 0) * 100 * 0.40)
          + ((rm.rewatch_rate    - b.min_rr) / NULLIF(b.max_rr - b.min_rr, 0) * 100 * 0.25)
          + ((rm.share_rate      - b.min_sr) / NULLIF(b.max_sr - b.min_sr, 0) * 100 * 0.20)
          + ((rm.unique_viewers  - b.min_uv)::NUMERIC / NULLIF(b.max_uv - b.min_uv, 0) * 100 * 0.15)
        ), 2) AS engagement_score
    FROM raw_metrics rm
    CROSS JOIN bounds b
),

-- ── Step 2: Calculate portfolio-level medians as quadrant thresholds ──────
portfolio_medians AS (
    SELECT
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY engagement_score) AS median_engagement,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY unique_viewers)   AS median_reach
    FROM scored
),

-- ── Step 3: Assign quadrant to each title ────────────────────────────────
quadrant_assigned AS (
    SELECT
        s.content_id,
        COALESCE(cc.title, 'Title_' || s.content_id)         AS title,
        COALESCE(cc.genre, 'Unknown')                         AS genre,
        s.engagement_score,
        s.unique_viewers                                      AS reach,
        s.total_plays,
        ROUND(s.completion_rate * 100, 2)                     AS completion_pct,
        ROUND(s.rewatch_rate    * 100, 2)                     AS rewatch_pct,
        ROUND(s.share_rate      * 100, 2)                     AS share_pct,
        pm.median_engagement,
        pm.median_reach,

        CASE
            WHEN s.engagement_score >= pm.median_engagement
             AND s.unique_viewers   >= pm.median_reach   THEN 'Stars'
            WHEN s.engagement_score <  pm.median_engagement
             AND s.unique_viewers   >= pm.median_reach   THEN 'Cash Cows'
            WHEN s.engagement_score >= pm.median_engagement
             AND s.unique_viewers   <  pm.median_reach   THEN 'Question Marks'
            ELSE                                              'Dogs'
        END                                                   AS quadrant

    FROM scored s
    CROSS JOIN portfolio_medians pm
    LEFT JOIN content_catalogue cc ON cc.content_id = s.content_id
),

-- ── Step 4: Rank within each quadrant for "top 3 titles" output ──────────
ranked_within_quadrant AS (
    SELECT
        qa.*,
        DENSE_RANK() OVER (
            PARTITION BY qa.quadrant
            ORDER BY qa.engagement_score DESC
        )                                                     AS rank_in_quadrant
    FROM quadrant_assigned qa
)

-- ── Final output: Summary statistics + all titles ────────────────────────
-- Section A: Portfolio summary by quadrant
SELECT
    'SUMMARY' AS output_type,
    rq.quadrant,
    COUNT(*)                                                  AS title_count,
    ROUND(AVG(rq.engagement_score), 2)                        AS avg_engagement_score,
    ROUND(AVG(rq.reach), 0)                                   AS avg_reach,
    ROUND(AVG(rq.completion_pct), 2)                          AS avg_completion_pct,
    NULL::TEXT                                                AS title,
    NULL::TEXT                                                AS genre,
    NULL::INTEGER                                             AS rank_in_quadrant
FROM ranked_within_quadrant rq
GROUP BY rq.quadrant

UNION ALL

-- Section B: Top 3 titles per quadrant
SELECT
    'TOP_3'   AS output_type,
    rq.quadrant,
    NULL::BIGINT                                              AS title_count,
    rq.engagement_score                                       AS avg_engagement_score,
    rq.reach::NUMERIC                                         AS avg_reach,
    rq.completion_pct                                         AS avg_completion_pct,
    rq.title,
    rq.genre,
    rq.rank_in_quadrant
FROM ranked_within_quadrant rq
WHERE rq.rank_in_quadrant <= 3

ORDER BY
    CASE quadrant
        WHEN 'Stars'          THEN 1
        WHEN 'Cash Cows'      THEN 2
        WHEN 'Question Marks' THEN 3
        WHEN 'Dogs'           THEN 4
    END,
    output_type,
    rank_in_quadrant;
