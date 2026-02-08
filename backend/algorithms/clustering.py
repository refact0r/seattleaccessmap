"""
HDBSCAN clustering analysis for accessibility barriers.
"""

import numpy as np
import pandas as pd
import hdbscan


def spatial_spread_meters(group):
    """Calculate max spatial spread from centroid in meters (rough approximation)."""
    lat_spread = (group["lat"].max() - group["lat"].min()) * 111_000
    lng_spread = (
        (group["lon"].max() - group["lon"].min())
        * 111_000
        * np.cos(np.radians(group["lat"].mean()))
    )
    return max(lat_spread, lng_spread)


def generate_clusters(barriers_df, min_severity=3):
    """
    Generate HDBSCAN clusters from barrier data.

    Args:
        barriers_df: DataFrame with columns: lat, lon, adjusted_severity, label, attr_id, neighborhood
        min_severity: Only cluster barriers with adjusted_severity >= this value (default: 4)

    Returns:
        dict with 'clusters' and 'heatmap_data' keys
    """
    # Use all barriers for heatmap, filter for clustering only
    df_all = barriers_df.copy()
    df_severe = barriers_df[barriers_df["adjusted_severity"] >= min_severity].copy()

    if len(df_all) == 0:
        return {
            "clusters": [],
            "heatmap_data": [],
        }

    # HDBSCAN clustering on lat/lng coordinates (haversine metric)
    coords = np.radians(df_severe[["lat", "lon"]].values)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=12,
        min_samples=8,
        metric="haversine",
        cluster_selection_method="leaf",
    )
    df_severe["cluster"] = clusterer.fit_predict(coords)

    # Filter to only clustered points (exclude noise: cluster == -1)
    clustered_df = df_severe[df_severe["cluster"] != -1]

    if len(clustered_df) == 0:
        return {
            "clusters": [],
            "heatmap_data": df_all[["lat", "lon", "adjusted_severity"]].values.tolist(),
        }

    # Calculate type breakdown per cluster
    type_counts = (
        clustered_df.groupby(["cluster", "label"]).size().unstack(fill_value=0)
    )
    type_counts.columns = [f"n_{c}" for c in type_counts.columns]

    # Calculate cluster statistics
    cluster_stats = clustered_df.groupby("cluster").agg(
        count=("attr_id", "size"),
        mean_severity=("adjusted_severity", "mean"),
        max_severity=("adjusted_severity", "max"),
        n_types=("label", "nunique"),
        top_type=("label", lambda x: x.mode().iloc[0]),
        top_neighborhood=(
            "neighborhood",
            lambda x: x.mode().iloc[0] if len(x) > 0 else "Unknown",
        ),
        lat_center=("lat", "mean"),
        lng_center=("lon", "mean"),
    )
    cluster_stats = cluster_stats.join(type_counts)
    cluster_stats["spread_m"] = clustered_df.groupby("cluster").apply(
        spatial_spread_meters, include_groups=False
    )

    # Calculate hotspot score: count × mean severity
    cluster_stats["hotspot_score"] = (
        cluster_stats["count"] * cluster_stats["mean_severity"]
    )
    cluster_stats = cluster_stats.sort_values("hotspot_score", ascending=False)

    # Export cluster metadata
    clusters_export = []
    for rank, (cid, crow) in enumerate(cluster_stats.iterrows()):
        # Get all points in this cluster
        cluster_pts = df_severe[df_severe["cluster"] == cid]
        points = [
            {"lat": float(row["lat"]), "lng": float(row["lon"])}
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

    return {
        "clusters": clusters_export,
        "heatmap_data": df_all[["lat", "lon", "adjusted_severity"]].values.tolist(),
    }
