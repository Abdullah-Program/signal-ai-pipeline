import asyncio
import aiohttp
import json
import os
import time
import random
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Fallback chain: Groq models in order
LLM_FALLBACK_CHAIN = [
    {
        "provider": "groq",
        "model": "llama-3.1-8b-instant",
        "api_url": "https://api.groq.com/openai/v1/chat/completions",
        "max_tokens": 1000,
    },
    {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "api_url": "https://api.groq.com/openai/v1/chat/completions",
        "max_tokens": 1000,
    },
    {
        "provider": "groq",
        "model": "gemma2-9b-it",
        "api_url": "https://api.groq.com/openai/v1/chat/completions",
        "max_tokens": 1000,
    },
]

MAX_CHUNK_CHARS = 3000
MAX_RETRIES = 3

def chunk_text(text, max_chars=MAX_CHUNK_CHARS):
    """Split text into chunks under max_chars"""
    if len(text) <= max_chars:
        return [text]
    chunks = []
    while len(text) > max_chars:
        split_at = text.rfind(" ", 0, max_chars)
        if split_at == -1:
            split_at = max_chars
        chunks.append(text[:split_at])
        text = text[split_at:].strip()
    if text:
        chunks.append(text)
    return chunks

async def call_llm(session, prompt, model_config, retries=0):
    """Call LLM with exponential backoff on 429"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_config["model"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": model_config["max_tokens"],
        "temperature": 0.1
    }

    try:
        async with session.post(
            model_config["api_url"],
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:

            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]

            elif resp.status == 429:
                # Rate limit — exponential backoff with jitter
                if retries < MAX_RETRIES:
                    wait = (2 ** retries) + random.uniform(0, 1)
                    print(f"  [429] Rate limit hit. Waiting {wait:.1f}s... (retry {retries+1})")
                    await asyncio.sleep(wait)
                    return await call_llm(session, prompt, model_config, retries + 1)
                else:
                    print(f"  [429] Max retries reached for {model_config['model']}")
                    return None

            elif resp.status == 413:
                print(f"  [413] Payload too large for {model_config['model']}")
                return None

            else:
                print(f"  [ERROR] Status {resp.status} from {model_config['model']}")
                return None

    except asyncio.TimeoutError:
        print(f"  [TIMEOUT] {model_config['model']}")
        return None
    except Exception as e:
        print(f"  [EXCEPTION] {model_config['model']}: {e}")
        return None

async def extract_with_fallback(session, prompt):
    """Try each model in fallback chain until one succeeds"""
    for i, model_config in enumerate(LLM_FALLBACK_CHAIN):
        print(f"  Trying [{model_config['model']}]...")
        result = await call_llm(session, prompt, model_config)
        if result:
            print(f"  ✅ Success with {model_config['model']}")
            return result, model_config['model']
        else:
            print(f"  ❌ Failed, trying next model...")
    return None, None

def build_startup_prompt(raw_text):
    """Build extraction prompt for startup data"""
    chunk = chunk_text(raw_text)[0]
    return f"""Extract startup information from this text and return ONLY valid JSON.

Text: {chunk}

Return this exact JSON structure:
{{
  "entityName": "company name",
  "description": "what the company does in one sentence",
  "category": "AI subcategory",
  "employeeCount": null or number,
  "location": "city, country or null"
}}

Return ONLY the JSON, no explanation."""

def build_paper_prompt(paper):
    """Build enrichment prompt for research paper"""
    title = paper.get("content", {}).get("title", "")
    abstract = paper.get("content", {}).get("abstract", "")
    chunk = chunk_text(f"Title: {title}\nAbstract: {abstract}")[0]

    return f"""Analyze this AI research paper and return ONLY valid JSON.

{chunk}

Return this exact JSON:
{{
  "key_contribution": "one sentence summary of main contribution",
  "methods_used": ["method1", "method2"],
  "application_domain": "domain like NLP, CV, RL etc",
  "novelty_score": 1-10
}}

