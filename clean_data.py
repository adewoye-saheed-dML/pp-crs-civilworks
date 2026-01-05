import pandas as pd
import os
import re
from collections import defaultdict, Counter

INPUT_FILENAME = "2025_PURE_CIVIL_WORKS_STRICT.csv"
CLEAN_OUTPUT_FILENAME = "2025_CIVIL_WORKS_CLEANED.csv"
BUYER_MAP_FILENAME = "buyer_canonical_map.csv"


def find_file(filename):
    base = os.path.dirname(os.path.abspath(__file__))
    for root, _, files in os.walk(base):
        if filename in files:
            return os.path.join(root, filename)
    return None


def basic_normalize(text):
    if pd.isna(text):
        return ""
    text = str(text).strip().lower()
    text = re.sub(r'\b(ltd\.?|limited)\b', 'limited', text)
    text = re.sub(r'\b(plc\.?)\b', 'plc', text)
    text = re.sub(r'\b(co\.?)\b', 'company', text)
    text = re.sub(r'\b(gov\.?|govt)\b', 'government', text)
    text = text.replace('&', 'and')
    text = re.sub(r'\s+', ' ', text)
    return text


def acronym(text):
    return ''.join(word[0] for word in text.split() if word).upper()


def build_canonical_map(names):
    clusters = defaultdict(list)

    for name in names.dropna().unique():
        norm = basic_normalize(name)
        key = acronym(norm) if len(norm.split()) > 1 else norm.upper()
        clusters[key].append(name)

    canonical_rows = []

    for key, variants in clusters.items():
        acronym_matches = [
            v for v in variants
            if v.replace(" ", "").upper() == key
        ]

        canonical = (
            acronym_matches[0]
            if acronym_matches
            else Counter(variants).most_common(1)[0][0]
        )

        for v in variants:
            canonical_rows.append({
                "buyer_name_raw": v,
                "buyer_name_canonical": canonical
            })

    return pd.DataFrame(canonical_rows)


def clean_financials(val):
    if pd.isna(val):
        return 0.0
    val = re.sub(r'[^\d.]', '', str(val))
    try:
        return float(val)
    except ValueError:
        return 0.0


def run():
    input_path = find_file(INPUT_FILENAME)
    if not input_path:
        raise FileNotFoundError(INPUT_FILENAME)

    df = pd.read_csv(input_path)

    df["buyer_name_raw"] = df["buyer_name"]
    buyer_map = build_canonical_map(df["buyer_name"])
    df = df.merge(buyer_map, on="buyer_name_raw", how="left")
    df["buyer_name"] = df["buyer_name_canonical"]
    df.drop(columns=["buyer_name_canonical"], inplace=True)

    df["value_amount"] = df["value_amount"].apply(clean_financials)

    df = df.drop_duplicates(subset=["ocid"])
    df = df[df["value_amount"] > 0]

    out_dir = os.path.dirname(input_path)
    df.to_csv(os.path.join(out_dir, CLEAN_OUTPUT_FILENAME), index=False)
    buyer_map.to_csv(os.path.join(out_dir, BUYER_MAP_FILENAME), index=False)


if __name__ == "__main__":
    run()
