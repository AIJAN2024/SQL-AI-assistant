import pyodbc
import pandas as pd

conn_str = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=localhost;"
    "Database=库2;"
    "Trusted_Connection=yes;"
)
conn = pyodbc.connect(conn_str)

df = pd.read_sql_query("SELECT TOP 5 * FROM monthly_stats", conn)
print(df)
conn.close()
