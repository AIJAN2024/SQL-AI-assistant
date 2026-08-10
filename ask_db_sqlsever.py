import requests
import pymssql
import pandas as pd
import re

# ============================================
# 1. 连接 SQL Server（请修改为你的实际信息）
# ============================================
import pyodbc

conn_str = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=localhost;"
    "Database=master;"
    "Trusted_Connection=yes;"
)
conn = pyodbc.connect(conn_str)

print("✅ 已连接到 SQL Server")

# ============================================
# 2. 表结构描述（让AI了解你的业务）
# ============================================
TABLE_SCHEMA = """
SQL Server database tables:
(请根据你的实际表结构修改)

Table: orders
- id: int, primary key, identity(1,1)
- product_name: nvarchar(100)
- category: nvarchar(50)
- price: decimal(10,2)
- sales_volume: int
- sale_date: date

Current date function in SQL Server: GETDATE()
Date calculation: DATEADD(day, -30, GETDATE())
Example: WHERE sale_date >= DATEADD(day, -30, GETDATE())
"""


# ============================================
# 3. 调用本地Ollama生成SQL
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

        # 提取纯SQL
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
# 4. 执行SQL（支持查询和修改，带安全确认）
# ============================================
def execute_sql(sql):
    try:
        clean_sql = sql.rstrip(';').strip()

        # 判断SQL类型
        sql_upper = clean_sql.upper()

        # 如果是修改类操作，需要用户确认
        if sql_upper.startswith(('INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE')):
            print("\n⚠️  检测到修改操作，请确认是否执行？")
            print(f"📝 {clean_sql}")
            confirm = input("确认执行吗？(输入 y 执行，其他任意键取消): ")
            if confirm.lower() != 'y':
                return "⏸️  操作已取消"

        # 执行SQL
        if sql_upper.startswith('SELECT'):
            df = pd.read_sql_query(clean_sql, conn)
            return df
        else:
            cursor = conn.cursor()
            cursor.execute(clean_sql)
            conn.commit()
            return f"✅ 操作成功，影响了 {cursor.rowcount} 行"
    except Exception as e:
        return f"❌ Execution error: {str(e)}"


# ============================================
# 5. 主循环
# ============================================
print("\n" + "=" * 60)
print("🤖 SQL AI 助手 (SQL Server 版)")
print("=" * 60)
print("\n💡 你可以问：")
print("  - 查询订单表的所有数据")
print("  - 创建一个订单表，包含商品名称、类别、单价、销量")
print("  - 插入一条记录：商品是手机，单价2999，销量50")
print("  - 修改手机的价格为2500")
print("  - 删除销量为0的商品")
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