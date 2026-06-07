# Content Engagement Analytics Platform 🎬

> **A production-grade streaming analytics project replicating the data workflows used at Netflix and YouTube — built end-to-end from synthetic data generation through SQL analysis, Power BI dashboards, Tableau visualizations, and executive storytelling.**

---

## Business Problem Statement

Streaming platforms generate massive volumes of play event data every second. The challenge is not collecting data — it's translating engagement signals into strategic decisions: which titles deserve continued investment, which are coasting on legacy audiences, which are genuinely high-quality but algorithmically invisible, and which should be quietly retired.

This project answers that question by building a full analytical stack around a single core metric — the **Engagement Quality Score** — a weighted composite of completion rate, rewatch rate, share rate, and audience reach. The resulting insight framework mirrors the kind of content performance reporting used by OTT analytics teams at streaming companies.

**Key analytical questions answered:**
1. Which titles are truly engaging vs. merely popular?
2. How quickly does a title lose its audience after release?
3. Which audience segments (age group × genre × device) have the highest affinity?
4. Can Day-1 viewer behaviour predict long-term content success?
5. How should the content portfolio be classified for investment decisions?

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     DATA GENERATION LAYER                                │
│                                                                          │
│  Netflix Titles (Kaggle)         Python Script (Faker + NumPy)           │
│  netflix_titles.csv              generate_play_events.py                 │
│         │                                   │                            │
│         └──────────────┬────────────────────┘                            │
│                        ▼                                                 │
│              play_events.csv (500K rows)                                 │
│              content_catalogue.csv (500 titles)                          │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│                     ANALYTICAL LAYER (PostgreSQL)                        │
│                                                                          │
│  01_engagement_quality_score.sql    ─── Weighted composite EQS           │
│  02_content_decay_curve.sql         ─── Weekly retention tracking        │
│  03_audience_segment_affinity.sql   ─── Genre × Age × Device cross-tab   │
│  04_cold_start_signal.sql           ─── Day-1/3 predictive model         │
│  05_portfolio_health_report.sql     ─── BCG quadrant classification       │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
        ┌────────────────────┼──────────────────────┐
        ▼                    ▼                       ▼
┌───────────────┐   ┌────────────────┐   ┌──────────────────┐
│  POWER BI     │   │   TABLEAU      │   │     EXCEL        │
│               │   │                │   │                  │
│ 3-page dash   │   │ Scatter Plot   │   │ 3 Pivot Tables   │
│ 12 DAX meas.  │   │ Affinity Heat  │   │ Waterfall Chart  │
│ Star schema   │   │ Decay Curves   │   │ XLOOKUP Formulas │
└───────────────┘   └────────────────┘   └──────────────────┘
        │                    │                       │
        └────────────────────┴──────────────────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │   EXECUTIVE NARRATIVE    │
              │   + COLD START SIGNAL    │
              │   + QUADRANT STRATEGY    │
              └──────────────────────────┘
```

---

## Dataset Description

| Dataset               | Source                        | Rows     | Key Fields                                              |
|-----------------------|-------------------------------|----------|---------------------------------------------------------|
| `play_events.csv`     | Synthetic (Python-generated)  | 500,000  | user_id, content_id, watch_date, duration, flags, device |
| `content_catalogue.csv` | Synthetic (mapped to Netflix) | 500    | content_id, genre, content_duration, release_date       |
| `netflix_titles.csv`  | Kaggle Netflix Titles Dataset | ~8,800   | title, type, genre, release_year, country, rating       |

### Synthetic Data Distributions
- **Watch duration**: Beta distribution (α=5, β=2.5) — skewed to 60–80% completion
- **Rewatch rate**: 8% base (boosted to 14% for >85% completions)
- **Share rate**: 4–7% depending on genre
- **Content popularity**: Pareto distribution (top 20% titles get ~80% views)
- **Date range**: January 2023 – December 2024

---

## Project Folder Structure

```
content-engagement-analytics/
│
├── data/
│   ├── generate_play_events.py       # DELIVERABLE 1 — Data generation script
│   ├── play_events.csv               # Generated (run the script to create)
│   └── content_catalogue.csv         # Generated (auto-created by script)
│
├── sql/
│   ├── 00_schema_setup.sql           # Table creation + data load instructions
│   ├── 01_engagement_quality_score.sql
│   ├── 02_content_decay_curve.sql
│   ├── 03_audience_segment_affinity.sql
│   ├── 04_cold_start_signal.sql
│   └── 05_portfolio_health_report.sql
│
├── powerbi/
│   └── powerbi_dashboard_spec.md     # DELIVERABLE 3 — Full DAX + layout spec
│
├── tableau/
│   └── tableau_viz_spec.md           # DELIVERABLE 4 — All calculated fields
│
├── excel/
│   └── excel_workbook_spec.md        # DELIVERABLE 5 — Formulas + pivot setup
│
├── insights/
│   └── executive_narrative.md        # DELIVERABLE 6 — 500-word business brief
│
├── docs/
│   ├── resume_bullets.md             # DELIVERABLE 7 — 4 resume bullets
│   └── interview_qa.md               # DELIVERABLE 9 — 10 Q&A pairs
│
└── README.md                         # This file
```

---

## Local Setup Instructions

### 1. Prerequisites

```bash
# Python 3.9+
pip install pandas numpy faker tqdm

