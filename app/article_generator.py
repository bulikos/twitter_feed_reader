import sqlite3
import pandas as pd
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)



class ArticleGenerator:
    """
    Simple ArticleGenerator class to store id and read_id into SQLite.
    """
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to app/data/staging.db
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            self.db_path = os.path.join(data_dir, "staging.db")
        else:
            self.db_path = db_path

    def add_entries(self, df: pd.DataFrame):
        """
        Receives df with columns: id, read_id.
        Stores them into SQLITE table.
        """
        if df is None or df.empty:
            logger.info("ArticleGenerator: No entries to add.")
            return

        expected_cols = {'id', 'read_id'}
        if not expected_cols.issubset(df.columns):
            logger.error(f"ArticleGenerator: Input DataFrame missing required columns: {expected_cols - set(df.columns)}")
            return

        # Select only interested columns
        df_to_save = df[['id', 'read_id']].copy()

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Store into 'article_generator' table
                df_to_save.to_sql('article_generator', conn, if_exists='append', index=False)
            logger.info(f"ArticleGenerator: Added {len(df)} entries to 'article_generator' table.")
        except Exception as e:
            logger.error(f"ArticleGenerator: Error adding entries: {e}")