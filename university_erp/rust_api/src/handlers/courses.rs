use axum::{
    extract::{Path, Query, State},
    routing::{get, delete},
    Json, Router,
};
use serde_json::json;
use uuid::Uuid;

use crate::db::Db;
use crate::errors::{AppError, Result};
use crate::models::*;

pub fn routes() -> Router<Db> {
    Router::new()
        .route("/", get(list).post(create))
        .route("/:id", get(show).put(update).delete(remove))
}

async fn list(State(db): State<Db>, Query(p): Query<ListParams>) -> Result<Json<serde_json::Value>> {
    let limit = p.limit.unwrap_or(50);
    let offset = p.offset.unwrap_or(0);

    let courses = sqlx::query_as::<_, Course>(
        "SELECT * FROM courses ORDER BY code ASC LIMIT $1 OFFSET $2"
    )
    .bind(limit)
    .bind(offset)
    .fetch_all(&db)
    .await?;

    let total: (i64,) = sqlx::query_as("SELECT COUNT(*) FROM courses")
        .fetch_one(&db)
        .await?;

    Ok(Json(json!({ "data": courses, "total": total.0 })))
}

async fn show(State(db): State<Db>, Path(id): Path<Uuid>) -> Result<Json<Course>> {
    let course = sqlx::query_as::<_, Course>("SELECT * FROM courses WHERE id = $1")
        .bind(id)
        .fetch_optional(&db)
        .await?
        .ok_or_else(|| AppError::NotFound(format!("Course {} not found", id)))?;
    Ok(Json(course))
}

async fn create(State(db): State<Db>, Json(input): Json<CreateCourse>) -> Result<Json<Course>> {
    if input.credits < 1 || input.credits > 6 {
        return Err(AppError::Validation("Credits must be 1–6".into()));
    }
    if input.capacity < 1 {
        return Err(AppError::Validation("Capacity must be positive".into()));
    }

    let course = sqlx::query_as::<_, Course>(
        r#"INSERT INTO courses (id, code, title, department_id, credits, capacity, status)
           VALUES ($1, $2, $3, $4, $5, $6, 'active')
           RETURNING *"#
    )
    .bind(Uuid::new_v4())
    .bind(&input.code)
    .bind(&input.title)
    .bind(input.department_id)
    .bind(input.credits)
    .bind(input.capacity)
    .fetch_one(&db)
    .await?;

    Ok(Json(course))
}

async fn update(
    State(db): State<Db>,
    Path(id): Path<Uuid>,
    Json(input): Json<CreateCourse>,
) -> Result<Json<Course>> {
    let course = sqlx::query_as::<_, Course>(
        r#"UPDATE courses SET code=$2, title=$3, department_id=$4, credits=$5, capacity=$6, updated_at=NOW()
           WHERE id=$1 RETURNING *"#
    )
    .bind(id)
    .bind(&input.code)
    .bind(&input.title)
    .bind(input.department_id)
    .bind(input.credits)
    .bind(input.capacity)
    .fetch_optional(&db)
    .await?
    .ok_or_else(|| AppError::NotFound(format!("Course {} not found", id)))?;

    Ok(Json(course))
}

async fn remove(State(db): State<Db>, Path(id): Path<Uuid>) -> Result<Json<serde_json::Value>> {
    let r = sqlx::query("DELETE FROM courses WHERE id = $1")
        .bind(id)
        .execute(&db)
        .await?;
    if r.rows_affected() == 0 {
        return Err(AppError::NotFound(format!("Course {} not found", id)));
    }
    Ok(Json(json!({ "deleted": true })))
}
