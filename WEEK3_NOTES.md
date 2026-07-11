# Week 3 — Backend API & Async Architecture ✅

## Kya bana (aaj ka kaam)

### Naye files
| File | Kaam |
|---|---|
| `backend/app/routers/auth.py` | Register / Login / Refresh / Me (JWT, auto-login on signup) |
| `backend/app/routers/tenders.py` | `/tenders/feed` (personalized, match-score sorted), `/search`, `/saved`, detail, `/save` + `/reject` (Tinder swipe) |
| `backend/app/routers/proposals.py` | List / Get / Edit (auto version bump) / Delete / Export `.md` + `.pdf` (WeasyPrint) |
| `backend/app/routers/ws.py` | WebSocket `/api/v1/ws/evaluations/{job_id}?token=JWT` — live agent progress |
| `backend/app/services/progress_service.py` | Redis pub/sub bridge (worker → WebSocket) + snapshot cache for late joiners |

### Upgraded files
- `agents/graph.py` — ab `ainvoke` ki jagah **`astream`** use karta hai: har agent node complete hote hi progress callback fire hota hai (revision loop rounds bhi annotate hote hain)
- `tasks/evaluation_task.py` — progress DB me persist + Redis pe publish (completed/failed terminal events included)
- `routers/evaluations.py` — ab fully authed: plan quota check (402 on limit), duplicate-job guard, quota refund on queue failure, + naya `/{job_id}/report` endpoint (compliance matrix + risk)
- `main.py` — saare routers wired

## Live progress flow
```
Celery worker → graph.astream → on_progress()
                                   ├─ DB update (polling fallback)
                                   └─ Redis publish → WebSocket → Frontend
```
Events: `context_builder 5% → preprocessor 20% → matchmaker 35% → auditor 55% → risk 70% → writer 85% → reviewer 95% → completed 100%`

## Test kaise kare
```bash
make infra-up && make dev        # terminal 1
make worker                       # terminal 2
```
```bash
# 1. Register
curl -X POST localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@sme.in","password":"password123","full_name":"Test SME"}'
# → access_token copy karo

# 2. Feed
curl localhost:8000/api/v1/tenders/feed -H "Authorization: Bearer <TOKEN>"

# 3. Evaluation trigger (202 + job_id)
curl -X POST localhost:8000/api/v1/evaluations/start \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"tender_id":"<TENDER_UUID>"}'

# 4. Live progress (browser console)
# new WebSocket(`ws://localhost:8000/api/v1/ws/evaluations/${jobId}?token=${token}`)

# 5. Report
curl localhost:8000/api/v1/evaluations/<JOB_ID>/report -H "Authorization: Bearer <TOKEN>"
```

## Notes
- `requirements.txt` me `markdown==3.7` add hua (PDF export ke liye). `pip install -r requirements.txt` dobara chala lena.
- PDF export WeasyPrint pe hai — agar system libs (pango/cairo) missing hain to 501 dega, `.md` export hamesha kaam karega.
- Naya migration chahiye nahi — koi model change nahi hua.
- WS auth query-param token se hota hai (browsers WS pe headers nahi bhej sakte).

## Next (Week 4)
Next.js frontend: magic onboarding, dashboard (feed swipe UI), live progress bar (WS), eligibility report UI (green/red matrix).
