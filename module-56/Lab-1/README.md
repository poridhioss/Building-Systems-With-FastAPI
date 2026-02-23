# Lab 1: Local Tracing Setup with Grafana Tempo

## Introduction

This lab teaches you to implement distributed tracing for a Flask-Celery application using OpenTelemetry and Grafana Tempo. Building on Module 55's task-level monitoring with Flower, you will deploy an observability stack, instrument your application to generate trace spans, and visualize end-to-end request flows in Grafana. By the end of this lab, you will have full-stack visibility that shows the complete journey of a request from the Flask API through Redis to the Celery worker, with timing breakdowns for every operation.

## Architecture Diagram

The tracing system adds two new components—Grafana Tempo and Grafana—alongside the existing Flask-Celery-Redis infrastructure:

```
┌──────────────────────────────────────────────────────────────────┐
│                         Client (curl)                            │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         │ HTTP POST /register
                         │ (Request with Trace ID)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Flask Application (Port 5000)                       │
│              Instrumented with OpenTelemetry                     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Root Span: POST /register                             │    │
│  │  ├─ Span: Validate input                               │    │
│  │  ├─ Span: Redis RPUSH (queue task)                     │    │
│  │  └─ Span: Return HTTP 201                              │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Sends spans via OTLP HTTP ──────────────────────┐              │
└──────────────────────────────────────────────────┼──────────────┘
                         │                         │
                         │ Queue task              │
                         ▼                         │
┌─────────────────────────────────────────────────┼──────────────┐
│              Redis (Port 6379)                   │              │
│              Broker + Result Backend             │              │
└──────────────────────┬───────────────────────────┼──────────────┘
                       │                           │
                       │ Poll for tasks            │
                       ▼                           │
┌─────────────────────────────────────────────────┼──────────────┐
│         Celery Worker (Background Process)       │              │
│         Instrumented with OpenTelemetry          │              │
│                                                  │              │
│  ┌────────────────────────────────────────────┐ │              │
│  │  Child Span: send_welcome_email            │ │              │
│  │  ├─ Span: Simulate network delay (5s)     │ │              │
│  │  └─ Span: Return result                   │ │              │
│  └────────────────────────────────────────────┘ │              │
│                                                  │              │
│  Sends spans via OTLP HTTP ──────────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                                                  │
                                                  │ OTLP HTTP Export
                                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│              Grafana Tempo (Port 4318)                           │
│              Trace Storage Backend                               │
│                                                                  │
│  Stores traces with:                                             │
│  - Trace ID: abc-123                                             │
│  - All spans from Flask and Celery                               │
│  - Span relationships (parent-child)                             │
│  - Span attributes (user_id, email, etc.)                        │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         │ Query traces via HTTP API
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Grafana (Port 3000)                                 │
│              Trace Visualization UI                              │
│                                                                  │
│  Displays:                                                       │
│  - Complete trace timeline (Flask → Celery)                      │
│  - Span duration breakdown                                       │
│  - Span attributes and metadata                                  │
│  - Service dependency graph                                      │
└─────────────────────────────────────────────────────────────────┘
```

**Key Flow:**

1. **Client** sends an HTTP request to Flask
2. **Flask** creates a root span with a new Trace ID, processes the request, queues a task, and sends spans to Tempo
3. **Celery Worker** picks up the task, creates a child span with the same Trace ID, executes it, and sends spans to Tempo
4. **Tempo** stores all spans and links them by Trace ID
5. **Grafana** queries Tempo and visualizes the complete trace timeline

> **Note:** This diagram shows the **final system** after completing all chapters. In early chapters, Flask and Celery traces will appear as separate traces with different Trace IDs. Trace context propagation (linking them into a single trace) is explained in Chapter 7 and implemented in Chapter 8.

## Learning Objectives

By the end of this lab, you will be able to:

1. Deploy Grafana and Tempo locally using Docker Compose as a trace collection backend
2. Install and configure OpenTelemetry SDK with OTLP HTTP exporter for Python applications
3. Auto-instrument Flask, Redis, and Celery to capture traces without modifying business logic
4. Generate and visualize distributed traces in Grafana showing cross-service request flows
5. Add custom spans to instrument specific business logic operations
6. Enrich spans with custom attributes for targeted filtering and debugging
7. Trace request propagation from Flask to Celery across process boundaries
8. Search and filter traces using TraceQL to isolate specific requests or errors
9. Identify performance bottlenecks by analyzing span durations in the trace timeline

**Prerequisites:** Completion of Module 54 Lab 1 with a working Flask-Celery application including retry logic, timeout enforcement, and error handling. Redis must be configured as both broker and result backend. Tasks `send_welcome_email`, `generate_monthly_report`, `flaky_task`, and `slow_task` must be defined.

## Prologue: The Challenge

You join the platform engineering team responsible for a Flask-Celery application that processes thousands of background tasks daily: welcome emails, report generation, data processing, and notification delivery. Module 54 gave the system retry logic, timeout enforcement, and error handling. Module 55 added Flower for real-time task monitoring. The team can now see which tasks are running, which failed, and what the exception tracebacks look like.

On Monday morning, the support team reports that user registration feels slow. The Flower dashboard shows tasks completing successfully, but users complain that the entire registration flow takes too long. Nobody can determine whether the delay originates in the Flask API, the Redis broker, or the Celery worker. Flower shows that `send_welcome_email` takes 5 seconds, but the total user-facing latency is 8 seconds. Where are the other 3 seconds?

On Tuesday, a production incident occurs. An external SMTP service degrades, causing email tasks to slow from 3 seconds to 30 seconds. Flower shows tasks are succeeding, but the latency spike cascades into queue backlogs. Without visibility into what happens inside each task—which step takes how long—the team cannot determine the root cause.

On Wednesday, the architecture grows to include multiple services. A new microservice processes webhook callbacks, and tasks now flow across three different processes. Correlating log entries across services requires matching timestamps manually, a process that takes 20 minutes during an incident. By then, hundreds of customers are affected.

Your task is to implement distributed tracing that answers these questions instantly: How long does the complete request flow take? Where is the time spent? How do requests propagate across services? Which operation is the bottleneck? You will deploy Grafana Tempo, instrument the application with OpenTelemetry, and visualize end-to-end traces that provide this visibility.

## Environment Setup

This lab extends the Module 55 project on a fresh virtual machine. You will set up the Flask-Celery infrastructure and then add OpenTelemetry instrumentation with Grafana Tempo.

Check Python version:

```bash
python --version
```

If Python 3.12 is not available, install it:

```bash
sudo apt update
sudo apt install python3.12-venv -y
alias python=python3.12
source ~/.bashrc
```

Clone the project codebase:

```bash
git clone https://github.com/poridhioss/Building-Systems-With-FastAPI.git
cd Building-Systems-With-FastAPI/
git checkout -b mod-54/lab-1 origin/mod-54/lab-1
```

Create and activate a virtual environment:

```bash
cd flask-celery-app
python -m venv .venv
source .venv/bin/activate
```

Install the base dependencies:

```bash
pip install -r requirements.txt
```

Verify Redis is running via Docker Compose and confirm the Flask application and Celery worker are functional before proceeding. This lab assumes the Module 55 infrastructure is operational.

---

## Chapter 1: Understanding Distributed Tracing

Flower provides visibility into Celery's internal operations—task states, worker health, queue lengths. However, it cannot show the complete journey of a user request across multiple services. Distributed tracing fills this gap by capturing detailed timing information for every operation in the request lifecycle.

### 1.1 The Visibility Gap

Consider the following scenario. A user calls `POST /register`, which queues a `send_welcome_email` task. Traditional logging produces four separate entries:

```
[Flask Log]  10:30:15 - Received POST /register
[Flask Log]  10:30:15 - Queued task abc-123
[Celery Log] 10:30:16 - Task abc-123 started
[Celery Log] 10:30:21 - Task abc-123 succeeded
```

These log entries are disconnected. To determine total request duration, you must manually correlate timestamps across log files. This manual correlation does not reveal:

- How long Flask spent processing before queuing the task
- How long the task waited in the Redis queue
- What operations happened inside the task and how long each took

Distributed tracing solves this by producing a unified timeline:

#####CHANGE_NEEDED: celery task should be inside redis span. maybe
```
Trace ID: abc-123
├─ Span: POST /register [Flask API] ────────── 50ms
│  ├─ Span: Validate email ───── 5ms
│  ├─ Span: Queue task to Redis ─ 10ms
│  └─ Span: Return response ───── 5ms
└─ Span: send_welcome_email [Celery Worker] ─── 5000ms
   ├─ Span: Connect to SMTP ───── 1000ms
   ├─ Span: Send email ────────── 3000ms
   └─ Span: Update database ───── 1000ms
```

This timeline shows that the entire request took 5050ms, Flask responded in 50ms, the task waited less than 1ms in the queue (no backlog), and 3000ms of task execution was spent sending the email—a potential optimization target.

### 1.2 Core Terminology

Five concepts form the foundation of distributed tracing:

**Trace** — A trace represents the complete journey of a single **user request** through the system. It has a unique Trace ID that ties all related operations together. One user request = one Trace ID. A new Trace ID is generated every time a client sends a request to the Flask API. If three users register in the same minute, three separate Trace IDs are generated:

```
User Alice registers  → Trace ID: abc-111
User Bob registers    → Trace ID: abc-222
User Carol registers  → Trace ID: abc-333
```

Each trace contains multiple spans from multiple services, but they all share the same Trace ID.

**Span** — A span represents a single operation within a trace. Each span has a name (e.g., "POST /register", "send_email"), a start time, a duration, a parent span (except for the root span), and attributes (key-value metadata like `user_id` or `http.method`). Spans nest to show parent-child relationships:

```
Root Span: HTTP Request
├─ Child Span: Validate input
├─ Child Span: Database query
└─ Child Span: Queue background task
```

