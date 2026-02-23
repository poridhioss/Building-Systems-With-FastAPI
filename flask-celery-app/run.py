from otel_config import configure_opentelemetry

# Configure OpenTelemetry FIRST, before any app imports

from app import app

configure_opentelemetry(service_name="flask-api")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)