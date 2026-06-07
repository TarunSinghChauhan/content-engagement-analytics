# DELIVERABLE 4 — Tableau Visualization Complete Specification
## Content Engagement Analytics Platform

---

## Prerequisites

1. Connect Tableau Desktop to `play_events.csv` and `content_catalogue.csv`
2. Create a **Data Source Join**: LEFT JOIN `play_events` → `content_catalogue` ON `content_id`
3. Set `watch_date` as Date field (Data type: Date)
4. Set `rewatch_flag` and `shared_flag` as **Measures** (Integer)
5. Set `genre`, `user_age_group`, `device_type`, `user_region` as **Dimensions**

---

## VISUALIZATION 1 — Engagement Scatter Plot

**Business Purpose:** Identify Star content (high completion + high rewatch) vs Dead content (bottom-left quadrant) at a glance.

### Calculated Fields Required

**1. Completion Percentage**
```
Name: [Completion %]
Formula:
MIN(
    [Watch Duration Minutes] / NULLIF([Content Duration Minutes], 0),
    1.0
) * 100
```

**2. Rewatch Rate**
```
Name: [Rewatch Rate %]
Formula:
AVG([Rewatch Flag]) * 100
```

**3. Audience Reach (Unique Viewers)**
```
Name: [Unique Viewers]
Formula:
COUNTD([User Id])
```

**4. Engagement Score (Tableau simplified version)**
```
Name: [Engagement Score]
Formula:
(
    AVG(MIN([Watch Duration Minutes] / NULLIF([Content Duration Minutes], 0), 1.0)) * 100 * 0.40
  + AVG([Rewatch Flag]) * 100 * 0.25
  + AVG([Shared Flag])  * 100 * 0.20
  + COUNTD([User Id]) * 0.15
)
```

**5. Quadrant Label**
```
Name: [Quadrant]
Formula:
IF AVG([Engagement Score]) >= WINDOW_MEDIAN(AVG([Engagement Score]))
   AND COUNTD([User Id]) >= WINDOW_MEDIAN(COUNTD([User Id]))
   THEN "⭐ Stars"
ELSEIF AVG([Engagement Score]) < WINDOW_MEDIAN(AVG([Engagement Score]))
   AND COUNTD([User Id]) >= WINDOW_MEDIAN(COUNTD([User Id]))
   THEN "🐄 Cash Cows"
ELSEIF AVG([Engagement Score]) >= WINDOW_MEDIAN(AVG([Engagement Score]))
   AND COUNTD([User Id]) < WINDOW_MEDIAN(COUNTD([User Id]))
   THEN "❓ Question Marks"
ELSE "🐕 Dogs"
END
```

### Build Steps

1. **New Sheet** → Rename: "Engagement Scatter Plot"
2. Drag `[Completion %]` → **Columns** shelf
3. Drag `[Rewatch Rate %]` → **Rows** shelf
4. Drag `Content Id` → **Detail** mark (to show one dot per title)
5. Drag `[Unique Viewers]` → **Size** mark
   - Click Size mark → Edit Size → Scale to range [3, 20]
6. Drag `Genre` → **Color** mark
   - Click Color → Edit Colors → use a 10-color qualitative palette (e.g., Tableau 10)
7. Drag `Title` → **Tooltip** mark
8. Drag `[Engagement Score]` → **Tooltip** mark
9. Drag `[Quadrant]` → **Tooltip** mark

### Reference Lines (Quadrant Dividers)
1. Right-click X-axis → **Add Reference Line**
   - Value: Average ([Completion %]) across entire view → Line at median
   - Label: Custom: "Median Completion"
   - Format: Dashed, grey
2. Right-click Y-axis → **Add Reference Line**
   - Value: Average ([Rewatch Rate %]) across entire view
   - Label: Custom: "Median Rewatch"
   - Format: Dashed, grey

### Formatting
- Mark type: **Circle**
- Transparency: 70%
- Title: "Content Engagement Matrix — Completion vs Rewatch"
- Add annotation in each quadrant corner: Stars | Cash Cows | Question Marks | Dogs

---

## VISUALIZATION 2 — Genre × Age Group Affinity Heatmap

**Business Purpose:** Identify which editorial verticals resonate most with each demographic — critical for personalised homepage curation and targeted content investment.

### Calculated Fields Required

**1. Segment Engagement Score**
```
Name: [Segment Engagement Score]
Formula:
(
    AVG(MIN([Watch Duration Minutes] / NULLIF([Content Duration Minutes], 0), 1.0)) * 100 * 0.40
  + AVG([Rewatch Flag]) * 100 * 0.25
  + AVG([Shared Flag])  * 100 * 0.20
  + LOG(COUNTD([User Id]) + 1, 10) / LOG(2001, 10) * 100 * 0.15
)
```
> Note: LOG normalisation avoids extreme reach values dominating the heatmap.

**2. Affinity Tier**
```
Name: [Affinity Tier]
Formula:
IF [Segment Engagement Score] >= 65 THEN "High Affinity"
ELSEIF [Segment Engagement Score] >= 45 THEN "Medium Affinity"
ELSE "Low Affinity"
END
```

