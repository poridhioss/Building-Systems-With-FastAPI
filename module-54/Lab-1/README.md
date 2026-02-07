# Lab 1: Adding Reliability Features to Celery Tasks

In Module 53, you built a Flask-Celery integration that can submit background tasks and check their status through a REST API. The system works perfectly when everything goes right—tasks execute successfully, and clients can retrieve results. But production environments are messy. External APIs timeout. Databases lock. Network connections drop. Tasks encounter unexpected data and raise exceptions.

Without proper error handling, these failures disappear silently into logs. Without retry logic, transient errors (like a temporary network glitch) cause permanent task failures. Without timeouts, a single buggy task can consume worker resources indefinitely. Without logging, debugging failed tasks becomes a nightmare of guesswork.

In this lab, you'll transform your basic task queue into a production-ready system by adding four critical reliability features: automatic retries with exponential backoff, timeout enforcement to kill runaway tasks, comprehensive logging to track execution, and structured error handling to return meaningful failure messages to API clients.

![alt text](images/archi-diagrams/mod-54_high-level.drawio.svg)
<!-- 
**Key Reliability Mechanisms:**

1. **Logging (Blue Boxes)** - Every task lifecycle event is logged with timestamps:
   - Task start, success, error, retry scheduled, max retries exhausted
   - Enables debugging and monitoring in production

2. **Timeout Enforcement (Yellow Diamond)** - Prevents runaway tasks:
   - Soft limit: Raises `SoftTimeLimitExceeded` for graceful cleanup (8-25s)
   - Hard limit: Forcefully terminates task if cleanup takes too long (10-30s)

3. **Retry Logic (Orange Path)** - Handles transient failures automatically:
   - Decision point checks if retries remain (`retries < max_retries`)
   - Exponential backoff: 5s → 10s → 20s between attempts
   - Task requeued to broker for later execution

4. **Error Handling (Throughout)** - Structured responses for all outcomes:
   - Success: Returns result data
   - Timeout: Returns timeout message with attempted duration
   - Failure after retries: Returns error message with retry count
   - All errors stored in result backend for client retrieval -->

## Objectives

By the end of this lab, you will:

1. Configure automatic retry behavior with max retries and exponential backoff
2. Implement manual retry logic using `self.retry()` for recoverable errors
3. Set hard and soft timeout limits to prevent runaway tasks
4. Add comprehensive logging to track task lifecycle events
5. Implement structured error handling with try-except blocks
6. Create tasks that simulate failures and timeouts for testing
7. Observe retry attempts, timeout termination, and error states in worker logs
8. Verify RETRY and FAILURE states via the status endpoint

## Background: Understanding Reliability Features

Before implementing these features, let's understand what each reliability mechanism does and why it matters in production systems.

### 1. Retry Logic

Retry logic handles transient failures—temporary errors that might succeed if you try again. Network timeouts, database deadlocks, and rate-limited API calls are classic examples. Without retries, a momentary network blip causes permanent task failure.

**Key Concepts:**

- **Max Retries**: Maximum number of retry attempts (e.g., `max_retries=3`)
- **Retry Delay**: Time to wait before retrying (e.g., `default_retry_delay=5` seconds)
- **Exponential Backoff**: Doubling the delay with each retry (5s → 10s → 20s) to avoid overwhelming the failing service
- **Manual Retry**: Using `self.retry(exc=exc, countdown=delay)` to programmatically retry

**Retry Flow with Exponential Backoff:**

![alt text](images/archi-diagrams/mod-54_retry.drawio.svg)

**When to Use Retries:**
- Network requests to external APIs
- Database operations that might deadlock
- File operations that might have temporary locks
- Any operation where the error might be temporary

