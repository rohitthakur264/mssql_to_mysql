# HIS to FHIR Python ETL Framework

A production-grade Python ETL framework for migrating a Hospital Information System (HIS) from Microsoft SQL Server to MySQL, adopting a FHIR-inspired structure.

## Overview

This framework is designed to be highly modular, scalable, and configuration-driven. It automates the process of:
1. Connecting to Microsoft SQL Server and extracting metadata (Tables, Columns, Primary Keys, Foreign Keys, Data Types).
2. Generating equivalent MySQL schemas, with data type translations.
3. Transforming standard Master tables into a strict 6-column FHIR structure (`id`, `code`, `display`, `display_arb`, `system`, `isactive`).
4. Batched data extraction, transformation, and loading into MySQL.
5. Extensive validation (record counts, duplicate checks, null PK checks).
6. Generating comprehensive Excel reports on migration status, schemas, and mappings.

## Architecture & Project Structure

The project follows a clean architecture:
*   `config/`: Contains `settings.json` (database credentials) and `mapping.json` (configurable table lists and FHIR mappings).
*   `metadata/reader.py`: Connects to MSSQL using `pyodbc` and queries system catalog views (`sys.tables`, `sys.columns`, etc.) to dynamically discover schema.
*   `schema/generator.py`: Maps MSSQL data types to MySQL data types and generates `CREATE TABLE` and `ALTER TABLE` statements.
*   `migration/extractor.py`: Extracts data in batches from MSSQL, applying configured `WHERE` filters.
*   `migration/transformer.py`: Maps and transforms Master table data into the FHIR structure. Acts as a passthrough for Business tables.
*   `migration/loader.py`: Connects to MySQL using `mysql-connector-python` and executes batched `INSERT` statements.
*   `validation/validator.py`: Connects to both databases post-migration to verify record counts, identify duplicate IDs, and catch missing primary keys.
*   `reports/generator.py`: Uses `pandas` to output `Migration_Report.xlsx`, `Schema_Report.xlsx`, `Mapping_Report.xlsx`, and `Relationship_Report.xlsx` to the `output/` directory.

## Prerequisites

1. Python 3.12+
2. Microsoft ODBC Driver 17 for SQL Server (must be installed on the system running the script).
3. MySQL Server running and accessible.

## Installation

1. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure Database Credentials:
   Open `config/settings.json` and provide your actual MSSQL and MySQL connection details.

3. Configure Mappings:
   Open `config/mapping.json`. It comes pre-populated with your specified Business Tables and Master Tables. You can update the column mappings (like `id_column`, `code_column`) for specific master tables as needed without changing any Python code.

## Execution

Run the orchestrator script:
```bash
python main.py
```

## Logs and Reports

- **Logs**: The execution process, including any errors or skipped records, will be logged to the console and saved in `logs/Migration_Log.txt`.
- **Reports**: After execution, check the `output/` directory for beautifully formatted Excel workbooks containing the migration results and validation statuses.
