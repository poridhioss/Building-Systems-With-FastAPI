In Module 52, students ran standalone Python scripts. In Module 53, the focus shifts to **Web Application Integration**, specifically solving the problem of "How do I make my Flask API respond immediately while doing heavy work in the background?"

---

### **Lab 1: Flask-Celery Integration with Real-World Use Cases**
**Context:** Integrating Celery with Flask can be tricky due to how Flask handles "Application Contexts" (the state of the application). If not done correctly, your background tasks won't have access to your database or app configuration. In this lab, you will set up the complete Flask-Celery infrastructure using the "Application Factory" pattern and implement real-world use cases: sending email notifications (network latency) and generating PDF reports (CPU intensity). You will learn how to structure your API to "Fire and Forget" these tasks.

*   **Goals:**
    *   **Environment:** Install `Flask` and `celery[redis]` and spin up the Redis container (Broker/Backend) using Docker Compose.
    *   **Configuration:** Create a `config.py` file to manage Celery settings (Broker URL, Result Backend) alongside Flask settings.
    *   **The Factory Pattern:** Implement a utility function (e.g., `make_celery(app)`) that bridges the Flask app context with the Celery worker instance.
    *   **Task Definition:** Define three Celery tasks:
        *   `test_task()`: Simple health check that prints "Pong from Background!"
        *   `send_welcome_email(user_email)`: Simulates a 5-second network delay.
        *   `generate_monthly_report(user_id)`: Simulates a 10-second CPU-intensive process.
    *   **API Endpoints:** Create Flask routes:
        *   `POST /ping`: Triggers `test_task` to verify the wiring is correct.
        *   `POST /register`: Saves user (simulated) $\rightarrow$ Triggers email task $\rightarrow$ Returns `201 Created` instantly.
        *   `POST /reports/generate`: Triggers PDF task $\rightarrow$ Returns `202 Accepted` with the Task ID.
    *   **Latency Analysis:** Compare the execution time. Students must observe that the HTTP response takes milliseconds, even though the task logic takes seconds.
*   **Deliverables:**
    *   A `celery_utils.py` file containing the context-binding logic.
    *   An `app/__init__.py` initializing both Flask and Celery.
    *   A `tasks.py` file containing all three background tasks.
    *   A `routes.py` with all three endpoints.
    *   **Verification:** Terminal curl requests returning immediately (202/201) while the Celery Worker terminal shows task execution logs appearing 3-10 seconds later.