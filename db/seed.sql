-- ==========================================
-- SEED DATA for Career Matching Engine MVP
-- ==========================================

-- ==========================================
-- Phase 1: Geographic Data (Canada-focused)
-- ==========================================
INSERT INTO countries (country_code, country_name, currency_code, is_active) VALUES
('CA', 'Canada', 'CAD', TRUE);

INSERT INTO provinces (country_id, province_code, province_name, is_active) VALUES
(1, 'ON', 'Ontario', TRUE),
(1, 'BC', 'British Columbia', TRUE),
(1, 'AB', 'Alberta', TRUE),
(1, 'QC', 'Quebec', TRUE),
(1, 'MB', 'Manitoba', TRUE);

INSERT INTO cities (province_id, city_name, population, cost_of_living_index, job_market_score, is_active) VALUES
(1, 'Toronto', 2930000, 95.5, 92.0, TRUE),
(1, 'Ottawa', 1017000, 88.2, 85.5, TRUE),
(2, 'Vancouver', 675000, 105.8, 88.3, TRUE),
(2, 'Victoria', 385000, 98.2, 72.1, TRUE),
(3, 'Calgary', 1336000, 82.4, 89.2, TRUE),
(3, 'Edmonton', 1010000, 78.9, 84.6, TRUE),
(4, 'Montreal', 1704000, 86.5, 81.2, TRUE),
(5, 'Winnipeg', 850000, 75.3, 78.9, TRUE);

-- ==========================================
-- Phase 2: Core User Data
-- ==========================================
INSERT INTO users (email, password_hash, first_name, last_name, current_city_id, profile_completion, email_verified, is_active) VALUES
('john.smith@example.com', '$2b$12$abcdef1234567890', 'John', 'Smith', 1, 45.0, TRUE, TRUE),
('sarah.tech@example.com', '$2b$12$abcdef1234567890', 'Sarah', 'Johnson', 3, 72.0, TRUE, TRUE),
('alex.creative@example.com', '$2b$12$abcdef1234567890', 'Alex', 'Chen', 1, 58.0, TRUE, TRUE),
('emma.data@example.com', '$2b$12$abcdef1234567890', 'Emma', 'Williams', 2, 85.0, TRUE, TRUE),
('michael.ops@example.com', '$2b$12$abcdef1234567890', 'Michael', 'Brown', 5, 62.0, FALSE, TRUE);

INSERT INTO user_preferences (user_id, target_job_title, experience_level, salary_min, salary_max, preferred_industries, preferred_work_style, location_flexibility, updated_at) VALUES
(1, 'Software Engineer', 'mid-level', 85000, 120000, '["Technology", "Finance"]'::jsonb, 'hybrid', 'moderate', NOW()),
(2, 'Data Scientist', 'senior', 110000, 150000, '["Technology", "Healthcare"]'::jsonb, 'remote', 'high', NOW()),
(3, 'UX Designer', 'mid-level', 75000, 100000, '["Technology", "E-commerce"]'::jsonb, 'flexible', 'moderate', NOW()),
(4, 'Machine Learning Engineer', 'senior', 120000, 180000, '["Technology", "AI"]'::jsonb, 'hybrid', 'low', NOW()),
(5, 'DevOps Engineer', 'mid-level', 95000, 140000, '["Technology", "SaaS"]'::jsonb, 'remote', 'high', NOW());

