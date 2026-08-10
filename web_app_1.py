"""
SQL AI 智能查询助手 - 方向一优化版
优化内容：缓存、历史记录、加载动画、交互体验
"""

import streamlit as st
import pyodbc
import pandas as pd
import requests
import re
import plotly.express as px
from datetime import datetime
import hashlib
import time
from functools import lru_cache
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

# ============================================
# 页面配置
# ============================================
st.set_page_config(
    page_title="SQL AI 智能查询助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS（优化视觉体验）
st.markdown("""
    <style>
    .stTextInput > div > div > input {
        font-size: 16px;
    }
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-bottom: 1.5rem;
    }
    .history-item {
        padding: 4px 8px;
        border-radius: 4px;
        margin-bottom: 2px;
        cursor: pointer;
    }
    .history-item:hover {
        background-color: #f0f2f6;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================
# 数据库连接函数
# ============================================
@st.cache_resource
def get_connection():
    """获取数据库连接"""
    conn_str = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=localhost;"
        "Database=NBS;"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)

# 初始化数据库连接
try:
    conn = get_connection()
except Exception as e:
    st.error(f"❌ 数据库连接失败: {e}")
    st.stop()

# ============================================
# 初始化 Session State
# ============================================
if 'history' not in st.session_state:
    st.session_state.history = []
if 'query_count' not in st.session_state:
    st.session_state.query_count = 0
if 'df_result' not in st.session_state:
    st.session_state.df_result = None
if 'last_sql' not in st.session_state:
    st.session_state.last_sql = None
if 'last_question' not in st.session_state:
    st.session_state.last_question = None

# ============================================
# 标题
# ============================================
st.markdown('<p class="main-header">🤖 SQL AI 智能查询助手</p >', unsafe_allow_html=True)
st.markdown('<p class="sub-header">基于 Qwen2.5-7B 本地部署 | 支持多表查询 | 自动可视化</p >', unsafe_allow_html=True)

# ============================================
# 侧边栏：配置 + 历史
# ============================================

# ✅ conn 在这里定义（在 with st.sidebar 之前）
try:
    conn = get_connection()
    st.sidebar.success("✅ 数据库连接成功")
except Exception as e:
    st.sidebar.error(f"❌ 连接失败: {e}")
    st.stop()

with st.sidebar:
    # ============================================
    # 1. 数据库配置
    # ============================================
    st.header("⚙️ 数据库配置")
    database = st.text_input(
        "数据库名",
        value="NBS",
        key="db_name",
        help="要连接的数据库名称"
    )
    table_name = st.text_input(
        "查询表名（留空自动识别）",
        value="",
        key="table_name",
        placeholder="留空则AI自动识别表",
        help="输入表名则强制使用该表，留空则AI自动识别"
    )

    # ============================================
    # 2. 快捷查询
    # ============================================
    st.divider()
    st.markdown("### ⚡ 快捷查询")

    quick_queries = [
        ("📈 CPI月率 > 2", "查询CPI月率大于2的数据"),
        ("📊 GDP年度数据", "查询GDP年度数据"),
        ("💰 M2货币供应量", "查询M2货币供应量"),
        ("📉 PMI指数", "查询PMI月度数据"),
        ("🏦 LPR利率", "查询LPR利率"),
        ("📊 制造业同比增长", "查询制造业-同比增长大于4的月份")
    ]

    # 用两列布局显示快捷按钮
    col1, col2 = st.columns(2)
    for i, (label, q) in enumerate(quick_queries):
        if i % 2 == 0:
            with col1:
                if st.button(label, use_container_width=True, key=f"quick_{i}"):
                    st.session_state.quick_question = q
        else:
            with col2:
                if st.button(label, use_container_width=True, key=f"quick_{i}"):
                    st.session_state.quick_question = q

    # ============================================
    # 3. 查询历史
    # ============================================
    st.divider()
    st.markdown("### 📜 查询历史")

    # 显示历史条数
    st.caption(f"📊 共 {len(st.session_state.history)} 条记录")

    if st.session_state.history:
        # 只显示最近10条
        for idx, (q, t) in enumerate(st.session_state.history[-10:]):
            # 根据是否成功显示不同图标
            if q.startswith("❌"):
                icon = "❌"
                display_q = q[2:]  # 去掉 ❌ 前缀
            elif q.startswith("🔗"):
                icon = "🔗"
                display_q = q[2:]  # 去掉 🔗 前缀
            else:
                icon = "✅"
                display_q = q

            display_q = display_q[:30] + "..." if len(display_q) > 30 else display_q
            button_label = f"{icon} {t} {display_q}"

            if st.button(button_label, key=f"hist_{idx}_{t}_{i}", use_container_width=True):
                # 如果点击历史记录，自动填入输入框
                st.session_state.hist_question = q
    else:
        st.caption("暂无查询历史，开始查询吧！")

    # ============================================
    # 4. 查询模式（新功能）
    # ============================================
    st.divider()
    st.markdown("### 🔍 查询模式")

    # 显示上次查询模式
    if 'last_query_mode' in st.session_state and st.session_state.last_query_mode:
        st.caption(f"📌 上次查询: {st.session_state.last_query_mode}")
    else:
        st.caption("📌 尚未查询")

    # 模式说明
    st.caption("💡 不指定表名时自动识别")
    st.caption("💡 包含'对比'/'和'等词自动切换多表")

    # ============================================
    # 5. 数据库状态
    # ============================================
    st.divider()
    st.markdown("### 📊 数据库状态")
    st.caption(f"🗄️ 数据库: {database}")
    st.caption(f"📋 当前表: {table_name if table_name else '自动识别'}")
    st.caption(f"🔢 总查询次数: {st.session_state.query_count}")

    # 显示连接状态
    try:
        # 测试连接是否有效
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        st.success("✅ 数据库连接正常")
    except:
        st.error("❌ 数据库连接断开")


# ============================================
# 数据库连接
# ============================================
@st.cache_resource
def get_connection():
    conn_str = (
        "Driver={ODBC Driver 17 for SQL Server};"
        f"Server=localhost;"
        f"Database={database};"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)


try:
    conn = get_connection()
    st.sidebar.success("✅ 数据库连接成功")
except Exception as e:
    st.sidebar.error(f"❌ 连接失败: {e}")
    st.stop()


# ============================================
# 获取所有表结构（用于多表查询）
# ============================================
def get_all_tables_schema():
    """获取数据库中所有用户表的结构"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE='BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        tables = [row[0] for row in cursor.fetchall()]

        if not tables:
            return "No tables found in database."

        all_schema = ""
        for table_name in tables:
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
            """, (table_name,))
            cols = cursor.fetchall()

            all_schema += f"Table: {table_name}\n"
            for col_name, data_type, is_nullable in cols:
                nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
                all_schema += f"  - {col_name}: {data_type} ({nullable})\n"
            all_schema += "\n"

        return all_schema
    except Exception as e:
        return f"Error getting schema: {e}"


# ============================================
# 自动识别表名
# ============================================
def detect_table(question):
    """根据用户问题自动识别应该查询哪张表"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE='BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        tables = [row[0] for row in cursor.fetchall()]

        if not tables:
            print("❌ 数据库中没有表")
            return None

        tables_str = ", ".join(tables)
        print(f"📋 可用的表: {tables}")

        prompt = f"""根据用户问题，从以下表中选择最相关的一张表，只输出表名，不要输出任何其他内容。

可选表：{tables_str}
用户问题：{question}
表名："""

        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'qwen2.5:7b',
                'prompt': prompt,
                'stream': False,
                'temperature': 0,
                'max_tokens': 50
            },
            timeout=30
        )
        detected = response.json()['response'].strip()
        detected = detected.replace('"', '').replace("'", '').replace('[', '').replace(']', '').strip()
        print(f"🔍 AI 返回的表名: '{detected}'")

        # 1. 精确匹配
        for t in tables:
            if t == detected:
                print(f"✅ 精确匹配: {t}")
                return t

        # 2. 忽略大小写匹配
        for t in tables:
            if t.lower() == detected.lower():
                print(f"✅ 忽略大小写匹配: {t}")
                return t

        # 3. 包含匹配（处理表名包含空格的情况）
        for t in tables:
            t_clean = t.replace(" ", "")
            detected_clean = detected.replace(" ", "")
            if detected_clean.lower() in t_clean.lower() or t_clean.lower() in detected_clean.lower():
                print(f"✅ 包含匹配: {t}")
                return t

        # 4. 关键词映射
        keyword_map = {
            '客户': 'Customers', '顾客': 'Customers',
            '订单': 'Orders', '产品': 'Products', '商品': 'Products',
            '员工': 'Employees', '供应商': 'Suppliers',
            '类别': 'Categories', '分类': 'Categories',
            '物流': 'Shippers', '运货': 'Shippers'
        }
        for keyword, table in keyword_map.items():
            if keyword in question and table in tables:
                print(f"✅ 关键词匹配: {keyword} → {table}")
                return table

        # 5. 兜底：返回第一个表
        print(f"⚠️ 使用默认表: {tables[0]}")
        return tables[0] if tables else None

    except Exception as e:
        print(f"❌ 自动识别表失败: {e}")
        # 出错时返回第一个表作为兜底
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
            first = cursor.fetchone()
            return first[0] if first else None
        except:
            return None

