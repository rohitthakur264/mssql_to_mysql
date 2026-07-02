import json
import logging
import os
import sys

from metadata.reader import MSSQLMetadataReader
from schema.generator import SchemaGenerator
from migration.extractor import DataExtractor
from migration.transformer import DataTransformer
from migration.loader import DataLoader
from validation.validator import Validator
from reports.generator import ReportGenerator

# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/Migration_Log.txt"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def load_config():
    with open("config/settings.json", "r") as f:
        settings = json.load(f)
    with open("config/mapping.json", "r") as f:
        mapping = json.load(f)
    return settings, mapping

def build_mssql_conn_string(mssql_conf):
    return (
        f"DRIVER={{{mssql_conf['driver']}}};"
        f"SERVER={mssql_conf['server']};"
        f"DATABASE={mssql_conf['database']};"
        f"UID={mssql_conf['user']};"
        f"PWD={mssql_conf['password']}"
    )

def run_migration():
    logger.info("Starting ETL Migration Framework...")
    
    settings, mapping = load_config()
    mssql_conn_str = build_mssql_conn_string(settings['mssql'])
    
    reader = MSSQLMetadataReader(mssql_conn_str)
    schema_gen = SchemaGenerator()
    extractor = DataExtractor(mssql_conn_str)
    transformer = DataTransformer()
    loader = DataLoader(settings['mysql'])
    validator = Validator(settings['mssql'], settings['mysql'])
    reporter = ReportGenerator(output_dir="output")
    
    validation_results = []
    schema_records = []
    relationship_records = []
    
    # 1. Process Business Tables
    business_tables = mapping.get("business_tables", [])
    logger.info(f"Processing {len(business_tables)} Business Tables...")
    
    for table in business_tables:
        target_table = f"fhir_{table.lower()}"
        try:
            logger.info(f"--- Processing Business Table: {table} -> {target_table} ---")
            
            # Metadata
            metadata = reader.get_table_metadata(table)
            schema_records.append({"Source Table": table, "Target Table": target_table, "Type": "Business", "Columns": len(metadata['columns'])})
            
            for fk in metadata['foreign_keys']:
                relationship_records.append({"Table": table, "Column": fk['column_name'], "Ref Table": fk['ref_table'], "Ref Column": fk['ref_column']})
            
            # Schema
            schema_sql = schema_gen.generate_business_table_sql(target_table, metadata)
            loader.execute_schema_sql(schema_sql)
            
            # Data
            for batch in extractor.extract_data(table, batch_size=5000):
                transformed = transformer.transform_business_batch(batch)
                loader.load_data(target_table, transformed)
                
            # Validate
            # Assume first PK is the ID for validation, or generic fallback if no PK
            id_col = metadata['primary_keys'][0] if metadata['primary_keys'] else None
            if id_col:
                val_res = validator.validate_table(table, target_table, id_col)
                validation_results.append(val_res)
            else:
                logger.warning(f"No primary key found for {table}, skipping some validations.")
                
        except Exception as e:
            logger.error(f"Failed to process business table {table}: {e}")

    # 2. Process Master Tables
    master_tables = mapping.get("master_tables", [])
    logger.info(f"Processing {len(master_tables)} Master Tables...")
    
    import re
    for m_table_config in master_tables:
        source_table_raw = m_table_config['source_table']
        parts = re.split(r'\s+where\s+', source_table_raw, flags=re.IGNORECASE)
        source_table = parts[0].strip()
        
        target_table = m_table_config.get('target_table', f"fhir_{source_table.lower()}")
        filter_clause = m_table_config.get('source_filter')
        
        if len(parts) > 1 and not filter_clause:
            filter_clause = "WHERE " + parts[1]
            # Ensure the extractor uses the raw table name if it's baked into the source_table property
            # Actually, it's safer to pass the clean table name and the extracted filter_clause
        
        try:
            logger.info(f"--- Processing Master Table: {source_table} -> {target_table} ---")
            
            # Metadata
            metadata = reader.get_table_metadata(source_table)
            schema_records.append({"Source Table": source_table, "Target Table": target_table, "Type": "Master", "Columns": 6})
            
            # Schema
            schema_sql = schema_gen.generate_master_fhir_table_sql(target_table, metadata, m_table_config)
            loader.execute_schema_sql(schema_sql)
            
            # Data
            for batch in extractor.extract_data(source_table, filter_clause=filter_clause, batch_size=5000):
                transformed = transformer.transform_master_batch(batch, m_table_config)
                loader.load_data(target_table, transformed)
                
            # Validate
            val_res = validator.validate_table(source_table, target_table, id_column='id', filter_clause=filter_clause)
            validation_results.append(val_res)
            
        except Exception as e:
            logger.error(f"Failed to process master table {source_table}: {e}")
            
    # 3. Generate Foreign Keys
    # Depending on order of creation, FKs should be created after all tables are loaded.
    logger.info("Applying Foreign Key constraints...")
    for table in business_tables:
        target_table = f"fhir_{table.lower()}"
        try:
            metadata = reader.get_table_metadata(table)
            fk_sql = schema_gen.generate_foreign_keys_sql(target_table, metadata)
            if fk_sql:
                try:
                    loader.execute_schema_sql(fk_sql)
                    logger.info(f"Successfully generated and applied FKs for {table}.")
                except Exception as e:
                    logger.warning(f"Could not apply some FKs for {table} (referenced table might be missing or renamed): {e}")
        except Exception as e:
            logger.error(f"Failed to generate FKs for {table}: {e}")

    for m_table_config in master_tables:
        source_table_raw = m_table_config['source_table']
        parts = re.split(r'\s+where\s+', source_table_raw, flags=re.IGNORECASE)
        source_table = parts[0].strip()
        target_table = m_table_config.get('target_table', f"fhir_{source_table.lower()}")
        try:
            metadata = reader.get_table_metadata(source_table)
            fk_sql = schema_gen.generate_foreign_keys_sql(target_table, metadata)
            if fk_sql:
                try:
                    loader.execute_schema_sql(fk_sql)
                    logger.info(f"Successfully generated and applied FKs for {source_table}.")
                except Exception as e:
                    logger.warning(f"Could not apply some FKs for {source_table} (referenced table might be missing or renamed): {e}")
        except Exception as e:
            logger.error(f"Failed to generate FKs for {source_table}: {e}")

    # 4. Generate Reports
    logger.info("Generating reports...")
    reporter.generate_migration_report(validation_results)
    reporter.generate_schema_report(schema_records)
    reporter.generate_relationship_report(relationship_records)
    reporter.generate_mapping_report(master_tables)
    
    logger.info("Migration process completed.")

if __name__ == "__main__":
    run_migration()
