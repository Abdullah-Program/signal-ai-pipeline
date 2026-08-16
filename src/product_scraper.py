import asyncio
import aiohttp
import json
import csv
import os
from datetime import datetime
from tqdm import tqdm

PRICING_MAP = {
    "free": "FREE",
    "open source": "FREE",
    "open-source": "FREE",
    "freemium": "FREEMIUM",
    "free trial": "FREEMIUM",
    "pro": "PAID",
    "paid": "PAID",
    "premium": "PAID",
    "enterprise": "ENTERPRISE",
    "contact sales": "ENTERPRISE",
}

def detect_pricing(text):
    if not text:
        return "FREEMIUM"
    text_lower = text.lower()
    for keyword, model in PRICING_MAP.items():
        if keyword in text_lower:
            return model
    return "FREEMIUM"

def get_canonical_startup(org_name):
    canonical_map = {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "google": "Google",
        "meta-llama": "Meta",
        "meta": "Meta",
        "mistralai": "Mistral AI",
        "microsoft": "Microsoft",
        "huggingface": "Hugging Face",
        "stabilityai": "Stability AI",
        "cohere-ai": "Cohere",
        "01-ai": "01.AI",
        "qwen": "Alibaba",
        "deepseek-ai": "DeepSeek",
        "nvidia": "NVIDIA",
        "apple": "Apple",
        "amazon": "Amazon",
        "ibm": "IBM",
    }
    return canonical_map.get(org_name.lower(), org_name)

async def fetch_hf_models_as_products(session):
    """HuggingFace models = AI products"""
    products = []
    seen = set()

    endpoints = [
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=text-generation",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=image-generation",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=text-to-image",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=summarization",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=translation",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=question-answering",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=conversational",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=text-classification",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=token-classification",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=image-classification",
        "https://huggingface.co/api/models?sort=likes&direction=-1&limit=100&filter=text-generation",
        "https://huggingface.co/api/models?sort=likes&direction=-1&limit=100&filter=text-to-image",
        "https://huggingface.co/api/models?sort=likes&direction=-1&limit=100&filter=image-to-text",
        "https://huggingface.co/api/models?sort=likes&direction=-1&limit=100&filter=automatic-speech-recognition",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=object-detection",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=feature-extraction",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=fill-mask",
        "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=100&filter=sentence-similarity",
        "https://huggingface.co/api/models?sort=likes&direction=-1&limit=100&filter=reinforcement-learning",
        "https://huggingface.co/api/models?sort=likes&direction=-1&limit=100&filter=video-classification",
    ]

    for url in endpoints:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    models = await resp.json()
                    for m in models:
                        model_id = m.get("id", "")
                        if model_id and model_id not in seen:
                            seen.add(model_id)
                            parts = model_id.split("/")
                            org = parts[0] if len(parts) > 1 else "unknown"
                            model_name = parts[1] if len(parts) > 1 else parts[0]
                            tags = m.get("tags", [])
                            pricing = "FREE" if "open-source" in tags or m.get("private") == False else "FREEMIUM"

                            products.append({
                                "schemaVersion": "1.0",
                                "recordType": "PRODUCT",
                                "source": {
                                    "name": "HuggingFace",
                                    "url": f"https://huggingface.co/{model_id}"
                                },
                                "content": {
                                    "productName": model_name,
                                    "startupName": get_canonical_startup(org),
                                    "pricingModel": pricing,
                                    "category": m.get("pipeline_tag", "AI Model"),
                                    "downloads": m.get("downloads", 0),
                                    "likes": m.get("likes", 0),
                                    "tags": ", ".join(tags[:5]),
                                    "description": f"AI model for {m.get('pipeline_tag','inference')} by {org}"
                                },
                                "collectedAt": datetime.utcnow().isoformat() + "Z"
                            })
            await asyncio.sleep(0.5)
            print(f"  Products so far: {len(products)}")
        except Exception as e:
            print(f"  Error: {e}")

    return products

async def fetch_hf_spaces_as_products(session):
    """HuggingFace Spaces = deployed AI apps/products"""
    products = []
    seen = set()

    urls = [
        "https://huggingface.co/api/spaces?sort=likes&direction=-1&limit=100",
        "https://huggingface.co/api/spaces?sort=likes&direction=-1&limit=100&filter=gradio",
        "https://huggingface.co/api/spaces?sort=likes&direction=-1&limit=100&filter=streamlit",
        "https://huggingface.co/api/spaces?sort=createdAt&direction=-1&limit=100",
        "https://huggingface.co/api/spaces?sort=likes&direction=-1&limit=100&p=1",
        "https://huggingface.co/api/spaces?sort=likes&direction=-1&limit=100&p=2",
        "https://huggingface.co/api/spaces?sort=likes&direction=-1&limit=100&p=3",
    ]

    for url in urls:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    spaces = await resp.json()
                    for s in spaces:
                        space_id = s.get("id", "")
                        if space_id and space_id not in seen:
                            seen.add(space_id)
                            parts = space_id.split("/")
                            org = parts[0] if len(parts) > 1 else "unknown"
                            app_name = parts[1] if len(parts) > 1 else parts[0]

                            products.append({
                                "schemaVersion": "1.0",
                                "recordType": "PRODUCT",
                                "source": {
                                    "name": "HuggingFace Spaces",
                                    "url": f"https://huggingface.co/spaces/{space_id}"
                                },
                                "content": {
                                    "productName": app_name,
                                    "startupName": get_canonical_startup(org),
                                    "pricingModel": "FREE",
                                    "category": "AI Application",
                                    "downloads": 0,
                                    "likes": s.get("likes", 0),
                                    "tags": "",
                                    "description": f"AI app deployed on HuggingFace Spaces by {org}"
                                },
                                "collectedAt": datetime.utcnow().isoformat() + "Z"
                            })
            await asyncio.sleep(0.5)
            print(f"  Spaces products so far: {len(products)}")
        except Exception as e:
            print(f"  Spaces error: {e}")

    return products

