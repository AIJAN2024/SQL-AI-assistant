"""
业务术语知识库
把业务术语映射为：表名、列名、关联关系、计算公式
"""

BUSINESS_TERMS = {
    # ===== 销售相关 =====
    "销售总额": {
        "tables": ["Categories", "Products", "Order Details", "Orders"],
        "formula": "SUM([Order Details].[UnitPrice] * [Order Details].[Quantity])",
        "join_path": "Categories → Products → Order Details → Orders",
        "group_by": "[Categories].[CategoryName]"
    },
    "销售额": {
        "tables": ["Employees", "Orders", "Order Details"],
        "formula": "SUM([Order Details].[UnitPrice] * [Order Details].[Quantity])",
        "join_path": "Employees → Orders → Order Details",
        "group_by": "[Employees].[EmployeeID], [Employees].[FirstName], [Employees].[LastName]",
        "alias": "TotalSales"
    },
    "总销售额": {
        "tables": ["Employees", "Orders", "Order Details"],
        "formula": "SUM([Order Details].[UnitPrice] * [Order Details].[Quantity])",
        "join_path": "Employees → Orders → Order Details",
        "group_by": "[Employees].[EmployeeID], [Employees].[FirstName], [Employees].[LastName]",
        "alias": "TotalSales"
    },
    "订单金额": {
        "tables": ["Order Details"],
        "formula": "[UnitPrice] * [Quantity]",
        "alias": "OrderAmount"
    },
    "总订单金额": {
        "tables": ["Order Details"],
        "formula": "SUM([Order Details].[UnitPrice] * [Order Details].[Quantity])",
        "alias": "TotalAmount"
    },
    "金额区间": {
        "tables": ["Customers", "Orders", "Order Details"],
        "formula": """
   SELECT 
       [Customers].[CustomerID],
       [Customers].[CompanyName],
       SUM([Order Details].[UnitPrice] * [Order Details].[Quantity]) AS TotalAmount,
       CASE 
           WHEN SUM([Order Details].[UnitPrice] * [Order Details].[Quantity]) <= 1000 THEN '0-1000'
           WHEN SUM([Order Details].[UnitPrice] * [Order Details].[Quantity]) <= 5000 THEN '1000-5000'
           ELSE '5000+'
       END AS AmountRange
   FROM [Customers]
   INNER JOIN [Orders] ON [Customers].[CustomerID] = [Orders].[CustomerID]
   INNER JOIN [Order Details] ON [Orders].[OrderID] = [Order Details].[OrderID]
   GROUP BY [Customers].[CustomerID], [Customers].[CompanyName]
   """
    },
    "多种产品客户": {
        "tables": ["Customers", "Orders", "Order Details"],
        "sql": """
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
    """
    },

    # ===== 客户相关 =====
    "客户": {
        "table": "Customers",
        "key": "CustomerID",
        "display": "CompanyName"
    },
    "每个客户": {
        "table": "Customers",
        "key": "CustomerID",
        "display": "CompanyName",
        "aggregate": "GROUP BY [Customers].[CustomerID], [Customers].[CompanyName]"
    },

    # ===== 订单相关 =====
    "订单": {
        "table": "Orders",
        "key": "OrderID",
        "display": "OrderID"
    },
    "没有订单": {
        "tables": ["Employees", "Orders"],
        "join": "LEFT JOIN [Orders] ON [Employees].[EmployeeID] = [Orders].[EmployeeID]",
        "condition": "WHERE [Orders].[OrderID] IS NULL",
        "select": "[Employees].[EmployeeID], [Employees].[FirstName], [Employees].[LastName]"
    },

    # ===== 员工相关 =====
    "员工": {
        "table": "Employees",
        "key": "EmployeeID",
        "display": "[FirstName] + ' ' + [LastName]"
    },
    "每个员工": {
        "table": "Employees",
        "key": "EmployeeID",
        "display": "[FirstName] + ' ' + [LastName]",
        "aggregate": "GROUP BY [Employees].[EmployeeID], [Employees].[FirstName], [Employees].[LastName]"
    },
    "员工订单金额差值": {
        "tables": ["Employees", "Orders", "Order Details"],
        "sql": """
    WITH EmployeeSales AS (
        SELECT 
            [Employees].[EmployeeID],
            [Employees].[FirstName] + ' ' + [Employees].[LastName] AS EmployeeName,
            SUM([Order Details].[UnitPrice] * [Order Details].[Quantity]) AS TotalAmount
        FROM [Employees]
        INNER JOIN [Orders] ON [Employees].[EmployeeID] = [Orders].[EmployeeID]
        INNER JOIN [Order Details] ON [Orders].[OrderID] = [Order Details].[OrderID]
        GROUP BY [Employees].[EmployeeID], [Employees].[FirstName], [Employees].[LastName]
    )
    SELECT 
        EmployeeName,
        TotalAmount,
        ROUND((SELECT AVG(TotalAmount) FROM EmployeeSales), 2) AS AvgAmount,
        ROUND(TotalAmount - (SELECT AVG(TotalAmount) FROM EmployeeSales), 2) AS DiffFromAvg
    FROM EmployeeSales
    ORDER BY TotalAmount DESC
    """
    },

    # ===== 产品相关 =====
    "产品": {
        "table": "Products",
        "key": "ProductID",
        "display": "ProductName"
    },
    "产品数量": {
        "tables": ["Categories", "Products"],
        "select": "COUNT([Products].[ProductID])",
        "join": "[Categories].[CategoryID] = [Products].[CategoryID]",
        "group_by": "[Categories].[CategoryID], [Categories].[CategoryName]",
        "alias": "ProductCount"
    },
    "产品ID": {
        "table": "Products",
        "key": "ProductID",
        "display": "ProductID"
    },

    # ===== 类别相关 =====
    "类别": {
        "table": "Categories",
        "key": "CategoryID",
        "display": "CategoryName"
    },
    "每个类别": {
        "tables": ["Categories", "Products"],
        "select": "COUNT([Products].[ProductID])",
        "join": "[Categories].[CategoryID] = [Products].[CategoryID]",
        "group_by": "[Categories].[CategoryID], [Categories].[CategoryName]",
        "alias": "ProductCount"
    },

    # ===== 价格相关 =====
    "平均单价": {
        "tables": ["Products"],
        "formula": "AVG([Products].[UnitPrice])",
        "alias": "AvgPrice"
    },
    "最高单价": {
        "tables": ["Products"],
        "formula": "MAX([Products].[UnitPrice])",
        "alias": "MaxPrice"
    },
    "最低单价": {
        "tables": ["Products"],
        "formula": "MIN([Products].[UnitPrice])",
        "alias": "MinPrice"
    },

    # ===== 供应商相关 =====
    "供应商": {
        "table": "Suppliers",
        "key": "SupplierID",
        "display": "CompanyName"
    },
    "每个供应商": {
        "table": "Suppliers",
        "key": "SupplierID",
        "display": "CompanyName",
        "aggregate": "GROUP BY [Suppliers].[SupplierID], [Suppliers].[CompanyName]"
    },

    # ===== 物流相关 =====
    "物流": {
        "table": "Shippers",
        "key": "ShipperID",
        "display": "CompanyName"
    },
    "每个物流": {
        "table": "Shippers",
        "key": "ShipperID",
        "display": "CompanyName",
        "aggregate": "GROUP BY [Shippers].[ShipperID], [Shippers].[CompanyName]"
    },
    "客户和供应商": {
        "tables": ["Customers", "Suppliers"],
        "sql": """
    SELECT '客户' AS Type, [CompanyName] FROM [Customers]
    UNION ALL
    SELECT '供应商' AS Type, [CompanyName] FROM [Suppliers]
    """
    },
    "综合统计": {
        "tables": ["Customers", "Orders", "Products", "Employees"],
        "sql": """
    SELECT 
        (SELECT COUNT(*) FROM [Customers]) AS CustomerCount,
        (SELECT COUNT(*) FROM [Orders]) AS OrderCount,
        (SELECT COUNT(*) FROM [Products]) AS ProductCount,
        (SELECT COUNT(*) FROM [Employees]) AS EmployeeCount
    """
    }
}


