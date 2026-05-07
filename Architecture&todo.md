# Career Matching Engine - Course Recommendation Architecture

## Context

本项目的课程推荐模块分为两个阶段：

- **子任务 1-2 已完成基础数据层**：建立 `institutions`、`courses`、`course_skill_mapping`，并用 MVP CSV seed 导入 BCIT、UBC、SFU 的课程样本。
- **子任务 3-5 将实现核心推荐能力**：用 `bge-large-en-v1.5` 生成 dense embedding，用 skill taxonomy 生成 sparse features，用 XGBoost 做最终课程匹配排序，并用 SHAP 输出可解释推荐理由。

重要原则：

- 学校官网只用于 **monthly catalog ingestion pipeline**，不用于用户在线推理。
- 在线推荐接口只读数据库、向量索引、XGBoost 模型和 SHAP 解释结果。
- LLM 可以后续用于润色解释文案，但不负责核心 matching decision。

---

## Current Implementation Baseline

当前 repo 已具备：

- FastAPI + SQLAlchemy + PostgreSQL 16 + pgvector。
- `courses.embedding VECTOR(768)` 字段，用于课程语义向量。
- `course_skill_mapping` 表，用于把课程映射到 `skills_taxonomy`。
- `scripts/import_course_data.py`，用于把 curated CSV 导入数据库。
- `scripts/refresh_course_catalog.py`，使用 connector framework + BeautifulSoup，从 allowlisted official pages 定向刷新课程 catalog snapshot。

兼容性检查：

| Area | Current State | Compatibility with New Plan |
|------|---------------|-----------------------------|
| Database | PostgreSQL + pgvector | Compatible |
| Course tables | `institutions`, `courses`, `course_skill_mapping` exists | Compatible baseline |
| Dense embedding column | `VECTOR(768)` | Needs migration for `bge-large-en-v1.5` |
| Course employment fields | Course facts and O*NET alignment fields exist in CSV/schema | Compatible baseline for richer matching |
| Sparse skill features | `courses.sparse_features JSONB` exists | Needs preprocessing population |
| ML libraries | Not installed | Need `sentence-transformers`, `torch`, `xgboost`, `shap`, `numpy`, `pandas`, `scikit-learn` |
| Scraping | BeautifulSoup connector script exists | Compatible with chosen strategy |
| API | Only basic FastAPI endpoints exist | Need `/career/course-recommendations` in Service `:8004` |

Note: `bge-large-en-v1.5` commonly outputs **1024-dimensional embeddings**. The current `VECTOR(768)` schema only fits a 768-dim model such as `bge-base-en-v1.5`. Since the selected model is `bge-large-en-v1.5`, sub-task 3 should migrate relevant embedding columns to `VECTOR(1024)` unless the team intentionally switches to a 768-dim embedding model.

---

## Data Ingestion Strategy

### Catalog Ingestion Pipeline

The course catalog should be refreshed on a monthly schedule:

```
Official university catalog pages
    ↓
Institution connector
    ↓
BeautifulSoup parser
    ↓
Normalized course records
    ↓
Database upsert with source_hash
    ↓
Dense + sparse feature preprocessing
    ↓
Course recommendation model input
```

### Connector Framework

Use one connector per institution:

- `BCITCourseCatalogConnector`
  - Reads allowlisted BCIT subject/program/course pages.
  - Parses course code, title, description, credits, prerequisites, credential metadata, campus, delivery mode, and intake terms when available.

- `UBCCourseCatalogConnector`
  - Reads Academic Calendar subject pages.
  - Expands beyond `CPSC_V` as needed by adding more subject allowlist entries.

- `SFUCourseCatalogConnector`
  - Reads official Calendar course pages and subject lists.
  - Avoids whole-site crawling and only follows course catalog URLs.

The connector framework should not crawl the whole university website. It should keep a controlled allowlist of catalog/program listing URLs and parse only compact structured fields from those pages.

### Update Semantics

Each monthly run should:

- Compute `source_hash` from normalized course fields.
- Insert new courses.
- Update changed courses.
- Set `last_seen_at` for courses still present.
- Mark courses as stale if missing from the latest run.
- Only set `is_active = FALSE` after repeated misses, not after one failed scrape.

Recommended future tables:

- `catalog_sources`: institution-specific source URLs and parser config.
- `catalog_ingestion_runs`: run status, counts, duration, and errors.
- `course_snapshots`: optional historical copy of parsed course data for auditing.

---

## Expanded Course Catalog Fields

The course CSV and `courses` table should store more than title, description, and URL. The model should not visit university pages at inference time, so the ingestion pipeline must persist the course facts and employment-alignment features needed for matching.

### School-Sourced Course Facts

These fields come from institution catalog pages and program/course listing pages. Full course outline text should not be stored in the database.

