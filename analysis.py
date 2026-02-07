"""
Seattle Sidewalk Accessibility Analysis
========================================
Data cleaning, exploratory analysis, and HDBSCAN clustering
to identify streets/areas with severe accessibility problems.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import hdbscan
from pathlib import Path
import json

# ── Config ──────────────────────────────────────────────────────────────────
DATA_PATH = Path(__file__).parent / "data" / "data.csv"
OUT_DIR = Path(__file__).parent / "output"
OUT_DIR.mkdir(exist_ok=True)

sns.set_theme(style="whitegrid")
plt.rcParams["figure.dpi"] = 150

# ── 1. Load & Clean ────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH)

# Rename columns for convenience
df = df.rename(
    columns={
        "geometry/coordinates/0": "lng",
        "geometry/coordinates/1": "lat",
        "properties/attribute_id": "id",
        "properties/label_type": "label_type",
        "properties/neighborhood": "neighborhood",
        "properties/severity": "severity",
        "properties/is_temporary": "is_temporary",
    }
)

# Drop the constant columns
df = df.drop(columns=["type", "geometry/type"])

# Convert types
df["is_temporary"] = df["is_temporary"].map({"true": True, "false": False}).astype(bool)
df["severity"] = pd.to_numeric(df["severity"], errors="coerce")

print(f"Total records: {len(df):,}")
print(
    f"Missing severity: {df['severity'].isna().sum():,} ({df['severity'].isna().mean():.1%})"
)
print(f"Label types: {df['label_type'].nunique()}")
print(f"Neighborhoods: {df['neighborhood'].nunique()}")
print()

# For clustering and severity analysis, we'll work with rows that have severity
df_with_sev = df.dropna(subset=["severity"]).copy()
print(f"Records with severity: {len(df_with_sev):,}")

# ── 2. Basic EDA ───────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 2a. Label type distribution
type_counts = df["label_type"].value_counts()
type_counts.plot.barh(
    ax=axes[0, 0], color=sns.color_palette("viridis", len(type_counts))
)
axes[0, 0].set_title("Accessibility Issues by Type")
axes[0, 0].set_xlabel("Count")

# 2b. Severity distribution
df_with_sev["severity"].value_counts().sort_index().plot.bar(
    ax=axes[0, 1], color=sns.color_palette("YlOrRd", 5)
)
axes[0, 1].set_title("Severity Distribution")
axes[0, 1].set_xlabel("Severity")
axes[0, 1].set_ylabel("Count")

# 2c. Top 15 neighborhoods by issue count
top_neighborhoods = df["neighborhood"].value_counts().head(15)
top_neighborhoods.plot.barh(ax=axes[1, 0], color=sns.color_palette("mako", 15))
axes[1, 0].set_title("Top 15 Neighborhoods by Issue Count")
axes[1, 0].set_xlabel("Count")
axes[1, 0].invert_yaxis()

# 2d. Mean severity by label type
mean_sev = (
    df_with_sev.groupby("label_type")["severity"].mean().sort_values(ascending=False)
)
mean_sev.plot.barh(ax=axes[1, 1], color=sns.color_palette("flare", len(mean_sev)))
axes[1, 1].set_title("Mean Severity by Issue Type")
axes[1, 1].set_xlabel("Mean Severity")

plt.tight_layout()
plt.savefig(OUT_DIR / "eda_overview.png", bbox_inches="tight")
plt.close()
print("Saved: eda_overview.png")

# ── 3. Neighborhood severity heatmap ───────────────────────────────────────
# Top 20 neighborhoods × label type mean severity
top20 = df_with_sev["neighborhood"].value_counts().head(20).index
pivot = (
    df_with_sev[df_with_sev["neighborhood"].isin(top20)]
    .groupby(["neighborhood", "label_type"])["severity"]
    .mean()
    .unstack(fill_value=0)
)

fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(pivot, annot=True, fmt=".1f", cmap="YlOrRd", ax=ax)
ax.set_title("Mean Severity: Top 20 Neighborhoods × Issue Type")
plt.tight_layout()
plt.savefig(OUT_DIR / "neighborhood_severity_heatmap.png", bbox_inches="tight")
plt.close()
print("Saved: neighborhood_severity_heatmap.png")

# ── 4. HDBSCAN Clustering ──────────────────────────────────────────────────
# Focus on severe issues (severity >= 3) to find street-level problem hotspots
df_severe = df_with_sev[df_with_sev["severity"] >= 3].copy()
print(f"\nSevere issues (severity >= 3): {len(df_severe):,}")

# HDBSCAN on lat/lng — convert to radians for haversine metric
coords = np.radians(df_severe[["lat", "lng"]].values)

# Street-level clustering:
#   min_cluster_size=8  — a bad block may have just 8-15 issues
#   min_samples=5       — require genuine local density
#   leaf selection       — always pick the finest-grained clusters
clusterer = hdbscan.HDBSCAN(
    min_cluster_size=12,
    min_samples=8,
    metric="haversine",
    cluster_selection_method="leaf",
)
df_severe["cluster"] = clusterer.fit_predict(coords)

n_clusters = df_severe["cluster"].max() + 1
n_noise = (df_severe["cluster"] == -1).sum()
n_clustered = len(df_severe) - n_noise
print(
    f"HDBSCAN found {n_clusters} clusters, {n_clustered:,} clustered, {n_noise:,} noise points"
)


# ── 5. Cluster summary ─────────────────────────────────────────────────────
def spatial_spread_meters(group):
    """Max distance from centroid in meters (rough)."""
    lat_spread = (group["lat"].max() - group["lat"].min()) * 111_000
    lng_spread = (
        (group["lng"].max() - group["lng"].min())
        * 111_000
        * np.cos(np.radians(group["lat"].mean()))
    )
    return max(lat_spread, lng_spread)


clustered_df = df_severe[df_severe["cluster"] != -1]

# Type breakdown per cluster
type_counts = (
    clustered_df.groupby(["cluster", "label_type"]).size().unstack(fill_value=0)
)
type_counts.columns = [f"n_{c}" for c in type_counts.columns]

cluster_stats = clustered_df.groupby("cluster").agg(
    count=("id", "size"),
    mean_severity=("severity", "mean"),
    max_severity=("severity", "max"),
    n_types=("label_type", "nunique"),
    top_type=("label_type", lambda x: x.mode().iloc[0]),
    top_neighborhood=("neighborhood", lambda x: x.mode().iloc[0]),
    lat_center=("lat", "mean"),
    lng_center=("lng", "mean"),
)
cluster_stats = cluster_stats.join(type_counts)
cluster_stats["spread_m"] = clustered_df.groupby("cluster").apply(
    spatial_spread_meters, include_groups=False
)
# Composite score: more issues × higher severity = worse hotspot
# Bonus for multi-type clusters (compounding failures)
cluster_stats["hotspot_score"] = (
    cluster_stats["count"]
    * cluster_stats["mean_severity"]
    * (1 + 0.15 * (cluster_stats["n_types"] - 1))
)
cluster_stats = cluster_stats.sort_values("hotspot_score", ascending=False)

print("\nTop 10 hotspot clusters (scored by count × severity × type diversity):")
print(
    cluster_stats.head(10)[
        [
            "count",
            "mean_severity",
            "n_types",
            "spread_m",
            "top_type",
            "top_neighborhood",
            "lat_center",
            "lng_center",
        ]
    ].to_string()
)
cluster_stats.to_csv(OUT_DIR / "cluster_summary.csv")
print("Saved: cluster_summary.csv")

# ── 6. Cluster scatter plot ────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 10))
noise = df_severe[df_severe["cluster"] == -1]
clustered = df_severe[df_severe["cluster"] != -1]

ax.scatter(noise["lng"], noise["lat"], c="lightgray", s=1, alpha=0.3, label="Noise")
scatter = ax.scatter(
    clustered["lng"],
    clustered["lat"],
    c=clustered["cluster"],
    cmap="tab20",
    s=3,
    alpha=0.6,
)
ax.set_title(f"HDBSCAN Clusters of Severe Accessibility Issues ({n_clusters} clusters)")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")
plt.tight_layout()
plt.savefig(OUT_DIR / "hdbscan_clusters.png", bbox_inches="tight")
plt.close()
print("Saved: hdbscan_clusters.png")

# ── 7. Export data to JSON for web visualization ──────────────────────────
colors = [
    "#e6194b",
    "#3cb44b",
    "#4363d8",
    "#f58231",
    "#911eb4",
    "#42d4f4",
    "#f032e6",
    "#bfef45",
    "#fabed4",
    "#469990",
    "#dcbeff",
    "#9A6324",
    "#800000",
    "#aaffc3",
    "#808000",
    "#ffd8b1",
    "#000075",
    "#a9a9a9",
    "#ffe119",
    "#000000",
]

# Export map config and cluster metadata
center = [float(df_severe["lat"].mean()), float(df_severe["lng"].mean())]
map_config = {
    "center": center,
    "zoom_start": 12,
    "colors": colors,
}

# Export heatmap data
heat_data = df_severe[["lat", "lng", "severity"]].values.tolist()
with open(OUT_DIR / "heatmap_data.json", "w") as f:
    json.dump(heat_data, f)
print("Saved: heatmap_data.json")

# Export top 30 clusters with full metadata
clusters_export = []
for rank, (cid, crow) in enumerate(cluster_stats.iterrows()):
    # Get all points in this cluster
    cluster_pts = df_severe[df_severe["cluster"] == cid]
    points = [
        {"lat": float(row["lat"]), "lng": float(row["lng"])}
        for _, row in cluster_pts.iterrows()
    ]

    # Build type breakdown
    type_cols = [c for c in crow.index if c.startswith("n_")]
    type_breakdown = {}
    for tc in type_cols:
        n = int(crow[tc])
        if n > 0:
            type_breakdown[tc[2:]] = n

    clusters_export.append(
        {
            "rank": rank + 1,
            "cluster_id": int(cid),
            "color": colors[rank % len(colors)],
            "name": f"#{rank+1}: {crow['top_neighborhood']} ({crow['top_type']})",
            "neighborhood": crow["top_neighborhood"],
            "top_type": crow["top_type"],
            "count": int(crow["count"]),
            "n_types": int(crow["n_types"]),
            "mean_severity": float(crow["mean_severity"]),
            "max_severity": float(crow["max_severity"]),
            "spread_m": float(crow["spread_m"]),
            "hotspot_score": float(crow["hotspot_score"]),
            "lat_center": float(crow["lat_center"]),
            "lng_center": float(crow["lng_center"]),
            "type_breakdown": type_breakdown,
            "points": points,
        }
    )

# Export cluster data
with open(OUT_DIR / "clusters_data.json", "w") as f:
    json.dump(
        {
            "config": map_config,
            "clusters": clusters_export,
        },
        f,
        indent=2,
    )
print("Saved: clusters_data.json")
print("→ View map: Open everyday/index.html in a browser with a local server")

# ── 8. Temporary vs Permanent breakdown ────────────────────────────────────
temp_stats = df.groupby(["label_type", "is_temporary"]).size().unstack(fill_value=0)
temp_stats.columns = (
    ["Permanent", "Temporary"] if len(temp_stats.columns) == 2 else ["Permanent"]
)

fig, ax = plt.subplots(figsize=(8, 5))
temp_stats.plot.barh(
    stacked=True, ax=ax, color=["#2196F3", "#FF9800"][: len(temp_stats.columns)]
)
ax.set_title("Permanent vs Temporary Issues by Type")
ax.set_xlabel("Count")
ax.legend(["Permanent", "Temporary"])
plt.tight_layout()
plt.savefig(OUT_DIR / "temp_vs_permanent.png", bbox_inches="tight")
plt.close()
print("Saved: temp_vs_permanent.png")

print("\n✓ Analysis complete. Outputs in:", OUT_DIR)