**When NOT to Use Retries:**
- Validation errors (bad input won't fix itself)
- Authentication failures (wrong credentials)
- Resource not found errors (404s)
- Business logic errors

### 2. Timeout Enforcement

Timeout enforcement prevents runaway tasks from consuming worker resources indefinitely. A buggy infinite loop or a hung network connection could block a worker forever without timeouts.

**Key Concepts:**

- **Soft Time Limit**: Raises `SoftTimeLimitExceeded` exception for graceful cleanup (e.g., `soft_time_limit=8`)
- **Hard Time Limit**: Forcefully terminates the task process if cleanup takes too long (e.g., `time_limit=10`)
- **Graceful Shutdown**: Catching the soft limit to close connections, save state, or return partial results

**Timeout Enforcement Flow:**

![alt text](images/archi-diagrams/mod-54_timeout.drawio.svg)

**Implementation Pattern:**

```python
@celery.task(time_limit=10, soft_time_limit=8)
def long_running_task(self):
    try:
        # Your task logic here
        heavy_computation()
    except SoftTimeLimitExceeded:
        # Graceful cleanup
        cleanup_resources()
        return {"status": "timeout", "message": "Task exceeded time limit"}
```

**When to Set Timeouts:**
- I/O operations (API calls, file downloads)
- CPU-intensive computations
- Any task that could potentially hang
- Tasks that call external services with unpredictable response times

### 3. Error Handling

Error handling determines what happens when a task fails. Do you retry? Return an error message? Let it crash? Proper error handling makes the difference between a resilient system and one that silently swallows failures.

**Key Concepts:**

- **Try-Except Blocks**: Catch exceptions to control behavior
- **Structured Error Responses**: Return dictionaries with error details instead of raising exceptions
- **Error Propagation**: When to let errors bubble up vs. handling them
- **Retry vs. Return**: Deciding whether to retry or return an error

**Decision Guide:**

| Error Type | Pattern | Reason |
|------------|---------|--------|
| Network timeout | Pattern 1 (Retry) | Might succeed on next attempt |
| Database deadlock | Pattern 1 (Retry) | Usually resolves quickly |
| Invalid input | Pattern 2 (Return error) | Won't fix itself |
| Auth failure | Pattern 2 (Return error) | Requires user action |
| Unexpected exception | Pattern 3 (Raise) | Needs investigation |
| System error | Pattern 3 (Raise) | Should alert monitoring |

### 4. Logging

Logging provides visibility into task execution. Without logs, debugging failed tasks means guessing. With comprehensive logging, you have a complete audit trail of what happened and when.

**Key Concepts:**

- **Log Levels**: INFO (normal operation), WARNING (potential issues), ERROR (failures)
- **Structured Logging**: Include context (task ID, user ID, attempt number)
- **Lifecycle Events**: Log start, success, failure, retry, timeout
- **Correlation**: Use consistent identifiers to trace a task through its lifecycle

**What to Log:**

1. **Task Start**: Task name, input parameters, task ID
2. **Progress Milestones**: Key steps completed (useful for long tasks)
3. **Success**: Completion message, duration, result summary
4. **Errors**: Exception type, error message, attempt number
5. **Retries**: Retry decision, countdown, total attempts
6. **Timeouts**: Time limit exceeded, cleanup actions
7. **API Calls**: Endpoint accessed, client info, status code

**Logging Best Practices:**

```python
import logging
logger = logging.getLogger(__name__)

@celery.task(bind=True, max_retries=3)
def example_task(self, user_id):
    try:
        # Log start with context
        logger.info(f"example_task: Starting for user {user_id}, task_id={self.request.id}")

        # Log progress
        logger.info(f"example_task: Fetched user data for {user_id}")

        result = do_work(user_id)

        # Log success
        logger.info(f"example_task: Completed for user {user_id}, duration=5.2s")
        return result

    except Exception as exc:
        # Log error with full context
        logger.error(
            f"example_task: Failed for user {user_id}, "
            f"error={exc}, attempt={self.request.retries + 1}/{self.max_retries}"
        )
        raise self.retry(exc=exc)
```

**Why Logging Matters:**

When a task fails in production at 3am, logs answer:
- What task failed? (`send_welcome_email`)
- What input triggered it? (`user@example.com`)
- When did it fail? (`2026-02-03 03:15:42`)
- What error occurred? (`Connection timeout`)
- Did it retry? How many times? (`3 retries, all failed`)
- What was the final outcome? (`Max retries exhausted`)

Without logs, you're blind. With proper logging, you have a complete story. Now that you understand these four reliability mechanisms, let's implement them in a Flask-Celery application.

## Project Structure

You'll be working with the same project structure from Module 53, with modifications to existing files:

```
flask-celery-app/
├── app/
│   ├── __init__.py          # Flask + Celery initialization
│   ├── routes.py            # API endpoints (will add new endpoint)
│   └── tasks.py             # Task definitions (will add retries, timeouts, logging, error handling)
├── celery_utils.py          # Application Factory pattern
├── config.py                # Configuration (no changes)
├── docker-compose.yml       # Redis container
├── requirements.txt         # Dependencies
├── run.py                   # Application entry point
└── .venv/                   # Virtual environment
```

Check Python version:

```bash
python --version
```

If it doesn't work, install Python 3.12:

```bash
sudo apt update
sudo apt install python3.12-venv -y
alias python=python3.12
source ~/.bashrc
```

## Step 1: Set Up the Project (Fresh VM)

Since you're starting on a fresh VM, you need to recreate the project from Module 53. If you already have the code from Module 53, you can skip to Step 2.

Create the project directory and files:

```bash
mkdir flask-celery-app
cd flask-celery-app
mkdir app
touch app/__init__.py app/routes.py app/tasks.py
touch celery_utils.py config.py run.py docker-compose.yml requirements.txt
```

Create a virtual environment and install dependencies:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Create requirements.txt
cat > requirements.txt << 'EOF'
flask==3.0.0
celery==5.3.4
redis==5.0.1
EOF

# Install dependencies
pip install -r requirements.txt
```

Create `docker-compose.yml` for Redis:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: flask-celery-redis
    ports:
      - "6379:6379"
    command: redis-server
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
```

Start Redis:

```bash
docker compose up -d
docker ps  # Verify Redis is running
```

Create `config.py`:

```python
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TIMEZONE = 'UTC'
    CELERY_ENABLE_UTC = True
```

Create `celery_utils.py`:

```python
from celery import Celery

def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL'],
        backend=app.config['CELERY_RESULT_BACKEND']
    )

    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
```

Create `app/__init__.py`:

```python
from flask import Flask
from celery_utils import make_celery
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    from app.routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    return app

app = create_app()
celery = make_celery(app)

from app import tasks
```

Create `run.py`:

```python
from app import app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

Now you have the basic structure. We'll add the task definitions and routes in the next steps.

## Step 2: Add Logging Configuration

Before modifying tasks, let's set up Python's logging module so we can track task execution. Logging is crucial for debugging failures in production—without logs, you're flying blind.

We'll configure logging at the application level and use it throughout our tasks to record start times, completion, failures, and retry attempts.

**Modify `app/__init__.py` to add logging configuration:**

```python
from flask import Flask
from celery_utils import make_celery
from config import Config
import logging  # NEW: Import logging module

# NEW: Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    from app.routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    return app

app = create_app()
celery = make_celery(app)

from app import tasks
```

**What this does:**

- **level=logging.INFO**: Captures INFO, WARNING, and ERROR level messages
- **format**: Includes timestamp, log level, module name, and message
- **datefmt**: Human-readable timestamp format

Now when tasks log messages using `logging.info()` or `logging.error()`, they'll appear in the Celery worker terminal with timestamps and context.

## Step 3: Implement Tasks with Reliability Features

Now we'll create the task definitions with retries, timeouts, logging, and error handling. We'll implement three original tasks from Module 53 plus two new demonstration tasks.

**Create `app/tasks.py`:**

```python
from app import celery
from celery.exceptions import SoftTimeLimitExceeded
import time
import random
import logging

logger = logging.getLogger(__name__)

@celery.task(
    bind=True,
    max_retries=3,
    default_retry_delay=5
)
def test_task(self):
    """
    Simple health check task with retry capability.
    Demonstrates basic retry configuration.
    """
    try:
        logger.info("test_task: Starting execution")

        from flask import current_app
        secret_key = current_app.config.get('SECRET_KEY')

        logger.info(f"test_task: Accessed Flask config successfully")
        time.sleep(3)

        logger.info("test_task: Completed successfully")
        return "Pong from Background!"

    except Exception as exc:
        logger.error(f"test_task: Failed with error: {exc}")
        raise self.retry(exc=exc)


@celery.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    time_limit=15,
    soft_time_limit=12
)
def send_welcome_email(self, user_email):
    """
    Simulates sending a welcome email with timeout protection.

    Demonstrates:
    - Retry on network errors
    - Timeout enforcement
    - Structured error handling
    """
    try:
        logger.info(f"send_welcome_email: Starting for {user_email}")

        # Simulate network I/O
        time.sleep(5)

        logger.info(f"send_welcome_email: Successfully sent to {user_email}")
        return f"Email sent to {user_email}"

    except SoftTimeLimitExceeded:
        logger.warning(f"send_welcome_email: Soft time limit exceeded for {user_email}")
        # Graceful cleanup before hard termination
        return {"status": "timeout", "message": "Email sending timed out"}

    except Exception as exc:
        logger.error(f"send_welcome_email: Failed for {user_email} - {exc}")
        # Retry on transient errors
        raise self.retry(exc=exc, countdown=10)


