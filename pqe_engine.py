import pandas as pd
import os
import re

# --- CONFIGURATION ---
INPUT_FILENAME = "2025_CIVIL_WORKS_CLEANED.csv"   # cleaned dataset (use this)
REF_FILENAME = "material_reference.csv"
OUTPUT_FILENAME = "2025_CARBON_RISK_SCREENED.csv"
MIN_SPEND_GBP = 5000


def find_file_in_project(filename):
    """Search project tree for filename."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    for root, _, files in os.walk(project_root):
        if filename in files:
            return os.path.join(root, filename)
    return None


def clean_currency(val):
    """Return float parsed from messy currency strings (0.0 on failure)."""
    try:
        clean_str = re.sub(r"[^\d.]", "", str(val))
        return float(clean_str) if clean_str else 0.0
    except Exception:
        return 0.0


def detect_material(text, ref_df):
    """
    Return a material row as a dict based on keyword matching.
    Row order in ref_df should be most-specific -> generic.
    """
    text = str(text).lower()
    for _, row in ref_df.iterrows():
        if str(row.get("material_id", "")).upper() == "MAT_GEN":
            continue
        keywords = [k.strip().lower() for k in str(row.get("keywords", "")).split("|") if k.strip()]
        if any(k and k in text for k in keywords):
            return row.to_dict()
    # fallback
    gen = ref_df[ref_df["material_id"] == "MAT_GEN"]
    if not gen.empty:
        return gen.iloc[0].to_dict()
    return None


def run_pqe_engine():
    print("--- Starting PQE Engine ---")

    input_path = find_file_in_project(INPUT_FILENAME)
    if not input_path:
        print(f"Error: Could not find '{INPUT_FILENAME}'. Place cleaned CSV in project.")
        return

    ref_path = find_file_in_project(REF_FILENAME)
    if not ref_path:
        print(f"Error: Could not find '{REF_FILENAME}'.")
        return

    contracts = pd.read_csv(input_path, encoding="utf-8-sig")
    materials = pd.read_csv(ref_path, encoding="utf-8-sig")

    print(f"Loaded {len(contracts)} contracts and {len(materials)} material profiles.")

    results = []

    for _, row in contracts.iterrows():
        title = row.get("title", "") or ""
        description = row.get("description", "") or ""
        full_text = f"{title} {description}"
        spend_gbp = clean_currency(row.get("value_amount", 0))

        if spend_gbp < MIN_SPEND_GBP:
            r = row.to_dict()
            r["pqe_status"] = "SKIPPED_LOW_VALUE"
            results.append(r)
            continue

        mat = detect_material(full_text, materials)
        if not mat:
            r = row.to_dict()
            r["pqe_status"] = "SKIPPED_NO_REF"
            results.append(r)
            continue

        # safe numeric extraction
        try:
            price = float(mat.get("composite_price_gbp_per_tonne") or 0)
        except Exception:
            price = 0.0
        try:
            factor = float(mat.get("carbon_factor_kgco2e_per_tonne") or 0)
        except Exception:
            factor = 0.0

        if price <= 0 or factor <= 0:
            r = row.to_dict()
            r["pqe_status"] = "SKIPPED_INVALID_REF"
            r["ref_price"] = mat.get("composite_price_gbp_per_tonne")
            r["ref_factor"] = mat.get("carbon_factor_kgco2e_per_tonne")
            results.append(r)
            continue

        est_tonnes = spend_gbp / price
        est_co2e = (est_tonnes * factor) / 1000.0
        low_bound = est_co2e * 0.75
        high_bound = est_co2e * 1.25

        if est_co2e >= 1000:
            risk = "CRITICAL"
        elif est_co2e >= 250:
            risk = "HIGH"
        elif est_co2e >= 50:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        r = row.to_dict()
        r.update({
            "pqe_status": "CALCULATED",
            "detected_material_id": mat.get("material_id"),
            "detected_material_name": mat.get("material_name"),
            "applied_price_rate": price,
            "applied_carbon_factor": factor,
            "est_material_tonnes": round(est_tonnes, 2),
            "est_co2e_tonnes": round(est_co2e, 2),
            "co2e_range_low": round(low_bound, 2),
            "co2e_range_high": round(high_bound, 2),
            "risk_category": risk,
            "data_source_ref": mat.get("ice_source_ref")
        })
        results.append(r)

    out_df = pd.DataFrame(results)

    if "est_co2e_tonnes" in out_df.columns:
        out_df["sort_helper"] = out_df["est_co2e_tonnes"].fillna(-1)
        out_df = out_df.sort_values(by="sort_helper", ascending=False).drop(columns=["sort_helper"])

    output_path = os.path.join(os.path.dirname(input_path), OUTPUT_FILENAME)
    out_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Saved output to: {output_path}")

    if not out_df.empty:
        print("\nTop 5 Highest Carbon Risks:")
        cols = ["buyer_name", "title", "est_co2e_tonnes", "detected_material_name"]
        print(out_df[cols].head(5).to_string(index=False))


if __name__ == "__main__":
    run_pqe_engine()
