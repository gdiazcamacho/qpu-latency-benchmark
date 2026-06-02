import sqlite3
import pandas as pd


def load_timing_jobs(db_path: str) -> pd.DataFrame:
    with sqlite3.connect(db_path) as con:
        return pd.read_sql_query("SELECT * FROM timing_jobs", con)
