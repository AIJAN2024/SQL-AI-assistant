import akshare as ak
import pyodbc
import pandas as pd

# ============================================
# 1. 获取数据
# ============================================
print("🔄 正在获取CPI月率数据...")
df = ak.macro_china_cpi_monthly()
print(f"✅ 获取到 {len(df)} 条数据")

# ============================================
# 2. 按列位置提取数据
# ============================================
dates = df.iloc[:, 1]  # 日期
values = df.iloc[:, 2]  # 今值（CPI月率）

clean_data = []
for i in range(len(dates)):
    date_str = str(dates.iloc[i])
    val_str = str(values.iloc[i])

    try:
        period = pd.to_datetime(date_str).strftime('%Y-%m')
    except:
        continue

    try:
        value = float(val_str)
    except:
        continue

    if pd.notna(value):
        clean_data.append({'period': period, 'cpi_rate': value})

df_clean = pd.DataFrame(clean_data)
df_clean = df_clean.sort_values('period')

print(f"✅ 清洗后剩余 {len(df_clean)} 条有效数据")
print(df_clean.head())


# ============================================
# 3. 存入 SQL Server（指定数据库和表名）
# ============================================
def save_to_sql(df):
    if df.empty:
        print("⚠️ 没有数据可保存")
        return

    # 连接字符串指定数据库 NBS
    conn_str = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=localhost;"
        "Database=NBS;"  # ← 改成你的数据库名
        "Trusted_Connection=yes;"
    )

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        print("✅ 连接数据库成功")

        # 指定表名 nrban_CPI
        table_name = 'urban_CPI'

        # 建表
        cursor.execute(f"""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{table_name}' AND xtype='U')
            CREATE TABLE {table_name} (
                id INT IDENTITY(1,1) PRIMARY KEY,
                period NVARCHAR(20),
                cpi_rate DECIMAL(10, 4),
                created_at DATETIME DEFAULT GETDATE()
            )
        """)
        print(f"✅ 表 {table_name} 准备就绪")

        # 插入数据（去重）
        count = 0
        for _, row in df.iterrows():
            period = row['period']
            value = float(row['cpi_rate'])

            # 检查是否已存在
            cursor.execute(
                f"SELECT COUNT(*) FROM {table_name} WHERE period = ?",
                (period,)
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    f"INSERT INTO {table_name} (period, cpi_rate) VALUES (?, ?)",
                    (period, value)
                )
                count += 1

        conn.commit()
        conn.close()
        print(f"✅ 成功导入 {count} 条新数据到 {table_name}")

    except Exception as e:
        print(f"❌ 数据库操作失败：{e}")


# 执行入库
save_to_sql(df_clean)