In Module 54, you built a reliable task queue with retries, timeouts, error handling, and logging. Your Celery workers are now production-ready, but there's a critical gap: **visibility**. When tasks fail in production, you need to answer questions like: "Which tasks are currently running?", "How many tasks failed in the last hour?", "Why is this worker slow?", "Are tasks piling up in the queue?"

Without a monitoring tool, answering these questions means parsing logs manually or writing custom scripts. That's where **Flower** comes in—a real-time web-based monitoring tool for Celery that provides instant visibility into task states, worker health, and queue backlogs.

---

### **Lab 1: Monitoring Celery Workers with Flower**
**Context:** Flower is a real-time monitoring dashboard for Celery that shows task execution, worker status, task history, and performance metrics. In this lab, you will install Flower, connect it to your existing Flask-Celery application from Module 54, and learn how to use it to monitor task execution, debug failures, inspect worker health, and track task routing. You'll also secure the dashboard with basic authentication to prevent unauthorized access in production environments.

*   **Goals:**
    *   **Installation:** Install Flower as a Python package and understand its role in the Celery ecosystem.
    *   **Dashboard Access:** Launch the Flower web UI and connect it to your Redis broker and backend.
    *   **Real-Time Monitoring:** Monitor tasks as they execute, observing state transitions (PENDING → STARTED → SUCCESS/FAILURE/RETRY).
    *   **Task Inspection:** View task arguments, return values, exception tracebacks, and retry history.
    *   **Worker Health:** Monitor active workers, their concurrency settings, and resource usage.
    *   **Performance Analysis:** Use the task timeline to identify slow tasks and bottlenecks.
    *   **Security (Optional):** Configure basic authentication to protect the Flower dashboard.
    *   **Production Setup (Optional):** Deploy Flower behind Nginx as a reverse proxy.
*   **Deliverables:**
    *   A running Flower dashboard accessible at `http://localhost:5555`
    *   Screenshots showing the Tasks, Workers, and Monitor pages with active task execution
    *   Verification of task state transitions in the Flower UI as tasks are triggered via Flask endpoints
    *   (Optional) Flower dashboard secured with username/password authentication
    *   (Optional) Nginx configuration for reverse proxy setup
