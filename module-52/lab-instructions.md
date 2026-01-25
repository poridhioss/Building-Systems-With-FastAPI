This structure allows students to grasp the "Pure Python" concepts of distributed tasks before integrating them into a web API in Module 53.

---

### **Lab 1: The Asynchronous Architecture (Producer, Broker, Worker)**
**Context:** In this lab, you will strip away web frameworks to build the "Hello World" of distributed computing. You will manually set up and interact with the three core components of Celery: the Producer (Sender), the Broker (Message Queue), and the Consumer (Worker). This "Fire and Forget" model is the foundation of asynchronous processing.

*   **Goals:**
    *   **Infrastructure Setup:** Provision a **Redis** container to act as the **Message Broker**.
    *   **The Worker (Consumer):** Create a standalone Python script (`tasks.py`) that defines a Celery instance and a function simulating a long-running process (e.g., a 10-second sleep).
    *   **The Producer:** Use a Python shell to "produce" messages and push them into the Redis Broker.
    *   **Architecture Visualization:** Explicitly demonstrate the flow of data: *Producer $\rightarrow$ Redis Broker $\rightarrow$ Celery Worker*, validating that the Producer returns instantly while the Worker processes in the background.
*   **Deliverables:**
    *   A `docker-compose.yml` file running the Redis service.
    *   A `tasks.py` file containing the Celery application definition.
    *   **Evidence:** A split-terminal screenshot.
        *   **Terminal A (Producer):** Shows the command returning a Task ID immediately.
        *   **Terminal B (Worker):** Shows the log entry `Task received` followed 10 seconds later by `Task succeeded`.

---

### **Lab 2: Closing the Loop (The Result Backend)**
**Context:** In the previous lab, we sent tasks blindly ("Fire and Forget"). In real-world scenarios, we often need to know *if* a task finished and *what* the result was. This lab introduces the fourth component of the architecture: the **Result Backend**. You will learn how the Worker writes data back to storage and how the Producer can retrieve it.

*   **Goals:**
    *   **Backend Configuration:** Modify the Celery configuration to use Redis as the **Result Backend** (distinct from its role as a Broker).
    *   **State Management:** Implement a polling script (`client.py`) that uses the Task ID to query the status of a job (`PENDING` vs `SUCCESS`).
    *   **Architecture Visualization:** Update the mental model to demonstrate the "Round Trip" architecture: *Worker $\rightarrow$ writes result to Backend $\rightarrow$ Producer queries Backend*.
    *   **Data Retrieval:** Successfully fetch the return value (e.g., a calculation result) from Redis after the worker completes the task.
*   **Deliverables:**
    *   An updated `tasks.py` with `backend='redis://...'` configuration.
    *   A Python script (`client.py`) that triggers a task and loops until the status changes to SUCCESS.
    *   **Verification:** A terminal output log showing the state transition: `Status: PENDING` ... `Status: PENDING` ... `Status: SUCCESS` ... `Result: 100`.