import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection details
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "careerMatchingEngine")
DB_HOST = "localhost" # Assume localhost if running outside
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS onet_occupations (
    onetsoc_code VARCHAR(20) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS onet_knowledge_elements (
    element_id VARCHAR(20) PRIMARY KEY,
    element_name VARCHAR(255) NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS onet_work_activities_elements (
    element_id VARCHAR(20) PRIMARY KEY,
    element_name VARCHAR(255) NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS onet_occupation_vectors (
    onetsoc_code VARCHAR(20) PRIMARY KEY REFERENCES onet_occupations(onetsoc_code),
    vector VECTOR(74), -- 33 Knowledge elements + 41 Work Activity elements
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS onet_occupation_vectors_idx ON onet_occupation_vectors USING hnsw (vector vector_cosine_ops);
"""

def init_db():
    print(f"Connecting to {DATABASE_URL}...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(SQL)
    conn.commit()
    cur.close()
    conn.close()
    print("O*NET tables initialized.")

if __name__ == "__main__":
    init_db()