-- ==========================================
-- Phase 3: Skills Taxonomy (Common Tech & Professional Skills)
-- ==========================================
INSERT INTO skills_taxonomy (skill_name, skill_category, skill_subcategory, skill_description, skill_synonyms, is_technical, proficiency_levels, learning_time_weeks, demand_score, salary_impact, last_updated, created_at) VALUES
('Python', 'Programming Language', 'Backend', 'Python programming language for web development and data science', '["Python3", "Py"]'::jsonb, TRUE, '["Beginner", "Intermediate", "Advanced", "Expert"]'::jsonb, 8, 95.5, 8500, NOW(), NOW()),
('JavaScript', 'Programming Language', 'Frontend', 'JavaScript for web development and frontend applications', '["JS", "ES6", "TypeScript"]'::jsonb, TRUE, '["Beginner", "Intermediate", "Advanced", "Expert"]'::jsonb, 6, 92.3, 7800, NOW(), NOW()),
('React', 'Framework', 'Frontend', 'React library for building user interfaces', '["React.js", "ReactJS"]'::jsonb, TRUE, '["Beginner", "Intermediate", "Advanced"]'::jsonb, 12, 88.9, 6500, NOW(), NOW()),
('SQL', 'Database', 'Data Management', 'SQL for database queries and management', '["MySQL", "PostgreSQL", "T-SQL"]'::jsonb, TRUE, '["Beginner", "Intermediate", "Advanced"]'::jsonb, 4, 94.1, 7200, NOW(), NOW()),
('Machine Learning', 'AI/ML', 'Data Science', 'Machine learning algorithms and applications', '["ML", "Deep Learning"]'::jsonb, TRUE, '["Intermediate", "Advanced", "Expert"]'::jsonb, 16, 96.8, 12000, NOW(), NOW()),
('Data Analysis', 'Data', 'Analytics', 'Data analysis and visualization', '["Analytics", "BI"]'::jsonb, TRUE, '["Beginner", "Intermediate", "Advanced"]'::jsonb, 10, 89.2, 5600, NOW(), NOW()),
('Communication', 'Soft Skills', 'Interpersonal', 'Effective communication and presentation skills', '["Verbal Communication", "Presentation"]'::jsonb, FALSE, '["Basic", "Intermediate", "Advanced"]'::jsonb, 4, 87.5, 3200, NOW(), NOW()),
('Project Management', 'Management', 'Leadership', 'Project planning and management', '["PM", "Agile", "Scrum"]'::jsonb, FALSE, '["Beginner", "Intermediate", "Advanced"]'::jsonb, 8, 85.3, 4100, NOW(), NOW()),
('Cloud Architecture', 'Cloud', 'Infrastructure', 'AWS, Azure, or GCP cloud platform expertise', '["AWS", "Azure", "GCP", "Cloud"]'::jsonb, TRUE, '["Intermediate", "Advanced", "Expert"]'::jsonb, 12, 93.7, 9800, NOW(), NOW()),
('DevOps', 'Infrastructure', 'Operations', 'DevOps practices and CI/CD pipelines', '["CI/CD", "Docker", "Kubernetes"]'::jsonb, TRUE, '["Intermediate", "Advanced"]'::jsonb, 10, 91.4, 8900, NOW(), NOW());

-- ==========================================
-- Phase 3B: Institution Course Catalogs
-- ==========================================
INSERT INTO institutions (name, slug, website_url, catalog_url, city, province, country, created_at, updated_at) VALUES
('British Columbia Institute of Technology', 'bcit', 'https://www.bcit.ca', 'https://www.bcit.ca/course_subjects/computer-systems-comp/', 'Burnaby', 'British Columbia', 'Canada', NOW(), NOW()),
('University of British Columbia', 'ubc', 'https://www.ubc.ca', 'https://vancouver.calendar.ubc.ca/course-descriptions/subject/cpscv', 'Vancouver', 'British Columbia', 'Canada', NOW(), NOW()),
('Simon Fraser University', 'sfu', 'https://www.sfu.ca', 'https://www.sfu.ca/students/calendar/2026/summer/courses/cmpt/', 'Burnaby', 'British Columbia', 'Canada', NOW(), NOW())
ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    website_url = EXCLUDED.website_url,
    catalog_url = EXCLUDED.catalog_url,
    city = EXCLUDED.city,
    province = EXCLUDED.province,
    country = EXCLUDED.country,
    updated_at = NOW();

CREATE TEMP TABLE staging_course_catalog (
    institution_slug TEXT,
    course_code TEXT,
    subject_code TEXT,
    course_number TEXT,
    title TEXT,
    description TEXT,
    credits NUMERIC,
    course_url TEXT,
    source_url TEXT,
    source_hash TEXT
);

