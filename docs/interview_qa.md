# DELIVERABLE 9 — Interview Q&A Preparation
## Content Engagement Analytics Platform

> These answers are written as if you are presenting this project in a Data Analyst interview at a streaming or tech company. Speak these fluently — the goal is confident specificity, not memorisation.

---

## Q1 — SQL Logic: Walk me through your most complex SQL query in this project.

**Answer:**

The most technically demanding query was the Cold Start Signal analysis — Query 4. Let me walk you through it.

The business question was: *can we predict whether a title will be a long-term hit based on its first 1–3 days of viewer behaviour?*

The challenge is that "Day 1" is different for every title — we don't have a clean release date dimension, so I computed a synthetic first-play date per title using `MIN(watch_date) GROUP BY content_id` as a release anchor. That anchor lives in a CTE called `release_anchors`.

From there, I built three separate CTEs — one each for Day-1, Day-3, and Day-30 metrics — using date arithmetic with the anchor as an offset. For Day-30, I recalculated the full Engagement Quality Score using the same weighted formula from Query 1, but scoped to only the first 30 days of each title's life, so it's a fair early-window benchmark.

The most interesting part was the prediction accuracy flag at the end. I used `PERCENTILE_CONT(0.25)` and `PERCENTILE_CONT(0.75)` to compute Day-1 completion quartile boundaries, then classified each title's outcome as a True Positive, True Negative, False Positive (hype bubble), or False Negative (slow burn) using a CASE expression. That gave us a usable signal accuracy rate of ~71% for top-quartile prediction — which I then framed as a business recommendation around early-trigger algorithmic promotion.

The final query joins all five CTEs and uses `CROSS JOIN` to bring in the bounds without subquery repetition.

---

## Q2 — Window Functions: Where did you use window functions and why?

**Answer:**

Window functions appeared in three places across the project:

**1. DENSE_RANK in Query 1** — to rank all 500 titles by their composite Engagement Quality Score. I chose DENSE_RANK over RANK because ties should share the same rank without creating gaps in the output — important when you're presenting a top-10 list to stakeholders and position 4 shouldn't jump to position 6 because of two tied entries at rank 4.

**2. PERCENT_RANK in Query 2** — for the decay curve classification. After computing each title's Week-4 retention ratio, I used `PERCENT_RANK() OVER (ORDER BY w4_retention_ratio ASC)` to identify the bottom and top deciles. PERCENT_RANK returns 0 for the minimum value and 1 for the maximum, so `<= 0.10` gives the bottom 10% of retainers — the "fastest decay" group. I deliberately chose PERCENT_RANK over NTILE here because the distribution is continuous and NTILE's bucket sizing would misrepresent gradual decay patterns.

**3. NTILE(4) in Query 4** — to assign quartiles to Day-30 engagement scores. NTILE is appropriate here because I wanted strict equal-sized groups (exactly 25% of titles per quartile) for the prediction accuracy flag — not percentile ranks. If I used PERCENT_RANK, the quartile boundary would shift depending on the current filter context, making the prediction comparison unstable.

The general rule I used: RANK/DENSE_RANK for ordered lists, PERCENT_RANK for distribution positioning, NTILE for bucket assignment.

---

## Q3 — CTEs: Why did you structure your SQL using CTEs rather than subqueries or temp tables?

**Answer:**

For these analytical queries, CTEs were the right tool for three reasons:

**Readability and auditability:** CTEs give each logical step a name — `raw_metrics`, `bounds`, `normalised`, `scored`. When a content lead or a peer reviewer looks at the query, they can follow the analytical logic linearly without decoding nested subquery layers. In a production environment where queries get peer-reviewed and modified over time, this matters.

**Step-by-step validation:** With CTEs, I can comment out the final SELECT and run intermediate CTEs in isolation to verify intermediate results. For example, I can run just through `normalised` to confirm that min-max scaling is working before applying the weights. With subqueries, you can't do this easily.

**Avoiding redundant computation:** The `bounds` CTE is `CROSS JOIN`ed into `normalised` rather than being a subquery repeated four times. Without CTEs, each normalised column would require a separate correlated subquery for `MIN()` and `MAX()`, which PostgreSQL would execute multiple times.

**When I'd use temp tables instead:** If the CTE were referenced more than once in the same query, PostgreSQL does not materialise it by default (before PG 12) — it re-executes it. In that case, creating a temp table with an index would be more efficient. For these five queries, each CTE is referenced only once, so CTEs are the cleaner choice.

---

