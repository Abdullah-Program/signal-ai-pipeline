import asyncio
import aiohttp
import json
import csv
import os
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from tqdm import tqdm

CUTOFF_HOURS = 24

def is_within_24hrs(date_str):
    """Check if a date string is within last 24 hours"""
    if not date_str:
        return False
    try:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=CUTOFF_HOURS)
        
        # Try multiple formats
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S GMT",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt >= cutoff
            except:
                continue
        return False
    except:
        return False

def parse_relative_date(text):
    """Convert '2 hours ago' → ISO timestamp"""
    try:
        now = datetime.now(timezone.utc)
        text = text.lower().strip()
        
        if "just now" in text or "moments ago" in text:
            return now.isoformat()
        
        import re
        patterns = [
            (r"(\d+)\s*minute", "minutes"),
            (r"(\d+)\s*hour", "hours"),
            (r"(\d+)\s*day", "days"),
            (r"(\d+)\s*week", "weeks"),
        ]
        
        for pattern, unit in patterns:
            match = re.search(pattern, text)
            if match:
                n = int(match.group(1))
                delta = timedelta(**{unit: n})
                return (now - delta).isoformat()
        
        return now.isoformat()
    except:
        return datetime.now(timezone.utc).isoformat()

async def fetch_rss_feed(session, url, source_name):
    """Fetch and parse RSS feed"""
    items = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                text = await resp.text()
                soup = BeautifulSoup(text, 'lxml-xml') if 'xml' in text[:100] else BeautifulSoup(text, 'lxml')
                
                entries = soup.find_all('item') or soup.find_all('entry')
                for entry in entries:
                    title = entry.find('title')
                    link = entry.find('link')
                    pub_date = entry.find('pubDate') or entry.find('published') or entry.find('updated')
                    description = entry.find('description') or entry.find('summary')
                    
                    title_text = title.get_text(strip=True) if title else ""
                    link_text = link.get_text(strip=True) if link else (link.get('href','') if link else "")
                    date_text = pub_date.get_text(strip=True) if pub_date else ""
                    desc_text = description.get_text(strip=True)[:500] if description else ""
                    
                    if title_text and is_within_24hrs(date_text):
                        items.append({
                            "schemaVersion": "1.0",
                            "recordType": "NEWS",
                            "source": {
                                "name": source_name,
                                "url": link_text
                            },
                            "content": {
                                "title": title_text,
                                "description": desc_text,
                                "published_date": date_text,
                                "collected_at": datetime.now(timezone.utc).isoformat()
                            },
                            "collectedAt": datetime.now(timezone.utc).isoformat() + "Z"
                        })
    except Exception as e:
        print(f"  RSS error [{source_name}]: {e}")
    return items

async def fetch_hackernews_ai(session):
    """HackerNews AI stories from last 24hrs"""
    items = []
    try:
        # Get top stories
        url = "https://hacker-news.firebaseio.com/v0/newstories.json"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                story_ids = await resp.json()
                story_ids = story_ids[:100]  # Top 100
                
                ai_keywords = ["ai", "llm", "gpt", "machine learning", "neural", 
                              "openai", "anthropic", "gemini", "claude", "artificial intelligence",
                              "deep learning", "transformer", "model", "ml"]
                
                now = datetime.now(timezone.utc)
                cutoff = now - timedelta(hours=24)
                cutoff_ts = int(cutoff.timestamp())
                
                for story_id in tqdm(story_ids[:60], desc="  HN stories"):
                    story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                    async with session.get(story_url, timeout=aiohttp.ClientTimeout(total=10)) as sresp:
                        if sresp.status == 200:
                            story = await sresp.json()
                            if story and story.get("time", 0) >= cutoff_ts:
                                title = story.get("title", "").lower()
                                if any(kw in title for kw in ai_keywords):
                                    pub_date = datetime.fromtimestamp(story["time"], tz=timezone.utc).isoformat()
                                    items.append({
                                        "schemaVersion": "1.0",
                                        "recordType": "NEWS",
                                        "source": {
                                            "name": "Hacker News",
                                            "url": story.get("url", f"https://news.ycombinator.com/item?id={story_id}")
                                        },
                                        "content": {
                                            "title": story.get("title", ""),
                                            "description": story.get("text", "")[:300] if story.get("text") else "",
                                            "published_date": pub_date,
                                            "score": story.get("score", 0),
                                            "collected_at": now.isoformat()
                                        },
                                        "collectedAt": now.isoformat() + "Z"
                                    })
                    await asyncio.sleep(0.1)
    except Exception as e:
        print(f"  HN error: {e}")
    return items

