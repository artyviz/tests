use sqlx::PgPool;

/// Type alias used as Axum shared state.
pub type Db = PgPool;
