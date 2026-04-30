# Career Matching Engine - LLM Integration Plan

## Context

The Career Matching Engine MVP has a fully populated PostgreSQL database with vector support (pgvector extension). The database contains:
- User profiles, assessments (VISI), and preferences
- Job market data (5+ sample job profiles)
- Skills taxonomy (10+ skills with demand/salary impact)
- NOC codes (Canadian occupation classifications)
- Geographic data (Canadian cities with job market scores)
- Three vector indexes (HNSW) on `noc_codes`, `skills_taxonomy`, and `job_profiles`

**Goal:** Enable the LLM (via OpenRouter) to provide intelligent, data-driven recommendations to users about:
1. **Career paths** - based on VISI assessments and user skills
2. **Colleges/Educational institutions** - relevant to target career
3. **Courses/Learning pathways** - to bridge skill gaps

**Approach:** Implement a Retrieval-Augmented Generation (RAG) system that searches the database in real-time, retrieves relevant context, and passes it to the LLM for personalized recommendations.

---

## Architecture Overview

### High-Level Flow

```
User Input
    ↓
[Question Vectorization] ← Use OpenRouter embed endpoint
    ↓
[Vector Search] ← Query HNSW indexes for top 5-10 relevant results
    ├─ Search job_profiles for career matches
    ├─ Search noc_codes for related occupations
    ├─ Search skills_taxonomy for skill recommendations
    └─ Query education_history for college patterns
    ↓
[Context Assembly] ← Format retrieved data as structured context
    ├─ User profile data
    ├─ Relevant careers with salary/demand
    ├─ Required vs preferred skills
    ├─ Learning pathways
    └─ Market insights
    ↓
[LLM Prompt Construction] ← Build system prompt + context + user question
    ↓
[OpenRouter API Call] ← Send to Claude/GPT via OpenRouter
    ↓
[Response Generation] ← LLM synthesizes answer with recommendations
    ↓
User Receives Personalized Recommendations
```

---

## Detailed System Components

### 1. Question Vectorization

**Input:** User natural language question
- Example: "I have 5 years of Python experience and want to transition to data science. What career paths should I consider?"

**Process:**
- Call OpenRouter embedding endpoint (text-embedding-3-small or equivalent)
- Generate 768-dimensional vector representation
- Vector captures semantic meaning of the question

**Output:** Float array [768 dimensions]

---

### 2. Vector Search Layer

**Component:** Multi-index search across three tables

#### 2a. Job Profiles Search
- **Query:** Find top 5 job profiles most similar to user's question
- **Index Used:** `job_profiles_embedding_idx` (HNSW, cosine similarity)
- **Retrieved Fields:**
  - `job_title`, `company_name`, `job_description`
  - `salary_min`, `salary_max`, `salary_currency`
  - `required_skills`, `preferred_skills`
  - `experience_level`, `market_demand`
  - `remote_work_option`

**SQL Pattern:**
```
SELECT job_title, company_name, salary_min, salary_max, required_skills
FROM job_profiles
ORDER BY embedding <=> user_question_vector::vector
LIMIT 5
```

#### 2b. NOC Codes Search
- **Query:** Find top 3 relevant occupation classifications
- **Index Used:** `noc_codes_embedding_idx` (HNSW, cosine similarity)
- **Retrieved Fields:**
  - `noc_code`, `noc_title`, `noc_description`
  - `main_duties`, `employment_requirements`
  - `median_salary_cad`, `job_outlook`
  - `related_job_titles`

#### 2c. Skills Taxonomy Search
- **Query:** Find top 5 relevant skills matching user interest
- **Index Used:** `skills_taxonomy_embedding_idx` (HNSW, cosine similarity)
- **Retrieved Fields:**
  - `skill_name`, `skill_category`, `skill_subcategory`
  - `skill_description`, `is_technical`
  - `demand_score`, `salary_impact`, `learning_time_weeks`
  - `proficiency_levels`

---

### 3. Context Assembly Engine

**Input:** Results from all vector searches + user profile data

**Processing Steps:**

#### Step 3a: User Profile Assembly
- Query user's current profile: `user_profiles`, `work_experience`, `education_history`
- Extract VISI assessment: `visi_assessments` (personality, values, interests, skills)
- Get career recommendations history: `career_recommendations`
- Compile user preferences: `user_preferences`

