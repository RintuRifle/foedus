<div align="center">

# Foedus

### AI Tender Intelligence for Indian SMEs

*"Tender dhundo mat — tender khud tumhare paas aaye."*

Six AI agents that scrape government tender portals, audit your eligibility with
**verified, grounded citations**, and draft a submission-ready proposal — in under two minutes.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-6--agent_pipeline-1C3C3C)](https://langchain-ai.github.io/langgraph/)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![Gemini](https://img.shields.io/badge/Gemini-1.5_Flash-4285F4?logo=google&logoColor=white)](https://ai.google.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-D4A853.svg)](LICENSE)

</div>

---

## The Problem

Indian government publishes tenders worth **lakhs of crores** every year across eprocure.gov.in, GeM, and CPPP. For a small business, participating means:

- Manually scanning multiple portals daily
- Reading **80-page tender PDFs** to find the eligibility section buried on page 40
- One missed clause (turnover certificate, EMD format, license copy) → **instant rejection**
- Days of effort writing a technical proposal from scratch

Foedus automates the entire funnel: **discover → match → audit → assess risk → draft → review**.

## The Product

### ✨ Magic Onboarding — no forms, just drop your brochure
The AI reads your company brochure PDF and builds your profile: sectors, turnover, certifications, past projects.

![Magic Onboarding](docs/screenshots/onboarding.png)

### 🎯 Daily Matches — Tinder for tenders
Every morning the scraper pulls fresh tenders and matches them against your profile. Swipe right to save, left to dismiss. Match score, EMD, deadline — sab card pe.

![Daily Matches](docs/screenshots/daily-matches.png)

### 🤖 The 6-Agent Evaluation Pipeline
One click deploys six LangGraph agents with **live WebSocket progress**:

```
Preprocessor → Matchmaker → Auditor → Risk Assessor → Writer ⇄ Reviewer
                              ↑                          (revision loop)
                    the star: extracts every
                 eligibility criterion & cross-checks
                    against your document vault
```

![Pipeline](docs/screen