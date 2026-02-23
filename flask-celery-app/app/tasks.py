from app import celery
from celery.exceptions import SoftTimeLimitExceeded
import time
import random
import logging

logger = logging.getLogger(__name__)

@celery.task(
    bind=True,  # A1
    max_retries=3,
    default_retry_delay=5
)
def test_task(self):
    """
    Simple health check task with retry capability.
    """
    try:
        logger.info("test_task: Starting execution")

        from flask import current_app
        secret_key = current_app.config.get('SECRET_KEY')

        logger.info("test_task: Accessed Flask config successfully")
        time.sleep(3)

        logger.info("test_task: Completed successfully")
        return "Pong from Background!"

    except Exception as exc:
        logger.error(f"test_task: Failed with error: {exc}")
        raise self.retry(exc=exc)  # A2


# @celery.task(
#     bind=True,
#     max_retries=3,
#     default_retry_delay=10,
#     time_limit=15,
#     soft_time_limit=12
# )
# def send_welcome_email(self, user_email):
#     """
#     Simulates sending a welcome email with timeout protection.
#     """
#     try:
#         logger.info(f"send_welcome_email: Starting for {user_email}")
#         time.sleep(5)
#         logger.info(f"send_welcome_email: Successfully sent to {user_email}")
#         return f"Email sent to {user_email}"

#     except SoftTimeLimitExceeded:  # A3
#         logger.warning(f"send_welcome_email: Soft time limit exceeded for {user_email}")
#         return {"status": "timeout", "message": "Email sending timed out"}

#     except Exception as exc:
#         logger.error(f"send_welcome_email: Failed for {user_email} - {exc}")
#         raise self.retry(exc=exc)


@celery.task(
    bind=True,
    max_retries=2,
    default_retry_delay=15,
    time_limit=30,
    soft_time_limit=25
)
def generate_monthly_report(self, user_id):
    """
    Simulates PDF generation with comprehensive error handling.
    """
    try:
        logger.info(f"generate_monthly_report: Starting for user {user_id}")
        time.sleep(10)

        report_filename = f"report_user_{user_id}_{int(time.time())}.pdf"
        logger.info(f"generate_monthly_report: Generated {report_filename}")

        return {
            "filename": report_filename,
            "user_id": user_id,
            "status": "completed"
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"generate_monthly_report: Soft time limit exceeded for user {user_id}")
        return {
            "status": "timeout",
            "message": "Report generation exceeded time limit",
            "user_id": user_id
        }

    except Exception as exc:
        logger.error(f"generate_monthly_report: Failed for user {user_id} - {exc}")
        raise self.retry(exc=exc, countdown=15)

@celery.task(
    bind=True,
    max_retries=3,
    default_retry_delay=5
)
def flaky_task(self, task_number):
    """
    Intentionally fails 70% of the time to demonstrate retry behavior.
    """
    try:
        logger.info(f"flaky_task: Attempt started for task #{task_number}")
        time.sleep(2)

        # 70% chance of failure
        if random.random() < 0.7:
            logger.warning(f"flaky_task: Simulated failure for task #{task_number}")
            raise Exception("Simulated transient error (network timeout)")

        logger.info(f"flaky_task: Successfully completed task #{task_number}")
        return {
            "status": "success",
            "task_number": task_number,
            "message": "Task succeeded after retries"
        }

    except Exception as exc:
        logger.error(f"flaky_task: Failed task #{task_number} - {exc}")

        # Check if we've exhausted retries
        if self.request.retries >= self.max_retries:
            logger.error(f"flaky_task: Max retries exhausted for task #{task_number}")
            return {
                "status": "failed",
                "task_number": task_number,
                "error": str(exc),
                "retries": self.request.retries
            }

        # Exponential backoff: 5s, 10s, 20s
        countdown = self.default_retry_delay * (2 ** self.request.retries)
        logger.info(f"flaky_task: Retrying task #{task_number} in {countdown} seconds")

        raise self.retry(exc=exc, countdown=countdown)

@celery.task(
    bind=True,
    time_limit=10,
    soft_time_limit=8
)
def slow_task(self, duration):
    """
    Intentionally runs longer than timeout to demonstrate termination.
    """
    try:
        logger.info(f"slow_task: Starting {duration}-second task")

        # This will exceed our 8-second soft limit if duration > 8
        time.sleep(duration)

        logger.info("slow_task: Completed successfully")
        return {
            "status": "completed",
            "duration": duration
        }

    except SoftTimeLimitExceeded:
        logger.warning("slow_task: Soft time limit (8s) exceeded")

        # Return gracefully before hard termination
        return {
            "status": "timeout",
            "message": f"Task exceeded {self.soft_time_limit}s soft limit",
            "attempted_duration": duration
        }
    

from opentelemetry import trace

tracer = trace.get_tracer(__name__)

# logger = logging.getLogger(__name__)

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