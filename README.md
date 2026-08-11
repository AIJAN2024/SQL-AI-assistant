🤖 SQL AI 智能查询助手

基于本地大模型的自然语言数据查询系统 | 让不懂SQL的人也能轻松查数据

https://img.shields.io/badge/Python-3.9+-blue.svg
https://img.shields.io/badge/Streamlit-1.28+-red.svg
https://img.shields.io/badge/Ollama-0.3+-green.svg
https://img.shields.io/badge/SQL%20Server-2019+-orange.svg

📖 项目简介

SQL AI 智能查询助手 是一个基于本地大模型的自然语言数据查询系统。用户只需用中文或英文输入问题，系统自动生成 SQL 并执行，返回查询结果。

核心价值：

· 🔓 降低门槛：业务人员无需掌握SQL即可查询数据
· 🔒 数据安全：大模型本地部署，数据不外传
· 🚀 即问即答：自然语言→SQL→结果，全自动流程
· 🧠 智能识别：自动识别表名，支持多表联合查询

🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户界面（前端）                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │           Streamlit Web 界面                              │  │
│  │  - 自然语言输入  - 自动识别表  - 多表联合查询  - 可视化  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        应用逻辑层（后端）                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Python 业务逻辑                              │  │
│  │  - Prompt工程  - SQL生成与执行  - 表结构自动识别         │  │
│  │  - 多表路由  - 结果缓存  - 异常重试                      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         数据层（后端）                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │       SQL Server 数据库              Ollama + Qwen2.5    │  │
│  │  - 7张宏观经济表  - 14张业务测试表    - 本地大模型部署   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

✨ 核心功能

功能 说明
自然语言生成SQL 输入中文问题，AI自动生成并执行SQL
自动识别表名 无需手动指定表名，系统根据问题自动选择最相关的表
多表联合查询 检测到"对比"、"和"等关键词时，自动切换到多表JOIN模式
四表 JOIN 支持 支持 Categories → Products → Order Details → Orders 等多层关联
数据可视化 查询结果自动生成折线图、柱状图、散点图
数据导出 一键导出CSV格式，方便二次分析
查询历史 自动记录查询历史，点击即可复用
快捷查询 预设常用查询按钮，一键执行
多数据库支持 支持 NBS、Northwind 等多套数据库切换

📊 数据资产

Northwind 数据库（业务测试数据）

Northwind 是微软经典的示例数据库，模拟了一家贸易公司的业务运营，包含 14 张表：

| 表名 | 说明 | 关键字段 |
|------|------|---------|
| `Customers` | 客户信息 | CustomerID, CompanyName, Country |
| `Employees` | 员工信息 | EmployeeID, FirstName, LastName |
| `Orders` | 订单主表 | OrderID, CustomerID, EmployeeID, OrderDate |
| `Order Details` | 订单明细 | OrderID, ProductID, UnitPrice, Quantity |
| `Products` | 产品信息 | ProductID, ProductName, CategoryID, UnitPrice |
| `Categories` | 产品类别 | CategoryID, CategoryName |
| `Suppliers` | 供应商信息 | SupplierID, CompanyName |
| `Shippers` | 物流公司 | ShipperID, CompanyName |

🚀 快速开始

1️⃣ 环境要求

· Python 3.9+
· SQL Server 2019+
· Ollama
· 8GB+ 内存

2️⃣ 安装依赖

```bash
# 克隆项目
git clone https://github.com/AIJAN2024/SQL-AI-assistant.git
cd SQL-AI-assistant

# 安装Python依赖
pip install -r requirements.txt
```

3️⃣ 下载模型

```bash
# 启动Ollama服务
ollama serve

# 下载Qwen2.5模型
ollama run qwen2.5:7b
```

4️⃣ 配置数据库

在 web_app.py 中修改连接信息：

```python
conn_str = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=localhost;"        # 改成你的服务器地址
    "Database=Northwind;"            # 改成你的数据库名
    "Trusted_Connection=yes;"
)
```

5️⃣ 启动应用

```bash
streamlit run web_app_2.py
```

浏览器自动打开 http://localhost:8501

## 🎯 使用示例

以下示例均基于 Northwind 数据库，展示了从简单到复杂的查询能力。

示例1：单表查询

用户输入：
```

查询所有客户的公司名称和所在国家
```

AI 生成的 SQL：
```sql
SELECT [CompanyName], [Country] FROM [Customers]
```

示例2：两表 JOIN

用户输入：

```
查询每个客户的订单数量
```

AI 生成的 SQL：

```sql
SELECT 
    [Customers].[CompanyName], 
    COUNT([Orders].[OrderID]) AS OrderCount
FROM [Customers]
LEFT JOIN [Orders] ON [Customers].[CustomerID] = [Orders].[CustomerID]
GROUP BY [Customers].[CompanyName]
ORDER BY OrderCount DESC
```

示例3：三表 JOIN

用户输入：