**Service** — A service is a running process that generates spans. In this lab, there are two services: `flask-api` (the Flask application process) and `celery-worker` (the Celery worker process). A service is NOT tied to a single Trace ID. Instead, a service participates in many different traces over time:

```
flask-api service participates in:
  - Trace abc-111 (Alice's request)
  - Trace abc-222 (Bob's request)
  - Trace abc-333 (Carol's request)

celery-worker service also participates in:
  - Trace abc-111 (Alice's email task)
  - Trace abc-222 (Bob's email task)
  - Trace abc-333 (Carol's email task)
```

The key relationship: **One Trace ID spans multiple services. One service generates spans for many different Trace IDs.**

**OpenTelemetry (OTel)** — The industry-standard framework for instrumenting applications to generate traces, metrics, and logs. It provides SDKs for multiple languages (Python, Go, Java, Node.js), auto-instrumentation for popular frameworks (Flask, Django, FastAPI), and exporters to send data to various backends (Tempo, Jaeger, Zipkin, Datadog).

**Grafana Tempo** — A distributed tracing backend that stores traces efficiently. It integrates with Grafana for visualization and supports the OTLP (OpenTelemetry Protocol) for receiving trace data over HTTP or gRPC.

### 1.3 How a Trace ID Travels Across Services

The word "distributed" in distributed tracing means a single Trace ID follows a request as it moves from one process to another. This requires **trace context propagation** — the mechanism that passes the Trace ID from Flask to Celery.

Here is the complete lifecycle of a Trace ID for a single registration request:

```
1. Client sends POST /register
   └─ No Trace ID yet

2. Flask receives the request
   └─ OpenTelemetry generates: Trace ID = abc-123, Span ID = span-1
   └─ Creates Root Span: "POST /register" (Trace ID: abc-123)

3. Flask queues a Celery task via Redis
   └─ OpenTelemetry INJECTS trace context into the task message:
      Task payload: {
        "task": "send_welcome_email",
        "args": ["alice@example.com"],
        "headers": {
          "traceparent": "00-abc123-span1-01"  ← Trace ID embedded here
        }
      }
   └─ Flask sends its spans to Tempo

4. Celery worker picks up the task from Redis
   └─ OpenTelemetry EXTRACTS trace context from the task headers:
      Found: Trace ID = abc-123, Parent Span ID = span-1
   └─ Creates Child Span: "send_welcome_email" with:
      - Same Trace ID: abc-123
      - Parent: span-1 (the Flask root span)
      - New Span ID: span-2

5. Celery worker completes the task
   └─ Celery sends its spans to Tempo

6. Tempo receives spans from both Flask and Celery
   └─ Both have Trace ID = abc-123
   └─ Tempo links them into a single trace

7. Grafana queries Tempo for Trace ID abc-123
   └─ Shows unified timeline:
      ├─ POST /register [flask-api] ───── 130ms
      └─ send_welcome_email [celery-worker] ───── 5000ms
```

**Step 3 is the critical step.** If the trace context is NOT injected into the task message, the Celery worker has no way to know which Trace ID it belongs to. It creates a **new, unrelated Trace ID** instead. This results in two disconnected traces in Grafana — one for Flask, one for Celery — and the "distributed" in distributed tracing is broken.

**Without propagation (broken):**

```
Trace ID: abc-123 [flask-api only]
└─ POST /register ────── 130ms

Trace ID: xyz-789 [celery-worker only]  ← Different Trace ID!
└─ send_welcome_email ────── 5000ms
```

**With propagation (working correctly):**

```
Trace ID: abc-123 [both services]
├─ POST /register [flask-api] ────── 130ms
└─ send_welcome_email [celery-worker] ────── 5000ms  (child of above)
```

This lab implements trace context propagation in Chapter 7 to ensure Flask and Celery spans are properly linked.

### 1.4 Prediction Exercise

Before building the tracing system, consider this scenario:

A `POST /register` request arrives at Flask. Flask validates the input (5ms), queues a Celery task (10ms), and returns a response (5ms). The Celery worker picks up the task and executes `send_welcome_email`, which connects to SMTP (1000ms), sends the email (3000ms), and updates the database (500ms).

**Question:** How many spans will this request generate? What will the parent-child hierarchy look like? Write down your prediction.

<details>
<summary>Reveal Answer</summary>

The request generates at least 7 spans:

1. Root span: `POST /register` (parent of all Flask spans)
2. Child span: `Validate input` (parent: root)
3. Child span: `Queue task to Redis` (parent: root)
4. Child span: `Return response` (parent: root)
5. Child span: `send_welcome_email` (parent: root, different service)
6. Grandchild span: `SMTP connect` (parent: send_welcome_email)
7. Grandchild span: `Send email` (parent: send_welcome_email)
8. Grandchild span: `Update database` (parent: send_welcome_email)

Auto-instrumentation adds additional spans for Redis operations (RPUSH for queuing), making the total higher. All spans share the same Trace ID despite spanning two processes (Flask and Celery).

</details>

### 1.5 Checkpoint

Verify your understanding before proceeding:

- [ ] A trace represents one complete request; a span represents one operation within that request
- [ ] A Trace ID is generated per request, not per service — one Trace ID spans multiple services
- [ ] A service (like flask-api) participates in many different Trace IDs over time
- [ ] Spans form parent-child hierarchies that show how operations nest
- [ ] Trace context propagation passes the Trace ID from Flask to Celery via task message headers
- [ ] Without propagation, Flask and Celery create separate disconnected traces
- [ ] OpenTelemetry generates trace data; Tempo stores it; Grafana visualizes it

---

## Chapter 2: Deploying the Observability Stack

The tracing infrastructure requires two new services: Grafana Tempo to store traces, and Grafana to visualize them. Both run as Docker containers alongside the existing Redis service.

### 2.1 Updating Docker Compose

Update `docker-compose.yml` to include Tempo and Grafana:

```yaml
version: '3.8'

services:
  # Existing Redis service
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

  # Grafana Tempo - Trace storage backend
  tempo:
    image: grafana/tempo:2.3.1
    container_name: tempo
    command: [ "-config.file=/etc/tempo.yaml" ]
    volumes:
      - ./tempo-config.yaml:/etc/tempo.yaml
      - tempo-data:/tmp/tempo
    ports:
      - "4318:4318"  # OTLP HTTP
      - "3200:3200"  # Tempo HTTP API

  # Grafana - Visualization UI
  grafana:
    image: grafana/grafana:10.2.3
    container_name: grafana
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
      - GF_AUTH_DISABLE_LOGIN_FORM=true
    volumes:
      - ./grafana-datasources.yaml:/etc/grafana/provisioning/datasources/datasources.yaml
    ports:
      - "3001:3000"  # using 3001 instead of 3000 because poridhi vm reserved port 3000 for other purpose
    depends_on:
      - tempo

volumes:
  tempo-data:
```

The Tempo service listens on port 4318 for OTLP HTTP trace data and port 3200 for its HTTP API. Grafana connects to Tempo via the internal Docker network. Anonymous authentication is enabled for development—production deployments require proper authentication.

### 2.2 Configuring Tempo

Create the Tempo configuration file `tempo-config.yaml`:

```yaml
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        http:
          endpoint: 0.0.0.0:4318

storage:
  trace:
    backend: local
    local:
      path: /tmp/tempo/blocks
    wal:
      path: /tmp/tempo/wal
```

This configuration sets up:

- **OTLP HTTP receiver** on port 4318 to accept traces from the application
- **Local storage** for trace data (suitable for development; use S3/GCS in production)
- **Write-Ahead Log (WAL)** for durability during restarts

### 2.3 Configuring the Grafana Datasource

Create the Grafana datasource configuration `grafana-datasources.yaml`:

```yaml
apiVersion: 1

datasources:
  - name: Tempo
    type: tempo
    access: proxy
    url: http://tempo:3200
    uid: tempo
    editable: true
    isDefault: true
```

This file auto-provisions Tempo as the default tracing datasource when Grafana starts.

### 2.4 Starting the Stack

Start all containers:

```bash
docker compose up -d
```

Verify all three containers are running:

```bash
docker ps
```

![alt text](image.png)

Expected output shows three containers: `flask-celery-redis`, `tempo`, and `grafana`.

### 2.5 Accessing Grafana using Poridhi's Load Balancer

To access Grafana through Poridhi's Load Balancer, first find your wt0 IP address by running `ifconfig` and looking for the `wt0` interface. Note the IP address (something like `100.125.246.186`).


![alt text](image-1.png)

**Create Load Balancer:**

Go to Poridhi's Load Balancer dashboard, create a new Load Balancer, use your wt0 IP address with port 3000, and click "Create".

![alt text](image-2.png)

You will receive a public URL like `https://lb-xxxxx.poridhi.io` that provides access to Grafana from anywhere.

Open the URL in a browser. The Grafana homepage loads without requiring login due to the anonymous authentication configuration.

![alt text](image-3.png)

Click **Explore** (compass icon in the left sidebar), then select **Tempo** as the datasource. No traces appear yet because the application has not been instrumented.

![alt text](image-4.png)

### 2.6 Checkpoint

Before proceeding, verify:

- [ ] Three Docker containers are running: `flask-celery-redis`, `tempo`, `grafana`
- [ ] Grafana is accessible via the Load Balancer URL
- [ ] Tempo appears as a datasource in Grafana Explore

---

## Chapter 3: Configuring OpenTelemetry

With the tracing backend running, the next step is configuring the application to generate and export trace data. This requires installing the OpenTelemetry SDK and creating a centralized configuration module.

### 3.1 Installing OpenTelemetry Packages

Activate the virtual environment and install the required packages:

```bash
source .venv/bin/activate
```

