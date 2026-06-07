"""
==============================================================================
Content Engagement Analytics Platform -- Streamlit Dashboard
==============================================================================
Run locally  : streamlit run app.py
Deploy free  : https://streamlit.io/cloud  (connect GitHub repo, select app.py)
==============================================================================
"""

import math
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Content Engagement Analytics",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Dark gradient background */
.stApp { background: linear-gradient(135deg, #0d0d1a 0%, #0f1923 50%, #0a0f1e 100%); }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #12192d 0%, #0d1520 100%);
    border-right: 1px solid #1e2d45;
}

/* KPI metric cards */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #1a2540 0%, #151e35 100%);
    border: 1px solid #253350;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    transition: transform 0.2s;
}
[data-testid="metric-container"]:hover { transform: translateY(-2px); }

/* Metric label */
[data-testid="metric-container"] label {
    color: #7a9cc4 !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* Metric value */
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #e8f0fe !important;
    font-size: 1.7rem !important;
    font-weight: 700 !important;
}

/* Metric delta */
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-size: 0.82rem !important;
}

/* Section headers */
h1 { color: #e8f0fe !important; font-weight: 700 !important; }
h2 { color: #c5d8f0 !important; font-weight: 600 !important; }
h3 { color: #a8c4e0 !important; font-weight: 500 !important; }

/* Tabs */
[data-baseweb="tab-list"] { background: #1a2540; border-radius: 10px; padding: 4px; gap: 4px; }
[data-baseweb="tab"] { color: #7a9cc4 !important; border-radius: 8px !important; font-weight: 500; }
[aria-selected="true"] { background: #e50914 !important; color: white !important; }

/* Divider */
hr { border-color: #1e2d45; }

/* Plotly chart bg */
.js-plotly-plot { border-radius: 12px; overflow: hidden; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0d0d1a; }
::-webkit-scrollbar-thumb { background: #253350; border-radius: 3px; }

/* Selectbox / multiselect */
[data-baseweb="select"] { background: #1a2540 !important; }
</style>
""", unsafe_allow_html=True)

# ── Colour palette (consistent across charts) ─────────────────────────────────
PALETTE = {
    "red":    "#e50914",
    "blue":   "#1e90ff",
    "green":  "#00c853",
    "gold":   "#ffd700",
    "purple": "#9c27b0",
    "teal":   "#00bcd4",
    "orange": "#ff6d00",
    "pink":   "#f06292",
    "bg":     "#0d0d1a",
    "card":   "#1a2540",
    "border": "#253350",
    "text":   "#e8f0fe",
    "muted":  "#7a9cc4",
}

QUADRANT_COLORS = {
    "Stars":          "#ffd700",
    "Cash Cows":      "#00c853",
    "Question Marks": "#1e90ff",
    "Dogs":           "#e57373",
}

GENRE_COLORS = px.colors.qualitative.Bold


# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING & CACHING
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner="Loading play events...")
def load_data():
    import os
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    pe_path  = os.path.join(data_dir, "play_events.csv")
    cc_path  = os.path.join(data_dir, "content_catalogue.csv")

    pe = pd.read_csv(pe_path,  parse_dates=["watch_date"])
    cc = pd.read_csv(cc_path,  parse_dates=["release_date"])

    # Enrich -----------
    pe = pe.merge(cc[["content_id", "release_date"]], on="content_id", how="left")
    pe["completion_pct"] = (
        pe["watch_duration_minutes"] / pe["content_duration_minutes"]
    ).clip(upper=1.0)
    pe["watch_month"]   = pe["watch_date"].dt.to_period("M").astype(str)
    pe["watch_year"]    = pe["watch_date"].dt.year

    return pe, cc


@st.cache_data(show_spinner="Computing engagement scores...")
def compute_engagement_scores(pe: pd.DataFrame) -> pd.DataFrame:
    raw = pe.groupby("content_id").agg(
        completion_rate = ("completion_pct",          "mean"),
        rewatch_rate    = ("rewatch_flag",            "mean"),
        share_rate      = ("shared_flag",             "mean"),
        unique_viewers  = ("user_id",                 "nunique"),
        total_plays     = ("event_id",                "count"),
        genre           = ("genre",                   "first"),
    ).reset_index()

    def minmax(s):
        rng = s.max() - s.min()
        return (s - s.min()) / rng * 100 if rng > 0 else s * 0

    raw["norm_completion"] = minmax(raw["completion_rate"])
    raw["norm_rewatch"]    = minmax(raw["rewatch_rate"])
    raw["norm_share"]      = minmax(raw["share_rate"])
    raw["norm_reach"]      = minmax(raw["unique_viewers"].astype(float))

    raw["engagement_score"] = (
        raw["norm_completion"] * 0.40
      + raw["norm_rewatch"]    * 0.25
      + raw["norm_share"]      * 0.20
      + raw["norm_reach"]      * 0.15
    ).round(2)

    raw["score_rank"] = raw["engagement_score"].rank(ascending=False, method="dense").astype(int)

    # Quadrant
    med_score  = raw["engagement_score"].median()
    med_reach  = raw["unique_viewers"].median()
    raw["quadrant"] = np.select(
        [
            (raw["engagement_score"] >= med_score) & (raw["unique_viewers"] >= med_reach),
            (raw["engagement_score"] <  med_score) & (raw["unique_viewers"] >= med_reach),
            (raw["engagement_score"] >= med_score) & (raw["unique_viewers"] <  med_reach),
        ],
        ["Stars", "Cash Cows", "Question Marks"],
        default="Dogs",
    )

    # Tier flag
    p90 = raw["engagement_score"].quantile(0.90)
    p10 = raw["engagement_score"].quantile(0.10)
    raw["tier"] = np.select(
        [raw["engagement_score"] >= p90, raw["engagement_score"] <= p10],
        ["Top 10%", "Bottom 10%"],
        default="Mid Tier",
    )
    return raw


@st.cache_data(show_spinner="Computing decay curves...")
def compute_decay(pe: pd.DataFrame) -> pd.DataFrame:
    anchors = pe.groupby("content_id")["watch_date"].min().rename("first_play_date").reset_index()
    df = pe.merge(anchors, on="content_id")
    df["days_since"] = (df["watch_date"] - df["first_play_date"]).dt.days
    df["week_num"]   = (df["days_since"] // 7) + 1
    df = df[df["week_num"].between(1, 12)]

    wk = df.groupby(["content_id", "genre", "week_num"]).size().reset_index(name="plays")
    w1 = wk[wk["week_num"] == 1][["content_id", "plays"]].rename(columns={"plays": "w1_plays"})
    wk = wk.merge(w1, on="content_id")
    wk["retention_pct"] = (wk["plays"] / wk["w1_plays"] * 100).round(2)
    return wk


# Load
pe, cc = load_data()
scores = compute_engagement_scores(pe)
decay  = compute_decay(pe)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 8px 0 20px 0'>
        <span style='font-size:2.4rem'>🎬</span>
        <h2 style='color:#e8f0fe; margin:4px 0 2px 0; font-size:1.1rem; font-weight:700'>
            Content Analytics
        </h2>
        <p style='color:#7a9cc4; font-size:0.75rem; margin:0'>Netflix-Style Platform</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### Filters")

    all_genres = sorted(pe["genre"].unique())
    sel_genres = st.multiselect("Genre", all_genres, default=all_genres, key="genre_filter")

    all_regions = sorted(pe["user_region"].unique())
    sel_regions = st.multiselect("Region", all_regions, default=all_regions, key="region_filter")

    all_devices = sorted(pe["device_type"].unique())
    sel_devices = st.multiselect("Device", all_devices, default=all_devices, key="device_filter")

    all_ages = sorted(pe["user_age_group"].unique())
    sel_ages = st.multiselect("Age Group", all_ages, default=all_ages, key="age_filter")

    date_min = pe["watch_date"].min().date()
    date_max = pe["watch_date"].max().date()
    sel_dates = st.date_input("Date Range", value=(date_min, date_max),
                              min_value=date_min, max_value=date_max)

    st.markdown("---")
    st.markdown("""
    <div style='color:#7a9cc4; font-size:0.72rem; line-height:1.6'>
        <b style='color:#a8c4e0'>Data</b><br>
        500K plays &nbsp;|&nbsp; 2K users<br>
        500 titles &nbsp;|&nbsp; Jan 2023–Dec 2024<br><br>
        <b style='color:#a8c4e0'>EQS Weights</b><br>
        Completion 40% &nbsp;|&nbsp; Rewatch 25%<br>
        Share 20% &nbsp;|&nbsp; Reach 15%
    </div>
    """, unsafe_allow_html=True)

# ── Apply filters ─────────────────────────────────────────────────────────────
d_start = pd.to_datetime(sel_dates[0]) if len(sel_dates) >= 1 else pd.to_datetime(date_min)
d_end   = pd.to_datetime(sel_dates[1]) if len(sel_dates) == 2 else pd.to_datetime(date_max)

mask = (
    pe["genre"].isin(sel_genres)
  & pe["user_region"].isin(sel_regions)
  & pe["device_type"].isin(sel_devices)
  & pe["user_age_group"].isin(sel_ages)
  & pe["watch_date"].between(d_start, d_end)
)
pf = pe[mask].copy()
sf = scores[scores["genre"].isin(sel_genres)].copy()

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style='padding: 8px 0 20px 0'>
    <h1 style='margin:0; font-size:1.9rem; color:#e8f0fe'>
        🎬 Content Engagement Analytics Platform
    </h1>
    <p style='color:#7a9cc4; margin:4px 0 0 0; font-size:0.9rem'>
        Netflix-style streaming analytics &nbsp;·&nbsp; 
        Engagement Quality Score &nbsp;·&nbsp; 
        Portfolio Intelligence
    </p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Executive Scorecard",
    "🔍 Engagement Deep Dive",
    "👥 Audience Affinity",
    "🧬 Content Decay",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — EXECUTIVE SCORECARD
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    # KPI row
    k1, k2, k3, k4, k5, k6 = st.columns(6)

    total_plays     = len(pf)
    unique_viewers  = pf["user_id"].nunique()
    avg_eqs         = sf["engagement_score"].mean()
    avg_completion  = pf["completion_pct"].mean() * 100
    avg_rewatch     = pf["rewatch_flag"].mean()   * 100
    avg_share       = pf["shared_flag"].mean()    * 100

    k1.metric("Total Plays",       f"{total_plays:,.0f}")
    k2.metric("Unique Viewers",    f"{unique_viewers:,.0f}")
    k3.metric("Avg EQS",           f"{avg_eqs:.1f}")
    k4.metric("Avg Completion",    f"{avg_completion:.1f}%")
    k5.metric("Rewatch Rate",      f"{avg_rewatch:.1f}%")
    k6.metric("Share Rate",        f"{avg_share:.1f}%")

    st.markdown("<br>", unsafe_allow_html=True)
    col_left, col_right = st.columns([1.4, 1])

    with col_left:
        # Portfolio quadrant scatter
        st.markdown("#### 🎯 Portfolio Quadrant Map")
        fig_quad = px.scatter(
            sf,
            x="completion_rate",
            y="unique_viewers",
            size="engagement_score",
            color="quadrant",
            color_discrete_map=QUADRANT_COLORS,
            hover_data={"content_id": True, "genre": True,
                        "engagement_score": True,
                        "completion_rate": ":.2f",
                        "unique_viewers": True},
            labels={"completion_rate": "Avg Completion Rate",
                    "unique_viewers": "Unique Viewers",
                    "quadrant": "Quadrant"},
            size_max=28,
        )
        fig_quad.add_hline(y=sf["unique_viewers"].median(),
                           line_dash="dot", line_color="#444", line_width=1,
                           annotation_text="Median Reach", annotation_font_color="#666")
        fig_quad.add_vline(x=sf["completion_rate"].median(),
                           line_dash="dot", line_color="#444", line_width=1,
                           annotation_text="Median Completion", annotation_font_color="#666")
        fig_quad.update_layout(
            paper_bgcolor="#0d1520", plot_bgcolor="#0d1520",
            font_color="#c5d8f0", legend_title_text="Quadrant",
            margin=dict(l=0, r=0, t=10, b=0), height=380,
        )
        fig_quad.update_xaxes(gridcolor="#1a2540", showline=False,
                              tickformat=".0%")
        fig_quad.update_yaxes(gridcolor="#1a2540", showline=False)
        st.plotly_chart(fig_quad, use_container_width=True)

    with col_right:
        # Quadrant summary
        st.markdown("#### 📋 Quadrant Summary")
        qsum = sf.groupby("quadrant").agg(
            Titles        = ("content_id",       "count"),
            Avg_EQS       = ("engagement_score", "mean"),
            Avg_Viewers   = ("unique_viewers",   "mean"),
            Avg_Completion= ("completion_rate",  "mean"),
        ).reset_index().round(1)
        qsum["Avg_Completion"] = (qsum["Avg_Completion"] * 100).round(1)
        qsum = qsum.rename(columns={
            "quadrant": "Quadrant",
            "Avg_EQS": "Avg EQS",
            "Avg_Viewers": "Avg Reach",
            "Avg_Completion": "Avg Compl %",
        })
        qsum = qsum.sort_values("Avg EQS", ascending=False)

        def style_quadrant(row):
            color_map = {
                "Stars": "#ffd700", "Cash Cows": "#00c853",
                "Question Marks": "#1e90ff", "Dogs": "#e57373",
            }
            c = color_map.get(row["Quadrant"], "#ffffff")
            return [f"color: {c}; font-weight:600"] + ["color:#c5d8f0"] * (len(row) - 1)

        styled = qsum.style.apply(style_quadrant, axis=1).format({
            "Avg EQS": "{:.1f}", "Avg Reach": "{:,.0f}", "Avg Compl %": "{:.1f}%",
        })
        st.dataframe(styled, use_container_width=True, hide_index=True, height=200)

        # Donut: quadrant distribution
        st.markdown("###### Title Distribution by Quadrant")
        fig_donut = px.pie(
            qsum, names="Quadrant", values="Titles",
            color="Quadrant", color_discrete_map=QUADRANT_COLORS,
            hole=0.6,
        )
        fig_donut.update_traces(textinfo="percent+label", textfont_color="#e8f0fe")
        fig_donut.update_layout(
            paper_bgcolor="#0d1520", plot_bgcolor="#0d1520",
            font_color="#c5d8f0", showlegend=False,
            margin=dict(l=0, r=0, t=10, b=0), height=200,
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    # Monthly trend
    st.markdown("#### 📈 Monthly Play Volume Trend")
    monthly = pf.groupby("watch_month").size().reset_index(name="plays")
    monthly = monthly.sort_values("watch_month")
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=monthly["watch_month"], y=monthly["plays"],
        mode="lines+markers",
        line=dict(color="#e50914", width=2.5),
        marker=dict(size=5, color="#e50914"),
        fill="tozeroy",
        fillcolor="rgba(229,9,20,0.08)",
        name="Plays",
    ))
    fig_trend.update_layout(
        paper_bgcolor="#0d1520", plot_bgcolor="#0d1520",
        font_color="#c5d8f0", margin=dict(l=0, r=0, t=10, b=0), height=220,
        xaxis=dict(gridcolor="#1a2540", showline=False),
        yaxis=dict(gridcolor="#1a2540", showline=False, title="Total Plays"),
        showlegend=False,
    )
    st.plotly_chart(fig_trend, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — ENGAGEMENT DEEP DIVE
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    c_left, c_right = st.columns(2)

    with c_left:
        st.markdown("#### 🔵 Completion vs Rewatch (Bubble = Reach)")
        fig_scatter = px.scatter(
            sf,
            x=sf["completion_rate"] * 100,
            y=sf["rewatch_rate"]    * 100,
            size="unique_viewers",
            color="genre",
            color_discrete_sequence=GENRE_COLORS,
            hover_data={"content_id": True, "engagement_score": True},
            labels={"x": "Avg Completion %", "y": "Rewatch Rate %", "genre": "Genre"},
            size_max=30,
        )
        fig_scatter.add_hline(y=sf["rewatch_rate"].median() * 100,
                              line_dash="dot", line_color="#333", line_width=1)
        fig_scatter.add_vline(x=sf["completion_rate"].median() * 100,
                              line_dash="dot", line_color="#333", line_width=1)
        fig_scatter.update_layout(
            paper_bgcolor="#0d1520", plot_bgcolor="#0d1520",
            font_color="#c5d8f0", margin=dict(l=0, r=0, t=10, b=0), height=360,
            legend=dict(font=dict(size=10)),
        )
        fig_scatter.update_xaxes(gridcolor="#1a2540")
        fig_scatter.update_yaxes(gridcolor="#1a2540")
        st.plotly_chart(fig_scatter, use_container_width=True)

    with c_right:
        st.markdown("#### 📊 Engagement Score by Genre")
        genre_eqs = sf.groupby("genre").agg(
            Avg_EQS  = ("engagement_score", "mean"),
            Titles   = ("content_id",       "count"),
        ).reset_index().sort_values("Avg_EQS", ascending=True)

        fig_genre = go.Figure(go.Bar(
            x=genre_eqs["Avg_EQS"],
            y=genre_eqs["genre"],
            orientation="h",
            marker=dict(
                color=genre_eqs["Avg_EQS"],
                colorscale=[[0,"#1a2540"],[0.5,"#1e90ff"],[1,"#e50914"]],
                showscale=False,
            ),
            text=genre_eqs["Avg_EQS"].round(1),
            textposition="outside",
            textfont=dict(color="#c5d8f0", size=11),
        ))
        fig_genre.update_layout(
            paper_bgcolor="#0d1520", plot_bgcolor="#0d1520",
            font_color="#c5d8f0", margin=dict(l=0, r=0, t=10, b=0), height=360,
            xaxis=dict(gridcolor="#1a2540", range=[0, genre_eqs["Avg_EQS"].max() * 1.15]),
            yaxis=dict(gridcolor="#1a2540"),
        )
        st.plotly_chart(fig_genre, use_container_width=True)

    # Top & Bottom 10 content table
    st.markdown("#### 🏆 Top 20 Titles by Engagement Quality Score")
    top20 = sf.nlargest(20, "engagement_score")[
        ["content_id", "genre", "engagement_score", "completion_rate",
         "rewatch_rate", "share_rate", "unique_viewers", "quadrant", "tier"]
    ].copy()
    top20["completion_rate"] = (top20["completion_rate"] * 100).round(1)
    top20["rewatch_rate"]    = (top20["rewatch_rate"]    * 100).round(1)
    top20["share_rate"]      = (top20["share_rate"]      * 100).round(1)
    top20 = top20.rename(columns={
        "content_id": "Content ID", "genre": "Genre",
        "engagement_score": "EQS", "completion_rate": "Completion %",
        "rewatch_rate": "Rewatch %", "share_rate": "Share %",
        "unique_viewers": "Viewers", "quadrant": "Quadrant", "tier": "Tier",
    })
    st.dataframe(top20, use_container_width=True, hide_index=True, height=380)

    # Waterfall: avg score decomposition
    st.markdown("#### 💧 Avg Engagement Score Decomposition")
    avg_scores = sf[["norm_completion","norm_rewatch","norm_share","norm_reach"]].mean()
    contributions = {
        "Completion (40%)": avg_scores["norm_completion"] * 0.40,
        "Rewatch (25%)":    avg_scores["norm_rewatch"]    * 0.25,
        "Share (20%)":      avg_scores["norm_share"]      * 0.20,
        "Reach (15%)":      avg_scores["norm_reach"]      * 0.15,
    }
    labels  = list(contributions.keys())
    values  = list(contributions.values())
    colors  = ["#1e90ff", "#00c853", "#ffd700", "#ff6d00"]
    total   = sum(values)

    fig_wf = go.Figure(go.Waterfall(
        x=labels + ["Total EQS"],
        y=values  + [None],
        measure=["relative"] * len(labels) + ["total"],
        connector=dict(line=dict(color="#253350", width=1)),
        increasing=dict(marker=dict(color=colors[-1])),
        totals=dict(marker=dict(color="#e50914")),
        text=[f"{v:.1f}" for v in values] + [f"{total:.1f}"],
        textposition="outside",
        textfont=dict(color="#c5d8f0"),
    ))
    for i, (lbl, val, col) in enumerate(zip(labels, values, colors)):
        fig_wf.data[0].marker.color = colors  # type: ignore

    fig_wf.update_traces(
        marker_color=colors + ["#e50914"],
        selector=dict(type="waterfall"),
    )
    fig_wf.update_layout(
        paper_bgcolor="#0d1520", plot_bgcolor="#0d1520",
        font_color="#c5d8f0", margin=dict(l=0, r=0, t=10, b=0), height=280,
        yaxis=dict(gridcolor="#1a2540", title="Score Points"),
        xaxis=dict(gridcolor="#1a2540"),
        showlegend=False,
    )
    st.plotly_chart(fig_wf, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — AUDIENCE AFFINITY
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("#### 🔥 Genre × Age Group Affinity Heatmap")
    seg = pf.groupby(["genre", "user_age_group"]).agg(
        avg_completion = ("completion_pct",  "mean"),
        avg_rewatch    = ("rewatch_flag",    "mean"),
        avg_share      = ("shared_flag",     "mean"),
        unique_viewers = ("user_id",         "nunique"),
        total_plays    = ("event_id",        "count"),
    ).reset_index()

    seg["seg_score"] = (
        seg["avg_completion"] * 100 * 0.40
      + seg["avg_rewatch"]    * 100 * 0.25
      + seg["avg_share"]      * 100 * 0.20
      + (np.log1p(seg["unique_viewers"]) / np.log1p(2001) * 100 * 0.15)
    ).round(2)

    age_order = ["13-17","18-24","25-34","35-44","45-54","55+"]
    seg["user_age_group"] = pd.Categorical(seg["user_age_group"], categories=age_order, ordered=True)
    seg = seg.sort_values(["genre", "user_age_group"])

    pivot = seg.pivot(index="genre", columns="user_age_group", values="seg_score").fillna(0)

    fig_heat = px.imshow(
        pivot,
        color_continuous_scale=[(0, "#1a2540"), (0.4, "#1e3a6e"), (0.7, "#1e90ff"), (1, "#e50914")],
        aspect="auto",
        text_auto=".1f",
        labels=dict(x="Age Group", y="Genre", color="Segment EQS"),
    )
    fig_heat.update_coloraxes(colorbar=dict(
        title="Score", tickfont=dict(color="#c5d8f0"), titlefont=dict(color="#c5d8f0"),
    ))
    fig_heat.update_traces(textfont=dict(color="#ffffff", size=12))
    fig_heat.update_layout(
        paper_bgcolor="#0d1520", plot_bgcolor="#0d1520",
        font_color="#c5d8f0", margin=dict(l=0, r=0, t=10, b=0), height=400,
        xaxis=dict(side="bottom"),
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    c3a, c3b = st.columns(2)
    with c3a:
        st.markdown("#### 📱 Plays by Device Type")
        dev_data = pf.groupby("device_type").size().reset_index(name="plays")
        fig_dev = px.bar(
            dev_data.sort_values("plays", ascending=True),
            x="plays", y="device_type", orientation="h",
            color="plays",
            color_continuous_scale=[[0,"#1a2540"],[1,"#1e90ff"]],
            labels={"plays": "Total Plays", "device_type": "Device"},
        )
        fig_dev.update_coloraxes(showscale=False)
        fig_dev.update_layout(
            paper_bgcolor="#0d1520", plot_bgcolor="#0d1520",
            font_color="#c5d8f0", margin=dict(l=0, r=0, t=10, b=0), height=280,
        )
        fig_dev.update_xaxes(gridcolor="#1a2540")
        fig_dev.update_yaxes(gridcolor="#1a2540")
        st.plotly_chart(fig_dev, use_container_width=True)

    with c3b:
        st.markdown("#### 🌍 Plays by Region")
        reg_data = pf.groupby("user_region").size().reset_index(name="plays")
        fig_reg = px.pie(
            reg_data, names="user_region", values="plays",
            color_discrete_sequence=px.colors.sequential.Blues_r,
            hole=0.5,
        )
        fig_reg.update_traces(textinfo="percent+label", textfont_color="#e8f0fe",
                              textfont_size=11, pull=[0.03]*len(reg_data))
        fig_reg.update_layout(
            paper_bgcolor="#0d1520", font_color="#c5d8f0",
            margin=dict(l=0, r=0, t=10, b=0), height=280, showlegend=False,
        )
        st.plotly_chart(fig_reg, use_container_width=True)

    # Age × device stacked bar
    st.markdown("#### 📊 Plays Volume: Age Group × Device Type")
    age_dev = pf.groupby(["user_age_group","device_type"]).size().reset_index(name="plays")
    age_dev["user_age_group"] = pd.Categorical(
        age_dev["user_age_group"], categories=age_order, ordered=True
    )
    age_dev = age_dev.sort_values("user_age_group")
    fig_agedev = px.bar(
        age_dev, x="user_age_group", y="plays", color="device_type",
        color_discrete_sequence=px.colors.qualitative.Pastel,
        labels={"user_age_group": "Age Group", "plays": "Total Plays", "device_type": "Device"},
        barmode="stack",
    )
    fig_agedev.update_layout(
        paper_bgcolor="#0d1520", plot_bgcolor="#0d1520",
        font_color="#c5d8f0", margin=dict(l=0, r=0, t=10, b=0), height=280,
        legend=dict(font=dict(size=10)),
    )
    fig_agedev.update_xaxes(gridcolor="#1a2540")
    fig_agedev.update_yaxes(gridcolor="#1a2540")
    st.plotly_chart(fig_agedev, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — CONTENT DECAY
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown("#### 📉 Content Decay Curves — Weekly Retention by Portfolio Quadrant")

    decay_q = decay.merge(
        scores[["content_id","quadrant"]], on="content_id", how="left"
    )
    decay_agg = decay_q.groupby(["quadrant","week_num"]).agg(
        avg_retention = ("retention_pct", "mean"),
        title_count   = ("content_id",   "nunique"),
    ).reset_index()

    fig_decay = px.line(
        decay_agg, x="week_num", y="avg_retention",
        color="quadrant", color_discrete_map=QUADRANT_COLORS,
        markers=True,
        labels={"week_num": "Week Since Release",
                "avg_retention": "Avg Retention % (vs Week 1)",
                "quadrant": "Quadrant"},
    )
    fig_decay.add_hline(y=50, line_dash="dot", line_color="#444",
                        annotation_text="50% threshold", annotation_font_color="#666",
                        line_width=1)
    fig_decay.update_traces(line_width=2.5, marker_size=6)
    fig_decay.update_layout(
        paper_bgcolor="#0d1520", plot_bgcolor="#0d1520",
        font_color="#c5d8f0", margin=dict(l=0, r=0, t=10, b=0), height=380,
        xaxis=dict(gridcolor="#1a2540", dtick=1, title="Week Since Release"),
        yaxis=dict(gridcolor="#1a2540", range=[0, 115], title="Retention % vs Week 1"),
        legend=dict(font=dict(size=11)),
    )
    st.plotly_chart(fig_decay, use_container_width=True)

    c4a, c4b = st.columns(2)
    with c4a:
        st.markdown("#### ⚡ Fastest Decay (Bottom 10% — Week 4 Retention)")
        decay_w4 = decay[decay["week_num"] == 4].groupby("content_id").agg(
            w4_retention = ("retention_pct", "mean"),
            genre        = ("genre",         "first"),
        ).reset_index()
        bottom10 = decay_w4.nsmallest(10, "w4_retention")
        fig_bot = px.bar(
            bottom10.sort_values("w4_retention"),
            x="w4_retention", y="content_id", orientation="h",
            color="genre", color_discrete_sequence=px.colors.qualitative.Pastel,
            labels={"w4_retention": "Week-4 Retention %", "content_id": "Content ID"},
        )
        fig_bot.update_layout(
            paper_bgcolor="#0d1520", plot_bgcolor="#0d1520",
            font_color="#c5d8f0", margin=dict(l=0, r=0, t=10, b=0), height=340,
            showlegend=False,
        )
        fig_bot.update_xaxes(gridcolor="#1a2540")
        fig_bot.update_yaxes(gridcolor="#1a2540")
        st.plotly_chart(fig_bot, use_container_width=True)

    with c4b:
        st.markdown("#### 🌿 Slowest Decay (Top 10% — Evergreen Content)")
        top10 = decay_w4.nlargest(10, "w4_retention")
        fig_top = px.bar(
            top10.sort_values("w4_retention"),
            x="w4_retention", y="content_id", orientation="h",
            color="genre", color_discrete_sequence=px.colors.qualitative.Pastel,
            labels={"w4_retention": "Week-4 Retention %", "content_id": "Content ID"},
        )
        fig_top.update_layout(
            paper_bgcolor="#0d1520", plot_bgcolor="#0d1520",
            font_color="#c5d8f0", margin=dict(l=0, r=0, t=10, b=0), height=340,
            showlegend=False,
        )
        fig_top.update_xaxes(gridcolor="#1a2540")
        fig_top.update_yaxes(gridcolor="#1a2540")
        st.plotly_chart(fig_top, use_container_width=True)

    # Avg retention at key milestones per quadrant
    st.markdown("#### 📅 Milestone Retention Summary by Quadrant")
    milestones = [1, 2, 3, 4, 8, 12]
    mil_data = decay_q[decay_q["week_num"].isin(milestones)].groupby(
        ["quadrant", "week_num"]
    )["retention_pct"].mean().round(1).unstack("week_num")
    mil_data.columns = [f"Week {w}" for w in mil_data.columns]
    mil_data = mil_data.reset_index()
    mil_data = mil_data.rename(columns={"quadrant": "Quadrant"})

    def color_quadrant_col(val, col_name, row_quadrant):
        c = QUADRANT_COLORS.get(row_quadrant, "#c5d8f0")
        if col_name == "Quadrant":
            return f"color: {c}; font-weight:700"
        return "color: #c5d8f0"

    st.dataframe(
        mil_data.style.format({c: "{:.1f}%" for c in mil_data.columns if c != "Quadrant"}),
        use_container_width=True, hide_index=True, height=200,
    )