async def fetch_pwc_methods(session):
    """Papers with Code - Methods as products"""
    products = []
    seen = set()

    try:
        pages = [1, 2, 3, 4, 5]
        for page in pages:
            url = f"https://paperswithcode.com/api/v1/methods/?page={page}&items_per_page=50"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for m in data.get("results", []):
                        name = m.get("name", "")
                        if name and name not in seen:
                            seen.add(name)
                            products.append({
                                "schemaVersion": "1.0",
                                "recordType": "PRODUCT",
                                "source": {
                                    "name": "Papers With Code",
                                    "url": f"https://paperswithcode.com/method/{m.get('id','')}"
                                },
                                "content": {
                                    "productName": name,
                                    "startupName": m.get("paper", {}).get("authors", ["Research Community"])[0] if isinstance(m.get("paper"), dict) else "Research Community",
                                    "pricingModel": "FREE",
                                    "category": "AI Method / Algorithm",
                                    "downloads": 0,
                                    "likes": m.get("paper", {}).get("stars", 0) if isinstance(m.get("paper"), dict) else 0,
                                    "tags": m.get("full_name", ""),
                                    "description": m.get("description", "")[:300] if m.get("description") else ""
                                },
                                "collectedAt": datetime.utcnow().isoformat() + "Z"
                            })
            await asyncio.sleep(1)
            print(f"  PWC methods so far: {len(products)}")
    except Exception as e:
        print(f"  PWC error: {e}")

    return products

async def fetch_pwc_datasets(session):
    """Papers with Code datasets as products"""
    products = []
    seen = set()
    try:
        for page in range(1, 6):
            url = f"https://paperswithcode.com/api/v1/datasets/?page={page}&items_per_page=50"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for d in data.get("results", []):
                        name = d.get("name", "")
                        if name and name not in seen:
                            seen.add(name)
                            products.append({
                                "schemaVersion": "1.0",
                                "recordType": "PRODUCT",
                                "source": {
                                    "name": "Papers With Code Datasets",
                                    "url": d.get("url", "https://paperswithcode.com/datasets")
                                },
                                "content": {
                                    "productName": name,
                                    "startupName": "Research Community",
                                    "pricingModel": "FREE",
                                    "category": "AI Dataset",
                                    "downloads": 0,
                                    "likes": 0,
                                    "tags": "",
                                    "description": d.get("description", "")[:300] if d.get("description") else ""
                                },
                                "collectedAt": datetime.utcnow().isoformat() + "Z"
                            })
            await asyncio.sleep(1)
            print(f"  PWC datasets so far: {len(products)}")
    except Exception as e:
        print(f"  PWC datasets error: {e}")
    return products

async def main():
    all_products = []
    seen_ids = set()

    print("Starting Product scraper...")
    print("Sources: HuggingFace Models + Spaces + PWC Methods + PWC Datasets\n")

    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:

        print("[SOURCE 1] HuggingFace Models as Products...")
        hf_products = await fetch_hf_models_as_products(session)
        for p in hf_products:
            uid = p["source"]["url"]
            if uid not in seen_ids:
                seen_ids.add(uid)
                all_products.append(p)
        print(f"  ✅ Total: {len(all_products)}\n")

        print("[SOURCE 2] HuggingFace Spaces as Products...")
        hf_spaces = await fetch_hf_spaces_as_products(session)
        for p in hf_spaces:
            uid = p["source"]["url"]
            if uid not in seen_ids:
                seen_ids.add(uid)
                all_products.append(p)
        print(f"  ✅ Total: {len(all_products)}\n")

        print("[SOURCE 3] Papers With Code Methods...")
        pwc_methods = await fetch_pwc_methods(session)
        for p in pwc_methods:
            uid = p["source"]["url"]
            if uid not in seen_ids:
                seen_ids.add(uid)
                all_products.append(p)
        print(f"  ✅ Total: {len(all_products)}\n")

        print("[SOURCE 4] Papers With Code Datasets...")
        pwc_datasets = await fetch_pwc_datasets(session)
        for p in pwc_datasets:
            uid = p["source"]["url"]
            if uid not in seen_ids:
                seen_ids.add(uid)
                all_products.append(p)
        print(f"  ✅ Total: {len(all_products)}\n")

    os.makedirs("output", exist_ok=True)

    with open("output/products.json", "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)

    with open("output/products.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "schemaVersion", "recordType", "source_name", "source_url",
            "productName", "startupName", "pricingModel", "category",
            "downloads", "likes", "collectedAt"
        ])
        writer.writeheader()
        for p in all_products:
            writer.writerow({
                "schemaVersion": p["schemaVersion"],
                "recordType": p["recordType"],
                "source_name": p["source"]["name"],
                "source_url": p["source"]["url"],
                "productName": p["content"]["productName"],
                "startupName": p["content"]["startupName"],
                "pricingModel": p["content"]["pricingModel"],
                "category": p["content"]["category"],
                "downloads": p["content"].get("downloads", 0),
                "likes": p["content"].get("likes", 0),
                "collectedAt": p["collectedAt"]
            })

    print(f"\n✅ Done! Total products: {len(all_products)}")
    print(f"📁 Saved to output/products.json + products.csv")

if __name__ == "__main__":
    asyncio.run(main())