"""
SQL AI 智能查询助手 - 完整版
功能：自然语言生成SQL、自动识别表、多表联合查询、数据可视化
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

# 自定义 CSS
st.markdown("""
<style>
.stTextInput > div > div > input { font-size: 16px; }
.main-header { font-size: 2.5rem; font-weight: 700; color: #1f77b4; margin-bottom: 0.5rem; }
.sub-header { font-size: 1rem; color: #666; margin-bottom: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ============================================
# 初始化 Session State
# ============================================
if 'current_db' not in st.session_state:
    st.session_state.current_db = "NBS"
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
if 'last_query_mode' not in st.session_state:
    st.session_state.last_query_mode = ""


# ============================================
# 数据库连接函数（唯一定义）
# ============================================
def get_connection(db_name=None):
    """动态获取数据库连接"""
    if db_name is None:
        db_name = st.session_state.get('current_db', 'NBS')
    conn_str = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=localhost;"
        f"Database={db_name};"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)

# 初始化连接（只在启动时使用）
try:
    conn = get_connection(st.session_state.current_db)
except Exception as e:
    st.error(f"❌ 数据库连接失败: {e}")
    st.stop()

# ============================================
# 标题
# ============================================
st.markdown('<p class="main-header">🤖 SQL AI 智能查询助手</p >', unsafe_allow_html=True)
st.markdown('<p class="sub-header">基于 Qwen2.5-7B 本地部署 | 支持多表查询 | 自动可视化</p >', unsafe_allow_html=True)

# ============================================
# 侧边栏
# ============================================
with st.sidebar:
    st.header("⚙️ 数据库配置")

    # 数据库切换
    db_options = ["NBS", "Northwind"]
    current_db = st.session_state.get('current_db', 'NBS')
    default_index = db_options.index(current_db) if current_db in db_options else 0

    database = st.selectbox(
        "选择数据库",
        options=db_options,
        index=default_index,
        key="db_select"
    )

    if database != st.session_state.get('current_db'):
        st.session_state.current_db = database
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

    st.caption(f"当前连接: {database}")

    table_name = st.text_input(
        "查询表名（留空自动识别）",
        value="",
        key="table_name",
        placeholder="留空则AI自动识别表",
        help="输入表名则强制使用该表，留空则AI自动识别"
    )

    # 快捷查询
    st.divider()
    st.markdown("### ⚡ 快捷查询")

    quick_queries = [
        ("📈 CPI月率 > 2", "查询CPI月率大于2的数据"),
        ("📊 GDP年度数据", "查询GDP年度数据"),
        ("💰 M2货币供应量", "查询M2货币供应量"),
        ("📉 PMI指数", "查询PMI月度数据"),
        ("🏦 LPR利率", "查询LPR利率"),
        ("📊 制造业同比增长", "查询制造业-同比增长大于4的月份"),
        ("👥 客户订单数", "查询每个客户的订单数量")
    ]

    col1, col2 = st.columns(2)
    for i, (label, q) in enumerate(quick_queries):
        target_col = col1 if i % 2 == 0 else col2
        if target_col.button(label, use_container_width=True, key=f"quick_{i}"):
            st.session_state.quick_question = q

    # 查询历史
    st.divider()
    st.markdown("### 📜 查询历史")
    st.caption(f"📊 共 {len(st.session_state.history)} 条记录")

    if st.session_state.history:
        for idx, (q, t) in enumerate(st.session_state.history[-10:]):
            icon = "❌" if q.startswith("❌") else "🔗" if q.startswith("🔗") else "✅"
            display_q = q[2:] if q.startswith(("❌", "🔗")) else q
            display_q = display_q[:30] + "..." if len(display_q) > 30 else display_q

            if st.button(f"{icon} {t} {display_q}", key=f"hist_{idx}_{t}", use_container_width=True):
                st.session_state.hist_question = q
    else:
        st.caption("暂无查询历史，开始查询吧！")

    # 查询模式
    st.divider()
    st.markdown("### 🔍 查询模式")
    st.caption(f"📌 上次查询: {st.session_state.last_query_mode if st.session_state.last_query_mode else '尚未查询'}")
    st.caption("💡 不指定表名时自动识别")
    st.caption("💡 包含'对比'/'和'等词自动切换多表")

    # 数据库状态
    st.divider()
    st.markdown("### 📊 数据库状态")
    st.caption(f"🗄️ 数据库: {database}")
    st.caption(f"📋 当前表: {table_name if table_name else '自动识别'}")
    st.caption(f"🔢 总查询次数: {st.session_state.query_count}")

    try:
        test_conn = get_connection(st.session_state.current_db)
        test_conn.close()
        st.success("✅ 数据库连接正常")
    except:
        st.error("❌ 数据库连接断开")


# ============================================
# 获取表结构（带缓存）
# ============================================
@st.cache_data(ttl=3600)
def get_table_schema_cached(table_name):
    """获取表结构，带缓存，并附加示例数据帮助AI理解"""
    conn_local = None
    try:
        conn_local = get_connection(st.session_state.current_db)
        cursor = conn_local.cursor()
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
        """, (table_name,))
        cols = cursor.fetchall()

        if not cols:
            return f"Table: {table_name} (结构未知，请检查表名是否正确)"

        schema = f"Table: {table_name}\n"
        schema += "字段说明:\n"
        for col_name, data_type in cols:
            schema += f"  - {col_name}: {data_type}\n"

        try:
            sample_df = pd.read_sql_query(f"SELECT TOP 3 * FROM {table_name}", conn_local)
            if not sample_df.empty:
                schema += "\n示例数据 (前3行):\n"
                schema += sample_df.to_string(index=False)
        except Exception as e:
            schema += f"\n(无法获取示例数据: {e})"

        return schema
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        if conn_local:
            try:
                conn_local.close()
            except:
                pass


# ============================================
# 获取所有表结构（用于多表查询）
# ============================================
@st.cache_data(ttl=3600)
def get_all_tables_schema():
    """获取数据库中所有用户表的结构（超清晰格式）"""
    conn_local = None
    try:
        conn_local = get_connection(st.session_state.current_db)
        cursor = conn_local.cursor()

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
                SELECT COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
            """, (table_name,))
            cols = cursor.fetchall()

            # ✅ 修正：使用正确的方括号
            all_schema += f"\n=== 表名: [{table_name}] ===\n"
            all_schema += "列名: "
            col_list = []
            for col in cols:
                col_list.append(f"[{col[0]}]")  # ✅ 这里用 ] 不是 }
            all_schema += ", ".join(col_list)
            all_schema += "\n"

        return all_schema

    except Exception as e:
        return f"Error getting schema: {e}"
    finally:
        if conn_local:
            try:
                conn_local.close()
            except:
                pass

