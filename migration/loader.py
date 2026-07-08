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
        For ALTER TABLE ADD CONSTRAINT statements, automatically drops the
        constraint first if it already exists (prevents Error 1826 duplicates),
        and runs with FOREIGN_KEY_CHECKS=0 to allow FK creation even if
        existing data has referential mismatches.
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    for statement in sql.split(';'):
                        stmt = statement.strip()
                        if not stmt:
                            continue

                        # For ADD CONSTRAINT statements, drop first if exists
                        if 'ADD CONSTRAINT' in stmt.upper():
                            import re
                            # Extract table name and constraint name
                            tbl_match = re.search(r'ALTER TABLE\s+`?(\w+)`?', stmt, re.IGNORECASE)
                            con_match = re.search(r'ADD CONSTRAINT\s+`?(\w+)`?', stmt, re.IGNORECASE)
                            if tbl_match and con_match:
                                tbl_name = tbl_match.group(1)
                                con_name = con_match.group(1)
                                # Check if constraint already exists before trying to drop
                                cursor.execute(
                                    "SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS "
                                    "WHERE CONSTRAINT_SCHEMA = DATABASE() "
                                    "AND TABLE_NAME = %s AND CONSTRAINT_NAME = %s",
                                    (tbl_name, con_name)
                                )
                                if cursor.fetchone()[0] > 0:
                                    cursor.execute(f"ALTER TABLE `{tbl_name}` DROP FOREIGN KEY `{con_name}`")

                            # Disable FK checks so data mismatches don't block FK creation
                            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                            cursor.execute(stmt)
                            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                        else:
                            cursor.execute(stmt)
                conn.commit()
        except Exception as e:
            logger.error(f"Error executing schema SQL:\n{sql}\nError: {e}")
            raise


    def truncate_table(self, table_name: str):
        """
        Truncates a table before re-loading to avoid duplicate key errors on re-runs.
        Disables FK checks temporarily so dependent tables don't block truncation.
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                    cursor.execute(f"TRUNCATE TABLE `{table_name}`")
                    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                conn.commit()
            logger.info(f"Truncated table {table_name} before reload.")
        except Exception as e:
            logger.warning(f"Could not truncate {table_name} (may not exist yet): {e}")

    def load_data(self, table_name: str, batch: List[Dict[str, Any]]):
        """
        Upserts a batch of records into the target MySQL table.
        Uses INSERT ... ON DUPLICATE KEY UPDATE so re-runs are safe.
        """
        if not batch:
            return

        # Prepare the query
        columns = list(batch[0].keys())
        col_names_str = ", ".join([f"`{col}`" for col in columns])
        placeholders_str = ", ".join(["%s"] * len(columns))
        update_clause = ", ".join([f"`{col}`=VALUES(`{col}`)" for col in columns])

        query = (
            f"INSERT INTO `{table_name}` ({col_names_str}) VALUES ({placeholders_str}) "
            f"ON DUPLICATE KEY UPDATE {update_clause}"
        )

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