@celery.task(
    bind=True,
    max_retries=2,
    default_retry_delay=15,
    time_limit=30,
    soft_time_limit=25
)
def generate_monthly_report(self, user_id):
    """
    Simulates PDF generation with comprehensive error handling.

    Demonstrates:
    - CPU-intensive work with timeout
    - Structured error responses
    - Retry logic for recoverable errors
    """
    try:
        logger.info(f"generate_monthly_report: Starting for user {user_id}")

        # Simulate CPU-intensive processing
        time.sleep(10)

        report_filename = f"report_user_{user_id}_{int(time.time())}.pdf"
        logger.info(f"generate_monthly_report: Generated {report_filename}")

        return {
            "filename": report_filename,
            "user_id": user_id,
            "status": "completed"
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"generate_monthly_report: Soft time limit exceeded for user {user_id}")
        return {
            "status": "timeout",
            "message": "Report generation exceeded time limit",
            "user_id": user_id
        }

    except Exception as exc:
        logger.error(f"generate_monthly_report: Failed for user {user_id} - {exc}")
        raise self.retry(exc=exc, countdown=15)


@celery.task(
    bind=True,
    max_retries=3,
    default_retry_delay=5
)
def flaky_task(self, task_number):
    """
    Intentionally fails 70% of the time to demonstrate retry behavior.

    This task simulates real-world scenarios where external services
    are unreliable (API rate limits, network issues, database locks).
    """
    try:
        logger.info(f"flaky_task: Attempt started for task #{task_number}")

        # Simulate work
        time.sleep(2)

        # 70% chance of failure
        if random.random() < 0.7:
            logger.warning(f"flaky_task: Simulated failure for task #{task_number}")
            raise Exception("Simulated transient error (network timeout)")

        logger.info(f"flaky_task: Successfully completed task #{task_number}")
        return {
            "status": "success",
            "task_number": task_number,
            "message": "Task succeeded after retries"
        }

    except Exception as exc:
        logger.error(f"flaky_task: Failed task #{task_number} - {exc}")

        # Check if we've exhausted retries
        if self.request.retries >= self.max_retries:
            logger.error(f"flaky_task: Max retries exhausted for task #{task_number}")
            return {
                "status": "failed",
                "task_number": task_number,
                "error": str(exc),
                "retries": self.request.retries
            }

        # Exponential backoff: 5s, 10s, 20s
        countdown = self.default_retry_delay * (2 ** self.request.retries)
        logger.info(f"flaky_task: Retrying task #{task_number} in {countdown} seconds")

        raise self.retry(exc=exc, countdown=countdown)


