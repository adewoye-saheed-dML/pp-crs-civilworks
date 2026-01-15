# PP-CRS: Public Procurement Carbon Risk Screen
### *Forensic Intelligence for Scope 3 Emissions in Civil Infrastructure*

![Build Status](https://img.shields.io/badge/build-passing-brightgreen) ![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Status](https://img.shields.io/badge/status-active_forensic-red)

## Project Overview

The Public Procurement Carbon Risk Screen (PP-CRS) is an open-source forensic intelligence tool designed to audit government spending data for hidden climate risks.

**The Problem:** Traditional carbon accounting relies on "Bill of Quantities" data provided *after* a project is built. This is too late to influence design choices.

**The Solution:** PP-CRS flips this model. It uses Heuristic Financial Modeling to estimate hidden embodied carbon risks *before* contracts are fully executed.

The tool ingests raw open procurement data, filters for heavy civil engineering works, and transmutes Financial Capital (Spend in £) into Natural Capital (Carbon in $tCO_2e$) using calibrated industry composite rates.

---

## The Forensic Methodology

The tool operates on a strict "Noise-to-Signal" Pipeline, transforming raw, messy government data into targeted executive intelligence.

### Phase 1: Ingestion & Filter (`ingest_contracts.py`)
**Objective:** Isolate "Shovel-Ready" infrastructure projects from administrative noise.
* **Source:** UK Contracts Finder OCDS API (Open Contracting Data Standard).
* **Forensic Screen:**
    * **CPV Code Filter:** Strictly accepts only `45xxxxxx` (Construction Work) parent nodes.
    * **Semantic Negative Lookahead:** Rejects non-physical contracts via regex (e.g., *"Feasibility"*, *"Design Only"*, *"Consultancy"*, *"Legal Services"*).
* **Result:** Reduces raw API stream by **~95%**, isolating purely physical infrastructure works.

### Phase 2: Data Hygiene & Entity Resolution (`clean_data.py`)
**Objective:** Normalize inconsistent government entry data to prevent Scope 3 leakage.
* **Entity Resolution:** Merges fragmented buyer names (e.g., *"Sellafield Ltd"* + *"Sellafield Limited"* $\rightarrow$ Sellafield Limited) using a regex normalization dictionary.
* **Deduplication:** Removes duplicate OCDS entries (common in government datasets) and sanitizes currency fields.
* **Impact:** In 2025 tests, this phase merged 20+ distinct buyer entities and removed ~15% of rows as duplicates/zero-value, ensuring high-fidelity reporting.

### Phase 3: The PQE Engine (`pqe_engine.py`)
**Objective:** The core "Alchemy" step—converting Money (£) into Carbon ($tCO_2e$).
* **Logic:** Public procurement data lists *Money*, not *Materials*. The engine solves this by applying a Price-to-Quantity Heuristic calibrated against UK industry standards.
* **Algorithm:**
    1.  **Material Detection:** Scans contract titles/descriptions for keywords (e.g., "Resurfacing" -> Asphalt, "Bridge" -> Concrete/Steel).
    2.  **Mass Estimation:** Divides Spend by the Composite Installed Rate.
    3.  **Carbon Calculation:** Multiplies Mass by the Embodied Carbon Factor.

#### The Equations
$$
\text{Estimated Mass (t)} = \frac{\text{Contract Value (£)}}{\text{Composite Installed Rate (£/t)}}
$$

$$
\text{Carbon Risk (tCO}_2\text{e)} = \frac{\text{Mass (t)} \times \text{Emission Factor (kgCO}_2\text{e/t)}}{1000}
$$

### Phase 4: Physics Calibration (Traceable Data)
All carbon factors are strictly traceable to verified UK industry standards.

| Detected Profile | Composite Rate (SPONS '24) | Carbon Factor (ICE V4.1 / DEFRA) | Source |
| :--- | :--- | :--- | :--- |
| **Asphalt (Roads)** | £85.00 / t | **56.15** kg/t | ICE Database V4.1 (4% Binder) |
| **Concrete (Civils)** | £110.00 / t | **119.00** kg/t | ICE Database V4.1 (C25/30 CEM I) |
| **Steel (Structural)** | £1,500.00 / t | **1,610.00** kg/t | ICE Database V4.1 (World Avg) |
| **Earthworks** | £18.00 / t | **5.41** kg/t | DEFRA 2025 (Fuel Factors: Diesel) |
| **General Blend** | £45.00 / t | **31.00** kg/t | Synthetic Mix (40% Earth / 30% Agg / 30% Conc) |

*Note: Earthworks factor is derived from diesel consumption of 20t Excavators (approx 2.0L/tonne).*

### Phase 5: Automated Advisory (`generate_memo.py`)
**Objective:** Generate "Privacy-Safe" executive intelligence.
* Automatically generates a Forensic Memo (PDF) for any entity flagged as CRITICAL RISK (>1,000 $tCO_2e$).
* **Content:** Audits the math ($£ \rightarrow t \rightarrow CO_2$) and suggests specific material interventions (e.g., *"Switch to Warm Mix Asphalt"*).

---

## Project Structure

```text
pp-crs-civilworks/
├── data/
│   ├── 2025_PURE_CIVIL_WORKS_STRICT.csv    # Raw API Data (Filtered by CPV)
│   ├── 2025_CIVIL_WORKS_CLEANED.csv        # Normalized Data (Deduped & Entities Resolved)
│   ├── 2025_CARBON_RISK_SCREENED.csv       # Final Output (Ranked by Carbon)
│   └── material_reference.csv              # The Physics Kernel (Price/Carbon Factors)
├── memos/                                  # Auto-generated PDF Forensic Reports
│   ├── Memo_Sellafield_Limited.pdf
│   └── Memo_Westminster_City_Council.pdf
├── ingest_contracts.py                     # Step 1: Fetches & Filters API Data
├── filter_civil_work.py                    # Step 2: Filters only Relevant civil works
├── clean_data.py                           # Step 3: Entity Resolution & Hygiene
├── pqe_engine.py                           # Step 4: Price-to-Quantity Estimator
├── generate_memo.py                        # Step 5: PDF Report Generator
├── requirements.txt                        # Dependencies
└── README.md                               # This documentation
```
## Installation & Setup

### Prerequisites

- Python 3.10 or higher
- pip

### Installation

1. Clone the repository:

```bash
git clone https://github.com/adewoye-saheed-dml/pp-crs-civilworks.git
cd pp-crs-civilworks
```

2. Create a Virtual Environment (Optional but Recommended):

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Dependencies:

```bash
pip install -r requirements.txt
```

## Usage Guide

The system is designed as a sequential forensic pipeline. Run these commands in order:

### Step 1: Ingest & Filter

Pull live data from the UK Contracts Finder API with CPV code and regex filters:

```bash
python3 ingest_contracts.py
```

**Output**: `data/2025_PURE_CIVIL_WORKS_STRICT.csv`

### Step 2: Forensic Cleaning

Normalize buyer names (e.g., merging "Ltd" and "Limited") and sanitize currency fields:

```bash
python3 clean_data.py
```

**Output**: `data/2025_CIVIL_WORKS_CLEANED.csv`

### Step 3: Run the PQE Engine

Execute the Price-to-Quantity Estimator to aggregate contracts by Buyer Entity and calculate carbon risk:

```bash
python3 pqe_engine.py
```

**Output**: `data/2025_CARBON_RISK_SCREENED.csv`

### Step 4: Generate Intelligence Reports

Automatically create PDF Forensic Memos for the top critical risks:

```bash
python3 generate_memo.py
```

**Output**: PDF files in the `memos/` directory

## Limitations & Disclaimer

### Screening Tool Only

This is a **probabilistic screening tool**, not a Life Cycle Assessment (LCA). It is designed to identify priorities, not to certify emissions.

### Price Volatility

Composite rates are static estimates based on SPONS 2024. Actual contract rates may vary by region and supply chain.

### Worst-Case Baseline

The model assumes "Standard" materials (e.g., CEM I Concrete). If contractors use low-carbon alternatives, this tool will overestimate the risk (which is the intended fail-safe direction).

### Liability

This tool is provided "as is". The maintainers accept no liability for decisions made based on this data.

## License & Credits

### License

MIT License

### Data Sources

- **Carbon Factors**: Circular Ecology ICE Database V4.1 & UK Gov DEFRA 2025
- **Procurement Data**: UK Contracts Finder (OCDS)
- **Pricing Heuristics**: Derived from industry averages (SPONS / BCIS)
