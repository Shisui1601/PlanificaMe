from backend.app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Base actual
    dbname = conn.execute(text("SELECT current_database();")).scalar()
    # Tablas del esquema public
    rows = conn.execute(
        text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public';")
    ).fetchall()

print("Base actual:", dbname)
print("Tablas:", [r[0] for r in rows])