import mysql.connector
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class DataLoader:
    """
    Loads transformed data into MySQL database.
    """
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config

    def get_connection(self):
        return mysql.connector.connect(**self.db_config)

    def execute_schema_sql(self, sql: str):
        """
        Executes DDL statements (CREATE TABLE, ALTER TABLE).
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # We might have multiple statements in the sql block, but mysql.connector doesn't support executing multiple by default in execute()
                    # We can use multi=True if needed or split by semicolon.
                    for statement in sql.split(';'):
                        if statement.strip():
                            cursor.execute(statement)
                conn.commit()
        except Exception as e:
            logger.error(f"Error executing schema SQL:\n{sql}\nError: {e}")
            raise

    def load_data(self, table_name: str, batch: List[Dict[str, Any]]):
        """
        Inserts a batch of records into the target MySQL table.
        """
        if not batch:
            return

        # Prepare the query
        columns = list(batch[0].keys())
        col_names_str = ", ".join([f"`{col}`" for col in columns])
        placeholders_str = ", ".join(["%s"] * len(columns))
        
        query = f"INSERT INTO `{table_name}` ({col_names_str}) VALUES ({placeholders_str})"
        
        # Prepare the values
        values = []
        for row in batch:
            # Handle potential missing keys gracefully, defaulting to None
            values.append(tuple(row.get(col) for col in columns))

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(query, values)
                conn.commit()
            logger.debug(f"Successfully loaded {len(batch)} records into {table_name}.")
        except Exception as e:
            logger.error(f"Error loading data into {table_name}: {e}")
            raise
