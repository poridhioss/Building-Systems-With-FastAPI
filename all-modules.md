# Building Systems With FastAPI

## Module 50: Build a JWT-Based Authentication API

- Understand the FastAPI request lifecycle
- Learn JWT structure: Header, Payload, Signature
- Implement secure password hashing with bcrypt
- Design a relational SQL schema for user management
- Develop authentication middleware to protect routes
- Handle token expiration and implement refresh token strategies

## Module 51: Deploy the Authentication API

- Deploy the JWT Auth API on Poridhi Cloud
- Deploy the API on AWS using EC2 and RDS
- Package and deploy the Auth API as an AWS Lambda function (serverless)

## Module 52: Introduction to Celery and Task Queues

- What is Celery and when to use it
- Architecture: Broker, Worker, Result Backend
- Use cases: offloading long-running tasks from API

## Module 53: Integrating Celery with Flask

- Set up a Flask API that submits background tasks
- Install and configure celery[redis]
- Connect Celery to Redis as both broker and backend
- Define tasks for email sending, PDF generation, etc.

## Module 54: Task Management and Reliability

- Implement task retries, timeouts, and error handling
- Expose an endpoint to check task status by ID
- Track task results and understand Celery state transitions
- Add logging and exception capture in tasks

## Module 55: Monitoring Celery Workers (Optional)

- Install and use Flower for monitoring Celery tasks
- View task state, retries, and real-time processing
- Secure Flower dashboard (optional)

## Module 56: Local Tracing Setup with Grafana Tempo

- Deploy Grafana + Tempo using Docker Compose
- Instrument FastAPI or Flask using opentelemetry-instrument or the OTEL SDK
- Configure OTLP HTTP exporter via environment variables or YAML
- Trigger requests and visualize traces in Grafana

## Module 57: Adding Custom Spans and Metadata

- Add manual spans in key business logic
- Include custom tags like user ID, request ID, query time
- Use nested spans to measure internal function-level latency

## Module 58: Distributed Tracing with Celery

- Connect tracing across Flask API and Celery worker
- Propagate trace context via headers or task payload
- Visualize end-to-end distributed trace in Tempo

## Module 59: Celery with AWS SQS – Theory

- Celery architecture: producer, broker (SQS), worker
- Flask integration with Celery
- AWS SQS configuration: visibility timeout, polling interval, dead-letter queue
- Comparison between Redis and SQS as brokers
- Secure AWS access using IAM roles and credentials
- Task retries, delayed jobs, and cloud-native worker scaling
- Monitoring and observability using Flower and cloud tools

## Module 60: Celery with AWS SQS – Practical

- Set up Flask API to trigger Celery background tasks
- Configure Celery to use AWS SQS as broker
- Handle long-running background jobs
- Return task ID and expose task status endpoint
- Deploy Flower dashboard with Nginx for secure access