**Output Example:**
```
User Profile Summary:
- Current Role: Junior Software Engineer at StartupXYZ
- Years of Experience: 3 years
- Key Skills: Python, SQL, JavaScript
- VISI Personality Type: INTJ
- Career Interests: Technology, Innovation, Growth
- Salary Expectations: $85K - $150K CAD
- Location: Toronto
```

#### Step 3b: Career Recommendations Section
- Format top 5 job matches with rankings
- Include salary ranges, skill requirements
- Highlight market demand and remote options
- Show alignment with user preferences

**Output Example:**
```
Top 5 Matching Careers:
1. Senior Software Engineer (90% match)
   - Companies: TechCorp Inc, CloudStack Services
   - Salary: $120K - $160K CAD
   - Key Skills Required: Python, Cloud Architecture, DevOps
   - Market Demand: Very High
   - Growth Outlook: 15-20% annually

2. Data Scientist (82% match)
   [...]
```

#### Step 3c: Skills Gap Analysis
- Compare user's current skills with required skills
- Identify skill gaps and learning opportunities
- Calculate effort/time to acquire each skill

**Output Example:**
```
Skills Gap Analysis:
Current Skills: Python (Advanced), SQL (Intermediate)
Target Skills for Senior Engineer Role:
  ✓ Python (have) - Intermediate level
  ✓ SQL (have) - Need to advance
  ✗ Cloud Architecture (gap) - 12 weeks to learn
  ✗ DevOps (gap) - 10 weeks to learn
  ✗ Project Management (gap) - 8 weeks to learn
```

#### Step 3d: Educational Pathways
- Query `education_history` for patterns
- Map skill gaps to learning resources
- Suggest colleges/institutions based on target career
- Recommend relevant courses/certifications

**Output Example:**
```
Recommended Learning Pathways:
1. Cloud Architecture (3-6 months)
   - AWS Certification (SAA-C03)
   - Suggested Providers: Coursera, Linux Academy
   - Estimated Cost: $500-1000 CAD
   - ROI: +$15K-20K salary increase

2. Advanced Python & Data Science (6-12 months)
   - Suggested Program: University of Waterloo, SFU
   - Focus: Machine Learning, Big Data
   - Format: Part-time online + bootcamp
```

---

### 4. LLM Prompt Construction

**System Prompt Template:**
```
You are an expert career advisor specializing in technology careers in Canada. 
Your role is to:
1. Analyze user profiles, skills, and aspirations
2. Recommend specific career paths with realistic timelines
3. Suggest educational institutions and courses aligned with career goals
4. Provide actionable learning pathways with ROI calculations
5. Base all recommendations on real market data and user preferences

Always be specific with:
- Job titles and salary ranges in CAD
- Actual companies and roles from our database
- Concrete learning timelines and resources
- Market demand forecasts and growth trends
```

**User Context Section:**
```
[User Profile Summary - from Step 3a]
[Career Recommendations - from Step 3b]
[Skills Gap Analysis - from Step 3c]
[Educational Pathways - from Step 3d]
```

**User Question:**
```
[Original user question from input]
```

---

### 5. OpenRouter Integration

**API Endpoint Used:** OpenRouter Chat Completions

**Request Structure:**
- **Model:** claude-3-sonnet (or claude-3-opus for higher quality)
- **Max Tokens:** 2000 (for comprehensive recommendations)
- **Temperature:** 0.7 (balance creativity with consistency)
- **System Prompt:** Career advisor instructions (Step 4)
- **Messages:** User question with full context

**Response Processing:**
- Extract text from OpenRouter response
- Validate response length and content quality
- Log recommendation for future analysis
- Return formatted response to user

---

## Data Flow Sequence Diagram

