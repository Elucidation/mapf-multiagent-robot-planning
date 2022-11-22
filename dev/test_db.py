import sqlite3 as sl
con = sl.connect('test1.db')

# with con:
#     con.execute("""
#         CREATE TABLE USER (
#             id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
#             name TEXT,
#             age INTEGER
#             );
#         """)


# sql = 'INSERT INTO USER (id, name, age) values(?, ?, ?)'
# # data = [
# #     (1, 'Alice', 21),
# #     (2, 'Bob', 22),
# #     (3, 'Chris', 23)
# # ]

# data = [
#     (4, 'John', 33),
#     (5, 'Jill', 34),
# ]

with con:
    con.execute("""
        CREATE TABLE IF NOT EXISTS Robot (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            x INTEGER,
            y INTEGER
            );
        """)

# sql = 'INSERT INTO Robot (id, x, y) values(?, ?, ?)'

# data = [
#     (2, 2, 6),
#     (3, 3, 5),
# ]
# with con:
#     con.executemany(sql, data)

import time

sql = 'UPDATE Robot SET X = ?, Y = ? WHERE id = ?'

for i in range(10):
    c = 1
    x = 5 + i
    y = 3
    print(f'{i} - new pos {c}: {x} {y}')
    data = [
        (x, y, c),
    ]
    con.executemany(sql, data)
    con.commit()

    time.sleep(1)




# with con:
#     # data = con.execute("SELECT * FROM USER WHERE age > 21")
#     data = con.execute("SELECT * FROM Robot WHERE id = 1")
#     for row in data:
#         print(row)