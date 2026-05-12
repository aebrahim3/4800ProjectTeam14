# 4800ProjectTeam14

## Environment Setup

### Creating a .env file

**Important:** Each developer must create their own `.env` file locally. This file should never be committed to the repository.

- Use the default value from .env.example would work, except the OPENROUTER_API_KEY row:
   - `POSTGRES_USER`: postgres
   - `POSTGRES_PASSWORD`: postgres
   - `POSTGRES_DB`: careerMatchingEngine
   - `OPENROUTER_API_KEY`: your_openrouter_api_key_here

## Getting Started

### Prerequisites
- Docker and Docker Compose installed on your system

### Starting the Project

1. **Start the application and database:**
   ```bash
   docker-compose up -d
   ```
   This command will:
   - Build and start the PostgreSQL database container
   - Build and start the FastAPI application container
   - The API will be available at `http://localhost:8000`
   - The recommendation API will be available at `http://localhost:8004`

2. **Check the application health:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Stop the application:**
   ```bash
   docker-compose down
   ```
   This will stop and remove all containers. Your database data will be preserved in the volume.

### API Endpoints

- `GET /` - Health check endpoint (returns "Hello World")
- `GET /health` - Database connection health check
- `POST /api/llm` - Call OpenRouter LLM API (requires OPENROUTER_API_KEY)
- `POST /career/course-recommendations` - Hybrid course recommendations on service port `8004`

## Institution Course Catalog Data

This branch includes the MVP data layer for local institution and course mapping:

- `institutions` stores BCIT, UBC, and SFU catalog metadata.
- `courses` stores normalized course catalog rows.
- `course_skill_mapping` links courses to existing `skills_taxonomy` records.
- `data/course_catalog_mvp.csv` contains the curated MVP course catalog.
- `data/course_skill_mapping_mvp.csv` contains the curated skill mappings.
- The course catalog CSV includes expanded school-sourced and O*NET-aligned fields such as prerequisites, learning outcomes, program/credential association, certifications, O*NET-SOC codes, O*NET skill elements, technology skills, work activities, task statements, job zone, and sparse features.

On a fresh database volume, Docker Compose loads `db/init.sql`, then `db/seed.sql`, and imports the CSV files from `data/`.

To import or refresh the course seed data against an existing database:

```bash
python scripts/import_course_data.py
```

After applying `db/migrations/001_course_dual_features.sql`, run the dual-track feature preprocessor to populate course sparse features and BGE embeddings:

```bash
python scripts/preprocess_course_features.py
```

For a quick sparse-only smoke test without downloading the BGE model:

```bash
python scripts/preprocess_course_features.py --skip-embeddings --limit 5
```

To import data and then run preprocessing in one command:

```bash
python scripts/import_course_data.py --preprocess-features
```

## Hybrid Course Recommendation API

The recommender service loads an existing XGBoost model from `COURSE_RANKER_MODEL_PATH`, defaulting to `models/course_ranker.json`. The model must use this feature order:

```text
dense_similarity, skill_hit_count, credits, is_local
```

If the model file is missing or cannot be loaded, the API uses a deterministic rule fallback and returns `model_version: "rule_fallback"`.

Start the database and recommendation service:

```bash
docker-compose up -d db recommender
```

Example request:

```bash
curl -X POST http://localhost:8004/career/course-recommendations \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"skill_gaps":["AWS","Python","Agile"],"preferred_location":"British Columbia","limit":3}'
```

To regenerate a scraped catalog snapshot from the allowlisted official pages:

```bash
python scripts/refresh_course_catalog.py --output data/scraped_course_catalog.csv
```

To also fetch compact enrichment fields such as BCIT learning outcomes and credential/program mappings:

```bash
python scripts/refresh_course_catalog.py --enrich --output data/scraped_course_catalog.csv
```

The scraper intentionally avoids whole-site crawling. It only requests the configured BCIT, UBC, and SFU catalog pages with a delay between requests.
The scraper is organized as institution-specific connectors under `scripts/course_catalog/connectors`, with shared CSV fields and source-hash logic.
