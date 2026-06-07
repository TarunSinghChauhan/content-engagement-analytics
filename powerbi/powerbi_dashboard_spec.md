# DELIVERABLE 3 — Power BI Dashboard Complete Specification
## Content Engagement Analytics Platform

---

## 3.1 Data Model Design

### Tables

| Table Name         | Source                    | Type       | Grain                          |
|--------------------|---------------------------|------------|--------------------------------|
| `fact_play_events` | play_events.csv           | Fact       | One row per streaming play     |
| `dim_content`      | content_catalogue.csv     | Dimension  | One row per content_id         |
| `dim_date`         | Auto-generated DAX table  | Dimension  | One row per calendar date      |
| `dim_user`         | Derived from fact table   | Dimension  | One row per user_id            |
| `agg_engagement`   | SQL Query 1 result        | Aggregate  | One row per content_id (score) |

### Table Definitions

**fact_play_events**
```
event_id                 TEXT (PK)
user_id                  TEXT (FK → dim_user)
content_id               TEXT (FK → dim_content)
watch_date               DATE (FK → dim_date)
watch_duration_minutes   INTEGER
content_duration_minutes INTEGER
rewatch_flag             INTEGER  (0 / 1)
shared_flag              INTEGER  (0 / 1)
device_type              TEXT
user_age_group           TEXT
user_region              TEXT
genre                    TEXT
```

**dim_content**
```
content_id      TEXT (PK)
title           TEXT
genre           TEXT
content_duration INTEGER
release_date    DATE
```

**dim_date**  ← generated via DAX CALENDARAUTO()
```
Date        DATE (PK)
Year        INTEGER
Quarter     TEXT
Month       INTEGER
MonthName   TEXT
Week        INTEGER
WeekDay     TEXT
```

**dim_user** ← derived via Power Query grouping on fact_play_events
```
user_id          TEXT (PK)
user_age_group   TEXT
user_region      TEXT
```

**agg_engagement** ← import SQL Query 1 result
```
content_id          TEXT (PK)
title               TEXT
genre               TEXT
engagement_score    DECIMAL
score_rank          INTEGER
completion_rate_pct DECIMAL
rewatch_rate_pct    DECIMAL
share_rate_pct      DECIMAL
unique_viewers      INTEGER
```

### Relationships & Cardinality

| From Table           | Key            | To Table         | Key          | Cardinality | Direction |
|----------------------|----------------|------------------|--------------|-------------|-----------|
| fact_play_events     | content_id     | dim_content      | content_id   | Many → One  | Single    |
| fact_play_events     | watch_date     | dim_date         | Date         | Many → One  | Single    |
| fact_play_events     | user_id        | dim_user         | user_id      | Many → One  | Single    |
| fact_play_events     | content_id     | agg_engagement   | content_id   | Many → One  | Single    |
| dim_content          | content_id     | agg_engagement   | content_id   | One → One   | Single    |

> **Note:** Do NOT create a direct relationship between dim_user and dim_content.
> Cross-filter direction should be Single (fact → dimension) for all relationships
> to prevent ambiguous filter propagation and incorrect aggregations.

---

## 3.2 DAX Measures (Complete, Pasteable)

### File: powerbi_dax_measures.dax

Paste each measure into Power BI Desktop → New Measure.

---

### MEASURE 1 — Engagement Quality Score

