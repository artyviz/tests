use axum::{
    extract::{Path, Query, State}, // Cache buster for sqlx schema sync
    routing::{get, post, put, delete},
    Json, Router,
};
use serde_json::json;
use uuid::Uuid;

use crate::db::Db;
use crate::errors::{AppError, Result};
use crate::models::*;

const COLS: &str = "id, first_name, last_name, email, date_of_birth, department_id, gpa, status, created_at, updated_at";
const COURSE_COLS: &str = "id, code, title, department_id, credits, capacity, is_active, created_at, updated_at";

pub fn routes() -> Router<Db> {
    Router::new()
        .route("/", get(list).post(create))
        .route("/:id", get(show).put(update).delete(remove))
        .route("/:id/enroll", post(enroll))
        .route("/:id/grade", post(assign_grade))
        .route("/search/:query", get(search))
}

/// GET /api/students
async fn list(State(db): State<Db>, Query(p): Query<ListParams>) -> Result<Json<serde_json::Value>> {
    let limit = p.limit.unwrap_or(50);
    let offset = p.offset.unwrap_or(0);

    let q = format!("SELECT {} FROM students ORDER BY created_at DESC LIMIT $1 OFFSET $2", COLS);
    let students = sqlx::query_as::<_, Student>(&q)
    .bind(limit)
    .bind(offset)
    .fetch_all(&db)
    .await?;

    let total: (i64,) = sqlx::query_as("SELECT COUNT(*) FROM students")
        .fetch_one(&db)
        .await?;

    Ok(Json(json!({
        "data": students,
        "total": total.0,
        "limit": limit,
        "offset": offset
    })))
}

/// GET /api/students/:id
async fn show(State(db): State<Db>, Path(id): Path<Uuid>) -> Result<Json<Student>> {
    let q = format!("SELECT {} FROM students WHERE id = $1", COLS);
    let student = sqlx::query_as::<_, Student>(&q)
        .bind(id)
        .fetch_optional(&db)
        .await?
        .ok_or_else(|| AppError::NotFound(format!("Student {} not found", id)))?;
    Ok(Json(student))
}

/// POST /api/students
async fn create(State(db): State<Db>, Json(input): Json<CreateStudent>) -> Result<Json<Student>> {
    // Check duplicate email
    let exists: Option<(Uuid,)> =
        sqlx::query_as("SELECT id FROM students WHERE email = $1")
            .bind(&input.email)
            .fetch_optional(&db)
            .await?;
    if exists.is_some() {
        return Err(AppError::Duplicate(format!(
            "Student with email {} already exists",
            input.email
        )));
    }

    let id = Uuid::new_v4();
    let ret = format!("RETURNING {}", COLS);
    let q = format!(
        "INSERT INTO students (id, first_name, last_name, email, date_of_birth, department_id, gpa, status) VALUES ($1, $2, $3, $4, $5, $6, 0.0, 'active') {}",
        ret
    );
    let student = sqlx::query_as::<_, Student>(&q)
    .bind(id)
    .bind(&input.first_name)
    .bind(&input.last_name)
    .bind(&input.email)
    .bind(input.date_of_birth)
    .bind(input.department_id)
    .fetch_one(&db)
    .await?;

    Ok(Json(student))
}

/// PUT /api/students/:id
async fn update(
    State(db): State<Db>,
    Path(id): Path<Uuid>,
    Json(input): Json<UpdateStudent>,
) -> Result<Json<Student>> {
    let ret = format!("RETURNING {}", COLS);
    let q = format!(
        "UPDATE students SET first_name = COALESCE($2, first_name), last_name = COALESCE($3, last_name), email = COALESCE($4, email), status = COALESCE($5, status), updated_at = NOW() WHERE id = $1 {}",
        ret
    );
    let student = sqlx::query_as::<_, Student>(&q)
    .bind(id)
    .bind(&input.first_name)
    .bind(&input.last_name)
    .bind(&input.email)
    .bind(&input.status)
    .fetch_optional(&db)
    .await?
    .ok_or_else(|| AppError::NotFound(format!("Student {} not found", id)))?;

    Ok(Json(student))
}

