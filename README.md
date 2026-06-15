# Metrology QC & Traceability Platform

End-to-end Data Engineering pipeline for laboratory calibration quality control,
built by a Physics & Mathematical Engineer with real-world metrology experience
under ISO 17025 / ISO 17034.

Ingests synthetic but realistic calibration data for 11 instruments across 3
sub-laboratories, processes it through a Medallion architecture, applies
statistical process control and Monte Carlo uncertainty propagation, and serves
the results through a REST API and an interactive dashboard.

## Why this project exists

Most DE portfolios process financial or web data. This one is different: it
models the actual data flows of an accredited calibration laboratory — drift
detection, uncertainty budgets, traceability chains, and predictive maintenance
— using the same production-grade tooling (Airflow, dbt, Docker) that powers
enterprise data systems.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          ORCHESTRATION                              │
│                       Apache Airflow 2.8                            │
│                                                                     │
│  ingest_bronze ──► dbt_run ──► dbt_test ──► [monte_carlo +         │
│                                               predictive_maintenance]│
└────────┬───────────────────────────────────────┬────────────────────┘
         │                                       │
         ▼                                       ▼
┌─────────────────┐                   ┌──────────────────────────┐
│     BRONZE      │                   │     dbt transforms       │
│  DuckDB (raw)   │                   │                          │
│                 │                   │  Silver (views)          │
│ calibration_    │──────────────────►│  stg_calibration_        │
│ measurements    │                   │  stg_environmental_      │
│ environmental_  │                   │                          │
│ conditions      │                   │  Gold (tables)           │
└─────────────────┘                   │  fact_instrument_stats   │
         ▲                            │  fact_control_charts     │
         │                            │  fact_calibration_status │
  src/generate/                       │  fact_uncertainty (MC)   │
  synthetic.py                        │  fact_predictive_maint.  │
  src/ingestion/                      └──────────┬───────────────┘
  loaders.py                                     │
                                                 ▼
                              ┌──────────────────────────────────┐
                              │   FastAPI  /  Streamlit          │
                              │                                  │
                              │  GET /instruments/               │
                              │  GET /instruments/{id}           │
                              │  GET /trends/{id}?days=N         │
                              │  POST /uncertainty/calculate     │
                              │                                  │
                              │  Dashboard: Levey-Jennings,      │
                              │  risk overview, uncertainty      │
                              │  budget                          │
                              └──────────────────────────────────┘
```

## Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | Apache Airflow 2.8 (Python 3.11) |
| Storage | DuckDB 1.2 (file-based, shared volume) |
| Transform | dbt 1.8 + dbt-duckdb |
| Science | Python — scipy, scikit-learn, numpy |
| API | FastAPI + uvicorn |
| Dashboard | Streamlit + Plotly |
| Containers | Docker / Docker Compose |
| Testing | pytest (16 tests) |

## Sub-laboratories and instruments

| Sub-lab | Instrument | ID | Drift pattern |
|---------|-----------|-----|--------------|
| Masa & Volumen | Balanza Analítica | BAL-001 | Linear — mechanical wear |
| Masa & Volumen | Balanza de Precisión | BAL-002 | Linear — mechanical wear |
| Masa & Volumen | Pipeta Volumétrica | PIP-001 | Abrupt jump — contamination |
| Masa & Volumen | Bureta | BUR-001 | Linear — plunger wear |
| Temp & Humedad | Termómetro Referencia | TER-REF | Seasonal — temperature correlation |
| Temp & Humedad | Termómetro Industrial | TER-IND | Seasonal + noise |
| Temp & Humedad | Higrómetro | HIG-001 | Seasonal |
| Temp & Humedad | Barómetro | BAR-001 | Gaussian — stable |
| Química Analítica | Espectrómetro XRF | XRF-001 | Exponential — tube degradation |
| Química Analítica | Cromatógrafo HPLC | HPL-001 | Linear — column degradation |
| Química Analítica | pH-metro | PHM-001 | Linear + abrupt jump — electrode |

## Key features

**Levey-Jennings Control Charts**
Daily mean error per instrument plotted against long-term ±1σ, ±2σ, ±3σ
control limits. Western Electric Rule 1 (beyond ±3σ) and Rule 2 (beyond ±2σ)
flags are computed in dbt SQL and served via API and dashboard.

**Monte Carlo Uncertainty Propagation**
Uncertainty budget combining Type A (statistical, from 20 replicates) and
Type B (reference standard, defined per instrument class) via 100,000-sample
Monte Carlo simulation. Expanded uncertainty U(k=2) reported per instrument,
following GUM / CIPM-2007 methodology.

**Predictive Maintenance**
Linear regression over the full-year error time series estimates drift slope
and intercepts the tolerance limit to predict days to failure. Risk levels:
CRITICAL (≤30 days), HIGH (≤90), MEDIUM (≤180), LOW (>180).

**FastAPI over Gold layer**
Three endpoints directly over DuckDB Gold tables — no intermediate cache.
The `/uncertainty/calculate` endpoint accepts dynamic measurement inputs and
returns a full uncertainty budget on the fly.

## Project structure

```
metrology-platform/
├── airflow/dags/metrology_pipeline.py   # Airflow DAG
├── api/                                 # FastAPI app
│   ├── main.py
│   └── routers/
│       ├── instruments.py
│       ├── trends.py
│       └── uncertainty.py
├── dashboard/app.py                     # Streamlit dashboard
├── dbt/
│   ├── models/staging/                  # Silver layer
│   └── models/marts/                    # Gold layer
├── models/
│   ├── monte_carlo.py                   # Uncertainty propagation
│   └── predictive.py                    # Drift prediction
├── src/
│   ├── generate/synthetic.py            # Data generator
│   └── ingestion/loaders.py             # Bronze loader
├── tests/                               # 16 pytest tests
├── data/db/                             # DuckDB file (gitignored)
└── docker-compose.yml
```

## Setup

### Prerequisites
- Docker + Docker Compose
- Python 3.11+ with conda (for local scripts)

### Run

```bash
# Clone and enter
git clone https://gitlab.com/plasmallan/metrology-platform.git
cd metrology-platform

# Fix Airflow log permissions
mkdir -p airflow/logs
sudo chown -R 50000:0 airflow/logs

# Generate synthetic data (run once)
conda activate metrology
pip install duckdb pandas numpy scipy
python src/generate/synthetic.py
python src/ingestion/loaders.py

# Start all services
docker compose up -d

# Access
# Airflow:   http://localhost:8080  (admin / admin)
# API:       http://localhost:8000/docs
# Dashboard: http://localhost:8501
```

### Run tests

```bash
pip install pytest httpx fastapi duckdb
pytest tests/ -v
```

## Metrological context

Laboratory environmental conditions are controlled per ISO 17025 requirements:
temperature 20 ± 2 °C, relative humidity 45–65 % RH, pressure 1005–1025 hPa.
Drift patterns are modeled after real failure modes observed in accredited
calibration laboratories: tube degradation in XRF, column aging in HPLC,
electrode replacement cycles in pH-meters, and seasonal thermal effects in
thermometers.

Uncertainty is reported as expanded uncertainty U with coverage factor k=2,
corresponding to a coverage probability of approximately 95 % for a normal
distribution, in accordance with the Guide to the Expression of Uncertainty
in Measurement (GUM).