```dax
Engagement Quality Score =
VAR CompletionRate =
    DIVIDE(
        SUMX(
            fact_play_events,
            MIN(
                DIVIDE(
                    fact_play_events[watch_duration_minutes],
                    fact_play_events[content_duration_minutes]
                ),
                1
            )
        ),
        COUNTROWS(fact_play_events)
    )

VAR RewatchRate =
    DIVIDE(
        SUMX(fact_play_events, fact_play_events[rewatch_flag]),
        COUNTROWS(fact_play_events)
    )

VAR ShareRate =
    DIVIDE(
        SUMX(fact_play_events, fact_play_events[shared_flag]),
        COUNTROWS(fact_play_events)
    )

VAR UniqueViewers =
    DISTINCTCOUNT(fact_play_events[user_id])

-- Min-Max Normalisation bounds (calculated across ALL content in context)
VAR MaxCompletion = MAXX(ALL(agg_engagement), agg_engagement[completion_rate_pct] / 100)
VAR MinCompletion = MINX(ALL(agg_engagement), agg_engagement[completion_rate_pct] / 100)
VAR MaxRewatch    = MAXX(ALL(agg_engagement), agg_engagement[rewatch_rate_pct]    / 100)
VAR MinRewatch    = MINX(ALL(agg_engagement), agg_engagement[rewatch_rate_pct]    / 100)
VAR MaxShare      = MAXX(ALL(agg_engagement), agg_engagement[share_rate_pct]      / 100)
VAR MinShare      = MINX(ALL(agg_engagement), agg_engagement[share_rate_pct]      / 100)
VAR MaxViewers    = MAXX(ALL(agg_engagement), agg_engagement[unique_viewers])
VAR MinViewers    = MINX(ALL(agg_engagement), agg_engagement[unique_viewers])

VAR NormCompletion =
    DIVIDE(CompletionRate - MinCompletion, MaxCompletion - MinCompletion, 0) * 100
VAR NormRewatch    =
    DIVIDE(RewatchRate    - MinRewatch,    MaxRewatch    - MinRewatch,    0) * 100
VAR NormShare      =
    DIVIDE(ShareRate      - MinShare,      MaxShare      - MinShare,      0) * 100
VAR NormViewers    =
    DIVIDE(UniqueViewers  - MinViewers,    MaxViewers    - MinViewers,    0) * 100

RETURN
    ROUND(
        (NormCompletion * 0.40) +
        (NormRewatch    * 0.25) +
        (NormShare      * 0.20) +
        (NormViewers    * 0.15),
        2
    )
```

---

### MEASURE 2 — 30-Day Rolling Average Viewership

```dax
30-Day Rolling Avg Viewership =
VAR SelectedDate    = MAX(dim_date[Date])
VAR RollingWindow   = DATESINPERIOD(dim_date[Date], SelectedDate, -30, DAY)
VAR ViewsInWindow   =
    CALCULATE(
        COUNTROWS(fact_play_events),
        RollingWindow
    )
RETURN
    DIVIDE(ViewsInWindow, 30)
```

---

### MEASURE 3 — Week-over-Week Completion Rate Change

```dax
WoW Completion Rate Change =
VAR CurrentWeekCompletion =
    DIVIDE(
        SUMX(
            fact_play_events,
            MIN(
                DIVIDE(fact_play_events[watch_duration_minutes],
                       fact_play_events[content_duration_minutes]),
                1
            )
        ),
        COUNTROWS(fact_play_events)
    )

VAR PriorWeekCompletion =
    CALCULATE(
        DIVIDE(
            SUMX(
                fact_play_events,
                MIN(
                    DIVIDE(fact_play_events[watch_duration_minutes],
                           fact_play_events[content_duration_minutes]),
                    1
                )
            ),
            COUNTROWS(fact_play_events)
        ),
        DATEADD(dim_date[Date], -7, DAY)
    )

RETURN
    IF(
        ISBLANK(PriorWeekCompletion),
        BLANK(),
        DIVIDE(
            CurrentWeekCompletion - PriorWeekCompletion,
            PriorWeekCompletion
        )
    )
```

---

### MEASURE 4 — Top 10% vs Bottom 10% Content Flag

```dax
Content Tier Flag =
VAR CurrentScore     = [Engagement Quality Score]
VAR Top10Threshold   =
    PERCENTILEX.INC(
        ALL(agg_engagement),
        agg_engagement[engagement_score],
        0.90
    )
VAR Bottom10Threshold =
    PERCENTILEX.INC(
        ALL(agg_engagement),
        agg_engagement[engagement_score],
        0.10
    )
RETURN
    SWITCH(
        TRUE(),
        CurrentScore >= Top10Threshold,    "⭐ Top 10%",
        CurrentScore <= Bottom10Threshold, "⚠️ Bottom 10%",
        "Mid Tier"
    )
```

---

### MEASURE 5 — Content Quadrant Classification