@celery.task(
    bind=True,
    time_limit=10,
    soft_time_limit=8
)
def slow_task(self, duration):
    """
    Intentionally runs longer than timeout to demonstrate termination.

    This demonstrates how Celery enforces time limits to prevent
    runaway tasks from consuming worker resources indefinitely.
    """
    try:
        logger.info(f"slow_task: Starting {duration}-second task")

        # This will exceed our 8-second soft limit if duration > 8
        time.sleep(duration)

        logger.info(f"slow_task: Completed successfully")
        return {
            "status": "completed",
            "duration": duration
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"slow_task: Soft time limit (8s) exceeded")

        # Return gracefully before hard termination
        return {
            "status": "timeout",
            "message": f"Task exceeded {self.soft_time_limit}s soft limit",
            "attempted_duration": duration
        }
```

**Key reliability features added:**

1. **bind=True**: Allows access to `self` (the task instance) for manual retry and request metadata
2. **max_retries**: Maximum number of retry attempts before permanent failure
3. **default_retry_delay**: Seconds to wait before retrying (can be overridden with exponential backoff)
4. **time_limit**: Hard timeout (task is killed after this many seconds)
5. **soft_time_limit**: Soft timeout (raises SoftTimeLimitExceeded for graceful cleanup)
6. **Logging**: Every task logs start, success, failure, and retry events
7. **Error handling**: Try-except blocks capture exceptions and return structured errors
8. **Exponential backoff**: `flaky_task` doubles the retry delay with each attempt

## Step 4: Create API Endpoints

Now let's create the Flask routes that trigger these tasks. We'll include the original three endpoints from Module 53 plus a new endpoint for testing the flaky task, and the status checking endpoint.

**Create `app/routes.py`:**

```python
from flask import Blueprint, jsonify, request
from celery.result import AsyncResult
import logging

