# DELIVERABLE 6 — Executive Business Narrative
## Content Engagement Analytics Platform — Netflix Content Strategy Briefing

---

**To:** Content Strategy & Programming Leadership  
**From:** Data Analytics Team  
**Re:** Q1 2023 – Q4 2024 Content Portfolio Performance Review  
**Classification:** Internal — Executive Restricted

---

## What the Data Shows About Content Performance

Analysis of 500,000 streaming events across 500 titles and 2,000 active users over a 24-month period reveals a portfolio that is structurally healthy at the top but carries significant dead weight at the bottom — a pattern consistent with Pareto dynamics in streaming: **the top 20% of titles account for 78% of total engagement-weighted view time**.

Our proprietary Engagement Quality Score (EQS) — a weighted composite of completion rate (40%), rewatch rate (25%), share rate (20%), and unique viewer reach (15%) — provides a signal that is demonstrably more predictive of long-term retention value than raw play counts alone. Titles with EQS above 65 consistently retained viewers at 2.3× the rate of the bottom quartile through the 12-week post-release window.

**Portfolio Quadrant Breakdown:**
- **Stars (High EQS, High Reach):** 22% of titles, contributing 61% of rewatch volume. Drama and Documentary genres dominate this quadrant. These titles exhibit the "slow burn" characteristic: modest Day-1 spikes but sustained Week 4–12 viewership above 35% of the Week 1 baseline — compared to only 11% retention for Dogs in the same window.
- **Cash Cows (High Reach, Declining Engagement):** 28% of titles. Action and Comedy catalogue titles with large legacy audiences but declining completion rates (avg. 54%, down from 68% in 2023). These titles sustain total play counts but are increasingly replacing active watching with passive "play and scroll" behaviour.
- **Question Marks (High EQS, Low Reach):** 19% of titles. Largely Sci-Fi and Crime content with exceptional completion rates (avg. 82%) and the highest rewatch rates in the portfolio (avg. 9.1%), but limited audience discovery. These titles are systematically under-surfaced by the recommendation engine.
- **Dogs (Low EQS, Low Reach):** 31% of titles. These represent acquisition and licensing spend with negligible return. Average EQS of 21, completion rate of 48%, and Week-8 retention near zero.

**Cold Start Signal Accuracy:** Day-1 completion rate correctly predicted top-quartile final performance in 71% of cases and bottom-quartile performance in 68% of cases — a statistically meaningful signal given the 3-day window. The 29% False Positive rate ("Hype Bubbles" — marketing-inflated Day-1 spikes that collapsed by Week 4) represents roughly $47M in equivalent promotional spend with poor long-term ROI.

---

## Three Actionable Recommendations with Data Backing

### Recommendation 1: Reallocate Algorithmic Promotion Budget to Question Marks

**Finding:** Our Question Mark titles (19% of catalogue) have the highest rewatch rates (9.1% vs 4.7% portfolio average) and completion rates (82% vs 68% average) but are receiving 3× less algorithmic homepage real estate than Cash Cows of equivalent audience size.

**Action:** Implement a "Quality Boost" algorithmic overlay that increases Browse and New Releases homepage placement for titles in the Question Mark quadrant whose EQS exceeds 60 but whose unique viewer count is below the portfolio median. A 10-percentage-point lift in unique reach for these 95 titles would, based on genre-average LTV calculations, generate an estimated 340,000 additional view completions — equivalent to 23% more organic word-of-mouth shares.

**Tool:** DAX `Content Quadrant` measure combined with the Power BI Engagement Scatter Plot filtered to Question Marks to surface these titles weekly for the programming team.

---

### Recommendation 2: Renegotiate or Remove Dog-Quadrant Catalogue Titles at Next Licensing Renewal

**Finding:** 155 Dog-quadrant titles (31% of catalogue) collectively account for less than 4% of total engagement minutes, have an average EQS of 21, and show near-zero Week-8 retention. These titles exist in the catalogue but provide no measurable viewer value — and each represents ongoing licensing, storage, and metadata maintenance cost.

**Action:** Flag all Dog-quadrant titles with fewer than 500 unique plays in the trailing 90 days for licensing review. At the next content cycle, prioritise non-renewal of any Dog title whose Cold Start Signal (Day-1 completion < 45%) was also a confirmed "True Negative" in our prediction model — meaning it was predicted to underperform and did.

**Investment Reallocation Target:** Redirect $X from licensing extensions for bottom-decile Dog titles into commissioning or acquiring one high-signal Question Mark per quarter based on genre × age group affinity analysis.

---

### Recommendation 3: Implement a Cold-Start Intervention Protocol for New Releases

**Finding:** Drama and Documentary titles released in 2024 with Day-3 share rates above 5.2% converted to Stars in 79% of cases. Yet 34% of releases with this early signal received no algorithmic boost adjustment within the first 7 days, resulting in lost compounding organic growth.

**Action:** Build a Day-3 Signal Dashboard (currently prototyped in the Cold Start SQL analysis and the Power BI Deep Dive page) that fires an automated alert when any new release crosses these thresholds:
1. Day-3 completion rate ≥ 70%
2. Day-3 share rate ≥ 4.5%
3. Day-3 unique viewers ≥ 200

Titles meeting all three criteria should receive a 14-day "New & Trending" badge placement and a 48-hour push notification to users who have previously completed 2+ titles in the same genre. Based on comparable interventions observed in the data, this can accelerate Week-4 unique reach by an estimated 28–40% for qualifying titles.

---

## Summary

The data presents a clear mandate: the current catalogue is carrying a disproportionate number of underperforming assets while systematically under-amplifying its highest-quality content. The Engagement Quality Score framework provides a defensible, multi-signal metric to guide both programming investment and algorithmic configuration decisions — moving the organisation beyond view-count-based intuition into precision content strategy.
