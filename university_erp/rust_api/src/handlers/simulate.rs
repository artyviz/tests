use axum::{extract::Extension, http::StatusCode, response::IntoResponse, Json};
use lapin::{options::*, BasicProperties, Connection, types::FieldTable};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Deserialize)]
pub struct SimulateRequest {
    pub count: u32,
}

#[derive(Serialize)]
pub struct SimulateResponse {
    pub job_id: Uuid,
    pub message: String,
}

#[derive(Serialize)]
pub struct TaskPayload {
    pub job_id: Uuid,
    pub count: u32,
    pub batch_size: u32,
}

#[axum::debug_handler]
pub async fn start_simulation(
    Extension(amqp): Extension<std::sync::Arc<Connection>>,
    Json(payload): Json<SimulateRequest>,
) -> impl IntoResponse {
    let job_id = Uuid::new_v4();
    let channel = match amqp.create_channel().await {
        Ok(c) => c,
        Err(e) => {
            tracing::error!("Failed to create AMQP channel: {}", e);
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(SimulateResponse {
                    job_id: Uuid::nil(),
                    message: "Internal server error".into(),
                }),
            );
        }
    };

    let _ = channel
        .queue_declare(
            "generation_queue",
            QueueDeclareOptions {
                durable: true,
                ..Default::default()
            },
            FieldTable::default(),
        )
        .await;

    let batch_size = 10000;
    let mut remaining = payload.count;

    while remaining > 0 {
        let chunk = if remaining > batch_size { batch_size } else { remaining };
        let task = TaskPayload {
            job_id,
            count: chunk,
            batch_size: chunk,
        };
        
        let payload_bytes = serde_json::to_vec(&task).unwrap();
        
        let publish = channel
            .basic_publish(
                "",
                "generation_queue",
                BasicPublishOptions::default(),
                &payload_bytes,
                BasicProperties::default().with_delivery_mode(2),
            )
            .await;
            
        if let Err(e) = publish {
            tracing::error!("Failed to publish task: {}", e);
        }
        
        remaining -= chunk;
    }

    (
        StatusCode::ACCEPTED,
        Json(SimulateResponse {
            job_id,
            message: format!("Simulation started for {} records", payload.count),
        }),
    )
}
