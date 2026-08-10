import pyodbc
import pandas as pd

conn_str = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=localhost;"
    "Database=NBS;"
    "Trusted_Connection=yes;"
)
conn = pyodbc.connect(conn_str)

tables = ['gdp_yearly', 'cpi_monthly', 'ppi_monthly', 'pmi_monthly', 'm2_monthly', 'lpr', 'fdi']
print("📊 各表数据量：")
for table in tables:
    try:
        df = pd.read_sql_query(f"SELECT COUNT(*) as cnt FROM {table}", conn)
        print(f"  ✅ {table}: {df['cnt'].iloc[0]} 行")
    except Exception as e:
        print(f"  ❌ {table}: 不存在")

conn.close()