## Q4 — KPI Selection: Why did you choose completion rate, rewatch rate, share rate, and reach — and those specific weights?

**Answer:**

I started from the business question: *what behaviours indicate that a viewer genuinely found value in the content*, not just that they clicked on it.

- **Completion rate (40%)** is the highest-weight signal because it's the most direct proxy for content quality. A user who watches 90% of a two-hour film is demonstrably engaged — they made an active decision not to stop. Raw play counts don't capture this; a three-second autoplay and a 90-minute completion look identical in a view-count metric.

- **Rewatch rate (25%)** captures long-term value. A title that users return to repeatedly has "catalogue stickiness" — it retains subscribers. Rewatch is especially important for the platform's retention argument against churn.

- **Share rate (20%)** is organic acquisition. When a user shares content, they are effectively doing unpaid marketing. For a streaming platform, this drives new subscriber growth without CAC.

- **Reach / unique viewers (15%)** is given the lowest weight deliberately. It measures breadth, not quality. A poorly-rated title that was heavily promoted might have high reach but terrible completion — so reach alone is misleading. It's included because a title with extremely low reach may not have had a fair chance to accumulate engagement signals.

The weights are not arbitrary — they reflect the relative strategic value of each behaviour. I'd adjust them if the platform's current strategic priority is subscriber acquisition (increase share_rate weight) or retention (increase rewatch weight). In a real project, I'd ideally validate these weights through correlation analysis against known business outcomes (like subscriber renewal rates).

---

## Q5 — Business Judgement: A title has a 90% completion rate but only 100 unique viewers. Should it be classified as a Star?

**Answer:**

No — and this is exactly why reach is a component of the Engagement Quality Score, even at a lower weight.

A title with 100 unique viewers and 90% completion has exceptional quality signal, but almost no evidence that the audience exists at scale. In BCG portfolio terms, it belongs in the **Question Mark** quadrant — high engagement, low reach — not Stars. Stars require *both* high-quality engagement *and* meaningful audience size.

The right business action here is to investigate *why* the reach is low:
1. **Was it properly promoted?** If it was buried on page 3 of the catalogue with no homepage placement, the low reach is a discovery problem — not a content problem. This is actually the most common case in my analysis, and it's where the algorithmic reallocation recommendation comes from.
2. **Is it niche content with a small but highly engaged audience?** Some documentary or foreign-language content has naturally smaller audiences but extremely high completion rates. This can still be commercially valuable if the niche audience has high LTV.
3. **Was it recently released?** A title with only 7 days of data will always have low reach — it hasn't had time to accumulate viewers. The cold-start signal analysis specifically addresses this by using a 30-day normalisation window.

In the dashboard, I flag this as a Question Mark with a note for the programming team to review its promotion status before any deprioritisation decision.

---

## Q6 — Dashboard Design: Why did you build three separate Power BI pages rather than one?

**Answer:**

The principle I follow is: *one page = one decision-maker, one set of decisions*. Mixing executive KPIs with granular operational metrics on the same canvas creates cognitive overload and implicitly suggests that all information is equally important.

**Page 1 — Executive Scorecard** is designed for a VP of Content or a C-level leader who has 90 seconds. It answers: "Is the catalogue healthy? Is engagement trending up or down? Which genres are winning?" Six KPI cards and one scorecard matrix at a glance. No scrolling, no deep-dive required.

**Page 2 — Engagement Deep Dive** is for a Content Strategy Analyst or Programming Manager who needs to understand *why* a specific title is over or underperforming. The scatter plot surfaces outliers; the waterfall shows which engagement component is weak; the cold-start table reveals hype bubbles. This page triggers an action.

**Page 3 — Audience Affinity** is for the Marketing team making targeting and media spend decisions. They need to know which demographic responds to which genre on which device. A heatmap and demographic breakdowns serve this need; the scorecard from Page 1 doesn't.

This separation also has a technical benefit: slicers on Page 1 don't inadvertently filter Page 3's segmentation view, which would break the analysis if a content filter is applied.

---

## Q7 — Stakeholder Communication: How would you explain the Engagement Quality Score to a non-technical executive?

**Answer:**

I'd use an analogy: *"Think of it like a restaurant review score that combines not just the star rating, but whether customers came back, whether they told their friends, and how busy the restaurant actually is — all weighted by how much each factor tells us about the restaurant's true quality."*

For the actual number: *"We score every title from 0 to 100. A score of 75 means a title is performing in the upper 25% of our catalogue across all four quality signals. A score of 30 means it's finishing poorly, 40% of viewers are dropping off early, nobody's rewatching it, and it's not being shared."*

