import pyodbc

try:
    # Windows 身份验证连接
    conn_str = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=localhost;"
        "Database=库2;"
        "Trusted_Connection=yes;"
    )
    conn = pyodbc.connect(conn_str)
    print("✅ 连接成功！")

    cursor = conn.cursor()
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES")
    rows = cursor.fetchall()
    print("\n📋 当前数据库中的表：")
    for row in rows:
        print(f"  - {row[0]}")

    conn.close()
except Exception as e:
    print(f"❌ 错误: {e}")

    # 查看 course 表有哪些列
    cursor.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='course'")
    print("\n📋 course 表结构：")
    for col in cursor.fetchall():
        print(f"  - {col[0]} ({col[1]})")