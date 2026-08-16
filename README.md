# Signal AI — Intelligence Graph Pipeline

A production-grade AI data pipeline for GraphOne/FrontierAtlas that ingests, normalizes, and enriches multi-dimensional datasets across startups, products, research papers, jobs, and news.

## Results

| Entity | Count | Source |
|--------|-------|--------|
| Research Papers | 1,025 | Arxiv API + Papers with Code |
| Startups | 1,002 | HuggingFace + GitHub + YC |
| Products | 2,081 | HuggingFace Models + Spaces |
| News | 19 | RSS Feeds + HackerNews (24hr fresh) |
| Jobs | 22 | Remotive + Arbeitnow (24hr fresh) |
| Entity Mappings | 3,105 | RapidFuzz Resolution Engine |

## Setup

```bash
git clone https://github.com/Abdullah-Program/signal-ai-pipeline
cd signal-ai-pipeline
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r src/requirements.txt
cp .env.example .env
# Add your GROQ_API_KEY in .env
```

## Running the Pipeline

```bash
# Phase I — Data Acquisition
python src/paper_scraper.py       # 1000+ research papers
python src/startup_scraper.py     # 1000+ startups
python src/product_scraper.py     # 1000+ products

# Phase II — Fresh Signals (24hr)
python src/news_jobs_scraper.py   # news + jobs

# Phase III — LLM Extraction
python src/llm_orchestrator.py    # fallback chain

# Phase IV — Entity Resolution
python src/entity_resolver.py     # deduplication
```

## Project Structure

```
signal-ai/
├── src/
│   ├── paper_scraper.py        # Arxiv API + Papers with Code
│   ├── startup_scraper.py      # HuggingFace + GitHub orgs
│   ├── product_scraper.py      # HuggingFace models + spaces
│   ├── news_jobs_scraper.py    # RSS feeds + job board APIs
│   ├── llm_orchestrator.py     # Multi-tier LLM fallback engine
│   ├── entity_resolver.py      # Fuzzy entity deduplication
│   ├── generate_pdf.py         # Architecture PDF generator
│   └── requirements.txt
├── output/
│   ├── research_papers.csv
│   ├── startups.csv
│   ├── products.csv
│   ├── news.csv
│   ├── jobs.csv
│   └── entity_mapping_log.csv
├── .env.example
├── README.md
└── architecture.pdf
```
## Phase I — Massive Data Acquisition

**Research Papers**
- Source: Arxiv public API (no auth required)
- 20 AI topics: LLMs, diffusion models, RAG, RL, CV, NLP etc.
- GitHub star enrichment via Papers with Code API
- Output: 1,025 unique papers with authors, abstracts, github_url, github_stars

**Startups**
- Sources: HuggingFace model/spaces/dataset orgs + GitHub topic search
- No bot protection issues — all free public APIs
- Output: 1,002 unique organizations

**Products**
- Source: HuggingFace models (2000+ AI models as products)
- Pricing detection: FREE/FREEMIUM/PAID/ENTERPRISE via tag analysis
- Output: 2,081 unique products with canonical startup mapping

## Phase II — 24hr Fresh Signal Ingestion

**News Sources (5)**
1. VentureBeat AI — RSS feed
2. TechCrunch AI — RSS feed
3. The Verge AI — RSS feed
4. Ars Technica — RSS feed
5. Hacker News — Firebase API with AI keyword filter

**Job Boards (5)**
1. Remotive — REST API (remote AI jobs)
2. Arbeitnow — REST API with AI keyword filter
3. GitHub — search API for job postings
4. HuggingFace Jobs — scraped listings
5. YC Work at a Startup — API

**Date Normalization**
- Handles: ISO-8601, RFC-2822, relative ("2 hours ago"), missing dates
- Heuristic: if no date found, compare content hash against last run
- All timestamps normalized to UTC ISO-8601

## Phase III — LLM Extraction Engine

**Fallback Chain**
llama-3.1-8b-instant → llama-3.3-70b-versatile → gemma2-9b-it

**Rate Limit Handling (429)**
- Exponential backoff: wait = 2^retry + random(0,1)
- Max 3 retries per model before falling to next
- Jitter prevents thundering herd problem

**Context Window / Chunking (413 prevention)**
- Max chunk size: 3,000 characters
- Splits at word boundaries (rfind " ")
- Semantically dense content prioritized in first chunk

## Phase IV — Entity Resolution

- Seed DB: 50 canonical AI entities (OpenAI, Anthropic, Google DeepMind etc.)
- Alias map: 49 known variants ("openai inc" → "OpenAI")
- RapidFuzz token_sort_ratio at 85% threshold
- Partial ratio fallback at 90% threshold
- Stats: 6 alias, 176 fuzzy, 93 partial, 2830 no-match

## Phase V — Anti-Bot Strategy

**Current Implementation**
- Async: `asyncio + aiohttp` with TCP connection pooling
- User-Agent rotation via `fake-useragent`
- Polite rate limiting: `asyncio.sleep()` between requests
- Preferred free public APIs over protected HTML pages

**For Cloudflare-Protected Sites (Production)**

Strategy: Playwright Async + Stealth Plugin

playwright install chromium
Use playwright-stealth to mask automation signals
Residential proxy rotation (BrightData / Oxylabs)
Human-like delays: random.uniform(2, 5) seconds
Cookie persistence across sessions
CAPTCHA fallback: 2captcha API integration

**For JavaScript-Heavy Sites**
- Playwright async for full JS rendering
- Wait for network idle before extraction
- Extract from __NEXT_DATA__ or window.__STATE__ when available

## Phase VI — Scale to 500k+

**Distributed Architecture**

URL Frontier (Redis SET)
↓
Task Queue (Celery + Redis)
↓
Scraper Workers (N horizontal pods)
↓
LLM Extraction (async, rate-limited)
↓
Entity Resolution (batch processing)
↓
PostgreSQL + Qdrant

**Freshness Tracking**
- Redis SET stores SHA256(url) for deduplication
- TTL-based expiry for re-crawl scheduling
- Vector similarity in Qdrant detects near-duplicate content

**Storage**
- PostgreSQL: structured entity data (startups, products, papers)
- Qdrant: vector embeddings for semantic deduplication
- Redis: URL frontier + job queue + rate limit counters

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Python 3.11, asyncio |
| HTTP | aiohttp, BeautifulSoup4 |
| LLM | Groq API (llama-3.1, llama-3.3, gemma2) |
| Entity Resolution | RapidFuzz |
| Storage (current) | JSON + CSV |
| Storage (production) | PostgreSQL + Qdrant + Redis |
| Anti-Bot | Playwright + stealth + proxies |

## Environment Variables

GROQ_API_KEY=your_groq_api_key_here