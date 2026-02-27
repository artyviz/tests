# Python Worker - Fixes Applied

## Root Cause Analysis
The python_worker was crashing immediately (exit code 1) due to several configuration and implementation issues:

1. **Incomplete environment variables** - Missing DB_USER, DB_PORT, DB_NAME
2. **Lack of connection retry logic** - RabbitMQ connections would timeout without backoff
3. **Poor error logging** - Exceptions were not being logged with full context
4. **RabbitMQ healthcheck** - Was using `check_port_connectivity` instead of `ping`
5. **No start_period** - Containers were being health-checked before startup completed

## Changes Made

### 1. docker-compose.yml

#### RabbitMQ Service (Lines 31-48)
- Added explicit credentials environment variables
- Changed healthcheck from `rabbitmq-diagnostics check_port_connectivity` to `rabbitmq-diagnostics ping` (more reliable)
- Added `start_period: 30s` to allow RabbitMQ time to boot before health checks
- Reduced retry count from 10 to 5 (more reasonable)

#### Python Worker Service (Lines 83-113)
- Added comprehensive environment variables:
  - `DB_HOST`, `DB_PORT`, `DB_NAME` (explicitly set)
  - `DB_USER`: erp_admin
  - `MQ_HOST`: rabbitmq (hostname for internal reference)
  - `PYTHONUNBUFFERED: "1"` (unbuffered Python output)
  - `LOG_LEVEL`: INFO
- Added healthcheck that verifies RabbitMQ connectivity (not just process existence)
- Added `start_period: 60s` to give worker time to initialize before health checks

### 2. main.py

#### Enhanced error handling in main() function
- Wrapped startup in try-except to capture and display fatal errors
- Logs clear startup sequence to stderr and logs
- Distinguishes between ConfigurationError and unexpected errors
- Uses traceback for debugging

#### Added retry logic in start_message_consumer()
- Connection retry loop with max_retries = 5
- Exponential backoff (2-5 second delays between retries)
- Configurable pika parameters:
  - `connection_attempts: 3`
  - `retry_delay: 2`
  - `socket_timeout: 5.0`
- Clear logging at each retry step
- Graceful exit after max retries with descriptive error

#### Improved exception logging
- Added `exc_info=True` to log.error() for full traceback
- Separated ImportError handling with clearer message

### 3. RUNNING.txt

- Added warning about `--profile etl` requirement
- Added 50+ lines of detailed troubleshooting:
  - Diagnostics for "Restarting (1)" status
  - Verification commands for each dependency
  - Environment variable inspection
  - RabbitMQ connectivity testing
  - No-cache rebuild instructions

## What This Fixes

✅ Worker now waits properly for RabbitMQ to be ready (healthcheck + start_period)  
✅ Worker retries connection failures instead of crashing immediately  
✅ Clear error messages in logs when issues occur  
✅ Proper environment variable propagation from docker-compose to Python code  
✅ Easier debugging with detailed log output  

## Testing the Fix

### Rebuild the worker:
```bash
docker compose build python_worker
```

### Start the full stack with worker:
```bash
docker compose up -d              # Start core services (postgres, rabbitmq, rust_api, web_app)
docker compose --profile etl up -d  # Start the python_worker
```

### Verify it's running:
```bash
docker ps              # Check erp_python_worker is "Up"
docker logs erp_python_worker --tail 30  # Should show "Worker ready — waiting for tasks"
```

### Trigger a simulation from the web app:
Navigate to http://localhost:8000/simulate and click a batch button

### Check worker received the task:
```bash
docker logs erp_python_worker --tail 20  # Should show "Received generation task"
```

## Fallback Debugging

If issues persist:

1. **Full container rebuild** (clears all cached layers):
   ```bash
   docker compose build --no-cache python_worker
   docker compose --profile etl up python_worker
   ```

2. **Verify RabbitMQ directly**:
   ```bash
   docker exec erp_python_worker python -c \
     "import pika; conn = pika.BlockingConnection(pika.URLParameters('amqp://guest:guest@rabbitmq:5672/%2f')); print('Connected!')"
   ```

3. **Check environment in container**:
   ```bash
   docker exec erp_python_worker env | grep -E "DB_|RABBIT|LOG"
   ```
