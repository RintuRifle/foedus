# Week 4 — Frontend: "The Dossier" ✅

## Design direction
Intelligence-agency war room. Ink-black + brass/gold (sarkari seal energy), film grain, brass aurora. **Fraunces** serif display + **IBM Plex Sans/Mono**. Tender = classified dossier card with rotating stamps.

## Naya backend (Week 4 prerequisite)
- `backend/app/routers/company.py` — company CRUD + document vault + **`POST /company/onboard-brochure`**: PDF upload → OCR → Gemini structured parse → profile auto-fill (Magic Onboarding ka engine)

## Frontend structure (`frontend/`)
| Route | Kya hai |
|---|---|
| `/` | Landing — serif hero, portal ticker |
| `/login` `/register` | Auth (dossier card, auto-login on signup) |
| `/onboarding` | ✨ Magic onboarding — brochure drop → AI parse theater → review card with confidence stamp |
| `/dashboard` | **Daily Matches** — Tinder swipe deck (drag right = save, left = reject, keyboard ←/→/↵, stamps reveal on drag) |
| `/dashboard/saved` | Saved tenders list |
| `/dashboard/pipeline` | Evaluation jobs with live progress bars (8s auto-refresh) |
| `/dashboard/tender/[id]` | Tender dossier + "⚡ Evaluate with AI" trigger (402 quota handling) |
| `/dashboard/evaluations/[jobId]` | **Evaluation Theater** — 7-agent rail with live WebSocket progress (polling fallback), then intelligence report: score rings, compliance matrix (✓/◐/✕ expandable rows with source quotes), risk factors, proposal CTA |
| `/dashboard/proposals` + `[id]` | Proposal viewer (markdown render) + inline editor (version bump) + PDF/MD export |

## Stack
Next.js 15 (App Router) · React 19 · TypeScript · Tailwind · Framer Motion · react-markdown. JWT in localStorage with silent refresh-on-401 (`lib/api.ts`).

## Chalane ke liye
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev          # http://localhost:3000
```
Backend + worker bhi chahiye (`make dev` + `make worker`). Backend `.env` me `CORS_ORIGINS` me `http://localhost:3000` already hai.

## Flow test
Register → brochure PDF drop karo → profile auto-fill dekho → dashboard me swipe → tender open → Evaluate → live agent theater → report → proposal open → PDF export.

## Next (Week 5)
Guardrails: structured output hardening, LangSmith evals, scanned-PDF fallback edge cases.