**3. Completion Rate (for tooltip detail)**
```
Name: [Avg Completion Rate]
Formula:
AVG(MIN([Watch Duration Minutes] / NULLIF([Content Duration Minutes], 0), 1.0)) * 100
```

### Build Steps

1. **New Sheet** → Rename: "Genre-Age Affinity Heatmap"
2. Drag `Genre` → **Columns** shelf
3. Drag `User Age Group` → **Rows** shelf
4. In the Marks card, change mark type to **Square**
5. Drag `[Segment Engagement Score]` → **Color** mark
   - Click Color → Edit Colors
   - Select Palette: **Red-Green Diverging** (reversed: red = low, green = high)
   - Set Center: 55 (midpoint of typical score range)
6. Drag `[Segment Engagement Score]` → **Label** mark
   - Format: 1 decimal place
7. Drag `[Affinity Tier]` → **Tooltip** mark
8. Drag `[Avg Completion Rate]` → **Tooltip** mark
9. Drag `COUNTD([User Id])` → **Tooltip** mark (label: Unique Viewers)

### Sizing
- Row height: 45 px
- Column width: 90 px
- Font: 11pt Tableau Book

### Sort
- Sort `Genre` by AVG([Segment Engagement Score]) Descending
- Sort `User Age Group` by default order (13-17 → 55+)

### Title
"Audience Affinity Heatmap — Genre × Age Group (Avg Engagement Score)"

### Add: Top 3 Annotations
1. Identify the top 3 (genre, age group) cells by score
2. Right-click each cell → Annotate → Mark
3. Text: "Top 3 Affinity Segment"

---

## VISUALIZATION 3 — Content Decay Curve

**Business Purpose:** Show how quickly each quadrant of content loses its initial audience spike, enabling data-driven decisions about re-promotion windows and algorithmic boost duration.

### Calculated Fields Required

**1. Week Number Since Release**
```
Name: [Week Since Release]
Formula:
DATEPART('week', [Watch Date]) 
- WINDOW_MIN(DATEPART('week', [Watch Date]))
+ 1
```
> Note: For a per-title week calculation, this needs to be computed at the content_id level using a LOD expression.

**2. LOD Expression: First Play Date per Title**
```
Name: [First Play Date]
Formula:
{FIXED [Content Id] : MIN([Watch Date])}
```

**3. Days Since Release**
```
Name: [Days Since Release]
Formula:
DATEDIFF('day', [First Play Date], [Watch Date])
```

**4. Week Since Release (LOD-based — production grade)**
```
Name: [Week Since Release LOD]
Formula:
INT([Days Since Release] / 7) + 1
```

**5. Weekly Plays (Table Calculation)**
```
Name: [Weekly Plays]
Formula:
SUM([Number of Records])
```

**6. Week 1 Baseline (window table calculation)**
```
Name: [Week 1 Baseline]
Formula:
WINDOW_SUM(
    IF [Week Since Release LOD] = 1 THEN [Weekly Plays] ELSE 0 END
)
```

**7. Retention % vs Week 1**
```
Name: [Retention % vs Week 1]
Formula:
ROUND([Weekly Plays] / NULLIF([Week 1 Baseline], 0) * 100, 2)
```

### Build Steps

1. **New Sheet** → Rename: "Content Decay Curve"
2. Drag `[Week Since Release LOD]` → **Columns** shelf
   - Filter: Keep weeks 1 through 12
3. Drag `[Retention % vs Week 1]` → **Rows** shelf
4. Drag `[Quadrant]` → **Color** mark
   - Assign colors:
     - Stars: #FFD700 (gold)
     - Cash Cows: #00A651 (green)
     - Question Marks: #1E90FF (blue)
     - Dogs: #B22222 (red)
5. Mark type: **Line**
6. Drag `[Quadrant]` → **Path** mark to draw one line per quadrant
7. Drag `[Retention % vs Week 1]` → **Label** mark (show at end of line only)

### Reference Lines
- Right-click Y-axis → Add Reference Line
  - Value: 50 (50 % retention threshold)
  - Label: "50% Retention Threshold"
  - Format: Dashed, #888888

### Formatting
- Y-axis: 0 % to 110 %, custom tick every 10 %
- X-axis: Label "Week Since Release"
- Title: "Content Decay Curves — Weekly Viewership Retention by Portfolio Quadrant"
- Add legend annotation: "Each line = average across all titles in quadrant"

---

## Combined Dashboard in Tableau

1. Create a **New Dashboard** (1440 × 900 px)
2. Layout: Tiled
3. **Row 1:** Engagement Scatter Plot (60% width) | Bar chart: Top Genres (40% width)
4. **Row 2:** Genre-Age Heatmap (50%) | Content Decay Curve (50%)
5. Add **Filter Action**: Click on Genre in Scatter Plot → Filter all other sheets to selected genre
6. Add **Highlight Action**: Click on Quadrant in legend → Highlight matching marks in all sheets
7. Add **Title Banner**: "Content Engagement Analytics — Executive View"
8. Add Filter controls: Genre | Date Range | Region
