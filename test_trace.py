import sys
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://foedus:foedus_dev_2024@localhost:5432/foedus_db')
try:
    with engine.connect() as conn:
        res = conn.execute(text("SELECT error_log FROM evaluation_jobs ORDER BY created_at DESC LIMIT 1"))
        print(res.fetchone()[0])
except Exception as e:
    print(e)
