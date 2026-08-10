import pyodbc
import pandas as pd
import re
import requests

# ============================================
# 1. 连接 SQL Server（Windows 身份验证）
# ============================================
conn_str = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=localhost;"
    "Database=NBS;"  # ← 改成你的数据库名
    "Trusted_Connection=yes;"
)
try:
    conn = pyodbc.connect(conn_str)
    print("✅ 已连接到 SQL Server")
except Exception as e:
    print(f"❌ 连接失败: {e}")
    exit()


# ============================================
# 2. 自动获取所有用户表的元数据
# ============================================
def get_schema():
    cursor = conn.cursor()
    cursor.execute("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE='BASE TABLE' 
          AND TABLE_NAME NOT LIKE 'sys%'
        ORDER BY TABLE_NAME
    """)
    tables = cursor.fetchall()

    schema_desc = "SQL Server database: 库2\n\n"
    for (table_name,) in tables:
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """, table_name)
        columns = cursor.fetchall()
        schema_desc += f"Table: {table_name}\n"
        for col_name, data_type, is_nullable in columns:
            nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
            schema_desc += f"  - {col_name}: {data_type} ({nullable})\n"
        schema_desc += "\n"

    schema_desc += "Date functions (SQL Server):\n"
    schema_desc += "  - Current date: GETDATE()\n"
    schema_desc += "  - Date add: DATEADD(day, -30, GETDATE())\n"
    schema_desc += "  - Example: WHERE sale_date >= DATEADD(day, -30, GETDATE())\n"

    cursor.close()
    return schema_desc


TABLE_SCHEMA = get_schema()
print(f"📋 已加载表结构，共 {len(TABLE_SCHEMA.split('Table:')) - 1} 个表\n")


# ============================================
# 3. 调用本地 Ollama 生成 SQL
# ============================================
def ask_ollama(question):
    prompt = f"""You are a SQL Server expert. Convert the user's question to SQL Server SQL.

IMPORTANT: Output ONLY the SQL query. No explanation, no extra text.

Table schema:
{TABLE_SCHEMA}

User question: {question}
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
        match = re.search(
            r'(SELECT\s+.*?;|INSERT\s+.*?;|UPDATE\s+.*?;|DELETE\s+.*?;|CREATE\s+.*?;|DROP\s+.*?;|ALTER\s+.*?;)', sql,
            re.IGNORECASE | re.DOTALL)
        if match:
            sql = match.group(1)
        else:
            lines = sql.split('\n')
            sql_lines = []
            for line in lines:
                if line.strip().upper().startswith(('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER')):
                    sql_lines.append(line)
                elif sql_lines and line.strip():
                    sql_lines.append(line)
            sql = '\n'.join(sql_lines) if sql_lines else sql

        sql = re.sub(r'```sql\s*', '', sql)
        sql = re.sub(r'```\s*', '', sql)
        sql = sql.strip()
        if sql and not sql.endswith(';'):
            sql += ';'
        return sql
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================
# 4. 执行 SQL（只读模式）
# ============================================
def execute_sql(sql):
    try:
        clean_sql = sql.rstrip(';').strip()
        if not clean_sql.upper().startswith('SELECT'):
            return "⚠️  当前模式仅支持 SELECT 查询。"
        cursor = conn.cursor()
        cursor.execute(clean_sql)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        df = pd.DataFrame.from_records(rows, columns=columns)
        cursor.close()
        return df
    except Exception as e:
        return f"❌ Execution error: {str(e)}"


# ============================================
# 5. 主循环
# ============================================
print("\n" + "=" * 60)
print("🤖 SQL AI 助手 (SQL Server - 自动识别所有表)")
print("=" * 60)
print("\n💡 你可以直接问任何表的问题，例如：")
print("  - 查询 course 表的所有数据")
print("  - 显示 Student 表中的学生姓名")
print("  - 统计 grade 表中成绩大于90的人数")
print("  - 列出 class 表的全部内容")
print("\n输入 'quit' 退出\n")

while True:
    question = input("👤 你: ")
    if question.lower() in ['quit', 'exit', 'q']:
        print("👋 再见！")
        break
    if not question.strip():
        continue

    print("\n⏳ 正在生成SQL...")
    sql = ask_ollama(question)

    if sql.startswith("Error"):
        print(f"❌ {sql}")
        continue

    print(f"\n📝 生成的SQL:\n{sql}\n")

    print("⏳ 正在执行...")
    result = execute_sql(sql)

    if isinstance(result, str):
        print(result)
    elif isinstance(result, pd.DataFrame):
        print(f"\n📊 查询结果 (共 {len(result)} 行):\n")
        print(result.to_string(index=False))
        print()
    else:
        print(result)

conn.close()