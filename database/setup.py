import sqlite3
import json
import os

DB_FILE = os.path.join(os.path.dirname(__file__), '..', 'cx_simulator.db')
DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'scenarios.json')

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crm_data (
            ticket_id TEXT PRIMARY KEY,
            customer_name TEXT,
            current_plan TEXT,
            billing_cycle TEXT,
            sentiment TEXT,
            recent_usage_metric TEXT,
            cross_sell_offered BOOLEAN DEFAULT 0,
            status TEXT DEFAULT 'open'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_base (
            article_id TEXT PRIMARY KEY,
            title TEXT,
            content TEXT,
            resolution_code TEXT
        )
    ''')
    conn.commit()
    conn.close()

def seed_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM crm_data")
    cursor.execute("DELETE FROM knowledge_base")
    
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
        
    for crm in data["crm_data"]:
        cursor.execute('''
            INSERT INTO crm_data (ticket_id, customer_name, current_plan, billing_cycle, sentiment, recent_usage_metric, cross_sell_offered, status)
            VALUES (?, ?, ?, ?, ?, ?, 0, 'open')
        ''', (crm["ticket_id"], crm["customer_name"], crm["current_plan"], crm["billing_cycle"], crm["sentiment"], crm["recent_usage_metric"]))
        
    for kb in data["knowledge_base"]:
        cursor.execute('''
            INSERT INTO knowledge_base (article_id, title, content, resolution_code)
            VALUES (?, ?, ?, ?)
        ''', (kb["article_id"], kb["title"], kb["content"], kb["resolution_code"]))
        
    conn.commit()
    conn.close()
    return {"message": "Database seeded successfully."}