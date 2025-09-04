from sqlalchemy import text
from app.services.db import engine

with engine.begin() as conn:
    conn.execute(text("CREATE TABLE IF NOT EXISTS healthcheck (ok boolean)"))
    conn.execute(text("TRUNCATE healthcheck"))
    conn.execute(text("INSERT INTO healthcheck (ok) VALUES (true)"))
    print(conn.execute(text("SELECT ok FROM healthcheck LIMIT 1")).scalar())