# ===== 表关联关系 =====
TABLE_JOINS = {
    "Customers → Orders": "[Customers].[CustomerID] = [Orders].[CustomerID]",
    "Orders → Customers": "[Orders].[CustomerID] = [Customers].[CustomerID]",
    "Employees → Orders": "[Employees].[EmployeeID] = [Orders].[EmployeeID]",
    "Orders → Employees": "[Orders].[EmployeeID] = [Employees].[EmployeeID]",
    "Orders → Order Details": "[Orders].[OrderID] = [Order Details].[OrderID]",
    "Order Details → Orders": "[Order Details].[OrderID] = [Orders].[OrderID]",
    "Products → Order Details": "[Products].[ProductID] = [Order Details].[ProductID]",
    "Order Details → Products": "[Order Details].[ProductID] = [Products].[ProductID]",
    "Categories → Products": "[Categories].[CategoryID] = [Products].[CategoryID]",
    "Products → Categories": "[Products].[CategoryID] = [Categories].[CategoryID]",
    "Suppliers → Products": "[Suppliers].[SupplierID] = [Products].[SupplierID]",
    "Products → Suppliers": "[Products].[SupplierID] = [Suppliers].[SupplierID]"
}


def detect_business_terms(question):
    """
    检测问题中的业务术语，返回匹配的术语列表
    """
    matched = []
    question_lower = question.lower()

    for term, config in BUSINESS_TERMS.items():
        if term.lower() in question_lower:
            matched.append({
                "term": term,
                "config": config,
                "original": term
            })

    return matched


def get_table_from_term(question):
    """
    根据问题中的术语推断主表
    """
    matched = detect_business_terms(question)

    # 优先级：表格 > 销售 > 客户 > 订单 > 产品 > 员工
    for m in matched:
        config = m["config"]
        if "tables" in config:
            # 取第一张表
            return config["tables"][0] if config["tables"] else None
        if "table" in config:
            return config["table"]

    return None