```bash
pip install \
  setuptools==68.0.0 \
  opentelemetry-api==1.22.0 \
  opentelemetry-sdk==1.22.0 \
  opentelemetry-instrumentation==0.43b0 \
  opentelemetry-distro==0.43b0 \
  opentelemetry-exporter-otlp==1.22.0 \
  opentelemetry-instrumentation-flask==0.43b0 \
  opentelemetry-instrumentation-redis==0.43b0 \
  opentelemetry-instrumentation-celery==0.43b0
```

The `setuptools` package at version 68.0.0 provides `pkg_resources`, which OpenTelemetry packages require for dependency management. Newer versions of setuptools (70+) changed the `pkg_resources` interface, causing compatibility issues. The `opentelemetry-api`, `opentelemetry-sdk`, and `opentelemetry-instrumentation` packages must be installed explicitly at matching versions. Without pinning these, pip may resolve transitive dependencies to incompatible versions, causing `ImportError` at startup.

Each package serves a specific role:

| Package | Purpose |
|---------|---------|
| `setuptools==68.0.0` | Provides `pkg_resources` required by OpenTelemetry (newer versions incompatible) |
| `opentelemetry-api` | Core tracing API interfaces |
| `opentelemetry-sdk` | SDK implementation of the tracing API |
| `opentelemetry-instrumentation` | Base classes for all instrumentors (`BaseInstrumentor`) |
| `opentelemetry-distro` | Meta-package for auto-instrumentation tools |
| `opentelemetry-exporter-otlp` | OTLP exporter for sending traces to Tempo |
| `opentelemetry-instrumentation-flask` | Auto-instruments Flask HTTP requests |
| `opentelemetry-instrumentation-redis` | Auto-instruments Redis operations (LPUSH, RPUSH, GET, SET) |
| `opentelemetry-instrumentation-celery` | Auto-instruments Celery task execution |

Update `requirements.txt` to include the new dependencies:

```bash
cat >> requirements.txt << EOF
setuptools==68.0.0
opentelemetry-api==1.22.0
opentelemetry-sdk==1.22.0
opentelemetry-instrumentation==0.43b0
opentelemetry-distro==0.43b0
opentelemetry-exporter-otlp==1.22.0
opentelemetry-instrumentation-flask==0.43b0
opentelemetry-instrumentation-redis==0.43b0
opentelemetry-instrumentation-celery==0.43b0
EOF
```

### 3.2 Creating the OpenTelemetry Configuration Module

Create a new file `otel_config.py` to centralize tracing configuration:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME


_configured = False

def configure_opentelemetry(service_name: str):
    global _configured

    # Prevent double-configuration in the same process
    if _configured:
        print(f"OpenTelemetry already configured, skipping configuration for: {service_name}")
        return

    # Create a resource identifying this service in traces
    resource = Resource(attributes={
        SERVICE_NAME: service_name
    })

    # Create a tracer provider with the resource
    provider = TracerProvider(resource=resource)

    # Configure OTLP HTTP exporter pointing to Tempo
    otlp_exporter = OTLPSpanExporter(
        endpoint="http://localhost:4318/v1/traces",
        timeout=10
    )

    # Batch spans before sending for efficiency
    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)

    # Set as the global tracer provider
    trace.set_tracer_provider(provider)

    _configured = True
    print(f"OpenTelemetry configured for service: {service_name}")
    print(f"Exporting traces to: http://localhost:4318/v1/traces")
```

The `_configured` guard prevents double-configuration. This is critical because when `worker.py` imports the Flask app, the app module would otherwise try to reconfigure OpenTelemetry with a different service name, overriding or conflicting with the worker's configuration.

Four components work together in this configuration:

- **Resource** — Metadata identifying the service generating traces (name, version, environment)
- **TracerProvider** — Factory that creates tracers for generating spans
- **OTLPSpanExporter** — Sends spans to Tempo via HTTP
- **BatchSpanProcessor** — Batches spans before export, reducing network overhead compared to sending each span individually

### 3.3 Prediction Exercise

The configuration uses `BatchSpanProcessor` rather than sending each span immediately.

**Question:** What would happen if the application sent every span individually to Tempo instead of batching? What trade-offs does batching introduce?

<details>
<summary>Reveal Answer</summary>

Without batching, every span generates an HTTP request to Tempo. In a high-throughput application processing hundreds of requests per second, this could produce thousands of HTTP calls per second, overwhelming both the application and the tracing backend with network overhead.

Batching collects spans over a time window (default 5 seconds) or until a batch size threshold is reached, then sends them in a single HTTP request. The trade-off: if the application crashes before a batch is exported, those spans are lost. For development this is acceptable. In production, configure the batch size and export interval based on throughput and durability requirements.

</details>

### 3.4 Checkpoint

Verify your understanding:

- [ ] Nine packages are installed with pinned versions: setuptools, OpenTelemetry api/sdk/instrumentation base, distro, OTLP exporter, Flask/Redis/Celery instrumentors
- [ ] The `otel_config.py` module creates a TracerProvider with a service name Resource
- [ ] BatchSpanProcessor batches spans before sending to reduce network overhead
- [ ] The OTLP exporter targets `http://localhost:4318/v1/traces` (Tempo's HTTP endpoint)

---

## Chapter 4: Instrumenting Flask and Celery

OpenTelemetry's auto-instrumentation creates spans automatically for Flask HTTP requests, Redis operations, and Celery task executions. The key design principle is: **configure OpenTelemetry in the entry point files (`run.py` and `worker.py`), NOT inside the app module**. This ensures each process gets the correct service name.

### 4.1 Updating the Flask Application Module

Update `app/__init__.py` to add instrumentors. **Do NOT call `configure_opentelemetry` here** — that will be done in the entry points:

```python
from flask import Flask
from celery_utils import make_celery
from config import Config
import logging

from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor


logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Auto-instrument Flask: creates spans for all HTTP requests
    FlaskInstrumentor().instrument_app(app)

    # Auto-instrument Redis: creates spans for all Redis operations
    RedisInstrumentor().instrument()

    # Register blueprints
    from app.routes import bp
    app.register_blueprint(bp)

    return app

app = create_app()
celery = make_celery(app)

from app import tasks
```

**Why no `configure_opentelemetry` here?** Because this module is imported by BOTH `run.py` (Flask process) and `worker.py` (Celery process). If `configure_opentelemetry(service_name="flask-api")` were called here, the worker process would also get `flask-api` as its service name — hiding the Celery service in Grafana. By keeping this module free of OpenTelemetry configuration, each entry point controls its own service name.

`FlaskInstrumentor` automatically creates a span for every HTTP request, capturing method, path, status code, and duration. `RedisInstrumentor` creates spans for Redis operations showing which commands executed and their latency. These instrumentors use whatever TracerProvider was set before the import — which is why the entry point must configure OpenTelemetry first.

### 4.2 Creating the Flask Entry Point

Update `run.py` to configure OpenTelemetry BEFORE importing the app:

```python
from otel_config import configure_opentelemetry

# Configure OpenTelemetry FIRST, before any app imports
configure_opentelemetry(service_name="flask-api")

from app import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
```

**Critical: The call to `configure_opentelemetry` MUST come before `from app import app`.** When Python executes `from app import app`, it runs all module-level code in `app/__init__.py`, including `FlaskInstrumentor().instrument_app(app)`. The instrumentor attaches to whatever TracerProvider is currently set. If no provider is set yet, the instrumentor uses a no-op provider and **Flask spans are silently discarded** — this is the most common reason for missing Flask traces in Grafana.

**Note:** `debug=False` is used because Flask's debug reloader spawns a child process that can interfere with OpenTelemetry initialization. For development debugging, use print statements or logging instead.

### 4.3 Creating the Celery Worker Entry Point

**Important:** You must create a separate `worker.py` file to properly instrument the Celery worker with the correct service name. Using `celery -A app.celery worker` will use the Flask app's configuration and show the wrong service name.

Create a new file `worker.py` to run the Celery worker with OpenTelemetry:

```python
from otel_config import configure_opentelemetry

# Step 1: Configure OpenTelemetry for the Celery worker service FIRST
configure_opentelemetry(service_name="celery-worker")

# Step 2: Import celery instance (this triggers create_app() in app/__init__.py)
from app import celery

# Step 3: Instrument Celery AFTER the celery app exists
# CeleryInstrumentor hooks into Celery signals (task_prerun, task_postrun, etc.)
# These signals must be connected after the celery app is imported.
from opentelemetry.instrumentation.celery import CeleryInstrumentor
CeleryInstrumentor().instrument()

if __name__ == '__main__':
    # worker_main() starts the worker directly without CLI argument parsing
    celery.worker_main([
        'worker',
        '--loglevel=info'
    ])
```

`CeleryInstrumentor` creates spans when tasks execute, capturing task name, arguments, duration, and result status.

**Critical ordering:** `CeleryInstrumentor().instrument()` MUST be called AFTER `from app import celery`. The instrumentor hooks into Celery's signal system (`task_prerun`, `task_postrun`, `before_task_publish`, etc.). If called before the celery app is imported, the signals are not connected and **task execution spans will not be generated** — you will only see Redis operation spans from the worker.

**Why `worker_main()` instead of `start()`?** The `celery.start()` method parses command-line arguments and would interpret `worker.py` as a Celery subcommand, causing a "No such command 'worker.py'" error. `worker_main()` starts the worker process directly.

### 4.4 Understanding the Import Order

The import order is critical for correct service naming. Here is what happens in each process:

**Flask process (`python run.py`):**

```
1. configure_opentelemetry("flask-api")  → Sets TracerProvider with flask-api
2. from app import app                   → Triggers create_app()
3.   FlaskInstrumentor().instrument_app() → Attaches to flask-api TracerProvider ✓
4.   RedisInstrumentor().instrument()     → Attaches to flask-api TracerProvider ✓
5. app.run()                              → Serves requests, spans go to flask-api ✓
```

**Celery process (`python worker.py`):**

