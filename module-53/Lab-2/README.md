# Lab 2: Real-World Use Cases - Email and PDF Generation

In Lab 1, you built the foundation: a Flask application integrated with Celery using the Application Factory pattern. You verified the setup worked with a simple `test_task` that just printed "Pong from Background!" and returned. That was essential infrastructure work, but it didn't solve any real problems.

In this lab, we're implementing two of the most common bottlenecks in web applications: sending email notifications and generating PDF reports. These operations are slow for different reasons—emails suffer from network latency (waiting for SMTP servers to respond), while PDF generation is CPU-intensive (rendering complex documents). Both would make your API unacceptably slow if handled synchronously.

We'll build two endpoints: `POST /register` that creates a user and triggers a welcome email in the background, and `POST /reports/generate` that queues a PDF report generation task. You'll observe the dramatic difference between synchronous and asynchronous processing—HTTP responses returning in milliseconds while the actual work happens over 5-10 seconds in the background.

## Architecture Diagram

```mermaid
graph TB
    subgraph "Client (Postman via Load Balancer)"
        A[POST /register<br/>email: user@example.com]
        B[POST /reports/generate<br/>user_id: 123]
    end

    subgraph "Flask Application"
        C[/register endpoint<br/>Save user data]
        D[Queue email task<br/>send_welcome_email.delay()]
        E[/reports/generate endpoint]
        F[Queue PDF task<br/>generate_monthly_report.delay()]
    end

    subgraph "Redis (Docker)"
        G[(Broker<br/>Task Queue)]
    end

    subgraph "Celery Worker Process"
        H[Process Email Task<br/>5-second network delay]
        I[Process PDF Task<br/>10-second CPU work]
    end

    A -->|"1. Register user"| C
    C -->|"2. Trigger email task"| D
    D -->|"3. Queue in broker"| G
    C -->|"4. Return 201 Created (instant)"| A

    B -->|"5. Request PDF"| E
    E -->|"6. Trigger PDF task"| F
    F -->|"7. Queue in broker"| G
    E -->|"8. Return 202 Accepted (instant)"| B

    G -->|"9. Worker polls"| H
    G -->|"10. Worker polls"| I

    style A fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style B fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style C fill:#c8e6c9,stroke:#1b5e20,stroke-width:2px
    style D fill:#c8e6c9,stroke:#1b5e20,stroke-width:2px
    style E fill:#c8e6c9,stroke:#1b5e20,stroke-width:2px
    style F fill:#c8e6c9,stroke:#1b5e20,stroke-width:2px
    style G fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    style H fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    style I fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
```

