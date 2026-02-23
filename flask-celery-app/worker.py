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