# ============================================
# 获取表结构（带缓存 + 示例数据）
# ============================================
@st.cache_data(ttl=3600)
def get_table_schema_cached(table_name):
    """获取表结构，带缓存，并附加示例数据帮助AI理解"""
    cursor = conn.cursor()
    try:
        # 1. 获取列信息
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = ?
        """, (table_name,))
        cols = cursor.fetchall()

        if not cols:
            return f"Table: {table_name} (结构未知，请检查表名是否正确)"

        # 2. 构建表结构描述
        schema = f"Table: {table_name}\n"
        schema += "字段说明:\n"
        for col_name, data_type in cols:
            schema += f"  - {col_name}: {data_type}\n"

        # 3. 增加示例数据（帮助AI理解字段含义和格式）
        try:
            sample_df = pd.read_sql_query(f"SELECT TOP 3 * FROM {table_name}", conn)
            if not sample_df.empty:
                schema += "\n示例数据 (前3行):\n"
                schema += sample_df.to_string(index=False)
        except Exception as e:
            schema += f"\n(无法获取示例数据: {e})"

        return schema
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================
# 获取所有表结构（用于多表查询）
# ============================================
@st.cache_data(ttl=3600)
def get_all_tables_schema():
    """获取数据库中所有用户表的结构（增强版）"""
    cursor = conn.cursor()

    # 获取所有用户表（排除系统表）
    cursor.execute("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE='BASE TABLE' 
          AND TABLE_NAME NOT IN ('sysdiagrams', 'spt_values')
        ORDER BY TABLE_NAME
    """)
    tables = [row[0] for row in cursor.fetchall()]

    if not tables:
        return "No tables found in database."

    all_schema = ""
    for table_name in tables:
        # 获取列信息（包含更详细的信息）
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """, (table_name,))
        cols = cursor.fetchall()

        if not cols:
            continue

        all_schema += f"Table: {table_name}\n"
        all_schema += f"  Columns:\n"
        for col_name, data_type, is_nullable in cols:
            nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
            all_schema += f"    - [{col_name}]: {data_type} ({nullable})\n"

        # 增加示例数据（帮助AI理解字段含义和实际数据格式）
        try:
            sample_df = pd.read_sql_query(f"SELECT TOP 3 * FROM [{table_name}]", conn)
            if not sample_df.empty:
                all_schema += f"  Sample Data (first 3 rows):\n"
                # 格式化示例数据，显示列名和值
                for _, row in sample_df.iterrows():
                    row_str = []
                    for col in sample_df.columns:
                        val = str(row[col])[:50] if row[col] is not None else 'NULL'
                        row_str.append(f"[{col}]={val}")
                    all_schema += f"    " + ", ".join(row_str) + "\n"
        except Exception as e:
            all_schema += f"  (Sample data unavailable: {e})\n"

        all_schema += "\n"

    # 增加表之间的关联关系
    all_schema += """
