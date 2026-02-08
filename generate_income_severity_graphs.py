"""
Generate graphs: average income vs average adjusted severity per neighborhood.
Merges Project Sidewalk accessibility data with ACS income data via the lookup table.
"""

import sys
sys.path.insert(0, "data")

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from data.neighborhood_lookup import NEIGHBORHOOD_LOOKUP

# --- Load data ---
sidewalk = pd.read_csv("data/data_clean.csv")
income_raw = pd.read_csv("data/neighborhood-incomes.csv")

# --- Compute average adjusted severity per clean neighborhood ---
severity_by_hood = (
    sidewalk.groupby("neighborhood")["adjusted_severity"]
    .mean()
    .reset_index()
    .rename(columns={"adjusted_severity": "avg_severity"})
)

# --- Map clean neighborhoods to income CRA names ---
severity_by_hood["income_name"] = severity_by_hood["neighborhood"].map(NEIGHBORHOOD_LOOKUP)

# Drop neighborhoods with no mapping
unmapped = severity_by_hood[severity_by_hood["income_name"].isna()]["neighborhood"].tolist()
if unmapped:
    print(f"Warning: no income mapping for: {unmapped}")
severity_by_hood = severity_by_hood.dropna(subset=["income_name"])

# --- Parse income data ---
# Use CRA rows (Neighborhood Type == "CRA") as primary, fall back to UCUV
income_raw["Neighborhood Name"] = income_raw["Neighborhood Name"].str.strip()

# Compute per-capita income: Aggregate income / Total Population
income_raw["per_capita_income"] = (
    income_raw["Aggregate income in the past 12 months (in 2022 inflation-adjusted dollars)"]
    / income_raw["Total Population"]
)

# Also compute median-proxy: Aggregate Household Income / Total Households
income_raw["avg_household_income"] = (
    income_raw["Aggregate Household Income"] / income_raw["Total Households"]
)

# Build income lookup (prefer CRA rows)
income_cra = income_raw[income_raw["Neighborhood Type"] == "CRA"].set_index("Neighborhood Name")
income_ucuv = income_raw[income_raw["Neighborhood Type"] == "UCUV"].set_index("Neighborhood Name")
income_lookup = pd.concat([income_ucuv, income_cra])  # CRA overwrites UCUV dupes
income_lookup = income_lookup[~income_lookup.index.duplicated(keep="last")]

# --- Merge ---
merged = severity_by_hood.merge(
    income_lookup[["per_capita_income", "avg_household_income"]],
    left_on="income_name",
    right_index=True,
    how="inner",
)

# Some clean neighborhoods map to the same CRA — aggregate by income_name
grouped = merged.groupby("income_name").agg(
    avg_severity=("avg_severity", "mean"),
    per_capita_income=("per_capita_income", "first"),
    avg_household_income=("avg_household_income", "first"),
).reset_index()

print(f"Matched {len(grouped)} neighborhoods for plotting")
print(grouped[["income_name", "avg_severity", "avg_household_income"]].to_string(index=False))

# --- Plot 1: Scatter — Avg Household Income vs Avg Adjusted Severity ---
fig, ax = plt.subplots(figsize=(12, 8))
ax.scatter(grouped["avg_household_income"], grouped["avg_severity"], s=60, alpha=0.7, edgecolors="k", linewidth=0.5)

# Label each point
for _, row in grouped.iterrows():
    ax.annotate(
        row["income_name"],
        (row["avg_household_income"], row["avg_severity"]),
        fontsize=7, alpha=0.8,
        xytext=(5, 5), textcoords="offset points",
    )

# Trend line
z = np.polyfit(grouped["avg_household_income"], grouped["avg_severity"], 1)
p = np.poly1d(z)
x_line = np.linspace(grouped["avg_household_income"].min(), grouped["avg_household_income"].max(), 100)
ax.plot(x_line, p(x_line), "--", color="red", alpha=0.6, label=f"Linear fit (slope={z[0]:.2e})")

corr = grouped["avg_household_income"].corr(grouped["avg_severity"])
ax.set_xlabel("Average Household Income ($, 2022 inflation-adjusted)", fontsize=12)
ax.set_ylabel("Average Adjusted Severity (0–10)", fontsize=12)
ax.set_title(f"Avg Household Income vs Avg Accessibility Barrier Severity\nby Seattle Neighborhood (r = {corr:.3f})", fontsize=14)
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("graphs/income_vs_severity_scatter.png", dpi=150)
print("Saved: graphs/income_vs_severity_scatter.png")

# --- Plot 2: Scatter — Per Capita Income vs Avg Adjusted Severity ---
fig, ax = plt.subplots(figsize=(12, 8))
ax.scatter(grouped["per_capita_income"], grouped["avg_severity"], s=60, alpha=0.7, color="teal", edgecolors="k", linewidth=0.5)

for _, row in grouped.iterrows():
    ax.annotate(
        row["income_name"],
        (row["per_capita_income"], row["avg_severity"]),
        fontsize=7, alpha=0.8,
        xytext=(5, 5), textcoords="offset points",
    )

z2 = np.polyfit(grouped["per_capita_income"], grouped["avg_severity"], 1)
p2 = np.poly1d(z2)
x_line2 = np.linspace(grouped["per_capita_income"].min(), grouped["per_capita_income"].max(), 100)
ax.plot(x_line2, p2(x_line2), "--", color="red", alpha=0.6, label=f"Linear fit (slope={z2[0]:.2e})")

corr2 = grouped["per_capita_income"].corr(grouped["avg_severity"])
ax.set_xlabel("Per Capita Income ($, 2022 inflation-adjusted)", fontsize=12)
ax.set_ylabel("Average Adjusted Severity (0–10)", fontsize=12)
ax.set_title(f"Per Capita Income vs Avg Accessibility Barrier Severity\nby Seattle Neighborhood (r = {corr2:.3f})", fontsize=14)
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("graphs/income_vs_severity_scatter_percapita.png", dpi=150)
print("Saved: graphs/income_vs_severity_scatter_percapita.png")

# --- Plot 3: Bar chart — neighborhoods sorted by severity, colored by income ---
sorted_df = grouped.sort_values("avg_severity", ascending=True)
norm = plt.Normalize(sorted_df["avg_household_income"].min(), sorted_df["avg_household_income"].max())
cmap = plt.cm.RdYlGn  # Red=low income, Green=high income

fig, ax = plt.subplots(figsize=(14, 10))
bars = ax.barh(
    sorted_df["income_name"],
    sorted_df["avg_severity"],
    color=cmap(norm(sorted_df["avg_household_income"])),
    edgecolor="k",
    linewidth=0.3,
)
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = plt.colorbar(sm, ax=ax, pad=0.02)
cbar.set_label("Avg Household Income ($)", fontsize=11)

ax.set_xlabel("Average Adjusted Severity (0–10)", fontsize=12)
ax.set_ylabel("Neighborhood", fontsize=12)
ax.set_title("Accessibility Barrier Severity by Neighborhood\n(color = household income level)", fontsize=14)
ax.grid(True, axis="x", alpha=0.3)
plt.tight_layout()
plt.savefig("graphs/severity_by_neighborhood_income_colored.png", dpi=150)
print("Saved: graphs/severity_by_neighborhood_income_colored.png")

plt.close("all")
print("\nDone! All graphs saved to graphs/")
