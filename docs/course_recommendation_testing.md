# Course Recommendation Testing Guide

This guide explains where the course recommendation tests live, how to run them, and what output to expect.

## Test Files

- `scripts/test_course_recommendation_api.py`
  - End-to-end smoke test against the running FastAPI recommender service on `http://localhost:8004`.
  - Checks service health, sends multiple recommendation requests, validates response shape, and prints top recommendations.
- `tests/test_course_recommendations.py`
  - Unit tests for skill normalization, sparse hit counting, Hybrid NN scoring, zero-hit penalty, response ranking, and FastAPI route validation.
- `tests/test_preprocess_course_features.py`
  - Unit tests for BGE dimension expectations, feature-key normalization, taxonomy synonym matching, sparse feature generation, manual mapping conversion, and embedding dimension validation.
- `tests/test_course_catalog_connectors.py`
  - Unit tests for course catalog connector parsing.

## Prerequisites

Start the database and recommender service:

```bash
docker compose up -d db recommender
```

The recommendation API requires:

- `careerMatchingEngine` database initialized from `db/init.sql` and `db/seed.sql`
- `courses.embedding` populated by `scripts/preprocess_course_features.py`
- `courses.sparse_features` populated by `scripts/preprocess_course_features.py`

For a fresh local database:

```bash
docker compose down -v
docker compose up -d db recommender
docker compose exec recommender python scripts/preprocess_course_features.py
```

After code changes:

```bash
docker compose restart recommender
```

If dependencies changed in `requirements.txt`, rebuild:

```bash
docker compose build recommender
docker compose up -d recommender
```

## Automated API Smoke Test

Run:

```bash
python scripts/test_course_recommendation_api.py
```

The script first checks:

```text
Health check passed: {'status': 'healthy', 'database': 'connected'}
```

Then it sends all API cases below. A successful run ends with:

```text
All course recommendation API smoke cases passed.
```

If the service is slow to start or BGE model loading is cold, use longer retries:

```bash
python scripts/test_course_recommendation_api.py --attempts 12 --retry-delay 5
```

## API Test Cases And Expected Output

All successful recommendation responses should include:

- `model_version: "hybrid_nn_v1"`
- `used_rule_fallback: false`
- `recommendations`
- each recommendation has `score`, `dense_similarity`, `skill_hit_count`, `matched_skills`, `missing_skills`, and `ranking_signals`

Scores can shift slightly if embeddings, course data, or taxonomy aliases change. The stable expectation is the response shape and the matched/missing skill behavior.

### Case 1: AWS + Python + Agile

Request:

```bash
curl -s -X POST http://localhost:8004/career/course-recommendations \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"skill_gaps":["AWS","Python","Agile"],"preferred_location":"British Columbia","limit":3}' | python3 -m json.tool
```

Expected:

- HTTP `200`
- `unknown_skill_gaps: []`
- Top recommendation should prefer courses with more sparse hits.
- Example observed output:

```text
COMP 2800 0.6368 hits: ['AWS', 'Agile'] missing: ['Python'] penalty: False
CPSC_V 319 0.5453 hits: ['Agile'] missing: ['AWS', 'Python'] penalty: False
COMP 1800 0.5343 hits: ['Agile'] missing: ['AWS', 'Python'] penalty: False
```

### Case 2: Python Only

Request:

```bash
curl -s -X POST http://localhost:8004/career/course-recommendations \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"skill_gaps":["Python"],"preferred_location":"British Columbia","limit":5}' | python3 -m json.tool
```

Expected:

- HTTP `200`
- `unknown_skill_gaps: []`
- Top recommendations should match `Python`.
- `missing_skills` should be empty for courses that hit Python.
- Example observed output:

```text
CPSC_V 103 0.7395 hits: ['Python'] missing: [] penalty: False
CMPT 120 0.7391 hits: ['Python'] missing: [] penalty: False
CPSC_V 100 0.7333 hits: ['Python'] missing: [] penalty: False
CPSC_V 203 0.7305 hits: ['Python'] missing: [] penalty: False
CPSC_V 221 0.7245 hits: ['Python'] missing: [] penalty: False
```

### Case 3: AWS Only

Request:

```bash
curl -s -X POST http://localhost:8004/career/course-recommendations \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"skill_gaps":["AWS"],"preferred_location":"British Columbia","limit":5}' | python3 -m json.tool
```