```
┌─────────────┐
│   User      │
│  (Browser)  │
└──────┬──────┘
       │
       │ POST /api/career-recommendation
       │ { user_id: 1, question: "..." }
       │
       ▼
┌──────────────────────────────────────────┐
│     FastAPI Endpoint Handler             │
│  /api/career-recommendation              │
└──────┬───────────────────────────────────┘
       │
       │ 1. Fetch user profile from DB
       │
       ▼
┌──────────────────────────────────────────┐
│  Question Vectorization Service          │
│  - Call OpenRouter embed() API           │
│  - Input: user question                  │
│  - Output: 768-dim vector                │
└──────┬───────────────────────────────────┘
       │
       │ 2. Multi-index vector search
       │
       ├──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
       │                              │                              │                              │
       ▼                              ▼                              ▼                              ▼
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐      ┌──────────────────┐
│  job_profiles       │      │  noc_codes          │      │  skills_taxonomy    │      │  user_profiles   │
│  HNSW Search        │      │  HNSW Search        │      │  HNSW Search        │      │  Direct Query    │
│  Top 5 results      │      │  Top 3 results      │      │  Top 5 results      │      │  (metadata)      │
└──────┬──────────────┘      └──────┬──────────────┘      └──────┬──────────────┘      └────────┬─────────┘
       │                            │                             │                              │
       │ 3. Assemble context        │                             │                              │
       │                            │                             │                              │
       └────────────────────────────┴─────────────────────────────┴──────────────────────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────┐
                    │  Context Assembly Engine     │
                    │  - User Profile Summary      │
                    │  - Career Recommendations    │
                    │  - Skills Gap Analysis       │
                    │  - Learning Pathways         │
                    └──────┬───────────────────────┘
                           │
                           │ 4. Build LLM prompt
                           │
                           ▼
                    ┌──────────────────────────────┐
                    │  LLM Prompt Constructor      │
                    │  - System prompt (role)      │
                    │  - Context section           │
                    │  - User question             │
                    └──────┬───────────────────────┘
                           │
                           │ 5. Call OpenRouter API
                           │
                           ▼
                    ┌──────────────────────────────┐
                    │  OpenRouter API              │
                    │  Model: claude-3-sonnet      │
                    │  Endpoint: /chat/completions │
                    └──────┬───────────────────────┘
                           │
                           │ 6. LLM Generates response
                           │
                           ▼
                    ┌──────────────────────────────┐
                    │  Response Processing         │
                    │  - Parse LLM output          │
                    │  - Validate content          │
                    │  - Format for user           │
                    └──────┬───────────────────────┘
                           │
                           │ 7. Return recommendation
                           │
                           ▼
                    ┌──────────────────────────────┐
                    │  User                        │
                    │  Receives Answer             │
                    └──────────────────────────────┘
```

---

## Key Database Queries

### Query 1: Vectorize User Question
```python
# Pseudocode
question_vector = openrouter.embedding.create(
    input=user_question,
    model="text-embedding-3-small"
)
```

### Query 2: Find Similar Job Profiles
```sql
SELECT 
    id, job_title, company_name, job_description,
    salary_min, salary_max, required_skills, preferred_skills,
    experience_level, market_demand, remote_work_option,
    embedding <-> :question_vector::vector AS distance
FROM job_profiles
ORDER BY embedding <-> :question_vector::vector
LIMIT 5;
```

### Query 3: Find Related NOC Codes
```sql
SELECT 
    id, noc_code, noc_title, noc_description,
    main_duties, employment_requirements, median_salary_cad, job_outlook,
    embedding <-> :question_vector::vector AS distance
FROM noc_codes
ORDER BY embedding <-> :question_vector::vector
LIMIT 3;
```

### Query 4: Find Relevant Skills
```sql
SELECT 
    id, skill_name, skill_category, skill_subcategory,
    skill_description, is_technical, demand_score, salary_impact,
    learning_time_weeks, proficiency_levels,
    embedding <-> :question_vector::vector AS distance
FROM skills_taxonomy
ORDER BY embedding <-> :question_vector::vector
LIMIT 5;
```

### Query 5: Get User Profile Context
```sql
SELECT 
    u.id, u.email, u.first_name, u.last_name, u.current_city_id,
    up.current_job_title, up.current_company,
    upref.target_job_title, upref.experience_level, 
    upref.salary_min, upref.salary_max,
    va.personality_type, va.key_strengths
FROM users u
LEFT JOIN user_profiles up ON u.id = up.user_id
LEFT JOIN user_preferences upref ON u.id = upref.user_id
LEFT JOIN visi_assessments va ON u.id = va.user_id
WHERE u.id = :user_id
AND va.is_current = TRUE;
```

