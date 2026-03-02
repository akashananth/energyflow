# ⚡ EnergyFlow — Real-Time Energy Trading Data Platform

> A production-grade data engineering portfolio project simulating a real-time
> electricity trading data platform — built from scratch using industry-standard tools.

![Status](https://img.shields.io/badge/Status-In%20Progress-yellow)
![Stack](https://img.shields.io/badge/Stack-Kafka%20%7C%20Spark%20%7C%20Delta%20Lake%20%7C%20Airflow%20%7C%20dbt%20%7C%20Docker-blue)

---

## 🎯 Project Purpose

Energy trading desks make buy/sell decisions on electricity markets every 15 minutes.
Prices shift based on demand, renewable generation, and grid conditions.

This platform ingests live electricity spot price data across European regions,
processes it through a streaming pipeline, stores it in a lakehouse, and surfaces
trading-relevant insights — reliably, replayably, and at scale.

---

## 🏗️ Architecture

```
[Python Producer]
      │
      │  Simulates real ENTSO-E electricity spot prices
      │  5 regions (DE, FR, GB, NL, ES) · 15-min intervals
      ▼
[Apache Kafka]
      │
      │  Decoupled ingestion · 7-day retention · replayability
      ▼
[Spark Structured Streaming]
      │
      │  Real-time micro-batch processing · exactly-once semantics
      ▼
[Delta Lake — Bronze Layer]
      │
      │  Raw, immutable · Kafka metadata preserved · schema versioned
      ▼
[Delta Lake — Silver Layer]          (coming soon)
      │
      │  Cleaned · validated · data contracts enforced
      ▼
[Delta Lake — Gold Layer]            (coming soon)
      │
      │  Business aggregates · trading signals · hourly/daily rollups
      ▼
[dbt models + DuckDB]                (coming soon)
      │
      ▼
[Grafana Dashboard]                  (coming soon)
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Ingestion | Apache Kafka | Real-time message streaming, replayability |
| Processing | Apache Spark (PySpark) | Distributed stream + batch processing |
| Storage | Delta Lake | ACID transactions, time travel, schema enforcement |
| Orchestration | Apache Airflow | DAG-based scheduling, dependency management |
| Transformation | dbt | SQL-based data modeling, testing, documentation |
| Serving | DuckDB | Fast analytical queries on Delta files |
| Visualization | Grafana | Real-time trading dashboards |
| Infrastructure | Docker + Docker Compose | Fully containerized local development |

---

## 📊 Data Model

### Producer Output (Kafka Message Schema v1)

```json
{
  "event_id": "DE-20240115T143000000000",
  "region": "DE",
  "price_eur_mwh": 72.45,
  "currency": "EUR",
  "unit": "MWh",
  "timestamp_utc": "2024-01-15T14:30:00+00:00",
  "market_hour": 14,
  "delivery_period": "PT15M",
  "dominant_source": "wind",
  "renewable_share_pct": 62.3,
  "quality_flag": "ok",
  "producer_version": "1.0.0",
  "schema_version": "1"
}
```

### Simulated Regions

| Region | Base Price (€/MWh) | Characteristics |
|---|---|---|
| DE | 65 | Large renewables share, moderate volatility |
| FR | 60 | Nuclear baseload, most stable |
| GB | 80 | Island grid, highest volatility |
| NL | 68 | Gas hub influence |
| ES | 55 | High solar, significant price swings |

### Simulated Data Quality Issues
- **2% missing** — sensor/network failures (`quality_flag: missing`)
- **1% suspect** — stale or duplicate readings (`quality_flag: suspect`)
- **3% negative prices** — renewable surplus events (real phenomenon)

---

## 🚀 Getting Started

### Prerequisites
- Docker Desktop
- Git

### Run the platform

```bash
git clone https://github.com/YOUR_USERNAME/energyflow.git
cd energyflow
docker-compose up --build
```

### Verify it's working

| Service | URL | What you'll see |
|---|---|---|
| Kafka UI | http://localhost:8080 | Live price events flowing |
| Spark UI | http://localhost:4040 | Streaming job progress |

---

## 📁 Project Structure

```
energyflow/
├── docker-compose.yml          # Full platform infrastructure
├── producer/
│   ├── producer.py             # Energy price simulator
│   ├── Dockerfile
│   └── requirements.txt
├── spark/
│   ├── notebooks/
│   │   └── bronze_stream.ipynb # Kafka → Bronze Delta Lake
│   ├── delta/                  # Delta table files (gitignored)
│   └── checkpoints/            # Spark checkpoints (gitignored)
└── README.md
```

---

## 🔄 Medallion Architecture

This project implements the **Medallion (Bronze/Silver/Gold)** architecture —
the standard pattern used in Databricks and Azure Data Lake environments.

| Layer | Description | Status |
|---|---|---|
| **Bronze** | Raw data exactly as received from Kafka. Immutable. Enables replayability. | ✅ Complete |
| **Silver** | Cleaned, validated, schema-enforced. Data contracts applied. | 🔄 In Progress |
| **Gold** | Business aggregates — hourly avg price, volatility scores, trading signals. | 📋 Planned |

---

## 💡 Key Engineering Decisions

**Why Kafka instead of writing directly to a database?**
Kafka decouples producers from consumers and enables replayability.
If Spark goes down, it replays missed messages from Kafka's 7-day retention window.
In trading systems, missing or reprocessing data correctly is critical.

**Why Delta Lake over plain Parquet?**
Delta adds ACID transactions, schema enforcement, and time travel on top of Parquet.
If a bad deploy corrupts the Silver layer, we can roll back to a previous version.

**Why the Medallion architecture?**
Raw data is preserved in Bronze forever — any bug in Silver/Gold processing
can be fixed and replayed without going back to the source system.

---

## 📈 Roadmap

- [x] Phase 1 — Kafka + Producer (real-time price simulation)
- [x] Phase 2 — Spark Streaming → Bronze Delta Lake
- [ ] Phase 3 — Silver layer (data contracts, validation, cleaning)
- [ ] Phase 4 — Airflow orchestration + replay pipeline
- [ ] Phase 5 — dbt models + DuckDB serving layer
- [ ] Phase 6 — Grafana dashboard + IaC polish

---

## 👤 Author

Built as a portfolio project to demonstrate production-grade data engineering
skills in the energy trading domain.