```dax
Content Quadrant =
VAR ContentScore =
    CALCULATE(
        AVERAGE(agg_engagement[engagement_score]),
        ALLEXCEPT(agg_engagement, agg_engagement[content_id])
    )
VAR ContentReach =
    CALCULATE(
        AVERAGE(agg_engagement[unique_viewers]),
        ALLEXCEPT(agg_engagement, agg_engagement[content_id])
    )
VAR MedianScore =
    PERCENTILEX.INC(ALL(agg_engagement), agg_engagement[engagement_score], 0.50)
VAR MedianReach =
    PERCENTILEX.INC(ALL(agg_engagement), agg_engagement[unique_viewers],   0.50)

RETURN
    SWITCH(
        TRUE(),
        ContentScore >= MedianScore && ContentReach >= MedianReach, "⭐ Stars",
        ContentScore <  MedianScore && ContentReach >= MedianReach, "🐄 Cash Cows",
        ContentScore >= MedianScore && ContentReach <  MedianReach, "❓ Question Marks",
        "🐕 Dogs"
    )
```

---

### SUPPORTING MEASURES

```dax
-- Avg Completion Rate %
Avg Completion Rate =
DIVIDE(
    SUMX(
        fact_play_events,
        MIN(DIVIDE(fact_play_events[watch_duration_minutes],
                   fact_play_events[content_duration_minutes]), 1)
    ),
    COUNTROWS(fact_play_events)
) * 100

-- Rewatch Rate %
Rewatch Rate % =
DIVIDE(
    SUM(fact_play_events[rewatch_flag]),
    COUNTROWS(fact_play_events)
) * 100

-- Share Rate %
Share Rate % =
DIVIDE(
    SUM(fact_play_events[shared_flag]),
    COUNTROWS(fact_play_events)
) * 100

-- Total Plays
Total Plays =
COUNTROWS(fact_play_events)

-- Unique Viewers
Unique Viewers =
DISTINCTCOUNT(fact_play_events[user_id])

-- Plays per Unique Viewer (Stickiness)
Stickiness Index =
DIVIDE([Total Plays], [Unique Viewers])
```

---

## 3.3 Dashboard Layout

---

### PAGE 1: Executive Content Scorecard

**Purpose:** C-suite overview — daily performance pulse; one-glance health check of entire catalogue.