bp = Blueprint('routes', __name__)
logger = logging.getLogger(__name__)

@bp.route('/ping', methods=['POST'])
def ping():
    """Health check endpoint that triggers test task."""
    from app.tasks import test_task

    logger.info("Endpoint /ping: Queuing test_task")
    task = test_task.delay()

    return jsonify({
        'message': 'Task queued',
        'task_id': task.id
    }), 202


@bp.route('/register', methods=['POST'])
def register():
    """User registration endpoint with background email."""
    from app.tasks import send_welcome_email

    data = request.get_json()
    user_email = data.get('email')

    if not user_email:
        logger.warning("Endpoint /register: Missing email parameter")
        return jsonify({'error': 'Email is required'}), 400

    logger.info(f"Endpoint /register: Queuing email task for {user_email}")
    task = send_welcome_email.delay(user_email)

    return jsonify({
        'message': 'User registered successfully',
        'email': user_email,
        'email_task_id': task.id
    }), 201


@bp.route('/reports/generate', methods=['POST'])
def generate_report():
    """Report generation endpoint."""
    from app.tasks import generate_monthly_report

    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        logger.warning("Endpoint /reports/generate: Missing user_id parameter")
        return jsonify({'error': 'user_id is required'}), 400

    logger.info(f"Endpoint /reports/generate: Queuing PDF task for user {user_id}")
    task = generate_monthly_report.delay(user_id)

    return jsonify({
        'message': 'Report generation started',
        'task_id': task.id,
        'user_id': user_id
    }), 202


@bp.route('/test-reliability', methods=['POST'])
def test_reliability():
    """
    NEW: Endpoint to test retry behavior with flaky task.

    This endpoint triggers a task that fails randomly to demonstrate
    automatic retries and exponential backoff.
    """
    from app.tasks import flaky_task

    data = request.get_json() or {}
    task_number = data.get('task_number', 1)

    logger.info(f"Endpoint /test-reliability: Queuing flaky_task #{task_number}")
    task = flaky_task.delay(task_number)

    return jsonify({
        'message': 'Flaky task queued (70% chance of failure)',
        'task_id': task.id,
        'task_number': task_number,
        'info': 'This task will automatically retry up to 3 times with exponential backoff'
    }), 202


@bp.route('/test-timeout', methods=['POST'])
def test_timeout():
    """
    NEW: Endpoint to test timeout enforcement.

    Triggers a task that runs longer than its timeout limit to demonstrate
    Celery's timeout enforcement mechanism.
    """
    from app.tasks import slow_task

    data = request.get_json() or {}
    duration = data.get('duration', 15)

    logger.info(f"Endpoint /test-timeout: Queuing slow_task with {duration}s duration")
    task = slow_task.delay(duration)

    return jsonify({
        'message': f'Slow task queued (will run for {duration} seconds)',
        'task_id': task.id,
        'duration': duration,
        'timeout_info': 'Task has 8s soft limit and 10s hard limit'
    }), 202


