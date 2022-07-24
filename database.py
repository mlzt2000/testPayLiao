import sqlite3
from typing import Tuple, Any

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
        datetime_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
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

def get_all_requests() -> Tuple[Tuple[Any, ...], ...]:
    curr.execute(f"""
    SELECT * FROM Requests
    """)
    return curr.fetchall()

def get_request_from_id(request_id: int) -> Tuple:
    curr.execute(f"""
    SELECT * FROM Requests
    WHERE id = {request_id};
    """)
    out = curr.fetchall()
    if out:
        return out[0]
    return out

def get_all_requests_involving_username(username: str) -> Tuple[Tuple[Any, ...], ...]:
    curr.execute(f"""
    SELECT * FROM Requests
    WHERE payer_username = '{username}'
    OR debtor_username = '{username}';
    """)
    return curr.fetchall()

def get_all_requests_from_payer_username(payer_username: str) -> Tuple[Tuple[Any, ...], ...]:
    curr.execute(f"""
    SELECT * FROM Requests
    WHERE payer_username = '{payer_username}';
    """)
    return curr.fetchall()

def get_unpaid_requests_from_debtor_username(debtor_username: str) -> Tuple[Tuple[Any, ...], ...]:
    curr.execute(f"""
    SELECT * FROM Requests
    WHERE debtor_username = '{debtor_username}'
    AND paid = False;
    """)
    return curr.fetchall()

def get_unacknowledged_requests_from_payer_username(payer_username: str) -> Tuple[Tuple[Any, ...], ...]:
    curr.execute(f"""
    SELECT * FROM Requests
    WHERE payer_username = '{payer_username}'
    AND paid = True
    AND acknowledged = False;
    """)
    return curr.fetchall()

def get_user_from_id(id: int) -> Tuple[Any, ...]:
    curr.execute(f"""
    SELECT * FROM Users
    WHERE id = {id};
    """)
    out = curr.fetchall()
    if out:
        return out[0]
    return out

def get_user_from_username(username: str) -> Tuple[Any, ...]:
    curr.execute(f"""
    SELECT * FROM Users
    WHERE username = '{username}';
    """)
    out = curr.fetchall()
    if out:
        return out[0]
    return out

def get_all_users() -> Tuple[Tuple[Any,...],...]:
    curr.execute(f"""
    SELECT * FROM Users
    """)
    return curr.fetchall()

####################
# UPDATE FUNCTIONS #
####################

def mark_request_as_paid_from_id(request_id: int) -> Tuple:
    curr.execute(f"""
    UPDATE Requests
    SET paid = True
    WHERE id = {request_id};
    """)
    return conn.commit()

def mark_request_as_unpaid_from_id(request_id: int) -> Tuple:
    print(request_id)
    curr.execute(f"""
    UPDATE Requests
    SET paid = False
    WHERE id = {request_id};
    """)
    return conn.commit()

def mark_request_as_acknowledged_from_id(request_id: int) -> Tuple:
    print(request_id)
    curr.execute(f"""
    UPDATE Requests
    SET acknowledged = True
    WHERE id = {request_id};
    """)
    return conn.commit()

def update_user_username(id: int, username: str) -> Tuple:
    curr.execute(f"""
    UPDATE Users
    SET username = '{username}'
    WHERE id = {id};
    """)
    return conn.commit()