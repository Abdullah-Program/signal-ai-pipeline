import asyncio
import aiohttp
import json
import csv
import os
import time
from datetime import datetime
from tqdm import tqdm

BASE_URL = "http://export.arxiv.org/api/query"

TOPICS = [
    "large language models",
    "generative ai",
    "reinforcement learning",
    "computer vision transformer",
    "diffusion models",
    "retrieval augmented generation",
    "multimodal learning",
    "graph neural networks",
    "federated learning",
    "ai alignment",
    "natural language processing",
    "object detection deep learning",
    "autonomous agents llm",
    "speech recognition transformer",
    "neural architecture search",
    "knowledge graph embedding",
    "contrastive learning",
    "zero shot learning",
    "prompt engineering",
    "ai safety"
]
async def fetch_papers(session, topic, start=0, max_results=100):
    params = {
        "search_query": f"all:{topic}",
        "start": start,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }
    try:
        async with session.get(BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                return await resp.text()
            else:
                print(f"[ERROR] Status {resp.status} for topic: {topic}")
                return None
    except Exception as e:
        print(f"[ERROR] {topic}: {e}")
        return None

def parse_papers(xml_text, topic):
    import xml.etree.ElementTree as ET
    papers = []
    try:
        root = ET.fromstring(xml_text)
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'arxiv': 'http://arxiv.org/schemas/atom'
        }
        entries = root.findall('atom:entry', ns)
        for entry in entries:
            title = entry.find('atom:title', ns)
            summary = entry.find('atom:summary', ns)
            published = entry.find('atom:published', ns)
            paper_url = entry.find('atom:id', ns)
            authors = entry.findall('atom:author', ns)

            author_names = []
            for a in authors:
                name = a.find('atom:name', ns)
                if name is not None:
                    author_names.append(name.text.strip())

            papers.append({
                "schemaVersion": "1.0",
                "recordType": "RESEARCH_PAPER",
                "content": {
                    "title": title.text.strip() if title is not None else "",
                    "authors": author_names,
                    "paper_url": paper_url.text.strip() if paper_url is not None else "",
                    "github_url": "",
                    "github_stars": 0,
                    "published_date": published.text.strip() if published is not None else "",
                    "topic": topic,
                    "abstract": summary.text.strip()[:500] if summary is not None else ""
                },
                "collectedAt": datetime.utcnow().isoformat() + "Z"
            })
    except Exception as e:
        print(f"[PARSE ERROR] {e}")
    return papers

async def get_github_stars(session, github_url):
    if not github_url:
        return 0
    try:
        repo_path = github_url.replace("https://github.com/", "").strip("/")
        api_url = f"https://api.github.com/repos/{repo_path}"
        async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("stargazers_count", 0)
    except:
        pass
    return 0

async def fetch_pwc_github(session, arxiv_id):
    try:
        clean_id = arxiv_id.split("/abs/")[-1].strip()
        url = f"https://paperswithcode.com/api/v1/papers/?arxiv_id={clean_id}"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.json()
                results = data.get("results", [])
                if results:
                    repo_url = results[0].get("repository", {})
                    if isinstance(repo_url, dict):
                        return repo_url.get("url", "")
                    return str(repo_url) if repo_url else ""
    except:
        pass
    return ""

async def main():
    all_papers = []
    seen_urls = set()

    print("Starting Arxiv paper scraper...")
    print(f"Topics: {len(TOPICS)} | Target: 1000+ papers\n")

    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:
        for topic in TOPICS:
            print(f"\n[TOPIC] {topic}")
            for start in range(0, 200, 100):
                xml_data = await fetch_papers(session, topic, start=start, max_results=100)
                if xml_data:
                    papers = parse_papers(xml_data, topic)
                    new_papers = []
                    for p in papers:
                        url = p["content"]["paper_url"]
                        if url not in seen_urls:
                            seen_urls.add(url)
                            new_papers.append(p)

                    print(f"  Fetched {len(new_papers)} unique papers (start={start})")

                    # Fetch GitHub links from Papers with Code
                    for paper in tqdm(new_papers, desc="  GitHub lookup"):
                        arxiv_id = paper["content"]["paper_url"]
                        github_url = await fetch_pwc_github(session, arxiv_id)
                        paper["content"]["github_url"] = github_url
                        if github_url:
                            stars = await get_github_stars(session, github_url)
                            paper["content"]["github_stars"] = stars
                        await asyncio.sleep(0.3)

                    all_papers.extend(new_papers)
                    print(f"  Total so far: {len(all_papers)}")

                await asyncio.sleep(3)

            if len(all_papers) >= 1000:
                print(f"\n[DONE] 1000+ papers collected!")
                break

    # Save to JSON
    os.makedirs("output", exist_ok=True)
    with open("output/research_papers.json", "w", encoding="utf-8") as f:
        json.dump(all_papers, f, indent=2, ensure_ascii=False)

    # Save to CSV
    with open("output/research_papers.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "schemaVersion", "recordType", "title", "authors",
            "paper_url", "github_url", "github_stars", "published_date", "collectedAt"
        ])
        writer.writeheader()
        for p in all_papers:
            writer.writerow({
                "schemaVersion": p["schemaVersion"],
                "recordType": p["recordType"],
                "title": p["content"]["title"],
                "authors": ", ".join(p["content"]["authors"]),
                "paper_url": p["content"]["paper_url"],
                "github_url": p["content"]["github_url"],
                "github_stars": p["content"]["github_stars"],
                "published_date": p["content"]["published_date"],
                "collectedAt": p["collectedAt"]
            })

    print(f"\n✅ Done! Total papers: {len(all_papers)}")
    print(f"📁 Saved to output/research_papers.json")
    print(f"📁 Saved to output/research_papers.csv")

if __name__ == "__main__":
    asyncio.run(main())