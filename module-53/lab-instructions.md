In Module 52, students ran standalone Python scripts. In Module 53, the focus shifts to **Web Application Integration**, specifically solving the problem of "How do I make my Flask API respond immediately while doing heavy work in the background?"

---

### **Lab 1: The Flask-Celery Application Factory**
**Context:** Integrating Celery with Flask can be tricky due to how Flask handles "Application Contexts" (the state of the application). If not done correctly, your background tasks won't have access to your database or app configuration. In this lab, you will set up the foundational project structure using the "Application Factory" pattern, ensuring Flask and Celery can initialize together without circular import errors.

*   **Goals:**
    *   **Environment:** Install `Flask` and `celery[redis]` and spin up the Redis container (Broker/Backend) using Docker Compose.
    *   **Configuration:** Create a `config.py` file to manage Celery settings (Broker URL, Result Backend) alongside Flask settings.
    *   **The Factory Pattern:** Implement a utility function (e.g., `make_celery(app)`) that bridges the Flask app context with the Celery worker instance.
    *   **Health Check:** Create a simple `POST /ping` endpoint that triggers a background `test_task` to verify the wiring is correct.
*   **Deliverables:**
    *   A `celery_utils.py` file containing the context-binding logic.
    *   An `app.py` (or `__init__.py`) initializing both Flask and Celery.
    *   **Verification:** A Postman request to `/ping` returning `202 Accepted` immediately, while the specific string "Pong from Background!" appears in the Celery Worker terminal logs.

---

### **Lab 2: Implementing Real-World Use Cases (Email & PDF)**
**Context:** Now that the infrastructure is stable, we will implement the specific use cases mentioned in the syllabus. You will simulate two common bottlenecks in web development: sending email notifications (network latency) and generating PDF reports (CPU intensity). You will learn how to structure your API to "Fire and Forget" these tasks.

*   **Goals:**
    *   **Task Definition:** Define two distinct Celery tasks:
        *   `send_welcome_email(user_email)`: Simulates a 5-second network delay.
        *   `generate_monthly_report(user_id)`: Simulates a 10-second CPU-intensive process.
    *   **API Endpoints:** Create corresponding Flask routes:
        *   `POST /register`: Saves user (simulated) $\rightarrow$ Triggers email task $\rightarrow$ Returns `201 Created` instantly.
        *   `POST /reports/generate`: Triggers PDF task $\rightarrow$ Returns `202 Accepted` with the Task ID.
    *   **Latency Analysis:** Compare the execution time. Students must observe that the HTTP response takes milliseconds, even though the task logic takes seconds.
*   **Deliverables:**
    *   A `tasks.py` file containing the business logic.
    *   The updated `routes.py` with the new endpoints.
    *   **Evidence:** A split-screen view showing Postman receiving an immediate JSON response (e.g., `{"message": "Email queued"}`) while the Celery Worker terminal shows the "Email Sent" log 5 seconds later.