COPY staging_course_catalog
FROM '/docker-entrypoint-initdb.d/data/course_catalog_mvp.csv'
WITH (FORMAT csv, HEADER true);

INSERT INTO courses (
    institution_id,
    course_code,
    subject_code,
    course_number,
    title,
    description,
    credits,
    course_url,
    source_url,
    source_hash,
    last_seen_at,
    is_active,
    created_at,
    updated_at
)
SELECT
    i.id,
    s.course_code,
    s.subject_code,
    s.course_number,
    s.title,
    s.description,
    s.credits,
    s.course_url,
    s.source_url,
    COALESCE(NULLIF(s.source_hash, ''), md5(s.course_code || '|' || s.title || '|' || COALESCE(s.description, ''))),
    NOW(),
    TRUE,
    NOW(),
    NOW()
FROM staging_course_catalog s
JOIN institutions i ON i.slug = s.institution_slug
ON CONFLICT (institution_id, course_code) DO UPDATE SET
    subject_code = EXCLUDED.subject_code,
    course_number = EXCLUDED.course_number,
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    credits = EXCLUDED.credits,
    course_url = EXCLUDED.course_url,
    source_url = EXCLUDED.source_url,
    source_hash = EXCLUDED.source_hash,
    last_seen_at = NOW(),
    is_active = TRUE,
    updated_at = NOW();

CREATE TEMP TABLE staging_course_skill_mapping (
    institution_slug TEXT,
    course_code TEXT,
    skill_name TEXT,
    confidence_score NUMERIC,
    mapping_source TEXT,
    rationale TEXT
);

COPY staging_course_skill_mapping
FROM '/docker-entrypoint-initdb.d/data/course_skill_mapping_mvp.csv'
WITH (FORMAT csv, HEADER true);

INSERT INTO course_skill_mapping (
    course_id,
    skill_taxonomy_id,
    confidence_score,
    mapping_source,
    rationale,
    created_at,
    updated_at
)
SELECT
    c.id,
    st.id,
    s.confidence_score,
    s.mapping_source,
    s.rationale,
    NOW(),
    NOW()
FROM staging_course_skill_mapping s
JOIN institutions i ON i.slug = s.institution_slug
JOIN courses c ON c.institution_id = i.id AND c.course_code = s.course_code
JOIN skills_taxonomy st ON st.skill_name = s.skill_name
ON CONFLICT (course_id, skill_taxonomy_id) DO UPDATE SET
    confidence_score = EXCLUDED.confidence_score,
    mapping_source = EXCLUDED.mapping_source,
    rationale = EXCLUDED.rationale,
    updated_at = NOW();

-- ==========================================
-- Phase 3: NOC Codes (Canadian Job Classification)
-- ==========================================
INSERT INTO noc_codes (noc_code, noc_title, noc_description, skill_level, skill_type, main_duties, employment_requirements, related_job_titles, median_salary_cad, job_outlook, last_updated, created_at) VALUES
('2173', 'Software Developers and Programmers', 'Develop, design and maintain application software', 'Level A', 'Professional', 'Design and develop software; test and debug programs; document code', 'Bachelor degree in Computer Science or equivalent experience', '["Full-stack Developer", "Backend Developer", "Software Engineer"]'::jsonb, 95000, 'Strong demand', NOW(), NOW()),
('2174', 'Database Analysts and Administrators', 'Manage databases and develop and maintain database systems', 'Level A', 'Professional', 'Design database systems; manage backups; ensure data security', 'Bachelor degree in Computer Science or IT', '["Database Administrator", "Data Manager"]'::jsonb, 92000, 'Good demand', NOW(), NOW()),
('2161', 'Computer Network and Web Technicians', 'Install and maintain computer networks and web systems', 'Level B', 'Technical', 'Install network infrastructure; troubleshoot connectivity issues', 'Diploma in IT or relevant certification', '["Network Technician", "Web Technician"]'::jsonb, 65000, 'Moderate demand', NOW(), NOW()),
('2171', 'Information Systems Analysts and Consultants', 'Analyze IT systems and advise on solutions', 'Level A', 'Professional', 'Analyze business requirements; design IT solutions; manage implementations', 'Bachelor degree in IT or Business', '["Systems Analyst", "IT Consultant"]'::jsonb, 98000, 'Strong demand', NOW(), NOW()),
('2162', 'Information and Communications Technology Specialists', 'Provide technical support and IT consulting', 'Level A', 'Professional', 'Provide technical support; troubleshoot issues; advise on IT solutions', 'Diploma or Bachelor in IT', '["IT Specialist", "Tech Support Specialist"]'::jsonb, 72000, 'Good demand', NOW(), NOW());