=== 表之间的关联关系 ===
- gdp_yearly: 年度GDP数据，使用 [年份] 列
- cpi_monthly: 月度CPI数据，使用 [月份] 列
- ppi_monthly: 月度PPI数据，使用 [月份] 列
- pmi_monthly: 月度PMI数据，使用 [月份] 列
- m2_monthly: 月度M2数据，使用 [月份] 列
- lpr: LPR利率数据，使用 [月份] 列
- fdi: 外商直接投资数据，使用 [月份] 列

重要提醒：
1. 所有列名必须用方括号 [] 包裹
2. 查询多表时使用月份或年份进行关联
3. 如果列名包含中文字符或特殊符号，必须使用 [] 
4. 例如: [制造业-同比增长], [2023年12月份]
"""

    return all_schema


# ============================================
# 自动识别表名（方案一）
# ============================================
@st.cache_data(ttl=3600)
def get_all_tables_schema():
    """获取数据库中所有用户表的结构（增强版 + 调试）"""
    cursor = conn.cursor()

    # 获取所有用户表
    cursor.execute("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE='BASE TABLE'
        ORDER BY TABLE_NAME
    """)
    tables = [row[0] for row in cursor.fetchall()]

    if not tables:
        return "No tables found in database."

    all_schema = ""
    for table_name in tables:
        # 获取列信息
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """, (table_name,))
        cols = cursor.fetchall()

        all_schema += f"Table: {table_name}\n"
        for col_name, data_type, is_nullable in cols:
            nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
            all_schema += f"  - {col_name}: {data_type} ({nullable})\n"
        all_schema += "\n"

    return all_schema


# ============================================
# 判断是否需要多表联合查询（方案四）
# ============================================
def need_multi_table(question):
    """判断问题是否需要多表联合查询"""
    keywords = ['对比', '比较', '和', '与', 'VS', 'vs', '同时', '分别',
                'GDP和CPI', '各指标', '多个指标', 'GDP与CPI', '跨表']
    for kw in keywords:
        if kw in question:
            return True
    return False


# ============================================
# 多表联合查询（方案四）
# ============================================
def ask_ollama_multi_table(question):
    """使用所有表结构生成SQL（支持跨表JOIN）"""
    all_schemas = get_all_tables_schema()

    prompt = f"""You are a SQL Server expert. Convert the user's question to SQL.
