use std::net::SocketAddr;

use axum::{routing::{get, post}, Router};
use sqlx::postgres::PgPoolOptions;
use tower_http::cors::{Any, CorsLayer};
use tower_http::trace::TraceLayer;
use tracing_subscriber::EnvFilter;
use tokio::sync::broadcast;
use lapin::{options::*, types::FieldTable, Connection, ConnectionProperties};
use futures_util::stream::StreamExt;

pub mod auth;
mod config;
mod db;
mod errors;
mod handlers;
mod models;

#[tokio::main]
async fn main() {
    dotenvy::dotenv().ok();

    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    let cfg = config::Config::from_env();

    let pool = PgPoolOptions::new()
        .max_connections(20)
        .connect(&cfg.database_url)
        .await
        .expect("Failed to connect to Postgres");

    tracing::info!("Connected to database");

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let auth_routes = Router::new()
        .route("/register", post(auth::register))
        .route("/login", post(auth::login))
        .route("/me", get(auth::me));

    let amqp_conn = Connection::connect(&cfg.rabbitmq_url, ConnectionProperties::default())
        .await
        .expect("Failed to connect to RabbitMQ");

    tracing::info!("Connected to RabbitMQ");

    let (metrics_tx, _) = broadcast::channel(1024);
    let metrics_broadcast = handlers::ws::MetricsBroadcast { sender: metrics_tx.clone() };

    let amqp_channel = amqp_conn.create_channel().await.unwrap();

    amqp_channel.exchange_declare(
        "metrics_exchange",
        lapin::ExchangeKind::Fanout,
        ExchangeDeclareOptions::default(),
        FieldTable::default()
    ).await.unwrap();

    let queue = amqp_channel.queue_declare(
        "",
        QueueDeclareOptions { exclusive: true, ..Default::default() },
        FieldTable::default()
    ).await.unwrap();

    amqp_channel.queue_bind(
        queue.name().as_str(),
        "metrics_exchange",
        "",
        QueueBindOptions::default(),
        FieldTable::default()
    ).await.unwrap();

    let mut consumer = amqp_channel.basic_consume(
        queue.name().as_str(),
        "rust_metrics_consumer",
        BasicConsumeOptions::default(),
        FieldTable::default()
    ).await.unwrap();

    tokio::spawn(async move {
        while let Some(delivery) = consumer.next().await {
            if let Ok(delivery) = delivery {
                let _ = delivery.ack(BasicAckOptions::default()).await;
                if let Ok(msg) = String::from_utf8(delivery.data) {
                    let _ = metrics_tx.send(msg);
                }
            }
        }
    });

    let app = Router::new()
        .nest("/api/auth", auth_routes)
        .nest("/api", handlers::routes())
        .layer(cors)
        .layer(TraceLayer::new_for_http())
        .layer(axum::Extension(std::sync::Arc::new(amqp_conn)))
        .layer(axum::Extension(metrics_broadcast))
        .with_state(pool);

    let addr = SocketAddr::from(([0, 0, 0, 0], cfg.port));
    tracing::info!("Rust API listening on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
