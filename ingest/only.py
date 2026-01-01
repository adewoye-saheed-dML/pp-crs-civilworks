import pandas as pd
import os

INPUT_FILE = "data/2025_construction_contracts.csv" 
OUTPUT_FILE = "2025_PURE_CIVIL_WORKS_STRICT.csv"


ALLOWED_PREFIXES = (
    "451",  # Site preparation, Demolition, Test drilling (The start of civil works)
    "4520", # Works for complete/part construction & civil engineering (Specific general code)
    "4522", # Engineering works: Bridges, Tunnels, Shafts, Subways
    "4523", # The "Heavy" Stuff: Pipelines, Highways, Roads, Railways, Airfields
    "4524", # Water Projects: Dams, Canals, Dredging, Flood Defence
    "4525"  # Industrial: Plants, Mining, Manufacturing facilities
)

def filter_strict_cpvs():
    print(f"--- Processing {INPUT_FILE} ---")
    
    try:
        df = pd.read_csv(INPUT_FILE, encoding='utf-8')
    except UnicodeDecodeError:
        print("UTF-8 failed, trying Latin-1 encoding...")
        df = pd.read_csv(INPUT_FILE, encoding='latin1')
        
    print(f"Original Row Count: {len(df)}")
    
    df['cpv_code'] = df['cpv_code'].astype(str).str.strip()
    
    civil_mask = df['cpv_code'].str.startswith(ALLOWED_PREFIXES)
    
    result_df = df[civil_mask]


    result_df.to_csv(OUTPUT_FILE, index=False)
    
    print(f"\n--- Filtering Complete ---")
    print(f"Dropped {len(df) - len(result_df)} rows (Buildings/Generic/Noise).")
    print(f"Retained {len(result_df)} High-Confidence Civil Works rows.")
    print(f"Saved to: {OUTPUT_FILE}")
    
    if not result_df.empty:
        print("\nPreview of Pure Data:")
        print(result_df[['title', 'cpv_code']].head(10))
    else:
        print("\nWARNING: No contracts matched your strict criteria. Check your input file.")

if __name__ == "__main__":
    if os.path.exists(INPUT_FILE):
        filter_strict_cpvs()
    else:
        print(f"Error: Could not find {INPUT_FILE}")