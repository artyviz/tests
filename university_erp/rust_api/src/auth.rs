use argon2::{
    password_hash::{rand_core::OsRng, PasswordHash, PasswordHasher, PasswordVerifier, SaltString},
    Argon2,
};
use axum::{
    extract::{Request, State},
    http::{HeaderMap, StatusCode},
    middleware::Next,
    response::Response,
    Json,
};
use chrono::Utc;
use jsonwebtoken::{decode, encode, DecodingKey, EncodingKey, Header, Validation};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::db::Db;
use crate::errors::{AppError, Result};

// ── JWT secret (use env var in production) ──────────
fn jwt_secret() -> String {
    std::env::var("JWT_SECRET").unwrap_or_else(|_| "erp-jwt-secret-change-in-prod".to_string())
}

// ── Claims embedded in the JWT ──────────────────────
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Claims {
    pub sub: Uuid,       // user id
    pub username: String,
    pub role: String,    // admin, student, faculty
    pub exp: usize,      // expiry (unix timestamp)
}

// ── Request / response types ────────────────────────
#[derive(Debug, Deserialize)]
pub struct RegisterRequest {
    pub username: String,
    pub email: String,
    pub password: String,
    pub role: Option<String>,    // defaults to "student"
    pub full_name: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct LoginRequest {
    pub username: String,
    pub password: String,
}

#[derive(Debug, Serialize)]
pub struct AuthResponse {
    pub token: String,
    pub user: UserInfo,
}

#[derive(Debug, Serialize, sqlx::FromRow)]
pub struct UserInfo {
    pub id: Uuid,
    pub username: String,
    pub email: String,
    pub role: String,
    pub full_name: String,
}

#[derive(Debug, Serialize, sqlx::FromRow)]
struct UserRow {
    id: Uuid,
    username: String,
    email: String,
    password_hash: String,
    role: String,
    full_name: String,
    is_active: bool,
}

// ── Hash password ───────────────────────────────────
fn hash_password(password: &str) -> Result<String> {
    let salt = SaltString::generate(&mut OsRng);
    let hash = Argon2::default()
        .hash_password(password.as_bytes(), &salt)
        .map_err(|e| AppError::Internal(format!("Password hash error: {}", e)))?;
    Ok(hash.to_string())
}

fn verify_password(password: &str, hash: &str) -> Result<bool> {
    let parsed = PasswordHash::new(hash)
        .map_err(|e| AppError::Internal(format!("Invalid hash: {}", e)))?;
    Ok(Argon2::default()
        .verify_password(password.as_bytes(), &parsed)
        .is_ok())
}

// ── Generate JWT ────────────────────────────────────
fn create_token(user_id: Uuid, username: &str, role: &str) -> Result<String> {
    let expiry = Utc::now()
        .checked_add_signed(chrono::Duration::hours(24))
        .unwrap()
        .timestamp() as usize;

    let claims = Claims {
        sub: user_id,
        username: username.to_string(),
        role: role.to_string(),
        exp: expiry,
    };

    encode(
        &Header::default(),
        &claims,
        &EncodingKey::from_secret(jwt_secret().as_bytes()),
    )
    .map_err(|e| AppError::Internal(format!("Token creation failed: {}", e)))
}

/// Parse and validate a JWT, returning the claims.
pub fn decode_token(token: &str) -> Result<Claims> {
    let data = decode::<Claims>(
        token,
        &DecodingKey::from_secret(jwt_secret().as_bytes()),
        &Validation::default(),
    )
    .map_err(|_| AppError::Validation("Invalid or expired token".into()))?;
    Ok(data.claims)
}

// ── Register ────────────────────────────────────────
pub async fn register(State(db): State<Db>, Json(input): Json<RegisterRequest>) -> Result<Json<AuthResponse>> {
    if input.username.len() < 3 {
        return Err(AppError::Validation("Username must be at least 3 characters".into()));
    }
    if input.password.len() < 6 {
        return Err(AppError::Validation("Password must be at least 6 characters".into()));
    }

    // Check duplicate
    let exists: Option<(Uuid,)> = sqlx::query_as("SELECT id FROM users WHERE username = $1 OR email = $2")
        .bind(&input.username)
        .bind(&input.email)
        .fetch_optional(&db)
        .await?;
    if exists.is_some() {
        return Err(AppError::Duplicate("Username or email already taken".into()));
    }

    let password_hash = hash_password(&input.password)?;
    let role = input.role.unwrap_or_else(|| "student".to_string());
    let full_name = input.full_name.unwrap_or_default();

    let user = sqlx::query_as::<_, UserInfo>(
        r#"INSERT INTO users (id, username, email, password_hash, role, full_name)
           VALUES ($1, $2, $3, $4, $5, $6)
           RETURNING id, username, email, role, full_name"#
    )
    .bind(Uuid::new_v4())
    .bind(&input.username)
    .bind(&input.email)
    .bind(&password_hash)
    .bind(&role)
    .bind(&full_name)
    .fetch_one(&db)
    .await?;

    let token = create_token(user.id, &user.username, &user.role)?;

    Ok(Json(AuthResponse { token, user }))
}

// ── Login ───────────────────────────────────────────
pub async fn login(State(db): State<Db>, Json(input): Json<LoginRequest>) -> Result<Json<AuthResponse>> {
    let user = sqlx::query_as::<_, UserRow>(
        "SELECT id, username, email, password_hash, role, full_name, is_active FROM users WHERE username = $1"
    )
    .bind(&input.username)
    .fetch_optional(&db)
    .await?
    .ok_or_else(|| AppError::Validation("Invalid username or password".into()))?;

    if !user.is_active {
        return Err(AppError::Validation("Account is deactivated".into()));
    }

    if !verify_password(&input.password, &user.password_hash)? {
        return Err(AppError::Validation("Invalid username or password".into()));
    }

    let token = create_token(user.id, &user.username, &user.role)?;

    Ok(Json(AuthResponse {
        token,
        user: UserInfo {
            id: user.id,
            username: user.username,
            email: user.email,
            role: user.role,
            full_name: user.full_name,
        },
    }))
}

// ── Get current user ────────────────────────────────
pub async fn me(State(db): State<Db>, headers: HeaderMap) -> Result<Json<UserInfo>> {
    let claims = extract_claims(&headers)?;
    let user = sqlx::query_as::<_, UserInfo>(
        "SELECT id, username, email, role, full_name FROM users WHERE id = $1"
    )
    .bind(claims.sub)
    .fetch_optional(&db)
    .await?
    .ok_or_else(|| AppError::NotFound("User not found".into()))?;
    Ok(Json(user))
}

// ── Helper: extract claims from Authorization header ─
fn extract_claims(headers: &HeaderMap) -> Result<Claims> {
    let auth_header = headers
        .get("Authorization")
        .and_then(|v| v.to_str().ok())
        .ok_or_else(|| AppError::Validation("Missing Authorization header".into()))?;

    let token = auth_header
        .strip_prefix("Bearer ")
        .ok_or_else(|| AppError::Validation("Invalid Authorization format".into()))?;

    decode_token(token)
}

// ── Middleware: require authentication ───────────────
pub async fn require_auth(
    headers: HeaderMap,
    mut request: Request,
    next: Next,
) -> std::result::Result<Response, StatusCode> {
    let claims = extract_claims(&headers).map_err(|_| StatusCode::UNAUTHORIZED)?;
    request.extensions_mut().insert(claims);
    Ok(next.run(request).await)
}

// ── Middleware: require admin role ───────────────────
pub async fn require_admin(
    headers: HeaderMap,
    mut request: Request,
    next: Next,
) -> std::result::Result<Response, StatusCode> {
    let claims = extract_claims(&headers).map_err(|_| StatusCode::UNAUTHORIZED)?;
    if claims.role != "admin" {
        return Err(StatusCode::FORBIDDEN);
    }
    request.extensions_mut().insert(claims);
    Ok(next.run(request).await)
}
