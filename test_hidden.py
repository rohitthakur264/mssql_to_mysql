import json
settings=json.load(open('config/settings.json'))
from main import build_mssql_conn_string
conn_str=build_mssql_conn_string(settings['mssql'])
from migration.extractor import DataExtractor
ext=DataExtractor(conn_str)
b=next(ext.extract_data('Service_Mst', batch_size=1))
from migration.transformer import DataTransformer
t=DataTransformer()
mapping=json.load(open('config/mapping.json'))
sm=next(m for m in mapping['master_tables'] if m['source_table']=='Service_Mst')

row_lower = {k.lower(): v for k, v in b[0].items()}
def find_col(r, e, h):
    e=e.lower()
    if e in r: return e
    for k in r.keys():
        for hi in h:
            if hi in k.lower(): return k
    return None

id_col = find_col(row_lower, sm.get('id_column', ''), ['id'])
code_col = find_col(row_lower, sm.get('code_column', ''), ['code'])
display_col = find_col(row_lower, sm.get('display_column', ''), ['desc', 'description', 'name'])
display_arb_col = find_col(row_lower, sm.get('display_arb_column', ''), ['arb', 'arabic'])
active_col = find_col(row_lower, sm.get('active_column', ''), ['active', 'isactive', 'status'])
mapped_cols_lower = [c for c in [id_col, code_col, display_col, display_arb_col, active_col] if c is not None]

print("id_col:", id_col)
print("code_col:", code_col)
print("display_col:", display_col)
print("display_arb_col:", display_arb_col)
print("active_col:", active_col)
print("mapped_cols_lower:", mapped_cols_lower)
