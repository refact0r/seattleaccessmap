from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT_DIR / "data" / "data.csv"
OUTPUT_FILE = ROOT_DIR / "data" / "data_clean.csv"

# label-specific adjusted severity ranges (0-10)
SEVERITY_RANGES = {
    "CurbRamp": (0, 5),
    "NoCurbRamp": (3, 8),
    "NoSidewalk": (5, 10),
    "Obstacle": (2, 7),
    "SurfaceProblem": (1, 6),
    "Other": (1, 4),
}


def adjust_severity(row):
    lo, hi = SEVERITY_RANGES.get(row["label"], (1, 5))
    return lo + (row["severity"] - 1) / 4 * (hi - lo)


def main() -> None:
    def log(message):
        print(message.lower())

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

    df_clean["adjusted_severity"] = df_clean.apply(adjust_severity, axis=1)

    df_clean.to_csv(OUTPUT_FILE, index=False)

    log(
        f"cleaned data saved to {OUTPUT_FILE} (before={before}, after={len(df_clean)}, removed={dropped})"
    )


if __name__ == "__main__":
    main()