Return ONLY the JSON."""

async def enrich_sample_papers(session, papers, sample_size=10):
    """Enrich a sample of papers with LLM extraction"""
    print(f"\n[LLM] Enriching {sample_size} papers as demonstration...")
    enriched = []

    for paper in papers[:sample_size]:
        prompt = build_paper_prompt(paper)
        result, model_used = await extract_with_fallback(session, prompt)

        if result:
            try:
                # Clean JSON response
                clean = result.strip()
                if "```" in clean:
                    clean = clean.split("```")[1]
                    if clean.startswith("json"):
                        clean = clean[4:]
                extracted = json.loads(clean.strip())
                paper["content"]["llm_enrichment"] = extracted
                paper["content"]["llm_model_used"] = model_used
            except json.JSONDecodeError:
                paper["content"]["llm_enrichment"] = {"raw": result}
                paper["content"]["llm_model_used"] = model_used

        enriched.append(paper)
        await asyncio.sleep(0.5)

    return enriched

async def enrich_sample_startups(session, startups, sample_size=10):
    """Enrich a sample of startups with LLM"""
    print(f"\n[LLM] Enriching {sample_size} startups as demonstration...")
    enriched = []

    for startup in startups[:sample_size]:
        name = startup["content"]["entityName"]
        desc = startup["content"].get("description", "")
        raw_text = f"Company: {name}. {desc}"

        prompt = build_startup_prompt(raw_text)
        result, model_used = await extract_with_fallback(session, prompt)

        if result:
            try:
                clean = result.strip()
                if "```" in clean:
                    clean = clean.split("```")[1]
                    if clean.startswith("json"):
                        clean = clean[4:]
                extracted = json.loads(clean.strip())
                startup["content"]["llm_enrichment"] = extracted
                startup["content"]["llm_model_used"] = model_used
            except json.JSONDecodeError:
                startup["content"]["llm_enrichment"] = {"raw": result}
                startup["content"]["llm_model_used"] = model_used

        enriched.append(startup)
        await asyncio.sleep(0.5)

    return enriched

async def main():
    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY not found in .env!")
        print("Add: GROQ_API_KEY=your_key to .env file")
        return

    print("Starting LLM Orchestration Engine...")
    print(f"Fallback chain: {' → '.join([m['model'] for m in LLM_FALLBACK_CHAIN])}")
    print(f"Max chunk size : {MAX_CHUNK_CHARS} chars")
    print(f"Max retries    : {MAX_RETRIES}\n")

    connector = aiohttp.TCPConnector(limit=3)
    async with aiohttp.ClientSession(connector=connector) as session:

        # Test fallback chain first
        print("[TEST] Testing LLM fallback chain...")
        test_prompt = 'Return this exact JSON: {"status": "ok", "message": "LLM working"}'
        result, model = await extract_with_fallback(session, test_prompt)
        if result:
            print(f"  Chain working! Model: {model}\n")
        else:
            print("  ❌ All models failed — check API key!\n")
            return

        # Load data
        with open("output/research_papers.json", "r", encoding="utf-8") as f:
            papers = json.load(f)

        with open("output/startups.json", "r", encoding="utf-8") as f:
            startups = json.load(f)

        # Enrich samples
        enriched_papers = await enrich_sample_papers(session, papers, sample_size=15)
        enriched_startups = await enrich_sample_startups(session, startups, sample_size=15)

        # Save enriched outputs
        os.makedirs("output", exist_ok=True)

        with open("output/papers_enriched.json", "w", encoding="utf-8") as f:
            json.dump(enriched_papers[:15], f, indent=2, ensure_ascii=False)

        with open("output/startups_enriched.json", "w", encoding="utf-8") as f:
            json.dump(enriched_startups[:15], f, indent=2, ensure_ascii=False)

        print(f"\n✅ LLM Orchestration complete!")
        print(f"📁 output/papers_enriched.json (15 samples)")
        print(f"📁 output/startups_enriched.json (15 samples)")
        print(f"\nFallback chain is production-ready for full pipeline.")

if __name__ == "__main__":
    asyncio.run(main())