You can query across multiple tables using JOIN if needed.

IMPORTANT: Output ONLY the SQL query. No explanation.

All table schemas and relationships:
{all_schemas}

User question: {question}
SQL:"""

    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'qwen2.5:7b',
                'prompt': prompt,
                'stream': False,
                'temperature': 0,
                'max_tokens': 600
            },
            timeout=90
        )
        sql = response.json()['response'].strip()
        # 提取 SQL
        match = re.search(r'(SELECT\s+.*?;)', sql, re.IGNORECASE | re.DOTALL)
        if match:
            sql = match.group(1)
        sql = re.sub(r'```sql\s*', '', sql)
        sql = re.sub(r'```\s*', '', sql)
        sql = sql.strip()
        if not sql.endswith(';'):
            sql += ';'
        return sql
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================
# 调用 Ollama 生成 SQL（带缓存）
# ============================================
@lru_cache(maxsize=50)
def cached_ask_ollama(cache_key):
    """
    带缓存的AI调用
    cache_key 包含问题和表结构，相同输入直接返回缓存结果
    """
    # 从cache_key中解析出问题和表结构
    parts = cache_key.split('|||')
    if len(parts) != 2:
        return "Error: 缓存键格式错误"
    question, table_schema = parts

    prompt = f"""You are a SQL Server expert. Convert the user's question to SQL.

IMPORTANT: Output ONLY the SQL query. No explanation.

IMPORTANT RULES:
1. Output ONLY the SQL query. No explanation.
2. ALL column names MUST be wrapped in square brackets [ ].
3. ALL table names MUST be wrapped in square brackets [ ].
4. 列名包含特殊字符（如 -、空格等）必须用 [ ] 包裹。

Example:
- Correct: SELECT [制造业-同比增长] FROM [pmi_monthly] WHERE [制造业-同比增长] > 4
- Wrong: SELECT 制造业-同比增长 FROM pmi_monthly WHERE 制造业-同比增长 > 4

Table schema:
{table_schema}

