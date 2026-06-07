# DELIVERABLE 5 — Excel Workbook Complete Specification
## Content Engagement Analytics Platform

---

## Workbook Structure

| Tab Name                  | Color Code | Purpose                                          |
|---------------------------|------------|--------------------------------------------------|
| `README`                  | Blue       | Instructions and navigation guide                |
| `Raw_Data`                | Grey       | Imported play_events.csv (source of truth)       |
| `Content_Catalogue`       | Grey       | content_catalogue.csv reference table            |
| `PT1_Genre_Device`        | Orange     | Pivot Table 1: Engagement by Genre & Device      |
| `PT2_Monthly_Quadrant`    | Orange     | Pivot Table 2: Monthly Viewership by Quadrant    |
| `PT3_AgeGroup_Completion` | Orange     | Pivot Table 3: Age Group × Completion Rate       |
| `Waterfall_Chart`         | Green      | Engagement Score Decomposition Waterfall         |
| `Formulas_Reference`      | Purple     | All custom formulas with examples                |
| `Executive_Summary`       | Red        | Key findings narrative and KPI snapshot          |

---

## TAB 1 — Raw_Data (play_events.csv Import)

### Import Instructions

1. Open Excel → **Data** tab → **Get Data** → **From Text/CSV**
2. Navigate to `play_events.csv`
3. In the Power Query preview:
   - Confirm delimiter: **Comma**
   - Set `watch_date` → Data Type: **Date**
   - Set `watch_duration_minutes`, `content_duration_minutes` → Data Type: **Whole Number**
   - Set `rewatch_flag`, `shared_flag` → Data Type: **Whole Number** (0/1)
   - All other columns → **Text**
4. Click **Load** → Load to existing worksheet (Raw_Data tab, cell A1)
5. After loading, press **Ctrl+T** to format as a Table
   - Table name: `tbl_PlayEvents`
   - Check "My table has headers"

### Column Verification Checklist
After import, verify these columns exist with correct types:
- [ ] event_id (Text)
- [ ] user_id (Text)
- [ ] content_id (Text)
- [ ] watch_date (Date)
- [ ] watch_duration_minutes (Number)
- [ ] content_duration_minutes (Number)
- [ ] rewatch_flag (Number — 0 or 1 only)
- [ ] shared_flag (Number — 0 or 1 only)
- [ ] device_type (Text)
- [ ] user_age_group (Text)
- [ ] user_region (Text)
- [ ] genre (Text)

Similarly import `content_catalogue.csv` → Table name: `tbl_ContentCatalogue`

---

## TAB 4 — PT1_Genre_Device: Engagement by Genre & Device

### Pivot Table 1 Setup

1. Click inside `tbl_PlayEvents` → **Insert** → **PivotTable** → New Sheet
2. Rename sheet: `PT1_Genre_Device`

**PivotTable Field Configuration:**
- **Rows:** `genre`
- **Columns:** `device_type`
- **Values (add 5 value fields):**

  | Value Field                | Aggregation     | Number Format     |
  |----------------------------|-----------------|-------------------|
  | `watch_duration_minutes`   | Average         | Number, 1 decimal |
  | `rewatch_flag`             | Average         | Percentage, 2 dp  |
  | `shared_flag`              | Average         | Percentage, 2 dp  |
  | `content_duration_minutes` | Average         | Number, 1 decimal |
  | `event_id`                 | Count           | Number, 0 dp      |

3. **Calculated Field** — Completion Rate:
   - PivotTable Analyze → Fields, Items & Sets → **Calculated Field**
   - Name: `Completion_Rate`
   - Formula: `= watch_duration_minutes / content_duration_minutes`

4. **Calculated Field** — Engagement Score:
   - Name: `Engagement_Score_Approx`
   - Formula: `= (watch_duration_minutes/content_duration_minutes)*0.40 + rewatch_flag*0.25 + shared_flag*0.20`

5. Apply **Conditional Formatting** to Engagement_Score_Approx column:
   - Three-Color Scale: Red (min) → Yellow (mid: 0.05) → Green (max)

6. Sort Rows by `Engagement_Score_Approx` Descending

---

## TAB 5 — PT2_Monthly_Quadrant: Monthly Viewership by Quadrant

### Prerequisites

First, add a helper column in Raw_Data (Column N):
```excel
Column Header: completion_pct
Cell N2:      =[@watch_duration_minutes]/[@content_duration_minutes]
```