-- ==========================================
-- Phase 3: Job Profiles (Sample Job Postings)
-- ==========================================
INSERT INTO job_profiles (job_title, company_name, job_description, required_skills, preferred_skills, experience_level, salary_min, salary_max, salary_currency, city_id, remote_work_option, employment_type, industry, noc_code, job_source, market_demand, last_updated, created_at) VALUES
('Senior Software Engineer', 'TechCorp Inc', 'We are looking for an experienced software engineer to lead development of our cloud platform', '["Python", "SQL", "Cloud Architecture"]'::jsonb, '["Machine Learning", "Docker"]'::jsonb, 'senior', 120000, 160000, 'CAD', 1, TRUE, 'Full-time', 'Technology', '2173', 'Internal', 'High', NOW(), NOW()),
('Data Scientist', 'DataInsights Ltd', 'Join our analytics team to build predictive models and analyze large datasets', '["Python", "Machine Learning", "Data Analysis"]'::jsonb, '["SQL", "Communication"]'::jsonb, 'mid-level', 95000, 135000, 'CAD', 2, TRUE, 'Full-time', 'Technology', '2171', 'LinkedIn', 'High', NOW(), NOW()),
('React Frontend Developer', 'WebSolutions Co', 'Develop responsive web applications using React and modern JavaScript', '["JavaScript", "React", "Communication"]'::jsonb, '["Cloud Architecture", "Project Management"]'::jsonb, 'mid-level', 85000, 120000, 'CAD', 1, TRUE, 'Full-time', 'Technology', '2173', 'Internal', 'High', NOW(), NOW()),
('Database Administrator', 'FinanceFlow Systems', 'Manage and optimize our PostgreSQL and MySQL database infrastructure', '["SQL", "DevOps"]'::jsonb, '["Cloud Architecture", "Project Management"]'::jsonb, 'mid-level', 90000, 130000, 'CAD', 3, FALSE, 'Full-time', 'Finance', '2174', 'Indeed', 'Medium', NOW(), NOW()),
('DevOps Engineer', 'CloudStack Services', 'Design and maintain CI/CD pipelines and cloud infrastructure using AWS', '["DevOps", "Cloud Architecture"]'::jsonb, '["Python", "Project Management"]'::jsonb, 'senior', 110000, 150000, 'CAD', 5, TRUE, 'Full-time', 'Technology', '2173', 'LinkedIn', 'High', NOW(), NOW());

-- ==========================================
-- Phase 4: User Profiles & Experience
-- ==========================================
INSERT INTO user_profiles (user_id, linkedin_url, current_job_title, current_company, is_current, created_at, updated_at) VALUES
(1, 'https://linkedin.com/in/johnsmith', 'Junior Software Engineer', 'StartupXYZ', TRUE, NOW(), NOW()),
(2, 'https://linkedin.com/in/sarahjohnson', 'Senior Data Scientist', 'BigDataCorp', TRUE, NOW(), NOW()),
(3, 'https://linkedin.com/in/alexchen', 'UI/UX Designer', 'DesignStudio', TRUE, NOW(), NOW()),
(4, 'https://linkedin.com/in/emmawilliams', 'ML Engineer', 'AILabs', TRUE, NOW(), NOW()),
(5, 'https://linkedin.com/in/michaelbrown', 'Systems Administrator', 'InfoTech Solutions', TRUE, NOW(), NOW());