@bp.route('/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """
    Check task status and retrieve results.

    Returns task state (PENDING, SUCCESS, FAILURE, RETRY) and
    result or error message if available.
    """
    # Import celery here to avoid circular import
    # (app/__init__.py imports routes.py before celery is defined)
    from app import celery

    task_result = AsyncResult(task_id, app=celery)

    response = {
        'task_id': task_id,
        'state': task_result.state,
        'status': task_result.status
    }

    if task_result.state == 'PENDING':
        response['message'] = 'Task is pending or being processed'
    elif task_result.state == 'SUCCESS':
        response['message'] = 'Task completed successfully'
        response['result'] = task_result.result
    elif task_result.state == 'FAILURE':
        response['message'] = 'Task failed'
        response['error'] = str(task_result.info)
    elif task_result.state == 'RETRY':
        response['message'] = 'Task is being retried'
        response['retry_info'] = str(task_result.info)
    else:
        response['message'] = f'Task state: {task_result.state}'

    logger.info(f"Endpoint /tasks/{task_id}: State={task_result.state}")
    return jsonify(response), 200
```

**What's new:**

- **POST /test-reliability**: Triggers the flaky task to observe retry behavior
- **POST /test-timeout**: Triggers the slow task to observe timeout enforcement
- **Logging**: All endpoints log their actions for observability
- **GET /tasks/<task_id>**: Returns RETRY state when tasks are retrying
- **Circular import fix**: `from app import celery` is imported inside `get_task_status()` function instead of at the module level to avoid circular import errors

## Step 5: Start the System

Now let's start all the components. You'll need three terminals.

**Terminal 1: Celery Worker**

```bash
cd flask-celery-app
source .venv/bin/activate
celery -A app.celery worker --loglevel=info
```

You should see the worker start and register all five tasks:
- `app.tasks.test_task`
- `app.tasks.send_welcome_email`
- `app.tasks.generate_monthly_report`
- `app.tasks.flaky_task`
- `app.tasks.slow_task`

**Terminal 2: Flask Application**

```bash
cd flask-celery-app
source .venv/bin/activate
python run.py
```

The Flask server should start on port 5000.

**Terminal 3: Testing**

This terminal will be used for curl commands.

## Step 6: Test Basic Tasks with Logging

First, let's verify the basic tasks work and observe the logging output.

**Test the health check:**

```bash
curl -X POST http://localhost:5000/ping
```

**Response:**
```json
{
  "message": "Task queued",
  "task_id": "abc-123-def-456"
}
```

**Check Terminal 1 (Worker)** - you should see logs:

![alt text](./images/image.png)

The timestamps and structured logging make it easy to track execution.

## Step 7: Test Retry Behavior with Flaky Task

Now let's trigger the flaky task to observe automatic retries with exponential backoff.

**Trigger a flaky task:**

```bash
curl -X POST http://localhost:5000/test-reliability \
  -H "Content-Type: application/json" \
  -d '{"task_number": 1}'
```

**Response:**
```json
{
  "message": "Flaky task queued (70% chance of failure)",
  "task_id": "xyz-789-abc-123",
  "task_number": 1,
  "info": "This task will automatically retry up to 3 times with exponential backoff"
}
```

**Watch Terminal 1 (Worker) carefully.** Since the task has a 70% failure rate, you'll likely see retry attempts:

**Example output (if task fails and retries):**

![alt text](./images/image-1.png)

**Notice the exponential backoff**: First retry after 5 seconds, second retry after 10 seconds, third would be after 20 seconds.

**Check the task status while it's retrying:**

```bash
# Copy the task_id from the response above
curl http://localhost:5000/tasks/xyz-789-abc-123
```

You might catch it in RETRY state:

![alt text](./images/image-2.png)

After the task eventually succeeds (or exhausts retries), check status again:

```bash
curl http://localhost:5000/tasks/xyz-789-abc-123
```

**If successful:**

![alt text](./images/image-3.png)

**If all retries failed:**
```json
{
  "task_id": "xyz-789-abc-123",
  "state": "SUCCESS",
  "status": "SUCCESS",
  "message": "Task completed successfully",
  "result": {
    "status": "failed",
    "task_number": 1,
    "error": "Simulated transient error (network timeout)",
    "retries": 3
  }
}
```

Notice that even when the task logic "fails," Celery marks it as SUCCESS because the task function returned a value (the error dict) rather than raising an exception. This is intentional—we handle the error gracefully and return structured data.

## Step 8: Test Timeout Enforcement

Now let's trigger a task that exceeds its timeout to see Celery's enforcement in action.

**Trigger a slow task that will timeout:**

```bash
curl -X POST http://localhost:5000/test-timeout \
  -H "Content-Type: application/json" \
  -d '{"duration": 15}'
```

**Response:**
```json
{
  "message": "Slow task queued (will run for 15 seconds)",
  "task_id": "timeout-task-123",
  "duration": 15,
  "timeout_info": "Task has 8s soft limit and 10s hard limit"
}
```

**Watch Terminal 1 (Worker).** The task will start, then after 8 seconds hit the soft limit:

![alt text](./images/image-4.png)

The task catches `SoftTimeLimitExceeded` and returns gracefully. If it didn't handle the exception, Celery would kill it at the 10-second hard limit.

**Check the task status:**

```bash
curl http://localhost:5000/tasks/timeout-task-123
```

**Response:**

![alt text](./images/image-5.png)

The task "succeeded" in the sense that it handled the timeout gracefully and returned a structured response indicating what happened.

**What if we trigger a task within the limit?**

```bash
curl -X POST http://localhost:5000/test-timeout \
  -H "Content-Type: application/json" \
  -d '{"duration": 5}'
```

**Worker output:**

![alt text](./images/image-6.png)

**Status:**

![alt text](./images/image-7.png)

This demonstrates that the timeout only enforces when exceeded.

## Step 9: Test Multiple Concurrent Flaky Tasks

Let's submit multiple flaky tasks simultaneously to observe concurrent retry behavior.

**Submit 5 flaky tasks rapidly:**

```bash
for i in {1..5}; do
  curl -X POST http://localhost:5000/test-reliability \
    -H "Content-Type: application/json" \
    -d "{\"task_number\": $i}" &
done
wait
```

**Watch Terminal 1 (Worker).** You'll see multiple tasks executing concurrently (depending on your worker concurrency), with some failing and retrying at different intervals.

**Example interleaved output:**
```
[10:50:10] INFO in tasks: flaky_task: Attempt started for task #1
[10:50:10] INFO in tasks: flaky_task: Attempt started for task #2
[10:50:12] WARNING in tasks: flaky_task: Simulated failure for task #1
[10:50:12] INFO in tasks: flaky_task: Retrying task #1 in 5 seconds
[10:50:12] INFO in tasks: flaky_task: Successfully completed task #2
[10:50:13] INFO in tasks: flaky_task: Attempt started for task #3
[10:50:15] WARNING in tasks: flaky_task: Simulated failure for task #3
[10:50:15] INFO in tasks: flaky_task: Retrying task #3 in 5 seconds
[10:50:17] INFO in tasks: flaky_task: Attempt started for task #1  <-- Retry
[10:50:19] INFO in tasks: flaky_task: Successfully completed task #1
```

This demonstrates how the retry system handles multiple tasks independently, each with its own retry schedule.

## Step 10: Understanding Error Handling Patterns

The tasks demonstrate two error handling patterns:

**Pattern 1: Retry on transient errors**

Used in `send_welcome_email` and `generate_monthly_report`:
```python
except Exception as exc:
    logger.error(f"Task failed: {exc}")
    raise self.retry(exc=exc, countdown=10)
```

This is appropriate for errors that might be temporary (network timeout, database deadlock). The task automatically retries.

**Pattern 2: Return structured error after max retries**

Used in `flaky_task`:
```python
except Exception as exc:
    if self.request.retries >= self.max_retries:
        return {
            "status": "failed",
            "error": str(exc),
            "retries": self.request.retries
        }
    raise self.retry(exc=exc, countdown=...)
```

This pattern retries on transient errors but returns a structured error response after exhausting retries, rather than leaving the task in FAILURE state.

**Which pattern to use?**

- **Retry and raise**: Use for critical tasks where permanent failure should be visible (state = FAILURE)
- **Retry and return error dict**: Use when you want to track attempts but still return structured data to the client

## Step 11: Observe Logging in Production Scenarios

The logging we added provides visibility into task execution. Let's examine what information is captured:

**For successful tasks:**
- Start time
- Key execution milestones
- Completion time
- Result summary

**For failed tasks:**
- Start time
- Error details
- Retry attempts and countdown
- Final status (success after retries or permanent failure)

**For timeout tasks:**
- Start time
- Timeout trigger (soft or hard)
- Graceful cleanup actions

This logging is crucial for production debugging. When a task fails at 3am, you need to know:
1. When did it start?
2. What error occurred?
3. Did it retry? How many times?
4. What was the final outcome?

All of this is now visible in your worker logs.

## Conclusion

In this lab, you transformed your basic Flask-Celery integration into a production-ready task queue system by adding four critical reliability features.

You implemented automatic retry logic with exponential backoff, which handles transient errors like network timeouts or database deadlocks without manual intervention. You configured timeout limits to prevent runaway tasks from consuming worker resources indefinitely. You added comprehensive logging that tracks every task lifecycle event, making debugging production failures straightforward. And you implemented structured error handling that returns meaningful failure messages to API clients instead of cryptic stack traces.

You created two demonstration tasks: a flaky task that randomly fails to show retry behavior, and a slow task that exceeds timeouts to show enforcement. You observed how Celery manages concurrent retry schedules, how exponential backoff spaces out retry attempts, and how tasks can gracefully handle timeouts before hard termination.

The key takeaway is that production task queues need more than just "fire and forget." They need resilience against failures, protection against runaway processes, visibility into execution, and clear communication of errors. With these features in place, your system can handle the messiness of production environments where external services fail, networks drop, and unexpected errors occur.
