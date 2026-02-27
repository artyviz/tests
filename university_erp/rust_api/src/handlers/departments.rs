use axum::{extract::State, routing::get, Json, Router};

use crate::db::Db;
use crate::errors::Result;
use crate::models::Department;

pub fn routes() -> Router<Db> {
    Router::new().route("/", get(list))
}

async fn list(State(db): State<Db>) -> Result<Json<Vec<Department>>> {
    let depts = sqlx::query_as::<_, Department>(
        "SELECT id, name, code, budget::float8, created_at, updated_at FROM departments ORDER BY name ASC"
    )
    .fetch_all(&db)
    .await?;

    Ok(Json(depts))
}
