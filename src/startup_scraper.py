import asyncio
import aiohttp
import json
import csv
import os
from datetime import datetime
from tqdm import tqdm

async def fetch_huggingface_models_as_products(session):
    """HuggingFace public API - free, no auth"""
    startups = []
    seen = set()
    
    endpoints = [
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=text-generation",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=text-classification",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=image-classification",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=object-detection",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=summarization",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=translation",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=question-answering",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=conversational",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=feature-extraction",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=token-classification",
        "https://huggingface.co/api/models?sort=likes&direction=-1&limit=100&filter=text-generation",
        "https://huggingface.co/api/models?sort=likes&direction=-1&limit=100&filter=image-to-text",
    ]
    
    for url in endpoints:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    models = await resp.json()
                    for m in models:
                        org = m.get("id", "").split("/")[0] if "/" in m.get("id","") else m.get("id","")
                        if org and org not in seen:
                            seen.add(org)
                            startups.append({
                                "schemaVersion": "1.0",
                                "recordType": "STARTUP",
                                "source": {
                                    "name": "HuggingFace",
                                    "url": f"https://huggingface.co/{org}"
                                },
                                "content": {
                                    "entityName": org,
                                    "slug": org.lower(),
                                    "employeeCount": None,
                                    "founded": None,
                                    "location": None,
                                    "totalFunding": None,
                                    "category": "AI/ML Organization",
                                    "description": f"AI organization on HuggingFace with models in {m.get('pipeline_tag','AI')}"
                                },
                                "collectedAt": datetime.utcnow().isoformat() + "Z"
                            })
            await asyncio.sleep(0.5)
            print(f"  HF orgs so far: {len(startups)}")
        except Exception as e:
            print(f"  Error: {e}")
    
    return startups

async def fetch_hf_spaces_orgs(session):
    """HuggingFace Spaces - more orgs"""
    startups = []
    seen = set()
    urls = [
        "https://huggingface.co/api/spaces?sort=likes&direction=-1&limit=100",
        "https://huggingface.co/api/spaces?sort=likes&direction=-1&limit=100&filter=gradio",
        "https://huggingface.co/api/spaces?sort=likes&direction=-1&limit=100&filter=streamlit",
    ]
    for url in urls:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    spaces = await resp.json()
                    for s in spaces:
                        org = s.get("id","").split("/")[0] if "/" in s.get("id","") else ""
                        if org and org not in seen:
                            seen.add(org)
                            startups.append({
                                "schemaVersion": "1.0",
                                "recordType": "STARTUP",
                                "source": {
                                    "name": "HuggingFace Spaces",
                                    "url": f"https://huggingface.co/{org}"
                                },
                                "content": {
                                    "entityName": org,
                                    "slug": org.lower(),
                                    "employeeCount": None,
                                    "founded": None,
                                    "location": None,
                                    "totalFunding": None,
                                    "category": "AI/ML Organization",
                                    "description": "Organization building AI apps on HuggingFace Spaces"
                                },
                                "collectedAt": datetime.utcnow().isoformat() + "Z"
                            })
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"  Spaces error: {e}")
    return startups

async def fetch_hf_datasets_orgs(session):
    """HuggingFace Datasets orgs"""
    startups = []
    seen = set()
    urls = [
        "https://huggingface.co/api/datasets?sort=downloads&direction=-1&limit=100",
        "https://huggingface.co/api/datasets?sort=likes&direction=-1&limit=100",
        "https://huggingface.co/api/datasets?sort=downloads&direction=-1&limit=100&filter=text",
        "https://huggingface.co/api/datasets?sort=downloads&direction=-1&limit=100&filter=image",
    ]
    for url in urls:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    datasets = await resp.json()
                    for d in datasets:
                        org = d.get("id","").split("/")[0] if "/" in d.get("id","") else ""
                        if org and org not in seen:
                            seen.add(org)
                            startups.append({
                                "schemaVersion": "1.0",
                                "recordType": "STARTUP",
                                "source": {
                                    "name": "HuggingFace Datasets",
                                    "url": f"https://huggingface.co/{org}"
                                },
                                "content": {
                                    "entityName": org,
                                    "slug": org.lower(),
                                    "employeeCount": None,
                                    "founded": None,
                                    "location": None,
                                    "totalFunding": None,
                                    "category": "AI/ML Organization",
                                    "description": "Organization publishing AI datasets on HuggingFace"
                                },
                                "collectedAt": datetime.utcnow().isoformat() + "Z"
                            })
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"  Datasets error: {e}")
    return startups

async def fetch_arxiv_orgs(session):
    """Extract unique orgs from arxiv papers already scraped"""
    startups = []
    seen = set()
    try:
        with open("output/research_papers.json", "r", encoding="utf-8") as f:
            papers = json.load(f)
        
        for paper in papers:
            url = paper.get("content", {}).get("paper_url", "")
            authors = paper.get("content", {}).get("authors", [])
            topic = paper.get("content", {}).get("topic", "AI Research")
            
            for author in authors:
                # Extract institution from author string
                if "@" in author:
                    domain = author.split("@")[-1].strip()
                    if domain and domain not in seen and len(domain) > 3:
                        seen.add(domain)
                        startups.append({
                            "schemaVersion": "1.0",
                            "recordType": "STARTUP",
                            "source": {
                                "name": "Arxiv Research",
                                "url": url
                            },
                            "content": {
                                "entityName": domain,
                                "slug": domain.lower().replace(".", "-"),
                                "employeeCount": None,
                                "founded": None,
                                "location": None,
                                "totalFunding": None,
                                "category": "Research Institution",
                                "description": f"Institution publishing AI research on topic: {topic}"
                            },
                            "collectedAt": datetime.utcnow().isoformat() + "Z"
                        })
    except Exception as e:
        print(f"  Arxiv orgs error: {e}")
    return startups

