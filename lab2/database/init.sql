--хранение информации о работах (исп. File Storing Service)
CREATE TABLE IF NOT EXISTS works (
    id VARCHAR PRIMARY KEY, --уникальный айди записи
    student_name VARCHAR NOT NULL,
    assignment_id VARCHAR NOT NULL,
    description TEXT,
    filename VARCHAR NOT NULL,
    filepath VARCHAR NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_size VARCHAR,
    mime_type VARCHAR
);

--хранение отчетов анализа (исп. File Analysis Service)
CREATE TABLE IF NOT EXISTS analysis_reports (
    id VARCHAR PRIMARY KEY,
    work_id VARCHAR NOT NULL,
    assignment_id VARCHAR NOT NULL,
    student_name VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    plagiarism_score FLOAT,
    is_plagiarism BOOLEAN,
    report_data TEXT,
    analyzed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    wordcloud_url VARCHAR
);

--ускорение поиска
CREATE INDEX IF NOT EXISTS idx_works_assignment_id ON works(assignment_id);
CREATE INDEX IF NOT EXISTS idx_works_student_name ON works(student_name);
CREATE INDEX IF NOT EXISTS idx_reports_work_id ON analysis_reports(work_id);
CREATE INDEX IF NOT EXISTS idx_reports_assignment_id ON analysis_reports(assignment_id);
CREATE INDEX IF NOT EXISTS idx_reports_status ON analysis_reports(status);