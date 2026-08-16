import json
import csv
import os
from rapidfuzz import fuzz, process
from datetime import datetime

# Seed list of 50 canonical AI entities
CANONICAL_ENTITIES = [
    "OpenAI", "Anthropic", "Google DeepMind", "Meta AI", "Microsoft",
    "Hugging Face", "Mistral AI", "Cohere", "Stability AI", "Inflection AI",
    "Perplexity AI", "Scale AI", "Weights & Biases", "Pinecone", "Weaviate",
    "LangChain", "LlamaIndex", "Replicate", "Together AI", "Anyscale",
    "Databricks", "Snowflake", "NVIDIA", "AMD", "Intel",
    "Amazon Web Services", "Google Cloud", "Microsoft Azure", "IBM", "Salesforce",
    "Palantir", "C3.ai", "DataRobot", "H2O.ai", "Dataiku",
    "Runway", "Synthesia", "Jasper", "Writer", "Midjourney",
    "Character AI", "Adept", "Fireworks AI", "Modal", "Lightning AI",
    "Roboflow", "Label Studio", "Encord", "Qdrant", "ChromaDB"
]

# Alias map for known variants
ALIAS_MAP = {
    "openai inc": "OpenAI",
    "open ai": "OpenAI",
    "openai, inc.": "OpenAI",
    "openai inc.": "OpenAI",
    "anthropic pbc": "Anthropic",
    "anthropic, inc": "Anthropic",
    "google deepmind": "Google DeepMind",
    "deepmind": "Google DeepMind",
    "google deep mind": "Google DeepMind",
    "meta platforms": "Meta AI",
    "meta ai research": "Meta AI",
    "facebook ai": "Meta AI",
    "fair": "Meta AI",
    "microsoft corporation": "Microsoft",
    "microsoft corp": "Microsoft",
    "ms research": "Microsoft",
    "huggingface": "Hugging Face",
    "hugging-face": "Hugging Face",
    "hf": "Hugging Face",
    "mistralai": "Mistral AI",
    "mistral": "Mistral AI",
    "stability": "Stability AI",
    "stabilityai": "Stability AI",
    "perplexity": "Perplexity AI",
    "weights and biases": "Weights & Biases",
    "wandb": "Weights & Biases",
    "aws": "Amazon Web Services",
    "amazon aws": "Amazon Web Services",
    "gcp": "Google Cloud",
    "google cloud platform": "Google Cloud",
    "azure": "Microsoft Azure",
    "microsoft azure ml": "Microsoft Azure",
    "nvidia corporation": "NVIDIA",
    "nvidia corp": "NVIDIA",
    "ibm watson": "IBM",
    "ibm research": "IBM",
    "salesforce einstein": "Salesforce",
    "sfdc": "Salesforce",
    "langchain inc": "LangChain",
    "llamaindex": "LlamaIndex",
    "llama index": "LlamaIndex",
    "character.ai": "Character AI",
    "c.ai": "Character AI",
    "h2o": "H2O.ai",
    "h2o ai": "H2O.ai",
    "c3 ai": "C3.ai",
    "datarobot inc": "DataRobot",
    "chroma": "ChromaDB",
    "chromadb": "ChromaDB",
}

THRESHOLD = 85  # Fuzzy match threshold

def resolve_entity(raw_name):
    """Resolve a raw entity name to its canonical form"""
    if not raw_name or len(raw_name.strip()) < 2:
        return raw_name, "NO_MATCH", 0

    cleaned = raw_name.strip().lower()

    # 1. Exact alias match
    if cleaned in ALIAS_MAP:
        return ALIAS_MAP[cleaned], "ALIAS_MATCH", 100

    # 2. Fuzzy match against canonical list
    result = process.extractOne(
        raw_name,
        CANONICAL_ENTITIES,
        scorer=fuzz.token_sort_ratio
    )

    if result and result[1] >= THRESHOLD:
        return result[0], "FUZZY_MATCH", result[1]

    # 3. Partial ratio fallback
    result2 = process.extractOne(
        raw_name,
        CANONICAL_ENTITIES,
        scorer=fuzz.partial_ratio
    )

    if result2 and result2[1] >= 90:
        return result2[0], "PARTIAL_MATCH", result2[1]

    return raw_name, "NO_MATCH", result[1] if result else 0