```
1. configure_opentelemetry("celery-worker") → Sets TracerProvider with celery-worker
2. from app import celery                    → Triggers create_app()
3.   FlaskInstrumentor().instrument_app()    → Attaches to celery-worker provider (harmless)
4.   RedisInstrumentor().instrument()        → Attaches to celery-worker provider ✓
5. CeleryInstrumentor().instrument()         → Hooks into Celery signals ✓
6. celery.worker_main()                      → Processes tasks, spans go to celery-worker ✓
```

**Why CeleryInstrumentor must come AFTER the import:** The instrumentor connects to Celery's task signals (`task_prerun`, `task_postrun`, etc.) to create spans around task execution. If called before the celery app exists, the signals are never connected and task execution spans (like `run/app.tasks.send_welcome_email`) are silently lost — you would only see Redis command spans (PUBLISH, LLEN, SADD) from the worker's internal operations.

If `configure_opentelemetry` were called inside `create_app()` instead, the worker process would set the TracerProvider to `flask-api` before `worker.py` could set it to `celery-worker`, and all worker spans would be incorrectly labeled.

### 4.5 Prediction Exercise

Two different service names are configured: `flask-api` for the Flask application and `celery-worker` for the Celery worker.

**Question:** Why use separate service names instead of a single name for the entire application? What would happen in Grafana if both services used the same name?

<details>
<summary>Reveal Answer</summary>

Separate service names allow Grafana to distinguish which process generated each span. In the trace timeline, spans from `flask-api` and `celery-worker` appear in different colors, making it visually clear which service handled each operation. If both used the same name, all spans would appear as a single service, losing the ability to identify cross-service transitions and making it difficult to determine whether latency originates in the API layer or the worker layer.

</details>

### 4.6 Checkpoint

Verify your instrumentation:

- [ ] `app/__init__.py` contains `FlaskInstrumentor` and `RedisInstrumentor` but does NOT call `configure_opentelemetry`
- [ ] `run.py` calls `configure_opentelemetry(service_name="flask-api")` BEFORE `from app import app`
- [ ] `worker.py` calls `configure_opentelemetry(service_name="celery-worker")` BEFORE `from app import celery`
- [ ] `worker.py` calls `CeleryInstrumentor().instrument()` AFTER `from app import celery` (not before)
- [ ] Flask and Celery use different service names (`flask-api` and `celery-worker`)
- [ ] The worker is started with `python worker.py`, not `celery -A app.celery worker`
- [ ] Auto-instrumentation creates spans without modifying business logic code

---

## Chapter 5: Generating and Visualizing Traces

With instrumentation in place, start the application and generate traces to verify the tracing pipeline works end to end.

### 5.1 Starting the Instrumented Application

Open four terminals.

![alt text](images/archi-diagrams/mod-56_active-terminals.drawio.svg)

**Terminal 1 — Docker containers (already running):**

```bash
docker compose up -d
docker ps
```

**Terminal 2 — Flask application:**

```bash
source .venv/bin/activate
python run.py
```

The output MUST include the OpenTelemetry initialization message:

![alt text](image-9.png)

**If you do NOT see "OpenTelemetry configured for service: flask-api" in this terminal, Flask traces will NOT appear in Grafana.** Go back to Chapter 4.2 and verify that `run.py` calls `configure_opentelemetry` before importing the app.

**Terminal 3 — Celery worker:**

**Important:** Use the instrumented `worker.py` file, not the standard `celery` command:

```bash
source .venv/bin/activate
python worker.py
```

The worker output should include:

![alt text](image-10.png)

**Critical:** The service name must show ONLY `celery-worker`. You should NOT see `flask-api` in the worker logs. If you see both service names, your `worker.py` imports are in the wrong order.

### 5.2 Triggering a Request

From a fourth terminal, send a registration request:

```bash
curl -X POST http://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d '{"email": "bob@example.com"}'
```

Expected response:

![alt text](image-16.png)

Wait 5 seconds for the `send_welcome_email` task to complete.

### 5.3 Understanding Worker Background Traces

Before viewing the registration trace, note that you may already see multiple traces from the `celery-worker` service in Grafana. These include Redis operations like PUBLISH, LLEN, SADD, PING, SREM, and DEL. These are **Celery's internal heartbeat and queue management operations** — they are normal.

The `RedisInstrumentor` captures ALL Redis commands in the worker process, including Celery's internal bookkeeping:

| Redis Command | Purpose |
|---------------|---------|
| `PING` | Worker health check / connection keepalive |
| `PUBLISH` | Celery event broadcast (task-sent, task-succeeded, heartbeat) |
| `LLEN` | Queue length polling (checks how many tasks are waiting) |
| `SADD` | Worker registration in Redis |
| `SREM` | Worker deregistration |
| `DEL` | Cleanup of processed task results |

These traces appear every few seconds regardless of whether you send requests. To filter them out in Grafana, set **Span Duration > 100ms** to focus on meaningful task execution traces.

### 5.4 Viewing Traces in Grafana

Open Grafana in your browser via the Load Balancer URL.

![alt text](image-5.png)

Navigate to **Explore** (compass icon in the left sidebar) and select **Tempo** as the datasource from the dropdown.

In the query section, click the **Search** tab. To filter out the noisy Celery heartbeat traces, set **Span Duration > 100ms**, then click **Run query**. If you still see more than two traces, feel free to increase the lower limit of the span duration (for instance: 400ms).

**Tip:** Without the duration filter, you will see many short-lived Redis traces (PUBLISH, PING, LLEN, SADD) from the Celery worker's internal operations. Setting the duration threshold hides these and shows only meaningful request traces.

**Common mistake:** Do NOT set "Span Name" to "celery-worker" or "flask-api" — these are service names, not span names. Applying incorrect filters will hide traces from one of the services.



You will see **two separate traces** in the results table — one from `flask-api` and one from `celery-worker`. Each has a **different Trace ID**:

![alt text](image-17.png)

Click on each trace to inspect it separately:

**Flask trace (`flask-api`):**

![alt text](image-19.png)

**Celery trace (`celery-worker`):**

![alt text](image-18.png)

**Why are these separate?** Trace context propagation between Flask and Celery is NOT yet implemented. Flask creates one Trace ID, Celery creates a completely different one. They appear as two unrelated traces in Grafana. Chapter 7 explains why this happens, and Chapter 8 implements the fix to link them into a single unified trace.

Key observations at this stage:

1. **Two services** produce traces independently: `flask-api` and `celery-worker`
2. **Different Trace IDs**: Each service generates its own Trace ID — there is no parent-child link yet
3. **Flask trace is fast** (~554ms) — it queues the task and returns immediately
4. **Celery trace is slow** (~4.6s) — it executes the actual work
5. **Timing breakdown**: Each span's duration is visible within its respective trace

### 5.5 Inspecting Span Attributes
Click on individual spans to view their attributes:
The flask-api parent span attributes include:

![alt text](image-20.png)

The Celery span attributes include:

![alt text](image-21.png)

These attributes are added automatically by the instrumentors—no manual code required.

### 5.6 Checkpoint

Verify your tracing pipeline:

- [ ] Flask shows "OpenTelemetry configured for service: flask-api" on startup
- [ ] Celery shows "OpenTelemetry configured for service: celery-worker" on startup (not flask-api)
- [ ] Traces appear in Grafana after sending a request
- [ ] You see **two separate traces** — one from `flask-api` (~554ms) and one from `celery-worker` (~4.6s) with **different Trace IDs** (this is expected; propagation is implemented in Chapter 8)
- [ ] The `flask-api` trace contains the HTTP request span and Redis RPUSH span
- [ ] The `celery-worker` trace contains the task execution span
- [ ] Clicking a span reveals auto-captured attributes (HTTP method, task name, etc.)

---

## Chapter 6: Adding Custom Spans

Auto-instrumentation captures framework-level operations (HTTP requests, Redis commands, task execution), but it does not capture business logic. Custom spans provide visibility into specific operations within your code.

### 6.1 Custom Spans in Celery Tasks

Update `app/tasks.py` to add custom spans that measure each step of the email sending process:

```python
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
import time
import random
import logging

from opentelemetry import trace

tracer = trace.get_tracer(__name__)

logger = logging.getLogger(__name__)

# ... existing task configuration ...

@celery.task(bind=True, max_retries=3, default_retry_delay=5)
def send_welcome_email(self, user_email):

    # Custom span for email validation
    with tracer.start_as_current_span("validate_email") as span:
        span.set_attribute("email.address", user_email)
        span.set_attribute("email.domain", user_email.split('@')[-1])

        logger.info(f"send_welcome_email: Validating email {user_email}")
        time.sleep(0.1)

        if '@' not in user_email:
            span.set_attribute("email.valid", False)
            span.set_attribute("error", True)
            raise ValueError("Invalid email format")

        span.set_attribute("email.valid", True)

    # Custom span for SMTP connection
    with tracer.start_as_current_span("smtp_connect") as span:
        span.set_attribute("smtp.server", "smtp.example.com")
        span.set_attribute("smtp.port", 587)

        logger.info(f"send_welcome_email: Connecting to SMTP server")
        time.sleep(1)

        span.set_attribute("smtp.connected", True)

    # Custom span for sending the email
    with tracer.start_as_current_span("send_email_message") as span:
        span.set_attribute("email.to", user_email)
        span.set_attribute("email.subject", "Welcome to Our Platform")

        logger.info(f"send_welcome_email: Sending email to {user_email}")
        time.sleep(3)

        span.set_attribute("email.sent", True)
        span.set_attribute("email.message_id", f"<{int(time.time())}@example.com>")

    # Custom span for database update
    with tracer.start_as_current_span("update_user_record") as span:
        span.set_attribute("db.operation", "UPDATE")
        span.set_attribute("db.table", "users")
        span.set_attribute("user.email", user_email)

        logger.info(f"send_welcome_email: Updating user record")
        time.sleep(0.5)

        span.set_attribute("db.rows_affected", 1)

    logger.info(f"send_welcome_email: Successfully sent to {user_email}")
    return f"Welcome email sent to {user_email}"
```

