import pyodbc
import logging
from typing import Generator, List, Dict, Any

logger = logging.getLogger(__name__)

class DataExtractor:
    """
    Extracts data from Microsoft SQL Server.
    """
    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def get_connection(self):
        return pyodbc.connect(self.connection_string)

    def extract_data(self, table_name: str, filter_clause: str = None, batch_size: int = 10000) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Extracts data from a given table, yielding batches of rows as dictionaries.
        """
        query = f"SELECT * FROM {table_name}"
        if filter_clause:
            query += f" {filter_clause}"
            
        logger.info(f"Extracting data from {table_name} with query: {query}")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                
                columns = [column[0] for column in cursor.description]
                
                while True:
                    rows = cursor.fetchmany(batch_size)
                    if not rows:
                        break
                        
                    batch = []
                    for row in rows:
                        batch.append(dict(zip(columns, row)))
                        
                    yield batch
        except Exception as e:
            logger.error(f"Error extracting data from {table_name}: {e}")
            raise
