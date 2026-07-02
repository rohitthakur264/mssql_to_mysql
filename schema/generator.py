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
        
        sql = f"CREATE TABLE IF NOT EXISTS `{target_table_name}` (\n"
        col_defs = []
        for col in columns:
            mysql_type = mssql_to_mysql_type(
                col['data_type'], 
                col['max_length'], 
                col['precision'], 
                col['scale']
            )
            nullable = "NULL" if col['is_nullable'] else "NOT NULL"
            col_defs.append(f"    `{col['column_name']}` {mysql_type} {nullable}")
        
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
        id_col_name = mapping_config.get('id_column', 'ID')
        
        # Find the datatype of the source ID column to use for the target `id`
        id_mysql_type = "VARCHAR(100)" # Default fallback
        for col in columns:
            if col['column_name'].lower() == id_col_name.lower():
                id_mysql_type = mssql_to_mysql_type(
                    col['data_type'], 
                    col['max_length'], 
                    col['precision'], 
                    col['scale']
                )
                break
                
        fhir_cols = ['id', 'code', 'display', 'display_arb', 'system', 'isactive']
        
        sql = f"CREATE TABLE IF NOT EXISTS `{target_table_name}` (\n"
        col_defs = [
            f"    `id` {id_mysql_type} NOT NULL",
            "    `code` VARCHAR(100)",
            "    `display` VARCHAR(255)",
            "    `display_arb` VARCHAR(255)",
            "    `system` VARCHAR(255)",
            "    `isactive` TINYINT(1)"
        ]
        
        for col in columns:
            col_name = col['column_name']
            if col_name.lower() in fhir_cols:
                continue # Skip original columns that conflict with FHIR component names
            mysql_type = mssql_to_mysql_type(
                col['data_type'], 
                col['max_length'], 
                col['precision'], 
                col['scale']
            )
            nullable = "NULL" if col['is_nullable'] else "NOT NULL"
            col_defs.append(f"    `{col_name}` {mysql_type} {nullable}")
            
        col_defs.append("    PRIMARY KEY (`id`)")
        
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
            fk_name = f"fk_{target_table_name}_{fk['column_name']}"
            fk_defs.append(f"  ADD CONSTRAINT `{fk_name}` FOREIGN KEY (`{fk['column_name']}`) REFERENCES `{ref_target_table}` (`{fk['ref_column']}`)")
            
        sql += ",\n".join(fk_defs)
        sql += ";\n"
        return sql
