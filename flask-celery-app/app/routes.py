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


# @bp.route('/register', methods=['POST'])
# def register():
#     """User registration endpoint with background email."""
#     from app.tasks import send_welcome_email

#     data = request.get_json()
#     user_email = data.get('email')

#     if not user_email:
#         logger.warning("Endpoint /register: Missing email parameter")
#         return jsonify({'error': 'Email is required'}), 400

#     logger.info(f"Endpoint /register: Queuing email task for {user_email}")
#     task = send_welcome_email.delay(user_email)

#     return jsonify({
#         'message': 'User registered successfully',
#         'email': user_email,
#         'email_task_id': task.id
#     }), 201


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
    Endpoint to test retry behavior with flaky task.
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
    Endpoint to test timeout enforcement.
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
    """
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




from opentelemetry import trace
tracer = trace.get_tracer(__name__)

@bp.route('/register', methods=['POST'])
def register():

    from app.tasks import send_welcome_email

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
