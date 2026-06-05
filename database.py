import aiosqlite
import os

DB_PATH = "logistics.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS couriers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                name TEXT,
                city TEXT,
                username TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT,
                courier_id INTEGER,
                courier_name TEXT,
                city TEXT,
                status TEXT,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def add_courier(telegram_id, name, city, username):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO couriers (telegram_id, name, city, username)
            VALUES (?, ?, ?, ?)
        """, (telegram_id, name, city, username))
        await db.commit()

async def get_couriers_by_city(city):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT telegram_id, name FROM couriers WHERE city = ?", (city,)
        ) as cursor:
            return await cursor.fetchall()

async def get_courier(telegram_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM couriers WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            return await cursor.fetchone()

async def save_order(order_number, courier_id, courier_name, city, status, note):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO orders (order_number, courier_id, courier_name, city, status, note)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (order_number, courier_id, courier_name, city, status, note))
        await db.commit()

async def update_order_status(order_number, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE orders SET status = ? WHERE order_number = ?
        """, (status, order_number))
        await db.commit()

async def get_all_orders():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM orders") as cursor:
            return await cursor.fetchall()