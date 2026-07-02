import pyodbc
import mysql.connector
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class Validator:
    """
    Validates migrated data between MSSQL and MySQL.
    """
    def __init__(self, mssql_config: Dict[str, Any], mysql_config: Dict[str, Any]):
        self.mssql_config = mssql_config
        self.mysql_config = mysql_config

    def get_mssql_conn(self):
        # We assume connection string is passed or built from config
        conn_str = (
            f"DRIVER={{{self.mssql_config['driver']}}};"
            f"SERVER={self.mssql_config['server']};"
            f"DATABASE={self.mssql_config['database']};"
            f"UID={self.mssql_config['user']};"
            f"PWD={self.mssql_config['password']}"
        )
        return pyodbc.connect(conn_str)

    def get_mysql_conn(self):
        return mysql.connector.connect(**self.mysql_config)

    def get_source_count(self, table_name: str, filter_clause: str = None) -> int:
        query = f"SELECT COUNT(*) FROM {table_name}"
        if filter_clause:
            query += f" {filter_clause}"
        try:
            with self.get_mssql_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting source count for {table_name}: {e}")
            return -1

    def get_destination_count(self, table_name: str) -> int:
        query = f"SELECT COUNT(*) FROM `{table_name}`"
        try:
            with self.get_mysql_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting destination count for {table_name}: {e}")
            return -1

    def check_duplicate_ids(self, table_name: str, id_column: str) -> int:
        """Returns the number of duplicate IDs found in destination."""
        query = f"""
        SELECT `{id_column}`, COUNT(*) 
        FROM `{table_name}` 
        GROUP BY `{id_column}` 
        HAVING COUNT(*) > 1
        """
        try:
            with self.get_mysql_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                results = cursor.fetchall()
                return len(results)
        except Exception as e:
            logger.error(f"Error checking duplicate IDs for {table_name}: {e}")
            return -1

    def check_null_pks(self, table_name: str, id_column: str) -> int:
        """Returns the number of null primary keys found in destination."""
        query = f"SELECT COUNT(*) FROM `{table_name}` WHERE `{id_column}` IS NULL"
        try:
            with self.get_mysql_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error checking null PKs for {table_name}: {e}")
            return -1

    def validate_table(self, source_table: str, dest_table: str, id_column: str, filter_clause: str = None) -> Dict[str, Any]:
        """Runs all validations for a specific table."""
        logger.info(f"Validating {source_table} -> {dest_table}...")
        
        source_count = self.get_source_count(source_table, filter_clause)
        dest_count = self.get_destination_count(dest_table)
        duplicates = self.check_duplicate_ids(dest_table, id_column)
        null_pks = self.check_null_pks(dest_table, id_column)
        
        status = "PASSED"
        if source_count != dest_count or duplicates > 0 or null_pks > 0:
            status = "FAILED"
            
        return {
            "Source Table": source_table,
            "Destination Table": dest_table,
            "Source Count": source_count,
            "Destination Count": dest_count,
            "Count Match": source_count == dest_count,
            "Duplicate IDs": duplicates,
            "Null PKs": null_pks,
            "Status": status
        }
