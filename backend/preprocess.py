"""
Preprocessing script - Run once to build data structures from CSV.
Output is saved to data_processed/ and loaded by the server at startup.
"""
import pandas as pd
import pickle
from pathlib import Path

def preprocess():
    print("Loading data...")
    df = pd.read_csv("../data/data_clean.csv")

    # TODO: Build graph, spatial index, etc.
    # For now, just save the dataframe

    output_dir = Path(__file__).parent / "data_processed"
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "data.pkl", "wb") as f:
        pickle.dump(df, f)

    print(f"Preprocessed {len(df)} records -> {output_dir}/data.pkl")

if __name__ == "__main__":
    preprocess()
