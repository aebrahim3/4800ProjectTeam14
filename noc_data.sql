-- NOC 2021 Data Export
BEGIN;

CREATE TABLE IF NOT EXISTS occupations (
    noc_code VARCHAR(10) PRIMARY KEY,
    title TEXT NOT NULL,
    level INTEGER
);

CREATE TABLE IF NOT EXISTS progression_paths (
    id SERIAL PRIMARY KEY,
    source_noc VARCHAR(10) REFERENCES occupations(noc_code),
    target_noc VARCHAR(10) REFERENCES occupations(noc_code),
    description TEXT
);

-- Inserting Occupations
INSERT INTO occupations (noc_code, title, level) VALUES ('00011', 'Senior government managers and officials', 5) ON CONFLICT (noc_code) DO UPDATE SET title = EXCLUDED.title;
INSERT INTO occupations (noc_code, title, level) VALUES ('00012', 'Senior managers - financial, communications and other business services', 5) ON CONFLICT (noc_code) DO UPDATE SET title = EXCLUDED.title;
INSERT INTO occupations (noc_code, title, level) VALUES ('10010', 'Financial managers', 5) ON CONFLICT (noc_code) DO UPDATE SET title = EXCLUDED.title;
INSERT INTO occupations (noc_code, title, level) VALUES ('10011', 'Human resources managers', 5) ON CONFLICT (noc_code) DO UPDATE SET title = EXCLUDED.title;
INSERT INTO occupations (noc_code, title, level) VALUES ('10019', 'Other administrative services managers', 5) ON CONFLICT (noc_code) DO UPDATE SET title = EXCLUDED.title;
INSERT INTO occupations (noc_code, title, level) VALUES ('10021', 'Banking, credit and other investment managers', 5) ON CONFLICT (noc_code) DO UPDATE SET title = EXCLUDED.title;
INSERT INTO occupations (noc_code, title, level) VALUES ('10022', 'Advertising, marketing and public relations managers', 5) ON CONFLICT (noc_code) DO UPDATE SET title = EXCLUDED.title;
INSERT INTO occupations (noc_code, title, level) VALUES ('14103', 'Court Clerks', 4) ON CONFLICT (noc_code) DO UPDATE SET title = EXCLUDED.title;
INSERT INTO occupations (noc_code, title, level) VALUES ('21232', 'Software developers and programmers', 5) ON CONFLICT (noc_code) DO UPDATE SET title = EXCLUDED.title;

-- Inserting Progression Paths
INSERT INTO progression_paths (source_noc, target_noc, description) VALUES ('10019', '14103', 'Duties of court registrars can include those of other court services occupations such as court administrator and "Court Clerks" (14103) depending on the location and size of the courthouse. ');
INSERT INTO progression_paths (source_noc, target_noc, description) VALUES ('21232', '00012', 'Progression to senior management positions is possible with experience (NOC 00012).');

COMMIT;
