"""
==============================================================================
DELIVERABLE 1 -- Synthetic Play Event Log Generator
==============================================================================
Project  : Content Engagement Analytics Platform
Author   : [Your Name]
Date     : 2024
Purpose  : Generates 500,000 synthetic streaming play event rows that mimic
           real-world user behavior distributions observed on OTT platforms.

Usage    : python generate_play_events.py
Output   : play_events.csv  (same directory as this script)
           content_catalogue.csv  (same directory)

Dependencies:
    pip install faker numpy pandas tqdm
==============================================================================
"""

import os
import sys
import time
import random
import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta

# ==============================================================================
# CONFIGURATION
# ==============================================================================
RANDOM_SEED           = 42
N_EVENTS              = 500_000
N_USERS               = 2_000
N_CONTENT             = 500
DATE_START            = datetime(2023, 1,  1)
DATE_END              = datetime(2024, 12, 31)
REWATCH_RATE          = 0.08   # 8 % of watches are rewatches
SHARE_RATE            = 0.04   # 4 % of watches result in a share
OUTPUT_PATH           = os.path.join(os.path.dirname(os.path.abspath(__file__)), "play_events.csv")
CATALOGUE_PATH        = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content_catalogue.csv")

# Beta distribution parameters -- skewed toward 60-80 % completion
BETA_ALPHA            = 5.0
BETA_BETA             = 2.5

np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
fake = Faker()

SEP  = "=" * 62
SEP2 = "-" * 62

# ==============================================================================
# 1. REFERENCE LOOKUP TABLES
# ==============================================================================

DEVICE_TYPES   = ["smart_tv", "mobile", "tablet", "desktop", "console"]
DEVICE_WEIGHTS = [0.35, 0.30, 0.12, 0.18, 0.05]

AGE_GROUPS     = ["13-17", "18-24", "25-34", "35-44", "45-54", "55+"]
AGE_WEIGHTS    = [0.06, 0.22, 0.28, 0.20, 0.14, 0.10]

REGIONS        = [
    "North America", "Europe", "Latin America",
    "Asia Pacific", "Middle East & Africa",
]
REGION_WEIGHTS = [0.38, 0.27, 0.15, 0.14, 0.06]

GENRES = [
    "Drama", "Comedy", "Action", "Documentary",
    "Thriller", "Romance", "Sci-Fi", "Horror",
    "Animation", "Crime",
]

# Genre-level share-rate overrides (Drama/Documentary share more)
GENRE_SHARE_RATE = {
    "Drama": 0.06, "Documentary": 0.07, "Comedy": 0.05, "Action": 0.04,
    "Thriller": 0.04, "Romance": 0.05, "Sci-Fi": 0.03, "Horror": 0.03,
    "Animation": 0.05, "Crime": 0.04,
}


def sample_content_durations(n: int) -> np.ndarray:
    """Return realistic content durations (minutes).
    40 % movies (80-180 min), 60 % series episodes (22-60 min).
    """
    n_movies   = int(n * 0.40)
    n_episodes = n - n_movies
    movies     = np.random.randint(80, 181, size=n_movies)
    episodes   = np.random.randint(22,  61, size=n_episodes)
    durations  = np.concatenate([movies, episodes])
    np.random.shuffle(durations)
    return durations


# ==============================================================================
# 2. CONTENT CATALOGUE  (500 titles)
# ==============================================================================
print("Building content catalogue ...")

content_ids       = [f"CID_{str(i).zfill(4)}" for i in range(1, N_CONTENT + 1)]
content_genres    = np.random.choice(GENRES, size=N_CONTENT)
content_durations = sample_content_durations(N_CONTENT)

# Release dates spread 0-1100 days before 2023-01-01 (circa 2020-2023)
content_release_dates = [
    DATE_START - timedelta(days=int(np.random.randint(0, 1100)))
    for _ in range(N_CONTENT)
]

content_catalogue = pd.DataFrame({
    "content_id"      : content_ids,
    "genre"           : content_genres,
    "content_duration": content_durations,
    "release_date"    : content_release_dates,
})

# Pareto popularity weights: top 20 % of titles attract ~80 % of plays
raw_weights   = np.random.pareto(a=1.5, size=N_CONTENT) + 1
content_probs = raw_weights / raw_weights.sum()


# ==============================================================================
# 3. USER POOL  (2,000 unique users)
# ==============================================================================
print("Building user pool ...")

user_ids        = [f"UID_{str(i).zfill(5)}" for i in range(1, N_USERS + 1)]
user_age_groups = np.random.choice(AGE_GROUPS,   size=N_USERS, p=AGE_WEIGHTS)
user_regions    = np.random.choice(REGIONS,      size=N_USERS, p=REGION_WEIGHTS)
user_devices    = np.random.choice(DEVICE_TYPES, size=N_USERS, p=DEVICE_WEIGHTS)

user_pool = pd.DataFrame({
    "user_id"       : user_ids,
    "user_age_group": user_age_groups,
    "user_region"   : user_regions,
    "primary_device": user_devices,
})

SECONDARY_DEVICE_PROB = 0.25   # 25 % of events use a non-primary device


# ==============================================================================
# 4. VECTORISED EVENT GENERATION
# ==============================================================================
print(f"Generating {N_EVENTS:,} play events ...")

# --- timestamps ---------------------------------------------------------------
total_seconds    = int((DATE_END - DATE_START).total_seconds())
event_timestamps = DATE_START + pd.to_timedelta(
    np.random.randint(0, total_seconds, size=N_EVENTS), unit="s"
)

