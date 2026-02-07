from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT_DIR / "data" / "data.csv"
OUTPUT_FILE = ROOT_DIR / "data" / "data_clean.csv"


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

    df_clean = df.dropna()
    dropped = before - len(df_clean)
    df_clean.to_csv(OUTPUT_FILE, index=False)

    print(
        "Cleaned data ready at",
        OUTPUT_FILE,
        f"(rows before={before}, rows after={len(df_clean)}, rows removed={dropped})",
    )


if __name__ == "__main__":
    main()