Each `tracer.start_as_current_span()` call creates a nested span within the parent `send_welcome_email` span. Custom attributes attached to each span provide metadata for debugging and filtering—email addresses, SMTP server details, database operations.

### 6.2 Custom Spans in Flask Routes

Update `app/routes.py` to add custom spans to the API layer:

```python
from flask import Blueprint, request, jsonify
from app.tasks import send_welcome_email, generate_monthly_report, flaky_task, slow_task
from app import celery

from opentelemetry import trace
import logging

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__)

@bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')

    # Custom span for input validation
    with tracer.start_as_current_span("validate_request") as span:
        span.set_attribute("request.email", email)

        if not email:
            span.set_attribute("validation.failed", True)
            span.set_attribute("validation.error", "Email is required")
            return jsonify({"error": "Email is required"}), 400

        span.set_attribute("validation.passed", True)

    # Custom span for task queuing
    with tracer.start_as_current_span("queue_email_task") as span:
        span.set_attribute("task.name", "send_welcome_email")
        span.set_attribute("task.args", email)

        logger.info(f"Endpoint /register: Queuing email task for {email}")
        result = send_welcome_email.delay(email)

        span.set_attribute("task.id", result.id)
        span.set_attribute("task.state", result.state)

    # Custom span for response construction
    with tracer.start_as_current_span("build_response") as span:
        response_data = {
            "message": "User registered. Welcome email is being sent in the background.",
            "task_id": result.id
        }
        span.set_attribute("response.status_code", 201)
        span.set_attribute("response.task_id", result.id)

    logger.info(f"Endpoint /register: Returned task_id {result.id}")
    return jsonify(response_data), 201

# ... other routes remain the same ...
```

### 6.3 Testing Custom Spans

Restart the Flask application and Celery worker to pick up the changes.

Trigger a new request:

```bash
curl -X POST http://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com"}'
```

Expected response:

![alt text](image-11.png)

Wait 5 seconds for the `send_welcome_email` task to complete.

In Grafana, find the new traces. Since propagation is not yet implemented, you will see two separate traces — one for each service. But now each trace contains detailed custom span breakdowns:

![alt text](image-12.png)

**Flask trace (`flask-api`):**

![alt text](image-13.png)

**Celery trace (`celery-worker`):**

![alt text](image-14.png)


Notice how each service's custom spans nest correctly within their respective traces. After implementing propagation in Chapter 8, these two traces will merge into a single unified trace.

Click on the `send_email_message` span to view custom attributes:

![alt text](image-15.png)

If an email fails to send, these attributes immediately reveal which step failed (SMTP connection? Email delivery? Database update?), the exact error, and how long each step took before the failure.

### 6.4 Checkpoint

Verify your custom instrumentation:

- [ ] Custom spans appear in the trace timeline for both Flask and Celery operations
- [ ] Each custom span carries relevant attributes (email address, SMTP server, task ID)
- [ ] The span hierarchy nests correctly: HTTP request > validate_request > queue_email_task
- [ ] Auto-instrumented spans (Redis RPUSH) still appear alongside custom spans

---

## Chapter 7: Trace Context Propagation

In previous chapters, Flask and Celery each produced traces independently. If you compare Trace IDs in Grafana, you will notice that Flask spans carry one Trace ID and Celery spans carry a completely different Trace ID. This means the traces are **disconnected** — Grafana cannot stitch them into a single timeline.

This chapter explains **why** this happens and **what trace context propagation means** conceptually. The next chapter will implement the fix.

### 7.1 Observing the Problem

Send a request and find the resulting traces in Grafana:

```bash
curl -X POST http://localhost:5000/send-email \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "subject": "Test", "body": "Hello"}'
```

Open Grafana → Explore → Tempo. Search for `flask-api` traces and `celery-worker` traces separately:

| Service | Trace ID | Observation |
|---------|----------|-------------|
| flask-api | `aaaa-1111-...` | Contains HTTP span + Redis RPUSH span |
| celery-worker | `bbbb-2222-...` | Contains task execution span + custom spans |

The two Trace IDs are **different**. Grafana shows them as two unrelated traces. There is no parent-child link between the Flask span and the Celery span.

### 7.2 Why Auto-Instrumentation Does Not Propagate Context Here

OpenTelemetry auto-instrumentation propagates trace context automatically for **HTTP-based** communication. When Service A calls Service B over HTTP, the instrumentation injects a `traceparent` header into the outgoing request, and the receiving service extracts it.

Flask-to-Celery communication does **not** use HTTP. The flow is:

```
Flask process → Redis RPUSH (task message) → Celery worker BRPOP (picks up message)
```

Redis is a message broker here, not an HTTP endpoint. The `RedisInstrumentor` traces the Redis commands themselves (RPUSH, BRPOP), but it has no mechanism to inject trace context **into the task payload**. The `CeleryInstrumentor` creates spans for task execution, but it does not extract trace context **from the task payload** either.

The result: Flask starts a trace, Celery starts a **separate** trace. The two never connect.

### 7.3 What Propagation Requires

For Flask and Celery to share the same Trace ID, two things must happen:

**Step 1 — Injection (Flask side):** Before the task message enters Redis, the current trace context (Trace ID + Span ID) must be **serialized** and **attached** to the task message as a header.

The W3C Trace Context standard defines the format:

```
traceparent: 00-<trace_id>-<parent_span_id>-01
```

Example:

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

This header carries three pieces of information:
- The Trace ID (`4bf92f...`)
- The parent Span ID (`00f067...`)
- A sampling flag (`01` = sampled)

**What is the sampling flag?** In production systems handling thousands of requests per second, tracing every single request generates enormous amounts of data. Sampling controls which requests get traced. The sampling flag in the `traceparent` header tells downstream services whether this particular trace was selected for recording:

- `01` = **sampled** — this trace IS being recorded. The downstream service should also record its spans for this trace.
- `00` = **not sampled** — this trace is NOT being recorded. The downstream service can skip creating spans for this request, saving resources.

When the flag is `01`, all services in the chain agree to record spans for this trace, ensuring the complete request journey is captured. When it's `00`, services may choose to drop the trace entirely. In this lab, all traces are sampled (`01`) because we are not using a sampling strategy — every request gets traced. Production systems typically use ratio-based sampling (e.g., trace 10% of requests) to balance observability with cost.

**Step 2 — Extraction (Celery side):** When the worker picks up the task, it must **read** the `traceparent` header from the task message, **parse** the Trace ID and parent Span ID, and use them as the context for its new span. This ensures the worker's span becomes a **child** of the Flask span.

### 7.4 The Propagation Mechanism: Celery Signals

Celery provides a **signal** system — hooks that fire at specific points in the task lifecycle. Two signals are relevant:

| Signal | Fires when | Runs in |
|--------|-----------|---------|
| `before_task_publish` | A task is about to be sent to the broker | Flask process |
| `task_prerun` | A task is about to execute | Celery worker process |

OpenTelemetry provides two functions for propagation:

| Function | Purpose |
|----------|---------|
| `propagate.inject(carrier)` | Serializes the current trace context (Trace ID + Span ID) into a dictionary |
| `propagate.extract(carrier)` | Deserializes trace context from a dictionary and returns an OTel Context object |

The propagation flow:

```
Flask process                          Celery worker process
─────────────                          ──────────────────────
1. HTTP request arrives                
2. OTel creates Trace ID abc-123       
3. before_task_publish fires           
4. propagate.inject() writes           
   traceparent into task headers       
5. Task message + headers → Redis      
                                       6. Worker picks up task
                                       7. task_prerun fires
                                       8. propagate.extract() reads
                                          traceparent from headers
                                       9. OTel creates span with
                                          Trace ID abc-123 (same!)
                                       10. Span's parent = Flask's span
```

After propagation, the trace in Grafana looks like:

```
Trace: abc-123
├─ POST /send-email [flask-api] ──────── 120ms
│  ├─ validate_request ────────────────── 2ms
│  ├─ queue_email_task ────────────────── 15ms
│  └─ Redis RPUSH ─────────────────────── 5ms
└─ tasks.send_email [celery-worker] ──── 5200ms   ← CHILD of Flask span
   ├─ smtp_connect ────────────────────── 200ms
   └─ smtp_send ───────────────────────── 5000ms
```

Both services share Trace ID `abc-123`. Grafana stitches them into one timeline.

### 7.5 Prediction Exercise

Before implementing the fix in the next chapter, predict:

1. Which file needs the `before_task_publish` signal handler — `run.py`, `app/__init__.py`, or `worker.py`?
2. Which file needs the `task_prerun` signal handler?
3. If `propagate.inject()` is called but `propagate.extract()` is not, what happens? (Hint: the headers travel through Redis but nobody reads them)
4. If both signals work correctly, will the Redis RPUSH span from `flask-api` appear as a parent or sibling of the Celery task span?

<details>
<summary><strong>Answers</strong></summary>

1. **`app/__init__.py`** — The `before_task_publish` signal fires in the process that **publishes** tasks — which is the Flask process (the one calling `.delay()`). The Celery worker never publishes tasks in this architecture, so it does not need this handler. The question is: which file in the Flask process should register it?

   - **Not `run.py`** — While `run.py` runs in the Flask process, it is an entry point script, not a module that gets imported. Placing framework-level signal handlers in an entry point mixes infrastructure plumbing with startup logic.
   - **Not `worker.py`** — This runs in the worker process. Even if you registered the handler here, it would never fire because the worker never calls `.delay()`.
   - **`app/__init__.py` is correct** — This file contains framework-level setup (Flask app, Celery app, instrumentors). When `run.py` executes `from app import app`, Python runs `app/__init__.py` as module-level code, registering the signal handler in the Flask process before any request arrives. The handler is also registered in the worker process (since `worker.py` does `from app import celery`), but it is harmless there — the worker never publishes tasks, so the signal never fires.

