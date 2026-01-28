from app import celery
import time

@celery.task
def test_task():
    """
    A simple background task for testing the Flask-Celery integration.
    This will execute inside Flask's application context thanks to make_celery().
    """
    print("Pong from Background!")
    time.sleep(3)
    print("Task completed!")
    return "Pong from Background!"