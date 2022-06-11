CREATE TABLE Orders (
    id INTEGER PRIMARY KEY,
    payer_id INTEGER NOT NULL,
    datetime_created DATETIME NOT NULL,
    descr TEXT
);

CREATE TABLE Items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES Orders(id),
    payee_id INTEGER NOT NULL,
    cost FLOAT NOT NULL,
    descr TEXT
);