I'd then show them one example comparison — a title they recognise as a hit with a high score, and a title that got a lot of press but flopped, with a low score — to anchor the metric in something tangible before showing the full scorecard.

The key is to never lead with the formula. Lead with the insight, offer the formula only if they ask.

---

## Q8 — Trade-offs & Assumptions: What assumptions did you make in this project that could affect the conclusions?

**Answer:**

I made several deliberate simplifications worth disclosing:

**1. MIN(watch_date) as release date proxy.** In production, a title's release date is a known metadata field. I used the first observed play event as a release date approximation because the synthetic data doesn't include a guaranteed release date. This means very popular titles (with high early viewership) have more accurate anchors, while obscure titles may have a first-play date days or weeks after actual release, compressing their decay curve.

**2. Uniform user sampling.** In the generator, I selected users uniformly at random across all 2,000 users. Real streaming platforms have power users who account for a disproportionate share of views. This would inflate unique viewer counts for niche content and slightly compress the Pareto skew in content popularity.

**3. Independent share and rewatch flags.** In the synthetic data, share and rewatch events are assigned probabilistically per play, independently of each other. In reality, a user who rewatches is more likely to share — these flags are correlated. This means the synthetic data slightly underestimates the compounding effect of rewatch-and-share behaviour in high-quality content.

**4. Fixed weighting in the EQS.** The 40/25/20/15 weights are informed assumptions, not empirically validated coefficients. In a production deployment, I would run a regression analysis correlating each component against a known retention outcome (like 30-day subscriber renewal) to derive data-driven weights.

In an interview, disclosing these assumptions proactively demonstrates analytical maturity — it shows that I know where the model is strong and where it could break.

---

## Q9 — SQL Window Functions Advanced: How does PERCENTILE_CONT differ from PERCENT_RANK, and when did you use each?

**Answer:**

These are frequently confused — they serve completely different purposes.

**PERCENTILE_CONT(p) WITHIN GROUP (ORDER BY expr)** is an *aggregate function* that returns the value at the `p`-th percentile of a column's distribution. It interpolates between adjacent values when necessary — that's the "continuous" part. I used this in Queries 4 and 5 to compute the 25th and 75th percentile threshold values of Day-1 completion rate and engagement score — essentially finding "what score marks the boundary of the top quartile?"

```sql
PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY d1_completion_rate)
-- Returns: the actual completion rate value at the 75th percentile
-- e.g., 72.4 — meaning "titles above 72.4% are in the top quartile"
```

**PERCENT_RANK() OVER (ORDER BY expr)** is a *window function* that returns each row's relative rank within its result set as a fraction between 0 and 1. It doesn't give you a threshold value — it tells you where each row sits in the distribution.

```sql
PERCENT_RANK() OVER (ORDER BY w4_retention_ratio ASC)
-- Returns: 0.0 for the fastest-decaying title, 1.0 for slowest
-- I used this to flag bottom 10% decayers: WHERE result <= 0.10
```

The practical rule: use PERCENTILE_CONT when you need a specific threshold value for classification; use PERCENT_RANK when you need to know each row's relative position in the distribution.

---

## Q10 — Career & Project: What would you do differently if you had more time or were doing this at Netflix for real?

**Answer:**

Four things:

**1. Empirically validate the EQS weights.** I'd run a logistic regression — or Shapley value analysis — using actual subscriber renewal data as the dependent variable and the four engagement signals as features. That would replace my assumed 40/25/20/15 weights with coefficients grounded in business outcomes.

**2. Add session-level analysis.** My current grain is one row per play event. In production, I'd also want session-level data — what did the user watch before and after a given title, did they return the same day, did this title trigger a binge. This enables path analysis and funnel modelling that the current schema doesn't support.

**3. Build a statistical inference layer for the Cold Start model.** My 71% accuracy figure is a descriptive statistic, not a rigorous model. I'd formalise it as a binary classifier (Day-1 signals → top-quartile flag) using logistic regression, report precision and recall separately, and set a confidence threshold before triggering any automated algorithmic boost.

**4. Automate the pipeline.** Right now the analysis is a snapshot. At Netflix scale, this would run daily via Airflow or dbt — incrementally updating the engagement scores, triggering Power BI dataset refreshes, and pushing alert notifications to the content team's Slack channel when a new title crosses the cold-start threshold. The analytical logic I've built is the hard part — operationalising it is the next step.
