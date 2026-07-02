from metadata.reader import MSSQLMetadataReader
import json

conf = json.load(open('config/settings.json'))['mssql']
conn_str = f"DRIVER={{{conf['driver']}}};SERVER={conf['server']};DATABASE={conf['database']};UID={conf['user']};PWD={conf['password']}"
r = MSSQLMetadataReader(conn_str)
m = r.get_table_metadata('DiscountReason_Mst')
print("Columns for DiscountReason_Mst:", [c['column_name'] for c in m['columns']])