async def fetch_jobs_remotive(session):
    """Remotive.io - Remote AI/ML jobs API (free)"""
    jobs = []
    try:
        categories = ["software-dev", "data", "product"]
        for cat in categories:
            url = f"https://remotive.com/api/remote-jobs?category={cat}&limit=50"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for job in data.get("jobs", []):
                        title = job.get("title", "").lower()
                        # Filter AI/ML jobs
                        ai_keywords = ["ai", "ml", "machine learning", "deep learning", 
                                      "data scientist", "nlp", "llm", "python", "engineer"]
                        if any(kw in title for kw in ai_keywords):
                            pub_date = job.get("publication_date", "")
                            if is_within_24hrs(pub_date):
                                jobs.append({
                                    "schemaVersion": "1.0",
                                    "recordType": "JOB",
                                    "source": {
                                        "name": "Remotive",
                                        "url": job.get("url", "https://remotive.com")
                                    },
                                    "content": {
                                        "company": job.get("company_name", ""),
                                        "title": job.get("title", ""),
                                        "date": pub_date,
                                        "is_remote": True,
                                        "role_family": "Engineering",
                                        "location": job.get("candidate_required_location", "Remote"),
                                        "salary": job.get("salary", ""),
                                        "tags": ", ".join(job.get("tags", [])[:5])
                                    },
                                    "collectedAt": datetime.now(timezone.utc).isoformat() + "Z"
                                })
            await asyncio.sleep(1)
    except Exception as e:
        print(f"  Remotive error: {e}")
    return jobs

async def fetch_jobs_github(session):
    """GitHub Jobs via search (public repos with job postings)"""
    jobs = []
    try:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        date_str = cutoff.strftime("%Y-%m-%d")
        
        queries = [
            "AI engineer hiring",
            "ML engineer job remote",
            "LLM engineer position"
        ]
        
        for query in queries:
            url = f"https://api.github.com/search/repositories?q={query}+created:>{date_str}&sort=updated&per_page=20"
            headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Mozilla/5.0"}
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("items", []):
                        jobs.append({
                            "schemaVersion": "1.0",
                            "recordType": "JOB",
                            "source": {
                                "name": "GitHub",
                                "url": item.get("html_url", "")
                            },
                            "content": {
                                "company": item.get("owner", {}).get("login", ""),
                                "title": item.get("name", ""),
                                "date": item.get("created_at", ""),
                                "is_remote": True,
                                "role_family": "Engineering",
                                "location": "Remote",
                                "salary": "",
                                "tags": ", ".join(item.get("topics", [])[:5])
                            },
                            "collectedAt": now.isoformat() + "Z"
                        })
            await asyncio.sleep(2)
    except Exception as e:
        print(f"  GitHub jobs error: {e}")
    return jobs

async def fetch_jobs_arbeitnow(session):
    """Arbeitnow free jobs API"""
    jobs = []
    try:
        url = "https://www.arbeitnow.com/api/job-board-api"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                data = await resp.json()
                ai_keywords = ["ai", "machine learning", "data scientist", "nlp", 
                              "deep learning", "python", "ml engineer", "llm"]
                now = datetime.now(timezone.utc)
                cutoff_ts = int((now - timedelta(hours=24)).timestamp())
                
                for job in data.get("data", []):
                    title = job.get("title", "").lower()
                    if any(kw in title for kw in ai_keywords):
                        created_at = job.get("created_at", 0)
                        if isinstance(created_at, int) and created_at >= cutoff_ts:
                            pub_date = datetime.fromtimestamp(created_at, tz=timezone.utc).isoformat()
                            jobs.append({
                                "schemaVersion": "1.0",
                                "recordType": "JOB",
                                "source": {
                                    "name": "Arbeitnow",
                                    "url": job.get("url", "https://www.arbeitnow.com")
                                },
                                "content": {
                                    "company": job.get("company_name", ""),
                                    "title": job.get("title", ""),
                                    "date": pub_date,
                                    "is_remote": job.get("remote", False),
                                    "role_family": "Engineering",
                                    "location": job.get("location", ""),
                                    "salary": "",
                                    "tags": ", ".join(job.get("tags", [])[:5])
                                },
                                "collectedAt": now.isoformat() + "Z"
                            })
    except Exception as e:
        print(f"  Arbeitnow error: {e}")
    return jobs

