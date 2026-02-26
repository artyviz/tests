use axum::{extract::State, routing::get, Json, Router};
use serde_json::json;

use crate::db::Db;
use crate::errors::Result;

pub fn routes() -> Router<Db> {
    Router::new().route("/health", get(health))
}

async fn health(State(db): State<Db>) -> Result<Json<serde_json::Value>> {
    let db_ok = sqlx::query("SELECT 1").execute(&db).await.is_ok();

    Ok(Json(json!({
        "status": if db_ok { "healthy" } else { "degraded" },
        "service": "university-erp-api",
        "database": db_ok,
    })))
}