def process_startups():
    """Resolve entity names in startups"""
    mappings = []
    try:
        with open("output/startups.json", "r", encoding="utf-8") as f:
            startups = json.load(f)

        for s in startups:
            raw = s["content"]["entityName"]
            canonical, match_type, score = resolve_entity(raw)
            s["content"]["canonicalName"] = canonical
            s["content"]["matchType"] = match_type
            s["content"]["matchScore"] = score

            mappings.append({
                "recordType": "STARTUP",
                "rawName": raw,
                "canonicalName": canonical,
                "matchType": match_type,
                "matchScore": score
            })

        with open("output/startups_resolved.json", "w", encoding="utf-8") as f:
            json.dump(startups, f, indent=2, ensure_ascii=False)

        print(f"  ✅ Startups resolved: {len(startups)}")
    except Exception as e:
        print(f"  Error: {e}")
    return mappings

def process_products():
    """Resolve startup names in products"""
    mappings = []
    try:
        with open("output/products.json", "r", encoding="utf-8") as f:
            products = json.load(f)

        for p in products:
            raw = p["content"]["startupName"]
            canonical, match_type, score = resolve_entity(raw)
            p["content"]["canonicalStartupName"] = canonical
            p["content"]["matchType"] = match_type
            p["content"]["matchScore"] = score

            mappings.append({
                "recordType": "PRODUCT",
                "rawName": raw,
                "canonicalName": canonical,
                "matchType": match_type,
                "matchScore": score
            })

        with open("output/products_resolved.json", "w", encoding="utf-8") as f:
            json.dump(products, f, indent=2, ensure_ascii=False)

        print(f"  ✅ Products resolved: {len(products)}")
    except Exception as e:
        print(f"  Error: {e}")
    return mappings

def process_jobs():
    """Resolve company names in jobs"""
    mappings = []
    try:
        with open("output/jobs.json", "r", encoding="utf-8") as f:
            jobs = json.load(f)

        for j in jobs:
            raw = j["content"]["company"]
            canonical, match_type, score = resolve_entity(raw)
            j["content"]["canonicalCompany"] = canonical
            j["content"]["matchType"] = match_type
            j["content"]["matchScore"] = score

            mappings.append({
                "recordType": "JOB",
                "rawName": raw,
                "canonicalName": canonical,
                "matchType": match_type,
                "matchScore": score
            })

        with open("output/jobs_resolved.json", "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)

        print(f"  ✅ Jobs resolved: {len(jobs)}")
    except Exception as e:
        print(f"  Error: {e}")
    return mappings

def save_entity_mapping_log(all_mappings):
    """Save entity mapping log CSV"""
    with open("output/entity_mapping_log.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "recordType", "rawName", "canonicalName", "matchType", "matchScore"
        ])
        writer.writeheader()
        writer.writerows(all_mappings)

    # Stats
    total = len(all_mappings)
    alias = sum(1 for m in all_mappings if m["matchType"] == "ALIAS_MATCH")
    fuzzy = sum(1 for m in all_mappings if m["matchType"] == "FUZZY_MATCH")
    partial = sum(1 for m in all_mappings if m["matchType"] == "PARTIAL_MATCH")
    no_match = sum(1 for m in all_mappings if m["matchType"] == "NO_MATCH")

    print(f"\n📊 Entity Resolution Stats:")
    print(f"  Total processed : {total}")
    print(f"  Alias matches   : {alias}")
    print(f"  Fuzzy matches   : {fuzzy}")
    print(f"  Partial matches : {partial}")
    print(f"  No match        : {no_match}")

def main():
    print("Starting Entity Resolution Engine...")
    print(f"Canonical entities: {len(CANONICAL_ENTITIES)}")
    print(f"Known aliases     : {len(ALIAS_MAP)}\n")

    all_mappings = []

    print("[1] Resolving Startups...")
    all_mappings += process_startups()

    print("[2] Resolving Products...")
    all_mappings += process_products()

    print("[3] Resolving Jobs...")
    all_mappings += process_jobs()

    print("\n[4] Saving Entity Mapping Log...")
    save_entity_mapping_log(all_mappings)

    print(f"\n✅ Done!")
    print(f"📁 output/entity_mapping_log.csv")
    print(f"📁 output/startups_resolved.json")
    print(f"📁 output/products_resolved.json")
    print(f"📁 output/jobs_resolved.json")

if __name__ == "__main__":
    main()