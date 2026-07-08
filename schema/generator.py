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
            col_name = col['column_name'].lower()
            # Handle specific translations as requested
            if col_name.endswith('city'):
                col_name = col_name.replace('city', 'city_id')
            elif col_name.endswith('state'):
                col_name = col_name.replace('state', 'state_id')
                
            col_defs.append(f"    `{col_name}` {mysql_type} {nullable}")
        
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
            if expected is None:
                return None
            expected = expected.lower()
            for c in cols:
                if c.lower() == expected: return c
            for c in cols:
                for hint in hints:
                    if hint in c.lower(): return c
            if 'id' in hints and len(cols) > 0:
                return cols[0]
            return None

        col_names = [c['column_name'] for c in columns]
        id_col          = find_col_name(col_names, mapping_config.get('id_column', 'ID'), ['id'])
        code_col        = find_col_name(col_names, mapping_config.get('code_column', 'Code'), ['code'])
        display_col     = find_col_name(col_names, mapping_config.get('display_column', 'Description'), ['desc', 'description', 'name'])
        display_arb_col = find_col_name(col_names, mapping_config.get('display_arb_column'), ['arb', 'arabic'])
        active_col      = find_col_name(col_names, mapping_config.get('active_column'), ['active', 'isactive', 'status'])

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
                continue # Skip this, as it is renamed to a FHIR column
            
            # Apply translations to unmapped columns
            if col_name.endswith('city'):
                col_name = col_name.replace('city', 'city_id')
            elif col_name.endswith('state'):
                col_name = col_name.replace('state', 'state_id')

            final_col_name = col_name
            if final_col_name in fhir_cols:
                final_col_name = "src_" + final_col_name # Rename original column to avoid clash and keep data
            
            mysql_type = mssql_to_mysql_type(col['data_type'], col['max_length'], col['precision'], col['scale'])
            nullable = "NULL" if col['is_nullable'] else "NOT NULL"
            col_defs.append(f"    `{final_col_name}` {mysql_type} {nullable}")
            
        # Use PRIMARY KEY (`id`) to preserve primary keys in exported schemas/backups
        col_defs.append("    PRIMARY KEY (`id`)")

        sql += ",\n".join(col_defs)
        sql += "\n);\n"
        return sql

    def generate_foreign_keys_sql(self, target_table_name: str, metadata: Dict[str, Any], mapping_config: Dict[str, Any] = None) -> str:
        """
        Generates ALTER TABLE statements for foreign keys.
        """
        fks = metadata.get('foreign_keys', [])
        
        # Build a set of actual column names in this table (lowercased) for validation
        actual_cols = set(col['column_name'].lower() for col in metadata.get('columns', []))
        # Also include city->city_id / state->state_id translations
        actual_cols_translated = set()
        for c in actual_cols:
            if c.endswith('city'):
                actual_cols_translated.add(c.replace('city', 'city_id'))
            elif c.endswith('state'):
                actual_cols_translated.add(c.replace('state', 'state_id'))
            else:
                actual_cols_translated.add(c)
        
        fk_defs = []
        seen_fk_names = set()  # Track FK names to prevent duplicates (Error 1826)

        for fk in fks:
            # Clean up referenced table name (in case it matches a master table with a WHERE clause)
            ref_table_raw = fk['ref_table']
            
            # Remap ward_mst1 -> ward_mst (ward_mst1 is legacy; fhir_ward_mst is canonical)
            if ref_table_raw.lower() == 'ward_mst1':
                ref_table_raw = 'Ward_mst'

            # Default mapping
            ref_target_table = f"fhir_{ref_table_raw.lower()}"
            ref_target_column = fk['ref_column'].lower()
            
            # Check if referenced table is a master table
            is_master = False
            if mapping_config and 'master_tables' in mapping_config:
                import re
                for m_table in mapping_config['master_tables']:
                    m_source_raw = m_table['source_table']
                    m_source_clean = re.split(r'\s+where\s+', m_source_raw, flags=re.IGNORECASE)[0].strip()
                    
                    if ref_table_raw.lower() == m_source_clean.lower():
                        is_master = True
                        ref_target_table = m_table.get('target_table', f"fhir_{m_source_clean.lower()}")
                        
                        # Master tables always have their primary reference mapped to 'id'
                        ref_target_column = 'id'
                        break
            
            # Also check if referenced table is a business table (to get exact target table name if customized later)
            is_business = False
            if not is_master and mapping_config and 'business_tables' in mapping_config:
                for b_table in mapping_config['business_tables']:
                    if ref_table_raw.lower() == b_table.lower():
                        is_business = True
                        ref_target_table = f"fhir_{b_table.lower()}"
                        break
            
            # Skip generating the FK if the referenced table is not mapped to be migrated
            if not is_master and not is_business:
                continue
            
            fk_col_name = fk['column_name'].lower()
            if fk_col_name.endswith('city'):
                fk_col_name = fk_col_name.replace('city', 'city_id')
            elif fk_col_name.endswith('state'):
                fk_col_name = fk_col_name.replace('state', 'state_id')
            
            # Skip if the column doesn't actually exist in the table
            if fk_col_name not in actual_cols_translated:
                continue


            fk_name = f"fk_{target_table_name}_{fk_col_name}"
            
            # EXCLUSION LIST: Explicitly skip specific problematic foreign keys due to 
            # legacy SSMS data mismatches (as requested by user)
            excluded_fks = {
                'fk_fhir_visit_roomid',
                'fk_fhir_visit_wardid',
                'fk_auto_fhir_payee_mst_billingcity_id',
                'fk_auto_fhir_payee_mst_billingstate_id',
                'fk_auto_fhir_payee_mst_regofficecity_id',
                'fk_auto_fhir_payee_mst_regofficestate_id',
                'fk_auto_fhir_visit_payee_city_id',
                'fk_auto_fhir_visit_payee_state_id',
                'fk_auto_fhir_visit_rel_city_id',
                'fk_auto_fhir_visit_rel_state_id',
                'fk_fhir_visit_patientid'
            }
            if fk_name in excluded_fks:
                continue
            
            # Skip if we've already seen this FK name (Error 1826 de-duplication)
            if fk_name in seen_fk_names:
                continue
            seen_fk_names.add(fk_name)

            
            fk_defs.append(f"  ADD CONSTRAINT `{fk_name}` FOREIGN KEY (`{fk_col_name}`) REFERENCES `{ref_target_table}` (`{ref_target_column}`)")

        # Numeric types that are compatible with 'id' (INT) in city/state master tables
        NUMERIC_TYPES = {'int', 'tinyint', 'smallint', 'bigint', 'integer'}

        # Auto-guess missing foreign keys for city and state based on actual columns
        for col in metadata.get('columns', []):
            col_name = col['column_name'].lower()
            col_type = col.get('data_type', '').lower()

            if col_name.endswith('city_id') or col_name.endswith('city'):
                fk_col_name = col_name if col_name.endswith('city_id') else col_name.replace('city', 'city_id')
                # Only add if the translated column exists in the table
                if fk_col_name not in actual_cols_translated:
                    continue
                # Skip if this table IS city_mst (prevents self-referencing FK)
                if target_table_name == 'fhir_city_mst':
                    continue
                # Skip if column type is not numeric (e.g. VARCHAR) — incompatible with INT id (Error 3780)
                if col_type not in NUMERIC_TYPES:
                    continue
                fk_name = f"fk_auto_{target_table_name}_{fk_col_name}"
                
                # EXCLUSION LIST: Skip legacy mismatched data
                if fk_name in {
                    'fk_auto_fhir_bank_mst_city_id', 
                    'fk_auto_fhir_bank_mst_state_id',
                    'fk_auto_fhir_payee_mst_billingcity_id',
                    'fk_auto_fhir_payee_mst_billingstate_id',
                    'fk_auto_fhir_payee_mst_regofficecity_id',
                    'fk_auto_fhir_payee_mst_regofficestate_id',
                    'fk_auto_fhir_visit_payee_city_id',
                    'fk_auto_fhir_visit_payee_state_id',
                    'fk_auto_fhir_visit_rel_city_id',
                    'fk_auto_fhir_visit_rel_state_id'
                }:
                    continue
                
                # Prevent duplicate constraints (check both name and column reference)
                if fk_name not in seen_fk_names and not any(f"`{fk_col_name}`" in d for d in fk_defs):
                    seen_fk_names.add(fk_name)
                    fk_defs.append(f"  ADD CONSTRAINT `{fk_name}` FOREIGN KEY (`{fk_col_name}`) REFERENCES `fhir_city_mst` (`id`)")
            elif col_name.endswith('state_id') or col_name.endswith('state'):
                fk_col_name = col_name if col_name.endswith('state_id') else col_name.replace('state', 'state_id')
                # Only add if the translated column exists in the table
                if fk_col_name not in actual_cols_translated:
                    continue
                # Skip if this table IS state_mst (prevents self-referencing FK)
                if target_table_name == 'fhir_state_mst':
                    continue
                # Skip if column type is not numeric (e.g. VARCHAR) — incompatible with INT id (Error 3780)
                if col_type not in NUMERIC_TYPES:
                    continue
                fk_name = f"fk_auto_{target_table_name}_{fk_col_name}"
                
                # EXCLUSION LIST: Skip legacy mismatched data
                if fk_name in {
                    'fk_auto_fhir_bank_mst_city_id', 
                    'fk_auto_fhir_bank_mst_state_id',
                    'fk_auto_fhir_payee_mst_billingcity_id',
                    'fk_auto_fhir_payee_mst_billingstate_id',
                    'fk_auto_fhir_payee_mst_regofficecity_id',
                    'fk_auto_fhir_payee_mst_regofficestate_id',
                    'fk_auto_fhir_visit_payee_city_id',
                    'fk_auto_fhir_visit_payee_state_id',
                    'fk_auto_fhir_visit_rel_city_id',
                    'fk_auto_fhir_visit_rel_state_id'
                }:
                    continue
                    
                if fk_name not in seen_fk_names and not any(f"`{fk_col_name}`" in d for d in fk_defs):
                    seen_fk_names.add(fk_name)
                    fk_defs.append(f"  ADD CONSTRAINT `{fk_name}` FOREIGN KEY (`{fk_col_name}`) REFERENCES `fhir_state_mst` (`id`)")

        sqls = []
        for defn in fk_defs:
            sqls.append(f"ALTER TABLE `{target_table_name}`\n{defn};")
        return sqls