INSERT INTO work_experience (user_profile_id, company_name, job_title, start_date, end_date, is_current, description, created_at) VALUES
(1, 'StartupXYZ', 'Junior Software Engineer', '2022-06-01', NULL, TRUE, 'Developed backend APIs using Python and Django; worked with PostgreSQL databases', NOW()),
(1, 'TechCorp', 'Intern', '2021-09-01', '2022-05-31', FALSE, 'Assisted in frontend development using JavaScript', NOW()),
(2, 'BigDataCorp', 'Senior Data Scientist', '2020-01-15', NULL, TRUE, 'Led machine learning projects; mentored junior data scientists', NOW()),
(2, 'DataAnalytics Co', 'Data Scientist', '2018-03-01', '2019-12-31', FALSE, 'Analyzed datasets and built predictive models', NOW()),
(3, 'DesignStudio', 'UI/UX Designer', '2021-02-01', NULL, TRUE, 'Designed user interfaces for web and mobile applications', NOW()),
(4, 'AILabs', 'ML Engineer', '2019-07-01', NULL, TRUE, 'Developed and deployed machine learning models at scale', NOW()),
(5, 'InfoTech Solutions', 'Systems Administrator', '2018-11-01', NULL, TRUE, 'Managed IT infrastructure and support systems', NOW());

INSERT INTO education_history (user_profile_id, institution_name, degree_type, field_of_study, specialization, start_date, end_date, gpa, is_current, city_id, created_at) VALUES
(1, 'University of Toronto', 'Bachelor', 'Computer Science', 'Software Engineering', '2018-09-01', '2022-05-31', 3.7, FALSE, 1, NOW()),
(2, 'Simon Fraser University', 'Master', 'Data Science', 'Machine Learning', '2016-09-01', '2018-05-31', 3.8, FALSE, 3, NOW()),
(3, 'Ryerson University', 'Bachelor', 'Design', 'User Experience Design', '2019-09-01', '2023-05-31', 3.6, TRUE, 1, NOW()),
(4, 'University of Waterloo', 'Master', 'Computer Science', 'Artificial Intelligence', '2017-09-01', '2019-05-31', 3.9, FALSE, 1, NOW()),
(5, 'Red River Polytechnic', 'Diploma', 'Information Technology', 'Systems Administration', '2016-09-01', '2018-05-31', 3.5, FALSE, 8, NOW());

-- ==========================================
-- Phase 4: VISI Assessments
-- ==========================================
INSERT INTO visi_assessments (user_id, assessment_version, questions_answers, values_scores, interests_scores, skills_scores, income_preferences, personality_type, key_strengths, completion_time_minutes, is_current, completed_at) VALUES
(1, '1.0', '{"q1": "Creative problem-solving", "q2": "Team collaboration", "q3": "Technical challenges"}'::jsonb, '{"innovation": 85, "stability": 60, "growth": 90}'::jsonb, '{"technology": 95, "business": 70, "creative": 65}'::jsonb, '{"coding": 85, "communication": 70, "leadership": 55}'::jsonb, '{"min": 85000, "max": 150000, "currency": "CAD"}'::jsonb, 'INTJ', '["Analytical Thinking", "Problem Solving"]'::jsonb, 35, TRUE, NOW()),
(2, '1.0', '{"q1": "Data analysis", "q2": "Research", "q3": "Mentoring"}'::jsonb, '{"growth": 95, "innovation": 88, "autonomy": 80}'::jsonb, '{"science": 92, "technology": 90, "research": 95}'::jsonb, '{"analytics": 95, "machine_learning": 92, "communication": 80}'::jsonb, '{"min": 110000, "max": 200000, "currency": "CAD"}'::jsonb, 'INTP', '["Data Analysis", "Strategic Thinking"]'::jsonb, 42, TRUE, NOW()),
(3, '1.0', '{"q1": "Design", "q2": "User experience", "q3": "Visual communication"}'::jsonb, '{"creativity": 92, "collaboration": 85, "impact": 88}'::jsonb, '{"design": 98, "technology": 75, "art": 90}'::jsonb, '{"design": 90, "communication": 85, "project_management": 60}'::jsonb, '{"min": 75000, "max": 130000, "currency": "CAD"}'::jsonb, 'ENFP', '["Creative Expression", "User-Centered Design"]'::jsonb, 38, TRUE, NOW()),
(4, '1.0', '{"q1": "AI research", "q2": "Innovation", "q3": "Cutting-edge technology"}'::jsonb, '{"innovation": 98, "growth": 95, "autonomy": 90}'::jsonb, '{"technology": 98, "science": 95, "research": 92}'::jsonb, '{"machine_learning": 98, "python": 95, "research": 93}'::jsonb, '{"min": 120000, "max": 200000, "currency": "CAD"}'::jsonb, 'INTJ', '["Innovation", "Deep Learning"]'::jsonb, 40, TRUE, NOW()),
(5, '1.0', '{"q1": "Systems management", "q2": "Reliability", "q3": "Infrastructure"}'::jsonb, '{"stability": 88, "growth": 75, "autonomy": 80}'::jsonb, '{"technology": 80, "operations": 85, "infrastructure": 88}'::jsonb, '{"devops": 85, "cloud": 80, "problem_solving": 85}'::jsonb, '{"min": 95000, "max": 160000, "currency": "CAD"}'::jsonb, 'ISTJ', '["System Reliability", "Infrastructure Design"]'::jsonb, 36, TRUE, NOW());