### Query 6: Get User's Skill Background
```sql
SELECT 
    es.raw_skill_text, es.proficiency_level, es.years_experience,
    st.skill_name, st.demand_score, st.salary_impact
FROM extracted_skills es
LEFT JOIN skills_taxonomy st ON es.skill_taxonomy_id = st.id
WHERE es.user_profile_id = (
    SELECT id FROM user_profiles WHERE user_id = :user_id
)
ORDER BY es.years_experience DESC;
```

---

## API Endpoint Specification

### Endpoint: POST /api/career-recommendation

**Request:**
```json
{
  "user_id": 1,
  "question": "I have 5 years of Python experience and want to transition to data science. What careers should I pursue? What colleges offer relevant programs?"
}
```

**Response (Success 200):**
```json
{
  "status": "success",
  "user_id": 1,
  "question": "...",
  "recommendation": {
    "career_paths": [
      {
        "title": "Data Scientist",
        "match_score": 0.92,
        "description": "...",
        "salary_range": "$95K - $135K CAD",
        "required_skills": ["Python", "Machine Learning", "Statistics"],
        "market_demand": "Very High",
        "timeframe_to_achieve": "1-2 years"
      }
    ],
    "educational_recommendations": [
      {
        "institution": "University of Waterloo",
        "program": "Master of Data Science",
        "duration_months": 24,
        "cost_cad": 45000,
        "relevance_score": 0.95,
        "skills_covered": ["Machine Learning", "Data Analytics", "Statistics"]
      }
    ],
    "learning_pathways": [
      {
        "skill_name": "Machine Learning",
        "current_proficiency": "Beginner",
        "target_proficiency": "Advanced",
        "estimated_weeks": 16,
        "resources": ["Coursera", "DataCamp", "Fast.ai"]
      }
    ],
    "llm_recommendation": "Based on your background and the current job market... [full LLM-generated response]"
  },
  "processing_time_ms": 2543,
  "data_freshness": "real-time"
}
```

**Error Response (4xx/5xx):**
```json
{
  "status": "error",
  "error_code": "INVALID_USER_ID",
  "message": "User not found in database"
}
```

---

## Implementation Checklist

### Phase 1: Foundation (Week 1)
- [ ] Create SQLAlchemy ORM models for all 19 tables
- [ ] Set up database connection pool
- [ ] Create vector search utility functions
- [ ] Test HNSW indexes are functioning correctly
- [ ] Verify pgvector extension in production database

### Phase 2: Service Layer (Week 1-2)
- [ ] Implement QuestionVectorizer service (OpenRouter embedding)
- [ ] Implement VectorSearchService (multi-index queries)
- [ ] Implement ContextAssemblyService (format search results)
- [ ] Implement UserProfileService (fetch user data)
- [ ] Create LLMPromptBuilder service

### Phase 3: Integration (Week 2)
- [ ] Integrate OpenRouter API client
- [ ] Implement LLMRecommendationService
- [ ] Create response formatting logic
- [ ] Add error handling and logging
- [ ] Implement response caching (optional for performance)

### Phase 4: API Layer (Week 2)
- [ ] Create FastAPI endpoint `/api/career-recommendation`
- [ ] Add input validation and sanitization
- [ ] Implement request/response schemas (Pydantic)
- [ ] Add authentication middleware (if needed)
- [ ] Create comprehensive API documentation

### Phase 5: Testing & Optimization (Week 3)
- [ ] Unit tests for each service
- [ ] Integration tests with database
- [ ] Load testing with OpenRouter API
- [ ] Latency optimization
- [ ] Vector search accuracy validation

### Phase 6: Deployment (Week 3-4)
- [ ] Containerize the updated application
- [ ] Update docker-compose.yml with environment variables
- [ ] Deploy to staging
- [ ] User acceptance testing
- [ ] Deploy to production

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | FastAPI | REST API, async support |
| **ORM** | SQLAlchemy 2.0 | Database abstraction |
| **Database** | PostgreSQL 16 + pgvector | Vector storage & search |
| **Embedding** | OpenRouter API | Question vectorization |
| **LLM** | Claude 3 (via OpenRouter) | Recommendation generation |
| **Async** | Python asyncio | Non-blocking I/O |
| **Validation** | Pydantic | Request/response schemas |
| **Logging** | Python logging | Monitoring & debugging |

