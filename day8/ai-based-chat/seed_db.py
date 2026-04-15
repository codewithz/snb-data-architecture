"""
Seed script: Creates and populates an e-commerce SQLite database.
Run this once to generate ecommerce.db
"""
import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "ecommerce.db"

def create_tables(cur):
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        address TEXT,
        city TEXT,
        country TEXT DEFAULT 'Saudi Arabia',
        created_at TEXT NOT NULL,
        loyalty_tier TEXT DEFAULT 'Bronze'
    );

    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sku TEXT UNIQUE NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        stock_quantity INTEGER DEFAULT 0,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE NOT NULL,
        customer_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        total_amount REAL NOT NULL,
        shipping_address TEXT,
        payment_method TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT,
        tracking_number TEXT,
        estimated_delivery TEXT,
        notes TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    );

    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        unit_price REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    );

    CREATE TABLE IF NOT EXISTS support_tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_number TEXT UNIQUE NOT NULL,
        customer_id INTEGER NOT NULL,
        order_id INTEGER,
        subject TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'open',
        priority TEXT DEFAULT 'medium',
        created_at TEXT NOT NULL,
        resolved_at TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (order_id) REFERENCES orders(id)
    );

    CREATE TABLE IF NOT EXISTS returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        return_number TEXT UNIQUE NOT NULL,
        order_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        reason TEXT NOT NULL,
        status TEXT DEFAULT 'requested',
        refund_amount REAL,
        created_at TEXT NOT NULL,
        processed_at TEXT,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    );
    """)

def seed_data(cur):
    # --- Customers ---
    customers = [
        ("Ahmed", "Al-Rashid", "ahmed.rashid@email.com", "+966501234567", "123 King Fahd Rd", "Riyadh", "Saudi Arabia", "2024-01-15", "Gold"),
        ("Fatima", "Hassan", "fatima.h@email.com", "+966509876543", "45 Olaya St", "Riyadh", "Saudi Arabia", "2024-02-20", "Silver"),
        ("Omar", "Khalid", "omar.k@email.com", "+966551112233", "78 Tahlia St", "Jeddah", "Saudi Arabia", "2024-03-10", "Bronze"),
        ("Sara", "Mohammed", "sara.m@email.com", "+966557778899", "12 Corniche Rd", "Jeddah", "Saudi Arabia", "2023-11-05", "Gold"),
        ("Khalid", "Ibrahim", "khalid.i@email.com", "+966503334455", "90 Prince Sultan St", "Dammam", "Saudi Arabia", "2024-04-01", "Bronze"),
        ("Noura", "Abdullah", "noura.a@email.com", "+966508889900", "34 Al Khobar Rd", "Al Khobar", "Saudi Arabia", "2023-09-15", "Platinum"),
        ("Yusuf", "Ali", "yusuf.ali@email.com", "+966506667788", "56 Dhahran Blvd", "Dhahran", "Saudi Arabia", "2024-05-12", "Bronze"),
        ("Layla", "Nasser", "layla.n@email.com", "+966502223344", "22 Medina Rd", "Medina", "Saudi Arabia", "2024-01-30", "Silver"),
        ("Mohammed", "Saleh", "m.saleh@email.com", "+966504445566", "67 Abha St", "Abha", "Saudi Arabia", "2023-12-20", "Gold"),
        ("Aisha", "Rahman", "aisha.r@email.com", "+966501119988", "11 Taif Rd", "Taif", "Saudi Arabia", "2024-06-01", "Bronze"),
        ("Hassan", "Omar", "hassan.o@email.com", "+966507776655", "88 Jubail Ave", "Jubail", "Saudi Arabia", "2024-02-14", "Silver"),
        ("Maryam", "Faisal", "maryam.f@email.com", "+966503332211", "44 Yanbu Marina", "Yanbu", "Saudi Arabia", "2023-10-10", "Gold"),
    ]
    cur.executemany(
        "INSERT INTO customers (first_name,last_name,email,phone,address,city,country,created_at,loyalty_tier) VALUES (?,?,?,?,?,?,?,?,?)",
        customers
    )

    # --- Products ---
    products = [
        ("iPhone 15 Pro Max", "ELEC-001", "Electronics", 4999.00, 150, "Apple iPhone 15 Pro Max 256GB"),
        ("Samsung Galaxy S24 Ultra", "ELEC-002", "Electronics", 4599.00, 200, "Samsung Galaxy S24 Ultra 512GB"),
        ("MacBook Pro 16\"", "ELEC-003", "Electronics", 9499.00, 75, "Apple MacBook Pro 16-inch M3 Pro"),
        ("Sony WH-1000XM5", "ELEC-004", "Electronics", 1399.00, 300, "Sony noise-cancelling headphones"),
        ("iPad Air", "ELEC-005", "Electronics", 2499.00, 120, "Apple iPad Air M2 chip 256GB"),
        ("Arabic Coffee Set (Dallah)", "HOME-001", "Home & Kitchen", 350.00, 500, "Traditional brass Arabic coffee pot with 6 cups"),
        ("Oud Perfume Collection", "BEAU-001", "Beauty", 890.00, 250, "Premium Arabian oud perfume set - 3 bottles"),
        ("Men's Thobe (White)", "FASH-001", "Fashion", 450.00, 400, "Premium white cotton thobe"),
        ("Women's Abaya (Black)", "FASH-002", "Fashion", 680.00, 350, "Designer embroidered black abaya"),
        ("Dates Gift Box (Medjool)", "FOOD-001", "Food & Gifts", 220.00, 600, "Premium Medjool dates 1kg gift box"),
        ("Smart Watch Pro", "ELEC-006", "Electronics", 1299.00, 180, "Fitness & health tracking smartwatch"),
        ("Bukhoor Burner Set", "HOME-002", "Home & Kitchen", 275.00, 450, "Electric bukhoor incense burner with sampler pack"),
        ("Arabic Calligraphy Art", "HOME-003", "Home & Kitchen", 1200.00, 60, "Hand-painted Arabic calligraphy wall art"),
        ("Gaming Console X", "ELEC-007", "Electronics", 2199.00, 90, "Next-gen gaming console with 2 controllers"),
        ("Leather Laptop Bag", "FASH-003", "Fashion", 599.00, 200, "Genuine leather laptop messenger bag"),
    ]
    cur.executemany(
        "INSERT INTO products (name,sku,category,price,stock_quantity,description) VALUES (?,?,?,?,?,?)",
        products
    )

    # --- Orders ---
    statuses = ["pending", "confirmed", "shipped", "delivered", "cancelled"]
    payment_methods = ["Credit Card", "Apple Pay", "Mada", "Cash on Delivery", "Bank Transfer"]
    random.seed(42)
    base = datetime(2024, 1, 1)
    orders = []
    for i in range(1, 36):
        cid = random.randint(1, 12)
        status = random.choice(statuses)
        dt = base + timedelta(days=random.randint(0, 500))
        created = dt.strftime("%Y-%m-%d %H:%M:%S")
        updated = (dt + timedelta(days=random.randint(1, 5))).strftime("%Y-%m-%d %H:%M:%S")
        tracking = f"SA{random.randint(100000000, 999999999)}" if status in ("shipped", "delivered") else None
        est_del = (dt + timedelta(days=random.randint(3, 10))).strftime("%Y-%m-%d") if status in ("shipped", "confirmed", "delivered") else None
        orders.append((
            f"ORD-{1000+i}",
            cid,
            status,
            0,  # placeholder total
            f"Customer {cid} address",
            random.choice(payment_methods),
            created,
            updated,
            tracking,
            est_del,
            None,
        ))
    cur.executemany(
        "INSERT INTO orders (order_number,customer_id,status,total_amount,shipping_address,payment_method,created_at,updated_at,tracking_number,estimated_delivery,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        orders,
    )

    # --- Order Items & update totals ---
    for oid in range(1, 36):
        n_items = random.randint(1, 4)
        total = 0.0
        chosen = random.sample(range(1, 16), n_items)
        for pid in chosen:
            qty = random.randint(1, 3)
            cur.execute("SELECT price FROM products WHERE id=?", (pid,))
            price = cur.fetchone()[0]
            cur.execute("INSERT INTO order_items (order_id,product_id,quantity,unit_price) VALUES (?,?,?,?)", (oid, pid, qty, price))
            total += price * qty
        cur.execute("UPDATE orders SET total_amount=? WHERE id=?", (round(total, 2), oid))

    # --- Support Tickets ---
    subjects = [
        "Order not received", "Wrong item delivered", "Request for refund",
        "Damaged product", "Tracking not updating", "Payment issue",
        "Want to change delivery address", "Missing item from order",
    ]
    for i in range(1, 16):
        cid = random.randint(1, 12)
        oid = random.randint(1, 35)
        dt = base + timedelta(days=random.randint(30, 500))
        status = random.choice(["open", "in_progress", "resolved", "closed"])
        resolved = (dt + timedelta(days=random.randint(1, 7))).strftime("%Y-%m-%d %H:%M:%S") if status in ("resolved", "closed") else None
        cur.execute(
            "INSERT INTO support_tickets (ticket_number,customer_id,order_id,subject,description,status,priority,created_at,resolved_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (f"TKT-{2000+i}", cid, oid, random.choice(subjects), "Customer reported an issue.", status, random.choice(["low","medium","high"]), dt.strftime("%Y-%m-%d %H:%M:%S"), resolved),
        )

    # --- Returns ---
    reasons = ["Defective product", "Wrong size", "Changed mind", "Not as described", "Arrived late"]
    for i in range(1, 9):
        oid = random.randint(1, 35)
        cur.execute("SELECT customer_id, total_amount FROM orders WHERE id=?", (oid,))
        row = cur.fetchone()
        cid, amt = row
        refund = round(amt * random.uniform(0.5, 1.0), 2)
        dt = base + timedelta(days=random.randint(60, 500))
        status = random.choice(["requested", "approved", "completed", "rejected"])
        processed = (dt + timedelta(days=random.randint(2, 10))).strftime("%Y-%m-%d %H:%M:%S") if status in ("approved", "completed") else None
        cur.execute(
            "INSERT INTO returns (return_number,order_id,customer_id,reason,status,refund_amount,created_at,processed_at) VALUES (?,?,?,?,?,?,?,?)",
            (f"RET-{3000+i}", oid, cid, random.choice(reasons), status, refund, dt.strftime("%Y-%m-%d %H:%M:%S"), processed),
        )


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    create_tables(cur)
    seed_data(cur)
    conn.commit()
    conn.close()
    print(f"Database seeded successfully at {DB_PATH}")
