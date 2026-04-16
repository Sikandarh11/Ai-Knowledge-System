import sqlite3

conn = sqlite3.connect("app.db")
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("tables=", [r[0] for r in cur.fetchall()])

cur.execute("SELECT id, email, substr(hashed_password,1,20) FROM users ORDER BY id DESC LIMIT 10")
print("users=", cur.fetchall())