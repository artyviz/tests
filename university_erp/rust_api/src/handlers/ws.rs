use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        Extension,
    },
    response::IntoResponse,
};
use futures_util::{sink::SinkExt, stream::StreamExt};
use tokio::sync::broadcast;

#[derive(Clone)]
pub struct MetricsBroadcast {
    pub sender: broadcast::Sender<String>,
}

pub async fn ws_handler(
    ws: WebSocketUpgrade,
    Extension(broadcast): Extension<MetricsBroadcast>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_socket(socket, broadcast))
}

async fn handle_socket(socket: WebSocket, broadcast: MetricsBroadcast) {
    let (mut sender, _) = socket.split();
    let mut rx = broadcast.sender.subscribe();

    while let Ok(msg) = rx.recv().await {
        if sender.send(Message::Text(msg)).await.is_err() {
            break;
        }
    }
}
