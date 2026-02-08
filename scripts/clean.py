from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT_DIR / "data" / "data.csv"
OUTPUT_FILE = ROOT_DIR / "data" / "data_clean.csv"

# Adjusted severity ranges (0-10 scale) per label type.
# Each label maps original severity 1-5 to a (min, max) effective range
# via linear interpolation: adj = min + (severity - 1) / 4 * (max - min)
#
# Rationale:
#   CurbRamp:       Positive feature (ramp exists). Sev 1 = good ramp (no barrier),
#                   sev 5 = problematic ramp (moderate barrier, but ramp still exists).
#   NoCurbRamp:     Missing curb ramp. Even sev 1 is a real barrier (low curb or
#                   alternate route exists). Sev 5 = severely inaccessible.
#   NoSidewalk:     Missing sidewalk. Always significant — even sev 1 means no sidewalk.
#   Obstacle:       Obstruction on path. Severity maps directly to impact.
#   SurfaceProblem: Damaged surface. Severity maps directly to impact.
#   Other:          Miscellaneous (only ~64 records). Low weight.
SEVERITY_RANGES = {
    "CurbRamp":       (0, 5),
    "NoCurbRamp":     (3, 8),
    "NoSidewalk":     (5, 10),
    "Obstacle":       (2, 7),
    "SurfaceProblem": (1, 6),
    "Other":          (1, 4),
}


def adjust_severity(row):
    """Rescale severity from 1-5 to an effective 0-10 value based on label type."""
    lo, hi = SEVERITY_RANGES.get(row["label"], (1, 5))
    return lo + (row["severity"] - 1) / 4 * (hi - lo)


def main() -> None:
    df = pd.read_csv(DATA_FILE)
    before = len(df)

    df = df.drop(columns=["type", "geometry/type"], errors="ignore")
    df = df.rename(
        columns={
            "geometry/coordinates/0": "lon",
            "geometry/coordinates/1": "lat",
            "properties/attribute_id": "attr_id",
            "properties/label_type": "label",
            "properties/neighborhood": "neighborhood",
            "properties/severity": "severity",
            "properties/is_temporary": "is_temporary",
        }
    )

    df_clean = df.dropna().copy()
    dropped = before - len(df_clean)

    # Rescale severity per label type to a 0-10 effective scale
    df_clean["adjusted_severity"] = df_clean.apply(adjust_severity, axis=1)

    df_clean.to_csv(OUTPUT_FILE, index=False)

    print(
        "Cleaned data ready at",
        OUTPUT_FILE,
        f"(rows before={before}, rows after={len(df_clean)}, rows removed={dropped})",
    )
    print("\nAdjusted severity stats by label:")
    print(df_clean.groupby("label")["adjusted_severity"].describe().round(2))


if __name__ == "__main__":
    main()