2. **`worker.py`** — The `task_prerun` signal fires in the **worker** process just before a task executes. The worker entry point is `worker.py`, so registering the handler there ensures it runs in the correct process. Putting it in `app/__init__.py` would also work (since the worker imports from `app`), but `worker.py` is the cleaner choice because extraction is a worker-specific concern — Flask never needs to extract trace context from task headers.

3. **Traces remain disconnected.** The `traceparent` header would be written into the task message headers and travel through Redis, but the worker would never read it. The worker would generate a new Trace ID as usual, and the two traces would remain separate. The injected headers would simply be ignored — dead data sitting in the task payload.

4. **Sibling.** The Redis RPUSH span is created by the `RedisInstrumentor` as a child of the Flask HTTP span. The Celery task span, after propagation, becomes a child of the Flask HTTP span as well. Both share the same parent (the Flask HTTP span), making them **siblings** in the trace tree — not parent-child of each other.

</details>

### 7.6 Performance Analysis with Traces

After implementing propagation in Chapter 8, unified traces will reveal performance bottlenecks across services. Even without propagation, individual service traces already provide timing visibility.

Trigger a report generation task:

```bash
curl -X POST http://localhost:5000/reports/generate \
  -H "Content-Type: application/json" \
  -d '{"user_id": 42}'
```

Find the `celery-worker` trace in Grafana:

GG

The Celery trace alone shows the bottleneck:

```
Trace: celery-worker (Total: ~10000ms)
└─ generate_monthly_report [celery-worker] ─ 10000ms
   └─ time.sleep(10) ──────────────────────────── 10000ms
```

After propagation is implemented (Chapter 8), this same request will produce a **unified** trace:

```
Unified Trace (Total: ~10050ms)
├─ POST /reports/generate [flask-api] ──────── 50ms
└─ generate_monthly_report [celery-worker] ─ 10000ms
   └─ time.sleep(10) ──────────────────────────── 10000ms
```

The bottleneck is immediately visible: 99.5% of the total time is spent in task execution. Flask's contribution is negligible at 50ms.

Without tracing, debugging a slow endpoint requires guessing: Is the database slow? Is Redis the bottleneck? Is an external API taking too long? With tracing, the timeline shows exactly where the time is spent:

```
Trace: GET /user/profile
├─ Database query: users ───────────── 150ms
├─ Database query: orders ──────────── 50ms
├─ External API: payment_service ───── 20ms
├─ Redis GET: user_cache ───────────── 5ms
└─ Template rendering ──────────────── 10ms
Total: 235ms
```

The `users` database query consumes 64% of the total time—the optimization target is immediately clear.

### 7.7 Checkpoint

Verify your understanding of trace propagation:

- [ ] Flask and Celery currently produce **different** Trace IDs (disconnected traces)
- [ ] Auto-instrumentation does not propagate context through Redis message brokers — only through HTTP
- [ ] Propagation requires two steps: injection (Flask side) and extraction (Celery side)
- [ ] Celery signals (`before_task_publish` and `task_prerun`) provide the hooks for injection and extraction
- [ ] `propagate.inject()` serializes trace context; `propagate.extract()` deserializes it
- [ ] After propagation, both services share the same Trace ID and Grafana stitches them into one timeline
- [ ] Performance bottlenecks are identifiable by comparing span durations in the trace timeline

---

## Chapter 8: Implementing Trace Context Propagation

Chapter 7 explained why Flask and Celery traces are disconnected and what propagation requires conceptually. This chapter implements the fix using Celery signals and OpenTelemetry's propagation API.

### 8.1 Adding the Injection Signal Handler

The `before_task_publish` signal fires in the **Flask process** whenever a task is about to be sent to Redis. This is where the current trace context gets injected into the task message headers.

**Why `app/__init__.py` and not another file?**

The injection handler must run in the **Flask process** — because that is where `.delay()` is called and where the `before_task_publish` signal fires. The question is: which file in the Flask process should register this handler?

- **Not `run.py`** — While `run.py` does run in the Flask process, it is an entry point script. It is never imported as a module by anyone else. Signal handlers registered in `run.py` would work for Flask, but placing framework-level plumbing in an entry point violates separation of concerns.
- **Not `app/routes.py`** — Route files define HTTP endpoints, not infrastructure hooks. Mixing trace propagation logic with route handlers makes the codebase harder to navigate.
- **Not `otel_config.py`** — This file configures the OpenTelemetry SDK (TracerProvider, exporter, processor). Celery signal handlers are application-level hooks, not SDK configuration.
- **`app/__init__.py` is correct** — This file already contains framework-level setup: Flask app creation, Celery app creation, and auto-instrumentor registration (`FlaskInstrumentor`, `RedisInstrumentor`). The `before_task_publish` signal handler is the same category — framework-level instrumentation plumbing. It belongs alongside the other instrumentors.

There is also a **technical reason**: `app/__init__.py` executes as module-level code when Python runs `from app import app` (in `run.py`). This means the `before_task_publish` signal handler is registered in the Flask process before any HTTP request arrives — which is exactly what we need. The handler is also registered in the worker process (since `worker.py` does `from app import celery`, which triggers `app/__init__.py`), but this is harmless: the worker never calls `.delay()`, so the `before_task_publish` signal never fires there. The handler simply sits idle in the worker process with no side effects.

**How `propagate.inject()` works under the hood:**

When `propagate.inject(headers)` is called, OpenTelemetry does the following:

1. Reads the **current span** from the active context (the Flask HTTP request span)
2. Extracts the Trace ID and Span ID from that span
3. Formats them into the W3C `traceparent` header: `00-<trace_id>-<span_id>-<flags>`
4. Writes this string into the `headers` dictionary: `headers["traceparent"] = "00-abc123-span1-01"`

The `headers` dictionary is the task message's header map — part of the Celery message protocol. When the task is serialized and pushed to Redis via RPUSH, these headers travel with it as metadata. If no active span exists (e.g., `propagate.inject()` is called outside a request context), it writes nothing — the headers dictionary remains unchanged, and the worker will generate a new Trace ID as usual.

Update `app/__init__.py` to add the signal handler:

```python
from flask import Flask
from celery import Celery
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry import propagate
from celery.signals import before_task_publish

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['result_backend'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

def create_app():
    app = Flask(__name__)
    app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
    app.config['result_backend'] = 'redis://localhost:6379/0'

    from app.routes import bp
    app.register_blueprint(bp)

    FlaskInstrumentor().instrument_app(app)
    RedisInstrumentor().instrument()

    return app

app = create_app()
celery = make_celery(app)

# --- Trace Context Propagation: Injection ---
# This signal fires in the FLASK process before a task message is sent to Redis.
# It injects the current trace context (Trace ID + Span ID) into the task headers.
@before_task_publish.connect
def inject_trace_context(headers=None, **kwargs):
    if headers is None:
        headers = {}
    propagate.inject(headers)

from app import tasks
```

**What changed:** Two new imports (`propagate`, `before_task_publish`) and a signal handler function `inject_trace_context`. When Flask calls `send_welcome_email.delay(email)`, this handler fires automatically and writes the `traceparent` header into the task message before it enters Redis.

### 8.2 Adding the Extraction Signal Handler

The `task_prerun` signal fires in the **Celery worker process** just before a task executes. This is where the trace context gets extracted from the task headers and set as the active context.

**Why `worker.py` and not another file?**

The extraction handler must run in the **Celery worker process** — because that is where tasks execute and where the `task_prerun` signal fires. The question is: which file in the worker process should register this handler?

- **Not `app/__init__.py`** — While placing it here would technically work (since `worker.py` imports `from app import celery`, which triggers `app/__init__.py`), extraction is a **worker-specific concern**. The Flask process never needs to extract trace context from task headers — it is the publisher, not the consumer. Keeping it in `app/__init__.py` would register the handler in the Flask process too, where it would never fire but would add unnecessary imports.
- **Not `app/tasks.py`** — Task files define business logic (what the task does), not infrastructure plumbing (how trace context arrives). Every new task file would need to import and register the handler, violating DRY.
- **`worker.py` is correct** — This file is the worker's entry point and the natural place for worker-specific infrastructure setup. It already configures OpenTelemetry for the worker (`configure_opentelemetry("celery-worker")`), imports the Celery app, and calls `CeleryInstrumentor().instrument()`. The `task_prerun` handler fits this same pattern: worker-specific instrumentation that runs once at startup.

**How `propagate.extract()` and `context.attach()` work under the hood:**

When the worker picks up a task from Redis, the task message includes headers — the same dictionary that `propagate.inject()` wrote to in the Flask process. The extraction process works in two steps:

1. **`propagate.extract(headers)`** — OpenTelemetry reads the `traceparent` value from the headers dictionary (e.g., `"00-abc123-span1-01"`), parses the Trace ID (`abc123`), parent Span ID (`span1`), and sampling flag (`01`), and constructs an OTel `Context` object containing this information. **This does NOT yet affect the current trace.** It only creates a context object in memory.