- `prerequisites`: prerequisite course codes or text.
- `credits`: numeric course credits.
- `program_credential_association`: related program, credential, certificate, diploma, degree, or specialization.
- `credential_type`: normalized credential label such as `certificate`, `diploma`, `degree`, `microcredential`, or `continuing_education`.
- `certification`: external certification explicitly prepared for or awarded, such as AWS, Cisco, Microsoft, CompTIA, PMP, or institution-issued certificate.
- `learning_outcomes`: skills/outcomes stated by the school.
- `course_level`: introductory, intermediate, advanced, undergraduate, graduate, continuing studies.
- `delivery_mode`: in-person, online, hybrid, asynchronous, part-time.
- `campus`: campus/location when available.
- `term_availability`: terms or schedule availability when published.

### O*NET-Aligned Employment Features

O*NET occupation-side files show which employment features matter most for job matching. The official Skills file maps occupations to `Element ID`, `Element Name`, `Scale ID`, and `Data Value`; Technology Skills includes `Example`, `Hot Technology`, and `In Demand`; Education, Training, and Experience includes required education/training elements and percent-frequency categories; Job Zones describe the education, experience, and training level needed by an occupation.

For course matching, store normalized O*NET alignment fields on each course:

- `onet_soc_codes`: likely O*NET-SOC occupations addressed by the course.
- `onet_skill_elements`: O*NET skill elements covered by the course, including element id/name and optional importance/level values.
- `onet_technology_skills`: tools and technologies covered, including whether they are hot or in-demand for target occupations.
- `onet_knowledge_elements`: knowledge domains covered by the course.
- `onet_work_activities`: work activities practiced or prepared for.
- `onet_task_statements`: relevant task statements when course outcomes map to job tasks.
- `onet_job_zone`: expected job-zone level this course best supports.
- `onet_alignment_notes`: human-readable audit note for why the course maps to those occupation features.

This keeps the CSV useful for both:

- **Dense matching**: `bge-large-en-v1.5` embeds rich course text.
- **Sparse/employment matching**: XGBoost sees exact skill/tool/work-activity/job-zone features that employers care about.

---

## Updated Development Plan (Sub-Tasks 3-5)

### Sub-Task 3: Feature Engineering and Dual-Track Vectorization

Goal: Give each course both semantic meaning and precise skill tags.

Actions:

- Add preprocessing pipeline for courses after ingestion.
- Use `bge-large-en-v1.5` to encode course text into dense embeddings.
- Extract skill labels from course title, description, prerequisites, and learning outcomes when present.
- Match extracted labels to `skills_taxonomy`.
- Store sparse skill features for each course.

Dense track:

```text
course_text = title + description + prerequisites + learning_outcomes
embedding = bge-large-en-v1.5(course_text)
courses.embedding = embedding
```

Sparse track:

```json
{
  "aws": 1,
  "python": 1,
  "agile": 1,
  "sql": 0
}
```

Recommended schema changes:

- Migrate `courses.embedding` to match selected model dimension, preferably `VECTOR(1024)` for `bge-large-en-v1.5`.
- Add `courses.sparse_features JSONB`.
- Add richer course fields over time: `prerequisites`, `learning_outcomes`, `delivery_mode`, `campus`, `term_availability`.
- Extend `course_skill_mapping` with feature metadata if needed:
  - `evidence_text`
  - `source_field`
  - `feature_key`

Acceptance criteria:

- Every active course has a dense embedding.
- Every active course has sparse feature JSON, even if empty.
- Skills are mapped through `skills_taxonomy`, not free-form strings only.

---

### Sub-Task 4: Hybrid XGBoost Model and API Deployment

Goal: Build the core matching model that balances semantic relevance and exact skill coverage.

Training phase:

- Use O*NET data or simulated historical matching data.
- Build course-user/career training examples.
- Generate features:
  - `dense_similarity`: cosine similarity between user gap/career vector and course embedding.
  - `skill_hit_count`: number of user gap skills covered by course sparse features.
  - `skill_coverage_ratio`: covered gap skills divided by total gap skills.
  - `missing_required_skill_count`: user gap skills not covered.
  - `credits`: course credit value.
  - `is_local`: whether institution is local or preferred by user.
  - Optional: institution type, delivery mode, course level, recency/freshness.
- Train XGBoost so exact skill mismatch can strongly penalize otherwise semantically similar courses.

Inference phase in Service `:8004`:

```text
Input: user skill gap pool
    ↓
Build dense query embedding with bge-large-en-v1.5
    ↓
pgvector coarse retrieval: Top 50 active courses
    ↓
Build hybrid feature rows for each candidate
    ↓
XGBoost scoring
    ↓
Return Top 3 course cards
```

API endpoint:

```http
POST /career/course-recommendations
```

Request:

```json
{
  "user_id": 1,
  "skill_gaps": ["AWS", "Python", "Agile"],
  "preferred_location": "British Columbia",
  "limit": 3
}
```

Response:

```json
{
  "recommendations": [
    {
      "course_id": 42,
      "institution": "BCIT",
      "course_code": "COMP 2800",
      "title": "Projects 2",
      "url": "https://www.bcit.ca/cst",
      "score": 0.91,
      "matched_skills": ["AWS", "Agile"],
      "missing_skills": ["Python"],
      "explanation": "This course precisely covers Agile and has strong semantic alignment with applied cloud project work."
    }
  ]
}
```

Acceptance criteria:

