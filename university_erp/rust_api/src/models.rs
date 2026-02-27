use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use uuid::Uuid;

// ── Student ─────────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Student {
    pub id: Uuid,
    pub first_name: String,
    pub last_name: String,
    pub email: String,
    pub date_of_birth: chrono::NaiveDate,
    pub department_id: Option<Uuid>,
    pub gpa: f64,
    pub status: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Deserialize)]
pub struct CreateStudent {
    pub first_name: String,
    pub last_name: String,
    pub email: String,
    pub date_of_birth: chrono::NaiveDate,
    pub department_id: Option<Uuid>,
}

#[derive(Debug, Deserialize)]
pub struct UpdateStudent {
    pub first_name: Option<String>,
    pub last_name: Option<String>,
    pub email: Option<String>,
    pub status: Option<String>,
}

// ── Course ──────────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Course {
    pub id: Uuid,
    pub code: String,
    pub title: String,
    pub department_id: Option<Uuid>,
    pub credits: i32,
    pub capacity: i32,
    pub is_active: bool,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Deserialize)]
pub struct CreateCourse {
    pub code: String,
    pub title: String,
    pub department_id: Option<Uuid>,
    pub credits: i32,
    pub capacity: i32,
}

// ── Department ──────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Department {
    pub id: Uuid,
    pub name: String,
    pub code: String,
    pub budget: f64,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

// ── Enrollment ──────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Enrollment {
    pub id: Uuid,
    pub student_id: Uuid,
    pub course_id: Uuid,
    pub semester: String,
    pub status: String,
    pub grade: Option<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Deserialize)]
pub struct EnrollRequest {
    pub course_id: Uuid,
    pub semester: String,
}

#[derive(Debug, Deserialize)]
pub struct GradeRequest {
    pub course_id: Uuid,
    pub grade: String,
}

// ── Faculty ─────────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Faculty {
    pub id: Uuid,
    pub first_name: String,
    pub last_name: String,
    pub email: String,
    pub department_id: Option<Uuid>,
    pub rank: String,
    pub is_active: bool,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

// ── Analytics ───────────────────────────────────────
#[derive(Debug, Serialize)]
pub struct DashboardStats {
    pub total_students: i64,
    pub active_students: i64,
    pub total_courses: i64,
    pub total_departments: i64,
    pub average_gpa: f64,
}

#[derive(Debug, Serialize, FromRow)]
pub struct DepartmentSummary {
    pub department_id: Uuid,
    pub department_name: String,
    pub student_count: i64,
    pub avg_gpa: f64,
}

// ── Query params ────────────────────────────────────
#[derive(Debug, Deserialize)]
pub struct ListParams {
    pub limit: Option<i64>,
    pub offset: Option<i64>,
    pub search: Option<String>,
    pub department: Option<String>,
    pub status: Option<String>,
}

// ── Enrollment with course details (JOIN result) ────
#[derive(Debug, Clone, Serialize, FromRow)]
pub struct EnrollmentDetail {
    pub id: Uuid,
    pub student_id: Uuid,
    pub course_id: Uuid,
    pub semester: String,
    pub status: String,
    pub grade: Option<String>,
    pub course_code: String,
    pub course_title: String,
    pub credits: i32,
}