User question: {question}
SQL:"""

    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'qwen2.5:7b',
                'prompt': prompt,
                'stream': False,
                'temperature': 0,  # ← 改为0，完全确定
                'max_tokens': 500
            },
            timeout=60
        )
        sql = response.json()['response'].strip()
        # 提取 SQL
        match = re.search(r'(SELECT\s+.*?;)', sql, re.IGNORECASE | re.DOTALL)
        if match:
            sql = match.group(1)
        sql = re.sub(r'```sql\s*', '', sql)
        sql = re.sub(r'```\s*', '', sql)
        sql = sql.strip()
        if not sql.endswith(';'):
            sql += ';'
        return sql
    except Exception as e:
        return f"Error: {str(e)}"


def ask_ollama_with_retry(question, table_schema, max_retries=2):
    for attempt in range(max_retries):
        # 生成缓存键（只传1个参数）
        cache_key = generate_cache_key(question, table_schema)

        # ✅ 只传 cache_key（1个参数）
        sql = cached_ask_ollama(cache_key)

        if sql.startswith('Error'):
            print(f"第 {attempt + 1} 次尝试: AI生成失败，重试中...")
            continue

        # 尝试执行
        df, error = execute_sql(sql)
        if not error:
            return sql, df

        # 如果执行失败，重新生成（换一种表述）
        print(f"第 {attempt + 1} 次尝试: SQL执行失败，重试中...")
        question = question + "（请使用正确的列名）"

    return None, None


# ============================================
# 执行 SQL
# ============================================
def execute_sql(sql):
    try:
        clean_sql = sql.rstrip(';').strip()
        if not clean_sql.upper().startswith('SELECT'):
            return None, "⚠️ 只支持 SELECT 查询"
        df = pd.read_sql_query(clean_sql, conn)
        return df, None
    except Exception as e:
        return None, str(e)


# ============================================
# 生成缓存键
# ============================================
def generate_cache_key(question, table_schema):
    """生成唯一的缓存键"""
    content = f"{question}|||{table_schema}"
    return content  # 直接使用完整内容作为键，lru_cache会处理


# ============================================
# 主输入区域
# ============================================
# 检查是否有历史记录点击触发的问题
if 'hist_question' in st.session_state and st.session_state.hist_question:
    default_question = st.session_state.hist_question
    # 清除，避免下次刷新时重复填充
    st.session_state.hist_question = None
else:
    default_question = ""

# 检查是否有快捷查询触发
if 'quick_question' in st.session_state and st.session_state.quick_question:
    default_question = st.session_state.quick_question
    st.session_state.quick_question = None

col1, col2 = st.columns([4, 1])
with col1:
    question = st.text_input(
        "💬 输入你的问题",
        value=default_question,
        placeholder="例如：查询 CPI 月率大于 2 的数据",
        key="question_input",
        label_visibility="collapsed"
    )
with col2:
    st.write("")
    st.write("")
    submit = st.button("🔍 查询", type="primary", use_container_width=True)

# 回车触发查询
if 'question_input' in st.session_state and st.session_state.question_input:
    # 用 session_state 标记回车触发
    pass

# ============================================
# 主查询逻辑
# ============================================
if submit and question:
    # 开始计时
    start_time = time.time()
    error = None

    # ============================================
    # 智能路由：自动选择查询模式
    # ============================================

    # 1. 判断是否需要多表查询
    is_multi = need_multi_table(question)

    # 2. 如果用户手动指定了表名，优先使用用户指定的
    user_selected_table = table_name  # 来自侧边栏输入框

    if user_selected_table and user_selected_table.strip():
        # 用户手动指定了表名，使用单表模式
        use_table = user_selected_table
        query_mode = "单表查询（用户指定）"
        is_multi = False  # 强制单表
    else:
        # 用户没有指定表名，自动识别
        detected = detect_table(question)
        if detected:
            use_table = detected
            query_mode = "单表查询（自动识别）"
            # 显示自动识别的结果
            st.sidebar.success(f"🔍 自动识别: {use_table}")
        else:
            use_table = None
            query_mode = "待判断"

    # 3. 如果涉及多表或用户问题包含对比关键词，切换到多表模式
    if is_multi and not user_selected_table:
        query_mode = "多表联合查询（自动切换）"
        st.sidebar.info(f"🔗 自动切换到多表联合查询模式")

        with st.spinner("🧠 AI 正在生成跨表 SQL（可能需要20-40秒）..."):
            sql = ask_ollama_multi_table(question)

        if sql.startswith("Error"):
            st.error(f"❌ {sql}")
            st.session_state.history.append((f"❌ 多表查询失败: {question[:30]}", datetime.now().strftime("%H:%M")))
            st.stop()

        # 执行 SQL
        with st.spinner("⏳ 正在执行跨表查询..."):
            df, error = execute_sql(sql)

        if error:
            st.error(f"❌ {error}")
            st.session_state.history.append((f"❌ SQL执行失败: {question[:30]}", datetime.now().strftime("%H:%M")))
            st.stop()

        # 显示结果
        with st.expander("📝 查看生成的 SQL", expanded=True):
            st.code(sql, language="sql")

        if df is not None and not df.empty:
            st.session_state.query_count += 1
            st.session_state.df_result = df
            st.session_state.last_sql = sql
            st.session_state.last_question = question

            if not st.session_state.history or st.session_state.history[-1][0] != question:
                st.session_state.history.append((f"🔗 {question}", datetime.now().strftime("%H:%M")))

            elapsed = time.time() - start_time
            st.success(f"✅ 跨表查询成功！共 {len(df)} 行数据，耗时 {elapsed:.2f} 秒")

            if len(st.session_state.history) > 20:
                st.session_state.history = st.session_state.history[-20:]

            st.rerun()
        else:
            st.warning("⚠️ 查询返回空结果")
            st.stop()

    else:
        # ============================================
        # 单表查询模式（原有的查询逻辑）
        # ============================================

        # 如果用户没有指定表名，自动识别
        if not user_selected_table or not user_selected_table.strip():
            detected = detect_table(question)
            if detected:
                use_table = detected
                query_mode = "单表查询（自动识别）"
                st.sidebar.success(f"🔍 自动识别: {use_table}")
            else:
                # ✅ 即使识别失败，也使用第一个表作为兜底
                cursor = conn.cursor()
                cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
                first_table = cursor.fetchone()
                if first_table:
                    use_table = first_table[0]
                    st.sidebar.warning(f"⚠️ 自动识别失败，使用默认表: {use_table}")
                else:
                    st.error("❌ 数据库中没有可用的表")
                    st.stop()

        # ============================================
        # 单表查询模式
        # ============================================

        # 如果用户没有指定表名，使用自动识别的表
        if not user_selected_table or not user_selected_table.strip():
            if use_table:
                table_name = use_table
            else:
                st.error("❌ 无法自动识别表，请在侧边栏手动指定表名")
                st.stop()

        # ✅ 先获取表结构（必须在这里定义 table_schema）
        table_schema = get_table_schema_cached(table_name)

        if table_schema.startswith("Error"):
            st.error(f"❌ 获取表结构失败: {table_schema}")
            st.stop()

        # 生成缓存键并调用AI
        cache_key = generate_cache_key(question, table_schema)

        with st.spinner(f"🧠 AI 正在生成 SQL（查询表: {table_name}）..."):
            sql = cached_ask_ollama(cache_key)

        if sql.startswith("Error"):
            st.error(f"❌ {sql}")
            st.session_state.history.append((f"❌ AI错误: {question[:30]}", datetime.now().strftime("%H:%M")))
            st.stop()

        # 显示 SQL
        with st.expander("📝 查看生成的 SQL", expanded=True):
            st.code(sql, language="sql")

        # 执行查询
        with st.spinner("⏳ 正在执行查询..."):
            df, error = execute_sql(sql)

        if error:
            st.error(f"❌ {error}")
            st.session_state.history.append((f"❌ SQL错误: {question[:30]}", datetime.now().strftime("%H:%M")))
            st.stop()

        # 生成缓存键并调用AI
        cache_key = generate_cache_key(question, table_schema)

        with st.spinner(f"🧠 AI 正在生成 SQL（查询表: {table_name}）..."):
            sql = cached_ask_ollama(cache_key)

        if sql.startswith("Error"):
            st.error(f"❌ {sql}")
            st.session_state.history.append((f"❌ AI错误: {question[:30]}", datetime.now().strftime("%H:%M")))
            st.stop()

        # 显示 SQL
        with st.expander("📝 查看生成的 SQL", expanded=True):
            st.code(sql, language="sql")

        # 执行查询
        with st.spinner("⏳ 正在执行查询..."):
            df, error = execute_sql(sql)

        if error:
            st.error(f"❌ {error}")
            st.session_state.history.append((f"❌ SQL错误: {question[:30]}", datetime.now().strftime("%H:%M")))
            st.stop()

        # 查询成功
        st.session_state.query_count += 1
        st.session_state.df_result = df
        st.session_state.last_sql = sql
        st.session_state.last_question = question

        if not st.session_state.history or st.session_state.history[-1][0] != question:
            st.session_state.history.append((question, datetime.now().strftime("%H:%M")))

        elapsed = time.time() - start_time
        st.success(f"✅ 查询成功！共 {len(df)} 行数据，耗时 {elapsed:.2f} 秒")

        if len(st.session_state.history) > 20:
            st.session_state.history = st.session_state.history[-20:]

        # 显示缓存状态
        if hasattr(cached_ask_ollama, 'cache_info'):
            info = cached_ask_ollama.cache_info()
            if info.hits > 0:
                st.caption("💡 本次查询来自缓存")

        st.rerun()

# ============================================
# 结果展示区域
# ============================================
if st.session_state.df_result is not None:
    df = st.session_state.df_result

    # 判断是否有数值列用于图表
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
    text_cols = df.select_dtypes(include=['object']).columns.tolist()

    # Tab 切换
    tab1, tab2, tab3 = st.tabs(["📋 数据表格", "📊 图表可视化", "📈 数据统计"])

    with tab1:
        st.dataframe(df, use_container_width=True, height=400)

        # 导出按钮
        col1, col2, col3 = st.columns(3)
        with col1:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 导出 CSV",
                data=csv,
                file_name=f"query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col2:
            # 显示行数
            st.caption(f"共 {len(df)} 行数据")
        with col3:
            # 如果数据量不大，显示列信息
            if len(df.columns) <= 10:
                st.caption(f"列: {', '.join(df.columns.tolist())}")

    with tab2:
        if numeric_cols and (text_cols or numeric_cols):
            st.subheader("📊 数据可视化")

            # 自动选择X轴和Y轴
            if text_cols:
                default_x = text_cols[0]
            else:
                default_x = numeric_cols[0]
            default_y = numeric_cols[0] if numeric_cols else None

            x_col = st.selectbox("X 轴", df.columns.tolist(),
                                 index=df.columns.tolist().index(default_x) if default_x in df.columns else 0)
            y_col = st.selectbox("Y 轴", numeric_cols, index=0 if numeric_cols else None)
            chart_type = st.selectbox("图表类型", ["📈 折线图", "📊 柱状图", "🔵 散点图", "📦 箱线图"])

            if y_col:
                if "折线图" in chart_type:
                    fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} 趋势图")
                elif "柱状图" in chart_type:
                    fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} 柱状图")
                elif "散点图" in chart_type:
                    fig = px.scatter(df, x=x_col, y=y_col, title=f"{y_col} 散点图")
                else:
                    fig = px.box(df, x=x_col, y=y_col, title=f"{y_col} 箱线图")

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("💡 没有数值列，无法生成图表")
        else:
            st.info("💡 数据中没有数值列或列数不足，无法生成图表")

    with tab3:
        st.subheader("📈 数据统计摘要")

        if numeric_cols:
            st.dataframe(df[numeric_cols].describe(), use_container_width=True)
        else:
            st.info("💡 没有数值列，无法生成统计信息")

        # 显示数据基本信息
        with st.expander("📋 数据信息"):
            st.write(f"**行数**: {len(df)}")
            st.write(f"**列数**: {len(df.columns)}")
            st.write(f"**列名**: {', '.join(df.columns.tolist())}")
            if not df.empty:
                st.write(f"**内存占用**: {df.memory_usage(deep=True).sum() / 1024:.2f} KB")

# ============================================
# 底部
# ============================================
st.divider()
st.caption("🤖 SQL AI 智能查询助手 | 技术栈: Qwen2.5-7B + Streamlit + SQL Server | 数据来源: 国家统计局")

# 显示缓存信息（调试用，可注释掉）
# st.caption(f"缓存状态: {cached_ask_ollama.cache_info()}")
