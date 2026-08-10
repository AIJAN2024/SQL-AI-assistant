import requests
import pyodbc
import pandas as pd
import re

# ============================================
# 1. 连接 SQL Server（Windows 身份验证，pyodbc）
# ============================================
conn_str = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=localhost;"
    "Database=库2;"
    "Trusted_Connection=yes;"
)
try:
    conn = pyodbc.connect(conn_str)
    print("✅ 已连接到 SQL Server")
except Exception as e:
    print(f"❌ 连接失败: {e}")
    exit()

# ============================================
# 2. 表结构描述（请根据实际字段填写）
# ============================================
TABLE_SCHEMA = """
SQL Server database: 库2

Table: course
- id: int, primary key
- course_name: nvarchar(100)   (课程名称)
- teacher: nvarchar(50)        (授课教师)
- credits: int                 (学分)
- (其他字段请补充...)

Table: Student (可选，后续可添加)
...

Current date function: GETDATE()
Date calculation: DATEADD(day, -30, GETDATE())
"""


# 这里先只配置 course 表，后续可以添加更多表

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
# 4. 执行 SQL（只读查询模式，安全）
# ============================================
def execute_sql(sql):
    try:
        clean_sql = sql.rstrip(';').strip()
        # 只允许 SELECT
        if not clean_sql.upper().startswith('SELECT'):
            return "⚠️  当前模式仅支持 SELECT 查询。"

        # 使用 cursor 执行查询，避免 pandas 警告
        cursor = conn.cursor()
        cursor.execute(clean_sql)
        # 获取列名
        columns = [col[0] for col in cursor.description]
        # 获取所有行
        rows = cursor.fetchall()
        # 构造 DataFrame
        df = pd.DataFrame.from_records(rows, columns=columns)
        cursor.close()
        return df
    except Exception as e:
        return f"❌ Execution error: {str(e)}"


# ============================================
# 5. 主循环
# ============================================
print("\n" + "=" * 60)
print("🤖 SQL AI 助手 (SQL Server 版 - 只读)")
print("=" * 60)
print("\n💡 你可以问：")
print("  - 查询 course 表的所有数据")
print("  - 查看 course 表的课程名称和学分")
print("  - 有多少门课程？")
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