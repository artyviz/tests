pub mod students;
pub mod courses;
pub mod departments;
pub mod faculty;
pub mod enrollments;
pub mod analytics;
pub mod health;
pub mod simulate;
pub mod ws;

use axum::{routing::{get, post}, Router};
use crate::db::Db;

pub fn routes() -> Router<Db> {
    Router::new()
        .nest("/students", students::routes())
        .nest("/courses", courses::routes())
        .nest("/departments", departments::routes())
        .nest("/faculty", faculty::routes())
        .nest("/enrollments", enrollments::routes())
        .nest("/analytics", analytics::routes())
        .route("/simulate", post(simulate::start_simulation))
        .route("/ws", get(ws::ws_handler))
        .merge(health::routes())
}
