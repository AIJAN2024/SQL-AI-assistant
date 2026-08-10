import sqlite3
import random
from datetime import datetime, timedelta

# 创建实体数据库文件（保存在项目目录下）
conn = sqlite3.connect('orders.db')  # 改成文件名，而不是 ':memory:'
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    product_name TEXT,
    category TEXT,
    price REAL,
    sales_volume INTEGER,
    sale_date DATE
)
''')

products = [('手机', '电子', 2999), ('书包', '文具', 199), ('牛奶', '食品', 49),
            ('耳机', '电子', 599), ('笔记本', '文具', 29), ('面包', '食品', 15)]

# 先清空旧数据（避免重复插入）
cursor.execute('DELETE FROM orders')

for i in range(1000):
    p = random.choice(products)
    days_ago = random.randint(1, 90)
    date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
    volume = random.randint(10, 100)
    cursor.execute(f"INSERT INTO orders (product_name, category, price, sales_volume, sale_date) VALUES ('{p[0]}','{p[1]}',{p[2]},{volume},'{date}')")

conn.commit()
conn.close()  # 关闭连接

print("✅ 数据库准备完成！1000条订单数据已插入 orders.db")