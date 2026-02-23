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