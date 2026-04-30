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


