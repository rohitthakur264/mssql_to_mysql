import pyodbc
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class MSSQLMetadataReader:
    """
    Reads database schema metadata from Microsoft SQL Server using system catalog views.
    """
    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def get_connection(self):
        return pyodbc.connect(self.connection_string)

    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Retrieves all columns, their data types, max length, and nullability for a given table.
        """
        query = """
        SELECT 
            c.name AS column_name,
            t.name AS data_type,
            c.max_length,
            c.precision,
            c.scale,
            c.is_nullable,
            c.is_identity
        FROM sys.columns c
        INNER JOIN sys.tables tbl ON c.object_id = tbl.object_id
        INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
        WHERE tbl.name = ?
        ORDER BY c.column_id;
        """
        columns = []
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, table_name)
                for row in cursor.fetchall():
                    columns.append({
                        "column_name": row.column_name,
                        "data_type": row.data_type,
                        "max_length": row.max_length,
                        "precision": row.precision,
                        "scale": row.scale,
                        "is_nullable": bool(row.is_nullable),
                        "is_identity": bool(row.is_identity)
                    })
        except Exception as e:
            logger.error(f"Failed to get columns for table {table_name}: {e}")
            raise
        return columns

    def get_primary_keys(self, table_name: str) -> List[str]:
        """
        Retrieves the primary key columns for a given table.
        """
        query = """
        SELECT 
            c.name AS column_name
        FROM sys.key_constraints kc
        INNER JOIN sys.index_columns ic ON kc.parent_object_id = ic.object_id AND kc.unique_index_id = ic.index_id
        INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        INNER JOIN sys.tables tbl ON kc.parent_object_id = tbl.object_id
        WHERE kc.type = 'PK' AND tbl.name = ?
        ORDER BY ic.key_ordinal;
        """
        pks = []
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, table_name)
                for row in cursor.fetchall():
                    pks.append(row.column_name)
        except Exception as e:
            logger.error(f"Failed to get primary keys for table {table_name}: {e}")
            raise
        return pks

    def get_foreign_keys(self, table_name: str) -> List[Dict[str, str]]:
        """
        Retrieves foreign keys for a given table.
        Returns a list of dicts: {'column': ..., 'ref_table': ..., 'ref_column': ...}
        """
        query = """
        SELECT 
            c_parent.name AS column_name,
            tbl_ref.name AS ref_table,
            c_ref.name AS ref_column
        FROM sys.foreign_keys fk
        INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
        INNER JOIN sys.tables tbl_parent ON fkc.parent_object_id = tbl_parent.object_id
        INNER JOIN sys.columns c_parent ON fkc.parent_object_id = c_parent.object_id AND fkc.parent_column_id = c_parent.column_id
        INNER JOIN sys.tables tbl_ref ON fkc.referenced_object_id = tbl_ref.object_id
        INNER JOIN sys.columns c_ref ON fkc.referenced_object_id = c_ref.object_id AND fkc.referenced_column_id = c_ref.column_id
        WHERE tbl_parent.name = ?;
        """
        fks = []
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, table_name)
                for row in cursor.fetchall():
                    fks.append({
                        "column_name": row.column_name,
                        "ref_table": row.ref_table,
                        "ref_column": row.ref_column
                    })
        except Exception as e:
            logger.error(f"Failed to get foreign keys for table {table_name}: {e}")
            raise
        return fks

    def get_table_metadata(self, table_name: str) -> Dict[str, Any]:
        """
        Aggregates all metadata for a table.
        """
        return {
            "table_name": table_name,
            "columns": self.get_table_columns(table_name),
            "primary_keys": self.get_primary_keys(table_name),
            "foreign_keys": self.get_foreign_keys(table_name)
        }
