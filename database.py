import sqlite3
from typing import Tuple

conn = sqlite3.connect(
    "payliaodb.db", 
    detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    check_same_thread = False
)

curr = conn.cursor()

def drop_all_tables():
    reset_cmd = """
    DROP TABLE IF EXISTS Checklists;
    """
    curr.execute(reset_cmd)

    reset_cmd = """
    DROP TABLE IF EXISTS Requests;
    """
    curr.execute(reset_cmd)

    reset_cmd = """
    DROP TABLE IF EXISTS Users;
    """
    curr.execute(reset_cmd)
    conn.commit()

def create_all_tables():
    create_requests_cmd = """
    CREATE TABLE IF NOT EXISTS Requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payer_username TEXT NOT NULL REFERENCES Users(username) ON UPDATE CASCADE,
        debtor_username TEXT NOT NULL REFERENCES Users(username) ON UPDATE CASCADE,
        descr TEXT NOT NULL,
        cost FLOAT NOT NULL,
        paid BOOLEAN NOT NULL DEFAULT FALSE,
        acknowledged BOOLEAN NOT NULL DEFAULT FALSE
    );
    """
    curr.execute(create_requests_cmd)

    create_users_cmd = """
    CREATE TABLE IF NOT EXISTS Users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE
    );
    """
    curr.execute(create_users_cmd)
    conn.commit()

####################
# INSERT FUNCTIONS #
####################

def insert_request(payer_username: str, debtor_username: str, descr: str, cost: float) -> int:
    """Store request into database"""
    curr.execute(f"""
    INSERT INTO Requests(payer_username, debtor_username, descr, cost)
    VALUES('{payer_username}', '{debtor_username}', '{descr}', {cost});
    """)
    return conn.commit()

def insert_user(id: int, username: str) -> Tuple:
    user_exists = get_user_from_id(id)
    if user_exists:
        return update_user_username(id, username)
    curr.execute(f"""
    INSERT INTO Users(id, username)
    VALUES({id}, '{username}')
    """)
    return conn.commit()

####################
# SELECT FUNCTIONS #
####################

def get_request(request_id: int) -> Tuple:
    curr.execute(f"""
    SELECT * FROM Requests
    WHERE id = {request_id}
    """)
    return curr.fetchall()

def get_open_checklists_of_payer_username(username: str) -> Tuple[Tuple, ...]:
    curr.execute(f"""
    SELECT * FROM Checklists
    WHERE payer_username = '{username}'
    AND closed = FALSE;
    """)
    return curr.fetchall()

def get_checklist(checklist_id: int) -> Tuple:
    curr.execute(f"""
    SELECT * FROM Checklists
    WHERE id = {checklist_id};
    """)
    return curr.fetchall()

def get_requests_of_checklist(checklist_id: int) -> Tuple[Tuple, ...]:
    curr.execute(f"""
    SELECT id FROM REQUESTS
    WHERE checklist_id = {checklist_id};
    """)
    return curr.fetchall()

def get_unpaid_requests_of_checklist(checklist_id: int) -> Tuple[Tuple, ...]:
    curr.execute(f"""
    SELECT * FROM Requests
    WHERE checklist_id = {checklist_id}
    AND paid = FALSE
    """)
    return curr.fetchall()

def get_user_from_id(id: int) -> Tuple:
    curr.execute(f"""
    SELECT * FROM Users
    WHERE id = {id};
    """)
    return curr.fetchall()

def get_user_from_username(username: str) -> Tuple:
    curr.execute(f"""
    SELECT * FROM Users
    WHERE username = '{username}';
    """)
    return curr.fetchall()

####################
# UPDATE FUNCTIONS #
####################

def update_user_username(id: int, username: str) -> Tuple:
    curr.execute(f"""
    UPDATE Users
    SET username = '{username}'
    WHERE id = {id};
    """)
    conn.commit()