2. **`context.attach(ctx)`** — This sets the extracted context as the **active context** for the current thread. From this point forward, any new span created by OpenTelemetry (including the `CeleryInstrumentor`'s task span) will inherit the Trace ID and parent Span ID from this context. Without this call, the extracted context would be discarded and the worker would still generate a new Trace ID.

Both steps are required. If you call `propagate.extract()` without `context.attach()`, the trace context is parsed but never activated — the worker still creates an independent trace. If you call `context.attach()` with an empty context, nothing changes — the worker still creates an independent trace.

Update `worker.py`:

```python
from otel_config import configure_opentelemetry
configure_opentelemetry(service_name="celery-worker")

from app import celery

from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry import context, propagate
from celery.signals import task_prerun

CeleryInstrumentor().instrument()

# --- Trace Context Propagation: Extraction ---
# This signal fires in the CELERY WORKER process before a task executes.
# It extracts the trace context from the task headers and sets it as the active context.
@task_prerun.connect
def extract_trace_context(sender=None, **kwargs):
    task = sender
    if task and hasattr(task.request, 'get'):
        headers = task.request.get('headers') or {}
    else:
        headers = {}
    ctx = propagate.extract(headers)
    context.attach(ctx)

if __name__ == '__main__':
    celery.worker_main([
        'worker',
        '--loglevel=info'
    ])
```

**What changed:** Two new imports (`context`, `propagate`, `task_prerun`) and a signal handler function `extract_trace_context`. When the worker picks up a task, this handler reads the `traceparent` header from the task message, parses the Trace ID and parent Span ID, and makes it the active context. All subsequent spans in this task will inherit the Flask Trace ID.

### 8.3 Understanding the Signal Flow

With both handlers in place, the propagation flow is:

```
1. Flask receives POST /register
   → OTel creates Trace ID: abc-123, Span ID: span-1

2. Flask calls send_welcome_email.delay(email)
   → before_task_publish fires (in Flask process)
   → propagate.inject() writes to task headers:
     headers["traceparent"] = "00-abc123-span1-01"

3. Task message + headers → Redis RPUSH

4. Celery worker BRPOP → picks up task message
   → task_prerun fires (in worker process)
   → propagate.extract(headers) reads traceparent
   → context.attach(ctx) sets Trace ID to abc-123

5. CeleryInstrumentor creates task span
   → trace_id = abc-123 (inherited from context!)
   → parent_span_id = span-1 (Flask's span)

6. Both Flask and Celery spans arrive in Tempo
   → Same Trace ID → unified trace
```

### 8.4 Verifying Propagation

Restart both the Flask application and the Celery worker to pick up the changes:

```bash
# Terminal 2 — restart Flask
python run.py

# Terminal 3 — restart Celery worker
python worker.py
```

Send a request:

```bash
curl -X POST http://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d '{"email": "propagation-test@example.com"}'
```

Wait 10 seconds for spans to flush, then open Grafana → Explore → Tempo.

Set **Span Duration > 400ms** and click **Run query**.

You should now see a **single trace** that contains spans from **both** services:

GG

```
Unified Trace (Total: ~5700ms)
├─ POST /register [flask-api] ───────────────── 50ms
│  ├─ validate_request ────────────────────────── 5ms
│  ├─ queue_email_task ────────────────────────── 10ms
│  │  └─ RPUSH celery (Redis) ──────────────────── 8ms
│  └─ build_response ──────────────────────────── 2ms
└─ send_welcome_email [celery-worker] ─────── 5650ms
   ├─ validate_email ──────────────────────────── 100ms
   ├─ smtp_connect ────────────────────────────── 1000ms
   ├─ send_email_message ──────────────────────── 3000ms
   └─ update_user_record ──────────────────────── 500ms
```

**Key verification points:**

1. **One Trace ID** — Both services appear under a single trace entry in the search table
2. **Parent-child link** — Click on the Celery task span; its `parent_span_id` points to the Flask HTTP span
3. **Same Trace ID** — Both Flask and Celery spans share the same `trace_id` value
4. **Two colors** — Flask spans and Celery spans appear in different colors within the same timeline

If you still see two separate traces, check:
- Did you restart **both** Flask and the worker after making changes?
- Is the `before_task_publish` handler in `app/__init__.py` (not in `run.py` or `worker.py`)?
- Is the `task_prerun` handler in `worker.py`?
- Check Flask terminal output for import errors

### 8.5 Checkpoint

Verify trace context propagation is working:

- [ ] Both signal handlers are registered (`before_task_publish` in `app/__init__.py`, `task_prerun` in `worker.py`)
- [ ] A single trace contains spans from **both** `flask-api` and `celery-worker`
- [ ] Flask and Celery spans share the **same** Trace ID
- [ ] The Celery task span's `parent_span_id` references the Flask HTTP span
- [ ] Custom spans (from Chapter 6) still appear nested within their respective service spans

---

## Chapter 9: Searching and Monitoring Traces

As the system processes thousands of requests, finding specific traces requires filtering and search capabilities. Grafana Tempo supports TraceQL, a query language for searching traces by attributes.

### 9.1 Searching by Service Name

In Grafana Explore, switch to the **TraceQL** tab.

Find all traces from the Flask API:

```
{resource.service.name="flask-api"}
```

Find all traces from the Celery worker:

```
{resource.service.name="celery-worker"}
```

### 9.2 Searching by Span Attributes

Custom attributes added in Chapter 6 enable targeted searches.

Find all traces for a specific email:

```
{span.email.address="alice@example.com"}
```

Find all failed email validations:

```
{span.email.valid=false}
```

Find traces where SMTP connection exceeded 2 seconds:

```
{resource.service.name="celery-worker" && name="smtp_connect"} | duration > 2s
```

### 9.3 Searching by HTTP Status Code

Find all failed API requests:

```
{span.http.status_code>=400}
```

Find server errors specifically:

```
{span.http.status_code>=500}
```

### 9.4 Monitoring Error Traces

Trigger the flaky task that fails randomly (70% failure rate):

```bash
curl -X POST http://localhost:5000/test-reliability
```

If the task fails, find its trace in Grafana:

![alt text](image-9.png)

Error traces display:

- A red error indicator on the span
- Span status: `ERROR`
- Exception type: `Exception`
- Exception message: `"Simulated random failure"`

Click on the span to see the full error details:

![alt text](image-10.png)

Span attributes for errors include:

- `exception.type`: Exception
- `exception.message`: Simulated random failure
- `exception.stacktrace`: The complete Python traceback

This visibility eliminates the need to search through log files for error context. The trace shows the exact error, the full stack trace, and all contextual attributes (task arguments, timing, service name).

### 9.5 Checkpoint

Verify your understanding of trace search capabilities:

- [ ] TraceQL filters traces by service name, span attributes, and duration
- [ ] Custom span attributes (added in Chapter 6) are searchable in Grafana
- [ ] Error traces display exception type, message, and full stack trace
- [ ] HTTP status code filtering enables monitoring API error rates

---

## Epilogue: The Complete System

Your Flask-Celery application now has a complete distributed tracing pipeline:

| Component | Role | Port |
|-----------|------|------|
| Flask API | Generates root spans for HTTP requests | 5000 |
| Celery Worker | Generates child spans for task execution | — |
| Redis | Broker and result backend | 6379 |
| Grafana Tempo | Stores and indexes trace data | 4318 (OTLP), 3200 (API) |
| Grafana | Visualizes traces and supports TraceQL queries | 3000 |

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Defines Redis, Tempo, and Grafana services |
| `tempo-config.yaml` | Configures Tempo's OTLP receiver and storage |
| `grafana-datasources.yaml` | Auto-provisions Tempo as Grafana's datasource |
| `otel_config.py` | Centralizes OpenTelemetry configuration with idempotency guard |
| `run.py` | Flask entry point — configures OTel as `flask-api` before importing app |
| `worker.py` | Celery entry point — configures OTel as `celery-worker`, extracts trace context via `task_prerun` signal |
| `app/__init__.py` | Flask/Redis auto-instrumentors + `before_task_publish` signal for trace propagation |
| `app/tasks.py` | Custom spans for business logic in Celery tasks |
| `app/routes.py` | Custom spans for API layer operations |

Verify the complete system by running these commands in sequence:

```bash
# Verify containers are running
docker ps

# Trigger a traced request
curl -X POST http://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d '{"email": "verify@example.com"}'

# Wait for task completion
sleep 6

# Trigger a report generation
curl -X POST http://localhost:5000/reports/generate \
  -H "Content-Type: application/json" \
  -d '{"user_id": 42}'

# Trigger a flaky task
curl -X POST http://localhost:5000/test-reliability
```

Open Grafana and verify that traces appear for all three requests, showing span hierarchies, custom attributes, and timing breakdowns.

---

## The Principles

1. **Trace at service boundaries** — Auto-instrument HTTP requests, message queues, and database operations to capture the complete request flow without manual code changes.

2. **Add custom spans for business logic** — Auto-instrumentation captures framework operations but not domain-specific steps. Custom spans reveal precisely where time is spent within application logic.

3. **Enrich spans with attributes** — Spans without attributes show timing but not context. Adding relevant metadata (email addresses, user IDs, task names) makes traces searchable and debuggable.

4. **Batch span exports** — Individual span exports generate excessive network overhead. BatchSpanProcessor reduces this by collecting spans before sending, trading slight latency for significant throughput improvement.

5. **Use semantic attribute names** — Follow OpenTelemetry semantic conventions (`http.method`, `db.operation`, `messaging.destination`) rather than inventing custom names. Semantic conventions enable cross-service correlation and standard tooling.

6. **Sample in production** — Tracing every request in high-throughput production systems is expensive. Use ratio-based sampling to capture a representative subset while maintaining full tracing for critical endpoints.

---

## Troubleshooting

### Only seeing celery-worker traces (no flask-api spans)

**Cause:** This is almost always because `configure_opentelemetry(service_name="flask-api")` was either not called, or was called AFTER the Flask app was already created. The most common mistake is calling `configure_opentelemetry` inside `create_app()` in `app/__init__.py` instead of in `run.py`.

**Solution:**

1. **Check `run.py`:** It MUST call `configure_opentelemetry` BEFORE importing the app:
   ```python
   from otel_config import configure_opentelemetry
   configure_opentelemetry(service_name="flask-api")  # MUST be before next line
   from app import app
   ```

2. **Check `app/__init__.py`:** It must NOT call `configure_opentelemetry`. Remove any line like:
   ```python
   # REMOVE this line from app/__init__.py
   configure_opentelemetry(service_name="flask-api")
   ```

3. **Check Flask terminal output:** You MUST see this line when Flask starts:
   ```
   OpenTelemetry configured for service: flask-api
   ```
   If you don't see it, `run.py` is not calling `configure_opentelemetry`.

4. **Restart both processes:** After fixing, stop both Flask and the Celery worker, then restart:
   ```bash
   # Terminal 2
   python run.py
   # Terminal 3
   python worker.py
   ```

5. **Send a new request and wait:** After restarting, send a fresh curl request and wait 10 seconds before checking Grafana (BatchSpanProcessor needs time to flush).

### Only seeing one service in traces in Grafana search table

**Cause:** Incorrect filters applied in Grafana are hiding spans from one service, or the Grafana search table only displays the "primary" service for each trace.

**Solution:**

1. **Clear all Grafana filters:** Ensure ALL filter fields are set to "Select value":
   - Service Name: "Select value" (or leave empty)
   - Span Name: "Select value" (NOT "celery-worker" or "flask-api")
   - Status: "Select value"
   - Clear any other applied filters

2. **Click on the Trace ID link:** The search table may only show one service per row. Click on the blue trace ID link to expand the full trace timeline — both services should appear inside.

3. **Common mistake:** Do not set "Span Name" filter to service names like "celery-worker" — these are service names, not span names.

### No traces appear in Grafana

**Cause:** Tempo is not running, the OTLP exporter is misconfigured, or the application did not initialize OpenTelemetry.

**Solution:**

```bash
# Verify Tempo is running
docker ps | grep tempo

# Check Tempo logs for errors
docker logs tempo

# Test OTLP endpoint directly
curl -X POST http://localhost:4318/v1/traces \
  -H "Content-Type: application/json" \
  -d '{}'

# Verify Flask logs show OpenTelemetry initialization
# Expected: "OpenTelemetry configured for service: flask-api"
```

### Tempo does not appear as a datasource in Grafana Explore

**Cause:** The `grafana-datasources.yaml` file was not created before the Grafana container was started, so Grafana never provisioned the Tempo datasource.

**Solution:**

1. **Verify the file exists:**
   ```bash
   ls grafana-datasources.yaml
   ```
   If missing, create it (see Chapter 2.3).

2. **Recreate the Grafana container** so it picks up the provisioning file:
   ```bash
   docker compose down
   docker compose up -d
   ```

3. **Verify in Grafana:** Go to **Explore** → click the datasource dropdown at the top left. "Tempo" should appear in the list. If Grafana is already open, refresh the browser after recreating containers.

4. **Check Grafana logs** if Tempo still doesn't appear:
   ```bash
   docker logs grafana
   ```
   Look for provisioning errors or file mount issues.

### Traces are fragmented (Flask and Celery not linked)

**Cause:** Trace context propagation is not implemented, or the signal handlers from Chapter 8 are missing or misconfigured.

**Solution:**

- **Check Chapter 8 implementation:** Ensure both signal handlers exist:
  - `before_task_publish` in `app/__init__.py` — injects trace context into task headers
  - `task_prerun` in `worker.py` — extracts trace context from task headers
- **Check service name:** Ensure the Celery worker shows `OpenTelemetry configured for service: celery-worker`, not `flask-api`
- **Use correct startup:** Start with `python worker.py`, not `celery -A app.celery worker`
- Verify `CeleryInstrumentor().instrument()` is called in the worker
- Confirm both Flask and Celery target the same OTLP endpoint
- **Restart both processes** after adding the signal handlers

### Worker only shows Redis traces (PUBLISH, LLEN, SADD) but no task execution spans

**Cause:** `CeleryInstrumentor().instrument()` was called BEFORE importing the celery app. The instrumentor hooks into Celery's signal system, but if the celery app doesn't exist yet, the signals are never connected and task execution spans are silently lost.

**Solution:**

Ensure the correct order in `worker.py`:

```python
# Step 1: Configure OpenTelemetry
configure_opentelemetry(service_name="celery-worker")

# Step 2: Import app (BEFORE instrumenting Celery)
from app import celery

# Step 3: Instrument Celery AFTER import
CeleryInstrumentor().instrument()
```

If `CeleryInstrumentor().instrument()` appears before `from app import celery`, move it after the import and restart the worker.

### "Overriding of current TracerProvider is not allowed" warning

**Cause:** OpenTelemetry is being configured multiple times, typically when the Flask app is imported before the Celery worker configures its own OpenTelemetry instance.

**Solution:**

Ensure OpenTelemetry is configured for the Celery worker BEFORE importing the Flask app in `worker.py`:

```python
# Correct order:
# 1. Configure OpenTelemetry for celery-worker
configure_opentelemetry(service_name="celery-worker")

# 2. Import the Flask app
from app import celery

# 3. THEN instrument Celery
CeleryInstrumentor().instrument()
```

If you see both service names ("flask-api" and "celery-worker") in the startup logs, ensure `otel_config.py` has the `_configured` guard.

### No such command 'worker.py' error

**Cause:** The `celery.start()` method tries to parse command line arguments and doesn't recognize `worker.py` as a valid Celery command.

**Solution:**

Use `celery.worker_main()` instead of `celery.start()` in your `worker.py` file:

```python
if __name__ == '__main__':
    # Wrong - causes command parsing error
    celery.start()
    
    # Correct - starts worker directly
    celery.worker_main([
        'worker',
        '--loglevel=info'
    ])
```

This method bypasses the command-line parsing and starts the worker process directly.

### Worker shows wrong service name (flask-api instead of celery-worker)

**Cause:** Starting the worker with `celery -A app.celery worker` imports the Flask app configuration, which sets the service name to `flask-api`. Or the `worker.py` file imports the Flask app before configuring OpenTelemetry, causing Flask's configuration to run first.

**Solution:**

Always use the instrumented worker file that configures OpenTelemetry BEFORE importing the Flask app:

```bash
# Wrong - uses Flask app configuration
celery -A app.celery worker --loglevel=info

# Correct - uses dedicated worker configuration
python worker.py
```

If you see both "flask-api" and "celery-worker" service names in the startup logs, your `worker.py` is importing the Flask app too early. The correct order is:

1. Configure OpenTelemetry with `service_name="celery-worker"`
2. Instrument Celery
3. Import the Flask app
4. Start the worker

Restart the worker with the correct command. You should see ONLY `OpenTelemetry configured for service: celery-worker` in the output.

### ModuleNotFoundError: No module named 'pkg_resources'

**Cause:** The `setuptools` package is missing or incompatible. OpenTelemetry packages require `pkg_resources` from `setuptools`, but setuptools 70+ changed the `pkg_resources` interface.

**Solution:**

Downgrade to a compatible setuptools version:

```bash
pip install setuptools==68.0.0
```

This error occurs when setuptools 70+ is installed, as these versions changed how `pkg_resources` works. OpenTelemetry requires the older interface.

### ImportError from opentelemetry.instrumentation.instrumentor

**Cause:** The `opentelemetry-instrumentation` base package is missing or its version is incompatible with the instrumentor packages. This occurs when pip resolves transitive dependencies to mismatched versions.

**Solution:**

Install the base packages explicitly at matching versions:

```bash
pip install setuptools==68.0.0 \
  opentelemetry-api==1.22.0 \
  opentelemetry-sdk==1.22.0 \
  opentelemetry-instrumentation==0.43b0
```

The version `0.43b0` (instrumentation) corresponds to `1.22.0` (API/SDK). These must match. If versions drift, the `BaseInstrumentor` import fails.

### Too many spans overwhelm the UI

**Cause:** Auto-instrumentation captures every operation including high-frequency internal calls.

**Solution:**

```python
# Disable specific auto-instrumentation
from opentelemetry.instrumentation.redis import RedisInstrumentor
RedisInstrumentor().uninstrument()

# Or create spans conditionally
if condition_worth_tracing:
    with tracer.start_as_current_span("operation"):
        do_work()
else:
    do_work()
```

---

## Next Steps

This lab established local distributed tracing. Several extensions deepen observability capabilities:

- **Custom spans for database queries** — Instrument database operations to identify slow queries and N+1 query problems in traces
- **Nested span hierarchies** — Create multi-level span trees that map to internal function call chains
- **External API tracing** — Add spans for outbound HTTP calls with request/response attributes
- **Trace-log correlation** — Embed trace IDs in log entries so log searches link directly to trace visualizations
- **Production sampling strategies** — Configure ratio-based or priority-based sampling to control trace volume
- **Performance dashboards** — Create Grafana dashboards with TraceQL queries to monitor slow tasks and API error rates continuously

Module 57 covers advanced instrumentation techniques: function-level latency measurement, database query tracing, external API spans, and trace-log-metric correlation for a complete observability solution.

---

## Additional Resources

### Official Documentation

- **OpenTelemetry Python SDK**: https://opentelemetry.io/docs/languages/python/
- **OpenTelemetry Auto-Instrumentation**: https://opentelemetry.io/docs/languages/python/automatic/
- **Grafana Tempo Documentation**: https://grafana.com/docs/tempo/latest/
- **TraceQL Query Language**: https://grafana.com/docs/tempo/latest/traceql/

### Specification and Standards

- **OpenTelemetry Specification**: https://opentelemetry.io/docs/specs/otel/
- **Semantic Conventions**: https://opentelemetry.io/docs/specs/semconv/
- **OTLP Protocol**: https://opentelemetry.io/docs/specs/otlp/

### Grafana Ecosystem

- **Grafana Documentation**: https://grafana.com/docs/grafana/latest/
- **Grafana Tempo Configuration**: https://grafana.com/docs/tempo/latest/configuration/
- **Grafana Datasource Provisioning**: https://grafana.com/docs/grafana/latest/administration/provisioning/#data-sources
