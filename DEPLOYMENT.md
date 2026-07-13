# Foedus — Production Deployment Guide

Total cost early stage: **~₹0/month** (sab free tiers). Scale hone pe ~₹500-1500/mo.

## Architecture

```
Vercel (Next.js)  →  Render (FastAPI + Celery + Redis + cron scraper)
                          ↓
              Supabase (Postgres) + Qdrant Cloud + Gemini API
```

## Step 1 — Supabase (Database, free tier)
1. [supabase.com](https://supabase.com) → New project (region: Mumbai `ap-south-1`)
2. Settings → Database → **Connection Pooler** (Transaction mode) URI copy karo
3. Do formats banao:
   - `DATABASE_URL` = `postgresql+asyncpg://postgres.xxx:PASS@...pooler.supabase.com:6543/postgres`
   - `DATABASE_URL_SYNC` = same but `postgresql://` (alembic ke liye)
4. Migrations: local se `DATABASE_URL_SYNC=<prod> make migrate`

## Step 2 — Qdrant Cloud (Vector DB, free 1GB)
1. [cloud.qdrant.io](https://cloud.qdrant.io) → free cluster (Mumbai/Singapore)
2. `QDRANT_URL` = cluster URL (API key bhi milega — agar code me use ho to env me daalo)

## Step 3 — Render (Backend, blueprint)
1. Repo GitHub pe push karo
2. Render → **New → Blueprint** → repo select → `render.yaml` auto-detect
3. 4 services banenge: `foedus-api` (web), `foedus-worker`, `foedus-scraper` (cron 6AM IST), `foedus-redis`
4. `sync: false` wale env vars dashboard me manually bharo:
   - `DATABASE_URL`, `DATABASE_URL_SYNC`, `QDRANT_URL`, `GEMINI_API_KEY`
   - `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`
   - `CORS_ORIGINS` = `https://<your-app>.vercel.app`
5. Deploy hone ke baad: `https://foedus-api.onrender.com/health` check karo

> **Free tier note:** Render free web services 15 min idle ke baad sleep hote hain (first request slow). Starter plan ($7/mo) se ye hat jaata hai — launch ke baad upgrade karna.

## Step 4 — Vercel (Frontend)
1. Vercel → New Project → repo import → **Root Directory: `frontend`**
2. Environment variables:
   - `NEXT_PUBLIC_API_URL` = `https://foedus-api.onrender.com/api/v1`
   - `NEXT_PUBLIC_WS_URL` = `wss://foedus-api.onrender.com/api/v1`
3. Deploy. Fir Render pe `CORS_ORIGINS` me Vercel URL daal ke redeploy.

## Step 5 — Razorpay (Live mode)
1. [dashboard.razorpay.com](https://dashboard.razorpay.com) → KYC complete karo → Live keys generate
2. `RAZORPAY_KEY_ID` + `RAZORPAY_KEY_SECRET` Render me daalo
3. **Webhook setup**: Settings → Webhooks → Add:
   - URL: `https://foedus-api.onrender.com/api/v1/payments/webhook`
   - Event: `payment.captured`
   - Secret generate karke `RAZORPAY_WEBHOOK_SECRET` me daalo
4. Test: pehle Test mode keys se full flow verify karo (test card `4111 1111 1111 1111`)

## Step 6 — Gemini API
[aistudio.google.com](https://aistudio.google.com) → API key → `GEMINI_API_KEY`. Free tier ~15 RPM — early users ke liye kaafi.

## Launch Checklist
- [ ] `/health` green
- [ ] Register → onboard → swipe → evaluate → report → proposal PDF (full E2E prod pe)
- [ ] WebSocket progress prod pe chalta hai (wss://)
- [ ] Test-mode payment → plan upgrades to Pro
- [ ] Webhook delivery success (Razorpay dashboard me dikhta hai)
- [ ] Scraper cron ka pehla run — tenders DB me aaye
- [ ] `JWT_SECRET` production me random hai (render.yaml `generateValue` se auto)
- [ ] Sentry DSN (optional, error tracking)

## Local production dry-run
```bash
docker build -f backend/Dockerfile -t foedus-backend .
docker run -p 8000:8000 --env-file backend/.env foedus-backend
```
