from sqlalchemy import create_engine, text
e = create_engine('postgresql://foedus:foedus_dev_2024@localhost:5432/foedus_db')
r = e.connect()
tenders = r.execute(text('SELECT COUNT(*) FROM tenders')).scalar()
matches = r.execute(text("SELECT COUNT(*) FROM tender_matches WHERE user_id = '5ef6aee2-7fee-4f8d-8b68-32144925946f'")).scalar()
print(f"Total Tenders in DB: {tenders}")
print(f"Matches for Govind: {matches}")

# Show some tender titles
rows = r.execute(text("SELECT id, title, sector FROM tenders LIMIT 5")).fetchall()
for row in rows:
    print(f"  - {row[1]} | sector: {row[2]}")
