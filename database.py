import sqlite3
import logging

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO

)

# connect to database or create one if needed
conn = sqlite3.connect(
    "payliaodb.db", 
    detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    check_same_thread = False
)
curr = conn.cursor()

# enable foreign key constraints
curr.execute("""PRAGMA foreign_key = ON;""")

"""
Creates tables. 
@param: None
@returns None
"""
def create_tables():
    try:
        # Create Orders table
        curr.execute("""
        CREATE TABLE IF NOT EXISTS Orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payer_username TEXT NOT NULL REFERENCES Users(username) ON UPDATE CASCADE,
            datetime_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            descr TEXT,
            closed BOOLEAN NOT NULL DEFAULT FALSE
        );
        """)
        
        # Create Items table
        curr.execute("""
        CREATE TABLE IF NOT EXISTS Items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL REFERENCES Orders(id) ON DELETE CASCADE,
            descr FLOAT NOT NULL,
            cost TEXT NOT NULL
        );
        """)

        # Create Options table
        curr.execute("""
        CREATE TABLE IF NOT EXISTS Options (
            item_id INTEGER NOT NULL REFERENCES Items(id),
            order_id INTEGER NOT NULL REFERENCES Orders(id) ON DELETE CASCADE,
            payee_username TEXT NOT NULL REFERENCES Users(username) ON UPDATE CASCADE,
            qty INTEGER NOT NULL DEFAULT 1,
            paid BOOLEAN NOT NULL DEFAULT FALSE,
            acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
            PRIMARY KEY (item_id, order_id, payee_username)
        );
        """)

        # Create Users table
        curr.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE
        );
        """)

        conn.commit()
    except Exception:
        logging.WARNING(f"database.py/create_table():\n{Exception}")

"""
Drops all tables
@params None
@returns None
"""
def drop_all_tables():
    try:
        drop_table("Orders")
        drop_table("Items")
        drop_table("Options")
        drop_table("Users")
    except Exception:
        logging.WARNING(f"database.py/delete_all_tables():\n{Exception}")

"""
Drops table based on name of table
@params table_name: str
@returns None
"""
def drop_table(table_name: str):
    try:
        curr.exec(f"""
        DROP TABLE IF EXISTS {table_name};
        """)
        conn.commit()
    except Exception:
        logging.WARNING(f"database.py/delete_table():\n{Exception}")

"""
Deletes all entries in all tables
@params None
@returns None
"""
def clear_all_tables():
    try:
        clear_table("Orders")
        clear_table("Items")
        clear_table("Options")
        clear_table("Users")
    except Exception:
        logging.WARNING(f"database.py/clear_all_tables():\n{Exception}")

"""
Deletes all entries in table based on name of table
@params table_name: str
@returns None
"""
def clear_table(table_name: str):
    try:
        curr.exec(f"""
        DELETE FROM {table_name};
        """)
    except Exception:
        logging.WARNING(f"database.py/clear_table():\n{Exception}")

"""
Returns all rows from a table based on name of table
@params table_name: str
@returns None
"""
def select_table(table_name: str):
    try:
        curr.exec(f"""
        SELECT * FROM {table_name};
        """)
        return curr.fetchall()
    except Exception:
        logging.WARNING(f"database.py/select_table():\n{Exception}")

"""
Returns rows from orders based on 
"""
