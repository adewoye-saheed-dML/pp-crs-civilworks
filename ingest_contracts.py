
import requests
import pandas as pd
import time
import os
import json
from datetime import datetime


API_URL = "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search"

START_DATE = "2025-01-01"
END_DATE   = "2025-12-31"

OUTPUT_DIR = "data"
OUTPUT_FILE = f"{OUTPUT_DIR}/2025_construction_contracts.csv"
CURSOR_FILE = f"{OUTPUT_DIR}/last_cursor.txt"

PAGE_LIMIT = 100
SLEEP_SECONDS = 0.7
MAX_RETRIES = 5

# Civil / Construction CPV prefixes
CIVIL_WORKS_CPVS = [
    "45",   # Construction work (broad – intentional)
    "71"    # Engineering & construction-related services
]


# SAFE REQUEST HANDLER

def safe_get(url, params=None, retries=MAX_RETRIES, backoff=2):
    for attempt in range(retries):
        try:
            return requests.get(url, params=params, timeout=40)
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Network error ({attempt+1}/{retries}): {e}")
            time.sleep(backoff * (attempt + 1))
    raise RuntimeError("Max retries exceeded – aborting request")


# HELPERS

def normalize_cpv(raw):
    if not raw:
        return "UNKNOWN"
    return "".join(c for c in str(raw) if c.isdigit()) or "UNKNOWN"


def extract_cpv(tender, release):
    classification = None

    if tender:
        classification = tender.get("classification")

    if isinstance(classification, dict):
        return normalize_cpv(classification.get("id"))

    if isinstance(classification, list):
        for c in classification:
            if isinstance(c, dict) and c.get("id"):
                return normalize_cpv(c.get("id"))

    if isinstance(release.get("classification"), dict):
        return normalize_cpv(release["classification"].get("id"))

    return "UNKNOWN"


def extract_value(tender, release):
    for obj in (tender, release):
        if not obj:
            continue
        value = obj.get("value")
        if isinstance(value, dict) and value.get("amount") is not None:
            return value.get("amount", 0), value.get("currency", "GBP")
    return 0, "GBP"


def load_last_cursor():
    if os.path.exists(CURSOR_FILE):
        with open(CURSOR_FILE, "r") as f:
            return f.read().strip()
    return None


def save_last_cursor(cursor_url):
    with open(CURSOR_FILE, "w") as f:
        f.write(cursor_url)



# MAIN INGESTION

def fetch_2025_construction_contracts():
    print("\n--- UK Contracts Finder | 2025 Construction Ingestion ---")
    print(f"Date range: {START_DATE} → {END_DATE}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_contracts = []
    seen_ocids = set()

    params = {
        "limit": PAGE_LIMIT,
        "publishedFrom": START_DATE,
        "publishedTo": END_DATE
    }

    next_url = load_last_cursor()
    first_page = next_url is None
    page_count = 0

    try:
        while True:
            page_count += 1
            print(f"Fetching page {page_count}... (Saved {len(all_contracts)})")

            if first_page:
                response = safe_get(API_URL, params=params)
                first_page = False
            else:
                response = safe_get(next_url)

            if response.status_code != 200:
                print("[ERROR] API returned:", response.status_code)
                break

            data = response.json()
            releases = data.get("releases", [])

            if not releases:
                print("No more releases. End reached.")
                break

            for release in releases:
                ocid = release.get("ocid")
                if not ocid or ocid in seen_ocids:
                    continue

                tender = release.get("tender", {})
                cpv = extract_cpv(tender, release)

                if cpv == "UNKNOWN":
                    continue

                if not any(cpv.startswith(prefix) for prefix in CIVIL_WORKS_CPVS):
                    continue

                amount, currency = extract_value(tender, release)

                buyer = release.get("buyer") or {}
                parties = release.get("parties") or []

                buyer_country = "GB"
                for p in parties:
                    if p.get("id") == buyer.get("id"):
                        buyer_country = (p.get("address") or {}).get("countryName", "GB")

                all_contracts.append({
                    "ocid": ocid,
                    "title": tender.get("title", "Unknown"),
                    "description": (tender.get("description") or "")[:500],
                    "cpv_code": cpv,
                    "value_amount": amount,
                    "currency": currency,
                    "published_date": release.get("date"),
                    "buyer_name": buyer.get("name", "Unknown"),
                    "buyer_country": buyer_country,
                    "tender_status": tender.get("status"),
                    "source": "UK Contracts Finder"
                })

                seen_ocids.add(ocid)

            # Pagination 
            if data.get("links") and data["links"].get("next"):
                next_url = data["links"]["next"]
                save_last_cursor(next_url)
            else:
                print("Pagination complete.")
                break

            time.sleep(SLEEP_SECONDS)

    except Exception as e:
        print("[CRITICAL] Ingestion interrupted:", e)


    # SAVE OUTPUT 
   
    print(f"\n--- DONE. Total 2025 construction contracts: {len(all_contracts)} ---")

    if all_contracts:
        df = pd.DataFrame(all_contracts)
        df.drop_duplicates(subset="ocid", inplace=True)
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"Saved to {OUTPUT_FILE}")
        print(df[["title", "value_amount", "cpv_code"]].head(10))
    else:
        print("No matching contracts found.")


if __name__ == "__main__":
    fetch_2025_construction_contracts()