# ============================================
# 自动识别表名
# ============================================
def detect_table(question):
    """根据用户问题自动识别应该查询哪张表"""
    conn_local = None
    try:
        conn_local = get_connection(st.session_state.current_db)
        cursor = conn_local.cursor()
        cursor.execute("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE='BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        tables = [row[0] for row in cursor.fetchall()]

        if not tables:
            return None

        tables_str = ", ".join(tables)

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

        # 精确匹配
        for t in tables:
            if t == detected:
                return t

        # 忽略大小写匹配
        for t in tables:
            if t.lower() == detected.lower():
                return t

        # 包含匹配
        for t in tables:
            t_clean = t.replace(" ", "")
            detected_clean = detected.replace(" ", "")
            if detected_clean.lower() in t_clean.lower() or t_clean.lower() in detected_clean.lower():
                return t

        # 关键词映射
        keyword_map = {
            '客户': 'Customers', '顾客': 'Customers',
            '订单': 'Orders', '产品': 'Products', '商品': 'Products',
            '员工': 'Employees', '供应商': 'Suppliers',
            '类别': 'Categories', '分类': 'Categories',
            '物流': 'Shippers', '运货': 'Shippers'
        }
        for keyword, table in keyword_map.items():
            if keyword in question and table in tables:
                return table

        return tables[0] if tables else None

    except Exception as e:
        print(f"detect_table 错误: {e}")
        return None
    finally:
        if conn_local:
            try:
                conn_local.close()
            except:
                pass


# ============================================
# 判断是否需要多表联合查询
# ============================================
def need_multi_table(question):
    """判断问题是否需要多表联合查询"""
    keywords = ['对比', '比较', '和', '与', 'VS', 'vs', '同时', '分别',
                'GDP和CPI', '各指标', '多个指标', 'GDP与CPI', '跨表',
                '每个客户', '每位客户', '所有客户', '订单数量', '总订单',
                '每个类别', '每个产品', '每个员工', '每个供应商']  # ✅ 添加 "每个类别"
    for kw in keywords:
        if kw in question:
            return True

    # 检查是否提到多个表名
    table_names = ['cpi', 'ppi', 'pmi', 'gdp', 'm2', 'lpr', 'fdi',
                   'customers', 'orders', 'products', 'employees']
    count = 0
    for name in table_names:
        if name.lower() in question.lower():
            count += 1
    if count >= 2:
        return True

    return False


# ============================================
# 调用 Ollama 生成 SQL（带缓存）
# ============================================
@lru_cache(maxsize=50)
def cached_ask_ollama(cache_key):
    """带缓存的AI调用"""
    parts = cache_key.split('|||')
    if len(parts) != 2:
        return "Error: 缓存键格式错误"
    question, table_schema = parts

    prompt = f"""You are a SQL Server expert. Convert the user's question to SQL.

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
                'temperature': 0,
                'max_tokens': 500
            },
            timeout=60
        )
        sql = response.json()['response'].strip()
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
# 多表联合查询
# ============================================
def ask_ollama_multi_table(question):
    all_schemas = get_all_tables_schema()

    prompt = f"""You are a SQL Server expert. Convert the user's question to SQL.

【最重要规则 - 必须严格遵守】
1. 只输出 SQL 语句，不要任何解释。
2. 【禁止编造】所有列名和表名必须**严格复制**下方【所有表结构】中提供的名称。
3. 【格式要求】使用方括号 [ ] 包裹所有列名和表名，例如：[Employees].[EmployeeID]。
4. 【JOIN规则】如果查询涉及多表，请使用下方【所有表结构】中的关联字段进行 JOIN。
5. 【聚合规则】使用 AS 定义别名时，必须写完整的别名，如 AS TotalAmount。

【所有表结构 - 只从这里复制名称】
{all_schemas}

【用户问题】
{question}

【SQL】"""

    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'qwen2.5:7b',
                'prompt': prompt,
                'stream': False,
                'temperature': 0,
                'max_tokens': 500
            },
            timeout=60
        )
        sql = response.json()['response'].strip()
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
# 执行 SQL
# ============================================
def execute_sql(sql):
    try:
        clean_sql = sql.rstrip(';').strip()
        if not clean_sql.upper().startswith('SELECT'):
            return None, "⚠️ 只支持 SELECT 查询"
        conn_local = get_connection(st.session_state.current_db)
        df = pd.read_sql_query(clean_sql, conn_local)
        conn_local.close()
        return df, None
    except Exception as e:
        return None, str(e)


# ============================================
# 生成缓存键
# ============================================
def generate_cache_key(question, table_schema):
    content = f"{question}|||{table_schema}"
    return content


# ============================================
# 主输入区域
# ============================================
if 'hist_question' in st.session_state and st.session_state.hist_question:
    default_question = st.session_state.hist_question
    st.session_state.hist_question = None
else:
    default_question = ""

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

# ============================================
# 主查询逻辑
# ============================================
if submit and question:
    start_time = time.time()

    # 智能路由
    is_multi = need_multi_table(question)
    user_selected_table = table_name

    if user_selected_table and user_selected_table.strip():
        use_table = user_selected_table
        query_mode = "单表查询（用户指定）"
        is_multi = False
    else:
        detected = detect_table(question)
        if detected:
            use_table = detected
            query_mode = "单表查询（自动识别）"
            st.sidebar.success(f"🔍 自动识别: {use_table}")
        else:
            use_table = None
            query_mode = "待判断"

    # 多表查询
    if is_multi and not user_selected_table:
        query_mode = "多表联合查询（自动切换）"
        st.session_state.last_query_mode = query_mode
        st.sidebar.info(f"🔗 自动切换到多表联合查询模式")

        with st.spinner("🧠 AI 正在生成跨表 SQL（可能需要20-40秒）..."):
            sql = ask_ollama_multi_table(question)

        if sql.startswith("Error"):
            st.error(f"❌ {sql}")
            st.session_state.history.append((f"❌ 多表查询失败: {question[:30]}", datetime.now().strftime("%H:%M")))
            st.stop()

        with st.spinner("⏳ 正在执行跨表查询..."):
            df, error = execute_sql(sql)

        if error:
            st.error(f"❌ {error}")
            st.session_state.history.append((f"❌ SQL执行失败: {question[:30]}", datetime.now().strftime("%H:%M")))
            st.stop()

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
        # 单表查询
        if not user_selected_table or not user_selected_table.strip():
            if use_table:
                table_name = use_table
            else:
                st.error("❌ 无法自动识别表，请在侧边栏手动指定表名")
                st.stop()

        table_schema = get_table_schema_cached(table_name)

        if table_schema.startswith("Error"):
            st.error(f"❌ 获取表结构失败: {table_schema}")
            st.stop()

        cache_key = generate_cache_key(question, table_schema)

        with st.spinner(f"🧠 AI 正在生成 SQL（查询表: {table_name}）..."):
            sql = cached_ask_ollama(cache_key)

        if sql.startswith("Error"):
            st.error(f"❌ {sql}")
            st.session_state.history.append((f"❌ AI错误: {question[:30]}", datetime.now().strftime("%H:%M")))
            st.stop()

        with st.expander("📝 查看生成的 SQL", expanded=True):
            st.code(sql, language="sql")

        with st.spinner("⏳ 正在执行查询..."):
            df, error = execute_sql(sql)

        if error:
            st.error(f"❌ {error}")
            st.session_state.history.append((f"❌ SQL错误: {question[:30]}", datetime.now().strftime("%H:%M")))
            st.stop()

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

        st.rerun()

# ============================================
# 结果展示区域
# ============================================
if st.session_state.df_result is not None:
    df = st.session_state.df_result

    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
    text_cols = df.select_dtypes(include=['object']).columns.tolist()

    tab1, tab2, tab3 = st.tabs(["📋 数据表格", "📊 图表可视化", "📈 数据统计"])

    with tab1:
        st.dataframe(df, use_container_width=True, height=400)

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
            st.caption(f"共 {len(df)} 行数据")
        with col3:
            if len(df.columns) <= 10:
                st.caption(f"列: {', '.join(df.columns.tolist())}")

    with tab2:
        if numeric_cols and (text_cols or numeric_cols):
            st.subheader("📊 数据可视化")

            if text_cols:
                default_x = text_cols[0]
            else:
                default_x = numeric_cols[0]

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