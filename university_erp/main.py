"""
University ERP — Python Worker Entry Point

Loads configuration, initialises the logger, connects to the
database, and starts the background worker loop (RabbitMQ
consumer or gRPC server) to accept tasks from the Elixir
API gateway.
"""

from __future__ import annotations

import os
import sys
import signal
import yaml
from typing import Any, Dict

# Ensure the project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from python_core.utils.logger import ERPLogger
from python_core.utils.exceptions import ConfigurationError


def _resolve_env_vars(obj):
    """Recursively resolve ${VAR:-default} patterns in config values."""
    import re
    pattern = re.compile(r'\$\{(\w+)(?::-(.*?))?\}')
    if isinstance(obj, str):
        def replacer(m):
            return os.environ.get(m.group(1), m.group(2) or "")
        return pattern.sub(replacer, obj)
    elif isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_env_vars(v) for v in obj]
    return obj


def load_config(path: str = None) -> Dict[str, Any]:
    """Load and validate settings.yaml, resolving env-var placeholders."""
    if path is None:
        path = os.path.join(PROJECT_ROOT, "config", "settings.yaml")
    if not os.path.isfile(path):
        raise ConfigurationError("settings.yaml", f"File not found: {path}")
    with open(path, encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    if not isinstance(config, dict):
        raise ConfigurationError("settings.yaml", "Root must be a YAML mapping")
    return _resolve_env_vars(config)


def configure_logging(config: Dict[str, Any]) -> None:
    """Initialise the ERP logger from config."""
    log_cfg = config.get("logging", {})
    ERPLogger.configure(
        level=log_cfg.get("level", "DEBUG"),
        fmt=log_cfg.get("format"),
        log_file=log_cfg.get("file"),
        max_bytes=log_cfg.get("max_bytes", 10_485_760),
        backup_count=log_cfg.get("backup_count", 5),
    )


def connect_database(config: Dict[str, Any]):
    """
    Create a psycopg2 connection pool.

    Returns the connection pool object (or None if psycopg2
    is not installed — graceful degradation for dev).
    """
    db_cfg = config.get("database", {})
    try:
        import psycopg2
        from psycopg2 import pool

        return pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=db_cfg.get("pool_size", 20),
            host=db_cfg.get("host", "localhost"),
            port=db_cfg.get("port", 5432),
            dbname=db_cfg.get("name", "university_erp"),
            user=db_cfg.get("user", "erp_admin"),
            password=os.environ.get("DB_PASSWORD", db_cfg.get("password", "")),
            connect_timeout=db_cfg.get("timeout", 30),
        )
    except ImportError:
        return None


def start_message_consumer(config: Dict[str, Any], db_pool: Any) -> None:
    """Block on a RabbitMQ consumer that processes generation tasks."""
    log = ERPLogger.get_logger("main")
    
    rabbitmq_url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/%2f")
    log.info("Connecting to RabbitMQ at %s", rabbitmq_url)

    try:
        import pika
        import json
        import time
        from python_core.etl.generator import generate_students
        from python_core.repository.student_repo import StudentRepository

        # Retry logic for connection
        max_retries = 5
        retry_count = 0
        connection = None
        
        while retry_count < max_retries and connection is None:
            try:
                params = pika.URLParameters(rabbitmq_url)
                params.connection_attempts = 3
                params.retry_delay = 2
                params.socket_timeout = 5.0
                
                connection = pika.BlockingConnection(params)
                log.info("Successfully connected to RabbitMQ")
                break
            except Exception as conn_err:
                retry_count += 1
                log.warning(
                    "Failed to connect to RabbitMQ (attempt %d/%d): %s",
                    retry_count,
                    max_retries,
                    str(conn_err)
                )
                if retry_count < max_retries:
                    log.info("Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    log.error("Max retries reached. Exiting.")
                    raise

        channel = connection.channel()

        # Input task queue from Rust
        channel.queue_declare(queue="generation_queue", durable=True)
        # Output metrics exchange to Rust WebSockets
        channel.exchange_declare(exchange="metrics_exchange", exchange_type="fanout")

        def callback(ch, method, properties, body):
            task = json.loads(body)
            job_id = task.get("job_id")
            count = task.get("count", 0)
            
            log.info("Received generation task for %s records (Job: %s)", count, job_id)
            
            # For each chunk requested by Rust
            # The Rust layer slices them into chunks, e.g. 10,000. 
            # We will generate and insert these directly.
            
            start_time = time.time()
            students_data = list(generate_students(count))
            
            # Insert into DB
            if db_pool:
                conn = db_pool.getconn()
                try:
                    repo = StudentRepository(conn)
                    inserted = repo.bulk_insert(students_data)
                    elapsed = time.time() - start_time
                    rate = inserted / elapsed if elapsed > 0 else 0
                    
                    sample = students_data[0] if inserted > 0 else {}
                    
                    # Compute metric summary
                    terminal_log = (
                        f"[{job_id[:8]}] Inserted {inserted} records | "
                        f"Rate: {rate:,.0f} req/sec | Latency: {elapsed*1000/inserted if inserted>0 else 0:.2f}ms/req | "
                        f"Sample: {sample.get('first_name')} {sample.get('last_name')}"
                    )
                    
                    # Publish progress
                    metric_payload = {
                        "job_id": job_id,
                        "inserted": inserted,
                        "rate": rate,
                        "elapsed": elapsed,
                        "log": terminal_log
                    }
                    
                    ch.basic_publish(
                        exchange="metrics_exchange",
                        routing_key="",
                        body=json.dumps(metric_payload)
                    )
                    log.info("Batch processed: %s", terminal_log)
                finally:
                    db_pool.putconn(conn)
            else:
                log.warning("No DB pool available. Simulation ran in memory only.")

            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue="generation_queue", on_message_callback=callback)

        log.info("Worker ready — waiting for tasks on 'generation_queue'. Press Ctrl+C to exit.")
        channel.start_consuming()

    except ImportError as ie:
        log.warning("pika not installed — running in standalone dev mode: %s", ie)
        # Block until SIGINT
        signal.pause() if hasattr(signal, "pause") else input("Press Enter to exit...\n")
    except Exception as exc:
        log.error("Worker failed with exception: %s", exc, exc_info=True)
        raise


def main() -> None:
    try:
        config = load_config()
        configure_logging(config)
        
        log = ERPLogger.get_logger("main")
        log.info("=" * 60)
        log.info("Starting University ERP Python Worker")
        log.info("=" * 60)
        
        log.info("Loading configuration and initializing database...")
        db_pool = connect_database(config)
        
        if db_pool:
            log.info("Database pool initialized successfully")
        else:
            log.warning("Database pool not available - some features may not work")
        
        log.info("Starting message consumer...")
        start_message_consumer(config, db_pool)
        
    except ConfigurationError as cfg_err:
        print(f"FATAL: Configuration error: {cfg_err}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"FATAL: Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
