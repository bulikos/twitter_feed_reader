import sqlite3
import pandas as pd
import json
import logging
import os
from typing import Dict, Optional, List
from .models import Tweet

logger = logging.getLogger(__name__)

class Catalogue:
    """
    Simple Catalogue class to store Tweet objects into SQLite.
    This is a staging procedure.
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
        Receives data (DataFrame) and stores them into SQLITE.
        The format of table should fit Tweet object.
        """
        if df is None or df.empty:
            logger.info("Catalogue: No entries to add.")
            return

        # Prepare data for SQLite (handle list/dict/objects)
        # We copy to avoid modifying the original dataframe
        df_clean = df.copy()
        
        # Iterate over columns to handle complex types (list, dict) which SQLite doesn't support natively
        for col in df_clean.columns:
            # We check if the column type is object, which typically holds lists/dicts/strings
            if df_clean[col].dtype == 'object':
                # Convert list or dict to JSON string
                # We use apply to handle mixed types safely (e.g. None mixed with lists)
                df_clean[col] = df_clean[col].apply(
                    lambda x: json.dumps(x) if isinstance(x, (list, dict)) else str(x) if x is not None else None
                )
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Store into 'catalogue' table
                # if_exists='append' ensures we add to existing data
                df_clean.to_sql('catalogue', conn, if_exists='append', index=False)
            logger.info(f"Catalogue: Added {len(df)} entries to 'catalogue' table.")
        except Exception as e:
            logger.error(f"Catalogue: Error adding entries: {e}")