```
查询每个客户的订单总金额，同时显示员工的名字
```

AI 生成的 SQL：

```sql
SELECT 
    [Customers].[CompanyName],
    [Employees].[FirstName] + ' ' + [Employees].[LastName] AS EmployeeName,
    SUM([Order Details].[UnitPrice] * [Order Details].[Quantity]) AS TotalAmount
FROM [Customers]
INNER JOIN [Orders] ON [Customers].[CustomerID] = [Orders].[CustomerID]
INNER JOIN [Employees] ON [Orders].[EmployeeID] = [Employees].[EmployeeID]
INNER JOIN [Order Details] ON [Orders].[OrderID] = [Order Details].[OrderID]
GROUP BY [Customers].[CompanyName], [Employees].[FirstName], [Employees].[LastName]
ORDER BY TotalAmount DESC
```

示例4：四表 JOIN

用户输入：

```
统计每个产品类别的销售总额
```

AI 生成的 SQL：

```sql
SELECT 
    [Categories].[CategoryName],
    SUM([Order Details].[UnitPrice] * [Order Details].[Quantity]) AS TotalSales
FROM [Categories]
INNER JOIN [Products] ON [Categories].[CategoryID] = [Products].[CategoryID]
INNER JOIN [Order Details] ON [Products].[ProductID] = [Order Details].[ProductID]
INNER JOIN [Orders] ON [Order Details].[OrderID] = [Orders].[OrderID]
GROUP BY [Categories].[CategoryName]
ORDER BY TotalSales DESC
```

示例5：复杂聚合 + 条件过滤

用户输入：

```
统计每个客户购买的不同产品数量，只显示购买超过5种的客户
```

AI 生成的 SQL：

```sql
SELECT 
    [Customers].[CustomerID],
    [Customers].[CompanyName],
    COUNT(DISTINCT [Order Details].[ProductID]) AS ProductCount
FROM [Customers]
INNER JOIN [Orders] ON [Customers].[CustomerID] = [Orders].[CustomerID]
INNER JOIN [Order Details] ON [Orders].[OrderID] = [Order Details].[OrderID]
GROUP BY [Customers].[CustomerID], [Customers].[CompanyName]
HAVING COUNT(DISTINCT [Order Details].[ProductID]) > 5
ORDER BY ProductCount DESC
```

🛠️ 技术栈

分类 技术
前端 Streamlit
后端 Python 3.9+
AI模型 Qwen2.5-7B (Ollama)
数据库 SQL Server
数据采集 akshare
可视化 Plotly
数据操作 Pandas, pyodbc
业务知识库 business_knowledge.py

📝 更新日志

v4.0 (2026-08-11)
- ✨ 新增业务术语知识库（解决语义歧义问题）
- ✨ 新增一键启动（start.bat + launcher.py）
- ✨ 新增查询历史记录
- 📝 统一使用 Northwind 数据库

v3.0 (2026-08-10)

· ✨ 新增多表联合查询（自动切换）
· ✨ 新增 Northwind 测试数据库支持
· ✨ 新增四表 JOIN 支持
· ✨ 新增自动识别表名功能
· ✨ 新增查询历史记录
· 🐛 修复 AS 语法错误
· 🐛 修复列名识别问题
· 🐛 修复数据库连接管理

v2.0 (2026-08-09)

· ✨ 新增Web界面（Streamlit）
· ✨ 新增数据可视化（图表）
· ✨ 新增数据导出CSV
· ✨ 新增快捷查询

v1.0 (2026-08-01)

· 🎉 初始版本
· ✅ 基础自然语言生成SQL
· ✅ 支持SQL Server
· ✅ 宏观经济数据采集（7张表）

📁 项目结构

```

SQL-AI-assistant/
├── web_app_2.py                # 主程序（最新版本）
├── business_knowledge.py       # 业务术语知识库
├── requirements.txt            # 依赖清单
├── start.bat                   # Windows 一键启动
├── launcher.py                 # 跨平台一键启动
├── README.md                   # 项目文档
├── .gitignore                  # Git忽略文件
└── data/
└── northwind.sql           # Northwind数据库脚本

```

⚠️ 注意事项

1. Ollama服务：使用前确保 ollama serve 正在运行
2. 内存要求：Qwen2.5-7B约占用4-5GB内存
3. 数据库权限：建议使用只读账号，避免误操作
4. 网络环境：首次下载模型需要稳定网络

🤝 贡献

欢迎提出建议和问题，也欢迎提交PR。

📄 许可证

MIT License

📧 联系方式

· GitHub：AIJAN2024
· 项目地址：https://github.com/AIJAN2024/SQL-AI-assistant

🙏 致谢

· Qwen - 通义千问大模型
· Ollama - 本地模型部署框架
· Streamlit - Web应用框架
· akshare - 财经数据接口库

⭐ Star History

如果你觉得这个项目对你有帮助，欢迎点个 Star ⭐

---

🎉 项目持续迭代中，欢迎关注！
