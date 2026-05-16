import pandas as pd
import os
import psycopg2
import json
from dotenv import load_dotenv

load_dotenv()

# Database connection parameters
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASSWORD", "postgres")

OASIS_DIR = os.path.join(os.path.dirname(__file__), '../data/oasis/processed_xlsx')

NUMERICAL_FILES = {
    'abilities': 'abilities_oasis_2025_v1.1.xlsx',
    'skills': 'skills_oasis_2025_v1.1.xlsx',
    'work_context': 'work-context_oasis_2025_v1.1.xlsx',
    'knowledge': 'knowledge_oasis_2025_v.1.1.xlsx',
    'personal_attributes': 'personal-attributes_oasis_2025_v1.1.xlsx',
    'work_activities': 'work-activities_oasis_2025_v1.1.xlsx'
}

TEXT_FILES = {
    'core_competencies': 'corecompetencies_oasis_2025_v1.1-en.xlsx',
    'interests': 'interests_oasis_2025_v1.1.xlsx'
}

# Known dimensions for vector padding
DIMS = {
    'abilities': 52,
    'skills': 33,
    'work_context': 66,
    'knowledge': 44,
    'personal_attributes': 13,
    'work_activities': 39
}

def process_numerical_file(filepath):
    df = pd.read_excel(filepath)
    df = df.rename(columns={df.columns[0]: 'code', df.columns[1]: 'title'})
    df['code'] = df['code'].astype(str)
    feature_cols = df.columns[2:]
    df[feature_cols] = df[feature_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
    df['vector'] = df[feature_cols].values.tolist()
    return df[['code', 'title', 'vector']]

def process_text_file(filepath):
    df = pd.read_excel(filepath)
    df = df.rename(columns={df.columns[0]: 'code', df.columns[1]: 'title'})
    df['code'] = df['code'].astype(str)
    feature_cols = df.columns[2:]
    df[feature_cols] = df[feature_cols].astype(str).replace('nan', '')
    df['text_data'] = df[feature_cols].to_dict(orient='records')
    return df[['code', 'text_data']]

def main():
    print("Connecting to database...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        cur = conn.cursor()
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return

    domain_dfs = {}
    
    print("Reading OaSIS Numerical Excel files...")
    for domain, filename in NUMERICAL_FILES.items():
        filepath = os.path.join(OASIS_DIR, filename)
        if os.path.exists(filepath):
            print(f"Processing {domain}...")
            domain_dfs[domain] = process_numerical_file(filepath)
        else:
            print(f"Warning: File not found: {filepath}")

    print("Reading OaSIS Text Excel files...")
    for domain, filename in TEXT_FILES.items():
        filepath = os.path.join(OASIS_DIR, filename)
        if os.path.exists(filepath):
            print(f"Processing {domain}...")
            domain_dfs[domain] = process_text_file(filepath)
        else:
            print(f"Warning: File not found: {filepath}")

    if not domain_dfs:
        print("No files were found to process.")
        return

    # Base dataframe to merge everything
    base_domain = list(domain_dfs.keys())[0]
    merged_df = domain_dfs[base_domain][['code']].copy()

    # Get the title from whichever file has it
    titles_df = pd.concat([df[['code', 'title']] for domain, df in domain_dfs.items() if 'title' in df.columns]).drop_duplicates(subset=['code'])
    merged_df = pd.merge(merged_df, titles_df, on='code', how='outer')

    for domain, df in domain_dfs.items():
        if domain in NUMERICAL_FILES:
            df_domain = df[['code', 'vector']].rename(columns={'vector': f'{domain}_vector'})
        else:
            df_domain = df[['code', 'text_data']].rename(columns={'text_data': f'{domain}_data'})
        merged_df = pd.merge(merged_df, df_domain, on='code', how='outer')

    print(f"Merged data for {len(merged_df)} occupations.")
    merged_df = merged_df.sort_values('code')

    inserted_count = 0
    print("Inserting data into PostgreSQL...")
    for _, row in merged_df.iterrows():
        code = str(row['code'])
        title = str(row['title']) if 'title' in row and not pd.isna(row['title']) else 'Unknown Title'

        vectors = {}
        combined_vector = []
        domain_order = ['abilities', 'skills', 'work_context', 'knowledge', 'personal_attributes', 'work_activities']

        for domain in domain_order:
            vec_col = f'{domain}_vector'
            if vec_col in row and isinstance(row[vec_col], list):
                vec = row[vec_col]
            else:
                vec = [0.0] * DIMS[domain]
            vectors[domain] = vec
            combined_vector.extend(vec)

        core_competencies = row.get('core_competencies_data', {})
        if pd.isna(core_competencies): core_competencies = {}

        interests = row.get('interests_data', {})
        if pd.isna(interests): interests = {}

        # Insert into oasis_occupations
        cur.execute("""
            INSERT INTO oasis_occupations (oasis_code, title, core_competencies, interests)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (oasis_code) DO UPDATE SET 
                title = EXCLUDED.title,
                core_competencies = EXCLUDED.core_competencies,
                interests = EXCLUDED.interests
        """, (code, title, json.dumps(core_competencies), json.dumps(interests)))

        # Insert into oasis_occupation_vectors
        cur.execute("""
            INSERT INTO oasis_occupation_vectors (
                oasis_code, 
                abilities_vector, skills_vector, work_context_vector,
                knowledge_vector, personal_attributes_vector, work_activities_vector,
                combined_vector
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (oasis_code) DO UPDATE SET
                abilities_vector = EXCLUDED.abilities_vector,
                skills_vector = EXCLUDED.skills_vector,
                work_context_vector = EXCLUDED.work_context_vector,
                knowledge_vector = EXCLUDED.knowledge_vector,
                personal_attributes_vector = EXCLUDED.personal_attributes_vector,
                work_activities_vector = EXCLUDED.work_activities_vector,
                combined_vector = EXCLUDED.combined_vector
        """, (
            code,
            json.dumps(vectors['abilities']),
            json.dumps(vectors['skills']),
            json.dumps(vectors['work_context']),
            json.dumps(vectors['knowledge']),
            json.dumps(vectors['personal_attributes']),
            json.dumps(vectors['work_activities']),
            json.dumps(combined_vector)
        ))
        
        inserted_count += 1
        if inserted_count % 100 == 0:
            print(f"Inserted {inserted_count} records...")

    conn.commit()
    cur.close()
    conn.close()
    print(f"Successfully processed and inserted {inserted_count} occupations.")

if __name__ == "__main__":
    main()