---

## Performance Considerations

### Latency Breakdown (Target: < 5 seconds)

1. **Question Vectorization:** ~500ms
   - OpenRouter API call with embedding
   - Network I/O

2. **Vector Search:** ~200-400ms
   - HNSW index lookups (3 parallel queries)
   - Database query execution

3. **Context Assembly:** ~300-500ms
   - Additional database queries for context
   - Data formatting and transformation

4. **LLM API Call:** ~2-3 seconds
   - OpenRouter request transmission
   - Claude model inference time

5. **Response Processing:** ~100-200ms
   - Parse and format LLM output

**Total Expected:** 3.5-5 seconds (real-time, acceptable for web app)

### Optimization Strategies

- **Connection Pooling:** Reuse database connections
- **Parallel Searches:** Execute vector searches concurrently
- **Caching:** Cache question vectors for identical queries (optional)
- **Lazy Loading:** Fetch additional context only if needed
- **Batch Requests:** Support multiple users simultaneously

---

## Error Handling Strategy

### Possible Failures & Mitigation

| Failure | Cause | Mitigation |
|---------|-------|-----------|
| User not found | Invalid user_id | Return 404 with helpful message |
| OpenRouter API down | Network/service issue | Fallback to cached embeddings or retry |
| Database connection fail | PostgreSQL unavailable | Retry with exponential backoff |
| Vector search timeout | Large data volume | Set query timeout, limit result set |
| LLM API error | Rate limit/quota exceeded | Queue request, retry with delay |
| Invalid question | Empty or malformed input | Validate input, return 400 error |

---

## Security Considerations

1. **Input Validation**
   - Sanitize user questions (no SQL injection)
   - Limit question length (< 1000 chars)
   - Validate user_id format

2. **API Security**
   - Rate limiting per user/IP
   - Authentication via API key or JWT
   - CORS policy enforcement

3. **Data Privacy**
   - Encrypt OpenRouter API key in environment
   - Don't log sensitive user data
   - Implement access control (users see only their recommendations)

4. **LLM Output**
   - Validate LLM response before returning
   - Sanitize HTML/script content
   - Monitor for prompt injection attempts

---

## Verification & Testing Strategy

### Unit Tests
- Test vectorization service with mock OpenRouter
- Test context assembly with sample data
- Test prompt construction with various inputs
- Test vector search queries with seeded data

### Integration Tests
- End-to-end flow with real database
- Real OpenRouter API calls (subset)
- Multiple user profiles simultaneously
- Error scenarios and edge cases

### User Acceptance Testing
- Test with 5 sample user profiles
- Verify recommendation quality and accuracy
- Check response time meets SLA (< 5 seconds)
- Validate educational recommendations align with career paths

### Manual Testing Scenarios

**Scenario 1: Junior Developer → Senior Engineer**
```
Input: User with 3 years Python, wants to progress to Senior SWE
Expected: Recommend cloud skills, leadership training, specific companies
```

**Scenario 2: Career Changer**
```
Input: User with 8 years in non-tech, 1 year bootcamp Python
Expected: Recommend junior roles, foundational courses, realistic timeline
```

**Scenario 3: Geographic Preference**
```
Input: User in Vancouver wanting remote work
Expected: Show remote job opportunities, relevant BC institutions
```

---

## Future Enhancements (Out of Scope)

1. **Fine-tuned Model:** Train custom embedding model on career data
2. **Feedback Loop:** Track recommendation quality, user satisfaction
3. **Skill Verification:** Integrate with LinkedIn/GitHub for skill validation
4. **Job Board Integration:** Real-time job listings from Indeed/LinkedIn
5. **Salary Prediction:** ML model for salary forecasting
6. **Interactive Refinement:** Follow-up questions to refine recommendations
7. **Batch Recommendations:** Schedule recommendations for users periodically

---

## Success Metrics

1. **Latency:** Average response time < 5 seconds (p95 < 7 seconds)
2. **Accuracy:** Career recommendations match user preferences 85%+
3. **Relevance:** Educational suggestions map to top 3 careers 90%+
4. **Availability:** System uptime 99.5%+
5. **Cost:** API calls < $0.50 per recommendation
6. **User Satisfaction:** Recommendation helpfulness rating 4.5/5.0+

