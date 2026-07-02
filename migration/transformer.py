import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def find_col(row_lower: Dict[str, Any], expected: str, hints: List[str]) -> str:
    """
    Attempts to find the correct column in row_lower based on expected name and hints.
    """
    expected = expected.lower()
    if expected in row_lower:
        return expected
    # Try hints
    for k in row_lower.keys():
        for hint in hints:
            if hint in k.lower():
                return k
    # Fallback for ID to the first column
    if 'id' in hints and len(row_lower) > 0:
        return list(row_lower.keys())[0]
    return expected

class DataTransformer:
    """
    Transforms extracted data into the target schema format.
    """
    def __init__(self):
        pass

    def transform_business_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Business tables are migrated essentially as-is (schema-wise).
        This acts as a passthrough, but can be extended for data cleansing if needed.
        """
        return batch

    def transform_master_batch(self, batch: List[Dict[str, Any]], mapping_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transforms a batch of master table records into the standard 6-column FHIR structure.
        """
        transformed_batch = []
        for row in batch:
            try:
                # Handle cases where column names might be case-insensitive in the DB but case-sensitive in the dict
                # We do a case-insensitive lookup for safety
                row_lower = {k.lower(): v for k, v in row.items()}
                
                id_col = find_col(row_lower, mapping_config.get('id_column', ''), ['id'])
                code_col = find_col(row_lower, mapping_config.get('code_column', ''), ['code'])
                display_col = find_col(row_lower, mapping_config.get('display_column', ''), ['desc', 'description', 'name'])
                display_arb_col = find_col(row_lower, mapping_config.get('display_arb_column', ''), ['arb'])
                active_col = find_col(row_lower, mapping_config.get('active_column', ''), ['active', 'deactive'])
                
                is_active_val = row_lower.get(active_col)
                # Convert active value to TINYINT(1) equivalent (1 or 0)
                # Assuming Deactive = 0 means Active = 1. The specific logic depends on business rules.
                # If the column is literally 'Deactive', we should invert it if we want 'isactive'
                if active_col.lower() == 'deactive':
                    final_active = 1 if (is_active_val == 0 or is_active_val is False) else 0
                else:
                    # Generic active flag mapping
                    final_active = 1 if is_active_val in (1, True, 'Y', 'Yes') else 0

                mapped_cols_lower = [c for c in [id_col, code_col, display_col, display_arb_col, active_col] if c is not None]

                fhir_cols = ['id', 'code', 'display', 'display_arb', 'system', 'isactive']
                transformed_row = {}
                
                # Copy all unmapped original columns. If they clash, prefix them with src_
                for k, v in row.items():
                    if k.lower() in mapped_cols_lower:
                        continue # Skip this, as it is renamed to a FHIR column
                    if k.lower() in fhir_cols:
                        transformed_row["src_" + k] = v
                    else:
                        transformed_row[k] = v

                # Set FHIR columns
                transformed_row['id'] = row_lower.get(id_col)
                transformed_row['code'] = str(row_lower.get(code_col)) if row_lower.get(code_col) is not None else None
                transformed_row['display'] = str(row_lower.get(display_col)) if row_lower.get(display_col) is not None else None
                transformed_row['display_arb'] = str(row_lower.get(display_arb_col)) if row_lower.get(display_arb_col) is not None else None
                transformed_row['system'] = mapping_config.get('system_uri')
                transformed_row['isactive'] = final_active
                
                transformed_batch.append(transformed_row)
            except Exception as e:
                logger.error(f"Error transforming row: {row}. Error: {e}")
                # Depending on strictness, we might raise or just skip
                raise
                
        return transformed_batch
