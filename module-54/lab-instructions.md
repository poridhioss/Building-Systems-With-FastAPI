In Module 53, you built a Flask-Celery integration that can submit tasks and check their status. However, production systems need to handle failures gracefully, prevent tasks from running indefinitely, and provide visibility into execution. Module 54 focuses on **Task Reliability**—making your task queue robust enough for real-world use.

---

### **Lab 1: Adding Reliability Features (Retries, Timeouts, Error Handling, Logging)**
**Context:** In production, tasks fail for many reasons: network timeouts, external API errors, database deadlocks, or unexpected data. Without proper handling, failed tasks disappear silently, and runaway tasks consume resources indefinitely. In this lab, you will extend the Module 53 Flask-Celery app with production-ready reliability features: automatic retries with exponential backoff, timeout limits to kill long-running tasks, comprehensive logging to track execution, and structured error handling to return meaningful failure messages to clients.

*   **Goals:**
    *   **Task Retries:** Configure automatic retry behavior using `max_retries`, `default_retry_delay`, and manual retry with `self.retry()`. Implement a "flaky task" that randomly fails to demonstrate retry attempts with exponential backoff.
    *   **Timeouts:** Set hard and soft time limits on tasks using `time_limit` and `soft_time_limit`. Create a task that exceeds the limit and observe Celery's termination behavior.
    *   **Logging:** Set up Python's logging module to track task lifecycle events (start, success, failure, retry). Configure structured log output visible in the Celery worker terminal.
    *   **Error Handling:** Implement try-except blocks in tasks to capture exceptions and return structured error responses. Distinguish between retryable errors (network timeout) and non-retryable errors (invalid input).
*   **Deliverables:**
    *   Updated `app/tasks.py` with retry configuration, timeout limits, logging, and error handling on all three existing tasks.
    *   A new task `flaky_task()` that randomly fails 70% of the time to demonstrate retries.
    *   A new task `slow_task()` that sleeps for 60 seconds to demonstrate timeout enforcement.
    *   A new Flask endpoint `POST /test-reliability` that triggers the flaky task.
    *   **Verification:** Terminal output showing:
        *   Worker logs displaying retry attempts: `Task app.tasks.flaky_task[abc-123] retry: Attempt 1/3`
        *   Timeout termination: `Task app.tasks.slow_task[def-456] raised unexpected: TimeLimitExceeded(30,)`
        *   Status endpoint returning `RETRY` and `FAILURE` states with error messages
        *   Structured logs showing task start/complete/fail events with timestamps