---

## Dependencies & Resources

### External APIs
- **OpenRouter:** For embedding and LLM access
- **PostgreSQL 16:** Database with pgvector extension
- **FastAPI:** Web framework

### Python Libraries
```
fastapi>=0.104.0
sqlalchemy>=2.0
psycopg2-binary>=2.9
pgvector>=0.2.0
openai>=1.0 (OpenRouter compatible)
pydantic>=2.0
python-dotenv>=1.0
uvicorn>=0.24.0
```

### Infrastructure
- Docker & Docker Compose
- PostgreSQL container (pgvector/pgvector:pg16)
- Python 3.11+

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| OpenRouter API rate limit | Medium | High | Implement request queuing, request caching |
| LLM generates incorrect data | Low | High | Validate facts against database, human review initial rollout |
| Vector search latency spike | Low | Medium | Add query timeouts, implement fallback strategies |
| Cold starts / slow embeddings | Medium | Medium | Pre-warm cache, implement async processing |
| Data consistency issues | Low | Medium | Transaction management, data validation |

---

## Appendix: Sample Data Flow Example

**User Input:**
```
User ID: 2 (Sarah Johnson, Senior Data Scientist aspirant)
Question: "I want to transition from generic data analyst to ML-focused roles. 
What colleges offer specialized ML programs? What's the timeline?"
```

**Step 1: Vectorization**
- Question vectorized: 768-dim vector capturing ML transition theme

**Step 2: Vector Search Results**

*Job Profiles (Top 2):*
- Senior Data Scientist at DataInsights Ltd (salary: $110K-$150K, match: 0.96)
- ML Engineer at AILabs (salary: $120K-$180K, match: 0.94)

*NOC Codes (Top 2):*
- 2173 Software Developers (median: $95K, match: 0.91)
- 2171 Systems Analysts (median: $98K, match: 0.88)

*Skills (Top 3):*
- Machine Learning (demand: 96.8, impact: +$12K, learn: 16 weeks)
- Python (demand: 95.5, impact: +$8.5K, learn: 8 weeks)
- Data Analysis (demand: 89.2, impact: +$5.6K, learn: 10 weeks)

**Step 3: Context Assembly**

*User Profile:*
- Current: Senior Data Scientist at BigDataCorp
- Years: 4-6 years experience
- Personality: INTP (analytical, research-oriented)
- Skills Gap: Need advanced ML expertise

*Recommendations:*
- Primary: ML Engineer (14-20% salary increase possible)
- Timeline: 6-12 months intensive study

**Step 4: LLM Prompt**
```
You are a career advisor. Based on this context:

User: Sarah Johnson, Senior Data Scientist, 5+ years experience
Current Skills: Advanced Data Analysis, Python, SQL
Target: Machine Learning Engineering focus
Available Universities: [SFU, UWaterloo, UBC]
Market Data: ML Engineer roles at 0.96 similarity match

User's Question: "I want to transition from generic data analyst to ML-focused roles. 
What colleges offer specialized ML programs? What's the timeline?"

Provide specific college recommendations and realistic timeline.
```

**Step 5: LLM Response**
```
Based on your background and the current job market in Canada, here's my recommendation:

Top College Programs for ML Transition:
1. University of Waterloo - Master of Data Science (24 months)
   - Focus: Machine Learning, Big Data, AI
   - Cost: ~$45K CAD
   - Match: 95% (covers all skills needed for ML Engineer role)

2. Simon Fraser University - Master of Data Science (20 months)
   - Format: Part-time flexible, online options
   - Cost: ~$35K CAD
   - Match: 92%

3. UBC - Master of Data Science (24 months)
   - Specialized ML track available
   - Cost: ~$50K CAD
   - Match: 94%

Timeline to ML Engineer Role:
- 3-6 months: Complete core ML courses + build portfolio
- 6-12 months: Interview for mid-level ML roles
- 12-18 months: Transition to senior ML Engineer (estimated salary: $155K-$190K)

Your current skills (Python, Data Analysis, Statistics) provide a strong foundation.
Focus on: Deep Learning, ML Systems Design, and MLOps practices.
```

---

## Document Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-30 | Claude Code | Initial plan document |

