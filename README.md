# Foedus

### AI-Powered Tender Discovery & Proposal Agent for Indian SMEs

> *"Tender dhundo mat — Tender khud tumhare paas aaye."*

Foedus is a multi-agent AI SaaS that automatically scrapes government tender portals (eprocure.gov.in, GeM, CPPP), matches tenders to your company profile, checks eligibility, and drafts ready-to-submit proposals — all in under 2 minutes.

---

## Architecture

```
Internet (Govt Portals) → Scraper → OCR → Vector DB
                                              ↓
User (Next.js Dashboard) → FastAPI → LangGraph (6-Agent Pipeline)
                                              ↓
                              Compliance Report + Proposal PDF
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, Tailwind, Shadcn/UI, Framer Motion |
| Backend | FastAPI (Python 3.12), Celery, Redis |
| AI Engine | LangGraph, Gemini 1.5 Flash, BGE-M3 |
| Database | PostgreSQL (Supabase), Qdrant |
| Payments | Razorpay |

## Quick Start

### Prerequisites
- Python 3.12+
- Docker & Docker Compose
- Node.js 20+ (for frontend, Week 4)

### 1. Clone & Setup
```bash
git clone https://github.com/your-username/foedus.git
cd foedus
cp .env.example .env
# Fill in your API keys in .env
```

### 2. Start Infrastructure
```bash
make infra-up
# Starts: PostgreSQL :5432 | Redis :6379 | Qdrant :6333
```

### 3. Install Dependencies
```bash
make install
```

### 4. Run Migrations
```bash
make migrate
```

### 5. Start Development Server
```bash
make dev
# API available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### 6. Run Scraper (fetch tenders)
```bash
make scrape
```

## Project Structure

```
foedus/
├── backend/          # FastAPI + LangGraph agents
│   ├── app/
│   │   ├── agents/   # 6-agent LangGraph pipeline
│   │   ├── models/   # SQLAlchemy ORM models
│   │   ├── routers/  # API endpoints
│   │   ├── schemas/  # Pydantic validation
│   │   ├── services/ # Business logic
│   │   ├── tasks/    # Celery async tasks
│   │   └── utils/    # Helpers, security, logging
│   └── alembic/      # DB migrations
├── scraper/          # Standalone scraper service
├── frontend/         # Next.js 15 (Week 4)
└── docker-compose.yml
```

## License

MIT

---

*Built for India. For the person tired of reading 80-page tender PDFs at midnight.*