**Canvas Size:** 1280 × 720 px | Theme: Dark (custom — background #0F1117, accent #E50914)

#### Visuals:

1. **KPI Cards (top row — 6 cards)**
   - Total Plays (period-filtered)
   - Unique Active Viewers
   - Avg Engagement Quality Score
   - Avg Completion Rate %
   - Rewatch Rate %
   - Share Rate %
   - *Why:* Immediate single-number situational awareness; mimics Netflix internal dashboards.

2. **Scorecard Matrix — Content Tier Table**
   - Rows: Title
   - Columns: Engagement Score | Completion % | Rewatch % | Share % | Reach | Tier Flag | Quadrant
   - *Why:* Allows sorting/filtering to surface top/bottom performers instantly.
   - Conditional formatting: see Section 3.4

3. **Clustered Bar Chart — Engagement Score by Genre**
   - X: Engagement Score (average)
   - Y: Genre
   - Color: by Quadrant
   - *Why:* Genre-level benchmark for programming decisions.

4. **Line Chart — 30-Day Rolling Avg Viewership Trend**
   - X: Date
   - Y: [30-Day Rolling Avg Viewership]
   - *Why:* Trend signal; identifies seasonal spikes and dips.

**KPIs:** Total Plays, Unique Viewers, Avg Engagement Score, Avg Completion Rate

**Slicers:** Date Range | Genre | Region | Device Type | Content Tier Flag

---

### PAGE 2: Engagement Deep Dive

**Purpose:** Content team operational view — which specific titles are over/under-performing and why.

#### Visuals:

1. **Scatter Plot — Completion Rate vs Rewatch Rate**
   - X: Avg Completion Rate %
   - Y: Rewatch Rate %
   - Size: Unique Viewers
   - Color: Quadrant
   - Tooltip: Title, Genre, Engagement Score
   - *Why:* Instantly reveals quality/stickiness relationship. Stars cluster top-right.

2. **Area Chart — Weekly Viewership by Quadrant**
   - X: Week number (relative to release)
   - Y: Total Plays
   - Series: Quadrant
   - *Why:* Visual representation of decay curves by portfolio tier.

3. **Waterfall Chart — Engagement Score Decomposition**
   - Start: 0
   - Bars: Completion contribution | Rewatch contribution | Share contribution | Reach contribution
   - End: Total Engagement Score
   - *Why:* Shows which factor drives each title's score — critical for intervention decisions.

4. **Table — Cold Start Signal vs Day-30 Performance**
   - Columns: Title | Day-1 Completion % | Day-1 Share % | Day-30 Engagement Score | Prediction Outcome
   - Conditional formatting on Prediction Outcome
   - *Why:* Surfaces anomalies (Hype Bubbles / Slow Burns) for content strategy review.

5. **Hundred-Percent Stacked Bar — Device Type by Genre**
   - X: Genre
   - Y: % of plays
   - Series: Device Type
   - *Why:* Identifies where content is consumed — informs UI optimisation (mobile vs TV).

**KPIs:** WoW Completion Rate Change | Top 10 % vs Bottom 10 % split | Stickiness Index

**Slicers:** Title Search | Release Year | Content Tier

---

### PAGE 3: Audience Affinity & Segmentation

**Purpose:** Marketing/Acquisition team view — which audience segments engage with which content.

#### Visuals:

1. **Matrix (Heatmap) — Genre × Age Group × Avg Engagement Score**
   - Rows: Genre
   - Columns: Age Group
   - Values: [Engagement Quality Score]
   - Conditional format: gradient from red (low) → white → green (high)
   - *Why:* Cross-tab visual reveals high-affinity segments for targeted campaigns.

2. **Donut Chart — Revenue Contribution by Region**
   - Segments: Region (5 values)
   - Value: Total Plays
   - *Why:* Geographic audience distribution for licensing and localisation decisions.

3. **Clustered Column Chart — Plays by Age Group and Device Type**
   - X: Age Group
   - Y: Total Plays
   - Series: Device Type
   - *Why:* Reveals consumption habits; millennials on mobile vs boomers on smart TV.

4. **Treemap — Unique Viewers by Genre**
   - Group: Genre
   - Size: Unique Viewers
   - Color: Avg Engagement Score
   - *Why:* Genre reach at a glance; larger box = bigger audience; darker = higher quality.

5. **Ribbon Chart — Genre Ranking by Age Group**
   - X: Age Group
   - Y: Total Plays
   - Series: Genre
   - *Why:* Shows which genre rises/falls across age cohorts — critical for slate diversification.

**KPIs:** Top Genre by Engagement | Top Age Group by Volume | Top Region

**Slicers:** Genre | Age Group | Region | Device Type | Date Range

---

## 3.4 Conditional Formatting Rules

### Scorecard Matrix — Engagement Score Column
| Condition               | Background Color | Font Color |
|-------------------------|-----------------|------------|
| Score ≥ 75              | #1A7F37 (green) | #FFFFFF    |
| Score between 50 and 75 | #E6B330 (amber) | #000000    |
| Score < 50              | #B22222 (red)   | #FFFFFF    |

**Power BI Setup:**
- Select the Engagement Score column in the matrix
- Format → Conditional formatting → Background color → Rules
- Rule 1: If value ≥ 75 → Format with #1A7F37
- Rule 2: If value ≥ 50 and < 75 → Format with #E6B330
- Rule 3: If value < 50 → Format with #B22222

### Content Tier Flag Column
| Value        | Icon  | Color   |
|--------------|-------|---------|
| Top 10%      | ●     | #00C853 |
| Bottom 10%   | ●     | #D50000 |
| Mid Tier     | ●     | #9E9E9E |

**Power BI Setup:**
- Select Tier Flag column
- Format → Conditional formatting → Icons
- Use Rules based on field value text match

### WoW Completion Rate Change (KPI Card)
- Positive change → Arrow Up + Green (#00C853)
- Negative change → Arrow Down + Red (#D50000)
- Zero → Dash + Grey
- Format: Percentage, 2 decimal places
