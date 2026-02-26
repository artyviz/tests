use axum::{
    extract::{Path, Query, State},
    routing::{get, post, delete},
    Json, Router,
};
use serde::Deserialize;
use serde_json::json;
use uuid::Uuid;

use crate::db::Db;
use crate::errors::{AppError, Result};
use crate::models::*;

pub fn routes() -> Router<Db> {
    Router::new()
        .route("/", get(list))
        .route("/student/:student_id", get(student_enrollments))
        .route("/enroll", post(enroll))
        .route("/:id/drop", delete(drop_enrollment))
}

async fn list(State(db): State<Db>, Query(p): Query<ListParams>) -> Result<Json<serde_json::Value>> {
    let limit = p.limit.unwrap_or(50);

    let enrollments = sqlx::query_as::<_, Enrollment>(
        "SELECT * FROM enrollments ORDER BY created_at DESC LIMIT $1"
    )
    .bind(limit)
    .fetch_all(&db)
    .await?;

    Ok(Json(json!({ "data": enrollments })))
}

async fn student_enrollments(
    State(db): State<Db>,
    Path(student_id): Path<Uuid>,
) -> Result<Json<serde_json::Value>> {
    // Join enrollments with course info
    let rows = sqlx::query_as::<_, EnrollmentDetail>(
        r#"SELECT e.id, e.student_id, e.course_id, e.semester, e.status, e.grade,
                  c.code AS course_code, c.title AS course_title, c.credits
           FROM enrollments e
           JOIN courses c ON c.id = e.course_id
           WHERE e.student_id = $1
           ORDER BY e.semester DESC, c.code"#
    )
    .bind(student_id)
    .fetch_all(&db)
    .await?;

    Ok(Json(json!({ "data": rows })))
}

#[derive(Debug, Deserialize)]
pub struct EnrollInput {
    pub student_id: Uuid,
    pub course_id: Uuid,
    pub semester: String,
}

async fn enroll(State(db): State<Db>, Json(input): Json<EnrollInput>) -> Result<Json<Enrollment>> {
    // Check student exists
    let _s = sqlx::query("SELECT id FROM students WHERE id = $1")
        .bind(input.student_id)
        .fetch_optional(&db)
        .await?
        .ok_or_else(|| AppError::NotFound("Student not found".into()))?;

    // Check course exists + capacity
    let course = sqlx::query_as::<_, Course>("SELECT * FROM courses WHERE id = $1")
        .bind(input.course_id)
        .fetch_optional(&db)
        .await?
        .ok_or_else(|| AppError::NotFound("Course not found".into()))?;

    let count: (i64,) = sqlx::query_as(
        "SELECT COUNT(*) FROM enrollments WHERE course_id = $1 AND status IN ('registered','in_progress')"
    )
    .bind(input.course_id)
    .fetch_one(&db)
    .await?;

    if count.0 >= course.capacity as i64 {
        return Err(AppError::Validation("Course is full".into()));
    }

    // Check duplicate
    let exists = sqlx::query(
        "SELECT id FROM enrollments WHERE student_id=$1 AND course_id=$2 AND semester=$3"
    )
    .bind(input.student_id)
    .bind(input.course_id)
    .bind(&input.semester)
    .fetch_optional(&db)
    .await?;

    if exists.is_some() {
        return Err(AppError::Duplicate("Already enrolled in this course for this semester".into()));
    }

    let enrollment = sqlx::query_as::<_, Enrollment>(
        r#"INSERT INTO enrollments (id, student_id, course_id, semester, status)
           VALUES ($1, $2, $3, $4, 'registered')
           RETURNING *"#
    )
    .bind(Uuid::new_v4())
    .bind(input.student_id)
    .bind(input.course_id)
    .bind(&input.semester)
    .fetch_one(&db)
    .await?;

    Ok(Json(enrollment))
}

async fn drop_enrollment(State(db): State<Db>, Path(id): Path<Uuid>) -> Result<Json<serde_json::Value>> {
    let r = sqlx::query("DELETE FROM enrollments WHERE id = $1")
        .bind(id)
        .execute(&db)
        .await?;
    if r.rows_affected() == 0 {
        return Err(AppError::NotFound("Enrollment not found".into()));
    }
    Ok(Json(json!({ "dropped": true })))
}
