In Module 55, you added real-time monitoring to your Celery workers using Flower, giving you visibility into task states, failures, and worker health. However, Flower only shows you what's happening inside the Celery layer. It can't answer questions like: "How long did the entire user request take from API call to task completion?", "When a task fails, was it slow before it failed?", or "How much time is spent in the database vs. external API calls?"

These questions require **distributed tracing**—a technique that instruments your code to track requests as they flow through multiple services, creating a complete timeline of execution. Instead of piecing together logs from different systems, you get a single unified view of the entire request journey.

---

### **Lab 1: Local Tracing Setup with Grafana Tempo**
**Context:** Distributed tracing instruments your application to capture timing data for each operation (called "spans") and stitches them together into a complete request trace. Grafana Tempo is a distributed tracing backend that stores these traces, while Grafana provides a UI to visualize them. OpenTelemetry is the industry-standard framework for instrumenting code to generate traces. In this lab, you will deploy a local observability stack (Grafana + Tempo) using Docker Compose, instrument your Flask application with OpenTelemetry auto-instrumentation to capture traces automatically, configure the OTLP HTTP exporter to send traces to Tempo, trigger requests and visualize the complete execution timeline in Grafana, and add custom spans to measure specific business logic operations.

*   **Goals:**
    *   **Observability Stack Deployment:** Deploy Grafana and Tempo locally using Docker Compose.
    *   **OpenTelemetry Installation:** Install OpenTelemetry SDK and auto-instrumentation packages for Flask.
    *   **Auto-Instrumentation:** Use `opentelemetry-instrument` to automatically capture HTTP requests, database queries, and Redis operations.
    *   **Exporter Configuration:** Configure the OTLP HTTP exporter via environment variables to send traces to Tempo.
    *   **Trace Visualization:** Trigger Flask API requests and visualize traces in Grafana showing request flow, timing breakdowns, and service dependencies.
    *   **Custom Spans:** Add manual instrumentation using the OpenTelemetry SDK to create custom spans for business logic (e.g., "validate_email", "calculate_report").
    *   **Span Attributes:** Enrich spans with custom attributes like user_id, email, task_id for better filtering and debugging.
    *   **Trace Propagation:** Understand how trace context flows from Flask to Celery (trace ID and span ID).
*   **Deliverables:**
    *   A `docker-compose.yml` running Grafana and Tempo containers
    *   Flask application instrumented with OpenTelemetry auto-instrumentation
    *   Screenshots showing traces in Grafana with multiple spans (HTTP request → task queue → task execution)
    *   Custom spans visible in the trace timeline with custom attributes
    *   Evidence of trace propagation: a single trace spanning both Flask API and Celery task execution
    *   Performance analysis: identify slow operations in the trace timeline (e.g., database queries taking >100ms)
