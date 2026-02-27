-- ============================================================
-- University ERP — PostgreSQL Schema
-- ============================================================
-- Run: psql -U erp_admin -d university_erp -f init.sql
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ┌──────────────────────────────────────────────────────────┐
-- │  USERS (authentication)                                   │
-- └──────────────────────────────────────────────────────────┘
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username        VARCHAR(100) NOT NULL UNIQUE,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    role            VARCHAR(20) NOT NULL DEFAULT 'student'
                        CHECK (role IN ('admin', 'student', 'faculty')),
    full_name       VARCHAR(200) NOT NULL DEFAULT '',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email    ON users(email);
CREATE INDEX idx_users_role     ON users(role);

-- ┌──────────────────────────────────────────────────────────┐
-- │  DEPARTMENTS                                             │
-- └──────────────────────────────────────────────────────────┘
CREATE TABLE IF NOT EXISTS departments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(200) NOT NULL,
    code            VARCHAR(20)  NOT NULL UNIQUE,
    head_faculty_id UUID,
    budget          NUMERIC(15, 2) DEFAULT 0.00,
    description     TEXT DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_departments_code ON departments(code);

-- ┌──────────────────────────────────────────────────────────┐
-- │  FACULTY                                                 │
-- └──────────────────────────────────────────────────────────┘
CREATE TABLE IF NOT EXISTS faculty (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    department_id   UUID NOT NULL REFERENCES departments(id),
    rank            VARCHAR(50)  NOT NULL CHECK (rank IN (
                        'lecturer', 'assistant_professor',
                        'associate_professor', 'professor',
                        'distinguished_professor'
                    )),
    hire_date       DATE NOT NULL DEFAULT CURRENT_DATE,
    specialisation  VARCHAR(200) DEFAULT '',
    course_ids      UUID[] DEFAULT '{}',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_faculty_department ON faculty(department_id);
CREATE INDEX idx_faculty_email      ON faculty(email);

-- Back-reference: department head
ALTER TABLE departments
    ADD CONSTRAINT fk_dept_head
    FOREIGN KEY (head_faculty_id) REFERENCES faculty(id)
    ON DELETE SET NULL;

-- ┌──────────────────────────────────────────────────────────┐
-- │  STUDENTS                                                │
-- └──────────────────────────────────────────────────────────┘
CREATE TABLE IF NOT EXISTS students (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name           VARCHAR(100) NOT NULL,
    last_name            VARCHAR(100) NOT NULL,
    email                VARCHAR(255) NOT NULL UNIQUE,
    date_of_birth        DATE NOT NULL,
    enrollment_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    department_id        UUID NOT NULL REFERENCES departments(id),
    status               VARCHAR(20) NOT NULL DEFAULT 'active'
                             CHECK (status IN (
                                 'active', 'inactive', 'graduated',
                                 'suspended', 'on_leave'
                             )),
    gpa                  FLOAT8 DEFAULT 0.00,
    enrolled_course_ids  UUID[] DEFAULT '{}',
    completed_course_ids UUID[] DEFAULT '{}',
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_students_department ON students(department_id);
CREATE INDEX idx_students_email      ON students(email);
CREATE INDEX idx_students_status     ON students(status);
CREATE INDEX idx_students_gpa        ON students(gpa);

-- ┌──────────────────────────────────────────────────────────┐
-- │  COURSES                                                 │
-- └──────────────────────────────────────────────────────────┘
CREATE TABLE IF NOT EXISTS courses (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code                 VARCHAR(20) NOT NULL UNIQUE,
    title                VARCHAR(200) NOT NULL,
    department_id        UUID NOT NULL REFERENCES departments(id),
    credits              INT NOT NULL CHECK (credits BETWEEN 1 AND 12),
    capacity             INT NOT NULL CHECK (capacity >= 1),
    description          TEXT DEFAULT '',
    instructor_id        UUID REFERENCES faculty(id),
    prerequisite_ids     UUID[] DEFAULT '{}',
    enrolled_student_ids UUID[] DEFAULT '{}',
    semester             VARCHAR(20) DEFAULT '',
    is_active            BOOLEAN DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_courses_department ON courses(department_id);
CREATE INDEX idx_courses_code       ON courses(code);
CREATE INDEX idx_courses_semester   ON courses(semester);

-- ┌──────────────────────────────────────────────────────────┐
-- │  ENROLLMENTS  (junction table)                           │
-- └──────────────────────────────────────────────────────────┘
CREATE TABLE IF NOT EXISTS enrollments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id      UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id       UUID NOT NULL REFERENCES courses(id)  ON DELETE CASCADE,
    semester        VARCHAR(20) NOT NULL,
    enrollment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status          VARCHAR(20) NOT NULL DEFAULT 'registered'
                        CHECK (status IN (
                            'registered', 'in_progress',
                            'completed', 'withdrawn', 'failed'
                        )),
    grade           VARCHAR(5),
    grade_point     NUMERIC(3, 2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (student_id, course_id, semester)
);

CREATE INDEX idx_enrollments_student  ON enrollments(student_id);
CREATE INDEX idx_enrollments_course   ON enrollments(course_id);
CREATE INDEX idx_enrollments_semester ON enrollments(semester);

-- ┌──────────────────────────────────────────────────────────┐
-- │  ETL RUN LOG                                             │
-- └──────────────────────────────────────────────────────────┘
CREATE TABLE IF NOT EXISTS etl_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_name   VARCHAR(100) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'running'
                        CHECK (status IN ('running', 'completed', 'failed')),
    extracted       INT DEFAULT 0,
    transformed     INT DEFAULT 0,
    validated       INT DEFAULT 0,
    loaded          INT DEFAULT 0,
    errors          JSONB DEFAULT '[]',
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ┌──────────────────────────────────────────────────────────┐
-- │  UPDATED_AT TRIGGER                                      │
-- └──────────────────────────────────────────────────────────┘
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at_students
    BEFORE UPDATE ON students
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_courses
    BEFORE UPDATE ON courses
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_faculty
    BEFORE UPDATE ON faculty
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_departments
    BEFORE UPDATE ON departments
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_enrollments
    BEFORE UPDATE ON enrollments
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
