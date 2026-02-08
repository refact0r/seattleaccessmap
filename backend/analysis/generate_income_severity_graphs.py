import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from data.neighborhood_lookup import NEIGHBORHOOD_LOOKUP

GRAPHS_DIR = Path(__file__).parent / "graphs"
GRAPHS_DIR.mkdir(exist_ok=True)


def log(message):
    print(message.lower())


sidewalk = pd.read_csv(PROJECT_ROOT / "data/data_clean.csv")
income_raw = pd.read_csv(PROJECT_ROOT / "data/neighborhood-incomes.csv")

severity_by_hood = (
    sidewalk.groupby("neighborhood")["adjusted_severity"]
    .mean()
    .reset_index()
    .rename(columns={"adjusted_severity": "avg_severity"})
)

severity_by_hood["income_name"] = severity_by_hood["neighborhood"].map(
    NEIGHBORHOOD_LOOKUP
)

unmapped = severity_by_hood[severity_by_hood["income_name"].isna()][
    "neighborhood"
].tolist()
if unmapped:
    log(f"warning: no income mapping for: {unmapped}")
severity_by_hood = severity_by_hood.dropna(subset=["income_name"])

income_raw["Neighborhood Name"] = income_raw["Neighborhood Name"].str.strip()

income_raw["per_capita_income"] = (
    income_raw[
        "Aggregate income in the past 12 months (in 2022 inflation-adjusted dollars)"
    ]
    / income_raw["Total Population"]
)

income_raw["avg_household_income"] = (
    income_raw["Aggregate Household Income"] / income_raw["Total Households"]
)

income_cra = income_raw[income_raw["Neighborhood Type"] == "CRA"].set_index(
    "Neighborhood Name"
)
income_ucuv = income_raw[income_raw["Neighborhood Type"] == "UCUV"].set_index(
    "Neighborhood Name"
)
income_lookup = pd.concat([income_ucuv, income_cra])
income_lookup = income_lookup[~income_lookup.index.duplicated(keep="last")]

merged = severity_by_hood.merge(
    income_lookup[["per_capita_income", "avg_household_income"]],
    left_on="income_name",
    right_index=True,
    how="inner",
)

grouped = (
    merged.groupby("income_name")
    .agg(
        avg_severity=("avg_severity", "mean"),
        per_capita_income=("per_capita_income", "first"),
        avg_household_income=("avg_household_income", "first"),
    )
    .reset_index()
)

fig, ax = plt.subplots(figsize=(12, 8))
ax.scatter(
    grouped["avg_household_income"],
    grouped["avg_severity"],
    s=60,
    alpha=0.7,
    edgecolors="k",
    linewidth=0.5,
)

for _, row in grouped.iterrows():
    ax.annotate(
        row["income_name"],
        (row["avg_household_income"], row["avg_severity"]),
        fontsize=7,
        alpha=0.8,
        xytext=(5, 5),
        textcoords="offset points",
    )

z = np.polyfit(grouped["avg_household_income"], grouped["avg_severity"], 1)
p = np.poly1d(z)
x_line = np.linspace(
    grouped["avg_household_income"].min(), grouped["avg_household_income"].max(), 100
)
ax.plot(
    x_line,
    p(x_line),
    "--",
    color="red",
    alpha=0.6,
    label=f"Linear fit (slope={z[0]:.2e})",
)

corr = grouped["avg_household_income"].corr(grouped["avg_severity"])
ax.set_xlabel("Average Household Income ($, 2022 inflation-adjusted)", fontsize=12)
ax.set_ylabel("Average Adjusted Severity (0–10)", fontsize=12)
ax.set_title(
    f"Avg Household Income vs Avg Accessibility Barrier Severity\nby Seattle Neighborhood (r = {corr:.3f})",
    fontsize=14,
)
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(GRAPHS_DIR / "income_vs_severity_scatter.png", dpi=150)

fig, ax = plt.subplots(figsize=(12, 8))
ax.scatter(
    grouped["per_capita_income"],
    grouped["avg_severity"],
    s=60,
    alpha=0.7,
    color="teal",
    edgecolors="k",
    linewidth=0.5,
)

for _, row in grouped.iterrows():
    ax.annotate(
        row["income_name"],
        (row["per_capita_income"], row["avg_severity"]),
        fontsize=7,
        alpha=0.8,
        xytext=(5, 5),
        textcoords="offset points",
    )

z2 = np.polyfit(grouped["per_capita_income"], grouped["avg_severity"], 1)
p2 = np.poly1d(z2)
x_line2 = np.linspace(
    grouped["per_capita_income"].min(), grouped["per_capita_income"].max(), 100
)
ax.plot(
    x_line2,
    p2(x_line2),
    "--",
    color="red",
    alpha=0.6,
    label=f"Linear fit (slope={z2[0]:.2e})",
)

corr2 = grouped["per_capita_income"].corr(grouped["avg_severity"])
ax.set_xlabel("Per Capita Income ($, 2022 inflation-adjusted)", fontsize=12)
ax.set_ylabel("Average Adjusted Severity (0–10)", fontsize=12)
ax.set_title(
    f"Per Capita Income vs Avg Accessibility Barrier Severity\nby Seattle Neighborhood (r = {corr2:.3f})",
    fontsize=14,
)
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(GRAPHS_DIR / "income_vs_severity_scatter_percapita.png", dpi=150)

sorted_df = grouped.sort_values("avg_severity", ascending=True)
norm = plt.Normalize(
    sorted_df["avg_household_income"].min(), sorted_df["avg_household_income"].max()
)
cmap = plt.cm.RdYlGn

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
ax.set_title(
    "Accessibility Barrier Severity by Neighborhood\n(color = household income level)",
    fontsize=14,
)
ax.grid(True, axis="x", alpha=0.3)
plt.tight_layout()
plt.savefig(GRAPHS_DIR / "severity_by_neighborhood_income_colored.png", dpi=150)

plt.close("all")
log(f"done: graphs saved to {GRAPHS_DIR}")
