from typing import Dict, Any, List

def mssql_to_mysql_type(mssql_type: str, max_length: int, precision: int, scale: int) -> str:
    """
    Maps Microsoft SQL Server data types to MySQL data types.
    """
    mssql_type = mssql_type.lower()
    
    if mssql_type in ['int', 'tinyint', 'smallint', 'bigint']:
        return mssql_type.upper()
    elif mssql_type == 'bit':
        return 'TINYINT(1)'
    elif mssql_type in ['varchar', 'nvarchar', 'char', 'nchar']:
        if max_length == -1 or max_length > 16383:
            return 'TEXT' if mssql_type in ['varchar', 'char'] else 'LONGTEXT'
        # max_length in sys.columns is in bytes; nvarchar uses 2 bytes per char
        length = max_length // 2 if 'n' in mssql_type else max_length
        return f'VARCHAR({length})'
    elif mssql_type in ['text', 'ntext']:
        return 'LONGTEXT'
    elif mssql_type in ['decimal', 'numeric']:
        return f'DECIMAL({precision},{scale})'
    elif mssql_type in ['float', 'real']:
        return 'DOUBLE' if mssql_type == 'float' else 'FLOAT'
    elif mssql_type in ['datetime', 'datetime2', 'smalldatetime']:
        return 'DATETIME'
    elif mssql_type == 'date':
        return 'DATE'
    elif mssql_type == 'time':
        return 'TIME'
    elif mssql_type == 'uniqueidentifier':
        return 'VARCHAR(36)'
    elif mssql_type == 'image':
        return 'LONGBLOB'
    elif mssql_type in ['varbinary', 'binary']:
        if max_length == -1:
            return 'LONGBLOB'
        return f'VARBINARY({max_length})'
    elif mssql_type == 'money':
        return 'DECIMAL(19,4)'
    else:
        return 'TEXT' # fallback

class SchemaGenerator:
    """
    Generates MySQL CREATE TABLE statements.
    """
    def __init__(self):
        pass

    def generate_business_table_sql(self, target_table_name: str, metadata: Dict[str, Any]) -> str:
        """
        Generates standard CREATE TABLE for business tables based on exact source schema.
        """
        columns = metadata['columns']
        pks = metadata['primary_keys']
        
        sql = f"DROP TABLE IF EXISTS `{target_table_name}`;\n"
        sql += f"CREATE TABLE `{target_table_name}` (\n"
        col_defs = []
        for col in columns:
            mysql_type = mssql_to_mysql_type(
                col['data_type'], 
                col['max_length'], 
                col['precision'], 
                col['scale']
            )
            nullable = "NULL" if col['is_nullable'] else "NOT NULL"
            col_defs.append(f"    `{col['column_name'].lower()}` {mysql_type} {nullable}")
        
        if pks:
            pk_str = ", ".join([f"`{pk}`" for pk in pks])
            col_defs.append(f"    PRIMARY KEY ({pk_str})")
            
        sql += ",\n".join(col_defs)
        sql += "\n);\n"
        return sql

    def generate_master_fhir_table_sql(self, target_table_name: str, metadata: Dict[str, Any], mapping_config: Dict[str, Any]) -> str:
        """
        Generates FHIR-compliant Master CREATE TABLE statement (6 specific columns + all original columns).
        """
        columns = metadata['columns']
        def find_col_name(cols: List[str], expected: str, hints: List[str]) -> str:
            expected = expected.lower()
            for c in cols:
                if c.lower() == expected: return c
            for c in cols:
                for hint in hints:
                    if hint in c.lower(): return c
            return None

        col_names = [c['column_name'] for c in columns]
        id_col = find_col_name(col_names, mapping_config.get('id_column', 'ID'), ['id'])
        code_col = find_col_name(col_names, mapping_config.get('code_column', 'Code'), ['code'])
        display_col = find_col_name(col_names, mapping_config.get('display_column', 'Description'), ['desc', 'description', 'name'])
        display_arb_col = find_col_name(col_names, mapping_config.get('display_arb_column', 'DescriptionArb'), ['arb', 'arabic'])
        active_col = find_col_name(col_names, mapping_config.get('active_column', 'Deactive'), ['active', 'isactive', 'status'])

        mapped_original_cols = [c for c in [id_col, code_col, display_col, display_arb_col, active_col] if c is not None]

        def get_col_type(c_name, default_type):
            if not c_name: return default_type
            for c in columns:
                if c['column_name'] == c_name:
                    return mssql_to_mysql_type(c['data_type'], c['max_length'], c['precision'], c['scale'])
            return default_type

        id_mysql_type = get_col_type(id_col, "VARCHAR(100)")
        code_mysql_type = get_col_type(code_col, "VARCHAR(100)")
        display_mysql_type = get_col_type(display_col, "VARCHAR(255)")
        display_arb_mysql_type = get_col_type(display_arb_col, "VARCHAR(255)")

        sql = f"DROP TABLE IF EXISTS `{target_table_name}`;\n"
        sql += f"CREATE TABLE `{target_table_name}` (\n"
        col_defs = [
            f"    `id` {id_mysql_type} NOT NULL",
            f"    `code` {code_mysql_type}",
            f"    `display` {display_mysql_type}",
            f"    `display_arb` {display_arb_mysql_type}",
            f"    `system` VARCHAR(255)",
            f"    `isactive` TINYINT(1)"
        ]

        fhir_cols = ['id', 'code', 'display', 'display_arb', 'system', 'isactive']

        mapped_original_cols_lower = [c.lower() for c in mapped_original_cols]

        for col in columns:
            col_name = col['column_name'].lower()
            if col_name in mapped_original_cols_lower:
                continue # Renamed to FHIR column
            
            final_col_name = col_name
            if final_col_name in fhir_cols:
                final_col_name = "src_" + final_col_name # Rename original column to avoid clash and keep data
            
            mysql_type = mssql_to_mysql_type(col['data_type'], col['max_length'], col['precision'], col['scale'])
            nullable = "NULL" if col['is_nullable'] else "NOT NULL"
            col_defs.append(f"    `{final_col_name}` {mysql_type} {nullable}")
            
        # Removed PRIMARY KEY (`id`) to allow extracting duplicate records from union views like AdmissionSource

        sql += ",\n".join(col_defs)
        sql += "\n);\n"
        return sql

    def generate_foreign_keys_sql(self, target_table_name: str, metadata: Dict[str, Any]) -> str:
        """
        Generates ALTER TABLE statements for foreign keys.
        """
        fks = metadata['foreign_keys']
        
        if not fks:
            return ""
            
        sql = f"ALTER TABLE `{target_table_name}`\n"
        fk_defs = []
        for fk in fks:
            # We assume referenced tables are also migrated. 
            # If a business table references a master table that was renamed to fhir_*, 
            # this logic might need adjustment during execution to point to the new name.
            # For now, we generate standard FKs.
            ref_target_table = f"fhir_{fk['ref_table'].lower()}"
            fk_name = f"fk_{target_table_name}_{fk['column_name'].lower()}"
            fk_defs.append(f"  ADD CONSTRAINT `{fk_name}` FOREIGN KEY (`{fk['column_name'].lower()}`) REFERENCES `{ref_target_table}` (`{fk['ref_column'].lower()}`)")
            
        sql += ",\n".join(fk_defs)
        sql += ";\n"
        return sql
