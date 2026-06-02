import json
import sqlite3
import pandas as pd


def load_timing_jobs(db_path: str) -> pd.DataFrame:
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql_query("SELECT * FROM timing_jobs", con)
    return enrich_timing_jobs(df)


def enrich_timing_jobs(df: pd.DataFrame) -> pd.DataFrame:
    """Add convenience columns extracted from metadata_json when available."""
    if df.empty or "metadata_json" not in df.columns:
        return df

    experiment_types = []
    sweep_variables = []
    for raw in df["metadata_json"].fillna(""):
        experiment_type = None
        sweep_variable = None
        try:
            meta = json.loads(raw) if raw else {}
            point = meta.get("point", {})
            experiment_type = point.get("experiment_type")
            sweep_variable = point.get("sweep_variable")
        except Exception:
            pass
        experiment_types.append(experiment_type)
        sweep_variables.append(sweep_variable)

    df = df.copy()
    df["experiment_type"] = experiment_types
    df["sweep_variable"] = sweep_variables
    return df