Add helper column (Column O):
```excel
Column Header: quadrant_helper_score
Cell O2:       =N2*0.40 + [@rewatch_flag]*0.25 + [@shared_flag]*0.20
```

Add Year-Month column (Column P):
```excel
Column Header: year_month
Cell P2:       =TEXT([@watch_date],"YYYY-MM")
```

### Pivot Table 2 Setup

1. Insert PivotTable on sheet `PT2_Monthly_Quadrant`

**Field Configuration:**
- **Rows:** `year_month` (group by month — right-click → Group → Months)
- **Columns:** Manual grouping by quadrant (see note below)
- **Values:** Count of `event_id` | Average of `completion_pct`

**Quadrant Grouping Note:**
Since quadrant assignment requires normalised scoring (not directly available in Excel without Python/SQL), use the helper score quartile as proxy:
- Add column `quadrant_label` in Raw_Data:

```excel
Column Header: quadrant_label
Cell Q2:
=IF(AND(O2>=PERCENTILE($O$2:$O$500001,0.5), COUNTIF($C$2:$C$500001,[@content_id])>=MEDIAN(IF($C$2:$C$500001=$C$2,$C$2:$C$500001))),"Stars",
 IF(AND(O2<PERCENTILE($O$2:$O$500001,0.5), COUNTIF($C$2:$C$500001,[@content_id])>=MEDIAN(IF($C$2:$C$500001=$C$2,$C$2:$C$500001))),"Cash Cows",
 IF(AND(O2>=PERCENTILE($O$2:$O$500001,0.5), COUNTIF($C$2:$C$500001,[@content_id])<MEDIAN(IF($C$2:$C$500001=$C$2,$C$2:$C$500001))),"Question Marks","Dogs")))
```

> **Practical tip for 500k rows:** Instead of computing quadrant in Excel (slow), export the SQL Query 5 result to a CSV called `content_quadrants.csv` with columns `content_id, quadrant`. Then XLOOKUP the quadrant into Raw_Data.

Then in Pivot:
- **Columns:** `quadrant_label`
- **Values:** Count of `event_id`

Format as **Stacked Column Chart** on same sheet.

---

## TAB 6 — PT3_AgeGroup_Completion: Age Group × Completion Rate

### Pivot Table 3 Setup

1. Insert PivotTable on sheet `PT3_AgeGroup_Completion`

**Field Configuration:**
- **Rows:** `user_age_group`
- **Columns:** `genre`
- **Values:**
  - Average of `completion_pct` (requires the helper column from above)
  - Count of `event_id`

2. Sort Age Group in logical order: 13-17 → 18-24 → 25-34 → 35-44 → 45-54 → 55+
   (Manual sort: right-click → Sort → More options → Custom list)

3. Apply **Conditional Formatting**:
   - Values cells → Color Scale: White (40%) → Deep Blue (100%)
   - This creates a natural heatmap effect

4. **Insert PivotChart:**
   - Select the pivot → Insert → PivotChart → **Clustered Bar Chart**
   - Title: "Average Completion Rate by Age Group and Genre"

---

## TAB 7 — Waterfall_Chart: Engagement Score Decomposition

### Data Preparation (manual table on this sheet)

Create this table in cells A1:C7 of the `Waterfall_Chart` sheet:

| Row | Category               | Value  | Type  |
|-----|------------------------|--------|-------|
| 1   | Start                  | 0      | Total |
| 2   | Completion (40% wt)    | [calc] | Bar   |
| 3   | Rewatch (25% wt)       | [calc] | Bar   |
| 4   | Share (20% wt)         | [calc] | Bar   |
| 5   | Reach (15% wt)         | [calc] | Bar   |
| 6   | Engagement Score       | [calc] | Total |

Use AVERAGEIF from Raw_Data to populate the values:

```excel
=AVERAGEIF(Raw_Data!$C:$C, "[your content_id]", Raw_Data!$N:$N) * 100 * 0.40
```

Or for portfolio-wide averages:
```excel
B3 (Completion contribution): =AVERAGE(Raw_Data!N:N)*100*0.40
B4 (Rewatch contribution):    =AVERAGE(Raw_Data!G:G)*100*0.25
B5 (Share contribution):      =AVERAGE(Raw_Data!H:H)*100*0.20
B6 (Reach contribution):      =15        (placeholder; reach contribution varies by content)
B7 (Total):                   =SUM(B3:B6)
```

### Chart Creation