-- ==========================================
-- Phase 5: Career Recommendations
-- ==========================================
INSERT INTO career_recommendations (user_id, visi_assessment_id, user_profile_id, recommendation_type, recommended_careers, match_scores, skills_gap_analysis, learning_pathways, market_insights, salary_projections, confidence_score, processing_time_seconds, llm_model_used, data_sources, expires_at, generated_at) VALUES
(1, 1, 1, 'career_path', '["Software Engineer", "Solutions Architect", "Tech Lead"]'::jsonb, '{"Software Engineer": 88, "Solutions Architect": 76, "Tech Lead": 71}'::jsonb, '{"gaps": ["Cloud Architecture", "Leadership"], "strength": ["Python", "Problem Solving"]}'::jsonb, '["AWS Certification (3-6 months)", "Leadership Training (6-12 months)"]'::jsonb, '{"demand": "Very High", "growth": "15-20% annually"}'::jsonb, '{"1yr": 115000, "3yr": 145000, "5yr": 180000}'::jsonb, 0.92, 2.3, 'claude-3-sonnet', '["VISI Assessment", "Resume Analysis", "Job Market Data"]'::jsonb, NOW() + INTERVAL '1 year', NOW()),
(2, 2, 2, 'career_path', '["Principal Data Scientist", "ML Research Lead", "Data Engineering Lead"]'::jsonb, '{"Principal Data Scientist": 96, "ML Research Lead": 93, "Data Engineering Lead": 85}'::jsonb, '{"gaps": [], "strength": ["Machine Learning", "Analytics", "Leadership"]}'::jsonb, '["Advanced ML Techniques (ongoing)", "Team Leadership (3-6 months)"]'::jsonb, '{"demand": "Very High", "growth": "25%+ annually"}'::jsonb, '{"1yr": 155000, "3yr": 185000, "5yr": 220000}'::jsonb, 0.94, 2.8, 'claude-3-sonnet', '["VISI Assessment", "Work History", "Skills Assessment"]'::jsonb, NOW() + INTERVAL '1 year', NOW()),
(3, 3, 3, 'career_path', '["Senior UX Designer", "Product Designer", "Design Lead"]'::jsonb, '{"Senior UX Designer": 91, "Product Designer": 88, "Design Lead": 79}'::jsonb, '{"gaps": ["Project Management", "Product Strategy"], "strength": ["Design", "Communication"]}'::jsonb, '["Product Management Basics (3-4 months)", "Design Leadership (6-9 months)"]'::jsonb, '{"demand": "High", "growth": "10-15% annually"}'::jsonb, '{"1yr": 105000, "3yr": 140000, "5yr": 170000}'::jsonb, 0.89, 2.5, 'claude-3-sonnet', '["VISI Assessment", "Portfolio Analysis", "Market Research"]'::jsonb, NOW() + INTERVAL '1 year', NOW()),
(4, 4, 4, 'career_path', '["AI/ML Research Scientist", "ML Platform Lead", "Chief AI Officer"]'::jsonb, '{"AI/ML Research Scientist": 97, "ML Platform Lead": 94, "Chief AI Officer": 88}'::jsonb, '{"gaps": ["Business Strategy"], "strength": ["Deep Learning", "Innovation", "Research"]}'::jsonb, '["Advanced AI Techniques (ongoing)", "Business Strategy (6-12 months)"]'::jsonb, '{"demand": "Critical", "growth": "30%+ annually"}'::jsonb, '{"1yr": 175000, "3yr": 220000, "5yr": 280000}'::jsonb, 0.95, 3.1, 'claude-3-sonnet', '["VISI Assessment", "Technical Skills", "Innovation Metrics"]'::jsonb, NOW() + INTERVAL '1 year', NOW()),
(5, 5, 5, 'career_path', '["Senior DevOps Engineer", "Infrastructure Lead", "Cloud Architect"]'::jsonb, '{"Senior DevOps Engineer": 90, "Infrastructure Lead": 87, "Cloud Architect": 82}'::jsonb, '{"gaps": ["Strategic Planning"], "strength": ["DevOps", "Cloud Architecture", "Systems Design"]}'::jsonb, '["Advanced Cloud Solutions (3-6 months)", "Architectural Design (6-12 months)"]'::jsonb, '{"demand": "Very High", "growth": "18-22% annually"}'::jsonb, '{"1yr": 135000, "3yr": 165000, "5yr": 200000}'::jsonb, 0.91, 2.6, 'claude-3-sonnet', '["VISI Assessment", "Experience Analysis", "Technology Trends"]'::jsonb, NOW() + INTERVAL '1 year', NOW());

