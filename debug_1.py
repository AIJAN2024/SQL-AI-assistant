import sqlite3
import pandas as pd

conn = sqlite3.connect('orders.db')
df = pd.read_sql_query("SELECT * FROM orders LIMIT 10", conn)
print(df)
conn.close()