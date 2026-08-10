import pandas as pd
import pyodbc
import os

csv_path = 'consumption_data_2024.csv'

if not os.path.exists(csv_path):
    print(f"❌ 找不到文件：{csv_path}")
    exit()

print(f"✅ 找到文件：{csv_path}")

# ============================================
# 按行读取，跳过说明行
# ============================================
with open(csv_path, 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()

print(f"文件共 {len(lines)} 行")

# 找数据起始行
data_start = 0
for i, line in enumerate(lines):
    if '\t' in line and any(c.isdigit() for c in line):
        data_start = i
        break

print(f"数据起始行：第 {data_start + 1} 行")

# 提取数据行
data_lines = lines[data_start:]

rows = []
for line in data_lines:
    parts = line.strip().split('\t')
    if len(parts) > 1:
        rows.append(parts)

print(f"共解析到 {len(rows)} 行数据")

if not rows:
    print("❌ 没有解析到数据")
    exit()

# 第一行作为列名，后面作为数据
raw_columns = rows[0]
data = rows[1:]

# 清理列名
cleaned_columns = []
for col in raw_columns:
    col = col.strip().strip(',').strip()
    if not col:
        col = 'unnamed'
    if col in cleaned_columns:
        count = 1
        while f"{col}_{count}" in cleaned_columns:
            count += 1
        col = f"{col}_{count}"
    cleaned_columns.append(col)

# 创建DataFrame，同时清理数据中的多余逗号
clean_data = []
for row in data:
    clean_row = []
    for val in row:
        # 去掉值中的逗号
        val = val.strip().strip(',').strip()
        clean_row.append(val)
    clean_data.append(clean_row)

df = pd.DataFrame(clean_data, columns=cleaned_columns)

print(f"✅ 成功构建DataFrame，共 {len(df)} 行，{len(df.columns)} 列")
print(f"   列名：{df.columns.tolist()}")
print(f"\n前两行预览：\n{df.head(2)}")

# ============================================
# 入库到 SQL Server（使用 pyodbc）
# ============================================
table_name = 'monthly_stats_2024'

try:
    conn_str = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=localhost;"
        "Database=NBS;"  # 改成你的数据库名
        "Trusted_Connection=yes;"
    )
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    print("✅ 连接数据库成功")

    # 建表
    cols = df.columns.tolist()
    create_sql = f"""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{table_name}' AND xtype='U')
        CREATE TABLE {table_name} (
            id INT IDENTITY(1,1) PRIMARY KEY,
            {', '.join([f'[{col}] NVARCHAR(500)' for col in cols])}
        )
    """
    cursor.execute(create_sql)
    print(f"✅ 表 {table_name} 准备就绪")

    # 插入数据
    count = 0
    for _, row in df.iterrows():
        placeholders = ', '.join(['?'] * len(cols))  # pyodbc 用 ? 作为占位符
        values = tuple(str(v) if pd.notna(v) else '' for v in row)
        cursor.execute(
            f"INSERT INTO {table_name} ({', '.join([f'[{col}]' for col in cols])}) VALUES ({placeholders})",
            values
        )
        count += 1

    conn.commit()
    conn.close()
    print(f"✅ 成功导入 {count} 条数据到 {table_name}")

except Exception as e:
    print(f"❌ 数据库操作失败：{e}")