Expected:

- HTTP `200`
- `unknown_skill_gaps: []`
- AWS-matching cloud courses should rank above zero-hit courses.
- Any zero-hit recommendation should show `zero_hit_penalty_applied: true`.
- Example observed output:

```text
CMPT 756 0.7192 hits: ['AWS'] missing: [] penalty: False
COMP 2800 0.7102 hits: ['AWS'] missing: [] penalty: False
CPSC_V 416 0.6943 hits: ['AWS'] missing: [] penalty: False
CMPT 431 0.6898 hits: ['AWS'] missing: [] penalty: False
CPSC_V 319 0.1431 hits: [] missing: ['AWS'] penalty: True
```

### Case 4: Kubernetes + AWS

Request:

```bash
curl -s -X POST http://localhost:8004/career/course-recommendations \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"skill_gaps":["Kubernetes","AWS"],"preferred_location":"British Columbia","limit":3}' | python3 -m json.tool
```

Expected:

- HTTP `200`
- `Kubernetes` is expected to be known if it exists in `skills_taxonomy` or its synonyms.
- Courses matching both Kubernetes and AWS should rank above courses matching only AWS.
- Example observed output:

```text
CMPT 756 0.7247 hits: ['Kubernetes', 'AWS'] missing: [] penalty: False
COMP 2800 0.5556 hits: ['AWS'] missing: ['Kubernetes'] penalty: False
CPSC_V 416 0.5494 hits: ['AWS'] missing: ['Kubernetes'] penalty: False
```

To verify why Kubernetes is known:

```bash
docker compose exec db psql -U postgres -d careerMatchingEngine -c "
SELECT skill_name, skill_synonyms
FROM skills_taxonomy
WHERE lower(skill_name) LIKE '%kubernetes%'
   OR skill_synonyms::text ILIKE '%kubernetes%';
"
```

### Case 5: Unknown Skill + AWS

Request:

```bash
curl -s -X POST http://localhost:8004/career/course-recommendations \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"skill_gaps":["TotallyMadeUpSkillXYZ","AWS"],"preferred_location":"British Columbia","limit":3}' | python3 -m json.tool
```

Expected:

- HTTP `200`
- `unknown_skill_gaps: ["TotallyMadeUpSkillXYZ"]`
- Unknown skills do not count against `skill_coverage`.
- AWS still participates in ranking.
- Example observed output:

```text
COMP 2800 0.7159 hits: ['AWS'] missing: [] penalty: False
CMPT 756 0.7005 hits: ['AWS'] missing: [] penalty: False
CPSC_V 416 0.6796 hits: ['AWS'] missing: [] penalty: False
```

### Case 6: Empty Skill Gaps

Request:

```bash
curl -i -X POST http://localhost:8004/career/course-recommendations \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"skill_gaps":[],"preferred_location":"British Columbia","limit":3}'
```

Expected:

- HTTP `422`
- Response:

```json
{"detail":"skill_gaps must contain at least one non-empty value"}
```

## Unit And Regression Tests

Run the core unit tests:

```bash
python3 -m unittest tests.test_course_recommendations tests.test_preprocess_course_features
```

Expected:

```text
OK
```

Run all tests:

```bash
python3 -m unittest discover
```

Expected:

```text
OK
```

If local dependencies are missing, install from `requirements.txt` or run in the Docker container.

Run compile checks:

```bash
python3 -m py_compile app/main.py app/recommendations.py scripts/preprocess_course_features.py scripts/import_course_data.py scripts/test_course_recommendation_api.py
```

Expected: no output and exit code `0`.

## Troubleshooting

If API smoke tests fail with connection reset:

```bash
docker compose ps recommender
docker compose logs --tail=200 recommender
python scripts/test_course_recommendation_api.py --attempts 12 --retry-delay 5
```

If the API returns a database or recall error, verify schema and embeddings:

```bash
docker compose exec db psql -U postgres -d careerMatchingEngine -c "\dt"
docker compose exec db psql -U postgres -d careerMatchingEngine -c "
SELECT COUNT(*) AS total_courses, COUNT(embedding) AS courses_with_embedding
FROM courses;
"
```

If `courses_with_embedding` is `0`, run:

```bash
docker compose exec recommender python scripts/preprocess_course_features.py
```