**Key Concepts:**
- **Network I/O Tasks (Email)**: Slow because of external dependencies (SMTP servers, network latency)
- **CPU-Intensive Tasks (PDF)**: Slow because of computational complexity (rendering, formatting)
- **Fire and Forget**: API returns immediately, tasks process in background
- **Task IDs**: Client gets a reference to check status later (though we won't implement status checking in this lab)

## Objectives

By the end of this lab, you will:

1. Pull Lab 1 code from a GitHub repository to continue building on existing infrastructure
2. Implement two realistic background tasks: email sending and PDF generation
3. Create API endpoints that trigger these tasks asynchronously
4. Configure Flask to work with Poridhi's load balancer for external access
5. Use Postman to test the API and observe the performance difference between sync and async processing
6. Verify tasks execute in the background while the API remains responsive

## Prerequisites

- Completion of Module 53 Lab 1 concepts (Application Factory pattern, Flask-Celery integration)
- Docker and docker-compose installed
- Git installed
- Basic understanding of REST APIs and HTTP status codes

## What's New in Lab 2

In Lab 1, we had:
- Application Factory pattern with `make_celery()`
- Configuration in `config.py`
- Simple `test_task` that printed to terminal
- `/ping` endpoint that triggered the test task

In Lab 2, we're adding:
- **Real tasks**: `send_welcome_email` (network I/O simulation) and `generate_monthly_report` (CPU-intensive simulation)
- **Real endpoints**: `POST /register` and `POST /reports/generate`
- **Load balancer integration**: Configure Flask to work with Poridhi's external access
- **Postman testing**: Proper API testing with expected payloads
- **Performance observation**: Measure the difference between sync and async execution

The infrastructure (Application Factory, Redis, Celery worker) remains the same. We're just building real features on top of it.

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


## Step 1: Get Lab 1 Code

Since we're on a fresh VM, we need to pull the code from Lab 1. This gives us the complete Flask-Celery setup without rebuilding everything from scratch.

```bash
# Clone the repository
git clone https://github.com/poridhioss/Building-Systems-With-FastAPI.git
cd Building-Systems-With-FastAPI

# Checkout the Lab 2 branch
git checkout -b mod-53/lab-1 origin/mod-53/lab-1
cd flask-celery-app
```

Let's verify the project structure:

```bash
ls -la
```

You should see:
```
app/
├── __init__.py
├── routes.py
├── tasks.py
celery_utils.py
config.py
docker-compose.yml
requirements.txt
run.py
```

This is the same structure from Lab 1, with the Application Factory pattern already set up.

## Step 2: Set Up Python Environment

Create a virtual environment and install dependencies:

```bash
# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

The `requirements.txt` from Lab 1 already has everything we need:
- flask==3.0.0
- celery==5.3.4
- redis==5.0.1

## Step 3: Start Redis Container

The Lab 1 code includes a `docker-compose.yml` file that defines the Redis service. Start it:

```bash
docker compose up -d
```

Verify Redis is running:

```bash
docker ps
docker exec -it flask-celery-redis redis-cli ping
```

You should see `PONG`.

## Step 4: Update Tasks with Real-World Use Cases

Now we'll replace the simple `test_task` with two realistic tasks. Open `app/tasks.py` and replace its contents:

```python
from app import celery
import time

@celery.task
def send_welcome_email(user_email):
    """
    NEW IN LAB 2: Simulates sending a welcome email via SMTP.

    In production, this would use an email service (SendGrid, AWS SES, etc.)
    Network latency makes this slow (5 seconds to connect, authenticate, send).
    """
    print(f"[EMAIL TASK] Starting to send welcome email to {user_email}")

    # Simulate network I/O delay (connecting to SMTP server, sending email)
    time.sleep(5)

    print(f"[EMAIL TASK] Welcome email sent successfully to {user_email}")
    return f"Email sent to {user_email}"

@celery.task
def generate_monthly_report(user_id):
    """
    NEW IN LAB 2: Simulates generating a complex PDF report.

    In production, this would query databases, aggregate data, render charts,
    and compile a multi-page PDF document. CPU-intensive work takes 10 seconds.
    """
    print(f"[PDF TASK] Starting report generation for user {user_id}")

    # Simulate CPU-intensive processing (data aggregation, PDF rendering)
    time.sleep(10)

    report_filename = f"report_user_{user_id}_{int(time.time())}.pdf"
    print(f"[PDF TASK] Report generated: {report_filename}")

    return {
        "filename": report_filename,
        "user_id": user_id,
        "status": "completed"
    }
```

**What changed:**
- Removed `test_task` (from Lab 1)
- Added `send_welcome_email`: Simulates 5-second network latency
- Added `generate_monthly_report`: Simulates 10-second CPU work
- Both tasks print detailed logs so we can observe execution in the worker terminal
- Both tasks return meaningful results (email confirmation, PDF metadata)

## Step 5: Update Routes with New Endpoints

Now we'll replace the `/ping` endpoint with two realistic API routes. Open `app/routes.py` and replace its contents:

```python
from flask import Blueprint, jsonify, request

bp = Blueprint('routes', __name__)

@bp.route('/register', methods=['POST'])
def register():
    """
    NEW IN LAB 2: User registration endpoint that triggers welcome email.

    In production, this would validate data, hash passwords, save to database.
    Then trigger the email task asynchronously so the API returns immediately.
    """
    from app.tasks import send_welcome_email

    data = request.get_json()
    user_email = data.get('email')

    if not user_email:
        return jsonify({'error': 'Email is required'}), 400

    # In production: save user to database here
    # user = User(email=user_email)
    # db.session.add(user)
    # db.session.commit()

    # Trigger email task asynchronously
    task = send_welcome_email.delay(user_email)

    return jsonify({
        'message': 'User registered successfully',
        'email': user_email,
        'email_task_id': task.id
    }), 201

@bp.route('/reports/generate', methods=['POST'])
def generate_report():
    """
    NEW IN LAB 2: Report generation endpoint that triggers PDF task.

    Returns immediately with task ID. Client can use this ID to check
    status later (status checking will be implemented in a future module).
    """
    from app.tasks import generate_monthly_report

    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    # Trigger PDF generation task asynchronously
    task = generate_monthly_report.delay(user_id)

    return jsonify({
        'message': 'Report generation started',
        'task_id': task.id,
        'user_id': user_id
    }), 202
```

**What changed:**
- Removed `/ping` endpoint (from Lab 1)
- Added `POST /register`: Accepts email, queues welcome email task, returns 201 Created
- Added `POST /reports/generate`: Accepts user_id, queues PDF task, returns 202 Accepted
- Both endpoints validate input and return appropriate HTTP status codes
- Both endpoints return task IDs so clients could check status later (not implemented in this lab)

## Step 6: Configure Flask for Load Balancer Access

Since we're running on a Poridhi VM and want to test with Postman from outside the VM, we need to use Poridhi's load balancer. The load balancer provides a public URL that routes traffic to your VM.

The Flask app is already configured to listen on `0.0.0.0:5000` (see `run.py`), which means it accepts connections from any network interface. This is exactly what we need for the load balancer to reach it.

No code changes are needed—the Lab 1 setup already works with the load balancer. Just make sure you start Flask on port 5000 (which we will in Step 8).

## Step 7: Start the Celery Worker

Open a terminal and start the Celery worker:

```bash
cd ~/code/flask-celery-app
source .venv/bin/activate
celery -A app.celery worker --loglevel=info
```

You should see output confirming:
- Connected to Redis broker at `redis://localhost:6379/0`
- Result backend at `redis://localhost:6379/1`
- Registered tasks:
  - `app.tasks.send_welcome_email`
  - `app.tasks.generate_monthly_report`

**Important:** Keep this terminal open and running. This is your background worker process.

## Step 8: Start the Flask Application

Open a **second terminal**, navigate to the project directory, and start Flask:

```bash
cd ~/code/flask-celery-app
source .venv/bin/activate
python run.py
```

You should see:

```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://0.0.0.0:5000
```

The Flask API is now running and accessible through the load balancer.

**Important:** Keep this terminal open as well. You now have two terminals running:
- Terminal 1: Celery Worker
- Terminal 2: Flask Application

## Step 9: Get Your Load Balancer URL

Poridhi provides a load balancer URL for accessing services running on your VM. You need this URL to test with Postman.

**Finding your load balancer URL:**

1. In the Poridhi lab interface, look for the "Load Balancer" section
2. You should see a URL like: `http://<unique-id>.poridhi.io:5000`
3. Copy this URL—you'll use it in Postman

The load balancer routes traffic from the public internet to your VM's port 5000, where Flask is listening.

## Step 10: Test with Postman - Register Endpoint

Open Postman and test the `/register` endpoint.

**Request Configuration:**
- **Method**: POST
- **URL**: `http://<your-load-balancer-url>.poridhi.io:5000/register`
- **Headers**:
  - `Content-Type: application/json`
- **Body** (raw JSON):
```json
{
  "email": "alice@example.com"
}
```

Click **Send**.

**Expected Response (instant - within milliseconds):**

```json
{
  "message": "User registered successfully",
  "email": "alice@example.com",
  "email_task_id": "a1b2c3d4-5678-90ef-ghij-klmnopqrstuv"
}
```

**Status Code:** `201 Created`

Notice how the response came back **immediately**—your Flask app didn't wait for the email to send.

**Meanwhile, in the Celery Worker terminal:**

You'll see the task executing:

```
[2026-01-28 10:30:00,123: INFO/MainProcess] Task app.tasks.send_welcome_email[a1b2c3d4-...] received
[EMAIL TASK] Starting to send welcome email to alice@example.com
```

Then after about 5 seconds:

```
[EMAIL TASK] Welcome email sent successfully to alice@example.com
[2026-01-28 10:30:05,456: INFO/ForkPoolWorker-1] Task app.tasks.send_welcome_email[a1b2c3d4-...] succeeded in 5.002s: 'Email sent to alice@example.com'
```

The API returned in milliseconds, but the email task took 5 seconds in the background.

## Step 11: Test with Postman - Report Generation Endpoint

Now test the `/reports/generate` endpoint.

**Request Configuration:**
- **Method**: POST
- **URL**: `http://<your-load-balancer-url>.poridhi.io:5000/reports/generate`
- **Headers**:
  - `Content-Type: application/json`
- **Body** (raw JSON):
```json
{
  "user_id": 123
}
```

Click **Send**.

**Expected Response (instant):**

```json
{
  "message": "Report generation started",
  "task_id": "e5f6g7h8-1234-56ab-cdef-ghijklmnopqr",
  "user_id": 123
}
```

**Status Code:** `202 Accepted`

Again, the response returned **immediately**.

**Meanwhile, in the Celery Worker terminal:**

```
[2026-01-28 10:35:00,789: INFO/MainProcess] Task app.tasks.generate_monthly_report[e5f6g7h8-...] received
[PDF TASK] Starting report generation for user 123
```

Then after about 10 seconds:

```
[PDF TASK] Report generated: report_user_123_1738065310.pdf
[2026-01-28 10:35:10,012: INFO/ForkPoolWorker-1] Task app.tasks.generate_monthly_report[e5f6g7h8-...] succeeded in 10.001s: {'filename': 'report_user_123_1738065310.pdf', 'user_id': 123, 'status': 'completed'}
```

The API returned in milliseconds, but the PDF generation took 10 seconds in the background.

## Step 12: Observe Performance Difference

Let's quantify the performance improvement. We'll compare synchronous vs asynchronous execution.

**Synchronous Processing (the old way - NOT implemented):**

If we had implemented email sending synchronously (without Celery), the flow would be:

1. Client sends POST to `/register`
2. Flask receives request
3. Flask sends email (waits 5 seconds)
4. Flask returns response
5. **Total client wait time: ~5 seconds**

For the report endpoint, it would be **~10 seconds** of waiting.

**Asynchronous Processing (with Celery - what we built):**

Current flow:

1. Client sends POST to `/register`
2. Flask receives request
3. Flask queues email task in Redis (instant)
4. Flask returns response
5. **Total client wait time: ~50-100 milliseconds**

The email actually sends in the background over 5 seconds, but the client doesn't wait for it.

**Testing multiple requests:**

In Postman, send the `/register` request 3 times in rapid succession with different emails:

```json
{"email": "user1@example.com"}
{"email": "user2@example.com"}
{"email": "user3@example.com"}
```

All three requests will return `201 Created` **instantly** with different task IDs.

In the Worker terminal, you'll see all three email tasks executing. If you have concurrency=2 (default for a 2-core VM), two emails will process simultaneously, then the third will process after one finishes.

This demonstrates the power of asynchronous task processing: your API can handle hundreds of registration requests per second, even though each email takes 5 seconds to send. The bottleneck is moved from the API layer to the worker layer, where it can be scaled independently.

## Step 13: Verify Input Validation

Let's verify the endpoints handle invalid input correctly.

**Test 1: Missing email in /register**

- **Method**: POST
- **URL**: `http://<your-load-balancer-url>.poridhi.io:5000/register`
- **Headers**: `Content-Type: application/json`
- **Body**: `{}`

**Expected Response:**
```json
{
  "error": "Email is required"
}
```
**Status Code:** `400 Bad Request`

The API returned immediately without queuing any task. Check the worker terminal—no task was triggered.

**Test 2: Missing user_id in /reports/generate**

- **Method**: POST
- **URL**: `http://<your-load-balancer-url>.poridhi.io:5000/reports/generate`
- **Headers**: `Content-Type: application/json`
- **Body**: `{}`

**Expected Response:**
```json
{
  "error": "user_id is required"
}
```
**Status Code:** `400 Bad Request`

Again, no task was queued because the request was invalid.

## Understanding What We Built

Let's examine the complete flow for both use cases.

**Email Sending Flow:**

1. User submits registration via Postman: `POST /register` with email
2. Flask route handler receives request
3. Route validates email is present
4. Route calls `send_welcome_email.delay(user_email)`
5. Celery serializes task: `{"task": "app.tasks.send_welcome_email", "args": ["alice@example.com"]}`
6. Task pushed to Redis broker (database 0)
7. Flask returns `201 Created` with task ID (instant - under 100ms)
8. Celery worker polls Redis, retrieves task
9. Worker executes `send_welcome_email("alice@example.com")`
10. Worker sleeps 5 seconds (simulating SMTP interaction)
11. Worker logs "Email sent successfully"
12. Worker writes result to Redis backend (database 1)

**Total user wait time: ~50-100ms**
**Actual task execution time: 5 seconds (happens in background)**

**PDF Generation Flow:**

1. User requests report via Postman: `POST /reports/generate` with user_id
2. Flask route handler receives request
3. Route validates user_id is present
4. Route calls `generate_monthly_report.delay(user_id)`
5. Celery serializes task
6. Task pushed to Redis broker
7. Flask returns `202 Accepted` with task ID (instant)
8. Worker polls Redis, retrieves task
9. Worker executes `generate_monthly_report(123)`
10. Worker sleeps 10 seconds (simulating PDF rendering)
11. Worker logs report filename
12. Worker writes result to Redis backend

**Total user wait time: ~50-100ms**
**Actual task execution time: 10 seconds (happens in background)**

**Key Observations:**

- **Decoupling**: The API layer is completely decoupled from the processing layer
- **Scalability**: You can scale workers independently from Flask instances
- **Responsiveness**: Users get immediate feedback even for slow operations
- **Reliability**: If a worker crashes, tasks remain in Redis and can be retried
- **Resource Utilization**: Long-running tasks don't block precious API worker threads

**Why This Matters:**

In a synchronous system, if your API server can handle 100 concurrent requests, and each registration takes 5 seconds to send an email, you can only process 20 registrations per second (100 / 5 = 20). Once all 100 threads are blocked waiting for emails, new requests start failing.

With async task processing, the same API server can handle 100 concurrent requests, and each registration returns in 50ms. That's 2,000 registrations per second (100 / 0.05 = 2,000)—a 100x improvement. The email sending is handled by workers, which can be scaled independently based on the email queue size.

## Conclusion

In this lab, you transformed the basic Flask-Celery infrastructure from Lab 1 into a realistic application with two common use cases: email notifications and PDF report generation. You implemented endpoints that handle these expensive operations asynchronously, allowing your API to remain responsive even while processing tasks that take 5-10 seconds.

The key achievement was observing the dramatic performance difference between synchronous and asynchronous processing. Your API endpoints returned in milliseconds while the actual work happened in the background over several seconds. This pattern enables web applications to scale to thousands of concurrent users without blocking on slow operations.

You also integrated your application with Poridhi's load balancer, making it accessible via a public URL for testing with Postman. This simulates a real production environment where your API is exposed to external clients.

However, there's still a limitation: once you trigger a task and get a task ID back, you have no way to check if it's done or retrieve the result through the API. The client receives `task_id: "abc-123"` but can't ask "Is it done? What was the result?" through an HTTP endpoint.

In Module 54, you'll extend this system with status-checking endpoints. Clients will be able to poll for task completion and retrieve results through REST APIs. You'll also implement task failure handling, retry logic, and more sophisticated task workflows. This will complete the full lifecycle: submit task → get task ID → check status → retrieve result.
