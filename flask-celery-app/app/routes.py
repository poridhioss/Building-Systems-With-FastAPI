from flask import Blueprint, jsonify

bp = Blueprint('routes', __name__)

@bp.route('/ping', methods=['POST'])
def ping():
    """
    Health check endpoint that triggers a background task.
    Returns immediately with 202 Accepted while task processes in background.
    """
    from app.tasks import test_task

    task = test_task.delay()

    return jsonify({
        'message': 'Task queued',
        'task_id': task.id
    }), 202