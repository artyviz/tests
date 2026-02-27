use axum::{
    extract::{Path, Query, State},
    routing::get,
    Json, Router,
};
use serde_json::json;
use uuid::Uuid;

use crate::db::Db;
use crate::errors::{AppError, Result};
use crate::models::*;

const COLS: &str = "id, first_name, last_name, email, department_id, rank, is_active, created_at, updated_at";

pub fn routes() -> Router<Db> {
    Router::new()
        .route("/", get(list))
        .route("/:id", get(show))
}

async fn list(State(db): State<Db>, Query(p): Query<ListParams>) -> Result<Json<serde_json::Value>> {
    let limit = p.limit.unwrap_or(50);
    let offset = p.offset.unwrap_or(0);

    let q = format!("SELECT {} FROM faculty ORDER BY last_name ASC LIMIT $1 OFFSET $2", COLS);
    let faculty = sqlx::query_as::<_, Faculty>(&q)
    .bind(limit)
    .bind(offset)
    .fetch_all(&db)
    .await?;

    let total: (i64,) = sqlx::query_as("SELECT COUNT(*) FROM faculty")
        .fetch_one(&db)
        .await?;

    Ok(Json(json!({ "data": faculty, "total": total.0 })))
}

async fn show(State(db): State<Db>, Path(id): Path<Uuid>) -> Result<Json<Faculty>> {
    let q = format!("SELECT {} FROM faculty WHERE id = $1", COLS);
    let f = sqlx::query_as::<_, Faculty>(&q)
        .bind(id)
        .fetch_optional(&db)
        .await?
        .ok_or_else(|| AppError::NotFound(format!("Faculty {} not found", id)))?;
    Ok(Json(f))
}
