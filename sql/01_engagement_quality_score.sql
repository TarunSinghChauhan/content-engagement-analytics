/*
=============================================================================
QUERY 1 — Engagement Quality Score (Weighted Composite)
=============================================================================
Business Question:
    Which titles are truly driving high-quality user engagement — not just
    high view counts — and where should the content strategy team place
    its next investment?

Methodology:
    A composite score is built from four behavioural signals, each normalised
    to a 0–100 scale (min-max) before weighting:

        ┌───────────────────────┬────────┐
        │ Component             │ Weight │
        ├───────────────────────┼────────┤
        │ Completion Rate       │  40 %  │
        │ Rewatch Rate          │  25 %  │
        │ Share Rate            │  20 %  │
        │ Unique Viewer Reach   │  15 %  │
        └───────────────────────┴────────┘

    Min-max normalisation formula:
        normalised = (x - min(x)) / NULLIF(max(x) - min(x), 0) * 100

Usage:
    Run against the play_events table after loading play_events.csv.
    JOIN against the content_catalogue or netflix_titles table for title/genre.
=============================================================================
*/

-- ── Step 1: Raw per-content metrics ──────────────────────────────────────────
WITH raw_metrics AS (
    SELECT
        pe.content_id,
        -- Completion Rate: avg(watch / content duration), clipped at 1.0
        AVG(
            LEAST(
                pe.watch_duration_minutes::NUMERIC / NULLIF(pe.content_duration_minutes, 0),
                1.0
            )
        )                                               AS completion_rate,

        -- Rewatch Rate: proportion of plays marked as rewatch
        AVG(pe.rewatch_flag::NUMERIC)                  AS rewatch_rate,

        -- Share Rate: proportion of plays that led to a share
        AVG(pe.shared_flag::NUMERIC)                   AS share_rate,

        -- Audience Reach: distinct viewers (absolute count, normalised later)
        COUNT(DISTINCT pe.user_id)                     AS unique_viewers,

        -- Total plays (for reference)
        COUNT(*)                                        AS total_plays

    FROM play_events pe
    GROUP BY pe.content_id
),

-- ── Step 2: Min-max bounds for each component ─────────────────────────────
bounds AS (
    SELECT
        MIN(completion_rate)   AS min_cr,  MAX(completion_rate)   AS max_cr,
        MIN(rewatch_rate)      AS min_rr,  MAX(rewatch_rate)      AS max_rr,
        MIN(share_rate)        AS min_sr,  MAX(share_rate)        AS max_sr,
        MIN(unique_viewers)    AS min_uv,  MAX(unique_viewers)    AS max_uv
    FROM raw_metrics
),

-- ── Step 3: Normalise each component to 0–100 ────────────────────────────
normalised AS (
    SELECT
        rm.content_id,
        rm.completion_rate,
        rm.rewatch_rate,
        rm.share_rate,
        rm.unique_viewers,
        rm.total_plays,

        -- Normalised components
        (rm.completion_rate  - b.min_cr) / NULLIF(b.max_cr - b.min_cr, 0) * 100 AS norm_completion,
        (rm.rewatch_rate     - b.min_rr) / NULLIF(b.max_rr - b.min_rr, 0) * 100 AS norm_rewatch,
        (rm.share_rate       - b.min_sr) / NULLIF(b.max_sr - b.min_sr, 0) * 100 AS norm_share,
        (rm.unique_viewers   - b.min_uv)::NUMERIC / NULLIF(b.max_uv - b.min_uv, 0) * 100 AS norm_reach

    FROM raw_metrics rm
    CROSS JOIN bounds b
),

-- ── Step 4: Weighted composite engagement score ───────────────────────────
scored AS (
    SELECT
        n.content_id,
        n.completion_rate,
        n.rewatch_rate,
        n.share_rate,
        n.unique_viewers,
        n.total_plays,
        n.norm_completion,
        n.norm_rewatch,
        n.norm_share,
        n.norm_reach,

        -- Weighted composite score
        ROUND(
            (n.norm_completion * 0.40)
          + (n.norm_rewatch    * 0.25)
          + (n.norm_share      * 0.20)
          + (n.norm_reach      * 0.15),
            2
        )                                               AS engagement_score

    FROM normalised n
)

-- ── Step 5: Final output with rank ──────────────────────────────────────
SELECT
    s.content_id,

    -- Join to content catalogue for human-readable metadata
    -- Replace 'content_catalogue' with 'netflix_titles' if using Kaggle dataset
    COALESCE(cc.title,  'Title_' || s.content_id)      AS title,
    COALESCE(cc.genre,  'Unknown')                      AS genre,

    -- Raw metrics (for transparency)
    ROUND(s.completion_rate * 100, 2)                  AS completion_rate_pct,
    ROUND(s.rewatch_rate    * 100, 2)                  AS rewatch_rate_pct,
    ROUND(s.share_rate      * 100, 2)                  AS share_rate_pct,
    s.unique_viewers,
    s.total_plays,

    -- Normalised scores (for audit trail)
    ROUND(s.norm_completion, 2)                        AS norm_completion_score,
    ROUND(s.norm_rewatch,    2)                        AS norm_rewatch_score,
    ROUND(s.norm_share,      2)                        AS norm_share_score,
    ROUND(s.norm_reach,      2)                        AS norm_reach_score,

    -- Final composite
    s.engagement_score,

    -- Dense rank: ties share the same rank without gaps
    DENSE_RANK() OVER (ORDER BY s.engagement_score DESC) AS score_rank

FROM scored s
LEFT JOIN content_catalogue cc
    ON cc.content_id = s.content_id
ORDER BY s.engagement_score DESC;