1. Select A1:B7 → Insert → Chart → **Waterfall**
2. Right-click the "Start" and "Engagement Score" bars → **Set as total**
3. Format each bar:
   - Completion: #1E90FF (blue)
   - Rewatch: #32CD32 (green)
   - Share: #FFD700 (gold)
   - Reach: #FF8C00 (orange)
   - Total: #E50914 (netflix red)
4. Add data labels: Value on each bar
5. Title: "Engagement Score Decomposition — Weighted Component Waterfall"

---

## TAB 8 — Formulas_Reference

### FORMULA 1 — XLOOKUP: Enrich Play Events with Title Metadata

Used to bring `title` and `genre` from `content_catalogue.csv` into `play_events`.

**Setup:**
- In `Raw_Data` sheet, add Column R header: `title`
- In `Raw_Data` sheet, add Column S header: `catalogue_genre`

```excel
=== Cell R2 (Title from Catalogue) ===
=XLOOKUP(
    [@content_id],                       -- Lookup value: content_id in play_events
    tbl_ContentCatalogue[content_id],    -- Lookup array: content_id column in catalogue
    tbl_ContentCatalogue[title],         -- Return array: title column
    "Not Found",                         -- If not found
    0,                                   -- Exact match
    1                                    -- Search first-to-last
)

=== Cell S2 (Genre from Catalogue, as cross-check) ===
=XLOOKUP(
    [@content_id],
    tbl_ContentCatalogue[content_id],
    tbl_ContentCatalogue[genre],
    "Unknown",
    0,
    1
)
```

---

### FORMULA 2 — AVERAGEIFS: Segment-Level Metrics

**Average completion rate for a specific age group and genre:**

```excel
=AVERAGEIFS(
    Raw_Data[completion_pct],        -- Average this column
    Raw_Data[user_age_group],        -- Criteria range 1
    "18-24",                         -- Criteria 1: age group
    Raw_Data[genre],                 -- Criteria range 2
    "Drama"                          -- Criteria 2: genre
)
```

**Average rewatch rate for mobile users in a specific region:**

```excel
=AVERAGEIFS(
    Raw_Data[rewatch_flag],
    Raw_Data[device_type],
    "mobile",
    Raw_Data[user_region],
    "North America"
)
```

**Average completion rate for content released in 2024 only:**

```excel
=AVERAGEIFS(
    Raw_Data[completion_pct],
    Raw_Data[watch_date],    ">=" & DATE(2024,1,1),
    Raw_Data[watch_date],    "<=" & DATE(2024,12,31)
)
```

---

### FORMULA 3 — PERCENTRANK: Scoring Normalisation

**Percentile rank of a title's engagement score relative to all titles:**

```excel
=PERCENTRANK.INC(
    PT1_Genre_Device!$B$5:$B$15,   -- Array of all engagement scores
    B5,                              -- The score to rank
    2                                -- Significance (2 decimal places)
)
```

**Flag if a title is in the top 10%:**

```excel
=IF(
    PERCENTRANK.INC($G$2:$G$501, G2, 2) >= 0.90,
    "Top 10%",
    IF(
        PERCENTRANK.INC($G$2:$G$501, G2, 2) <= 0.10,
        "Bottom 10%",
        "Mid Tier"
    )
)
```

**Min-Max normalisation (mirrors SQL Query 1 normalisation):**

```excel
=== Normalise a completion rate value to 0-100 scale ===
=(B2-MIN($B$2:$B$501))/(MAX($B$2:$B$501)-MIN($B$2:$B$501))*100
```

**Weighted engagement score using normalised components:**

```excel
=== Cell Z2: Full Engagement Score Formula ===
=(
    ((N2 - MIN($N$2:$N$500001)) / (MAX($N$2:$N$500001) - MIN($N$2:$N$500001)) * 100 * 0.40)  -- Completion norm
  + ((G2 - MIN($G$2:$G$500001)) / (MAX($G$2:$G$500001) - MIN($G$2:$G$500001)) * 100 * 0.25)  -- Rewatch norm
  + ((H2 - MIN($H$2:$H$500001)) / (MAX($H$2:$H$500001) - MIN($H$2:$H$500001)) * 100 * 0.20)  -- Share norm
  + (COUNTIF($C$2:$C$500001, C2) / MAX(COUNTIF($C$2:$C$500001, $C$2:$C$500001)) * 100 * 0.15) -- Reach norm
)
```
> Note: This formula is computationally heavy on 500k rows. Pre-calculate components in helper columns.
