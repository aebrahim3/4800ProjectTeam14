import os
import requests
import zipfile
import csv
import io
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

# Database connection details
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "careerMatchingEngine")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

# If running outside docker, 'db' host won't work, fallback to localhost
if DB_HOST == "db":
    DB_HOST = "localhost"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# O*NET 30.1 URL
ONET_ZIP_URL = "https://www.onetcenter.org/dl_files/database/db_30_1_text.zip"

def download_onet_data():
    print(f"Downloading O*NET data from {ONET_ZIP_URL}...")
    response = requests.get(ONET_ZIP_URL)
    response.raise_for_status()
    return zipfile.ZipFile(io.BytesIO(response.content))

def process_onet_data(zf):
    print("Processing O*NET files...")
    # Files in the zip are usually in a subdirectory like db_30_1_text/
    file_list = zf.namelist()
    base_path = [name for name in file_list if name.endswith('/') and '/' not in name[:-1]][0]
    
    occupations_file = f"{base_path}Occupation Data.txt"
    knowledge_file = f"{base_path}Knowledge.txt"
    activities_file = f"{base_path}Work Activities.txt"
    content_model_file = f"{base_path}Content Model Reference.txt"

    # 1. Load Elements
    knowledge_elements = []
    activity_elements = []
    
    with zf.open(content_model_file) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'), delimiter='\t')
        for row in reader:
            eid = row['Element ID']
            name = row['Element Name']
            desc = row['Description']
            # Knowledge elements are 2.C.*
            if eid.startswith('2.C'):
                knowledge_elements.append((eid, name, desc))
            # Work Activity elements are 4.A.*
            elif eid.startswith('4.A'):
                activity_elements.append((eid, name, desc))

    # Sort elements to ensure consistent vector mapping
    knowledge_elements.sort(key=lambda x: x[0])
    activity_elements.sort(key=lambda x: x[0])
    
    k_id_to_idx = {e[0]: i for i, e in enumerate(knowledge_elements)}
    a_id_to_idx = {e[0]: i for i, e in enumerate(activity_elements)}

    print(f"Found {len(knowledge_elements)} Knowledge elements and {len(activity_elements)} Work Activity elements.")

    # 2. Load Occupations
    occupations = []
    with zf.open(occupations_file) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'), delimiter='\t')
        for row in reader:
            occupations.append((row['O*NET-SOC Code'], row['Title'], row['Description']))

    # 3. Load Knowledge Scores (Level - LV)
    k_scores = {} # onetsoc_code -> [0] * 33
    with zf.open(knowledge_file) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'), delimiter='\t')
        for row in reader:
            if row['Scale ID'] == 'LV':
                code = row['O*NET-SOC Code']
                eid = row['Element ID']
                if eid in k_id_to_idx:
                    if code not in k_scores:
                        k_scores[code] = [0.0] * len(knowledge_elements)
                    k_scores[code][k_id_to_idx[eid]] = float(row['Data Value'])

    # 4. Load Activity Scores (Level - LV)
    a_scores = {} # onetsoc_code -> [0] * 41
    with zf.open(activities_file) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'), delimiter='\t')
        for row in reader:
            if row['Scale ID'] == 'LV':
                code = row['O*NET-SOC Code']
                eid = row['Element ID']
                if eid in a_id_to_idx:
                    if code not in a_scores:
                        a_scores[code] = [0.0] * len(activity_elements)
                    a_scores[code][a_id_to_idx[eid]] = float(row['Data Value'])

    return {
        'occupations': occupations,
        'knowledge_elements': knowledge_elements,
        'activity_elements': activity_elements,
        'k_scores': k_scores,
        'a_scores': a_scores
    }

def import_to_db(data):
    print(f"Connecting to database at {DB_HOST}...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print("Importing elements...")
    execute_values(cur, """
        INSERT INTO onet_knowledge_elements (element_id, element_name, description) 
        VALUES %s 
        ON CONFLICT (element_id) DO UPDATE SET 
            element_name = EXCLUDED.element_name, 
            description = EXCLUDED.description
    """, data['knowledge_elements'])
    
    execute_values(cur, """
        INSERT INTO onet_work_activities_elements (element_id, element_name, description) 
        VALUES %s 
        ON CONFLICT (element_id) DO UPDATE SET 
            element_name = EXCLUDED.element_name, 
            description = EXCLUDED.description
    """, data['activity_elements'])
    
    print("Importing occupations...")
    execute_values(cur, """
        INSERT INTO onet_occupations (onetsoc_code, title, description) 
        VALUES %s 
        ON CONFLICT (onetsoc_code) DO UPDATE SET 
            title = EXCLUDED.title, 
            description = EXCLUDED.description
    """, data['occupations'])
    
    print("Importing vectors...")
    vector_data = []
    k_len = len(data['knowledge_elements'])
    a_len = len(data['activity_elements'])
    
    for code, title, desc in data['occupations']:
        k_vec = data['k_scores'].get(code, [0.0] * k_len)
        a_vec = data['a_scores'].get(code, [0.0] * a_len)
        combined_vec = k_vec + a_vec
        
        # Convert to pgvector string format: '[val1, val2, ...]'
        vector_str = "[" + ",".join(map(str, combined_vec)) + "]"
        vector_data.append((code, vector_str))
        
    execute_values(cur, """
        INSERT INTO onet_occupation_vectors (onetsoc_code, vector) 
        VALUES %s 
        ON CONFLICT (onetsoc_code) DO UPDATE SET 
            vector = EXCLUDED.vector
    """, vector_data)
    
    conn.commit()
    cur.close()
    conn.close()
    print("Import complete!")

if __name__ == "__main__":
    try:
        zf = download_onet_data()
        data = process_onet_data(zf)
        import_to_db(data)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