# --- content selection (Pareto-weighted) --------------------------------------
sel_content_idx = np.random.choice(np.arange(N_CONTENT), size=N_EVENTS, p=content_probs)
sel_content     = content_catalogue.iloc[sel_content_idx].reset_index(drop=True)

# --- user selection (uniform) -------------------------------------------------
sel_user_idx = np.random.randint(0, N_USERS, size=N_EVENTS)
sel_users    = user_pool.iloc[sel_user_idx].reset_index(drop=True)

# --- watch duration (beta distribution) ---------------------------------------
completion_fractions = np.clip(
    np.random.beta(BETA_ALPHA, BETA_BETA, size=N_EVENTS), 0.01, 1.0
)
watch_duration_minutes = np.maximum(
    (completion_fractions * sel_content["content_duration"].values).astype(int), 1
)

# --- rewatch flag (8 %; boosted to 14 % for near-complete watches) ------------
rewatch_probs = np.where(completion_fractions > 0.85, 0.14, REWATCH_RATE)
rewatch_flags = (np.random.rand(N_EVENTS) < rewatch_probs).astype(int)

# --- share flag (genre-dependent) ---------------------------------------------
genre_share_probs = (
    sel_content["genre"].map(GENRE_SHARE_RATE).fillna(SHARE_RATE).values
)
share_flags = (np.random.rand(N_EVENTS) < genre_share_probs).astype(int)

# --- device (primary + 25 % cross-device) ------------------------------------
secondary_devices = np.random.choice(DEVICE_TYPES, size=N_EVENTS, p=DEVICE_WEIGHTS)
device_types      = np.where(
    np.random.rand(N_EVENTS) < SECONDARY_DEVICE_PROB,
    secondary_devices,
    sel_users["primary_device"].values,
)


# ==============================================================================
# 5. ASSEMBLE FINAL DATAFRAME
# ==============================================================================
print("Assembling DataFrame ...")

events = pd.DataFrame({
    "event_id"                : [f"EVT_{str(i).zfill(7)}" for i in range(1, N_EVENTS + 1)],
    "user_id"                 : sel_users["user_id"].values,
    "content_id"              : sel_content["content_id"].values,
    "watch_date"              : event_timestamps.date,
    "watch_duration_minutes"  : watch_duration_minutes,
    "content_duration_minutes": sel_content["content_duration"].values,
    "rewatch_flag"            : rewatch_flags,
    "shared_flag"             : share_flags,
    "device_type"             : device_types,
    "user_age_group"          : sel_users["user_age_group"].values,
    "user_region"             : sel_users["user_region"].values,
    "genre"                   : sel_content["genre"].values,
})

# Temporary validation column (dropped before save)
events["_completion_pct"] = (
    events["watch_duration_minutes"] / events["content_duration_minutes"]
).round(4).clip(upper=1.0)


# ==============================================================================
# 6. DATA QUALITY REPORT
# ==============================================================================
print("\n" + SEP)
print("  DATA QUALITY REPORT")
print(SEP2)
print(f"  Total events         : {len(events):>10,}")
print(f"  Unique users         : {events['user_id'].nunique():>10,}")
print(f"  Unique content IDs   : {events['content_id'].nunique():>10,}")
print(f"  Date range           : {events['watch_date'].min()} -> {events['watch_date'].max()}")
print(f"  Rewatch rate         : {events['rewatch_flag'].mean()*100:>9.2f} %")
print(f"  Share rate           : {events['shared_flag'].mean()*100:>9.2f} %")
print(f"  Avg completion       : {events['_completion_pct'].mean()*100:>9.2f} %")
print(f"  Median completion    : {events['_completion_pct'].median()*100:>9.2f} %")
print(f"  Null values          : {events.isnull().sum().sum():>10,}")
print(SEP + "\n")

# Hard assertions
assert len(events) == N_EVENTS,                  "FAIL: Event count mismatch"
assert events["user_id"].nunique()    <= N_USERS,   "FAIL: Too many users"
assert events["content_id"].nunique() <= N_CONTENT, "FAIL: Too many content IDs"
assert events.isnull().sum().sum()    == 0,       "FAIL: Null values detected"
print("All assertions passed.")

# Drop internal column
events.drop(columns=["_completion_pct"], inplace=True)


# ==============================================================================
# 7. SAVE OUTPUTS
# ==============================================================================
print(f"\nSaving play_events.csv to:\n  {OUTPUT_PATH}")
t0 = time.time()
events.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
elapsed = time.time() - t0
size_mb = os.path.getsize(OUTPUT_PATH) / 1e6
print(f"  Done in {elapsed:.1f}s  |  File size: {size_mb:.1f} MB")

print(f"\nSaving content_catalogue.csv to:\n  {CATALOGUE_PATH}")
content_catalogue.to_csv(CATALOGUE_PATH, index=False, encoding="utf-8")
size_mb2 = os.path.getsize(CATALOGUE_PATH) / 1e6
print(f"  File size: {size_mb2:.2f} MB")

print("\n" + SEP)
print("  [OK] Generation complete.")
print("  Next steps:")
print("  1. Run sql/00_schema_setup.sql in PostgreSQL")
print("  2. COPY play_events.csv and content_catalogue.csv into the DB")
print("  3. Run sql/01 through 05 for analysis")
print("  4. Load CSVs into Power BI / Tableau")
print(SEP + "\n")