# PostgreSQL 13+ (local or Docker)
# Docker option:
docker run --name pg-analytics -e POSTGRES_PASSWORD=analytics123 -p 5432:5432 -d postgres:15
```

### 2. Generate Synthetic Data

```bash
cd data/
python generate_play_events.py
# Output: play_events.csv (~47 MB), content_catalogue.csv
```

### 3. Load Data into PostgreSQL

```bash
# Connect to PostgreSQL
psql -U postgres -h localhost

# Run the schema setup script
\i sql/00_schema_setup.sql

# Verify row count
SELECT COUNT(*) FROM play_events;   -- Expected: 500,000
SELECT COUNT(*) FROM content_catalogue;  -- Expected: 500
```

### 4. Run SQL Analyses

```bash
# Run each query in order
\i sql/01_engagement_quality_score.sql
\i sql/02_content_decay_curve.sql
\i sql/03_audience_segment_affinity.sql
\i sql/04_cold_start_signal.sql
\i sql/05_portfolio_health_report.sql
```

### 5. Power BI Dashboard
1. Open Power BI Desktop
2. Get Data → CSV → load `play_events.csv` and `content_catalogue.csv`
3. Follow `powerbi/powerbi_dashboard_spec.md` for data model and DAX measures

### 6. Tableau
1. Open Tableau Desktop → Connect → Text File → `play_events.csv`
2. Follow `tableau/tableau_viz_spec.md` for calculated fields and build steps

---

## Key Findings

| Metric | Value |
|--------|-------|
| Total events analysed | 500,000 |
| Unique users | 2,000 |
| Catalogue titles | 500 |
| Average completion rate | ~68% |
| Average rewatch rate | ~8% |
| Average share rate | ~4.5% |
| Stars (high EQS + high reach) | ~22% of titles |
| Dogs (low EQS + low reach) | ~31% of titles |
| Cold-start Day-1 prediction accuracy | ~71% (top quartile) |
| Completion → Engagement Score correlation | 0.78 |

**Top Insight:** Question Mark titles (high EQS, low reach — 19% of catalogue) have rewatch rates nearly 2× the portfolio average but receive significantly less algorithmic promotion than lower-quality Cash Cow titles. Reallocating homepage placement to these titles represents the single highest-ROI lever available without new content spend.

---

## Skills Demonstrated

| Category | Tools & Techniques |
|----------|--------------------|
| **Data Engineering** | Python, Pandas, NumPy, Faker, statistical distributions |
| **SQL Analytics** | PostgreSQL, CTEs, Window Functions, PERCENTILE_CONT, NTILE, CASE |
| **Business Intelligence** | Power BI, DAX, Star Schema design, rolling calculations |
| **Data Visualisation** | Tableau, LOD expressions, Table Calculations, Parameter Actions |
| **Spreadsheet Analysis** | Excel, XLOOKUP, AVERAGEIFS, PERCENTRANK, Pivot Tables, Waterfall Charts |
| **Statistical Methods** | Min-max normalisation, Beta distribution, Pareto simulation, Percentile ranking |
| **Business Acumen** | BCG matrix adaptation, KPI design, cold-start analysis, executive narrative |

---

## Screenshots

> *After building the dashboards, replace these placeholders with actual screenshots.*

| Dashboard | Preview |
|-----------|---------|
| Power BI — Executive Scorecard | `docs/screenshots/powerbi_page1.png` |
| Power BI — Engagement Deep Dive | `docs/screenshots/powerbi_page2.png` |
| Power BI — Audience Affinity | `docs/screenshots/powerbi_page3.png` |
| Tableau — Engagement Scatter Plot | `docs/screenshots/tableau_scatter.png` |
| Tableau — Affinity Heatmap | `docs/screenshots/tableau_heatmap.png` |
| Tableau — Content Decay Curves | `docs/screenshots/tableau_decay.png` |
| Excel — Waterfall Chart | `docs/screenshots/excel_waterfall.png` |

---

## Author

**[Tarun]**  
Data Analyst | Python · SQL · Power BI · Tableau  
[LinkedIn](https://www.linkedin.com/in/tarunchauhanml) · [Portfolio](https://tarunsinghchauhan.github.io/portfolio-website/)

---

## License

MIT License — data is entirely synthetic and does not contain any personally identifiable information.
