use axum::{extract::State, routing::get, Json, Router};
use serde_json::json;

use crate::db::Db;
use crate::errors::Result;
use crate::models::*;

pub fn routes() -> Router<Db> {
    Router::new()
        .route("/dashboard", get(dashboard))
        .route("/departments", get(department_summary))
        .route("/top-students", get(top_students))
}

async fn dashboard(State(db): State<Db>) -> Result<Json<DashboardStats>> {
    let total: (i64,) = sqlx::query_as("SELECT COUNT(*) FROM students")
        .fetch_one(&db).await?;
    let active: (i64,) = sqlx::query_as("SELECT COUNT(*) FROM students WHERE status='active'")
        .fetch_one(&db).await?;
    let courses: (i64,) = sqlx::query_as("SELECT COUNT(*) FROM courses")
        .fetch_one(&db).await?;
    let depts: (i64,) = sqlx::query_as("SELECT COUNT(*) FROM departments")
        .fetch_one(&db).await?;

    let avg: (Option<f64>,) = sqlx::query_as("SELECT AVG(gpa)::float8 FROM students")
        .fetch_one(&db).await?;

    Ok(Json(DashboardStats {
        total_students: total.0,
        active_students: active.0,
        total_courses: courses.0,
        total_departments: depts.0,
        average_gpa: avg.0.unwrap_or(0.0),
    }))
}

async fn department_summary(State(db): State<Db>) -> Result<Json<Vec<DepartmentSummary>>> {
    let summaries = sqlx::query_as::<_, DepartmentSummary>(
        r#"SELECT
              d.id AS department_id,
              d.name AS department_name,
              COUNT(s.id) AS student_count,
              COALESCE(AVG(s.gpa), 0)::float8 AS avg_gpa
           FROM departments d
           LEFT JOIN students s ON s.department_id = d.id
           GROUP BY d.id, d.name
           ORDER BY d.name"#
    )
    .fetch_all(&db)
    .await?;

    Ok(Json(summaries))
}

async fn top_students(State(db): State<Db>) -> Result<Json<serde_json::Value>> {
    let students = sqlx::query_as::<_, Student>(
        r#"SELECT * FROM students WHERE gpa >= 3.5 ORDER BY gpa DESC LIMIT 20"#
    )
    .fetch_all(&db)
    .await?;

    Ok(Json(json!({ "data": students })))
}