- Dense retrieval returns candidates in under one second for expected MVP scale.
- XGBoost reranking returns deterministic Top 3 results for the same input.
- Courses with zero sparse skill hits are penalized even when dense similarity is high.

---

### Sub-Task 5: SHAP-Based White-Box Explanation Engine

Goal: Explain why each recommended course was selected using model features, not generic AI text.

Actions:

- Run SHAP explanation on the XGBoost score for each Top 3 course.
- Identify the largest positive contributors.
- Map technical feature names to user-facing explanation templates.

Feature-to-template mapping:

```text
feature_sparse_[skill] is largest positive contributor
→ "This course precisely covers your priority skill: [skill]."

dense_similarity is largest positive contributor
→ "The overall course content is highly aligned with your target career direction."

skill_coverage_ratio is largest positive contributor
→ "This course covers several of your current skill gaps at once."

is_local is largest positive contributor
→ "This institution is local to your preferred study region."
```

Output should include:

- `explanation`
- `top_positive_factors`
- `matched_skills`
- `missing_skills`
- `model_score`

Acceptance criteria:

- Each returned course card includes at least one explanation.
- Explanations are generated from SHAP/model features, not hallucinated facts.
- Any displayed course facts must come from database fields.

---

## Service Architecture

### Service `:8005` - Course Data Layer

Responsibilities:

- Run catalog ingestion jobs.
- Normalize institution course data.
- Upsert courses and course snapshots.
- Run dense/sparse preprocessing.
- Store embeddings and sparse features.

This service may run as scheduled jobs or admin-triggered tasks. It is not on the critical path for user recommendation latency.

### Service `:8004` - Recommendation Logic Layer

Responsibilities:

- Accept skill gap arrays from user/career matching output.
- Query `courses` using pgvector for coarse retrieval.
- Build XGBoost feature rows.
- Score and rank candidates.
- Generate SHAP explanations.
- Return frontend-ready course card JSON.

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| API framework | FastAPI | Service `:8004` and optional admin endpoints |
| Database | PostgreSQL 16 + pgvector | Course storage, dense vector search |
| ORM/SQL | SQLAlchemy 2.0 + psycopg2 | Database access |
| Scraping | Requests + BeautifulSoup | Connector framework for monthly catalog ingestion |
| Embedding model | `bge-large-en-v1.5` | Dense semantic course/user/career vectors |
| Sparse features | `skills_taxonomy` + JSONB | Exact skill coverage |
| Ranking model | XGBoost | Hybrid course matching score |
| Explanation | SHAP | White-box score explanation |
| Optional LLM | OpenRouter/LLM provider | Text polish only, not core matching |

Recommended future Python dependencies:

```text
sentence-transformers
torch
xgboost
shap
numpy
pandas
scikit-learn
pgvector
beautifulsoup4
requests
```

---

## Testing Strategy

### Sub-Task 3 Tests

- Course preprocessing creates embeddings for all active courses.
- Embedding dimensions match the database vector column.
- Sparse features contain expected keys for sample courses.
- Skill extraction maps known strings like `AWS`, `Python`, `SQL`, and `Agile` to `skills_taxonomy`.

### Sub-Task 4 Tests

- Dense retrieval query returns Top 50 active courses.
- Feature builder calculates cosine similarity, skill hit count, coverage ratio, credits, and locality correctly.
- XGBoost scoring is deterministic for fixed model artifacts.
- Zero skill-hit courses receive lower scores than comparable courses with exact skill hits.

### Sub-Task 5 Tests

- SHAP returns top contributing features for each recommended course.
- Explanation templates map sparse skill features to readable reasons.
- Output JSON includes course facts only from the database.

### End-to-End Scenario

Input:

```json
{
  "skill_gaps": ["AWS", "Python", "Agile"]
}
```

Expected:

- Dense retrieval finds relevant computing/cloud/software project courses.
- XGBoost reranks courses with exact `AWS` or cloud/project skill coverage higher.
- SHAP explanation states which skill or similarity feature drove the recommendation.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `bge-large-en-v1.5` dimension mismatch | Embedding insert fails | Migrate vector columns to `VECTOR(1024)` or use a 768-dim model intentionally |
| University HTML changes | Monthly ingestion fails | Connector tests, source hashes, failure logs, keep old data active |
| Sparse extraction misses skills | Recommendations lose exactness | Use taxonomy synonyms, manual review, and mapping confidence |
| XGBoost lacks real labels | Poor ranking quality | Start with simulated/O*NET-derived labels, improve with user feedback |
| SHAP explanations expose confusing feature names | Poor UX | Use template mapping and hide raw feature names from frontend |

---

## Success Metrics

- Monthly catalog ingestion succeeds for BCIT, UBC, and SFU.
- At least 95% of active courses have valid dense embeddings.
- At least 80% of computing-related courses have one or more sparse skill mappings.
- `/career/course-recommendations` returns Top 3 recommendations in under two seconds at MVP scale.
- Each returned course includes a SHAP-backed explanation.

---

## Document Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-30 | Claude Code | Initial LLM/RAG plan |
| 2.0 | 2026-05-04 | Codex | Updated to catalog ingestion, bge-large-en-v1.5, XGBoost, and SHAP architecture |
