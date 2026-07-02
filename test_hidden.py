import json
settings=json.load(open('config/settings.json'))
from main import build_mssql_conn_string
conn_str=build_mssql_conn_string(settings['mssql'])
import pyodbc
conn=pyodbc.connect(conn_str)
cursor=conn.cursor()
cursor.execute("SELECT c.name, COLUMNPROPERTY(tbl.object_id, c.name, 'IsHidden') FROM sys.columns c INNER JOIN sys.tables tbl ON c.object_id = tbl.object_id WHERE tbl.name = 'IVItem'")
print(cursor.fetchall())