-- ==========================================
-- Phase 5: Saved Careers
-- ==========================================
INSERT INTO saved_careers (user_id, recommendation_id, career_title, noc_code, match_score, salary_range, market_demand, progress_status, target_date, is_primary_goal, saved_at, updated_at) VALUES
(1, 1, 'Software Engineer', '2173', 0.88, '115K - 180K CAD', 'Very High', 'In Progress', '2026-12-31', TRUE, NOW(), NOW()),
(1, 1, 'Solutions Architect', '2171', 0.76, '130K - 200K CAD', 'High', 'Planning', '2027-12-31', FALSE, NOW(), NOW()),
(2, 2, 'Principal Data Scientist', '2173', 0.96, '155K - 220K CAD', 'Very High', 'In Progress', '2026-06-30', TRUE, NOW(), NOW()),
(3, 3, 'Senior UX Designer', '2173', 0.91, '105K - 170K CAD', 'High', 'Exploring', '2027-06-30', TRUE, NOW(), NOW()),
(4, 4, 'AI/ML Research Scientist', '2173', 0.97, '175K - 280K CAD', 'Critical', 'Advanced', '2026-12-31', TRUE, NOW(), NOW()),
(5, 5, 'Senior DevOps Engineer', '2173', 0.90, '135K - 200K CAD', 'Very High', 'In Progress', '2026-09-30', TRUE, NOW(), NOW());

-- ==========================================
-- Phase 5: User Feedback
-- ==========================================
INSERT INTO user_feedback (user_id, recommendation_id, career_title, match_score, salary_range, market_demand, saved_at) VALUES
(1, 1, 'Software Engineer', 88, '115K - 180K CAD', 'Very High', NOW()),
(2, 2, 'Principal Data Scientist', 96, '155K - 220K CAD', 'Very High', NOW()),
(3, 3, 'Senior UX Designer', 91, '105K - 170K CAD', 'High', NOW()),
(4, 4, 'AI/ML Research Scientist', 97, '175K - 280K CAD', 'Critical', NOW()),
(5, 5, 'Senior DevOps Engineer', 90, '135K - 200K CAD', 'Very High', NOW());
