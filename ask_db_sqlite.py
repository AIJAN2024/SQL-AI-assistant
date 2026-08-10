import requests
import sqlite3
import pandas as pd
import re

conn = sqlite3.connect('orders.db')

TABLE_SCHEMA = """
SQLite database table orders:
- id: integer primary key
- product_name: text
- category: text
- price: real
- sales_volume: integer
- sale_date: date

Date functions for SQLite:
- Today: DATE('now')
- Last 30 days: DATE('now', '-30 days')
- Example: WHERE sale_date >= DATE('now', '-30 days')
- Important: Do not use DATE_SUB or CURDATE()
"""


def ask_ollama(question):
    prompt = f"""You are a SQLite expert. Convert the user question to SQLite SQL.

IMPORTANT: Output ONLY the SQL query. Do not include any explanation, description, or extra text. Just the SQL statement.

Table schema:
{TABLE_SCHEMA}

Question: {question}
SQL:"""

    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'qwen2.5:7b',
                'prompt': prompt,
                'stream': False,
                'temperature': 0.1,
                'max_tokens': 500
            },
            timeout=60
        )
        sql = response.json()['response'].strip()

        # 更严格的SQL提取：只保留SELECT语句
        match = re.search(r'(SELECT\s+.*?;)', sql, re.IGNORECASE | re.DOTALL)
        if match:
            sql = match.group(1)
        else:
            # 如果没有SELECT，尝试清理多余文字
            lines = sql.split('\n')
            sql_lines = []
            for line in lines:
                if line.strip().upper().startswith('SELECT') or line.strip().upper().startswith('WITH'):
                    sql_lines.append(line)
                elif sql_lines and line.strip():
                    sql_lines.append(line)
            sql = '\n'.join(sql_lines) if sql_lines else sql

        # 清理markdown和多余内容
        sql = re.sub(r'```sql\s*', '', sql)
        sql = re.sub(r'```\s*', '', sql)
        sql = sql.strip()

        # 确保以分号结尾
        if sql and not sql.endswith(';'):
            sql += ';'

        return sql
    except Exception as e:
        return f"Error: {str(e)}"


def execute_sql(sql):
    try:
        clean_sql = sql.rstrip(';')
        df = pd.read_sql_query(clean_sql, conn)
        return df
    except Exception as e:
        return f"Execution error: {str(e)}"


print("\n" + "=" * 50)
print("SQL AI Assistant")
print("=" * 50)
print("\nTry asking:")
print("  - Top 5 products by sales volume")
print("  - Average price of electronic products")
print("  - Total sales in the last 30 days")
print("  - Total sales by category")
print("\nType 'quit' to exit\n")

while True:
    question = input("You: ")
    if question.lower() in ['quit', 'exit', 'q']:
        print("Bye!")
        break
    if not question.strip():
        continue

    print("\nGenerating SQL...")
    sql = ask_ollama(question)

    if sql.startswith("Error"):
        print(f"Error: {sql}")
        continue

    print(f"\nSQL:\n{sql}\n")
    print("Executing...")
    result = execute_sql(sql)

    if isinstance(result, str):
        print(f"Error: {result}")
    else:
        print(f"Results ({len(result)} rows):\n")
        print(result.to_string(index=False))
        print()

conn.close()