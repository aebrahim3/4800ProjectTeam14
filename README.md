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

To regenerate a scraped catalog snapshot from the allowlisted official pages:

```bash
python scripts/refresh_course_catalog.py --output data/scraped_course_catalog.csv
```

The scraper intentionally avoids whole-site crawling. It only requests the configured BCIT, UBC, and SFU catalog pages with a delay between requests.
The scraper is organized as institution-specific connectors under `scripts/course_catalog/connectors`, with shared CSV fields and source-hash logic.
