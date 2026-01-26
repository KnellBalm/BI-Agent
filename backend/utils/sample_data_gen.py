import sqlite3
import os
import random
import datetime

def generate_sample_sqlite(db_path: str = "backend/data/sample_sales.sqlite"):
    """
    Creates a sample SQLite database with sales, products, and customers tables.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create Tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY,
        name TEXT,
        category TEXT,
        price REAL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        sale_id INTEGER PRIMARY KEY,
        product_id INTEGER,
        customer_id INTEGER,
        amount REAL,
        quantity INTEGER,
        sale_date TEXT,
        region TEXT
    )
    """)
    
    # Insert Sample Data
    categories = ["Electronics", "Furniture", "Clothing", "Toys"]
    products = []
    for i in range(1, 11):
        name = f"Product {i}"
        cat = random.choice(categories)
        price = round(random.uniform(10.0, 500.0), 2)
        products.append((i, name, cat, price))
    
    cursor.executemany("INSERT OR IGNORE INTO products VALUES (?, ?, ?, ?)", products)
    
    regions = ["Seoul", "Busan", "Incheon", "Daegu", "Gwangju"]
    sales = []
    start_date = datetime.date(2023, 1, 1)
    for i in range(1, 101):
        prod = random.choice(products)
        qty = random.randint(1, 5)
        amnt = round(prod[3] * qty, 2)
        date = (start_date + datetime.timedelta(days=random.randint(0, 365))).isoformat()
        reg = random.choice(regions)
        sales.append((i, prod[0], random.randint(100, 200), amnt, qty, date, reg))
        
    cursor.executemany("INSERT OR IGNORE INTO sales VALUES (?, ?, ?, ?, ?, ?, ?)", sales)
    
    conn.commit()
    conn.close()
    return db_path

if __name__ == "__main__":
    path = generate_sample_sqlite()
    print(f"Sample database generated at: {path}")
