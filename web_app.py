import streamlit as st
import pyodbc
import pandas as pd
import requests
import re
import plotly.express as px
from datetime import datetime

# ============================================
# 页面配置
# ============================================
st.set_page_config(page_title="SQL AI 助手", layout="wide")
st.title("🤖 SQL AI 智能查询助手")
st.caption(f"基于 Qwen2.5-7B 本地部署 | 数据来源：国家统计局 NBS 数据库")

# ============================================
# 侧边栏：数据库连接信息
# ============================================
with st.sidebar:
    st.header("⚙️ 数据库配置")
    database = st.text_input("数据库名", value="NBS")
    table_name = st.text_input("查询表名", value="urban_CPI")

    st.divider()
    st.markdown("### 📊 快捷查询")
    if st.button("📈 查看 CPI 趋势图"):
        st.session_state.quick_query = "SELECT period, cpi_rate FROM urban_CPI ORDER BY period"

    st.divider()
    st.markdown("### 📌 使用说明")
    st.markdown("""
    1. 输入自然语言问题
    2. AI 自动生成 SQL
    3. 执行并展示结果
    4. 支持图表可视化
    """)


# ============================================
# 连接数据库
# ============================================
@st.cache_resource
def get_connection():
    conn_str = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=localhost;"
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
# 获取表结构（自动）
# ============================================
def get_table_schema(table_name):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = ?
    """, (table_name,))
    cols = cursor.fetchall()
    if not cols:
        return f"Table: {table_name} (结构未知，请检查表名是否正确)"
    schema = f"Table: {table_name}\n"
    for col_name, data_type in cols:
        schema += f"  - {col_name}: {data_type}\n"
    return schema


# ============================================
# 调用 Ollama 生成 SQL
# ============================================
def ask_ollama(question, table_schema):
    prompt = f"""You are a SQL Server expert. Convert the user's question to SQL.

IMPORTANT: Output ONLY the SQL query. No explanation.

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
                'temperature': 0.1,
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
# 主界面
# ============================================
# 输入区域
col1, col2 = st.columns([4, 1])
with col1:
    question = st.text_input(
        "💬 输入你的问题",
        placeholder="例如：查询 CPI 月率大于 2 的数据",
        key="question_input"
    )
with col2:
    st.write("")
    st.write("")
    submit = st.button("🔍 查询", type="primary", use_container_width=True)

# 快速查询处理
if 'quick_query' in st.session_state and st.session_state.quick_query:
    sql = st.session_state.quick_query
    st.session_state.quick_query = None
    with st.spinner("⏳ 执行查询..."):
        df, error = execute_sql(sql)
        if error:
            st.error(f"❌ {error}")
        else:
            st.success(f"✅ 查询成功，共 {len(df)} 行")
            st.session_state.df = df
            st.session_state.sql = sql

# 主查询逻辑
if submit and question:
    table_schema = get_table_schema(table_name)

    with st.spinner("🧠 AI 正在生成 SQL..."):
        sql = ask_ollama(question, table_schema)

    if sql.startswith("Error"):
        st.error(f"❌ {sql}")
    else:
        st.code(sql, language="sql")

        with st.spinner("⏳ 执行查询..."):
            df, error = execute_sql(sql)

        if error:
            st.error(f"❌ {error}")
        else:
            st.success(f"✅ 查询成功，共 {len(df)} 行")
            st.session_state.df = df
            st.session_state.sql = sql

# ============================================
# 结果展示区域
# ============================================
if 'df' in st.session_state and st.session_state.df is not None:
    df = st.session_state.df

    # Tab 切换：表格 / 图表
    tab1, tab2 = st.tabs(["📋 数据表格", "📊 图表可视化"])

    with tab1:
        st.dataframe(df, use_container_width=True)

        # 导出按钮
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 导出 CSV",
            data=csv,
            file_name=f"query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

    with tab2:
        if len(df.columns) >= 2:
            # 自动选择数值列作为 y
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
            text_cols = df.select_dtypes(include=['object']).columns.tolist()

            if numeric_cols and text_cols:
                x_col = st.selectbox("X 轴", text_cols + numeric_cols)
                y_col = st.selectbox("Y 轴", numeric_cols)
                chart_type = st.selectbox("图表类型", ["折线图", "柱状图", "散点图"])

                if chart_type == "折线图":
                    fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} 趋势图")
                elif chart_type == "柱状图":
                    fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} 柱状图")
                else:
                    fig = px.scatter(df, x=x_col, y=y_col, title=f"{y_col} 散点图")

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("💡 数据中没有可用的数值列，无法生成图表")
        else:
            st.info("💡 数据列数不足，无法生成图表")

# ============================================
# 底部
# ============================================
st.divider()
st.caption("Powered by Qwen2.5-7B | Streamlit | SQL Server")