/// DELETE /api/students/:id
async fn remove(State(db): State<Db>, Path(id): Path<Uuid>) -> Result<Json<serde_json::Value>> {
    let result = sqlx::query("DELETE FROM students WHERE id = $1")
        .bind(id)
        .execute(&db)
        .await?;

    if result.rows_affected() == 0 {
        return Err(AppError::NotFound(format!("Student {} not found", id)));
    }
    Ok(Json(json!({ "deleted": true, "id": id })))
}

/// POST /api/students/:id/enroll
async fn enroll(
    State(db): State<Db>,
    Path(id): Path<Uuid>,
    Json(input): Json<EnrollRequest>,
) -> Result<Json<Enrollment>> {
    // Verify student exists
    let q = format!("SELECT {} FROM students WHERE id = $1", COLS);
    let _student = sqlx::query_as::<_, Student>(&q)
        .bind(id)
        .fetch_optional(&db)
        .await?
        .ok_or_else(|| AppError::NotFound("Student not found".into()))?;

    // Check capacity
    let enrolled_count: (i64,) = sqlx::query_as(
        "SELECT COUNT(*) FROM enrollments WHERE course_id = $1 AND status IN ('registered','in_progress')"
    )
    .bind(input.course_id)
    .fetch_one(&db)
    .await?;

    let cq = format!("SELECT {} FROM courses WHERE id = $1", COURSE_COLS);
    let course = sqlx::query_as::<_, Course>(&cq)
        .bind(input.course_id)
        .fetch_optional(&db)
        .await?
        .ok_or_else(|| AppError::NotFound("Course not found".into()))?;

    if enrolled_count.0 >= course.capacity as i64 {
        return Err(AppError::Validation("Course is at full capacity".into()));
    }

    let enrollment = sqlx::query_as::<_, Enrollment>(
        r#"INSERT INTO enrollments (id, student_id, course_id, semester, status)
           VALUES ($1, $2, $3, $4, 'registered')
           RETURNING id, student_id, course_id, semester, status, grade, created_at, updated_at"#
    )
    .bind(Uuid::new_v4())
    .bind(id)
    .bind(input.course_id)
    .bind(&input.semester)
    .fetch_one(&db)
    .await?;

    Ok(Json(enrollment))
}

/// POST /api/students/:id/grade
async fn assign_grade(
    State(db): State<Db>,
    Path(id): Path<Uuid>,
    Json(input): Json<GradeRequest>,
) -> Result<Json<Enrollment>> {
    let valid_grades = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F"];
    if !valid_grades.contains(&input.grade.as_str()) {
        return Err(AppError::Validation(format!("Invalid grade: {}", input.grade)));
    }

    let status = if input.grade == "F" { "failed" } else { "completed" };

    let enrollment = sqlx::query_as::<_, Enrollment>(
        r#"UPDATE enrollments SET grade = $1, status = $2, updated_at = NOW()
           WHERE student_id = $3 AND course_id = $4
           RETURNING id, student_id, course_id, semester, status, grade, created_at, updated_at"#
    )
    .bind(&input.grade)
    .bind(status)
    .bind(id)
    .bind(input.course_id)
    .fetch_optional(&db)
    .await?
    .ok_or_else(|| AppError::NotFound("Enrollment not found".into()))?;

    Ok(Json(enrollment))
}

/// GET /api/students/search/:query
async fn search(State(db): State<Db>, Path(q): Path<String>) -> Result<Json<Vec<Student>>> {
    let pattern = format!("%{}%", q);
    let query = format!(
        "SELECT {} FROM students WHERE first_name ILIKE $1 OR last_name ILIKE $1 OR email ILIKE $1 LIMIT 50",
        COLS
    );
    let students = sqlx::query_as::<_, Student>(&query)
    .bind(&pattern)
    .fetch_all(&db)
    .await?;

    Ok(Json(students))
}