async def main():
    all_news = []
    all_jobs = []

    print("Starting News + Jobs scraper...")
    print("Freshness: Last 24 hours only\n")

    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:

        # ============ NEWS SOURCES ============
        print("=" * 50)
        print("NEWS SOURCES")
        print("=" * 50)

        # 1. RSS Feeds
        rss_sources = [
            ("https://feeds.feedburner.com/venturebeat/SZYF", "VentureBeat AI"),
            ("https://techcrunch.com/category/artificial-intelligence/feed/", "TechCrunch AI"),
            ("https://www.theverge.com/ai-artificial-intelligence/rss/index.xml", "The Verge AI"),
            ("https://feeds.arstechnica.com/arstechnica/technology-lab", "Ars Technica"),
            ("https://www.wired.com/feed/tag/artificial-intelligence/rss", "Wired AI"),
        ]

        for feed_url, source_name in rss_sources:
            print(f"\n[NEWS] {source_name}...")
            items = await fetch_rss_feed(session, feed_url, source_name)
            all_news.extend(items)
            print(f"  Fresh articles (24hr): {len(items)}")

        # 2. HackerNews AI
        print(f"\n[NEWS] Hacker News AI stories...")
        hn_items = await fetch_hackernews_ai(session)
        all_news.extend(hn_items)
        print(f"  Fresh HN stories: {len(hn_items)}")

        print(f"\n✅ Total fresh news: {len(all_news)}")

        # ============ JOB SOURCES ============
        print("\n" + "=" * 50)
        print("JOB SOURCES")
        print("=" * 50)

        # 1. Remotive
        print("\n[JOBS] Remotive (remote AI jobs)...")
        remotive_jobs = await fetch_jobs_remotive(session)
        all_jobs.extend(remotive_jobs)
        print(f"  Fresh jobs: {len(remotive_jobs)}")

        # 2. Arbeitnow
        print("\n[JOBS] Arbeitnow...")
        arbeitnow_jobs = await fetch_jobs_arbeitnow(session)
        all_jobs.extend(arbeitnow_jobs)
        print(f"  Fresh jobs: {len(arbeitnow_jobs)}")

        # 3. GitHub
        print("\n[JOBS] GitHub job postings...")
        gh_jobs = await fetch_jobs_github(session)
        all_jobs.extend(gh_jobs)
        print(f"  Fresh jobs: {len(gh_jobs)}")

        print(f"\n✅ Total fresh jobs: {len(all_jobs)}")

    # Save outputs
    os.makedirs("output", exist_ok=True)

    # News JSON + CSV
    with open("output/news.json", "w", encoding="utf-8") as f:
        json.dump(all_news, f, indent=2, ensure_ascii=False)

    with open("output/news.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "schemaVersion", "recordType", "source_name", "source_url",
            "title", "description", "published_date", "collectedAt"
        ])
        writer.writeheader()
        for n in all_news:
            writer.writerow({
                "schemaVersion": n["schemaVersion"],
                "recordType": n["recordType"],
                "source_name": n["source"]["name"],
                "source_url": n["source"]["url"],
                "title": n["content"]["title"],
                "description": n["content"].get("description", ""),
                "published_date": n["content"]["published_date"],
                "collectedAt": n["collectedAt"]
            })

    # Jobs JSON + CSV
    with open("output/jobs.json", "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, indent=2, ensure_ascii=False)

    with open("output/jobs.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "schemaVersion", "recordType", "source_name", "source_url",
            "company", "title", "date", "is_remote", "role_family",
            "location", "salary", "collectedAt"
        ])
        writer.writeheader()
        for j in all_jobs:
            writer.writerow({
                "schemaVersion": j["schemaVersion"],
                "recordType": j["recordType"],
                "source_name": j["source"]["name"],
                "source_url": j["source"]["url"],
                "company": j["content"]["company"],
                "title": j["content"]["title"],
                "date": j["content"]["date"],
                "is_remote": j["content"]["is_remote"],
                "role_family": j["content"]["role_family"],
                "location": j["content"].get("location", ""),
                "salary": j["content"].get("salary", ""),
                "collectedAt": j["collectedAt"]
            })

    print(f"\n{'='*50}")
    print(f"✅ News saved: {len(all_news)} articles → output/news.csv")
    print(f"✅ Jobs saved: {len(all_jobs)} jobs → output/jobs.csv")

if __name__ == "__main__":
    asyncio.run(main())