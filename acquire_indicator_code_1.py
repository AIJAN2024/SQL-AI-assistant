"""
宏观经济数据全量采集脚本
采集 GDP、CPI、PPI、PMI、M2、LPR、FDI 数据
存入 NBS 数据库
"""

import akshare as ak
import pyodbc
import pandas as pd
import time
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

# ============================================
# 1. 数据库连接配置
# ============================================
conn_str = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=localhost;"
    "Database=NBS;"
    "Trusted_Connection=yes;"
)

# ============================================
# 2. 定义所有数据源
# ============================================
DATA_SOURCES = {
    "gdp_yearly": {
        "name": "GDP年度数据",
        "func": ak.macro_china_gdp_yearly,
        "description": "中国年度GDP"
    },
    "cpi_monthly": {
        "name": "CPI月度数据",
        "func": ak.macro_china_cpi,
        "description": "居民消费价格指数"
    },
    "ppi_monthly": {
        "name": "PPI月度数据",
        "func": ak.macro_china_ppi,
        "description": "工业生产者出厂价格指数"
    },
    "pmi_monthly": {
        "name": "PMI月度数据",
        "func": ak.macro_china_pmi,
        "description": "制造业采购经理指数"
    },
    "m2_monthly": {
        "name": "M2月度数据",
        "func": ak.macro_china_money_supply,
        "description": "货币供应量M2"
    },
    "lpr": {
        "name": "LPR数据",
        "func": ak.macro_china_lpr,
        "description": "贷款市场报价利率"
    },
    "fdi": {
        "name": "FDI数据",
        "func": ak.macro_china_fdi,
        "description": "外商直接投资"
    }
}


# ============================================
# 3. 通用入库函数
# ============================================
def save_to_sql(df, table_name, description):
    """将 DataFrame 存入 SQL Server（自动建表，所有列存为 NVARCHAR）"""
    if df.empty:
        print(f"   ⚠️ 数据为空，跳过")
        return False

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # 获取列名
        cols = df.columns.tolist()
        print(f"   📋 列名: {cols[:5]}{'...' if len(cols) > 5 else ''}")

        # 建表（所有列用 NVARCHAR）
        create_cols = [f'[{col}] NVARCHAR(500)' for col in cols]
        create_sql = f"""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{table_name}' AND xtype='U')
            CREATE TABLE {table_name} (
                id INT IDENTITY(1,1) PRIMARY KEY,
                {', '.join(create_cols)}
            )
        """
        cursor.execute(create_sql)

        # 清空旧数据
        cursor.execute(f"DELETE FROM {table_name}")

        # 插入数据
        count = 0
        for _, row in df.iterrows():
            placeholders = ', '.join(['?'] * len(cols))
            values = tuple(str(v) if pd.notna(v) else '' for v in row)
            cursor.execute(
                f"INSERT INTO {table_name} ({', '.join([f'[{col}]' for col in cols])}) VALUES ({placeholders})",
                values
            )
            count += 1

        conn.commit()
        conn.close()
        print(f"   ✅ 成功写入 {count} 条数据")
        return True

    except Exception as e:
        print(f"   ❌ 入库失败: {e}")
        return False


# ============================================
# 4. 获取数据库中已存在的表
# ============================================
def get_existing_tables():
    """查询当前数据库中已有的表"""
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    except Exception as e:
        print(f"⚠️ 查询已有表失败: {e}")
        return []


# ============================================
# 5. 主程序
# ============================================
def main():
    print("=" * 60)
    print("🚀 宏观经济数据全量采集系统")
    print("=" * 60)

    # 检查数据库连接
    try:
        conn = pyodbc.connect(conn_str)
        conn.close()
        print("✅ 数据库连接成功\n")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print("请检查:")
        print("  1. SQL Server 是否运行")
        print("  2. 数据库 'NBS' 是否存在")
        print("  3. ODBC Driver 17 是否安装")
        return

    # 获取已有表
    existing = get_existing_tables()
    print(f"📋 当前已有 {len(existing)} 张表: {existing if existing else '无'}\n")

    # 统计信息
    total_success = 0
    total_fail = 0
    skipped = 0

    # 遍历所有数据源
    for table_name, config in DATA_SOURCES.items():
        print(f"⏳ [{table_name}] 正在采集 {config['name']}...")

        # 检查是否已存在（可选：强制刷新）
        if table_name in existing:
            print(f"   📌 表已存在，将覆盖更新")

        try:
            # 采集数据
            df = config['func']()
            print(f"   📊 获取到 {len(df)} 行数据")

            # 入库
            if save_to_sql(df, table_name, config['description']):
                total_success += 1
            else:
                total_fail += 1

        except Exception as e:
            print(f"   ❌ 采集失败: {e}")
            total_fail += 1

        print()  # 空行分隔
        time.sleep(1.5)  # 礼貌性延迟

    # 输出总结
    print("=" * 60)
    print("📊 采集完成！")
    print(f"   ✅ 成功: {total_success} 张表")
    print(f"   ❌ 失败: {total_fail} 张表")
    print(f"   📌 总计: {len(DATA_SOURCES)} 张表")
    print("=" * 60)


if __name__ == '__main__':
    main()