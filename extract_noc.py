import csv
import re
import os

# Configuration
STRUCTURE_FILE = "noc_structure.csv"
ELEMENTS_FILE = "noc_elements.csv"
SQL_FILE = "noc_data.sql"

# Sample data extracted via browser (used if files are missing)
SAMPLE_ELEMENTS = """Level,Code - NOC 2021 V1.0,Class title,Element Type Label English,Element Description English
5,00011,Senior government managers and officials,Additional information,There is mobility among senior management occupations. 
5,10010,Financial managers,Additional information,"Progression to senior management positions, such as vice-president of finance, is possible with experience. "
5,10011,Human resources managers,Additional information,Progression to senior management positions is possible with experience. 
5,10019,Other administrative services managers,Additional information,"Duties of court registrars can include those of other court services occupations such as court administrator and ""Court Clerks"" (14103) depending on the location and size of the courthouse. "
5,10021,"Banking, credit and other investment managers",Additional information,Progression to senior management positions in this field is possible with experience. 
5,10022,"Advertising, marketing and public relations managers",Additional information,Progression to senior management positions is possible with experience. 
5,21232,"Software developers and programmers",Additional information,"Progression to senior management positions is possible with experience (NOC 00012)."
"""

def extract_data():
    occupations = {}
    progression_links = []

    # Check if files exist, otherwise use sample
    if os.path.exists(STRUCTURE_FILE):
        print(f"Parsing {STRUCTURE_FILE}...")
        with open(STRUCTURE_FILE, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get('Code - NOC 2021 V1.0')
                title = row.get('Class title') or row.get('Title - NOC 2021 V1.0 - English')
                level = row.get('Level')
                if code and title:
                    occupations[code] = {'title': title, 'level': level}
    else:
        print("Structure file not found, using minimal mock data for occupations.")
        # Minimal mock data based on elements sample
        occupations = {
            '00011': {'title': 'Senior government managers and officials', 'level': '5'},
            '00012': {'title': 'Senior managers - financial, communications and other business services', 'level': '5'},
            '10010': {'title': 'Financial managers', 'level': '5'},
            '10011': {'title': 'Human resources managers', 'level': '5'},
            '10019': {'title': 'Other administrative services managers', 'level': '5'},
            '10021': {'title': 'Banking, credit and other investment managers', 'level': '5'},
            '10022': {'title': 'Advertising, marketing and public relations managers', 'level': '5'},
            '14103': {'title': 'Court Clerks', 'level': '4'},
            '21232': {'title': 'Software developers and programmers', 'level': '5'},
        }

    # Parse Elements
    rows = []
    if os.path.exists(ELEMENTS_FILE):
        print(f"Parsing {ELEMENTS_FILE}...")
        with open(ELEMENTS_FILE, mode='r', encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
    else:
        print("Elements file not found, using extracted sample data.")
        f = SAMPLE_ELEMENTS.strip().splitlines()
        reader = csv.DictReader(f)
        rows = list(reader)

    print("Extracting progression paths...")
    for row in rows:
        element_type = row.get('Element Type Label English')
        if element_type == "Additional information":
            source_code = row.get('Code - NOC 2021 V1.0')
            description = row.get('Element Description English', '')
            
            if not source_code or not description:
                continue
            
            # Regex for 5-digit NOC codes
            matches = re.findall(r'\b\d{5}\b', description)
            
            for target_code in matches:
                if target_code != source_code:
                    progression_links.append({
                        'source': source_code,
                        'target': target_code,
                        'description': description.replace("'", "''")
                    })

    # Generate SQL
    print(f"Generating {SQL_FILE}...")
    with open(SQL_FILE, 'w', encoding='utf-8') as f:
        f.write("-- NOC 2021 Data Export\n")
        f.write("BEGIN;\n\n")
        
        f.write("CREATE TABLE IF NOT EXISTS occupations (\n")
        f.write("    noc_code VARCHAR(10) PRIMARY KEY,\n")
        f.write("    title TEXT NOT NULL,\n")
        f.write("    level INTEGER\n")
        f.write(");\n\n")
        
        f.write("CREATE TABLE IF NOT EXISTS progression_paths (\n")
        f.write("    id SERIAL PRIMARY KEY,\n")
        f.write("    source_noc VARCHAR(10) REFERENCES occupations(noc_code),\n")
        f.write("    target_noc VARCHAR(10) REFERENCES occupations(noc_code),\n")
        f.write("    description TEXT\n")
        f.write(");\n\n")

        f.write("-- Inserting Occupations\n")
        for code, data in occupations.items():
            title_esc = data['title'].replace("'", "''")
            level = data['level'] if data['level'] else 'NULL'
            f.write(f"INSERT INTO occupations (noc_code, title, level) VALUES ('{code}', '{title_esc}', {level}) ON CONFLICT (noc_code) DO UPDATE SET title = EXCLUDED.title;\n")
        
        f.write("\n-- Inserting Progression Paths\n")
        for link in progression_links:
            f.write(f"INSERT INTO progression_paths (source_noc, target_noc, description) VALUES ('{link['source']}', '{link['target']}', '{link['description']}');\n")
            
        f.write("\nCOMMIT;\n")

    print(f"Done! Created {SQL_FILE}")

if __name__ == "__main__":
    extract_data()