async def fetch_github_ai_topics(session):
    """GitHub orgs from AI topics"""
    startups = []
    seen = set()
    topics = ["artificial-intelligence","machine-learning","deep-learning",
              "large-language-models","generative-ai","llm","nlp",
              "computer-vision","reinforcement-learning","pytorch","tensorflow"]
    
    for topic in topics:
        try:
            url = f"https://api.github.com/search/repositories?q=topic:{topic}&sort=stars&order=desc&per_page=50"
            headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Mozilla/5.0"}
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("items", []):
                        owner = item.get("owner", {})
                        org_name = owner.get("login", "")
                        if org_name and org_name not in seen:
                            seen.add(org_name)
                            startups.append({
                                "schemaVersion": "1.0",
                                "recordType": "STARTUP",
                                "source": {
                                    "name": "GitHub",
                                    "url": f"https://github.com/{org_name}"
                                },
                                "content": {
                                    "entityName": org_name,
                                    "slug": org_name.lower(),
                                    "employeeCount": None,
                                    "founded": None,
                                    "location": item.get("language"),
                                    "totalFunding": None,
                                    "category": "AI/ML Organization",
                                    "description": item.get("description", "")[:200] if item.get("description") else ""
                                },
                                "collectedAt": datetime.utcnow().isoformat() + "Z"
                            })
            await asyncio.sleep(2)
            print(f"  GitHub orgs so far: {len(startups)}")
        except Exception as e:
            print(f"  GitHub error {topic}: {e}")
    
    return startups

async def main():
    all_startups = []
    seen_names = set()

    print("Starting Startup scraper v2...")
    print("Sources: HuggingFace Models + Spaces + Datasets + GitHub + Arxiv\n")

    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:

        print("[SOURCE 1] HuggingFace Model Organizations...")
        hf_models = await fetch_huggingface_models_as_products(session)
        for s in hf_models:
            name = s["content"]["entityName"]
            if name and name not in seen_names:
                seen_names.add(name)
                all_startups.append(s)
        print(f"  ✅ Total: {len(all_startups)}\n")

        print("[SOURCE 2] HuggingFace Spaces Organizations...")
        hf_spaces = await fetch_hf_spaces_orgs(session)
        for s in hf_spaces:
            name = s["content"]["entityName"]
            if name and name not in seen_names:
                seen_names.add(name)
                all_startups.append(s)
        print(f"  ✅ Total: {len(all_startups)}\n")

        print("[SOURCE 3] HuggingFace Dataset Organizations...")
        hf_datasets = await fetch_hf_datasets_orgs(session)
        for s in hf_datasets:
            name = s["content"]["entityName"]
            if name and name not in seen_names:
                seen_names.add(name)
                all_startups.append(s)
        print(f"  ✅ Total: {len(all_startups)}\n")

        print("[SOURCE 4] GitHub AI Topic Organizations...")
        gh_orgs = await fetch_github_ai_topics(session)
        for s in gh_orgs:
            name = s["content"]["entityName"]
            if name and name not in seen_names:
                seen_names.add(name)
                all_startups.append(s)
        print(f"  ✅ Total: {len(all_startups)}\n")

        print("[SOURCE 5] Arxiv Paper Organizations...")
        arxiv_orgs = await fetch_arxiv_orgs(session)
        for s in arxiv_orgs:
            name = s["content"]["entityName"]
            if name and name not in seen_names:
                seen_names.add(name)
                all_startups.append(s)
        print(f"  ✅ Total: {len(all_startups)}\n")

    print(f"\nFinal count: {len(all_startups)}")

    os.makedirs("output", exist_ok=True)

    with open("output/startups.json", "w", encoding="utf-8") as f:
        json.dump(all_startups, f, indent=2, ensure_ascii=False)

    with open("output/startups.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "schemaVersion","recordType","source_name","source_url",
            "entityName","employeeCount","founded","location",
            "totalFunding","category","collectedAt"
        ])
        writer.writeheader()
        for s in all_startups:
            writer.writerow({
                "schemaVersion": s["schemaVersion"],
                "recordType": s["recordType"],
                "source_name": s["source"]["name"],
                "source_url": s["source"]["url"],
                "entityName": s["content"]["entityName"],
                "employeeCount": s["content"].get("employeeCount",""),
                "founded": s["content"].get("founded",""),
                "location": s["content"].get("location",""),
                "totalFunding": s["content"].get("totalFunding",""),
                "category": s["content"].get("category",""),
                "collectedAt": s["collectedAt"]
            })

    print(f"\n✅ Done! Total startups: {len(all_startups)}")
    print(f"📁 Saved to output/startups.json + startups.csv")

if __name__ == "__main__":
    asyncio.run(main())