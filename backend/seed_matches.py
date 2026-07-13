from sqlalchemy import create_engine, text
import uuid

e = create_engine('postgresql://foedus:foedus_dev_2024@localhost:5432/foedus_db')
conn = e.connect()

govind_id = '5ef6aee2-7fee-4f8d-8b68-32144925946f'
tenders = conn.execute(text("SELECT id, title FROM tenders WHERE status = 'active'")).fetchall()
print(f"Found {len(tenders)} active tenders")

for tender in tenders:
    tender_id = str(tender[0])
    title = tender[1]
    
    exists = conn.execute(text(
        "SELECT COUNT(*) FROM tender_matches WHERE user_id = :uid AND tender_id = :tid"
    ), {"uid": govind_id, "tid": tender_id}).scalar()
    
    if exists:
        print(f"  Skip: {title}")
        continue
    
    match_id = str(uuid.uuid4())
    conn.execute(text("""
        INSERT INTO tender_matches (id, user_id, tender_id, match_score, match_reasons, is_seen, is_saved, is_rejected, created_at)
        VALUES (:id, :uid, :tid, 0.85, :reasons, false, false, false, NOW())
    """), {
        "id": match_id,
        "uid": govind_id,
        "tid": tender_id,
        "reasons": "{\"Solar sector overlap with NexaSolar profile\",\"Renewable energy expertise match\",\"Bihar-based company matching state tender\"}",
    })
    conn.commit()
    print(f"  ✅ Matched: {title} (85%)")

total = conn.execute(text("SELECT COUNT(*) FROM tender_matches WHERE user_id = :uid"), {"uid": govind_id}).scalar()
print(f"\nTotal matches for Govind: {total}")
conn.close()
